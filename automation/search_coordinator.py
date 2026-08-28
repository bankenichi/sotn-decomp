"""Deterministic coordinator for bounded, recoverable search tasks."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple, Union

from .search_archive import ArchiveError, ArtifactCorrupt, ArtifactMissing, ContentAddressedArchive
from .search_frontier import SearchFrontier, frontier_from_events
from .search_ledger import AppendOnlyLedger, LedgerError
from .search_patterns import (
    PatternArtifactError,
    PatternIdentityMismatch,
    PatternInputError,
    SearchPatternReport,
    load_report_artifact,
)
from .search_types import (
    ArchiveDecision,
    ArtifactRef,
    Budget,
    CandidateRecord,
    ExhaustionReceipt,
    EvaluationEvent,
    GroupedPatch,
    Interruption,
    LedgerEvent,
    MutationEvent,
    OracleReceipt,
    OracleRequest,
    ParentRun,
    RunManifest,
    RunStop,
    ScoreVector,
    SearchTask,
    TaskTerminal,
    TIER_ORDER,
    TIERS,
    LANE_TOOL_KEYS,
    event_payload,
    canonical_bytes,
    hash_canonical,
    iter_artifact_refs,
    oracle_receipt_identity,
    oracle_request_identity,
    validate_hash,
)


class CoordinatorError(RuntimeError):
    """Base class for coordinator failures."""


class TierBlocked(CoordinatorError):
    """A cheaper tier has not emitted a terminal receipt yet."""


class BudgetExhausted(CoordinatorError):
    """No logical run-global task ordinal remains."""


class ExplicitSubsetError(CoordinatorError):
    """The task recipient is outside the immutable manifest subset."""


class OracleRequired(CoordinatorError):
    """A score-zero candidate was supplied without an oracle policy."""


LANE_TIERS: Dict[str, str] = {
    "upstream_current": "exact_deterministic",
    "upstream_pinned": "exact_deterministic",
    "upstream_open_pr": "exact_deterministic",
    "mipsmatch_exact": "exact_deterministic",
    "preserved_candidate": "exact_deterministic",
    "shared_header": "structural_dependency",
    "transplant": "structural_dependency",
    "whole_tu": "structural_dependency",
    "dependency_closure": "structural_dependency",
    "multi_donor": "structural_dependency",
    "cfg_dataflow": "structural_dependency",
    "m2c_ensemble": "cheap_generated",
    "idiom_atlas": "cheap_generated",
    "bounded_synthesis": "cheap_generated",
    "permuter_random": "compiler_guided",
    "permuter_targeted": "compiler_guided",
    "permuter_recombine": "compiler_guided",
    "permuter_ddmin": "compiler_guided",
    "model_fleet": "model",
    "model_expensive": "model",
}

LANES_BY_TIER: Dict[str, Tuple[str, ...]] = {
    tier: tuple(lane for lane, lane_tier in LANE_TIERS.items() if lane_tier == tier)
    for tier in TIERS
}


# Durable full-build oracle identity is a reserved manifest tool entry. It is
# checked before filesystem initialization so a rejected oracle cannot create or
# alter a run.
FULL_ORACLE_TOOL_IDENTITY = "full_oracle"

# The manifest has no mutable policy extension.  A prior report is therefore
# bound as a reserved tool identity, alongside the full-oracle identity.  The
# value is the report artifact hash, never a path or an in-memory policy.
SEARCH_PATTERN_REPORT_TOOL_IDENTITY = "search_pattern_report"


# Semantic transition points are intentionally named here so a recovery
# test can exercise every coordinator-owned durable boundary. The lower-level
# archive and ledger hooks remain available as well.
DURABLE_FAULT_POINTS: Tuple[str, ...] = (
    "before_manifest_publish",
    "after_manifest_publish",
    "before_manifest_event",
    "after_manifest_event",
    "before_task_scheduled",
    "after_task_scheduled",
    "before_task_started",
    "after_task_started",
    "before_mutation_artifact",
    "after_mutation_artifact",
    "before_mutation_event",
    "after_mutation_event",
    "before_source_artifact",
    "after_source_artifact",
    "before_candidate_event",
    "after_candidate_event",
    "before_evaluation_event",
    "after_evaluation_event",
    "before_archive_event",
    "after_archive_event",
    "before_oracle_request",
    "after_oracle_request",
    "before_oracle_request_artifact",
    "after_oracle_request_artifact",
    "before_oracle_request_event",
    "after_oracle_request_event",
    "before_oracle_execution",
    "after_oracle_execution",
    "before_oracle_result",
    "after_oracle_result",
    "before_oracle_result_artifact",
    "after_oracle_result_artifact",
    "before_oracle_result_event",
    "after_oracle_result_event",
    "before_task_terminal",
    "after_task_terminal",
    "before_checkpoint_publish",
    "after_checkpoint_publish",
    "before_checkpoint_event",
    "after_checkpoint_event",
    "before_exhaustion_artifact",
    "after_exhaustion_artifact",
    "before_exhaustion_event",
    "after_exhaustion_event",
    "before_run_stop",
    "after_run_stop",
    "before_run_stop_snapshot",
    "after_run_stop_snapshot",
    "before_run_stop_event",
    "after_run_stop_event",
    # Existing low-level aliases remain named so the same matrix can cover
    # failures inside the archive, ledger and epoch wrappers.
    "before_artifact_write",
    "after_artifact_write",
    "before_artifact_rename",
    "after_artifact_rename",
    "before_ledger_append",
    "after_ledger_write",
    "after_ledger_append",
    "before_epoch_commit",
    "after_epoch_commit",
    "before_checkpoint_write",
    "after_checkpoint_write",
    "before_graceful_stop",
    "after_graceful_stop",
)
# Oracle handoff points are kept as a named subset for the replay-window matrix.
ORACLE_FAULT_POINTS: Tuple[str, ...] = (
    "before_oracle_request",
    "after_oracle_request",
    "before_oracle_request_artifact",
    "after_oracle_request_artifact",
    "before_oracle_request_event",
    "after_oracle_request_event",
    "before_oracle_execution",
    "after_oracle_execution",
    "before_oracle_result",
    "after_oracle_result",
    "before_oracle_result_artifact",
    "after_oracle_result_artifact",
    "before_oracle_result_event",
    "after_oracle_result_event",
    "before_task_terminal",
    "after_task_terminal",
)

# Alias kept short for callers that only need to enumerate supported points.
FAULT_POINTS = DURABLE_FAULT_POINTS


@dataclass(frozen=True)
class TaskResult:
    """Immutable worker output.  Workers do not receive coordinator state."""

    task_id: str
    mutation: Optional[MutationEvent] = None
    candidate: Optional[CandidateRecord] = None
    source: Optional[str] = None
    evaluation: Optional[EvaluationEvent] = None
    archive_decision: Optional[ArchiveDecision] = None
    result_artifacts: Tuple[ArtifactRef, ...] = ()
    state: str = "completed"
    reason: str = "worker completed"

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id:
            raise CoordinatorError("task result needs a task id")
        object.__setattr__(
            self,
            "result_artifacts",
            tuple(
                item if isinstance(item, ArtifactRef) else ArtifactRef.from_dict(item)  # type: ignore[arg-type]
                for item in self.result_artifacts
            ),
        )
        if self.state not in ("completed", "rejected"):
            raise CoordinatorError("task result state must be completed or rejected")
        if not isinstance(self.reason, str) or not self.reason:
            raise CoordinatorError("task result reason must be nonempty")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TaskResult":
        data = dict(value)
        if data.get("mutation") is not None:
            data["mutation"] = MutationEvent.from_dict(data["mutation"])
        if data.get("candidate") is not None:
            data["candidate"] = CandidateRecord.from_dict(data["candidate"])
        if data.get("evaluation") is not None:
            data["evaluation"] = EvaluationEvent.from_dict(data["evaluation"])
        if data.get("archive_decision") is not None:
            data["archive_decision"] = ArchiveDecision.from_dict(data["archive_decision"])
        return cls(**data)


Worker = Callable[[SearchTask], TaskResult]


class DurableOracle(Protocol):
    """Restart-safe oracle boundary keyed by the durable request identity.

    ``execute`` must persist its result under ``request.request_id`` before
    returning. ``lookup`` must return that same result on every later retry.
    """

    identity: str

    def lookup(self, request_id: str) -> Optional[Any]:
        ...

    def execute(self, request: OracleRequest) -> Any:
        ...


Oracle = Union[DurableOracle, Callable[[CandidateRecord], Any]]
FaultHook = Callable[[str], None]


def _task_identity(
    run_id: str,
    recipient_id: str,
    lane: str,
    tier: str,
    operation: str,
    parent_candidate_ids: Sequence[str],
    budget_ordinal: int,
    config_identity: str,
) -> str:
    return hash_canonical(
        {
            "run_id": run_id,
            "recipient_id": recipient_id,
            "lane": lane,
            "tier": tier,
            "operation": operation,
            "parent_candidate_ids": list(parent_candidate_ids),
            "budget_ordinal": budget_ordinal,
            "config_identity": config_identity,
        }
    )


def _task_seed(run_seed: int, task_id: str) -> int:
    return int(hash_canonical({"run_seed": run_seed, "task_id": task_id})[7:23], 16)


def _validate_task_binding(manifest: RunManifest, task: SearchTask) -> None:
    """Validate every task identity against the immutable run manifest."""
    if not isinstance(manifest, RunManifest):
        raise CoordinatorError("task binding requires a typed RunManifest")
    if not isinstance(task, SearchTask):
        raise CoordinatorError("task binding requires a typed SearchTask")
    if task.recipient_id not in manifest.queue_record_ids:
        raise CoordinatorError("task recipient is outside the manifest subset")
    expected_tier = LANE_TIERS.get(task.lane)
    if expected_tier is None:
        raise CoordinatorError("task lane has no tier mapping")
    if task.lane not in manifest.selected_lanes:
        raise CoordinatorError("task lane is not selected by the immutable manifest")
    if task.tier != expected_tier:
        raise CoordinatorError("task lane and tier do not agree")
    if task.config_identity != manifest.config_identity:
        raise CoordinatorError("task config differs from manifest")
    if task.budget_ordinal >= manifest.coordinator_budget.limit:
        raise BudgetExhausted("budget ordinal exceeds immutable manifest limit")
    expected_task_id = _task_identity(
        manifest.run_id,
        task.recipient_id,
        task.lane,
        task.tier,
        task.operation,
        task.parent_candidate_ids,
        task.budget_ordinal,
        manifest.config_identity,
    )
    if task.task_id != expected_task_id:
        raise CoordinatorError("task_id does not match its immutable task fields")
    expected_seed = _task_seed(manifest.run_seed, expected_task_id)
    if task.task_seed != expected_seed:
        raise CoordinatorError("task_seed does not match its immutable task identity")


# Public alias used by recovery so task binding has one implementation.
validate_task_binding = _validate_task_binding


def _event_task_id(event_id: str, marker: str) -> str:
    """Extract the task identity from a task-scoped materialization event."""
    token = ":" + marker + ":"
    prefix, separator, task_id = event_id.partition(token)
    if not separator or not prefix or not task_id:
        raise CoordinatorError("ledger event id does not carry its task identity")
    return task_id


def _verify_bound_artifact(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    expected: Any,
    label: str,
) -> None:
    """Verify both the archive reference and the bytes bound by its record."""
    try:
        actual = archive.verify(reference)
    except ArchiveError as exc:
        raise CoordinatorError(label + " artifact is missing, corrupt, or outside the run") from exc
    if actual != canonical_bytes(expected):
        raise CoordinatorError(label + " artifact bytes differ from its durable record")


def validate_ledger_prefix(
    manifest: RunManifest,
    events: Sequence[LedgerEvent],
    *,
    archive: Optional[ContentAddressedArchive] = None,
    verify_artifacts: bool = True,
) -> None:
    """Validate replay ordering and cross-record bindings before restoration.

    ``LedgerEvent`` validates each record in isolation.  This pass validates
    the relationships that only exist across the prefix: task lifecycle and
    global ordinals, candidate/mutation ancestry, and the artifact-backed
    oracle and exhaustion handoffs.  Recovery and coordinator reopen both call
    this function before rebuilding mutable indexes.
    """
    if not isinstance(manifest, RunManifest):
        raise CoordinatorError("ledger prefix requires a typed RunManifest")
    if not events:
        raise CoordinatorError("ledger prefix is empty")
    first = events[0]
    if first.event_type != "run_started" or first.payload != manifest:
        raise CoordinatorError("ledger prefix does not start with the immutable manifest")

    tasks: Dict[str, SearchTask] = {}
    started = set()
    interrupted = set()
    terminal: Dict[str, TaskTerminal] = {}
    budget_claims: Dict[int, str] = {}
    mutations: Dict[str, MutationEvent] = {}
    mutation_tasks: Dict[str, str] = {}
    candidates: Dict[Tuple[str, str], CandidateRecord] = {}
    evaluations: Dict[Tuple[str, str], EvaluationEvent] = {}
    archive_decisions: Dict[Tuple[str, str], ArchiveDecision] = {}
    oracle_requests: Dict[str, OracleRequest] = {}
    oracle_results: Dict[str, OracleReceipt] = {}
    receipts: Dict[Tuple[str, str], ExhaustionReceipt] = {}
    stopped: Optional[RunStop] = None

    def require_active_task(task_id: str, label: str) -> SearchTask:
        task = tasks.get(task_id)
        if task is None:
            raise CoordinatorError(label + " names an unknown task")
        if task_id in terminal:
            raise CoordinatorError(label + " follows a terminal task")
        return task

    def allow_after_stop(task_id: Optional[str], label: str) -> None:
        """Allow only completion of a task named by a resumable stop."""
        if stopped is None:
            return
        if not stopped.resumable:
            raise CoordinatorError(label + " follows a non-resumable run stop")
        if task_id is None or task_id not in stopped.pending_task_ids:
            raise CoordinatorError(label + " is outside the resumable stop boundary")

    for event in events:
        if verify_artifacts and archive is not None and event.event_type != "checkpoint_committed":
            for reference in iter_artifact_refs(event.payload):
                try:
                    archive.verify(reference)
                except ArchiveError as exc:
                    raise CoordinatorError(
                        "ledger references a missing, corrupt, or escaped artifact: " + reference.path
                    ) from exc

        if event.event_type == "run_started":
            if event is not first:
                raise CoordinatorError("run_started appears more than once")
            if event.event_id != f"{manifest.run_id}:run_started":
                raise CoordinatorError("run_started event id differs from the run manifest")
            continue

        if event.event_type in ("task_scheduled", "task_started"):
            task = event.payload
            assert isinstance(task, SearchTask)
            validate_task_binding(manifest, task)
            if event.event_type == "task_scheduled" and task.state != "scheduled":
                raise CoordinatorError("task_scheduled payload must be scheduled")
            if event.event_type == "task_started" and task.state != "started":
                raise CoordinatorError("task_started payload must be started")
            expected_event_id = f"{task.task_id}:{'scheduled' if event.event_type == 'task_scheduled' else 'started'}"
            if event.event_id != expected_event_id:
                raise CoordinatorError("task lifecycle event id differs from its task")
            if event.event_type == "task_scheduled" and stopped is not None:
                raise CoordinatorError("task scheduling follows a run stop")
            allow_after_stop(task.task_id, "task start")
            prior_budget_task = budget_claims.get(task.budget_ordinal)
            if prior_budget_task is not None and prior_budget_task != task.task_id:
                raise CoordinatorError("ledger reuses a global budget ordinal for different tasks")
            budget_claims[task.budget_ordinal] = task.task_id
            if event.event_type == "task_scheduled":
                if task.task_id in tasks:
                    raise CoordinatorError("task was scheduled more than once")
                if task.task_id in terminal:
                    raise CoordinatorError("task was scheduled after completion")
                tasks[task.task_id] = task
            else:
                existing = tasks.get(task.task_id)
                if existing is None:
                    raise CoordinatorError("task started before it was scheduled")
                if task.task_id in started:
                    raise CoordinatorError("task was started more than once")
                if replace(existing, state="scheduled") != replace(task, state="scheduled"):
                    raise CoordinatorError("task identity changed between schedule and start")
                tasks[task.task_id] = task
                started.add(task.task_id)
            continue

        if event.event_type == "task_interrupted":
            interruption = event.payload
            assert isinstance(interruption, Interruption)
            if interruption.task_id not in tasks:
                raise CoordinatorError("interruption names an unknown task")
            if interruption.task_id not in started:
                raise CoordinatorError("interruption precedes task start")
            if interruption.task_id in terminal:
                raise CoordinatorError("interruption follows a terminal task")
            if interruption.task_id in interrupted:
                raise CoordinatorError("task was interrupted more than once")
            allow_after_stop(interruption.task_id, "task interruption")
            interrupted.add(interruption.task_id)
            continue

        if event.event_type == "task_completed":
            completed = event.payload
            assert isinstance(completed, TaskTerminal)
            if completed.state not in ("completed", "rejected"):
                raise CoordinatorError("task_completed payload has an invalid terminal state")
            if completed.task_id not in tasks:
                raise CoordinatorError("terminal result names an unknown task")
            if completed.task_id not in started:
                raise CoordinatorError("terminal result precedes task start")
            allow_after_stop(completed.task_id, "task completion")
            existing = terminal.get(completed.task_id)
            if existing is not None:
                raise CoordinatorError("task has duplicate terminal results")
            if event.event_id != f"{completed.task_id}:completed":
                raise CoordinatorError("terminal event id differs from its task")
            terminal[completed.task_id] = completed
            continue

        if event.event_type == "run_stopped":
            candidate_stop = event.payload
            assert isinstance(candidate_stop, RunStop)
            if event.event_id != f"{manifest.run_id}:stopped:{event.sequence}":
                raise CoordinatorError("run stop event id differs from its sequence")
            if stopped is not None:
                raise CoordinatorError("run has multiple stop records")
            pending = set(candidate_stop.pending_task_ids)
            known = set(tasks)
            incomplete = known.difference(terminal)
            if pending != incomplete:
                raise CoordinatorError("run stop pending tasks differ from the ledger")
            if candidate_stop.last_committed_task_id is not None:
                if candidate_stop.last_committed_task_id not in terminal:
                    raise CoordinatorError("run stop names an uncompleted last task")
            stopped = candidate_stop
            continue

        if event.event_type == "mutation_materialized":
            mutation = event.payload
            assert isinstance(mutation, MutationEvent)
            prefix, separator, task_id = event.event_id.rpartition(":materialized:")
            if not separator or prefix != mutation.mutation_id or not task_id:
                raise CoordinatorError("mutation event id is not bound to its mutation and task")
            task = require_active_task(task_id, "mutation")
            if task_id not in started:
                raise CoordinatorError("mutation materialization precedes task start")
            allow_after_stop(task_id, "mutation materialization")
            if task.recipient_id != mutation.recipient_id or task.lane != mutation.lane:
                raise CoordinatorError("mutation lane or recipient differs from task")
            existing = mutations.get(mutation.mutation_id)
            if existing is not None and existing != mutation:
                raise CoordinatorError("mutation identity maps to different payload")
            existing_task = mutation_tasks.get(mutation.mutation_id)
            if existing_task is not None and existing_task != task_id:
                raise CoordinatorError("mutation identity is reused by different tasks")
            mutations[mutation.mutation_id] = mutation
            mutation_tasks[mutation.mutation_id] = task_id
            continue

        if event.event_type == "candidate_materialized":
            candidate = event.payload
            assert isinstance(candidate, CandidateRecord)
            task_id = _event_task_id(event.event_id, "materialized")
            if event.event_id != f"{candidate.candidate_id}:materialized:{task_id}":
                raise CoordinatorError("candidate event id differs from its candidate and task")
            task = require_active_task(task_id, "candidate")
            if task_id not in started:
                raise CoordinatorError("candidate materialization precedes task start")
            allow_after_stop(task_id, "candidate materialization")
            if candidate.recipient_id != task.recipient_id or candidate.lane != task.lane:
                raise CoordinatorError("candidate lane or recipient differs from task")
            parents = set(candidate.parent_candidate_ids)
            task_parents = set(task.parent_candidate_ids)
            if candidate.mutation_id is None:
                if not parents.issubset(task_parents):
                    raise CoordinatorError("candidate ancestry is outside task parent candidates")
            else:
                mutation = mutations.get(candidate.mutation_id)
                if mutation is None:
                    raise CoordinatorError("candidate names an unknown mutation")
                if mutation_tasks.get(candidate.mutation_id) != task_id:
                    raise CoordinatorError("candidate mutation is bound to a different task")
                if mutation.replay_status != "applied":
                    raise CoordinatorError("candidate names a non-applied mutation")
                if mutation.recipient_id != task.recipient_id or mutation.lane != task.lane:
                    raise CoordinatorError("candidate mutation lane or recipient differs from task")
                expected_parents = {mutation.parent_candidate_id}
                expected_parents.update(mutation.donor_candidate_ids)
                if not expected_parents.issubset(task_parents):
                    raise CoordinatorError("mutation ancestry is outside task parent candidates")
                if parents != expected_parents:
                    raise CoordinatorError("candidate ancestry differs from mutation parents")
                if mutation.result_source_hash != candidate.source_artifact.content_hash:
                    raise CoordinatorError("candidate source differs from mutation result")
            key = (task_id, candidate.candidate_id)
            existing = candidates.get(key)
            if existing is not None and existing != candidate:
                raise CoordinatorError("candidate identity maps to different payload")
            candidates[key] = candidate
            continue

        if event.event_type == "evaluation_completed":
            evaluation = event.payload
            assert isinstance(evaluation, EvaluationEvent)
            if event.event_id != f"{evaluation.task_id}:evaluation":
                raise CoordinatorError("evaluation event id differs from its task")
            task = require_active_task(evaluation.task_id, "evaluation")
            if evaluation.task_id not in started:
                raise CoordinatorError("evaluation precedes task start")
            allow_after_stop(evaluation.task_id, "evaluation")
            candidate = candidates.get((evaluation.task_id, evaluation.candidate_id))
            if candidate is None:
                raise CoordinatorError("evaluation names an unmaterialized candidate")
            if evaluation.recipient_id != task.recipient_id or evaluation.recipient_id != candidate.recipient_id:
                raise CoordinatorError("evaluation recipient differs from task or candidate")
            if evaluation.after.compiler_identity != manifest.compiler_identity:
                raise CoordinatorError("evaluation compiler identity differs from manifest")
            expected_cache_key = hash_canonical(
                {
                    "recipient_id": evaluation.recipient_id,
                    "candidate_or_mutation_id": evaluation.candidate_id,
                    "evaluator_identity": evaluation.after.compiler_identity,
                }
            )
            if evaluation.cache_key != expected_cache_key:
                raise CoordinatorError("evaluation cache key is not recipient local")
            if candidate.evaluation is not None and candidate.evaluation != evaluation.after:
                raise CoordinatorError("candidate and evaluation vectors differ")
            key = (evaluation.task_id, evaluation.candidate_id)
            existing = evaluations.get(key)
            if existing is not None and existing != evaluation:
                raise CoordinatorError("evaluation identity maps to different payload")
            evaluations[key] = evaluation
            continue

        if event.event_type == "archive_decided":
            decision = event.payload
            assert isinstance(decision, ArchiveDecision)
            task_id = _event_task_id(event.event_id, "archive")
            if event.event_id != f"{decision.candidate_id}:archive:{task_id}":
                raise CoordinatorError("archive event id differs from its candidate and task")
            require_active_task(task_id, "archive decision")
            allow_after_stop(task_id, "archive decision")
            candidate = candidates.get((task_id, decision.candidate_id))
            if candidate is None:
                raise CoordinatorError("archive decision names an unmaterialized candidate")
            if decision.recipient_id != candidate.recipient_id:
                raise CoordinatorError("archive decision recipient differs from candidate")
            key = (task_id, decision.candidate_id)
            existing = archive_decisions.get(key)
            if existing is not None and existing != decision:
                raise CoordinatorError("archive decision identity maps to different payload")
            archive_decisions[key] = decision
            continue

        if event.event_type == "oracle_requested":
            request = event.payload
            assert isinstance(request, OracleRequest)
            task = require_active_task(request.task_id, "oracle request")
            if request.task_id not in started:
                raise CoordinatorError("oracle request precedes task start")
            if event.event_id != f"{request.request_id}:requested":
                raise CoordinatorError("oracle request event id differs from its request")
            allow_after_stop(request.task_id, "oracle request")
            candidate = candidates.get((request.task_id, request.candidate_id))
            if candidate is None:
                raise CoordinatorError("oracle request names an unmaterialized candidate")
            if request.recipient_id != task.recipient_id or request.recipient_id != candidate.recipient_id:
                raise CoordinatorError("oracle request recipient differs from task or candidate")
            if request.candidate != candidate or request.source_hash != candidate.source_artifact.content_hash:
                raise CoordinatorError("oracle request candidate differs from its task materialization")
            if request.config_identity != manifest.config_identity:
                raise CoordinatorError("oracle request config differs from manifest")
            expected_oracle = manifest.tool_identities.get(FULL_ORACLE_TOOL_IDENTITY)
            if expected_oracle is None or request.oracle_identity != expected_oracle:
                raise CoordinatorError("oracle request identity differs from manifest full_oracle binding")
            request_payload = request.to_dict()
            request_payload.pop("request_artifact")
            if archive is None:
                raise CoordinatorError("oracle request artifact cannot be verified without an archive")
            _verify_bound_artifact(archive, request.request_artifact, request_payload, "oracle request")
            existing = oracle_requests.get(request.request_id)
            if existing is not None and existing != request:
                raise CoordinatorError("oracle request identity maps to different payload")
            oracle_requests[request.request_id] = request
            continue

        if event.event_type == "oracle_result_recorded":
            receipt = event.payload
            assert isinstance(receipt, OracleReceipt)
            request = oracle_requests.get(receipt.request_id)
            if request is None:
                raise CoordinatorError("oracle result has no durable request")
            if event.event_id != f"{receipt.request_id}:result":
                raise CoordinatorError("oracle result event id differs from its request")
            require_active_task(request.task_id, "oracle result")
            allow_after_stop(request.task_id, "oracle result")
            if receipt.oracle_identity != request.oracle_identity:
                raise CoordinatorError("oracle result identity differs from request")
            if archive is None:
                raise CoordinatorError("oracle result artifact cannot be verified without an archive")
            result_payload = {
                "request_id": receipt.request_id,
                "oracle_identity": receipt.oracle_identity,
                "outcome": receipt.outcome,
                "result": dict(receipt.result),
            }
            _verify_bound_artifact(archive, receipt.result_artifact, result_payload, "oracle result")
            existing = oracle_results.get(receipt.request_id)
            if existing is not None and existing != receipt:
                raise CoordinatorError("oracle request has different durable results")
            oracle_results[receipt.request_id] = receipt
            continue

        if event.event_type == "exhaustion_recorded":
            receipt = event.payload
            assert isinstance(receipt, ExhaustionReceipt)
            allow_after_stop(None, "exhaustion receipt")
            if receipt.recipient_id not in manifest.queue_record_ids:
                raise CoordinatorError("ledger receipt recipient is outside manifest subset")
            if event.event_id != f"{receipt.receipt_id}:exhaustion":
                raise CoordinatorError("exhaustion event id differs from its receipt")
            if receipt.lane not in manifest.selected_lanes:
                raise CoordinatorError("ledger receipt lane is outside manifest selection")
            if LANE_TIERS.get(receipt.lane) != receipt.tier:
                raise CoordinatorError("ledger receipt lane and tier do not agree")
            if receipt.config_identity != manifest.config_identity:
                raise CoordinatorError("ledger receipt config differs from manifest")
            declared_budget = manifest.lane_budgets.get(receipt.lane)
            if declared_budget is None or receipt.budget.unit != declared_budget.unit or receipt.budget.limit != declared_budget.limit:
                raise CoordinatorError("ledger receipt budget differs from immutable manifest")
            expected_tool_keys = set(LANE_TOOL_KEYS.get(receipt.lane, ()))
            if set(receipt.tool_identities) != expected_tool_keys:
                raise CoordinatorError("ledger receipt tools differ from lane manifest contract")
            if any(manifest.tool_identities.get(key) != value for key, value in receipt.tool_identities.items()):
                raise CoordinatorError("ledger receipt tool identity differs from manifest")
            if archive is None:
                raise CoordinatorError("exhaustion receipt artifact cannot be verified without an archive")
            receipt_payload = receipt.to_dict()
            receipt_payload.pop("receipt_artifact")
            _verify_bound_artifact(archive, receipt.receipt_artifact, receipt_payload, "exhaustion receipt")
            key = (receipt.recipient_id, receipt.lane)
            existing = receipts.get(key)
            if existing is not None and existing != receipt:
                raise CoordinatorError("duplicate exhaustion receipt differs")
            receipts[key] = receipt
            continue

        if event.event_type == "checkpoint_committed":
            if stopped is not None:
                raise CoordinatorError("checkpoint follows a run stop")
            checkpoint = event.payload
            if event.event_id != f"{manifest.run_id}:checkpoint:{checkpoint.through_sequence}":  # type: ignore[union-attr]
                raise CoordinatorError("checkpoint event id differs from its run and sequence")
            continue

        if stopped is not None:
            raise CoordinatorError("ledger event follows a run stop")


class SearchCoordinator:
    """Own task identity, tier order, budgets and ledger commit ordering."""

    def __init__(
        self,
        run_root: Union[str, os.PathLike[str]],
        manifest: Union[RunManifest, Mapping[str, Any]],
        *,
        worker: Optional[Worker] = None,
        oracle: Optional[Oracle] = None,
        oracle_compatibility: bool = False,
        budget_limit: Optional[int] = None,
        fault_hook: Optional[FaultHook] = None,
        recommendation_report: Optional[Any] = None,
        recommendation_artifact_root: Optional[Union[str, os.PathLike[str]]] = None,
    ) -> None:
        self.run_root = Path(run_root)
        self.manifest = manifest if isinstance(manifest, RunManifest) else RunManifest.from_dict(manifest)
        self.worker = worker
        self.oracle = oracle
        self.oracle_compatibility = oracle_compatibility
        declared_budget = self.manifest.coordinator_budget
        if budget_limit is not None:
            if isinstance(budget_limit, bool) or not isinstance(budget_limit, int):
                raise CoordinatorError("compatibility budget_limit must be an integer")
            if budget_limit != declared_budget.limit:
                raise CoordinatorError(
                    "compatibility budget_limit differs from immutable manifest coordinator_budget"
                )
        self.fault_hook = fault_hook
        # Validate and read the optional prior report before creating the run
        # directory, manifest or ledger.  Reading a report never tunes a live
        # coordinator and cannot alter task identity or scheduling.
        self.recommendation_report = self._load_recommendation_report(
            recommendation_report,
            recommendation_artifact_root,
        )
        self._validate_oracle_configuration()
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.archive = ContentAddressedArchive(self.run_root, fault_hook=self._archive_fault)
        # Keep a validated prior report inside this run before the first
        # ledger event.  A later resume can therefore recover the exact bytes
        # from the run root even if the caller's external report archive is
        # gone.  The manifest binding remains the sole authority for its
        # identity.
        self._materialize_recommendation_report()
        self.ledger = AppendOnlyLedger(
            self.run_root / "ledger.jsonl",
            run_id=self.manifest.run_id,
            archive=self.archive,
            fault_hook=self._ledger_fault,
        )
        self._write_manifest()
        existing = self.ledger.verify()
        if not existing:
            self._fault("before_manifest_event")
            self.ledger.start_run(self.manifest, event_id=f"{self.manifest.run_id}:run_started")
            self._fault("after_manifest_event")
            existing = self.ledger.verify()
        elif not isinstance(existing[0].payload, RunManifest) or existing[0].payload != self.manifest:
            raise CoordinatorError("manifest differs from run_started")
        self._tasks: Dict[str, SearchTask] = {}
        self._terminal: Dict[str, TaskTerminal] = {}
        self._started = set()
        self._scheduled = set()
        self._consumed = set()
        self._budget_claims: Dict[int, str] = {}
        self._receipts: Dict[Tuple[str, str], ExhaustionReceipt] = {}
        self._tier_completed: Dict[Tuple[str, str], bool] = {}
        self._lane_yield: Dict[Tuple[str, str], Tuple[int, int]] = {}
        self._buffered: Dict[str, TaskResult] = {}
        self._oracle_candidates: List[str] = []
        self._oracle_requests: Dict[str, OracleRequest] = {}
        self._oracle_results: Dict[str, OracleReceipt] = {}
        self._stopped: Optional[RunStop] = None
        self._restore_task_indexes(existing)
        self._restore_oracle_indexes(existing)
        # The prefix validator runs before frontier or any other mutable index
        # is reconstructed.  A forged lifecycle or handoff record therefore
        # cannot influence resumed scheduling state.
        self.frontier = frontier_from_events(existing, cap=self.manifest.frontier_cap)
        self._rebuild_oracle_candidates(existing)

    @property
    def budget_limit(self) -> int:
        """Expose the manifest task limit without creating mutable budget state."""
        return self.manifest.coordinator_budget.limit

    def _materialize_recommendation_report(self) -> None:
        report = self.recommendation_report
        if report is None:
            return
        expected = self.manifest.tool_identities.get(
            SEARCH_PATTERN_REPORT_TOOL_IDENTITY
        )
        if expected is None or report.report_id != expected or report.artifact.content_hash != expected:
            raise CoordinatorError(
                "validated recommendation report does not match its manifest identity"
            )
        payload = canonical_bytes(report.payload())
        artifact = self.archive.put_bytes(
            payload,
            category="pattern_reports",
            suffix=".json",
            media_type="application/json",
        )
        if artifact.content_hash != expected or artifact.byte_size != len(payload):
            raise CoordinatorError(
                "materialized recommendation report differs from manifest identity"
            )
        try:
            self.recommendation_report = replace(report, artifact=artifact)
        except (PatternArtifactError, PatternIdentityMismatch, PatternInputError) as exc:
            raise CoordinatorError(
                "materialized recommendation report failed identity validation"
            ) from exc

    def _load_recommendation_report(
        self,
        value: Optional[Any],
        artifact_root: Optional[Union[str, os.PathLike[str]]],
    ) -> Optional[SearchPatternReport]:
        """Load one immutable report only when the manifest binds its hash.

        A manifest binding without a supplied report is resolved from an
        already materialized artifact beneath the run root.  No directory is
        created while resolving this input, so a missing or changed report
        fails before any fresh run state exists.
        """
        expected = self.manifest.tool_identities.get(
            SEARCH_PATTERN_REPORT_TOOL_IDENTITY
        )
        if value is None and expected is None:
            return None
        if value is not None and expected is None:
            raise CoordinatorError(
                "a recommendation report requires manifest tool identity "
                f"{SEARCH_PATTERN_REPORT_TOOL_IDENTITY!r}"
            )
        if expected is None:
            # The branch is reachable only for type-checkers.  The early
            # return above handles the no-report/no-binding case.
            return None
        try:
            if value is None:
                candidates = []
                artifacts = self.run_root / "artifacts"
                digest = expected.removeprefix("sha256:")
                if artifacts.is_dir():
                    candidates = sorted(
                        path for path in artifacts.rglob(digest + "*") if path.is_file()
                    )
                if len(candidates) != 1:
                    raise PatternArtifactError(
                        "bound recommendation artifact is missing or ambiguous"
                    )
                return load_report_artifact(
                    candidates[0],
                    artifact_root=self.run_root,
                    expected_hash=expected,
                )
            return load_report_artifact(
                value,
                artifact_root=artifact_root,
                expected_hash=expected,
            )
        except (PatternArtifactError, PatternIdentityMismatch, PatternInputError) as exc:
            raise CoordinatorError(f"recommendation report rejected: {exc}") from exc

    @staticmethod
    def _is_durable_oracle(value: Any) -> bool:
        return (
            value is not None
            and isinstance(getattr(value, "identity", None), str)
            and callable(getattr(value, "lookup", None))
            and callable(getattr(value, "execute", None))
        )

    def _validate_oracle_configuration(self) -> None:
        if self.oracle is None:
            return
        if self._is_durable_oracle(self.oracle):
            oracle_identity = self.oracle.identity  # type: ignore[union-attr]
            try:
                validate_hash(oracle_identity, "oracle.identity")
            except ValueError as exc:
                raise CoordinatorError("durable oracle identity must be a sha256 hash") from exc
            manifest_identity = self.manifest.tool_identities.get(
                FULL_ORACLE_TOOL_IDENTITY
            )
            if manifest_identity is None:
                raise CoordinatorError(
                    "durable oracle requires manifest tool identity "
                    f"{FULL_ORACLE_TOOL_IDENTITY!r}"
                )
            if manifest_identity != oracle_identity:
                raise CoordinatorError(
                    "durable oracle identity differs from manifest tool identity "
                    f"{FULL_ORACLE_TOOL_IDENTITY!r}"
                )
            return
        if not self.oracle_compatibility:
            raise CoordinatorError(
                "oracle must implement the restart-safe lookup/execute contract; "
                "legacy callbacks require oracle_compatibility=True"
            )
        if not callable(self.oracle):
            raise CoordinatorError("oracle compatibility mode requires a callable")

    def _fault(self, point: str) -> None:
        if self.fault_hook is not None:
            self.fault_hook(point)

    def _archive_fault(self, point: str, _path: Path) -> None:
        self._fault(point)

    def _ledger_fault(self, point: str, _path: Path) -> None:
        self._fault(point)

    def _write_manifest(self) -> None:
        path = self.run_root / "manifest.json"
        encoded = (self.manifest.to_json() + "\n").encode("utf-8")
        if path.exists():
            if path.read_bytes() != encoded:
                raise CoordinatorError("manifest.json differs from immutable manifest")
            return
        temporary = path.with_name("." + path.name + ".tmp")
        try:
            with temporary.open("wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            self._fault("before_manifest_publish")
            os.replace(str(temporary), str(path))
            self._fault("after_manifest_publish")
            self._fsync_directory(path.parent)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            descriptor = os.open(str(path), os.O_RDONLY)
        except (OSError, ValueError):
            return
        try:
            os.fsync(descriptor)
        except OSError:
            pass
        finally:
            os.close(descriptor)

    def _restore_task_indexes(self, events: Sequence[LedgerEvent]) -> None:
        validate_ledger_prefix(self.manifest, events, archive=self.archive)
        for event in events:
            if event.event_type in ("task_scheduled", "task_started"):
                task = event.payload
                assert isinstance(task, SearchTask)
                self._validate_task_binding(task)
                self._tasks[task.task_id] = task
                self._scheduled.add(task.task_id)
                budget_ordinal = task.budget_ordinal
                prior = self._budget_claims.get(budget_ordinal)
                if prior is not None and prior != task.task_id:
                    raise CoordinatorError("ledger reuses a global budget ordinal for different tasks")
                self._budget_claims[budget_ordinal] = task.task_id
                if event.event_type == "task_started":
                    self._started.add(task.task_id)
            elif event.event_type == "task_completed":
                terminal = event.payload
                assert isinstance(terminal, TaskTerminal)
                self._terminal[terminal.task_id] = terminal
                self._consumed.add(terminal.task_id)
            elif event.event_type == "task_interrupted":
                interruption = event.payload
                self._started.add(interruption.task_id)  # type: ignore[union-attr]
            elif event.event_type == "run_stopped":
                stop = event.payload
                assert isinstance(stop, RunStop)
                if self._stopped is not None and self._stopped != stop:
                    raise CoordinatorError("run has multiple different stop records")
                self._stopped = stop
            elif event.event_type == "exhaustion_recorded":
                receipt = event.payload
                assert isinstance(receipt, ExhaustionReceipt)
                if receipt.recipient_id not in self.manifest.queue_record_ids:
                    raise CoordinatorError("ledger receipt recipient is outside manifest subset")
                if receipt.lane not in self.manifest.selected_lanes:
                    raise CoordinatorError("ledger receipt lane is outside manifest selection")
                declared_budget = self.manifest.lane_budgets.get(receipt.lane)
                if declared_budget is None or receipt.budget.unit != declared_budget.unit or receipt.budget.limit != declared_budget.limit:
                    raise CoordinatorError("ledger receipt budget differs from immutable manifest")
                expected_tool_keys = set(LANE_TOOL_KEYS.get(receipt.lane, ()))
                if set(receipt.tool_identities) != expected_tool_keys:
                    raise CoordinatorError("ledger receipt tools differ from lane manifest contract")
                if any(self.manifest.tool_identities.get(key) != value for key, value in receipt.tool_identities.items()):
                    raise CoordinatorError("ledger receipt tool identity differs from manifest")
                self._receipts[(receipt.recipient_id, receipt.lane)] = receipt
                self._tier_completed[(receipt.recipient_id, receipt.tier)] = True
                self._lane_yield[(receipt.recipient_id, receipt.lane)] = (
                    len(receipt.best_candidate_ids), receipt.attempts
                )

    def _restore_oracle_indexes(self, events: Sequence[LedgerEvent]) -> None:
        for event in events:
            if event.event_type == "oracle_requested":
                request = event.payload
                assert isinstance(request, OracleRequest)
                existing = self._oracle_requests.get(request.request_id)
                if existing is not None and existing != request:
                    raise CoordinatorError("oracle request identity maps to different payload")
                self._oracle_requests[request.request_id] = request
            elif event.event_type == "oracle_result_recorded":
                receipt = event.payload
                assert isinstance(receipt, OracleReceipt)
                if receipt.request_id not in self._oracle_requests:
                    raise CoordinatorError("oracle result has no durable request")
                existing = self._oracle_results.get(receipt.request_id)
                if existing is not None and existing != receipt:
                    raise CoordinatorError("oracle request has different durable results")
                self._oracle_results[receipt.request_id] = receipt

    @staticmethod
    def _is_zero_candidate(candidate: CandidateRecord) -> bool:
        return (
            candidate.evaluation is not None
            and candidate.evaluation.compile_status == "success"
            and candidate.evaluation.total == 0
        ) or candidate.status == "zero_pending_oracle"

    def _rebuild_oracle_candidates(self, events: Sequence[LedgerEvent]) -> None:
        """Reconstruct only score-zero candidates still awaiting the oracle.

        Candidate status alone is not sufficient after a successful oracle
        handoff because the immutable candidate record remains evidence of the
        zero score. A terminal task for its evaluation is the durable proof
        that the handoff completed.
        """
        evaluation_tasks: Dict[str, List[str]] = {}
        candidate_tasks: Dict[str, List[str]] = {}
        for event in events:
            if event.event_type == "evaluation_completed":
                evaluation = event.payload
                assert isinstance(evaluation, EvaluationEvent)
                evaluation_tasks.setdefault(evaluation.candidate_id, []).append(evaluation.task_id)
            elif event.event_type == "candidate_materialized":
                candidate = event.payload
                assert isinstance(candidate, CandidateRecord)
                marker = ":materialized:"
                if marker in event.event_id:
                    candidate_tasks.setdefault(candidate.candidate_id, []).append(
                        event.event_id.rsplit(marker, 1)[1]
                    )
        terminal_ids = set(self._terminal)
        pending = []
        for candidate in self.frontier.graph.all():
            if not self._is_zero_candidate(candidate):
                continue
            task_ids = list(evaluation_tasks.get(candidate.candidate_id, ()))
            task_ids.extend(candidate_tasks.get(candidate.candidate_id, ()))
            if not task_ids or any(task_id not in terminal_ids for task_id in task_ids):
                pending.append(candidate.candidate_id)
        self._oracle_candidates = sorted(set(pending))

    def _terminal_from_ledger(self, task_id: str) -> Optional[TaskTerminal]:
        for event in reversed(self.ledger.events()):
            if event.event_type != "task_completed":
                continue
            terminal = event.payload
            assert isinstance(terminal, TaskTerminal)
            if terminal.task_id == task_id:
                return terminal
        return None

    def _record_terminal(
        self,
        terminal: TaskTerminal,
        candidate_ids: Iterable[str] = (),
    ) -> None:
        self._terminal[terminal.task_id] = terminal
        self._consumed.add(terminal.task_id)
        resolved_candidates = set(candidate_ids)
        resolved_candidates.update(
            event.payload.candidate_id
            for event in self.ledger.events()
            if event.event_type == "evaluation_completed"
            and isinstance(event.payload, EvaluationEvent)
            and event.payload.task_id == terminal.task_id
        )
        if resolved_candidates:
            self._oracle_candidates = [
                candidate_id
                for candidate_id in self._oracle_candidates
                if candidate_id not in resolved_candidates
            ]

    @property
    def events(self) -> Tuple[LedgerEvent, ...]:
        return self.ledger.events()

    @staticmethod
    def task_identity(
        run_id: str,
        recipient_id: str,
        lane: str,
        tier: str,
        operation: str,
        parent_candidate_ids: Sequence[str],
        budget_ordinal: int,
        config_identity: str,
    ) -> str:
        return _task_identity(
            run_id,
            recipient_id,
            lane,
            tier,
            operation,
            parent_candidate_ids,
            budget_ordinal,
            config_identity,
        )

    @staticmethod
    def task_seed(run_seed: int, task_id: str) -> int:
        return _task_seed(run_seed, task_id)

    def _validate_task_binding(self, task: SearchTask) -> None:
        _validate_task_binding(self.manifest, task)

    def _ensure_task_replay_allowed(self, task_id: str) -> None:
        """Enforce a persisted stop boundary for task replay and completion."""
        stop = self._stopped
        if stop is None:
            return
        if not stop.resumable:
            raise CoordinatorError("task operation follows a non-resumable run stop")
        if task_id not in stop.pending_task_ids:
            raise CoordinatorError("task operation is outside the resumable stop boundary")
        if task_id not in self._tasks:
            raise CoordinatorError("resumable stop names an unknown task")

    def _ensure_no_stop_for_mutation(self, label: str) -> None:
        if self._stopped is not None:
            raise CoordinatorError(label + " is not allowed after a run stop")

    def _check_recipient(self, recipient_id: str) -> None:
        # ``recipient_id`` is the queue record ownership boundary.  Function
        # symbols are descriptive manifest data, not an implicit alternate
        # subset; accepting them would let a caller bypass the explicit queue
        # selection that made this run safe.
        if recipient_id not in self.manifest.queue_record_ids:
            raise ExplicitSubsetError(f"recipient {recipient_id!r} is outside the manifest subset")

    def _check_tier(self, recipient_id: str, tier: str) -> None:
        tier_index = TIER_ORDER.index(tier)
        selected = set(self.manifest.selected_lanes)
        for previous in TIER_ORDER[:tier_index]:
            missing = [
                lane for lane in LANES_BY_TIER[previous]
                if lane in selected and (recipient_id, lane) not in self._receipts
            ]
            if missing:
                raise TierBlocked(
                    f"{previous} is incomplete for {recipient_id}; missing lanes: {', '.join(missing)}"
                )

    def _manifest_lane_tools(self, lane: str) -> Dict[str, str]:
        """Return the exact manifest tool set assigned to one lane."""
        keys = LANE_TOOL_KEYS.get(lane)
        if not keys:
            raise CoordinatorError("lane has no manifest tool contract")
        tools: Dict[str, str] = {}
        for key in keys:
            value = self.manifest.tool_identities.get(key)
            if value is None:
                raise CoordinatorError(
                    "manifest is missing tool identity " + key + " for lane " + lane
                )
            tools[key] = value
        return dict(sorted(tools.items()))

    def create_task(
        self,
        *,
        recipient_id: str,
        lane: str,
        operation: str,
        parent_candidate_ids: Sequence[str] = (),
        budget_ordinal: int = 0,
        tier: Optional[str] = None,
    ) -> SearchTask:
        self._check_recipient(recipient_id)
        if self._stopped is not None and not self._stopped.resumable:
            raise CoordinatorError("task allocation follows a non-resumable run stop")
        expected_tier = LANE_TIERS.get(lane)
        if expected_tier is None:
            raise CoordinatorError(f"no tier mapping for lane {lane!r}")
        if lane not in self.manifest.selected_lanes:
            raise CoordinatorError("lane is not selected by the immutable manifest")
        if tier is not None and tier != expected_tier:
            raise CoordinatorError("lane and tier do not agree")
        tier = expected_tier
        self._check_tier(recipient_id, tier)
        if budget_ordinal >= self.manifest.coordinator_budget.limit:
            raise BudgetExhausted("budget ordinal exceeds immutable manifest limit")
        task_id = self.task_identity(
            self.manifest.run_id,
            recipient_id,
            lane,
            tier,
            operation,
            parent_candidate_ids,
            budget_ordinal,
            self.manifest.config_identity,
        )
        task = SearchTask(
            task_id=task_id,
            recipient_id=recipient_id,
            lane=lane,
            tier=tier,
            operation=operation,
            parent_candidate_ids=tuple(parent_candidate_ids),
            budget_ordinal=budget_ordinal,
            task_seed=self.task_seed(self.manifest.run_seed, task_id),
            config_identity=self.manifest.config_identity,
            state="scheduled",
        )
        self._validate_task_binding(task)
        if self._stopped is not None:
            self._ensure_task_replay_allowed(task.task_id)
        prior = self._budget_claims.get(task.budget_ordinal)
        if prior is not None and prior != task.task_id:
            raise BudgetExhausted("budget ordinal is already assigned to another task")
        return task

    def schedule_task(self, task: SearchTask) -> SearchTask:
        self._validate_task_binding(task)
        if self._stopped is not None:
            self._ensure_task_replay_allowed(task.task_id)
        self._check_tier(task.recipient_id, task.tier)
        if task.state != "scheduled":
            raise CoordinatorError("only scheduled tasks may be added")
        existing = self._tasks.get(task.task_id)
        if existing is not None:
            if replace(existing, state="scheduled") != task:
                raise CoordinatorError("task id maps to different immutable task")
            return existing
        prior = self._budget_claims.get(task.budget_ordinal)
        if prior is not None and prior != task.task_id:
            raise BudgetExhausted("budget ordinal is already assigned to another task")
        # Append first. If a fault occurs after the durable append, a retry
        # can discover the event and then update process-local indexes.
        self._fault("before_task_scheduled")
        self._append_event_once(
            "task_scheduled", task, event_id=f"{task.task_id}:scheduled"
        )
        self._fault("after_task_scheduled")
        self._tasks[task.task_id] = task
        self._budget_claims[task.budget_ordinal] = task.task_id
        self._scheduled.add(task.task_id)
        return task

    def schedule_tasks(self, tasks: Iterable[SearchTask]) -> Tuple[SearchTask, ...]:
        def lane_key(task: SearchTask) -> Tuple[Fraction, str, str]:
            accepted, attempts = self._lane_yield.get((task.recipient_id, task.lane), (0, 0))
            yield_rate = Fraction(accepted, attempts) if attempts else Fraction(0, 1)
            return (-yield_rate, task.lane, task.task_id)

        ordered = tuple(sorted(tasks, key=lane_key))
        for task in ordered:
            self.schedule_task(task)
        return ordered

    def set_lane_yield(self, recipient_id: str, lane: str, *, accepted: int, attempts: int) -> None:
        """Set measured yield used for deterministic within-tier ordering.

        Receipts normally populate this value.  The explicit setter is useful
        to adapters that measure a lane before its terminal receipt is written.
        It is intentionally local and cannot allocate budget or mutate the
        ledger.
        """
        self._ensure_no_stop_for_mutation("lane yield update")
        self._check_recipient(recipient_id)
        if lane not in LANE_TIERS or accepted < 0 or attempts < 0 or accepted > attempts:
            raise CoordinatorError("invalid lane yield")
        self._lane_yield[(recipient_id, lane)] = (accepted, attempts)

    def start_task(self, task_id: str) -> SearchTask:
        self._ensure_task_replay_allowed(task_id)
        task = self._tasks.get(task_id)
        if task is None:
            raise CoordinatorError("unknown task")
        if task_id in self._terminal:
            return task
        if task_id not in self._started:
            started = replace(task, state="started")
            # As with scheduling, process-local state follows the durable
            # event so same-process retries are safe after a post-append fault.
            self._fault("before_task_started")
            self._append_event_once(
                "task_started", started, event_id=f"{task_id}:started"
            )
            self._fault("after_task_started")
            self._started.add(task_id)
            self._tasks[task_id] = started
        return self._tasks[task_id]

    def dispatch(self, tasks: Optional[Iterable[SearchTask]] = None) -> Tuple[TaskResult, ...]:
        if self.worker is None:
            raise CoordinatorError("no stateless worker configured")
        selected = tuple(tasks) if tasks is not None else tuple(self._tasks.values())
        results = []
        for task in sorted(selected, key=lambda item: item.task_id):
            if task.task_id in self._terminal:
                continue
            started = self.start_task(task.task_id)
            result = self.worker(started)
            if not isinstance(result, TaskResult):
                result = TaskResult.from_dict(result)  # type: ignore[arg-type]
            results.append(result)
        return tuple(results)

    def buffer_result(self, result: TaskResult) -> None:
        if not isinstance(result, TaskResult):
            result = TaskResult.from_dict(result)  # type: ignore[arg-type]
        if result.task_id not in self._tasks:
            raise CoordinatorError("result names an unscheduled task")
        self._ensure_task_replay_allowed(result.task_id)
        existing = self._buffered.get(result.task_id)
        if existing is not None and existing != result:
            raise CoordinatorError("duplicate task result differs")
        self._buffered[result.task_id] = result

    def _materialize_candidate(self, result: TaskResult) -> Optional[CandidateRecord]:
        candidate = result.candidate
        if candidate is None:
            return None
        try:
            self.archive.verify(candidate.source_artifact)
        except ArtifactMissing:
            if result.source is None:
                raise CoordinatorError("candidate source artifact is unavailable")
            reference = self.archive.put_source(result.source)
            if reference.content_hash != candidate.source_artifact.content_hash:
                raise CoordinatorError("candidate source identity differs from result source")
            candidate = replace(candidate, source_artifact=reference)
        except ArtifactCorrupt as exc:
            raise CoordinatorError("candidate source artifact is corrupt") from exc
        except ArchiveError as exc:
            raise CoordinatorError("candidate source artifact path is invalid") from exc
        return candidate

    def _append_event_once(
        self,
        event_type: str,
        payload: Any,
        *,
        event_id: str,
    ) -> LedgerEvent:
        for existing in self.ledger.events():
            if existing.event_id == event_id:
                if existing.event_type != event_type or existing.payload != payload:
                    raise CoordinatorError("durable event id maps to different payload")
                return existing
        return self.ledger.append_event(event_type, payload, event_id=event_id)

    def _oracle_request_from_ledger(self, request_id: str) -> Optional[OracleRequest]:
        request = self._oracle_requests.get(request_id)
        if request is not None:
            return request
        for event in reversed(self.ledger.events()):
            if event.event_type != "oracle_requested":
                continue
            candidate = event.payload
            assert isinstance(candidate, OracleRequest)
            if candidate.request_id == request_id:
                self._oracle_requests[request_id] = candidate
                return candidate
        return None

    def _oracle_result_from_ledger(self, request_id: str) -> Optional[OracleReceipt]:
        receipt = self._oracle_results.get(request_id)
        if receipt is not None:
            return receipt
        for event in reversed(self.ledger.events()):
            if event.event_type != "oracle_result_recorded":
                continue
            candidate = event.payload
            assert isinstance(candidate, OracleReceipt)
            if candidate.request_id == request_id:
                request = self._oracle_request_from_ledger(request_id)
                if request is None:
                    raise CoordinatorError("oracle result has no durable request")
                if candidate.oracle_identity != request.oracle_identity:
                    raise CoordinatorError("oracle result identity differs from request")
                self._oracle_results[request_id] = candidate
                return candidate
        return None

    def _existing_oracle_request_for_candidate(
        self,
        task: SearchTask,
        candidate: CandidateRecord,
        oracle_identity: str,
    ) -> Optional[OracleRequest]:
        # Search durable requests by the task/candidate identity before using
        # the current oracle identity to derive a request id.  A changed
        # service must never create a second request for the same handoff.
        known: Dict[str, OracleRequest] = dict(self._oracle_requests)
        for event in self.ledger.events():
            if event.event_type != "oracle_requested":
                continue
            request = event.payload
            assert isinstance(request, OracleRequest)
            existing = known.get(request.request_id)
            if existing is not None and existing != request:
                raise CoordinatorError("durable oracle request id maps to different payload")
            known[request.request_id] = request
        matches = [
            request
            for request in known.values()
            if (
                request.task_id == task.task_id
                and request.recipient_id == task.recipient_id
                and request.candidate_id == candidate.candidate_id
                and request.source_hash == candidate.source_artifact.content_hash
                and request.config_identity == self.manifest.config_identity
            )
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise CoordinatorError("multiple durable oracle requests map to one candidate")
        request = matches[0]
        if request.oracle_identity != oracle_identity:
            raise CoordinatorError("durable oracle identity changed for existing request")
        if request.candidate != candidate:
            raise CoordinatorError("durable oracle request candidate differs on resume")
        self._oracle_requests[request.request_id] = request
        return request

    def _ensure_oracle_request(self, task: SearchTask, candidate: CandidateRecord) -> OracleRequest:
        if not self._is_durable_oracle(self.oracle):
            raise OracleRequired("score-zero candidate requires a durable restart-safe oracle service")
        oracle_identity = self.oracle.identity  # type: ignore[union-attr]
        existing_for_candidate = self._existing_oracle_request_for_candidate(
            task,
            candidate,
            oracle_identity,
        )
        if existing_for_candidate is not None:
            return existing_for_candidate
        request_id = oracle_request_identity(
            task_id=task.task_id,
            recipient_id=task.recipient_id,
            candidate_id=candidate.candidate_id,
            source_hash=candidate.source_artifact.content_hash,
            config_identity=self.manifest.config_identity,
            oracle_identity=oracle_identity,
        )
        existing = self._oracle_request_from_ledger(request_id)
        if existing is not None:
            return existing
        self._fault("before_oracle_request")
        request_payload = {
            "request_id": request_id,
            "task_id": task.task_id,
            "recipient_id": task.recipient_id,
            "candidate_id": candidate.candidate_id,
            "source_hash": candidate.source_artifact.content_hash,
            "candidate": candidate.to_dict(),
            "config_identity": self.manifest.config_identity,
            "oracle_identity": oracle_identity,
        }
        self._fault("before_oracle_request_artifact")
        artifact = self.archive.put_json(
            request_payload,
            category="oracle_requests",
            suffix=".json",
        )
        self._fault("after_oracle_request_artifact")
        request = OracleRequest(
            request_id=request_id,
            task_id=task.task_id,
            recipient_id=task.recipient_id,
            candidate_id=candidate.candidate_id,
            source_hash=candidate.source_artifact.content_hash,
            candidate=candidate,
            config_identity=self.manifest.config_identity,
            oracle_identity=oracle_identity,
            request_artifact=artifact,
        )
        self._fault("before_oracle_request_event")
        self._append_event_once(
            "oracle_requested",
            request,
            event_id=f"{request_id}:requested",
        )
        self._fault("after_oracle_request_event")
        self._fault("after_oracle_request")
        self._oracle_requests[request_id] = request
        return request

    @staticmethod
    def _coerce_oracle_value(
        request: OracleRequest,
        value: Any,
    ) -> Tuple[str, Mapping[str, Any]]:
        if isinstance(value, OracleReceipt):
            if value.request_id != request.request_id:
                raise CoordinatorError("oracle receipt names a different request")
            if value.oracle_identity != request.oracle_identity:
                raise CoordinatorError("oracle receipt names a different oracle")
            return value.outcome, value.result
        if not isinstance(value, Mapping):
            raise CoordinatorError("durable oracle must return an object result or OracleReceipt")
        if "outcome" in value:
            outcome = value["outcome"]
            result = value.get("result")
            if not isinstance(result, Mapping):
                raise CoordinatorError("oracle outcome result must be an object")
            return str(outcome), result
        return "matched", value

    def _materialize_oracle_result(
        self,
        request: OracleRequest,
        outcome: str,
        result: Mapping[str, Any],
    ) -> Tuple[LedgerEvent, ...]:
        existing = self._oracle_result_from_ledger(request.request_id)
        if existing is not None:
            if existing.oracle_identity != request.oracle_identity:
                raise CoordinatorError("durable oracle result names a different oracle")
            if existing.outcome != outcome or dict(existing.result) != dict(result):
                raise CoordinatorError("oracle request returned a different immutable result")
            return ()
        self._fault("before_oracle_result")
        result_payload = {
            "request_id": request.request_id,
            "oracle_identity": request.oracle_identity,
            "outcome": outcome,
            "result": dict(result),
        }
        self._fault("before_oracle_result_artifact")
        artifact = self.archive.put_json(
            result_payload,
            category="oracle_results",
            suffix=".json",
        )
        self._fault("after_oracle_result_artifact")
        receipt = OracleReceipt(
            receipt_id=oracle_receipt_identity(
                request_id=request.request_id,
                oracle_identity=request.oracle_identity,
                outcome=outcome,
                result=result,
            ),
            request_id=request.request_id,
            oracle_identity=request.oracle_identity,
            outcome=outcome,
            result=result,
            result_artifact=artifact,
        )
        self._fault("before_oracle_result_event")
        event = self._append_event_once(
            "oracle_result_recorded",
            receipt,
            event_id=f"{request.request_id}:result",
        )
        self._fault("after_oracle_result_event")
        self._fault("after_oracle_result")
        self._oracle_results[request.request_id] = receipt
        return (event,)

    def _oracle_handoff(
        self,
        task: SearchTask,
        candidate: CandidateRecord,
    ) -> Tuple[LedgerEvent, ...]:
        if self.oracle is None:
            raise OracleRequired("score-zero candidate is durable and awaits the full oracle")
        if not self._is_durable_oracle(self.oracle):
            if self.oracle_compatibility:
                # This explicitly unsafe path exists only for legacy adapters.
                self.oracle(candidate)  # type: ignore[operator]
                return ()
            raise OracleRequired("score-zero candidate requires a durable restart-safe oracle service")
        request = self._ensure_oracle_request(task, candidate)
        if self._oracle_result_from_ledger(request.request_id) is not None:
            return ()
        try:
            raw = self.oracle.lookup(request.request_id)  # type: ignore[union-attr]
        except Exception as exc:
            raise CoordinatorError("durable oracle lookup failed") from exc
        if raw is None:
            self._fault("before_oracle_execution")
            try:
                executed = self.oracle.execute(request)  # type: ignore[union-attr]
            except Exception as exc:
                raise CoordinatorError("durable oracle execution failed") from exc
            executed_outcome, executed_value = self._coerce_oracle_value(request, executed)
            try:
                persisted = self.oracle.lookup(request.request_id)  # type: ignore[union-attr]
            except Exception as exc:
                raise CoordinatorError("durable oracle read-after-write lookup failed") from exc
            if persisted is None:
                raise CoordinatorError("durable oracle did not persist result")
            persisted_outcome, persisted_value = self._coerce_oracle_value(request, persisted)
            if (
                executed_outcome != persisted_outcome
                or hash_canonical(executed_value) != hash_canonical(persisted_value)
            ):
                raise CoordinatorError("durable oracle read-after-write result differs")
            # This fault point is after the mandatory read-after-write proof.
            self._fault("after_oracle_execution")
            raw = persisted
        outcome, value = self._coerce_oracle_value(request, raw)
        return self._materialize_oracle_result(request, outcome, value)

    def _validate_result_binding(self, task: SearchTask, result: TaskResult) -> None:
        """Reject worker bindings and artifacts before any durable output."""
        mutation = result.mutation
        candidate = result.candidate
        evaluation = result.evaluation
        archive_decision = result.archive_decision
        task_parents = set(task.parent_candidate_ids)

        if mutation is not None:
            if mutation.recipient_id != task.recipient_id:
                raise CoordinatorError("mutation recipient differs from task")
            if mutation.lane != task.lane:
                raise CoordinatorError("mutation lane differs from task")
            mutation_parents = {mutation.parent_candidate_id}
            mutation_parents.update(mutation.donor_candidate_ids)
            if not mutation_parents.issubset(task_parents):
                raise CoordinatorError("mutation ancestry is outside task parent candidates")

        if candidate is not None:
            if candidate.recipient_id != task.recipient_id:
                raise CoordinatorError("candidate recipient differs from task")
            if candidate.lane != task.lane:
                raise CoordinatorError("candidate lane differs from task")
            candidate_parents = set(candidate.parent_candidate_ids)
            if mutation is None:
                if candidate.mutation_id is not None:
                    raise CoordinatorError("candidate mutation_id has no matching mutation")
                if not candidate_parents.issubset(task_parents):
                    raise CoordinatorError("candidate ancestry is outside task parent candidates")
            else:
                if mutation.replay_status != "applied":
                    raise CoordinatorError("non-applied mutation cannot produce a candidate")
                if candidate.mutation_id != mutation.mutation_id:
                    raise CoordinatorError("candidate mutation_id differs from mutation")
                if mutation.result_source_hash is None:
                    raise CoordinatorError("applied mutation must name its result source")
                if candidate.source_artifact.content_hash != mutation.result_source_hash:
                    raise CoordinatorError("candidate source differs from mutation result")
                expected_parents = {mutation.parent_candidate_id}
                expected_parents.update(mutation.donor_candidate_ids)
                if candidate_parents != expected_parents:
                    raise CoordinatorError("candidate ancestry differs from mutation parents")

        if evaluation is not None:
            if evaluation.task_id != task.task_id:
                raise CoordinatorError("evaluation task differs from result task")
            if evaluation.recipient_id != task.recipient_id:
                raise CoordinatorError("evaluation recipient differs from task")
            if evaluation.after.compiler_identity != self.manifest.compiler_identity:
                raise CoordinatorError("evaluation compiler identity differs from manifest")
            if candidate is None:
                raise CoordinatorError("evaluation requires a durable candidate")
            if candidate is not None:
                if evaluation.candidate_id != candidate.candidate_id:
                    raise CoordinatorError("evaluation candidate differs from result candidate")
                if candidate.evaluation is not None and candidate.evaluation != evaluation.after:
                    raise CoordinatorError("candidate and evaluation vectors differ")
            expected_cache_key = self.frontier.cache.key_for(
                evaluation.recipient_id,
                evaluation.candidate_id,
                evaluation.after.compiler_identity,
            )
            if evaluation.cache_key != expected_cache_key:
                raise CoordinatorError("evaluation cache key is not recipient local")

        if archive_decision is not None:
            if candidate is None:
                raise CoordinatorError("archive decision requires a candidate")
            if archive_decision.candidate_id != candidate.candidate_id:
                raise CoordinatorError("archive decision does not name its candidate")
            if archive_decision.recipient_id != candidate.recipient_id:
                raise CoordinatorError("archive decision recipient differs from candidate")

        for artifact in result.result_artifacts:
            try:
                self.archive.verify(artifact)
            except ArchiveError as exc:
                raise CoordinatorError("task result artifact is missing, corrupt, or outside the run") from exc

    def _commit_one(self, result: TaskResult) -> Tuple[LedgerEvent, ...]:
        self._ensure_task_replay_allowed(result.task_id)
        task = self._tasks.get(result.task_id)
        if task is None:
            raise CoordinatorError("result names an unscheduled task")
        self._validate_result_binding(task, result)
        if result.task_id in self._terminal:
            return ()
        # Resolve or publish the candidate source before the first ledger
        # append.  Invalid worker bindings above therefore cannot leave a
        # task-started or mutation event behind, while a valid retry can still
        # reuse an already materialized source artifact.
        candidate = None
        if result.candidate is not None:
            self._fault("before_source_artifact")
            candidate = self._materialize_candidate(result)
            self._fault("after_source_artifact")
        # A ledger append can be durable even when a fault is raised after the
        # write. Refresh the terminal index before replaying worker output so
        # a same-process retry does not invoke an oracle twice.
        durable_terminal = self._terminal_from_ledger(result.task_id)
        if durable_terminal is not None:
            self._record_terminal(
                durable_terminal,
                (
                    (result.candidate.candidate_id,)
                    if result.candidate is not None
                    else ()
                ),
            )
            return ()
        self.start_task(result.task_id)
        events: List[LedgerEvent] = []
        if result.mutation is not None:
            if result.mutation.recipient_id != task.recipient_id:
                raise CoordinatorError("mutation recipient differs from task")
            self._fault("before_mutation_artifact")
            self.archive.put_patch(result.mutation.grouped_patch)
            self._fault("after_mutation_artifact")
            self._fault("before_mutation_event")
            events.append(self._append_event_once(
                "mutation_materialized",
                result.mutation,
                event_id=f"{result.mutation.mutation_id}:materialized:{task.task_id}",
            ))
            self._fault("after_mutation_event")
        if candidate is not None:
            if candidate.recipient_id != task.recipient_id:
                raise CoordinatorError("candidate recipient differs from task")
            if result.evaluation is not None:
                evaluation = result.evaluation
                if evaluation.candidate_id != candidate.candidate_id:
                    raise CoordinatorError("evaluation candidate differs from result candidate")
                if candidate.evaluation is not None and candidate.evaluation != evaluation.after:
                    raise CoordinatorError("candidate and evaluation vectors differ")
                candidate = replace(
                    candidate,
                    evaluation=evaluation.after,
                    status=(
                        "zero_pending_oracle"
                        if evaluation.after.compile_status == "success" and evaluation.after.total == 0
                        else (
                            "evaluated"
                            if candidate.status == "zero_pending_oracle"
                            else candidate.status
                        )
                    ),
                )
            elif self._is_zero_candidate(candidate):
                # A worker may return an already evaluated candidate without a
                # separate EvaluationEvent. Persist its pending status rather
                # than losing the oracle handoff during recovery.
                candidate = replace(candidate, status="zero_pending_oracle")
            self._fault("before_candidate_event")
            events.append(self._append_event_once(
                "candidate_materialized",
                candidate,
                event_id=f"{candidate.candidate_id}:materialized:{task.task_id}",
            ))
            self._fault("after_candidate_event")
            self.frontier.add_candidate(candidate)
        if result.evaluation is not None:
            evaluation = result.evaluation
            if evaluation.task_id != task.task_id:
                raise CoordinatorError("evaluation task differs from result task")
            if evaluation.recipient_id != task.recipient_id:
                raise CoordinatorError("evaluation recipient differs from task")
            if evaluation.after.compiler_identity != self.manifest.compiler_identity:
                raise CoordinatorError("evaluation compiler identity differs from manifest")
            if evaluation.after.compile_status == "success" and evaluation.after.total == 0 and candidate is None:
                raise CoordinatorError("score-zero evaluation requires a durable candidate")
            if candidate is not None and evaluation.candidate_id != candidate.candidate_id:
                raise CoordinatorError("evaluation candidate differs from result candidate")
            expected_cache_key = self.frontier.cache.key_for(
                evaluation.recipient_id,
                evaluation.candidate_id,
                evaluation.after.compiler_identity,
            )
            if evaluation.cache_key != expected_cache_key:
                raise CoordinatorError("evaluation cache key is not recipient local")
            self._fault("before_evaluation_event")
            events.append(self._append_event_once(
                "evaluation_completed",
                evaluation,
                event_id=f"{evaluation.task_id}:evaluation",
            ))
            self._fault("after_evaluation_event")
            if candidate is not None:
                self.frontier.cache.put(
                    evaluation.recipient_id,
                    evaluation.candidate_id,
                    evaluation.after.compiler_identity,
                    evaluation,
                )
                self.frontier.add_candidate(candidate)
        if candidate is not None and candidate.evaluation is not None:
            decision = self.frontier.archive.consider(candidate)
            if result.archive_decision is not None and result.archive_decision != decision:
                raise CoordinatorError("worker archive decision differs from coordinator decision")
            if decision.candidate_id != candidate.candidate_id or decision.recipient_id != candidate.recipient_id:
                raise CoordinatorError("archive decision does not name its candidate")
            self._fault("before_archive_event")
            events.append(self._append_event_once(
                "archive_decided",
                decision,
                event_id=f"{candidate.candidate_id}:archive:{task.task_id}",
            ))
            self._fault("after_archive_event")
            if self._is_zero_candidate(candidate):
                if candidate.candidate_id not in self._oracle_candidates:
                    self._oracle_candidates.append(candidate.candidate_id)
                events.extend(self._oracle_handoff(task, candidate))
        terminal = TaskTerminal(
            task_id=task.task_id,
            state=result.state,
            result_artifacts=result.result_artifacts,
            reason=result.reason,
        )
        self._fault("before_task_terminal")
        events.append(self._append_event_once(
            "task_completed",
            terminal,
            event_id=f"{task.task_id}:completed",
        ))
        self._fault("after_task_terminal")
        self._record_terminal(
            terminal,
            (candidate.candidate_id,) if candidate is not None else (),
        )
        return tuple(events)

    def commit_epoch(self, results: Optional[Iterable[TaskResult]] = None) -> Tuple[LedgerEvent, ...]:
        if self._stopped is not None and not self._stopped.resumable:
            raise CoordinatorError("epoch commit follows a non-resumable run stop")
        if results is not None:
            for result in results:
                self.buffer_result(result)
        self._fault("before_epoch_commit")
        events: List[LedgerEvent] = []
        ready = sorted(self._buffered)
        commit_ids = ready[: self.manifest.epoch_size]
        for task_id in commit_ids:
            events.extend(self._commit_one(self._buffered[task_id]))
        for task_id in commit_ids:
            self._buffered.pop(task_id, None)
        self._fault("after_epoch_commit")
        return tuple(events)

    commit_results = commit_epoch

    def complete_tier(self, recipient_id: str, tier: str, *, lane: Optional[str] = None, reason: str = "tier complete") -> ExhaustionReceipt:
        self._check_recipient(recipient_id)
        if tier not in TIERS:
            raise CoordinatorError("unknown tier")
        if lane is None:
            raise CoordinatorError("a receipt lane is required")
        declared_budget = self.manifest.lane_budgets.get(lane)
        if declared_budget is None:
            raise CoordinatorError("manifest has no budget for lane " + str(lane))
        return self.record_exhaustion(
            recipient_id=recipient_id,
            lane=lane,
            tier=tier,
            input_identities=(self.manifest.source_identity,),
            budget_unit=declared_budget.unit,
            budget_limit=declared_budget.limit,
            budget_consumed=0,
            attempts=0,
            rejection_counts={"none": 0},
            best_candidate_ids=(),
            completion_reason="search_space_exhausted",
            reason=reason,
            tool_identities=self._manifest_lane_tools(lane),
        )

    def record_exhaustion(
        self,
        *,
        recipient_id: str,
        lane: str,
        tier: str,
        input_identities: Sequence[str],
        budget_unit: Optional[str] = None,
        budget_limit: Optional[int] = None,
        budget_consumed: Optional[int] = None,
        attempts: int = 0,
        rejection_counts: Optional[Mapping[str, int]] = None,
        best_candidate_ids: Sequence[str] = (),
        completion_reason: str = "search_space_exhausted",
        reason: str = "lane complete",
        tool_identities: Optional[Mapping[str, str]] = None,
    ) -> ExhaustionReceipt:
        self._ensure_no_stop_for_mutation("exhaustion receipt")
        self._check_recipient(recipient_id)
        if lane not in self.manifest.selected_lanes:
            raise CoordinatorError("receipt lane is not selected by the immutable manifest")
        if lane not in LANE_TIERS or LANE_TIERS[lane] != tier:
            raise CoordinatorError("lane and receipt tier do not agree")
        self._check_tier(recipient_id, tier)

        # The manifest is the only source of a lane limit.  Compatibility
        # arguments remain accepted for callers that still spell out the
        # receipt budget, but a mismatch is an integrity error rather than a
        # second process-local policy.
        declared_budget = self.manifest.lane_budgets.get(lane)
        if declared_budget is None:
            raise CoordinatorError("manifest has no budget for lane " + lane)
        if budget_unit is not None and budget_unit != declared_budget.unit:
            raise CoordinatorError("receipt budget unit differs from immutable manifest lane budget")
        if budget_limit is not None:
            if isinstance(budget_limit, bool) or not isinstance(budget_limit, int):
                raise CoordinatorError("receipt budget limit must be an integer")
            if budget_limit != declared_budget.limit:
                raise CoordinatorError("receipt budget limit differs from immutable manifest lane budget")
        budget_unit = declared_budget.unit
        budget_limit = declared_budget.limit
        if budget_consumed is None:
            budget_consumed = 0
        if isinstance(budget_consumed, bool) or not isinstance(budget_consumed, int):
            raise CoordinatorError("receipt budget consumed must be an integer")
        if budget_consumed < 0 or budget_consumed > budget_limit:
            raise CoordinatorError("receipt budget is outside its declared limit")

        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 0:
            raise CoordinatorError("receipt attempts must be nonnegative")
        input_ids = tuple(input_identities)
        if not input_ids or len(set(input_ids)) != len(input_ids):
            raise CoordinatorError("receipt input identities must be nonempty and unique")
        try:
            for identity in input_ids:
                validate_hash(identity, "receipt input identity")
        except ValueError as exc:
            raise CoordinatorError("receipt input identity is not a content hash") from exc

        if rejection_counts is None:
            rejection_counts = {}
        if not isinstance(rejection_counts, Mapping):
            raise CoordinatorError("receipt rejection_counts must be a mapping")
        normalized_rejections: Dict[str, int] = {}
        for key, value in rejection_counts.items():
            if not isinstance(key, str) or not key:
                raise CoordinatorError("receipt rejection class must be a nonempty string")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise CoordinatorError("receipt rejection counts must be nonnegative integers")
            normalized_rejections[key] = value
        normalized_rejections = dict(sorted(normalized_rejections.items()))

        normalized_best = tuple(best_candidate_ids)
        if len(set(normalized_best)) != len(normalized_best):
            raise CoordinatorError("receipt best candidates must be unique")
        try:
            for candidate_id in normalized_best:
                validate_hash(candidate_id, "receipt best candidate")
        except ValueError as exc:
            raise CoordinatorError("receipt best candidate is not a content hash") from exc

        # Tool provenance is explicit and lane-scoped.  A receipt never
        # inherits unrelated manifest entries such as full_oracle or
        # search_pattern_report.
        manifest_tools = dict(sorted(self.manifest.tool_identities.items()))
        if not isinstance(tool_identities, Mapping) or not tool_identities:
            raise CoordinatorError("receipt tool_identities must be explicit and nonempty")
        normalized_tools = {}
        for key, value in tool_identities.items():
            if not isinstance(key, str) or key not in manifest_tools:
                raise CoordinatorError("receipt tool identity is not bound by the manifest")
            try:
                validate_hash(value, "receipt tool identity")
            except ValueError as exc:
                raise CoordinatorError("receipt tool identity is invalid") from exc
            if manifest_tools[key] != value:
                raise CoordinatorError("receipt tool identity differs from manifest binding")
            normalized_tools[key] = value
        normalized_tools = dict(sorted(normalized_tools.items()))
        expected_tool_keys = set(LANE_TOOL_KEYS.get(lane, ()))
        if set(normalized_tools) != expected_tool_keys:
            raise CoordinatorError(
                "receipt tool identities must exactly match the lane manifest contract"
            )

        budget = Budget(budget_unit, budget_limit, budget_consumed)
        receipt_identity = {
            "recipient_id": recipient_id,
            "lane": lane,
            "tier": tier,
            "tool_identities": normalized_tools,
            "config_identity": self.manifest.config_identity,
            "input_identities": list(input_ids),
            "budget": budget.to_dict(),
            "attempts": attempts,
            "rejection_counts": normalized_rejections,
            "best_candidate_ids": list(normalized_best),
            "complete": True,
            "completion_reason": completion_reason,
        }
        receipt_id = hash_canonical(receipt_identity)
        existing_receipt = self._receipts.get((recipient_id, lane))
        if existing_receipt is not None:
            if existing_receipt.receipt_id != receipt_id:
                raise CoordinatorError("receipt identity differs from completed lane")
            return existing_receipt

        # Exercise the complete typed receipt validation before creating the
        # artifact.  The placeholder is never published or referenced.
        preflight_artifact = ArtifactRef(
            hash_canonical({"receipt_preflight": receipt_id}),
            "artifacts/receipts/.preflight.json",
            "application/json",
            0,
        )
        ExhaustionReceipt(
            receipt_id=receipt_id,
            recipient_id=recipient_id,
            lane=lane,
            tier=tier,
            tool_identities=normalized_tools,
            config_identity=self.manifest.config_identity,
            input_identities=input_ids,
            budget=budget,
            attempts=attempts,
            rejection_counts=normalized_rejections,
            best_candidate_ids=normalized_best,
            complete=True,
            completion_reason=completion_reason,
            receipt_artifact=preflight_artifact,
        )

        self._fault("before_exhaustion_artifact")
        artifact = self.archive.put_receipt(dict(receipt_identity, receipt_id=receipt_id))
        self._fault("after_exhaustion_artifact")
        receipt = ExhaustionReceipt(
            receipt_id=receipt_id,
            recipient_id=recipient_id,
            lane=lane,
            tier=tier,
            tool_identities=normalized_tools,
            config_identity=self.manifest.config_identity,
            input_identities=input_ids,
            budget=budget,
            attempts=attempts,
            rejection_counts=normalized_rejections,
            best_candidate_ids=normalized_best,
            complete=True,
            completion_reason=completion_reason,
            receipt_artifact=artifact,
        )
        self._fault("before_exhaustion_event")
        self._append_event_once("exhaustion_recorded", receipt, event_id=f"{receipt_id}:exhaustion")
        self._fault("after_exhaustion_event")
        self._receipts[(recipient_id, lane)] = receipt
        self._tier_completed[(recipient_id, tier)] = True
        self._lane_yield[(recipient_id, lane)] = (len(receipt.best_candidate_ids), receipt.attempts)
        return receipt

    def pending_task_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(task_id for task_id in self._scheduled if task_id not in self._terminal))

    def write_checkpoint(self) -> LedgerEvent:
        self._ensure_no_stop_for_mutation("checkpoint")
        events = self.ledger.events()
        if not events:
            raise CoordinatorError("cannot checkpoint an empty ledger")
        if events[-1].event_type == "checkpoint_committed":
            return events[-1]
        through = events[-1]
        snapshot = self.state_dict()
        snapshot["through_sequence"] = through.sequence
        snapshot["through_event_hash"] = through.event_hash
        self._fault("before_checkpoint_write")
        self._fault("before_checkpoint_publish")
        artifact = self.archive.put_json(snapshot, category="checkpoints", suffix=".json")
        self._fault("after_checkpoint_publish")
        self._fault("after_checkpoint_write")
        from .search_types import Checkpoint

        payload = Checkpoint(through.sequence, through.event_hash, artifact)
        self._fault("before_checkpoint_event")
        event = self._append_event_once(
            "checkpoint_committed",
            payload,
            event_id=f"{self.manifest.run_id}:checkpoint:{through.sequence}",
        )
        self._fault("after_checkpoint_event")
        return event

    def stop(self, *, reason: str = "graceful_stop", resumable: Optional[bool] = None) -> LedgerEvent:
        if resumable is None:
            resumable = reason == "graceful_stop"
        existing_stop = next((event for event in reversed(self.events) if event.event_type == "run_stopped"), None)
        if existing_stop is not None:
            return existing_stop
        self._fault("before_run_stop")
        self._fault("before_graceful_stop")
        self._fault("before_run_stop_snapshot")
        budget_snapshot = self.archive.put_json(
            {"consumed_task_ids": sorted(self._consumed), "pending_task_ids": self.pending_task_ids()},
            category="receipts",
            suffix=".budget.json",
        )
        self._fault("after_run_stop_snapshot")
        pending = self.pending_task_ids()
        last = None
        for committed in reversed(self.events):
            if committed.event_type == "task_completed":
                last = committed.payload.task_id  # type: ignore[union-attr]
                break
        payload = RunStop(reason, last, pending, budget_snapshot.content_hash, bool(resumable))
        self._fault("before_run_stop_event")
        event = self.ledger.append_event("run_stopped", payload, event_id=f"{self.manifest.run_id}:stopped:{len(self.events)}")
        # The stop is authoritative as soon as its ledger event is durable,
        # including when a later fault interrupts the caller.
        self._stopped = payload
        self._fault("after_run_stop_event")
        self._fault("after_graceful_stop")
        self._fault("after_run_stop")
        return event

    def state_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.manifest.run_id,
            "scheduled_task_ids": sorted(self._scheduled),
            "started_task_ids": sorted(self._started),
            "completed_task_ids": sorted(self._terminal),
            "pending_task_ids": list(self.pending_task_ids()),
            "consumed_budget_task_ids": sorted(self._consumed),
            "scalar_elite_candidate_id": self.frontier.scalar_elite_id,
            "pareto_candidate_ids": list(self.frontier.pareto_ids),
            "oracle_candidate_ids": list(self._oracle_candidates),
            "oracle_requests": [
                request.to_dict()
                for request in sorted(self._oracle_requests.values(), key=lambda item: item.request_id)
            ],
            "oracle_results": [
                receipt.to_dict()
                for receipt in sorted(self._oracle_results.values(), key=lambda item: item.request_id)
            ],
            "receipt_ids": sorted(receipt.receipt_id for receipt in self._receipts.values()),
            "receipts": [receipt.to_dict() for receipt in sorted(self._receipts.values(), key=lambda item: item.receipt_id)],
            "frontier_candidates": [candidate.to_dict() for candidate in self.frontier.graph.all()],
            "cache_entries": [
                {"key": list(key), "value": value.to_dict() if hasattr(value, "to_dict") else value}
                for key, value in self.frontier.cache.items()
            ],
            "budget_claims": [
                {"ordinal": ordinal, "task_id": task_id}
                for ordinal, task_id in sorted(self._budget_claims.items())
            ],
            "stopped": self._stopped.to_dict() if self._stopped is not None else None,
        }

    @property
    def pending_oracle_candidate_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(set(self._oracle_candidates)))


Coordinator = SearchCoordinator


__all__ = [
    "CoordinatorError", "TierBlocked", "BudgetExhausted", "ExplicitSubsetError",
    "OracleRequired", "LANE_TIERS", "DURABLE_FAULT_POINTS", "ORACLE_FAULT_POINTS", "FAULT_POINTS",
    "FULL_ORACLE_TOOL_IDENTITY", "SEARCH_PATTERN_REPORT_TOOL_IDENTITY",
    "TaskResult", "DurableOracle", "SearchCoordinator", "Coordinator",
    "validate_task_binding", "validate_ledger_prefix",
]
