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
    CompletedLineageContext,
    CompletedLineageDiagnostic,
    PatternActiveRun,
    PatternArtifactError,
    PatternIdentityMismatch,
    PatternInputError,
    PatternLedgerCorrupt,
    PatternPartialLedger,
    SearchPatternReport,
    load_completed_lineage_contexts,
    load_report_artifact,
    mine_completed_lineages,
    render_derivation_summary,
)
from automation.search_supervisor import EVALUATOR_TOOL_KEY
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
    tools = dict(base.tool_identities)
    # The reserved evaluator binding makes these runs promotable evidence
    # under the corpus contract; without it they are diagnostics only.
    tools[EVALUATOR_TOOL_KEY] = hash_bytes(b"search-evaluator")
    return replace(
        base,
        run_id=run_id,
        queue_record_ids=(recipient,),
        function_ids=(recipient,),
        subset_identity=canonical_subset_identity((recipient,)),
        target_identities={recipient: hash_bytes(("target-" + recipient).encode())},
        tool_identities=tools,
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
            # The canonical coordinator semantic pass now refuses the forged
            # cross-record binding before the miner ever groups a sample; the
            # typed pattern errors remain for the cases their own checks own.
            with self.assertRaises(PatternLedgerCorrupt):
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


def _lineage_digest(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


def _lineage_manifest(
    run_id: str,
    *,
    lane: str,
    recipient: str,
    compiler_identity: str,
    config_identity: str,
    schema_identity: str,
    include_evaluator: bool,
    target_identity: str,
    evaluator_identity: str | None = None,
    include_full_oracle: bool = True,
):
    base = manifest()
    tools = {
        lane: _lineage_digest("tool:" + lane),
    }
    if include_full_oracle:
        tools["full_oracle"] = _lineage_digest("full-oracle")
    if include_evaluator:
        tools[EVALUATOR_TOOL_KEY] = (
            evaluator_identity or _lineage_digest("search-evaluator")
        )
    return replace(
        base,
        run_id=run_id,
        queue_record_ids=(recipient,),
        function_ids=(recipient,),
        subset_identity=canonical_subset_identity((recipient,)),
        target_identities={recipient: target_identity},
        compiler_identity=compiler_identity,
        config_identity=config_identity,
        schema_identity=schema_identity,
        selected_lanes=(lane,),
        tool_identities=tools,
        lane_budgets={lane: base.lane_budgets[lane]},
    )


def _completed_lineage_run(
    root: Path,
    run_id: str,
    *,
    lane: str = "cfg_dataflow",
    recipient: str = "us:ST:fn",
    compiler_identity: str | None = None,
    config_identity: str | None = None,
    schema_identity: str | None = None,
    include_evaluator: bool = True,
    target_identity: str | None = None,
    evaluator_identity: str | None = None,
    include_full_oracle: bool = True,
    scorer_algorithm: str = "difflib",
    divergence: FirstDivergence | None = None,
) -> Path:
    """Write one completed, artifact-verified ledger with requested bindings.

    One observation per run, deliberately: the frontier refuses a repeated
    candidate id under conflicting metadata, so sample aggregation is
    designed to happen across runs whose manifests share the bindings under
    test.
    """

    compiler = compiler_identity or _lineage_digest("compiler")
    config = config_identity or _lineage_digest("config")
    schema = schema_identity or _lineage_digest("schema")
    target = target_identity or _lineage_digest("target:" + recipient)
    coordinator = SearchCoordinator(
        root,
        _lineage_manifest(
            run_id,
            lane=lane,
            recipient=recipient,
            compiler_identity=compiler,
            config_identity=config,
            schema_identity=schema,
            include_evaluator=include_evaluator,
            target_identity=target,
            evaluator_identity=evaluator_identity,
            include_full_oracle=include_full_oracle,
        ),
    )
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
        lane=lane,
        operation="lineage-parent-fixture",
        budget_ordinal=0,
    )
    coordinator.schedule_task(parent_task)
    parent_candidate = CandidateRecord(
        base_hash, recipient, base_artifact, (), None, lane, 0, None, "materialized",
    )
    coordinator.commit_epoch(
        [TaskResult(parent_task.task_id, candidate=parent_candidate, source=base_source)]
    )
    task = coordinator.create_task(
        recipient_id=recipient,
        lane=lane,
        operation="lineage-fixture",
        parent_candidate_ids=(base_hash,),
        budget_ordinal=1,
    )
    coordinator.schedule_task(task)
    # Identical candidate content across runs on purpose: the group key
    # includes the patch id, so varied content would split the samples into
    # singleton groups that never meet min_samples.
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
    mutation = MutationEvent(
        hash_bytes(f"lineage-{run_id}".encode()),
        base_hash,
        recipient,
        lane,
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
        mutation.mutation_id,
        lane,
        1,
        None,
        "materialized",
    )
    after = replace(
        score(1, signature=f"lineage-{run_id}"),
        compiler_identity=compiler,
        scorer_algorithm=scorer_algorithm,
        first_divergence=divergence,
    )
    evaluation = EvaluationEvent(
        task.task_id,
        recipient,
        source_hash,
        None,
        None,
        after,
        ScoreDeltas(-1, 0, 0, 0, 0, -1),
        coordinator.frontier.cache.key_for(recipient, source_hash, after.compiler_identity),
        "scalar_elite",
    )
    coordinator.commit_epoch(
        [TaskResult(task.task_id, mutation=mutation, candidate=candidate, source=source, evaluation=evaluation)]
    )
    coordinator.stop(reason="completed", resumable=False)
    return root


class CompletedLineageContextTests(unittest.TestCase):
    def fixture_completed_ledger(
        self,
        root: Path,
        *,
        include_evaluator: bool = True,
        compiler_identity: str | None = None,
        config_identity: str | None = None,
        schema_identity: str | None = None,
        lane: str = "cfg_dataflow",
        recipient_id: str = "us:ST:fn",
        target_identity: str | None = None,
        evaluator_identity: str | None = None,
        include_full_oracle: bool = True,
        scorer_algorithm: str = "difflib",
        divergence: FirstDivergence | None = None,
    ) -> Path:
        return _completed_lineage_run(
            root,
            "lineage-" + root.name,
            lane=lane,
            recipient=recipient_id,
            compiler_identity=compiler_identity,
            config_identity=config_identity,
            schema_identity=schema_identity,
            include_evaluator=include_evaluator,
            target_identity=target_identity,
            evaluator_identity=evaluator_identity,
            include_full_oracle=include_full_oracle,
            scorer_algorithm=scorer_algorithm,
            divergence=divergence,
        )

    def test_active_ledger_never_becomes_lineage_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            active = Path(directory) / "running"
            SearchCoordinator(
                active,
                _lineage_manifest(
                    "lineage-running",
                    lane="cfg_dataflow",
                    recipient="us:ST:fn",
                    compiler_identity=_lineage_digest("compiler"),
                    config_identity=_lineage_digest("config"),
                    schema_identity=_lineage_digest("schema"),
                    include_evaluator=True,
                    target_identity=_lineage_digest("target:us:ST:fn"),
                ),
            )
            with self.assertRaisesRegex(PatternActiveRun, "active or resumable"):
                load_completed_lineage_contexts([active])

    def test_completed_context_binds_lane_target_and_evaluator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture_completed_ledger(Path(directory) / "run")
            context = load_completed_lineage_contexts([root])[0]
            self.assertIsInstance(context, CompletedLineageContext)
            self.assertEqual(context.compiler_identity, _lineage_digest("compiler"))
            self.assertEqual(context.config_identity, _lineage_digest("config"))
            self.assertEqual(context.schema_identity, _lineage_digest("schema"))
            self.assertEqual(context.scorer_algorithms, ("difflib",))
            self.assertEqual(
                context.lane_tool_identities,
                (("cfg_dataflow", _lineage_digest("tool:cfg_dataflow")),),
            )
            self.assertEqual(
                context.recipient_target_identities,
                (("us:ST:fn", _lineage_digest("target:us:ST:fn")),),
            )
            self.assertEqual(
                context.evaluator_identity, _lineage_digest("search-evaluator")
            )

    def test_missing_historical_evaluator_is_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture_completed_ledger(
                Path(directory) / "run", include_evaluator=False
            )
            context = load_completed_lineage_contexts([root])[0]
            self.assertIsInstance(context, CompletedLineageDiagnostic)
            self.assertEqual(context.reason_code, "missing_evaluator_identity")
            self.assertEqual(
                context.observed_identities,
                tuple(
                    sorted(
                        (
                            _lineage_digest("compiler"),
                            _lineage_digest("config"),
                            _lineage_digest("schema"),
                            _lineage_digest("full-oracle"),
                        )
                    )
                ),
            )

    def test_diagnostic_without_full_oracle_has_no_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture_completed_ledger(
                Path(directory) / "run",
                include_evaluator=False,
                include_full_oracle=False,
            )
            context = load_completed_lineage_contexts([root])[0]
            self.assertIsInstance(context, CompletedLineageDiagnostic)
            # Only identities that actually exist are retained: no empty
            # placeholder stands in for the absent full-oracle binding.
            self.assertEqual(
                context.observed_identities,
                tuple(
                    sorted(
                        (
                            _lineage_digest("compiler"),
                            _lineage_digest("config"),
                            _lineage_digest("schema"),
                        )
                    )
                ),
            )

    def test_diagnostic_records_reject_forged_shapes(self) -> None:
        def diagnostic(**overrides):
            values = dict(
                ledger_identity=_lineage_digest("ledger"),
                run_id="lineage-run",
                reason_code="missing_evaluator_identity",
                observed_identities=(
                    _lineage_digest("compiler"),
                    _lineage_digest("config"),
                ),
            )
            values.update(overrides)
            return CompletedLineageDiagnostic(**values)

        first_hash = _lineage_digest("compiler")
        second_hash = _lineage_digest("config")
        low, high = sorted((first_hash, second_hash))
        with self.assertRaises(PatternInputError):
            diagnostic(observed_identities=(high, low))
        with self.assertRaises(PatternInputError):
            diagnostic(observed_identities=(first_hash, ""))
        with self.assertRaises(PatternInputError):
            diagnostic(observed_identities=None)
        self.assertIsInstance(
            diagnostic(observed_identities=(low, high)),
            CompletedLineageDiagnostic,
        )

    def test_recommendations_carry_lineage_identities(self) -> None:
        divergence = FirstDivergence(4, 5, "lw v0, 0(a0)", "lw v0, 4(a0)")
        with tempfile.TemporaryDirectory() as directory:
            # Two runs with identical bindings: aggregation is designed to
            # happen across runs, since one run contributes one observation.
            first = self.fixture_completed_ledger(
                Path(directory) / "run-a",
                divergence=divergence,
            )
            second = self.fixture_completed_ledger(
                Path(directory) / "run-b",
                divergence=divergence,
            )
            report = mine_completed_lineages(
                [first, second], output_root=Path(directory) / "reports"
            )
            self.assertEqual(len(report.recommendations), 1)
            recommendation = report.recommendations[0]
            self.assertEqual(recommendation["scorer_algorithm"], "difflib")
            self.assertEqual(
                recommendation["compiler_identity"], _lineage_digest("compiler")
            )
            self.assertEqual(
                recommendation["config_identity"], _lineage_digest("config")
            )
            self.assertEqual(
                recommendation["schema_identity"], _lineage_digest("schema")
            )
            self.assertEqual(
                recommendation["lane_tool_identity"],
                _lineage_digest("tool:cfg_dataflow"),
            )
            self.assertEqual(recommendation["recipient_id"], "us:ST:fn")
            self.assertEqual(
                recommendation["target_identity"],
                _lineage_digest("target:us:ST:fn"),
            )
            self.assertEqual(
                recommendation["evaluator_identity"],
                _lineage_digest("search-evaluator"),
            )
            self.assertEqual(
                recommendation["first_divergence"]["target_instruction"],
                "lw v0, 0(a0)",
            )

    def test_incompatible_compilers_stay_separate_lineages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = self.fixture_completed_ledger(
                Path(directory) / "run-a",
                compiler_identity=_lineage_digest("compiler-a"),
            )
            second = self.fixture_completed_ledger(
                Path(directory) / "run-b",
                compiler_identity=_lineage_digest("compiler-a"),
            )
            third = self.fixture_completed_ledger(
                Path(directory) / "run-c",
                compiler_identity=_lineage_digest("compiler-b"),
            )
            fourth = self.fixture_completed_ledger(
                Path(directory) / "run-d",
                compiler_identity=_lineage_digest("compiler-b"),
            )
            report = mine_completed_lineages(
                [first, second, third, fourth],
                output_root=Path(directory) / "reports",
            )
            self.assertEqual(len(report.recommendations), 2)
            self.assertEqual(
                {item["compiler_identity"] for item in report.recommendations},
                {_lineage_digest("compiler-a"), _lineage_digest("compiler-b")},
            )

    def test_reversed_ledger_order_produces_identical_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = self.fixture_completed_ledger(Path(directory) / "run-a")
            second = self.fixture_completed_ledger(Path(directory) / "run-b")
            one = mine_completed_lineages(
                [first, second], output_root=Path(directory) / "reports-one"
            )
            two = mine_completed_lineages(
                [second, first], output_root=Path(directory) / "reports-two"
            )
            self.assertEqual(one.report_id, two.report_id)
            self.assertEqual(one.recommendations, two.recommendations)

    def test_missing_evaluator_ledgers_are_excluded_from_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            # Two otherwise promotable runs whose manifests lost the reserved
            # evaluator binding: diagnostics only, never recommendation input.
            first = self.fixture_completed_ledger(
                Path(directory) / "run-a", include_evaluator=False
            )
            second = self.fixture_completed_ledger(
                Path(directory) / "run-b", include_evaluator=False
            )
            report = mine_completed_lineages(
                [first, second], output_root=Path(directory) / "reports"
            )
            self.assertEqual(report.recommendations, ())
            contexts = load_completed_lineage_contexts([first, second])
            self.assertEqual(len(contexts), 2)
            for context in contexts:
                self.assertIsInstance(context, CompletedLineageDiagnostic)
                self.assertEqual(context.reason_code, "missing_evaluator_identity")

    def test_context_projection_is_order_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = self.fixture_completed_ledger(Path(directory) / "run-a")
            second = self.fixture_completed_ledger(
                Path(directory) / "run-b", include_evaluator=False
            )
            forward = load_completed_lineage_contexts([first, second])
            backward = load_completed_lineage_contexts([second, first])
            self.assertEqual(list(forward), list(backward))
            self.assertEqual(
                [item.ledger_identity for item in forward],
                sorted(item.ledger_identity for item in forward),
            )

    def test_forged_score_provenance_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "forged"
            _run_with_observation(root, "pattern-forged-provenance")
            forged_compiler = _lineage_digest("other-compiler")

            def tamper_evaluation(row):
                if row["event_type"] == "evaluation_completed":
                    payload = row["payload"]
                    payload["after"]["compiler_identity"] = forged_compiler
                    payload["cache_key"] = hash_canonical(
                        {
                            "recipient_id": payload["recipient_id"],
                            "candidate_or_mutation_id": payload["candidate_id"],
                            "evaluator_identity": forged_compiler,
                        }
                    )

            _rewrite_ledger(root / "ledger.jsonl", tamper_evaluation)
            with self.assertRaisesRegex(PatternLedgerCorrupt, "differs from manifest"):
                mine_completed_lineages(
                    root, output_root=Path(directory) / "reports"
                )

    def test_context_records_reject_forged_shapes(self) -> None:
        def context(**overrides):
            values = dict(
                ledger_identity=_lineage_digest("ledger"),
                run_id="lineage-run",
                compiler_identity=_lineage_digest("compiler"),
                config_identity=_lineage_digest("config"),
                schema_identity=_lineage_digest("schema"),
                scorer_algorithms=("difflib",),
                lane_tool_identities=(
                    ("cfg_dataflow", _lineage_digest("tool:cfg_dataflow")),
                ),
                recipient_target_identities=(
                    ("us:ST:fn", _lineage_digest("target:us:ST:fn")),
                ),
                evaluator_identity=_lineage_digest("search-evaluator"),
            )
            values.update(overrides)
            return CompletedLineageContext(**values)

        with self.assertRaises(PatternInputError):
            context(ledger_identity="not-a-hash")
        with self.assertRaises(PatternInputError):
            context(scorer_algorithms=("levenshtein", "difflib"))
        with self.assertRaises(PatternInputError):
            context(
                lane_tool_identities=(
                    ("cfg_dataflow", _lineage_digest("tool-one")),
                    ("cfg_dataflow", _lineage_digest("tool-two")),
                )
            )
        # Malformed shapes fail as typed domain errors, never as raw
        # Python type errors.
        with self.assertRaises(PatternInputError):
            context(scorer_algorithms=None)
        with self.assertRaises(PatternInputError):
            context(lane_tool_identities=None)
        with self.assertRaises(PatternInputError):
            context(recipient_target_identities=None)
        with self.assertRaises(PatternInputError):
            context(lane_tool_identities=(("cfg_dataflow", 5),))
        with self.assertRaises(PatternInputError):
            context(lane_tool_identities=(42,))
        with self.assertRaises(PatternInputError):
            CompletedLineageDiagnostic(
                ledger_identity=_lineage_digest("ledger"),
                run_id="lineage-run",
                reason_code="made_up_reason",
                observed_identities=(_lineage_digest("compiler"),),
            )
        with self.assertRaises(PatternInputError):
            CompletedLineageDiagnostic(
                ledger_identity=_lineage_digest("ledger"),
                run_id="lineage-run",
                reason_code="missing_evaluator_identity",
                observed_identities=None,
            )
        self.assertIsInstance(context(), CompletedLineageContext)

    def test_scorer_algorithm_separates_lineages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = self.fixture_completed_ledger(
                Path(directory) / "dif-a", scorer_algorithm="difflib"
            )
            second = self.fixture_completed_ledger(
                Path(directory) / "dif-b", scorer_algorithm="difflib"
            )
            third = self.fixture_completed_ledger(
                Path(directory) / "lev-a", scorer_algorithm="levenshtein"
            )
            fourth = self.fixture_completed_ledger(
                Path(directory) / "lev-b", scorer_algorithm="levenshtein"
            )
            report = mine_completed_lineages(
                [first, second, third, fourth],
                output_root=Path(directory) / "reports",
            )
            self.assertEqual(len(report.recommendations), 2)
            self.assertEqual(
                {item["scorer_algorithm"] for item in report.recommendations},
                {"difflib", "levenshtein"},
            )

    def test_evaluator_identity_separates_lineages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = self.fixture_completed_ledger(
                Path(directory) / "ev-a",
                evaluator_identity=_lineage_digest("evaluator-a"),
            )
            second = self.fixture_completed_ledger(
                Path(directory) / "ev-b",
                evaluator_identity=_lineage_digest("evaluator-a"),
            )
            third = self.fixture_completed_ledger(
                Path(directory) / "ev-c",
                evaluator_identity=_lineage_digest("evaluator-b"),
            )
            fourth = self.fixture_completed_ledger(
                Path(directory) / "ev-d",
                evaluator_identity=_lineage_digest("evaluator-b"),
            )
            report = mine_completed_lineages(
                [first, second, third, fourth],
                output_root=Path(directory) / "reports",
            )
            self.assertEqual(len(report.recommendations), 2)
            self.assertEqual(
                {item["evaluator_identity"] for item in report.recommendations},
                {_lineage_digest("evaluator-a"), _lineage_digest("evaluator-b")},
            )


if __name__ == "__main__":
    unittest.main()
