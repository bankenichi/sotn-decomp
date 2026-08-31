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
from typing import Any, Callable, Set, Tuple

try:  # package imports
    from .compiler_idioms import CompilerIdiomError, validate_commit_identity
    from .search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive
    from .search_lanes import (
        DonorEvidence,
        LaneError,
        UnsafeSemanticConstant,
        reject_unsafe_semantic_constant,
    )
    from .search_supervisor import (
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from .search_types import (
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_canonical,
        validate_hash,
    )
except ImportError:  # direct invocation from the automation directory
    from automation.compiler_idioms import (  # type: ignore
        CompilerIdiomError,
        validate_commit_identity,
    )
    from automation.search_archive import (  # type: ignore
        ArchiveError,
        ArtifactRef,
        ContentAddressedArchive,
    )
    from automation.search_lanes import (  # type: ignore
        DonorEvidence,
        LaneError,
        UnsafeSemanticConstant,
        reject_unsafe_semantic_constant,
    )
    from automation.search_supervisor import (  # type: ignore
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from automation.search_types import (  # type: ignore
        RunManifest,
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
        if not isinstance(self.version, str) or self.version not in DONOR_VERSIONS:
            raise DonorRevisionSetError(
                f"donor version {self.version!r} is not one of "
                + ", ".join(DONOR_VERSIONS)
            )
        try:
            revision = validate_commit_identity(self.revision, "revision")
        except (CompilerIdiomError, TypeError, ValueError) as exc:
            raise DonorRevisionSetError(
                "donor revision must be a full immutable commit identity"
            ) from exc
        object.__setattr__(self, "revision", revision)
        if not isinstance(self.source_artifact, ArtifactRef):
            try:
                source_artifact = ArtifactRef.from_dict(self.source_artifact)  # type: ignore[arg-type]
            except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
                raise DonorRevisionSetError(
                    "donor revision source artifact is invalid"
                ) from exc
            object.__setattr__(self, "source_artifact", source_artifact)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorRevision":
        fields = ("version", "revision", "source_artifact")
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorIndexInputError(
                "donor revision fields do not match its protocol"
            )
        try:
            data = {key: value[key] for key in fields}
            data["source_artifact"] = ArtifactRef.from_dict(data["source_artifact"])
            return cls(**data)
        except (
            AttributeError,
            DonorIndexError,
            SearchValidationError,
            TypeError,
            ValueError,
        ) as exc:
            if isinstance(exc, DonorIndexError):
                raise
            raise DonorIndexInputError(
                "donor revision payload is invalid: " + str(exc)
            ) from exc

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

    if not isinstance(revisions, (tuple, list)):
        raise DonorIndexInputError(
            "donor revisions must be an explicit tuple or list"
        )
    try:
        revision_values = tuple(revisions)
    except (TypeError, ValueError) as exc:
        raise DonorIndexInputError("donor revisions are not a valid sequence") from exc
    normalized: list[DonorRevision] = []
    for revision in revision_values:
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
    compiler_identity: str
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
        _hash_value(self.compiler_identity, "compiler_identity")
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
        # The caller's lane list is validated, not overwritten: a forged lane
        # set must refuse rather than silently inherit the receipt's lanes.
        if not isinstance(self.selected_lanes, (tuple, list)):
            raise DonorIndexInputError(
                "donor index binding selected lanes must be a tuple or list"
            )
        lanes = tuple(self.selected_lanes)
        if lanes != tuple(self.integration_gate.selected_lanes):
            raise DonorIndexIdentityMismatch(
                "donor index selected lanes differ from their integration receipt"
            )
        object.__setattr__(self, "selected_lanes", lanes)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorIndexBinding":
        fields = (
            "integration_gate",
            "integration_gate_id",
            "manifest_artifact_identity",
            "compiler_identity",
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
        try:
            data["integration_gate"] = IntegrationGateReceipt.from_dict(
                data["integration_gate"]
            )
            return cls(**data)
        except DonorIndexError:
            raise
        except (
            AttributeError,
            IntegrationGateError,
            KeyError,
            SearchValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise DonorIndexInputError(
                "donor index binding payload is invalid: " + str(exc)
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration_gate": self.integration_gate.to_dict(),
            "integration_gate_id": self.integration_gate_id,
            "manifest_artifact_identity": self.manifest_artifact_identity,
            "compiler_identity": self.compiler_identity,
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
    compiler_identity: str,
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
        compiler_identity=_hash_value(compiler_identity, "compiler_identity"),
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
            try:
                revision = DonorRevision.from_dict(self.revision)  # type: ignore[arg-type]
            except DonorIndexError:
                raise
            except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
                raise DonorIndexInputError(
                    "donor index entry revision is invalid"
                ) from exc
            object.__setattr__(self, "revision", revision)
        if not isinstance(self.evidence, DonorEvidence):
            raise DonorIndexInputError(
                "donor index entries need typed donor evidence"
            )
        if not isinstance(self.evidence.source, ArtifactRef):
            raise DonorIndexInputError(
                "donor index entries need an immutable source artifact"
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
        try:
            data["revision"] = DonorRevision.from_dict(data["revision"])
            evidence = data["evidence"]
            if not isinstance(evidence, DonorEvidence):
                source = evidence.get("source")
                if isinstance(source, Mapping):
                    source = ArtifactRef.from_dict(source)
                data["evidence"] = DonorEvidence(
                    **{**evidence, "source": source}
                )
            return cls(**data)
        except (
            AttributeError,
            LaneError,
            DonorIndexError,
            SearchValidationError,
            TypeError,
            ValueError,
        ) as exc:
            if isinstance(exc, DonorIndexError):
                raise
            raise DonorIndexInputError(
                "donor index entry payload is invalid: " + str(exc)
            ) from exc

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
            try:
                binding = DonorIndexBinding.from_dict(self.binding)  # type: ignore[arg-type]
            except DonorIndexError:
                raise
            except (
                AttributeError,
                IntegrationGateError,
                KeyError,
                SearchValidationError,
                TypeError,
                ValueError,
            ) as exc:
                raise DonorIndexInputError(
                    "donor index binding is invalid"
                ) from exc
            object.__setattr__(self, "binding", binding)
        revisions = _ordered_revisions(self.revisions)
        if self.binding.revision_set_identity != revision_set_identity(revisions):
            raise DonorIndexIdentityMismatch(
                "donor index revisions differ from their bound revision set"
            )
        object.__setattr__(self, "revisions", revisions)
        pinned = {item.version: item for item in revisions}
        if not isinstance(self.entries, (tuple, list)):
            raise DonorIndexInputError(
                "donor index generation entries must be an explicit tuple or list"
            )
        try:
            entries = tuple(self.entries)
        except (TypeError, ValueError) as exc:
            raise DonorIndexInputError(
                "donor index generation entries are not a valid sequence"
            ) from exc
        seen_entry_ids: Set[str] = set()
        for entry in entries:
            if not isinstance(entry, DonorIndexEntry):
                raise DonorIndexInputError(
                    "donor index generation entries must be typed entries"
                )
            if entry.revision != pinned.get(entry.evidence.version):
                raise DonorIndexIdentityMismatch(
                    "donor index entry revision differs from the pinned "
                    "revision for its version"
                )
            if entry.entry_id in seen_entry_ids:
                raise DonorIndexIdentityMismatch(
                    "donor index generation contains duplicate entry ids"
                )
            seen_entry_ids.add(entry.entry_id)
        ordered_entries = tuple(sorted(entries, key=lambda item: item.entry_id))
        object.__setattr__(self, "entries", ordered_entries)
        if not isinstance(self.artifact, ArtifactRef):
            try:
                artifact = ArtifactRef.from_dict(self.artifact)  # type: ignore[arg-type]
            except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
                raise DonorIndexInputError(
                    "donor index artifact is invalid"
                ) from exc
            object.__setattr__(self, "artifact", artifact)
        if not isinstance(self.generation_id, str):
            raise DonorIndexInputError("donor index generation id must be a hash")
        _hash_value(self.generation_id, "generation_id")
        payload = _donor_index_payload(self.binding, revisions, ordered_entries)
        if self.generation_id != hash_canonical(payload):
            raise DonorIndexIdentityMismatch(
                "generation_id does not match the donor index payload"
            )
        expected_bytes = canonical_bytes(payload)
        expected_path = (
            "artifacts/donor_indexes/"
            + self.generation_id.removeprefix("sha256:")
            + ".json"
        )
        if (
            self.artifact.content_hash != self.generation_id
            or self.artifact.path != expected_path
            or self.artifact.media_type != "application/json"
            or self.artifact.byte_size != len(expected_bytes)
        ):
            raise DonorIndexIdentityMismatch(
                "donor index artifact identity or metadata differs from "
                "canonical payload bytes"
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DonorIndexGeneration":
        fields = ("generation_id", "binding", "revisions", "entries", "artifact")
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise DonorIndexInputError(
                "donor index generation fields do not match its protocol"
            )
        data = {key: value[key] for key in fields}
        for name in ("revisions", "entries"):
            if not isinstance(data[name], (list, tuple)):
                raise DonorIndexInputError(
                    f"donor index generation {name} must be an array"
                )
        try:
            data["binding"] = DonorIndexBinding.from_dict(data["binding"])
            data["artifact"] = ArtifactRef.from_dict(data["artifact"])
            revisions = tuple(
                DonorRevision.from_dict(item) for item in data["revisions"]
            )
            entries = tuple(
                DonorIndexEntry.from_dict(item) for item in data["entries"]
            )
            return cls(
                generation_id=data["generation_id"],
                binding=data["binding"],
                revisions=revisions,
                entries=entries,
                artifact=data["artifact"],
            )
        except DonorIndexError:
            raise
        except (
            AttributeError,
            IntegrationGateError,
            KeyError,
            SearchValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise DonorIndexInputError(
                "donor index generation payload is invalid: " + str(exc)
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "binding": self.binding.to_dict(),
            "revisions": [item.to_dict() for item in self.revisions],
            "entries": [item.to_dict() for item in self.entries],
            "artifact": self.artifact.to_dict(),
        }

    def payload(self) -> dict[str, Any]:
        """Return the canonical payload whose bytes identify this generation."""

        return _donor_index_payload(self.binding, self.revisions, self.entries)


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


def _reject_forbidden_key_tree(value: Any, label: str) -> None:
    """Walk one donor tree and refuse forbidden version-specific keys.

    A nested mapping can hide registers, relocations, or branch
    displacements that a top-level key check would index; the walk is
    field-aware so the refusal names the exact offending path.
    """

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise DonorIndexInputError(
                    f"donor {label} keys must be strings"
                )
            if key in _FORBIDDEN_METADATA_KEYS:
                raise DonorIndexInputError(
                    f"donor {label} cannot carry version-specific {key}"
                )
            _reject_forbidden_key_tree(item, f"{label}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_forbidden_key_tree(item, f"{label}[{index}]")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise DonorIndexInputError(
            f"donor {label} carries an unsupported value shape"
        )


def _reject_unsafe_constant_tree(value: Any, label: str) -> None:
    """Reject unsafe semantic constants anywhere in a constants tree.

    The path label feeds the lane validator's field-aware register and
    branch context, so a constant nested under a register- or
    displacement-shaped key is judged in that context, never as a bare
    top-level value.
    """

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise DonorIndexInputError(
                    "donor constants keys must be strings"
                )
            _reject_unsafe_constant_tree(item, f"{label}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_unsafe_constant_tree(item, f"{label}[{index}]")
    elif value is None or isinstance(value, (str, int, float, bool)):
        try:
            reject_unsafe_semantic_constant(value, label=label)
        except UnsafeSemanticConstant as exc:
            raise DonorIndexInputError(str(exc)) from exc
    else:
        raise DonorIndexInputError(
            f"donor {label} carries an unsupported constant shape"
        )


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
    except ArchiveError as exc:
        raise DonorIndexInputError(
            "donor source artifact is missing or corrupt: " + evidence.source.path
        ) from exc
    # Queryable signature fields are null or real strings: Task 6 consumes
    # them as indexed selectors, and a malformed selector would silently
    # narrow or poison the query space.
    for name in (
        "symbol",
        "instruction_signature",
        "cfg_signature",
        "dataflow_signature",
    ):
        value = getattr(evidence, name)
        if value is not None and (not isinstance(value, str) or not value):
            raise DonorIndexInputError(
                f"donor {name} must be null or a nonempty string"
            )
    if not isinstance(evidence.compatible, bool):
        raise DonorIndexInputError(
            "donor compatibility must be an actual boolean"
        )
    if not any(
        getattr(evidence, name)
        for name in (
            "symbol",
            "instruction_signature",
            "cfg_signature",
            "dataflow_signature",
        )
    ):
        raise DonorIndexInputError(
            "donor evidence must retain at least one semantic selector"
        )
    _reject_forbidden_key_tree(evidence.metadata, "metadata")
    _reject_forbidden_key_tree(evidence.declarations, "declarations")
    _reject_forbidden_key_tree(evidence.constants, "constants")
    _reject_unsafe_constant_tree(evidence.constants, "constants")


def build_donor_index(
    revisions: Sequence[DonorRevision],
    *,
    integration_gate: IntegrationGateReceipt,
    integration_archive: ContentAddressedArchive,
    scan_revision: Callable[[DonorRevision], Iterable[DonorEvidence]],
    indexer_identity: str,
    indexer_source_identity: str,
    config_identity: str,
    signature_identity: str,
    schema_identity: str,
    generation_ordinal: int,
    archive: ContentAddressedArchive,
) -> DonorIndexGeneration:
    """Scan each pinned revision once and publish the immutable generation.

    ``integration_archive`` is the canonical integration-run archive that
    owns the receipt; the donor output ``archive`` stays separate. The
    canonical validator is called exactly once, before revisions are
    canonicalized, the scanner is invoked, or any donor evidence is read, so
    a forged or self-consistent receipt can never authorize a scan.
    """

    if not isinstance(archive, ContentAddressedArchive):
        raise DonorIndexInputError("donor index needs a content-addressed archive")
    if not isinstance(integration_archive, ContentAddressedArchive):
        raise IntegrationGateError(
            "integration gate archive is required before any donor evidence is read"
        )
    # The one canonical validator call for this generation boundary.
    verified_manifest = validate_integration_gate(
        integration_gate,
        archive=integration_archive,
    )
    if not isinstance(verified_manifest, RunManifest):
        raise IntegrationGateError(
            "integration gate validator did not return its verified manifest"
        )
    binding = make_donor_binding(
        revisions,
        integration_gate=integration_gate,
        compiler_identity=verified_manifest.compiler_identity,
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
