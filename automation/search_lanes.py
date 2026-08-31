"""Read-only adapters for deterministic and structural search lanes.

The lane layer deliberately sits between repository evidence producers and the
search coordinator.  It accepts an explicit RunManifest subset, asks only the
named producer for evidence, and returns immutable in-memory candidates plus a
coordinator-compatible receipt proposal.  It never applies a candidate, writes
src, or reports to the queue.  The coordinator owns artifact materialization and
ledger events.

The producers in this repository predate the coordinator and some of their
high-level entry points enumerate the live queue or publish files.  This module
uses their narrow read-only indexes instead of those broad entry points.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence, Tuple

try:
    from .search_coordinator import LANE_TIERS
    from .search_types import (
        ArtifactRef,
        Budget,
        CandidateRecord,
        LANE_TOOL_KEYS,
        RunManifest,
        SearchTask,
        SearchValidationError,
        canonical_json,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_lane,
    )
except ImportError:  # pragma: no cover - direct script compatibility
    from search_coordinator import LANE_TIERS  # type: ignore
    from search_types import (  # type: ignore
        ArtifactRef,
        Budget,
        CandidateRecord,
        LANE_TOOL_KEYS,
        RunManifest,
        SearchTask,
        SearchValidationError,
        canonical_json,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_lane,
    )


REPO = Path(__file__).resolve().parent.parent
MODULE_IDENTITY = hash_canonical(
    {"module": "automation.search_lanes", "version": "1.0.0"}
)
DETERMINISTIC_LANES = (
    "upstream_current",
    "upstream_pinned",
    "upstream_open_pr",
    "mipsmatch_exact",
    "preserved_candidate",
    "shared_header",
    "transplant",
    "whole_tu",
    "dependency_closure",
    "multi_donor",
    "cfg_dataflow",
)
_COMPLETION_REASONS = frozenset(
    {
        "budget_exhausted",
        "search_space_exhausted",
        "inapplicable",
        "matched_pending_oracle",
        "operator_stop",
        "superseded_by_stronger_evidence",
    }
)

# Any of these options would cross the lane's read-only boundary.  They are
# rejected even when the caller supplies False-ish values such as "yes"; only
# truthy values are considered an attempted write.
_WRITE_OPTIONS = (
    "apply",
    "write",
    "write_src",
    "write_queue",
    "queue_report",
    "publish",
    "build",
    "mutate",
    "commit",
    "landing",
)


class LaneError(RuntimeError):
    """Base class for lane adapter errors."""


class SubsetViolation(LaneError):
    """The supplied recipients are not exactly the manifest subset."""


class ReadOnlyViolation(LaneError):
    """A caller attempted to give a lane a write authority."""


class UnsafeSemanticConstant(LaneError):
    """A register or branch displacement was presented as a semantic value."""


class IncompatibleDonor(LaneError):
    """A donor cannot be used for the selected recipient."""


class CandidateIdentityMismatch(LaneError):
    """A supplied candidate does not match its immutable source bytes."""


class AdapterSignatureError(LaneError):
    """An adapter does not accept the one documented invocation shape."""


class ImmutableReferenceError(LaneError):
    """An upstream reference was not resolved to an immutable identity."""


def _freeze_donor_json(value: Any, label: str) -> Any:
    """Deep-freeze one JSON-shaped donor value.

    Donor evidence crosses the index boundary and is retained by immutable
    generation records.  Freezing only the outer mapping leaves nested lists
    and mappings as caller-owned mutable aliases, which can change the
    serialized evidence after its content identity was computed.
    """

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise LaneError(f"{label} mapping keys must be strings")
        return MappingProxyType(
            {
                key: _freeze_donor_json(item, f"{label}.{key}")
                for key, item in value.items()
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_donor_json(item, f"{label}[{index}]")
            for index, item in enumerate(value)
        )
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise LaneError(f"{label} must contain JSON-compatible values")


def _thaw_donor_json(value: Any) -> Any:
    """Return an independent mutable JSON copy of frozen donor evidence."""

    if isinstance(value, Mapping):
        return {key: _thaw_donor_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_donor_json(item) for item in value]
    return value


@dataclass(frozen=True)
class Recipient:
    """The queue identity and read-only metadata needed by one lane."""

    recipient_id: str
    overlay: str
    function: str
    status: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_id(self.recipient_id, "recipient_id")
        if not isinstance(self.overlay, str):
            raise LaneError("recipient overlay must be a string")
        if not isinstance(self.function, str) or not self.function:
            raise LaneError("recipient function must be nonempty")
        if not isinstance(self.status, str):
            raise LaneError("recipient status must be a string")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def id(self) -> str:
        return self.recipient_id

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Recipient":
        if not isinstance(value, Mapping):
            raise LaneError("recipient must be an object")
        recipient_id = value.get("recipient_id", value.get("id"))
        if not isinstance(recipient_id, str):
            raise LaneError("recipient needs id or recipient_id")
        bits = recipient_id.split(":", 2)
        overlay = value.get("overlay")
        function = value.get("function")
        if not isinstance(overlay, str):
            overlay = bits[1] if len(bits) == 3 else ""
        if not isinstance(function, str):
            function = bits[2] if len(bits) == 3 else recipient_id
        known = {"id", "recipient_id", "overlay", "function", "status"}
        metadata = {str(k): v for k, v in value.items() if k not in known}
        return cls(
            recipient_id=recipient_id,
            overlay=overlay,
            function=function,
            status=str(value.get("status", "")),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        result = dict(self.metadata)
        result.update(
            {
                "id": self.recipient_id,
                "overlay": self.overlay,
                "function": self.function,
                "status": self.status,
            }
        )
        return result


QueueRecipient = Recipient
SearchRecipient = Recipient


@dataclass(frozen=True)
class LaneEvidence:
    """Small typed wrapper for a provenance edge.

    The JSON form is intentionally open because upstream, mipsmatch and the
    structural indexes expose different evidence fields.  The lane always adds
    recipient and source identities to the mapping before returning it.
    """

    kind: str
    source: str
    identity: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise LaneError("evidence kind must be nonempty")
        if not isinstance(self.source, str):
            raise LaneError("evidence source must be a string")
        validate_hash(self.identity, "evidence identity")
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    def to_dict(self) -> dict[str, Any]:
        result = dict(self.details)
        result.update(
            {
                "kind": self.kind,
                "source": self.source,
                "identity": self.identity,
            }
        )
        return result


Provenance = LaneEvidence


@dataclass(frozen=True)
class LaneCandidate:
    """A candidate source and its complete read-only provenance."""

    candidate: CandidateRecord
    source: str = ""
    provenance: Tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, CandidateRecord):
            raise LaneError("lane candidate needs a CandidateRecord")
        if not isinstance(self.source, str):
            raise LaneError("candidate source must be text")
        if self.source and hash_bytes(self.source.encode("utf-8")) != self.candidate.candidate_id:
            raise CandidateIdentityMismatch(
                "candidate source bytes disagree with candidate_id"
            )
        entries = []
        for item in self.provenance:
            if isinstance(item, LaneEvidence):
                item = item.to_dict()
            elif not isinstance(item, Mapping):
                raise LaneError("candidate provenance entries must be mappings")
            edge = dict(item)
            edge.setdefault("lane", self.candidate.lane)
            edge.setdefault("recipient_id", self.candidate.recipient_id)
            if "source_identity" not in edge and "identity" in edge:
                edge["source_identity"] = edge.pop("identity")
            if not isinstance(edge.get("kind"), str) or not edge["kind"]:
                raise LaneError("candidate provenance kind must be nonempty")
            if edge.get("lane") != self.candidate.lane:
                raise LaneError("candidate provenance lane differs from candidate")
            if edge.get("recipient_id") != self.candidate.recipient_id:
                raise LaneError("candidate provenance recipient differs from candidate")
            if not isinstance(edge.get("source"), str) or not edge["source"]:
                raise LaneError("candidate provenance source must be nonempty")
            if "source_identity" not in edge or "input_identity" not in edge:
                raise LaneError(
                    "candidate provenance needs source_identity and input_identity"
                )
            edge["source_identity"] = _identity(
                edge["source_identity"], label="candidate provenance source"
            )
            edge["input_identity"] = _identity(
                edge["input_identity"], label="candidate provenance input"
            )
            entries.append(MappingProxyType(edge))
        object.__setattr__(self, "provenance", tuple(entries))

    @property
    def record(self) -> CandidateRecord:
        return self.candidate

    @property
    def candidate_id(self) -> str:
        return self.candidate.candidate_id

    @property
    def recipient_id(self) -> str:
        return self.candidate.recipient_id

    @property
    def body(self) -> str:
        return self.source

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "source": self.source,
            "provenance": [dict(item) for item in self.provenance],
        }


CandidateEvidence = LaneCandidate


@dataclass(frozen=True)
class LaneRefusal:
    """A machine-readable reason a lane could not produce a candidate."""

    recipient_id: str
    lane: str
    code: str
    reason: str
    evidence: Tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        validate_id(self.recipient_id, "refusal recipient_id")
        validate_lane(self.lane)
        if not isinstance(self.code, str) or not self.code:
            raise LaneError("refusal code must be nonempty")
        if not isinstance(self.reason, str) or not self.reason:
            raise LaneError("refusal reason must be nonempty")
        object.__setattr__(
            self,
            "evidence",
            tuple(
                MappingProxyType(dict(item))
                if isinstance(item, Mapping)
                else MappingProxyType({"detail": str(item)})
                for item in self.evidence
            ),
        )

    @property
    def reason_code(self) -> str:
        return self.code

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipient_id": self.recipient_id,
            "lane": self.lane,
            "code": self.code,
            "reason": self.reason,
            "evidence": [dict(item) for item in self.evidence],
        }


Refusal = LaneRefusal


@dataclass(frozen=True)
class LaneReceiptProposal:
    """Coordinator-compatible receipt data that has not been materialized.

    Lane adapters are read-only.  They may calculate the exact identity and
    arguments for ``SearchCoordinator.record_exhaustion``, but they cannot
    publish the coordinator-owned receipt artifact or ledger event.  Keeping
    this as a separate type prevents a lane result from masquerading as a
    durable ``ExhaustionReceipt``.
    """

    recipient_id: str
    lane: str
    tier: str
    tool_identities: Mapping[str, str]
    config_identity: str
    input_identities: Tuple[str, ...]
    budget: Budget
    attempts: int
    rejection_counts: Mapping[str, int]
    best_candidate_ids: Tuple[str, ...]
    completion_reason: str
    reason: str = ""

    def __post_init__(self) -> None:
        validate_id(self.recipient_id, "proposal recipient_id")
        validate_lane(self.lane)
        if self.tier != LANE_TIERS[self.lane]:
            raise LaneError("proposal lane and tier do not agree")
        tools = dict(self.tool_identities)
        if not tools:
            raise LaneError("proposal tool_identities must not be empty")
        for key, value in tools.items():
            validate_id(key, "proposal tool identity key")
            validate_hash(value, "proposal tool identity")
        expected_tool_keys = set(LANE_TOOL_KEYS.get(self.lane, ()))
        if set(tools) != expected_tool_keys:
            raise LaneError("proposal tool identities must exactly match the lane manifest contract")
        object.__setattr__(self, "tool_identities", MappingProxyType(dict(sorted(tools.items()))))
        validate_hash(self.config_identity, "proposal config_identity")
        inputs = tuple(self.input_identities)
        if not inputs:
            raise LaneError("proposal needs at least one input identity")
        for item in inputs:
            validate_hash(item, "proposal input identity")
        if len(set(inputs)) != len(inputs):
            raise LaneError("proposal input identities must be unique")
        object.__setattr__(self, "input_identities", inputs)
        if not isinstance(self.budget, Budget):
            raise LaneError("proposal budget must be a Budget")
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int) or self.attempts < 0:
            raise LaneError("proposal attempts must be a nonnegative integer")
        rejections = dict(self.rejection_counts)
        for key, value in rejections.items():
            if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise LaneError("proposal rejection counts must be nonnegative integers")
        object.__setattr__(self, "rejection_counts", MappingProxyType(dict(sorted(rejections.items()))))
        best = tuple(self.best_candidate_ids)
        if len(set(best)) != len(best):
            raise LaneError("proposal best candidates must be unique")
        for item in best:
            validate_hash(item, "proposal best candidate")
        object.__setattr__(self, "best_candidate_ids", best)
        if self.completion_reason not in _COMPLETION_REASONS:
            raise LaneError("invalid proposal completion_reason")
        if not isinstance(self.reason, str):
            raise LaneError("proposal reason must be a string")

    @property
    def complete(self) -> bool:
        return True

    @property
    def receipt_id(self) -> str:
        return hash_canonical(self._identity_payload())

    @property
    def materialized(self) -> bool:
        return False

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "recipient_id": self.recipient_id,
            "lane": self.lane,
            "tier": self.tier,
            "tool_identities": dict(self.tool_identities),
            "config_identity": self.config_identity,
            "input_identities": list(self.input_identities),
            "budget": self.budget.to_dict(),
            "attempts": self.attempts,
            "rejection_counts": dict(self.rejection_counts),
            "best_candidate_ids": list(self.best_candidate_ids),
            "complete": True,
            "completion_reason": self.completion_reason,
        }

    def to_coordinator_kwargs(self) -> dict[str, Any]:
        """Return only arguments accepted by ``record_exhaustion``."""
        return {
            "recipient_id": self.recipient_id,
            "lane": self.lane,
            "tier": self.tier,
            "input_identities": self.input_identities,
            "budget_unit": self.budget.unit,
            "budget_limit": self.budget.limit,
            "budget_consumed": self.budget.consumed,
            "attempts": self.attempts,
            "rejection_counts": dict(self.rejection_counts),
            "best_candidate_ids": self.best_candidate_ids,
            "completion_reason": self.completion_reason,
            "reason": self.reason or "lane complete",
            "tool_identities": dict(self.tool_identities),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LaneReceiptProposal":
        """Rebuild a proposal archived by the supervisor after a restart."""
        if not isinstance(value, Mapping):
            raise LaneError("receipt proposal must be an object")
        fields = {
            "recipient_id", "lane", "tier", "tool_identities",
            "config_identity", "input_identities", "budget", "attempts",
            "rejection_counts", "best_candidate_ids", "completion_reason",
            "reason", "receipt_id", "complete", "materialized",
        }
        missing = fields.difference(value)
        if missing:
            raise LaneError(
                "receipt proposal is missing fields: "
                + ", ".join(sorted(missing))
            )
        unknown = set(value).difference(fields)
        if unknown:
            raise LaneError("receipt proposal has unknown fields")
        proposal = cls(
            recipient_id=value["recipient_id"],
            lane=value["lane"],
            tier=value["tier"],
            tool_identities=value["tool_identities"],
            config_identity=value["config_identity"],
            input_identities=tuple(value["input_identities"]),
            budget=Budget.from_dict(value["budget"]),
            attempts=value["attempts"],
            rejection_counts=value["rejection_counts"],
            best_candidate_ids=tuple(value["best_candidate_ids"]),
            completion_reason=value["completion_reason"],
            reason=value.get("reason", ""),
        )
        declared = value.get("receipt_id")
        if declared is not None and declared != proposal.receipt_id:
            raise LaneError("receipt proposal identity changed")
        if value.get("complete", True) is not True:
            raise LaneError("receipt proposal must be complete")
        if value.get("materialized", False) is not False:
            raise LaneError("archived proposal cannot claim coordinator materialization")
        return proposal

    def to_dict(self) -> dict[str, Any]:
        """Serialize a proposal without inventing a receipt artifact."""
        return dict(
            self._identity_payload(),
            receipt_id=self.receipt_id,
            reason=self.reason,
            materialized=False,
        )


@dataclass(frozen=True)
class LaneOutcome:
    """One recipient's immutable lane result and receipt proposal."""

    lane: str
    recipient_id: str
    candidates: Tuple[LaneCandidate, ...]
    receipt: LaneReceiptProposal
    provenance: Tuple[Mapping[str, Any], ...] = ()
    refusal: Optional[LaneRefusal] = None
    reason: str = ""

    def __post_init__(self) -> None:
        validate_lane(self.lane)
        validate_id(self.recipient_id, "outcome recipient_id")
        if not isinstance(self.receipt, LaneReceiptProposal):
            raise LaneError("lane outcome needs an unmaterialized receipt proposal")
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(
            self,
            "provenance",
            tuple(
                MappingProxyType(dict(item))
                if isinstance(item, Mapping)
                else MappingProxyType({"detail": str(item)})
                for item in self.provenance
            ),
        )
        if self.refusal is not None and self.refusal.recipient_id != self.recipient_id:
            raise LaneError("refusal recipient differs from outcome")
        if self.receipt.recipient_id != self.recipient_id or self.receipt.lane != self.lane:
            raise LaneError("receipt identity differs from outcome")

    @property
    def exhausted(self) -> bool:
        return self.receipt.complete

    @property
    def candidate_records(self) -> Tuple[CandidateRecord, ...]:
        return tuple(item.candidate for item in self.candidates)

    @property
    def inapplicable(self) -> bool:
        return self.receipt.completion_reason == "inapplicable"

    @property
    def receipt_proposal(self) -> LaneReceiptProposal:
        return self.receipt

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "recipient_id": self.recipient_id,
            "candidates": [item.to_dict() for item in self.candidates],
            "receipt_proposal": self.receipt.to_dict(),
            "provenance": [dict(item) for item in self.provenance],
            "refusal": self.refusal.to_dict() if self.refusal else None,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class LaneBatch:
    """Results for every recipient in one exact manifest subset."""

    lane: str
    outcomes: Tuple[LaneOutcome, ...]

    def __post_init__(self) -> None:
        validate_lane(self.lane)
        object.__setattr__(self, "outcomes", tuple(self.outcomes))
        if any(item.lane != self.lane for item in self.outcomes):
            raise LaneError("batch contains another lane")

    def __iter__(self) -> Iterator[LaneOutcome]:
        return iter(self.outcomes)

    def __len__(self) -> int:
        return len(self.outcomes)

    def __getitem__(self, index: int) -> LaneOutcome:
        return self.outcomes[index]

    @property
    def candidates(self) -> Tuple[LaneCandidate, ...]:
        return tuple(item for outcome in self.outcomes for item in outcome.candidates)

    @property
    def candidate_records(self) -> Tuple[CandidateRecord, ...]:
        return tuple(item.candidate for item in self.candidates)

    @property
    def receipts(self) -> Tuple[LaneReceiptProposal, ...]:
        return tuple(item.receipt for item in self.outcomes)

    @property
    def refusals(self) -> Tuple[LaneRefusal, ...]:
        return tuple(
            item.refusal for item in self.outcomes if item.refusal is not None
        )

    @property
    def receipt(self) -> Optional[LaneReceiptProposal]:
        return self.receipts[0] if len(self.receipts) == 1 else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "outcomes": [item.to_dict() for item in self.outcomes],
        }


