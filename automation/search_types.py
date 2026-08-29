"""Immutable records shared by the instrumented search core.

The JSON schema is deliberately kept as the source of field names and enum
values.  This module mirrors those fields with strict value objects so that
callers do not have to pass unvalidated dictionaries between search lanes.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple, Type, TypeVar


SCHEMA_VERSION = "1.0.0"
SUBSET_ARTIFACT_TYPE = "sotn-search-subset"
SUBSET_SCHEMA_VERSION = "1.0.0"
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]*$")

LANES = (
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
    "m2c_ensemble",
    "idiom_atlas",
    "bounded_synthesis",
    "permuter_random",
    "permuter_targeted",
    "permuter_recombine",
    "permuter_ddmin",
    "model_fleet",
    "model_expensive",
)

# Each lane receipt names this exact manifest tool key.  Keeping the mapping
# explicit prevents a receipt from inheriting unrelated tools such as the full
# oracle or pattern-report producer.
LANE_TOOL_KEYS = MappingProxyType({lane: (lane,) for lane in LANES})
TIERS = (
    "exact_deterministic",
    "structural_dependency",
    "cheap_generated",
    "compiler_guided",
    "model",
)
TIER_ORDER = TIERS
EVENT_TYPES = (
    "run_started",
    "task_scheduled",
    "task_started",
    "mutation_materialized",
    "candidate_materialized",
    "evaluation_completed",
    "archive_decided",
    "oracle_requested",
    "oracle_result_recorded",
    "task_completed",
    "task_interrupted",
    "checkpoint_committed",
    "exhaustion_recorded",
    "run_stopped",
    "run_resumed",
)
SCORE_FIELDS = ("stack", "regalloc", "reordering", "insertion", "deletion")


class SearchValidationError(ValueError):
    """Raised when a value does not conform to the search schema."""


T = TypeVar("T")


def _strict_dict(
    value: Mapping[str, Any],
    required: Iterable[str],
    allowed: Iterable[str],
    label: str,
) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SearchValidationError(f"{label} must be an object")
    required_set = set(required)
    allowed_set = set(allowed)
    missing = required_set.difference(value)
    unknown = set(value).difference(allowed_set)
    if missing:
        raise SearchValidationError(
            f"{label} is missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise SearchValidationError(
            f"{label} has unknown fields: {', '.join(sorted(unknown))}"
        )
    return dict(value)


def _integer(value: Any, label: str, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SearchValidationError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise SearchValidationError(f"{label} must be at least {minimum}")
    return value


def validate_hash(value: Any, label: str = "hash") -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise SearchValidationError(f"{label} must be a sha256 hash")
    return value


def validate_id(value: Any, label: str = "id") -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise SearchValidationError(f"{label} must be a nonempty identifier")
    if not ID_RE.fullmatch(value):
        raise SearchValidationError(f"{label} contains invalid characters")
    return value


def validate_lane(value: Any) -> str:
    if value not in LANES:
        raise SearchValidationError(f"unknown lane: {value!r}")
    return str(value)


def validate_tier(value: Any) -> str:
    if value not in TIERS:
        raise SearchValidationError(f"unknown tier: {value!r}")
    return str(value)


def validate_relative_path(value: Any, label: str = "path") -> str:
    if not isinstance(value, str) or not value:
        raise SearchValidationError(f"{label} must be a nonempty relative path")
    if value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", value):
        raise SearchValidationError(f"{label} must be relative")
    parts = value.replace("\\", "/").split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise SearchValidationError(f"{label} contains traversal")
    return value


def _unique_tuple(values: Iterable[T], label: str, minimum: int = 0) -> Tuple[T, ...]:
    result = tuple(values)
    if len(result) < minimum:
        raise SearchValidationError(f"{label} must contain at least {minimum} item(s)")
    if len(set(result)) != len(result):
        raise SearchValidationError(f"{label} must not contain duplicates")
    return result


def _frozen_map(value: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SearchValidationError(f"{label} must be an object")
    return MappingProxyType(dict(value))


def _frozen_json(value: Any, label: str) -> Any:
    """Freeze JSON-shaped oracle results, including nested containers."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise SearchValidationError(f"{label} keys must be strings")
        return MappingProxyType({
            key: _frozen_json(item, label)
            for key, item in value.items()
        })
    if isinstance(value, (tuple, list)):
        return tuple(_frozen_json(item, label) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise SearchValidationError(f"{label} must contain JSON values")


def _plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if dataclasses.is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in dataclasses.fields(value)}
    return value


