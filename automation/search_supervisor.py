#!/usr/bin/env python3
"""Supervisor integration for typed, manifest-bound search runs.

This module deliberately owns no search state. The manifest, append-only ledger
and immutable artifacts remain authoritative. Its only persistent state outside
a run is an advisory ownership registry used to prevent legacy and instrumented
schedulers from overlapping.
"""
from __future__ import annotations

import functools
import json
import os
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Tuple

try:
    from .search_archive import ContentAddressedArchive
    from .search_cli import _load_manifest_file, _safe_run_root
    from .search_coordinator import LANE_TIERS, SearchCoordinator, TaskResult
    from .search_lanes import (
        LaneAdapters,
        LaneCandidate,
        LaneOutcome,
        LaneReceiptProposal,
        LaneRefusal,
        Recipient,
        execute_task,
    )
    from .search_recovery import recover_run
    from .search_types import (
        ArtifactRef,
        CandidateRecord,
        LANES,
        LedgerEvent,
        MAX_CHILD_TASKS_PER_BASE,
        MAX_COORDINATOR_TASKS,
        SearchTask,
        TIER_ORDER,
        OracleRequest,
        RunStop,
        RunResume,
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_run_id,
    )
except ImportError:  # pragma: no cover - direct script compatibility
    from search_archive import ContentAddressedArchive  # type: ignore
    from search_cli import _load_manifest_file, _safe_run_root  # type: ignore
    from search_coordinator import LANE_TIERS, SearchCoordinator, TaskResult  # type: ignore
    from search_lanes import (  # type: ignore
        LaneAdapters,
        LaneCandidate,
        LaneOutcome,
        LaneReceiptProposal,
        LaneRefusal,
        Recipient,
        execute_task,
    )
    from search_recovery import recover_run  # type: ignore
    from search_types import (  # type: ignore
        ArtifactRef,
        CandidateRecord,
        LANES,
        LedgerEvent,
        MAX_CHILD_TASKS_PER_BASE,
        MAX_COORDINATOR_TASKS,
        SearchTask,
        TIER_ORDER,
        OracleRequest,
        RunStop,
        RunResume,
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_run_id,
    )


LEGACY_MODE = "legacy"
INSTRUMENTED_MODE = "instrumented"
MODE_TOOL_KEY = "search_supervisor_mode"
LEASE_PROTOCOL = "search-supervisor-lease-v1"
ORACLE_PROTOCOL = "landing-oracle-v1"
TASK_RESULT_PROTOCOL = "search-supervisor-task-result-v1"
STOP_REQUEST_PROTOCOL = "search-supervisor-stop-request-v1"
STOP_REQUEST_FILENAME = "stop-request.json"
STOP_REQUEST_REASON = "graceful_stop"
STOP_REQUEST_PENDING = "pending"
STOP_REQUEST_ACKNOWLEDGED = "acknowledged"
GATE_RECEIPT_PROTOCOL = "search-supervisor-integration-gate-v1"
# Gate kinds are deliberately closed.  A receipt is either the one-record
# smoke proof or the bounded multi-record completed-run proof; a boolean such
# as the old ``multi_record`` flag was too easy to forge or misread.
GATE_KIND_SMOKE = "smoke"
GATE_KIND_MULTI_RECORD = "multi_record"
_GATE_KINDS = frozenset((GATE_KIND_SMOKE, GATE_KIND_MULTI_RECORD))
# The factory keeps these bindings in the manifest tool map.  They are kept as
# literals here so gate issuance cannot accidentally trust a caller-provided
# marker or define a parallel factory protocol.
_FACTORY_TOOL_KEY = "search_run_factory"
_FACTORY_MARKER_KEY = "search_run_factory_marker"
# Reserved manifest tool key for evaluator/scorer provenance.  Deliberately
# distinct from the ``full_oracle`` landing authority: a completed run may
# carry full oracle evidence and still lack evaluator provenance for its
# score vectors, which is a diagnostic, not a promotion-eligible context.
EVALUATOR_TOOL_KEY = "search_evaluator"
# Factory-created manifests are globally bounded, including their child-task
# allowance.  Keep the supervisor defensive when handed a forged manifest.
# The cap itself is shared with factory admission through search_types.
_MAX_COORDINATOR_TASKS = MAX_COORDINATOR_TASKS
DEFAULT_LEASE_PATH = Path(
    os.environ.get(
        "SOTN_SEARCH_SUPERVISOR_LEASE",
        str(Path.home() / "sotn-work" / "search-supervisor-owners.json"),
    )
)
TerminalPersistence = Callable[[str, str], None]
LandingCallback = Callable[
    [str, str, TerminalPersistence],
    Tuple[bool, str],
]


class SupervisorIntegrationError(RuntimeError):
    """The supervisor integration boundary refused an unsafe operation."""


class SupervisorConflict(SupervisorIntegrationError):
    """Another live owner overlaps this run."""


class SupervisorModeError(SupervisorIntegrationError):
    """A manifest or invocation does not bind one explicit mode."""


class DurableOracleError(SupervisorIntegrationError):
    """The durable landing oracle store is missing, stale or corrupt."""


class IntegrationGateError(SupervisorIntegrationError):
    """The canonical integration receipt is missing, changed or unverifiable."""


def mode_identity(mode: str) -> str:
    if mode not in {LEGACY_MODE, INSTRUMENTED_MODE}:
        raise SupervisorModeError("unknown supervisor mode")
    return hash_canonical(
        {"protocol": "search-supervisor-mode-v1", "mode": mode}
    )


def require_instrumented_manifest(manifest: RunManifest) -> None:
    actual = manifest.tool_identities.get(MODE_TOOL_KEY)
    expected = mode_identity(INSTRUMENTED_MODE)
    if actual != expected:
        raise SupervisorModeError(
            "instrumented manifest does not bind the instrumented supervisor mode"
        )


def integration_gate_identity_payload(
    *,
    run_id: str,
    manifest_artifact_identity: str,
    subset_identity: str,
    queue_evidence_identity: str,
    selected_lanes: Sequence[str],
    coordinator_identity: str,
    connector_identity: str,
    execution_mode: str,
    gate_kind: str,
    record_count: int,
    last_sequence: Optional[int],
    last_event_hash: Optional[str],
    completed_task_ids: Sequence[str],
    base_task_coverage_identity: Optional[str],
) -> dict[str, Any]:
    """Return the exact identity payload archived as an integration receipt.

    ``gate_id`` is the canonical hash of this payload.  The archived artifact
    carries these bytes verbatim, so consumers verify a receipt by comparing
    its artifact against this payload instead of trusting local fields.
    """

    return {
        "protocol": GATE_RECEIPT_PROTOCOL,
        "run_id": run_id,
        "manifest_artifact_identity": manifest_artifact_identity,
        "subset_identity": subset_identity,
        "queue_evidence_identity": queue_evidence_identity,
        "selected_lanes": list(selected_lanes),
        "coordinator_identity": coordinator_identity,
        "connector_identity": connector_identity,
        "execution_mode": execution_mode,
        "gate_kind": gate_kind,
        "record_count": record_count,
        "last_sequence": last_sequence,
        "last_event_hash": last_event_hash,
        "completed_task_ids": list(completed_task_ids),
        "base_task_coverage_identity": base_task_coverage_identity,
    }


def _integration_gate_payload(
    receipt: "IntegrationGateReceipt",
) -> dict[str, Any]:
    return integration_gate_identity_payload(
        run_id=receipt.run_id,
        manifest_artifact_identity=receipt.manifest_artifact_identity,
        subset_identity=receipt.subset_identity,
        queue_evidence_identity=receipt.queue_evidence_identity,
        selected_lanes=receipt.selected_lanes,
        coordinator_identity=receipt.coordinator_identity,
        connector_identity=receipt.connector_identity,
        execution_mode=receipt.execution_mode,
        gate_kind=receipt.gate_kind,
        record_count=receipt.record_count,
        last_sequence=receipt.last_sequence,
        last_event_hash=receipt.last_event_hash,
        completed_task_ids=receipt.completed_task_ids,
        base_task_coverage_identity=receipt.base_task_coverage_identity,
    )


