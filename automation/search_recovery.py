"""Recovery and checkpoint validation for instrumented search runs."""

from __future__ import annotations

from contextvars import ContextVar
import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .search_archive import ContentAddressedArchive, ArchiveError, InvalidArtifactPath
from .search_coordinator import (
    CoordinatorError,
    DURABLE_FAULT_POINTS,
    LANE_TIERS,
    SearchCoordinator,
    validate_ledger_prefix,
    validate_task_binding,
)
from .search_frontier import SearchFrontier, frontier_from_events
from .search_ledger import AppendOnlyLedger, LedgerIntegrityError
from .search_types import (
    ArtifactRef,
    CandidateRecord,
    Checkpoint,
    ExhaustionReceipt,
    LANE_TOOL_KEYS,
    LedgerEvent,
    OracleReceipt,
    OracleRequest,
    ParentRun,
    RunManifest,
    RunResume,
    RunStop,
    SearchTask,
    TaskTerminal,
    canonical_json,
    hash_canonical,
    iter_artifact_refs,
)


class RecoveryError(RuntimeError):
    """Base class for recovery failures."""


class ResumeRefused(RecoveryError):
    """Inputs no longer match the immutable run manifest."""


class CheckpointInvalid(RecoveryError):
    """A checkpoint does not describe a valid ledger prefix."""


class InjectedFault(RecoveryError):
    """A named fault point deliberately stopped a scenario."""


FAULT_POINTS = DURABLE_FAULT_POINTS

_FACTORY_TOOL_KEY = "search_run_factory"
_FACTORY_MARKER_KEY = "search_run_factory_marker"
_PROVIDER_VALIDATION_ACTIVE: ContextVar[bool] = ContextVar(
    "search_recovery_provider_validation_active",
    default=False,
)


class FaultInjector:
    """Raise once at configured transition names for fault-injection tests."""

    def __init__(self, *points: str, repeat: bool = False) -> None:
        self.points = set(points)
        self.repeat = repeat
        self.seen: List[str] = []

    def __call__(self, point: str, *args: Any) -> None:
        self.seen.append(point)
        if point in self.points:
            if not self.repeat:
                self.points.remove(point)
            raise InjectedFault(point)


@dataclass(frozen=True)
class RecoveryState:
    run_root: Path
    manifest: RunManifest
    events: Tuple[LedgerEvent, ...]
    tasks: Mapping[str, SearchTask]
    terminal_tasks: Mapping[str, TaskTerminal]
    incomplete_tasks: Tuple[SearchTask, ...]
    frontier: SearchFrontier
    receipts: Tuple[ExhaustionReceipt, ...]
    last_sequence: int
    last_event_hash: Optional[str]
    consumed_budget_ordinals: Tuple[Tuple[str, str, int], ...]
    pending_oracle_candidate_ids: Tuple[str, ...] = ()
    stopped: Optional[RunStop] = None
    oracle_requests: Mapping[str, OracleRequest] = field(default_factory=dict)
    oracle_results: Mapping[str, OracleReceipt] = field(default_factory=dict)

    def reissue_tasks(self) -> Tuple[SearchTask, ...]:
        """Return incomplete tasks with their original IDs, seeds and ordinals."""
        return tuple(replace(task, state="scheduled") for task in self.incomplete_tasks)

    @property
    def scheduled_task_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self.tasks))

    @property
    def completed_task_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self.terminal_tasks))


def _load_manifest(run_root: Path) -> RunManifest:
    path = run_root / "manifest.json"
    try:
        return RunManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise RecoveryError("run manifest is missing") from exc
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        raise RecoveryError("run manifest is invalid") from exc


