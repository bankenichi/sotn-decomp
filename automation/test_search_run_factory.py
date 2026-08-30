"""Focused tests for the bounded production search-run creator."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation import search_cli  # noqa: E402
from automation import search_run_factory as _factory  # noqa: E402
from automation.mcp import commands_client as cc  # noqa: E402
from automation.search_coordinator import SearchCoordinator  # noqa: E402
from automation.search_lanes import LaneCandidate  # noqa: E402
from automation.search_recovery import recover_run  # noqa: E402
from automation.search_run_factory import (  # noqa: E402
    EvidenceRefusal,
    InputRefusal,
    PartialRunRefusal,
    RunNameCollision,
    create_instrumented_run,
)
from automation.search_supervisor import (  # noqa: E402
    SupervisorIntegrationError,
    run_instrumented,
)
from automation.search_types import (  # noqa: E402
    ArtifactRef,
    CandidateRecord,
    LANES,
    MAX_CHILD_TASKS_PER_BASE,
    MAX_COORDINATOR_TASKS,
    RunManifest,
    hash_bytes,
)


IDS = (
    "us:ST/RNO0:func_a",
    "us:ST/RNO1:func_b",
)


class FactoryFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="search-run-factory-")
        self.repo = Path(self.temp.name)
        (self.repo / "src").mkdir()
        (self.repo / "include").mkdir()
        (self.repo / "automation").mkdir()
        (self.repo / "tools" / "sotn_permuter").mkdir(parents=True)
        (self.repo / "src" / "source.c").write_text("int source;\n", encoding="utf-8")
        (self.repo / "include" / "header.h").write_text("#define X 1\n", encoding="utf-8")
        (self.repo / "automation" / "search_lanes.py").write_text(
            "LANE_IMPLEMENTATION = 1\n", encoding="utf-8"
        )
        (self.repo / "automation" / "search_supervisor.py").write_text(
            "SUPERVISOR_IMPLEMENTATION = 1\n", encoding="utf-8"
        )
        (self.repo / "automation" / "search_run_factory.py").write_text(
            "FACTORY_IMPLEMENTATION = 1\n", encoding="utf-8"
        )
        for module in (
            "search_coordinator.py",
            "search_types.py",
            "search_archive.py",
            "search_recovery.py",
            "upstream_harvest.py",
            "shim_sweep.py",
            "asm_twin_finder.py",
            "transplant.py",
        ):
            (self.repo / "automation" / module).write_text(
                f"{module.replace('.', '_')} = 1\n", encoding="utf-8"
            )
        (self.repo / "automation" / "search-ledger.schema.json").write_text(
            "{}\n", encoding="utf-8"
        )
        (self.repo / "tools" / "sotn_permuter" / "permuter_settings.us.toml").write_text(
            "compiler_command = 'cc | ld'\n", encoding="utf-8"
        )
        for build, overlay, function, unit in (
            ("us", "ST/RNO0", "func_a", "unit_a"),
            ("us", "ST/RNO1", "func_b", "unit_b"),
        ):
            asm = self.repo / "asm" / build / Path(*overlay.lower().split("/")) / "nonmatchings" / unit
            obj = self.repo / "build" / build / "src" / Path(*overlay.lower().split("/"))
            asm.mkdir(parents=True)
            obj.mkdir(parents=True)
            (asm / f"{function}.s").write_text(f"{function}:\n\tnop\n", encoding="utf-8")
            (obj / f"{unit}.c.o").write_bytes((function + " object\n").encode("ascii"))
        self.records = [
            {
                "id": IDS[0],
                "build": "us",
                "overlay": "ST/RNO0",
                "function": "func_a",
                "status": "todo",
                "claimed_by": "none",
                "notes": (
                    "a long queue proof " + "x" * 500 +
                    " asm=asm/us/st/rno0/nonmatchings/unit_a/func_a.s"
                    " object=build/us/src/st/rno0/unit_a.c.o"
                ),
                "updated_at": "2026-08-28T00:00:00Z",
            },
            {
                "id": IDS[1],
                "build": "us",
                "overlay": "ST/RNO1",
                "function": "func_b",
                "status": "todo",
                "claimed_by": "none",
                "notes": (
                    "second proof asm=asm/us/st/rno1/nonmatchings/unit_b/func_b.s"
                    " object=build/us/src/st/rno1/unit_b.c.o"
                ),
                "updated_at": "2026-08-28T00:00:00Z",
            },
        ]
        self.before_records = json.loads(json.dumps(self.records))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create(
        self,
        name: str,
        ids=IDS,
        lanes=None,
        *,
        queue_reader=None,
        compiler_identity_resolver=None,
        now=None,
        fault_hook=None,
    ):
        selected = lanes or [LANES[0], LANES[14]]
        return create_instrumented_run(
            name,
            ids,
            selected,
            repo=self.repo,
            queue_reader=queue_reader or (lambda: self.records),
            compiler_identity_resolver=(
                compiler_identity_resolver
                or (lambda _path: hash_bytes(b"compiler-v1"))
            ),
            now=now or (lambda: "2026-08-28T00:00:00Z"),
            fault_hook=fault_hook,
        )

    def test_one_record_captures_full_queue_and_exact_targets(self) -> None:
        result = self.create("run-one", ids=[IDS[0]])
        manifest_path = self.repo / "nonmatchings" / "func_a" / "search-runs" / "run-one" / "manifest.json"
        manifest = RunManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        self.assertFalse(result["idempotent"])
        self.assertEqual(manifest.queue_record_ids, (IDS[0],))
        self.assertEqual(manifest.function_ids, ("func_a",))
        self.assertIn("search_supervisor_mode", manifest.tool_identities)
        self.assertNotIn("full_oracle", manifest.tool_identities)
        self.assertEqual(set(manifest.target_identities), {IDS[0]})
        self.assertEqual(self.records, self.before_records)
        index_path = manifest_path.parent / result["evidence_index"]["path"]
        index = json.loads(index_path.read_text(encoding="utf-8"))
        queue_ref = index["queue_evidence"]
        queue_doc = json.loads((manifest_path.parent / queue_ref["path"]).read_text(encoding="utf-8"))
        self.assertEqual(queue_doc["records"][0]["notes"], self.records[0]["notes"])
        target_ref = index["target_evidence"][IDS[0]]
        self.assertEqual(target_ref["content_hash"], manifest.target_identities[IDS[0]])
        target_doc = json.loads((manifest_path.parent / target_ref["path"]).read_text(encoding="utf-8"))
        self.assertTrue(target_doc["assembly"]["path"].endswith("func_a.s"))
        self.assertTrue(target_doc["object"]["path"].endswith("unit_a.c.o"))

    def test_multiple_records_and_lanes_use_canonical_order_and_anchor(self) -> None:
        result = self.create(
            "run-many",
            ids=list(reversed(IDS)),
            lanes=["permuter_targeted", "upstream_current"],
        )
        manifest = result["manifest"]
        self.assertEqual(manifest["queue_record_ids"], list(IDS))
        self.assertEqual(manifest["selected_lanes"], ["upstream_current", "permuter_targeted"])
        self.assertEqual(result["anchor_function"], "func_a")
        self.assertTrue((self.repo / "nonmatchings" / "func_a" / "search-runs" / "run-many" / "manifest.json").is_file())

    def test_missing_and_non_todo_records_are_refused_without_fallback(self) -> None:
        with self.assertRaises(InputRefusal):
            self.create("missing", ids=["us:ST/RNO0:func_missing"])
        self.records[0]["status"] = "claimed"
        with self.assertRaises(InputRefusal):
            self.create("claimed", ids=[IDS[0]])
        self.assertFalse((self.repo / "nonmatchings" / "func_a" / "search-runs" / "claimed" / "manifest.json").exists())

    def test_validation_rejects_duplicates_unknown_lanes_and_unsafe_components(self) -> None:
        with self.assertRaises(InputRefusal):
            self.create("../escape")
        with self.assertRaises(InputRefusal):
            self.create("duplicate", ids=[IDS[0], IDS[0]])
        with self.assertRaises(InputRefusal):
            self.create("bad-lane", lanes=[LANES[0], LANES[0]])
        with self.assertRaises(InputRefusal):
            self.create("unknown-lane", lanes=["unknown"])
        for bad in ("../bad", "us:ST/RNO0:func_a/../x", "us:ST/RNO0:func-a", "us:ST//RNO0:func_a"):
            with self.assertRaises(InputRefusal):
                self.create("bad-id", ids=[bad])

    def test_run_name_boundary_matches_manifest_and_resolver_contract(self) -> None:
        name = "n" * 64
        result = self.create(name, ids=[IDS[0]], lanes=[LANES[0]])
        manifest = RunManifest.from_dict(result["manifest"])
        self.assertEqual(manifest.run_id, name)
        with self.assertRaises(InputRefusal):
            self.create("n" * 65, ids=[IDS[0]], lanes=[LANES[0]])

    def test_exact_retry_is_idempotent_and_conflict_is_immutable(self) -> None:
        first = self.create("retry", ids=[IDS[0]], lanes=[LANES[0]])
        second = self.create("retry", ids=[IDS[0]], lanes=[LANES[0]])
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        with self.assertRaises(RunNameCollision):
            self.create("retry", ids=[IDS[0]], lanes=[LANES[1]])

    def test_corrupt_artifact_is_refused_not_repaired(self) -> None:
        result = self.create("corrupt", ids=[IDS[0]])
        root = Path(result["run_root"])
        index_path = root / result["evidence_index"]["path"]
        index = json.loads(index_path.read_text(encoding="utf-8"))
        target_path = root / index["target_evidence"][IDS[0]]["path"]
        target_doc = json.loads(target_path.read_text(encoding="utf-8"))
        object_path = root / target_doc["object"]["artifact"]["path"]
        object_path.unlink()
        with self.assertRaises(PartialRunRefusal):
            self.create("corrupt", ids=[IDS[0]])

    def test_corrupt_index_is_refused_not_repaired(self) -> None:
        result = self.create("corrupt-index", ids=[IDS[0]])
        root = Path(result["run_root"])
        index_path = root / result["evidence_index"]["path"]
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["unexpected"] = "edited"
        index_path.write_text(json.dumps(index) + "\n", encoding="utf-8")
        with self.assertRaises(PartialRunRefusal):
            self.create("corrupt-index", ids=[IDS[0]])

    def test_cli_status_ledger_and_stop_refuse_corrupt_archive_without_runtime_inputs(self) -> None:
        result = self.create("cli-corrupt-archive", ids=[IDS[0]], lanes=[LANES[0]])
        root = Path(result["run_root"])
        manifest = RunManifest.from_dict(result["manifest"])
        SearchCoordinator(root, manifest)
        index = json.loads(
            (root / result["evidence_index"]["path"]).read_text(encoding="utf-8")
        )
        (root / index["source"]["path"]).unlink()

        with mock.patch.object(
            _factory,
            "_source_identity",
            side_effect=AssertionError("status paths must not remeasure source"),
        ), mock.patch.object(
            _factory,
            "_read_queue_from_scheduler",
            side_effect=AssertionError("status paths must not read the queue"),
        ), mock.patch.object(
            SearchCoordinator,
            "stop",
            side_effect=AssertionError("stop must not act on corrupt evidence"),
        ):
            for operation in (
                search_cli.status_run,
                search_cli.verify_ledger,
                search_cli.stop_run,
            ):
                with self.subTest(operation=operation.__name__):
                    with self.assertRaises(search_cli.RunInputError):
                        operation(root)

    def test_unpublished_temporary_is_refused_not_repaired(self) -> None:
        result = self.create("temporary", ids=[IDS[0]])
        root = Path(result["run_root"])
        (root / ".manifest.json.tmp-crashed").write_bytes(b"incomplete")
        with self.assertRaises(PartialRunRefusal):
            self.create("temporary", ids=[IDS[0]])

    def test_partial_root_without_manifest_is_refused(self) -> None:
        partial = (
            self.repo / "nonmatchings" / "func_a" / "search-runs" / "partial"
            / "artifacts"
        )
        partial.mkdir(parents=True)
        (partial / "leftover.bin").write_bytes(b"partial")
        with self.assertRaises(PartialRunRefusal):
            self.create("partial", ids=[IDS[0]])

    def test_symlinked_run_root_is_refused(self) -> None:
        parent = self.repo / "nonmatchings" / "func_a" / "search-runs"
        parent.mkdir(parents=True)
        target = self.repo / "safe-target"
        target.mkdir()
        run_root = parent / "symlink-run"
        try:
            run_root.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(PartialRunRefusal):
            self.create("symlink-run", ids=[IDS[0]])

    def test_exact_retry_ignores_queue_drift_and_queue_read_errors(self) -> None:
        first = self.create("identity", ids=[IDS[0]], lanes=[LANES[0]])
        self.records[0]["notes"] += " changed"
        self.records[0]["status"] = "claimed"

        def queue_must_not_be_read():
            raise AssertionError("exact retry must resolve from archived evidence first")

        second = self.create(
            "identity",
            ids=[IDS[0]],
            lanes=[LANES[0]],
            queue_reader=queue_must_not_be_read,
            now=lambda: (_ for _ in ()).throw(
                AssertionError("exact retry must not read the clock")
            ),
        )
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["manifest"], second["manifest"])

    def test_changed_logical_selection_collides_before_queue_read(self) -> None:
        self.create("identity-collision", ids=[IDS[0]], lanes=[LANES[0]])

        def queue_must_not_be_read():
            raise AssertionError("logical collision must resolve before queue read")

        with self.assertRaises(RunNameCollision):
            self.create(
                "identity-collision",
                ids=[IDS[1]],
                lanes=[LANES[0]],
                queue_reader=queue_must_not_be_read,
            )

    def test_same_name_at_another_anchor_is_refused_before_creating_a_second_root(self) -> None:
        other = (
            self.repo / "nonmatchings" / "other_function" / "search-runs" / "global-name"
        )
        other.mkdir(parents=True)
        (other / "manifest.json").write_text(
            json.dumps({"run_id": "global-name"}) + "\n", encoding="utf-8"
        )
        with self.assertRaises(RunNameCollision):
            self.create("global-name", ids=[IDS[0]])
        self.assertFalse(
            (self.repo / "nonmatchings" / "func_a" / "search-runs" / "global-name").exists()
        )

    def test_cli_factory_uses_scheduler_queue_and_existing_connector_resolver(self) -> None:
        queue_path = self.repo / "live-queue.jsonl"
        queue_path.write_text(
            "".join(json.dumps(record) + "\n" for record in self.records),
            encoding="utf-8",
        )
        queue_before = queue_path.read_bytes()
        previous_scheduler = sys.modules.pop("automation.scheduler", None)
        saved_repo = cc.REPO
        try:
            with mock.patch.dict(
                os.environ,
                {"SOTN_REPO": str(self.repo), "SOTN_QUEUE": str(queue_path)},
                clear=False,
            ), mock.patch(
                "automation.search_run_factory._compiler_identity",
                return_value=(hash_bytes(b"compiler-v1"), {"identity": hash_bytes(b"compiler-v1")}),
            ):
                planned = search_cli.plan_selection(
                    record_groups=[[IDS[1], IDS[0]]],
                    lane_groups=[["permuter_targeted", "upstream_current"]],
                )
                created = search_cli.create_instrumented_run(
                    "cli-path", planned.record_ids, planned.lanes
                )
            cc.REPO = self.repo
            start_argv = cc.build_argv(
                "search_start_instrumented", run_id="cli-path"
            )
            self.assertEqual(created["anchor_function"], "func_a")
            self.assertEqual(start_argv[-1], str(self.repo / "nonmatchings" / "func_a" / "search-runs" / "cli-path" / "manifest.json"))
            self.assertEqual(self.records, self.before_records)
            self.assertEqual(queue_path.read_bytes(), queue_before)
        finally:
            cc.REPO = saved_repo
            if previous_scheduler is None:
                sys.modules.pop("automation.scheduler", None)
            else:
                sys.modules["automation.scheduler"] = previous_scheduler
        if previous_scheduler is None:
            self.assertNotIn("automation.scheduler", sys.modules)
        else:
            self.assertIs(sys.modules.get("automation.scheduler"), previous_scheduler)

    @staticmethod
    def _candidate(source: str, *, recipient_id: str = IDS[0], lane: str = LANES[0]):
        data = source.encode("utf-8")
        artifact = ArtifactRef(
            hash_bytes(data),
            "artifacts/objects/" + hash_bytes(data)[7:] + ".bin",
            "application/octet-stream",
            len(data),
        )
        return CandidateRecord(
            artifact.content_hash,
            recipient_id,
            artifact,
            (),
            None,
            lane,
            0,
            None,
            "materialized",
        )

    def _runtime_refusal(self, result, mutate) -> None:
        manifest_path = Path(result["run_root"]) / "manifest.json"
        manifest = RunManifest.from_dict(result["manifest"])
        mutate()
        adapter_calls = []

        def adapter(_recipient):
            adapter_calls.append(True)
            return None

        with mock.patch.object(
            _factory,
            "_compiler_identity",
            return_value=(manifest.compiler_identity, {"identity": manifest.compiler_identity}),
        ), mock.patch.object(SearchCoordinator, "start_task") as started:
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    manifest_path,
                    adapters={manifest.selected_lanes[0]: adapter},
                    lease_path=self.repo / "lease.json",
                )
        self.assertFalse(started.called)
        self.assertEqual(adapter_calls, [])

    def test_factory_run_executes_base_and_child_tasks_with_bounded_ordinals(self) -> None:
        result = self.create("factory-run", ids=[IDS[0]], lanes=[LANES[0]])
        manifest_path = Path(result["run_root"]) / "manifest.json"
        first = self._candidate("factory-candidate-one")
        second = self._candidate("factory-candidate-two")
        adapters = {
            LANES[0]: lambda _recipient: {
                "candidates": [
                    LaneCandidate(first, "factory-candidate-one"),
                    LaneCandidate(second, "factory-candidate-two"),
                ]
            }
        }
        with mock.patch.object(
            _factory,
            "_compiler_identity",
            return_value=(
                RunManifest.from_dict(result["manifest"]).compiler_identity,
                {"identity": RunManifest.from_dict(result["manifest"]).compiler_identity},
            ),
        ):
            run_result = run_instrumented(
                manifest_path,
                adapters=adapters,
                lease_path=self.repo / "lease.json",
            )
        state = recover_run(Path(result["run_root"]))
        scheduled = [
            event.payload for event in state.events
            if event.event_type == "task_scheduled"
        ]
        terminals = [
            event.payload for event in state.events
            if event.event_type == "task_completed"
        ]
        self.assertEqual(len(scheduled), 3)
        self.assertEqual(len(terminals), 3)
        self.assertEqual(
            [task.budget_ordinal for task in scheduled],
            [0, 1, 2],
        )
        self.assertEqual(
            RunManifest.from_dict(result["manifest"]).coordinator_budget.limit,
            3,
        )
        self.assertEqual(
            set(run_result["state"]["completed_task_ids"]),
            {task.task_id for task in terminals},
        )

    def test_three_candidate_fan_out_is_refused_before_child_scheduling(self) -> None:
        result = self.create("fanout-cap", ids=[IDS[0]], lanes=[LANES[0]])
        manifest = RunManifest.from_dict(result["manifest"])
        manifest_path = Path(result["run_root"]) / "manifest.json"
        candidates = [
            (self._candidate("fanout-candidate-one"), "fanout-candidate-one"),
            (self._candidate("fanout-candidate-two"), "fanout-candidate-two"),
            (self._candidate("fanout-candidate-three"), "fanout-candidate-three"),
        ]
        adapters = {
            LANES[0]: lambda _recipient: {
                "candidates": [
                    LaneCandidate(candidate, source)
                    for candidate, source in candidates
                ]
            }
        }
        with mock.patch.object(
            _factory,
            "_compiler_identity",
            return_value=(
                manifest.compiler_identity,
                {"identity": manifest.compiler_identity},
            ),
        ):
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    manifest_path,
                    adapters=adapters,
                    lease_path=self.repo / "fanout-lease.json",
                )

        state = recover_run(Path(result["run_root"]))
        scheduled = [
            event.payload
            for event in state.events
            if event.event_type == "task_scheduled"
        ]
        self.assertEqual([task.budget_ordinal for task in scheduled], [0])
        self.assertFalse(
            any(task.operation.startswith("materialize_candidate:") for task in scheduled)
        )

    def test_coordinator_budget_includes_children_and_stays_globally_capped(self) -> None:
        self.assertEqual(MAX_COORDINATOR_TASKS, 4096)
        self.assertEqual(MAX_CHILD_TASKS_PER_BASE, 2)
        self.assertEqual(_factory._MAX_COORDINATOR_TASKS, MAX_COORDINATOR_TASKS)
        self.assertEqual(_factory._MAX_CHILD_TASKS_PER_BASE, MAX_CHILD_TASKS_PER_BASE)
        self.assertEqual(
            _factory._MAX_TASKS * (1 + MAX_CHILD_TASKS_PER_BASE),
            4095,
        )
        self.assertLessEqual(
            _factory._MAX_TASKS * (1 + MAX_CHILD_TASKS_PER_BASE),
            MAX_COORDINATOR_TASKS,
        )
        self.assertGreater(
            (_factory._MAX_TASKS + 1) * (1 + MAX_CHILD_TASKS_PER_BASE),
            MAX_COORDINATOR_TASKS,
        )
        with mock.patch.object(_factory, "MAX_COORDINATOR_TASKS", 6), mock.patch.object(
            _factory, "_MAX_TASKS", 2
        ):
            result = self.create(
                "budget-boundary",
                ids=[IDS[0]],
                lanes=[LANES[0], LANES[1]],
            )
            manifest = RunManifest.from_dict(result["manifest"])
            self.assertEqual(manifest.coordinator_budget.limit, 6)
            with self.assertRaises(InputRefusal):
                self.create(
                    "budget-over",
                    ids=IDS,
                    lanes=[LANES[0], LANES[1]],
                )

    def test_factory_crash_after_index_recovers_without_queue_or_clock(self) -> None:
        points = []
        clock_calls = []

        def fault(point):
            points.append(point)
            if point == "after_durable_index":
                raise KeyboardInterrupt("simulated loss after durable index")

        def clock():
            clock_calls.append(True)
            return "2026-08-28T00:00:00Z"

        with self.assertRaises(KeyboardInterrupt):
            self.create(
                "recover-index",
                ids=[IDS[0]],
                lanes=[LANES[0]],
                now=clock,
                fault_hook=fault,
            )
        self.records[0]["status"] = "claimed"

        def queue_must_not_be_read():
            raise AssertionError("recovery retry must use the durable intent")

        second = self.create(
            "recover-index",
            ids=[IDS[0]],
            lanes=[LANES[0]],
            queue_reader=queue_must_not_be_read,
            now=lambda: (_ for _ in ()).throw(
                AssertionError("recovery retry must not read the clock")
            ),
        )
        self.assertTrue(second["idempotent"])
        self.assertTrue(second["recovered"])
        self.assertEqual(points, ["after_durable_index"])
        self.assertEqual(len(clock_calls), 1)
        self.assertEqual(second["manifest"]["created_at"], "2026-08-28T00:00:00Z")

    def test_queue_id_accepts_tt_component_and_rejects_malformed_or_overlong_overlay(self) -> None:
        self.assertEqual(cc._queue_id("us:TT_000:func_a"), "us:TT_000:func_a")
        self.assertEqual(cc._queue_id("us:ST_0/TT_000:func_a"), "us:ST_0/TT_000:func_a")
        for malformed in (
            "us::func_a",
            "us:ST//TT_000:func_a",
            "us:st/TT_000:func_a",
            "us:ST-TT:func_a",
            "us:" + "A" * 33 + ":func_a",
        ):
            with self.assertRaises(cc.Rejected):
                cc._queue_id(malformed)

    def test_source_drift_is_refused_before_adapter_or_task_start(self) -> None:
        result = self.create("source-drift", ids=[IDS[0]], lanes=[LANES[0]])
        (self.repo / "src" / "source.c").write_text("int changed;\n", encoding="utf-8")
        self._runtime_refusal(result, lambda: None)

    def test_target_drift_is_refused_before_adapter_or_task_start(self) -> None:
        result = self.create("target-drift", ids=[IDS[0]], lanes=[LANES[0]])
        target = self.repo / "asm" / "us" / "st" / "rno0" / "nonmatchings" / "unit_a" / "func_a.s"
        target.write_text("func_a:\n\tmove $v0, $v0\n", encoding="utf-8")
        self._runtime_refusal(result, lambda: None)

    def test_config_schema_and_core_tool_drift_are_refused_before_task_start(self) -> None:
        result = self.create("config-drift", ids=[IDS[0]], lanes=[LANES[0]])
        (self.repo / "tools" / "sotn_permuter" / "permuter_settings.us.toml").write_text(
            "compiler_command = 'changed'\n", encoding="utf-8"
        )
        self._runtime_refusal(result, lambda: None)

        result = self.create("schema-drift", ids=[IDS[0]], lanes=[LANES[0]])
        (self.repo / "automation" / "search-ledger.schema.json").write_text(
            "{\"changed\": true}\n", encoding="utf-8"
        )
        self._runtime_refusal(result, lambda: None)

        result = self.create("tool-drift", ids=[IDS[0]], lanes=[LANES[0]])
        (self.repo / "automation" / "search_lanes.py").write_text(
            "LANE_IMPLEMENTATION = 2\n", encoding="utf-8"
        )
        self._runtime_refusal(result, lambda: None)

    def test_tampered_factory_marker_is_not_treated_as_legacy(self) -> None:
        result = self.create(
            "tampered-marker",
            ids=[IDS[0]],
            lanes=[LANES[0]],
        )
        root = Path(result["run_root"])
        manifest = RunManifest.from_dict(result["manifest"])
        for marker in ("changed", "missing"):
            raw = manifest.to_dict()
            if marker == "changed":
                raw["tool_identities"][_factory._FACTORY_MARKER_KEY] = hash_bytes(
                    b"tampered-marker"
                )
            else:
                raw["tool_identities"].pop(_factory._FACTORY_MARKER_KEY)
            tampered = RunManifest.from_dict(raw)
            with self.subTest(marker=marker):
                with self.assertRaises(PartialRunRefusal):
                    _factory.verify_factory_archive(root, tampered)

    def test_dynamic_lane_module_drift_is_refused_before_task_start(self) -> None:
        result = self.create(
            "dynamic-module-drift",
            ids=[IDS[0]],
            lanes=["shared_header"],
        )
        (self.repo / "automation" / "shim_sweep.py").write_text(
            "SHIM_IMPLEMENTATION = 2\n", encoding="utf-8"
        )
        self._runtime_refusal(result, lambda: None)

    def test_upstream_current_ref_drift_is_refused_before_task_start(self) -> None:
        ref = self.repo / ".git" / "refs" / "remotes" / "upstream" / "master"
        ref.parent.mkdir(parents=True)
        ref.write_text("a" * 40 + "\n", encoding="ascii")
        result = self.create(
            "upstream-ref-drift",
            ids=[IDS[0]],
            lanes=["upstream_current"],
        )
        ref.write_text("b" * 40 + "\n", encoding="ascii")
        self._runtime_refusal(result, lambda: None)

    def test_compiler_and_preserved_candidate_drift_are_refused_before_task_start(self) -> None:
        result = self.create("compiler-drift", ids=[IDS[0]], lanes=[LANES[0]])
        manifest = RunManifest.from_dict(result["manifest"])
        with mock.patch.object(
            _factory,
            "_compiler_identity",
            return_value=(hash_bytes(b"compiler-v2"), {"identity": hash_bytes(b"compiler-v2")}),
        ), mock.patch.object(SearchCoordinator, "start_task") as started:
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    Path(result["run_root"]) / "manifest.json",
                    adapters={LANES[0]: lambda _recipient: None},
                    lease_path=self.repo / "compiler-lease.json",
                )
        self.assertFalse(started.called)

        candidates = self.repo / "automation" / "candidates"
        candidates.mkdir()
        (candidates / "saved.c").write_text("int candidate;\n", encoding="utf-8")
        result = self.create(
            "candidate-drift",
            ids=[IDS[0]],
            lanes=["preserved_candidate"],
        )
        (candidates / "saved.c").write_text("int changed;\n", encoding="utf-8")
        self._runtime_refusal(result, lambda: None)

    def test_explicit_target_hints_cannot_escape_record_trees(self) -> None:
        self.records[0]["asm"] = "src/source.c"
        with self.assertRaises(EvidenceRefusal):
            self.create("bad-target", ids=[IDS[0]])

    def test_ambiguous_target_candidates_are_refused(self) -> None:
        duplicate = (
            self.repo / "asm" / "us" / "st" / "rno0" / "nonmatchings" / "unit_other"
        )
        duplicate.mkdir(parents=True)
        (duplicate / "func_a.s").write_text("func_a:\n\tnop\n", encoding="utf-8")
        with self.assertRaises(EvidenceRefusal):
            self.create("ambiguous-target", ids=[IDS[0]])

    def test_symlinked_target_tree_is_refused(self) -> None:
        symlink = self.repo / "asm" / "us" / "st" / "rno0" / "nonmatchings" / "link"
        try:
            symlink.symlink_to(self.repo / "src", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(EvidenceRefusal):
            self.create("symlink-target", ids=[IDS[0]])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