@dataclass(frozen=True)
class IntegrationGateReceipt:
    """Canonical receipt binding one completed run as integration evidence.

    This is the type the corpus and tuner plans import under the descriptive
    name ``IntegrationGateReceipt``.  It carries the complete gate binding:
    the archived receipt artifact, the manifest artifact identity, the frozen
    subset and queue evidence identities, the selected lanes, and the
    coordinator identity plus connector surface measured at gate issuance.
    """

    gate_id: str
    run_id: str
    receipt_artifact: ArtifactRef
    manifest_artifact_identity: str
    subset_identity: str
    queue_evidence_identity: str
    selected_lanes: Tuple[str, ...]
    coordinator_identity: str
    connector_identity: str
    execution_mode: str
    gate_kind: str
    record_count: int
    last_sequence: Optional[int]
    last_event_hash: Optional[str]
    completed_task_ids: Tuple[str, ...]
    base_task_coverage_identity: Optional[str]

    def __post_init__(self) -> None:
        validate_hash(self.gate_id, "gate_id")
        validate_run_id(self.run_id, "run_id")
        original_receipt_artifact = self.receipt_artifact
        try:
            receipt_artifact = (
                ArtifactRef.from_dict(self.receipt_artifact.to_dict())
                if isinstance(self.receipt_artifact, ArtifactRef)
                else ArtifactRef.from_dict(self.receipt_artifact)  # type: ignore[arg-type]
            )
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise SearchValidationError(
                "integration gate receipt artifact is invalid"
            ) from exc
        if (
            isinstance(original_receipt_artifact, ArtifactRef)
            and receipt_artifact != original_receipt_artifact
        ):
            raise SearchValidationError(
                "integration gate receipt artifact is invalid"
            )
        object.__setattr__(self, "receipt_artifact", receipt_artifact)
        for name in (
            "manifest_artifact_identity",
            "subset_identity",
            "queue_evidence_identity",
            "coordinator_identity",
            "connector_identity",
        ):
            validate_hash(getattr(self, name), name)
        if isinstance(self.selected_lanes, (str, bytes, bytearray)):
            raise SearchValidationError(
                "integration gate receipt selected_lanes must be a sequence"
            )
        try:
            lanes = tuple(self.selected_lanes)
            repeated_lanes = len(set(lanes)) != len(lanes)
        except (TypeError, ValueError) as exc:
            raise SearchValidationError(
                "integration gate receipt selected_lanes are invalid"
            ) from exc
        if repeated_lanes:
            raise SearchValidationError(
                "integration gate receipt repeats a selected lane"
            )
        canonical_lanes = tuple(lane for lane in LANES if lane in lanes)
        if not lanes:
            raise SearchValidationError(
                "integration gate receipt selected_lanes must be nonempty"
            )
        if lanes != canonical_lanes:
            raise SearchValidationError(
                "integration gate receipt lanes must use canonical LANES order"
            )
        object.__setattr__(self, "selected_lanes", lanes)
        if self.execution_mode != INSTRUMENTED_MODE:
            raise SearchValidationError(
                "integration gate receipt must bind instrumented execution"
            )
        if not isinstance(self.gate_kind, str) or self.gate_kind not in _GATE_KINDS:
            raise SearchValidationError(
                "integration gate receipt binds an unknown gate kind"
            )
        if (
            isinstance(self.record_count, bool)
            or not isinstance(self.record_count, int)
            or self.record_count < 1
        ):
            raise SearchValidationError(
                "integration gate receipt record_count must be positive"
            )
        if self.gate_kind == GATE_KIND_SMOKE and self.record_count != 1:
            raise SearchValidationError(
                "smoke integration gate must bind exactly one record"
            )
        if self.gate_kind == GATE_KIND_MULTI_RECORD and self.record_count < 2:
            raise SearchValidationError(
                "multi-record integration gate must bind at least two records"
            )

        if isinstance(self.completed_task_ids, (str, bytes, bytearray)):
            raise SearchValidationError(
                "integration gate completed task IDs must be a sequence"
            )
        try:
            completed = tuple(self.completed_task_ids)
            ordered_completed = tuple(sorted(set(completed)))
        except (TypeError, ValueError) as exc:
            raise SearchValidationError(
                "integration gate completed task IDs are invalid"
            ) from exc
        if completed != ordered_completed:
            raise SearchValidationError(
                "integration gate completed task IDs must be sorted and unique"
            )
        for task_id in completed:
            validate_id(task_id, "completed_task_id")
        object.__setattr__(self, "completed_task_ids", completed)

        proof_values = (
            self.last_sequence,
            self.last_event_hash,
            self.base_task_coverage_identity,
        )
        proof_present = any(value is not None for value in proof_values) or bool(completed)
        if not proof_present:
            if self.gate_kind == GATE_KIND_MULTI_RECORD:
                raise SearchValidationError(
                    "multi-record integration gate requires terminal proof"
                )
            if completed:
                raise SearchValidationError(
                    "integration gate terminal proof fields are inconsistent"
                )
        else:
            if (
                isinstance(self.last_sequence, bool)
                or not isinstance(self.last_sequence, int)
                or self.last_sequence < 0
                or self.last_event_hash is None
                or self.base_task_coverage_identity is None
            ):
                raise SearchValidationError(
                    "integration gate terminal proof fields are inconsistent"
                )
            validate_hash(self.last_event_hash, "last_event_hash")
            validate_hash(
                self.base_task_coverage_identity,
                "base_task_coverage_identity",
            )
        if self.gate_id != hash_canonical(_integration_gate_payload(self)):
            raise SearchValidationError(
                "gate_id does not match the integration gate identity payload"
            )
        expected_artifact = _integration_gate_payload(self)
        expected_bytes = canonical_bytes(expected_artifact)
        expected_path = (
            "artifacts/receipts/"
            + self.gate_id.removeprefix("sha256:")
            + ".json"
        )
        if (
            self.receipt_artifact.content_hash != self.gate_id
            or self.receipt_artifact.path != expected_path
            or self.receipt_artifact.media_type != "application/json"
            or self.receipt_artifact.byte_size != len(expected_bytes)
        ):
            raise SearchValidationError(
                "integration gate receipt artifact does not match its identity"
            )

    @property
    def multi_record(self) -> bool:
        """Compatibility view of the closed ``gate_kind`` field."""

        return self.gate_kind == GATE_KIND_MULTI_RECORD

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IntegrationGateReceipt":
        fields = (
            "gate_id",
            "run_id",
            "receipt_artifact",
            "manifest_artifact_identity",
            "subset_identity",
            "queue_evidence_identity",
            "selected_lanes",
            "coordinator_identity",
            "connector_identity",
            "execution_mode",
            "gate_kind",
            "record_count",
            "last_sequence",
            "last_event_hash",
            "completed_task_ids",
            "base_task_coverage_identity",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise SearchValidationError(
                "integration gate receipt fields do not match its protocol"
            )
        return cls(**{key: value[key] for key in fields})

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "run_id": self.run_id,
            "receipt_artifact": self.receipt_artifact.to_dict(),
            "manifest_artifact_identity": self.manifest_artifact_identity,
            "subset_identity": self.subset_identity,
            "queue_evidence_identity": self.queue_evidence_identity,
            "selected_lanes": list(self.selected_lanes),
            "coordinator_identity": self.coordinator_identity,
            "connector_identity": self.connector_identity,
            "execution_mode": self.execution_mode,
            "gate_kind": self.gate_kind,
            "record_count": self.record_count,
            "last_sequence": self.last_sequence,
            "last_event_hash": self.last_event_hash,
            "completed_task_ids": list(self.completed_task_ids),
            "base_task_coverage_identity": self.base_task_coverage_identity,
        }


def _connector_module_identity() -> str:
    """Hash the connector surface measured while this gate is issued.

    This is a certificate of the connector code visible at issuance time.  It
    is not a claim that the connector produced the earlier durable run.
    """

    path = Path(__file__).resolve().parent / "mcp" / "commands_client.py"
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise IntegrationGateError(
            "integration gate cannot read the connector surface module"
        ) from exc
    return hash_bytes(data)


def _gate_run_root(source: Any) -> tuple[Path, Path, RunManifest]:
    """Resolve a real run root and load its manifest from disk.

    A manifest object is intentionally not accepted here.  The gate is an
    integration proof about durable run evidence, so all of its inputs must
    come from the same on-disk run root.
    """

    if isinstance(source, RunManifest):
        raise IntegrationGateError(
            "integration gate issuance requires a run root or manifest path"
        )
    if not isinstance(source, (str, os.PathLike)):
        raise IntegrationGateError(
            "integration gate source must be a run root or manifest path"
        )
    candidate = Path(source)
    try:
        if candidate.is_dir():
            root = _safe_run_root(candidate)
            manifest_path = root / "manifest.json"
        else:
            manifest_path, _loaded = _load_manifest_file(candidate)
            root = _safe_run_root(manifest_path.parent)
        manifest_path, manifest = _load_manifest_file(root / "manifest.json")
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, IntegrationGateError):
            raise
        raise IntegrationGateError(
            "integration gate cannot load the exact run manifest"
        ) from exc
    try:
        resolved_root = root.resolve(strict=True)
        resolved_manifest = manifest_path.resolve(strict=True)
    except OSError as exc:
        raise IntegrationGateError("integration gate run root is unreadable") from exc
    if resolved_manifest != resolved_root / "manifest.json":
        raise IntegrationGateError(
            "integration gate manifest is not rooted in the requested run"
        )
    return resolved_root, resolved_manifest, manifest


def _require_gate_archive(
    archive: Optional[ContentAddressedArchive],
    root: Path,
) -> ContentAddressedArchive:
    if archive is None:
        return ContentAddressedArchive(root)
    if not isinstance(archive, ContentAddressedArchive):
        raise IntegrationGateError("integration gate archive is not canonical")
    try:
        archive_root = archive.run_root.resolve(strict=False)
    except OSError as exc:
        raise IntegrationGateError("integration gate archive root is unreadable") from exc
    if archive_root != root:
        raise IntegrationGateError(
            "integration gate archive must use the exact run root"
        )
    return archive


def _factory_gate_manifest(manifest: RunManifest) -> None:
    """Require both durable factory bindings before an integration proof."""

    if manifest.tool_identities.get(MODE_TOOL_KEY) != mode_identity(INSTRUMENTED_MODE):
        raise IntegrationGateError(
            "integration gate refuses legacy or non-instrumented execution"
        )
    marker = manifest.tool_identities.get(_FACTORY_MARKER_KEY)
    factory_identity = manifest.tool_identities.get(_FACTORY_TOOL_KEY)
    if not isinstance(marker, str) or not isinstance(factory_identity, str):
        raise IntegrationGateError(
            "integration gate requires factory-created archive evidence"
        )


def _base_task_coverage_payload(tasks: Iterable[SearchTask]) -> list[dict[str, Any]]:
    """Return stable identities for the exact base-task set."""

    values = []
    for task in tasks:
        # Task state is a lifecycle value and is not part of task identity.
        value = task.to_dict()
        value["state"] = "scheduled"
        values.append(value)
    return sorted(
        values,
        key=lambda item: (
            item["recipient_id"],
            item["lane"],
            item["task_id"],
        ),
    )


def _terminal_gate_proof(
    root: Path,
    manifest: RunManifest,
    state: Any,
    *,
    ledger_had_events: bool,
) -> tuple[Optional[int], Optional[str], tuple[str, ...], Optional[str]]:
    """Validate recovered completion and return its immutable terminal proof."""

    if not ledger_had_events:
        # ``recover_run`` rejects an empty ledger by design.  A factory-created
        # one-record shadow may still be a valid zero-event plan, represented
        # by an absent terminal proof.  Multi-record gates reject this later.
        return None, None, (), None
    if state is None:
        raise IntegrationGateError("integration gate has no recoverable run state")
    if state.incomplete_tasks:
        raise IntegrationGateError(
            "integration gate refuses a run with incomplete tasks"
        )
    active_stop = state.stopped
    if active_stop is not None and not (
        active_stop.reason == "completed"
        and active_stop.resumable is False
        and not active_stop.pending_task_ids
    ):
        raise IntegrationGateError("integration gate refuses an actively stopped run")
    if active_stop is not None:
        stop_events = [
            event for event in state.events if event.event_type == "run_stopped"
        ]
        if (
            not stop_events
            or state.events[-1] != stop_events[-1]
            or stop_events[-1].payload != active_stop
        ):
            raise IntegrationGateError(
                "integration gate completion stop is not the terminal ledger event"
            )
    completed = tuple(sorted(state.completed_task_ids))
    base_tasks = [
        task for task in state.tasks.values() if task.operation == "execute_lane"
    ]
    coverage_identity = hash_canonical(_base_task_coverage_payload(base_tasks))
    return (
        state.last_sequence,
        state.last_event_hash,
        completed,
        coverage_identity,
    )