def _establish_factory_manifest(
    run_root: Path,
    manifest: RunManifest,
) -> tuple[RunManifest, bool]:
    """Verify the immutable factory archive before replaying a factory run."""

    factory_created = any(
        key in manifest.tool_identities
        for key in (_FACTORY_TOOL_KEY, _FACTORY_MARKER_KEY)
    )
    if not factory_created:
        return manifest, False
    try:
        try:
            from .search_run_factory import verify_factory_archive
        except ImportError:  # pragma: no cover - direct script compatibility
            from search_run_factory import verify_factory_archive  # type: ignore
        verified = verify_factory_archive(run_root, manifest)
    except Exception as exc:  # typed factory refusal domains differ here
        raise RecoveryError("factory archive validation failed during recovery") from exc
    if not isinstance(verified, RunManifest):
        raise RecoveryError("factory archive validator returned an untyped manifest")
    return verified, True


def _verify_factory_provider(manifest: RunManifest, run_root: Path) -> None:
    """Revalidate registry-backed providers before accepting recovered state."""

    if _PROVIDER_VALIDATION_ACTIVE.get():
        # Canonical gate validation recovers the same run to inspect its
        # terminal proof.  The outer recovery already owns provider
        # revalidation, so nested evidence recovery must not recurse into the
        # provider registry a second time.
        return
    token = _PROVIDER_VALIDATION_ACTIVE.set(True)
    try:
        try:
            from .search_provider_lanes import verify_lane_provider
        except ImportError:  # pragma: no cover - direct script compatibility
            from search_provider_lanes import verify_lane_provider  # type: ignore
        verify_lane_provider(manifest, run_root)
    except Exception as exc:  # provider refusal domains differ by lane
        raise RecoveryError(
            "factory-created provider state could not be revalidated"
        ) from exc
    finally:
        _PROVIDER_VALIDATION_ACTIVE.reset(token)


def _validate_artifacts(events: Sequence[LedgerEvent], archive: ContentAddressedArchive) -> None:
    for event in events:
        for reference in iter_artifact_refs(event.payload):
            try:
                archive.verify(reference)
            except ArchiveError as exc:
                # Checkpoints are accelerators, never authority.  A deleted
                # or incomplete checkpoint must be ignored while the ledger
                # prefix remains fully recoverable from its durable events.
                if event.event_type == "checkpoint_committed":
                    continue
                raise RecoveryError(f"missing or corrupt artifact: {reference.path}") from exc
        if event.event_type == "run_stopped":
            stop = event.payload
            assert isinstance(stop, RunStop)
            valid = False
            digest = stop.budget_snapshot_hash.removeprefix("sha256:")
            # Deduplication may return an existing canonical `.json` path
            # instead of the requested `.budget.json` suffix.  The stop record
            # carries the content hash, so search the whole receipt store and
            # verify bytes rather than guessing a filename.
            try:
                receipt_root = archive._checked_path(archive.artifacts_root / "receipts")
            except InvalidArtifactPath as exc:
                raise RecoveryError("receipt artifact path escaped run root") from exc
            if receipt_root.is_dir():
                for path in receipt_root.rglob("*"):
                    try:
                        checked = archive._checked_path(path)
                    except InvalidArtifactPath as exc:
                        raise RecoveryError("receipt artifact path escaped run root") from exc
                    if not checked.is_file() or digest not in checked.name:
                        continue
                    try:
                        data = checked.read_bytes()
                    except OSError:
                        continue
                    if "sha256:" + hashlib.sha256(data).hexdigest() == stop.budget_snapshot_hash:
                        valid = True
                        break
            if not valid:
                raise RecoveryError("missing or corrupt budget snapshot artifact")