@dataclass(frozen=True)
class LaneRun:
    """Results for an explicit list of lanes over one explicit subset."""

    batches: Tuple[LaneBatch, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "batches", tuple(self.batches))

    def __iter__(self) -> Iterator[LaneBatch]:
        return iter(self.batches)

    def __len__(self) -> int:
        return len(self.batches)

    def __getitem__(self, index: int) -> LaneBatch:
        return self.batches[index]

    @property
    def candidates(self) -> Tuple[LaneCandidate, ...]:
        return tuple(item for batch in self.batches for item in batch.candidates)

    @property
    def receipts(self) -> Tuple[LaneReceiptProposal, ...]:
        return tuple(item.receipt for batch in self.batches for item in batch.outcomes)

    def to_dict(self) -> dict[str, Any]:
        return {"batches": [item.to_dict() for item in self.batches]}


@dataclass(frozen=True)
class LaneAdapters:
    """Optional read-only producer callbacks used by tests and operators."""

    upstream_current: Optional[Callable[[Recipient], Any]] = None
    upstream_pinned: Optional[Callable[[Recipient], Any]] = None
    upstream_open_pr: Optional[Callable[[Recipient], Any]] = None
    mipsmatch_exact: Optional[Callable[[Recipient], Any]] = None
    preserved_candidate: Optional[Callable[[Recipient], Any]] = None
    shared_header: Optional[Callable[[Recipient], Any]] = None
    transplant: Optional[Callable[[Recipient], Any]] = None
    whole_tu: Optional[Callable[[Recipient], Any]] = None
    dependency_closure: Optional[Callable[[Recipient], Any]] = None
    multi_donor: Optional[Callable[[Recipient], Any]] = None
    cfg_dataflow: Optional[Callable[[Recipient], Any]] = None

    def for_lane(self, lane: str) -> Optional[Callable[[Recipient], Any]]:
        return getattr(self, lane, None)

    @classmethod
    def from_mapping(cls, value: Optional[Mapping[str, Any]]) -> "LaneAdapters":
        if value is None:
            return cls()
        names = {field.name for field in dataclasses.fields(cls)}
        unknown = set(value).difference(names)
        if unknown:
            raise LaneError("unknown adapter(s): " + ", ".join(sorted(unknown)))
        for name, callback in value.items():
            if callback is not None and not callable(callback):
                raise LaneError("adapter must be callable: " + str(name))
        return cls(**{name: value.get(name) for name in names})


LaneProviders = LaneAdapters


@dataclass(frozen=True)
class LaneContext:
    """Explicit execution context.  The context itself carries no writers."""

    manifest: Any
    recipients: Tuple[Recipient, ...]
    adapters: LaneAdapters = field(default_factory=LaneAdapters)
    repo_root: Path = REPO
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized = validate_recipient_subset(self.manifest, self.recipients)
        object.__setattr__(self, "recipients", normalized)
        object.__setattr__(self, "repo_root", Path(self.repo_root))
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))


@dataclass(frozen=True)
class DonorEvidence:
    """A semantic donor bound to a recipient and a source identity.

    The first fields intentionally match the later context-search interface in
    the approved implementation plan.  Optional fields let this tranche carry
    declaration and signature evidence without inventing a second donor type.
    """

    donor_id: str
    recipient_id: str
    version: str
    source: Any
    match_kind: str
    signature: str
    body: Optional[str] = None
    symbol: Optional[str] = None
    instruction_signature: Optional[str] = None
    cfg_signature: Optional[str] = None
    dataflow_signature: Optional[str] = None
    declarations: Mapping[str, Any] = field(default_factory=dict)
    constants: Mapping[str, Any] = field(default_factory=dict)
    structural_differences: Tuple[str, ...] = ()
    compatible: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_id(self.donor_id, "donor_id")
        if not isinstance(self.recipient_id, str) or not self.recipient_id:
            raise LaneError("donor recipient_id must be nonempty")
        if not isinstance(self.version, str):
            raise LaneError("donor version must be a string")
        if not isinstance(self.match_kind, str) or not self.match_kind:
            raise LaneError("donor match_kind must be nonempty")
        if not isinstance(self.signature, str) or not self.signature:
            raise LaneError("donor signature must be nonempty")
        if self.source is not None and not isinstance(self.source, (str, ArtifactRef)):
            raise LaneError("donor source must be a path or ArtifactRef")
        if self.body is not None and not isinstance(self.body, str):
            raise LaneError("donor body must be text or null")
        for name, value in (
            ("declarations", self.declarations),
            ("constants", self.constants),
            ("metadata", self.metadata),
        ):
            if not isinstance(value, Mapping):
                raise LaneError(f"donor {name} must be a mapping")
            object.__setattr__(
                self,
                name,
                _freeze_donor_json(value, f"donor {name}"),
            )
        if not isinstance(self.structural_differences, (tuple, list)):
            raise LaneError("donor structural differences must be a tuple or list")
        try:
            differences = tuple(self.structural_differences)
        except (TypeError, ValueError) as exc:
            raise LaneError("donor structural differences must be a sequence") from exc
        if any(not isinstance(item, str) for item in differences):
            raise LaneError("donor structural differences must be strings")
        object.__setattr__(self, "structural_differences", differences)

    @property
    def source_path(self) -> str:
        if isinstance(self.source, ArtifactRef):
            return self.source.path
        return self.source if isinstance(self.source, str) else ""

    @property
    def source_identity(self) -> str:
        if isinstance(self.source, ArtifactRef):
            return self.source.content_hash
        declared = self.metadata.get("source_identity")
        if declared is not None:
            try:
                declared = validate_hash(declared, "donor source identity")
            except SearchValidationError:
                return ""
            if self.body is not None and declared != hash_bytes(self.body.encode("utf-8")):
                return ""
            return declared
        if isinstance(self.body, str) and self.body:
            return hash_bytes(self.body.encode("utf-8"))
        return ""

    def to_dict(self) -> dict[str, Any]:
        source = self.source.to_dict() if isinstance(self.source, ArtifactRef) else self.source
        return {
            "donor_id": self.donor_id,
            "recipient_id": self.recipient_id,
            "version": self.version,
            "source": source,
            "match_kind": self.match_kind,
            "signature": self.signature,
            "body": self.body,
            "symbol": self.symbol,
            "instruction_signature": self.instruction_signature,
            "cfg_signature": self.cfg_signature,
            "dataflow_signature": self.dataflow_signature,
            "declarations": _thaw_donor_json(self.declarations),
            "constants": _thaw_donor_json(self.constants),
            "structural_differences": list(self.structural_differences),
            "compatible": self.compatible,
            "metadata": _thaw_donor_json(self.metadata),
        }


@dataclass(frozen=True)
class StructuralTriangulation:
    donors: Tuple[DonorEvidence, ...]
    declarations: Mapping[str, Any]
    constants: Mapping[str, Any]
    structural_differences: Tuple[str, ...]
    refusals: Tuple[LaneRefusal, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "donors", tuple(self.donors))
        object.__setattr__(self, "declarations", MappingProxyType(dict(self.declarations)))
        object.__setattr__(self, "constants", MappingProxyType(dict(self.constants)))
        object.__setattr__(self, "structural_differences", tuple(self.structural_differences))
        object.__setattr__(self, "refusals", tuple(self.refusals))


@dataclass
class _Discovery:
    candidates: list[LaneCandidate] = field(default_factory=list)
    provenance: list[Mapping[str, Any]] = field(default_factory=list)
    input_identities: list[str] = field(default_factory=list)
    rejection_counts: Counter[str] = field(default_factory=Counter)
    attempts: int = 0
    completion_reason: str = "search_space_exhausted"
    reason: str = ""
    refusal_code: Optional[str] = None


def _value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _manifest_ids(manifest: Any) -> Tuple[str, ...]:
    if not isinstance(manifest, RunManifest):
        raise SubsetViolation("manifest must be a typed RunManifest")
    ids = manifest.queue_record_ids
    if not isinstance(ids, tuple):
        raise SubsetViolation("manifest queue_record_ids are not immutable")
    result = tuple(ids)
    for item in result:
        validate_id(item, "manifest queue_record_id")
    if len(set(result)) != len(result):
        raise SubsetViolation("manifest queue_record_ids contain duplicates")
    return result


def _manifest_hash(manifest: Any, key: str) -> str:
    value = _value(manifest, key)
    if value is None:
        raise LaneError("manifest is missing " + key)
    try:
        return validate_hash(value, key)
    except SearchValidationError as exc:
        raise LaneError("manifest has invalid " + key) from exc


def _manifest_tools(manifest: Any) -> dict[str, str]:
    value = _value(manifest, "tool_identities", {})
    if not isinstance(value, Mapping) or not value:
        raise LaneError("manifest tool_identities must be a nonempty mapping")
    result: dict[str, str] = {}
    for key, item in value.items():
        try:
            name = validate_id(key, "tool identity key")
            result[name] = validate_hash(item, "tool identity")
        except SearchValidationError as exc:
            raise LaneError("manifest has invalid tool identity") from exc
    return dict(sorted(result.items()))


def _manifest_config(manifest: Any) -> str:
    return _manifest_hash(manifest, "config_identity")


def _manifest_source(manifest: Any) -> str:
    return _manifest_hash(manifest, "source_identity")


def _manifest_compiler(manifest: Any) -> str:
    return _manifest_hash(manifest, "compiler_identity")


def _manifest_schema(manifest: Any) -> str:
    return _manifest_hash(manifest, "schema_identity")


def _manifest_target(manifest: Any, recipient_id: str) -> str:
    values = _value(manifest, "target_identities")
    if not isinstance(values, Mapping):
        raise LaneError("manifest target_identities must be a nonempty mapping")
    for key, value in values.items():
        try:
            validate_id(key, "target identity key")
            validate_hash(value, "target identity")
        except SearchValidationError as exc:
            raise LaneError("manifest has invalid target identity") from exc
    target = values.get(recipient_id)
    if target is None:
        raise LaneError("manifest has no target identity for " + recipient_id)
    try:
        return validate_hash(target, "target identity")
    except SearchValidationError as exc:
        raise LaneError("manifest has invalid target identity") from exc


def _manifest_lane_budget(manifest: Any, lane: str) -> Budget:
    """Return the typed, immutable lane budget bound by the run manifest.

    Older callers sometimes wrapped a plain manifest dictionary with an
    untyped lane_budgets extension.  That envelope is intentionally not a
    supported authority: callers must construct a validated RunManifest.
    """
    if not isinstance(manifest, RunManifest):
        raise LaneError("lane adapters require a typed RunManifest")
    try:
        budget = manifest.lane_budgets[lane]
    except (KeyError, TypeError):
        raise LaneError("manifest must define a budget for lane " + lane)
    if not isinstance(budget, Budget):
        # A RunManifest normally makes this impossible, but keep the boundary
        # defensive if a caller has manufactured an invalid object.
        raise LaneError("manifest has invalid budget for lane " + lane)
    if budget.consumed != 0:
        raise LaneError("manifest lane budget must start with zero consumption")
    return budget

def _manifest_lane_tools(manifest: RunManifest, lane: str) -> dict[str, str]:
    """Return the exact manifest tool identity set contracted for one lane."""
    keys = LANE_TOOL_KEYS.get(lane)
    if not keys:
        raise LaneError("lane has no manifest tool contract")
    tools: dict[str, str] = {}
    for key in keys:
        value = manifest.tool_identities.get(key)
        if value is None:
            raise LaneError(
                "manifest is missing tool identity " + key + " for lane " + lane
            )
        tools[key] = value
    return dict(sorted(tools.items()))

def _validate_manifest(manifest: Any, recipient_ids: Sequence[str], lane: str) -> None:
    """Validate every identity consumed by a lane before calling a producer."""
    _manifest_ids(manifest)
    _manifest_source(manifest)
    _manifest_config(manifest)
    _manifest_compiler(manifest)
    _manifest_schema(manifest)
    _manifest_tools(manifest)
    for recipient_id in recipient_ids:
        _manifest_target(manifest, recipient_id)
    _manifest_lane_budget(manifest, lane)


def _coerce_recipient(value: Any) -> Recipient:
    if isinstance(value, Recipient):
        return value
    if isinstance(value, str):
        bits = value.split(":", 2)
        return Recipient(
            value,
            bits[1] if len(bits) == 3 else "",
            bits[2] if len(bits) == 3 else value,
        )
    if isinstance(value, Mapping):
        return Recipient.from_dict(value)
    recipient_id = _value(value, "recipient_id", _value(value, "id"))
    if isinstance(recipient_id, str):
        return Recipient.from_dict(
            {
                "id": recipient_id,
                "overlay": _value(value, "overlay", ""),
                "function": _value(value, "function", recipient_id),
                "status": _value(value, "status", ""),
            }
        )
    raise SubsetViolation("recipient has no explicit id")


def validate_recipient_subset(
    manifest: Any, recipients: Mapping[str, Any] | Iterable[Any]
) -> Tuple[Recipient, ...]:
    """Require the supplied recipient set to equal manifest.queue_record_ids.

    This function never reads the queue.  A missing records argument is an
    error, rather than permission to enumerate todo, near or deferred state.
    """

    try:
        if not isinstance(manifest, RunManifest):
            manifest = RunManifest.from_dict(manifest)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise SubsetViolation("manifest is not a valid typed RunManifest") from exc
    expected = set(_manifest_ids(manifest))
    if isinstance(recipients, Mapping):
        supplied_keys = set(recipients)
        if any(not isinstance(key, str) for key in supplied_keys):
            raise SubsetViolation("recipient mapping keys must be strings")
        if supplied_keys != expected:
            missing = sorted(expected.difference(supplied_keys))
            extra = sorted(supplied_keys.difference(expected))
            detail = []
            if missing:
                detail.append("missing=" + ",".join(missing))
            if extra:
                detail.append("extra=" + ",".join(extra))
            raise SubsetViolation(
                "recipient mapping must equal manifest subset (" + "; ".join(detail) + ")"
            )
        values = [recipients[key] for key in sorted(expected)]
    else:
        if recipients is None:
            raise SubsetViolation("explicit recipients are required; queue fallback is forbidden")
        values = list(recipients)
    normalized = tuple(_coerce_recipient(item) for item in values)
    supplied = [item.recipient_id for item in normalized]
    if len(set(supplied)) != len(supplied) or set(supplied) != expected:
        missing = sorted(expected.difference(supplied))
        extra = sorted(set(supplied).difference(expected))
        detail = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if extra:
            detail.append("extra=" + ",".join(extra))
        raise SubsetViolation(
            "recipient iterable must equal manifest subset (" + "; ".join(detail) + ")"
        )
    return tuple(sorted(normalized, key=lambda item: item.recipient_id))


