"""Target-bound query construction and semantic-only candidate rendering.

The donor index deliberately contains no version-specific source body.  This
module is the other half of that boundary: it resolves a recipient only from
the immutable target evidence archived by the run, derives query selectors
from that target, and lets donor observations contribute semantic claims only.
No provider, repository tree, queue reader, or donor source is reachable from
the public functions below.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Optional

try:  # package imports
    from .search_mips_switch import recover_dispatches, split_local_tables
    from .search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive
    from .search_donor_index import DONOR_VERSIONS
    from .search_donor_query import (
        DonorQuery,
        DonorSemanticClaim,
        make_donor_query,
    )
    from .search_lanes import LaneCandidate, LaneError, Recipient
    from .search_semantic_signatures import (
        SemanticInstruction,
        assembly_signatures,
        has_numeric_branch_target,
    )
    from .search_types import (
        CandidateRecord,
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )
except ImportError:  # direct invocation from the automation directory
    from search_mips_switch import recover_dispatches, split_local_tables  # type: ignore
    from search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive  # type: ignore
    from search_donor_index import DONOR_VERSIONS  # type: ignore
    from search_donor_query import (  # type: ignore
        DonorQuery,
        DonorSemanticClaim,
        make_donor_query,
    )
    from search_lanes import LaneCandidate, LaneError, Recipient  # type: ignore
    from search_semantic_signatures import (  # type: ignore
        SemanticInstruction,
        assembly_signatures,
        has_numeric_branch_target,
    )
    from search_types import (  # type: ignore
        CandidateRecord,
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )


TARGET_RENDERER_PROTOCOL = "target-renderer-v1"
TARGET_INDEX_ARTIFACT_TYPE = "sotn-search-target-index"
TARGET_EVIDENCE_ARTIFACT_TYPE = "sotn-search-target-evidence"
TARGET_SCHEMA_VERSION = "1.0.0"
TARGET_RENDERER_IDENTITY = hash_canonical(
    {
        "module": "automation.search_target_renderer",
        "protocol": "sotn-indexed-runtime-renderer-v1",
    }
)
INDEXED_RENDER_LANES = frozenset({"multi_donor", "cfg_dataflow"})
_DEFAULT_LIMIT = 8


class TargetRendererError(LaneError):
    """Base class for target evidence and renderer failures."""


class TargetRendererInputError(TargetRendererError):
    """The target index, recipient, or semantic claims are malformed."""


class TargetEvidenceError(TargetRendererInputError):
    """Target evidence is missing, unarchived, or not bound to the manifest."""


# production-audit: pure-value
@dataclass(frozen=True)
class TargetContextUnsupported:
    """Typed, provenance-bearing refusal for an unrenderable target shape.

    The object is returned by :func:`render_target_candidate` rather than
    being converted to an empty successful search.  The indexed adapter turns
    it into the ordinary lane refusal mapping while retaining this query and
    target provenance.
    """

    recipient_id: str
    query: DonorQuery
    target_identity: str
    target_artifact_identity: str
    reason: str
    input_identities: tuple[str, ...]
    provenance: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        try:
            validate_id(self.recipient_id, "target refusal recipient_id")
        except SearchValidationError as exc:
            raise TargetRendererInputError(str(exc)) from exc
        if not isinstance(self.query, DonorQuery):
            raise TargetRendererInputError("target refusal needs a typed query")
        if self.query.recipient_id != self.recipient_id:
            raise TargetRendererInputError(
                "target refusal query recipient differs from refusal recipient"
            )
        for name, value in (
            ("target_identity", self.target_identity),
            ("target_artifact_identity", self.target_artifact_identity),
        ):
            try:
                validate_hash(value, name)
            except SearchValidationError as exc:
                raise TargetRendererInputError(str(exc)) from exc
        if not isinstance(self.reason, str) or not self.reason:
            raise TargetRendererInputError("target refusal reason must be nonempty")
        if not isinstance(self.input_identities, (tuple, list)):
            raise TargetRendererInputError(
                "target refusal input_identities must be a tuple or list"
            )
        input_ids = tuple(self.input_identities)
        for value in input_ids:
            try:
                validate_hash(value, "target refusal input identity")
            except SearchValidationError as exc:
                raise TargetRendererInputError(str(exc)) from exc
        if len(set(input_ids)) != len(input_ids):
            raise TargetRendererInputError(
                "target refusal input_identities must not contain duplicates"
            )
        object.__setattr__(self, "input_identities", input_ids)
        if not isinstance(self.provenance, (tuple, list)):
            raise TargetRendererInputError(
                "target refusal provenance must be a tuple or list"
            )
        normalized: list[Mapping[str, Any]] = []
        for item in self.provenance:
            if not isinstance(item, Mapping):
                raise TargetRendererInputError(
                    "target refusal provenance entries must be mappings"
                )
            edge = dict(item)
            for name in ("source", "kind"):
                if not isinstance(edge.get(name), str) or not edge[name]:
                    raise TargetRendererInputError(
                        f"target refusal provenance {name} must be nonempty"
                    )
            for name in ("source_identity", "input_identity"):
                try:
                    validate_hash(edge.get(name), "target refusal " + name)
                except SearchValidationError as exc:
                    raise TargetRendererInputError(str(exc)) from exc
            if edge.get("recipient_id") not in (None, self.recipient_id):
                raise TargetRendererInputError(
                    "target refusal provenance recipient differs"
                )
            edge["recipient_id"] = self.recipient_id
            normalized.append(MappingProxyType(edge))
        object.__setattr__(self, "provenance", tuple(normalized))

    @property
    def refusal_code(self) -> str:
        return "target_context_unsupported"

    @property
    def completion_reason(self) -> str:
        return "inapplicable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "refusal_code": self.refusal_code,
            "completion_reason": self.completion_reason,
            "recipient_id": self.recipient_id,
            "query": self.query.to_dict(),
            "query_identity": self.query.query_identity,
            "target_identity": self.target_identity,
            "target_artifact_identity": self.target_artifact_identity,
            "reason": self.reason,
            "input_identities": list(self.input_identities),
            "provenance": [dict(item) for item in self.provenance],
        }


# production-audit: pure-value
@dataclass(frozen=True)
class _TargetContext:
    recipient_id: str
    target_identity: str
    target_evidence_identity: str
    assembly: ArtifactRef
    assembly_path: str
    assembly_bytes: bytes
    symbol: str
    instruction_signature: Optional[str]
    cfg_signature: Optional[str]
    dataflow_signature: Optional[str]
    declarations: Mapping[str, Any]
    version: Optional[str]

    def __post_init__(self) -> None:
        try:
            validate_id(self.recipient_id, "target recipient_id")
            validate_hash(self.target_identity, "target identity")
            validate_hash(self.target_evidence_identity, "target evidence identity")
            validate_relative_path(self.assembly_path)
        except SearchValidationError as exc:
            raise TargetEvidenceError(str(exc)) from exc
        if not isinstance(self.assembly, ArtifactRef):
            raise TargetEvidenceError("target assembly must be an ArtifactRef")
        if not isinstance(self.assembly_bytes, bytes) or not self.assembly_bytes:
            raise TargetEvidenceError("target assembly bytes must be nonempty")
        if hash_bytes(self.assembly_bytes) != self.assembly.content_hash:
            raise TargetEvidenceError("target assembly bytes differ from its artifact")
        if self.assembly.byte_size != len(self.assembly_bytes):
            raise TargetEvidenceError("target assembly byte size differs from bytes")
        if self.assembly.media_type != "text/x-asm":
            raise TargetEvidenceError("target assembly media type is not text/x-asm")
        _validate_archived_assembly_ref(self.assembly)
        if not isinstance(self.symbol, str) or not _C_IDENTIFIER.fullmatch(self.symbol):
            raise TargetEvidenceError("target symbol is not a C identifier")
        for name in (
            "instruction_signature",
            "cfg_signature",
            "dataflow_signature",
        ):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise TargetEvidenceError(
                    f"target {name} must be null or a nonempty string"
                )
        if self.version is not None and self.version not in DONOR_VERSIONS:
            raise TargetEvidenceError("target version is not supported")
        if not isinstance(self.declarations, Mapping):
            raise TargetEvidenceError("target declarations must be a mapping")
        object.__setattr__(self, "declarations", _freeze_json(self.declarations, "declarations"))


# production-audit: pure-value
@dataclass(frozen=True)
class TargetIndex:
    """Archive-resolved target records used by production adapter closures."""

    records: tuple[_TargetContext, ...]
    artifact: Optional[ArtifactRef] = None

    def __post_init__(self) -> None:
        if not isinstance(self.records, (tuple, list)):
            raise TargetEvidenceError("target index records must be a tuple or list")
        records = tuple(self.records)
        if any(not isinstance(item, _TargetContext) for item in records):
            raise TargetEvidenceError("target index records must be archived target contexts")
        if len({item.recipient_id for item in records}) != len(records):
            raise TargetEvidenceError("target index contains duplicate recipients")
        object.__setattr__(self, "records", tuple(sorted(records, key=lambda item: item.recipient_id)))
        if self.artifact is not None and not isinstance(self.artifact, ArtifactRef):
            raise TargetEvidenceError("target index artifact must be an ArtifactRef")
        if self.artifact is not None:
            _validate_archived_ref(
                self.artifact,
                category="target-index",
                suffix=".json",
                media_type="application/json",
                label="target index",
            )

    def for_recipient(self, recipient_id: str) -> _TargetContext:
        matches = tuple(item for item in self.records if item.recipient_id == recipient_id)
        if len(matches) != 1:
            raise TargetEvidenceError(
                "target index must contain exactly one record for " + recipient_id
            )
        return matches[0]


_C_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_C_TYPE = re.compile(
    r"^(?:const\s+|volatile\s+|unsigned\s+|signed\s+|short\s+|long\s+)*"
    r"(?:void|char|short|int|long|float|double|u8|s8|u16|s16|u32|s32|f32|[A-Za-z_]\w*)"
    r"(?:\s*\*)*$"
)
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "source",
        "source_code",
        "source_bytes",
        "register",
        "registers",
        "regalloc",
        "relocation",
        "relocations",
        "branch_displacement",
        "branch_displacements",
        "displacement",
        "displacements",
        "raw_bytes",
        "object_bytes",
    }
)
_TARGET_EVIDENCE_FIELDS = frozenset(
    {
        "artifact_type",
        "assembly",
        "object",
        "record_id",
        "schema_version",
        # The factory emits only the required fields.  These optional fields
        # are accepted for hand-authored fixtures and future target metadata,
        # but no arbitrary extension can become renderer input.
        "symbol",
        "instruction_signature",
        "cfg_signature",
        "dataflow_signature",
        "signatures",
        "declarations",
        "target_declarations",
        "version",
        "platform",
    }
)
_TARGET_COMPONENT_FIELDS = frozenset(
    {"artifact", "content_hash", "path", "byte_size"}
)


def _freeze_json(value: Any, label: str) -> Any:
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TargetEvidenceError(f"{label} keys must be strings")
            _reject_forbidden_tree_key(key, f"{label}.{key}")
            frozen[key] = _freeze_json(item, f"{label}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json(item, f"{label}[{index}]") for index, item in enumerate(value))
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    raise TargetEvidenceError(f"{label} contains an unsupported value")


def _reject_forbidden_tree_key(key: str, label: str) -> None:
    lowered = key.lower()
    if lowered in _FORBIDDEN_KEYS or any(
        token in lowered
        for token in ("register", "relocat", "displacement", "raw_bytes")
    ):
        raise TargetEvidenceError(f"{label} contains forbidden donor-specific context")


def _reject_forbidden_tree(value: Any, label: str) -> None:
    """Reject donor-only context hidden below a target evidence mapping."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TargetEvidenceError(f"{label} keys must be strings")
            _reject_forbidden_tree_key(key, f"{label}.{key}")
            _reject_forbidden_tree(item, f"{label}.{key}")
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            _reject_forbidden_tree(item, f"{label}[{index}]")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        converted = to_dict()
        if isinstance(converted, Mapping):
            return dict(converted)
    raise TargetRendererInputError(label + " must be a mapping")


