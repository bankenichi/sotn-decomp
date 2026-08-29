import json
import tempfile
import unittest
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_coordinator import (
    BudgetExhausted,
    CoordinatorError,
    ExplicitSubsetError,
    LANE_TIERS,
    SEARCH_PATTERN_REPORT_TOOL_IDENTITY,
    SearchCoordinator,
    TaskResult,
    TierBlocked,
    OracleRequired,
)
from automation.search_patterns import SearchPatternReport, load_report_artifact
from automation.search_types import (
    ArtifactRef,
    Budget,
    CandidateRecord,
    EvaluationEvent,
    GroupedPatch,
    Interruption,
    TaskTerminal,
    MutationEvent,
    PatchHunk,
    RunResume,
    ScoreDeltas,
    canonical_bytes,
    canonical_subset_identity,
    hash_canonical,
    hash_bytes,
)
from automation.test_search_schema import manifest, score


class CountingOracle:
    identity = hash_bytes(b"test-durable-oracle")

    def __init__(self, identity=None):
        if identity is not None:
            self.identity = identity
        self.results = {}
        self.requests = []
        self.execute_count = 0
        self.lookup_count = 0

    def lookup(self, request_id):
        self.lookup_count += 1
        return self.results.get(request_id)

    def execute(self, request):
        self.requests.append(request)
        self.execute_count += 1
        result = {
            "outcome": "matched",
            "result": {"request_id": request.request_id, "matched": True},
        }
        self.results[request.request_id] = result
        return result


class NonPersistingOracle:
    identity = hash_bytes(b"non-persisting-oracle")

    def __init__(self):
        self.execute_count = 0
        self.lookup_count = 0

    def lookup(self, request_id):
        self.lookup_count += 1
        return None

    def execute(self, request):
        self.execute_count += 1
        return {
            "outcome": "matched",
            "result": {"request_id": request.request_id, "matched": True},
        }


class InconsistentOracle(NonPersistingOracle):
    identity = hash_bytes(b"inconsistent-oracle")

    def __init__(self):
        super().__init__()
        self.results = {}

    def lookup(self, request_id):
        self.lookup_count += 1
        return self.results.get(request_id)

    def execute(self, request):
        returned = super().execute(request)
        self.results[request.request_id] = {
            "outcome": "matched",
            "result": {"request_id": request.request_id, "matched": False},
        }
        return returned