def _compare_identity(manifest: RunManifest, expected: Any) -> None:
    if expected is None:
        return
    expected_manifest = expected if isinstance(expected, RunManifest) else None

    def values_for(value: RunManifest) -> Dict[str, Any]:
        return {
            "queue_record_ids": tuple(value.queue_record_ids),
            "function_ids": tuple(value.function_ids),
            "subset_identity": value.subset_identity,
            "queue_evidence_identity": value.queue_evidence_identity,
            "selected_lanes": tuple(value.selected_lanes),
            "source_identity": value.source_identity,
            "target_identities": dict(value.target_identities),
            "compiler_identity": value.compiler_identity,
            "tool_identities": dict(value.tool_identities),
            "config_identity": value.config_identity,
            "schema_identity": value.schema_identity,
            "coordinator_budget": value.coordinator_budget.to_dict(),
            "lane_budgets": {
                lane: budget.to_dict()
                for lane, budget in value.lane_budgets.items()
            },
            "epoch_size": value.epoch_size,
            "frontier_cap": value.frontier_cap,
            "tier_order": tuple(value.tier_order),
        }

    values = values_for(manifest)
    if expected_manifest is not None:
        expected_values = values_for(expected_manifest)
    elif isinstance(expected, Mapping):
        expected_values = dict(expected)
    else:
        raise ResumeRefused("expected identity must be a manifest or mapping")

    for key, expected_value in expected_values.items():
        if key not in values:
            continue
        actual = values[key]
        if key in {"queue_record_ids", "function_ids"}:
            # Queue/function subsets are canonicalized by RunManifest, so an
            # expected identity mapping may use either input order without
            # changing the frozen selection identity.
            expected_value = tuple(sorted(expected_value))
        elif key in {"selected_lanes", "tier_order"}:
            expected_value = tuple(expected_value)
        elif key in {"target_identities", "tool_identities"}:
            expected_value = dict(expected_value)
        elif key == "coordinator_budget":
            expected_value = (
                expected_value.to_dict()
                if hasattr(expected_value, "to_dict")
                else dict(expected_value)
            )
        elif key == "lane_budgets":
            expected_value = {
                lane: (
                    budget.to_dict()
                    if hasattr(budget, "to_dict")
                    else dict(budget)
                )
                for lane, budget in dict(expected_value).items()
            }
        if actual != expected_value:
            raise ResumeRefused(f"resume identity changed: {key}")

def _pending_oracle_candidate_ids(
    events: Sequence[LedgerEvent],
    frontier: SearchFrontier,
    terminal_tasks: Mapping[str, TaskTerminal],
) -> Tuple[str, ...]:
    """Return score-zero candidates whose oracle task is not terminal.

    Candidate records are immutable evidence and therefore keep their
    zero-pending status even after a successful handoff. The task terminal
    event is the durable boundary that clears the pending work.
    """
    evaluation_tasks: Dict[str, List[str]] = {}
    candidate_tasks: Dict[str, List[str]] = {}
    for event in events:
        if event.event_type == "evaluation_completed":
            evaluation = event.payload
            assert hasattr(evaluation, "candidate_id")
            evaluation_tasks.setdefault(evaluation.candidate_id, []).append(evaluation.task_id)
        elif event.event_type == "candidate_materialized":
            candidate = event.payload
            assert isinstance(candidate, CandidateRecord)
            marker = ":materialized:"
            if marker in event.event_id:
                candidate_tasks.setdefault(candidate.candidate_id, []).append(
                    event.event_id.rsplit(marker, 1)[1]
                )
    terminal_ids = set(terminal_tasks)
    pending = []
    for candidate in frontier.graph.all():
        score_zero = (
            candidate.status == "zero_pending_oracle"
            or (
                candidate.evaluation is not None
                and candidate.evaluation.compile_status == "success"
                and candidate.evaluation.total == 0
            )
        )
        if not score_zero:
            continue
        task_ids = list(evaluation_tasks.get(candidate.candidate_id, ()))
        task_ids.extend(candidate_tasks.get(candidate.candidate_id, ()))
        if not task_ids or any(task_id not in terminal_ids for task_id in task_ids):
            pending.append(candidate.candidate_id)
    return tuple(sorted(set(pending)))