def _optional_text(value: Any, label: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise TargetEvidenceError(label + " must be null or a nonempty string")
    return value


def _hash(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except SearchValidationError as exc:
        raise TargetEvidenceError(str(exc)) from exc


def _artifact(value: Any, label: str) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    try:
        return ArtifactRef.from_dict(value)
    except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise TargetEvidenceError(label + " is not a valid artifact reference") from exc


def _validate_archived_assembly_ref(reference: ArtifactRef) -> None:
    """Require the canonical archived target assembly shape."""

    parts = reference.path.split("/")
    digest = reference.content_hash.removeprefix("sha256:")
    if (
        len(parts) != 3
        or parts[0] != "artifacts"
        or parts[1] != "target-assembly"
        or parts[2] != digest + ".s"
    ):
        raise TargetEvidenceError("target assembly is not an archived target artifact")


def _validate_archived_ref(
    reference: ArtifactRef,
    *,
    category: str,
    suffix: str,
    media_type: str,
    label: str,
) -> None:
    digest = reference.content_hash.removeprefix("sha256:")
    if (
        reference.media_type != media_type
        or reference.path
        != f"artifacts/{category}/{digest}{suffix}"
    ):
        raise TargetEvidenceError(label + " is not a canonical archived artifact")


def _verify_archived_bytes(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    label: str,
) -> bytes:
    """Verify bytes without following a symlink inside the run archive."""

    try:
        root = archive.run_root.resolve(strict=False)
        raw_path = root / Path(reference.path)
        relative = raw_path.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise TargetEvidenceError(label + " is outside the run archive") from exc
    current = root
    if current.is_symlink():
        raise TargetEvidenceError(label + " archive root is a symlink")
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise TargetEvidenceError(label + " archive path contains a symlink")
    try:
        return archive.verify(reference)
    except (ArchiveError, OSError, ValueError, TypeError) as exc:
        raise TargetEvidenceError(label + " is missing or corrupt") from exc


def _raw_bytes(value: Any, label: str) -> Optional[bytes]:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    raise TargetEvidenceError(label + " content must be bytes or text")


def _value(value: Any, *names: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
        return default
    for name in names:
        observed = getattr(value, name, None)
        if observed is not None:
            return observed
    return default


def _index_records(target_index: Any) -> tuple[Any, ...]:
    if isinstance(target_index, TargetIndex):
        return tuple(target_index.records)
    if isinstance(target_index, Mapping):
        raw = target_index.get("records")
        if raw is None:
            # A keyed map is accepted only when every value is a record.  It
            # is still an explicit target index, not a repository fallback.
            keyed = [
                {**dict(item), "record_id": key}
                for key, item in target_index.items()
                if isinstance(key, str) and isinstance(item, Mapping)
            ]
            if keyed and len(keyed) == len(target_index):
                raw = keyed
        if not isinstance(raw, (tuple, list)):
            raise TargetRendererInputError("target index records must be a sequence")
        return tuple(raw)
    raw = _value(target_index, "records", "target_records")
    if not isinstance(raw, (tuple, list)):
        raise TargetRendererInputError("target index records must be a sequence")
    return tuple(raw)


def _context_from_record(value: Any) -> _TargetContext:
    if isinstance(value, _TargetContext):
        return value
    record = _mapping(value, "target index record")
    _reject_forbidden_tree(record, "target index record")
    evidence_raw = record.get("target_evidence", record.get("evidence", record))
    if isinstance(evidence_raw, ArtifactRef):
        raise TargetEvidenceError(
            "target evidence reference must be resolved from the run archive"
        )
    evidence = _mapping(evidence_raw, "target evidence")
    _reject_forbidden_tree(evidence, "target evidence")
    record_id = _value(record, "record_id", "recipient_id", "id")
    record_id = _value(evidence, "record_id", "recipient_id", "id", default=record_id)
    if not isinstance(record_id, str) or not record_id:
        raise TargetEvidenceError("target evidence has no recipient identity")
    target_identity = _value(record, "target_identity", "target_id")
    if target_identity is None:
        target_identity = _value(evidence, "target_identity", "target_id")
    target_identity = _hash(target_identity, "target identity")
    target_evidence_identity = _value(
        record,
        "target_evidence_identity",
        "target_artifact_identity",
        default=target_identity,
    )
    target_evidence_ref = _value(
        record,
        "target_evidence_artifact",
        "target_evidence_ref",
    )
    if target_evidence_ref is None:
        target_evidence_ref = _value(evidence, "artifact", "target_evidence_artifact")
    if target_evidence_ref is not None:
        target_evidence_ref = _artifact(target_evidence_ref, "target evidence artifact")
        target_evidence_identity = target_evidence_ref.content_hash
    target_evidence_identity = _hash(target_evidence_identity, "target evidence identity")

    assembly_raw = _value(evidence, "assembly", "target_assembly")
    if assembly_raw is None:
        assembly_raw = _value(record, "assembly", "target_assembly")
    if assembly_raw is None:
        raise TargetEvidenceError("target evidence has no assembly")
    assembly_ref: Optional[ArtifactRef] = None
    assembly_path: Optional[str] = None
    assembly_bytes: Optional[bytes] = None
    if isinstance(assembly_raw, ArtifactRef):
        assembly_ref = assembly_raw
    elif isinstance(assembly_raw, Mapping):
        assembly_ref_raw = _value(assembly_raw, "artifact", "artifact_ref", "archive")
        if assembly_ref_raw is not None:
            assembly_ref = _artifact(assembly_ref_raw, "target assembly artifact")
        assembly_path = _value(assembly_raw, "path", "source_path", "target_path")
        assembly_bytes = _raw_bytes(
            _value(
                assembly_raw,
                "bytes",
                "content",
                "text",
                "assembly_text",
                "source_text",
            ),
            "target assembly",
        )
    elif isinstance(assembly_raw, (bytes, bytearray, memoryview)):
        assembly_bytes = bytes(assembly_raw)
    elif isinstance(assembly_raw, str):
        # A path string is not source evidence.  Inline assembly is accepted
        # only when it is accompanied by an archived ArtifactRef below.
        if "\n" in assembly_raw or "\r" in assembly_raw:
            assembly_bytes = assembly_raw.encode("utf-8")
        else:
            assembly_path = assembly_raw
    else:
        raise TargetEvidenceError("target assembly has an unsupported shape")
    if assembly_ref is None:
        assembly_ref_raw = _value(
            evidence,
            "assembly_artifact",
            "assembly_ref",
        )
        if assembly_ref_raw is None:
            assembly_ref_raw = _value(record, "assembly_artifact", "assembly_ref")
        if assembly_ref_raw is not None:
            assembly_ref = _artifact(assembly_ref_raw, "target assembly artifact")
    if assembly_ref is None:
        raise TargetEvidenceError(
            "target assembly is unarchived and cannot reach the renderer"
        )
    if assembly_bytes is None:
        assembly_bytes = _raw_bytes(
            _value(evidence, "assembly_bytes", "assembly_content", "assembly_text"),
            "target assembly",
        )
    if assembly_bytes is None:
        raise TargetEvidenceError(
            "target assembly bytes must be resolved from the run archive"
        )
    if assembly_path is None:
        assembly_path = _value(evidence, "path", "source_path", "target_path")
    if not isinstance(assembly_path, str) or not assembly_path:
        raise TargetEvidenceError("target assembly source path is missing")
    assembly_path = assembly_path.replace("\\", "/")
    try:
        validate_relative_path(assembly_path)
    except SearchValidationError as exc:
        raise TargetEvidenceError("target assembly source path is invalid") from exc

    symbol = _value(
        evidence,
        "symbol",
        "function",
        default=_value(record, "symbol", "function", default=record_id.split(":")[-1]),
    )
    if not isinstance(symbol, str) or not symbol:
        raise TargetEvidenceError("target symbol is missing")
    signatures = _value(evidence, "signatures", "target_signatures", default={})
    if not isinstance(signatures, Mapping):
        raise TargetEvidenceError("target signatures must be a mapping")
    instruction_signature = _value(
        evidence,
        "instruction_signature",
        default=_value(signatures, "instruction_signature", "instructions"),
    )
    cfg_signature = _value(
        evidence,
        "cfg_signature",
        default=_value(signatures, "cfg_signature", "cfg"),
    )
    dataflow_signature = _value(
        evidence,
        "dataflow_signature",
        default=_value(signatures, "dataflow_signature", "dataflow", "flow"),
    )
    declarations = _value(
        evidence,
        "declarations",
        "target_declarations",
        default=_value(record, "declarations", "target_declarations", default={}),
    )
    if not isinstance(declarations, Mapping):
        raise TargetEvidenceError("target declarations must be a mapping")
    version = _value(evidence, "version", "platform", default=_value(record, "version", "platform"))
    if version is not None and not isinstance(version, str):
        raise TargetEvidenceError("target version must be a string or null")
    return _TargetContext(
        recipient_id=record_id,
        target_identity=target_identity,
        target_evidence_identity=target_evidence_identity,
        assembly=assembly_ref,
        assembly_path=assembly_path,
        assembly_bytes=assembly_bytes,
        symbol=symbol,
        instruction_signature=_optional_text(instruction_signature, "instruction_signature"),
        cfg_signature=_optional_text(cfg_signature, "cfg_signature"),
        dataflow_signature=_optional_text(dataflow_signature, "dataflow_signature"),
        declarations=declarations,
        version=version,
    )


def _target_context(target_index: Any, manifest: RunManifest, recipient: Recipient) -> _TargetContext:
    if not isinstance(manifest, RunManifest):
        raise TargetRendererInputError("target query requires a typed RunManifest")
    if not isinstance(recipient, Recipient):
        raise TargetRendererInputError("target query requires a typed Recipient")
    if not isinstance(target_index, TargetIndex):
        raise TargetEvidenceError(
            "target query requires an archive-resolved TargetIndex"
        )
    if target_index.artifact is None:
        raise TargetEvidenceError(
            "target query requires a content-addressed target index artifact"
        )
    if recipient.recipient_id not in manifest.queue_record_ids:
        raise TargetRendererInputError("recipient is outside the manifest subset")
    try:
        expected_target = manifest.target_identities[recipient.recipient_id]
    except (KeyError, TypeError) as exc:
        raise TargetEvidenceError("manifest has no target identity for recipient") from exc
    try:
        context = target_index.for_recipient(recipient.recipient_id)
    except TargetEvidenceError:
        raise
    except (TypeError, ValueError) as exc:
        raise TargetEvidenceError(
            "target index must contain exactly one target for " + recipient.recipient_id
        ) from exc
    if context.target_identity != expected_target:
        raise TargetEvidenceError("target evidence identity differs from manifest")
    expected_version = recipient.recipient_id.split(":", 1)[0]
    if context.version is not None and context.version != expected_version:
        raise TargetEvidenceError("target evidence platform differs from recipient")
    if expected_version in DONOR_VERSIONS and context.version is None:
        context = replace(context, version=expected_version)
    return context


def _coerce_manifest(manifest: Any) -> RunManifest:
    if isinstance(manifest, RunManifest):
        return manifest
    if isinstance(manifest, Mapping):
        try:
            return RunManifest.from_dict(manifest)
        except (
            AttributeError,
            KeyError,
            SearchValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise TargetRendererInputError("target query manifest is invalid") from exc
    raise TargetRendererInputError("target query requires a typed RunManifest")


_REGISTER = re.compile(
    r"((?:\$[0-9]{1,2}|\$(?:zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra)|"
    r"r(?:[0-9]{1,2}|zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra)))",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"(?<![A-Za-z_])(?:-?0[xX][0-9A-Fa-f]+|-?[0-9]+)(?![A-Za-z_])")
_ASM_RELOCATION = re.compile(
    r"(?:\.reloc\b|%hi\b|%lo\b|%higher\b|%highest\b|@(?:ha|l|h)\b|"
    r"R_(?:MIPS|SH|ARM)|\b(?:HI16|LO16|REL(?:32|24)?)\b)",
    re.IGNORECASE,
)
_ASM_DATA_DIRECTIVE = re.compile(
    r"^\s*\.(?:byte|2byte|4byte|8byte|half|word|dword|float|double|incbin|fill|space)\b",
    re.IGNORECASE,
)
_EMPTY_DIRECTIVE = re.compile(
    r"^\s*\.(?:size|ent|end|frame|mask|fmask|loc)\b",
    re.IGNORECASE,
)
_RETURN_MNEMONICS = frozenset({"jr", "rts", "ret"})
_ABI_PARAMETER_POSITIONS = {
    **{f"a{index}": index for index in range(4)},
    **{f"r{4 + index}": index for index in range(4)},
    **{str(4 + index): index for index in range(4)},
}


@dataclass(frozen=True)
class _Instruction:
    mnemonic: str
    operands: str
    label: Optional[str] = None
    unsupported: bool = False


@dataclass(frozen=True)
class RendererLimits:
    """Explicit variable bounds for one deterministic rendering attempt.

    Every field has a validated hard ceiling, so any valid instance still
    guarantees termination: the path budget caps total control-flow steps,
    the instruction cap keeps each linear pass proportional to its input,
    and the expression/body caps bound memory. Production rendering
    (render_target_candidate) always uses DEFAULT_LIMITS so archived runs
    replay exactly; custom instances are for scoped measurement and
    fixtures, and any future production use must archive the chosen
    instance alongside its inputs.
    """

    max_instructions: int = 64
    path_budget: int = 256
    max_expression: int = 4096
    max_body: int = 65536

    def __post_init__(self) -> None:
        for name, low, high in (
            ("max_instructions", 1, 512),
            ("path_budget", 1, 4096),
            ("max_expression", 1024, 16384),
            ("max_body", 4096, 262144),
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise TargetRendererInputError(
                    f"renderer limit {name} must be an integer from {low} through {high}")


DEFAULT_LIMITS = RendererLimits()


def _coerce_limits(value: Any) -> RendererLimits:
    """Accept the default, a RendererLimits, or an explicit partial mapping."""
    if value is None:
        return DEFAULT_LIMITS
    if isinstance(value, RendererLimits):
        return value
    if isinstance(value, Mapping):
        unknown = set(value) - {"max_instructions", "path_budget", "max_expression", "max_body"}
        if unknown:
            raise TargetRendererInputError("renderer limits contain unknown fields: " + ", ".join(sorted(unknown)))
        try:
            return RendererLimits(**{key: value[key] for key in (
                "max_instructions", "path_budget", "max_expression", "max_body") if key in value})
        except TypeError as exc:
            raise TargetRendererInputError("renderer limits are invalid: " + str(exc)) from exc
    raise TargetRendererInputError("renderer limits must be a RendererLimits or a mapping")


def _strip_assembly_comment(line: str) -> str:
    # Factory target artifacts are generated assembly, where '#' and '//' are
    # comments outside operand syntax.  Block comments are handled separately
    # so annotated spimdisasm instructions remain parseable.
    line = re.sub(r"/\*.*?\*/", " ", line)
    line = line.split("//", 1)[0]
    # ``#`` starts a MIPS comment, but ARM uses it for immediate operands
    # (``#4`` and ``#0x20``).  Preserve numeric immediates so the shared
    # semantic normalizer can classify numeric branch displacements; strip
    # only a hash that is not followed by a signed decimal or hexadecimal
    # value.
    line = re.sub(
        r"#(?!\s*[+-]?(?:0[xX][0-9A-Fa-f]+|[0-9]+)\b).*?$",
        "",
        line,
    )
    return line


_API_HI = re.compile(r"%hi\s*\(\s*(g_api_[A-Za-z_]\w*)\s*\)")
_API_LO = re.compile(r"%lo\s*\(\s*(g_api_[A-Za-z_]\w*)\s*\)")
_DATA_HI = re.compile(r"%hi\s*\(\s*(D_[A-Za-z0-9_.$]*)\s*\)")
_DATA_LO = re.compile(r"%lo\s*\(\s*(D_[A-Za-z0-9_.$]*)\s*\)")
_GLOBAL_HI = re.compile(r"%hi\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\)")
_GLOBAL_LO = re.compile(r"%lo\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\)")
_LINKER_HI = re.compile(r"%hi\s*\(\s*((?:PLAYER_|RIC_)[A-Za-z_]\w*)\s*\)")
_LINKER_LO = re.compile(r"%lo\s*\(\s*((?:PLAYER_|RIC_)[A-Za-z_]\w*)\s*\)")
_GLOBAL_OFF_HI = re.compile(r"%hi\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\+\s*(?:0[xX][0-9a-fA-F]+|[0-9]+)\s*\)")
_GLOBAL_OFF_LO = re.compile(r"%lo\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\+\s*(?:0[xX][0-9a-fA-F]+|[0-9]+)\s*\)")


def _is_supported_api_relocation(operands: str) -> bool:
    """Whether relocations are only g_api hi/lo halves, never other shapes."""
    if not _ASM_RELOCATION.search(operands):
        return False
    stripped = _API_HI.sub("", operands)
    stripped = _API_LO.sub("", stripped)
    return not _ASM_RELOCATION.search(stripped)

def _is_supported_data_relocation(operands: str) -> bool:
    """Whether relocations are only D_* data hi/lo halves, never other shapes."""
    if not _ASM_RELOCATION.search(operands):
        return False
    stripped = _DATA_HI.sub("", operands)
    stripped = _DATA_LO.sub("", stripped)
    return not _ASM_RELOCATION.search(stripped)

def _is_supported_global_relocation(operands: str) -> bool:
    """Whether relocations are only g_* global hi/lo halves, never other shapes."""
    if not _ASM_RELOCATION.search(operands):
        return False
    stripped = _GLOBAL_HI.sub("", operands)
    stripped = _GLOBAL_LO.sub("", stripped)
    stripped = _GLOBAL_OFF_HI.sub("", stripped)
    stripped = _GLOBAL_OFF_LO.sub("", stripped)
    return not _ASM_RELOCATION.search(stripped)

def _is_supported_linker_relocation(operands: str) -> bool:
    """Whether relocations are only PLAYER_/RIC_ absolute hi/lo halves."""
    if not _ASM_RELOCATION.search(operands):
        return False
    stripped = _LINKER_HI.sub("", operands)
    stripped = _LINKER_LO.sub("", stripped)
    return not _ASM_RELOCATION.search(stripped)

def _fold_const_expr(text: str):
    """Fold one assembler constant expression to an int, or None.

    Splat spells large constants as (0xC0000000 >> 16); the assembler
    folds these before encoding, so folding here models exact semantics.
    Only a single binary operator over plain numerics is admitted.
    """
    plain = re.fullmatch(r"-?(?:0[xX][0-9a-fA-F]+|[0-9]+)", text.strip())
    if plain:
        return int(plain.group(0), 0)
    folded = re.fullmatch(
        r"\(\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*(>>|<<|&|\||\+|-)\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*\)\s*",
        text.strip())
    if not folded:
        return None
    left, operator, right = int(folded.group(1), 0), folded.group(2), int(folded.group(3), 0)
    if operator == ">>":
        return left >> right
    if operator == "<<":
        return (left << right) & 0xFFFFFFFF
    if operator == "&":
        return left & right
    if operator == "|":
        return left | right
    if operator == "+":
        return (left + right) & 0xFFFFFFFF
    return (left - right) & 0xFFFFFFFF

def _parse_assembly(text: str, *, retain_relocations: bool = False) -> tuple[_Instruction, ...]:
    if not isinstance(text, str):
        raise TargetEvidenceError("target assembly is not UTF-8 text")
    instructions: list[_Instruction] = []
    pending_label: Optional[str] = None
    for raw_line in text.splitlines():
        line = _strip_assembly_comment(raw_line).strip()
        if not line:
            continue
        # Splat puts these scheduling directives at the top of every real
        # function. They describe the assembler, not target instructions or
        # embedded data. Unknown directives still refuse rendering below.
        if re.fullmatch(r"\.set\s+(?:noat|noreorder|nomacro)", line):
            continue
        if _ASM_DATA_DIRECTIVE.match(line) or (_ASM_RELOCATION.search(line) and not retain_relocations and not _is_supported_api_relocation(line) and not _is_supported_data_relocation(line) and not _is_supported_global_relocation(line) and not _is_supported_linker_relocation(line)):
            # Preserve a deterministic query shape while marking the target
            # context as non-renderable.  The renderer will turn this typed
            # shape into target_context_unsupported, and the raw line never
            # reaches generated C or donor claims.
            instructions.append(_Instruction("unsupported", "", pending_label, True))
            pending_label = None
            continue
        # objdump listings carry an address and instruction word before the
        # mnemonic.  Keeping only the mnemonic and operands avoids addresses
        # and branch displacements in semantic selectors and generated source.
        objdump = re.match(
            r"^(?:[0-9A-Fa-f]+:\s+)?(?:[0-9A-Fa-f]{8}\s+)?"
            r"(?P<mn>[A-Za-z][A-Za-z0-9.]*)\s*(?P<ops>.*)$",
            line,
        )
        label_match = re.match(r"^(?P<label>[A-Za-z_.$][A-Za-z0-9_.$]*):(?:\s*(?P<tail>.*))$", line)
        if label_match:
            if pending_label is not None:
                instructions.append(_Instruction("unsupported", "", pending_label, True))
            pending_label = label_match.group("label")
            line = (label_match.group("tail") or "").strip()
            if not line:
                continue
            if _ASM_DATA_DIRECTIVE.match(line) or (_ASM_RELOCATION.search(line) and not retain_relocations and not _is_supported_api_relocation(line) and not _is_supported_data_relocation(line) and not _is_supported_global_relocation(line) and not _is_supported_linker_relocation(line)):
                instructions.append(_Instruction("unsupported", "", pending_label, True))
                pending_label = None
                continue
            objdump = re.match(
                r"^(?:[0-9A-Fa-f]+:\s+)?(?:[0-9A-Fa-f]{8}\s+)?"
                r"(?P<mn>[A-Za-z][A-Za-z0-9.]*)\s*(?P<ops>.*)$",
                line,
            )
        if not objdump:
            # Function-body metadata (symbol sizes, frame descriptions, line
            # markers) carries no dataflow. The renderer independently
            # verifies prologue and epilogue behavior, so skipping these is
            # sound; anything else unparseable still refuses below.
            if _EMPTY_DIRECTIVE.match(line):
                pending_label = None
                continue
            instructions.append(_Instruction("unsupported", "", pending_label, True))
            pending_label = None
            continue
        mnemonic = objdump.group("mn").lower()
        operands = objdump.group("ops").strip()
        if mnemonic.startswith(".") or mnemonic in {
            "glabel",
            "section",
            "include",
            "size",
            "ent",
            "end",
            "frame",
            "mask",
            "fmask",
            "set",
            "loc",
            "word",
            "half",
            "byte",
            "ascii",
            "asciiz",
            "align",
        }:
            pending_label = None
            continue
        # The pattern above can treat a standalone label or macro as an
        # instruction.  Only actual mnemonic-like lines are retained.
        if not re.fullmatch(r"[a-z][a-z0-9.]*", mnemonic):
            pending_label = None
            continue
        if has_numeric_branch_target(mnemonic, operands) or (_ASM_RELOCATION.search(operands) and not _is_supported_api_relocation(operands) and not _is_supported_data_relocation(operands) and not _is_supported_global_relocation(operands) and not _is_supported_linker_relocation(operands)):
            instructions.append(_Instruction(mnemonic, operands, pending_label, True))
        else:
            instructions.append(_Instruction(mnemonic, operands, pending_label))
        pending_label = None
    if pending_label is not None:
        instructions.append(_Instruction("unsupported", "", pending_label, True))
    return tuple(instructions)


def _assembly_signatures(instructions: Sequence[_Instruction]) -> tuple[str, str, str]:
    semantic_instructions = tuple(
        SemanticInstruction(
            instruction.mnemonic,
            instruction.operands,
            instruction.unsupported,
        )
        for instruction in instructions
    )
    return assembly_signatures(semantic_instructions)


def _verified_target_signatures(
    context: _TargetContext,
    instructions: Sequence[_Instruction],
) -> tuple[str, str, str]:
    """Derive target selectors and reject stale stored selector claims.

    Target evidence may carry selectors as a convenience for a later loader,
    but those values are not an authority.  Recomputing them from the archived
    assembly keeps a forged or stale target index from redirecting donor query
    semantics while still allowing older evidence that omitted the optional
    fields to replay.
    """

    derived = _assembly_signatures(instructions)
    for name, stored, expected in zip(
        ("instruction_signature", "cfg_signature", "dataflow_signature"),
        (
            context.instruction_signature,
            context.cfg_signature,
            context.dataflow_signature,
        ),
        derived,
    ):
        if stored is None:
            continue
        try:
            validate_hash(stored, name)
        except SearchValidationError as exc:
            raise TargetEvidenceError(
                f"stored target {name} is not a content identity"
            ) from exc
        if stored != expected:
            raise TargetEvidenceError(
                f"stored target {name} differs from archived assembly"
            )
    return derived


def _version_for(recipient: Recipient, context: _TargetContext) -> Optional[str]:
    # ``DonorQuery.version`` filters the donor revision, not the target's
    # platform.  Production target queries intentionally leave it unset so
    # equivalent semantic claims from US, HD, PSPEU, and Saturn can be
    # reconciled by claim identity.  The recipient identity still binds the
    # target platform and subset exactly.
    del recipient, context
    return None


def _limit_for(recipient: Recipient, context: _TargetContext) -> int:
    raw = _value(
        context.declarations,
        "donor_query_limit",
        "query_limit",
        default=_value(recipient.metadata, "donor_query_limit", "query_limit"),
    )
    if raw is None:
        return _DEFAULT_LIMIT
    if isinstance(raw, bool) or not isinstance(raw, int) or not 1 <= raw <= 8:
        raise TargetRendererInputError("target query limit must be an integer from 1 through 8")
    return raw


def query_for_recipient(
    manifest: RunManifest | Mapping[str, Any],
    target_index: Any,
    recipient: Recipient,
) -> DonorQuery:
    """Build one donor query exclusively from archived target evidence."""

    typed_manifest = _coerce_manifest(manifest)
    context = _target_context(target_index, typed_manifest, recipient)
    try:
        assembly_text = context.assembly_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TargetEvidenceError("target assembly is not UTF-8 text") from exc
    instructions = _parse_assembly(assembly_text)
    if not instructions:
        raise TargetEvidenceError("target assembly has no instructions")
    derived_instruction, derived_cfg, derived_dataflow = _verified_target_signatures(
        context,
        instructions,
    )
    return make_donor_query(
        recipient_id=recipient.recipient_id,
        version=None,
        # Target assembly paths and donor C paths are different namespaces.
        # Exact symbol search spans all donor paths; conflicting definitions
        # retain the query's ordinary ambiguity refusal.
        source_path=None,
        symbol=context.symbol or recipient.function,
        instruction_signature=derived_instruction,
        cfg_signature=derived_cfg,
        dataflow_signature=derived_dataflow,
        compiler_identity=typed_manifest.compiler_identity,
        config_identity=typed_manifest.config_identity,
        limit=_limit_for(recipient, context),
    )


def _claim_tuple(recipient: Recipient, claims: Any) -> tuple[DonorSemanticClaim, ...]:
    if not isinstance(claims, (tuple, list)):
        raise TargetRendererInputError(
            "target renderer claims must be an explicit tuple or list"
        )
    result: list[DonorSemanticClaim] = []
    seen: set[str] = set()
    for claim in claims:
        if not isinstance(claim, DonorSemanticClaim):
            raise TargetRendererInputError(
                "target renderer accepts DonorSemanticClaim values only"
            )
        # This is defensive against subclasses or caller-side attribute
        # injection.  The semantic claim protocol intentionally has no body,
        # source, provider, or version-specific fields.
        if any(hasattr(claim, name) for name in ("body", "source", "metadata", "registers", "relocations")):
            raise TargetRendererInputError(
                "target renderer received non-semantic donor context"
            )
        if claim.recipient_id != recipient.recipient_id:
            raise TargetRendererInputError(
                "semantic claim recipient differs from target recipient"
            )
        if not claim.compatible:
            raise TargetRendererInputError("target renderer cannot consume an incompatible claim")
        # Re-run the claim's own identity boundary before any declaration is
        # consulted.  This also canonicalizes nested JSON aliases.
        canonical = DonorSemanticClaim.from_dict(claim.to_dict())
        if canonical != claim:
            raise TargetRendererInputError("semantic claim is not canonical")
        for name, value in (
            ("declarations", claim.declarations),
            ("constants", claim.constants),
        ):
            _reject_forbidden_tree(value, "semantic claim." + name)
        if claim.claim_identity not in seen:
            seen.add(claim.claim_identity)
            result.append(claim)
    return tuple(sorted(result, key=lambda item: item.claim_identity))


def _safe_type(value: Any, label: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value or "\n" in value or ";" in value:
        raise TargetRendererInputError(label + " is not a safe C type")
    value = " ".join(value.split())
    if not _C_TYPE.fullmatch(value):
        raise TargetRendererInputError(label + " is not a safe C type")
    return value


def _safe_parameters(
    value: Any,
    label: str,
    *,
    reject_abi_names: bool = False,
) -> Optional[list[tuple[str, str]]]:
    if value is None:
        return None
    if not isinstance(value, (tuple, list)):
        raise TargetRendererInputError(label + " must be a sequence")
    result: list[tuple[str, str]] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            bits = item.strip().split()
            if len(bits) < 2:
                raise TargetRendererInputError(f"{label}[{index}] needs a type and name")
            name = bits[-1]
            type_name = " ".join(bits[:-1])
        elif isinstance(item, Mapping):
            name = item.get("name")
            type_name = item.get("type", item.get("declaration"))
        else:
            raise TargetRendererInputError(f"{label}[{index}] has an invalid shape")
        if not isinstance(name, str) or not _C_IDENTIFIER.fullmatch(name):
            raise TargetRendererInputError(f"{label}[{index}] has an invalid name")
        if reject_abi_names and name.lower() in _ABI_PARAMETER_POSITIONS:
            raise TargetRendererInputError(
                f"{label}[{index}] uses an ABI register name without a target declaration"
            )
        checked_type = _safe_type(type_name, f"{label}[{index}].type")
        if checked_type is None:
            raise TargetRendererInputError(f"{label}[{index}] has no type")
        result.append((checked_type, name))
    return result


def _declaration_context(
    context: _TargetContext,
    claims: Sequence[DonorSemanticClaim],
) -> tuple[str, list[tuple[str, str]]]:
    target_declarations = dict(context.declarations)
    return_type = _safe_type(
        target_declarations.get("return_type", target_declarations.get("result_type", "int")),
        "target return_type",
    ) or "int"
    parameters = _safe_parameters(
        target_declarations.get("parameters", target_declarations.get("params")),
        "target parameters",
    )
    prototype = target_declarations.get("prototype", target_declarations.get("signature"))
    if prototype is not None:
        if (
            not isinstance(prototype, str)
            or "{" in prototype
            or "}" in prototype
            or ";" in prototype
            or "\n" in prototype
        ):
            raise TargetRendererInputError("target prototype is not a declaration")
        match = re.match(
            r"^\s*(?P<ret>[A-Za-z_]\w*(?:\s+[A-Za-z_]\w*)*(?:\s*\*)*)\s+"
            r"(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^()]*)\)\s*$",
            prototype,
        )
        if not match or match.group("name") != context.symbol:
            raise TargetRendererInputError("target prototype does not bind the target symbol")
        return_type = _safe_type(match.group("ret"), "target prototype return type") or "int"
        if parameters is None:
            raw_params = match.group("params").strip()
            if not raw_params or raw_params == "void":
                parameters = []
            else:
                parameters = _safe_parameters(
                    [part.strip() for part in raw_params.split(",")],
                    "target prototype parameters",
                )
    # Claims can supply declaration facts only when the target left that fact
    # unspecified.  No claim source, body, register, relocation, or literal is
    # consulted for generation.
    if parameters is None:
        for claim in claims:
            claim_declarations = dict(claim.declarations)
            if "parameters" in claim_declarations or "params" in claim_declarations:
                parameters = _safe_parameters(
                    claim_declarations.get("parameters", claim_declarations.get("params")),
                    "semantic claim parameters",
                    reject_abi_names=True,
                )
                break
    for claim in claims:
        if prototype is None and "return_type" not in target_declarations and "result_type" not in target_declarations:
            candidate_type = dict(claim.declarations).get(
                "return_type", dict(claim.declarations).get("result_type")
            )
            if candidate_type is not None:
                return_type = _safe_type(candidate_type, "semantic claim return type") or return_type
                break
    return return_type, parameters if parameters is not None else []


def _register_operands(operands: str) -> tuple[str, ...]:
    return tuple(
        match.group(1).removeprefix("$").lower()
        for match in _REGISTER.finditer(operands)
    )


def _target_parameter_for_register(
    register: str,
    parameters: Sequence[tuple[str, str]],
) -> Optional[str]:
    """Map a supported ABI argument register to its target parameter name.

    Assembly register spellings are implementation details.  The target C
    declaration, when present, is the only source of names that may reach the
    generated body.  A missing declaration is therefore an unsupported shape,
    not an invitation to invent ``a0`` or ``a1`` parameters.
    """

    position = _ABI_PARAMETER_POSITIONS.get(register.lower())
    if position is None or position >= len(parameters):
        return None
    return parameters[position][1]


def _literal_operand(operands: str) -> Optional[int]:
    values = _NUMBER.findall(operands)
    if not values:
        return None
    try:
        return int(values[-1], 0)
    except ValueError:
        return None


@dataclass(frozen=True)
class _PointerValue:
    kind: str
    expression: str




_COND_BRANCHES = frozenset({"beq", "bne", "beqz", "bnez", "bltz", "bgez", "bgtz", "blez"})
_CONTROL_OPS = _COND_BRANCHES | frozenset({"b", "j", "jr", "jal", "jalr"})
_LOOP_BARRED_OPS = frozenset({"mult", "multu", "div", "divu", "mflo", "mfhi"})
_LOOP_LOAD_OPS = frozenset({"lw", "lh", "lhu", "lb", "lbu"})
_LOOP_STORE_OPS = frozenset({"sw", "sh", "sb"})
_NEGATED_BRANCH = {"beq": "bne", "bne": "beq", "beqz": "bnez", "bnez": "beqz",
                   "bltz": "bgez", "bgez": "bltz", "bgtz": "blez", "blez": "bgtz"}


def _build_reg_aliases() -> dict:
    """Canonical register spellings shared by lowering and analysis.

    Single source for numeric and ABI names so region access sets cannot
    drift from the value machine below.
    """
    aliases = {"0": "zero", "r0": "zero", "2": "v0", "r2": "v0",
               "3": "v1", "r3": "v1", "31": "ra", "r31": "ra"}
    aliases.update({str(4 + i): "a" + str(i) for i in range(4)})
    aliases.update({"r" + str(4 + i): "a" + str(i) for i in range(4)})
    aliases.update({str(16 + i): "s" + str(i) for i in range(8)})
    aliases.update({"r" + str(16 + i): "s" + str(i) for i in range(8)})
    aliases.update({"29": "sp", "r29": "sp", "1": "at", "r1": "at"})
    for number, name in (*((8 + i, "t" + str(i)) for i in range(8)), (24, "t8"), (25, "t9")):
        aliases.update({str(number): name, "r" + str(number): name})
    return aliases


_REG_ALIASES = _build_reg_aliases()


def _canonical_reg(operand: str) -> str:
    """Normalize one register spelling exactly like the value machine."""
    value = operand.strip().removeprefix("$").lower()
    return _REG_ALIASES.get(value, value)


def _operand_regs(text: str) -> list[str]:
    """Canonical registers mentioned anywhere in an operand string."""
    return [_canonical_reg(match) for match in re.findall(r"\$[A-Za-z0-9]+", text or "")]


def _branch_target_index(instructions, labels: dict, index: int):
    """Label index a branch jumps to, or None when malformed or unbound.

    Mirrors the arity and binding checks of the lowering path below.
    """
    item = instructions[index]
    if item.mnemonic not in _COND_BRANCHES | {"b", "j"}:
        return None
    expected = 3 if item.mnemonic in {"beq", "bne"} else 1 if item.mnemonic in {"b", "j"} else 2
    args = tuple(part.strip() for part in item.operands.split(",")) if item.operands else ()
    if len(args) != expected or args[-1] not in labels:
        return None
    return labels[args[-1]]


def region_flow(instructions, start: int, end: int) -> tuple[set, set, set, set]:
    """Register use order over the half-open span [start, end).

    Pure helper for loop-carried analysis. Returns reads, writes,
    pure-written registers, and registers read before any define.
    Memory loads define fresh per-iteration values; every other define
    carries iteration state. Stores and branches only read. Malformed
    spans yield empty sets.
    """
    reads: set = set()
    writes: set = set()
    pure: set = set()
    read_first: set = set()
    try:
        span = instructions[start:end]
    except (TypeError, IndexError):
        return reads, writes, pure, read_first
    defined: set = set()
    for item in span:
        mnemonic = item.mnemonic
        operands = item.operands or ""
        if mnemonic in _LOOP_STORE_OPS or mnemonic in _COND_BRANCHES or mnemonic in {"b", "j", "jr", "jal", "jalr"} or not operands:
            for reg in _operand_regs(operands):
                reads.add(reg)
                if reg not in defined:
                    read_first.add(reg)
            continue
        args = [part.strip() for part in operands.split(",")]
        if args and args[0].startswith("$"):
            dest = _canonical_reg(args[0])
            for reg in _operand_regs(",".join(args[1:])):
                reads.add(reg)
                if reg not in defined:
                    read_first.add(reg)
            writes.add(dest)
            defined.add(dest)
            if mnemonic not in _LOOP_LOAD_OPS:
                pure.add(dest)
        else:
            for reg in _operand_regs(operands):
                reads.add(reg)
                if reg not in defined:
                    read_first.add(reg)
    return reads, writes, pure, read_first


def _same_exit_target(instructions, labels, exits) -> bool:
    """Whether every forward exit leaves the loop at one continuation. Pure helper."""
    first = _branch_target_index(instructions, labels, exits[0])
    return first is not None and all(
        _branch_target_index(instructions, labels, k) == first for k in exits[1:])


def loop_regions(instructions, *, allow_calls=False) -> tuple[list, list]:
    """Admitted do-while regions plus refusal reasons for a function.

    Pure structural helper shared by lowering and measurement. Calls may be
    admitted structurally; target-owned declarations and ABI validity are
    checked by the same call lowerer used outside loops. Structural admission
    is never a claim that a complete function can render.
    """
    labels: dict = {}
    for index, item in enumerate(instructions):
        if item.label:
            if item.label in labels:
                return [], ["duplicate-label"]
            labels[item.label] = index
    candidates = []
    refused: list = []
    for index, item in enumerate(instructions):
        if item.mnemonic not in _COND_BRANCHES | {"b", "j"}:
            continue
        target = _branch_target_index(instructions, labels, index)
        if target is None:
            continue
        if target == index + 1:
            refused.append("delay-entry")
            continue
        if target == index:
            refused.append("degenerate-latch")
            continue
        if target > index:
            continue
        if item.mnemonic in {"b", "j"}:
            candidates.append((target, index, False))
            continue
        candidates.append((target, index, True))
    admitted = []
    for start, branch, latch_cond in sorted(candidates):
        slot = branch + 1
        if slot >= len(instructions):
            refused.append("missing-slot")
            continue
        if instructions[slot].mnemonic in _CONTROL_OPS:
            refused.append("delay-control")
            continue
        if instructions[slot].mnemonic in _LOOP_LOAD_OPS:
            slot_args = (instructions[slot].operands or "").split(",")
            slot_dest = _canonical_reg(slot_args[0]) if slot_args and slot_args[0].strip().startswith("$") else None
            top_reads = set(region_flow(instructions, start, start + 1)[0])
            if slot_dest is not None and slot_dest in top_reads:
                refused.append("delay-hazard")
                continue
        exits = []
        for k in range(start, branch):
            item_k = instructions[k]
            if item_k.mnemonic not in _COND_BRANCHES:
                continue
            exit_target = _branch_target_index(instructions, labels, k)
            if exit_target is not None and exit_target > slot:
                exits.append(k)
        if not latch_cond:
            if not exits:
                refused.append("while-no-exit")
                continue
            if len(exits) > 1 and not _same_exit_target(instructions, labels, exits):
                refused.append("multi-exit")
                continue
            kind = "while"
        elif len(exits) > 1:
            if not _same_exit_target(instructions, labels, exits):
                refused.append("multi-exit")
                continue
            kind = "do-break"
        else:
            kind = "do-while" if not exits else "do-break"
        nested = []
        for k in range(start + 1, branch):
            inner = instructions[k]
            if inner.mnemonic not in _COND_BRANCHES | {"b", "j"}:
                continue
            inner_target = _branch_target_index(instructions, labels, k)
            if inner_target is None or not start <= inner_target < k:
                continue
            inner_slot = k + 1
            if inner_slot >= branch or inner_slot >= len(instructions):
                continue
            if instructions[inner_slot].mnemonic in _CONTROL_OPS:
                continue
            contained = True
            for j in range(inner_target, inner_slot + 1):
                if j == k:
                    continue
                op_j = instructions[j].mnemonic
                if op_j == "jal":
                    continue
                if op_j in _COND_BRANCHES | {"b", "j", "jr", "jalr"}:
                    tgt = _branch_target_index(instructions, labels, j)
                    if tgt is None or not inner_target <= tgt <= inner_slot:
                        contained = False
                        break
            if not contained:
                continue
            nested.append((inner_target, k))
        nested_spans = sorted((ns, nb + 1) for (ns, nb) in nested)
        for x in range(len(nested_spans)):
            for y in range(x + 1, len(nested_spans)):
                (aa, bb), (cc, dd) = nested_spans[x], nested_spans[y]
                if cc <= bb < dd:
                    nested_spans = []
                    break
        nested_starts = {ns for (ns, ne) in nested_spans}
        inner_bad = None
        inner_reason = "branch-in-loop"
        joins = set()
        returns = []
        for k in range(start, branch):
            item_k = instructions[k]
            if any(ns <= k <= ne for (ns, ne) in nested_spans):
                continue
            if item_k.mnemonic not in _CONTROL_OPS or k in exits:
                continue
            inner_target = _branch_target_index(instructions, labels, k)
            if item_k.mnemonic in {"jal", "jalr"}:
                if (allow_calls and k + 1 < branch
                        and instructions[k + 1].mnemonic not in _CONTROL_OPS):
                    continue
                inner_reason = "call-in-loop"
            elif item_k.mnemonic == "jr":
                jr_regs = [_canonical_reg(part.strip())
                           for part in (item_k.operands or "").split(",")]
                if (jr_regs != ["ra"] or not k + 1 < branch
                        or instructions[k + 1].mnemonic in _CONTROL_OPS):
                    inner_reason = "return-in-loop"
                else:
                    returns.append(k)
                    continue
            elif inner_target is not None and inner_target < k:
                inner_reason = "nested-loop"
            elif (item_k.mnemonic in _COND_BRANCHES and inner_target is not None
                    and exits and k < exits[0] < inner_target):
                inner_reason = "crossing-branch"
            elif (item_k.mnemonic in _COND_BRANCHES and inner_target is not None
                    and k + 1 < inner_target <= (exits[0] if exits and k < exits[0] else branch)
                    and instructions[k + 1].mnemonic not in _CONTROL_OPS
                    and instructions[inner_target - 1].mnemonic not in _CONTROL_OPS
                    and not any(ns <= inner_target <= ne for (ns, ne) in nested_spans)):
                joins.add(k)
                continue
            inner_bad = k
            break
        if inner_bad is not None:
            refused.append(inner_reason)
            continue
        if len(exits) > 1 and joins:
            # Join-plus-multi-exit composition is deferred; each shape is
            # proven separately first.
            refused.append("branch-in-loop")
            continue
        if any(instructions[k].mnemonic in _LOOP_BARRED_OPS for k in range(start, slot + 1)):
            refused.append("barred-op")
            continue
        if start > 0 and instructions[start - 1].mnemonic in _CONTROL_OPS:
            refused.append("delay-entry")
            continue
        if _touches_frame(instructions, start, slot + 1):
            refused.append("frame-adjust")
            continue
        if exits and any(_branch_target_index(instructions, labels, k) != slot + 1
                         for k in exits):
            refused.append("nonlocal-exit")
            continue
        outside = False
        for j, other in enumerate(instructions):
            if j == branch or j in joins or other.mnemonic not in _COND_BRANCHES | {"b", "j"}:
                continue
            if any(ns <= j <= ne for (ns, ne) in nested_spans):
                continue
            other_target = _branch_target_index(instructions, labels, j)
            if other_target is None:
                continue
            if other_target == start or (start < other_target <= slot
                                         and other_target not in nested_starts):
                outside = True
                break
        if outside:
            refused.append("outside-entry")
            continue
        admitted.append({"start": start, "branch": branch, "slot": slot,
                         "kind": kind, "exit": exits[0] if exits else None,
                         "exits": list(exits), "returns": list(returns),
                         "nested": [ns for (ns, ne) in nested_spans]})
    return admitted, refused


def _touches_frame(instructions, start: int, end: int) -> bool:
    """Whether the span adjusts the stack pointer. Pure helper."""
    for item in instructions[start:end]:
        if item.mnemonic == "addiu" and "sp" in {name.lower() for name in _operand_regs(item.operands or "")}:
            return True
    return False
def _leaf_body(instructions, parameters, return_type, callees=None, layouts=None, switches=None, apis=None, limits=None, datas=None, gdata=None, linker=None):
    """Lower bounded MIPS scalar paths without losing delay-slot dataflow.

    Values are unsigned 32-bit C expressions. Signed comparisons explicitly
    reinterpret them as signed words; arithmetic therefore cannot acquire C
    signed-overflow undefined behavior. Forward paths are expanded separately,
    with a shared budget to bound joins and nested branches. The bounds
    argument selects a validated RendererLimits; None means the canonical
    DEFAULT_LIMITS, which is what production archived runs always use.
    """
    bounds = _coerce_limits(limits)
    scalar_types = {"int", "signed int", "unsigned int", "s32", "u32"}
    # Call and caller signatures additionally admit short, narrow, boolean
    # and game-enum integer types. Values stay unsigned 32-bit C
    # expressions; the checksum oracle judges whether the admitted shape
    # matches, so wider admission cannot produce a false claim.
    call_scalars = scalar_types | {"s16", "u16", "s8", "u8", "char", "signed char", "unsigned char", "short", "signed short", "unsigned short", "bool", "PrimitiveType"}
    layouts = layouts or {}
    switches = switches or {}
    if (return_type not in call_scalars | {"void"} | set(layouts) or len(parameters) > 4
            or any(kind not in call_scalars and kind not in layouts for kind, _ in parameters)
            or len({name for _, name in parameters}) != len(parameters)
            or not 0 < len(instructions) <= bounds.max_instructions
            or any(item.unsupported for item in instructions)):
        return None
    aliases = dict(_REG_ALIASES)
    writable = {"v0", "v1", "at", *("a" + str(i) for i in range(4)),
                *("t" + str(i) for i in range(10))}
    preserved = {"s" + str(i) for i in range(8)}
    volatile = set(writable)
    writable.update(preserved)
    callees = callees or {}
    apis = apis or {}
    datas = datas or {}
    gdata = gdata or {}
    prototypes, temporaries = {}, []
    linker = linker or {}
    reserved_names = {name for _, name in parameters} | set(callees) | set(apis) | {name for name in datas if isinstance(name, str)} | {name for name in gdata if isinstance(name, str)} | {name for name in linker if isinstance(name, str)}
    data_ptrs, data_externs = {}, {}
    for data_name, declaration in datas.items():
        # Only identifier-safe declared data resolves to an address value.
        # Anything else refuses at its use site, never here.
        if (not isinstance(data_name, str) or not re.fullmatch(r"D_[A-Za-z_]\w*", data_name)
                or not isinstance(declaration, Mapping) or declaration.get("status") != "declared"):
            continue
        data_type = declaration.get("type")
        if not isinstance(data_type, str):
            continue
        pointer_kind = re.sub(r"\s*\*\s*", "*", data_type) + "*"
        if pointer_kind not in layouts:
            continue
        dims = declaration.get("dims", "")
        if not isinstance(dims, str):
            continue
        data_ptrs[data_name] = _PointerValue(layouts[pointer_kind]["canonical"],
                                             data_name if dims else "(&" + data_name + ")")
        data_externs[data_name] = "    extern " + data_type + " " + data_name + dims + ";"
    global_ptrs, global_externs = {}, {}
    for global_name, declaration in gdata.items():
        if (not isinstance(global_name, str) or not re.fullmatch(r"g_(?!api_)[A-Za-z_]\w*", global_name)
                or not isinstance(declaration, Mapping) or declaration.get("status") != "declared"):
            continue
        global_type = declaration.get("type")
        if not isinstance(global_type, str):
            continue
        global_kind = re.sub(r"\s*\*\s*", "*", global_type) + "*"
        if global_kind not in layouts:
            continue
        global_dims = declaration.get("dims", "")
        if not isinstance(global_dims, str):
            continue
        global_ptrs[global_name] = _PointerValue(layouts[global_kind]["canonical"],
                                                 global_name if global_dims else "(&" + global_name + ")")
        global_externs[global_name] = "    extern " + global_type + " " + global_name + global_dims + ";"
    linker_ptrs, linker_externs, linker_widths = {}, {}, {}
    for linker_name, declaration in linker.items():
        if (not isinstance(linker_name, str) or not re.fullmatch(r"(?:PLAYER_|RIC_)[A-Za-z_]\w*", linker_name)):
            continue
        if not isinstance(declaration, Mapping) or declaration.get("status") != "declared":
            continue
        linker_type = declaration.get("type")
        if not isinstance(linker_type, str):
            continue
        linker_kind = re.sub(r"\s*\*\s*", "*", linker_type) + "*"
        if linker_kind not in layouts:
            continue
        linker_dims = declaration.get("dims", "")
        if not isinstance(linker_dims, str):
            continue
        linker_ptrs[linker_name] = _PointerValue(layouts[linker_kind]["canonical"],
                                                 linker_name if linker_dims else "(&" + linker_name + ")")
        linker_externs[linker_name] = "    extern " + linker_type + " " + linker_name + linker_dims + ";"
    labels = {}
    for index, item in enumerate(instructions):
        if item.label:
            if item.label in labels:
                return None
            labels[item.label] = index
    conditional = set(_COND_BRANCHES)
    controls = set(_CONTROL_OPS)
    slots = {i + 1 for i, item in enumerate(instructions) if item.mnemonic in controls}
    state = {"zero": "0", "ra": "@entry-ra", "stack_offset": 0, "frame_size": 0}
    state.update({name: "@entry-" + name for name in preserved})
    state.update({"a" + str(i): "(unsigned int)" + name if kind in call_scalars else _PointerValue(layouts[kind]["canonical"], name)
                  for i, (kind, name) in enumerate(parameters)})
    visited, budget = set(), [bounds.path_budget]

    def register(value):
        value = value.strip().removeprefix("$").lower()
        return aliases.get(value, value)

    def immediate(value, low, high):
        # Splat folds assembler constant expressions before encoding;
        # folding here models the identical value at every use site.
        number = _fold_const_expr(value)
        if number is None:
            raise ValueError("not an immediate")
        if not low <= number <= high:
            raise ValueError("immediate out of range")
        return number

    def literal(value):
        value &= 0xFFFFFFFF
        return str(value) + ("U" if value > 0x7FFFFFFF else "")

    def operands(item):
        return tuple(part.strip() for part in item.operands.split(",")) if item.operands else ()

    def value_for(values, operand):
        value = values[register(operand)]
        if isinstance(value, _PointerValue) or "@" in value:
            raise ValueError("uninitialized preserved value")
        return value

    def pointer_expression(value, kind):
        if value == "0":
            return "0"
        if isinstance(value, _PointerValue) and value.kind == kind:
            return value.expression
        raise ValueError("pointer value differs from US data type")

    def advance_pointer(pointer, amount):
        if amount == 0:
            return pointer
        size = layouts[pointer.kind]["size"]
        if size <= 0 or amount % size or not -32768 <= amount <= 32767:
            raise ValueError("pointer advance is not a bounded whole element")
        return _PointerValue(pointer.kind, "((" + pointer.expression + ") + (" + str(amount // size) + "))")

    def constant_word(value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]+U?", value):
            raise ValueError("pointer offset is not a known constant")
        number = int(value.removesuffix("U"))
        return number if number < 0x80000000 else number - 0x100000000

    def new_temporary(prefix, kind="unsigned int"):
        name = prefix + str(len(temporaries))
        while name in reserved_names:
            name += "_"
        reserved_names.add(name)
        temporaries.append("    " + kind + " " + name + ";")
        return name

    def check_load_delay(index, destination):
        if destination == "zero" or index in slots:
            raise ValueError("unsupported load delay slot")
        if index + 1 < len(instructions) and destination in {
                register(reg) for reg in re.split(r"[,()\s]+", instructions[index + 1].operands)}:
            raise ValueError("load consumed before delay expires")

    def memory_access(pointer, offset, width, signed, store):
        layout = layouts[pointer.kind]
        if offset % width or layout["align"] < width:
            raise ValueError("unaligned pointer access")
        members = layout["members"]
        if layout["scalar"]:
            if offset % layout["size"]:
                raise ValueError("partial scalar pointer access")
            matches = [m for m in members if m["width"] == width]
            expression = "(" + pointer.expression + ")[" + str(offset // layout["size"]) + "]"
        else:
            matches = [m for m in members if m["offset"] == offset and m["width"] == width]
            expression = None
        if len(matches) != 1:
            raise ValueError("memory access has no unique named member")
        member = matches[0]
        if member.get("unsupported") or member.get("pointer_type") is not None and member["pointer_type"] not in layouts:
            raise ValueError("member has no supported US pointer binding")
        if store and not member["writable"]:
            raise ValueError("store through const-qualified target")
        # An unsigned load of a signed member (or conversely) needs an explicit
        # width cast. This also fixes plain-char behavior on host fixture builds.
        cast = ("signed" if signed else "unsigned") + " " + {1: "char", 2: "short", 4: "int"}[width]
        if expression is None:
            expression = "(*(" + pointer.expression + "))" + member["path"]
        return expression, cast, member.get("pointer_type")

    def step(index, values, lines, indent):
        item = instructions[index]
        op, args = item.mnemonic, operands(item)
        visited.add(index)
        if op == "nop" and not args:
            return
        if op == "break" and len(args) <= 1 and all(
                re.fullmatch(r"(?:0[xX][0-9a-fA-F]{1,5}|[0-9]{1,7})", part.strip()) for part in args):
            # Divide guards (break 7 for zero, break 6 for INT_MIN / -1)
            # are reproduced by the compiler from plain C division, and are
            # unreachable in correct execution. No state changes.
            return
        if op == "sll" and len(args) == 3 and register(args[0]) == register(args[1]) == "zero" and args[2] == "0":
            return
        if op == "addiu" and len(args) == 3 and register(args[0]) == register(args[1]) == "sp":
            amount = immediate(args[2], -4096, 4096)
            if amount < 0 and values["stack_offset"] == values["frame_size"] == 0 and amount % 8 == 0:
                values["frame_size"] = -amount
                values["stack_offset"] = amount
            elif amount > 0 and amount == values["frame_size"] == -values["stack_offset"]:
                values["stack_offset"] = 0
            else:
                raise ValueError("unsupported stack adjustment")
            return
        if op in {"sw", "sh", "sb", "lw", "lh", "lhu", "lb", "lbu"} and len(args) == 2:
            target_register = register(args[0])
            api_lo = re.fullmatch(r"%lo\s*\(\s*(g_api_[A-Za-z_]\w*)\s*\)\s*\(\s*(\$[A-Za-z0-9]+)\s*\)", args[1].strip())
            if api_lo is not None:
                if op != "lw":
                    raise ValueError("unsupported API access width")
                member, base = api_lo.group(1), register(api_lo.group(2))
                if values.get(base) != "@api-hi:" + member:
                    raise ValueError("API pointer halves are not paired")
                if target_register not in writable:
                    raise ValueError("unsupported API destination")
                check_load_delay(index, target_register)
                if target_register in materialize:
                    raise ValueError("loop-carried API handle")
                values[target_register] = "@api:" + member
                return
            linker_lo = re.fullmatch(r"%lo\s*\(\s*((?:PLAYER_|RIC_)[A-Za-z_]\w*)\s*\)\s*\(\s*(\$[A-Za-z0-9]+)\s*\)", args[1].strip())
            if linker_lo is not None:
                if op.startswith("s"):
                    raise ValueError("linker absolute store is deferred")
                _lsym, _lbase = linker_lo.group(1), register(linker_lo.group(2))
                if values.get(_lbase) != "@linker-hi:" + _lsym:
                    raise ValueError("linker halves are not paired")
                if target_register not in writable:
                    raise ValueError("unsupported linker destination")
                _lwidth = 4 if op == "lw" else 2 if op in {"lh", "lhu"} else 1 if op in {"lb", "lbu"} else None
                if _lwidth is None:
                    raise ValueError("unsupported linker access width")
                _lsigned = op in {"lb", "lh"}
                _lcast = ("signed" if _lsigned else "unsigned") + " " + {1: "char", 2: "short", 4: "int"}[_lwidth]
                if _lsym in linker_ptrs:
                    _ldecl = linker.get(_lsym, {})
                    _ltype = _ldecl.get("type") if isinstance(_ldecl, Mapping) else None
                    _lkind = re.sub(r"\s*\*\s*", "*", _ltype) + "*" if isinstance(_ltype, str) else None
                    if _lkind not in layouts or layouts[_lkind]["size"] != _lwidth or _ldecl.get("dims", "") != "":
                        raise ValueError("linker declaration width differs")
                    prototypes["linker:" + _lsym] = linker_externs[_lsym]
                    _lexpr = _lsym
                else:
                    _wtype = {"lb": "s8", "lbu": "u8", "lh": "s16", "lhu": "u16", "lw": "u32"}[op]
                    if _lsym in linker_widths and linker_widths[_lsym] != _wtype:
                        raise ValueError("linker width conflicts")
                    linker_widths[_lsym] = _wtype
                    prototypes["linker:" + _lsym] = "    extern " + _wtype + " " + _lsym + ";"
                    _lexpr = _lsym
                check_load_delay(index, target_register)
                if target_register in materialize:
                    _assign_carried(target_register, None, _lexpr, _lcast, values, lines, indent)
                    return
                _lname = new_temporary("memory_result_", "unsigned int")
                lines.append(indent + _lname + " = (unsigned int)(" + _lcast + ")(" + _lexpr + ");")
                values[target_register] = _lname
                return
            global_off_lo = re.fullmatch(r"%lo\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\+\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*\)\s*\(\s*(\$[A-Za-z0-9]+)\s*\)", args[1].strip())
            if global_off_lo is not None:
                if op.startswith("s"):
                    raise ValueError("global offset store is deferred")
                if op not in {"lb", "lbu"}:
                    raise ValueError("global offset width is deferred")
                _gosym, _goofftext, _gobase = global_off_lo.group(1), global_off_lo.group(2), register(global_off_lo.group(3))
                _gooff = _fold_const_expr(_goofftext)
                if _gooff is None or values.get(_gobase) != "@global-offhi:" + _gosym + "+" + str(_gooff):
                    raise ValueError("global offset halves are not paired")
                if target_register not in writable or _gosym not in global_ptrs:
                    raise ValueError("global offset load is unavailable")
                _gdecl = gdata.get(_gosym, {})
                _gtype = _gdecl.get("type") if isinstance(_gdecl, Mapping) else None
                _gkind = re.sub(r"\s*\*\s*", "*", _gtype) + "*" if isinstance(_gtype, str) else None
                if _gkind not in layouts or layouts[_gkind]["size"] != 1:
                    raise ValueError("global offset element is not a byte")
                prototypes["global:" + _gosym] = global_externs[_gosym]
                _gocast = ("signed char" if op == "lb" else "unsigned char")
                check_load_delay(index, target_register)
                if target_register in materialize:
                    _assign_carried(target_register, None, _gosym + "[" + str(_gooff) + "]", _gocast, values, lines, indent)
                    return
                _goname = new_temporary("memory_result_", "unsigned int")
                lines.append(indent + _goname + " = (unsigned int)(" + _gocast + ")(" + _gosym + "[" + str(_gooff) + "]);")
                values[target_register] = _goname
                return
            memory = re.fullmatch(r"(-?(?:0[xX][0-9A-Fa-f]+|[0-9]+))\(([^()]+)\)", args[1])
            if not memory or target_register not in writable | {"ra", "zero"}:
                raise ValueError("unsupported memory access")
            if register(memory[2]) != "sp":
                pointer = values.get(register(memory[2]))
                if not isinstance(pointer, _PointerValue) or target_register == "ra":
                    raise ValueError("memory base has no US pointer type")
                width = 4 if op in {"sw", "lw"} else 2 if op in {"sh", "lh", "lhu"} else 1
                store = op.startswith("s")
                offset = immediate(memory[1], -32768, 32767)
                expression, cast, pointer_type = memory_access(pointer, offset, width, op in {"lb", "lh"}, store)
                if store:
                    value = pointer_expression(values[target_register], pointer_type) if pointer_type else (
                        "(" + cast + ")(" + value_for(values, args[0]) + ")")
                    lines.append(indent + expression + " = " + value + ";")
                else:
                    check_load_delay(index, target_register)
                    if target_register in materialize:
                        _assign_carried(target_register, pointer_type, expression, cast, values, lines, indent)
                        return
                    name = new_temporary("memory_result_", pointer_type or "unsigned int")
                    if pointer_type:
                        lines.append(indent + name + " = " + expression + ";")
                        values[target_register] = _PointerValue(pointer_type, name)
                    else:
                        lines.append(indent + name + " = (unsigned int)(" + cast + ")(" + expression + ");")
                        values[target_register] = name
                return
            if op not in {"sw", "lw"}:
                raise ValueError("partial stack access")
            offset = values["stack_offset"] + immediate(memory[1], -4096, 4096)
            if values["stack_offset"] == 0 or offset % 4 or not -values["frame_size"] <= offset <= -4:
                raise ValueError("stack access outside owned frame")
            slot = "stack:" + str(offset)
            if op == "sw":
                if loop_active[0]:
                    raise ValueError("loop stack writes require stack phi values")
                values[slot] = values[target_register]
            else:
                check_load_delay(index, target_register)
                if target_register in materialize or loop_active[0] and target_register in writable:
                    _define(target_register, values[slot], values, lines, indent)
                else:
                    values[target_register] = values[slot]
            return
        if op in {"mult", "multu", "div", "divu"} and (
                len(args) == 2 or len(args) == 3 and register(args[0]) == "zero"):
            # Integer multiply/divide latches HI/LO without emitting C. The
            # pending triple lives beside the register file so branch paths
            # copy it; a later mult/div overwrites it, matching hardware.
            # Generic value sites never observe the tuple: no GPR is named
            # mul, and every consumer below validates the shape explicitly.
            # Three-operand divide spells the ignored rd field ($zero).
            operands2 = args[-2:]
            left = value_for(values, operands2[0])
            right = value_for(values, operands2[1])
            values["mul"] = (op, left, right)
            return
        if not args or register(args[0]) not in writable:
            raise ValueError("not a scratch-register assignment")
        destination = register(args[0])
        if op == "li" and len(args) == 2:
            value = literal(immediate(args[1], -0x80000000, 0xFFFFFFFF))
        elif op == "lui" and len(args) == 2:
            hi_match = re.fullmatch(r"%hi\s*\(\s*(g_api_[A-Za-z_]\w*)\s*\)", args[1].strip())
            data_hi = re.fullmatch(r"%hi\s*\(\s*(D_[A-Za-z0-9_.$]*)\s*\)", args[1].strip())
            global_hi = re.fullmatch(r"%hi\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\)", args[1].strip())
            linker_hi = re.fullmatch(r"%hi\s*\(\s*((?:PLAYER_|RIC_)[A-Za-z_]\w*)\s*\)", args[1].strip())
            global_off_hi = re.fullmatch(r"%hi\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\+\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*\)", args[1].strip())
            if hi_match is not None:
                value = "@api-hi:" + hi_match.group(1)
            elif data_hi is not None:
                if data_hi.group(1) not in data_ptrs:
                    raise ValueError("data declaration is unavailable")
                value = "@data-hi:" + data_hi.group(1)
            elif global_hi is not None:
                if global_hi.group(1) not in global_ptrs:
                    raise ValueError("global declaration is unavailable")
                value = "@global-hi:" + global_hi.group(1)
            elif linker_hi is not None:
                value = "@linker-hi:" + linker_hi.group(1)
            elif global_off_hi is not None:
                _osym, _offtext = global_off_hi.group(1), global_off_hi.group(2)
                _off = _fold_const_expr(_offtext)
                if _osym not in global_ptrs or _off is None or not 0 <= _off < 4096:
                    raise ValueError("global offset address is unavailable")
                value = "@global-offhi:" + _osym + "+" + str(_off)
            else:
                value = literal(immediate(args[1], 0, 0xFFFF) << 16)
        elif op == "move" and len(args) == 2:
            value = values[register(args[1])]
            if not isinstance(value, _PointerValue):
                value = value_for(values, args[1])
        elif op == "addiu" and len(args) == 3 and (re.fullmatch(r"%lo\s*\(\s*(D_[A-Za-z0-9_.$]*)\s*\)", args[2].strip()) is not None):
            # Data address computation: lui %hi(D) paired with addiu %lo(D).
            data_lo = re.fullmatch(r"%lo\s*\(\s*(D_[A-Za-z0-9_.$]*)\s*\)", args[2].strip())
            data_symbol = data_lo.group(1)
            data_base = register(args[1])
            if values.get(data_base) != "@data-hi:" + data_symbol or data_symbol not in data_ptrs:
                raise ValueError("data address halves are not paired")
            prototypes["data:" + data_symbol] = data_externs[data_symbol]
            _define(destination, data_ptrs[data_symbol], values, lines, indent)
            return
        elif op == "addiu" and len(args) == 3 and (re.fullmatch(r"%lo\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\)", args[2].strip()) is not None):
            # Global address computation: lui %hi(g) paired with addiu %lo(g).
            _glo = re.fullmatch(r"%lo\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\)", args[2].strip())
            _gsym = _glo.group(1)
            _gbase = register(args[1])
            if values.get(_gbase) != "@global-hi:" + _gsym or _gsym not in global_ptrs:
                raise ValueError("global address halves are not paired")
            prototypes["global:" + _gsym] = global_externs[_gsym]
            _define(destination, global_ptrs[_gsym], values, lines, indent)
            return
        elif op == "addiu" and len(args) == 3 and (re.fullmatch(r"%lo\s*\(\s*((?:PLAYER_|RIC_)[A-Za-z_]\w*)\s*\)", args[2].strip()) is not None):
            # Absolute address computation: lui %hi(S) paired with addiu %lo(S).
            _llo = re.fullmatch(r"%lo\s*\(\s*((?:PLAYER_|RIC_)[A-Za-z_]\w*)\s*\)", args[2].strip())
            _lsym = _llo.group(1)
            _lbase = register(args[1])
            if values.get(_lbase) != "@linker-hi:" + _lsym or _lsym not in linker_ptrs:
                raise ValueError("linker address halves are not paired")
            prototypes["linker:" + _lsym] = linker_externs[_lsym]
            _define(destination, linker_ptrs[_lsym], values, lines, indent)
            return
        elif op == "addiu" and len(args) == 3 and (re.fullmatch(r"%lo\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\+\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*\)", args[2].strip()) is not None):
            # Global offset address: lui %hi(g+off) paired with addiu %lo(g+off).
            _golo = re.fullmatch(r"%lo\s*\(\s*(g_(?!api_)[A-Za-z_]\w*)\s*\+\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*\)", args[2].strip())
            _gosym, _gooff = _golo.group(1), _fold_const_expr(_golo.group(2))
            _gobase = register(args[1])
            if _gooff is None or values.get(_gobase) != "@global-offhi:" + _gosym + "+" + str(_gooff) or _gosym not in global_ptrs:
                raise ValueError("global offset halves are not paired")
            prototypes["global:" + _gosym] = global_externs[_gosym]
            _define(destination, advance_pointer(global_ptrs[_gosym], _gooff), values, lines, indent)
            return
        elif op == "addiu" and len(args) == 3 and isinstance(values.get(register(args[1])), _PointerValue):
            amount = immediate(args[2], -0x8000, 0xFFFF)
            value = advance_pointer(values[register(args[1])], amount if amount < 0x8000 else amount - 0x10000)
        elif op in {"addu", "subu", "or"} and len(args) == 3 and any(
                isinstance(values.get(register(arg)), _PointerValue) for arg in args[1:]):
            left, right = (values[register(arg)] for arg in args[1:])
            if not isinstance(left, _PointerValue) and op in {"addu", "or"}:
                left, right = right, left
            if not isinstance(left, _PointerValue):
                raise ValueError("integer minus pointer")
            amount = constant_word(right)
            if op == "or" and amount != 0:
                raise ValueError("pointer bit operation")
            value = advance_pointer(left, -amount if op == "subu" else amount)
        elif op in {"addiu", "andi", "ori", "xori", "slti", "sltiu", "sll", "srl", "sra"} and len(args) == 3:
            left = value_for(values, args[1])
            if op in {"sll", "srl", "sra"}:
                right = str(immediate(args[2], 0, 31))
                operator = "<<" if op == "sll" else ">>"
                if op == "sra":
                    left = "(int)(" + left + ")"
            else:
                signed = op in {"addiu", "slti", "sltiu"}
                number = immediate(args[2], -0x8000 if signed else 0, 0xFFFF)
                if signed and number >= 0x8000:
                    number -= 0x10000
                right = literal(number)
                operator = {"addiu": "+", "andi": "&", "ori": "|", "xori": "^", "slti": "<", "sltiu": "<"}[op]
                if op == "slti":
                    left, right = "(int)(" + left + ")", str(number)
            if op not in {"sra", "slti"}:
                left = "(unsigned int)(" + left + ")"
            value = "(unsigned int)((" + left + ") " + operator + " (" + right + "))"
            if register(args[1]) == "zero" and op in {"addiu", "ori"}:
                value = right
        elif op in {"mflo", "mfhi"} and len(args) == 1:
            pending = values.get("mul")
            if (not isinstance(pending, tuple) or len(pending) != 3
                    or pending[0] not in {"mult", "multu", "div", "divu"}):
                raise ValueError("HI/LO read without a producing multiply")
            kind, left, right = pending
            unsigned = "(unsigned int)(" + left + ")", "(unsigned int)(" + right + ")"
            signed = "(int)(" + left + ")", "(int)(" + right + ")"
            if op == "mflo" and kind in {"mult", "multu"}:
                # Low words of signed and unsigned products coincide.
                value = "(unsigned int)((" + unsigned[0] + ") * (" + unsigned[1] + "))"
            elif op == "mflo":
                sides = unsigned if kind == "divu" else signed
                value = "(unsigned int)((" + sides[0] + ") / (" + sides[1] + "))"
            elif kind == "mult":
                value = ("(unsigned int)(((long long)" + signed[0] + " * (long long)" + signed[1]
                         + ") >> 32)")
            elif kind == "multu":
                value = ("(unsigned int)(((unsigned long long)" + unsigned[0]
                         + " * (unsigned long long)" + unsigned[1] + ") >> 32)")
            else:
                sides = unsigned if kind == "divu" else signed
                value = "(unsigned int)((" + sides[0] + ") % (" + sides[1] + "))"
            if len(value) > bounds.max_expression:
                raise ValueError("expression expansion limit")
            _define(destination, value, values, lines, indent)
            return
        elif op == "negu" and len(args) == 2:
            # Unsigned negate: 0 minus the operand with no overflow trap.
            # The trapping `neg` pseudo-instruction stays unsupported.
            subtrahend = "(unsigned int)(" + value_for(values, args[1]) + ")"
            value = "(unsigned int)(((unsigned int)(0)) - (" + subtrahend + "))"
        elif op in {"addu", "subu", "and", "or", "xor", "nor", "slt", "sltu"} and len(args) == 3:
            left, right = (value_for(values, arg) for arg in args[1:])
            operator = {"addu": "+", "subu": "-", "and": "&", "or": "|", "xor": "^", "nor": "|", "slt": "<", "sltu": "<"}[op]
            if op == "slt":
                left, right = "(int)(" + left + ")", "(int)(" + right + ")"
            else:
                left = "(unsigned int)(" + left + ")"
            value = "((" + left + ") " + operator + " (" + right + "))"
            if op == "nor":
                value = "~" + value
            value = "(unsigned int)(" + value + ")"
        else:
            raise ValueError("unsupported leaf instruction")
        if len(value.expression if isinstance(value, _PointerValue) else value) > bounds.max_expression:
            raise ValueError("expression expansion limit")
        _define(destination, value, values, lines, indent)

    def lower_call(index, values, lines, indent):
        op, args = instructions[index].mnemonic, operands(instructions[index])
        if op == "jal":
            if (len(args) != 1 or args[0] not in callees or args[0] in labels
                    or args[0] in {name for _, name in parameters}):
                raise ValueError("call has no target-owned declaration")
            declaration = callees[args[0]]
            if declaration.get("status") != "declared":
                raise ValueError("call declaration is unavailable")
            result_type = declaration.get("return_type")
            call_parameters = _safe_parameters(declaration.get("parameters"), "callee parameters")
            if (result_type not in call_scalars | {"void"} | set(layouts) or call_parameters is None
                    or len(call_parameters) > 4 or any(kind not in call_scalars and kind not in layouts for kind, _ in call_parameters)):
                raise ValueError("unsupported call ABI")
            if values["stack_offset"] != -values["frame_size"] or values["frame_size"] < 16:
                raise ValueError("call requires outgoing argument area")
            # jal writes ra before its delay slot. Saving ra there saves
            # the local continuation, not the caller's original return.
            values["ra"] = "@call-return"
            step(index + 1, values, lines, indent)
            if values["stack_offset"] != -values["frame_size"]:
                raise ValueError("call delay slot released its frame")
            arguments = []
            for i, (kind, _) in enumerate(call_parameters):
                value = values["a" + str(i)]
                if kind in call_scalars:
                    arguments.append("(" + kind + ")(" + value_for(values, "a" + str(i)) + ")")
                elif kind in layouts:
                    arguments.append(pointer_expression(value, layouts[kind]["canonical"]))
                else:
                    raise ValueError("call pointer type differs from US declaration")
            parameter_text = ", ".join(kind for kind, _ in call_parameters) or "void"
            prototypes[args[0]] = "    extern " + result_type + " " + args[0] + "(" + parameter_text + ");"
            expression = args[0] + "(" + ", ".join(arguments) + ")"
            values.pop("mul", None)
            for name in volatile:
                values.pop(name, None)
            # A callee owns the four argument-home words even for zero args.
            for offset in range(values["stack_offset"], values["stack_offset"] + 16, 4):
                values.pop("stack:" + str(offset), None)
            if result_type == "void":
                lines.append(indent + expression + ";")
            else:
                if result_type in layouts:
                    kind = layouts[result_type]["canonical"]
                    name = new_temporary("call_result_", kind)
                    lines.append(indent + name + " = " + expression + ";")
                    _define("v0", _PointerValue(kind, name), values, lines, indent)
                else:
                    name = new_temporary("call_result_")
                    lines.append(indent + name + " = (unsigned int)" + expression + ";")
                    _define("v0", name, values, lines, indent)
            return
        if op == "jalr":
            if len(args) != 1:
                raise ValueError("unsupported indirect call shape")
            held = values.get(register(args[0]))
            if not isinstance(held, str) or not held.startswith("@api:"):
                raise ValueError("indirect call without target-owned API declaration")
            member = held.removeprefix("@api:")
            if not re.fullmatch(r"g_api_[A-Za-z_]\w*", member) or member not in apis:
                raise ValueError("call has no target-owned declaration")
            if member in labels or member in {name for _, name in parameters}:
                raise ValueError("call has no target-owned declaration")
            declaration = apis[member]
            if not isinstance(declaration, Mapping) or declaration.get("status") != "declared":
                raise ValueError("call declaration is unavailable")
            result_type = declaration.get("return_type")
            call_parameters = _safe_parameters(declaration.get("parameters"), "callee parameters")
            if (result_type not in call_scalars | {"void"} | set(layouts) or call_parameters is None
                    or len(call_parameters) > 4 or any(kind not in call_scalars and kind not in layouts for kind, _ in call_parameters)):
                raise ValueError("unsupported call ABI")
            if values["stack_offset"] != -values["frame_size"] or values["frame_size"] < 16:
                raise ValueError("call requires outgoing argument area")
            values["ra"] = "@call-return"
            step(index + 1, values, lines, indent)
            if values["stack_offset"] != -values["frame_size"]:
                raise ValueError("call delay slot released its frame")
            arguments = []
            for pos, (kind, _) in enumerate(call_parameters):
                value = values["a" + str(pos)]
                if kind in call_scalars:
                    arguments.append("(" + kind + ")(" + value_for(values, "a" + str(pos)) + ")")
                elif kind in layouts:
                    arguments.append(pointer_expression(value, layouts[kind]["canonical"]))
                else:
                    raise ValueError("call pointer type differs from US declaration")
            parameter_text = ", ".join(kind for kind, _ in call_parameters) or "void"
            prototypes[member] = "    extern " + result_type + " (*" + member + ")(" + parameter_text + ");"
            expression = member + "(" + ", ".join(arguments) + ")"
            values.pop("mul", None)
            for name in volatile:
                values.pop(name, None)
            for offset in range(values["stack_offset"], values["stack_offset"] + 16, 4):
                values.pop("stack:" + str(offset), None)
            if result_type == "void":
                lines.append(indent + expression + ";")
            else:
                if result_type in layouts:
                    kind = layouts[result_type]["canonical"]
                    name = new_temporary("call_result_", kind)
                    lines.append(indent + name + " = " + expression + ";")
                    _define("v0", _PointerValue(kind, name), values, lines, indent)
                else:
                    name = new_temporary("call_result_")
                    lines.append(indent + name + " = (unsigned int)" + expression + ";")
                    _define("v0", name, values, lines, indent)
            return

    def path(index, values, indent):
        lines = []
        while index < len(instructions):
            if index in region_by_start:
                index = _lower_loop(region_by_start[index], values, lines, indent, labels)
                continue
            budget[0] -= 1
            if budget[0] < 0:
                raise ValueError("path expansion limit")
            item = instructions[index]
            if item.mnemonic not in controls:
                step(index, values, lines, indent)
                index += 1
                continue
            visited.add(index)
            op, args = item.mnemonic, operands(item)
            if index + 1 >= len(instructions):
                raise ValueError("missing delay slot")
            if index in switches:
                dispatch = switches[index]
                selector = value_for(values, dispatch.selector)
                # The guard slot runs on default and indexed paths. Capture
                # the selector first because that slot may overwrite it.
                step(index + 1, values, lines, indent)
                default_values = dict(values)
                case_values = dict(values)
                # The skipped address calculation has no C data meaning.
                # Refuse later reads until these scratch registers are written.
                for name in (dispatch.address_register, dispatch.target_register):
                    case_values[name] = "@jump-table-address"
                visited.update(range(index + 2, dispatch.jump + 2))
                lines.append(indent + "switch ((unsigned int)(" + selector + ")) {")
                groups = {}
                for case, label in enumerate(dispatch.targets):
                    groups.setdefault(label, []).append(case)
                for label, cases in groups.items():
                    for case in cases:
                        lines.append(indent + "case " + str(case) + ":")
                    lines.extend(path(labels[label], dict(case_values), indent + "    "))
                lines.append(indent + "default:")
                lines.extend(path(labels[dispatch.default_label], default_values, indent + "    "))
                return lines + [indent + "}"]
            if op in {"jal", "jalr"}:
                lower_call(index, values, lines, indent)
                index += 2
                continue
            if op == "jr":
                return lines + [indent + emit_return(index, values, lines, indent)]
            expected = 3 if op in {"beq", "bne"} else 1 if op in {"b", "j"} else 2
            if len(args) != expected or args[-1] not in labels:
                raise ValueError("unbound branch target")
            target = labels[args[-1]]
            if target <= index + 1 or target in slots:
                raise ValueError("loop or delay-slot entry")
            condition = None
            if op in conditional:
                condition = _cond_text(op, args, values, expected)
            # Capture the predicate from the old state, then execute the slot
            # once on both outgoing paths. A slot can overwrite its operands.
            step(index + 1, values, lines, indent)
            if condition is None:
                index = target
                continue
            taken = path(target, dict(values), indent + "    ")
            other = path(index + 2, dict(values), indent + "    ")
            return lines + [indent + "if (" + condition + ") {"] + taken + [indent + "} else {"] + other + [indent + "}"]
        raise ValueError("path does not return")

    def _cond_text(op, args, values, expected, negate=False):
        if negate:
            op = _NEGATED_BRANCH[op]
        left_value = values[register(args[0])]
        right_value = values[register(args[1])] if expected == 3 else "0"
        if isinstance(left_value, _PointerValue) or isinstance(right_value, _PointerValue):
            if op not in {"beq", "bne", "beqz", "bnez"} or not (
                    isinstance(left_value, _PointerValue) and right_value == "0"
                    or isinstance(right_value, _PointerValue) and left_value == "0"
                    or isinstance(left_value, _PointerValue) and isinstance(right_value, _PointerValue)
                    and left_value.kind == right_value.kind):
                raise ValueError("unsupported pointer comparison")
            left = left_value.expression if isinstance(left_value, _PointerValue) else left_value
            right = right_value.expression if isinstance(right_value, _PointerValue) else right_value
        else:
            left = value_for(values, args[0])
            right = value_for(values, args[1]) if expected == 3 else "0"
        operator = {"beq": "==", "bne": "!=", "beqz": "==", "bnez": "!=",
                    "bltz": "<", "bgez": ">=", "bgtz": ">", "blez": "<="}[op]
        if op in {"bltz", "bgez", "bgtz", "blez"}:
            left = "(int)(" + left + ")"
        return "(" + left + ") " + operator + " (" + right + ")"

    def _define(destination, value, values, lines, indent):
        if destination not in materialize:
            # Capture expressions before a later instruction mutates a loop slot.
            if loop_active[0] and (isinstance(value, _PointerValue)
                                  or isinstance(value, str) and "@" not in value):
                value = snapshot(value, lines, indent)
            values[destination] = value
            return
        current = materialize[destination]
        if isinstance(value, _PointerValue):
            if not isinstance(current, _PointerValue) or current.kind != value.kind:
                raise ValueError("loop-carried pointer kind differs")
            text, target = value.expression, current.expression
        else:
            if not isinstance(value, str) or "@" in value:
                raise ValueError("loop-carried value is not a C expression")
            if isinstance(current, _PointerValue):
                raise ValueError("loop-carried pointer kind differs")
            text, target = value, current
        if len(text) > bounds.max_expression:
            raise ValueError("expression expansion limit")
        lines.append(indent + target + " = " + text + ";")
        values[destination] = current

    def snapshot(value, lines, indent):
        kind = value.kind if isinstance(value, _PointerValue) else "unsigned int"
        text = value.expression if isinstance(value, _PointerValue) else value
        if not isinstance(text, str) or "@" in text or len(text) > bounds.max_expression:
            raise ValueError("value is not materializable")
        temp = new_temporary("iteration_", kind)
        lines.append(indent + temp + " = " + text + ";")
        return _PointerValue(kind, temp) if isinstance(value, _PointerValue) else temp

    def _assign_carried(target_register, pointer_kind, expression, cast, values, lines, indent):
        value = (_PointerValue(pointer_kind, expression) if pointer_kind is not None else
                 "(unsigned int)(" + cast + ")(" + expression + ")")
        _define(target_register, value, values, lines, indent)

    _JOIN_SPECIAL_KEYS = frozenset({"zero", "ra", "stack_offset", "frame_size", "mul"})

    class LoopValues(dict):
        """Track reads of entry values independently from mutable C storage.

        A discovery pass finds actual live-ins, including implicit call
        arguments after the delay slot. Forks share the evidence sets but
        keep their own set of values still inherited from loop entry.
        """
        def __init__(self, initial, reads=None, writes=None, inherited=None):
            super().__init__(initial)
            self.entry_reads = set() if reads is None else reads
            self.writes = set() if writes is None else writes
            self.inherited = set(initial) if inherited is None else set(inherited)

        def __getitem__(self, key):
            value = super().__getitem__(key)
            if key in self.inherited:
                self.entry_reads.add(key)
            return value

        def get(self, key, default=None):
            return self[key] if key in self else default

        def __setitem__(self, key, value):
            self.writes.add(key)
            self.inherited.discard(key)
            super().__setitem__(key, value)

        def pop(self, key, *default):
            self.writes.add(key)
            self.inherited.discard(key)
            return super().pop(key, *default)

        def copy(self):
            return LoopValues(dict(self), self.entry_reads, self.writes, self.inherited)

        def adopt(self, other):
            self.clear()
            self.update(other)
            self.inherited = set(other.inherited)

    def _merge_states(taken, fall_values, fall_lines, lines, indent, negcond):
        # Only values valid on both paths survive. A later read of a clobbered
        # caller-saved register then refuses rather than recovering stale data.
        merged = LoopValues({}, taken.entry_reads, taken.writes, set())
        assigns, before = [], []
        left_state, right_state = dict(taken), dict(fall_values)
        for key in sorted(left_state.keys() | right_state.keys()):
            if key not in left_state or key not in right_state:
                if key in _JOIN_SPECIAL_KEYS or key.startswith("stack:"):
                    # Calls can legitimately invalidate argument-home slots.
                    if key not in {"ra", "mul"} and not key.startswith("stack:"):
                        raise ValueError("join diverges on machine state")
                continue
            left, right = left_state[key], right_state[key]
            if left == right and type(left) is type(right):
                dict.__setitem__(merged, key, left)
                if key in taken.inherited | fall_values.inherited:
                    merged.inherited.add(key)
                continue
            if key == "ra":
                dict.__setitem__(merged, key, "@call-return")
                continue
            if key in _JOIN_SPECIAL_KEYS or key.startswith("stack:"):
                raise ValueError("join diverges on machine state")
            if isinstance(left, _PointerValue) or isinstance(right, _PointerValue):
                if (not isinstance(left, _PointerValue) or not isinstance(right, _PointerValue)
                        or left.kind != right.kind):
                    raise ValueError("join diverges on value kind")
                kind, taken_text, fall_text = left.kind, left.expression, right.expression
            else:
                kind, taken_text, fall_text = "unsigned int", left, right
            if "@" in taken_text or "@" in fall_text:
                raise ValueError("join cannot materialize a marker")
            if key in taken.inherited | fall_values.inherited:
                taken.entry_reads.add(key)
            temp = new_temporary("join_", kind)
            before.append(indent + temp + " = " + taken_text + ";")
            assigns.append(indent + "    " + temp + " = " + fall_text + ";")
            dict.__setitem__(merged, key, _PointerValue(kind, temp) if isinstance(left, _PointerValue) else temp)
        # Join initialization executes each time this branch is reached, never
        # in the loop preheader and never outside an enclosing branch.
        lines.extend(before)
        lines.append(indent + "if (" + negcond + ") {")
        lines.extend(fall_lines)
        lines.extend(assigns)
        lines.append(indent + "}")
        return merged

    def emit_return(index, values, lines, indent):
        """Shared function-return lowering for path ends and in-loop returns.

        Enforces the ordinary return preconditions wherever the return sits:
        the return address must be intact and callee-saved state restored.
        """
        item = instructions[index]
        args = operands(item)
        if len(args) != 1 or register(args[0]) != "ra":
            raise ValueError("indirect jump")
        if values["ra"] != "@entry-ra":
            raise ValueError("return address not restored")
        step(index + 1, values, lines, indent)
        if values["stack_offset"] != 0 or any(values[name] != "@entry-" + name for name in preserved):
            raise ValueError("callee-saved state not restored")
        if return_type == "void":
            return "return;"
        if return_type in layouts:
            return "return " + pointer_expression(values["v0"], layouts[return_type]["canonical"]) + ";"
        value = value_for(values, "v0")
        if not re.fullmatch(r"[0-9]+", value) and return_type in {"int", "signed int", "s32", "s16", "s8", "short", "signed short", "signed char"}:
            value = "(int)(" + value + ")"
        return "return " + value + ";"

    def branch_condition(index, values, lines, indent, *, negate=False):
        item = instructions[index]
        args = operands(item)
        arity = 3 if item.mnemonic in {"beq", "bne"} else 2
        if len(args) != arity:
            raise ValueError("malformed loop branch")
        condition = _cond_text(item.mnemonic, args, values, arity, negate=negate)
        # A Python expression string is not a runtime snapshot of mutable C
        # locals. Capture the predicate before executing the MIPS delay slot.
        return snapshot(condition, lines, indent)

    def _lower_segment(lo, hi, values, lines, indent, labels):
        index = lo
        while index < hi:
            if index in region_by_start and region_by_start[index] is not active_region[0]:
                index = _lower_loop(region_by_start[index], values, lines, indent, labels)
                continue
            budget[0] -= 1
            if budget[0] < 0:
                raise ValueError("path expansion limit")
            item = instructions[index]
            if item.mnemonic in {"jal", "jalr"}:
                if index + 1 >= hi:
                    raise ValueError("call crosses segment boundary")
                visited.add(index)
                lower_call(index, values, lines, indent)
                index += 2
                continue
            if item.mnemonic == "jr":
                if index + 1 >= hi:
                    raise ValueError("return crosses segment boundary")
                visited.add(index)
                lines.append(indent + emit_return(index, values, lines, indent))
                # An unconditional return ends this path; later straight-line
                # code in the segment is dynamically unreachable.
                visited.update(range(index + 2, hi))
                return
            if item.mnemonic in _COND_BRANCHES:
                target = _branch_target_index(instructions, labels, index)
                if target is None or not index + 1 < target <= hi:
                    raise ValueError("inner branch leaves its segment")
                visited.add(index)
                negcond = branch_condition(index, values, lines, indent, negate=True)
                step(index + 1, values, lines, indent)
                taken, fall_values = values.copy(), values.copy()
                fall_lines = []
                _lower_segment(index + 2, target, fall_values, fall_lines, indent + "    ", labels)
                values.adopt(_merge_states(taken, fall_values, fall_lines, lines, indent, negcond))
                index = target
                continue
            step(index, values, lines, indent)
            index += 1

    def _lower_loop(region, values, lines, indent, labels):
        start, branch, slot = region["start"], region["branch"], region["slot"]
        exit_index = region.get("exit")
        kind = region.get("kind", "do-while")
        body_indent = indent + "    "
        # With a nop exit slot, a test-first C while is exact. Otherwise emit
        # the predicate, delay slot and break inside while(1), including on
        # the zero-trip path. Both exits must reach the same continuation.
        exit_list = region.get("exits") or ([exit_index] if exit_index is not None else [])
        test_first = (len(exit_list) == 1 and kind == "while" and exit_index == start
                      and instructions[start + 1].mnemonic == "nop")

        def emit(initial):
            current = LoopValues(initial)
            body_lines, exit_states = [], None
            if test_first:
                condition = _cond_text(instructions[start].mnemonic, operands(instructions[start]),
                                       current, len(operands(instructions[start])), negate=True)
                exit_states = [current.copy()]
                step(start + 1, current, body_lines, body_indent)
                _lower_segment(start + 2, branch, current, body_lines, body_indent, labels)
                step(slot, current, body_lines, body_indent)
            else:
                bound = exit_list[0] if exit_list else branch
                _lower_segment(start, bound, current, body_lines, body_indent, labels)
                states = []
                for pos, exit_at in enumerate(exit_list):
                    predicate = branch_condition(exit_at, current, body_lines, body_indent)
                    step(exit_at + 1, current, body_lines, body_indent)
                    states.append(current.copy())
                    body_lines.append(body_indent + "if (" + predicate + ") break;")
                    follow = exit_list[pos + 1] if pos + 1 < len(exit_list) else branch
                    _lower_segment(exit_at + 2, follow, current, body_lines, body_indent, labels)
                exit_states = states or None
                condition = (branch_condition(branch, current, body_lines, body_indent)
                             if kind != "while" else "1")
                step(slot, current, body_lines, body_indent)
            return current, exit_states, condition, body_lines

        saved_region = active_region[0]
        saved_materialize = dict(materialize)
        saved_active = loop_active[0]
        active_region[0] = region
        loop_active[0] = True
        try:
            # Discover true live-ins using the ordinary interpreter, including
            # conditional definitions and the implicit inputs/outputs of calls.
            # No discovery C or temporary is retained in the emitted function.
            temporary_count = len(temporaries)
            names_before, prototypes_before = set(reserved_names), dict(prototypes)
            end, early_list, _, _ = emit(values)
            required, writes = set(end.entry_reads), set(end.writes)
            del temporaries[temporary_count:]
            reserved_names.clear()
            reserved_names.update(names_before)
            prototypes.clear()
            prototypes.update(prototypes_before)
            # Also preserve initialized live-outs: an assignment that is never
            # read inside the loop still has to reach the caller on both the
            # zero-trip and executed paths. Unknown scratch values stay absent.
            initialized = {reg for reg, value in values.items()
                           if isinstance(value, _PointerValue)
                           or isinstance(value, str) and "@" not in value}
            for reg in sorted(((required | initialized) & writes) & writable):
                if reg in materialize:
                    # An ancestor loop already owns carrier storage for this
                    # register; share it so every nesting level sees one binding.
                    values[reg] = materialize[reg]
                    continue
                entry = values.get(reg)
                if isinstance(entry, _PointerValue):
                    ctype, text = entry.kind, entry.expression
                elif isinstance(entry, str) and "@" not in entry:
                    ctype, text = "unsigned int", entry
                else:
                    raise ValueError("loop-carried value is not materializable")
                temp = new_temporary("loop_", ctype)
                lines.append(indent + temp + " = " + text + ";")
                storage = _PointerValue(ctype, temp) if isinstance(entry, _PointerValue) else temp
                materialize[reg] = storage
                values[reg] = storage
            initial = dict(values)
            end, early_list, condition, body_lines = emit(initial)
            final = dict(end)
            # Every value consumed from entry must remain available at the
            # backedge with the same binding. Call clobbers get no exemption.
            for key in required - {"ra", "mul"}:
                if key not in final or key not in initial or final[key] != initial[key]:
                    raise ValueError("loop backedge does not preserve a live-in")
            if test_first or kind == "while" and exit_index == start:
                lines.append(indent + "while (" + condition + ") {")
                lines.extend(body_lines)
                lines.append(indent + "}")
            else:
                lines.append(indent + "do {")
                lines.extend(body_lines)
                lines.append(indent + "} while (" + condition + ");")
            if early_list is not None:
                states = [dict(state) for state in early_list]
                if len(states) == 1:
                    if kind == "while":
                        final = states[0]
                    else:
                        # Keep only bindings valid at both the break and latch
                        # exits. Unused scratch state is allowed to disappear.
                        final = {key: value for key, value in final.items()
                                 if key in states[0] and states[0][key] == value}
                elif kind == "while":
                    final = states[0]
                    for other in states[1:]:
                        final = {key: value for key, value in final.items()
                                 if key in other and other[key] == value}
                else:
                    for other in states:
                        final = {key: value for key, value in final.items()
                                 if key in other and other[key] == value}
            values.clear()
            values.update(final)
            visited.update(range(start, slot + 1))
        finally:
            materialize.clear()
            materialize.update(saved_materialize)
            active_region[0] = saved_region
            loop_active[0] = saved_active
        return slot + 1

    materialize: dict = {}
    loop_active = [False]
    active_region = [None]
    loop_admitted, loop_refused = loop_regions(instructions, allow_calls=True)
    if loop_refused:
        return None
    region_by_start = {region["start"]: region for region in loop_admitted}
    try:
        body = path(0, state, "    ")
        # Extra definitions or unexplained dead code cannot be silently merged
        # into this function. Padding nops after its final return are harmless.
        if any(i not in visited and (item.mnemonic != "nop" or item.operands)
               for i, item in enumerate(instructions)):
            return None
        # An ignored return still calls the function exactly once, but needs
        # no unused local. Keep declarations at block start for the US C89 compiler.
        body_text = "\n".join(body)
        used_temporaries = []
        for declaration in temporaries:
            name = declaration.removesuffix(";").split()[-1]
            if len(re.findall(r"\b" + re.escape(name) + r"\b", body_text)) == 1:
                body_text = re.sub(r"\b" + re.escape(name) + r" = (?:\(unsigned int\))?",
                                   "" if name.startswith("call_result_") else "(void)", body_text, count=1)
            else:
                used_temporaries.append(declaration)
        result = "\n".join([*prototypes.values(), *used_temporaries, body_text])
        return result if len(result) <= bounds.max_body else None
    except (ValueError, KeyError, RecursionError):
        return None


def _deterministic_local_draft(
    context: _TargetContext,
    claims: Sequence[DonorSemanticClaim],
    *,
    limits: Any = None,
) -> Optional[str]:
    try:
        text = context.assembly_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return_type, parameters = _declaration_context(context, claims)
    try:
        code, tables = split_local_tables(text, _strip_assembly_comment)
        instructions = _parse_assembly(code, retain_relocations=bool(tables))
        switches = recover_dispatches(instructions, tables)
        proven_relocations = {branch + offset for branch in switches for offset in (2, 4)}
        instructions = tuple(replace(item, unsupported=False) if i in proven_relocations else item
                             for i, item in enumerate(instructions))
    except ValueError:
        return None
    bounds = _coerce_limits(limits)
    body = _leaf_body(instructions, parameters, return_type, context.declarations.get("call_declarations"),
                      context.declarations.get("pointer_layouts"), switches, context.declarations.get("api_declarations"),
                      datas=context.declarations.get("data_declarations"), gdata=context.declarations.get("global_declarations"), linker=context.declarations.get("linker_declarations"), limits=bounds)
    if body is None:
        return None
    parameter_text = "void" if not parameters else ", ".join(
        type_name + " " + name for type_name, name in parameters
    )
    return f"{return_type} {context.symbol}({parameter_text}) {{\n{body}\n}}\n"


def deterministic_local_draft(
    target_assembly: str | bytes,
    *,
    symbol: str,
    declarations: Mapping[str, Any] | None = None,
    claims: Sequence[DonorSemanticClaim] = (),
    limits: Any = None,
) -> Optional[str]:
    """Public pure wrapper around the local target draft generator.

    The limits argument selects a validated RendererLimits (or a partial
    mapping) for scoped measurement. None selects the canonical
    DEFAULT_LIMITS, which is the only setting production archived runs use.
    """

    raw = target_assembly.encode("utf-8") if isinstance(target_assembly, str) else target_assembly
    if not isinstance(raw, bytes):
        raise TargetRendererInputError("target assembly must be bytes or text")
    digest = hash_bytes(raw)
    artifact = ArtifactRef(digest, "artifacts/target-assembly/" + digest[7:] + ".s", "text/x-asm", len(raw))
    context = _TargetContext(
        recipient_id="us:target:target",
        target_identity=hash_canonical({"target": digest}),
        target_evidence_identity=hash_canonical({"target": digest}),
        assembly=artifact,
        assembly_path="asm/us/target.s",
        assembly_bytes=raw,
        symbol=symbol,
        instruction_signature=None,
        cfg_signature=None,
        dataflow_signature=None,
        declarations=declarations or {},
        version="us",
    )
    return _deterministic_local_draft(context, tuple(claims), limits=limits)


def _unsupported(
    context: _TargetContext,
    query: DonorQuery,
    reason: str,
    claims: Sequence[DonorSemanticClaim] = (),
    *,
    lane: Optional[str] = None,
) -> TargetContextUnsupported:
    input_ids = tuple(
        dict.fromkeys(
            (
                query.query_identity,
                context.target_identity,
                context.target_evidence_identity,
                context.assembly.content_hash,
                TARGET_RENDERER_IDENTITY,
                *(claim.claim_identity for claim in claims),
            )
        )
    )
    edge: dict[str, Any] = {
            "kind": "target_context",
            "source": context.assembly_path,
            "source_identity": context.assembly.content_hash,
            "input_identity": query.query_identity,
            "recipient_id": context.recipient_id,
            "target_identity": context.target_identity,
            "target_evidence_identity": context.target_evidence_identity,
            "assembly_artifact": context.assembly.to_dict(),
            "query": query.to_dict(),
            "claim_identities": [claim.claim_identity for claim in claims],
        }
    if lane is not None:
        edge["lane"] = lane
    provenance = (edge,)
    return TargetContextUnsupported(
        recipient_id=context.recipient_id,
        query=query,
        target_identity=context.target_identity,
        target_artifact_identity=context.target_evidence_identity,
        reason=reason,
        input_identities=input_ids,
        provenance=provenance,
    )


def _lane(lane: Optional[str], manifest: RunManifest) -> str:
    if lane is not None:
        if lane not in INDEXED_RENDER_LANES:
            raise TargetRendererInputError("target renderer lane is not indexed")
        return lane
    selected = tuple(item for item in manifest.selected_lanes if item in INDEXED_RENDER_LANES)
    return selected[0] if selected else "multi_donor"


def render_target_candidate(
    manifest: RunManifest | Mapping[str, Any],
    target_index: Any,
    recipient: Recipient,
    claims: Sequence[DonorSemanticClaim],
    *,
    lane: Optional[str] = None,
    query: Optional[DonorQuery] = None,
) -> LaneCandidate | tuple[LaneCandidate, ...] | TargetContextUnsupported:
    """Render a candidate from target assembly and semantic claims only."""

    typed_manifest = _coerce_manifest(manifest)
    context = _target_context(target_index, typed_manifest, recipient)
    lane_name = _lane(lane, typed_manifest)
    expected_query = query_for_recipient(typed_manifest, target_index, recipient)
    if query is None:
        query = expected_query
    elif (
        not isinstance(query, DonorQuery)
        or query.recipient_id != recipient.recipient_id
        or query != expected_query
    ):
        raise TargetRendererInputError(
            "target renderer query must be the archived target-derived query"
        )
    semantic_claims = _claim_tuple(recipient, claims)
    if not semantic_claims:
        return _unsupported(
            context,
            query,
            "no compatible semantic claim was supplied",
            lane=lane_name,
        )
    source = _deterministic_local_draft(context, semantic_claims)
    if source is None:
        return _unsupported(
            context,
            query,
            "target assembly requires a translation shape outside the deterministic renderer",
            semantic_claims,
            lane=lane_name,
        )
    source_bytes = source.encode("utf-8")
    candidate_id = hash_bytes(source_bytes)
    source_artifact = ArtifactRef(
        candidate_id,
        "artifacts/sources/" + candidate_id.removeprefix("sha256:") + ".c",
        "text/x-c",
        len(source_bytes),
    )
    record = CandidateRecord(
        candidate_id=candidate_id,
        recipient_id=recipient.recipient_id,
        source_artifact=source_artifact,
        parent_candidate_ids=(),
        mutation_id=None,
        lane=lane_name,
        depth=0,
        evaluation=None,
        status="materialized",
    )
    provenance = (
        {
            "kind": "target_renderer",
            "source": context.assembly_path,
            "source_identity": context.assembly.content_hash,
            "input_identity": query.query_identity,
            "recipient_id": recipient.recipient_id,
            "target_identity": context.target_identity,
            "target_evidence_identity": context.target_evidence_identity,
            "query_identity": query.query_identity,
            "renderer_identity": TARGET_RENDERER_IDENTITY,
            "claim_identities": [claim.claim_identity for claim in semantic_claims],
            "lane": lane_name,
        },
    )
    return LaneCandidate(record, source, provenance)


def _validate_target_evidence_document(document: Mapping[str, Any]) -> None:
    """Validate the canonical target-evidence envelope before projection.

    The factory's target measurement is intentionally small.  Keeping this
    check at the archive boundary prevents an otherwise harmless-looking extra
    field from smuggling donor source, register, relocation, or byte context
    into the renderer.
    """

    required = {"artifact_type", "assembly", "object", "record_id", "schema_version"}
    if set(document).difference(_TARGET_EVIDENCE_FIELDS) or not required.issubset(document):
        raise TargetEvidenceError("target evidence fields are not canonical")
    if (
        document.get("artifact_type") != TARGET_EVIDENCE_ARTIFACT_TYPE
        or document.get("schema_version") != TARGET_SCHEMA_VERSION
    ):
        raise TargetEvidenceError("target evidence envelope is unsupported")
    record_id = document.get("record_id")
    try:
        validate_id(record_id, "target evidence record_id")
    except SearchValidationError as exc:
        raise TargetEvidenceError(str(exc)) from exc
    _reject_forbidden_tree(document, "target evidence")
    for name, expected_category, expected_suffix, expected_media in (
        ("assembly", "target-assembly", ".s", "text/x-asm"),
        ("object", "target-object", ".o", "application/octet-stream"),
    ):
        component = document.get(name)
        if not isinstance(component, Mapping) or set(component) != _TARGET_COMPONENT_FIELDS:
            raise TargetEvidenceError(f"target evidence {name} fields are not canonical")
        reference = _artifact(component.get("artifact"), f"target {name} artifact")
        _validate_archived_ref(
            reference,
            category=expected_category,
            suffix=expected_suffix,
            media_type=expected_media,
            label=f"target {name}",
        )
        content_hash = component.get("content_hash")
        try:
            validate_hash(content_hash, f"target {name} content_hash")
        except SearchValidationError as exc:
            raise TargetEvidenceError(str(exc)) from exc
        if content_hash != reference.content_hash:
            raise TargetEvidenceError(f"target {name} content hash differs from artifact")
        byte_size = component.get("byte_size")
        if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 0:
            raise TargetEvidenceError(f"target {name} byte_size is invalid")
        if byte_size != reference.byte_size:
            raise TargetEvidenceError(f"target {name} byte size differs from artifact")
        source_path = component.get("path")
        if not isinstance(source_path, str) or not source_path:
            raise TargetEvidenceError(f"target {name} source path is invalid")
        try:
            validate_relative_path(source_path, f"target {name} source path")
        except SearchValidationError as exc:
            raise TargetEvidenceError(str(exc)) from exc
        if "\\" in source_path or source_path.startswith("artifacts/"):
            raise TargetEvidenceError(f"target {name} source path is not canonical")
        if not source_path.lower().endswith(expected_suffix):
            raise TargetEvidenceError(f"target {name} source path has the wrong suffix")
    signatures = document.get("signatures")
    if signatures is not None:
        if not isinstance(signatures, Mapping):
            raise TargetEvidenceError("target signatures must be a mapping")
        allowed = {
            "instruction_signature",
            "instructions",
            "cfg_signature",
            "cfg",
            "dataflow_signature",
            "dataflow",
            "flow",
        }
        if set(signatures).difference(allowed):
            raise TargetEvidenceError("target signatures contain unsupported fields")
    for canonical_name, aliases in (
        ("instruction_signature", ("instruction_signature", "instructions")),
        ("cfg_signature", ("cfg_signature", "cfg")),
        ("dataflow_signature", ("dataflow_signature", "dataflow", "flow")),
    ):
        observed: list[str] = []
        for alias in aliases:
            if alias in document:
                value = _optional_text(document[alias], canonical_name)
                if value is not None:
                    observed.append(value)
            if isinstance(signatures, Mapping) and alias in signatures:
                value = _optional_text(signatures[alias], canonical_name)
                if value is not None:
                    observed.append(value)
        if observed and len(set(observed)) != 1:
            raise TargetEvidenceError(
                f"target {canonical_name} aliases disagree"
            )
        for value in observed:
            try:
                validate_hash(value, canonical_name)
            except SearchValidationError as exc:
                raise TargetEvidenceError(
                    f"target {canonical_name} is not a content identity"
                ) from exc
    for name in (
        "instruction_signature",
        "cfg_signature",
        "dataflow_signature",
    ):
        if name in document:
            _optional_text(document[name], name)
    declarations = document.get("declarations", document.get("target_declarations"))
    if declarations is not None:
        if not isinstance(declarations, Mapping):
            raise TargetEvidenceError("target declarations must be a mapping")
        _reject_forbidden_tree(declarations, "target declarations")
    if "declarations" in document and "target_declarations" in document:
        if document["declarations"] != document["target_declarations"]:
            raise TargetEvidenceError("target declaration aliases disagree")
    for name in ("symbol", "version", "platform"):
        if name in document and document[name] is not None:
            if not isinstance(document[name], str) or not document[name]:
                raise TargetEvidenceError(f"target {name} must be a nonempty string")


def _archive_json(archive: ContentAddressedArchive, raw: Any, label: str) -> dict[str, Any]:
    reference = _artifact(raw, label)
    _validate_archived_ref(
        reference,
        category="target-evidence",
        suffix=".json",
        media_type="application/json",
        label=label,
    )
    try:
        data = _verify_archived_bytes(archive, reference, label)
        parsed = json.loads(data.decode("utf-8"))
        if canonical_bytes(parsed) != data or hash_canonical(parsed) != reference.content_hash:
            raise TargetEvidenceError(label + " is not canonical")
    except (ArchiveError, UnicodeDecodeError, json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        if isinstance(exc, TargetEvidenceError):
            raise
        raise TargetEvidenceError(label + " is missing or corrupt") from exc
    if not isinstance(parsed, Mapping):
        raise TargetEvidenceError(label + " is not a JSON object")
    return dict(parsed)


def _archive_target_index(archive: ContentAddressedArchive) -> tuple[dict[str, Any], ArtifactRef]:
    if not isinstance(archive, ContentAddressedArchive):
        raise TargetRendererInputError("target index loading requires a ContentAddressedArchive")
    root = archive.run_root
    if root.is_symlink():
        raise TargetEvidenceError("target archive root is a symlink")
    artifacts_root = root / "artifacts"
    if artifacts_root.is_symlink():
        raise TargetEvidenceError("target archive artifacts root is a symlink")
    if artifacts_root.is_dir():
        for entry in artifacts_root.rglob("*"):
            if entry.is_symlink():
                raise TargetEvidenceError("target archive contains a symlink")
    candidates: list[tuple[dict[str, Any], ArtifactRef]] = []
    for path in sorted(artifacts_root.rglob("*.json")) if artifacts_root.is_dir() else ():
        current = artifacts_root
        try:
            relative = path.relative_to(artifacts_root)
        except ValueError as exc:
            raise TargetEvidenceError("target archive path escapes artifacts root") from exc
        for component in relative.parts[:-1]:
            current = current / component
            if current.is_symlink():
                raise TargetEvidenceError("target archive path contains a symlink")
        if path.is_symlink() or not path.is_file():
            raise TargetEvidenceError("target archive contains a symlink or non-file")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TargetEvidenceError("target archive contains corrupt JSON") from exc
        if isinstance(document, Mapping) and document.get("artifact_type") == TARGET_INDEX_ARTIFACT_TYPE:
            data = path.read_bytes()
            reference = ArtifactRef(hash_bytes(data), path.relative_to(root).as_posix(), "application/json", len(data))
            _validate_archived_ref(
                reference,
                category="target-index",
                suffix=".json",
                media_type="application/json",
                label="target index",
            )
            try:
                verified = _verify_archived_bytes(archive, reference, "target index")
                if verified != data or canonical_bytes(document) != data:
                    raise TargetEvidenceError("target index artifact is not canonical")
                if hash_canonical(document) != reference.content_hash:
                    raise TargetEvidenceError("target index identity differs from payload")
            except ArchiveError as exc:
                raise TargetEvidenceError("target index artifact is missing or corrupt") from exc
            candidates.append((dict(document), reference))
    if len(candidates) != 1:
        raise TargetEvidenceError("run archive must contain exactly one target index")
    document, reference = candidates[0]
    return document, reference


def load_target_index(
    archive: ContentAddressedArchive,
    manifest: Optional[RunManifest] = None,
) -> TargetIndex:
    """Resolve one explicit target index and all target assembly bytes.

    Only the run archive is inspected.  No repository path in the evidence is
    opened, and there is no latest or queue fallback.
    """

    document, target_index_artifact = _archive_target_index(archive)
    if set(document) != {"artifact_type", "records", "schema_version"}:
        raise TargetEvidenceError("target index fields are not canonical")
    if document.get("schema_version") != TARGET_SCHEMA_VERSION:
        raise TargetEvidenceError("target index schema is unsupported")
    raw_records = document.get("records")
    if not isinstance(raw_records, list):
        raise TargetEvidenceError("target index records are not an array")
    record_ids = [
        item.get("record_id") if isinstance(item, Mapping) else None
        for item in raw_records
    ]
    if any(not isinstance(item, str) or not item for item in record_ids):
        raise TargetEvidenceError("target index record identities are invalid")
    if record_ids != sorted(record_ids):
        raise TargetEvidenceError("target index records are not in canonical order")
    contexts: list[_TargetContext] = []
    for raw in raw_records:
        if not isinstance(raw, Mapping) or set(raw) != {"record_id", "target_identity", "target_evidence"}:
            raise TargetEvidenceError("target index record fields are not canonical")
        record_id = raw["record_id"]
        target_identity = _hash(raw["target_identity"], "target identity")
        target_evidence_ref = _artifact(raw["target_evidence"], "target evidence artifact")
        if target_evidence_ref.content_hash != target_identity:
            raise TargetEvidenceError("target evidence reference differs from target identity")
        target_doc = _archive_json(archive, target_evidence_ref, "target evidence")
        if hash_canonical(target_doc) != target_evidence_ref.content_hash:
            raise TargetEvidenceError("target evidence identity differs from payload")
        _validate_target_evidence_document(target_doc)
        if (
            target_doc.get("artifact_type") != TARGET_EVIDENCE_ARTIFACT_TYPE
            or target_doc.get("schema_version") != TARGET_SCHEMA_VERSION
            or target_doc.get("record_id") != record_id
        ):
            raise TargetEvidenceError("target evidence record binding is invalid")
        assembly = target_doc.get("assembly")
        obj = target_doc.get("object")
        if not isinstance(assembly, Mapping) or not isinstance(obj, Mapping):
            raise TargetEvidenceError("target evidence assembly/object fields are missing")
        try:
            from .search_source_context import verify_target_context
            declarations = target_doc.get("declarations", {})
            compiler_identity = (manifest.compiler_identity if manifest is not None else
                                 declarations.get("context_evidence", {}).get("compiler_identity"))
            verify_target_context(declarations, archive, record_id, compiler_identity, assembly["path"])
        except Exception as exc:
            raise TargetEvidenceError("target declaration context is missing or corrupt") from exc
        assembly_ref = _artifact(assembly.get("artifact"), "target assembly artifact")
        object_ref = _artifact(obj.get("artifact"), "target object artifact")
        _validate_archived_ref(
            target_evidence_ref,
            category="target-evidence",
            suffix=".json",
            media_type="application/json",
            label="target evidence",
        )
        _validate_archived_ref(
            object_ref,
            category="target-object",
            suffix=".o",
            media_type="application/octet-stream",
            label="target object",
        )
        _validate_archived_assembly_ref(assembly_ref)
        _validate_archived_ref(
            assembly_ref,
            category="target-assembly",
            suffix=".s",
            media_type="text/x-asm",
            label="target assembly",
        )
        try:
            assembly_bytes = _verify_archived_bytes(
                archive, assembly_ref, "target assembly"
            )
            _verify_archived_bytes(archive, object_ref, "target object")
        except TargetEvidenceError:
            raise
        if (
            assembly_ref.media_type != "text/x-asm"
            or assembly.get("content_hash") != hash_bytes(assembly_bytes)
            or assembly.get("byte_size") != len(assembly_bytes)
            or obj.get("content_hash") != object_ref.content_hash
            or obj.get("byte_size") != object_ref.byte_size
        ):
            raise TargetEvidenceError("target assembly/object identity is invalid")
        inline = {
            **target_doc,
            "record_id": record_id,
            "target_identity": target_identity,
            "target_evidence_identity": target_evidence_ref.content_hash,
            "target_evidence_artifact": target_evidence_ref.to_dict(),
            "assembly": {
                **dict(assembly),
                "artifact": assembly_ref.to_dict(),
                "bytes": assembly_bytes,
            },
        }
        from .search_source_context import renderer_declarations
        context_evidence = target_doc.get("declarations", {}).get("context_evidence", {})
        context_bytes = (archive.verify(ArtifactRef.from_dict(context_evidence["preprocessed"]))
                         if "preprocessed" in context_evidence else None)
        sibling_contexts = tuple(archive.verify(ArtifactRef.from_dict(entry["preprocessed"]))
                                 for entry in context_evidence.get("siblings", ()) or ())
        inline["declarations"] = renderer_declarations(target_doc.get("declarations", {}), assembly_bytes, context_bytes, sibling_contexts)
        context = _context_from_record(inline)
        contexts.append(context)
    index = TargetIndex(tuple(contexts), target_index_artifact)
    if manifest is not None:
        if not isinstance(manifest, RunManifest):
            raise TargetRendererInputError("target index manifest must be typed")
        if tuple(item.recipient_id for item in index.records) != tuple(
            manifest.queue_record_ids
        ):
            raise TargetEvidenceError("target index coverage differs from manifest subset")
        for item in index.records:
            if manifest.target_identities.get(item.recipient_id) != item.target_identity:
                raise TargetEvidenceError("target index target identity differs from manifest")
    return index


__all__ = [
    "INDEXED_RENDER_LANES",
    "TARGET_EVIDENCE_ARTIFACT_TYPE",
    "TARGET_INDEX_ARTIFACT_TYPE",
    "TARGET_RENDERER_IDENTITY",
    "TARGET_RENDERER_PROTOCOL",
    "TargetContextUnsupported",
    "TargetEvidenceError",
    "TargetIndex",
    "TargetRendererError",
    "TargetRendererInputError",
    "deterministic_local_draft",
    "load_target_index",
    "query_for_recipient",
    "render_target_candidate",
]
