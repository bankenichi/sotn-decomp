"""Compiler idiom records and deterministic source transformations.

This module contains the value objects used by the draft-to-landed evidence
miner.  It deliberately has no repository writer and no compiler invocation.
Source text is treated as an immutable byte sequence: hashes are always hashes
of the supplied bytes, never hashes of paths or filesystem metadata.
"""

from __future__ import annotations

import dataclasses
import difflib
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Optional

try:
    from .search_types import (
        ArtifactRef,
        GroupedPatch,
        PatchHunk,
        SearchValidationError,
        canonical_bytes,
        canonical_json,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )
except ImportError:  # pragma: no cover - direct script compatibility
    from search_types import (  # type: ignore
        ArtifactRef,
        GroupedPatch,
        PatchHunk,
        SearchValidationError,
        canonical_bytes,
        canonical_json,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )


MODULE_VERSION = "compiler-idioms-v1"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class CompilerIdiomError(ValueError):
    """Base error for malformed idiom evidence."""


class MeasurementError(CompilerIdiomError):
    """Raised when a score or checksum measurement is not authoritative."""


def _plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if dataclasses.is_dataclass(value):
        return {
            field.name: _plain(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    return value


def _freeze_json(value: Any, label: str) -> Any:
    """Freeze JSON-shaped evidence without accepting arbitrary Python data."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise CompilerIdiomError(f"{label} keys must be strings")
        return MappingProxyType(
            {key: _freeze_json(item, label) for key, item in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json(item, label) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise CompilerIdiomError(f"{label} must contain JSON values")


def _unique_sorted(values: Iterable[str], label: str) -> tuple[str, ...]:
    raw = tuple(values)
    result = tuple(sorted(set(raw)))
    if len(result) != len(raw):
        raise CompilerIdiomError(f"{label} must not contain duplicates")
    if any(not isinstance(item, str) or not item for item in result):
        raise CompilerIdiomError(f"{label} must contain nonempty strings")
    return result


def _coerce_artifact(value: Any, label: str) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    if not isinstance(value, Mapping):
        raise CompilerIdiomError(f"{label} must be an ArtifactRef")
    try:
        return ArtifactRef.from_dict(value)
    except (SearchValidationError, TypeError, KeyError) as exc:
        raise CompilerIdiomError(f"invalid {label}") from exc


def _coerce_patch(value: Any) -> GroupedPatch:
    if isinstance(value, GroupedPatch):
        return value
    try:
        return GroupedPatch.from_dict(value)
    except (SearchValidationError, TypeError, KeyError) as exc:
        raise CompilerIdiomError("invalid grouped patch") from exc


def source_hash(source: str | bytes) -> str:
    """Hash source bytes exactly, without normalizing or touching a file."""
    if isinstance(source, str):
        source = source.encode("utf-8")
    if not isinstance(source, bytes):
        raise TypeError("source must be text or bytes")
    return hash_bytes(source)


def validate_commit_identity(value: Any, label: str = "commit") -> str:
    """Validate a full immutable Git object identity.

    A branch or tag name is mutable and therefore intentionally rejected here.
    Both SHA-1 and SHA-256 repositories are supported, but abbreviated object
    IDs are not.
    """
    if not isinstance(value, str):
        raise CompilerIdiomError(f"{label} must be an immutable object id")
    normalized = value.lower()
    if not _COMMIT_RE.fullmatch(normalized):
        raise CompilerIdiomError(
            f"{label} must be a full 40- or 64-hex commit identity"
        )
    return normalized


@dataclass(frozen=True)
class CompilerIdentity:
    """The identities that make one compiler observation reproducible."""

    compiler_identity: str
    tool_identity: Optional[str] = None
    config_identity: Optional[str] = None

    def __post_init__(self) -> None:
        validate_hash(self.compiler_identity, "compiler_identity")
        if self.tool_identity is not None:
            validate_hash(self.tool_identity, "tool_identity")
        if self.config_identity is not None:
            validate_hash(self.config_identity, "config_identity")

    def to_dict(self) -> dict[str, Any]:
        return {
            "compiler_identity": self.compiler_identity,
            "tool_identity": self.tool_identity,
            "config_identity": self.config_identity,
        }

    @property
    def identity(self) -> str:
        return hash_canonical({"kind": MODULE_VERSION, **self.to_dict()})


@dataclass(frozen=True)
class CompilerOperatorRecord:
    """One deterministic, source-local transformation operator.

    Exact before and after text remains in the record.  The feature labels are
    descriptive indexes only and never authorize a rewrite by themselves.
    """

    kind: str
    before: str
    after: str
    features: Mapping[str, Any] = field(default_factory=dict)
    operator_id: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise CompilerIdiomError("operator kind must be nonempty")
        if not isinstance(self.before, str) or not isinstance(self.after, str):
            raise CompilerIdiomError("operator source text must be strings")
        frozen = _freeze_json(self.features, "operator features")
        if not isinstance(frozen, Mapping):
            raise CompilerIdiomError("operator features must be an object")
        object.__setattr__(self, "features", frozen)
        expected = hash_canonical(
            {
                "kind": self.kind,
                "before": self.before,
                "after": self.after,
                "features": self.features,
            }
        )
        if self.operator_id:
            validate_hash(self.operator_id, "operator_id")
            if self.operator_id != expected:
                raise CompilerIdiomError("operator_id does not match operator content")
        else:
            object.__setattr__(self, "operator_id", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "kind": self.kind,
            "before": self.before,
            "after": self.after,
            "features": _plain(self.features),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CompilerOperatorRecord":
        if not isinstance(value, Mapping):
            raise CompilerIdiomError("operator record must be an object")
        allowed = {"operator_id", "kind", "before", "after", "features"}
        unknown = set(value).difference(allowed)
        if unknown:
            raise CompilerIdiomError(
                "operator record has unknown fields: " + ", ".join(sorted(unknown))
            )
        for name in ("kind", "before", "after"):
            if name not in value:
                raise CompilerIdiomError(f"operator record missing {name}")
        return cls(
            kind=value["kind"],
            before=value["before"],
            after=value["after"],
            features=value.get("features", {}),
            operator_id=value.get("operator_id", ""),
        )


def _operator_kind(before: str, after: str) -> str:
    """Classify one hunk without pretending the class proves equivalence."""
    text = f"{before}\n{after}"
    if re.search(r"\b(if|else|switch|case|for|while|do|goto)\b|[{}]", text):
        return "control_flow"
    if re.search(r"\b(struct|union|enum)\b|\b(?:u|s|f)(?:8|16|32|64)\b", text):
        return "type_layout"
    if before.strip() == "" or after.strip() == "":
        return "declaration"
    if re.search(r"\b(?:static|const|volatile|extern)\b", text):
        return "declaration"
    if "(" in text and ")" in text:
        return "call_or_expression"
    if "=" in text:
        return "assignment"
    return "expression"


def _shape(text: str) -> str:
    """Return a conservative shape feature while retaining exact text."""
    without_comments = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    without_strings = re.sub(r'"(?:\\.|[^"\\])*"', '"STR"', without_comments)
    without_numbers = re.sub(r"\b(?:0[xX][0-9a-fA-F]+|\d+)\b", "NUM", without_strings)
    # Identifiers are deliberately not normalized.  Doing so without field or
    # type evidence is how unrelated transformations become false idioms.
    return re.sub(r"\s+", " ", without_numbers).strip()


def _operator_features(before: str, after: str) -> dict[str, Any]:
    return {
        "declaration_order": tuple(
            line.strip() for line in before.splitlines() if line.strip()
        ),
        "control_flow_shape": tuple(
            token
            for token in ("if", "else", "switch", "case", "for", "while", "goto")
            if re.search(rf"\b{token}\b", f"{before}\n{after}")
        ),
        "expression_shape_before": _shape(before),
        "expression_shape_after": _shape(after),
    }


def _patch_identity(
    patch_format: str, base_source_hash: str, hunks: Sequence[PatchHunk]
) -> str:
    return hash_canonical(
        {
            "format": patch_format,
            "base_source_hash": base_source_hash,
            "atomic": True,
            "hunks": tuple(hunks),
        }
    )


def _idiom_identity(
    *,
    compiler_identity: str,
    tool_identity: Optional[str],
    config_identity: Optional[str],
    before: ArtifactRef,
    after: ArtifactRef,
    grouped_patches: Sequence[GroupedPatch],
    supporting_pair_hashes: Sequence[str],
    operator_records: Sequence[CompilerOperatorRecord],
    measurement: Mapping[str, Any],
) -> str:
    """Hash every identity-bearing field in one immutable idiom record."""
    return hash_canonical(
        {
            "kind": MODULE_VERSION,
            "compiler_identity": compiler_identity,
            "tool_identity": tool_identity,
            "config_identity": config_identity,
            "before": before,
            "after": after,
            "grouped_patches": tuple(grouped_patches),
            "supporting_pair_hashes": tuple(sorted(supporting_pair_hashes)),
            "operator_records": tuple(sorted(operator_records, key=lambda item: item.operator_id)),
            "measurement": measurement,
        }
    )


def make_grouped_patch(
    before: str,
    after: str,
    *,
    patch_format: str = "line_context",
    context_lines: int = 3,
) -> GroupedPatch:
    """Create one atomic patch containing all source changes.

    A no-change pair receives a deterministic no-op hunk because the shared
    schema requires at least one hunk.
    """
    if not isinstance(before, str) or not isinstance(after, str):
        raise TypeError("patch sources must be strings")
    if patch_format != "line_context":
        raise CompilerIdiomError(
            "only line_context grouped patches are implemented"
        )
    if isinstance(context_lines, bool) or not isinstance(context_lines, int):
        raise CompilerIdiomError("context_lines must be an integer")
    if context_lines < 0 or context_lines > 16:
        raise CompilerIdiomError("context_lines must be between zero and sixteen")

    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(
        a=before_lines, b=after_lines, autojunk=False
    )
    hunks: list[PatchHunk] = []
    ordinal = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        hunks.append(
            PatchHunk(
                ordinal=ordinal,
                before="".join(before_lines[i1:i2]),
                after="".join(after_lines[j1:j2]),
                leading_context=tuple(before_lines[max(0, i1 - context_lines):i1]),
                trailing_context=tuple(before_lines[i2:i2 + context_lines]),
                ast_path=None,
            )
        )
        ordinal += 1
    if not hunks:
        hunks.append(PatchHunk(0, before, before, (), ()))
    base_hash = source_hash(before)
    patch_id = _patch_identity(patch_format, base_hash, hunks)
    return GroupedPatch(
        patch_id=patch_id,
        format=patch_format,
        base_source_hash=base_hash,
        atomic=True,
        hunks=tuple(hunks),
    )


def operator_records_for_patch(
    patch: GroupedPatch,
) -> tuple[CompilerOperatorRecord, ...]:
    """Derive exact, deterministic operator records from one grouped patch."""
    records = [
        CompilerOperatorRecord(
            kind=_operator_kind(hunk.before, hunk.after),
            before=hunk.before,
            after=hunk.after,
            features=_operator_features(hunk.before, hunk.after),
        )
        for hunk in sorted(patch.hunks, key=lambda item: item.ordinal)
    ]
    return tuple(sorted(records, key=lambda item: item.operator_id))


@dataclass(frozen=True)
class ImprovementMeasurement:
    """An explicit score or checksum result used to accept an idiom."""

    kind: str
    before: Mapping[str, Any]
    after: Mapping[str, Any]
    improved: bool
    exact: bool = False
    evaluator_identity: Optional[str] = None
    target_identity: Optional[str] = None
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ("score", "checksum"):
            raise MeasurementError("measurement kind must be score or checksum")
        before = _freeze_json(self.before, "measurement.before")
        after = _freeze_json(self.after, "measurement.after")
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            raise MeasurementError("measurements must be objects")
        object.__setattr__(self, "before", before)
        object.__setattr__(self, "after", after)
        if not isinstance(self.improved, bool) or not self.improved:
            raise MeasurementError("an idiom requires an explicit improvement")
        if not isinstance(self.exact, bool):
            raise MeasurementError("measurement exact flag must be boolean")
        if self.evaluator_identity is not None:
            validate_hash(self.evaluator_identity, "evaluator_identity")
        if self.target_identity is not None:
            validate_hash(self.target_identity, "target_identity")
        object.__setattr__(self, "evidence", _unique_sorted(self.evidence, "evidence"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "before": _plain(self.before),
            "after": _plain(self.after),
            "improved": self.improved,
            "exact": self.exact,
            "evaluator_identity": self.evaluator_identity,
            "target_identity": self.target_identity,
            "evidence": list(self.evidence),
        }


def _measurement_value(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        if key in value:
            return value[key]
        score = value.get("score")
        if isinstance(score, Mapping):
            return score.get(key)
    return getattr(value, key, None)


def _as_measurement_map(value: Any, label: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    total = _measurement_value(value, "total")
    object_hash = _measurement_value(value, "object_hash")
    checksum = _measurement_value(value, "checksum")
    compile_status = _measurement_value(value, "compile_status")
    if total is None and object_hash is None and checksum is None:
        raise MeasurementError(f"{label} has no measured score or checksum")
    return {
        "total": total,
        "object_hash": object_hash,
        "checksum": checksum,
        "compile_status": compile_status,
    }


def measure_improvement(
    before: Any,
    after: Any,
    *,
    target_object_hash: Optional[str] = None,
    target_checksum: Optional[str] = None,
    evaluator_identity: Optional[str] = None,
    evidence: Iterable[str] = (),
) -> Optional[ImprovementMeasurement]:
    """Return a measurement only when lower score or exact hash is proven.

    A changed commit, a different filename, or an adjacency relationship is
    never considered evidence.  Successful score totals must be numeric and
    exact checksums must name the expected target identity.
    """
    if before is None or after is None:
        return None
    before_map = _as_measurement_map(before, "before")
    after_map = _as_measurement_map(after, "after")
    for label, measured in (("before", before_map), ("after", after_map)):
        status = _measurement_value(measured, "compile_status")
        if status is not None and status != "success":
            return None
        for hash_key in ("object_hash", "checksum"):
            hash_value = _measurement_value(measured, hash_key)
            if hash_value is not None:
                try:
                    validate_hash(hash_value, f"{label}.{hash_key}")
                except SearchValidationError as exc:
                    raise MeasurementError(f"{label}.{hash_key} is not a sha256 hash") from exc
    if evaluator_identity is not None:
        try:
            validate_hash(evaluator_identity, "evaluator_identity")
        except SearchValidationError as exc:
            raise MeasurementError("evaluator_identity is not a sha256 hash") from exc
    if target_object_hash is not None and target_checksum is not None:
        if target_object_hash != target_checksum:
            raise MeasurementError("target object and checksum identities disagree")
    for label, target in (("target_object_hash", target_object_hash), ("target_checksum", target_checksum)):
        if target is not None:
            try:
                validate_hash(target, label)
            except SearchValidationError as exc:
                raise MeasurementError(f"{label} is not a sha256 hash") from exc
    before_total = _measurement_value(before_map, "total")
    after_total = _measurement_value(after_map, "total")
    if isinstance(before_total, bool) or isinstance(after_total, bool):
        before_total = after_total = None
    if isinstance(before_total, float) and not math.isfinite(before_total):
        before_total = None
    if isinstance(after_total, float) and not math.isfinite(after_total):
        after_total = None
    score_better = (
        isinstance(before_total, (int, float))
        and isinstance(after_total, (int, float))
        and after_total < before_total
    )
    after_object = _measurement_value(after_map, "object_hash")
    after_checksum = _measurement_value(after_map, "checksum")
    expected_object = target_object_hash or target_checksum
    exact = bool(
        expected_object
        and isinstance(expected_object, str)
        and (after_object == expected_object or after_checksum == expected_object)
    )
    if exact:
        validate_hash(expected_object, "target checksum")
    if score_better:
        return ImprovementMeasurement(
            kind="score",
            before=before_map,
            after=after_map,
            improved=True,
            exact=exact,
            evaluator_identity=evaluator_identity,
            target_identity=expected_object,
            evidence=tuple(evidence),
        )
    if exact:
        return ImprovementMeasurement(
            kind="checksum",
            before=before_map,
            after=after_map,
            improved=True,
            exact=True,
            evaluator_identity=evaluator_identity,
            target_identity=expected_object,
            evidence=tuple(evidence),
        )
    return None


@dataclass(frozen=True)
class CompilerIdiomObservation:
    """A compiler-bound transformation supported by one or more exact pairs."""

    observation_id: str
    compiler_identity: str
    before: ArtifactRef
    after: ArtifactRef
    grouped_patches: tuple[GroupedPatch, ...]
    supporting_pair_hashes: tuple[str, ...]
    tool_identity: Optional[str] = None
    config_identity: Optional[str] = None
    operator_records: tuple[CompilerOperatorRecord, ...] = ()
    measurement: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_hash(self.observation_id, "observation_id")
        validate_hash(self.compiler_identity, "compiler_identity")
        if self.tool_identity is not None:
            validate_hash(self.tool_identity, "tool_identity")
        if self.config_identity is not None:
            validate_hash(self.config_identity, "config_identity")
        before = _coerce_artifact(self.before, "before")
        after = _coerce_artifact(self.after, "after")
        object.__setattr__(self, "before", before)
        object.__setattr__(self, "after", after)
        patches = tuple(_coerce_patch(item) for item in self.grouped_patches)
        if not patches:
            raise CompilerIdiomError("idiom needs at least one grouped patch")
        object.__setattr__(self, "grouped_patches", patches)
        pairs = tuple(self.supporting_pair_hashes)
        if len(set(pairs)) != len(pairs):
            raise CompilerIdiomError("supporting pair identities must be unique")
        for pair in pairs:
            validate_hash(pair, "supporting_pair_hash")
        object.__setattr__(self, "supporting_pair_hashes", tuple(sorted(pairs)))
        records = tuple(
            item if isinstance(item, CompilerOperatorRecord)
            else CompilerOperatorRecord.from_dict(item)
            for item in self.operator_records
        )
        if not records:
            raise CompilerIdiomError("idiom needs operator records")
        object.__setattr__(self, "operator_records", tuple(sorted(records, key=lambda item: item.operator_id)))
        measurement = _freeze_json(self.measurement, "measurement")
        if not isinstance(measurement, Mapping):
            raise CompilerIdiomError("measurement must be an object")
        object.__setattr__(self, "measurement", measurement)
        expected = _idiom_identity(
            compiler_identity=self.compiler_identity,
            tool_identity=self.tool_identity,
            config_identity=self.config_identity,
            before=self.before,
            after=self.after,
            grouped_patches=self.grouped_patches,
            supporting_pair_hashes=self.supporting_pair_hashes,
            operator_records=self.operator_records,
            measurement=self.measurement,
        )
        if self.observation_id != expected:
            raise CompilerIdiomError("observation_id does not match record content")

    @property
    def support_count(self) -> int:
        return len(self.supporting_pair_hashes)

    @property
    def identity(self) -> str:
        return _idiom_identity(
            compiler_identity=self.compiler_identity,
            tool_identity=self.tool_identity,
            config_identity=self.config_identity,
            before=self.before,
            after=self.after,
            grouped_patches=self.grouped_patches,
            supporting_pair_hashes=self.supporting_pair_hashes,
            operator_records=self.operator_records,
            measurement=self.measurement,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "compiler_identity": self.compiler_identity,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "grouped_patches": [item.to_dict() for item in self.grouped_patches],
            "supporting_pair_hashes": list(self.supporting_pair_hashes),
            "tool_identity": self.tool_identity,
            "config_identity": self.config_identity,
            "operator_records": [item.to_dict() for item in self.operator_records],
            "measurement": _plain(self.measurement),
        }

    def to_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CompilerIdiomObservation":
        if not isinstance(value, Mapping):
            raise CompilerIdiomError("idiom observation must be an object")
        required = {
            "observation_id", "compiler_identity", "before", "after",
            "grouped_patches", "supporting_pair_hashes",
        }
        allowed = required | {
            "tool_identity", "config_identity", "operator_records", "measurement",
        }
        missing = required.difference(value)
        unknown = set(value).difference(allowed)
        if missing or unknown:
            detail = []
            if missing:
                detail.append("missing=" + ",".join(sorted(missing)))
            if unknown:
                detail.append("unknown=" + ",".join(sorted(unknown)))
            raise CompilerIdiomError("invalid idiom observation (" + "; ".join(detail) + ")")
        try:
            return cls(
                observation_id=value["observation_id"],
                compiler_identity=value["compiler_identity"],
                before=ArtifactRef.from_dict(value["before"]),
                after=ArtifactRef.from_dict(value["after"]),
                grouped_patches=tuple(GroupedPatch.from_dict(item) for item in value["grouped_patches"]),
                supporting_pair_hashes=tuple(value["supporting_pair_hashes"]),
                tool_identity=value.get("tool_identity"),
                config_identity=value.get("config_identity"),
                operator_records=tuple(
                    CompilerOperatorRecord.from_dict(item)
                    for item in value.get("operator_records", ())
                ),
                measurement=value.get("measurement", {}),
            )
        except (SearchValidationError, TypeError, KeyError, ValueError) as exc:
            raise CompilerIdiomError("invalid idiom observation values") from exc


@dataclass(frozen=True)
class DraftLandedObservation:
    """One provenance-proven draft to verified landed source transition."""

    recipient_id: str
    draft: ArtifactRef
    landed: ArtifactRef
    landing_commit: str
    compiler_identity: str
    grouped_patches: tuple[GroupedPatch, ...]
    evidence: tuple[str, ...]
    draft_commit: Optional[str] = None
    draft_ref: Optional[str] = None
    landing_ref: Optional[str] = None
    tool_identity: Optional[str] = None
    config_identity: Optional[str] = None
    measurement: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_id(self.recipient_id, "recipient_id")
        object.__setattr__(self, "draft", _coerce_artifact(self.draft, "draft"))
        object.__setattr__(self, "landed", _coerce_artifact(self.landed, "landed"))
        object.__setattr__(
            self, "landing_commit", validate_commit_identity(self.landing_commit, "landing_commit")
        )
        validate_hash(self.compiler_identity, "compiler_identity")
        for label, value in (
            ("draft_commit", self.draft_commit),
        ):
            if value is not None:
                object.__setattr__(self, label, validate_commit_identity(value, label))
        if self.tool_identity is not None:
            validate_hash(self.tool_identity, "tool_identity")
        if self.config_identity is not None:
            validate_hash(self.config_identity, "config_identity")
        patches = tuple(_coerce_patch(item) for item in self.grouped_patches)
        if not patches:
            raise CompilerIdiomError("draft-landed observation needs a grouped patch")
        object.__setattr__(self, "grouped_patches", patches)
        evidence = tuple(self.evidence)
        if len(set(evidence)) != len(evidence) or any(
            not isinstance(item, str) or not item for item in evidence
        ):
            raise CompilerIdiomError("evidence must contain unique nonempty strings")
        object.__setattr__(self, "evidence", tuple(sorted(evidence)))
        measurement = _freeze_json(self.measurement, "measurement")
        if not isinstance(measurement, Mapping):
            raise CompilerIdiomError("measurement must be an object")
        object.__setattr__(self, "measurement", measurement)

    @property
    def pair_hash(self) -> str:
        return hash_canonical(
            {
                "kind": "draft-landed-pair-v1",
                "recipient_id": self.recipient_id,
                "draft": self.draft,
                "landed": self.landed,
                "landing_commit": self.landing_commit,
                "draft_commit": self.draft_commit,
                "draft_ref": self.draft_ref,
                "landing_ref": self.landing_ref,
                "compiler_identity": self.compiler_identity,
                "tool_identity": self.tool_identity,
                "config_identity": self.config_identity,
                "grouped_patches": self.grouped_patches,
                "evidence": self.evidence,
                "measurement": self.measurement,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipient_id": self.recipient_id,
            "draft": self.draft.to_dict(),
            "landed": self.landed.to_dict(),
            "landing_commit": self.landing_commit,
            "compiler_identity": self.compiler_identity,
            "grouped_patches": [item.to_dict() for item in self.grouped_patches],
            "evidence": list(self.evidence),
            "draft_commit": self.draft_commit,
            "draft_ref": self.draft_ref,
            "landing_ref": self.landing_ref,
            "tool_identity": self.tool_identity,
            "config_identity": self.config_identity,
            "measurement": _plain(self.measurement),
        }

    def to_json(self) -> str:
        return canonical_json(self)


def make_idiom_observation(
    pair: DraftLandedObservation,
    *,
    operators: Optional[Sequence[CompilerOperatorRecord]] = None,
) -> CompilerIdiomObservation:
    """Create one idiom observation from an accepted measured pair."""
    if not pair.measurement or not pair.measurement.get("improved", False):
        raise MeasurementError("pair has no accepted improvement measurement")
    records = tuple(operators or operator_records_for_patch(pair.grouped_patches[0]))
    observation_id = _idiom_identity(
        compiler_identity=pair.compiler_identity,
        tool_identity=pair.tool_identity,
        config_identity=pair.config_identity,
        before=pair.draft,
        after=pair.landed,
        grouped_patches=pair.grouped_patches,
        supporting_pair_hashes=(pair.pair_hash,),
        operator_records=records,
        measurement=pair.measurement,
    )
    return CompilerIdiomObservation(
        observation_id=observation_id,
        compiler_identity=pair.compiler_identity,
        before=pair.draft,
        after=pair.landed,
        grouped_patches=pair.grouped_patches,
        supporting_pair_hashes=(pair.pair_hash,),
        tool_identity=pair.tool_identity,
        config_identity=pair.config_identity,
        operator_records=records,
        measurement=pair.measurement,
    )


def deduplicate_idioms(
    observations: Iterable[CompilerIdiomObservation],
) -> tuple[CompilerIdiomObservation, ...]:
    """Merge identical operators deterministically while retaining all support."""
    groups: dict[str, list[CompilerIdiomObservation]] = {}
    for item in observations:
        if not isinstance(item, CompilerIdiomObservation):
            item = CompilerIdiomObservation.from_dict(item)  # type: ignore[arg-type]
        # Group by the exact operator, not by the source-specific patch base.
        # The same compiler idiom can recur in different source files.
        key = hash_canonical(
            {
                "compiler_identity": item.compiler_identity,
                "tool_identity": item.tool_identity,
                "config_identity": item.config_identity,
                "operator_records": item.operator_records,
            }
        )
        groups.setdefault(key, []).append(item)

    merged: list[CompilerIdiomObservation] = []
    for key, values in sorted(groups.items()):
        representative = min(
            values,
            key=lambda item: (
                item.before.content_hash,
                item.after.content_hash,
                item.observation_id,
            ),
        )
        pairs = tuple(
            sorted(
                {
                    pair
                    for value in values
                    for pair in value.supporting_pair_hashes
                }
            )
        )
        observation_id = _idiom_identity(
            compiler_identity=representative.compiler_identity,
            tool_identity=representative.tool_identity,
            config_identity=representative.config_identity,
            before=representative.before,
            after=representative.after,
            grouped_patches=representative.grouped_patches,
            supporting_pair_hashes=pairs,
            operator_records=representative.operator_records,
            measurement=representative.measurement,
        )
        merged.append(
            CompilerIdiomObservation(
                observation_id=observation_id,
                compiler_identity=representative.compiler_identity,
                before=representative.before,
                after=representative.after,
                grouped_patches=representative.grouped_patches,
                supporting_pair_hashes=pairs,
                tool_identity=representative.tool_identity,
                config_identity=representative.config_identity,
                operator_records=representative.operator_records,
                measurement=representative.measurement,
            )
        )
    return tuple(sorted(merged, key=lambda item: item.observation_id))


def replay_grouped_patch(source: str, patch: GroupedPatch) -> Any:
    """Use the shared atomic replay implementation without mutating ``source``."""
    try:
        from .search_mutations import replay_grouped_patch as replay
    except ImportError:  # pragma: no cover - direct script compatibility
        from search_mutations import replay_grouped_patch as replay  # type: ignore
    return replay(source, patch)


__all__ = [
    "MODULE_VERSION",
    "CompilerIdiomError",
    "MeasurementError",
    "CompilerIdentity",
    "CompilerOperatorRecord",
    "CompilerIdiomObservation",
    "DraftLandedObservation",
    "ImprovementMeasurement",
    "source_hash",
    "validate_commit_identity",
    "make_grouped_patch",
    "operator_records_for_patch",
    "measure_improvement",
    "make_idiom_observation",
    "deduplicate_idioms",
    "replay_grouped_patch",
    "canonical_bytes",
    "canonical_json",
    "hash_bytes",
    "hash_canonical",
    "validate_relative_path",
]
