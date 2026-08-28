"""Provenance-strict mining of historical draft-to-landed transitions.

The miner is intentionally read-only.  It accepts immutable candidate history,
queue provenance and a verified commit provider, then returns value objects and
typed refusals.  It never edits a source or donor file, uses filesystem times,
or treats commit adjacency as evidence that two artifacts belong together.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Optional, Protocol, runtime_checkable

try:
    from .compiler_idioms import (
        CompilerIdiomError,
        CompilerIdiomObservation,
        DraftLandedObservation,
        MeasurementError,
        deduplicate_idioms,
        hash_canonical,
        make_grouped_patch,
        make_idiom_observation,
        measure_improvement,
        source_hash,
        validate_relative_path,
        validate_commit_identity,
    )
    from .search_types import ArtifactRef, SearchValidationError, validate_id
except ImportError:  # pragma: no cover - direct script compatibility
    from compiler_idioms import (  # type: ignore
        CompilerIdiomError,
        CompilerIdiomObservation,
        DraftLandedObservation,
        MeasurementError,
        deduplicate_idioms,
        hash_canonical,
        make_grouped_patch,
        make_idiom_observation,
        measure_improvement,
        source_hash,
        validate_relative_path,
        validate_commit_identity,
    )
    from search_types import ArtifactRef, SearchValidationError, validate_id  # type: ignore


MODULE_VERSION = "draft-landed-miner-v1"
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RAW_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")
_GLOBAL_RECIPIENT = "unknown"


class MinerError(RuntimeError):
    """Base error for strict miner/provider failures."""


class ProviderError(MinerError):
    """A commit provider could not prove an immutable blob."""


class CorruptEvidence(MinerError):
    """Declared content and resolved content disagree."""


class AmbiguousEvidence(MinerError):
    """More than one endpoint satisfies incomplete provenance."""


class RefusalCode:
    """Stable machine-readable refusal codes."""

    MISSING_DRAFT = "missing_draft"
    AMBIGUOUS_DRAFT = "ambiguous_draft"
    MISSING_LANDING_COMMIT = "missing_landing_commit"
    AMBIGUOUS_LANDING = "ambiguous_landing"
    MISMATCHED_RECIPIENT = "mismatched_recipient"
    MISSING_QUEUE_PROVENANCE = "missing_queue_provenance"
    MISSING_ARTIFACT = "missing_artifact"
    MISSING_ARTIFACT_BYTES = "missing_artifact_bytes"
    CORRUPT_ARTIFACT = "corrupt_artifact"
    INVALID_COMMIT = "invalid_commit_identity"
    UNVERIFIED_COMMIT = "unverified_commit"
    PROVIDER_FAILURE = "provider_failure"
    IDENTITY_MISMATCH = "identity_mismatch"
    MISSING_IDENTITY = "missing_identity"
    UNMEASURED = "unmeasured_transition"
    NO_SOURCE_CHANGE = "no_source_change"
    INVALID_PROVENANCE = "invalid_provenance"
    DUPLICATE_CONFLICT = "duplicate_conflict"


@dataclass(frozen=True)
class MinerRefusal:
    """Typed, deterministic refusal for one recipient/input boundary."""

    recipient_id: str
    code: str
    reason: str
    input_identities: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.recipient_id, str) or not self.recipient_id:
            raise MinerError("refusal recipient_id must be nonempty")
        if not isinstance(self.code, str) or not self.code:
            raise MinerError("refusal code must be nonempty")
        if not isinstance(self.reason, str) or not self.reason:
            raise MinerError("refusal reason must be nonempty")
        inputs = tuple(sorted(set(self.input_identities)))
        if any(not isinstance(item, str) or not item for item in inputs):
            raise MinerError("refusal input identities must be nonempty strings")
        evidence = tuple(sorted(set(self.evidence)))
        if any(not isinstance(item, str) or not item for item in evidence):
            raise MinerError("refusal evidence must be nonempty strings")
        object.__setattr__(self, "input_identities", inputs)
        object.__setattr__(self, "evidence", evidence)

    @property
    def reason_code(self) -> str:
        return self.code

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipient_id": self.recipient_id,
            "code": self.code,
            "reason": self.reason,
            "input_identities": list(self.input_identities),
            "evidence": list(self.evidence),
        }


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise MinerError("evidence mapping keys must be strings")
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise MinerError("evidence must contain JSON values")


def _plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, bytes):
        return {"sha256": source_hash(value), "byte_size": len(value)}
    if dataclasses.is_dataclass(value):
        return {
            field.name: _plain(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    return value


def _as_bytes(value: Any, label: str) -> Optional[bytes]:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    raise CorruptEvidence(f"{label} content must be UTF-8 text or bytes")


def _valid_hash(value: Any) -> Optional[str]:
    if isinstance(value, str) and _HASH_RE.fullmatch(value):
        return value
    return None


def _declared_content_hash(value: Mapping[str, Any]) -> Optional[str]:
    for key in ("content_hash", "source_hash"):
        found = _valid_hash(value.get(key))
        if found is not None:
            return found
    return None


def _explicit_content(value: Any) -> Optional[bytes]:
    if isinstance(value, Mapping):
        # ``source`` is often a path in existing records, so it is deliberately
        # excluded.  Only explicit content fields can supply bytes.
        for key in ("content", "source_text", "body_text", "text"):
            if key in value:
                return _as_bytes(value[key], "artifact")
    return None


def _artifact_from(value: Any, *, label: str) -> tuple[ArtifactRef, Optional[bytes]]:
    if isinstance(value, ArtifactRef):
        return value, None
    if not isinstance(value, Mapping):
        raise CorruptEvidence(f"{label} artifact must be an object")
    content = _explicit_content(value)
    path = value.get("path")
    if not isinstance(path, str) or not path:
        raise CorruptEvidence(f"{label} artifact has no path")
    declared = _declared_content_hash(value)
    if content is not None:
        actual = source_hash(content)
        if declared is not None and declared != actual:
            raise CorruptEvidence(f"{label} content hash does not match bytes")
        declared = actual
    if declared is None:
        raise CorruptEvidence(f"{label} artifact has no content hash")
    media_type = value.get("media_type")
    if not isinstance(media_type, str) or not media_type:
        media_type = "text/x-c" if path.casefold().endswith(".c") else "application/octet-stream"
    byte_size = value.get("byte_size")
    if byte_size is None and content is not None:
        byte_size = len(content)
    if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 0:
        raise CorruptEvidence(f"{label} artifact has no valid byte_size")
    if content is not None and byte_size != len(content):
        raise CorruptEvidence(f"{label} byte_size does not match bytes")
    try:
        artifact = ArtifactRef(declared, path, media_type, byte_size)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise CorruptEvidence(f"invalid {label} artifact") from exc
    return artifact, content


def _recipient(value: Any, fallback: Optional[str] = None) -> Optional[str]:
    if isinstance(value, Mapping):
        candidate = value.get("recipient_id")
        if isinstance(candidate, str) and candidate:
            return candidate
    if isinstance(value, str) and value:
        return value
    return fallback


def _commit_token(value: Mapping[str, Any], kind: str) -> Optional[str]:
    key = "draft_commit" if kind == "draft" else "landing_commit"
    candidate = value.get(key)
    return candidate if isinstance(candidate, str) and candidate else None


def _ref_token(value: Mapping[str, Any], kind: str) -> Optional[str]:
    key = "draft_ref" if kind == "draft" else "landing_ref"
    candidate = value.get(key)
    return candidate if isinstance(candidate, str) and candidate else None


def _identity(value: Mapping[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _source_id(value: Mapping[str, Any], fallback: Optional[str]) -> Optional[str]:
    found = _identity(value, "provenance_id", "evidence_id")
    if found is not None:
        return found
    return fallback


def _record_identity(value: Any, *, label: str) -> Optional[str]:
    """Return an evidence identity only when content/commit context exists."""
    if not isinstance(value, Mapping):
        return None
    explicit = _identity(value, "provenance_id", "evidence_id", "record_id")
    if _valid_hash(explicit):
        return explicit
    content_hash = _declared_content_hash(value)
    commit = _commit_token(value, "draft") or _commit_token(value, "landing")
    recipient = _recipient(value)
    if content_hash is None and commit is None:
        return None
    # The path is not part of this fallback identity.  It is only a context
    # field in the provenance record, never a source of identity.
    return hash_canonical(
        {
            "kind": label,
            "recipient_id": recipient,
            "content_hash": content_hash,
            "commit": commit.lower() if isinstance(commit, str) else None,
            "ref": _ref_token(value, "draft") or _ref_token(value, "landing"),
            "generation": value.get("generation_id"),
        }
    )


@dataclass(frozen=True)
class VerifiedCommit:
    """An immutable commit snapshot returned by a verified provider."""

    commit_id: str
    ref: Optional[str] = None
    files: Mapping[str, bytes] = field(default_factory=dict)
    parent_commit_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "commit_id", validate_commit_identity(self.commit_id))
        if self.ref is not None and (not isinstance(self.ref, str) or not self.ref):
            raise ProviderError("commit ref must be nonempty or null")
        normalized: dict[str, bytes] = {}
        for path, content in self.files.items():
            if not isinstance(path, str) or not path:
                raise ProviderError("commit file path must be nonempty")
            normalized_path = path.replace("\\", "/")
            try:
                validate_relative_path(normalized_path, "commit file path")
            except (SearchValidationError, TypeError, ValueError) as exc:
                raise ProviderError("commit file path must be relative") from exc
            normalized[normalized_path] = _as_bytes(content, "commit blob") or b""
        object.__setattr__(self, "files", MappingProxyType(normalized))
        parents = tuple(self.parent_commit_ids)
        for parent in parents:
            validate_commit_identity(parent, "parent_commit_id")
        object.__setattr__(self, "parent_commit_ids", tuple(sorted(set(parents))))

    def blob(self, path: str) -> bytes:
        normalized = path.replace("\\", "/")
        if normalized not in self.files:
            raise KeyError(normalized)
        return self.files[normalized]

    def to_dict(self) -> dict[str, Any]:
        return {
            "commit_id": self.commit_id,
            "ref": self.ref,
            "files": {
                path: {"sha256": source_hash(content), "byte_size": len(content)}
                for path, content in sorted(self.files.items())
            },
            "parent_commit_ids": list(self.parent_commit_ids),
        }


@runtime_checkable
class VerifiedCommitProvider(Protocol):
    """Minimal provider contract used by the miner.

    ``resolve_commit`` must turn a ref or full object ID into a
    :class:`VerifiedCommit` or an equivalent mapping.  ``read_blob`` may be
    omitted when the resolved value carries a complete ``files`` mapping.
    """

    def resolve_commit(self, ref: str) -> VerifiedCommit: ...

    def read_blob(self, commit: VerifiedCommit, path: str) -> bytes: ...


class MappingCommitResolver:
    """Deterministic in-memory provider used by tests and offline callers."""

    def __init__(
        self,
        commits: Mapping[str, VerifiedCommit | Mapping[str, Any]],
        refs: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._commits: dict[str, VerifiedCommit] = {}
        for key, value in commits.items():
            commit = _coerce_commit(value, str(key))
            self._commits[commit.commit_id] = commit
            if isinstance(key, str) and _RAW_COMMIT_RE.fullmatch(key):
                # An object identity is immutable and may be used directly.
                if key.lower() != commit.commit_id:
                    raise ProviderError("commit mapping key disagrees with object identity")
        self._refs = {
            str(name).lower(): str(commit).lower()
            for name, commit in (refs or {}).items()
        }

    def resolve_commit(self, ref: str) -> VerifiedCommit:
        if not isinstance(ref, str) or not ref:
            raise ProviderError("empty commit/ref")
        token = ref.lower()
        if token in self._refs:
            token = self._refs[token].lower()
        if token not in self._commits:
            raise ProviderError(f"unverified commit/ref: {ref}")
        return self._commits[token]

    def read_blob(self, commit: VerifiedCommit, path: str) -> bytes:
        resolved = commit
        try:
            return resolved.blob(path)
        except KeyError as exc:
            raise ProviderError(f"commit {resolved.commit_id} lacks {path}") from exc

def _coerce_commit(value: Any, requested: str) -> VerifiedCommit:
    if isinstance(value, VerifiedCommit):
        return value
    if not isinstance(value, Mapping):
        raise ProviderError("resolver returned an invalid commit")
    commit_id = value.get("commit_id")
    if not isinstance(commit_id, str):
        raise ProviderError("resolver did not return an immutable commit identity")
    files = value.get("files", {})
    if not isinstance(files, Mapping):
        raise ProviderError("resolver commit files must be an object")
    normalized: dict[str, bytes] = {}
    for path, blob in files.items():
        if isinstance(blob, Mapping):
            if "content" in blob:
                blob = blob["content"]
            else:
                # A verified provider may return a tree manifest and expose
                # its bytes through read_blob.  Keep metadata-only entries out
                # of VerifiedCommit.files so the read method is consulted.
                continue
        normalized[str(path)] = _as_bytes(blob, "commit blob") or b""
    return VerifiedCommit(
        commit_id=commit_id,
        ref=value.get("ref") if isinstance(value.get("ref"), str) else requested,
        files=normalized,
        parent_commit_ids=tuple(value.get("parent_commit_ids", ())),
    )


def _provider_resolve(provider: Any, token: str) -> VerifiedCommit:
    method = getattr(provider, "resolve_commit", None)
    if not callable(method):
        raise ProviderError("provider must implement resolve_commit(ref)")
    try:
        result = method(token)
    except TypeError:
        # TypeError is allowed to cross this boundary.  It is an invocation
        # failure, not a signal to call the provider again with another shape.
        raise
    except Exception as exc:  # noqa: BLE001 - provider boundary
        raise ProviderError(f"provider cannot resolve commit/ref: {exc}") from exc
    commit = _coerce_commit(result, token)
    if _RAW_COMMIT_RE.fullmatch(token or "") and token.lower() != commit.commit_id:
        raise ProviderError("provider resolved a different object than requested")
    return commit


def _provider_blob(provider: Any, commit: VerifiedCommit, path: str) -> bytes:
    if commit.files:
        try:
            return commit.blob(path)
        except KeyError:
            # A provider may return metadata-only files and expose the blob via
            # its read method.  Continue to that method before refusing.
            pass
    method = getattr(provider, "read_blob", None)
    if not callable(method):
        raise ProviderError(
            f"provider must implement read_blob(commit, path) for {commit.commit_id}"
        )
    try:
        result = method(commit, path)
    except TypeError:
        # Never retry after invoking a provider.  An implementation TypeError
        # must remain observable to the caller and to the typed miner refusal.
        raise
    except Exception as exc:  # noqa: BLE001 - provider boundary
        raise ProviderError(f"provider failed to read {path}: {exc}") from exc
    blob = _as_bytes(result, f"provider blob {path}")
    if blob is None:
        raise ProviderError(f"provider returned no bytes for {path}")
    return blob


@dataclass(frozen=True)
class _Endpoint:
    kind: str
    recipient_id: str
    artifact: ArtifactRef
    content: Optional[bytes]
    commit_token: Optional[str]
    ref: Optional[str]
    generation: Optional[str]
    compiler_identity: Optional[str]
    tool_identity: Optional[str]
    config_identity: Optional[str]
    score: Any = None
    before_score: Any = None
    after_score: Any = None
    target_object_hash: Optional[str] = None
    target_checksum: Optional[str] = None
    verified: bool = False
    source_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind not in ("draft", "landing"):
            raise MinerError("endpoint kind is invalid")
        try:
            validate_id(self.recipient_id, "recipient_id")
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise MinerError("endpoint recipient is invalid") from exc
        for label in ("score", "before_score", "after_score"):
            value = getattr(self, label)
            if value is not None:
                try:
                    object.__setattr__(self, label, _freeze_json(value))
                except (MinerError, TypeError, ValueError) as exc:
                    raise MinerError(f"endpoint {label} is not JSON evidence") from exc

    @property
    def endpoint_identity(self) -> str:
        return hash_canonical(
            {
                "kind": self.kind,
                "recipient_id": self.recipient_id,
                "artifact": self.artifact,
                "commit": self.commit_token,
                "ref": self.ref,
                "generation": self.generation,
                "compiler_identity": self.compiler_identity,
                "tool_identity": self.tool_identity,
                "config_identity": self.config_identity,
                "source_id": self.source_id,
            }
        )


def _endpoint_from(
    value: Any,
    *,
    kind: str,
    fallback_recipient: Optional[str] = None,
    parent_identity: Optional[str] = None,
) -> _Endpoint:
    if isinstance(value, _Endpoint):
        return value
    if not isinstance(value, Mapping):
        raise CorruptEvidence(f"{kind} provenance must be an object")
    rid = _recipient(value, fallback_recipient)
    if rid is None:
        raise CorruptEvidence(f"{kind} provenance has no recipient")
    try:
        rid = validate_id(rid, "recipient_id")
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise CorruptEvidence(f"{kind} provenance has an invalid recipient") from exc
    nested = value.get(kind)
    if nested is None:
        artifact_value: Any = value
    elif isinstance(nested, ArtifactRef):
        artifact_value = nested.to_dict()
    elif isinstance(nested, Mapping):
        artifact_value = nested
    else:
        raise CorruptEvidence(f"{kind} artifact must be an object")
    nested_recipient = _recipient(artifact_value)
    if nested_recipient is not None and nested_recipient != rid:
        raise CorruptEvidence(f"{kind} endpoint recipient differs from record recipient")
    artifact, content = _artifact_from(artifact_value, label=kind)
    # Content fields on the parent are still accepted when the nested artifact
    # only contains path and hash.
    if content is None:
        content = _explicit_content(value)
    commit_token = _commit_token(value, kind)
    if commit_token is None and artifact_value is not value:
        commit_token = _commit_token(artifact_value, kind)
    ref = _ref_token(value, kind)
    if ref is None and artifact_value is not value:
        ref = _ref_token(artifact_value, kind)
    generation_value = value.get("generation_id")
    generation = generation_value if isinstance(generation_value, str) and generation_value else None
    if generation is None and artifact_value is not value:
        generation_value = artifact_value.get("generation_id")
        generation = generation_value if isinstance(generation_value, str) and generation_value else None
    compiler = _identity(value, "compiler_identity")
    tool = _identity(value, "tool_identity")
    config = _identity(value, "config_identity")
    if artifact_value is not value:
        compiler = compiler or _identity(artifact_value, "compiler_identity")
        tool = tool or _identity(artifact_value, "tool_identity")
        config = config or _identity(artifact_value, "config_identity")
    score = value.get("score")
    before_score = value.get("before_score", value.get("score_before"))
    after_score = value.get("after_score", value.get("score_after"))
    measurement = value.get("measurement")
    if isinstance(measurement, Mapping):
        before_score = before_score if before_score is not None else measurement.get("before")
        after_score = after_score if after_score is not None else measurement.get("after")
        score = score if score is not None else measurement
    target = _identity(value, "target_object_hash", "target_checksum")
    verified = value.get("verified", False) is True
    source_id = _source_id(value, parent_identity)
    return _Endpoint(
        kind=kind,
        recipient_id=rid,
        artifact=artifact,
        content=content,
        commit_token=commit_token,
        ref=ref,
        generation=generation,
        compiler_identity=compiler,
        tool_identity=tool,
        config_identity=config,
        score=score,
        before_score=before_score,
        after_score=after_score,
        target_object_hash=target,
        target_checksum=target,
        verified=verified,
        source_id=source_id,
    )


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        for key in ("entries", "artifacts"):
            if key in value:
                entries = value[key]
                if isinstance(entries, (str, bytes, bytearray)):
                    raise CorruptEvidence(f"{key} must be a list")
                if not isinstance(entries, Sequence):
                    raise CorruptEvidence(f"{key} must be a list")
                return list(entries)
        return [value]
    if isinstance(value, (str, bytes, bytearray)):
        raise CorruptEvidence("evidence sequence must be a list or object")
    if isinstance(value, Sequence):
        return list(value)
    raise CorruptEvidence("evidence sequence must be a list or object")


def _deduplicate_endpoints(values: Iterable[_Endpoint]) -> list[_Endpoint]:
    """Drop byte-for-byte duplicate records while preserving conflicts.

    The endpoint identity intentionally omits measurements and inline bytes so
    that the same provenance record can be replayed from two stores.  Those
    fields are included in this secondary fingerprint; a conflicting replay
    therefore remains ambiguous instead of being silently selected.
    """
    unique: dict[tuple[str, str], _Endpoint] = {}
    for item in values:
        key = (item.endpoint_identity, hash_canonical(_plain(item)))
        unique.setdefault(key, item)
    return sorted(unique.values(), key=lambda item: (item.endpoint_identity, hash_canonical(_plain(item))))


def _nested_endpoints(
    record: Any,
    *,
    kind: str,
    parent_identity: Optional[str],
) -> list[_Endpoint]:
    if not isinstance(record, Mapping):
        raise CorruptEvidence("history record must be an object")
    rid = _recipient(record)
    if kind not in ("draft", "landing"):
        raise CorruptEvidence("unknown endpoint kind")
    selected_key = kind
    if selected_key not in record:
        # A flat record is itself an endpoint when it carries artifact fields.
        if "path" in record and "content_hash" in record:
            return [_endpoint_from(record, kind=kind, fallback_recipient=rid, parent_identity=parent_identity)]
        return []
    raw = record[selected_key]
    values = _sequence(raw)
    out: list[_Endpoint] = []
    for item in values:
        if isinstance(item, ArtifactRef):
            item = item.to_dict()
        if not isinstance(item, Mapping):
            raise CorruptEvidence(f"{kind} endpoint is not an object")
        item_recipient = _recipient(item)
        if rid is not None and item_recipient is not None and item_recipient != rid:
            raise CorruptEvidence(f"{kind} endpoint recipient differs from record recipient")
        merged = dict(record)
        merged.update(item)
        out.append(
            _endpoint_from(
                merged,
                kind=kind,
                fallback_recipient=rid,
                parent_identity=parent_identity,
            )
        )
    return out


@dataclass(frozen=True)
class QueueProvenance:
    """The exact selectors tying one queue record to its history endpoints."""

    recipient_id: str
    draft_hash: Optional[str] = None
    draft_generation: Optional[str] = None
    draft_provenance_id: Optional[str] = None
    landing_commit: Optional[str] = None
    landing_id: Optional[str] = None
    landed_hash: Optional[str] = None
    compiler_identity: Optional[str] = None
    tool_identity: Optional[str] = None
    config_identity: Optional[str] = None
    evidence_id: Optional[str] = None
    before_score: Any = None
    after_score: Any = None

    def __post_init__(self) -> None:
        if not isinstance(self.recipient_id, str) or not self.recipient_id:
            raise MinerError("queue provenance recipient is required")
        try:
            validate_id(self.recipient_id, "recipient_id")
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise MinerError("queue provenance recipient is invalid") from exc
        for label, value in (
            ("draft_hash", self.draft_hash),
            ("draft_generation", self.draft_generation),
            ("draft_provenance_id", self.draft_provenance_id),
            ("landing_commit", self.landing_commit),
            ("landing_id", self.landing_id),
            ("landed_hash", self.landed_hash),
            ("compiler_identity", self.compiler_identity),
            ("tool_identity", self.tool_identity),
            ("config_identity", self.config_identity),
            ("evidence_id", self.evidence_id),
        ):
            if value is not None and not isinstance(value, str):
                raise MinerError(f"queue provenance {label} must be a string")
        for label, value in (
            ("draft_hash", self.draft_hash),
            ("landed_hash", self.landed_hash),
            ("compiler_identity", self.compiler_identity),
            ("tool_identity", self.tool_identity),
            ("config_identity", self.config_identity),
        ):
            if value is not None and _valid_hash(value) is None:
                raise MinerError(f"queue provenance {label} must be a sha256 identity")
        for label in ("before_score", "after_score"):
            value = getattr(self, label)
            if value is not None:
                try:
                    object.__setattr__(self, label, _freeze_json(value))
                except (MinerError, TypeError, ValueError) as exc:
                    raise MinerError(f"queue provenance {label} is not JSON evidence") from exc

    @property
    def identity(self) -> str:
        explicit = _valid_hash(self.evidence_id)
        if explicit:
            return explicit
        return hash_canonical(
            {
                "kind": "queue-provenance-v1",
                "recipient_id": self.recipient_id,
                "draft_hash": self.draft_hash,
                "draft_generation": self.draft_generation,
                "draft_provenance_id": self.draft_provenance_id,
                "landing_commit": self.landing_commit,
                "landing_id": self.landing_id,
                "landed_hash": self.landed_hash,
                "compiler_identity": self.compiler_identity,
                "tool_identity": self.tool_identity,
                "config_identity": self.config_identity,
                "before_score": self.before_score,
                "after_score": self.after_score,
            }
        )

    @classmethod
    def from_value(cls, value: Any) -> "QueueProvenance":
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise CorruptEvidence("queue provenance must be an object")
        rid = _recipient(value)
        if rid is None:
            raise CorruptEvidence("queue provenance has no recipient")
        return cls(
            recipient_id=rid,
            draft_hash=value.get("draft_hash"),
            draft_generation=value.get("draft_generation"),
            draft_provenance_id=value.get("draft_provenance_id"),
            landing_commit=value.get("landing_commit"),
            landing_id=value.get("landing_id"),
            landed_hash=value.get("landed_hash"),
            compiler_identity=value.get("compiler_identity"),
            tool_identity=value.get("tool_identity"),
            config_identity=value.get("config_identity"),
            evidence_id=value.get("evidence_id"),
            before_score=value.get("before_score"),
            after_score=value.get("after_score"),
        )


@dataclass(frozen=True)
class MiningResult:
    """Deterministic result of one read-only miner run."""

    observations: tuple[DraftLandedObservation, ...]
    idioms: tuple[CompilerIdiomObservation, ...]
    refusals: tuple[MinerRefusal, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "observations": [item.to_dict() for item in self.observations],
            "idioms": [item.to_dict() for item in self.idioms],
            "refusals": [item.to_dict() for item in self.refusals],
        }

    def to_json(self) -> str:
        return json.dumps(
            _plain(self.to_dict()), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )


@dataclass(frozen=True)
class _ResolvedEndpoint:
    endpoint: _Endpoint
    content: bytes
    commit_id: Optional[str]


class DraftLandedMiner:
    """Mine only transitions with exact, independently verified endpoints."""

    def __init__(
        self,
        resolver: Optional[VerifiedCommitProvider] = None,
        *,
        compiler_identity: Optional[str] = None,
        tool_identity: Optional[str] = None,
        config_identity: Optional[str] = None,
        evaluator: Optional[Any] = None,
    ) -> None:
        self.resolver = resolver
        self.compiler_identity = compiler_identity
        self.tool_identity = tool_identity
        self.config_identity = config_identity
        self.evaluator = evaluator
        for label, value in (
            ("compiler_identity", compiler_identity),
            ("tool_identity", tool_identity),
            ("config_identity", config_identity),
        ):
            if value is not None and not _valid_hash(value):
                raise MinerError(f"{label} must be a sha256 identity")

    def _refuse(
        self,
        refusals: list[MinerRefusal],
        recipient_id: Optional[str],
        code: str,
        reason: str,
        *,
        inputs: Iterable[str] = (),
        evidence: Iterable[str] = (),
    ) -> None:
        refusals.append(
            MinerRefusal(
                recipient_id=recipient_id or _GLOBAL_RECIPIENT,
                code=code,
                reason=reason,
                input_identities=tuple(inputs),
                evidence=tuple(evidence),
            )
        )

    def _resolve_endpoint(
        self,
        endpoint: _Endpoint,
        *,
        require_commit: bool,
    ) -> _ResolvedEndpoint:
        content = endpoint.content
        commit_token = endpoint.commit_token or endpoint.ref
        commit_id: Optional[str] = None
        if commit_token is not None:
            if self.resolver is None:
                raise ProviderError("a verified commit provider is required")
            try:
                commit = _provider_resolve(self.resolver, commit_token)
                commit_id = commit.commit_id
                blob = _provider_blob(self.resolver, commit, endpoint.artifact.path)
            except CompilerIdiomError as exc:
                raise ProviderError(f"{endpoint.kind} invalid commit identity: {exc}") from exc
            except ProviderError as exc:
                raise ProviderError(f"{endpoint.kind} provider failure: {exc}") from exc
            if content is not None and blob != content:
                raise CorruptEvidence(
                    f"{endpoint.kind} inline bytes differ from commit {commit_id}"
                )
            content = blob
        elif require_commit:
            raise ProviderError(f"{endpoint.kind} has no immutable landing commit/ref")
        if content is None:
            raise ProviderError(f"{endpoint.kind} has no resolvable bytes")
        actual = source_hash(content)
        if actual != endpoint.artifact.content_hash:
            raise CorruptEvidence(
                f"{endpoint.kind} bytes hash {actual} differs from declared {endpoint.artifact.content_hash}"
            )
        if endpoint.artifact.byte_size != len(content):
            raise CorruptEvidence(f"{endpoint.kind} byte size differs from bytes")
        return _ResolvedEndpoint(endpoint, content, commit_id)

    def _check_identities(
        self,
        recipient_id: str,
        draft: _Endpoint,
        landed: _Endpoint,
        queue: QueueProvenance,
        refusals: list[MinerRefusal],
    ) -> bool:
        values: list[tuple[str, Optional[str]]] = [
            ("compiler_identity", draft.compiler_identity),
            ("compiler_identity", landed.compiler_identity),
            ("compiler_identity", queue.compiler_identity),
            ("tool_identity", draft.tool_identity),
            ("tool_identity", landed.tool_identity),
            ("tool_identity", queue.tool_identity),
            ("config_identity", draft.config_identity),
            ("config_identity", landed.config_identity),
            ("config_identity", queue.config_identity),
        ]
        expected = {
            "compiler_identity": self.compiler_identity,
            "tool_identity": self.tool_identity,
            "config_identity": self.config_identity,
        }
        ok = True
        for label in ("compiler_identity", "tool_identity", "config_identity"):
            observed = [value for name, value in values if name == label and value is not None]
            configured = expected[label]
            invalid = [value for value in observed if _valid_hash(value) is None]
            if invalid:
                self._refuse(
                    refusals,
                    recipient_id,
                    RefusalCode.IDENTITY_MISMATCH,
                    f"{label} is not a content identity",
                    inputs=(draft.endpoint_identity, landed.endpoint_identity, queue.identity),
                )
                ok = False
                continue
            if configured is not None:
                # A configured identity binds both endpoints.  A lone identity
                # on one side is insufficient to prove that the other source
                # was produced by the same toolchain/configuration.
                endpoint_observed = [
                    value
                    for value in (
                        getattr(draft, label),
                        getattr(landed, label),
                    )
                    if value is not None
                ]
                if (
                    any(item != configured for item in observed)
                    or len(endpoint_observed) != 2
                    or any(item != configured for item in endpoint_observed)
                ):
                    self._refuse(
                        refusals,
                        recipient_id,
                        RefusalCode.IDENTITY_MISMATCH if observed else RefusalCode.MISSING_IDENTITY,
                        f"{label} does not match the miner identity",
                        inputs=(draft.endpoint_identity, landed.endpoint_identity, queue.identity),
                    )
                    ok = False
            elif observed and len(set(observed)) != 1:
                self._refuse(
                    refusals,
                    recipient_id,
                    RefusalCode.IDENTITY_MISMATCH,
                    f"{label} differs between endpoints",
                    inputs=(draft.endpoint_identity, landed.endpoint_identity, queue.identity),
                )
                ok = False
        if self.compiler_identity is None and not any(
            value is not None for name, value in values if name == "compiler_identity"
        ):
            self._refuse(
                refusals,
                recipient_id,
                RefusalCode.MISSING_IDENTITY,
                "compiler identity is absent from all provenance inputs",
                inputs=(draft.endpoint_identity, landed.endpoint_identity, queue.identity),
            )
            ok = False
        return ok

    @staticmethod
    def _select_draft(
        drafts: Sequence[_Endpoint], queue: QueueProvenance
    ) -> Optional[_Endpoint]:
        selected = list(drafts)
        if queue.draft_hash:
            selected = [item for item in selected if item.artifact.content_hash == queue.draft_hash]
        if queue.draft_generation:
            selected = [item for item in selected if item.generation == queue.draft_generation]
        if queue.draft_provenance_id:
            selected = [item for item in selected if item.source_id == queue.draft_provenance_id]
        if len(selected) != 1:
            return None
        return selected[0]

    @staticmethod
    def _select_landing(
        landings: Sequence[_Endpoint], queue: QueueProvenance
    ) -> Optional[_Endpoint]:
        selected = list(landings)
        if queue.landing_commit:
            selected = [
                item for item in selected
                if item.commit_token == queue.landing_commit
                or item.ref == queue.landing_commit
            ]
        if queue.landing_id:
            selected = [item for item in selected if item.source_id == queue.landing_id]
        if queue.landed_hash:
            selected = [item for item in selected if item.artifact.content_hash == queue.landed_hash]
        if len(selected) != 1:
            return None
        return selected[0]

    @staticmethod
    def _pair_measurement(
        draft: _Endpoint,
        landed: _Endpoint,
        queue: QueueProvenance,
        draft_source: str,
        landed_source: str,
        evaluator: Any,
    ) -> Optional[Any]:
        before = landed.before_score if landed.before_score is not None else draft.score
        if before is None:
            before = queue.before_score
        after = landed.after_score if landed.after_score is not None else landed.score
        if after is None:
            after = queue.after_score
        target_object = landed.target_object_hash or landed.target_checksum
        if evaluator is not None:
            try:
                result = evaluator(draft_source, landed_source)
            except TypeError:
                # A callback TypeError is not evidence that another signature
                # should be attempted.  Preserve the original failure and the
                # one-call guarantee for deterministic replay.
                raise
            except Exception as exc:  # noqa: BLE001 - evaluator boundary
                raise MeasurementError(f"score evaluator failed: {exc}") from exc
            if isinstance(result, Mapping):
                before = result.get("before", result.get("before_score", before))
                after = result.get("after", result.get("after_score", after))
                target_object = result.get(
                    "target_object_hash", result.get("target_checksum", target_object)
                )
                evaluator_identity = result.get("evaluator_identity", result.get("compiler_identity"))
            else:
                evaluator_identity = None
        else:
            evaluator_identity = None
        if before is None or after is None:
            return None
        evidence = [
            "draft:" + draft.artifact.content_hash,
            "landed:" + landed.artifact.content_hash,
        ]
        if landed.verified:
            evidence.append("landing-record:verified")
        if evaluator_identity is not None:
            if not isinstance(evaluator_identity, str):
                raise MeasurementError("evaluator identity is not a string")
            evidence.append("evaluator:" + evaluator_identity)
        return measure_improvement(
            before,
            after,
            target_object_hash=target_object,
            evaluator_identity=evaluator_identity,
            evidence=evidence,
        )

    def mine(
        self,
        candidate_history: Any,
        queue_provenance: Any = None,
        landing_commits: Any = None,
    ) -> MiningResult:
        """Mine exact pairs from explicit history, queue and landing inputs."""
        refusals: list[MinerRefusal] = []
        drafts: list[_Endpoint] = []
        landings: list[_Endpoint] = []
        queues: list[QueueProvenance] = []

        records = _sequence(candidate_history)
        for raw in records:
            record_identity = _record_identity(raw, label="candidate-history")
            try:
                drafts.extend(
                    _nested_endpoints(raw, kind="draft", parent_identity=record_identity)
                )
                # A history record may carry a verified landing receipt too.
                landings.extend(
                    _nested_endpoints(raw, kind="landing", parent_identity=record_identity)
                )
            except (MinerError, SearchValidationError, TypeError, ValueError) as exc:
                code = (
                    RefusalCode.CORRUPT_ARTIFACT
                    if isinstance(exc, CorruptEvidence)
                    else RefusalCode.INVALID_PROVENANCE
                )
                self._refuse(
                    refusals,
                    _recipient(raw),
                    code,
                    f"invalid candidate history: {exc}",
                    inputs=(record_identity,) if record_identity else (),
                )

        for raw in _sequence(landing_commits):
            record_identity = _record_identity(raw, label="landing-commit")
            try:
                parsed = _nested_endpoints(raw, kind="landing", parent_identity=record_identity)
                if not parsed:
                    raise CorruptEvidence("landing record has no landed artifact")
                landings.extend(parsed)
            except (MinerError, SearchValidationError, TypeError, ValueError) as exc:
                code = (
                    RefusalCode.CORRUPT_ARTIFACT
                    if isinstance(exc, CorruptEvidence)
                    else RefusalCode.INVALID_PROVENANCE
                )
                self._refuse(
                    refusals,
                    _recipient(raw),
                    code,
                    f"invalid landing evidence: {exc}",
                    inputs=(record_identity,) if record_identity else (),
                )

        for raw in _sequence(queue_provenance):
            try:
                queues.append(QueueProvenance.from_value(raw))
            except (MinerError, SearchValidationError, TypeError, ValueError) as exc:
                self._refuse(
                    refusals,
                    _recipient(raw),
                    RefusalCode.INVALID_PROVENANCE,
                    f"invalid queue provenance: {exc}",
                )

        # A record-level queue link is evidence, not an ordering hint.  Every
        # candidate/landing pair must pass the selectors below independently.
        draft_by_recipient: dict[str, list[_Endpoint]] = {}
        landing_by_recipient: dict[str, list[_Endpoint]] = {}
        queue_by_recipient: dict[str, list[QueueProvenance]] = {}
        for item in drafts:
            draft_by_recipient.setdefault(item.recipient_id, []).append(item)
        for item in landings:
            landing_by_recipient.setdefault(item.recipient_id, []).append(item)
        for item in queues:
            queue_by_recipient.setdefault(item.recipient_id, []).append(item)
        draft_by_recipient = {
            rid: _deduplicate_endpoints(items)
            for rid, items in draft_by_recipient.items()
        }
        landing_by_recipient = {
            rid: _deduplicate_endpoints(items)
            for rid, items in landing_by_recipient.items()
        }

        recipient_ids = sorted(
            set(draft_by_recipient) | set(landing_by_recipient) | set(queue_by_recipient)
        )
        observations_by_transition: dict[str, list[DraftLandedObservation]] = {}

        for rid in recipient_ids:
            recipient_drafts = sorted(
                draft_by_recipient.get(rid, []), key=lambda item: item.endpoint_identity
            )
            recipient_landings = sorted(
                landing_by_recipient.get(rid, []), key=lambda item: item.endpoint_identity
            )
            recipient_queues = sorted(
                queue_by_recipient.get(rid, []), key=lambda item: item.identity
            )
            if not recipient_drafts:
                self._refuse(refusals, rid, RefusalCode.MISSING_DRAFT, "no draft artifact has been recorded")
                continue
            if not recipient_queues:
                self._refuse(
                    refusals,
                    rid,
                    RefusalCode.MISSING_QUEUE_PROVENANCE,
                    "queue provenance is required to select a draft generation and landing",
                    inputs=tuple(item.endpoint_identity for item in recipient_drafts),
                )
                continue
            if not recipient_landings:
                self._refuse(
                    refusals,
                    rid,
                    RefusalCode.MISSING_LANDING_COMMIT,
                    "no landing artifact/commit was recorded",
                    inputs=tuple(item.endpoint_identity for item in recipient_drafts),
                )
                continue

            for queue in recipient_queues:
                draft = self._select_draft(recipient_drafts, queue)
                if draft is None:
                    candidates = [
                        item for item in recipient_drafts
                        if (not queue.draft_hash or item.artifact.content_hash == queue.draft_hash)
                        and (not queue.draft_generation or item.generation == queue.draft_generation)
                        and (not queue.draft_provenance_id or item.source_id == queue.draft_provenance_id)
                    ]
                    self._refuse(
                        refusals,
                        rid,
                        RefusalCode.AMBIGUOUS_DRAFT if len(candidates) > 1 else RefusalCode.MISSING_DRAFT,
                        "queue provenance does not select exactly one draft generation",
                        inputs=tuple(item.endpoint_identity for item in recipient_drafts),
                        evidence=("queue:" + queue.identity,),
                    )
                    continue
                landing = self._select_landing(recipient_landings, queue)
                if landing is None:
                    candidates = [
                        item for item in recipient_landings
                        if (not queue.landing_commit or item.commit_token == queue.landing_commit or item.ref == queue.landing_commit)
                        and (not queue.landing_id or item.source_id == queue.landing_id)
                        and (not queue.landed_hash or item.artifact.content_hash == queue.landed_hash)
                    ]
                    code = RefusalCode.AMBIGUOUS_LANDING if len(candidates) > 1 else RefusalCode.MISSING_LANDING_COMMIT
                    reason = (
                        "queue provenance does not select exactly one landing"
                        if candidates else "queue provenance selects no landing"
                    )
                    self._refuse(
                        refusals,
                        rid,
                        code,
                        reason,
                        inputs=(draft.endpoint_identity, queue.identity),
                    )
                    continue
                if draft.recipient_id != landing.recipient_id or draft.recipient_id != rid:
                    self._refuse(
                        refusals,
                        rid,
                        RefusalCode.MISMATCHED_RECIPIENT,
                        "draft, landing and queue recipients differ",
                        inputs=(draft.endpoint_identity, landing.endpoint_identity, queue.identity),
                    )
                    continue
                if not landing.commit_token and not landing.ref:
                    self._refuse(
                        refusals,
                        rid,
                        RefusalCode.MISSING_LANDING_COMMIT,
                        "landing has no immutable commit or resolvable ref",
                        inputs=(draft.endpoint_identity, landing.endpoint_identity),
                    )
                    continue
                if not self._check_identities(rid, draft, landing, queue, refusals):
                    continue

                try:
                    resolved_draft = self._resolve_endpoint(draft, require_commit=False)
                    resolved_landing = self._resolve_endpoint(landing, require_commit=True)
                    if resolved_landing.commit_id is None:
                        raise ProviderError("landing commit was not resolved")
                    draft_text = resolved_draft.content.decode("utf-8")
                    landed_text = resolved_landing.content.decode("utf-8")
                    patch = make_grouped_patch(draft_text, landed_text)
                except (MinerError, UnicodeDecodeError, SearchValidationError, TypeError, ValueError) as exc:
                    code = RefusalCode.CORRUPT_ARTIFACT if isinstance(exc, CorruptEvidence) else RefusalCode.PROVIDER_FAILURE
                    if isinstance(exc, ProviderError) and "invalid commit identity" in str(exc):
                        code = RefusalCode.INVALID_COMMIT
                    elif isinstance(exc, ProviderError) and "landing" in str(exc):
                        code = RefusalCode.UNVERIFIED_COMMIT
                    self._refuse(
                        refusals,
                        rid,
                        code,
                        f"endpoint verification failed: {exc}",
                        inputs=(draft.endpoint_identity, landing.endpoint_identity, queue.identity),
                    )
                    continue

                measurement = None
                try:
                    measurement = self._pair_measurement(
                        draft,
                        landing,
                        queue,
                        draft_text,
                        landed_text,
                        self.evaluator,
                    )
                except (MeasurementError, TypeError, ValueError) as exc:
                    self._refuse(
                        refusals,
                        rid,
                        RefusalCode.UNMEASURED,
                        f"score/checksum measurement failed: {exc}",
                        inputs=(draft.endpoint_identity, landing.endpoint_identity, queue.identity),
                    )
                evidence = {
                    "draft-artifact:" + draft.artifact.content_hash,
                    "landed-artifact:" + landing.artifact.content_hash,
                    "landing-commit:" + (resolved_landing.commit_id or ""),
                    "queue:" + queue.identity,
                }
                if resolved_draft.commit_id:
                    evidence.add("draft-commit:" + resolved_draft.commit_id)
                elif draft.source_id:
                    evidence.add("draft-provenance:" + draft.source_id)
                if draft.ref:
                    evidence.add("draft-ref:" + draft.ref)
                if landing.ref:
                    evidence.add("landing-ref:" + landing.ref)
                if landing.source_id:
                    evidence.add("landing-provenance:" + landing.source_id)
                if measurement is not None:
                    evidence.update(measurement.evidence)
                    expected_measurement_identity = (
                        self.compiler_identity
                        or draft.compiler_identity
                        or landing.compiler_identity
                        or queue.compiler_identity
                    )
                    if (
                        measurement.evaluator_identity is not None
                        and expected_measurement_identity is not None
                        and measurement.evaluator_identity != expected_measurement_identity
                    ):
                        self._refuse(
                            refusals,
                            rid,
                            RefusalCode.IDENTITY_MISMATCH,
                            "measurement evaluator identity differs from compiler identity",
                            inputs=(draft.endpoint_identity, landing.endpoint_identity, queue.identity),
                        )
                        continue
                    if (
                        measurement.evaluator_identity is not None
                        and _valid_hash(measurement.evaluator_identity) is None
                    ):
                        self._refuse(
                            refusals,
                            rid,
                            RefusalCode.IDENTITY_MISMATCH,
                            "measurement evaluator identity is not a content identity",
                            inputs=(draft.endpoint_identity, landing.endpoint_identity, queue.identity),
                        )
                        continue
                pair = DraftLandedObservation(
                    recipient_id=rid,
                    draft=draft.artifact,
                    landed=landing.artifact,
                    landing_commit=resolved_landing.commit_id,
                    compiler_identity=(
                        self.compiler_identity
                        or draft.compiler_identity
                        or landing.compiler_identity
                        or queue.compiler_identity
                    ),
                    grouped_patches=(patch,),
                    evidence=tuple(sorted(evidence)),
                    draft_commit=resolved_draft.commit_id,
                    draft_ref=draft.ref,
                    landing_ref=landing.ref,
                    tool_identity=self.tool_identity or draft.tool_identity or landing.tool_identity or queue.tool_identity,
                    config_identity=self.config_identity or draft.config_identity or landing.config_identity or queue.config_identity,
                    measurement=measurement.to_dict() if measurement is not None else {},
                )
                transition_key = hash_canonical(
                    {
                        "recipient_id": rid,
                        "draft": pair.draft,
                        "landed": pair.landed,
                        "landing_commit": pair.landing_commit,
                        "draft_commit": pair.draft_commit,
                        "compiler_identity": pair.compiler_identity,
                        "tool_identity": pair.tool_identity,
                        "config_identity": pair.config_identity,
                        "grouped_patches": pair.grouped_patches,
                    }
                )
                observations_by_transition.setdefault(transition_key, []).append(pair)
                if measurement is None:
                    self._refuse(
                        refusals,
                        rid,
                        RefusalCode.UNMEASURED,
                        "pair is provenance-valid but has no measured score/checksum improvement",
                        inputs=(pair.pair_hash,),
                    )
                elif draft_text == landed_text:
                    self._refuse(
                        refusals,
                        rid,
                        RefusalCode.NO_SOURCE_CHANGE,
                        "measurement improved but source bytes did not change",
                        inputs=(pair.pair_hash,),
                    )
        finalized: list[DraftLandedObservation] = []
        for transition_key, candidates in sorted(observations_by_transition.items()):
            ordered = sorted(candidates, key=lambda item: item.pair_hash)
            identity_variants = {
                (
                    item.draft_ref,
                    item.landing_ref,
                    hash_canonical(item.measurement),
                )
                for item in ordered
            }
            if len(identity_variants) != 1:
                self._refuse(
                    refusals,
                    ordered[0].recipient_id,
                    RefusalCode.DUPLICATE_CONFLICT,
                    "duplicate transition records disagree on ref or measurement identity",
                    inputs=tuple(sorted(item.pair_hash for item in ordered)),
                )
                continue
            representative = ordered[0]
            merged_evidence = tuple(
                sorted(
                    {
                        evidence
                        for item in ordered
                        for evidence in item.evidence
                    }
                )
            )
            finalized.append(
                representative
                if merged_evidence == representative.evidence
                else dataclasses.replace(representative, evidence=merged_evidence)
            )

        observations = tuple(sorted(finalized, key=lambda item: item.pair_hash))
        idiom_candidates: list[CompilerIdiomObservation] = []
        for pair in observations:
            if not pair.measurement.get("improved", False):
                continue
            if pair.draft.content_hash == pair.landed.content_hash:
                continue
            try:
                idiom_candidates.append(make_idiom_observation(pair))
            except MeasurementError as exc:
                self._refuse(
                    refusals,
                    pair.recipient_id,
                    RefusalCode.UNMEASURED,
                    str(exc),
                    inputs=(pair.pair_hash,),
                )
        idioms = deduplicate_idioms(idiom_candidates)
        # Refusals are evidence too.  Keep one deterministic copy of a repeated
        # refusal generated by duplicate queue records.
        refusal_map = {
            hash_canonical(item.to_dict()): item
            for item in refusals
        }
        final_refusals = tuple(
            sorted(refusal_map.values(), key=lambda item: hash_canonical(item.to_dict()))
        )
        return MiningResult(observations, idioms, final_refusals)

    def replay(
        self,
        candidate_history: Any,
        queue_provenance: Any = None,
        landing_commits: Any = None,
    ) -> MiningResult:
        """Replay the pure miner with the same inputs and identities."""
        return self.mine(
            candidate_history,
            queue_provenance,
            landing_commits,
        )

def mine_draft_landed(
    candidate_history: Any,
    queue_provenance: Any = None,
    landing_commits: Any = None,
    *,
    resolver: Optional[VerifiedCommitProvider] = None,
    compiler_identity: Optional[str] = None,
    tool_identity: Optional[str] = None,
    config_identity: Optional[str] = None,
    evaluator: Optional[Any] = None,
) -> MiningResult:
    """Functional entry point for one deterministic mining pass."""
    miner = DraftLandedMiner(
        resolver=resolver,
        compiler_identity=compiler_identity,
        tool_identity=tool_identity,
        config_identity=config_identity,
        evaluator=evaluator,
    )
    return miner.mine(candidate_history, queue_provenance, landing_commits)

__all__ = [
    "MODULE_VERSION",
    "MinerError",
    "ProviderError",
    "CorruptEvidence",
    "AmbiguousEvidence",
    "RefusalCode",
    "MinerRefusal",
    "VerifiedCommit",
    "VerifiedCommitProvider",
    "MappingCommitResolver",
    "QueueProvenance",
    "MiningResult",
    "DraftLandedMiner",
    "mine_draft_landed",
]