assert_exact_subset = validate_recipient_subset
validate_manifest_subset = validate_recipient_subset


def _repo_root(options: Mapping[str, Any]) -> Path:
    value = options.get("repo_root", REPO)
    if isinstance(value, ArtifactRef):
        value = value.path
    if not isinstance(value, (str, Path)):
        raise LaneError("repo_root must be a path")
    root = Path(value).resolve(strict=False)
    if not root.is_dir():
        raise LaneError("repo_root must name an existing directory")
    return root


def _relative_path(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value:
        return None
    try:
        raw = value.replace("\\", "/")
        if raw.startswith("/") or re.match(r"^[A-Za-z]:/", raw):
            return None
        parts = raw.split("/")
        if any(part in ("", ".", "..") for part in parts):
            return None
        return raw
    except (AttributeError, TypeError):
        return None


def _resolve_contained_path(path_value: Any, root: Path) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve a path before checking containment, including symlink targets."""
    raw_value = path_value.path if isinstance(path_value, ArtifactRef) else path_value
    if not isinstance(raw_value, (str, Path)) or not raw_value:
        return None, None
    raw_text = str(raw_value).replace("\\", "/")
    raw = Path(raw_text)
    root_resolved = Path(root).resolve(strict=False)
    candidate = raw if raw.is_absolute() else root_resolved / raw
    try:
        resolved = candidate.resolve(strict=False)
        relative = resolved.relative_to(root_resolved)
    except (OSError, RuntimeError, ValueError):
        return None, None
    relative_text = str(relative).replace("\\", "/")
    if _relative_path(relative_text) is None:
        return None, None
    return resolved, relative_text


def _read_repo_text(path_value: Any, root: Path) -> Tuple[str, str]:
    path, relative = _resolve_contained_path(path_value, root)
    if path is None or relative is None:
        return "", ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return "", ""
    return text, relative


def _file_identity(path_value: Any, root: Path) -> str:
    path, _relative = _resolve_contained_path(path_value, root)
    if path is None:
        return ""
    try:
        return hash_bytes(path.read_bytes())
    except OSError:
        return ""


def _mask_c_noncode(text: str) -> str:
    """Mask comments and literals while preserving offsets and newlines."""
    chars = list(text)
    index = 0
    state = "code"
    while index < len(text):
        current = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if current == "/" and following == "/":
                chars[index] = " "
                chars[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if current == "/" and following == "*":
                chars[index] = " "
                chars[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if current == '"':
                chars[index] = " "
                index += 1
                state = "string"
                continue
            if current == "'":
                chars[index] = " "
                index += 1
                state = "character"
                continue
            index += 1
            continue
        if state == "line_comment":
            if current == "\n":
                state = "code"
                index += 1
            else:
                chars[index] = " "
                index += 1
            continue
        if state == "block_comment":
            if current == "*" and following == "/":
                chars[index] = " "
                chars[index + 1] = " "
                index += 2
                state = "code"
            else:
                if current != "\n":
                    chars[index] = " "
                index += 1
            continue
        if state in {"string", "character"}:
            if current == "\\":
                if current != "\n":
                    chars[index] = " "
                index += 1
                if index < len(text):
                    if text[index] != "\n":
                        chars[index] = " "
                    index += 1
                continue
            if (state == "string" and current == '"') or (
                state == "character" and current == "'"
            ):
                chars[index] = " "
                index += 1
                state = "code"
            else:
                if current != "\n":
                    chars[index] = " "
                index += 1
    return "".join(chars)


def _extract_function(text: str, function: str) -> str:
    """Extract one C definition while ignoring comments and C literals."""
    if not text:
        return ""
    masked = _mask_c_noncode(text)
    pattern = re.compile(
        r"(?m)^[ \t]*(?:(?:static|inline|extern)[ \t]+)*"
        r"[A-Za-z_][A-Za-z0-9_ \t\*]*?\b"
        + re.escape(function)
        + r"[ \t]*\([^;{}]*\)[ \t]*\{"
    )
    match = pattern.search(masked)
    if match is None:
        return ""
    start = masked.find("{", match.start(), match.end())
    depth = 0
    index = start
    while index < len(masked):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start(): index + 1]
        index += 1
    return ""


def _base_function(function: str) -> str:
    return re.sub(r"_from_[A-Za-z0-9_]+$", "", function)


def _path_text(path: Any) -> str:
    if isinstance(path, ArtifactRef):
        return path.path
    return str(path) if isinstance(path, str) else ""


def _call_fetcher(fetcher: Callable[..., Any], *args: Any) -> Any:
    """Call an adapter in its one documented shape.

    Signature binding happens before invocation.  A ``TypeError`` raised by
    the provider itself therefore propagates unchanged and is never mistaken
    for an arity mismatch.
    """
    if not callable(fetcher):
        raise AdapterSignatureError("adapter must be callable")
    try:
        signature = inspect.signature(fetcher)
    except (TypeError, ValueError):
        # Some extension callables do not expose a signature.  Invoke once and
        # preserve any provider exception rather than probing alternate arities.
        return fetcher(*args)
    try:
        signature.bind(*args)
    except TypeError as exc:
        raise AdapterSignatureError(
            f"adapter requires the documented {len(args)}-argument shape"
        ) from exc
    return fetcher(*args)


def _identity(value: Any, *, root: Optional[Path] = None, label: str = "identity") -> str:
    """Return an existing or content-derived identity, never a path digest."""
    if isinstance(value, ArtifactRef):
        return validate_hash(value.content_hash, label)
    if isinstance(value, bytes):
        return hash_bytes(value)
    if isinstance(value, str):
        try:
            return validate_hash(value, label)
        except SearchValidationError:
            if root is not None:
                identity = _file_identity(value, root)
                if identity:
                    return identity
            raise LaneError(f"{label} must be a content hash or resolved immutable reference")
    if isinstance(value, Mapping):
        for key in ("content_hash", "source_identity", "resolved_identity", "reference_identity"):
            if key in value:
                try:
                    return validate_hash(value[key], label)
                except SearchValidationError as exc:
                    raise LaneError(f"{label} has an invalid hash") from exc
        content = value.get("content")
        if isinstance(content, str):
            return hash_bytes(content.encode("utf-8"))
        if isinstance(content, bytes):
            return hash_bytes(content)
    if isinstance(value, Path) and root is not None:
        identity = _file_identity(value, root)
        if identity:
            return identity
    raise LaneError(f"{label} must be a content hash or resolved immutable reference")


def _provenance(
    *,
    lane: str,
    recipient: Recipient,
    kind: str,
    source: str,
    details: Optional[Mapping[str, Any]] = None,
    root: Optional[Path] = None,
    source_identity: Optional[str] = None,
    input_identity: Optional[str] = None,
) -> dict[str, Any]:
    payload = dict(details or {})
    payload.update({"kind": kind, "lane": lane, "recipient_id": recipient.recipient_id})
    payload.setdefault("source", source)
    declared_source = (
        source_identity if source_identity is not None else payload.get("source_identity")
    )
    if declared_source is None:
        content = payload.get("source_content")
        if isinstance(content, (str, bytes)):
            declared_source = _identity(content, label="provenance source")
        else:
            declared_source = _identity(source, root=root, label="provenance source")
    else:
        declared_source = _identity(declared_source, label="provenance source")
    payload["source_identity"] = declared_source
    declared_input = (
        input_identity
        if input_identity is not None
        else payload.get("input_identity", declared_source)
    )
    payload["input_identity"] = _identity(declared_input, label="provenance input")
    return payload


def _source_candidate(
    *,
    lane: str,
    recipient: Recipient,
    source: str,
    provenance: Sequence[Mapping[str, Any]] = (),
    source_path: Optional[str] = None,
    parent_candidate_ids: Sequence[str] = (),
    mutation_id: Optional[str] = None,
) -> Optional[LaneCandidate]:
    if not isinstance(source, str) or not source:
        return None
    source_hash = hash_bytes(source.encode("utf-8"))
    relative = _relative_path(source_path)
    if relative is None:
        relative = "artifacts/sources/" + source_hash[7:] + ".c"
    artifact = ArtifactRef(
        source_hash,
        relative,
        "text/x-c",
        len(source.encode("utf-8")),
    )
    record = CandidateRecord(
        candidate_id=source_hash,
        recipient_id=recipient.recipient_id,
        source_artifact=artifact,
        parent_candidate_ids=tuple(parent_candidate_ids),
        mutation_id=mutation_id,
        lane=lane,
        depth=len(tuple(parent_candidate_ids)),
        evaluation=None,
        status="materialized",
    )
    entries = list(provenance)
    entries.append(
        _provenance(
            lane=lane,
            recipient=recipient,
            kind="candidate_source",
            source=relative or "candidate",
            details={"candidate_id": source_hash},
            source_identity=source_hash,
            input_identity=source_hash,
        )
    )
    return LaneCandidate(record, source, tuple(entries))


def _verify_candidate_record_source(record: CandidateRecord, root: Path) -> None:
    """Verify a repository-backed candidate artifact before accepting it."""
    path_value = record.source_artifact.path
    resolved, _relative = _resolve_contained_path(path_value, root)
    if resolved is None:
        # Archive paths are owned by the coordinator.  A lane cannot inspect a
        # missing archive object here.  If an object with that name does exist
        # in the repository, however, a symlink escape is still an error.
        if path_value.startswith("artifacts/"):
            local_path = Path(root) / path_value
            if local_path.exists() or local_path.is_symlink():
                raise CandidateIdentityMismatch(
                    "supplied CandidateRecord source artifact is outside the repository"
                )
            return
        raise CandidateIdentityMismatch(
            "supplied CandidateRecord source artifact is outside the repository"
        )
    try:
        content = resolved.read_bytes()
    except OSError as exc:
        if path_value.startswith("artifacts/"):
            return
        raise CandidateIdentityMismatch(
            "supplied CandidateRecord source artifact is unavailable"
        ) from exc
    if hash_bytes(content) != record.candidate_id:
        raise CandidateIdentityMismatch(
            "supplied CandidateRecord source artifact disagrees with candidate_id"
        )


def _normalise_provenance_entry(
    value: Any,
    *,
    lane: str,
    recipient: Recipient,
    root: Path,
) -> Mapping[str, Any]:
    if isinstance(value, LaneEvidence):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise LaneError("producer provenance entries must be mappings")
    edge = dict(value)
    kind = edge.get("kind", "producer_evidence")
    source = edge.get("source") or edge.get("reference_id") or edge.get("source_path")
    if not isinstance(kind, str) or not kind:
        raise LaneError("producer provenance kind must be nonempty")
    if not isinstance(source, str) or not source:
        raise LaneError("producer provenance needs an explicit source")
    edge.pop("kind", None)
    edge.pop("source", None)
    source_identity = edge.pop("source_identity", edge.pop("identity", None))
    input_identity = edge.pop("input_identity", None)
    return _provenance(
        lane=lane,
        recipient=recipient,
        kind=kind,
        source=source,
        details=edge,
        root=root,
        source_identity=source_identity,
        input_identity=input_identity,
    )


def _candidate_from_value(
    value: Any,
    *,
    lane: str,
    recipient: Recipient,
    root: Path,
    inherited_provenance: Sequence[Mapping[str, Any]] = (),
) -> Optional[LaneCandidate]:
    if isinstance(value, LaneCandidate):
        _verify_candidate_record_source(value.candidate, root)
        if value.recipient_id != recipient.recipient_id:
            raise SubsetViolation("candidate recipient is outside selected recipient")
        if value.source and hash_bytes(value.source.encode("utf-8")) != value.candidate_id:
            raise CandidateIdentityMismatch(
                "supplied lane candidate source disagrees with its immutable identity"
            )
        return value
    if isinstance(value, CandidateRecord):
        _verify_candidate_record_source(value, root)
        source = ""
        if not value.source_artifact.path.startswith("artifacts/"):
            source, _ = _read_repo_text(value.source_artifact.path, root)
        if source and hash_bytes(source.encode("utf-8")) != value.candidate_id:
            raise CandidateIdentityMismatch(
                "supplied CandidateRecord source disagrees with candidate_id"
            )
        return LaneCandidate(value, source, tuple(inherited_provenance))
    if isinstance(value, str):
        return _source_candidate(
            lane=lane,
            recipient=recipient,
            source=value,
            provenance=inherited_provenance,
        )
    if not isinstance(value, Mapping):
        return None

    nested = value.get("candidate")
    source = value.get(
        "source",
        value.get("body", value.get("body_source", value.get("source_code", ""))),
    )
    source_path = value.get("source_path", value.get("path"))
    if source is not None and not isinstance(source, str):
        raise LaneError("candidate source must be text")
    if not source:
        source, discovered_path = _read_repo_text(source_path, root)
        function = value.get("function")
        if discovered_path and function:
            if not isinstance(function, str):
                raise LaneError("candidate function must be text")
            extracted = _extract_function(source, function)
            if extracted:
                source = extracted
    inherited = list(inherited_provenance)
    raw_provenance = value.get("provenance", ())
    if isinstance(raw_provenance, Mapping):
        raw_provenance = (raw_provenance,)
    if isinstance(raw_provenance, (list, tuple)):
        inherited.extend(
            _normalise_provenance_entry(
                item, lane=lane, recipient=recipient, root=root
            )
            for item in raw_provenance
        )

    if isinstance(nested, Mapping):
        try:
            nested = CandidateRecord.from_dict(nested)
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise CandidateIdentityMismatch("supplied candidate record is invalid") from exc

    if isinstance(nested, CandidateRecord):
        candidate = nested
        _verify_candidate_record_source(candidate, root)
        if candidate.recipient_id != recipient.recipient_id:
            raise SubsetViolation("candidate recipient is outside selected recipient")
        if source and candidate.candidate_id != hash_bytes(source.encode("utf-8")):
            raise CandidateIdentityMismatch(
                "supplied CandidateRecord source disagrees with candidate_id"
            )
        declared_id = value.get("candidate_id")
        if declared_id is not None and declared_id != candidate.candidate_id:
            raise CandidateIdentityMismatch(
                "candidate_id wrapper disagrees with supplied CandidateRecord"
            )
        return LaneCandidate(candidate, source, tuple(inherited))

    declared_id = value.get("candidate_id")
    declared_artifact = value.get("source_artifact")
    if declared_id is not None or declared_artifact is not None:
        if not isinstance(declared_id, str) or not isinstance(declared_artifact, Mapping):
            raise CandidateIdentityMismatch(
                "candidate identity fields must be supplied together"
            )
        try:
            declared_artifact = ArtifactRef.from_dict(declared_artifact)
            validate_hash(declared_id, "candidate_id")
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise CandidateIdentityMismatch("candidate identity fields are invalid") from exc
        if declared_id != declared_artifact.content_hash:
            raise CandidateIdentityMismatch(
                "candidate_id disagrees with source_artifact.content_hash"
            )
        if source and declared_id != hash_bytes(source.encode("utf-8")):
            raise CandidateIdentityMismatch(
                "source bytes disagree with supplied candidate identity"
            )
        raise CandidateIdentityMismatch(
            "a complete CandidateRecord is required for supplied immutable identity"
        )

    parent_ids = value.get("parent_candidate_ids", ())
    if isinstance(parent_ids, str):
        parent_ids = (parent_ids,)
    return _source_candidate(
        lane=lane,
        recipient=recipient,
        source=source,
        provenance=inherited,
        source_path=source_path if isinstance(source_path, str) else None,
        parent_candidate_ids=tuple(parent_ids or ()),
        mutation_id=value.get("mutation_id"),
    )


def _merge_candidates(candidates: Iterable[LaneCandidate]) -> Tuple[LaneCandidate, ...]:
    merged: dict[Tuple[str, str], LaneCandidate] = {}
    for candidate in candidates:
        key = (candidate.recipient_id, candidate.candidate_id)
        prior = merged.get(key)
        if prior is None:
            merged[key] = candidate
            continue
        provenance = list(prior.provenance)
        seen = {canonical_json(dict(item)) for item in provenance}
        for item in candidate.provenance:
            marker = canonical_json(dict(item))
            if marker not in seen:
                provenance.append(item)
                seen.add(marker)
        merged[key] = LaneCandidate(prior.candidate, prior.source or candidate.source, tuple(provenance))
    return tuple(
        merged[key] for key in sorted(merged, key=lambda item: (item[0], item[1]))
    )


def _discovery_from_values(
    raw: Any,
    *,
    lane: str,
    recipient: Recipient,
    root: Path,
) -> _Discovery:
    if isinstance(raw, _Discovery):
        return raw
    if isinstance(raw, LaneOutcome):
        return _Discovery(
            candidates=list(raw.candidates),
            provenance=list(raw.provenance),
            input_identities=list(raw.receipt.input_identities),
            attempts=raw.receipt.attempts,
            completion_reason=raw.receipt.completion_reason,
            reason=raw.reason,
            refusal_code=raw.refusal.code if raw.refusal else None,
        )
    metadata: Mapping[str, Any] = {}
    values: Any = raw
    if isinstance(raw, Mapping):
        metadata = raw
        values = raw.get(
            "candidates",
            raw.get("hits", raw.get("donors", raw.get("results", ()))),
        )
        if values is None:
            values = ()
    if isinstance(values, (str, bytes, CandidateRecord, LaneCandidate)):
        values = (values,)
    elif values is None:
        values = ()
    else:
        try:
            values = tuple(values)
        except TypeError as exc:
            raise LaneError("producer candidates must be a sequence") from exc
    raw_refusal = metadata.get("refusal_code", metadata.get("reason_code"))
    if raw_refusal is not None and not isinstance(raw_refusal, str):
        raise LaneError("producer refusal_code must be a string")
    raw_attempts = metadata.get("attempts", len(values))
    if isinstance(raw_attempts, bool) or not isinstance(raw_attempts, int) or raw_attempts < 0:
        raise LaneError("producer attempts must be a nonnegative integer")
    attempts = raw_attempts
    default_completion = (
        "inapplicable" if not values and not attempts else "search_space_exhausted"
    )
    completion = metadata.get("completion_reason", default_completion)
    if not isinstance(completion, str):
        raise LaneError("producer completion_reason must be a string")
    if completion not in _COMPLETION_REASONS:
        raise LaneError("producer completion_reason is not recognized")
    if completion == "inapplicable" and not raw_refusal:
        raw_refusal = "inapplicable"
    reason = metadata.get("reason", "")
    if not isinstance(reason, str):
        raise LaneError("producer reason must be a string")
    result = _Discovery(
        attempts=attempts,
        reason=reason,
        completion_reason=completion,
        refusal_code=raw_refusal,
    )
    raw_rejections = metadata.get("rejection_counts", {})
    if isinstance(raw_rejections, Mapping):
        for key, value in raw_rejections.items():
            if (
                not isinstance(key, str)
                or isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise LaneError("producer rejection counts must be nonnegative integers")
            result.rejection_counts[key] += value
    elif raw_rejections is not None:
        raise LaneError("producer rejection_counts must be a mapping")
    raw_inputs = metadata.get("input_identities", ())
    if raw_inputs is None:
        raw_inputs = ()
    if isinstance(raw_inputs, str):
        raw_inputs = (raw_inputs,)
    elif isinstance(raw_inputs, bytes):
        raw_inputs = (raw_inputs,)
    else:
        try:
            raw_inputs = tuple(raw_inputs)
        except TypeError as exc:
            raise LaneError("producer input_identities must be a sequence") from exc
    for item in raw_inputs:
        result.input_identities.append(_identity(item, root=root, label="producer input"))
    raw_provenance = metadata.get("provenance", ())
    if raw_provenance is None:
        raw_provenance = ()
    if isinstance(raw_provenance, Mapping):
        raw_provenance = (raw_provenance,)
    elif not isinstance(raw_provenance, (list, tuple)):
        raise LaneError("producer provenance must be a sequence")
    for item in raw_provenance:
        result.provenance.append(
            _normalise_provenance_entry(
                item, lane=lane, recipient=recipient, root=root
            )
        )
    for item in values:
        candidate = _candidate_from_value(
            item,
            lane=lane,
            recipient=recipient,
            root=root,
            inherited_provenance=result.provenance,
        )
        if candidate is None:
            result.rejection_counts["candidate_unavailable"] += 1
            continue
        result.candidates.append(candidate)
        result.provenance.extend(candidate.provenance)
        result.input_identities.append(candidate.candidate_id)
    if not result.attempts:
        result.attempts = len(values)
    return result


def _load_module(name: str) -> Any:
    """Load a legacy producer without executing a mutating entry point."""
    automation = str(REPO / "automation")
    if automation not in sys.path:
        sys.path.insert(0, automation)
    try:
        return importlib.import_module(name)
    except ImportError:
        return importlib.import_module("automation." + name)


def _resolve_immutable_ref(
    value: Any,
    *,
    options: Mapping[str, Any],
    recipient: Recipient,
    lane: str,
) -> Tuple[str, str]:
    """Resolve a displayed upstream ref to a content-addressed identity."""
    displayed: Any = value
    identity: Any = None
    if isinstance(value, Mapping):
        displayed = value.get("ref", value.get("name"))
        identity = value.get(
            "commit_identity",
            value.get("resolved_identity", value.get("reference_identity", value.get("identity"))),
        )
        if identity is None:
            identity = value.get("commit")
    if not isinstance(displayed, str) or not displayed:
        raise ImmutableReferenceError("upstream reference must name a ref")

    if identity is None:
        # A plain sha256 value is already an immutable displayed ref.  A branch
        # or tag name is accepted only when a resolver records its commit hash.
        try:
            identity = validate_hash(displayed, "upstream reference identity")
        except SearchValidationError:
            resolved_maps = (
                options.get("resolved_ref_identities"),
                options.get("upstream_ref_identities"),
                options.get("ref_identities"),
            )
            for values in resolved_maps:
                if isinstance(values, Mapping) and displayed in values:
                    identity = values[displayed]
                    break
        if identity is None:
            resolver = options.get("upstream_ref_resolver")
            if callable(resolver):
                resolved = _call_fetcher(resolver, displayed, recipient)
                if isinstance(resolved, Mapping):
                    resolved_displayed = resolved.get("ref", resolved.get("name", displayed))
                    if resolved_displayed != displayed:
                        raise ImmutableReferenceError(
                            "upstream resolver changed the requested ref"
                        )
                    identity = resolved.get(
                        "commit_identity",
                        resolved.get(
                            "resolved_identity",
                            resolved.get("reference_identity", resolved.get("identity")),
                        ),
                    )
                else:
                    identity = resolved
    try:
        immutable = validate_hash(identity, "upstream reference identity")
    except SearchValidationError as exc:
        raise ImmutableReferenceError(
            f"{lane} reference {displayed!r} did not resolve to an immutable hash"
        ) from exc
    return displayed, immutable


def _upstream_discovery(
    recipient: Recipient,
    *,
    pinned: bool,
    options: Mapping[str, Any],
    root: Path,
) -> _Discovery:
    lane = "upstream_pinned" if pinned else "upstream_current"
    result = _Discovery(attempts=1)
    try:
        upstream = _load_module("upstream_harvest")
    except (ImportError, OSError) as exc:
        result.refusal_code = "producer_unavailable"
        result.reason = "upstream_harvest unavailable: " + str(exc)
        result.completion_reason = "inapplicable"
        result.rejection_counts["producer_unavailable"] += 1
        return result

    base = _base_function(recipient.function)
    path_map = options.get("upstream_paths", {})
    path = ""
    if isinstance(path_map, Mapping):
        selected = path_map.get(recipient.recipient_id, path_map.get(base, ""))
        if isinstance(selected, Mapping):
            selected = selected.get("path", "")
        if selected is not None and not isinstance(selected, str):
            result.refusal_code = "invalid_upstream_path"
            result.reason = "upstream definition path must be a string"
            result.completion_reason = "inapplicable"
            result.rejection_counts["invalid_upstream_path"] += 1
            return result
        path = selected or ""
    if not path:
        try:
            # Do not call harvest(), which enumerates every queue status.
            discovered_path = upstream.upstream_files(recipient.overlay).get(base, "")
            if discovered_path is not None and not isinstance(discovered_path, str):
                result.refusal_code = "invalid_upstream_path"
                result.reason = "upstream definition path must be a string"
                result.completion_reason = "inapplicable"
                result.rejection_counts["invalid_upstream_path"] += 1
                return result
            path = discovered_path or ""
        except (AttributeError, OSError, RuntimeError):
            path = ""
    if not path:
        result.refusal_code = "no_definition"
        result.reason = "no exact-overlay upstream definition"
        result.completion_reason = "inapplicable"
        result.rejection_counts["no_definition"] += 1
        return result
    if _relative_path(path) is None:
        result.refusal_code = "invalid_upstream_path"
        result.reason = "upstream definition path must be relative"
        result.completion_reason = "inapplicable"
        result.rejection_counts["invalid_upstream_path"] += 1
        return result

    raw_ref: Any = None
    if pinned:
        refs = options.get("pinned_refs", {})
        if isinstance(refs, Mapping):
            raw_ref = refs.get(recipient.recipient_id, refs.get(recipient.overlay))
        if raw_ref is None:
            raw_ref = recipient.metadata.get("pinned_ref")
        if raw_ref is None:
            raw_ref = recipient.metadata.get("open_pr_ref")
        if raw_ref is None:
            result.refusal_code = "missing_pinned_ref"
            result.reason = "pinned lane requires an explicit immutable ref"
            result.completion_reason = "inapplicable"
            result.rejection_counts["missing_pinned_ref"] += 1
            return result
    else:
        raw_ref = options.get("current_ref") or recipient.metadata.get("current_ref")
        producer_ref: Any = None
        if raw_ref is None:
            try:
                producer_ref = getattr(upstream, "upstream_commit", lambda: "")()
            except (AttributeError, OSError, RuntimeError):
                producer_ref = None
            raw_ref = producer_ref
        if raw_ref is None or raw_ref == "":
            result.refusal_code = "missing_immutable_ref"
            result.reason = "current upstream requires an explicit immutable ref"
            result.completion_reason = "inapplicable"
            result.rejection_counts["missing_immutable_ref"] += 1
            return result
    try:
        ref, ref_identity = _resolve_immutable_ref(
            raw_ref, options=options, recipient=recipient, lane=lane
        )
    except ImmutableReferenceError as exc:
        result.refusal_code = "unresolved_immutable_ref"
        result.reason = str(exc)
        result.completion_reason = "inapplicable"
        result.rejection_counts["unresolved_immutable_ref"] += 1
        return result

    fetcher = options.get("upstream_fetch")
    raw_source: Any = None
    reference = f"{ref}:{path}"
    if callable(fetcher):
        raw_source = _call_fetcher(fetcher, ref, path, recipient)
    elif isinstance(recipient.metadata.get("upstream_source"), str):
        raw_source = recipient.metadata["upstream_source"]
    else:
        git_reader = getattr(upstream, "_git", None)
        if callable(git_reader):
            try:
                raw_source = git_reader("show", reference)
            except (AttributeError, KeyError, OSError, RuntimeError):
                raw_source = ""
    if isinstance(raw_source, bytes):
        source_text = raw_source.decode("utf-8", "replace")
    elif isinstance(raw_source, str):
        source_text = raw_source
    else:
        source_text = ""
    body = _extract_function(source_text, base)
    if not body:
        result.refusal_code = "body_unavailable"
        result.reason = "upstream path exists but body could not be read"
        result.completion_reason = "inapplicable"
        result.rejection_counts["body_unavailable"] += 1
        return result
    if recipient.function != base:
        body = re.sub(r"\b" + re.escape(base) + r"\b", recipient.function, body)
    evidence = _provenance(
        lane=lane,
        recipient=recipient,
        kind="upstream_definition",
        source=reference,
        details={
            "reference_id": reference,
            "reference_identity": ref_identity,
            "reference_ref": ref,
            "reference_path": path,
            "function": base,
            "target_function": recipient.function,
            "pinned": pinned,
        },
        source_identity=hash_bytes(source_text.encode("utf-8")),
        input_identity=ref_identity,
    )
    result.candidates.append(
        _source_candidate(
            lane=lane,
            recipient=recipient,
            source=body,
            provenance=(evidence,),
        )
    )
    result.provenance.append(evidence)
    result.input_identities.extend(
        (ref_identity, hash_bytes(source_text.encode("utf-8")), result.candidates[-1].candidate_id)
    )
    result.completion_reason = "matched_pending_oracle"
    result.reason = "one exact upstream definition discovered"
    return result


def _preserved_discovery(
    recipient: Recipient,
    *,
    options: Mapping[str, Any],
    root: Path,
) -> _Discovery:
    result = _Discovery()
    custom = options.get("preserved_paths", {})
    paths: list[str] = []
    if isinstance(custom, Mapping):
        chosen = custom.get(recipient.recipient_id, ())
        if isinstance(chosen, str):
            chosen = (chosen,)
        paths.extend(str(item) for item in chosen)
    elif isinstance(custom, (list, tuple)):
        paths.extend(str(item) for item in custom)

    if not paths:
        candidate_root = root / "automation" / "candidates"
        try:
            paths = [
                str(path.relative_to(root)).replace("\\", "/")
                for path in sorted(candidate_root.rglob("*.c"))
                if path.is_file()
            ]
        except OSError:
            paths = []

    base = _base_function(recipient.function)
    for path in paths:
        text, relative = _read_repo_text(path, root)
        if not text:
            result.rejection_counts["artifact_unavailable"] += 1
            continue
        marker = (
            recipient.recipient_id in text
            or ("record :" + recipient.recipient_id) in text
            or recipient.function in Path(relative).name
            or base in Path(relative).name
        )
        if not marker:
            continue
        evidence = _provenance(
            lane="preserved_candidate",
            recipient=recipient,
            kind="preserved_candidate",
            source=relative,
            details={"artifact_path": relative, "function": recipient.function},
            root=root,
        )
        candidate = _candidate_from_value(
            {"source": text, "source_path": relative, "provenance": (evidence,)},
            lane="preserved_candidate",
            recipient=recipient,
            root=root,
        )
        if candidate is not None:
            result.candidates.append(candidate)
            result.provenance.append(evidence)
            file_identity = _file_identity(relative, root)
            if file_identity:
                result.input_identities.append(file_identity)
            result.input_identities.append(candidate.candidate_id)
            result.attempts += 1
    if result.candidates:
        result.completion_reason = "matched_pending_oracle"
        result.reason = "preserved candidate evidence discovered"
    else:
        result.completion_reason = "inapplicable"
        result.refusal_code = "no_preserved_candidate"
        result.reason = "no preserved candidate names this recipient"
        result.rejection_counts["no_preserved_candidate"] += 1
    return result


def _shared_header_discovery(
    recipient: Recipient,
    *,
    options: Mapping[str, Any],
    root: Path,
) -> _Discovery:
    result = _Discovery()
    callback_data = options.get("shared_header_evidence")
    if isinstance(callback_data, Mapping):
        callback_data = callback_data.get(recipient.recipient_id)
    if callback_data is not None:
        return _discovery_from_values(
            callback_data,
            lane="shared_header",
            recipient=recipient,
            root=root,
        )

    try:
        sweep = _load_module("shim_sweep")
        headers = sweep.shared_headers()
        files = sweep.stage_files()
        peers, state = sweep.build_peer_map(headers, files)
    except (ImportError, OSError, RuntimeError) as exc:
        result.refusal_code = "producer_unavailable"
        result.reason = "shim_sweep unavailable: " + str(exc)
        result.completion_reason = "inapplicable"
        result.rejection_counts["producer_unavailable"] += 1
        return result

    target_path = str(
        recipient.metadata.get("source_path")
        or recipient.metadata.get("target_path")
        or recipient.metadata.get("target_file")
        or ""
    ).replace("\\", "/")
    target_files = []
    for path, row in sorted(state.items(), key=lambda item: str(item[0])):
        resolved_path, relative = _resolve_contained_path(path, root)
        if resolved_path is None or relative is None:
            result.rejection_counts["target_path_outside_root"] += 1
            continue
        if target_path and relative != target_path:
            continue
        stage = str(row.get("stage", "")).lower()
        if recipient.overlay and recipient.overlay.rsplit("/", 1)[-1].lower() != stage:
            continue
        if recipient.function not in set(row.get("stub_fns", ())):
            continue
        target_files.append((resolved_path, row))
    if not target_files and target_path:
        result.rejection_counts["target_file_not_found"] += 1

    for path, row in target_files:
        for header_name in sorted(peers.get(path.stem, {})):
            peer_stages = tuple(sorted(peers[path.stem][header_name]))
            header = headers.get(header_name)
            if header is None:
                continue
            header_path, relative = _resolve_contained_path(header, root)
            if header_path is None or relative is None:
                result.rejection_counts["header_outside_root"] += 1
                continue
            text = sweep.read(header_path)
            if isinstance(text, bytes):
                text = text.decode("utf-8", "replace")
            if not isinstance(text, str) or not text:
                result.rejection_counts["header_unavailable"] += 1
                continue
            header_identity = _file_identity(header_path, root)
            if not header_identity:
                header_identity = hash_bytes(text.encode("utf-8"))
            risks = tuple(sweep.header_risks_text(text))
            evidence = _provenance(
                lane="shared_header",
                recipient=recipient,
                kind="shared_header_viability",
                source=relative,
                details={
                    "header": relative,
                    "peer_stages": peer_stages,
                    "risks": risks,
                    "target_file": str(path.relative_to(root)).replace("\\", "/"),
                    "header_content_hash": header_identity,
                },
                source_identity=header_identity,
                input_identity=header_identity,
            )
            result.provenance.append(evidence)
            result.input_identities.append(header_identity)
            result.attempts += 1
            if risks:
                result.rejection_counts["header_risk"] += 1
                continue
            # Viability is provenance.  The candidate itself is only the exact
            # target definition, so unrelated header declarations cannot leak
            # into the candidate artifact identity.
            body = _extract_function(text, recipient.function)
            if body:
                result.candidates.append(
                    _source_candidate(
                        lane="shared_header",
                        recipient=recipient,
                        source=body,
                        provenance=(evidence,),
                    )
                )
                result.input_identities.append(hash_bytes(body.encode("utf-8")))
    if result.candidates:
        result.completion_reason = "matched_pending_oracle"
        result.reason = "shared header is viable for the selected stub"
    else:
        result.completion_reason = "inapplicable"
        result.refusal_code = "shared_header_inapplicable"
        result.reason = (
            "no risk-free shared header with a target definition and peer evidence"
        )
        result.rejection_counts["shared_header_inapplicable"] += 1
    return result


def _twin_rows(recipient: Recipient) -> list[dict[str, Any]]:
    try:
        finder = _load_module("asm_twin_finder")
        rows = finder.analyse(_base_function(recipient.function))
    except (ImportError, OSError, RuntimeError):
        return []
    return [
        dict(row) for row in rows
        if str(row.get("symbol", "")) in {recipient.function, _base_function(recipient.function)}
    ]


def _twin_discovery(
    recipient: Recipient,
    *,
    options: Mapping[str, Any],
    root: Path,
    transplant_only: bool = False,
) -> _Discovery:
    # Both twin discovery modes currently feed the single transplant lane.
    # Keep the keyword for callers that select the mode, but do not pretend
    # it changes the lane identity.
    lane = "transplant"
    result = _Discovery()
    rows = _twin_rows(recipient)
    symbols: list[tuple[int, str, str, Mapping[str, Any]]] = []
    rank = {"name": 0, "shape": 1, "token": 2}
    for row in rows:
        for item in row.get("name_twins", ()) or ():
            symbols.append((rank["name"], str(item.get("function", "")), "name", item))
        for item in row.get("shape_twins", ()) or ():
            symbols.append((
                0 if item.get("identical_constants") else rank["shape"],
                str(item.get("symbol", "")),
                "shape",
                item,
            ))
        for item in row.get("token_twins", ()) or ():
            symbols.append((rank["token"], str(item.get("function", "")), "token", item))
    try:
        transplant = _load_module("transplant")
        extra = transplant.twin_sources(recipient.function)
    except (ImportError, OSError, RuntimeError):
        extra = []
    for symbol in extra:
        symbols.append((0, str(symbol), "local-index", {"function": str(symbol)}))
    unique: dict[Tuple[int, str, str], Mapping[str, Any]] = {}
    for score, symbol, kind, item in symbols:
        if not symbol or symbol == recipient.function:
            continue
        unique.setdefault((score, symbol, kind), item)
    ordered = sorted(unique.items(), key=lambda item: item[0])
    target_path = str(
        recipient.metadata.get("source_path")
        or recipient.metadata.get("target_path")
        or ""
    )
    for (_score, symbol, kind), item in ordered:
        body = ""
        path = ""
        try:
            body, path = transplant.local_twin(symbol, exclude=target_path)
        except (AttributeError, OSError, RuntimeError):
            body, path = "", ""
        if not body:
            row_path = item.get("file")
            if isinstance(row_path, str):
                full, relative = _read_repo_text(row_path, root)
                body = _extract_function(full, symbol)
                path = relative
        body_identity = hash_bytes(body.encode("utf-8")) if body else ""
        donor_file_identity = _file_identity(path, root) if path else ""
        declared_identity = item.get("source_identity")
        if declared_identity is not None:
            try:
                declared_identity = _identity(
                    declared_identity, label="twin source identity"
                )
            except LaneError:
                result.rejection_counts["donor_identity_unavailable"] += 1
                result.attempts += 1
                continue
            computed_identity = donor_file_identity or body_identity
            if computed_identity and declared_identity != computed_identity:
                result.rejection_counts["donor_identity_mismatch"] += 1
                result.attempts += 1
                continue
            if not computed_identity:
                donor_file_identity = declared_identity
        if not body and not donor_file_identity:
            result.rejection_counts["donor_identity_unavailable"] += 1
            result.attempts += 1
            continue
        evidence = _provenance(
            lane=lane,
            recipient=recipient,
            kind="asm_twin" if kind != "local-index" else "transplant_twin",
            source=path or symbol,
            details={
                "donor_symbol": symbol,
                "match_kind": kind,
                "rank": _score,
                "asm_row": rows[0] if rows else {},
                "donor_path": path,
            },
            source_identity=donor_file_identity or body_identity,
            input_identity=donor_file_identity or body_identity,
        )
        result.provenance.append(evidence)
        result.input_identities.append(donor_file_identity or body_identity)
        result.attempts += 1
        if not body:
            result.rejection_counts["donor_body_unavailable"] += 1
            continue
        if recipient.function != symbol:
            body = re.sub(r"\b" + re.escape(symbol) + r"\b", recipient.function, body)
        candidate = _source_candidate(
            lane=lane,
            recipient=recipient,
            source=body,
            provenance=(evidence,),
        )
        if candidate is not None:
            result.candidates.append(candidate)
            result.input_identities.append(candidate.candidate_id)
    if result.candidates:
        result.completion_reason = "matched_pending_oracle"
        result.reason = "local twin and transplant evidence discovered"
    else:
        result.completion_reason = "inapplicable"
        result.refusal_code = "no_usable_twin"
        result.reason = "no locally defined twin body survived read-only analysis"
        result.rejection_counts["no_usable_twin"] += 1
    return result


def _whole_tu_discovery(
    recipient: Recipient,
    *,
    options: Mapping[str, Any],
    root: Path,
) -> _Discovery:
    lane = "whole_tu"
    result = _Discovery()
    data = options.get("whole_tu_sources", {})
    chosen: list[str] = []
    if isinstance(data, Mapping):
        raw = data.get(recipient.recipient_id, ())
        if isinstance(raw, str):
            raw = (raw,)
        chosen.extend(str(item) for item in raw)
    if not chosen:
        chosen.extend(
            str(item)
            for item in (
                recipient.metadata.get("whole_tu_source", ""),
                recipient.metadata.get("source_path", ""),
            )
            if item
        )
    for path in sorted(set(chosen)):
        text, relative = _read_repo_text(path, root)
        result.attempts += 1
        if not text:
            result.rejection_counts["translation_unit_unavailable"] += 1
            continue
        evidence = _provenance(
            lane=lane,
            recipient=recipient,
            kind="whole_translation_unit",
            source=relative,
            details={"translation_unit": relative},
            root=root,
        )
        result.provenance.append(evidence)
        file_identity = _file_identity(relative, root)
        if file_identity:
            result.input_identities.append(file_identity)
        if _extract_function(text, recipient.function):
            candidate = _source_candidate(
                lane=lane,
                recipient=recipient,
                source=text,
                source_path=relative,
                provenance=(evidence,),
            )
            if candidate is not None:
                result.candidates.append(candidate)
                result.input_identities.append(candidate.candidate_id)
        else:
            result.rejection_counts["function_not_in_translation_unit"] += 1
    if result.candidates:
        result.completion_reason = "matched_pending_oracle"
        result.reason = "whole translation-unit evidence contains the recipient"
    else:
        result.completion_reason = "inapplicable"
        result.refusal_code = "whole_tu_inapplicable"
        result.reason = "no selected translation unit contains the recipient"
        result.rejection_counts["whole_tu_inapplicable"] += 1
    return result


def _dependency_discovery(
    recipient: Recipient,
    *,
    options: Mapping[str, Any],
    root: Path,
) -> _Discovery:
    lane = "dependency_closure"
    result = _Discovery()
    closure = options.get("dependency_closures", {})
    if isinstance(closure, Mapping):
        closure = closure.get(recipient.recipient_id, ())
    if isinstance(closure, Mapping):
        closure = (closure,)
    if isinstance(closure, str):
        closure = (closure,)
    closure_items = tuple(closure or ())
    result.attempts = len(closure_items)
    if not closure_items:
        result.refusal_code = "no_dependency_evidence"
        result.completion_reason = "inapplicable"
        result.rejection_counts["no_dependency_evidence"] += 1
        result.reason = "dependency closure has no evidence for this recipient"
        return result
    for item in closure_items:
        if isinstance(item, Mapping):
            path = item.get("source_path", item.get("path", ""))
            text = item.get("source", item.get("body", ""))
            if not text:
                text, relative = _read_repo_text(path, root)
            else:
                relative = _relative_path(path) or ""
            if isinstance(text, bytes):
                text = text.decode("utf-8", "replace")
            source_identity = (
                hash_bytes(text.encode("utf-8"))
                if isinstance(text, str) and text
                else _file_identity(path, root)
            )
            raw_identity = item.get("source_identity")
            if raw_identity is not None:
                try:
                    declared_identity = _identity(
                        raw_identity, label="dependency source identity"
                    )
                except LaneError:
                    result.rejection_counts["dependency_identity_unavailable"] += 1
                    continue
                if source_identity and declared_identity != source_identity:
                    result.rejection_counts["dependency_identity_mismatch"] += 1
                    continue
                source_identity = declared_identity
            if not source_identity:
                result.rejection_counts["dependency_identity_unavailable"] += 1
                continue
            evidence = _provenance(
                lane=lane,
                recipient=recipient,
                kind="dependency_closure",
                source=relative or str(path),
                details={"dependencies": dict(item)},
                source_identity=source_identity,
                input_identity=source_identity,
            )
            result.provenance.append(evidence)
            result.input_identities.append(source_identity)
            if isinstance(text, str) and text:
                candidate = _source_candidate(
                    lane=lane,
                    recipient=recipient,
                    source=text,
                    source_path=relative or None,
                    provenance=(evidence,),
                )
                if candidate is not None:
                    result.candidates.append(candidate)
                    result.input_identities.append(candidate.candidate_id)
            else:
                result.rejection_counts["dependency_body_unavailable"] += 1
        else:
            try:
                source_identity = _identity(item, root=root, label="dependency input")
            except LaneError:
                result.rejection_counts["dependency_identity_unavailable"] += 1
                continue
            result.provenance.append(
                _provenance(
                    lane=lane,
                    recipient=recipient,
                    kind="dependency_closure",
                    source=str(item),
                    details={"dependency": str(item)},
                    source_identity=source_identity,
                    input_identity=source_identity,
                )
            )
            result.input_identities.append(source_identity)
    if result.candidates:
        result.completion_reason = "matched_pending_oracle"
        result.reason = "dependency closure supplied a candidate source"
    else:
        result.completion_reason = "search_space_exhausted"
        result.reason = "dependency evidence recorded without a complete source candidate"
    return result


_REGISTER = re.compile(
    r"(?<![A-Za-z0-9_])(?:\$[0-9]{1,2}|\$(?:zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra)|r(?:[0-9]{1,2}|zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra))(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
_BRANCH = re.compile(
    r"(?<![A-Za-z0-9_])(?:b(?:eq|ne|gez|gtz|lez|ltz|c1f|c1t)|j(?:alr?|r)?|bal)\b"
    r"(?:\s+[^\n;]*)?(?:\b(?:0x[0-9A-Fa-f]+|[0-9]+)\b|\$[A-Za-z0-9]+)?",
    re.IGNORECASE,
)



def reject_unsafe_semantic_constant(value: Any, *, label: str = "constant") -> None:
    """Reject raw register names and branch displacement evidence.

    Numeric literals remain valid semantic constants when their evidence is
    explicitly a source-level value.  Register-shaped strings and branch
    operands are never promoted to that status.
    """

    label_text = str(label).lower()
    text = str(value)
    register_context = any(
        token in label_text
        for token in (
            "register",
            "reg",
            "operand_register",
            "raw_reg",
            "register_index",
            "register_number",
            "rs",
            "rt",
            "rd",
            "shamt",
        )
    )
    branch_context = any(
        token in label_text
        for token in (
            "branch",
            "displacement",
            "branch_offset",
            "branch_target",
            "jump_offset",
            "target_offset",
            "pc_offset",
        )
    )
    if register_context and _REGISTER.search(text):
        raise UnsafeSemanticConstant(
            f"{label} is a raw register or register-bound value: {value!r}"
        )
    if branch_context and (_BRANCH.search(text) or re.fullmatch(r"-?(?:0x[0-9a-f]+|[0-9]+)", text, re.I)):
        raise UnsafeSemanticConstant(
            f"{label} is a branch displacement, not a semantic constant: {value!r}"
        )
    if _REGISTER.search(text):
        raise UnsafeSemanticConstant(
            f"{label} contains a raw register: {value!r}"
        )
    if _BRANCH.search(text):
        raise UnsafeSemanticConstant(
            f"{label} contains a branch displacement: {value!r}"
        )


def semantic_constant_allowed(value: Any, *, label: str = "constant") -> bool:
    try:
        reject_unsafe_semantic_constant(value, label=label)
    except UnsafeSemanticConstant:
        return False
    return True


is_safe_semantic_constant = semantic_constant_allowed
validate_semantic_constant = reject_unsafe_semantic_constant


def _coerce_donor(value: Any, recipient: Recipient) -> Optional[DonorEvidence]:
    if isinstance(value, DonorEvidence):
        return value
    if not isinstance(value, Mapping):
        return None
    donor_id = value.get("donor_id", value.get("id"))
    if not isinstance(donor_id, str) or not donor_id:
        return None
    recipient_id = value.get("recipient_id", recipient.recipient_id)
    if not isinstance(recipient_id, str) or not recipient_id:
        return None
    match_kind = value.get("match_kind", value.get("kind", "signature"))
    if not isinstance(match_kind, str) or not match_kind:
        return None
    signature = value.get("signature", value.get("instruction_signature", donor_id))
    if not isinstance(signature, str) or not signature:
        return None
    declarations = value.get("declarations", {})
    constants = value.get("constants", {})
    if not isinstance(declarations, Mapping):
        return None
    if not isinstance(constants, Mapping):
        return None
    differences = value.get("structural_differences", value.get("differences", ()))
    if isinstance(differences, str):
        differences = (differences,)
    if not isinstance(differences, (list, tuple)):
        return None
    if any(not isinstance(item, str) for item in differences):
        return None
    version = value.get("version", "us")
    if not isinstance(version, str) or not version:
        return None
    body = value.get("body", value.get("source_code"))
    if body is not None and not isinstance(body, str):
        return None
    compatible = value.get("compatible", True)
    if not isinstance(compatible, bool):
        return None
    declared_source_identity = value.get("source_identity")
    if declared_source_identity is not None:
        try:
            declared_source_identity = validate_hash(
                declared_source_identity, "donor source identity"
            )
        except SearchValidationError:
            return None
        if body is not None and declared_source_identity != hash_bytes(body.encode("utf-8")):
            return None
    return DonorEvidence(
        donor_id=donor_id,
        recipient_id=recipient_id,
        version=version,
        source=value.get("source", value.get("source_path", "")),
        match_kind=match_kind,
        signature=signature,
        body=body,
        symbol=value.get("symbol", value.get("function")),
        instruction_signature=value.get("instruction_signature"),
        cfg_signature=value.get("cfg_signature"),
        dataflow_signature=value.get("dataflow_signature"),
        declarations=declarations,
        constants=constants,
        structural_differences=tuple(differences),
        compatible=compatible,
        metadata={
            str(k): v for k, v in value.items()
            if k not in {
                "donor_id", "id", "recipient_id", "version", "source",
                "source_path", "match_kind", "kind", "signature", "body",
                "source_code", "symbol", "function", "instruction_signature",
                "cfg_signature", "dataflow_signature", "declarations", "constants",
                "structural_differences", "differences", "compatible",
            }
        },
    )


def _donor_rank(donor: DonorEvidence, recipient: Recipient) -> Tuple[int, str, str, str, str]:
    kind = donor.match_kind.lower().replace("-", "_")
    symbol = (donor.symbol or "").lower()
    function = recipient.function.lower()
    if symbol and symbol == function:
        rank = 0
    elif kind in {"symbol", "exact_symbol", "name", "exact_name"}:
        rank = 0
    elif "instruction" in kind or kind in {"opcode", "shape"}:
        rank = 1
    elif "cfg" in kind or "control" in kind:
        rank = 2
    elif "dataflow" in kind or "data_flow" in kind:
        rank = 3
    else:
        rank = 4
    source = donor.source_path.replace("\\", "/")
    return (rank, kind, donor.signature, donor.donor_id, source)


def gather_donors(
    recipient: Recipient | Mapping[str, Any] | str,
    donors: Iterable[Any],
) -> Tuple[DonorEvidence, ...]:
    """Filter and stably order semantic donors for one selected recipient."""
    target = _coerce_recipient(recipient)
    selected: list[DonorEvidence] = []
    seen: set[Tuple[str, str, str]] = set()
    for item in donors:
        donor = _coerce_donor(item, target)
        if donor is None:
            continue
        if donor.recipient_id not in {target.recipient_id, "*", ""}:
            continue
        try:
            _require_compatible_donor(donor)
        except IncompatibleDonor:
            continue
        key = (donor.donor_id, donor.version, donor.source_path)
        if key in seen:
            continue
        seen.add(key)
        selected.append(donor)
    selected.sort(key=lambda donor: _donor_rank(donor, target))
    return tuple(selected)


collect_donors = gather_donors
select_donors = gather_donors


def _require_compatible_donor(donor: DonorEvidence) -> None:
    if not donor.compatible:
        raise IncompatibleDonor(
            f"donor {donor.donor_id} is incompatible with recipient {donor.recipient_id}"
        )


def _donor_provenance(
    *,
    lane: str,
    recipient: Recipient,
    kind: str,
    donor: DonorEvidence,
    details: Mapping[str, Any],
) -> Optional[Mapping[str, Any]]:
    identity = donor.source_identity
    if not identity:
        return None
    return _provenance(
        lane=lane,
        recipient=recipient,
        kind=kind,
        source=donor.source_path or donor.donor_id,
        details=details,
        source_identity=identity,
        input_identity=identity,
    )


def _value_key(value: Any) -> str:
    try:
        return canonical_json(value)
    except (TypeError, ValueError):
        return repr(value)


def _iter_observations(value: Any) -> Iterable[Tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key), item
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            if isinstance(item, Mapping):
                name = item.get("name", item.get("symbol", item.get("key", "")))
                if name:
                    yield str(name), item.get("value", item.get("declaration", item))
            else:
                yield str(item), item
    elif value:
        yield "value", value


def triangulate_donors(
    recipient: Recipient | Mapping[str, Any] | str,
    donors: Iterable[Any],
    *,
    lane: str = "multi_donor",
) -> StructuralTriangulation:
    """Reconcile declaration and constant observations without guessing."""
    validate_lane(lane)
    target = _coerce_recipient(recipient)
    raw_donors = tuple(donors)
    selected = gather_donors(target, raw_donors)
    refusals: list[LaneRefusal] = []
    seen_incompatible: set[Tuple[str, str, str]] = set()
    for item in raw_donors:
        donor = _coerce_donor(item, target)
        if donor is None:
            continue
        if donor.recipient_id not in {target.recipient_id, "*", ""}:
            continue
        try:
            _require_compatible_donor(donor)
        except IncompatibleDonor as exc:
            key = (donor.donor_id, donor.version, donor.source_path)
            if key in seen_incompatible:
                continue
            seen_incompatible.add(key)
            evidence = _donor_provenance(
                lane=lane,
                recipient=target,
                kind="incompatible_donor",
                donor=donor,
                details={"donor": donor.to_dict()},
            )
            refusals.append(
                LaneRefusal(
                    target.recipient_id,
                    lane,
                    "incompatible_donor",
                    str(exc),
                    (evidence,) if evidence is not None else (),
                )
            )
            continue
    declarations: dict[str, Any] = {}
    constants: dict[str, Any] = {}
    differences: list[str] = []
    declaration_seen: dict[str, set[str]] = {}
    constant_seen: dict[str, set[str]] = {}
    declaration_values: dict[str, Any] = {}
    constant_values: dict[str, Any] = {}

    for donor in selected:
        for name, value in _iter_observations(donor.declarations):
            key = str(name)
            marker = _value_key(value)
            declaration_seen.setdefault(key, set()).add(marker)
            declaration_values.setdefault(key, value)
        for name, value in _iter_observations(donor.constants):
            key = str(name)
            try:
                reject_unsafe_semantic_constant(value, label=key)
            except UnsafeSemanticConstant as exc:
                evidence = _donor_provenance(
                    lane=lane,
                    recipient=target,
                    kind="unsafe_constant",
                    donor=donor,
                    details={
                        "donor_id": donor.donor_id,
                        "constant": key,
                        "value": value,
                    },
                )
                refusals.append(
                    LaneRefusal(
                        target.recipient_id,
                        lane,
                        "unsafe_semantic_constant",
                        str(exc),
                        (evidence,) if evidence is not None else (),
                    )
                )
                continue
            marker = _value_key(value)
            constant_seen.setdefault(key, set()).add(marker)
            constant_values.setdefault(key, value)
        differences.extend(str(item) for item in donor.structural_differences)

    for key, markers in declaration_seen.items():
        if len(markers) != 1:
            evidence = tuple(
                edge
                for donor in selected
                for edge in (
                    _donor_provenance(
                        lane=lane,
                        recipient=target,
                        kind="conflicting_declaration",
                        donor=donor,
                        details={
                            "donor_id": donor.donor_id,
                            "declaration": key,
                            "value": donor.declarations.get(key),
                        },
                    ),
                )
                if edge is not None
            )
            refusals.append(
                LaneRefusal(
                    target.recipient_id,
                    lane,
                    "conflicting_declaration",
                    "donors disagree about declaration " + key,
                    evidence,
                )
            )
        else:
            declarations[key] = declaration_values[key]
    for key, markers in constant_seen.items():
        if len(markers) != 1:
            evidence = tuple(
                edge
                for donor in selected
                for edge in (
                    _donor_provenance(
                        lane=lane,
                        recipient=target,
                        kind="conflicting_constant",
                        donor=donor,
                        details={
                            "donor_id": donor.donor_id,
                            "constant": key,
                            "value": donor.constants.get(key),
                        },
                    ),
                )
                if edge is not None
            )
            refusals.append(
                LaneRefusal(
                    target.recipient_id,
                    lane,
                    "conflicting_constant",
                    "donors disagree about constant " + key,
                    evidence,
                )
            )
        else:
            constants[key] = constant_values[key]
    if not selected:
        refusals.append(
            LaneRefusal(
                target.recipient_id,
                lane,
                "no_compatible_donor",
                "no compatible donor matched the selected recipient",
            )
        )
    return StructuralTriangulation(
        donors=selected,
        declarations=declarations,
        constants=constants,
        structural_differences=tuple(sorted(set(differences))),
        refusals=tuple(refusals),
    )


def _structural_discovery(
    recipient: Recipient,
    *,
    options: Mapping[str, Any],
    root: Path,
    lane: str = "multi_donor",
) -> _Discovery:
    result = _Discovery()
    raw = options.get("donors", ())
    if isinstance(raw, Mapping):
        raw = raw.get(recipient.recipient_id, ())
    if callable(raw):
        raw = _call_fetcher(raw, recipient)
    if raw is None:
        raw = ()
    try:
        raw = tuple(raw)
    except TypeError:
        raw = (raw,)
    if lane == "cfg_dataflow":
        raw = tuple(
            item for item in raw
            if str(_value(item, "match_kind", _value(item, "kind", ""))).lower()
            in {"cfg", "cfg_dataflow", "dataflow", "data_flow", "control_flow"}
        )
    triangulation = triangulate_donors(recipient, raw, lane=lane)
    result.attempts = len(raw)
    result.provenance.extend(
        edge
        for donor in triangulation.donors
        for edge in (
            _donor_provenance(
                lane=lane,
                recipient=recipient,
                kind="donor_selection",
                donor=donor,
                details={
                    "donor": donor.to_dict(),
                    "rank": _donor_rank(donor, recipient),
                },
            ),
        )
        if edge is not None
    )
    result.input_identities.extend(
        donor.source_identity
        for donor in triangulation.donors
        if donor.source_identity
    )
    for refusal in triangulation.refusals:
        result.refusal_code = result.refusal_code or refusal.code
        result.rejection_counts[refusal.code] += 1
        result.provenance.extend(refusal.evidence)
    blocking_codes = {
        "conflicting_declaration",
        "conflicting_constant",
        "incompatible_donor",
    }
    if any(refusal.code in blocking_codes for refusal in triangulation.refusals):
        result.completion_reason = "search_space_exhausted"
        result.reason = triangulation.refusals[0].reason
        return result
    if triangulation.refusals and not triangulation.donors:
        result.completion_reason = "inapplicable"
        result.reason = triangulation.refusals[0].reason
        return result

    for donor in triangulation.donors:
        body = donor.body or ""
        source_path = donor.source_path
        if not body and source_path:
            body, relative = _read_repo_text(source_path, root)
            source_path = relative or source_path
            if body and donor.symbol:
                extracted = _extract_function(body, donor.symbol)
                if extracted:
                    body = extracted
        if not body:
            result.rejection_counts["donor_body_unavailable"] += 1
            continue
        body_identity = hash_bytes(body.encode("utf-8"))
        file_identity = _file_identity(source_path, root) if source_path else ""
        declared_identity = ""
        if isinstance(donor.source, ArtifactRef):
            declared_identity = donor.source.content_hash
        elif donor.metadata.get("source_identity") is not None:
            try:
                declared_identity = _identity(
                    donor.metadata["source_identity"],
                    label="donor source identity",
                )
            except LaneError:
                result.rejection_counts["donor_identity_unavailable"] += 1
                continue
        if declared_identity:
            if file_identity and declared_identity != file_identity:
                result.rejection_counts["donor_identity_mismatch"] += 1
                continue
            if not file_identity and not source_path and declared_identity != body_identity:
                result.rejection_counts["donor_identity_mismatch"] += 1
                continue
        source_identity = declared_identity or file_identity or body_identity
        try:
            # This checks all supplied source-level constants before the
            # candidate is even materialized.  A rejected unsafe value remains
            # evidence in the refusal receipt and cannot silently become an edit.
            for key, value in donor.constants.items():
                reject_unsafe_semantic_constant(value, label=str(key))
        except UnsafeSemanticConstant:
            result.rejection_counts["unsafe_semantic_constant"] += 1
            continue
        evidence = _provenance(
            lane=lane,
            recipient=recipient,
            kind="semantic_donor",
            source=source_path or donor.donor_id,
            details={
                "donor_id": donor.donor_id,
                "version": donor.version,
                "match_kind": donor.match_kind,
                "signature": donor.signature,
                "declarations": dict(donor.declarations),
                "constants": dict(donor.constants),
                "structural_differences": list(donor.structural_differences),
            },
            source_identity=source_identity,
            input_identity=source_identity,
        )
        result.provenance.append(evidence)
        candidate = _source_candidate(
            lane=lane,
            recipient=recipient,
            source=body,
            provenance=(evidence,),
            source_path=source_path if _relative_path(source_path) else None,
        )
        if candidate is not None:
            result.candidates.append(candidate)
            result.input_identities.append(candidate.candidate_id)
    if result.candidates:
        result.completion_reason = "matched_pending_oracle"
        result.reason = "compatible semantic donors triangulated"
    elif triangulation.donors:
        # Donors were applicable, but every body was rejected or unavailable.
        # Preserve that distinction from an inapplicable lane with no evidence.
        result.completion_reason = "search_space_exhausted"
        result.refusal_code = result.refusal_code or "no_usable_donor"
        result.rejection_counts["no_usable_donor"] += 1
        result.reason = "donors had no complete, evidence-backed body"
    else:
        result.completion_reason = "inapplicable"
        result.refusal_code = result.refusal_code or "no_usable_donor"
        result.rejection_counts["no_usable_donor"] += 1
        result.reason = "donors had no complete, evidence-backed body"
    return result


def parse_mipsmatch_results(value: Any) -> Tuple[Mapping[str, Any], ...]:
    """Normalize JSON/YAML/list mipsmatch output without writing a report."""
    if value is None:
        return ()
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            try:
                yaml = importlib.import_module("yaml")
                documents = tuple(yaml.safe_load_all(value))
                value = documents
            except (ImportError, ValueError, TypeError):
                return ()
    if isinstance(value, Mapping):
        if any(key in value for key in ("matches", "functions", "segments", "results")):
            nested = next(
                value[key] for key in ("matches", "functions", "segments", "results")
                if key in value
            )
            return parse_mipsmatch_results(nested)
        return (dict(value),)
    if isinstance(value, (list, tuple)):
        result: list[Mapping[str, Any]] = []
        for item in value:
            if isinstance(item, Mapping):
                result.append(dict(item))
            elif isinstance(item, (list, tuple)):
                result.extend(parse_mipsmatch_results(item))
        return tuple(result)
    return ()


def mipsmatch_fingerprint(
    map_path: str,
    elf_path: str,
    *,
    output: Optional[str] = None,
    map_content: Optional[str | bytes] = None,
    elf_content: Optional[str | bytes] = None,
    map_content_hash: Optional[str] = None,
    elf_content_hash: Optional[str] = None,
    tool_identity: Optional[str] = None,
    tool_content: Optional[str | bytes] = None,
) -> Mapping[str, Any]:
    """Describe a fingerprint operation bound to real input identities.

    Paths are command arguments only.  They are never part of the reference
    identity because two paths can name the same bytes and one path can be
    replaced underneath a run.
    """
    if not isinstance(map_path, str) or not map_path:
        raise LaneError("mipsmatch map path must be a nonempty string")
    if not isinstance(elf_path, str) or not elf_path:
        raise LaneError("mipsmatch ELF path must be a nonempty string")
    if output is not None and not isinstance(output, str):
        raise LaneError("mipsmatch output path must be a string")

    def content_identity(
        content: Optional[str | bytes], declared: Optional[str], label: str
    ) -> str:
        computed = None
        if content is not None:
            if isinstance(content, str):
                content = content.encode("utf-8")
            if not isinstance(content, bytes):
                raise LaneError(label + " content must be bytes or text")
            computed = hash_bytes(content)
        if declared is None and computed is None:
            raise LaneError(label + " content identity is required")
        if declared is not None:
            declared = validate_hash(declared, label + " content hash")
        if declared is not None and computed is not None and declared != computed:
            raise LaneError(label + " content hash disagrees with supplied content")
        return declared or computed  # type: ignore[return-value]

    map_identity = content_identity(map_content, map_content_hash, "mipsmatch map")
    elf_identity = content_identity(elf_content, elf_content_hash, "mipsmatch ELF")
    computed_tool_identity = None
    if tool_content is not None:
        if isinstance(tool_content, str):
            tool_content = tool_content.encode("utf-8")
        if not isinstance(tool_content, bytes):
            raise LaneError("mipsmatch tool content must be bytes or text")
        computed_tool_identity = hash_bytes(tool_content)
    if tool_identity is None:
        if computed_tool_identity is None:
            raise LaneError("mipsmatch tool identity is required")
        tool_identity = computed_tool_identity
    tool_identity = validate_hash(tool_identity, "mipsmatch tool identity")
    if computed_tool_identity is not None and tool_identity != computed_tool_identity:
        raise LaneError("mipsmatch tool identity disagrees with supplied content")
    args = ["fingerprint", map_path, elf_path]
    if output:
        args = ["--output", output] + args
    reference_identity = hash_canonical(
        {
            "map_content_hash": map_identity,
            "elf_content_hash": elf_identity,
            "tool_identity": tool_identity,
        }
    )
    return {
        "tool": "tools/mipsmatch",
        "command": tuple(args),
        "map_content_hash": map_identity,
        "elf_content_hash": elf_identity,
        "tool_identity": tool_identity,
        "reference_identity": reference_identity,
        "read_only": True,
    }


def mipsmatch_scan(
    results: Any,
    *,
    target_recipient_id: Optional[str] = None,
) -> Tuple[Mapping[str, Any], ...]:
    """Return only explicitly proven exact hits for the requested target."""
    rows = parse_mipsmatch_results(results)
    selected = []
    for row in rows:
        if not _hit_exact(row):
            continue
        # A scan row without a target is ambiguous.  Discovery and scan must
        # use the same exact-target contract, so do not surface it as a
        # generic hit merely because it carries an exact marker.
        target = _hit_target(row)
        if not target or _mipsmatch_reference_identity(row) is None:
            continue
        if target_recipient_id is None or target == target_recipient_id:
            selected.append(row)
    return tuple(selected)


def _hit_target(row: Mapping[str, Any]) -> str:
    for key in ("recipient_id", "record_id", "queue_record_id", "target_id"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    target = row.get("target")
    if isinstance(target, str) and target:
        return target
    return ""


def _hit_exact(row: Mapping[str, Any]) -> bool:
    kind = row.get("match_kind", row.get("kind"))
    if not isinstance(kind, str) or kind.lower() not in {"exact", "exact_copy", "fingerprint"}:
        return False
    if row.get("exact") is False or row.get("is_exact") is False:
        return False
    if row.get("fingerprint_equal") is False:
        return False
    fingerprint = row.get("fingerprint")
    try:
        validate_hash(fingerprint, "mipsmatch fingerprint")
    except SearchValidationError:
        return False
    target_fingerprint = row.get("target_fingerprint")
    candidate_fingerprint = row.get("candidate_fingerprint")
    pair_equal = False
    if target_fingerprint is not None or candidate_fingerprint is not None:
        try:
            target_fingerprint = validate_hash(target_fingerprint, "target fingerprint")
            candidate_fingerprint = validate_hash(candidate_fingerprint, "candidate fingerprint")
        except SearchValidationError:
            return False
        if target_fingerprint != candidate_fingerprint:
            return False
        pair_equal = True
    proof = row.get("exact_proof")
    proof_equal = isinstance(proof, Mapping) and proof.get("fingerprint_equal") is True
    if proof is not None:
        if not proof_equal:
            return False
    if (
        row.get("exact") is not True
        and row.get("is_exact") is not True
        and row.get("fingerprint_equal") is not True
        and not proof_equal
        and not pair_equal
    ):
        return False
    return True


def _duplicate_rows(root: Path, options: Mapping[str, Any]) -> Tuple[Mapping[str, Any], ...]:
    source: Any = options.get("duplicate_provenance")
    if source is None:
        path = root / "automation" / "duplicate-provenance.us.json"
        try:
            source = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ()
    if isinstance(source, Mapping):
        rows = source.get("entries", source.get("rows", ()))
    else:
        rows = source
    if isinstance(rows, Mapping):
        rows = (rows,)
    if not isinstance(rows, (list, tuple)):
        return ()
    return tuple(dict(item) for item in rows if isinstance(item, Mapping))


def _duplicate_row_matches(
    row: Mapping[str, Any],
    recipient: Recipient,
) -> bool:
    function = str(row.get("target_function", row.get("function", "")))
    if function not in {recipient.function, _base_function(recipient.function)}:
        return False
    target_path = str(
        recipient.metadata.get("source_path")
        or recipient.metadata.get("target_path")
        or recipient.metadata.get("target_file")
        or ""
    ).replace("\\", "/")
    row_path = str(row.get("target_file", "")).replace("\\", "/")
    return not target_path or not row_path or target_path == row_path


def _mipsmatch_reference_identity(
    row: Mapping[str, Any],
) -> Optional[Tuple[str, str, str, str]]:
    """Return map, ELF, tool and combined identities from explicit content."""
    def content_identity(prefix: str) -> Optional[str]:
        declared = row.get(prefix + "_content_hash")
        content = row.get(prefix + "_content")
        computed = None
        if content is not None:
            if isinstance(content, str):
                content = content.encode("utf-8")
            if not isinstance(content, bytes):
                return None
            computed = hash_bytes(content)
        if declared is None and computed is None:
            return None
        try:
            declared = (
                validate_hash(declared, prefix + " content hash")
                if declared is not None
                else None
            )
        except SearchValidationError:
            return None
        if declared is not None and computed is not None and declared != computed:
            return None
        return declared or computed

    map_identity = content_identity("map")
    elf_identity = content_identity("elf")
    tool_identity = row.get("tool_identity", row.get("tool_hash"))
    computed_tool_identity = None
    if tool_identity is None:
        tool_content = row.get("tool_content")
        if isinstance(tool_content, str):
            tool_content = tool_content.encode("utf-8")
        if isinstance(tool_content, bytes):
            computed_tool_identity = hash_bytes(tool_content)
            tool_identity = computed_tool_identity
    elif row.get("tool_content") is not None:
        if not isinstance(row.get("tool_content"), (str, bytes)):
            return None
        tool_content = row["tool_content"]
        if isinstance(tool_content, str):
            tool_content = tool_content.encode("utf-8")
        computed_tool_identity = hash_bytes(tool_content)
    try:
        tool_identity = validate_hash(tool_identity, "mipsmatch tool identity")
    except SearchValidationError:
        return None
    if computed_tool_identity is not None and tool_identity != computed_tool_identity:
        return None
    if map_identity is None or elf_identity is None:
        return None
    reference_identity = hash_canonical(
        {
            "map_content_hash": map_identity,
            "elf_content_hash": elf_identity,
            "tool_identity": tool_identity,
        }
    )
    declared_reference = row.get("reference_identity")
    if declared_reference is not None:
        try:
            if validate_hash(declared_reference, "mipsmatch reference identity") != reference_identity:
                return None
        except SearchValidationError:
            return None
    return map_identity, elf_identity, tool_identity, reference_identity


def _mipsmatch_discovery(
    recipient: Recipient,
    *,
    options: Mapping[str, Any],
    root: Path,
    callback: Optional[Callable[[Recipient], Any]] = None,
) -> _Discovery:
    result = _Discovery()
    raw: Any = None
    if callback is not None:
        raw = _call_fetcher(callback, recipient)
    else:
        matches = options.get("mipsmatch_matches")
        if isinstance(matches, Mapping):
            # Exact key lookup is intentional.  There is no all-record fallback.
            raw = matches.get(recipient.recipient_id)
        elif matches is not None:
            raw = matches
        if raw is None:
            fixture = options.get("mipsmatch_fixture")
            if fixture:
                text, _ = _read_repo_text(fixture, root)
                raw = text
    rows = parse_mipsmatch_results(raw)
    result.attempts = len(rows)
    if raw is None:
        result.refusal_code = "no_mipsmatch_scan"
        result.completion_reason = "inapplicable"
        result.rejection_counts["no_mipsmatch_scan"] += 1
        result.reason = "mipsmatch scan input was not supplied"
        return result
    duplicate_rows = tuple(
        row for row in _duplicate_rows(root, options)
        if _duplicate_row_matches(row, recipient)
    )
    for row in rows:
        if not _hit_exact(row):
            result.rejection_counts["non_exact_hit"] += 1
            continue
        reference_identities = _mipsmatch_reference_identity(row)
        if reference_identities is None:
            result.rejection_counts["missing_reference_identity"] += 1
            continue
        map_identity, elf_identity, tool_identity, reference_identity = reference_identities
        target = _hit_target(row)
        function = row.get("function", row.get("symbol", ""))
        if not isinstance(function, str):
            function = ""
        if target != recipient.recipient_id:
            result.rejection_counts["recipient_mismatch"] += 1
            continue
        if not target:
            result.rejection_counts["recipient_ambiguous"] += 1
            continue
        if function and function not in {recipient.function, _base_function(recipient.function)}:
            result.rejection_counts["recipient_ambiguous"] += 1
            continue
        source = row.get(
            "body",
            row.get("source_code", row.get("candidate_source", row.get("source", ""))),
        )
        source_path = row.get("source_path")
        if not source and isinstance(source_path, str):
            source, source_path = _read_repo_text(source_path, root)
        if not source and isinstance(row.get("reference_path"), str):
            maybe, relative = _read_repo_text(row["reference_path"], root)
            if maybe:
                source = _extract_function(
                    maybe, function or recipient.function
                ) or maybe
                source_path = relative
        if isinstance(source, bytes):
            source = source.decode("utf-8", "replace")
        if isinstance(source, str) and source and function:
            extracted = _extract_function(source, function)
            if extracted and extracted.strip() != source.strip():
                source = extracted
        if not isinstance(source, str) or not source:
            result.rejection_counts["body_unavailable"] += 1
            continue
        body_identity = hash_bytes(source.encode("utf-8"))
        declared_body = row.get("body_hash")
        if declared_body is not None:
            try:
                if validate_hash(declared_body, "mipsmatch body hash") != body_identity:
                    result.rejection_counts["body_identity_mismatch"] += 1
                    continue
            except SearchValidationError:
                result.rejection_counts["body_identity_mismatch"] += 1
                continue
        reference_id = str(
            row.get("reference_id")
            or row.get("reference")
            or row.get("fingerprint")
            or row.get("reference_path")
            or row.get("source_path")
            or ""
        )
        if not reference_id:
            reference_id = reference_identity
        evidence = _provenance(
            lane="mipsmatch_exact",
            recipient=recipient,
            kind="mipsmatch_exact",
            source=reference_id,
            details={
                "reference_id": reference_id,
                "reference_identity": reference_identity,
                "map_content_hash": map_identity,
                "elf_content_hash": elf_identity,
                "tool_identity": tool_identity,
                "reference_path": row.get("reference_path"),
                "fingerprint": row.get("fingerprint"),
                "body_hash": body_identity,
                "target_offset": row.get("target_offset", row.get("offset")),
                "match_kind": row.get("match_kind", row.get("kind", "exact")),
                "body_source": row.get("body_source", row.get("source_path")),
                "raw_hit": dict(row),
                "duplicate_provenance": [dict(item) for item in duplicate_rows],
            },
            source_identity=reference_identity,
            input_identity=reference_identity,
        )
        candidate = _source_candidate(
            lane="mipsmatch_exact",
            recipient=recipient,
            source=source,
            provenance=(evidence,),
            source_path=source_path if isinstance(source_path, str) else None,
        )
        if candidate is None:
            result.rejection_counts["candidate_unavailable"] += 1
            continue
        result.candidates.append(candidate)
        result.provenance.append(evidence)
        result.input_identities.extend(
            (
                map_identity,
                elf_identity,
                tool_identity,
                reference_identity,
                body_identity,
                validate_hash(row["fingerprint"], "mipsmatch fingerprint"),
                candidate.candidate_id,
            )
        )
    if result.candidates:
        result.completion_reason = "matched_pending_oracle"
        result.reason = "exact mipsmatch body discovered and reconciled"
    elif result.rejection_counts:
        result.completion_reason = "search_space_exhausted"
        result.refusal_code = "no_exact_body"
        result.rejection_counts["no_exact_body"] += 1
        result.reason = "mipsmatch produced no usable exact body"
    else:
        result.completion_reason = "inapplicable"
        result.refusal_code = "no_exact_hit"
        result.rejection_counts["no_exact_hit"] += 1
        result.reason = "mipsmatch produced no exact hit for this recipient"
    return result


def _receipt(
    manifest: Any,
    recipient: Recipient,
    lane: str,
    discovery: _Discovery,
) -> LaneReceiptProposal:
    candidates = _merge_candidates(
        item for item in discovery.candidates if item.recipient_id == recipient.recipient_id
    )
    if len(candidates) != len(discovery.candidates):
        discovery.rejection_counts["recipient_mismatch"] += (
            len(discovery.candidates) - len(candidates)
        )
    candidate_ids = tuple(sorted(item.candidate_id for item in candidates))
    inputs = [_manifest_source(manifest), _manifest_target(manifest, recipient.recipient_id), _manifest_compiler(manifest)]
    for item in discovery.input_identities:
        inputs.append(_identity(item, label="lane input"))
    for item in discovery.provenance:
        if (
            not isinstance(item, Mapping)
            or "source_identity" not in item
            or "input_identity" not in item
        ):
            raise LaneError(
                "lane provenance needs source_identity and input_identity"
            )
        _identity(item["source_identity"], label="lane provenance source")
        inputs.append(_identity(item["input_identity"], label="lane provenance input"))
    input_ids = tuple(dict.fromkeys(inputs))
    if discovery.completion_reason not in _COMPLETION_REASONS:
        raise LaneError("lane completion_reason is not recognized")
    if (
        discovery.refusal_code
        and not candidates
        and discovery.completion_reason
        not in {"budget_exhausted", "search_space_exhausted"}
    ):
        discovery.completion_reason = "inapplicable"
    if isinstance(discovery.attempts, bool) or not isinstance(discovery.attempts, int) or discovery.attempts < 0:
        raise LaneError("lane attempts must be a nonnegative integer")
    attempts = discovery.attempts
    declared_budget = _manifest_lane_budget(manifest, lane)
    if declared_budget.unit == "attempts":
        measured = attempts
    elif declared_budget.unit == "candidates":
        measured = len(candidates)
    elif declared_budget.unit == "tasks":
        measured = 1 if (attempts or candidates or discovery.refusal_code) else 0
    else:
        raise LaneError(
            "lane budget unit must be attempts, candidates or tasks for read-only adapters"
        )
    consumed = min(measured, declared_budget.limit)
    budget = Budget(declared_budget.unit, declared_budget.limit, consumed)
    if measured > declared_budget.limit:
        discovery.completion_reason = "budget_exhausted"
        discovery.rejection_counts["budget_exhausted"] += measured - declared_budget.limit
    tools = _manifest_lane_tools(manifest, lane)
    return LaneReceiptProposal(
        recipient_id=recipient.recipient_id,
        lane=lane,
        tier=LANE_TIERS[lane],
        tool_identities=tools,
        config_identity=_manifest_config(manifest),
        input_identities=input_ids,
        budget=budget,
        attempts=attempts,
        rejection_counts=dict(sorted(discovery.rejection_counts.items())),
        best_candidate_ids=candidate_ids,
        completion_reason=discovery.completion_reason,
        reason=discovery.reason,
    )


def _outcome(
    manifest: Any,
    recipient: Recipient,
    lane: str,
    discovery: _Discovery,
) -> LaneOutcome:
    candidates = _merge_candidates(discovery.candidates)
    if candidates:
        discovery.completion_reason = (
            "matched_pending_oracle"
            if discovery.completion_reason == "inapplicable"
            else discovery.completion_reason
        )
    refusal = None
    if discovery.refusal_code:
        refusal = LaneRefusal(
            recipient.recipient_id,
            lane,
            discovery.refusal_code,
            discovery.reason or discovery.refusal_code,
            tuple(discovery.provenance),
        )
    receipt = _receipt(manifest, recipient, lane, discovery)
    return LaneOutcome(
        lane=lane,
        recipient_id=recipient.recipient_id,
        candidates=candidates,
        receipt=receipt,
        provenance=tuple(discovery.provenance),
        refusal=refusal,
        reason=discovery.reason,
    )


def _options_with_defaults(options: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    if options is None:
        return {}
    if not isinstance(options, Mapping):
        raise LaneError("options must be a mapping")
    return options


def _check_read_only(read_only: bool, kwargs: Mapping[str, Any]) -> None:
    if read_only is not True:
        raise ReadOnlyViolation("lane adapters are read-only")
    attempted = [key for key in _WRITE_OPTIONS if kwargs.get(key)]
    if attempted:
        raise ReadOnlyViolation(
            "lane write option(s) refused: " + ", ".join(attempted)
        )


def _dispatch(
    manifest: Any,
    lane: str,
    recipient: Recipient,
    *,
    adapters: LaneAdapters,
    options: Mapping[str, Any],
    root: Path,
) -> _Discovery:
    callback = adapters.for_lane(lane)
    if callback is not None:
        raw = _call_fetcher(callback, recipient)
        if lane == "mipsmatch_exact":
            return _mipsmatch_discovery(
                recipient, options=options, root=root, callback=lambda _r: raw
            )
        if (
            lane in {"multi_donor", "cfg_dataflow"}
            and isinstance(raw, Mapping)
            and "candidates" in raw
        ):
            return _discovery_from_values(
                raw, lane=lane, recipient=recipient, root=root
            )
        if lane in {"multi_donor", "cfg_dataflow"}:
            if isinstance(raw, Mapping) and "donors" in raw:
                raw = raw["donors"]
            scoped = dict(options)
            scoped["donors"] = raw
            return _structural_discovery(
                recipient, options=scoped, root=root, lane=lane
            )
        if lane in {"upstream_current", "upstream_pinned"}:
            return _discovery_from_values(
                raw, lane=lane, recipient=recipient, root=root
            )
        return _discovery_from_values(
            raw, lane=lane, recipient=recipient, root=root
        )

    if lane == "upstream_current":
        return _upstream_discovery(recipient, pinned=False, options=options, root=root)
    if lane == "upstream_pinned":
        return _upstream_discovery(recipient, pinned=True, options=options, root=root)
    if lane == "upstream_open_pr":
        # Open PR refs are explicit inputs, not current-upstream fallback.
        scoped = dict(options)
        scoped["pinned_refs"] = options.get("open_pr_refs", {})
        return _upstream_discovery(recipient, pinned=True, options=scoped, root=root)
    if lane == "preserved_candidate":
        return _preserved_discovery(recipient, options=options, root=root)
    if lane == "shared_header":
        return _shared_header_discovery(recipient, options=options, root=root)
    if lane == "transplant":
        return _twin_discovery(
            recipient, options=options, root=root, transplant_only=True
        )
    if lane == "whole_tu":
        return _whole_tu_discovery(recipient, options=options, root=root)
    if lane == "dependency_closure":
        return _dependency_discovery(recipient, options=options, root=root)
    if lane in {"multi_donor", "cfg_dataflow"}:
        return _structural_discovery(
            recipient, options=options, root=root, lane=lane
        )
    if lane == "mipsmatch_exact":
        return _mipsmatch_discovery(recipient, options=options, root=root)
    raise LaneError("no adapter for lane " + lane)


def _parse_run_lane_args(
    manifest: Any,
    lane: Any,
    recipients: Any,
) -> Tuple[Any, str, Any]:
    # Support both run_lane(manifest, lane, recipients) and the natural
    # run_lane(lane, manifest, recipients) spelling used by small scripts.
    if isinstance(manifest, str) and not isinstance(lane, str):
        manifest, lane = lane, manifest
    if not isinstance(lane, str):
        raise LaneError("lane name must be a string")
    validate_lane(lane)
    if recipients is None:
        raise SubsetViolation("explicit recipients are required; queue fallback is forbidden")
    return manifest, lane, recipients


def execute_task(
    task: SearchTask | Mapping[str, Any],
    manifest: RunManifest | Mapping[str, Any],
    recipients: Mapping[str, Any] | Iterable[Any] | None,
    *,
    adapters: Optional[LaneAdapters | Mapping[str, Any]] = None,
    options: Optional[Mapping[str, Any]] = None,
    repo_root: Optional[str | Path] = None,
    read_only: bool = True,
    **kwargs: Any,
) -> LaneOutcome:
    """Execute exactly one coordinator-owned task against its frozen recipient.

    The caller supplies the complete manifest subset so validation cannot fall
    back to the live queue. Only the task's named recipient is dispatched.
    Task identity, lane, tier, configuration and state are checked before any
    producer callback runs.
    """
    try:
        typed_manifest = (
            manifest if isinstance(manifest, RunManifest)
            else RunManifest.from_dict(manifest)
        )
        typed_task = (
            task if isinstance(task, SearchTask)
            else SearchTask.from_dict(task)
        )
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise LaneError("task execution requires typed manifest and task values") from exc
    # The coordinator derives task_id and task_seed from the immutable
    # manifest fields.  Reuse that single binding implementation here before
    # any producer callback runs, so a forged task cannot reach a lane merely
    # because its recipient and lane names look plausible.
    try:
        from .search_coordinator import (
            CoordinatorError,
            validate_task_binding,
        )
    except ImportError:  # pragma: no cover - direct script compatibility
        from search_coordinator import (  # type: ignore
            CoordinatorError,
            validate_task_binding,
        )
    try:
        validate_task_binding(typed_manifest, typed_task)
    except CoordinatorError as exc:
        raise LaneError("task identity is not bound to the immutable manifest") from exc
    if recipients is None:
        raise SubsetViolation("explicit recipients are required; queue fallback is forbidden")
    selected = validate_recipient_subset(typed_manifest, recipients)
    if typed_task.recipient_id not in typed_manifest.queue_record_ids:
        raise SubsetViolation("task recipient is outside the manifest subset")
    if typed_task.lane not in typed_manifest.selected_lanes:
        raise LaneError("task lane is not selected by the manifest")
    if typed_task.tier != LANE_TIERS[typed_task.lane]:
        raise LaneError("task lane and tier do not agree")
    if typed_task.config_identity != typed_manifest.config_identity:
        raise LaneError("task configuration differs from the manifest")
    if typed_task.state not in {"scheduled", "started"}:
        raise LaneError("only scheduled or started tasks may execute")
    recipient = next(
        item for item in selected if item.recipient_id == typed_task.recipient_id
    )
    _validate_manifest(typed_manifest, tuple(item.recipient_id for item in selected), typed_task.lane)
    adapter_set = (
        adapters
        if isinstance(adapters, LaneAdapters)
        else LaneAdapters.from_mapping(adapters)
    )
    merged_options = dict(_options_with_defaults(options))
    merged_options.update(kwargs)
    _check_read_only(read_only, merged_options)
    if repo_root is not None:
        merged_options["repo_root"] = repo_root
    root = _repo_root(merged_options)
    discovery = _dispatch(
        typed_manifest,
        typed_task.lane,
        recipient,
        adapters=adapter_set,
        options=merged_options,
        root=root,
    )
    return _outcome(
        typed_manifest, recipient, typed_task.lane, discovery
    )


def run_lane(
    manifest: Any,
    lane: str,
    recipients: Mapping[str, Any] | Iterable[Any] | None = None,
    *,
    adapters: Optional[LaneAdapters | Mapping[str, Any]] = None,
    options: Optional[Mapping[str, Any]] = None,
    repo_root: Optional[str | Path] = None,
    read_only: bool = True,
    **kwargs: Any,
) -> LaneBatch:
    """Run one named lane for exactly the manifest's recipient subset."""
    manifest, lane, recipients = _parse_run_lane_args(manifest, lane, recipients)
    try:
        if not isinstance(manifest, RunManifest):
            manifest = RunManifest.from_dict(manifest)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise LaneError("lane manifest is not a valid typed RunManifest") from exc
    selected = validate_recipient_subset(manifest, recipients)
    _validate_manifest(manifest, tuple(item.recipient_id for item in selected), lane)
    adapter_set = (
        adapters
        if isinstance(adapters, LaneAdapters)
        else LaneAdapters.from_mapping(adapters)
    )
    merged_options = dict(_options_with_defaults(options))
    merged_options.update(kwargs)
    _check_read_only(read_only, merged_options)
    if repo_root is not None:
        merged_options["repo_root"] = repo_root
    root = _repo_root(merged_options)
    outcomes = []
    for recipient in selected:
        discovery = _dispatch(
            manifest,
            lane,
            recipient,
            adapters=adapter_set,
            options=merged_options,
            root=root,
        )
        outcomes.append(_outcome(manifest, recipient, lane, discovery))
    return LaneBatch(lane, tuple(outcomes))


def run_lanes(
    manifest: Any,
    lanes: Sequence[str],
    recipients: Mapping[str, Any] | Iterable[Any] | None = None,
    *,
    adapters: Optional[LaneAdapters | Mapping[str, Any]] = None,
    options: Optional[Mapping[str, Any]] = None,
    repo_root: Optional[str | Path] = None,
    read_only: bool = True,
    **kwargs: Any,
) -> LaneRun:
    """Run explicit lanes over the same exact subset, in stable order."""
    if recipients is None:
        raise SubsetViolation("explicit recipients are required; queue fallback is forbidden")
    if not isinstance(lanes, (list, tuple)):
        raise LaneError("lanes must be an explicit sequence")
    if not lanes:
        raise LaneError("at least one explicit lane is required")
    if any(not isinstance(item, str) for item in lanes):
        raise LaneError("lane names must be strings")
    names = tuple(lanes)
    if len(set(names)) != len(names):
        raise LaneError("duplicate lane names are not allowed")
    for name in names:
        validate_lane(name)
    # Validate the subset once before starting any producer.
    validate_recipient_subset(manifest, recipients)
    batches = tuple(
        run_lane(
            manifest,
            name,
            recipients,
            adapters=adapters,
            options=options,
            repo_root=repo_root,
            read_only=read_only,
            **kwargs,
        )
        for name in names
    )
    return LaneRun(batches)


def run_deterministic_lanes(
    manifest: Any,
    recipients: Mapping[str, Any] | Iterable[Any] | None = None,
    *,
    lanes: Sequence[str] = DETERMINISTIC_LANES,
    adapters: Optional[LaneAdapters | Mapping[str, Any]] = None,
    options: Optional[Mapping[str, Any]] = None,
    repo_root: Optional[str | Path] = None,
    read_only: bool = True,
    **kwargs: Any,
) -> LaneRun:
    return run_lanes(
        manifest,
        lanes,
        recipients,
        adapters=adapters,
        options=options,
        repo_root=repo_root,
        read_only=read_only,
        **kwargs,
    )



def _run_named_lane(
    lane: str,
    manifest: Any,
    recipients: Mapping[str, Any] | Iterable[Any] | None = None,
    **kwargs: Any,
) -> LaneBatch:
    return run_lane(manifest, lane, recipients, **kwargs)


def run_upstream_current(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("upstream_current", manifest, recipients, **kwargs)


def run_upstream_pinned(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("upstream_pinned", manifest, recipients, **kwargs)


def run_upstream_open_pr(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("upstream_open_pr", manifest, recipients, **kwargs)


def run_mipsmatch_exact(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("mipsmatch_exact", manifest, recipients, **kwargs)


def run_preserved_candidate(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("preserved_candidate", manifest, recipients, **kwargs)


def run_shared_header(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("shared_header", manifest, recipients, **kwargs)


def run_transplant(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("transplant", manifest, recipients, **kwargs)


def run_whole_tu(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("whole_tu", manifest, recipients, **kwargs)


def run_dependency_closure(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("dependency_closure", manifest, recipients, **kwargs)


def run_multi_donor(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("multi_donor", manifest, recipients, **kwargs)


def run_cfg_dataflow(manifest: Any, recipients: Any = None, **kwargs: Any) -> LaneBatch:
    return _run_named_lane("cfg_dataflow", manifest, recipients, **kwargs)


def plan_mipsmatch_fingerprint(
    overlay: str,
    version: str,
    source_overlay: str,
    *,
    build_root: str = "build",
    map_content_hash: Optional[str] = None,
    elf_content_hash: Optional[str] = None,
    tool_identity: Optional[str] = None,
) -> Mapping[str, Any]:
    """Build a read-only fingerprint plan matching make-config.py."""
    build_dir = f"{build_root}/{version}"
    output = f"{build_dir}/fingerprint.{source_overlay}.yaml"
    map_path = f"{build_dir}/{source_overlay}.map"
    elf_path = f"{build_dir}/{source_overlay}.elf"
    plan: dict[str, Any] = {
        "overlay": overlay,
        "version": version,
        "source_overlay": source_overlay,
        "map_path": map_path,
        "elf_path": elf_path,
        "output": output,
        "command": ("--output", output, "fingerprint", map_path, elf_path),
        "read_only": True,
        "identity_ready": False,
    }
    if map_content_hash is not None or elf_content_hash is not None or tool_identity is not None:
        operation = mipsmatch_fingerprint(
            map_path,
            elf_path,
            output=output,
            map_content_hash=map_content_hash,
            elf_content_hash=elf_content_hash,
            tool_identity=tool_identity,
        )
        plan.update(
            {
                "map_content_hash": operation["map_content_hash"],
                "elf_content_hash": operation["elf_content_hash"],
                "tool_identity": operation["tool_identity"],
                "reference_identity": operation["reference_identity"],
                "identity_ready": True,
            }
        )
    return plan


current_upstream = run_upstream_current
pinned_upstream = run_upstream_pinned
open_pr_upstream = run_upstream_open_pr
preserved_candidates = run_preserved_candidate
shared_header = run_shared_header
transplant_lane = run_transplant
whole_tu_closure = run_whole_tu
dependency_data_closure = run_dependency_closure
multi_donor = run_multi_donor
cfg_dataflow_lane = run_cfg_dataflow


execute_lane = run_lane
execute_lanes = run_lanes
deterministic_lanes = run_deterministic_lanes
mipsmatch_lane = lambda manifest, recipients, **kw: run_lane(
    manifest, "mipsmatch_exact", recipients, **kw
)
multi_donor_lane = lambda manifest, recipients, **kw: run_lane(
    manifest, "multi_donor", recipients, **kw
)
structural_signature_lane = multi_donor_lane


__all__ = [
    "MODULE_IDENTITY",
    "DETERMINISTIC_LANES",
    "LaneError",
    "SubsetViolation",
    "ReadOnlyViolation",
    "UnsafeSemanticConstant",
    "IncompatibleDonor",
    "CandidateIdentityMismatch",
    "AdapterSignatureError",
    "ImmutableReferenceError",
    "Recipient",
    "QueueRecipient",
    "SearchRecipient",
    "LaneEvidence",
    "Provenance",
    "LaneCandidate",
    "CandidateEvidence",
    "LaneRefusal",
    "Refusal",
    "LaneOutcome",
    "LaneReceiptProposal",
    "LaneBatch",
    "LaneRun",
    "LaneAdapters",
    "LaneProviders",
    "LaneContext",
    "DonorEvidence",
    "StructuralTriangulation",
    "validate_recipient_subset",
    "assert_exact_subset",
    "validate_manifest_subset",
    "reject_unsafe_semantic_constant",
    "semantic_constant_allowed",
    "is_safe_semantic_constant",
    "validate_semantic_constant",
    "gather_donors",
    "collect_donors",
    "select_donors",
    "triangulate_donors",
    "parse_mipsmatch_results",
    "mipsmatch_fingerprint",
    "mipsmatch_scan",
    "run_lane",
    "run_upstream_current",
    "run_upstream_pinned",
    "run_upstream_open_pr",
    "run_mipsmatch_exact",
    "run_preserved_candidate",
    "run_shared_header",
    "run_transplant",
    "run_whole_tu",
    "run_dependency_closure",
    "run_multi_donor",
    "run_cfg_dataflow",
    "plan_mipsmatch_fingerprint",
    "current_upstream",
    "pinned_upstream",
    "open_pr_upstream",
    "preserved_candidates",
    "shared_header",
    "transplant_lane",
    "whole_tu_closure",
    "dependency_data_closure",
    "multi_donor",
    "cfg_dataflow_lane",
    "execute_lane",
    "execute_task",
    "run_lanes",
    "execute_lanes",
    "run_deterministic_lanes",
    "deterministic_lanes",
    "mipsmatch_lane",
    "multi_donor_lane",
    "structural_signature_lane",
]
