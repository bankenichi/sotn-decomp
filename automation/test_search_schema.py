import json
import sys
import unittest
from dataclasses import MISSING, fields, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_types import (
    ArtifactRef,
    ArchiveDecision,
    Budget,
    Checkpoint,
    CandidateRecord,
    EvaluationEvent,
    ExhaustionReceipt,
    GroupedPatch,
    Interruption,
    LedgerEvent,
    MutationEvent,
    OracleReceipt,
    OracleRequest,
    ParentRun,
    PatchHunk,
    RunManifest,
    RunResume,
    RunStop,
    ScoreComponents,
    ScoreDeltas,
    ScoreVector,
    SearchTask,
    SearchValidationError,
    TaskTerminal,
    EVENT_TYPES,
    LANES,
    PAYLOAD_TYPES,
    SCORE_FIELDS,
    TIERS,
    canonical_json,
    canonical_subset_identity,
    hash_bytes,
    hash_canonical,
    oracle_receipt_identity,
    oracle_request_identity,
)


def _hash(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


def score(total: int = 10, *, signature: str = "sig") -> ScoreVector:
    components = ScoreComponents(0, 0, 0, 0, 0)
    return ScoreVector(
        compile_status="success",
        elapsed_ms=1,
        total=total,
        components=components,
        weights=ScoreComponents(1, 5, 60, 100, 100),
        object_hash=_hash("object-" + str(total)),
        mismatch_signature=_hash(signature),
        first_divergence=None,
        target_instruction_count=3,
        candidate_instruction_count=3,
        diagnostic_artifact=None,
        scorer_algorithm="difflib",
        compiler_identity=_hash("compiler"),
    )


def manifest() -> RunManifest:
    return RunManifest(
        run_id="run-schema",
        created_at="2026-08-26T00:00:00Z",
        parent_run=None,
        queue_record_ids=("record-1",),
        function_ids=("record-1",),
        subset_identity=canonical_subset_identity(("record-1",)),
        queue_evidence_identity=_hash("queue-evidence"),
        selected_lanes=LANES,
        source_identity=_hash("source"),
        target_identities={"record-1": _hash("target")},
        compiler_identity=_hash("compiler"),
        tool_identities={
            "tool": _hash("tool"),
            **{lane: _hash("tool-" + lane) for lane in LANES},
        },
        config_identity=_hash("config"),
        schema_identity=_hash("schema"),
        run_seed=7,
        epoch_size=2,
        frontier_cap=8,
        coordinator_budget=Budget("tasks", 64, 0),
        lane_budgets={lane: Budget("attempts", 16, 0) for lane in LANES},
        tier_order=(
            "exact_deterministic",
            "structural_dependency",
            "cheap_generated",
            "compiler_guided",
            "model",
        ),
    )


def artifact(label: str = "artifact") -> ArtifactRef:
    data = label.encode("utf-8")
    digest = hash_bytes(data)
    return ArtifactRef(digest, "artifacts/objects/" + digest[7:] + ".bin", "application/octet-stream", len(data))


def candidate_record() -> CandidateRecord:
    source = artifact("candidate-source")
    return CandidateRecord(
        source.content_hash,
        "record-1",
        source,
        (),
        None,
        "upstream_current",
        0,
        score(0),
        "zero_pending_oracle",
    )


def grouped_patch() -> GroupedPatch:
    base = _hash("base-source")
    hunk = PatchHunk(0, "before\n", "after\n", (), ())
    patch_id = hash_canonical({
        "format": "line_context",
        "base_source_hash": base,
        "atomic": True,
        "hunks": [hunk],
    })
    return GroupedPatch(patch_id, "line_context", base, True, (hunk,))


def all_records():
    parent = ParentRun("parent-run", 0, _hash("parent-event"))
    mutation = MutationEvent(
        _hash("mutation"), _hash("parent-candidate"), "record-1", "upstream_current",
        "pass", 3, grouped_patch(), (), "applied", _hash("result-source"),
    )
    task = SearchTask(
        _hash("task"), "record-1", "upstream_current", "exact_deterministic", "discover", (),
        0, 11, manifest().config_identity, "scheduled",
    )
    candidate = candidate_record()
    evaluation = EvaluationEvent(
        task.task_id, "record-1", candidate.candidate_id, None, None, score(0),
        ScoreDeltas(0, 0, 0, 0, 0, 0),
        hash_canonical({"recipient_id": "record-1", "candidate_or_mutation_id": candidate.candidate_id,
                       "evaluator_identity": score(0).compiler_identity}),
        "zero_pending_oracle",
    )
    decision = ArchiveDecision(
        candidate.candidate_id, "record-1", "retain_both", candidate.candidate_id,
        (candidate.candidate_id,), "score zero pending oracle",
    )
    terminal = TaskTerminal(task.task_id, "completed", (artifact(),), "done")
    interruption = Interruption(task.task_id, "worker stopped", True)
    checkpoint = Checkpoint(0, _hash("event"), artifact("checkpoint"))
    budget = Budget("tasks", 2, 1)
    receipt_identity = {
        "recipient_id": "record-1", "lane": "upstream_current", "tier": "exact_deterministic",
        "tool_identities": {"upstream_current": manifest().tool_identities["upstream_current"]}, "config_identity": manifest().config_identity,
        "input_identities": [manifest().source_identity], "budget": budget.to_dict(), "attempts": 1,
        "rejection_counts": {"none": 0}, "best_candidate_ids": [candidate.candidate_id], "complete": True,
        "completion_reason": "matched_pending_oracle",
    }
    receipt_id = hash_canonical(receipt_identity)
    receipt = ExhaustionReceipt(
        receipt_id, "record-1", "upstream_current", "exact_deterministic",
        {"upstream_current": manifest().tool_identities["upstream_current"]},
        manifest().config_identity, (manifest().source_identity,), budget, 1, {"none": 0},
        (candidate.candidate_id,), True, "matched_pending_oracle", artifact("receipt"),
    )
    oracle_identity = _hash("oracle")
    request_id = oracle_request_identity(
        task_id=task.task_id,
        recipient_id=task.recipient_id,
        candidate_id=candidate.candidate_id,
        source_hash=candidate.source_artifact.content_hash,
        config_identity=manifest().config_identity,
        oracle_identity=oracle_identity,
    )
    oracle_request = OracleRequest(
        request_id,
        task.task_id,
        task.recipient_id,
        candidate.candidate_id,
        candidate.source_artifact.content_hash,
        candidate,
        manifest().config_identity,
        oracle_identity,
        artifact("oracle-request"),
    )
    oracle_result = {"matched": True, "candidate_id": candidate.candidate_id}
    oracle_receipt = OracleReceipt(
        oracle_receipt_identity(
            request_id=request_id,
            oracle_identity=oracle_identity,
            outcome="matched",
            result=oracle_result,
        ),
        request_id,
        oracle_identity,
        "matched",
        oracle_result,
        artifact("oracle-result"),
    )
    stop = RunStop("graceful_stop", task.task_id, (task.task_id,), _hash("budget"), True)
    resume = RunResume(
        "run-schema:stopped:1",
        _hash("stop-event"),
        None,
    )
    event_data = {
        "schema_version": "1.0.0",
        "sequence": 0,
        "event_id": "run-schema:all-records",
        "previous_event_hash": None,
        "recorded_at": "2026-08-26T00:00:00Z",
        "run_id": manifest().run_id,
        "event_type": "run_started",
        "payload": manifest().to_dict(),
    }
    event_data["event_hash"] = hash_canonical(event_data)
    ledger_event = LedgerEvent.from_dict(event_data)
    return [
        artifact(), ScoreComponents(0, 0, 0, 0, 0), score(0), PatchHunk(0, "before\n", "after\n", (), ()),
        grouped_patch(), mutation, parent, manifest(), task, candidate, ScoreDeltas(0, 0, 0, 0, 0, 0),
        evaluation, decision, oracle_request, oracle_receipt, terminal, interruption,
        checkpoint, budget, receipt, stop, resume, ledger_event,
    ]


class TestSearchSchema(unittest.TestCase):
    def test_manifest_task_and_score_round_trip(self) -> None:
        task = SearchTask(
            task_id=_hash("task"),
            recipient_id="record-1",
            lane="permuter_random",
            tier="compiler_guided",
            operation="random-pass",
            parent_candidate_ids=(),
            budget_ordinal=0,
            task_seed=11,
            config_identity=manifest().config_identity,
            state="scheduled",
        )
        self.assertEqual(RunManifest.from_dict(manifest().to_dict()), manifest())
        self.assertEqual(SearchTask.from_json(task.to_json()), task)
        self.assertEqual(ScoreVector.from_dict(score().to_dict()), score())

    def test_manifest_empty_subset_and_duplicate_function_shape_are_explicit(self) -> None:
        base = manifest()
        empty = replace(
            base,
            queue_record_ids=(),
            function_ids=(),
            subset_identity=canonical_subset_identity(()),
            queue_evidence_identity=_hash("queue-evidence-empty"),
            selected_lanes=("upstream_current", "mipsmatch_exact"),
            target_identities={},
            lane_budgets={
                lane: base.lane_budgets[lane]
                for lane in ("upstream_current", "mipsmatch_exact")
            },
        )
        self.assertEqual(RunManifest.from_dict(empty.to_dict()), empty)
        self.assertEqual(empty.to_json(), RunManifest.from_json(empty.to_json()).to_json())

        two_records = replace(
            base,
            queue_record_ids=("record-1", "record-2"),
            function_ids=("func_shared",),
            subset_identity=canonical_subset_identity(("record-1", "record-2")),
            queue_evidence_identity=_hash("queue-evidence-two"),
            target_identities={
                "record-1": _hash("target-one"),
                "record-2": _hash("target-two"),
            },
        )
        self.assertEqual(two_records.function_ids, ("func_shared",))
        self.assertEqual(len(two_records.queue_record_ids), 2)
        reversed_records = replace(
            two_records,
            queue_record_ids=("record-2", "record-1"),
        )
        self.assertEqual(reversed_records, two_records)

        with self.assertRaises(SearchValidationError):
            replace(base, queue_record_ids=(), function_ids=("record-1",), target_identities={})
        with self.assertRaises(SearchValidationError):
            replace(base, queue_record_ids=("record-1",), function_ids=("record-1",), selected_lanes=())
        with self.assertRaises(SearchValidationError):
            replace(base, queue_record_ids=("record-1",), function_ids=("record-1",), target_identities={})

    def test_subset_identity_helper_is_canonical_and_selection_only(self) -> None:
        self.assertEqual(
            canonical_subset_identity(("record-2", "record-1")),
            canonical_subset_identity(("record-1", "record-2")),
        )
        payload = {
            "artifact_type": "sotn-search-subset",
            "record_ids": ["record-1", "record-2"],
            "schema_version": "1.0.0",
        }
        self.assertEqual(
            canonical_subset_identity(("record-2", "record-1")),
            hash_canonical(payload),
        )

    def test_manifest_lane_tools_are_required_for_selected_lanes(self) -> None:
        value = manifest().to_dict()
        value["tool_identities"].pop("upstream_current")
        with self.assertRaises(SearchValidationError):
            RunManifest.from_dict(value)

    def test_manifest_lane_budgets_are_typed_and_exactly_selected(self) -> None:
        value = manifest().to_dict()
        value["lane_budgets"].pop("upstream_current")
        with self.assertRaises(SearchValidationError):
            RunManifest.from_dict(value)

        value = manifest().to_dict()
        value["lane_budgets"]["upstream_current"] = {
            "unit": "not-a-budget",
            "limit": 1,
            "consumed": 0,
        }
        with self.assertRaises(SearchValidationError):
            RunManifest.from_dict(value)

        value = manifest().to_dict()
        value["lane_budgets"]["shared_header"]["consumed"] = 1
        with self.assertRaises(SearchValidationError):
            RunManifest.from_dict(value)

        value = manifest().to_dict()
        value["subset_identity"] = _hash("different-subset")
        with self.assertRaises(SearchValidationError):
            RunManifest.from_dict(value)

        value = manifest().to_dict()
        value["queue_evidence_identity"] = "not-a-content-hash"
        with self.assertRaises(SearchValidationError):
            RunManifest.from_dict(value)

    def test_unknown_fields_and_bad_values_are_rejected(self) -> None:
        value = manifest().to_dict()
        value["unexpected"] = True
        with self.assertRaises(SearchValidationError):
            RunManifest.from_dict(value)
        components = ScoreComponents(0, 0, 0, 0, 0).to_dict()
        components["stack"] = -1
        with self.assertRaises(SearchValidationError):
            ScoreComponents.from_dict(components)
        with self.assertRaises(SearchValidationError):
            ArtifactRef(_hash("x"), "../escape", "text/plain", 1)

    def test_failed_score_does_not_fake_zero(self) -> None:
        failed = ScoreVector(
            compile_status="failed",
            elapsed_ms=4,
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
            compiler_identity=_hash("compiler"),
        )
        self.assertIsNone(failed.total)
        with self.assertRaises(SearchValidationError):
            ScoreVector.from_dict(dict(failed.to_dict(), total=0))

    def test_event_variant_payload_and_canonical_hash(self) -> None:
        m = manifest()
        event_data = {
            "schema_version": "1.0.0",
            "sequence": 0,
            "event_id": "run-schema:start",
            "previous_event_hash": None,
            "recorded_at": "2026-08-26T00:00:00Z",
            "run_id": m.run_id,
            "event_type": "run_started",
            "payload": m.to_dict(),
        }
        event_data["event_hash"] = hash_canonical(event_data)
        event = LedgerEvent.from_dict(event_data)
        self.assertEqual(event.calculated_hash(), event.event_hash)
        self.assertEqual(LedgerEvent.from_json(event.to_json()), event)
        self.assertEqual(canonical_json({"b": 1, "a": 2}), '{"a":2,"b":1}')

    def test_every_record_round_trips(self) -> None:
        for record in all_records():
            restored = type(record).from_dict(record.to_dict())
            self.assertEqual(restored, record, type(record).__name__)

    def test_schema_required_fields_and_enums_match_types(self) -> None:
        schema_path = Path(__file__).resolve().parent / "search-ledger.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        defs = schema["$defs"]
        self.assertEqual(tuple(defs["lane"]["enum"]), LANES)
        self.assertEqual(tuple(defs["search_task"]["properties"]["tier"]["enum"]), TIERS)
        self.assertEqual(tuple(defs["score_components"]["properties"]), SCORE_FIELDS)
        event_types = tuple(
            item["allOf"][1]["properties"]["event_type"]["const"]
            for item in schema["oneOf"]
        )
        self.assertEqual(event_types, EVENT_TYPES)
        for event_type in EVENT_TYPES:
            record_type = PAYLOAD_TYPES[event_type]
            name = {
                "run_started": "run_manifest", "task_scheduled": "search_task", "task_started": "search_task",
                "mutation_materialized": "mutation_event", "candidate_materialized": "candidate_record",
                "evaluation_completed": "evaluation_event", "archive_decided": "archive_decision",
                "oracle_requested": "oracle_request", "oracle_result_recorded": "oracle_receipt",
                "task_completed": "task_terminal", "task_interrupted": "interruption",
                "checkpoint_committed": "checkpoint", "exhaustion_recorded": "exhaustion_receipt",
                "run_stopped": "run_stop", "run_resumed": "run_resume",
            }[event_type]
            required = set(defs[name]["required"])
            self.assertEqual(
                required,
                {
                    field.name
                    for field in fields(record_type)
                    if field.default is MISSING and field.default_factory is MISSING
                },
                name,
            )
        self.assertEqual(
            set(defs["artifact_ref"]["required"]),
            {field.name for field in fields(ArtifactRef)},
        )
        self.assertEqual(
            set(defs["budget"]["required"]) if "budget" in defs else {"unit", "limit", "consumed"},
            {field.name for field in fields(Budget)},
        )

    def test_candidate_identity_is_source_content_hash(self) -> None:
        source = artifact("identity-source")
        with self.assertRaises(SearchValidationError):
            CandidateRecord(
                _hash("different-id"), "record-1", source, (), None, "upstream_current", 0,
                None, "materialized",
            )


if __name__ == "__main__":
    unittest.main()
