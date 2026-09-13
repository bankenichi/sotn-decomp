"""Focused tests for the bounded production search-run creator."""

from __future__ import annotations

import json
import os
import shutil
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
    def test_foreign_targets_are_refused_before_queue_or_archive_access(self):
        for version in ("hd", "pspeu", "saturn"):
            record_id = f"{version}:ST/RNO0:func_a"
            with self.assertRaisesRegex(InputRefusal, "targets must be US"):
                create_instrumented_run("foreign-target", [record_id], ["upstream_current"],
                    repo=self.repo, queue_reader=lambda: self.fail("queue read"))
            with self.assertRaisesRegex(cc.Rejected, "targets must be US"):
                cc.build_argv("search_create_instrumented", name="foreign-target",
                              record_ids=[record_id], lanes=["upstream_current"])
        self.assertFalse((self.repo / "nonmatchings").exists())

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
            "search_frontier.py",
            "search_types.py",
            "search_archive.py",
            "search_recovery.py",
            "search_evaluator.py",
            "compiler_corpus.py",
            "search_source_context.py",
            "upstream_harvest.py",
            "shim_sweep.py",
            "asm_twin_finder.py",
            "transplant.py",
        ):
            (self.repo / "automation" / module).write_text(
                f"{module.replace('.', '_')} = 1\n", encoding="utf-8"
            )
        vendor = self.repo / "tools" / "decomp-permuter" / "src"
        vendor.mkdir(parents=True)
        for module in ("scorer.py", "objdump.py"):
            (vendor / module).write_text("IMPLEMENTATION = 1\n", encoding="utf-8")
        actual_repo = Path(__file__).resolve().parents[1]
        for paths in _factory._LANE_MODULES.values():
            for relative in paths:
                path = self.repo / relative
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes((actual_repo / relative).read_bytes())
        shutil.copytree(actual_repo / "tools/decomp-permuter", vendor.parent,
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".git", ".mypy_cache", ".pytest_cache"))
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
            (asm / f"{function}.s").write_text(f"{function}:\n\tli $v0, 7\n\tjr $ra\n\tnop\n", encoding="utf-8")
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

    def test_transplant_binds_ninja_authority_and_source_freshness(self) -> None:
        database = self.repo / ".ninja_deps"
        graph = self.repo / "build.ninja"
        database.write_bytes(b"dependency generation one")
        graph.write_text("rule compile\n  command = cc\n", encoding="utf-8")
        original = _factory._lane_input_state(self.repo, "transplant")
        by_path = {entry["path"]: entry for entry in original["files"]}
        self.assertEqual(by_path[".ninja_deps"]["content_hash"], hash_bytes(database.read_bytes()))
        self.assertEqual(by_path["build.ninja"]["content_hash"], hash_bytes(graph.read_bytes()))
        self.assertFalse(any(path.endswith(".d") for path in by_path))
        database.write_bytes(b"dependency generation two")
        changed = _factory._lane_input_state(self.repo, "transplant")
        self.assertNotEqual(original, changed)
        source = self.repo / "include/header.h"
        source_time = source.stat().st_mtime_ns
        os.utime(source, ns=(source_time, source_time + 1_000_000_000))
        self.assertNotEqual(changed, _factory._lane_input_state(self.repo, "transplant"))

    def test_source_walk_refuses_nested_file_and_directory_links(self) -> None:
        root = self.repo / "src"
        for target, directory in ((self.repo / "include/header.h", False),
                                  (self.repo / "include", True)):
            link = root / "evidence-link"
            try:
                link.symlink_to(target, target_is_directory=directory)
            except OSError:
                self.skipTest("symlink creation is unavailable")
            try:
                with self.assertRaises(EvidenceRefusal):
                    _factory._walk_regular_files(root, self.repo, "source")
            finally:
                link.unlink()

    def create(
        self,
        name: str,
        ids=IDS,
        lanes=None,
        *,
        queue_reader=None,
        compiler_identity_resolver=None,
        runtime_id=None,
        land_matches=False,
        weight_tuning_run=None,
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
            runtime_id=runtime_id,
            land_matches=land_matches,
            weight_tuning_run=weight_tuning_run,
            now=now or (lambda: "2026-08-28T00:00:00Z"),
            fault_hook=fault_hook,
        )

    def test_target_context_is_archived_used_and_verified_without_live_source(self):
        from automation.search_archive import ContentAddressedArchive
        from automation.search_target_renderer import load_target_index, TargetEvidenceError
        from automation.search_source_context import target_declaration
        from automation.search_provider_factory import prepare_provider_inputs
        source = self.repo / "src/st/rno0/unit_a.c"
        source.parent.mkdir(parents=True)
        source.write_text('#include "header.h"\nint func_a(int value);\n')
        context = b"int func_a(int value);\n"
        asm = self.repo / "asm/us/st/rno0/nonmatchings/unit_a/func_a.s"
        asm.write_text("func_a:\naddiu $v0, $a0, 1\njr $ra\nnop\n")
        with mock.patch("automation.search_source_context.preprocess_target_context", return_value=context) as cpp:
            result = self.create("target-context", ids=[IDS[0]], lanes=["bounded_synthesis"])
        cpp.assert_called_once()
        root = Path(result["run_root"])
        archive = ContentAddressedArchive(root)
        index = json.loads((root / result["evidence_index"]["path"]).read_text())
        target = json.loads(archive.verify(ArtifactRef.from_dict(index["target_evidence"][IDS[0]])))
        declarations = target["declarations"]
        self.assertEqual(declarations["parameters"], [{"type": "int", "name": "value"}])
        self.assertEqual(declarations["context_evidence"]["status"], "declared")
        prepared = prepare_provider_inputs(self.repo, ["bounded_synthesis"],
            {IDS[0]: (asm.read_bytes(), b"object")}, {}, target_declarations={IDS[0]: declarations})
        self.assertIn("int value", prepared[IDS[0]]["seed"])
        self.assertTrue(prepared[IDS[0]]["expressions"])
        provider = json.loads(archive.verify(ArtifactRef.from_dict(index["provider_state"])))
        self.assertIn('"name": "value"', json.dumps(provider))
        manifest = RunManifest.from_dict(result["manifest"])
        with mock.patch.object(_factory, "_compiler_identity", return_value=(manifest.compiler_identity, {"identity": manifest.compiler_identity})):
            _factory.verify_factory_runtime(root, manifest, repo=self.repo)
            source.write_text("int func_a(unsigned int changed);\n")
            with self.assertRaisesRegex(EvidenceRefusal, "source"):
                _factory.verify_factory_runtime(root, manifest, repo=self.repo)
        source.unlink()
        with mock.patch("automation.search_source_context.preprocess_target_context", side_effect=AssertionError("live preprocessing")):
            load_target_index(archive=archive, manifest=manifest)
            from automation.search_provider_lanes import reconstruct_lane_adapters
            from automation.search_lanes import Recipient
            callback = reconstruct_lane_adapters(manifest, root).bounded_synthesis
            replay = callback(Recipient(IDS[0], "ST/RNO0", "func_a"))
            self.assertTrue(replay["candidates"])
            self.assertTrue(all("int value" in item.source for item in replay["candidates"]))
            self.assertTrue(self.create("target-context", ids=[IDS[0]], lanes=["bounded_synthesis"])["idempotent"])
        for key in ("input", "preprocessed"):
            path = root / declarations["context_evidence"][key]["path"]
            original = path.read_bytes()
            path.write_bytes(b"corrupt")
            with self.assertRaises(TargetEvidenceError):
                load_target_index(archive=archive, manifest=manifest)
            with self.assertRaises(PartialRunRefusal):
                self.create("target-context", ids=[IDS[0]], lanes=["bounded_synthesis"])
            path.write_bytes(original)

    def test_call_seed_and_index_projection_reconstruct_from_us_archive(self):
        from automation.search_archive import ContentAddressedArchive
        from automation.search_provider_lanes import reconstruct_lane_adapters
        from automation.search_target_renderer import load_target_index, deterministic_local_draft, TargetEvidenceError
        from automation.search_lanes import Recipient
        source = self.repo / "src/st/rno0/unit_a.c"
        source.parent.mkdir(parents=True)
        context = b"int func_a(int value);\nint callee(int value);\n"
        source.write_bytes(context)
        assembly = b"addiu $sp, $sp, -24\nsw $ra, 20($sp)\njal callee\naddiu $a0, $a0, 1\nlw $ra, 20($sp)\nnop\njr $ra\naddiu $sp, $sp, 24\n"
        (self.repo / "asm/us/st/rno0/nonmatchings/unit_a/func_a.s").write_bytes(assembly)
        with mock.patch("automation.search_source_context.preprocess_target_context", return_value=context):
            result = self.create("call-context", ids=[IDS[0]], lanes=["permuter_targeted", "bounded_synthesis"])
        root = Path(result["run_root"])
        archive = ContentAddressedArchive(root)
        manifest = RunManifest.from_dict(result["manifest"])
        source.unlink()
        with mock.patch("automation.search_source_context.preprocess_target_context", side_effect=AssertionError("live preprocessing")):
            target = load_target_index(archive, manifest).records[0]
            draft = deterministic_local_draft(assembly, symbol="func_a", declarations=target.declarations)
            self.assertIn("extern int callee(int);", draft)
            adapters = reconstruct_lane_adapters(manifest, root)
            provider = adapters.permuter_targeted.__self__
            item = provider._input_for(Recipient(IDS[0], "ST/RNO0", "func_a"))
            self.assertEqual(item.seed_source, draft)
            # Calls cannot be stripped into branch-local/side-effect-free expressions.
            synthesis = adapters.bounded_synthesis(Recipient(IDS[0], "ST/RNO0", "func_a"))
            self.assertFalse(synthesis["candidates"])
            self.assertTrue(self.create("call-context", ids=[IDS[0]], lanes=["permuter_targeted", "bounded_synthesis"])["idempotent"])
        path = root / target.declarations["context_evidence"]["preprocessed"]["path"]
        path.write_bytes(b"int callee(void);")
        with self.assertRaises(TargetEvidenceError):
            load_target_index(archive, manifest)
        with self.assertRaises(PartialRunRefusal):
            self.create("call-context", ids=[IDS[0]], lanes=["permuter_targeted", "bounded_synthesis"])

    def test_target_context_capture_rejects_source_race(self):
        source = self.repo / "src/st/rno0/unit_a.c"
        source.parent.mkdir(parents=True)
        source.write_text("int func_a(int x);\n")
        original = _factory._source_identity
        def race(repo):
            result = original(repo)
            source.write_text("int func_a(unsigned int y);\n")
            return result
        with mock.patch.object(_factory, "_source_identity", side_effect=race), mock.patch(
                "automation.search_source_context.preprocess_target_context", return_value=b"int func_a(unsigned int y);"):
            with self.assertRaisesRegex(EvidenceRefusal, "frozen source"):
                self.create("context-race", ids=[IDS[0]])
        self.assertFalse(list((self.repo / "nonmatchings").rglob("manifest.json")))
        self.assertFalse(list((self.repo / "nonmatchings").rglob("target-context/*.c")))

    def test_target_context_capture_rejects_header_race(self):
        source = self.repo / "src/st/rno0/unit_a.c"
        source.parent.mkdir(parents=True)
        source.write_text('#include "header.h"\nint func_a(int x);\n')
        def race(*args):
            (self.repo / "include/header.h").write_text("#define X 2\n")
            return b"int func_a(int x);"
        with mock.patch("automation.search_source_context.preprocess_target_context", side_effect=race):
            with self.assertRaisesRegex(EvidenceRefusal, "headers changed"):
                self.create("header-race", ids=[IDS[0]])
        self.assertFalse(list((self.repo / "nonmatchings").rglob("manifest.json")))

    def test_target_declaration_refuses_guesses_and_prefers_definition_names(self):
        from automation.search_source_context import target_declaration
        cases = [
            ("int f(void);", "declared"),
            ("int f(unsigned int);", "unsupported_declaration"),
            ("int f();", "unsupported_declaration"),
            ("typedef int f(int x);", "unsupported_declaration"),
            ("int f(int x);\nint f(unsigned int x);", "ambiguous_declaration"),
            ("int f(int x); int f(unsigned int x);", "ambiguous_declaration"),
            ("void outer(void) {\nint f(int local);\n}", "declaration_missing"),
            ("int f(Entity *self);", "declared"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(target_declaration(text, "f")[1], expected)
        facts, status = target_declaration("extern int f(int old);\nint f(int current) { return current; }", "f")
        self.assertEqual(facts["parameters"][0]["name"], "current")

    def test_verified_weights_are_frozen_and_read_by_runtime(self):
        from automation.weight_tuner import PROTOCOL, weights_for_run
        from automation.search_archive import ContentAddressedArchive
        from automation.compiler_corpus import DEFAULT_WEIGHTS
        baseline = self.create("weight-baseline")
        original = RunManifest.from_dict(baseline["manifest"])
        (self.repo / "automation/weight_tuner.py").write_bytes(
            (Path(__file__).parent / "weight_tuner.py").read_bytes())
        weights = {key: value * 2 for key, value in DEFAULT_WEIGHTS.items()}
        document = {"protocol": PROTOCOL, "dataset_id": hash_bytes(b"corpus"),
                    "selected_trial_id": hash_bytes(b"trial"), "weights": weights,
                    "compiler_identity": original.compiler_identity,
                    "config_identity": original.config_identity}
        with mock.patch("automation.weight_tuner.load_weights", return_value=document) as load:
            created = self.create("weighted", weight_tuning_run="qualified")
            load.assert_called_once_with(self.repo, "qualified")
        manifest = RunManifest.from_dict(created["manifest"])
        archive = ContentAddressedArchive(created["run_root"])
        self.assertEqual(weights_for_run(manifest, archive), weights)
        _factory.verify_factory_archive(created["run_root"], manifest)
        self.assertTrue(self.create("weighted", weight_tuning_run="qualified")["idempotent"])
        with self.assertRaises(RunNameCollision):
            self.create("weighted")
        self.assertEqual(weights_for_run(original, ContentAddressedArchive(baseline["run_root"])), DEFAULT_WEIGHTS)

    def test_automatic_landing_is_immutable_and_explicit(self):
        from automation.search_full_oracle import TOOL_FILES, capture_binding
        from automation.search_types import hash_canonical
        for relative in TOOL_FILES:
            path = self.repo / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("landing tool\n")
        (self.repo / "config").mkdir()
        (self.repo / "config/check.us.sha").write_text("checksum authority\n")
        (self.repo / "tools/builds").mkdir()
        (self.repo / "tools/builds/gen.py").write_text("build rules\n")
        result = self.create("auto-land", land_matches=True)
        value = RunManifest.from_dict(result["manifest"])
        self.assertEqual(value.tool_identities["full_oracle"], hash_canonical(capture_binding(self.repo)))
        _factory.verify_factory_archive(result["run_root"], value)
        self.assertTrue(self.create("auto-land", land_matches=True)["idempotent"])
        with self.assertRaisesRegex(RunNameCollision, "landing policy"):
            self.create("auto-land")
        argv = cc._search_create_argv("auto-land", IDS, [LANES[0]], land_matches=True)
        self.assertIn("--land-matches", argv)
        with self.assertRaises(cc.Rejected):
            cc._search_create_argv("auto-land", IDS, [LANES[0]], land_matches="yes")
        self.assertEqual(self.records, self.before_records)

    def test_indexed_runtime_is_required_only_for_indexed_lanes(self) -> None:
        runtime_id = hash_bytes(b"runtime")
        with self.assertRaisesRegex(InputRefusal, "require one explicit"):
            self.create("indexed-missing", lanes=["multi_donor"])
        with self.assertRaisesRegex(InputRefusal, "irrelevant"):
            self.create(
                "runtime-irrelevant",
                lanes=["upstream_current"],
                runtime_id=runtime_id,
            )
        with self.assertRaisesRegex(InputRefusal, "invalid"):
            self.create(
                "runtime-invalid",
                lanes=["cfg_dataflow"],
                runtime_id="latest",
            )

    def test_indexed_runtime_cli_commands_have_typed_parser_and_dispatch(self) -> None:
        pairs = [
            "us=" + "a" * 40,
            "hd=" + "b" * 40,
            "pspeu=" + "c" * 40,
            "saturn=" + "d" * 40,
        ]
        parser = search_cli.build_parser()

        parsed_publish = parser.parse_args(
            [
                "publish-indexed-runtime",
                "--gate-run-id",
                "gate-run",
                "--revisions",
                *reversed(pairs),
            ]
        )
        with mock.patch.object(
            search_cli,
            "publish_indexed_runtime",
            return_value={"ok": True, "command": "publish-indexed-runtime"},
        ) as publish:
            self.assertEqual(search_cli._dispatch(parsed_publish), {
                "ok": True,
                "command": "publish-indexed-runtime",
            })
        publish.assert_called_once_with("gate-run", [list(reversed(pairs))])

        parsed_verify = parser.parse_args(
            [
                "verify-indexed-runtime",
                "--runtime-id",
                "sha256:" + "e" * 64,
            ]
        )
        with mock.patch.object(
            search_cli,
            "verify_indexed_runtime",
            return_value={"ok": True, "command": "verify-indexed-runtime"},
        ) as verify:
            self.assertEqual(search_cli._dispatch(parsed_verify), {
                "ok": True,
                "command": "verify-indexed-runtime",
            })
        verify.assert_called_once_with("sha256:" + "e" * 64)

        for bad_revisions in (
            pairs[:3],
            [pairs[0], pairs[1], pairs[2], pairs[0]],
            ["us=" + "A" * 40, *pairs[1:]],
        ):
            with self.subTest(bad_revisions=bad_revisions):
                with self.assertRaises(search_cli.ArgumentFailure):
                    search_cli._normalize_revision_pairs(bad_revisions)

        for bad_runtime_id in ("latest", "../runtime"):
            with self.subTest(bad_runtime_id=bad_runtime_id):
                with self.assertRaises(search_cli.RunInputError):
                    search_cli.verify_indexed_runtime(bad_runtime_id)

        with self.assertRaises(search_cli.ArgumentFailure):
            parser.parse_args(
                [
                    "verify-indexed-runtime",
                    "--runtime-id",
                    "sha256:" + "f" * 64,
                    "--repo",
                    "outside",
                ]
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

    def test_factory_rejects_caller_callbacks_before_dispatch(self) -> None:
        result = self.create("reject-injection", ids=[IDS[0]], lanes=[LANES[0]])
        manifest = RunManifest.from_dict(result["manifest"])
        callback = mock.Mock()
        with mock.patch.object(
            _factory, "_compiler_identity",
            return_value=(manifest.compiler_identity, {"identity": manifest.compiler_identity}),
        ):
            with self.assertRaisesRegex(SupervisorIntegrationError, "providers"):
                run_instrumented(
                    Path(result["run_root"]) / "manifest.json",
                    adapters={LANES[0]: callback}, lease_path=self.repo / "lease.json",
                )
        callback.assert_not_called()

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
        # Isolate scheduling: production reconstruction rejects caller callbacks.
        with mock.patch(
            "automation.search_provider_lanes.reconstruct_lane_adapters", return_value=adapters,
        ), mock.patch(
            "automation.search_evaluator.IsolatedEvaluator._from_verified_factory", return_value=None,
        ), mock.patch.object(
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

    def test_three_candidate_fan_out_caps_children_and_preserves_outcome(self) -> None:
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
        # Isolate scheduling: production reconstruction rejects caller callbacks.
        with mock.patch(
            "automation.search_provider_lanes.reconstruct_lane_adapters", return_value=adapters,
        ), mock.patch(
            "automation.search_evaluator.IsolatedEvaluator._from_verified_factory", return_value=None,
        ), mock.patch.object(
            _factory,
            "_compiler_identity",
            return_value=(
                manifest.compiler_identity,
                {"identity": manifest.compiler_identity},
            ),
        ):
            run_result = run_instrumented(
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
        terminals = [
            event.payload
            for event in state.events
            if event.event_type == "task_completed"
        ]
        child_tasks = [
            task
            for task in scheduled
            if task.operation.startswith("materialize_candidate:")
        ]
        self.assertEqual(len(child_tasks), MAX_CHILD_TASKS_PER_BASE)
        self.assertEqual(len(terminals), 1 + MAX_CHILD_TASKS_PER_BASE)
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
        lane_terminal = next(
            terminal
            for terminal in terminals
            if terminal.task_id not in {task.task_id for task in child_tasks}
        )
        outcome_document = json.loads(
            (Path(result["run_root"]) / lane_terminal.result_artifacts[0].path).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(outcome_document["outcome"]["candidates"]), 3)

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

    def test_case_alias_target_files_are_deduplicated_by_filesystem_identity(self) -> None:
        actual_asm = (
            self.repo
            / "asm"
            / "us"
            / "st"
            / "rno0"
            / "nonmatchings"
            / "unit_a"
            / "func_a.s"
        )
        alias_asm = (
            self.repo
            / "asm"
            / "us"
            / "ST"
            / "RNO0"
            / "nonmatchings"
            / "unit_a"
            / "func_a.s"
        )
        actual_object = (
            self.repo / "build" / "us" / "src" / "st" / "rno0" / "unit_a.c.o"
        )
        alias_object = (
            self.repo / "build" / "us" / "src" / "ST" / "RNO0" / "unit_a.c.o"
        )
        try:
            alias_asm.parent.mkdir(parents=True, exist_ok=True)
            alias_object.parent.mkdir(parents=True, exist_ok=True)
            if not alias_asm.exists():
                os.link(actual_asm, alias_asm)
            if not alias_object.exists():
                os.link(actual_object, alias_object)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"filesystem aliases unavailable: {exc}")
        self.assertTrue(alias_asm.samefile(actual_asm))
        self.assertTrue(alias_object.samefile(actual_object))

        assembly, target_object = _factory._find_target_files(
            self.repo, self.records[0], IDS[0]
        )
        self.assertTrue(assembly.samefile(actual_asm))
        self.assertTrue(target_object.samefile(actual_object))
        self.create("case-alias-target", ids=[IDS[0]])

    def test_distinct_target_ambiguity_leaves_no_partial_run_root(self) -> None:
        duplicate = (
            self.repo / "asm" / "us" / "st" / "rno0" / "nonmatchings" / "unit_other"
        )
        duplicate.mkdir(parents=True)
        (duplicate / "func_a.s").write_text("func_a:\n\tnop\n", encoding="utf-8")
        run_root = (
            self.repo
            / "nonmatchings"
            / "func_a"
            / "search-runs"
            / "distinct-ambiguous"
        )
        with self.assertRaises(EvidenceRefusal):
            self.create("distinct-ambiguous", ids=[IDS[0]])
        self.assertFalse(run_root.exists())

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