def recover_run(
    run_root: Union[str, os.PathLike[str]],
    *,
    expected_identity: Any = None,
    strict_checkpoints: bool = False,
) -> RecoveryState:
    """Reconstruct authoritative state from manifest, ledger and artifacts."""
    root = Path(run_root)
    manifest = _load_manifest(root)
    manifest, factory_created = _establish_factory_manifest(root, manifest)
    _compare_identity(manifest, expected_identity)
    archive = ContentAddressedArchive(root)
    ledger = AppendOnlyLedger(root / "ledger.jsonl", run_id=manifest.run_id, archive=archive)
    try:
        events = ledger.verify()
    except LedgerIntegrityError as exc:
        raise RecoveryError("ledger integrity validation failed") from exc
    if not events:
        raise RecoveryError("ledger is empty")
    if not isinstance(events[0].payload, RunManifest) or events[0].payload != manifest:
        raise RecoveryError("manifest and run_started disagree")
    _validate_artifacts(events, archive)
    try:
        # Keep restart validation identical to coordinator reopen.  The
        # generic artifact pass above handles all ordinary references; this
        # shared pass adds lifecycle, ancestry and exact oracle/receipt bytes.
        validate_ledger_prefix(
            manifest,
            events,
            archive=archive,
            verify_artifacts=False,
        )
    except CoordinatorError as exc:
        raise RecoveryError("ledger prefix violates persisted search invariants") from exc
    if factory_created:
        _verify_factory_provider(manifest, root)

    tasks: Dict[str, SearchTask] = {}
    terminal: Dict[str, TaskTerminal] = {}
    interrupted = set()
    receipts: List[ExhaustionReceipt] = []
    consumed: List[Tuple[str, str, int]] = []
    budget_claims: Dict[int, str] = {}
    stopped: Optional[RunStop] = None
    oracle_requests: Dict[str, OracleRequest] = {}
    oracle_results: Dict[str, OracleReceipt] = {}
    for event in events:
        if event.event_type in ("task_scheduled", "task_started"):
            task = event.payload
            assert isinstance(task, SearchTask)
            try:
                validate_task_binding(manifest, task)
            except CoordinatorError as exc:
                raise RecoveryError("ledger task binding differs from immutable manifest") from exc
            prior_budget_task = budget_claims.get(task.budget_ordinal)
            if prior_budget_task is not None and prior_budget_task != task.task_id:
                raise RecoveryError(
                    "ledger reuses a global budget ordinal for different tasks"
                )
            budget_claims[task.budget_ordinal] = task.task_id
            existing = tasks.get(task.task_id)
            if event.event_type == "task_started" and existing is None:
                raise RecoveryError("task started before it was scheduled")
            if event.event_type == "task_scheduled" and existing is not None:
                raise RecoveryError("task was scheduled more than once")
            if existing is not None:
                if event.event_type == "task_started" and existing.state == "started":
                    raise RecoveryError("task was started more than once")
                # The lifecycle state is expected to change from scheduled to
                # started.  All identity-bearing fields must remain byte for
                # byte identical across those events.
                if replace(existing, state="scheduled") != replace(task, state="scheduled"):
                    raise RecoveryError("task identity changed in ledger")
                if task.state == "started":
                    tasks[task.task_id] = task
            else:
                tasks[task.task_id] = task
        elif event.event_type == "task_interrupted":
            interruption = event.payload
            assert hasattr(interruption, "task_id")
            if interruption.task_id not in tasks:
                raise RecoveryError("interruption names an unknown task")
            interrupted.add(interruption.task_id)
        elif event.event_type == "task_completed":
            completed = event.payload
            assert isinstance(completed, TaskTerminal)
            if completed.task_id not in tasks:
                raise RecoveryError("terminal result names an unknown task")
            existing = terminal.get(completed.task_id)
            if existing is not None and existing != completed:
                raise RecoveryError("duplicate terminal result differs")
            terminal[completed.task_id] = completed
            task = tasks.get(completed.task_id)
            if task is not None:
                consumed.append((task.recipient_id, task.lane, task.budget_ordinal))
        elif event.event_type == "oracle_requested":
            request = event.payload
            assert isinstance(request, OracleRequest)
            existing = oracle_requests.get(request.request_id)
            if existing is not None and existing != request:
                raise RecoveryError("oracle request identity maps to different payload")
            oracle_requests[request.request_id] = request
        elif event.event_type == "oracle_result_recorded":
            receipt = event.payload
            assert isinstance(receipt, OracleReceipt)
            if receipt.request_id not in oracle_requests:
                raise RecoveryError("oracle result has no durable request")
            existing = oracle_results.get(receipt.request_id)
            if existing is not None and existing != receipt:
                raise RecoveryError("oracle request has different durable results")
            oracle_results[receipt.request_id] = receipt
        elif event.event_type == "exhaustion_recorded":
            receipt = event.payload
            assert isinstance(receipt, ExhaustionReceipt)
            if receipt.recipient_id not in manifest.queue_record_ids:
                raise RecoveryError("receipt names a recipient outside the manifest subset")
            if receipt.lane not in manifest.selected_lanes:
                raise RecoveryError("receipt names a lane outside the manifest selection")
            if receipt.tier != LANE_TIERS.get(receipt.lane):
                raise RecoveryError("receipt lane and tier do not agree")
            if receipt.config_identity != manifest.config_identity:
                raise RecoveryError("receipt config differs from immutable manifest")
            declared_budget = manifest.lane_budgets.get(receipt.lane)
            if declared_budget is None:
                raise RecoveryError("receipt names a lane without a manifest budget")
            if (
                receipt.budget.unit != declared_budget.unit
                or receipt.budget.limit != declared_budget.limit
            ):
                raise RecoveryError("receipt budget differs from immutable manifest lane budget")
            expected_tool_keys = set(LANE_TOOL_KEYS.get(receipt.lane, ()))
            if set(receipt.tool_identities) != expected_tool_keys:
                raise RecoveryError("receipt tools differ from the lane manifest contract")
            for key, value in receipt.tool_identities.items():
                if manifest.tool_identities.get(key) != value:
                    raise RecoveryError("receipt tool identity differs from manifest binding")
            existing_receipt = next(
                (item for item in receipts if item.recipient_id == receipt.recipient_id and item.lane == receipt.lane),
                None,
            )
            if existing_receipt is not None and existing_receipt != receipt:
                raise RecoveryError("duplicate exhaustion receipt differs")
            if existing_receipt is None:
                receipts.append(receipt)
        elif event.event_type == "run_stopped":
            candidate_stop = event.payload
            assert isinstance(candidate_stop, RunStop)
            if stopped is not None and stopped != candidate_stop:
                raise RecoveryError("run has multiple active stop records")
            stopped = candidate_stop
        elif event.event_type == "run_resumed":
            resume = event.payload
            assert isinstance(resume, RunResume)
            stopped = None

    incomplete = [
        task
        for task_id, task in tasks.items()
        if task_id not in terminal
    ]
    # An interruption is deliberately non-terminal.  Keeping the task in the
    # same set makes both scheduled-only and started-only process loss replay
    # through exactly the original task identity.
    incomplete.sort(key=lambda task: task.task_id)
    frontier = frontier_from_events(events, cap=manifest.frontier_cap)
    pending_oracle = _pending_oracle_candidate_ids(events, frontier, terminal)
    latest = events[-1]
    state = RecoveryState(
        run_root=root,
        manifest=manifest,
        events=tuple(events),
        tasks=dict(tasks),
        terminal_tasks=dict(terminal),
        incomplete_tasks=tuple(incomplete),
        frontier=frontier,
        receipts=tuple(receipts),
        last_sequence=latest.sequence,
        last_event_hash=latest.event_hash,
        consumed_budget_ordinals=tuple(sorted(set(consumed))),
        pending_oracle_candidate_ids=pending_oracle,
        stopped=stopped,
        oracle_requests=dict(oracle_requests),
        oracle_results=dict(oracle_results),
    )
    for event in events:
        if event.event_type == "checkpoint_committed":
            try:
                validate_checkpoint(root, event, events, archive)
            except CheckpointInvalid:
                if strict_checkpoints:
                    raise
    return state


