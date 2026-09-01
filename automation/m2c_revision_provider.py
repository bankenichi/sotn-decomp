"""Immutable m2c revision and invocation boundary.

The provider never checks out a revision, reads the live queue, edits source,
or guesses which m2c tree should run.  Factory and connector code must supply
an explicitly measured revision identity.  Every invocation consumes archived
target bytes and returns an archived C source artifact.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

try:
    from .search_archive import ArchiveError, ContentAddressedArchive
    from .search_types import (
        ArtifactRef,
        SearchValidationError,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
    )
except ImportError:  # direct invocation from the automation directory
    from search_archive import ArchiveError, ContentAddressedArchive  # type: ignore
    from search_types import (  # type: ignore
        ArtifactRef,
        SearchValidationError,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
    )


CURRENT_M2C_REVISION = "94098d4de68c2fcc13fb8cf1096a1520eb171abe"
M2C_PROVIDER_PROTOCOL = "sotn-m2c-revision-provider-v1"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class M2CProviderError(ValueError):
    """Provider identity, revision, artifact, or invocation refusal."""


def _hash(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except SearchValidationError as exc:
        raise M2CProviderError(str(exc)) from exc


def _artifact(value: Any, label: str) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    try:
        return ArtifactRef.from_dict(value)
    except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise M2CProviderError(label + " is not a valid artifact reference") from exc


def _commit(value: Any, label: str) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise M2CProviderError(label + " must be a full lowercase 40-character revision")
    return value


@dataclass(frozen=True)
class M2CRevisionIdentity:
    revision_id: str
    tree_identity: str
    provider_identity: str
    executable_identity: str
    config_identity: str
    clean: bool
    detached: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "revision_id", _commit(self.revision_id, "m2c revision_id"))
        for name in (
            "tree_identity",
            "provider_identity",
            "executable_identity",
            "config_identity",
        ):
            object.__setattr__(self, name, _hash(getattr(self, name), "m2c " + name))
        if not isinstance(self.clean, bool) or not isinstance(self.detached, bool):
            raise M2CProviderError("m2c clean and detached flags must be boolean")
        if not self.clean or not self.detached:
            raise M2CProviderError("m2c revision must be clean and detached")

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "tree_identity": self.tree_identity,
            "provider_identity": self.provider_identity,
            "executable_identity": self.executable_identity,
            "config_identity": self.config_identity,
            "clean": self.clean,
            "detached": self.detached,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CRevisionIdentity":
        fields = {
            "revision_id",
            "tree_identity",
            "provider_identity",
            "executable_identity",
            "config_identity",
            "clean",
            "detached",
        }
        if not isinstance(value, Mapping) or set(value) != fields:
            raise M2CProviderError("m2c revision fields are invalid")
        return cls(**dict(value))


@dataclass(frozen=True)
class M2CInvocation:
    invocation_id: str
    revision_id: str
    tree_identity: str
    provider_identity: str
    recipient_id: str
    assembly_artifact: ArtifactRef
    context_artifacts: tuple[ArtifactRef, ...]
    switches: tuple[str, ...]
    target_identity: str
    compiler_identity: str
    tool_identity: str
    evaluator_identity: str
    scorer_taxonomy_identity: str
    config_identity: str
    integration_gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    archive_identity: str
    ordinal: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "revision_id", _commit(self.revision_id, "m2c revision_id"))
        try:
            validate_id(self.recipient_id, "m2c recipient_id")
        except SearchValidationError as exc:
            raise M2CProviderError(str(exc)) from exc
        for name in (
            "invocation_id",
            "tree_identity",
            "provider_identity",
            "target_identity",
            "compiler_identity",
            "tool_identity",
            "evaluator_identity",
            "scorer_taxonomy_identity",
            "config_identity",
            "integration_gate_id",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
            "archive_identity",
        ):
            object.__setattr__(self, name, _hash(getattr(self, name), "m2c " + name))
        assembly = _artifact(self.assembly_artifact, "m2c assembly_artifact")
        contexts = tuple(_artifact(item, "m2c context_artifact") for item in self.context_artifacts)
        if len({item.content_hash for item in contexts}) != len(contexts):
            raise M2CProviderError("m2c context artifacts must not repeat")
        switches = tuple(self.switches)
        if any(not isinstance(item, str) or not item for item in switches):
            raise M2CProviderError("m2c switches must be nonempty strings")
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal < 0:
            raise M2CProviderError("m2c ordinal must be a nonnegative integer")
        object.__setattr__(self, "assembly_artifact", assembly)
        object.__setattr__(self, "context_artifacts", contexts)
        object.__setattr__(self, "switches", switches)
        if self.invocation_id != hash_canonical(self.identity_payload()):
            raise M2CProviderError("m2c invocation_id differs from its complete payload")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": M2C_PROVIDER_PROTOCOL,
            "revision_id": self.revision_id,
            "tree_identity": self.tree_identity,
            "provider_identity": self.provider_identity,
            "recipient_id": self.recipient_id,
            "assembly_artifact": self.assembly_artifact.to_dict(),
            "context_artifacts": [item.to_dict() for item in self.context_artifacts],
            "switches": list(self.switches),
            "target_identity": self.target_identity,
            "compiler_identity": self.compiler_identity,
            "tool_identity": self.tool_identity,
            "evaluator_identity": self.evaluator_identity,
            "scorer_taxonomy_identity": self.scorer_taxonomy_identity,
            "config_identity": self.config_identity,
            "integration_gate_id": self.integration_gate_id,
            "integration_gate_artifact_id": self.integration_gate_artifact_id,
            "subset_identity": self.subset_identity,
            "queue_evidence_identity": self.queue_evidence_identity,
            "archive_identity": self.archive_identity,
            "ordinal": self.ordinal,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"invocation_id": self.invocation_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CInvocation":
        fields = {
            "invocation_id",
            "protocol",
            "revision_id",
            "tree_identity",
            "provider_identity",
            "recipient_id",
            "assembly_artifact",
            "context_artifacts",
            "switches",
            "target_identity",
            "compiler_identity",
            "tool_identity",
            "evaluator_identity",
            "scorer_taxonomy_identity",
            "config_identity",
            "integration_gate_id",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
            "archive_identity",
            "ordinal",
        }
        if not isinstance(value, Mapping) or set(value) != fields:
            raise M2CProviderError("m2c invocation fields are invalid")
        if value.get("protocol") != M2C_PROVIDER_PROTOCOL:
            raise M2CProviderError("m2c invocation protocol is invalid")
        payload = dict(value)
        payload.pop("protocol")
        return cls(**payload)


@dataclass(frozen=True)
class M2CDraftPayload:
    invocation_id: str
    revision_id: str
    source_artifact: ArtifactRef

    def __post_init__(self) -> None:
        object.__setattr__(self, "invocation_id", _hash(self.invocation_id, "m2c invocation_id"))
        object.__setattr__(self, "revision_id", _commit(self.revision_id, "m2c revision_id"))
        object.__setattr__(self, "source_artifact", _artifact(self.source_artifact, "m2c source_artifact"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "revision_id": self.revision_id,
            "source_artifact": self.source_artifact.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CDraftPayload":
        fields = {"invocation_id", "revision_id", "source_artifact"}
        if not isinstance(value, Mapping) or set(value) != fields:
            raise M2CProviderError("m2c draft payload fields are invalid")
        return cls(**dict(value))


class M2CRevisionProvider(Protocol):
    def resolve_revision(self, revision_id: str) -> M2CRevisionIdentity: ...

    def generate_draft(
        self,
        invocation: M2CInvocation,
        *,
        assembly: bytes,
        contexts: tuple[bytes, ...],
    ) -> M2CDraftPayload: ...


DraftGenerator = Callable[..., str | bytes]


class PinnedM2CRevisionProvider:
    """Run one pre-resolved immutable revision through one exact call shape."""

    def __init__(
        self,
        revisions: Sequence[M2CRevisionIdentity],
        *,
        generator: DraftGenerator,
        archive: ContentAddressedArchive,
        archive_identity: str,
    ) -> None:
        ordered = tuple(sorted(revisions, key=lambda item: item.revision_id))
        if not ordered or any(not isinstance(item, M2CRevisionIdentity) for item in ordered):
            raise M2CProviderError("m2c revisions must be typed immutable identities")
        if len({item.revision_id for item in ordered}) != len(ordered):
            raise M2CProviderError("m2c revisions must be unique")
        if not callable(generator):
            raise M2CProviderError("m2c draft generator must be callable")
        if not isinstance(archive, ContentAddressedArchive):
            raise M2CProviderError("m2c provider requires a content-addressed archive")
        self._revisions = MappingProxyType({item.revision_id: item for item in ordered})
        self._generator = generator
        self._archive = archive
        self._archive_identity = _hash(archive_identity, "m2c archive_identity")
        try:
            inspect.signature(generator).bind(
                object(), assembly=b"assembly", contexts=(b"context",)
            )
        except (TypeError, ValueError) as exc:
            raise M2CProviderError(
                "m2c generator must accept (invocation, *, assembly, contexts)"
            ) from exc

    def resolve_revision(self, revision_id: str) -> M2CRevisionIdentity:
        revision_id = _commit(revision_id, "m2c revision_id")
        try:
            return self._revisions[revision_id]
        except KeyError as exc:
            raise M2CProviderError("m2c revision is not explicitly available") from exc

    def _verify_input(self, reference: ArtifactRef, data: bytes, label: str) -> None:
        if not isinstance(data, bytes):
            raise M2CProviderError(label + " bytes are not typed")
        try:
            archived = self._archive.verify(reference)
        except (ArchiveError, OSError, SearchValidationError, TypeError, ValueError) as exc:
            raise M2CProviderError(label + " artifact is missing or corrupt") from exc
        if archived != data or hash_bytes(data) != reference.content_hash or len(data) != reference.byte_size:
            raise M2CProviderError(label + " bytes differ from the archived artifact")

    def generate_draft(
        self,
        invocation: M2CInvocation,
        *,
        assembly: bytes,
        contexts: tuple[bytes, ...],
    ) -> M2CDraftPayload:
        if not isinstance(invocation, M2CInvocation):
            raise M2CProviderError("m2c invocation must be typed")
        revision = self.resolve_revision(invocation.revision_id)
        if (
            invocation.tree_identity != revision.tree_identity
            or invocation.provider_identity != revision.provider_identity
            or invocation.tool_identity != revision.executable_identity
            or invocation.config_identity != revision.config_identity
            or invocation.archive_identity != self._archive_identity
        ):
            raise M2CProviderError("m2c invocation differs from its resolved revision")
        contexts = tuple(contexts)
        if len(contexts) != len(invocation.context_artifacts):
            raise M2CProviderError("m2c context bytes differ from invocation cardinality")
        self._verify_input(invocation.assembly_artifact, assembly, "m2c assembly")
        for reference, data in zip(invocation.context_artifacts, contexts):
            self._verify_input(reference, data, "m2c context")
        # The signature was checked before any invocation.  An internal
        # TypeError is deliberately surfaced after this one call, never used
        # as an arity probe and retried.
        source = self._generator(invocation, assembly=assembly, contexts=contexts)
        if isinstance(source, str):
            source_bytes = source.encode("utf-8")
        elif isinstance(source, bytes):
            source_bytes = source
        else:
            raise M2CProviderError("m2c generator returned neither text nor bytes")
        if not source_bytes:
            raise M2CProviderError("m2c generator returned an empty draft")
        reference = self._archive.put_bytes(
            source_bytes,
            category="m2c-drafts",
            suffix=".c",
            media_type="text/x-c",
        )
        if self._archive.verify(reference) != source_bytes:
            raise M2CProviderError("m2c draft artifact failed verification")
        return M2CDraftPayload(invocation.invocation_id, revision.revision_id, reference)


def make_invocation(**values: Any) -> M2CInvocation:
    """Construct an invocation after deriving its complete canonical identity."""

    payload = dict(values)
    payload.pop("invocation_id", None)
    probe = {
        "protocol": M2C_PROVIDER_PROTOCOL,
        **{
            key: (
                value.to_dict()
                if isinstance(value, ArtifactRef)
                else [item.to_dict() for item in value]
                if key == "context_artifacts"
                else list(value)
                if key == "switches"
                else value
            )
            for key, value in payload.items()
        },
    }
    payload["invocation_id"] = hash_canonical(probe)
    return M2CInvocation(**payload)


__all__ = [
    "CURRENT_M2C_REVISION",
    "M2C_PROVIDER_PROTOCOL",
    "M2CProviderError",
    "M2CRevisionIdentity",
    "M2CInvocation",
    "M2CDraftPayload",
    "M2CRevisionProvider",
    "PinnedM2CRevisionProvider",
    "make_invocation",
]