def canonical_json(value: Any) -> str:
    """Serialize a record with stable UTF-8 JSON semantics."""
    return json.dumps(
        _plain(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def hash_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def hash_canonical(value: Any) -> str:
    return hash_bytes(canonical_bytes(value))


def canonical_subset_payload(record_ids: Sequence[str]) -> Dict[str, Any]:
    """Return the canonical selection-only frozen subset payload."""
    if isinstance(record_ids, (str, bytes, bytearray)):
        raise SearchValidationError("record_ids must be a sequence of identifiers")
    try:
        raw_ids = tuple(record_ids)
    except TypeError as exc:
        raise SearchValidationError("record_ids must be a sequence of identifiers") from exc
    for record_id in raw_ids:
        validate_id(record_id, "record_id")
    normalized = tuple(sorted(_unique_tuple(raw_ids, "record_ids")))
    return {
        "artifact_type": SUBSET_ARTIFACT_TYPE,
        "record_ids": list(normalized),
        "schema_version": SUBSET_SCHEMA_VERSION,
    }


def canonical_subset_identity(record_ids: Sequence[str]) -> str:
    """Return the immutable identity of the canonical record ID subset."""
    return hash_canonical(canonical_subset_payload(record_ids))


class _Record:
    def to_dict(self) -> Dict[str, Any]:
        return {
            field.name: _plain(getattr(self, field.name))
            for field in dataclasses.fields(self)
        }

    def to_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_json(cls: Type[T], text: str) -> T:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SearchValidationError(f"invalid JSON for {cls.__name__}") from exc
        return cls.from_dict(value)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ArtifactRef(_Record):
    content_hash: str
    path: str
    media_type: str
    byte_size: int

    def __post_init__(self) -> None:
        validate_hash(self.content_hash, "content_hash")
        validate_relative_path(self.path)
        if not isinstance(self.media_type, str) or not self.media_type:
            raise SearchValidationError("media_type must be nonempty")
        _integer(self.byte_size, "byte_size", 0)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArtifactRef":
        data = _strict_dict(
            value,
            ("content_hash", "path", "media_type", "byte_size"),
            ("content_hash", "path", "media_type", "byte_size"),
            "artifact_ref",
        )
        return cls(**data)


def oracle_request_identity(
    *,
    task_id: str,
    recipient_id: str,
    candidate_id: str,
    source_hash: str,
    config_identity: str,
    oracle_identity: str,
) -> str:
    """Return the stable identity of one score-zero oracle handoff."""
    return hash_canonical(
        {
            "protocol": "oracle-v1",
            "task_id": task_id,
            "recipient_id": recipient_id,
            "candidate_id": candidate_id,
            "source_hash": source_hash,
            "config_identity": config_identity,
            "oracle_identity": oracle_identity,
        }
    )


def oracle_receipt_identity(
    *,
    request_id: str,
    oracle_identity: str,
    outcome: str,
    result: Mapping[str, Any],
) -> str:
    """Return the immutable identity of one oracle result."""
    return hash_canonical(
        {
            "protocol": "oracle-v1",
            "request_id": request_id,
            "oracle_identity": oracle_identity,
            "outcome": outcome,
            "result": _plain(result),
        }
    )


@dataclass(frozen=True)
class OracleRequest(_Record):
    """Durable request materialized before an external oracle invocation."""

    request_id: str
    task_id: str
    recipient_id: str
    candidate_id: str
    source_hash: str
    candidate: "CandidateRecord"
    config_identity: str
    oracle_identity: str
    request_artifact: ArtifactRef

    def __post_init__(self) -> None:
        validate_hash(self.request_id, "request_id")
        validate_id(self.task_id, "task_id")
        validate_id(self.recipient_id, "recipient_id")
        validate_hash(self.candidate_id, "candidate_id")
        validate_hash(self.source_hash, "source_hash")
        if not isinstance(self.candidate, CandidateRecord):
            object.__setattr__(
                self,
                "candidate",
                CandidateRecord.from_dict(self.candidate),  # type: ignore[arg-type]
            )
        if self.candidate.candidate_id != self.candidate_id:
            raise SearchValidationError("oracle request candidate identity differs")
        if self.candidate.recipient_id != self.recipient_id:
            raise SearchValidationError("oracle request candidate recipient differs")
        if self.candidate.source_artifact.content_hash != self.source_hash:
            raise SearchValidationError("oracle request source identity differs")
        validate_hash(self.config_identity, "config_identity")
        validate_hash(self.oracle_identity, "oracle_identity")
        if not isinstance(self.request_artifact, ArtifactRef):
            object.__setattr__(
                self,
                "request_artifact",
                ArtifactRef.from_dict(self.request_artifact),  # type: ignore[arg-type]
            )
        expected = oracle_request_identity(
            task_id=self.task_id,
            recipient_id=self.recipient_id,
            candidate_id=self.candidate_id,
            source_hash=self.source_hash,
            config_identity=self.config_identity,
            oracle_identity=self.oracle_identity,
        )
        if self.request_id != expected:
            raise SearchValidationError("request_id does not match oracle request identity")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OracleRequest":
        fields = (
            "request_id", "task_id", "recipient_id", "candidate_id", "source_hash",
            "candidate", "config_identity", "oracle_identity", "request_artifact",
        )
        data = _strict_dict(value, fields, fields, "oracle_request")
        data["candidate"] = CandidateRecord.from_dict(data["candidate"])
        data["request_artifact"] = ArtifactRef.from_dict(data["request_artifact"])
        return cls(**data)


@dataclass(frozen=True)
class OracleReceipt(_Record):
    """Immutable durable result returned for one oracle request."""

    receipt_id: str
    request_id: str
    oracle_identity: str
    outcome: str
    result: Mapping[str, Any]
    result_artifact: ArtifactRef

    def __post_init__(self) -> None:
        validate_hash(self.receipt_id, "receipt_id")
        validate_hash(self.request_id, "request_id")
        validate_hash(self.oracle_identity, "oracle_identity")
        if self.outcome not in ("matched", "not_matched", "error"):
            raise SearchValidationError("invalid oracle outcome")
        result = _frozen_json(self.result, "oracle result")
        if not isinstance(result, Mapping):
            raise SearchValidationError("oracle result must be an object")
        object.__setattr__(self, "result", result)
        if not isinstance(self.result_artifact, ArtifactRef):
            object.__setattr__(
                self,
                "result_artifact",
                ArtifactRef.from_dict(self.result_artifact),  # type: ignore[arg-type]
            )
        expected = oracle_receipt_identity(
            request_id=self.request_id,
            oracle_identity=self.oracle_identity,
            outcome=self.outcome,
            result=result,
        )
        if self.receipt_id != expected:
            raise SearchValidationError("receipt_id does not match oracle result identity")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OracleReceipt":
        fields = (
            "receipt_id", "request_id", "oracle_identity", "outcome", "result",
            "result_artifact",
        )
        data = _strict_dict(value, fields, fields, "oracle_receipt")
        data["result_artifact"] = ArtifactRef.from_dict(data["result_artifact"])
        return cls(**data)


@dataclass(frozen=True)
class ScoreComponents(_Record):
    stack: int
    regalloc: int
    reordering: int
    insertion: int
    deletion: int

    def __post_init__(self) -> None:
        for name in SCORE_FIELDS:
            _integer(getattr(self, name), f"components.{name}", 0)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScoreComponents":
        data = _strict_dict(value, SCORE_FIELDS, SCORE_FIELDS, "score_components")
        return cls(**data)

    def as_tuple(self) -> Tuple[int, int, int, int, int]:
        return tuple(getattr(self, name) for name in SCORE_FIELDS)  # type: ignore[return-value]

    def weighted_total(self, weights: "ScoreComponents") -> int:
        return sum(a * b for a, b in zip(self.as_tuple(), weights.as_tuple()))


@dataclass(frozen=True)
class FirstDivergence(_Record):
    target_index: int
    candidate_index: int
    target_instruction: Optional[str] = None
    candidate_instruction: Optional[str] = None

    def __post_init__(self) -> None:
        _integer(self.target_index, "target_index", 0)
        _integer(self.candidate_index, "candidate_index", 0)
        if self.target_instruction is not None and not isinstance(self.target_instruction, str):
            raise SearchValidationError("target_instruction must be a string or null")
        if self.candidate_instruction is not None and not isinstance(self.candidate_instruction, str):
            raise SearchValidationError("candidate_instruction must be a string or null")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FirstDivergence":
        data = _strict_dict(
            value,
            ("target_index", "candidate_index"),
            ("target_index", "candidate_index", "target_instruction", "candidate_instruction"),
            "first_divergence",
        )
        data.setdefault("target_instruction", None)
        data.setdefault("candidate_instruction", None)
        return cls(**data)


@dataclass(frozen=True)
class ScoreVector(_Record):
    compile_status: str
    elapsed_ms: int
    total: Optional[int]
    components: ScoreComponents
    weights: ScoreComponents
    object_hash: Optional[str]
    mismatch_signature: Optional[str]
    first_divergence: Optional[FirstDivergence]
    target_instruction_count: Optional[int]
    candidate_instruction_count: Optional[int]
    diagnostic_artifact: Optional[ArtifactRef]
    scorer_algorithm: str
    compiler_identity: str

    def __post_init__(self) -> None:
        if self.compile_status not in ("success", "failed", "timeout"):
            raise SearchValidationError("invalid compile_status")
        _integer(self.elapsed_ms, "elapsed_ms", 0)
        components = self.components
        if not isinstance(components, ScoreComponents):
            components = ScoreComponents.from_dict(components)  # type: ignore[arg-type]
            object.__setattr__(self, "components", components)
        weights = self.weights
        if not isinstance(weights, ScoreComponents):
            weights = ScoreComponents.from_dict(weights)  # type: ignore[arg-type]
            object.__setattr__(self, "weights", weights)
        if self.first_divergence is not None and not isinstance(self.first_divergence, FirstDivergence):
            object.__setattr__(self, "first_divergence", FirstDivergence.from_dict(self.first_divergence))  # type: ignore[arg-type]
        if self.diagnostic_artifact is not None and not isinstance(self.diagnostic_artifact, ArtifactRef):
            object.__setattr__(self, "diagnostic_artifact", ArtifactRef.from_dict(self.diagnostic_artifact))  # type: ignore[arg-type]
        if self.object_hash is not None:
            validate_hash(self.object_hash, "object_hash")
        if self.mismatch_signature is not None:
            validate_hash(self.mismatch_signature, "mismatch_signature")
        validate_hash(self.compiler_identity, "compiler_identity")
        if self.scorer_algorithm not in ("difflib", "levenshtein"):
            raise SearchValidationError("invalid scorer_algorithm")
        if self.compile_status == "success":
            if self.total is None or isinstance(self.total, bool):
                raise SearchValidationError("successful score must have a total")
            _integer(self.total, "total", 0)
            if self.object_hash is None or self.mismatch_signature is None:
                raise SearchValidationError("successful score must have hashes")
            if self.target_instruction_count is None or self.candidate_instruction_count is None:
                raise SearchValidationError("successful score must have instruction counts")
            _integer(self.target_instruction_count, "target_instruction_count", 0)
            _integer(self.candidate_instruction_count, "candidate_instruction_count", 0)
        else:
            if self.total is not None or self.object_hash is not None or self.mismatch_signature is not None:
                raise SearchValidationError("failed score cannot carry evaluated values")
            if self.target_instruction_count is not None:
                _integer(self.target_instruction_count, "target_instruction_count", 0)
            if self.candidate_instruction_count is not None:
                _integer(self.candidate_instruction_count, "candidate_instruction_count", 0)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScoreVector":
        fields = (
            "compile_status", "elapsed_ms", "total", "components", "weights",
            "object_hash", "mismatch_signature", "first_divergence",
            "target_instruction_count", "candidate_instruction_count",
            "diagnostic_artifact", "scorer_algorithm", "compiler_identity",
        )
        data = _strict_dict(value, fields, fields, "score_vector")
        data["components"] = ScoreComponents.from_dict(data["components"])
        data["weights"] = ScoreComponents.from_dict(data["weights"])
        if data["first_divergence"] is not None:
            data["first_divergence"] = FirstDivergence.from_dict(data["first_divergence"])
        if data["diagnostic_artifact"] is not None:
            data["diagnostic_artifact"] = ArtifactRef.from_dict(data["diagnostic_artifact"])
        return cls(**data)


@dataclass(frozen=True)
class PatchHunk(_Record):
    ordinal: int
    before: str
    after: str
    leading_context: Tuple[str, ...]
    trailing_context: Tuple[str, ...]
    ast_path: Optional[str] = None

    def __post_init__(self) -> None:
        _integer(self.ordinal, "ordinal", 0)
        if not isinstance(self.before, str) or not isinstance(self.after, str):
            raise SearchValidationError("patch text must be strings")
        object.__setattr__(self, "leading_context", tuple(self.leading_context))
        object.__setattr__(self, "trailing_context", tuple(self.trailing_context))
        if len(self.leading_context) > 16 or len(self.trailing_context) > 16:
            raise SearchValidationError("patch context is limited to 16 lines")
        if any(not isinstance(item, str) for item in self.leading_context + self.trailing_context):
            raise SearchValidationError("patch context must contain strings")
        if self.ast_path is not None and not isinstance(self.ast_path, str):
            raise SearchValidationError("ast_path must be a string or null")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PatchHunk":
        fields = ("ordinal", "before", "after", "leading_context", "trailing_context", "ast_path")
        data = _strict_dict(value, fields[:-1], fields, "patch_hunk")
        data.setdefault("ast_path", None)
        return cls(**data)


@dataclass(frozen=True)
class GroupedPatch(_Record):
    patch_id: str
    format: str
    base_source_hash: str
    atomic: bool
    hunks: Tuple[PatchHunk, ...]

    def __post_init__(self) -> None:
        validate_hash(self.patch_id, "patch_id")
        validate_hash(self.base_source_hash, "base_source_hash")
        if self.format not in ("canonical_tokens", "ast", "line_context"):
            raise SearchValidationError("invalid grouped patch format")
        if self.atomic is not True:
            raise SearchValidationError("grouped patches must be atomic")
        hunks = tuple(
            item if isinstance(item, PatchHunk) else PatchHunk.from_dict(item)  # type: ignore[arg-type]
            for item in self.hunks
        )
        if not hunks:
            raise SearchValidationError("grouped patch must contain a hunk")
        ordinals = [item.ordinal for item in hunks]
        if len(set(ordinals)) != len(ordinals):
            raise SearchValidationError("patch hunk ordinals must be unique")
        object.__setattr__(self, "hunks", hunks)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GroupedPatch":
        fields = ("patch_id", "format", "base_source_hash", "atomic", "hunks")
        data = _strict_dict(value, fields, fields, "grouped_patch")
        data["hunks"] = tuple(PatchHunk.from_dict(item) for item in data["hunks"])
        return cls(**data)


@dataclass(frozen=True)
class MutationEvent(_Record):
    mutation_id: str
    parent_candidate_id: str
    recipient_id: str
    lane: str
    pass_kind: str
    mutation_seed: int
    grouped_patch: GroupedPatch
    donor_candidate_ids: Tuple[str, ...]
    replay_status: str
    result_source_hash: Optional[str]

    def __post_init__(self) -> None:
        validate_hash(self.mutation_id, "mutation_id")
        validate_hash(self.parent_candidate_id, "parent_candidate_id")
        validate_id(self.recipient_id, "recipient_id")
        validate_lane(self.lane)
        if not isinstance(self.pass_kind, str) or not self.pass_kind:
            raise SearchValidationError("pass_kind must be nonempty")
        _integer(self.mutation_seed, "mutation_seed", 0)
        if not isinstance(self.grouped_patch, GroupedPatch):
            object.__setattr__(self, "grouped_patch", GroupedPatch.from_dict(self.grouped_patch))  # type: ignore[arg-type]
        donors = _unique_tuple(self.donor_candidate_ids, "donor_candidate_ids")
        for donor in donors:
            validate_hash(donor, "donor_candidate_id")
        object.__setattr__(self, "donor_candidate_ids", donors)
        if self.replay_status not in ("applied", "conflict", "invalid", "no_change"):
            raise SearchValidationError("invalid replay_status")
        if self.replay_status == "applied":
            if self.result_source_hash is None:
                raise SearchValidationError("applied mutation needs result_source_hash")
            validate_hash(self.result_source_hash, "result_source_hash")
        elif self.result_source_hash is not None:
            raise SearchValidationError("rejected mutation cannot carry result_source_hash")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MutationEvent":
        fields = (
            "mutation_id", "parent_candidate_id", "recipient_id", "lane",
            "pass_kind", "mutation_seed", "grouped_patch", "donor_candidate_ids",
            "replay_status", "result_source_hash",
        )
        data = _strict_dict(value, fields, fields, "mutation_event")
        data["grouped_patch"] = GroupedPatch.from_dict(data["grouped_patch"])
        return cls(**data)


@dataclass(frozen=True)
class ParentRun(_Record):
    run_id: str
    last_valid_sequence: int
    last_valid_event_hash: str

    def __post_init__(self) -> None:
        validate_id(self.run_id, "parent_run.run_id")
        _integer(self.last_valid_sequence, "last_valid_sequence", 0)
        validate_hash(self.last_valid_event_hash, "last_valid_event_hash")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ParentRun":
        fields = ("run_id", "last_valid_sequence", "last_valid_event_hash")
        return cls(**_strict_dict(value, fields, fields, "parent_run"))


@dataclass(frozen=True)
class RunManifest(_Record):
    run_id: str
    created_at: str
    parent_run: Optional[ParentRun]
    queue_record_ids: Tuple[str, ...]
    function_ids: Tuple[str, ...]
    subset_identity: str
    queue_evidence_identity: str
    selected_lanes: Tuple[str, ...]
    source_identity: str
    target_identities: Mapping[str, str]
    compiler_identity: str
    tool_identities: Mapping[str, str]
    config_identity: str
    schema_identity: str
    run_seed: int
    epoch_size: int
    frontier_cap: int
    # These budgets are part of the immutable run identity.  Budget.consumed
    # is deliberately zero in a manifest; consumption is reconstructed from
    # ledger events rather than drifting in process-local state.
    coordinator_budget: "Budget"
    lane_budgets: Mapping[str, "Budget"]
    tier_order: Tuple[str, ...]

    def __post_init__(self) -> None:
        validate_id(self.run_id, "run_id")
        if not isinstance(self.created_at, str):
            raise SearchValidationError("created_at must be a string")
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SearchValidationError("created_at must be an ISO date-time") from exc
        if self.parent_run is not None and not isinstance(self.parent_run, ParentRun):
            object.__setattr__(self, "parent_run", ParentRun.from_dict(self.parent_run))  # type: ignore[arg-type]
        # Queue and function subsets use the same sorted form as the CLI
        # subset artifact, so argv or JSON ordering cannot fork run identity.
        queue_ids = tuple(sorted(_unique_tuple(self.queue_record_ids, "queue_record_ids")))
        function_ids = tuple(sorted(_unique_tuple(self.function_ids, "function_ids")))
        if bool(queue_ids) != bool(function_ids):
            raise SearchValidationError(
                "queue_record_ids and function_ids must be empty or nonempty together"
            )
        for item in queue_ids:
            validate_id(item, "queue_record_id")
        for item in function_ids:
            validate_id(item, "function_id")
        object.__setattr__(self, "queue_record_ids", queue_ids)
        object.__setattr__(self, "function_ids", function_ids)
        validate_hash(self.subset_identity, "subset_identity")
        expected_subset_identity = canonical_subset_identity(queue_ids)
        if self.subset_identity != expected_subset_identity:
            raise SearchValidationError(
                "subset_identity does not match the canonical frozen subset"
            )
        validate_hash(self.queue_evidence_identity, "queue_evidence_identity")

        selected_lanes = _unique_tuple(self.selected_lanes, "selected_lanes")
        for lane in selected_lanes:
            validate_lane(lane)
        canonical_selected = tuple(lane for lane in LANES if lane in selected_lanes)
        if selected_lanes != canonical_selected:
            raise SearchValidationError(
                "selected_lanes must use canonical LANES order"
            )
        if queue_ids and not selected_lanes:
            raise SearchValidationError(
                "nonempty queue_record_ids require at least one selected lane"
            )
        object.__setattr__(self, "selected_lanes", selected_lanes)

        validate_hash(self.source_identity, "source_identity")
        validate_hash(self.compiler_identity, "compiler_identity")
        validate_hash(self.config_identity, "config_identity")
        validate_hash(self.schema_identity, "schema_identity")
        target = _frozen_map(self.target_identities, "target_identities")
        tools = _frozen_map(self.tool_identities, "tool_identities")
        if (queue_ids and not target) or not tools:
            raise SearchValidationError(
                "target_identities must be nonempty for a nonempty subset and "
                "tool_identities must never be empty"
            )
        if set(target) != set(queue_ids):
            raise SearchValidationError(
                "target_identities must correspond exactly to queue_record_ids"
            )
        for key, value in target.items():
            validate_id(key, "target identity key")
            validate_hash(value, "target identity")
        for key, value in tools.items():
            validate_id(key, "tool identity key")
            validate_hash(value, "tool identity")
        missing_lane_tools = {
            lane: tuple(
                key for key in LANE_TOOL_KEYS[lane]
                if key not in tools
            )
            for lane in selected_lanes
            if any(key not in tools for key in LANE_TOOL_KEYS[lane])
        }
        if missing_lane_tools:
            detail = "; ".join(
                lane + ": " + ", ".join(keys)
                for lane, keys in sorted(missing_lane_tools.items())
            )
            raise SearchValidationError(
                "tool_identities is missing selected lane binding(s): " + detail
            )
        object.__setattr__(self, "target_identities", target)
        object.__setattr__(self, "tool_identities", tools)
        _integer(self.run_seed, "run_seed", 0)
        _integer(self.epoch_size, "epoch_size", 1)
        if self.epoch_size > 4096:
            raise SearchValidationError("epoch_size exceeds schema maximum")
        _integer(self.frontier_cap, "frontier_cap", 1)
        if self.frontier_cap > 1024:
            raise SearchValidationError("frontier_cap exceeds schema maximum")

        coordinator_budget = self.coordinator_budget
        if not isinstance(coordinator_budget, Budget):
            coordinator_budget = Budget.from_dict(coordinator_budget)
            object.__setattr__(self, "coordinator_budget", coordinator_budget)
        if coordinator_budget.unit != "tasks":
            raise SearchValidationError("coordinator_budget.unit must be tasks")
        if coordinator_budget.consumed != 0:
            raise SearchValidationError("coordinator_budget.consumed must be zero in a manifest")

        if not isinstance(self.lane_budgets, Mapping):
            raise SearchValidationError("lane_budgets must be an object")
        lane_budgets = dict(self.lane_budgets)
        expected_lanes = set(self.selected_lanes)
        actual_lanes = set(lane_budgets)
        missing_lanes = expected_lanes.difference(actual_lanes)
        unknown_lanes = actual_lanes.difference(expected_lanes)
        if missing_lanes or unknown_lanes:
            details = []
            if missing_lanes:
                details.append("missing lanes: " + ", ".join(sorted(missing_lanes)))
            if unknown_lanes:
                details.append("unknown or unselected lanes: " + ", ".join(sorted(unknown_lanes)))
            raise SearchValidationError("lane_budgets must define exactly selected_lanes (" + "; ".join(details) + ")")
        normalized_lane_budgets = {}
        for lane in self.selected_lanes:
            try:
                budget = lane_budgets[lane]
                if not isinstance(budget, Budget):
                    budget = Budget.from_dict(budget)
            except (KeyError, TypeError, ValueError) as exc:
                raise SearchValidationError("lane_budgets contains an invalid budget for " + str(lane)) from exc
            if budget.consumed != 0:
                raise SearchValidationError(
                    "lane_budgets." + lane + ".consumed must be zero in a manifest"
                )
            normalized_lane_budgets[lane] = budget
        object.__setattr__(
            self,
            "lane_budgets",
            MappingProxyType(normalized_lane_budgets),
        )

        tier_order = tuple(self.tier_order)
        if tier_order != TIER_ORDER:
            raise SearchValidationError("tier_order must be the canonical five-tier order")
        object.__setattr__(self, "tier_order", tier_order)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunManifest":
        fields = (
            "run_id", "created_at", "parent_run", "queue_record_ids", "function_ids",
            "subset_identity", "queue_evidence_identity", "selected_lanes", "source_identity", "target_identities", "compiler_identity",
            "tool_identities", "config_identity", "schema_identity", "run_seed",
            "epoch_size", "frontier_cap", "coordinator_budget", "lane_budgets",
            "tier_order",
        )
        data = _strict_dict(value, fields, fields, "run_manifest")
        if data["parent_run"] is not None:
            data["parent_run"] = ParentRun.from_dict(data["parent_run"])
        return cls(**data)


@dataclass(frozen=True)
class SearchTask(_Record):
    task_id: str
    recipient_id: str
    lane: str
    tier: str
    operation: str
    parent_candidate_ids: Tuple[str, ...]
    budget_ordinal: int
    task_seed: int
    config_identity: str
    state: str

    def __post_init__(self) -> None:
        validate_id(self.task_id, "task_id")
        validate_id(self.recipient_id, "recipient_id")
        validate_lane(self.lane)
        validate_tier(self.tier)
        if not isinstance(self.operation, str) or not self.operation:
            raise SearchValidationError("operation must be nonempty")
        parents = _unique_tuple(self.parent_candidate_ids, "parent_candidate_ids")
        for item in parents:
            validate_hash(item, "parent_candidate_id")
        object.__setattr__(self, "parent_candidate_ids", parents)
        _integer(self.budget_ordinal, "budget_ordinal", 0)
        _integer(self.task_seed, "task_seed", 0)
        validate_hash(self.config_identity, "config_identity")
        if self.state not in ("scheduled", "started", "completed", "rejected", "interrupted"):
            raise SearchValidationError("invalid task state")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SearchTask":
        fields = (
            "task_id", "recipient_id", "lane", "tier", "operation",
            "parent_candidate_ids", "budget_ordinal", "task_seed",
            "config_identity", "state",
        )
        return cls(**_strict_dict(value, fields, fields, "search_task"))


@dataclass(frozen=True)
class CandidateRecord(_Record):
    candidate_id: str
    recipient_id: str
    source_artifact: ArtifactRef
    parent_candidate_ids: Tuple[str, ...]
    mutation_id: Optional[str]
    lane: str
    depth: int
    evaluation: Optional[ScoreVector]
    status: str

    def __post_init__(self) -> None:
        validate_hash(self.candidate_id, "candidate_id")
        validate_id(self.recipient_id, "recipient_id")
        if not isinstance(self.source_artifact, ArtifactRef):
            object.__setattr__(self, "source_artifact", ArtifactRef.from_dict(self.source_artifact))  # type: ignore[arg-type]
        if self.candidate_id != self.source_artifact.content_hash:
            raise SearchValidationError("candidate_id must equal source_artifact.content_hash")
        parents = _unique_tuple(self.parent_candidate_ids, "parent_candidate_ids")
        for item in parents:
            validate_hash(item, "parent_candidate_id")
        object.__setattr__(self, "parent_candidate_ids", parents)
        if self.mutation_id is not None:
            validate_hash(self.mutation_id, "mutation_id")
        validate_lane(self.lane)
        _integer(self.depth, "depth", 0)
        if self.evaluation is not None and not isinstance(self.evaluation, ScoreVector):
            object.__setattr__(self, "evaluation", ScoreVector.from_dict(self.evaluation))  # type: ignore[arg-type]
        if self.status not in (
            "materialized", "evaluated", "scalar_elite", "pareto", "dominated",
            "rejected", "zero_pending_oracle", "archived",
        ):
            raise SearchValidationError("invalid candidate status")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CandidateRecord":
        fields = (
            "candidate_id", "recipient_id", "source_artifact", "parent_candidate_ids",
            "mutation_id", "lane", "depth", "evaluation", "status",
        )
        data = _strict_dict(value, fields, fields, "candidate_record")
        data["source_artifact"] = ArtifactRef.from_dict(data["source_artifact"])
        if data["evaluation"] is not None:
            data["evaluation"] = ScoreVector.from_dict(data["evaluation"])
        return cls(**data)


@dataclass(frozen=True)
class ScoreDeltas(_Record):
    total: Optional[int]
    stack: int
    regalloc: int
    reordering: int
    insertion: int
    deletion: int

    def __post_init__(self) -> None:
        if self.total is not None:
            _integer(self.total, "deltas.total")
        for name in SCORE_FIELDS:
            _integer(getattr(self, name), f"deltas.{name}")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScoreDeltas":
        fields = ("total",) + SCORE_FIELDS
        return cls(**_strict_dict(value, fields, fields, "score_deltas"))


@dataclass(frozen=True)
class EvaluationEvent(_Record):
    task_id: str
    recipient_id: str
    candidate_id: str
    baseline_candidate_id: Optional[str]
    before: Optional[ScoreVector]
    after: ScoreVector
    deltas: ScoreDeltas
    cache_key: str
    decision: str

    def __post_init__(self) -> None:
        validate_id(self.task_id, "task_id")
        validate_id(self.recipient_id, "recipient_id")
        validate_hash(self.candidate_id, "candidate_id")
        if self.baseline_candidate_id is not None:
            validate_hash(self.baseline_candidate_id, "baseline_candidate_id")
        if self.before is not None and not isinstance(self.before, ScoreVector):
            object.__setattr__(self, "before", ScoreVector.from_dict(self.before))  # type: ignore[arg-type]
        if not isinstance(self.after, ScoreVector):
            object.__setattr__(self, "after", ScoreVector.from_dict(self.after))  # type: ignore[arg-type]
        if not isinstance(self.deltas, ScoreDeltas):
            object.__setattr__(self, "deltas", ScoreDeltas.from_dict(self.deltas))  # type: ignore[arg-type]
        validate_hash(self.cache_key, "cache_key")
        if self.decision not in (
            "scalar_elite", "pareto", "dominated", "compile_failed", "rejected", "zero_pending_oracle",
        ):
            raise SearchValidationError("invalid evaluation decision")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvaluationEvent":
        fields = (
            "task_id", "recipient_id", "candidate_id", "baseline_candidate_id",
            "before", "after", "deltas", "cache_key", "decision",
        )
        data = _strict_dict(value, fields, fields, "evaluation_event")
        if data["before"] is not None:
            data["before"] = ScoreVector.from_dict(data["before"])
        data["after"] = ScoreVector.from_dict(data["after"])
        data["deltas"] = ScoreDeltas.from_dict(data["deltas"])
        return cls(**data)


@dataclass(frozen=True)
class ArchiveDecision(_Record):
    candidate_id: str
    recipient_id: str
    decision: str
    scalar_elite_candidate_id: str
    pareto_candidate_ids: Tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        validate_hash(self.candidate_id, "candidate_id")
        validate_id(self.recipient_id, "recipient_id")
        if self.decision not in (
            "retain_scalar_elite", "retain_pareto", "retain_both", "archive_dominated", "reject",
        ):
            raise SearchValidationError("invalid archive decision")
        validate_hash(self.scalar_elite_candidate_id, "scalar_elite_candidate_id")
        ids = _unique_tuple(self.pareto_candidate_ids, "pareto_candidate_ids")
        for item in ids:
            validate_hash(item, "pareto_candidate_id")
        object.__setattr__(self, "pareto_candidate_ids", ids)
        if not isinstance(self.reason, str) or not self.reason:
            raise SearchValidationError("archive reason must be nonempty")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArchiveDecision":
        fields = (
            "candidate_id", "recipient_id", "decision", "scalar_elite_candidate_id",
            "pareto_candidate_ids", "reason",
        )
        return cls(**_strict_dict(value, fields, fields, "archive_decision"))


@dataclass(frozen=True)
class TaskTerminal(_Record):
    task_id: str
    state: str
    result_artifacts: Tuple[ArtifactRef, ...]
    reason: str

    def __post_init__(self) -> None:
        validate_id(self.task_id, "task_id")
        if self.state not in ("completed", "rejected"):
            raise SearchValidationError("invalid terminal task state")
        artifacts = tuple(
            item if isinstance(item, ArtifactRef) else ArtifactRef.from_dict(item)  # type: ignore[arg-type]
            for item in self.result_artifacts
        )
        object.__setattr__(self, "result_artifacts", artifacts)
        if not isinstance(self.reason, str) or not self.reason:
            raise SearchValidationError("task completion reason must be nonempty")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TaskTerminal":
        fields = ("task_id", "state", "result_artifacts", "reason")
        data = _strict_dict(value, fields, fields, "task_terminal")
        data["result_artifacts"] = tuple(ArtifactRef.from_dict(item) for item in data["result_artifacts"])
        return cls(**data)


@dataclass(frozen=True)
class Interruption(_Record):
    task_id: str
    reason: str
    retry_same_identity: bool

    def __post_init__(self) -> None:
        validate_id(self.task_id, "task_id")
        if not isinstance(self.reason, str) or not self.reason:
            raise SearchValidationError("interruption reason must be nonempty")
        if self.retry_same_identity is not True:
            raise SearchValidationError("interruption must retry the same identity")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Interruption":
        fields = ("task_id", "reason", "retry_same_identity")
        return cls(**_strict_dict(value, fields, fields, "interruption"))


@dataclass(frozen=True)
class Checkpoint(_Record):
    through_sequence: int
    through_event_hash: str
    checkpoint_artifact: ArtifactRef

    def __post_init__(self) -> None:
        _integer(self.through_sequence, "through_sequence", 0)
        validate_hash(self.through_event_hash, "through_event_hash")
        if not isinstance(self.checkpoint_artifact, ArtifactRef):
            object.__setattr__(self, "checkpoint_artifact", ArtifactRef.from_dict(self.checkpoint_artifact))  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Checkpoint":
        fields = ("through_sequence", "through_event_hash", "checkpoint_artifact")
        data = _strict_dict(value, fields, fields, "checkpoint")
        data["checkpoint_artifact"] = ArtifactRef.from_dict(data["checkpoint_artifact"])
        return cls(**data)


@dataclass(frozen=True)
class Budget(_Record):
    unit: str
    limit: int
    consumed: int

    def __post_init__(self) -> None:
        if self.unit not in ("tasks", "attempts", "iterations", "candidates", "seconds"):
            raise SearchValidationError("invalid budget unit")
        _integer(self.limit, "budget.limit", 0)
        _integer(self.consumed, "budget.consumed", 0)
        if self.consumed > self.limit:
            raise SearchValidationError("budget consumed exceeds limit")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Budget":
        fields = ("unit", "limit", "consumed")
        return cls(**_strict_dict(value, fields, fields, "budget"))


@dataclass(frozen=True)
class ExhaustionReceipt(_Record):
    receipt_id: str
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
    complete: bool
    completion_reason: str
    receipt_artifact: ArtifactRef

    def __post_init__(self) -> None:
        validate_hash(self.receipt_id, "receipt_id")
        validate_id(self.recipient_id, "recipient_id")
        validate_lane(self.lane)
        validate_tier(self.tier)
        tools = _frozen_map(self.tool_identities, "tool_identities")
        if not tools:
            raise SearchValidationError("tool_identities must not be empty")
        for key, value in tools.items():
            validate_id(key, "tool identity key")
            validate_hash(value, "tool identity")
        expected_tool_keys = set(LANE_TOOL_KEYS.get(self.lane, ()))
        if set(tools) != expected_tool_keys:
            raise SearchValidationError(
                "tool_identities must exactly match the lane manifest contract"
            )
        object.__setattr__(self, "tool_identities", tools)
        validate_hash(self.config_identity, "config_identity")
        inputs = _unique_tuple(self.input_identities, "input_identities", 1)
        for item in inputs:
            validate_hash(item, "input identity")
        object.__setattr__(self, "input_identities", inputs)
        if not isinstance(self.budget, Budget):
            object.__setattr__(self, "budget", Budget.from_dict(self.budget))  # type: ignore[arg-type]
        _integer(self.attempts, "attempts", 0)
        rejections = _frozen_map(self.rejection_counts, "rejection_counts")
        for key, value in rejections.items():
            if not isinstance(key, str):
                raise SearchValidationError("rejection class must be a string")
            _integer(value, "rejection count", 0)
        object.__setattr__(self, "rejection_counts", rejections)
        best = _unique_tuple(self.best_candidate_ids, "best_candidate_ids")
        for item in best:
            validate_hash(item, "best_candidate_id")
        object.__setattr__(self, "best_candidate_ids", best)
        if self.complete is not True:
            raise SearchValidationError("exhaustion receipt must be complete")
        if self.completion_reason not in (
            "budget_exhausted", "search_space_exhausted", "inapplicable",
            "matched_pending_oracle", "operator_stop", "superseded_by_stronger_evidence",
        ):
            raise SearchValidationError("invalid completion_reason")
        if not isinstance(self.receipt_artifact, ArtifactRef):
            object.__setattr__(self, "receipt_artifact", ArtifactRef.from_dict(self.receipt_artifact))  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExhaustionReceipt":
        fields = (
            "receipt_id", "recipient_id", "lane", "tier", "tool_identities",
            "config_identity", "input_identities", "budget", "attempts",
            "rejection_counts", "best_candidate_ids", "complete", "completion_reason",
            "receipt_artifact",
        )
        data = _strict_dict(value, fields, fields, "exhaustion_receipt")
        data["budget"] = Budget.from_dict(data["budget"])
        data["receipt_artifact"] = ArtifactRef.from_dict(data["receipt_artifact"])
        return cls(**data)


@dataclass(frozen=True)
class RunStop(_Record):
    reason: str
    last_committed_task_id: Optional[str]
    pending_task_ids: Tuple[str, ...]
    budget_snapshot_hash: str
    resumable: bool

    def __post_init__(self) -> None:
        if self.reason not in ("graceful_stop", "completed", "oracle_candidate_found", "fatal_integrity_error"):
            raise SearchValidationError("invalid stop reason")
        if self.last_committed_task_id is not None:
            validate_id(self.last_committed_task_id, "last_committed_task_id")
        pending = _unique_tuple(self.pending_task_ids, "pending_task_ids")
        for item in pending:
            validate_id(item, "pending_task_id")
        object.__setattr__(self, "pending_task_ids", pending)
        validate_hash(self.budget_snapshot_hash, "budget_snapshot_hash")
        if not isinstance(self.resumable, bool):
            raise SearchValidationError("resumable must be boolean")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunStop":
        fields = ("reason", "last_committed_task_id", "pending_task_ids", "budget_snapshot_hash", "resumable")
        return cls(**_strict_dict(value, fields, fields, "run_stop"))


@dataclass(frozen=True)
class RunResume(_Record):
    """Durable transition that clears one resumable stop boundary."""

    stop_event_id: str
    stop_event_hash: str
    request_id: Optional[str]

    def __post_init__(self) -> None:
        validate_id(self.stop_event_id, "stop_event_id")
        validate_hash(self.stop_event_hash, "stop_event_hash")
        if self.request_id is not None:
            validate_hash(self.request_id, "resume request_id")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunResume":
        fields = ("stop_event_id", "stop_event_hash", "request_id")
        return cls(**_strict_dict(value, fields, fields, "run_resume"))


PAYLOAD_TYPES: Dict[str, Type[_Record]] = {
    "run_started": RunManifest,
    "task_scheduled": SearchTask,
    "task_started": SearchTask,
    "mutation_materialized": MutationEvent,
    "candidate_materialized": CandidateRecord,
    "evaluation_completed": EvaluationEvent,
    "archive_decided": ArchiveDecision,
    "oracle_requested": OracleRequest,
    "oracle_result_recorded": OracleReceipt,
    "task_completed": TaskTerminal,
    "task_interrupted": Interruption,
    "checkpoint_committed": Checkpoint,
    "exhaustion_recorded": ExhaustionReceipt,
    "run_stopped": RunStop,
    "run_resumed": RunResume,
}


@dataclass(frozen=True)
class LedgerEvent(_Record):
    schema_version: str
    sequence: int
    event_id: str
    previous_event_hash: Optional[str]
    event_hash: str
    recorded_at: str
    run_id: str
    event_type: str
    payload: _Record

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise SearchValidationError("unsupported schema version")
        _integer(self.sequence, "sequence", 0)
        validate_id(self.event_id, "event_id")
        if self.previous_event_hash is not None:
            validate_hash(self.previous_event_hash, "previous_event_hash")
        validate_hash(self.event_hash, "event_hash")
        if not isinstance(self.recorded_at, str):
            raise SearchValidationError("recorded_at must be a string")
        try:
            datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SearchValidationError("recorded_at must be an ISO date-time") from exc
        validate_id(self.run_id, "run_id")
        if self.event_type not in EVENT_TYPES:
            raise SearchValidationError("unknown event type")
        payload_type = PAYLOAD_TYPES[self.event_type]
        if not isinstance(self.payload, payload_type):
            raise SearchValidationError(f"payload does not match {self.event_type}")
        if self.event_type == "run_started" and self.sequence != 0:
            raise SearchValidationError("run_started must be sequence zero")
        if self.event_type == "run_started" and self.previous_event_hash is not None:
            raise SearchValidationError("run_started cannot have a predecessor")
        if self.event_type == "run_started" and self.payload.run_id != self.run_id:  # type: ignore[attr-defined]
            raise SearchValidationError("run_started payload and envelope run ids differ")
        if self.event_type == "task_scheduled" and self.payload.state != "scheduled":  # type: ignore[attr-defined]
            raise SearchValidationError("task_scheduled payload must be scheduled")
        if self.event_type == "task_started" and self.payload.state != "started":  # type: ignore[attr-defined]
            raise SearchValidationError("task_started payload must be started")

    def without_event_hash(self) -> Dict[str, Any]:
        data = self.to_dict()
        del data["event_hash"]
        return data

    def calculated_hash(self) -> str:
        return hash_canonical(self.without_event_hash())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LedgerEvent":
        fields = (
            "schema_version", "sequence", "event_id", "previous_event_hash",
            "event_hash", "recorded_at", "run_id", "event_type", "payload",
        )
        data = _strict_dict(value, fields, fields, "event")
        event_type = data["event_type"]
        if event_type not in PAYLOAD_TYPES:
            raise SearchValidationError("unknown event type")
        data["payload"] = PAYLOAD_TYPES[event_type].from_dict(data["payload"])  # type: ignore[attr-defined]
        return cls(**data)


def event_payload(event_type: str, value: Any) -> _Record:
    """Coerce a payload to the exact record required by an event variant."""
    payload_type = PAYLOAD_TYPES.get(event_type)
    if payload_type is None:
        raise SearchValidationError(f"unknown event type: {event_type}")
    if isinstance(value, payload_type):
        return value
    return payload_type.from_dict(value)  # type: ignore[attr-defined]


def event_hash_without_hash(event: Mapping[str, Any]) -> str:
    data = dict(event)
    data.pop("event_hash", None)
    return hash_canonical(data)


def iter_artifact_refs(value: Any) -> Tuple[ArtifactRef, ...]:
    """Find all typed artifact references nested in a record or mapping."""
    found = []

    def visit(item: Any) -> None:
        if isinstance(item, ArtifactRef):
            found.append(item)
        elif isinstance(item, Mapping):
            if {"content_hash", "path", "media_type", "byte_size"}.issubset(item):
                found.append(ArtifactRef.from_dict(item))
            else:
                for child in item.values():
                    visit(child)
        elif isinstance(item, (tuple, list)):
            for child in item:
                visit(child)
        elif dataclasses.is_dataclass(item):
            for field in dataclasses.fields(item):
                visit(getattr(item, field.name))

    visit(value)
    return tuple(found)


__all__ = [
    "SCHEMA_VERSION", "SUBSET_ARTIFACT_TYPE", "SUBSET_SCHEMA_VERSION",
    "LANES", "LANE_TOOL_KEYS", "TIERS", "TIER_ORDER", "EVENT_TYPES", "SCORE_FIELDS",
    "SearchValidationError", "ArtifactRef", "ScoreComponents", "FirstDivergence",
    "ScoreVector", "PatchHunk", "GroupedPatch", "MutationEvent", "ParentRun",
    "RunManifest", "SearchTask", "CandidateRecord", "ScoreDeltas", "EvaluationEvent",
    "ArchiveDecision", "OracleRequest", "OracleReceipt", "TaskTerminal", "Interruption",
    "Checkpoint", "Budget", "ExhaustionReceipt", "RunStop", "RunResume", "LedgerEvent", "PAYLOAD_TYPES",
    "event_payload",
    "canonical_json", "canonical_bytes", "hash_bytes", "hash_canonical",
    "canonical_subset_payload", "canonical_subset_identity",
    "oracle_request_identity", "oracle_receipt_identity", "validate_hash",
    "validate_id", "validate_lane", "validate_tier", "validate_relative_path",
    "iter_artifact_refs",
]