def validate_checkpoint(
    run_root: Union[str, os.PathLike[str]],
    event: Union[LedgerEvent, Checkpoint],
    events: Sequence[LedgerEvent],
    archive: Optional[ContentAddressedArchive] = None,
) -> Mapping[str, Any]:
    """Validate a checkpoint artifact and its exact ledger prefix."""
    root = Path(run_root)
    if archive is None:
        archive = ContentAddressedArchive(root)
    checkpoint = event.payload if isinstance(event, LedgerEvent) else event
    if not isinstance(checkpoint, Checkpoint):
        raise CheckpointInvalid("event is not a checkpoint")
    if checkpoint.through_sequence >= len(events):
        raise CheckpointInvalid("checkpoint sequence is beyond ledger")
    through = events[checkpoint.through_sequence]
    if through.event_hash != checkpoint.through_event_hash:
        raise CheckpointInvalid("checkpoint prefix hash differs")
    try:
        raw = archive.verify(checkpoint.checkpoint_artifact)
        value = json.loads(raw.decode("utf-8"))
    except (ArchiveError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckpointInvalid("checkpoint artifact is unreadable") from exc
    if value.get("through_sequence") != checkpoint.through_sequence:
        raise CheckpointInvalid("checkpoint content sequence differs")
    if value.get("through_event_hash") != checkpoint.through_event_hash:
        raise CheckpointInvalid("checkpoint content hash differs")
    return value


def latest_checkpoint(
    run_root: Union[str, os.PathLike[str]],
    state: Optional[RecoveryState] = None,
    *,
    strict: bool = False,
) -> Optional[Mapping[str, Any]]:
    if state is None:
        state = recover_run(run_root, strict_checkpoints=strict)
    archive = ContentAddressedArchive(Path(run_root))
    for event in reversed(state.events):
        if event.event_type != "checkpoint_committed":
            continue
        try:
            return validate_checkpoint(Path(run_root), event, state.events, archive)
        except CheckpointInvalid:
            if strict:
                raise
    return None


def fork_run(
    source_root: Union[str, os.PathLike[str]],
    destination_root: Union[str, os.PathLike[str]],
    *,
    manifest: Optional[Union[RunManifest, Mapping[str, Any]]] = None,
    run_id: Optional[str] = None,
) -> SearchCoordinator:
    """Start a new immutable run while recording the parent prefix."""
    parent = recover_run(source_root)
    destination = Path(destination_root)
    if destination.exists() and any(destination.iterdir()):
        raise RecoveryError("fork destination must be empty")
    if manifest is None:
        from datetime import datetime, timezone

        new_id = run_id or hash_canonical({"parent": parent.manifest.run_id, "sequence": parent.last_sequence})
        new_manifest = replace(
            parent.manifest,
            run_id=new_id,
            created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            parent_run=ParentRun(parent.manifest.run_id, parent.last_sequence, parent.last_event_hash or parent.events[0].event_hash),
        )
    else:
        new_manifest = manifest if isinstance(manifest, RunManifest) else RunManifest.from_dict(manifest)
        expected_parent = ParentRun(
            parent.manifest.run_id,
            parent.last_sequence,
            parent.last_event_hash or parent.events[0].event_hash,
        )
        if new_manifest.parent_run is not None and new_manifest.parent_run != expected_parent:
            raise ResumeRefused("fork parent_run does not name the exact parent prefix")
        if new_manifest.source_identity != parent.manifest.source_identity:
            raise ResumeRefused("fork source identity does not match the parent source prefix")
        if new_manifest.parent_run is None:
            new_manifest = replace(
                new_manifest,
                parent_run=expected_parent,
            )
    return SearchCoordinator(destination, new_manifest)


recover = recover_run
fork = fork_run


__all__ = [
    "RecoveryError", "ResumeRefused", "CheckpointInvalid", "InjectedFault", "FAULT_POINTS", "FaultInjector",
    "RecoveryState", "recover_run", "recover", "validate_checkpoint", "latest_checkpoint",
    "fork_run", "fork", "validate_task_binding", "validate_ledger_prefix",
]