def _validate_gate_tasks(
    manifest: RunManifest,
    state: Any,
    *,
    gate_kind: str,
) -> None:
    if state is None:
        return
    expected_pairs = {
        (record_id, lane)
        for record_id in manifest.queue_record_ids
        for lane in manifest.selected_lanes
    }
    base_pairs: dict[tuple[str, str], SearchTask] = {}
    for task in state.tasks.values():
        if task.operation == "execute_lane":
            pair = (task.recipient_id, task.lane)
            if pair not in expected_pairs:
                raise IntegrationGateError(
                    "integration gate found an unexpected base task pair"
                )
            if pair in base_pairs:
                raise IntegrationGateError(
                    "integration gate found duplicate base task coverage"
                )
            base_pairs[pair] = task
        elif task.operation.startswith("materialize_candidate:"):
            # Candidate children are permitted, but recover_run's incomplete
            # task check below still requires every child to be terminal.
            continue
        else:
            raise IntegrationGateError(
                "integration gate found an unexpected task operation"
            )
    if gate_kind == GATE_KIND_MULTI_RECORD and set(base_pairs) != expected_pairs:
        missing = expected_pairs.difference(base_pairs)
        unexpected = set(base_pairs).difference(expected_pairs)
        detail = []
        if missing:
            detail.append("missing base task pair")
        if unexpected:
            detail.append("unexpected base task pair")
        raise IntegrationGateError(
            "integration gate base-task coverage is incomplete (" + ", ".join(detail) + ")"
        )
    for task in base_pairs.values():
        if task.task_id not in state.terminal_tasks:
            raise IntegrationGateError(
                "integration gate base task is not terminal"
            )


def _inspect_gate_runtime(
    root: Path,
    manifest: RunManifest,
    *,
    archive: ContentAddressedArchive,
    require_completed_stop: bool = False,
) -> tuple[str, int, Optional[int], Optional[str], tuple[str, ...], Optional[str]]:
    """Verify factory evidence and recover the durable run once."""

    _factory_gate_manifest(manifest)
    if not manifest.selected_lanes:
        raise IntegrationGateError("integration gate selected lanes must be nonempty")
    coordinator_identity = manifest.tool_identities.get("search_coordinator")
    if coordinator_identity is None:
        raise IntegrationGateError(
            "integration gate requires the factory-bound coordinator identity"
        )
    if manifest.coordinator_budget.limit > MAX_COORDINATOR_TASKS:
        raise IntegrationGateError(
            "integration gate manifest exceeds the global coordinator bound"
        )
    task_count = len(manifest.queue_record_ids) * len(manifest.selected_lanes)
    if task_count > manifest.coordinator_budget.limit:
        raise IntegrationGateError(
            "integration gate manifest cannot cover its selected task subset"
        )
    if task_count * (1 + MAX_CHILD_TASKS_PER_BASE) > MAX_COORDINATOR_TASKS:
        raise IntegrationGateError(
            "integration gate manifest exceeds the global coordinator bound"
        )

    try:
        try:
            from .search_run_factory import verify_factory_archive
        except ImportError:  # pragma: no cover - direct script compatibility
            from search_run_factory import verify_factory_archive  # type: ignore
        verified_manifest = verify_factory_archive(root, manifest)
    except IntegrationGateError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise IntegrationGateError(
            "integration gate factory archive verification failed"
        ) from exc
    if verified_manifest != manifest:
        raise IntegrationGateError(
            "integration gate factory archive returned a different manifest"
        )

    ledger_path = root / "ledger.jsonl"
    try:
        ledger_bytes = ledger_path.read_bytes() if ledger_path.exists() else b""
    except OSError as exc:
        raise IntegrationGateError("integration gate ledger cannot be read") from exc
    ledger_had_events = bool(ledger_bytes)
    state = None
    try:
        state = recover_run(root)
    except Exception as exc:  # noqa: BLE001
        if ledger_had_events:
            raise IntegrationGateError(
                "integration gate ledger cannot be recovered"
            ) from exc
        # An absent/empty ledger is permitted only for the smoke gate.  The
        # caller still invoked recover_run, so a nonempty malformed prefix is
        # never treated as a shadow plan.
    if state is not None and state.manifest != manifest:
        raise IntegrationGateError(
            "integration gate recovered manifest differs from the exact manifest"
        )
    if state is not None:
        try:
            gate_kind = (
                GATE_KIND_SMOKE
                if len(manifest.queue_record_ids) == 1
                else GATE_KIND_MULTI_RECORD
            )
            _validate_gate_tasks(manifest, state, gate_kind=gate_kind)
        except IntegrationGateError:
            raise
    gate_kind = (
        GATE_KIND_SMOKE
        if len(manifest.queue_record_ids) == 1
        else GATE_KIND_MULTI_RECORD
    )
    record_count = len(manifest.queue_record_ids)
    if gate_kind == GATE_KIND_MULTI_RECORD:
        if not ledger_had_events or state is None:
            raise IntegrationGateError(
                "multi-record integration gate requires a recovered ledger"
            )
        if not state.events:
            raise IntegrationGateError(
                "multi-record integration gate requires a nonempty ledger"
            )
        if require_completed_stop and not (
            state.stopped is not None
            and state.stopped.reason == "completed"
            and state.stopped.resumable is False
        ):
            raise IntegrationGateError(
                "multi-record integration gate requires terminal completion"
            )
    proof = _terminal_gate_proof(
        root,
        manifest,
        state,
        ledger_had_events=ledger_had_events,
    )
    if gate_kind == GATE_KIND_MULTI_RECORD and any(value is None for value in proof[:2]):
        raise IntegrationGateError("multi-record terminal proof is incomplete")
    return gate_kind, record_count, *proof


def archive_integration_gate(
    source: Any,
    *,
    archive: Optional[ContentAddressedArchive] = None,
    gate_kind: Optional[str] = None,
) -> IntegrationGateReceipt:
    """Create an immutable integration receipt from one real run root.

    Factory archive evidence and the recovered ledger are the authority.  A
    caller cannot supply a synthetic manifest, an unrelated archive, or a
    later connector claim in place of the durable run proof.
    """

    root, _manifest_path, manifest = _gate_run_root(source)
    archive = _require_gate_archive(archive, root)
    inferred_kind, record_count, last_sequence, last_event_hash, completed, coverage = _inspect_gate_runtime(
        root,
        manifest,
        archive=archive,
        require_completed_stop=True,
    )
    if gate_kind is None:
        gate_kind = inferred_kind
    if gate_kind != inferred_kind or gate_kind not in _GATE_KINDS:
        raise IntegrationGateError("integration gate kind is not permitted for this subset")
    payload = integration_gate_identity_payload(
        run_id=manifest.run_id,
        manifest_artifact_identity=hash_canonical(manifest.to_dict()),
        subset_identity=manifest.subset_identity,
        queue_evidence_identity=manifest.queue_evidence_identity,
        selected_lanes=manifest.selected_lanes,
        coordinator_identity=manifest.tool_identities["search_coordinator"],
        connector_identity=_connector_module_identity(),
        execution_mode=INSTRUMENTED_MODE,
        gate_kind=gate_kind,
        record_count=record_count,
        last_sequence=last_sequence,
        last_event_hash=last_event_hash,
        completed_task_ids=completed,
        base_task_coverage_identity=coverage,
    )
    artifact = archive.put_receipt(payload)
    return IntegrationGateReceipt(
        gate_id=hash_canonical(payload),
        run_id=manifest.run_id,
        receipt_artifact=artifact,
        manifest_artifact_identity=payload["manifest_artifact_identity"],
        subset_identity=payload["subset_identity"],
        queue_evidence_identity=payload["queue_evidence_identity"],
        selected_lanes=tuple(payload["selected_lanes"]),
        coordinator_identity=payload["coordinator_identity"],
        connector_identity=payload["connector_identity"],
        execution_mode=payload["execution_mode"],
        gate_kind=payload["gate_kind"],
        record_count=payload["record_count"],
        last_sequence=payload["last_sequence"],
        last_event_hash=payload["last_event_hash"],
        completed_task_ids=tuple(payload["completed_task_ids"]),
        base_task_coverage_identity=payload["base_task_coverage_identity"],
    )


def validate_integration_gate(
    receipt: Any,
    *,
    archive: ContentAddressedArchive,
) -> None:
    """Canonical validator for one archived integration receipt.

    Refuses anything that is not a typed receipt whose archived artifact
    matches its identity payload byte for byte.  Consumers call this exactly
    once before reading any corpus or donor evidence.
    """

    if not isinstance(receipt, IntegrationGateReceipt):
        raise IntegrationGateError("integration gate receipt is missing or not typed")
    try:
        canonical_receipt = IntegrationGateReceipt.from_dict(receipt.to_dict())
    except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
        raise IntegrationGateError("integration gate receipt invariants are invalid") from exc
    if canonical_receipt != receipt:
        raise IntegrationGateError("integration gate receipt invariants are invalid")
    root = getattr(archive, "run_root", None)
    if root is None:
        raise IntegrationGateError("integration gate archive is not canonical")
    try:
        root = Path(root).resolve(strict=True)
    except OSError as exc:
        raise IntegrationGateError("integration gate archive root is unreadable") from exc
    _require_gate_archive(archive, root)
    if not receipt.receipt_artifact.path.startswith("artifacts/receipts/"):
        raise IntegrationGateError("integration gate receipt artifact path is invalid")
    try:
        raw = archive.verify(receipt.receipt_artifact)
    except Exception as exc:  # noqa: BLE001
        raise IntegrationGateError(
            "integration gate receipt artifact does not verify"
        ) from exc
    payload = _integration_gate_payload(receipt)
    if raw != canonical_bytes(payload):
        raise IntegrationGateError(
            "integration gate receipt artifact differs from its identity payload"
        )
    expected_receipt_path = (
        "artifacts/receipts/"
        + receipt.gate_id.removeprefix("sha256:")
        + ".json"
    )
    if (
        receipt.receipt_artifact.path != expected_receipt_path
        or receipt.receipt_artifact.media_type != "application/json"
        or receipt.receipt_artifact.byte_size != len(raw)
        or receipt.receipt_artifact.content_hash != hash_bytes(raw)
    ):
        raise IntegrationGateError(
            "integration gate receipt artifact identity or metadata is invalid"
        )
    if receipt.gate_id != hash_canonical(payload):
        raise IntegrationGateError(
            "integration gate receipt identity does not match its archived payload"
        )
    try:
        _manifest_path, manifest = _load_manifest_file(root / "manifest.json")
    except Exception as exc:  # noqa: BLE001
        raise IntegrationGateError(
            "integration gate manifest is missing or invalid"
        ) from exc
    if receipt.run_id != manifest.run_id:
        raise IntegrationGateError("integration gate run identity differs from manifest")
    if receipt.manifest_artifact_identity != hash_canonical(manifest.to_dict()):
        raise IntegrationGateError("integration gate manifest identity is stale")
    try:
        expected = _inspect_gate_runtime(
            root,
            manifest,
            archive=archive,
            require_completed_stop=(receipt.gate_kind == GATE_KIND_MULTI_RECORD),
        )
    except IntegrationGateError:
        raise
    if expected != (
        receipt.gate_kind,
        receipt.record_count,
        receipt.last_sequence,
        receipt.last_event_hash,
        receipt.completed_task_ids,
        receipt.base_task_coverage_identity,
    ):
        raise IntegrationGateError(
            "integration gate terminal proof differs from recovered run"
        )


