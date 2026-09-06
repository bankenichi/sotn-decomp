"""Real compiler, durable retry, and coordinator evaluation integration."""
import json
import shutil
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation import compiler_corpus
from automation.search_archive import ArtifactCorrupt, ContentAddressedArchive
from automation.search_coordinator import SearchCoordinator, TaskResult, OracleRequired
from automation.search_evaluator import IsolatedEvaluator, validate_evaluation_receipts
from automation.search_run_factory import create_instrumented_run, _CORE_MODULES, _FACTORY_MODULE, _LANE_MODULES
from automation.search_supervisor import run_instrumented, SupervisorIntegrationError
from automation.search_types import CandidateRecord, hash_bytes
from automation.test_search_schema import manifest


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        pipeline = compiler_corpus._pipeline()
        target, _, _ = compiler_corpus._compile_source(
            "int neighbor(int x) { return x * 7; } int f(int x) { return x + 1; }",
            pipeline, self.root, name="target",
        )
        base = manifest()
        self.manifest = replace(
            base, compiler_identity=pipeline.identity.identity,
            tool_identities={**base.tool_identities, "search_evaluator": hash_bytes(b"evaluator")},
        )
        self.coordinator = SearchCoordinator(self.root / "run", self.manifest)
        self.archive = self.coordinator.archive
        self.target = self.archive.put_object(target.read_bytes())
        self.evaluator = IsolatedEvaluator(
            self.manifest, self.archive, {"record-1": self.target}, symbols={"record-1": "f"},
        )

    def result(self, source):
        ref = self.archive.put_source(source)
        task = self.coordinator.create_task(
            recipient_id="record-1", lane="upstream_current",
            operation="materialize_candidate:" + ref.content_hash, budget_ordinal=0,
        )
        self.coordinator.schedule_task(task)
        return TaskResult(
            task.task_id, candidate=CandidateRecord(
                ref.content_hash, "record-1", ref, (), None, "upstream_current",
                0, None, "materialized",
            ), source=source,
        )

    def factory_run(self, lanes=("preserved_candidate",)):
        repo = self.root / "repo"
        (repo / "src").mkdir(parents=True)
        (repo / "include").mkdir()
        for relative, _ in (*_CORE_MODULES, _FACTORY_MODULE):
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((compiler_corpus.ROOT / relative).read_bytes())
        for lane in lanes:
            for relative in _LANE_MODULES.get(lane, ()):
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((compiler_corpus.ROOT / relative).read_bytes())
        if any(lane.startswith("permuter_") for lane in lanes):
            for path in (compiler_corpus.ROOT / "automation").glob("*.py"):
                shutil.copy2(path, repo / "automation" / path.name)
            for relative in ("tools/decomp-permuter", "tools/maspsx"):
                shutil.copytree(compiler_corpus.ROOT / relative, repo / relative,
                                dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", ".git", ".mypy_cache", ".pytest_cache"))
            for relative in ("bin/cc1-psx-26", "tools/sotn_str/target/release/sotn_str"):
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(compiler_corpus.ROOT / relative, path)
        config = repo / "tools/sotn_permuter/permuter_settings.us.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_bytes(compiler_corpus.DEFAULT_CONFIG_PATH.read_bytes())
        (repo / "automation/search-ledger.schema.json").write_bytes(
            (compiler_corpus.ROOT / "automation/search-ledger.schema.json").read_bytes()
        )
        asm = repo / "asm/us/st/rno0/nonmatchings/unit/f.s"
        asm.parent.mkdir(parents=True)
        asm.write_text("f:\n    li $v0, 7\n    jr $ra\n    nop\n")
        obj = repo / "build/us/src/st/rno0/unit.c.o"
        obj.parent.mkdir(parents=True)
        obj.write_bytes(self.archive.verify(self.target))
        candidate = repo / "automation/candidates/f.c"
        candidate.parent.mkdir(parents=True)
        candidate.write_text("int f(int x) { return x + 2; }")
        record = {
            "id": "us:ST/RNO0:f", "function": "f", "build": "us",
            "overlay": "ST/RNO0", "status": "todo", "claimed_by": "none",
            "notes": "",
        }
        model_lanes = set(lanes).intersection({"model_fleet", "model_expensive"})
        if model_lanes:
            (repo / "automation/search-provider-settings.json").write_text(json.dumps({
                "protocol": "sotn-search-provider-settings-v1",
                "models": {lane: {
                    "endpoint": "http://localhost:8080/v1", "model_name": "fixture-model", "provider": "local",
                    "reasoning": "none", "paid": lane == "model_expensive", "timeout_seconds": 10,
                    "max_tokens": 128, "api_key_env": "MODEL_API_KEY",
                } for lane in model_lanes},
            }))
        if any(lane.startswith("permuter_") for lane in lanes):
            # Both factory and child process must measure the same isolated
            # repository, including the relative compiler configuration path.
            root_patch = patch.object(compiler_corpus, "ROOT", repo)
            root_patch.start()
            self.addCleanup(root_patch.stop)
        created = create_instrumented_run(
            "evaluation-proof", [record["id"]], lanes,
            repo=repo, queue_reader=lambda: [record],
        )
        return repo, created

    def test_public_factory_reconstructs_and_executes_five_concrete_providers(self):
        lanes = ("bounded_synthesis", "permuter_random", "permuter_targeted", "permuter_recombine", "permuter_ddmin")
        repo, created = self.factory_run(lanes)
        path = Path(created["run_root"]) / "manifest.json"
        result = run_instrumented(path, lease_path=self.root / "lease.json")
        self.assertTrue(result["ok"])
        funnel = result["funnel"]
        self.assertEqual(funnel["denominators"]["recipient_lane_pairs"], 5)
        self.assertEqual(funnel["totals"]["terminal_pairs"], 5)
        self.assertGreater(funnel["totals"]["evaluated_unique_across_lanes"], 0)
        self.assertEqual(funnel["totals"]["oracle_verified_matches"], 0)
        from automation.search_cli import status_run
        self.assertEqual(status_run(path.parent)["funnel"], funnel)
        manifest = type(self.manifest).from_dict(created["manifest"])
        events = SearchCoordinator(path.parent, manifest).events
        tasks = {event.payload.task_id: event.payload for event in events if event.event_type == "task_scheduled"}
        measured_lanes = {tasks[event.payload.task_id].lane for event in events if event.event_type == "evaluation_completed"}
        provider_results = [json.loads(p.read_text()) for p in (path.parent / "artifacts/permuter-results").glob("*.json")]
        self.assertTrue(set(lanes).difference({"permuter_recombine"}).issubset(measured_lanes),
                        [(r.get("status"), r.get("reason"), r.get("refusal_code")) for r in provider_results])
        operations = [json.loads(p.read_text()) for p in (path.parent / "artifacts/permuter-operations").glob("*.json")]
        self.assertEqual({item["strategy"] for item in operations}, {"random", "targeted", "recombine", "ddmin"})
        if "permuter_recombine" not in measured_lanes:
            self.assertTrue(all(item["result"]["conflict_patch_ids"] for item in operations if item["strategy"] == "recombine"))
        self.assertEqual(len(list((path.parent / "artifacts/provider-state").glob("*.json"))), 1)
        from automation.search_recovery import recover_run
        recovered = recover_run(path.parent)
        self.assertEqual(len(recovered.receipts), len(lanes))
        with patch("automation.search_evaluator.compile_against_object", side_effect=AssertionError("recompiled")):
            self.assertTrue(run_instrumented(path, lease_path=self.root / "lease.json")["ok"])

    def test_public_model_factories_are_deferred_before_dispatch(self):
        # The earlier positive dispatch fixture was superseded by the owner's
        # programmatic-first correction. Preserve transport behavior separately.
        lanes = ("model_fleet", "model_expensive")
        from automation.search_run_factory import InputRefusal
        with patch("automation.search_model_executor.urllib.request.urlopen", side_effect=AssertionError("deferred model call")) as network:
            with self.assertRaisesRegex(InputRefusal, "model lanes are deferred"):
                self.factory_run(lanes)
            network.assert_not_called()

    def test_measured_selection_keeps_unexamined_candidates_explicit(self):
        from automation.search_evaluator import measured_lane_report
        first = self.evaluator.evaluate(self.coordinator, self.result("int f(int x) { return x + 2; }"))
        self.coordinator.commit_epoch((first,))
        other = hash_bytes(b"not evaluated")
        task = SimpleNamespace(task_id="base", recipient_id="record-1", lane="upstream_current")
        outcome = SimpleNamespace(candidates=(
            SimpleNamespace(candidate_id=other),
            SimpleNamespace(candidate_id=first.candidate.candidate_id),
        ))
        report = measured_lane_report(self.manifest, task, outcome, self.coordinator.events)
        self.assertEqual(report["best_measured_candidate_ids"], [first.candidate.candidate_id])
        self.assertFalse(report["evaluation_complete"])
        self.assertEqual(report["evaluated"], 1)
        self.assertEqual(next(item for item in report["candidates"] if item["candidate_id"] == other)
                         ["disposition"], "unexamined_candidate_budget")

    def test_public_factory_start_measures_builtin_candidates_without_callbacks(self):
        repo, created = self.factory_run()
        path = Path(created["run_root"]) / "manifest.json"
        result = run_instrumented(path, lease_path=self.root / "lease.json")
        self.assertTrue(result["ok"])
        events = SearchCoordinator(
            path.parent, type(self.manifest).from_dict(created["manifest"]),
        ).events
        evaluations = [event.payload for event in events if event.event_type == "evaluation_completed"]
        self.assertEqual(len(evaluations), 1)
        self.assertGreater(evaluations[0].after.total, 0)
        with patch("automation.search_evaluator.compile_against_object", side_effect=AssertionError("recompiled")):
            self.assertTrue(run_instrumented(path, lease_path=self.root / "lease.json")["ok"])

    def test_public_factory_rejects_unbound_execution_overrides(self):
        repo, created = self.factory_run()
        path = Path(created["run_root"]) / "manifest.json"
        for overrides in (
            {"options": {"repo_root": str(self.root)}},
            {"options": {"preserved_paths": ["arbitrary.c"]}},
            {"lane_executor": lambda *args, **kwargs: None},
        ):
            with self.subTest(overrides=tuple(overrides)):
                with self.assertRaises(SupervisorIntegrationError):
                    run_instrumented(path, lease_path=self.root / "lease.json", **overrides)

    def test_measurement_flows_to_ordinary_ledger_and_frontier(self):
        result = self.evaluator.evaluate(
            self.coordinator, self.result("int f(int x) { return x + 2; }"),
        )
        self.assertGreater(result.evaluation.after.total, 0)
        self.coordinator.commit_epoch((result,))
        self.assertIn("evaluation_completed", [event.event_type for event in self.coordinator.events])
        self.assertEqual(
            self.coordinator.frontier.graph.get(result.candidate.candidate_id).evaluation,
            result.evaluation.after,
        )
        validate_evaluation_receipts(self.manifest, self.archive)

    def test_restart_after_receipt_never_recompiles_candidate(self):
        result = self.result("int f(int x) { return x + 2; }")
        measured = self.evaluator.evaluate(self.coordinator, result)
        restarted = IsolatedEvaluator(
            self.manifest, ContentAddressedArchive(self.archive.run_root),
            {"record-1": self.target}, symbols={"record-1": "f"},
        )
        with patch("automation.search_evaluator.compile_against_object", side_effect=AssertionError("recompiled")):
            replay = restarted.evaluate(self.coordinator, result)
        self.assertEqual(measured, replay)

    def test_corrupt_transitive_object_blocks_recovery(self):
        result = self.evaluator.evaluate(
            self.coordinator, self.result("int f(int x) { return x + 2; }"),
        )
        receipt = json.loads(self.archive.verify(result.result_artifacts[-1]))
        object_path = self.archive.run_root / receipt["object"]["path"]
        object_path.write_bytes(b"corrupted")
        with self.assertRaises(ArtifactCorrupt):
            validate_evaluation_receipts(self.manifest, self.archive)

    def test_zero_score_is_durable_but_never_claims_full_match(self):
        result = self.evaluator.evaluate(
            self.coordinator, self.result("int f(int x) { return x + 1; }"),
        )
        self.assertEqual(result.evaluation.after.total, 0)
        with self.assertRaises(OracleRequired):
            self.coordinator.commit_epoch((result,))
        candidate = self.coordinator.frontier.graph.get(result.candidate.candidate_id)
        self.assertEqual(candidate.status, "zero_pending_oracle")
        self.assertNotIn("oracle_result_recorded", [event.event_type for event in self.coordinator.events])

    def test_compile_rejection_retains_diagnostic_artifact(self):
        result = self.evaluator.evaluate(
            self.coordinator, self.result("int f(int x) { return + ; }"),
        )
        self.assertEqual(result.evaluation.after.compile_status, "failed")
        self.assertIsNone(result.evaluation.after.total)
        diagnostic = result.evaluation.after.diagnostic_artifact
        self.assertIsNotNone(diagnostic)
        self.assertTrue(self.archive.verify(diagnostic))


if __name__ == "__main__":
    unittest.main()
