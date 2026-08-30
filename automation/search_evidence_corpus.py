"""Canonical evidence corpus consuming the Task 8.2 integration gate.

Task 0 of the evidence-corpus/donor-index plan. This module owns the corpus
side of the canonical integration prerequisite: every corpus consumer imports
the Task 8.2 receipt and refusal from ``automation.search_supervisor`` under
the descriptive names ``IntegrationGateReceipt`` and ``IntegrationGateError``,
calls the canonical validator exactly once before reading any evidence, and
retains the complete validated receipt in every generation it publishes. No
local gate type, wrapper validator, or recovery wrapper is defined here.

Later tasks add lesson citations, scorer taxonomy, draft-landed promotion and
recurring-lineage hypotheses on top of this boundary.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Tuple

try:  # package imports
    from .search_archive import ArtifactRef, ContentAddressedArchive
    from .search_supervisor import (
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from .search_types import (
        SearchValidationError,
        canonical_json,
        hash_canonical,
        validate_hash,
    )
except ImportError:  # direct invocation from the automation directory
    from automation.search_archive import (  # type: ignore
        ArtifactRef,
        ContentAddressedArchive,
    )
    from automation.search_supervisor import (  # type: ignore
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from automation.search_types import (  # type: ignore
        SearchValidationError,
        canonical_json,
        hash_canonical,
        validate_hash,
    )


CORPUS_GENERATION_PROTOCOL = "sotn-search-corpus-generation-v1"


class EvidenceCorpusError(RuntimeError):
    """Base error for corpus and shadow input failures."""


class LessonCitationError(EvidenceCorpusError):
    """A lesson source hash or review span does not verify."""


class EvidenceIdentityMismatch(EvidenceCorpusError):
    """A corpus input identity disagrees with its immutable content."""


def _entry_payload(entry: Any) -> Any:
    if hasattr(entry, "to_dict"):
        return entry.to_dict()
    return entry


@dataclass(frozen=True)
class CorpusGeneration:
    """One immutable corpus generation bound to a validated integration gate.

    Every gate binding is copied from the validated receipt rather than
    accepted from the caller, so a generation cannot claim identities its
    receipt does not carry.
    """

    generation_id: str
    schema_identity: str
    integration_gate: IntegrationGateReceipt
    integration_gate_id: str
    manifest_artifact_identity: str
    subset_identity: str
    queue_evidence_identity: str
    selected_lanes: Tuple[str, ...]
    coordinator_identity: str
    connector_identity: str
    source_identities: Tuple[str, ...]
    entries: Tuple[Any, ...]
    artifact: ArtifactRef

    def __post_init__(self) -> None:
        validate_hash(self.generation_id, "generation_id")
        validate_hash(self.schema_identity, "schema_identity")
        if not isinstance(self.integration_gate, IntegrationGateReceipt):
            raise SearchValidationError(
                "corpus generation needs a typed integration gate receipt"
            )
        if self.integration_gate_id != self.integration_gate.gate_id:
            raise SearchValidationError(
                "corpus generation gate id differs from its integration receipt"
            )
        if not isinstance(self.artifact, ArtifactRef):
            object.__setattr__(
                self,
                "artifact",
                ArtifactRef.from_dict(self.artifact),  # type: ignore[arg-type]
            )
        object.__setattr__(self, "selected_lanes", tuple(self.selected_lanes))
        object.__setattr__(self, "source_identities", tuple(self.source_identities))
        object.__setattr__(self, "entries", tuple(self.entries))

    @classmethod
    def from_dict(cls, value: Mapping) -> "CorpusGeneration":
        fields = (
            "generation_id",
            "schema_identity",
            "integration_gate",
            "integration_gate_id",
            "manifest_artifact_identity",
            "subset_identity",
            "queue_evidence_identity",
            "selected_lanes",
            "coordinator_identity",
            "connector_identity",
            "source_identities",
            "entries",
            "artifact",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise SearchValidationError(
                "corpus generation fields do not match its protocol"
            )
        data = {key: value[key] for key in fields}
        data["integration_gate"] = IntegrationGateReceipt.from_dict(
            data["integration_gate"]
        )
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "schema_identity": self.schema_identity,
            "integration_gate": self.integration_gate.to_dict(),
            "integration_gate_id": self.integration_gate_id,
            "manifest_artifact_identity": self.manifest_artifact_identity,
            "subset_identity": self.subset_identity,
            "queue_evidence_identity": self.queue_evidence_identity,
            "selected_lanes": list(self.selected_lanes),
            "coordinator_identity": self.coordinator_identity,
            "connector_identity": self.connector_identity,
            "source_identities": list(self.source_identities),
            "entries": [_entry_payload(entry) for entry in self.entries],
            "artifact": self.artifact.to_dict(),
        }


def build_corpus_generation(
    entries: Iterable[Any],
    *,
    integration_gate: IntegrationGateReceipt,
    schema_identity: str,
    archive: ContentAddressedArchive,
) -> CorpusGeneration:
    """Publish one corpus generation bound to a validated integration receipt.

    The canonical Task 8.2 validator decides whether the receipt is missing,
    changed or otherwise invalid, and is called exactly once, before any
    entry is read. The generation artifact carries the complete receipt
    payload, including its archived receipt artifact reference, so consumers
    can re-verify the gate from the generation bytes alone.
    """

    if integration_gate is None:
        raise IntegrationGateError(
            "integration gate receipt is required before any corpus evidence is read"
        )
    if not isinstance(integration_gate, IntegrationGateReceipt):
        raise IntegrationGateError(
            "integration gate receipt is not the canonical typed receipt"
        )
    validate_hash(schema_identity, "schema_identity")
    # The one canonical validator call for this generation boundary.
    validate_integration_gate(integration_gate, archive=archive)
    entry_values = tuple(entries)
    payload = {
        "protocol": CORPUS_GENERATION_PROTOCOL,
        "schema_identity": schema_identity,
        "integration_gate": integration_gate.to_dict(),
        "source_identities": [],
        "entries": [_entry_payload(entry) for entry in entry_values],
    }
    artifact = archive.put_json(payload)
    return CorpusGeneration(
        generation_id=hash_canonical(payload),
        schema_identity=schema_identity,
        integration_gate=integration_gate,
        integration_gate_id=integration_gate.gate_id,
        manifest_artifact_identity=integration_gate.manifest_artifact_identity,
        subset_identity=integration_gate.subset_identity,
        queue_evidence_identity=integration_gate.queue_evidence_identity,
        selected_lanes=tuple(integration_gate.selected_lanes),
        coordinator_identity=integration_gate.coordinator_identity,
        connector_identity=integration_gate.connector_identity,
        source_identities=(),
        entries=entry_values,
        artifact=artifact,
    )


# canonical_json is re-exported for callers assembling entry payloads; the
# corpus identity rules require canonical serialization everywhere.
__all__ = [
    "CORPUS_GENERATION_PROTOCOL",
    "CorpusGeneration",
    "EvidenceCorpusError",
    "EvidenceIdentityMismatch",
    "LessonCitationError",
    "build_corpus_generation",
    "canonical_json",
]