def load_integration_gate(
    source: Any,
    *,
    archive: ContentAddressedArchive,
) -> IntegrationGateReceipt:
    """Load, decode and canonically validate one integration receipt."""

    try:
        if isinstance(source, (str, os.PathLike)):
            document = json.loads(Path(source).read_text(encoding="utf-8"))
        elif isinstance(source, (bytes, bytearray)):
            document = json.loads(bytes(source).decode("utf-8"))
        elif isinstance(source, Mapping):
            document = dict(source)
        else:
            raise TypeError(
                "integration gate source must be a path, bytes or mapping"
            )
    except IntegrationGateError:
        raise
    except (OSError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrationGateError(
            "integration gate receipt is unreadable"
        ) from exc
    try:
        receipt = IntegrationGateReceipt.from_dict(document)
    except (KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise IntegrationGateError("integration gate receipt is invalid") from exc
    validate_integration_gate(receipt, archive=archive)
    return receipt


def _stop_request_path(run_root: Path) -> Path:
    return Path(run_root) / STOP_REQUEST_FILENAME


def _stop_request_document(
    manifest: RunManifest,
    *,
    generation: int = 1,
) -> dict[str, Any]:
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise SupervisorIntegrationError("stop request generation must be positive")
    payload = {
        "protocol": STOP_REQUEST_PROTOCOL,
        "run_id": manifest.run_id,
        "manifest_identity": hash_canonical(manifest.to_dict()),
        "mode": INSTRUMENTED_MODE,
        "reason": STOP_REQUEST_REASON,
        "generation": generation,
    }
    return {
        **payload,
        "request_id": hash_canonical(payload),
        "state": STOP_REQUEST_PENDING,
    }


def _load_stop_request(
    run_root: Path,
    manifest: RunManifest,
) -> Optional[dict[str, Any]]:
    path = _stop_request_path(run_root)
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupervisorIntegrationError(
            "instrumented stop request is unreadable"
        ) from exc
    if not isinstance(document, Mapping):
        raise SupervisorIntegrationError(
            "instrumented stop request is not bound to this manifest"
        )
    required = {
        "protocol",
        "run_id",
        "manifest_identity",
        "mode",
        "reason",
        "generation",
        "request_id",
        "state",
    }
    if not required.issubset(document):
        raise SupervisorIntegrationError(
            "instrumented stop request is missing its protocol fields"
        )
    generation = document.get("generation")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise SupervisorIntegrationError("instrumented stop request generation is invalid")
    expected = _stop_request_document(manifest, generation=generation)
    state = document.get("state")
    if state == STOP_REQUEST_PENDING:
        if set(document) != set(expected) or dict(document) != expected:
            raise SupervisorIntegrationError(
                "instrumented stop request is not bound to this manifest"
            )
        return dict(document)
    if state != STOP_REQUEST_ACKNOWLEDGED:
        raise SupervisorIntegrationError("instrumented stop request has an unknown state")
    acknowledged = required | {
        "stop_event_id",
        "stop_event_hash",
        "resume_event_id",
        "resume_event_hash",
    }
    if set(document) != acknowledged:
        raise SupervisorIntegrationError(
            "acknowledged instrumented stop request has invalid fields"
        )
    expected_base = dict(expected)
    expected_base.pop("state")
    if any(document.get(key) != value for key, value in expected_base.items()):
        raise SupervisorIntegrationError(
            "acknowledged instrumented stop request is not bound to this manifest"
        )
    try:
        RunResume(
            stop_event_id=document["stop_event_id"],
            stop_event_hash=document["stop_event_hash"],
            request_id=document["request_id"],
        )
        RunResume(
            stop_event_id=document["resume_event_id"],
            stop_event_hash=document["resume_event_hash"],
            request_id=document["request_id"],
        )
    except (TypeError, ValueError) as exc:
        raise SupervisorIntegrationError(
            "acknowledged instrumented stop request has invalid event bindings"
        ) from exc
    return dict(document)


def _acknowledged_stop_request_document(
    request: Mapping[str, Any],
    stop_event: LedgerEvent,
    resume_event: LedgerEvent,
) -> dict[str, Any]:
    if request.get("state") != STOP_REQUEST_PENDING:
        raise SupervisorIntegrationError("stop request is not pending acknowledgement")
    if stop_event.event_type != "run_stopped":
        raise SupervisorIntegrationError("stop acknowledgement names a non-stop event")
    if resume_event.event_type != "run_resumed":
        raise SupervisorIntegrationError("stop acknowledgement names a non-resume event")
    resume = resume_event.payload
    if not isinstance(resume, RunResume):
        raise SupervisorIntegrationError("resume event payload is not typed")
    if resume.request_id != request.get("request_id"):
        raise SupervisorIntegrationError("resume event is bound to another stop request")
    return {
        **dict(request),
        "state": STOP_REQUEST_ACKNOWLEDGED,
        "stop_event_id": stop_event.event_id,
        "stop_event_hash": stop_event.event_hash,
        "resume_event_id": resume_event.event_id,
        "resume_event_hash": resume_event.event_hash,
    }


def _active_stop_event(events: Sequence[LedgerEvent]) -> Optional[LedgerEvent]:
    active: Optional[LedgerEvent] = None
    for event in events:
        if event.event_type == "run_stopped":
            active = event
        elif event.event_type == "run_resumed":
            active = None
    return active


def _is_completed_stop_event(event: Optional[LedgerEvent]) -> bool:
    if event is None or event.event_type != "run_stopped":
        return False
    payload = event.payload
    return isinstance(payload, RunStop) and payload.reason == "completed" and payload.resumable is False


def _resume_event_for_request(
    events: Sequence[LedgerEvent],
    request_id: str,
) -> Optional[LedgerEvent]:
    # The acknowledgement remains valid while the resumed coordinator appends
    # later task and receipt events.  Locate the exact request-bound transition
    # anywhere in the verified prefix rather than mistaking those later events
    # for a lost resume.
    for event in reversed(events):
        if event.event_type != "run_resumed":
            continue
        payload = event.payload
        if isinstance(payload, RunResume) and payload.request_id == request_id:
            return event
    return None


def _pid_alive(pid: int) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        "." + path.name + f".{os.getpid()}.{time.time_ns()}.tmp"
    )
    data = canonical_bytes(value) + b"\n"
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


class SupervisorLease:
    """Advisory cross-process ownership without becoming run authority."""

    def __init__(
        self,
        *,
        mode: str,
        run_id: str,
        record_ids: Iterable[str],
        path: Optional[Path] = None,
        pid: Optional[int] = None,
        pid_alive: Callable[[int], bool] = _pid_alive,
        timeout: float = 5.0,
    ) -> None:
        if mode not in {LEGACY_MODE, INSTRUMENTED_MODE}:
            raise SupervisorModeError("unknown supervisor lease mode")
        self.mode = mode
        self.run_id = str(run_id)
        self.record_ids = tuple(sorted(set(str(item) for item in record_ids)))
        self.path = Path(path or DEFAULT_LEASE_PATH)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.pid = int(pid if pid is not None else os.getpid())
        self.pid_alive = pid_alive
        self.timeout = timeout
        self.owner_id = f"{self.pid}:{time.time_ns()}"
        self._held = False

    def _take_lock(self) -> None:
        deadline = time.monotonic() + self.timeout
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                descriptor = os.open(
                    str(self.lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                try:
                    owner = int(
                        self.lock_path.read_text(encoding="ascii").strip()
                    )
                except (OSError, ValueError):
                    owner = -1
                if not self.pid_alive(owner):
                    try:
                        self.lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                if time.monotonic() >= deadline:
                    raise SupervisorConflict(
                        "supervisor ownership registry is locked by a live process"
                    )
                time.sleep(0.02)
                continue
            with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                stream.write(str(self.pid))
                stream.flush()
                os.fsync(stream.fileno())
            return

    def _drop_lock(self) -> None:
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass

    def _load_owners(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SupervisorConflict("supervisor ownership registry is corrupt") from exc
        if not isinstance(value, Mapping) or value.get("protocol") != LEASE_PROTOCOL:
            raise SupervisorConflict("supervisor ownership registry has an unknown format")
        owners = value.get("owners")
        if not isinstance(owners, list):
            raise SupervisorConflict("supervisor ownership registry owners are invalid")
        return [dict(item) for item in owners if isinstance(item, Mapping)]

    def _live_owners(self) -> list[dict[str, Any]]:
        live = []
        for owner in self._load_owners():
            pid = owner.get("pid")
            if isinstance(pid, int) and self.pid_alive(pid):
                live.append(owner)
        return live

    def _write_owners(self, owners: Sequence[Mapping[str, Any]]) -> None:
        _atomic_json(
            self.path,
            {
                "protocol": LEASE_PROTOCOL,
                "owners": [dict(item) for item in owners],
            },
        )

    def __enter__(self) -> "SupervisorLease":
        self._take_lock()
        try:
            owners = self._live_owners()
            requested = set(self.record_ids)
            for owner in owners:
                existing = set(str(item) for item in owner.get("record_ids", ()))
                same_run = owner.get("run_id") == self.run_id
                overlap = bool(requested.intersection(existing))
                second_instrumented = (
                    self.mode == INSTRUMENTED_MODE
                    and owner.get("mode") == INSTRUMENTED_MODE
                )
                if same_run or overlap or second_instrumented:
                    raise SupervisorConflict(
                        "supervisor run conflicts with a live "
                        + str(owner.get("mode", "unknown"))
                        + " owner"
                    )
            owners.append(
                {
                    "owner_id": self.owner_id,
                    "pid": self.pid,
                    "mode": self.mode,
                    "run_id": self.run_id,
                    "record_ids": list(self.record_ids),
                }
            )
            self._write_owners(owners)
            self._held = True
        finally:
            self._drop_lock()
        return self

    def __exit__(self, _kind: Any, _value: Any, _traceback: Any) -> None:
        if not self._held:
            return
        self._take_lock()
        try:
            owners = [
                owner
                for owner in self._live_owners()
                if owner.get("owner_id") != self.owner_id
            ]
            self._write_owners(owners)
            self._held = False
        finally:
            self._drop_lock()


def legacy_lease(
    record_resolver: Callable[[Tuple[str, ...]], Iterable[str]],
    *,
    path: Optional[Path] = None,
) -> Callable[[Callable[..., int]], Callable[..., int]]:
    """Wrap the existing legacy loop without moving its state into this module."""

    def decorate(function: Callable[..., int]) -> Callable[..., int]:
        @functools.wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> int:
            statuses = kwargs.get("statuses")
            if statuses is None and len(args) > 4:
                statuses = args[4]
            normalized = tuple(statuses or ())
            records = tuple(record_resolver(normalized))
            with SupervisorLease(
                mode=LEGACY_MODE,
                run_id="legacy-permuter-supervisor",
                record_ids=records,
                path=path,
            ):
                return function(*args, **kwargs)

        return wrapped

    return decorate


class InstrumentedLandingOracle:
    """Durable idempotent adapter around the existing landing gate."""

    def __init__(
        self,
        run_root: Path,
        identity: str,
        landing: LandingCallback,
    ) -> None:
        self.run_root = Path(run_root)
        self.identity = identity
        self.landing = landing
        self.store = self.run_root / "oracle-service"
        self.archive = ContentAddressedArchive(self.run_root)

    def _path(self, request_id: str) -> Path:
        if not request_id.startswith("sha256:"):
            raise DurableOracleError("oracle request id is not a content hash")
        return self.store / (request_id.removeprefix("sha256:") + ".json")

    def _document(
        self,
        request: OracleRequest,
        outcome: str,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "protocol": ORACLE_PROTOCOL,
            "request_id": request.request_id,
            "oracle_identity": self.identity,
            "outcome": outcome,
            "result": dict(result),
        }
        return {
            **payload,
            "receipt_identity": hash_canonical(payload),
        }

    def _persist(
        self,
        request: OracleRequest,
        outcome: str,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        document = self._document(request, outcome, result)
        path = self._path(request.request_id)
        if path.exists():
            current = self._load_document(path, request.request_id)
            if current != document:
                raise DurableOracleError(
                    "oracle request maps to a different durable result"
                )
        else:
            _atomic_json(path, document)
        return {"outcome": outcome, "result": dict(result)}

    def _load_document(
        self, path: Path, request_id: str
    ) -> dict[str, Any]:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DurableOracleError("durable oracle receipt is unreadable") from exc
        if not isinstance(document, Mapping):
            raise DurableOracleError("durable oracle receipt is not an object")
        payload = {
            "protocol": document.get("protocol"),
            "request_id": document.get("request_id"),
            "oracle_identity": document.get("oracle_identity"),
            "outcome": document.get("outcome"),
            "result": document.get("result"),
        }
        if (
            payload["protocol"] != ORACLE_PROTOCOL
            or payload["request_id"] != request_id
            or payload["oracle_identity"] != self.identity
            or payload["outcome"] not in {"matched", "not_matched", "error"}
            or not isinstance(payload["result"], Mapping)
            or document.get("receipt_identity") != hash_canonical(payload)
        ):
            raise DurableOracleError("durable oracle receipt failed identity validation")
        return dict(document)

    def lookup(self, request_id: str) -> Optional[dict[str, Any]]:
        path = self._path(request_id)
        if not path.is_file():
            return None
        document = self._load_document(path, request_id)
        return {
            "outcome": document["outcome"],
            "result": dict(document["result"]),
        }

    def execute(self, request: OracleRequest) -> dict[str, Any]:
        existing = self.lookup(request.request_id)
        if existing is not None:
            return existing
        try:
            source = self.archive.verify(
                request.candidate.source_artifact
            ).decode("utf-8")
        except (OSError, UnicodeDecodeError, RuntimeError) as exc:
            result = {
                "candidate_id": request.candidate_id,
                "detail": "candidate source artifact is unavailable",
            }
            return self._persist(request, "error", result)

        def persist_terminal(outcome: str, detail: str) -> None:
            if outcome not in {"matched", "not_matched"}:
                raise DurableOracleError(
                    "landing callback supplied an invalid terminal outcome"
                )
            self._persist(
                request,
                outcome,
                {
                    "candidate_id": request.candidate_id,
                    "recipient_id": request.recipient_id,
                    "detail": detail,
                },
            )

        try:
            matched, detail = self.landing(
                request.recipient_id, source, persist_terminal
            )
        except Exception as exc:
            # A callback failure is not converted into a second post-callback
            # write.  If it persisted first, the next attempt reads that
            # durable terminal result; if it did not, the task remains replayable.
            raise DurableOracleError("landing callback failed") from exc
        if not isinstance(matched, bool) or not isinstance(detail, str):
            raise DurableOracleError(
                "landing callback returned an invalid terminal result"
            )
        expected_outcome = "matched" if matched else "not_matched"
        persisted = self.lookup(request.request_id)
        if persisted is None:
            raise DurableOracleError(
                "landing callback returned without a durable terminal receipt"
            )
        if persisted["outcome"] != expected_outcome:
            raise DurableOracleError(
                "landing callback terminal outcome differs from durable receipt"
            )
        result = persisted["result"]
        if (
            result.get("candidate_id") != request.candidate_id
            or result.get("recipient_id") != request.recipient_id
            or result.get("detail") != detail
        ):
            raise DurableOracleError(
                "landing callback terminal result differs from durable receipt"
            )
        return persisted


def request_instrumented_stop(
    manifest_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Publish an atomic stop request for the lease-owning run coordinator.

    This command never constructs a coordinator and never appends a ledger
    event. The active ``run_instrumented`` owner observes the bound request at
    a task boundary and is the only process allowed to append ``run_stopped``.
    Leaving the request in place makes the handoff recoverable after either
    process exits.  Acknowledged requests are replaced atomically with a new
    generation when another stop is requested after a resume.
    """
    path, manifest = _load_manifest_file(manifest_path)
    root = _safe_run_root(path.parent)
    require_instrumented_manifest(manifest)
    try:
        state = recover_run(root)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise SupervisorIntegrationError(
            "cannot request a stop for an unrecoverable run"
        ) from exc
    if state.manifest != manifest:
        raise SupervisorIntegrationError(
            "stop request manifest differs from the durable run manifest"
        )

    request = _load_stop_request(root, manifest)
    stop_count = sum(event.event_type == "run_stopped" for event in state.events)
    if request is None:
        generation = stop_count if state.stopped is not None else stop_count + 1
        request = _stop_request_document(manifest, generation=generation)
        _atomic_json(_stop_request_path(root), request)
    elif request["state"] == STOP_REQUEST_PENDING:
        if state.stopped is None and _resume_event_for_request(
            state.events, request["request_id"]
        ) is not None:
            raise SupervisorIntegrationError(
                "stop request is awaiting durable resume acknowledgement"
            )
    elif state.stopped is not None:
        # A direct coordinator stop can leave an acknowledged request from a
        # prior generation behind.  Bind a fresh request to this active stop.
        request = _stop_request_document(manifest, generation=stop_count)
        _atomic_json(_stop_request_path(root), request)
    else:
        request = _stop_request_document(manifest, generation=stop_count + 1)
        _atomic_json(_stop_request_path(root), request)

    return {
        "command": "instrumented-stop-request",
        "ok": True,
        "mode": INSTRUMENTED_MODE,
        "run_id": manifest.run_id,
        "run_root": str(root),
        "request_id": request["request_id"],
        "pending": state.stopped is None,
        "stopped": (
            state.stopped.to_dict() if state.stopped is not None else None
        ),
    }


def _recipients(manifest: RunManifest) -> Tuple[Recipient, ...]:
    recipients = []
    for record_id in manifest.queue_record_ids:
        bits = record_id.split(":", 2)
        overlay = bits[1] if len(bits) == 3 else ""
        function = bits[2] if len(bits) == 3 else record_id
        recipients.append(
            Recipient(
                recipient_id=record_id,
                overlay=overlay,
                function=function,
                status="todo",
                metadata={
                    "target_identity": manifest.target_identities[record_id],
                    "queue_evidence_identity": manifest.queue_evidence_identity,
                },
            )
        )
    return tuple(recipients)


def _ordered_lanes(manifest: RunManifest) -> Tuple[str, ...]:
    return tuple(
        sorted(
            manifest.selected_lanes,
            key=lambda lane: (
                TIER_ORDER.index(LANE_TIERS[lane]),
                LANES.index(lane),
            ),
        )
    )


def _task_result_document(task: SearchTask, outcome: LaneOutcome) -> dict[str, Any]:
    """Bind the opaque lane result to the exact task that produced it."""
    if not isinstance(task, SearchTask):
        raise SupervisorIntegrationError("lane result needs a typed task")
    if not isinstance(outcome, LaneOutcome):
        raise SupervisorIntegrationError("lane executor returned an untyped result")
    if outcome.lane != task.lane or outcome.recipient_id != task.recipient_id:
        raise SupervisorIntegrationError(
            "lane result identity differs from the scheduled task"
        )
    payload = {
        "protocol": TASK_RESULT_PROTOCOL,
        "task": task.to_dict(),
        "outcome": outcome.to_dict(),
    }
    return {
        **payload,
        "result_identity": hash_canonical(payload),
    }


def _candidate_task_result(
    task: SearchTask,
    lane_candidate: LaneCandidate,
    result_artifact: Optional[ArtifactRef],
) -> TaskResult:
    """Convert one candidate from a lane result into a child task result."""
    candidate = lane_candidate.candidate
    if (
        candidate.recipient_id != task.recipient_id
        or candidate.lane != task.lane
    ):
        raise SupervisorIntegrationError(
            "candidate identity differs from the scheduled materialization task"
        )
    return TaskResult(
        task_id=task.task_id,
        candidate=candidate,
        source=lane_candidate.source or None,
        result_artifacts=(
            (result_artifact,) if result_artifact is not None else ()
        ),
        reason="candidate materialized from lane outcome",
    )


def _lane_task_result(
    task: SearchTask,
    outcome: LaneOutcome,
    result_artifact: ArtifactRef,
) -> TaskResult:
    """Close the lane execution task after all candidate children finish."""
    state = "rejected" if outcome.refusal is not None else "completed"
    reason = outcome.reason
    if not reason and outcome.refusal is not None:
        reason = outcome.refusal.reason
    return TaskResult(
        task_id=task.task_id,
        result_artifacts=(result_artifact,),
        state=state,
        reason=reason or "lane completed",
    )


def _task_parent_candidate_ids(
    coordinator: SearchCoordinator,
    recipient_id: str,
    lane: str,
) -> Tuple[str, ...]:
    """Reuse a persisted task's ancestry, or derive it from this frontier."""
    persisted = set()
    for event in coordinator.events:
        if event.event_type not in {"task_scheduled", "task_started"}:
            continue
        task = event.payload
        if (
            isinstance(task, SearchTask)
            and task.recipient_id == recipient_id
            and task.lane == lane
            and task.operation == "execute_lane"
        ):
            persisted.add(tuple(task.parent_candidate_ids))
    if len(persisted) > 1:
        raise SupervisorIntegrationError(
            "persisted lane tasks disagree about parent candidate identities"
        )
    if persisted:
        return next(iter(persisted))
    return tuple(
        sorted(
            candidate.candidate_id
            for candidate in coordinator.frontier.graph.all()
            if candidate.recipient_id == recipient_id
        )
    )


def _same_task_identity(value: Any, task: SearchTask) -> bool:
    """Compare immutable task fields while ignoring its lifecycle state."""
    if not isinstance(value, Mapping):
        return False
    try:
        archived = SearchTask.from_dict(value)
    except (KeyError, TypeError, ValueError):
        return False
    return replace(archived, state="scheduled") == replace(task, state="scheduled")


def _parse_task_result_document(
    document: Mapping[str, Any],
    task: SearchTask,
) -> LaneOutcome:
    """Decode and validate one durable lane outcome bound to ``task``."""
    required = {"protocol", "task", "outcome", "result_identity"}
    if set(document) != required:
        raise SupervisorIntegrationError(
            "lane result artifact fields do not match its protocol"
        )
    payload = {
        "protocol": document["protocol"],
        "task": document["task"],
        "outcome": document["outcome"],
    }
    if document["result_identity"] != hash_canonical(payload):
        raise SupervisorIntegrationError(
            "lane result artifact failed identity validation"
        )
    if payload["protocol"] != TASK_RESULT_PROTOCOL:
        raise SupervisorIntegrationError(
            "lane result artifact has an unknown protocol"
        )
    if not _same_task_identity(payload["task"], task):
        raise SupervisorIntegrationError(
            "lane result artifact is bound to another task"
        )
    raw_outcome = payload["outcome"]
    if not isinstance(raw_outcome, Mapping):
        raise SupervisorIntegrationError(
            "lane result artifact has no typed outcome"
        )
    outcome_fields = {
        "lane",
        "recipient_id",
        "candidates",
        "receipt_proposal",
        "provenance",
        "refusal",
        "reason",
    }
    if set(raw_outcome) != outcome_fields:
        raise SupervisorIntegrationError(
            "lane result outcome fields do not match its protocol"
        )
    raw_candidates = raw_outcome["candidates"]
    if not isinstance(raw_candidates, list):
        raise SupervisorIntegrationError(
            "lane result candidates must be an array"
        )
    candidates = []
    for raw_candidate in raw_candidates:
        if not isinstance(raw_candidate, Mapping):
            raise SupervisorIntegrationError(
                "lane result candidate must be an object"
            )
        if set(raw_candidate) != {"candidate", "source", "provenance"}:
            raise SupervisorIntegrationError(
                "lane result candidate fields do not match its protocol"
            )
        try:
            candidate = CandidateRecord.from_dict(raw_candidate["candidate"])
            provenance = raw_candidate["provenance"]
            if not isinstance(provenance, list):
                raise ValueError("candidate provenance must be an array")
            candidates.append(
                LaneCandidate(
                    candidate,
                    raw_candidate["source"],
                    tuple(provenance),
                )
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            raise SupervisorIntegrationError(
                "lane result candidate is invalid"
            ) from exc
    try:
        proposal = LaneReceiptProposal.from_dict(
            raw_outcome["receipt_proposal"]
        )
        refusal_value = raw_outcome["refusal"]
        refusal = None
        if refusal_value is not None:
            if not isinstance(refusal_value, Mapping) or set(refusal_value) != {
                "recipient_id", "lane", "code", "reason", "evidence"
            }:
                raise ValueError("lane result refusal is invalid")
            refusal = LaneRefusal(
                refusal_value["recipient_id"],
                refusal_value["lane"],
                refusal_value["code"],
                refusal_value["reason"],
                tuple(refusal_value["evidence"]),
            )
        outcome = LaneOutcome(
            lane=raw_outcome["lane"],
            recipient_id=raw_outcome["recipient_id"],
            candidates=tuple(candidates),
            receipt=proposal,
            provenance=tuple(raw_outcome["provenance"]),
            refusal=refusal,
            reason=raw_outcome["reason"],
        )
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise SupervisorIntegrationError(
            "lane result outcome is invalid"
        ) from exc
    if outcome.lane != task.lane or outcome.recipient_id != task.recipient_id:
        raise SupervisorIntegrationError(
            "lane result outcome identity differs from its task"
        )
    return outcome


def _read_task_result_reference(
    coordinator: SearchCoordinator,
    task: SearchTask,
    reference: ArtifactRef,
) -> LaneOutcome:
    try:
        raw = coordinator.archive.verify(reference)
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RuntimeError) as exc:
        raise SupervisorIntegrationError(
            "lane result artifact is unreadable"
        ) from exc
    if not isinstance(document, Mapping):
        raise SupervisorIntegrationError(
            "lane result artifact is not an object"
        )
    return _parse_task_result_document(document, task)


def _reference_for_scanned_result(
    coordinator: SearchCoordinator,
    path: Path,
    document: Mapping[str, Any],
) -> ArtifactRef:
    """Turn a discovered immutable result file back into its archive ref."""
    try:
        root = coordinator.archive.run_root.resolve(strict=False)
        resolved = path.resolve(strict=True)
        relative = resolved.relative_to(root).as_posix()
        raw = path.read_bytes()
    except (OSError, RuntimeError, ValueError) as exc:
        raise SupervisorIntegrationError(
            "scanned lane result artifact cannot be inspected"
        ) from exc
    canonical = canonical_bytes(document)
    if raw != canonical:
        raise SupervisorIntegrationError(
            "scanned lane result artifact is not canonical"
        )
    reference = ArtifactRef(
        hash_bytes(raw),
        relative,
        "application/json",
        len(raw),
    )
    try:
        coordinator.archive.verify(reference)
    except RuntimeError as exc:
        raise SupervisorIntegrationError(
            "scanned lane result artifact failed archive verification"
        ) from exc
    return reference


def _load_task_outcome(
    coordinator: SearchCoordinator,
    task: SearchTask,
    *,
    terminal_only: bool = False,
) -> Optional[Tuple[LaneOutcome, ArtifactRef]]:
    """Recover a durable lane outcome, including one not yet ledger-bound."""
    terminal = next(
        (
            event.payload
            for event in reversed(coordinator.events)
            if event.event_type == "task_completed"
            and getattr(event.payload, "task_id", None) == task.task_id
        ),
        None,
    )
    if terminal is not None:
        references = tuple(terminal.result_artifacts)
        if not references:
            raise SupervisorIntegrationError(
                "terminal lane task has no durable lane result artifact"
            )
        for reference in references:
            outcome = _read_task_result_reference(coordinator, task, reference)
            return outcome, reference
        raise SupervisorIntegrationError(
            "terminal lane task has no recoverable typed outcome"
        )
    if terminal_only:
        return None
    directory = coordinator.archive.run_root / "artifacts" / "lane_results"
    try:
        paths = sorted(directory.glob("*.json"))
    except OSError as exc:
        raise SupervisorIntegrationError(
            "lane result archive cannot be enumerated"
        ) from exc
    matches = []
    task_document = task.to_dict()
    for path in paths:
        try:
            raw = path.read_bytes()
            document = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(document, Mapping):
            continue
        if (
            document.get("protocol") != TASK_RESULT_PROTOCOL
            or not _same_task_identity(document.get("task"), task)
        ):
            continue
        reference = _reference_for_scanned_result(coordinator, path, document)
        outcome = _parse_task_result_document(document, task)
        matches.append((outcome, reference))
    if not matches:
        return None
    identities = {reference.content_hash for _outcome, reference in matches}
    if len(identities) != 1:
        raise SupervisorIntegrationError(
            "multiple durable lane outcomes disagree for one task"
        )
    return matches[0]


def _task_is_terminal(coordinator: SearchCoordinator, task_id: str) -> bool:
    return any(
        event.event_type == "task_completed"
        and getattr(event.payload, "task_id", None) == task_id
        for event in coordinator.events
    )


def _child_task(
    coordinator: SearchCoordinator,
    lane_task: SearchTask,
    candidate: LaneCandidate,
    budget_ordinal: int,
) -> SearchTask:
    candidate_parents = tuple(candidate.candidate.parent_candidate_ids)
    lane_parents = set(lane_task.parent_candidate_ids)
    if not set(candidate_parents).issubset(lane_parents):
        raise SupervisorIntegrationError(
            "candidate ancestry exceeds the coordinator-bound lane ancestry"
        )
    return coordinator.create_task(
        recipient_id=lane_task.recipient_id,
        lane=lane_task.lane,
        operation="materialize_candidate:" + candidate.candidate_id,
        parent_candidate_ids=candidate_parents,
        budget_ordinal=budget_ordinal,
    )


def _validate_child_terminals(
    coordinator: SearchCoordinator,
    lane_task: SearchTask,
    outcome: LaneOutcome,
    *,
    child_base: int,
    coordinator_limit: int,
) -> int:
    if outcome.lane != lane_task.lane or outcome.recipient_id != lane_task.recipient_id:
        raise SupervisorIntegrationError(
            "lane outcome identity differs from its scheduled task"
        )
    candidate_ids = {candidate.candidate_id for candidate in outcome.candidates}
    if not set(outcome.receipt.best_candidate_ids).issubset(candidate_ids):
        raise SupervisorIntegrationError(
            "lane receipt best candidates are outside the archived outcome"
        )
    children = _preflight_candidate_children(
        coordinator,
        lane_task,
        tuple(outcome.candidates),
        result_artifact=None,
        child_base=child_base,
        coordinator_limit=coordinator_limit,
    )
    for _lane_candidate, child, _result in children:
        if not _task_is_terminal(coordinator, child.task_id):
            raise SupervisorIntegrationError(
                "lane task is terminal before every candidate child is terminal"
            )
    return len(children)


def _preflight_candidate_children(
    coordinator: SearchCoordinator,
    lane_task: SearchTask,
    candidates: Sequence[LaneCandidate],
    *,
    result_artifact: Optional[ArtifactRef],
    child_base: int,
    coordinator_limit: int,
) -> Tuple[Tuple[LaneCandidate, SearchTask, TaskResult], ...]:
    """Validate the complete outcome before selecting bounded child tasks."""
    if isinstance(child_base, bool) or not isinstance(child_base, int) or child_base < 0:
        raise SupervisorIntegrationError("candidate child base ordinal is invalid")
    seen = set()
    validated = []
    for lane_candidate in candidates:
        if lane_candidate.candidate_id in seen:
            raise SupervisorIntegrationError(
                "lane outcome contains duplicate candidate identities"
            )
        seen.add(lane_candidate.candidate_id)
        candidate = lane_candidate.candidate
        if (
            candidate.recipient_id != lane_task.recipient_id
            or candidate.lane != lane_task.lane
        ):
            raise SupervisorIntegrationError(
                "candidate identity differs from the scheduled materialization task"
            )
        if not set(candidate.parent_candidate_ids).issubset(
            set(lane_task.parent_candidate_ids)
        ):
            raise SupervisorIntegrationError(
                "candidate ancestry exceeds the coordinator-bound lane ancestry"
            )
        expected_source_hash = candidate.source_artifact.content_hash
        source_bytes = lane_candidate.source.encode("utf-8") if lane_candidate.source else None
        if source_bytes is not None and hash_bytes(source_bytes) != expected_source_hash:
            raise SupervisorIntegrationError(
                "candidate source bytes differ from its immutable source identity"
            )
        try:
            archived_source = coordinator.archive.verify(candidate.source_artifact)
        except Exception as exc:  # noqa: BLE001
            if source_bytes is None:
                raise SupervisorIntegrationError(
                    "candidate source artifact is unavailable"
                ) from exc
            archived_source = None
        if archived_source is not None and source_bytes is not None and archived_source != source_bytes:
            raise SupervisorIntegrationError(
                "candidate source differs from its archived source artifact"
            )
        validated.append(lane_candidate)

    # Candidate IDs are already the canonical order used by the lane receipt.
    # Keep validating the complete outcome above, but spend coordinator budget
    # only on the bounded best prefix.
    selected = tuple(
        sorted(validated, key=lambda item: item.candidate_id)
        [:MAX_CHILD_TASKS_PER_BASE]
    )
    if child_base + len(selected) > coordinator_limit:
        raise SupervisorIntegrationError(
            "coordinator budget cannot materialize the selected lane candidates"
        )

    children = []
    for index, lane_candidate in enumerate(selected):
        try:
            child = _child_task(
                coordinator,
                lane_task,
                lane_candidate,
                child_base + index,
            )
            child_result = _candidate_task_result(
                child,
                lane_candidate,
                result_artifact,
            )
            coordinator._validate_result_binding(child, child_result)
        except SupervisorIntegrationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SupervisorIntegrationError(
                "candidate child result binding is invalid"
            ) from exc
        children.append((lane_candidate, child, child_result))
    return tuple(children)


def _fan_out_candidates(
    coordinator: SearchCoordinator,
    lane_task: SearchTask,
    outcome: LaneOutcome,
    result_artifact: ArtifactRef,
    *,
    child_base: int,
    coordinator_limit: int,
) -> int:
    """Materialize bounded candidates through deterministic single-result tasks."""
    candidates = tuple(outcome.candidates)
    if outcome.lane != lane_task.lane or outcome.recipient_id != lane_task.recipient_id:
        raise SupervisorIntegrationError(
            "lane outcome identity differs from its scheduled task"
        )
    candidate_ids = {candidate.candidate_id for candidate in candidates}
    if not set(outcome.receipt.best_candidate_ids).issubset(candidate_ids):
        raise SupervisorIntegrationError(
            "lane receipt best candidates are outside the archived outcome"
        )
    children = _preflight_candidate_children(
        coordinator,
        lane_task,
        candidates,
        result_artifact=result_artifact,
        child_base=child_base,
        coordinator_limit=coordinator_limit,
    )
    for lane_candidate, child, child_result in children:
        child = coordinator.schedule_task(child)
        if _task_is_terminal(coordinator, child.task_id):
            continue
        coordinator.commit_epoch((child_result,))
    return len(children)


def _terminal_proposal(
    coordinator: SearchCoordinator,
    task: SearchTask,
) -> Optional[LaneReceiptProposal]:
    loaded = _load_task_outcome(coordinator, task, terminal_only=True)
    return loaded[0].receipt if loaded is not None else None


def _consume_stop_request(
    coordinator: SearchCoordinator,
    run_root: Path,
    manifest: RunManifest,
) -> Optional[Any]:
    request = _load_stop_request(run_root, manifest)
    if request is None:
        return None
    active = _active_stop_event(coordinator.events)
    if request["state"] == STOP_REQUEST_ACKNOWLEDGED:
        if active is not None:
            raise SupervisorIntegrationError(
                "acknowledged stop request conflicts with an active stop"
            )
        if _resume_event_for_request(
            coordinator.events, request["request_id"]
        ) is None:
            raise SupervisorIntegrationError(
                "acknowledged stop request has no matching durable resume"
            )
        return None
    if active is None and _resume_event_for_request(
        coordinator.events, request["request_id"]
    ) is not None:
        raise SupervisorIntegrationError(
            "stop request is awaiting durable resume acknowledgement"
        )
    return coordinator.stop(reason=request["reason"], resumable=True)


def _find_event(
    events: Sequence[LedgerEvent],
    *,
    event_id: str,
    event_hash: str,
    event_type: str,
) -> LedgerEvent:
    for event in events:
        if (
            event.event_id == event_id
            and event.event_hash == event_hash
            and event.event_type == event_type
        ):
            return event
    raise SupervisorIntegrationError(
        "stop request references an event absent from the durable ledger"
    )


def _resume_stop_request(
    coordinator: SearchCoordinator,
    run_root: Path,
    manifest: RunManifest,
) -> LedgerEvent:
    """Durably resume one requested stop while the caller owns the lease."""
    request = _load_stop_request(run_root, manifest)
    if request is None:
        raise SupervisorIntegrationError("instrumented resume requires a stop request")
    events = coordinator.events
    active = _active_stop_event(events)
    if request["state"] == STOP_REQUEST_ACKNOWLEDGED:
        if active is not None:
            raise SupervisorIntegrationError(
                "acknowledged stop request conflicts with an active stop"
            )
        resume_event = _resume_event_for_request(
            events, request["request_id"]
        )
        if resume_event is None:
            raise SupervisorIntegrationError(
                "acknowledged stop request has no matching durable resume"
            )
    elif active is not None:
        resume_event = coordinator.resume(request_id=request["request_id"])
    else:
        resume_event = _resume_event_for_request(events, request["request_id"])
        if resume_event is None:
            raise SupervisorIntegrationError(
                "stop request has not reached a durable stop boundary"
            )

    resume = resume_event.payload
    if not isinstance(resume, RunResume):
        raise SupervisorIntegrationError("durable resume payload is not typed")
    stop_event = _find_event(
        coordinator.events,
        event_id=resume.stop_event_id,
        event_hash=resume.stop_event_hash,
        event_type="run_stopped",
    )
    if request["state"] == STOP_REQUEST_PENDING:
        acknowledged = _acknowledged_stop_request_document(
            request, stop_event, resume_event
        )
        _atomic_json(_stop_request_path(run_root), acknowledged)
    else:
        if (
            request.get("stop_event_id") != stop_event.event_id
            or request.get("stop_event_hash") != stop_event.event_hash
            or request.get("resume_event_id") != resume_event.event_id
            or request.get("resume_event_hash") != resume_event.event_hash
        ):
            raise SupervisorIntegrationError(
                "acknowledged stop request does not match the ledger transition"
            )
    return resume_event


def _factory_bound_manifest(manifest: RunManifest) -> bool:
    """Return whether the run carries the production factory bindings."""

    return (
        manifest.tool_identities.get(_FACTORY_TOOL_KEY) is not None
        and manifest.tool_identities.get(_FACTORY_MARKER_KEY) is not None
    )


def _completed_run_result(
    *,
    root: Path,
    manifest: RunManifest,
    coordinator: SearchCoordinator,
    executed: Sequence[str] = (),
    resumed: Sequence[str] = (),
) -> dict[str, Any]:
    """Return a completed result and, for factory runs, its canonical gate."""

    state = coordinator.state_dict()
    result: dict[str, Any] = {
        "command": "instrumented-run",
        "ok": True,
        "run_id": manifest.run_id,
        "run_root": str(root),
        "mode": INSTRUMENTED_MODE,
        "executed_task_ids": list(executed),
        "recovered_task_ids": list(resumed),
        "state": state,
    }
    if _factory_bound_manifest(manifest):
        receipt = archive_integration_gate(root, archive=coordinator.archive)
        result["integration_gate"] = receipt.to_dict()
    return result


def _run_instrumented_locked(
    *,
    root: Path,
    manifest: RunManifest,
    recipients: Tuple[Recipient, ...],
    lanes: Tuple[str, ...],
    task_count: int,
    coordinator: SearchCoordinator,
    had_prior_events: bool,
    adapters: Optional[LaneAdapters | Mapping[str, Any]],
    options: Optional[Mapping[str, Any]],
    lane_executor: Callable[..., LaneOutcome],
) -> dict[str, Any]:
    """Run the manifest while the caller holds the instrumented lease."""
    baseline_events = coordinator.events
    baseline_signature = (
        len(baseline_events),
        baseline_events[-1].event_hash if baseline_events else None,
    )

    def observe_stop() -> Optional[LedgerEvent]:
        requested = _consume_stop_request(coordinator, root, manifest)
        active = requested or _active_stop_event(coordinator.events)
        # A non-resumable completion stop is the durable success marker, not
        # an operator stop.  It is handled by the replay fast path below.
        return None if _is_completed_stop_event(active) else active

    stop_event = observe_stop()
    latest_transition = next(
        (
            event
            for event in reversed(coordinator.events)
            if event.event_type in {"run_stopped", "run_resumed"}
        ),
        None,
    )
    if stop_event is None and _is_completed_stop_event(latest_transition):
        return _completed_run_result(
            root=root,
            manifest=manifest,
            coordinator=coordinator,
            executed=(),
            resumed=(),
        )
    if stop_event is not None:
        state = coordinator.state_dict()
        return {
            "command": "instrumented-run",
            "ok": True,
            "run_id": manifest.run_id,
            "run_root": str(root),
            "mode": INSTRUMENTED_MODE,
            "executed_task_ids": [],
            "recovered_task_ids": [],
            "state": state,
        }
    durable_state_changed = not had_prior_events
    executed = []
    resumed = []
    child_offset = 0
    for lane_index, lane in enumerate(lanes):
        for recipient_index, recipient in enumerate(recipients):
            stop_event = observe_stop()
            if stop_event is not None:
                break
            parent_candidate_ids = _task_parent_candidate_ids(
                coordinator, recipient.recipient_id, lane
            )
            task = coordinator.create_task(
                recipient_id=recipient.recipient_id,
                lane=lane,
                operation="execute_lane",
                parent_candidate_ids=parent_candidate_ids,
                budget_ordinal=(lane_index * len(recipients)) + recipient_index,
            )
            task = coordinator.schedule_task(task)
            loaded = _load_task_outcome(coordinator, task)
            if _task_is_terminal(coordinator, task.task_id):
                if loaded is None:
                    raise SupervisorIntegrationError(
                        "terminal lane task has no recoverable typed outcome"
                    )
                outcome, reference = loaded
                child_count = _validate_child_terminals(
                    coordinator,
                    task,
                    outcome,
                    child_base=task_count + child_offset,
                    coordinator_limit=manifest.coordinator_budget.limit,
                )
                proposal = outcome.receipt
                resumed.append(task.task_id)
            else:
                if loaded is None:
                    started = coordinator.start_task(task.task_id)
                    outcome = lane_executor(
                        started,
                        manifest,
                        recipients,
                        adapters=adapters,
                        options=options,
                        read_only=True,
                    )
                    reference = coordinator.archive.put_json(
                        _task_result_document(task, outcome),
                        category="lane_results",
                        suffix=".json",
                    )
                    executed.append(task.task_id)
                else:
                    outcome, reference = loaded
                    coordinator.start_task(task.task_id)
                    resumed.append(task.task_id)
                child_count = _fan_out_candidates(
                    coordinator,
                    task,
                    outcome,
                    reference,
                    child_base=task_count + child_offset,
                    coordinator_limit=manifest.coordinator_budget.limit,
                )
                if not _task_is_terminal(coordinator, task.task_id):
                    coordinator.commit_epoch(
                        (_lane_task_result(task, outcome, reference),),
                    )
                if not _task_is_terminal(coordinator, task.task_id):
                    raise SupervisorIntegrationError(
                        "lane task did not reach a terminal state after fan-out"
                    )
                proposal = outcome.receipt
            child_offset += child_count
            before_receipt = coordinator.events
            coordinator.record_exhaustion(
                **proposal.to_coordinator_kwargs()
            )
            after_receipt = coordinator.events
            if len(after_receipt) != len(before_receipt):
                durable_state_changed = True
            elif after_receipt and before_receipt:
                durable_state_changed |= (
                    after_receipt[-1].event_hash != before_receipt[-1].event_hash
                )
            stop_event = observe_stop()
            if stop_event is not None:
                break
        if stop_event is not None:
            break
    final_events = coordinator.events
    if stop_event is not None:
        state = coordinator.state_dict()
        return {
            "command": "instrumented-run",
            "ok": True,
            "run_id": manifest.run_id,
            "run_root": str(root),
            "mode": INSTRUMENTED_MODE,
            "executed_task_ids": executed,
            "recovered_task_ids": resumed,
            "state": state,
        }
    stop_event = observe_stop()
    if stop_event is not None:
        state = coordinator.state_dict()
        return {
            "command": "instrumented-run",
            "ok": True,
            "run_id": manifest.run_id,
            "run_root": str(root),
            "mode": INSTRUMENTED_MODE,
            "executed_task_ids": executed,
            "recovered_task_ids": resumed,
            "state": state,
        }
    final_signature = (
        len(final_events),
        final_events[-1].event_hash if final_events else None,
    )
    durable_state_changed |= final_signature != baseline_signature
    if durable_state_changed:
        coordinator.write_checkpoint()
    # Keep the successful terminal marker after the checkpoint.  The
    # coordinator refuses mutations while stopped, so this ordering leaves
    # the completion stop as the final ledger event required by completed-run
    # consumers.  _append_event_once inside stop makes replay deterministic.
    if not any(
        _is_completed_stop_event(event)
        for event in coordinator.events
        if event.event_type == "run_stopped"
    ):
        coordinator.stop(reason="completed", resumable=False)
    return _completed_run_result(
        root=root,
        manifest=manifest,
        coordinator=coordinator,
        executed=executed,
        resumed=resumed,
    )


def _run_instrumented_entry(
    manifest_path: str | os.PathLike[str],
    *,
    adapters: Optional[LaneAdapters | Mapping[str, Any]] = None,
    options: Optional[Mapping[str, Any]] = None,
    landing: Optional[LandingCallback] = None,
    lease_path: Optional[Path] = None,
    lane_executor: Callable[..., LaneOutcome] = execute_task,
    resume: bool = False,
) -> dict[str, Any]:
    path, manifest = _load_manifest_file(manifest_path)
    root = _safe_run_root(path.parent)
    require_instrumented_manifest(manifest)
    recipients = _recipients(manifest)
    lanes = _ordered_lanes(manifest)
    task_count = len(recipients) * len(lanes)
    if manifest.coordinator_budget.limit > MAX_COORDINATOR_TASKS:
        raise SupervisorIntegrationError(
            "manifest coordinator budget exceeds the global task cap"
        )
    if task_count > manifest.coordinator_budget.limit:
        raise SupervisorIntegrationError(
            "manifest coordinator budget cannot schedule its selected lane subset"
        )

    oracle = None
    oracle_identity = manifest.tool_identities.get("full_oracle")
    if oracle_identity is not None and landing is not None:
        oracle = InstrumentedLandingOracle(root, oracle_identity, landing)

    ledger_path = root / "ledger.jsonl"
    try:
        had_prior_events = ledger_path.is_file() and ledger_path.stat().st_size > 0
    except OSError as exc:
        raise SupervisorIntegrationError(
            "run ledger cannot be inspected before execution"
        ) from exc

    with SupervisorLease(
        mode=INSTRUMENTED_MODE,
        run_id=manifest.run_id,
        record_ids=manifest.queue_record_ids,
        path=lease_path,
    ):
        # Factory-created runs carry a durable archive marker.  Verify their
        # current source, target, compiler, configuration, schema and lane
        # inputs while this process owns the run, before a coordinator can
        # append task_started or an adapter can observe a task.
        try:
            try:
                from .search_run_factory import verify_factory_runtime
            except ImportError:  # pragma: no cover - direct script compatibility
                from search_run_factory import verify_factory_runtime  # type: ignore
            verify_factory_runtime(root, manifest)
        except SupervisorIntegrationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SupervisorIntegrationError(
                "factory runtime evidence differs from the immutable run"
            ) from exc
        coordinator = SearchCoordinator(root, manifest, oracle=oracle)
        if resume:
            latest_transition = next(
                (
                    event
                    for event in reversed(coordinator.events)
                    if event.event_type in {"run_stopped", "run_resumed"}
                ),
                None,
            )
            if _is_completed_stop_event(latest_transition):
                return _completed_run_result(
                    root=root,
                    manifest=manifest,
                    coordinator=coordinator,
                )
            _resume_stop_request(coordinator, root, manifest)
        return _run_instrumented_locked(
            root=root,
            manifest=manifest,
            recipients=recipients,
            lanes=lanes,
            task_count=task_count,
            coordinator=coordinator,
            had_prior_events=had_prior_events,
            adapters=adapters,
            options=options,
            lane_executor=lane_executor,
        )


def run_instrumented(
    manifest_path: str | os.PathLike[str],
    *,
    adapters: Optional[LaneAdapters | Mapping[str, Any]] = None,
    options: Optional[Mapping[str, Any]] = None,
    landing: Optional[LandingCallback] = None,
    lease_path: Optional[Path] = None,
    lane_executor: Callable[..., LaneOutcome] = execute_task,
) -> dict[str, Any]:
    """Execute the frozen manifest through typed tasks and ledger receipts."""
    return _run_instrumented_entry(
        manifest_path,
        adapters=adapters,
        options=options,
        landing=landing,
        lease_path=lease_path,
        lane_executor=lane_executor,
    )


def resume_instrumented(
    manifest_path: str | os.PathLike[str],
    *,
    adapters: Optional[LaneAdapters | Mapping[str, Any]] = None,
    options: Optional[Mapping[str, Any]] = None,
    landing: Optional[LandingCallback] = None,
    lease_path: Optional[Path] = None,
    lane_executor: Callable[..., LaneOutcome] = execute_task,
) -> dict[str, Any]:
    """Resume one durable stop and continue the exact manifest under its lease."""
    result = _run_instrumented_entry(
        manifest_path,
        adapters=adapters,
        options=options,
        landing=landing,
        lease_path=lease_path,
        lane_executor=lane_executor,
        resume=True,
    )
    result["command"] = "instrumented-resume"
    return result


def status_instrumented(
    manifest_path: str | os.PathLike[str],
) -> dict[str, Any]:
    path, manifest = _load_manifest_file(manifest_path)
    require_instrumented_manifest(manifest)
    try:
        try:
            from .search_run_factory import verify_factory_archive
        except ImportError:  # pragma: no cover - direct script compatibility
            from search_run_factory import verify_factory_archive  # type: ignore
        verify_factory_archive(path.parent, manifest)
    except SupervisorIntegrationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise SupervisorIntegrationError(
            "factory archive integrity validation failed"
        ) from exc
    state = recover_run(_safe_run_root(path.parent))
    if state.manifest != manifest:
        raise SupervisorIntegrationError(
            "recovered manifest differs from the requested run"
        )
    return {
        "command": "instrumented-status",
        "ok": True,
        "mode": INSTRUMENTED_MODE,
        "run_id": manifest.run_id,
        "run_root": str(path.parent),
        "last_sequence": state.last_sequence,
        "last_event_hash": state.last_event_hash,
        "completed_task_ids": sorted(state.completed_task_ids),
        "incomplete_task_ids": sorted(
            task.task_id for task in state.incomplete_tasks
        ),
        "stopped": (
            state.stopped.to_dict() if state.stopped is not None else None
        ),
    }


__all__ = [
    "DEFAULT_LEASE_PATH",
    "DurableOracleError",
    "EVALUATOR_TOOL_KEY",
    "GATE_RECEIPT_PROTOCOL",
    "GATE_KIND_SMOKE",
    "GATE_KIND_MULTI_RECORD",
    "INSTRUMENTED_MODE",
    "InstrumentedLandingOracle",
    "IntegrationGateError",
    "IntegrationGateReceipt",
    "LEGACY_MODE",
    "LandingCallback",
    "MODE_TOOL_KEY",
    "SupervisorConflict",
    "SupervisorIntegrationError",
    "SupervisorLease",
    "SupervisorModeError",
    "archive_integration_gate",
    "integration_gate_identity_payload",
    "legacy_lease",
    "load_integration_gate",
    "mode_identity",
    "require_instrumented_manifest",
    "request_instrumented_stop",
    "resume_instrumented",
    "run_instrumented",
    "status_instrumented",
    "validate_integration_gate",
]
