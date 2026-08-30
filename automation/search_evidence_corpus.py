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
        ScoreVector,
        SearchValidationError,
        canonical_json,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
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
        ScoreVector,
        SearchValidationError,
        canonical_json,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
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
class AbsenceMaskingClaim:
    """The one negative-evidence shape the corpus records.

    The corpus records that narrowing ``andi`` masks are ABSENT before
    argument use in a reviewed span. That absence is evidence about the
    source, not an excerpt of it, and the shape is deliberately fixed: the
    only claim this plan accepts is the one reviewed in MATCHING-LESSONS
    section 2.
    """

    opcode: str
    masks: Tuple[str, ...]
    scope: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "opcode": self.opcode,
            "masks": list(self.masks),
            "scope": self.scope,
        }


_LESSON_SUFFIX = "MATCHING-LESSONS.md"
_EXPECTED_ABSENCE_CLAIM = AbsenceMaskingClaim(
    opcode="andi",
    masks=("0xff", "0xffff"),
    scope="argument-use",
)


@dataclass(frozen=True)
class LessonCitation:
    """A content-addressed citation into MATCHING-LESSONS.

    The citation stores no source prose. Its identity covers the source
    artifact, the reviewed section and line span, the span's content hash,
    and the reviewed rule with its optional absence claim, so a changed
    lesson revision creates a new citation and never silently moves an old
    span.
    """

    citation_id: str
    source: ArtifactRef
    section: str
    line_start: int
    line_end: int
    span_identity: str
    rule_id: str
    absence_masking: AbsenceMaskingClaim | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "source": self.source.to_dict(),
            "section": self.section,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "span_identity": self.span_identity,
            "rule_id": self.rule_id,
            "absence_masking": (
                self.absence_masking.to_dict()
                if self.absence_masking is not None
                else None
            ),
        }


def _lesson_span_bytes(source_bytes: bytes, line_start: int, line_end: int) -> bytes:
    lines = source_bytes.splitlines(keepends=True)
    if line_end > len(lines):
        raise LessonCitationError(
            f"review span {line_start}-{line_end} exceeds the lesson's "
            f"{len(lines)} lines"
        )
    return b"".join(lines[line_start - 1:line_end])


def _citation_identity_payload(
    source: ArtifactRef,
    section: str,
    line_start: int,
    line_end: int,
    span_identity: str,
    rule_id: str,
    absence_masking: AbsenceMaskingClaim | None,
) -> dict[str, Any]:
    return {
        "source": source.to_dict(),
        "section": section,
        "line_start": line_start,
        "line_end": line_end,
        "span_identity": span_identity,
        "rule_id": rule_id,
        "absence_masking": (
            absence_masking.to_dict() if absence_masking is not None else None
        ),
    }


def make_lesson_citation(
    source: ArtifactRef,
    source_bytes: bytes,
    *,
    section: str,
    line_start: int,
    line_end: int,
    rule_id: str,
    absence_masking: AbsenceMaskingClaim | None = None,
) -> LessonCitation:
    """Bind one reviewed lesson span without decoding any excerpt.

    The caller supplies the complete lesson bytes; the citation keeps only
    hashes and bounds. The source bytes must hash to the artifact's content
    hash, the artifact must name the lesson file, the bounds must be
    positive one-based line numbers inside the file, and any absence claim
    must be the exact reviewed section 2 shape.
    """

    if not isinstance(source, ArtifactRef):
        raise LessonCitationError("lesson citation needs a typed source artifact")
    if not isinstance(source_bytes, (bytes, bytearray)):
        raise LessonCitationError("lesson citation needs the complete source bytes")
    source_bytes = bytes(source_bytes)
    if source.content_hash != hash_bytes(source_bytes):
        raise LessonCitationError(
            "lesson source content hash differs from the supplied bytes"
        )
    if not source.path.endswith(_LESSON_SUFFIX):
        raise LessonCitationError(
            "lesson citations must point at " + _LESSON_SUFFIX
        )
    if not isinstance(section, str) or not section.strip():
        raise LessonCitationError("lesson section must be a nonempty string")
    if isinstance(line_start, bool) or not isinstance(line_start, int) or line_start < 1:
        raise LessonCitationError("line_start must be a positive one-based integer")
    if isinstance(line_end, bool) or not isinstance(line_end, int) or line_end < line_start:
        raise LessonCitationError(
            "line_end must be an integer at least line_start"
        )
    try:
        validate_id(rule_id, "rule_id")
    except SearchValidationError as exc:
        raise LessonCitationError(f"lesson rule_id is invalid: {exc}") from exc
    if absence_masking is not None:
        if not isinstance(absence_masking, AbsenceMaskingClaim):
            raise LessonCitationError(
                "absence masking must be the typed AbsenceMaskingClaim"
            )
        if absence_masking != _EXPECTED_ABSENCE_CLAIM:
            raise LessonCitationError(
                "the only reviewed absence claim is andi 0xff/0xffff at "
                "argument use in lesson section 2"
            )
        if section != "§2":
            raise LessonCitationError(
                "an absence claim is only defined for lesson section §2"
            )
    span = _lesson_span_bytes(source_bytes, line_start, line_end)
    span_identity = hash_bytes(span)
    payload = _citation_identity_payload(
        source,
        section,
        line_start,
        line_end,
        span_identity,
        rule_id,
        absence_masking,
    )
    return LessonCitation(
        citation_id=hash_canonical(payload),
        source=source,
        section=section,
        line_start=line_start,
        line_end=line_end,
        span_identity=span_identity,
        rule_id=rule_id,
        absence_masking=absence_masking,
    )


