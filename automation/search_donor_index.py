"""Immutable four-version donor index for the evidence corpus.

Task 5 of the evidence-corpus/donor-index plan. The index pins exactly one
source revision per supported version label, scans each pinned revision once
through a caller-supplied scanner, and publishes every semantic donor record
with its immutable revision provenance. Version-specific body bytes, register
evidence, relocations, and branch displacements are refused: the index stores
semantic claims that can be cited across versions, never copies of another
version's bytes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable, Tuple

try:  # package imports
    from .compiler_idioms import validate_commit_identity
    from .search_archive import ArtifactRef, ContentAddressedArchive
    from .search_lanes import (
        DonorEvidence,
        UnsafeSemanticConstant,
        reject_unsafe_semantic_constant,
    )
    from .search_supervisor import IntegrationGateError, IntegrationGateReceipt
    from .search_types import (
        SearchValidationError,
        canonical_bytes,
        hash_canonical,
        validate_hash,
    )
except ImportError:  # direct invocation from the automation directory
    from automation.compiler_idioms import validate_commit_identity  # type: ignore
    from automation.search_archive import (  # type: ignore
        ArtifactRef,
        ContentAddressedArchive,
    )
    from automation.search_lanes import (  # type: ignore
        DonorEvidence,
        UnsafeSemanticConstant,
        reject_unsafe_semantic_constant,
    )
    from automation.search_supervisor import (  # type: ignore
        IntegrationGateError,
        IntegrationGateReceipt,
    )
    from automation.search_types import (  # type: ignore
        SearchValidationError,
        canonical_bytes,
        hash_canonical,
        validate_hash,
    )


DONOR_VERSIONS = ("us", "hd", "pspeu", "saturn")
DONOR_INDEX_PROTOCOL = "sotn-search-donor-index-v1"
_DONOR_REVISION_SET_PROTOCOL = "sotn-donor-revision-set-v1"
_FORBIDDEN_METADATA_KEYS = (
    "bytes",
    "registers",
    "relocations",
    "branch_displacements",
)


class DonorIndexError(RuntimeError):
    """Base error for donor-index input and generation failures."""


class DonorIndexInputError(DonorIndexError):
    """A donor index input is incomplete, unsafe, or malformed."""


class DonorRevisionSetError(DonorIndexInputError):
    """The four-version pinned revision set is not complete and unique."""


class DonorIndexIdentityMismatch(DonorIndexInputError):
    """An indexed identity or immutable entry payload disagrees."""


def _hash_value(value: Any, label: str) -> str:
    try:
        validate_hash(value, label)
    except SearchValidationError as exc:
        raise DonorIndexIdentityMismatch(str(exc)) from exc
    return value


@dataclass(frozen=True)
class DonorRevision:
    """One exact pinned source revision for one supported version label."""

    version: str
    revision: str
    source_artifact: ArtifactRef

    def __post_init__(self) -> None:
        if self.version not in DONOR_VERSIONS:
            raise DonorRevisionSetError(
                f"donor version {self.version!r} is not one of "
                + ", ".join(DONOR_VERSIONS)
            )
        try:
            object.__setattr__(
                self, "revision", validate_commit_identity(self.revision, "revision")
            )
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, DonorIndexError):
                raise
            raise DonorRevisionSetError(
                "donor revision must be a full immutable commit identity"
            ) from exc
        if not isinstance(self.source_artifact, ArtifactRef):
            object.__setattr__(
                self,
                "source_artifact",
                ArtifactRef.from_dict(self.source_artifact),  # type: ignore[arg-type]
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorRevision":
        fields = ("version", "revision", "source_artifact")
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorIndexInputError(
                "donor revision fields do not match its protocol"
            )
        data = {key: value[key] for key in fields}
        data["source_artifact"] = ArtifactRef.from_dict(data["source_artifact"])
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "revision": self.revision,
            "source_artifact": self.source_artifact.to_dict(),
        }


def _ordered_revisions(
    revisions: Sequence[DonorRevision],
) -> Tuple[DonorRevision, ...]:
    """Canonicalize revision input and require one pin per version."""

    normalized: list[DonorRevision] = []
    for revision in revisions:
        if not isinstance(revision, DonorRevision):
            try:
                revision = DonorRevision.from_dict(revision)  # type: ignore[arg-type]
            except DonorIndexError:
                raise
            except (AttributeError, TypeError, ValueError) as exc:
                raise DonorIndexInputError(
                    "donor revisions must be typed records"
                ) from exc
        normalized.append(revision)
    ordered = tuple(
        sorted(normalized, key=lambda item: DONOR_VERSIONS.index(item.version))
    )
    if tuple(item.version for item in ordered) != DONOR_VERSIONS:
        raise DonorRevisionSetError(
            "one pinned revision per US, HD, PSPEU, and Saturn is required"
        )
    return ordered


def revision_set_identity(ordered_revisions: Sequence[DonorRevision]) -> str:
    """Return the identity of the complete ordered revision and source set."""

    return hash_canonical(
        {
            "protocol": _DONOR_REVISION_SET_PROTOCOL,
            "revisions": [item.to_dict() for item in ordered_revisions],
        }
    )


@dataclass(frozen=True)
class DonorIndexBinding:
    """The complete immutable binding behind one donor index generation."""

    integration_gate: IntegrationGateReceipt
    integration_gate_id: str
    manifest_artifact_identity: str
    subset_identity: str
    queue_evidence_identity: str
    selected_lanes: Tuple[str, ...]
    coordinator_identity: str
    connector_identity: str
    revision_set_identity: str
    indexer_identity: str
    indexer_source_identity: str
    config_identity: str
    signature_identity: str
    schema_identity: str
    generation_ordinal: int

    def __post_init__(self) -> None:
        if not isinstance(self.integration_gate, IntegrationGateReceipt):
            raise DonorIndexInputError(
                "donor index binding needs a typed integration gate receipt"
            )
        try:
            canonical_gate = IntegrationGateReceipt.from_dict(
                self.integration_gate.to_dict()
            )
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise DonorIndexInputError(
                "donor index integration gate invariants are invalid"
            ) from exc
        if canonical_gate != self.integration_gate:
            raise DonorIndexInputError(
                "donor index integration gate invariants are invalid"
            )
        if self.integration_gate_id != self.integration_gate.gate_id:
            raise DonorIndexIdentityMismatch(
                "donor index gate id differs from its integration receipt"
            )
        copied = (
            ("manifest_artifact_identity", self.manifest_artifact_identity),
            ("subset_identity", self.subset_identity),
            ("queue_evidence_identity", self.queue_evidence_identity),
            ("coordinator_identity", self.coordinator_identity),
            ("connector_identity", self.connector_identity),
        )
        for name, value in copied:
            _hash_value(value, name)
        for name, value in copied:
            if value != getattr(self.integration_gate, name):
                raise DonorIndexIdentityMismatch(
                    f"donor index {name} differs from its integration receipt"
                )
        for name in (
            "revision_set_identity",
            "indexer_identity",
            "indexer_source_identity",
            "config_identity",
            "signature_identity",
            "schema_identity",
        ):
            _hash_value(getattr(self, name), name)
        if (
            isinstance(self.generation_ordinal, bool)
            or not isinstance(self.generation_ordinal, int)
            or self.generation_ordinal < 1
        ):
            raise DonorIndexInputError(
                "donor index generation ordinal must be a positive integer"
            )
        object.__setattr__(
            self, "selected_lanes", tuple(self.integration_gate.selected_lanes)
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorIndexBinding":
        fields = (
            "integration_gate",
            "integration_gate_id",
            "manifest_artifact_identity",
            "subset_identity",
            "queue_evidence_identity",
            "selected_lanes",
            "coordinator_identity",
            "connector_identity",
            "revision_set_identity",
            "indexer_identity",
            "indexer_source_identity",
            "config_identity",
            "signature_identity",
            "schema_identity",
            "generation_ordinal",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorIndexInputError(
                "donor index binding fields do not match its protocol"
            )
        data = {key: value[key] for key in fields}
        data["integration_gate"] = IntegrationGateReceipt.from_dict(
            data["integration_gate"]
        )
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration_gate": self.integration_gate.to_dict(),
            "integration_gate_id": self.integration_gate_id,
            "manifest_artifact_identity": self.manifest_artifact_identity,
            "subset_identity": self.subset_identity,
            "queue_evidence_identity": self.queue_evidence_identity,
            "selected_lanes": list(self.selected_lanes),
            "coordinator_identity": self.coordinator_identity,
            "connector_identity": self.connector_identity,
            "revision_set_identity": self.revision_set_identity,
            "indexer_identity": self.indexer_identity,
            "indexer_source_identity": self.indexer_source_identity,
            "config_identity": self.config_identity,
            "signature_identity": self.signature_identity,
            "schema_identity": self.schema_identity,
            "generation_ordinal": self.generation_ordinal,
        }


def make_donor_binding(
    revisions: Sequence[DonorRevision],
    *,
    integration_gate: IntegrationGateReceipt,
    indexer_identity: str,
    indexer_source_identity: str,
    config_identity: str,
    signature_identity: str,
    schema_identity: str,
    generation_ordinal: int,
) -> DonorIndexBinding:
    """Build the immutable binding for one donor index generation."""

    ordered = _ordered_revisions(revisions)
    return DonorIndexBinding(
        integration_gate=integration_gate,
        integration_gate_id=integration_gate.gate_id,
        manifest_artifact_identity=integration_gate.manifest_artifact_identity,
        subset_identity=integration_gate.subset_identity,
        queue_evidence_identity=integration_gate.queue_evidence_identity,
        selected_lanes=tuple(integration_gate.selected_lanes),
        coordinator_identity=integration_gate.coordinator_identity,
        connector_identity=integration_gate.connector_identity,
        revision_set_identity=revision_set_identity(ordered),
        indexer_identity=_hash_value(indexer_identity, "indexer_identity"),
        indexer_source_identity=_hash_value(
            indexer_source_identity, "indexer_source_identity"
        ),
        config_identity=_hash_value(config_identity, "config_identity"),
        signature_identity=_hash_value(signature_identity, "signature_identity"),
        schema_identity=_hash_value(schema_identity, "schema_identity"),
        generation_ordinal=generation_ordinal,
    )


@dataclass(frozen=True)
class DonorIndexEntry:
    """One semantic donor record with its immutable revision provenance."""

    entry_id: str
    revision: DonorRevision
    evidence: DonorEvidence

    def __post_init__(self) -> None:
        _hash_value(self.entry_id, "entry_id")
        if not isinstance(self.revision, DonorRevision):
            object.__setattr__(
                self,
                "revision",
                DonorRevision.from_dict(self.revision),  # type: ignore[arg-type]
            )
        if not isinstance(self.evidence, DonorEvidence):
            raise DonorIndexInputError(
                "donor index entries need typed donor evidence"
            )
        if self.evidence.version != self.revision.version:
            raise DonorIndexIdentityMismatch(
                "donor evidence version differs from its pinned revision"
            )
        if self.entry_id != hash_canonical(self.identity_payload()):
            raise DonorIndexIdentityMismatch(
                "entry_id does not match the donor entry payload"
            )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": DONOR_INDEX_PROTOCOL,
            "revision": self.revision.to_dict(),
            "evidence": self.evidence.to_dict(),
        }

    @classmethod
    def from_evidence(
        cls, revision: DonorRevision, evidence: DonorEvidence
    ) -> "DonorIndexEntry":
        """Bind one scanner result to its pinned revision immutably."""

        return cls(
            entry_id=hash_canonical(
                {
                    "protocol": DONOR_INDEX_PROTOCOL,
                    "revision": revision.to_dict(),
                    "evidence": evidence.to_dict(),
                }
            ),
            revision=revision,
            evidence=evidence,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorIndexEntry":
        fields = ("entry_id", "revision", "evidence")
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorIndexInputError(
                "donor index entry fields do not match its protocol"
            )
        data = {key: value[key] for key in fields}
        data["revision"] = DonorRevision.from_dict(data["revision"])
        evidence = data["evidence"]
        if not isinstance(evidence, DonorEvidence):
            source = evidence.get("source")
            if isinstance(source, Mapping):
                source = ArtifactRef.from_dict(source)
            evidence = DonorEvidence(
                **{**evidence, "source": source}
            )
        data["evidence"] = evidence
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "revision": self.revision.to_dict(),
            "evidence": self.evidence.to_dict(),
        }


@dataclass(frozen=True)
class DonorIndexGeneration:
    """One published donor index generation and its complete binding."""

    generation_id: str
    binding: DonorIndexBinding
    revisions: Tuple[DonorRevision, ...]
    entries: Tuple[DonorIndexEntry, ...]
    artifact: ArtifactRef

    def __post_init__(self) -> None:
        if not isinstance(self.binding, DonorIndexBinding):
            object.__setattr__(
                self,
                "binding",
                DonorIndexBinding.from_dict(self.binding),  # type: ignore[arg-type]
            )
        revisions = _ordered_revisions(self.revisions)
        if self.binding.revision_set_identity != revision_set_identity(revisions):
            raise DonorIndexIdentityMismatch(
                "donor index revisions differ from their bound revision set"
            )
        object.__setattr__(self, "revisions", revisions)
        entries = tuple(self.entries)
        for entry in entries:
            if not isinstance(entry, DonorIndexEntry):
                raise DonorIndexInputError(
                    "donor index generation entries must be typed entries"
                )
        ordered_entries = tuple(sorted(entries, key=lambda item: item.entry_id))
        object.__setattr__(self, "entries", ordered_entries)
        if not isinstance(self.artifact, ArtifactRef):
            object.__setattr__(
                self,
                "artifact",
                ArtifactRef.from_dict(self.artifact),  # type: ignore[arg-type]
            )
        payload = _donor_index_payload(self.binding, revisions, ordered_entries)
        if self.generation_id != hash_canonical(payload):
            raise DonorIndexIdentityMismatch(
                "generation_id does not match the donor index payload"
            )
        if self.artifact.content_hash != self.generation_id:
            raise DonorIndexIdentityMismatch(
                "donor index artifact identity differs from its generation id"
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorIndexGeneration":
        fields = ("generation_id", "binding", "revisions", "entries", "artifact")
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorIndexInputError(
                "donor index generation fields do not match its protocol"
            )
        data = {key: value[key] for key in fields}
        data["binding"] = DonorIndexBinding.from_dict(data["binding"])
        data["artifact"] = ArtifactRef.from_dict(data["artifact"])
        return cls(
            generation_id=data["generation_id"],
            binding=data["binding"],
            revisions=tuple(
                DonorRevision.from_dict(item) for item in data["revisions"]
            ),
            entries=tuple(
                DonorIndexEntry.from_dict(item) for item in data["entries"]
            ),
            artifact=data["artifact"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "binding": self.binding.to_dict(),
            "revisions": [item.to_dict() for item in self.revisions],
            "entries": [item.to_dict() for item in self.entries],
            "artifact": self.artifact.to_dict(),
        }


def _donor_index_payload(
    binding: DonorIndexBinding,
    revisions: Sequence[DonorRevision],
    entries: Sequence[DonorIndexEntry],
) -> dict[str, Any]:
    return {
        "protocol": DONOR_INDEX_PROTOCOL,
        "integration_gate": binding.integration_gate.to_dict(),
        "binding": binding.to_dict(),
        "revisions": [item.to_dict() for item in revisions],
        "entries": [item.to_dict() for item in entries],
    }


def _validate_donor_evidence(
    evidence: DonorEvidence,
    revision: DonorRevision,
    archive: ContentAddressedArchive,
) -> None:
    """Apply every per-record acceptance invariant before indexing."""

    if evidence.version != revision.version or not isinstance(
        evidence.source, ArtifactRef
    ):
        raise DonorIndexIdentityMismatch(
            "donor evidence does not match pinned revision"
        )
    if evidence.source != revision.source_artifact:
        raise DonorIndexIdentityMismatch(
            "donor evidence source differs from the pinned revision source artifact"
        )
    if evidence.body is not None:
        raise DonorIndexInputError(
            "donor index cannot store version-specific body bytes"
        )
    try:
        archive.verify(evidence.source)
    except Exception as exc:  # noqa: BLE001
        raise DonorIndexInputError(
            "donor source artifact is missing or corrupt: " + evidence.source.path
        ) from exc
    for key in _FORBIDDEN_METADATA_KEYS:
        if key in evidence.metadata:
            raise DonorIndexInputError(
                f"donor metadata cannot carry version-specific {key}"
            )
    for key, value in evidence.constants.items():
        try:
            reject_unsafe_semantic_constant(value, label=str(key))
        except UnsafeSemanticConstant as exc:
            raise DonorIndexInputError(str(exc)) from exc


def build_donor_index(
    revisions: Sequence[DonorRevision],
    *,
    integration_gate: IntegrationGateReceipt,
    scan_revision: Callable[[DonorRevision], Iterable[DonorEvidence]],
    indexer_identity: str,
    indexer_source_identity: str,
    config_identity: str,
    signature_identity: str,
    schema_identity: str,
    generation_ordinal: int,
    archive: ContentAddressedArchive,
) -> DonorIndexGeneration:
    """Scan each pinned revision once and publish the immutable generation."""

    if not isinstance(archive, ContentAddressedArchive):
        raise DonorIndexInputError("donor index needs a content-addressed archive")
    binding = make_donor_binding(
        revisions,
        integration_gate=integration_gate,
        indexer_identity=indexer_identity,
        indexer_source_identity=indexer_source_identity,
        config_identity=config_identity,
        signature_identity=signature_identity,
        schema_identity=schema_identity,
        generation_ordinal=generation_ordinal,
    )
    ordered = _ordered_revisions(revisions)
    records: list[DonorIndexEntry] = []
    # Exactly one scanner call per pinned revision, in canonical version
    # order. Scanner exceptions propagate unchanged: a failed scan is a
    # failed generation, never a partially indexed one.
    for revision in ordered:
        for evidence in scan_revision(revision):
            _validate_donor_evidence(evidence, revision, archive)
            records.append(DonorIndexEntry.from_evidence(revision, evidence))
    records.sort(key=lambda item: item.entry_id)
    payload = _donor_index_payload(binding, ordered, records)
    artifact = archive.put_json(
        payload,
        category="donor_indexes",
        suffix=".json",
    )
    generation_id = hash_canonical(payload)
    if artifact.content_hash != generation_id:
        raise DonorIndexIdentityMismatch(
            "donor index artifact identity differs from its generation id"
        )
    return DonorIndexGeneration(
        generation_id=generation_id,
        binding=binding,
        revisions=ordered,
        entries=records,
        artifact=artifact,
    )


__all__ = [
    "DONOR_VERSIONS",
    "DonorIndexBinding",
    "DonorIndexEntry",
    "DonorIndexError",
    "DonorIndexGeneration",
    "DonorIndexIdentityMismatch",
    "DonorIndexInputError",
    "DonorRevision",
    "DonorRevisionSetError",
    "build_donor_index",
    "make_donor_binding",
    "revision_set_identity",
]
