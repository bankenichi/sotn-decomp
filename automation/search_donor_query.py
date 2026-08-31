"""Deterministic, read-only queries over the immutable donor index.

The donor index is deliberately a durable value rather than a scanner service.
This module verifies that durable boundary once, then binds a pure query
closure to the verified generation.  Query results retain the original typed
evidence objects, so callers can cite the index without gaining a provider,
scanner, or filesystem escape hatch.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Optional, Tuple

try:  # package imports
    from .search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive
    from .search_donor_index import (
        DONOR_VERSIONS,
        DonorIndexBinding,
        DonorIndexEntry,
        DonorIndexGeneration,
        DonorIndexError,
    )
    from .search_lanes import DonorEvidence, LaneError
    from .search_supervisor import IntegrationGateError, validate_integration_gate
    from .search_types import (
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )
except ImportError:  # direct invocation from the automation directory
    from automation.search_archive import (  # type: ignore
        ArchiveError,
        ArtifactRef,
        ContentAddressedArchive,
    )
    from automation.search_donor_index import (  # type: ignore
        DONOR_VERSIONS,
        DonorIndexBinding,
        DonorIndexEntry,
        DonorIndexGeneration,
        DonorIndexError,
    )
    from automation.search_lanes import DonorEvidence, LaneError  # type: ignore
    from automation.search_supervisor import (  # type: ignore
        IntegrationGateError,
        validate_integration_gate,
    )
    from automation.search_types import (  # type: ignore
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )


DONOR_QUERY_PROTOCOL = "donor-query-v1"
DONOR_SEMANTIC_CLAIM_PROTOCOL = "donor-semantic-claim-v1"
DONOR_AMBIGUITY_RECEIPT_PROTOCOL = "donor-ambiguity-receipt-v1"
DONOR_INCOMPATIBILITY_RECEIPT_PROTOCOL = "donor-incompatibility-receipt-v1"
DONOR_STALE_RECEIPT_PROTOCOL = "donor-stale-receipt-v1"
_AMBIGUITY_REASON = "conflicting_semantic_claims"
_INCOMPATIBILITY_REASONS = (
    "all structural donor matches are incompatible",
)

MATCH_RANKS = MappingProxyType(
    {
        "exact_symbol_path": 0,
        "instruction_shape": 1,
        "cfg": 2,
        "dataflow": 3,
    }
)
QUERY_STATUSES = frozenset(
    {"matched", "empty", "ambiguous", "incompatible", "stale"}
)


class DonorQueryError(RuntimeError):
    """Base error for donor query binding and typed query values."""


class DonorQueryInputError(DonorQueryError):
    """A donor query value or public result record is malformed."""


class DonorQueryIdentityMismatch(DonorQueryInputError):
    """A query, claim, receipt, or verified binding has the wrong identity."""


class DonorQueryArtifactError(ArchiveError):
    """The durable donor-index artifact is missing, corrupt, or not canonical."""


def _input_error(label: str, exc: BaseException) -> DonorQueryInputError:
    return DonorQueryInputError(f"{label}: {exc}")


def _hash(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise _input_error(label, exc) from exc


def _identity_hash(value: Any, label: str) -> str:
    return _hash(value, label)


def _identifier(value: Any, label: str) -> str:
    try:
        return validate_id(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise _input_error(label, exc) from exc


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise DonorQueryInputError(f"{label} must be a nonempty string")
    return value


def _optional_text(value: Any, label: str) -> Optional[str]:
    if value is None:
        return None
    return _text(value, label)


def _optional_path(value: Any, label: str) -> Optional[str]:
    if value is None:
        return None
    value = _text(value, label)
    try:
        return validate_relative_path(value)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise _input_error(label, exc) from exc


def _freeze_json(value: Any, label: str) -> Any:
    """Deep-freeze JSON data while refusing values canonical JSON cannot trust."""

    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise DonorQueryInputError(f"{label} keys must be strings")
            frozen[key] = _freeze_json(item, f"{label}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(item, f"{label}[{index}]")
            for index, item in enumerate(value)
        )
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DonorQueryInputError(f"{label} must contain finite numbers")
        return value
    raise DonorQueryInputError(f"{label} contains an unsupported value")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DonorQueryInputError(f"{label} must be a mapping")
    return _freeze_json(value, label)


def _strings(value: Any, label: str, *, unique: bool = False) -> Tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise DonorQueryInputError(f"{label} must be an explicit tuple or list")
    result = tuple(_text(item, f"{label}[{index}]") for index, item in enumerate(value))
    if unique and len(set(result)) != len(result):
        raise DonorQueryInputError(f"{label} must not contain duplicates")
    return result


def _hashes(value: Any, label: str) -> Tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise DonorQueryInputError(f"{label} must be an explicit tuple or list")
    result = tuple(_hash(item, f"{label}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise DonorQueryIdentityMismatch(f"{label} must not contain duplicates")
    return tuple(sorted(result))


def _structural_differences(value: Any) -> Tuple[str, ...]:
    return tuple(sorted(set(_strings(value, "structural_differences"))))


def _artifact(value: Any, label: str) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    try:
        return ArtifactRef.from_dict(value)
    except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise _input_error(label, exc) from exc


def _entry(value: Any) -> DonorIndexEntry:
    if isinstance(value, DonorIndexEntry):
        return value
    try:
        return DonorIndexEntry.from_dict(value)
    except (AttributeError, DonorIndexError, LaneError, SearchValidationError, TypeError, ValueError) as exc:
        raise _input_error("entry", exc) from exc


def _evidence(value: Any) -> DonorEvidence:
    if isinstance(value, DonorEvidence):
        return value
    if not isinstance(value, Mapping):
        raise DonorQueryInputError("donor evidence must be a typed record or mapping")
    data = dict(value)
    if "source" in data and not isinstance(data["source"], ArtifactRef):
        data["source"] = _artifact(data["source"], "evidence.source")
    try:
        return DonorEvidence(**data)
    except (AttributeError, LaneError, SearchValidationError, TypeError, ValueError) as exc:
        raise _input_error("evidence", exc) from exc


def _binding(value: Any, label: str) -> DonorIndexBinding:
    if isinstance(value, DonorIndexBinding):
        typed = value
    else:
        try:
            typed = DonorIndexBinding.from_dict(value)
        except (AttributeError, DonorIndexError, IntegrationGateError, SearchValidationError, TypeError, ValueError) as exc:
            raise _input_error(label, exc) from exc
    try:
        canonical = DonorIndexBinding.from_dict(typed.to_dict())
    except (AttributeError, DonorIndexError, IntegrationGateError, SearchValidationError, TypeError, ValueError) as exc:
        raise _input_error(label, exc) from exc
    if canonical != typed:
        raise DonorQueryIdentityMismatch(f"{label} is not canonical")
    return canonical


@dataclass(frozen=True)
class DonorQuery:
    """One immutable, content-addressed query over indexed donor evidence."""

    recipient_id: str
    version: Optional[str]
    source_path: Optional[str]
    symbol: Optional[str]
    instruction_signature: Optional[str]
    cfg_signature: Optional[str]
    dataflow_signature: Optional[str]
    compiler_identity: str
    config_identity: str
    limit: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "recipient_id", _identifier(self.recipient_id, "recipient_id"))
        if self.version is not None:
            version = _text(self.version, "version")
            if version not in DONOR_VERSIONS:
                raise DonorQueryInputError("version is not one of the supported donor versions")
            object.__setattr__(self, "version", version)
        object.__setattr__(self, "source_path", _optional_path(self.source_path, "source_path"))
        for name in (
            "symbol",
            "instruction_signature",
            "cfg_signature",
            "dataflow_signature",
        ):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))
        if not any(
            getattr(self, name)
            for name in (
                "symbol",
                "instruction_signature",
                "cfg_signature",
                "dataflow_signature",
            )
        ):
            raise DonorQueryInputError("at least one structural selector is required")
        object.__setattr__(self, "compiler_identity", _hash(self.compiler_identity, "compiler_identity"))
        object.__setattr__(self, "config_identity", _hash(self.config_identity, "config_identity"))
        if (
            isinstance(self.limit, bool)
            or not isinstance(self.limit, int)
            or not 1 <= self.limit <= 8
        ):
            raise DonorQueryInputError("limit must be an integer from 1 through 8")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": DONOR_QUERY_PROTOCOL,
            "recipient_id": self.recipient_id,
            "version": self.version,
            "source_path": self.source_path,
            "symbol": self.symbol,
            "instruction_signature": self.instruction_signature,
            "cfg_signature": self.cfg_signature,
            "dataflow_signature": self.dataflow_signature,
            "compiler_identity": self.compiler_identity,
            "config_identity": self.config_identity,
            "limit": self.limit,
        }

    @property
    def query_identity(self) -> str:
        return hash_canonical(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "query_identity": self.query_identity,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorQuery":
        fields = (
            "protocol",
            "recipient_id",
            "version",
            "source_path",
            "symbol",
            "instruction_signature",
            "cfg_signature",
            "dataflow_signature",
            "compiler_identity",
            "config_identity",
            "limit",
            "query_identity",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorQueryInputError("donor query fields do not match its protocol")
        if value["protocol"] != DONOR_QUERY_PROTOCOL:
            raise DonorQueryIdentityMismatch("donor query protocol is not supported")
        data = {key: value[key] for key in fields if key not in {"protocol", "query_identity"}}
        try:
            query = cls(**data)
        except DonorQueryError:
            raise
        except (TypeError, ValueError) as exc:
            raise _input_error("donor query", exc) from exc
        if value["query_identity"] != query.query_identity:
            raise DonorQueryIdentityMismatch("query_identity does not match the query payload")
        return query


def make_donor_query(
    *,
    recipient_id: str,
    version: Optional[str],
    source_path: Optional[str],
    symbol: Optional[str],
    instruction_signature: Optional[str],
    cfg_signature: Optional[str],
    dataflow_signature: Optional[str],
    compiler_identity: str,
    config_identity: str,
    limit: int,
) -> DonorQuery:
    """Construct one validated donor query."""

    return DonorQuery(
        recipient_id=recipient_id,
        version=version,
        source_path=source_path,
        symbol=symbol,
        instruction_signature=instruction_signature,
        cfg_signature=cfg_signature,
        dataflow_signature=dataflow_signature,
        compiler_identity=compiler_identity,
        config_identity=config_identity,
        limit=limit,
    )


@dataclass(frozen=True)
class DonorSemanticClaim:
    """The version-independent semantic content of one donor observation."""

    recipient_id: str
    symbol: Optional[str]
    signature: str
    instruction_signature: Optional[str]
    cfg_signature: Optional[str]
    dataflow_signature: Optional[str]
    declarations: Mapping[str, Any]
    constants: Mapping[str, Any]
    structural_differences: Tuple[str, ...]
    compatible: bool
    claim_identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "recipient_id", _identifier(self.recipient_id, "recipient_id"))
        object.__setattr__(self, "symbol", _optional_text(self.symbol, "symbol"))
        object.__setattr__(self, "signature", _text(self.signature, "signature"))
        for name in (
            "instruction_signature",
            "cfg_signature",
            "dataflow_signature",
        ):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))
        object.__setattr__(self, "declarations", _mapping(self.declarations, "declarations"))
        object.__setattr__(self, "constants", _mapping(self.constants, "constants"))
        object.__setattr__(self, "structural_differences", _structural_differences(self.structural_differences))
        if not isinstance(self.compatible, bool):
            raise DonorQueryInputError("compatible must be an actual boolean")
        _identity_hash(self.claim_identity, "claim_identity")
        expected = hash_canonical(self.identity_payload())
        if self.claim_identity != expected:
            raise DonorQueryIdentityMismatch("claim_identity does not match semantic claim")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": DONOR_SEMANTIC_CLAIM_PROTOCOL,
            "recipient_id": self.recipient_id,
            "symbol": self.symbol,
            "signature": self.signature,
            "instruction_signature": self.instruction_signature,
            "cfg_signature": self.cfg_signature,
            "dataflow_signature": self.dataflow_signature,
            "declarations": _thaw_json(self.declarations),
            "constants": _thaw_json(self.constants),
            "structural_differences": list(self.structural_differences),
            "compatible": self.compatible,
        }

    @classmethod
    def from_evidence(cls, evidence: DonorEvidence) -> "DonorSemanticClaim":
        if not isinstance(evidence, DonorEvidence):
            raise DonorQueryInputError("semantic claims require typed donor evidence")
        canonical_differences = _structural_differences(
            evidence.structural_differences
        )
        payload = {
            "recipient_id": evidence.recipient_id,
            "symbol": evidence.symbol,
            "signature": evidence.signature,
            "instruction_signature": evidence.instruction_signature,
            "cfg_signature": evidence.cfg_signature,
            "dataflow_signature": evidence.dataflow_signature,
            "declarations": evidence.declarations,
            "constants": evidence.constants,
            "structural_differences": canonical_differences,
            "compatible": evidence.compatible,
        }
        provisional = cls(
            claim_identity=hash_canonical(
                {
                    "protocol": DONOR_SEMANTIC_CLAIM_PROTOCOL,
                    **payload,
                }
            ),
            **payload,
        )
        return provisional

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorSemanticClaim":
        fields = (
            "claim_identity",
            "recipient_id",
            "symbol",
            "signature",
            "instruction_signature",
            "cfg_signature",
            "dataflow_signature",
            "declarations",
            "constants",
            "structural_differences",
            "compatible",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorQueryInputError("semantic claim fields do not match its protocol")
        try:
            return cls(**{key: value[key] for key in fields})
        except DonorQueryError:
            raise
        except (TypeError, ValueError) as exc:
            raise _input_error("semantic claim", exc) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_identity": self.claim_identity,
            "recipient_id": self.recipient_id,
            "symbol": self.symbol,
            "signature": self.signature,
            "instruction_signature": self.instruction_signature,
            "cfg_signature": self.cfg_signature,
            "dataflow_signature": self.dataflow_signature,
            "declarations": _thaw_json(self.declarations),
            "constants": _thaw_json(self.constants),
            "structural_differences": list(self.structural_differences),
            "compatible": self.compatible,
        }


@dataclass(frozen=True)
class DonorQueryHit:
    """One deterministic ranked hit retaining its original donor entry."""

    rank: int
    match_kind: str
    claim_identity: str
    entry: DonorIndexEntry
    generation_id: str

    def __post_init__(self) -> None:
        if isinstance(self.rank, bool) or not isinstance(self.rank, int):
            raise DonorQueryInputError("hit rank must be an integer")
        if self.match_kind not in MATCH_RANKS or MATCH_RANKS[self.match_kind] != self.rank:
            raise DonorQueryIdentityMismatch("hit rank and match kind disagree")
        _identity_hash(self.claim_identity, "claim_identity")
        _identity_hash(self.generation_id, "generation_id")
        entry = _entry(self.entry)
        if entry is not self.entry:
            object.__setattr__(self, "entry", entry)
        claim = DonorSemanticClaim.from_evidence(entry.evidence)
        if self.claim_identity != claim.claim_identity:
            raise DonorQueryIdentityMismatch("hit claim identity differs from donor evidence")

    @property
    def donor(self) -> DonorEvidence:
        """Return the original immutable donor evidence object."""

        return self.entry.evidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "match_kind": self.match_kind,
            "claim_identity": self.claim_identity,
            "entry": self.entry.to_dict(),
            "generation_id": self.generation_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorQueryHit":
        fields = ("rank", "match_kind", "claim_identity", "entry", "generation_id")
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorQueryInputError("query hit fields do not match its protocol")
        try:
            return cls(
                rank=value["rank"],
                match_kind=value["match_kind"],
                claim_identity=value["claim_identity"],
                entry=_entry(value["entry"]),
                generation_id=value["generation_id"],
            )
        except DonorQueryError:
            raise
        except (TypeError, ValueError) as exc:
            raise _input_error("query hit", exc) from exc


@dataclass(frozen=True)
class DonorAmbiguityReceipt:
    receipt_id: str
    query_identity: str
    generation_id: str
    entry_ids: Tuple[str, ...]
    reason_code: str

    def __post_init__(self) -> None:
        _identity_hash(self.receipt_id, "receipt_id")
        _identity_hash(self.query_identity, "query_identity")
        _identity_hash(self.generation_id, "generation_id")
        object.__setattr__(self, "entry_ids", _hashes(self.entry_ids, "entry_ids"))
        if len(self.entry_ids) < 2:
            raise DonorQueryInputError(
                "ambiguity receipt must identify at least two entries"
            )
        if self.reason_code != _AMBIGUITY_REASON:
            raise DonorQueryIdentityMismatch(
                "ambiguity receipt reason is not the production discriminant"
            )
        if self.receipt_id != hash_canonical(self.identity_payload()):
            raise DonorQueryIdentityMismatch("ambiguity receipt_id does not match its payload")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": DONOR_AMBIGUITY_RECEIPT_PROTOCOL,
            "query_identity": self.query_identity,
            "generation_id": self.generation_id,
            "entry_ids": list(self.entry_ids),
            "reason_code": self.reason_code,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "receipt_id": self.receipt_id}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorAmbiguityReceipt":
        fields = (
            "protocol",
            "receipt_id",
            "query_identity",
            "generation_id",
            "entry_ids",
            "reason_code",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorQueryInputError("ambiguity receipt fields do not match its protocol")
        if value["protocol"] != DONOR_AMBIGUITY_RECEIPT_PROTOCOL:
            raise DonorQueryIdentityMismatch("ambiguity receipt protocol is not supported")
        try:
            return cls(**{key: value[key] for key in fields if key != "protocol"})
        except DonorQueryError:
            raise
        except (TypeError, ValueError) as exc:
            raise _input_error("ambiguity receipt", exc) from exc


@dataclass(frozen=True)
class DonorIncompatibilityReceipt:
    receipt_id: str
    query_identity: str
    generation_id: str
    entry_ids: Tuple[str, ...]
    reasons: Tuple[str, ...]

    def __post_init__(self) -> None:
        _identity_hash(self.receipt_id, "receipt_id")
        _identity_hash(self.query_identity, "query_identity")
        _identity_hash(self.generation_id, "generation_id")
        object.__setattr__(self, "entry_ids", _hashes(self.entry_ids, "entry_ids"))
        if not self.entry_ids:
            raise DonorQueryInputError("incompatibility receipt must identify at least one entry")
        reasons = _strings(self.reasons, "reasons")
        if reasons != _INCOMPATIBILITY_REASONS:
            raise DonorQueryIdentityMismatch(
                "incompatibility reasons are not the production discriminant"
            )
        object.__setattr__(self, "reasons", reasons)
        if self.receipt_id != hash_canonical(self.identity_payload()):
            raise DonorQueryIdentityMismatch("incompatibility receipt_id does not match its payload")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": DONOR_INCOMPATIBILITY_RECEIPT_PROTOCOL,
            "query_identity": self.query_identity,
            "generation_id": self.generation_id,
            "entry_ids": list(self.entry_ids),
            "reasons": list(self.reasons),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "receipt_id": self.receipt_id}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorIncompatibilityReceipt":
        fields = (
            "protocol",
            "receipt_id",
            "query_identity",
            "generation_id",
            "entry_ids",
            "reasons",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorQueryInputError("incompatibility receipt fields do not match its protocol")
        if value["protocol"] != DONOR_INCOMPATIBILITY_RECEIPT_PROTOCOL:
            raise DonorQueryIdentityMismatch("incompatibility receipt protocol is not supported")
        try:
            return cls(**{key: value[key] for key in fields if key != "protocol"})
        except DonorQueryError:
            raise
        except (TypeError, ValueError) as exc:
            raise _input_error("incompatibility receipt", exc) from exc


@dataclass(frozen=True)
class DonorStaleReceipt:
    receipt_id: str
    query_identity: str
    generation_id: str
    expected_binding: DonorIndexBinding
    observed_binding: DonorIndexBinding

    def __post_init__(self) -> None:
        _identity_hash(self.receipt_id, "receipt_id")
        _identity_hash(self.query_identity, "query_identity")
        _identity_hash(self.generation_id, "generation_id")
        expected = _binding(self.expected_binding, "expected_binding")
        observed = _binding(self.observed_binding, "observed_binding")
        object.__setattr__(self, "expected_binding", expected)
        object.__setattr__(self, "observed_binding", observed)
        if expected == observed:
            raise DonorQueryIdentityMismatch("stale receipt bindings must disagree")
        if self.receipt_id != hash_canonical(self.identity_payload()):
            raise DonorQueryIdentityMismatch("stale receipt_id does not match its payload")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": DONOR_STALE_RECEIPT_PROTOCOL,
            "query_identity": self.query_identity,
            "generation_id": self.generation_id,
            "expected_binding": self.expected_binding.to_dict(),
            "observed_binding": self.observed_binding.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "receipt_id": self.receipt_id}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorStaleReceipt":
        fields = (
            "protocol",
            "receipt_id",
            "query_identity",
            "generation_id",
            "expected_binding",
            "observed_binding",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorQueryInputError("stale receipt fields do not match its protocol")
        if value["protocol"] != DONOR_STALE_RECEIPT_PROTOCOL:
            raise DonorQueryIdentityMismatch("stale receipt protocol is not supported")
        try:
            return cls(
                receipt_id=value["receipt_id"],
                query_identity=value["query_identity"],
                generation_id=value["generation_id"],
                expected_binding=_binding(value["expected_binding"], "expected_binding"),
                observed_binding=_binding(value["observed_binding"], "observed_binding"),
            )
        except DonorQueryError:
            raise
        except (TypeError, ValueError) as exc:
            raise _input_error("stale receipt", exc) from exc


Receipt = DonorAmbiguityReceipt | DonorIncompatibilityReceipt | DonorStaleReceipt


def _expected_artifact(generation_id: str, artifact: ArtifactRef) -> None:
    expected_path = f"artifacts/donor_indexes/{generation_id.removeprefix('sha256:')}.json"
    if (
        artifact.content_hash != generation_id
        or artifact.path != expected_path
        or artifact.media_type != "application/json"
        or not isinstance(artifact.byte_size, int)
        or artifact.byte_size < 0
    ):
        raise DonorQueryArtifactError("donor index artifact metadata is not canonical")


@dataclass(frozen=True)
class DonorQueryResult:
    """An immutable query outcome with durable generation provenance."""

    status: str
    query: DonorQuery
    query_identity: str
    generation_id: str
    hits: Tuple[DonorQueryHit, ...]
    donors: Tuple[DonorEvidence, ...]
    receipt: Optional[Receipt]
    provenance_artifact: ArtifactRef

    def __post_init__(self) -> None:
        if self.status not in QUERY_STATUSES:
            raise DonorQueryInputError("query result status is not supported")
        checked_query = _query_checked(self.query)
        object.__setattr__(self, "query", checked_query)
        if self.query_identity != checked_query.query_identity:
            raise DonorQueryIdentityMismatch(
                "query result identity differs from its typed query"
            )
        _identity_hash(self.query_identity, "query_identity")
        _identity_hash(self.generation_id, "generation_id")
        if not isinstance(self.hits, (tuple, list)):
            raise DonorQueryInputError("query result hits must be an explicit tuple or list")
        hits = tuple(self.hits)
        for hit in hits:
            if not isinstance(hit, DonorQueryHit):
                raise DonorQueryInputError("query result hits must be typed records")
            if hit.generation_id != self.generation_id:
                raise DonorQueryIdentityMismatch("query hit generation differs from result")
            ranked = _rank_entry(hit.entry, checked_query)
            if ranked != (hit.rank, hit.match_kind):
                raise DonorQueryIdentityMismatch(
                    "query hit rank or match kind differs from its query"
                )
        if len(hits) > checked_query.limit:
            raise DonorQueryIdentityMismatch("query result exceeds its query limit")
        ordered_hits = tuple(sorted(hits, key=lambda item: (item.rank, item.entry.entry_id)))
        if ordered_hits != hits or len({hit.entry.entry_id for hit in hits}) != len(hits):
            raise DonorQueryIdentityMismatch("query hits must be unique and deterministic")
        if hits and len({hit.rank for hit in hits}) != 1:
            raise DonorQueryIdentityMismatch("query hits must share the best structural rank")
        object.__setattr__(self, "hits", hits)
        if not isinstance(self.donors, (tuple, list)):
            raise DonorQueryInputError("query result donors must be an explicit tuple or list")
        donors = tuple(self.donors)
        if any(not isinstance(donor, DonorEvidence) for donor in donors):
            raise DonorQueryInputError("query result donors must be typed evidence")
        if len(donors) != len(hits) or any(
            donor is not hit.entry.evidence for donor, hit in zip(donors, hits)
        ):
            raise DonorQueryIdentityMismatch("query result donors must retain hit evidence references")
        object.__setattr__(self, "donors", donors)
        artifact = _artifact(self.provenance_artifact, "provenance_artifact")
        _expected_artifact(self.generation_id, artifact)
        object.__setattr__(self, "provenance_artifact", artifact)
        if self.status == "matched":
            if not hits or self.receipt is not None:
                raise DonorQueryIdentityMismatch("matched results need hits and no refusal receipt")
            if any(not hit.entry.evidence.compatible for hit in hits):
                raise DonorQueryIdentityMismatch(
                    "matched results cannot contain incompatible donor evidence"
                )
            if len({hit.claim_identity for hit in hits}) != 1:
                raise DonorQueryIdentityMismatch(
                    "matched results must share one semantic claim"
                )
        elif self.status == "empty":
            if hits or donors or self.receipt is not None:
                raise DonorQueryIdentityMismatch("empty results cannot carry hits or receipts")
        elif self.status == "ambiguous":
            if hits or donors or not isinstance(self.receipt, DonorAmbiguityReceipt):
                raise DonorQueryIdentityMismatch("ambiguous results need an ambiguity receipt only")
        elif self.status == "incompatible":
            if hits or donors or not isinstance(self.receipt, DonorIncompatibilityReceipt):
                raise DonorQueryIdentityMismatch("incompatible results need an incompatibility receipt only")
        elif self.status == "stale":
            if hits or donors or not isinstance(self.receipt, DonorStaleReceipt):
                raise DonorQueryIdentityMismatch("stale results need a stale receipt only")
            if (
                checked_query.compiler_identity
                != self.receipt.expected_binding.compiler_identity
                or checked_query.config_identity
                != self.receipt.expected_binding.config_identity
            ):
                raise DonorQueryIdentityMismatch(
                    "stale result query identities differ from expected binding"
                )
        if self.receipt is not None:
            if self.receipt.query_identity != self.query_identity:
                raise DonorQueryIdentityMismatch("receipt query identity differs from result")
            if self.receipt.generation_id != self.generation_id:
                raise DonorQueryIdentityMismatch("receipt generation differs from result")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query.to_dict(),
            "query_identity": self.query_identity,
            "generation_id": self.generation_id,
            "hits": [hit.to_dict() for hit in self.hits],
            "donors": [donor.to_dict() for donor in self.donors],
            "receipt": None if self.receipt is None else self.receipt.to_dict(),
            "provenance_artifact": self.provenance_artifact.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        index: Optional[DonorIndexGeneration] = None,
        expected_binding: Optional[DonorIndexBinding] = None,
        index_archive: Optional[ContentAddressedArchive] = None,
        integration_archive: Optional[ContentAddressedArchive] = None,
        query: Optional[DonorQuery] = None,
    ) -> "DonorQueryResult":
        """Replay a result only when the durable authority is supplied.

        A bare mapping is deliberately refused.  The archive-backed replay
        helper below recomputes the result and returns that fresh value, rather
        than trusting a serialized status, receipt, or donor reference.
        """

        if (
            index is None
            or expected_binding is None
            or index_archive is None
            or integration_archive is None
        ):
            raise DonorQueryInputError(
                "query result replay requires an index, expected binding, and both archives"
            )
        return replay_donor_query_result(
            index,
            value,
            expected_binding=expected_binding,
            index_archive=index_archive,
            integration_archive=integration_archive,
            query=query,
        )


def _verify_generation(
    index: DonorIndexGeneration,
    *,
    index_archive: ContentAddressedArchive,
    integration_archive: ContentAddressedArchive,
) -> Tuple[DonorIndexBinding, RunManifest, bytes]:
    if not isinstance(index, DonorIndexGeneration):
        raise DonorQueryInputError("query binding requires a typed donor index generation")
    if not isinstance(index_archive, ContentAddressedArchive):
        raise DonorQueryArtifactError("query binding requires a donor index archive")
    if not isinstance(integration_archive, ContentAddressedArchive):
        raise IntegrationGateError("query binding requires an integration gate archive")
    try:
        payload = index.payload()
        expected_bytes = canonical_bytes(payload)
        generation_id = index.generation_id
        artifact = index.artifact
        if hash_canonical(payload) != generation_id:
            raise DonorQueryArtifactError("donor index payload identity is not canonical")
        _expected_artifact(generation_id, artifact)
    except DonorQueryArtifactError:
        raise
    except (AttributeError, DonorIndexError, SearchValidationError, TypeError, ValueError) as exc:
        raise DonorQueryArtifactError("donor index generation payload is invalid") from exc
    try:
        archived_bytes = index_archive.verify(artifact)
    except (ArchiveError, AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise DonorQueryArtifactError("donor index artifact is missing or corrupt") from exc
    if archived_bytes != expected_bytes:
        raise DonorQueryArtifactError("donor index archive bytes differ from canonical generation")
    try:
        observed = _binding(index.binding, "observed_binding")
    except DonorQueryError:
        raise
    # This is intentionally the only gate validator call made by a query bind.
    manifest = validate_integration_gate(index.binding.integration_gate, archive=integration_archive)
    if not isinstance(manifest, RunManifest):
        raise IntegrationGateError("integration gate validator did not return its verified manifest")
    if observed.compiler_identity != manifest.compiler_identity:
        raise DonorQueryIdentityMismatch("indexed compiler identity differs from verified manifest")
    return observed, manifest, expected_bytes


def _rank_entry(entry: DonorIndexEntry, query: DonorQuery) -> Optional[Tuple[int, str]]:
    evidence = entry.evidence
    if evidence.recipient_id != query.recipient_id:
        return None
    if query.version is not None and evidence.version != query.version:
        return None
    selectors = (
        (
            "exact_symbol_path",
            query.symbol,
            evidence.symbol,
            query.source_path is None or evidence.source_path == query.source_path,
        ),
        ("instruction_shape", query.instruction_signature, evidence.instruction_signature, True),
        ("cfg", query.cfg_signature, evidence.cfg_signature, True),
        ("dataflow", query.dataflow_signature, evidence.dataflow_signature, True),
    )
    for kind, expected, observed, path_matches in selectors:
        if path_matches and expected is not None and expected == observed:
            return MATCH_RANKS[kind], kind
    return None


def _query_checked(query: Any) -> DonorQuery:
    if not isinstance(query, DonorQuery):
        raise DonorQueryInputError("query closure requires a typed DonorQuery")
    try:
        canonical = DonorQuery.from_dict(query.to_dict())
    except DonorQueryError:
        raise
    if canonical != query:
        raise DonorQueryIdentityMismatch("query is not canonical")
    return canonical


def _ambiguity(query: DonorQuery, generation_id: str, entries: Sequence[DonorIndexEntry]) -> DonorAmbiguityReceipt:
    entry_ids = tuple(sorted(entry.entry_id for entry in entries))
    payload = {
        "protocol": DONOR_AMBIGUITY_RECEIPT_PROTOCOL,
        "query_identity": query.query_identity,
        "generation_id": generation_id,
        "entry_ids": list(entry_ids),
            "reason_code": _AMBIGUITY_REASON,
    }
    return DonorAmbiguityReceipt(
        receipt_id=hash_canonical(payload),
        query_identity=query.query_identity,
        generation_id=generation_id,
        entry_ids=entry_ids,
        reason_code=_AMBIGUITY_REASON,
    )


def _incompatible(query: DonorQuery, generation_id: str, entries: Sequence[DonorIndexEntry]) -> DonorIncompatibilityReceipt:
    entry_ids = tuple(sorted(entry.entry_id for entry in entries))
    reasons = _INCOMPATIBILITY_REASONS
    payload = {
        "protocol": DONOR_INCOMPATIBILITY_RECEIPT_PROTOCOL,
        "query_identity": query.query_identity,
        "generation_id": generation_id,
        "entry_ids": list(entry_ids),
        "reasons": list(reasons),
    }
    return DonorIncompatibilityReceipt(
        receipt_id=hash_canonical(payload),
        query_identity=query.query_identity,
        generation_id=generation_id,
        entry_ids=entry_ids,
        reasons=reasons,
    )


def _stale(query: DonorQuery, generation_id: str, expected: DonorIndexBinding, observed: DonorIndexBinding) -> DonorStaleReceipt:
    payload = {
        "protocol": DONOR_STALE_RECEIPT_PROTOCOL,
        "query_identity": query.query_identity,
        "generation_id": generation_id,
        "expected_binding": expected.to_dict(),
        "observed_binding": observed.to_dict(),
    }
    return DonorStaleReceipt(
        receipt_id=hash_canonical(payload),
        query_identity=query.query_identity,
        generation_id=generation_id,
        expected_binding=expected,
        observed_binding=observed,
    )


def bind_donor_query(
    index: DonorIndexGeneration,
    *,
    index_archive: ContentAddressedArchive,
    integration_archive: ContentAddressedArchive,
    expected_binding: DonorIndexBinding,
) -> Callable[[DonorQuery], DonorQueryResult]:
    """Verify durable provenance and return a pure query closure."""

    observed, manifest, _expected_bytes = _verify_generation(
        index,
        index_archive=index_archive,
        integration_archive=integration_archive,
    )
    expected = _binding(expected_binding, "expected_binding")
    generation_id = index.generation_id

    def query(bound_query: DonorQuery) -> DonorQueryResult:
        checked = _query_checked(bound_query)
        if checked.compiler_identity != expected.compiler_identity:
            raise DonorQueryIdentityMismatch("query compiler identity differs from expected binding")
        if checked.config_identity != expected.config_identity:
            raise DonorQueryIdentityMismatch("query configuration identity differs from expected binding")
        if expected != observed:
            receipt = _stale(checked, generation_id, expected, observed)
            return DonorQueryResult(
                status="stale",
                query=checked,
                query_identity=checked.query_identity,
                generation_id=generation_id,
                hits=(),
                donors=(),
                receipt=receipt,
                provenance_artifact=index.artifact,
            )
        entries = tuple(index.entries)
        ranked = []
        for entry in entries:
            match = _rank_entry(entry, checked)
            if match is not None:
                rank, kind = match
                ranked.append((rank, kind, entry))
        ranked.sort(key=lambda item: (item[0], item[2].entry_id))
        if not ranked:
            return DonorQueryResult(
                status="empty",
                query=checked,
                query_identity=checked.query_identity,
                generation_id=generation_id,
                hits=(),
                donors=(),
                receipt=None,
                provenance_artifact=index.artifact,
            )
        # Establish the best structural rank before looking at compatibility.
        # An incompatible exact match must not silently turn into a weaker
        # instruction, CFG, or dataflow match merely because that lower-rank
        # record is compatible.
        best_rank = ranked[0][0]
        best = [item for item in ranked if item[0] == best_rank]
        compatible = [item for item in best if item[2].evidence.compatible]
        if not compatible:
            receipt = _incompatible(checked, generation_id, [item[2] for item in best])
            return DonorQueryResult(
                status="incompatible",
                query=checked,
                query_identity=checked.query_identity,
                generation_id=generation_id,
                hits=(),
                donors=(),
                receipt=receipt,
                provenance_artifact=index.artifact,
            )
        claim_ids = {DonorSemanticClaim.from_evidence(item[2].evidence).claim_identity for item in compatible}
        if len(claim_ids) > 1:
            receipt = _ambiguity(checked, generation_id, [item[2] for item in compatible])
            return DonorQueryResult(
                status="ambiguous",
                query=checked,
                query_identity=checked.query_identity,
                generation_id=generation_id,
                hits=(),
                donors=(),
                receipt=receipt,
                provenance_artifact=index.artifact,
            )
        selected = compatible[: checked.limit]
        hits = tuple(
            DonorQueryHit(
                rank=rank,
                match_kind=kind,
                claim_identity=DonorSemanticClaim.from_evidence(entry.evidence).claim_identity,
                entry=entry,
                generation_id=generation_id,
            )
            for rank, kind, entry in selected
        )
        return DonorQueryResult(
            status="matched",
            query=checked,
            query_identity=checked.query_identity,
            generation_id=generation_id,
            hits=hits,
            donors=tuple(hit.donor for hit in hits),
            receipt=None,
            provenance_artifact=index.artifact,
        )

    return query


def query_donor_index(
    index: DonorIndexGeneration,
    query: DonorQuery,
    *,
    index_archive: ContentAddressedArchive,
    integration_archive: ContentAddressedArchive,
    expected_binding: DonorIndexBinding,
) -> DonorQueryResult:
    """Verify and execute one query without exposing a scanner/provider."""

    return bind_donor_query(
        index,
        index_archive=index_archive,
        integration_archive=integration_archive,
        expected_binding=expected_binding,
    )(query)


def replay_donor_query_result(
    index: DonorIndexGeneration,
    result: Mapping[str, Any] | DonorQueryResult,
    *,
    expected_binding: DonorIndexBinding,
    index_archive: ContentAddressedArchive,
    integration_archive: ContentAddressedArchive,
    query: Optional[DonorQuery] = None,
) -> DonorQueryResult:
    """Recompute a serialized result against the durable index authority.

    This is the only public mapping replay boundary.  It never constructs a
    provenance-bearing result from the mapping itself: the typed query is
    extracted, the archive-backed query is run again, and the complete
    canonical serialization must match before that fresh result is returned.
    """

    if isinstance(result, DonorQueryResult):
        encoded = result.to_dict()
    elif isinstance(result, Mapping):
        encoded = dict(result)
    else:
        raise DonorQueryInputError("query result replay requires a typed result or mapping")
    required = {
        "status",
        "query",
        "query_identity",
        "generation_id",
        "hits",
        "donors",
        "receipt",
        "provenance_artifact",
    }
    if set(encoded) != required:
        raise DonorQueryInputError("query result fields do not match its protocol")
    if encoded["status"] in {"matched", "empty"} and encoded["receipt"] is not None:
        raise DonorQueryIdentityMismatch(
            "matched and empty replay results cannot carry a receipt"
        )
    try:
        encoded_query = DonorQuery.from_dict(encoded["query"])
    except DonorQueryError:
        raise
    if query is not None:
        checked_query = _query_checked(query)
        if checked_query != encoded_query:
            raise DonorQueryIdentityMismatch(
                "replay query differs from the serialized result query"
            )
    else:
        checked_query = encoded_query
    recomputed = query_donor_index(
        index,
        checked_query,
        expected_binding=expected_binding,
        index_archive=index_archive,
        integration_archive=integration_archive,
    )
    if encoded != recomputed.to_dict():
        raise DonorQueryIdentityMismatch(
            "serialized query result differs from archive-backed recomputation"
        )
    return recomputed


__all__ = [
    "DONOR_QUERY_PROTOCOL",
    "DONOR_SEMANTIC_CLAIM_PROTOCOL",
    "MATCH_RANKS",
    "DonorAmbiguityReceipt",
    "DonorIncompatibilityReceipt",
    "DonorQuery",
    "DonorQueryArtifactError",
    "DonorQueryError",
    "DonorQueryHit",
    "DonorQueryIdentityMismatch",
    "DonorQueryInputError",
    "DonorQueryResult",
    "DonorSemanticClaim",
    "DonorStaleReceipt",
    "bind_donor_query",
    "make_donor_query",
    "query_donor_index",
    "replay_donor_query_result",
]
