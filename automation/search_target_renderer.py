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


def _parse_assembly(text: str) -> tuple[_Instruction, ...]:
    if not isinstance(text, str):
        raise TargetEvidenceError("target assembly is not UTF-8 text")
    instructions: list[_Instruction] = []
    pending_label: Optional[str] = None
    for raw_line in text.splitlines():
        line = _strip_assembly_comment(raw_line).strip()
        if not line:
            continue
        if _ASM_DATA_DIRECTIVE.match(line) or _ASM_RELOCATION.search(line):
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
            pending_label = label_match.group("label")
            line = (label_match.group("tail") or "").strip()
            if not line:
                continue
            if _ASM_DATA_DIRECTIVE.match(line) or _ASM_RELOCATION.search(line):
                instructions.append(_Instruction("unsupported", "", pending_label, True))
                pending_label = None
                continue
            objdump = re.match(
                r"^(?:[0-9A-Fa-f]+:\s+)?(?:[0-9A-Fa-f]{8}\s+)?"
                r"(?P<mn>[A-Za-z][A-Za-z0-9.]*)\s*(?P<ops>.*)$",
                line,
            )
        if not objdump:
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
        if has_numeric_branch_target(mnemonic, operands):
            instructions.append(_Instruction(mnemonic, operands, pending_label, True))
        else:
            instructions.append(_Instruction(mnemonic, operands, pending_label))
        pending_label = None
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
        version=_version_for(recipient, context),
        source_path=context.assembly_path,
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
        if "return_type" not in target_declarations and "result_type" not in target_declarations:
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


def _deterministic_local_draft(
    context: _TargetContext,
    claims: Sequence[DonorSemanticClaim],
) -> Optional[str]:
    """Render the small, structurally complete subset supported locally.

    The generator intentionally refuses branches, calls, and unresolved
    memory accesses.  A plausible generic function is less useful than a
    typed refusal when the target context cannot be represented safely.
    """

    try:
        text = context.assembly_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None
    instructions = _parse_assembly(text)
    if not instructions:
        return None
    return_type, parameters = _declaration_context(context, claims)
    expression: Optional[str] = None
    returned = False
    for instruction in instructions:
        if instruction.unsupported:
            return None
        mnemonic = instruction.mnemonic
        operands = instruction.operands
        registers = _register_operands(operands)
        if mnemonic in {"nop", "sll"} and (mnemonic == "nop" or operands.replace("$", "").replace(" ", "") in {"$zero,$zero,0", "zero,zero,0"}):
            continue
        if mnemonic in {"addiu", "addi", "ori", "li"} and registers:
            if registers[0] != "v0":
                if registers[0] == "sp" and len(registers) > 1 and registers[1] == "sp":
                    continue
                return None
            literal = _literal_operand(operands)
            if literal is None:
                return None
            if mnemonic in {"addiu", "addi", "ori"} and len(registers) >= 2 and registers[1] != "zero":
                source = _target_parameter_for_register(registers[1], parameters)
                if source is None:
                    return None
                expression = f"{source} + {literal}"
            else:
                expression = str(literal)
            continue
        if mnemonic == "move" and len(registers) >= 2 and registers[0] == "v0":
            source = _target_parameter_for_register(registers[1], parameters)
            if source is None:
                return None
            expression = source
            continue
        if mnemonic in {"addu", "add", "subu", "sub"} and len(registers) >= 3 and registers[0] == "v0":
            left = _target_parameter_for_register(registers[1], parameters)
            right = _target_parameter_for_register(registers[2], parameters)
            if left is None or right is None:
                return None
            op = "-" if mnemonic in {"subu", "sub"} else "+"
            expression = f"{left} {op} {right}"
            continue
        if mnemonic in _RETURN_MNEMONICS:
            if mnemonic in {"rts", "ret"} or (registers and registers[0] == "ra"):
                returned = True
                continue
            return None
        # Stack save/restore instructions are compiler context, not source
        # semantics.  Other memory, branch, call, coprocessor and arithmetic
        # forms need a richer target translation and fail closed.
        if mnemonic in {"addiu", "addi"} and len(registers) >= 2 and registers[0] == registers[1] == "sp":
            continue
        if mnemonic in {"sw", "lw", "sh", "lh", "sb", "lb"} and "sp" in registers:
            continue
        return None
    if not returned:
        return None
    if return_type == "void":
        if expression is not None:
            return None
        body = "    return;"
    else:
        if expression is None:
            return None
        body = "    return " + expression + ";"
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
) -> Optional[str]:
    """Public pure wrapper around the local target draft generator."""

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
    return _deterministic_local_draft(context, tuple(claims))


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
