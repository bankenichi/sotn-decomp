import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_coordinator import (
    SEARCH_PATTERN_REPORT_TOOL_IDENTITY,
    SearchCoordinator,
    TaskResult,
)
from automation.search_patterns import (
    PatternActiveRun,
    PatternArtifactError,
    PatternIdentityMismatch,
    PatternPartialLedger,
    SearchPatternReport,
    load_report_artifact,
    mine_completed_lineages,
    render_derivation_summary,
)
from automation.search_types import (
    ArtifactRef,
    CandidateRecord,
    EvaluationEvent,
    FirstDivergence,
    GroupedPatch,
    MutationEvent,
    PatchHunk,
    ScoreComponents,
    ScoreDeltas,
    ScoreVector,
    canonical_bytes,
    canonical_json,
    canonical_subset_identity,
    hash_bytes,
    hash_canonical,
)
from automation.test_search_schema import manifest, score


def _manifest_for(run_id: str, recipient: str = "us:ST/RDAI:func_us_801B001C"):
    base = manifest()
    return replace(
        base,
        run_id=run_id,
        queue_record_ids=(recipient,),
        function_ids=(recipient,),
        subset_identity=canonical_subset_identity((recipient,)),
        target_identities={recipient: hash_bytes(("target-" + recipient).encode())},
    )


def _failed_score() -> ScoreVector:
    return ScoreVector(
        compile_status="failed",
        elapsed_ms=2,
        total=None,
        components=ScoreComponents(0, 0, 0, 0, 0),
        weights=ScoreComponents(1, 5, 60, 100, 100),
        object_hash=None,
        mismatch_signature=None,
        first_divergence=None,
        target_instruction_count=3,
        candidate_instruction_count=None,
        diagnostic_artifact=None,
        scorer_algorithm="difflib",
        compiler_identity=hash_bytes(b"compiler"),
    )


def _run_with_observation(
    root: Path,
    run_id: str,
    *,
    successful: bool = True,
    recipient: str = "us:ST/RDAI:func_us_801B001C",
) -> None:
    coordinator = SearchCoordinator(root, _manifest_for(run_id, recipient))
    base_source = "int candidate(void) { return 0; }\n"
    base_hash = hash_bytes(base_source.encode())
    base_artifact = ArtifactRef(
        base_hash,
        "artifacts/sources/" + base_hash[7:] + ".c",
        "text/x-c",
        len(base_source.encode()),
    )
    parent_task = coordinator.create_task(
        recipient_id=recipient,
        lane="upstream_current",
        operation="pattern-parent-fixture",
        budget_ordinal=0,
    )
    coordinator.schedule_task(parent_task)
    parent_candidate = CandidateRecord(
        base_hash,
        recipient,
        base_artifact,
        (),
        None,
        "upstream_current",
        0,
        None,
        "materialized",
    )
    coordinator.commit_epoch(
        [TaskResult(parent_task.task_id, candidate=parent_candidate, source=base_source)]
    )
    task = coordinator.create_task(
        recipient_id=recipient,
        lane="upstream_current",
        operation="pattern-fixture",
        parent_candidate_ids=(base_hash,),
        budget_ordinal=1,
    )
    coordinator.schedule_task(task)
    source = "int candidate(void) { return 1; }\n"
    source_hash = hash_bytes(source.encode())
    source_artifact = ArtifactRef(
        source_hash,
        "artifacts/sources/" + source_hash[7:] + ".c",
        "text/x-c",
        len(source.encode()),
    )
    hunk = PatchHunk(0, "return 0;\n", "return 1;\n", (), ())
    patch_payload = {
        "format": "line_context",
        "base_source_hash": base_hash,
        "atomic": True,
        "hunks": [hunk],
    }
    patch_id = hash_canonical(patch_payload)
    grouped_patch = GroupedPatch(
        patch_id,
        "line_context",
        patch_payload["base_source_hash"],
        True,
        (hunk,),
    )
    mutation_id = hash_bytes(b"pattern-pass")
    mutation = MutationEvent(
        mutation_id,
        base_hash,
        recipient,
        "upstream_current",
        "declaration_shape",
        task.task_seed,
        grouped_patch,
        (),
        "applied",
        source_hash,
    )
    candidate = CandidateRecord(
        source_hash,
        recipient,
        source_artifact,
        (base_hash,),
        mutation_id,
        "upstream_current",
        1,
        None,
        "materialized",
    )
    after = score(1, signature="pattern-residual") if successful else _failed_score()
    after = replace(
        after,
        first_divergence=FirstDivergence(
            target_index=4,
            candidate_index=5,
            target_instruction="lw v0, 0(a0)",
            candidate_instruction="lw v0, 4(a0)",
        ),
    )
    evaluation = EvaluationEvent(
        task.task_id,
        recipient,
        source_hash,
        None,
        None,
        after,
        ScoreDeltas(-1 if successful else None, 0, 0, 0, 0, -1 if successful else 0),
        coordinator.frontier.cache.key_for(recipient, source_hash, after.compiler_identity),
        "scalar_elite" if successful else "compile_failed",
    )
    coordinator.commit_epoch(
        [TaskResult(task.task_id, mutation=mutation, candidate=candidate, source=source, evaluation=evaluation)]
    )
    coordinator.stop(reason="completed", resumable=False)