def verify_lesson_citation(
    citation: LessonCitation,
    source_bytes: bytes,
) -> None:
    """Re-derive a citation against the lesson bytes it claims to cite."""

    if not isinstance(citation, LessonCitation):
        raise LessonCitationError("lesson citation is missing or not typed")
    if not isinstance(source_bytes, (bytes, bytearray)):
        raise LessonCitationError("lesson verification needs the source bytes")
    source_bytes = bytes(source_bytes)
    if citation.source.content_hash != hash_bytes(source_bytes):
        raise LessonCitationError(
            "lesson source content hash differs from the supplied bytes"
        )
    span = _lesson_span_bytes(
        source_bytes, citation.line_start, citation.line_end
    )
    if hash_bytes(span) != citation.span_identity:
        raise LessonCitationError(
            "the cited lesson span no longer matches its content hash"
        )
    payload = _citation_identity_payload(
        citation.source,
        citation.section,
        citation.line_start,
        citation.line_end,
        citation.span_identity,
        citation.rule_id,
        citation.absence_masking,
    )
    if citation.citation_id != hash_canonical(payload):
        raise LessonCitationError(
            "citation identity does not match its recorded span and rule"
        )


def scorer_taxonomy_identity_payload(taxonomy: "ScorerTaxonomy") -> dict[str, Any]:
    """Return the canonical payload behind a taxonomy's identity."""

    return {
        "before": taxonomy.before.to_dict(),
        "after": taxonomy.after.to_dict(),
        "evaluator_identity": taxonomy.evaluator_identity,
        "target_identity": taxonomy.target_identity,
    }


@dataclass(frozen=True)
class ScorerTaxonomy:
    """One before/after score pair with its evaluator and target binding.

    The taxonomy is the corpus's exact score evidence: complete score
    vectors, not the scalar totals, bound to the evaluator that produced
    them and the target they were produced against.
    """

    taxonomy_id: str
    before: ScoreVector
    after: ScoreVector
    evaluator_identity: str
    target_identity: str

    def __post_init__(self) -> None:
        if not isinstance(self.before, ScoreVector):
            object.__setattr__(
                self, "before", ScoreVector.from_dict(self.before)  # type: ignore[arg-type]
            )
        if not isinstance(self.after, ScoreVector):
            object.__setattr__(
                self, "after", ScoreVector.from_dict(self.after)  # type: ignore[arg-type]
            )
        if self.before.compiler_identity != self.after.compiler_identity:
            raise EvidenceIdentityMismatch(
                "scorer taxonomy before and after vectors come from different "
                "compilers"
            )
        if self.before.scorer_algorithm != self.after.scorer_algorithm:
            raise EvidenceIdentityMismatch(
                "scorer taxonomy before and after vectors use different "
                "scorer algorithms"
            )
        validate_hash(self.evaluator_identity, "evaluator_identity")
        validate_hash(self.target_identity, "target_identity")
        if self.taxonomy_id != hash_canonical(
            scorer_taxonomy_identity_payload(self)
        ):
            raise EvidenceIdentityMismatch(
                "taxonomy_id does not match the scorer taxonomy payload"
            )

    def identity_payload(self) -> dict[str, Any]:
        return scorer_taxonomy_identity_payload(self)

    def to_dict(self) -> dict[str, Any]:
        return {"taxonomy_id": self.taxonomy_id, **self.identity_payload()}


def make_scorer_taxonomy(
    before: ScoreVector,
    after: ScoreVector,
    *,
    evaluator_identity: str,
    target_identity: str,
) -> ScorerTaxonomy:
    """Bind one before/after score pair under its evaluator and target."""

    if not isinstance(before, ScoreVector) or not isinstance(after, ScoreVector):
        raise EvidenceIdentityMismatch(
            "scorer taxonomy needs typed before and after score vectors"
        )
    try:
        validate_hash(evaluator_identity, "evaluator_identity")
        validate_hash(target_identity, "target_identity")
    except SearchValidationError as exc:
        raise EvidenceIdentityMismatch(str(exc)) from exc
    payload = {
        "before": before.to_dict(),
        "after": after.to_dict(),
        "evaluator_identity": evaluator_identity,
        "target_identity": target_identity,
    }
    return ScorerTaxonomy(
        taxonomy_id=hash_canonical(payload),
        before=before,
        after=after,
        evaluator_identity=evaluator_identity,
        target_identity=target_identity,
    )


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
    "AbsenceMaskingClaim",
    "CorpusGeneration",
    "EvidenceCorpusError",
    "EvidenceIdentityMismatch",
    "LessonCitation",
    "LessonCitationError",
    "ScorerTaxonomy",
    "build_corpus_generation",
    "canonical_json",
    "make_lesson_citation",
    "make_scorer_taxonomy",
    "scorer_taxonomy_identity_payload",
    "verify_lesson_citation",
]