class TestSearchCoordinator(unittest.TestCase):
    @staticmethod
    def _manifest_for_oracle(oracle):
        base = manifest()
        return replace(
            base,
            tool_identities={
                **base.tool_identities,
                "full_oracle": oracle.identity,
            },
        )

    @staticmethod
    def _zero_result(coordinator, task):
        source = "int candidate(void) { return 0; }\n"
        source_hash = hash_bytes(source.encode("utf-8"))
        candidate = CandidateRecord(
            source_hash,
            "record-1",
            ArtifactRef(
                source_hash,
                "artifacts/sources/" + source_hash[7:] + ".c",
                "text/x-c",
                len(source),
            ),
            (),
            None,
            "upstream_current",
            0,
            None,
            "materialized",
        )
        after = score(0)
        evaluation = EvaluationEvent(
            task.task_id,
            "record-1",
            source_hash,
            None,
            None,
            after,
            ScoreDeltas(0, 0, 0, 0, 0, 0),
            coordinator.frontier.cache.key_for(
                "record-1",
                source_hash,
                after.compiler_identity,
            ),
            "zero_pending_oracle",
        )
        return TaskResult(
            task.task_id,
            candidate=candidate,
            source=source,
            evaluation=evaluation,
        )

    def test_manifest_budget_is_the_only_task_limit_and_compatibility_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            with self.assertRaises(CoordinatorError):
                SearchCoordinator(root, manifest(), budget_limit=63)
            self.assertFalse((root / "manifest.json").exists())

            coordinator = SearchCoordinator(root, manifest(), budget_limit=64)
            self.assertEqual(coordinator.budget_limit, 64)
            with self.assertRaises(AttributeError):
                coordinator.budget_limit = 65

            narrow = replace(
                manifest(),
                selected_lanes=("upstream_current",),
                lane_budgets={
                    "upstream_current": manifest().lane_budgets["upstream_current"],
                },
            )
            with tempfile.TemporaryDirectory() as narrow_directory:
                narrow_coordinator = SearchCoordinator(narrow_directory, narrow)
                with self.assertRaises(CoordinatorError):
                    narrow_coordinator.create_task(
                        recipient_id="record-1",
                        lane="model_fleet",
                        operation="unselected",
                    )

    def test_exhaustion_requires_exact_lane_tool_provenance_before_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            run_manifest = manifest()
            coordinator = SearchCoordinator(directory, run_manifest)
            with self.assertRaises(CoordinatorError):
                coordinator.record_exhaustion(
                    recipient_id="record-1",
                    lane="upstream_current",
                    tier="exact_deterministic",
                    input_identities=(run_manifest.source_identity,),
                )
            with self.assertRaises(CoordinatorError):
                coordinator.record_exhaustion(
                    recipient_id="record-1",
                    lane="upstream_current",
                    tier="exact_deterministic",
                    input_identities=(run_manifest.source_identity,),
                    tool_identities={"tool": run_manifest.tool_identities["tool"]},
                )
            receipts_root = Path(directory) / "artifacts" / "receipts"
            self.assertFalse(receipts_root.exists())

            tools = {
                "upstream_current": run_manifest.tool_identities["upstream_current"],
            }
            receipt = coordinator.record_exhaustion(
                recipient_id="record-1",
                lane="upstream_current",
                tier="exact_deterministic",
                input_identities=(run_manifest.source_identity,),
                tool_identities=tools,
            )
            replay = coordinator.record_exhaustion(
                recipient_id="record-1",
                lane="upstream_current",
                tier="exact_deterministic",
                input_identities=(run_manifest.source_identity,),
                tool_identities=tools,
            )
            self.assertEqual(receipt.receipt_id, replay.receipt_id)
            self.assertEqual(dict(receipt.tool_identities), tools)

    def test_global_task_budget_owns_each_ordinal_once(self):
        expanded = replace(
            manifest(),
            queue_record_ids=("record-1", "record-2"),
            function_ids=("record-1", "record-2"),
            subset_identity=canonical_subset_identity(("record-1", "record-2")),
            queue_evidence_identity=hash_bytes(b"two-record-evidence"),
            target_identities={
                "record-1": hash_bytes(b"target-one"),
                "record-2": hash_bytes(b"target-two"),
            },
            coordinator_budget=Budget("tasks", 2, 0),
        )
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, expanded)
            first = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="first",
                budget_ordinal=0,
            )
            coordinator.schedule_task(first)
            self.assertEqual(
                coordinator.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="first",
                    budget_ordinal=0,
                ),
                first,
            )
            with self.assertRaises(BudgetExhausted):
                coordinator.create_task(
                    recipient_id="record-1",
                    lane="upstream_pinned",
                    operation="different-lane",
                    budget_ordinal=0,
                )
            with self.assertRaises(BudgetExhausted):
                coordinator.create_task(
                    recipient_id="record-2",
                    lane="upstream_current",
                    operation="different-recipient",
                    budget_ordinal=0,
                )
            second = coordinator.create_task(
                recipient_id="record-2",
                lane="upstream_current",
                operation="second",
                budget_ordinal=1,
            )
            coordinator.schedule_task(second)
            with self.assertRaises(BudgetExhausted):
                coordinator.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="over-limit",
                    budget_ordinal=2,
                )
            self.assertEqual(
                coordinator.state_dict()["budget_claims"],
                [
                    {"ordinal": 0, "task_id": first.task_id},
                    {"ordinal": 1, "task_id": second.task_id},
                ],
            )

    def test_reopen_refuses_forged_task_lifecycle_prefixes(self):
        cases = (
            "started_before_scheduled",
            "duplicate_scheduled",
            "duplicate_started",
            "interrupted_before_started",
            "duplicate_terminal",
            "unknown_terminal",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                coordinator = SearchCoordinator(directory, manifest())
                task = coordinator.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="forged-lifecycle-" + case,
                )
                if case == "started_before_scheduled":
                    coordinator.ledger.append_event(
                        "task_started",
                        replace(task, state="started"),
                        event_id=task.task_id + ":forged-started",
                    )
                elif case == "duplicate_scheduled":
                    coordinator.schedule_task(task)
                    coordinator.ledger.append_event(
                        "task_scheduled",
                        task,
                        event_id=task.task_id + ":forged-scheduled",
                    )
                elif case == "duplicate_started":
                    coordinator.schedule_task(task)
                    coordinator.start_task(task.task_id)
                    coordinator.ledger.append_event(
                        "task_started",
                        replace(task, state="started"),
                        event_id=task.task_id + ":forged-started-again",
                    )
                elif case == "interrupted_before_started":
                    coordinator.schedule_task(task)
                    coordinator.ledger.append_event(
                        "task_interrupted",
                        Interruption(task.task_id, "forged interruption", True),
                        event_id=task.task_id + ":forged-interrupted",
                    )
                elif case == "duplicate_terminal":
                    coordinator.schedule_task(task)
                    coordinator.start_task(task.task_id)
                    terminal = TaskTerminal(task.task_id, "completed", (), "forged")
                    coordinator.ledger.append_event(
                        "task_completed",
                        terminal,
                        event_id=task.task_id + ":completed",
                    )
                    coordinator.ledger.append_event(
                        "task_completed",
                        terminal,
                        event_id=task.task_id + ":forged-completed-again",
                    )
                else:
                    coordinator.ledger.append_event(
                        "task_completed",
                        TaskTerminal(hash_bytes(b"unknown-terminal-task"), "completed", (), "forged"),
                        event_id="forged-terminal-event",
                    )

                with self.assertRaises(CoordinatorError):
                    SearchCoordinator(directory, manifest())

    def test_dispatch_never_reinvokes_a_terminal_task(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def worker(task):
                calls.append(task.task_id)
                return TaskResult(task.task_id)

            coordinator = SearchCoordinator(directory, manifest(), worker=worker)
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="terminal-dispatch",
            )
            coordinator.schedule_task(task)
            coordinator.commit_epoch((TaskResult(task.task_id),))

            self.assertEqual(coordinator.dispatch(), ())
            self.assertEqual(calls, [])

    def test_reopen_refuses_schema_valid_forged_task_id_or_seed(self):
        for field in ("task_id", "task_seed"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                coordinator = SearchCoordinator(directory, manifest())
                task = coordinator.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="forged-reopen-" + field,
                )
                coordinator.schedule_task(task)
                ledger_path = Path(directory) / "ledger.jsonl"
                lines = ledger_path.read_text(encoding="utf-8").splitlines()
                envelope = json.loads(lines[-1])
                forged_payload = dict(envelope["payload"])
                forged_payload[field] = (
                    hash_bytes(b"forged-reopen-task-id")
                    if field == "task_id"
                    else forged_payload["task_seed"] + 1
                )
                envelope["payload"] = forged_payload
                envelope.pop("event_hash", None)
                envelope["event_hash"] = hash_canonical(envelope)
                lines[-1] = json.dumps(
                    envelope,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

                with self.assertRaises(CoordinatorError):
                    SearchCoordinator(directory, manifest())

    def test_mutation_event_must_name_the_exact_active_task(self):
        from automation.search_recovery import RecoveryError, recover_run

        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            parent = hash_bytes(b"shared-active-parent")
            first = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="active-first",
                parent_candidate_ids=(parent,),
                budget_ordinal=0,
            )
            second = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="active-second",
                parent_candidate_ids=(parent,),
                budget_ordinal=1,
            )
            coordinator.schedule_task(first)
            coordinator.schedule_task(second)
            coordinator.start_task(first.task_id)
            coordinator.start_task(second.task_id)
            result = self._mutated_result(coordinator, first)
            coordinator.archive.put_patch(result.mutation.grouped_patch)
            coordinator.archive.put_source(result.source)
            coordinator.ledger.append_event(
                "mutation_materialized",
                result.mutation,
                event_id=f"{result.mutation.mutation_id}:materialized:{second.task_id}",
            )
            coordinator.ledger.append_event(
                "candidate_materialized",
                result.candidate,
                event_id=f"{result.candidate.candidate_id}:materialized:{first.task_id}",
            )

            with self.assertRaises(CoordinatorError):
                SearchCoordinator(directory, manifest())
            with self.assertRaises(RecoveryError):
                recover_run(directory)

    def test_stop_boundary_refuses_new_work_and_allows_only_resumable_pending_task(self):
        from automation.search_recovery import RecoveryError, recover_run

        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            pending = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="pending-after-stop",
            )
            coordinator.schedule_task(pending)
            coordinator.stop(reason="graceful_stop", resumable=True)
            resumed = SearchCoordinator(directory, manifest())
            self.assertEqual(resumed.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="pending-after-stop",
            ), pending)
            resumed.schedule_task(pending)
            with self.assertRaises(CoordinatorError):
                resumed.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="new-after-stop",
                    budget_ordinal=1,
                )
            resumed.commit_epoch([TaskResult(pending.task_id)])
            self.assertEqual(resumed.pending_task_ids(), ())

            with tempfile.TemporaryDirectory() as closed_directory:
                closed = SearchCoordinator(closed_directory, manifest())
                completed = closed.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="closed-run",
                )
                closed.schedule_task(completed)
                closed.commit_epoch([TaskResult(completed.task_id)])
                forged_after_stop = closed.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="forged-after-stop",
                    budget_ordinal=1,
                )
                closed.stop(reason="completed", resumable=False)
                with self.assertRaises(CoordinatorError):
                    closed.create_task(
                        recipient_id="record-1",
                        lane="upstream_current",
                        operation="after-closed",
                        budget_ordinal=1,
                    )
                with self.assertRaises(CoordinatorError):
                    closed.start_task(completed.task_id)
                closed.ledger.append_event(
                    "task_scheduled",
                    forged_after_stop,
                    event_id=forged_after_stop.task_id + ":forged-after-stop",
                )
                with self.assertRaises(CoordinatorError):
                    SearchCoordinator(closed_directory, manifest())
                with self.assertRaises(RecoveryError):
                    recover_run(closed_directory)

    def test_resume_is_ledger_bound_idempotent_and_reopens_future_boundaries(self):
        request_id = hash_bytes(b"resume-request")
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            pending = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="pending-before-resume",
                budget_ordinal=0,
            )
            coordinator.schedule_task(pending)
            stopped = coordinator.stop(reason="graceful_stop", resumable=True)
            self.assertEqual(stopped.payload.pending_task_ids, (pending.task_id,))

            resumed = coordinator.resume(request_id=request_id)
            retry = coordinator.resume(request_id=request_id)
            self.assertEqual(retry, resumed)
            self.assertIsNone(coordinator.stopped)
            self.assertEqual(
                sum(event.event_type == "run_stopped" for event in coordinator.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "run_resumed" for event in coordinator.events),
                1,
            )

            reopened = SearchCoordinator(directory, manifest())
            self.assertIsNone(reopened.stopped)
            future = reopened.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="future-after-resume",
                budget_ordinal=1,
            )
            reopened.schedule_task(future)
            reopened.commit_epoch(
                [TaskResult(pending.task_id), TaskResult(future.task_id)]
            )
            self.assertEqual(reopened.pending_task_ids(), ())

            with self.assertRaises(CoordinatorError):
                reopened.resume(request_id=request_id)

    def test_resume_prefix_rejects_malformed_order_and_duplicate_transition(self):
        from automation.search_recovery import RecoveryError, recover_run

        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            malformed = RunResume(
                "run-schema:stopped:0",
                hash_bytes(b"missing-stop"),
                None,
            )
            coordinator.ledger.append_event(
                "run_resumed",
                malformed,
                event_id="run-schema:resumed:0",
            )
            with self.assertRaises(CoordinatorError):
                SearchCoordinator(directory, manifest())
            with self.assertRaises(RecoveryError):
                recover_run(directory)

        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="duplicate-resume-boundary",
                budget_ordinal=0,
            )
            coordinator.schedule_task(task)
            stop = coordinator.stop(reason="graceful_stop", resumable=True)
            resume = coordinator.resume()
            coordinator.ledger.append_event(
                "run_resumed",
                resume.payload,
                event_id="run-schema:resumed:duplicate",
            )
            with self.assertRaises(CoordinatorError):
                SearchCoordinator(directory, manifest())

    def test_task_binding_rejects_forged_id_or_seed_before_state(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="binding",
            )
            forged_id = replace(task, task_id=hash_bytes(b"forged-task-id"))
            forged_seed = replace(task, task_seed=task.task_seed + 1)
            for forged in (forged_id, forged_seed):
                with self.assertRaises(CoordinatorError):
                    coordinator.schedule_task(forged)
            self.assertEqual(
                [event.event_type for event in coordinator.events],
                ["run_started"],
            )
            coordinator.schedule_task(task)
            self.assertEqual(coordinator.events[-1].event_type, "task_scheduled")

    @staticmethod
    def _mutated_result(coordinator, task):
        parent = task.parent_candidate_ids[0]
        source = "int candidate(void) { return 1; }\n"
        source_hash = hash_bytes(source.encode("utf-8"))
        mutation_id = hash_bytes(b"mutation-binding")
        hunk = PatchHunk(0, "return 0;\n", "return 1;\n", (), ())
        grouped_patch = GroupedPatch(
            hash_canonical({
                "format": "line_context",
                "base_source_hash": parent,
                "atomic": True,
                "hunks": [hunk],
            }),
            "line_context",
            parent,
            True,
            (hunk,),
        )
        mutation = MutationEvent(
            mutation_id,
            parent,
            task.recipient_id,
            task.lane,
            "binding-pass",
            1,
            grouped_patch,
            (),
            "applied",
            source_hash,
        )
        candidate = CandidateRecord(
            source_hash,
            task.recipient_id,
            ArtifactRef(
                source_hash,
                "artifacts/sources/" + source_hash[7:] + ".c",
                "text/x-c",
                len(source),
            ),
            (parent,),
            mutation_id,
            task.lane,
            1,
            None,
            "materialized",
        )
        return TaskResult(
            task.task_id,
            mutation=mutation,
            candidate=candidate,
            source=source,
        )

    def test_result_binding_rejects_forged_lane_and_ancestry_links(self):
        parent = hash_bytes(b"binding-parent")
        outside = hash_bytes(b"binding-outside")
        variants = (
            ("mutation-lane", lambda mutation, candidate: (replace(mutation, lane="upstream_pinned"), candidate)),
            ("mutation-recipient", lambda mutation, candidate: (replace(mutation, recipient_id="record-2"), candidate)),
            ("mutation-parent", lambda mutation, candidate: (replace(mutation, parent_candidate_id=outside), candidate)),
            ("mutation-donor", lambda mutation, candidate: (replace(mutation, donor_candidate_ids=(outside,)), candidate)),
            ("non-applied", lambda mutation, candidate: (replace(mutation, replay_status="conflict", result_source_hash=None), candidate)),
            ("candidate-mutation", lambda mutation, candidate: (mutation, replace(candidate, mutation_id=outside))),
            ("candidate-source", lambda mutation, candidate: (replace(mutation, result_source_hash=outside), candidate)),
            ("candidate-parent", lambda mutation, candidate: (mutation, replace(candidate, parent_candidate_ids=()))),
            ("candidate-lane", lambda mutation, candidate: (mutation, replace(candidate, lane="upstream_pinned"))),
            ("missing-mutation", lambda mutation, candidate: (None, candidate)),
            ("unbound-candidate-parent", lambda mutation, candidate: (None, replace(candidate, mutation_id=None, parent_candidate_ids=(outside,)))),
        )
        for name, forge in variants:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                coordinator = SearchCoordinator(directory, manifest())
                task = coordinator.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="binding-" + name,
                    parent_candidate_ids=(parent,),
                )
                coordinator.schedule_task(task)
                valid = self._mutated_result(coordinator, task)
                mutation, candidate = forge(valid.mutation, valid.candidate)
                forged = replace(valid, mutation=mutation, candidate=candidate)
                with self.assertRaises(CoordinatorError):
                    coordinator.commit_epoch([forged])
                self.assertEqual(
                    [event.event_type for event in coordinator.events],
                    ["run_started", "task_scheduled"],
                )

    def test_explicit_subset_and_deterministic_task_identity(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a = SearchCoordinator(first, manifest())
            b = SearchCoordinator(second, manifest())
            task_a = a.create_task(recipient_id="record-1", lane="upstream_current", operation="discover")
            task_b = b.create_task(recipient_id="record-1", lane="upstream_current", operation="discover")
            self.assertEqual(task_a, task_b)
            a.schedule_task(task_a)
            a.commit_epoch([TaskResult(task_a.task_id, reason="done")])
            with self.assertRaises(ExplicitSubsetError):
                a.create_task(recipient_id="other-record", lane="upstream_current", operation="discover")

    def test_tier_completion_is_a_hard_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            with self.assertRaises(TierBlocked):
                coordinator.create_task(recipient_id="record-1", lane="permuter_random", operation="random")
            with self.assertRaises(Exception):
                coordinator.complete_tier("record-1", "exact_deterministic")
            for lane in (
                "upstream_current", "upstream_pinned", "upstream_open_pr",
                "mipsmatch_exact", "preserved_candidate",
            ):
                receipt = coordinator.complete_tier("record-1", "exact_deterministic", lane=lane)
                self.assertEqual(set(receipt.tool_identities), {lane})
            task = coordinator.create_task(recipient_id="record-1", lane="shared_header", operation="headers")
            self.assertEqual(task.tier, "structural_dependency")

    def test_epoch_size_limits_commits_and_leaves_later_results_buffered(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, replace(manifest(), epoch_size=1))
            tasks = coordinator.schedule_tasks(
                coordinator.create_task(
                    recipient_id="record-1", lane="upstream_current", operation="discover-" + str(index),
                    budget_ordinal=index,
                )
                for index in (0, 1)
            )
            first = coordinator.commit_epoch(tuple(TaskResult(task.task_id) for task in tasks))
            self.assertEqual(sum(event.event_type == "task_completed" for event in first), 1)
            self.assertEqual(len(coordinator._buffered), 1)
            second = coordinator.commit_epoch()
            self.assertEqual(sum(event.event_type == "task_completed" for event in second), 1)

    def test_within_tier_schedule_uses_lane_yield_then_stable_ties(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            for lane in (
                "upstream_current", "upstream_pinned", "upstream_open_pr",
                "mipsmatch_exact", "preserved_candidate",
            ):
                coordinator.complete_tier("record-1", "exact_deterministic", lane=lane)
            coordinator.set_lane_yield("record-1", "shared_header", accepted=1, attempts=10)
            coordinator.set_lane_yield("record-1", "transplant", accepted=2, attempts=2)
            tasks = (
                coordinator.create_task(recipient_id="record-1", lane="shared_header", operation="headers", budget_ordinal=0),
                coordinator.create_task(recipient_id="record-1", lane="transplant", operation="transplant", budget_ordinal=1),
            )
            ordered = coordinator.schedule_tasks(tasks)
            self.assertEqual([task.lane for task in ordered], ["transplant", "shared_header"])

    def test_evaluation_compiler_identity_must_match_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            task = coordinator.create_task(recipient_id="record-1", lane="upstream_current", operation="discover")
            coordinator.schedule_task(task)
            source = "int candidate(void) { return 1; }\n"
            source_hash = hash_bytes(source.encode("utf-8"))
            candidate = CandidateRecord(
                source_hash, "record-1",
                ArtifactRef(source_hash, "artifacts/sources/" + source_hash[7:] + ".c", "text/x-c", len(source)),
                (), None, "upstream_current", 0, None, "materialized",
            )
            after = replace(score(3), compiler_identity=hash_bytes(b"other"))
            evaluation = EvaluationEvent(
                task.task_id, "record-1", source_hash, None, None, after,
                ScoreDeltas(3, 0, 0, 0, 0, 3),
                coordinator.frontier.cache.key_for("record-1", source_hash, after.compiler_identity),
                "scalar_elite",
            )
            with self.assertRaises(Exception):
                coordinator.commit_epoch([TaskResult(task.task_id, candidate=candidate, source=source, evaluation=evaluation)])

    def test_score_zero_is_durable_pending_oracle_state(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            task = coordinator.create_task(recipient_id="record-1", lane="upstream_current", operation="discover")
            coordinator.schedule_task(task)
            source = "int candidate(void) { return 0; }\n"
            source_hash = hash_bytes(source.encode("utf-8"))
            candidate = CandidateRecord(
                source_hash, "record-1",
                ArtifactRef(source_hash, "artifacts/sources/" + source_hash[7:] + ".c", "text/x-c", len(source)),
                (), None, "upstream_current", 0, None, "materialized",
            )
            after = score(0)
            evaluation = EvaluationEvent(
                task.task_id, "record-1", source_hash, None, None, after,
                ScoreDeltas(0, 0, 0, 0, 0, 0),
                coordinator.frontier.cache.key_for("record-1", source_hash, after.compiler_identity),
                "zero_pending_oracle",
            )
            with self.assertRaises(OracleRequired):
                coordinator.commit_epoch([
                    TaskResult(
                        task.task_id,
                        candidate=candidate,
                        source=source,
                        evaluation=evaluation,
                    )
                ])
            self.assertEqual(coordinator.pending_oracle_candidate_ids, (source_hash,))
            self.assertEqual(coordinator.pending_task_ids(), (task.task_id,))
            self.assertEqual(
                [event.event_type for event in coordinator.events],
                [
                    "run_started", "task_scheduled", "task_started",
                    "candidate_materialized", "evaluation_completed", "archive_decided",
                ],
            )
            recovered = __import__("automation.search_recovery", fromlist=["recover_run"]).recover_run(directory)
            self.assertEqual(recovered.pending_oracle_candidate_ids, (source_hash,))
            self.assertEqual([item.task_id for item in recovered.reissue_tasks()], [task.task_id])

    def test_zero_result_requires_then_calls_durable_oracle_without_source_landing(self):
        source = "int candidate(void) { return 0; }\n"
        source_hash = hash_bytes(source.encode("utf-8"))
        candidate = CandidateRecord(
            source_hash,
            "record-1",
            ArtifactRef(
                source_hash,
                "artifacts/sources/" + source_hash[7:] + ".c",
                "text/x-c",
                len(source),
            ),
            (),
            None,
            "upstream_current",
            0,
            None,
            "materialized",
        )
        with tempfile.TemporaryDirectory() as directory:
            oracle = CountingOracle()
            run_manifest = self._manifest_for_oracle(oracle)
            coordinator = SearchCoordinator(directory, run_manifest)
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="discover",
            )
            coordinator.schedule_task(task)
            after = score(0)
            evaluation = EvaluationEvent(
                task.task_id,
                "record-1",
                source_hash,
                None,
                None,
                after,
                ScoreDeltas(0, 0, 0, 0, 0, 0),
                coordinator.frontier.cache.key_for(
                    "record-1", source_hash, after.compiler_identity
                ),
                "zero_pending_oracle",
            )
            result = TaskResult(
                task.task_id,
                candidate=candidate,
                source=source,
                evaluation=evaluation,
            )

            with self.assertRaises(OracleRequired):
                coordinator.commit_epoch([result])

            from automation.search_recovery import recover_run

            interrupted = recover_run(directory)
            self.assertEqual(interrupted.pending_oracle_candidate_ids, (source_hash,))
            self.assertEqual([item.task_id for item in interrupted.reissue_tasks()], [task.task_id])
            self.assertEqual(interrupted.consumed_budget_ordinals, ())
            before_counts = {
                kind: sum(event.event_type == kind for event in interrupted.events)
                for kind in (
                    "candidate_materialized",
                    "evaluation_completed",
                    "archive_decided",
                )
            }

            resumed = SearchCoordinator(directory, run_manifest, oracle=oracle)
            resumed.commit_epoch([result])
            completed = recover_run(directory)
            self.assertEqual(oracle.execute_count, 1)
            self.assertEqual(oracle.lookup_count, 2)
            self.assertEqual(len(oracle.requests), 1)
            self.assertEqual(oracle.requests[0].candidate_id, source_hash)
            self.assertEqual(oracle.requests[0].source_hash, source_hash)
            self.assertEqual(oracle.requests[0].candidate.candidate_id, source_hash)
            self.assertEqual(oracle.requests[0].candidate.status, "zero_pending_oracle")
            self.assertEqual(completed.pending_oracle_candidate_ids, ())
            self.assertEqual(completed.completed_task_ids, (task.task_id,))
            self.assertEqual(
                completed.consumed_budget_ordinals,
                (("record-1", "upstream_current", 0),),
            )
            self.assertEqual(len(completed.oracle_requests), 1)
            self.assertEqual(len(completed.oracle_results), 1)
            self.assertEqual(
                sum(event.event_type == "oracle_requested" for event in completed.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "oracle_result_recorded" for event in completed.events),
                1,
            )
            self.assertFalse(Path(directory, "src").exists())
            for kind, count in before_counts.items():
                self.assertEqual(
                    sum(event.event_type == kind for event in completed.events),
                    count,
                )

    def test_non_persisting_durable_oracle_fails_closed_before_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            oracle = NonPersistingOracle()
            coordinator = SearchCoordinator(
                directory,
                self._manifest_for_oracle(oracle),
                oracle=oracle,
            )
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="discover",
            )
            coordinator.schedule_task(task)
            result = self._zero_result(coordinator, task)

            with self.assertRaisesRegex(CoordinatorError, "did not persist"):
                coordinator.commit_epoch([result])

            state = __import__("automation.search_recovery", fromlist=["recover_run"]).recover_run(directory)
            self.assertEqual(state.pending_oracle_candidate_ids, (result.candidate.candidate_id,))
            self.assertEqual(state.completed_task_ids, ())
            self.assertEqual(oracle.execute_count, 1)
            self.assertEqual(oracle.lookup_count, 2)
            self.assertEqual(
                sum(event.event_type == "oracle_requested" for event in state.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "oracle_result_recorded" for event in state.events),
                0,
            )
            self.assertEqual(
                sum(event.event_type == "task_completed" for event in state.events),
                0,
            )

    def test_inconsistent_durable_oracle_fails_closed_before_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            oracle = InconsistentOracle()
            coordinator = SearchCoordinator(
                directory,
                self._manifest_for_oracle(oracle),
                oracle=oracle,
            )
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="discover",
            )
            coordinator.schedule_task(task)
            result = self._zero_result(coordinator, task)

            with self.assertRaisesRegex(CoordinatorError, "read-after-write"):
                coordinator.commit_epoch([result])

            state = __import__("automation.search_recovery", fromlist=["recover_run"]).recover_run(directory)
            self.assertEqual(state.pending_oracle_candidate_ids, (result.candidate.candidate_id,))
            self.assertEqual(state.completed_task_ids, ())
            self.assertEqual(oracle.execute_count, 1)
            self.assertEqual(oracle.lookup_count, 2)
            self.assertEqual(
                sum(event.event_type == "oracle_requested" for event in state.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "oracle_result_recorded" for event in state.events),
                0,
            )
            self.assertEqual(
                sum(event.event_type == "task_completed" for event in state.events),
                0,
            )

    def test_durable_oracle_requires_manifest_identity_before_fresh_state(self):
        with tempfile.TemporaryDirectory() as parent:
            run_root = Path(parent) / "run"
            oracle = CountingOracle()

            with self.assertRaisesRegex(CoordinatorError, "full_oracle"):
                SearchCoordinator(run_root, manifest(), oracle=oracle)

            self.assertFalse(run_root.exists())

            mismatched_manifest = replace(
                manifest(),
                tool_identities={
                    **manifest().tool_identities,
                    "full_oracle": hash_bytes(b"other-oracle"),
                },
            )
            with self.assertRaisesRegex(CoordinatorError, "full_oracle"):
                SearchCoordinator(run_root, mismatched_manifest, oracle=oracle)

            self.assertFalse(run_root.exists())
            SearchCoordinator(
                run_root,
                self._manifest_for_oracle(oracle),
                oracle=oracle,
            )
            self.assertTrue((run_root / "manifest.json").is_file())

    def test_durable_oracle_mismatch_refuses_resume_before_first_request(self):
        with tempfile.TemporaryDirectory() as directory:
            original = CountingOracle()
            run_manifest = self._manifest_for_oracle(original)
            SearchCoordinator(directory, run_manifest, oracle=original)
            manifest_bytes = (Path(directory) / "manifest.json").read_bytes()
            ledger_bytes = (Path(directory) / "ledger.jsonl").read_bytes()

            changed = CountingOracle(identity=hash_bytes(b"changed-oracle"))
            with self.assertRaisesRegex(CoordinatorError, "full_oracle"):
                SearchCoordinator(directory, run_manifest, oracle=changed)

            self.assertEqual(changed.lookup_count, 0)
            self.assertEqual(changed.execute_count, 0)
            self.assertEqual((Path(directory) / "manifest.json").read_bytes(), manifest_bytes)
            self.assertEqual((Path(directory) / "ledger.jsonl").read_bytes(), ledger_bytes)
            self.assertEqual(
                sum(event.event_type == "oracle_requested" for event in SearchCoordinator(
                    directory,
                    run_manifest,
                    oracle=original,
                ).events),
                0,
            )

    def test_durable_oracle_same_identity_resumes_before_first_request(self):
        with tempfile.TemporaryDirectory() as directory:
            original = CountingOracle()
            run_manifest = self._manifest_for_oracle(original)
            SearchCoordinator(directory, run_manifest, oracle=original)

            replacement = CountingOracle(identity=original.identity)
            resumed = SearchCoordinator(directory, run_manifest, oracle=replacement)

            self.assertEqual(replacement.lookup_count, 0)
            self.assertEqual(replacement.execute_count, 0)
            self.assertEqual(
                [event.event_type for event in resumed.events],
                ["run_started"],
            )

    def test_legacy_oracle_callback_fails_closed_without_explicit_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CoordinatorError):
                SearchCoordinator(directory, manifest(), oracle=lambda item: item)

    def test_prior_pattern_report_requires_manifest_binding_and_is_read_only(self):
        payload = {
            "report_version": "1.0.0",
            "source_ledgers": [hash_bytes(b"completed-ledger")],
            "recommendations": [],
        }
        report_id = hash_canonical(payload)
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            report_root = parent / "report-archive"
            artifact = __import__("automation.search_archive", fromlist=["ContentAddressedArchive"]).ContentAddressedArchive(report_root).put_bytes(
                canonical_bytes(payload),
                category="pattern_reports",
                suffix=".json",
                media_type="application/json",
            )
            self.assertEqual(artifact.content_hash, report_id)
            report = load_report_artifact(artifact, artifact_root=report_root)
            self.assertIsInstance(report, SearchPatternReport)

            base = manifest()
            bound = replace(
                base,
                run_id="run-bound-pattern",
                tool_identities={
                    **base.tool_identities,
                    SEARCH_PATTERN_REPORT_TOOL_IDENTITY: report.artifact.content_hash,
                },
            )
            run_a = parent / "run-a"
            coordinator_a = SearchCoordinator(run_a, base)
            task_a = coordinator_a.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="before-report",
            )
            manifest_a = (run_a / "manifest.json").read_bytes()
            ledger_a = (run_a / "ledger.jsonl").read_bytes()

            run_b = parent / "run-b"
            coordinator_b = SearchCoordinator(
                run_b,
                bound,
                recommendation_report=report,
                recommendation_artifact_root=report_root,
            )
            task_b = coordinator_b.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="before-report",
            )
            self.assertTrue(coordinator_b.recommendation_report)
            self.assertEqual((run_a / "manifest.json").read_bytes(), manifest_a)
            self.assertEqual((run_a / "ledger.jsonl").read_bytes(), ledger_a)
            self.assertNotIn(task_a.task_id, coordinator_b._tasks)

            changed = replace(
                bound,
                tool_identities={
                    **bound.tool_identities,
                    SEARCH_PATTERN_REPORT_TOOL_IDENTITY: hash_bytes(b"changed-report"),
                },
            )
            with self.assertRaisesRegex(CoordinatorError, "recommendation report"):
                SearchCoordinator(
                    parent / "changed",
                    changed,
                    recommendation_report=report,
                    recommendation_artifact_root=report_root,
                )
            self.assertFalse((parent / "changed").exists())

            # A second reader with the same immutable binding produces the same
            # task identity.  The report is evidence, not an active scheduler
            # policy.
            coordinator_c = SearchCoordinator(
                parent / "run-c",
                bound,
                recommendation_report=report,
                recommendation_artifact_root=report_root,
            )
            self.assertEqual(
                task_b,
                coordinator_c.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="before-report",
                ),
            )

            # The new run owns an exact copy of the validated report.  Resume
            # must use that copy, even after the external source archive is
            # removed.
            report_path = report_root / report.artifact.path
            report_path.unlink()
            resumed = SearchCoordinator(parent / "run-b", bound)
            self.assertEqual(resumed.recommendation_report.report_id, report.report_id)
            self.assertEqual(resumed.recommendation_report.payload(), report.payload())

            with self.assertRaisesRegex(CoordinatorError, "recommendation report"):
                SearchCoordinator(
                    parent / "missing",
                    bound,
                    recommendation_report=report.artifact,
                    recommendation_artifact_root=report_root,
                )
            self.assertFalse((parent / "missing").exists())


if __name__ == "__main__":
    unittest.main()