def _rewrite_ledger(path: Path, mutate) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        mutate(row)
    previous = None
    for row in rows:
        row["previous_event_hash"] = previous
        row.pop("event_hash", None)
        row["event_hash"] = hash_canonical(row)
        previous = row["event_hash"]
    path.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
    )


class TestSearchPatterns(unittest.TestCase):
    def test_aggregates_completed_lineages_and_requires_two_successes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            runs = []
            for index, successful in enumerate((True, True, False), 1):
                root = parent / ("run-" + str(index))
                _run_with_observation(root, "pattern-run-" + str(index), successful=successful)
                runs.append(root)
            report = mine_completed_lineages(runs, output_root=parent / "reports")
            self.assertEqual(len(report.source_ledgers), 3)
            self.assertEqual(len(report.recommendations), 1)
            recommendation = report.recommendations[0]
            self.assertEqual(recommendation["pass_kind"], "declaration_shape")
            self.assertEqual(recommendation["patch_id"], hash_canonical({
                "format": "line_context",
                "base_source_hash": hash_bytes(
                    b"int candidate(void) { return 0; }\n"
                ),
                "atomic": True,
                "hunks": [PatchHunk(0, "return 0;\n", "return 1;\n", (), ())],
            }))
            self.assertEqual(recommendation["lane"], "upstream_current")
            self.assertEqual(recommendation["overlay"], "ST/RDAI")
            self.assertEqual(recommendation["function_archetype"], "generic")
            self.assertEqual(recommendation["sample_count"], 3)
            self.assertEqual(recommendation["successes"], 2)
            self.assertEqual(recommendation["failures"], 1)
            self.assertEqual(recommendation["first_divergence"]["target_index"], 4)
            self.assertEqual(recommendation["first_divergence"]["candidate_index"], 5)
            self.assertEqual(
                set(recommendation["source_ledgers"]),
                set(report.source_ledgers),
            )
            self.assertEqual(report.artifact.content_hash, report.report_id)

    def test_single_observation_is_not_published_as_a_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            _run_with_observation(root, "pattern-single")
            report = mine_completed_lineages(root, output_root=Path(directory) / "reports")
            self.assertEqual(report.recommendations, ())
            self.assertNotIn("declaration_shape", render_derivation_summary(report))

    def test_partial_active_and_corrupt_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            partial = parent / "partial"
            _run_with_observation(partial, "pattern-partial")
            with (partial / "ledger.jsonl").open("ab") as stream:
                stream.write(b'{"partial":')
            with self.assertRaises(PatternPartialLedger):
                mine_completed_lineages(partial, output_root=parent / "reports-partial")

            active = parent / "active"
            coordinator = SearchCoordinator(active, _manifest_for("pattern-active"))
            task = coordinator.create_task(
                recipient_id="us:ST/RDAI:func_us_801B001C",
                lane="upstream_current",
                operation="active",
            )
            coordinator.schedule_task(task)
            with self.assertRaises(PatternActiveRun):
                mine_completed_lineages(active, output_root=parent / "reports-active")

            corrupt = parent / "corrupt"
            _run_with_observation(corrupt, "pattern-corrupt")
            source_files = list((corrupt / "artifacts" / "sources").glob("*.c"))
            self.assertEqual(len(source_files), 2)
            source_files[0].write_text("changed\n", encoding="utf-8")
            with self.assertRaises(PatternArtifactError):
                mine_completed_lineages(corrupt, output_root=parent / "reports-corrupt")

    def test_started_task_identity_cannot_change_under_the_same_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "tampered"
            _run_with_observation(root, "pattern-task-identity")

            def tamper_started(row):
                if row["event_type"] != "task_started":
                    return
                payload = row["payload"]
                payload["recipient_id"] = "us:ST/RDAI:other_function"
                payload["lane"] = "transplant"
                payload["budget_ordinal"] = payload["budget_ordinal"] + 1
                payload["config_identity"] = hash_bytes(b"changed-task-config")

            _rewrite_ledger(root / "ledger.jsonl", tamper_started)
            with self.assertRaises(PatternIdentityMismatch):
                mine_completed_lineages(root, output_root=Path(directory) / "reports")

    def test_evaluation_cannot_name_an_unmaterialized_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "orphan-candidate"
            _run_with_observation(root, "pattern-orphan-candidate")

            def tamper_evaluation(row):
                if row["event_type"] == "evaluation_completed":
                    row["payload"]["candidate_id"] = hash_bytes(b"missing-candidate")

            _rewrite_ledger(root / "ledger.jsonl", tamper_evaluation)
            with self.assertRaises(PatternIdentityMismatch):
                mine_completed_lineages(root, output_root=Path(directory) / "reports")

    def test_identity_and_replay_are_deterministic_and_source_run_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            first = parent / "run-1"
            second = parent / "run-2"
            _run_with_observation(first, "pattern-replay-1")
            _run_with_observation(second, "pattern-replay-2")
            before = {
                root: ((root / "manifest.json").read_bytes(), (root / "ledger.jsonl").read_bytes())
                for root in (first, second)
            }
            output = parent / "reports"
            one = mine_completed_lineages([first, second], output_root=output)
            two = mine_completed_lineages([first, second], output_root=output)
            self.assertEqual(one, two)
            self.assertEqual(one.to_json(), two.to_json())
            for root in (first, second):
                self.assertEqual(before[root][0], (root / "manifest.json").read_bytes())
                self.assertEqual(before[root][1], (root / "ledger.jsonl").read_bytes())
            loaded = load_report_artifact(one.artifact, artifact_root=output)
            self.assertEqual(loaded, one)
            with self.assertRaises(PatternIdentityMismatch):
                load_report_artifact(one, expected_hash=hash_bytes(b"changed-report"))
            with self.assertRaises(PatternIdentityMismatch):
                mine_completed_lineages(first, output_root=first)

    def test_report_is_deeply_immutable_and_summary_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            sibling = Path(directory) / "sibling"
            _run_with_observation(root, "pattern-summary")
            _run_with_observation(sibling, "pattern-summary-sibling")
            report = mine_completed_lineages(
                [root, sibling],
                output_root=Path(directory) / "reports",
            )
            with self.assertRaises(TypeError):
                report.recommendations[0]["lane"] = "changed"  # type: ignore[index]
            summary = render_derivation_summary(report, max_chars=80)
            self.assertLessEqual(len(summary), 80)
            self.assertTrue(summary.endswith("..."))


if __name__ == "__main__":
    unittest.main()
