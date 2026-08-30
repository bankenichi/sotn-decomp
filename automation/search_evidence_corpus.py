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
from dataclasses import dataclass, replace
from typing import Any, Sequence, Tuple

try:  # package imports
    from .compiler_idioms import (
        CompilerIdiomObservation,
        DraftLandedObservation,
        MeasurementError,
        make_idiom_observation,
        measure_improvement,
    )
    from .search_archive import ArtifactRef, ContentAddressedArchive
    from .search_patterns import (
        CompletedLineageContext,
        CompletedLineageDiagnostic,
        SearchPatternReport,
    )
    from .search_supervisor import (
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from .search_types import (
        FirstDivergence,
        ScoreVector,
        SearchValidationError,
        canonical_bytes,
        canonical_json,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )
except ImportError:  # direct invocation from the automation directory
    from automation.compiler_idioms import (  # type: ignore
        CompilerIdiomObservation,
        DraftLandedObservation,
        MeasurementError,
        make_idiom_observation,
        measure_improvement,
    )
    from automation.search_archive import (  # type: ignore
        ArtifactRef,
        ContentAddressedArchive,
    )
    from automation.search_patterns import (  # type: ignore
        CompletedLineageContext,
        CompletedLineageDiagnostic,
        SearchPatternReport,
    )
    from automation.search_supervisor import (  # type: ignore
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from automation.search_types import (  # type: ignore
        FirstDivergence,
        ScoreVector,
        SearchValidationError,
        canonical_bytes,
        canonical_json,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
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
_ABSENCE_RULE_ID = "argument-width.absent-andi"
_ABSENCE_SECTION = "§2"
_ABSENCE_LINE_START = 146
_ABSENCE_LINE_END = 178


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


def _validate_lesson_inputs(
    source: ArtifactRef,
    source_bytes: bytes,
    *,
    section: str,
    line_start: int,
    line_end: int,
    rule_id: str,
    absence_masking: AbsenceMaskingClaim | None,
) -> bytes:
    """Reapply every citation constructor invariant.

    Keeping this as one helper is important: verification must not become a
    weaker path than construction when a caller assembles a dataclass or
    JSON mapping directly.
    """

    if not isinstance(source, ArtifactRef):
        raise LessonCitationError("lesson citation needs a typed source artifact")
    if not isinstance(source_bytes, (bytes, bytearray)):
        raise LessonCitationError("lesson citation needs the complete source bytes")
    source_bytes = bytes(source_bytes)
    try:
        source_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise LessonCitationError("lesson source must be strict UTF-8") from exc
    try:
        validate_hash(source.content_hash, "lesson source content_hash")
        validate_relative_path(source.path, "lesson source path")
    except SearchValidationError as exc:
        raise LessonCitationError("lesson source artifact identity is invalid") from exc
    if source.content_hash != hash_bytes(source_bytes):
        raise LessonCitationError(
            "lesson source content hash differs from the supplied bytes"
        )
    if not source.path.endswith(_LESSON_SUFFIX):
        raise LessonCitationError(
            "lesson citations must point at " + _LESSON_SUFFIX
        )
    if not isinstance(source.media_type, str) or source.media_type != "text/markdown":
        raise LessonCitationError("lesson source media type must be text/markdown")
    if (
        isinstance(source.byte_size, bool)
        or not isinstance(source.byte_size, int)
        or source.byte_size != len(source_bytes)
    ):
        raise LessonCitationError("lesson source byte size differs from its bytes")
    if not isinstance(section, str) or not section.strip():
        raise LessonCitationError("lesson section must be a nonempty string")
    if isinstance(line_start, bool) or not isinstance(line_start, int) or line_start < 1:
        raise LessonCitationError("line_start must be a positive one-based integer")
    if isinstance(line_end, bool) or not isinstance(line_end, int) or line_end < line_start:
        raise LessonCitationError("line_end must be an integer at least line_start")
    try:
        validate_id(rule_id, "rule_id")
    except SearchValidationError as exc:
        raise LessonCitationError(f"lesson rule_id is invalid: {exc}") from exc
    if absence_masking is not None and not isinstance(
        absence_masking, AbsenceMaskingClaim
    ):
        raise LessonCitationError(
            "absence masking must be the typed AbsenceMaskingClaim"
        )

    try:
        span = _lesson_span_bytes(source_bytes, line_start, line_end)
    except LessonCitationError:
        raise
    except (TypeError, ValueError) as exc:
        raise LessonCitationError("lesson review span is invalid") from exc

    # Section 2 is not a generic span API.  This exact source anchor and
    # absence claim are the reviewed fact that the corpus is allowed to carry.
    if section == _ABSENCE_SECTION:
        if (
            rule_id != _ABSENCE_RULE_ID
            or line_start != _ABSENCE_LINE_START
            or line_end != _ABSENCE_LINE_END
            or absence_masking != _EXPECTED_ABSENCE_CLAIM
        ):
            raise LessonCitationError(
                "section §2 requires the exact argument-width.absent-andi "
                "anchor and absence claim"
            )
    elif rule_id == _ABSENCE_RULE_ID or absence_masking is not None:
        raise LessonCitationError(
            "the argument-width absence claim is only defined for section §2"
        )
    return span


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

    source_bytes = bytes(source_bytes) if isinstance(source_bytes, (bytes, bytearray)) else source_bytes
    span = _validate_lesson_inputs(
        source,
        source_bytes,
        section=section,
        line_start=line_start,
        line_end=line_end,
        rule_id=rule_id,
        absence_masking=absence_masking,
    )
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
    source_bytes = bytes(source_bytes) if isinstance(source_bytes, (bytes, bytearray)) else source_bytes
    try:
        span = _validate_lesson_inputs(
            citation.source,
            source_bytes,
            section=citation.section,
            line_start=citation.line_start,
            line_end=citation.line_end,
            rule_id=citation.rule_id,
            absence_masking=citation.absence_masking,
        )
    except LessonCitationError:
        raise
    except (AttributeError, TypeError, ValueError, SearchValidationError) as exc:
        raise LessonCitationError("lesson citation constructor invariants are invalid") from exc
    try:
        validate_hash(citation.citation_id, "citation_id")
        validate_hash(citation.span_identity, "span_identity")
    except SearchValidationError as exc:
        raise LessonCitationError("lesson citation identity is invalid") from exc
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
        try:
            if not isinstance(self.before, ScoreVector):
                before = ScoreVector.from_dict(self.before)  # type: ignore[arg-type]
            else:
                before = ScoreVector.from_dict(self.before.to_dict())
            if not isinstance(self.after, ScoreVector):
                after = ScoreVector.from_dict(self.after)  # type: ignore[arg-type]
            else:
                after = ScoreVector.from_dict(self.after.to_dict())
            object.__setattr__(self, "before", before)
            object.__setattr__(self, "after", after)
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch(
                "scorer taxonomy contains an invalid score vector"
            ) from exc
        if not isinstance(self.before, ScoreVector) or not isinstance(
            self.after, ScoreVector
        ):
            raise EvidenceIdentityMismatch(
                "scorer taxonomy needs typed before and after score vectors"
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
        try:
            validate_hash(self.taxonomy_id, "taxonomy_id")
            validate_hash(self.evaluator_identity, "evaluator_identity")
            validate_hash(self.target_identity, "target_identity")
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch(
                "scorer taxonomy identity is not a content hash"
            ) from exc
        if self.taxonomy_id != hash_canonical(scorer_taxonomy_identity_payload(self)):
            raise EvidenceIdentityMismatch(
                "taxonomy_id does not match the scorer taxonomy payload"
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScorerTaxonomy":
        fields = {
            "taxonomy_id",
            "before",
            "after",
            "evaluator_identity",
            "target_identity",
        }
        if not isinstance(value, Mapping) or set(value) != fields:
            raise EvidenceIdentityMismatch(
                "scorer taxonomy fields do not match its complete identity payload"
            )
        try:
            before = ScoreVector.from_dict(value["before"])
            after = ScoreVector.from_dict(value["after"])
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch(
                "scorer taxonomy contains an invalid score vector"
            ) from exc
        try:
            return cls(
                taxonomy_id=value["taxonomy_id"],
                before=before,
                after=after,
                evaluator_identity=value["evaluator_identity"],
                target_identity=value["target_identity"],
            )
        except EvidenceIdentityMismatch:
            raise
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch("scorer taxonomy is invalid") from exc

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
        try:
            validate_hash(self.generation_id, "generation_id")
            validate_hash(self.schema_identity, "schema_identity")
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch("corpus generation identity is invalid") from exc
        if not isinstance(self.integration_gate, IntegrationGateReceipt):
            raise EvidenceIdentityMismatch(
                "corpus generation needs a typed integration gate receipt"
            )
        try:
            canonical_gate = IntegrationGateReceipt.from_dict(
                self.integration_gate.to_dict()
            )
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch(
                "corpus generation integration gate invariants are invalid"
            ) from exc
        if canonical_gate != self.integration_gate:
            raise EvidenceIdentityMismatch(
                "corpus generation integration gate invariants are invalid"
            )
        object.__setattr__(self, "integration_gate", canonical_gate)
        if self.integration_gate_id != self.integration_gate.gate_id:
            raise EvidenceIdentityMismatch(
                "corpus generation gate id differs from its integration receipt"
            )
        copied = (
            ("manifest_artifact_identity", self.manifest_artifact_identity),
            ("subset_identity", self.subset_identity),
            ("queue_evidence_identity", self.queue_evidence_identity),
            ("coordinator_identity", self.coordinator_identity),
            ("connector_identity", self.connector_identity),
        )
        try:
            for name, value in copied:
                validate_hash(value, name)
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch("corpus gate provenance is invalid") from exc
        for name, value in copied:
            if value != getattr(self.integration_gate, name):
                raise EvidenceIdentityMismatch(
                    f"corpus generation {name} differs from its integration receipt"
                )
        try:
            lanes = tuple(self.selected_lanes)
        except (TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch("corpus generation selected lanes are invalid") from exc
        if lanes != self.integration_gate.selected_lanes:
            raise EvidenceIdentityMismatch(
                "corpus generation selected lanes differ from its integration receipt"
            )
        if not lanes or lanes != tuple(dict.fromkeys(lanes)):
            raise EvidenceIdentityMismatch("corpus generation selected lanes are invalid")
        object.__setattr__(self, "selected_lanes", lanes)
        original_artifact = self.artifact
        try:
            artifact = (
                ArtifactRef.from_dict(self.artifact.to_dict())
                if isinstance(self.artifact, ArtifactRef)
                else ArtifactRef.from_dict(self.artifact)  # type: ignore[arg-type]
            )
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch("corpus artifact reference is invalid") from exc
        if isinstance(original_artifact, ArtifactRef) and artifact != original_artifact:
            raise EvidenceIdentityMismatch("corpus artifact reference is invalid")
        object.__setattr__(self, "artifact", artifact)
        try:
            source_identities = tuple(self.source_identities)
        except (TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch("corpus source identities are invalid") from exc
        if source_identities != tuple(sorted(set(source_identities))):
            raise EvidenceIdentityMismatch(
                "corpus source identities must be sorted and unique"
            )
        try:
            for identity in source_identities:
                validate_hash(identity, "source identity")
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch("corpus source identity is invalid") from exc
        object.__setattr__(self, "source_identities", source_identities)

        try:
            raw_entries = tuple(_entry_payload(entry) for entry in self.entries)
            entry_ids = []
            for entry in raw_entries:
                if not isinstance(entry, Mapping):
                    raise EvidenceIdentityMismatch("corpus entries must be objects")
                evidence_id = entry.get("evidence_id")
                validate_hash(evidence_id, "evidence_id")
                entry_ids.append(evidence_id)
            if len(set(entry_ids)) != len(entry_ids):
                raise EvidenceIdentityMismatch("corpus evidence IDs must be unique")
            ordered_entries = tuple(
                entry
                for _identity, entry in sorted(
                    zip(entry_ids, raw_entries), key=lambda item: item[0]
                )
            )
        except EvidenceIdentityMismatch:
            raise
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch("corpus entry identity is invalid") from exc
        object.__setattr__(self, "entries", ordered_entries)

        payload = _corpus_generation_payload(
            schema_identity=self.schema_identity,
            integration_gate=self.integration_gate,
            source_identities=source_identities,
            entries=ordered_entries,
        )
        expected_bytes = canonical_bytes(payload)
        try:
            validate_hash(self.artifact.content_hash, "corpus artifact content_hash")
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch("corpus artifact identity is invalid") from exc
        expected_hash = hash_bytes(expected_bytes)
        expected_generation = hash_canonical(payload)
        if self.generation_id != expected_generation:
            raise EvidenceIdentityMismatch(
                "generation_id does not match the exact corpus generation payload"
            )
        if (
            self.artifact.content_hash != expected_hash
            or self.artifact.media_type != "application/json"
            or self.artifact.byte_size != len(expected_bytes)
            or self.artifact.path
            != f"artifacts/evidence_corpus/{expected_hash.removeprefix('sha256:')}.json"
        ):
            raise EvidenceIdentityMismatch(
                "corpus artifact identity or metadata differs from canonical payload bytes"
            )

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
            raise EvidenceIdentityMismatch(
                "corpus generation fields do not match its protocol"
            )
        data = {key: value[key] for key in fields}
        try:
            data["integration_gate"] = IntegrationGateReceipt.from_dict(
                data["integration_gate"]
            )
            data["artifact"] = ArtifactRef.from_dict(data["artifact"])
            return cls(**data)
        except EvidenceIdentityMismatch:
            raise
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch("corpus generation payload is invalid") from exc

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


def _corpus_generation_payload(
    *,
    schema_identity: str,
    integration_gate: IntegrationGateReceipt,
    source_identities: Sequence[str],
    entries: Sequence[Any],
) -> dict[str, Any]:
    """Return the one canonical payload used by build and direct validation."""

    return {
        "protocol": CORPUS_GENERATION_PROTOCOL,
        "schema_identity": schema_identity,
        "integration_gate": integration_gate.to_dict(),
        "integration_gate_id": integration_gate.gate_id,
        "manifest_artifact_identity": integration_gate.manifest_artifact_identity,
        "subset_identity": integration_gate.subset_identity,
        "queue_evidence_identity": integration_gate.queue_evidence_identity,
        "selected_lanes": list(integration_gate.selected_lanes),
        "coordinator_identity": integration_gate.coordinator_identity,
        "connector_identity": integration_gate.connector_identity,
        "source_identities": list(source_identities),
        "entries": [_entry_payload(entry) for entry in entries],
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
    try:
        validate_hash(schema_identity, "schema_identity")
    except SearchValidationError as exc:
        raise EvidenceIdentityMismatch("schema identity is invalid") from exc
    # The one canonical validator call for this generation boundary.
    validate_integration_gate(integration_gate, archive=archive)
    entry_values = tuple(entries)
    try:
        entry_payloads = tuple(_entry_payload(entry) for entry in entry_values)
        entry_ids = []
        for entry in entry_payloads:
            if not isinstance(entry, Mapping):
                raise EvidenceIdentityMismatch("corpus entries must be objects")
            evidence_id = entry.get("evidence_id")
            validate_hash(evidence_id, "evidence_id")
            entry_ids.append(evidence_id)
        if len(set(entry_ids)) != len(entry_ids):
            raise EvidenceIdentityMismatch("corpus evidence IDs must be unique")
        ordered_entries = tuple(
            entry
            for _identity, entry in sorted(
                zip(entry_ids, entry_payloads), key=lambda item: item[0]
            )
        )
    except EvidenceIdentityMismatch:
        raise
    except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
        raise EvidenceIdentityMismatch("corpus entry identity is invalid") from exc
    source_identities: tuple[str, ...] = ()
    payload = _corpus_generation_payload(
        schema_identity=schema_identity,
        integration_gate=integration_gate,
        source_identities=source_identities,
        entries=ordered_entries,
    )
    artifact = archive.put_json(
        payload,
        category="evidence_corpus",
        suffix=".json",
    )
    if artifact.content_hash != hash_bytes(canonical_bytes(payload)):
        raise EvidenceIdentityMismatch(
            "corpus artifact identity differs from canonical payload bytes"
        )
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
        source_identities=source_identities,
        entries=ordered_entries,
        artifact=artifact,
    )


# canonical_json is re-exported for callers assembling entry payloads; the
# corpus identity rules require canonical serialization everywhere.


@dataclass(frozen=True)
class EvidenceRefusalReceipt:
    """Typed refusal for one evidence-gating operation.

    The receipt records what was refused and why without discarding the
    observations that caused the refusal; the paired ``CorpusEvidence`` keeps
    those observations as negative evidence.
    """

    receipt_id: str
    operation: str
    reason_code: str
    input_identities: Tuple[str, ...]
    observed_identities: Tuple[str, ...]
    new_generation_required: bool

    def __post_init__(self) -> None:
        try:
            validate_hash(self.receipt_id, "receipt_id")
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch(str(exc)) from exc
        if not isinstance(self.operation, str) or not self.operation:
            raise EvidenceIdentityMismatch("refusal operation must be named")
        if not isinstance(self.reason_code, str) or not self.reason_code:
            raise EvidenceIdentityMismatch("refusal reason must be named")
        inputs = tuple(self.input_identities)
        observed = tuple(self.observed_identities)
        for name, values in (("input", inputs), ("observed", observed)):
            for value in values:
                if not isinstance(value, str) or not value:
                    raise EvidenceIdentityMismatch(
                        f"refusal {name} identities must be nonempty strings"
                    )
        if isinstance(self.new_generation_required, bool) is False:
            raise EvidenceIdentityMismatch(
                "new_generation_required must be a boolean"
            )
        object.__setattr__(self, "input_identities", inputs)
        object.__setattr__(self, "observed_identities", observed)
        payload = {
            "protocol": "sotn-evidence-refusal-v1",
            "operation": self.operation,
            "reason_code": self.reason_code,
            "input_identities": list(inputs),
            "observed_identities": list(observed),
            "new_generation_required": self.new_generation_required,
        }
        if self.receipt_id != hash_canonical(payload):
            raise EvidenceIdentityMismatch(
                "receipt_id does not match the refusal receipt payload"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "operation": self.operation,
            "reason_code": self.reason_code,
            "input_identities": list(self.input_identities),
            "observed_identities": list(self.observed_identities),
            "new_generation_required": self.new_generation_required,
        }


@dataclass(frozen=True)
class CorpusEvidence:
    """One corpus record: a promotion, a recurrence, or negative evidence."""

    evidence_id: str
    kind: str
    outcome: str
    recipient_id: str | None
    compiler_identity: str | None
    tool_identity: str | None
    target_identity: str | None
    evaluator_identity: str | None
    config_identity: str | None
    scorer: ScorerTaxonomy | None
    citations: Tuple[LessonCitation, ...]
    draft_landed: Tuple[DraftLandedObservation, ...]
    idiom: CompilerIdiomObservation | None
    first_divergence: FirstDivergence | None
    support_identities: Tuple[str, ...]
    reason_code: str | None

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "outcome": self.outcome,
            "recipient_id": self.recipient_id,
            "compiler_identity": self.compiler_identity,
            "tool_identity": self.tool_identity,
            "target_identity": self.target_identity,
            "evaluator_identity": self.evaluator_identity,
            "config_identity": self.config_identity,
            "scorer": self.scorer.to_dict() if self.scorer else None,
            "citations": [item.to_dict() for item in self.citations],
            "draft_landed": [item.to_dict() for item in self.draft_landed],
            "idiom": self.idiom.to_dict() if self.idiom else None,
            "first_divergence": (
                self.first_divergence.to_dict()
                if self.first_divergence is not None
                else None
            ),
            "support_identities": list(self.support_identities),
            "reason_code": self.reason_code,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, **self.identity_payload()}


def _make_corpus_evidence(
    *,
    kind: str,
    outcome: str,
    recipient_id: str | None = None,
    compiler_identity: str | None = None,
    tool_identity: str | None = None,
    target_identity: str | None = None,
    evaluator_identity: str | None = None,
    config_identity: str | None = None,
    scorer: ScorerTaxonomy | None = None,
    citations: Tuple[LessonCitation, ...] = (),
    draft_landed: Tuple[DraftLandedObservation, ...] = (),
    idiom: CompilerIdiomObservation | None = None,
    first_divergence: FirstDivergence | None = None,
    support_identities: Tuple[str, ...] = (),
    reason_code: str | None = None,
) -> CorpusEvidence:
    """Build one corpus record with its content-addressed evidence id."""

    evidence = CorpusEvidence(
        evidence_id="",
        kind=kind,
        outcome=outcome,
        recipient_id=recipient_id,
        compiler_identity=compiler_identity,
        tool_identity=tool_identity,
        target_identity=target_identity,
        evaluator_identity=evaluator_identity,
        config_identity=config_identity,
        scorer=scorer,
        citations=tuple(citations),
        draft_landed=tuple(draft_landed),
        idiom=idiom,
        first_divergence=first_divergence,
        support_identities=tuple(support_identities),
        reason_code=reason_code,
    )
    object.__setattr__(
        evidence, "evidence_id", hash_canonical(evidence.identity_payload())
    )
    return evidence


@dataclass(frozen=True)
class PromotionAccepted:
    """A proven compiler-bound improvement over one draft-landed pair."""

    observation: CompilerIdiomObservation
    evidence: CorpusEvidence


@dataclass(frozen=True)
class PromotionRefused:
    """A refused promotion retained as typed negative evidence."""

    receipt: EvidenceRefusalReceipt
    evidence: CorpusEvidence


def _score_vector(value: Any, label: str) -> ScoreVector:
    if isinstance(value, ScoreVector):
        return value
    try:
        return ScoreVector.from_dict(value)
    except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
        raise EvidenceIdentityMismatch(
            f"{label} is not a typed score vector"
        ) from exc


def _promotion_refusal(
    *,
    reason_code: str,
    pair: DraftLandedObservation,
    before: ScoreVector,
    after: ScoreVector,
    evaluator_identity: str,
    target_identity: str,
    scorer: ScorerTaxonomy | None,
) -> PromotionRefused:
    input_identities = tuple(
        identity
        for identity in (
            pair.pair_hash,
            target_identity,
            before.object_hash,
            after.object_hash,
        )
        if identity
    )
    receipt = EvidenceRefusalReceipt(
        receipt_id=hash_canonical(
            {
                "protocol": "sotn-evidence-refusal-v1",
                "operation": "promote_draft_landed",
                "reason_code": reason_code,
                "input_identities": list(input_identities),
                "observed_identities": [
                    before.compiler_identity,
                    after.compiler_identity,
                ],
                "new_generation_required": False,
            }
        ),
        operation="promote_draft_landed",
        reason_code=reason_code,
        input_identities=input_identities,
        observed_identities=(before.compiler_identity, after.compiler_identity),
        new_generation_required=False,
    )
    evidence = _make_corpus_evidence(
        kind="negative",
        outcome="negative",
        recipient_id=pair.recipient_id,
        compiler_identity=pair.compiler_identity,
        tool_identity=pair.tool_identity,
        target_identity=target_identity,
        evaluator_identity=evaluator_identity,
        config_identity=pair.config_identity,
        scorer=scorer,
        draft_landed=(pair,),
        first_divergence=before.first_divergence,
        support_identities=(pair.pair_hash,),
        reason_code=reason_code,
    )
    return PromotionRefused(receipt=receipt, evidence=evidence)


def promote_draft_landed(
    pair: DraftLandedObservation,
    before: ScoreVector,
    after: ScoreVector,
    *,
    evaluator_identity: str,
    target_identity: str,
    target_object_hash: str | None = None,
    target_checksum: str | None = None,
) -> PromotionAccepted | PromotionRefused:
    """Gate one draft-landed pair on a proven compiler-bound improvement.

    The pair's own compiler identity must bound both score vectors, the
    vectors must share one scorer boundary, and ``measure_improvement`` must
    prove a lower score or an exact target identity. Anything else is
    retained as typed negative evidence, never as an idiom.
    """

    if not isinstance(pair, DraftLandedObservation):
        raise EvidenceIdentityMismatch(
            "promotion needs a typed draft-landed observation"
        )
    try:
        validate_hash(evaluator_identity, "evaluator_identity")
        validate_hash(target_identity, "target_identity")
    except SearchValidationError as exc:
        raise EvidenceIdentityMismatch(str(exc)) from exc
    before = _score_vector(before, "before score")
    after = _score_vector(after, "after score")
    if (
        before.compiler_identity != pair.compiler_identity
        or after.compiler_identity != pair.compiler_identity
    ):
        return _promotion_refusal(
            reason_code="compiler_mismatch",
            pair=pair,
            before=before,
            after=after,
            evaluator_identity=evaluator_identity,
            target_identity=target_identity,
            scorer=None,
        )
    if before.scorer_algorithm != after.scorer_algorithm:
        return _promotion_refusal(
            reason_code="scorer_boundary_mismatch",
            pair=pair,
            before=before,
            after=after,
            evaluator_identity=evaluator_identity,
            target_identity=target_identity,
            scorer=None,
        )
    try:
        measurement = measure_improvement(
            before,
            after,
            target_object_hash=target_object_hash,
            target_checksum=target_checksum,
            evaluator_identity=evaluator_identity,
            evidence=pair.evidence,
        )
    except MeasurementError as exc:
        raise EvidenceIdentityMismatch(str(exc)) from exc
    if measurement is None:
        return _promotion_refusal(
            reason_code="no_measured_improvement",
            pair=pair,
            before=before,
            after=after,
            evaluator_identity=evaluator_identity,
            target_identity=target_identity,
            scorer=make_scorer_taxonomy(
                before,
                after,
                evaluator_identity=evaluator_identity,
                target_identity=target_identity,
            ),
        )
    measured_pair = replace(pair, measurement=measurement.to_dict())
    observation = make_idiom_observation(measured_pair)
    taxonomy = make_scorer_taxonomy(
        before,
        after,
        evaluator_identity=evaluator_identity,
        target_identity=target_identity,
    )
    support = tuple(
        identity
        for identity in (
            pair.pair_hash,
            target_object_hash,
            target_checksum,
            *measurement.evidence,
        )
        if identity
    )
    evidence = _make_corpus_evidence(
        kind="draft_landed",
        outcome="accepted",
        recipient_id=pair.recipient_id,
        compiler_identity=pair.compiler_identity,
        tool_identity=pair.tool_identity,
        target_identity=target_identity,
        evaluator_identity=evaluator_identity,
        config_identity=pair.config_identity,
        scorer=taxonomy,
        draft_landed=(measured_pair,),
        idiom=observation,
        support_identities=support,
    )
    return PromotionAccepted(observation=observation, evidence=evidence)


def collect_recurring_first_divergence(
    report: SearchPatternReport,
    contexts: Sequence[CompletedLineageContext | CompletedLineageDiagnostic],
    *,
    min_independent_lineages: int = 2,
) -> Tuple[CorpusEvidence, ...]:
    """Extract recurring divergence evidence the completed contexts support.

    A recommendation becomes corpus evidence only when every source ledger it
    cites was loaded as a completed lineage context, the contexts agree with
    the recommendation's exact identity tuple, and at least two independent
    lineages contributed. A diagnostic ledger refuses the recommendation as
    typed evidence with incomplete provenance instead of fabricating a
    promotion-grade hypothesis.
    """

    if not isinstance(report, SearchPatternReport):
        raise EvidenceIdentityMismatch(
            "recurrence mining needs a typed search pattern report"
        )
    if isinstance(min_independent_lineages, bool) or not isinstance(
        min_independent_lineages, int
    ) or min_independent_lineages < 2:
        raise EvidenceIdentityMismatch(
            "min_independent_lineages must be at least two"
        )
    by_ledger: dict[str, CompletedLineageContext | CompletedLineageDiagnostic] = {}
    for context in contexts:
        if not isinstance(
            context, (CompletedLineageContext, CompletedLineageDiagnostic)
        ):
            raise EvidenceIdentityMismatch(
                "lineage contexts must be the typed context or diagnostic records"
            )
        by_ledger[context.ledger_identity] = context
    entries: list[CorpusEvidence] = []
    for recommendation in report.recommendations:
        divergence_raw = recommendation.get("first_divergence")
        if not divergence_raw:
            continue
        divergence = FirstDivergence.from_dict(divergence_raw)
        source_ledgers = tuple(recommendation.get("source_ledgers", ()))
        lineage_ids = tuple(recommendation.get("lineage_ids", ()))
        common: dict[str, Any] = {
            "recipient_id": recommendation.get("recipient_id"),
            "compiler_identity": recommendation.get("compiler_identity"),
            "tool_identity": recommendation.get("lane_tool_identity"),
            "target_identity": recommendation.get("target_identity"),
            "config_identity": recommendation.get("config_identity"),
            "first_divergence": divergence,
        }

        def _entry(
            *, outcome: str, reason_code: str | None, evaluator_identity: str | None
        ) -> CorpusEvidence:
            return _make_corpus_evidence(
                kind="first_divergence",
                outcome=outcome,
                evaluator_identity=evaluator_identity,
                support_identities=tuple(sorted(set(source_ledgers))),
                reason_code=reason_code,
                **common,
            )

        if any(ledger not in by_ledger for ledger in source_ledgers):
            entries.append(
                _entry(
                    outcome="refused",
                    reason_code="missing_lineage_context",
                    evaluator_identity=None,
                )
            )
            continue
        diagnostics = [
            by_ledger[ledger]
            for ledger in source_ledgers
            if isinstance(by_ledger[ledger], CompletedLineageDiagnostic)
        ]
        if diagnostics:
            entries.append(
                _entry(
                    outcome="refused",
                    reason_code=diagnostics[0].reason_code,
                    evaluator_identity=None,
                )
            )
            continue
        contexts_for = [by_ledger[ledger] for ledger in source_ledgers]
        incompatible = False
        for context in contexts_for:
            assert isinstance(context, CompletedLineageContext)
            context_tool_identities = {
                tool for _lane, tool in context.lane_tool_identities
            }
            context_target_pairs = set(context.recipient_target_identities)
            if (
                context.compiler_identity != recommendation.get("compiler_identity")
                or context.config_identity != recommendation.get("config_identity")
                or context.schema_identity != recommendation.get("schema_identity")
                or recommendation.get("scorer_algorithm")
                not in context.scorer_algorithms
                or recommendation.get("lane_tool_identity")
                not in context_tool_identities
                or (
                    recommendation.get("recipient_id"),
                    recommendation.get("target_identity"),
                )
                not in context_target_pairs
                or context.evaluator_identity != recommendation.get("evaluator_identity")
            ):
                incompatible = True
                break
        if incompatible:
            entries.append(
                _entry(
                    outcome="refused",
                    reason_code="incompatible_lineage_context",
                    evaluator_identity=recommendation.get("evaluator_identity"),
                )
            )
            continue
        if len(set(source_ledgers)) < 2 or len(set(lineage_ids)) < min_independent_lineages:
            continue
        # The report artifact identity is bound into the support set so a
        # recommendation can only support evidence through the verified
        # report that carried it.
        support = tuple(
            sorted(
                set(source_ledgers) | set(lineage_ids) | {report.artifact.content_hash}
            )
        )
        entries.append(
            _make_corpus_evidence(
                kind="first_divergence",
                outcome="positive",
                evaluator_identity=recommendation.get("evaluator_identity"),
                support_identities=support,
                reason_code=None,
                **common,
            )
        )
    return tuple(entries)


__all__ = [
    "CORPUS_GENERATION_PROTOCOL",
    "AbsenceMaskingClaim",
    "CorpusEvidence",
    "CorpusGeneration",
    "EvidenceCorpusError",
    "EvidenceIdentityMismatch",
    "EvidenceRefusalReceipt",
    "LessonCitation",
    "LessonCitationError",
    "PromotionAccepted",
    "PromotionRefused",
    "ScorerTaxonomy",
    "build_corpus_generation",
    "canonical_json",
    "collect_recurring_first_divergence",
    "make_lesson_citation",
    "make_scorer_taxonomy",
    "promote_draft_landed",
    "scorer_taxonomy_identity_payload",
    "verify_lesson_citation",
]
