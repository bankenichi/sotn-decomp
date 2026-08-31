"""Canonical, reproducible evidence corpus for instrumented search.

Every publication begins at the Task 8.2 integration boundary: this module
imports the supervisor's ``IntegrationGateReceipt`` and
``IntegrationGateError``, validates the archived run once before reading
evidence, and retains that complete proof in the resulting generation. It then
provides typed lesson citations, scorer taxonomy, draft-landed promotion and
refusal records, recurring first-divergence evidence, and content-addressed
``CorpusEvidence`` and ``CorpusGeneration`` replay boundaries. Refusals remain
self-contained evidence, and required support identities are derived and
checked mechanically rather than trusted as caller-maintained notes.

No local gate type, wrapper validator, or recovery wrapper is defined here.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Sequence, Set, Tuple

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
        PatternInputError,
        PatternArtifactError,
        SearchPatternReport,
        load_report_artifact,
        validate_search_recommendation,
    )
    from .search_supervisor import (
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from .search_types import (
        FirstDivergence,
        GroupedPatch,
        LANES,
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
        PatternInputError,
        PatternArtifactError,
        SearchPatternReport,
        load_report_artifact,
        validate_search_recommendation,
    )
    from automation.search_supervisor import (  # type: ignore
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from automation.search_types import (  # type: ignore
        FirstDivergence,
        GroupedPatch,
        LANES,
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
CORPUS_EVIDENCE_PROTOCOL = "sotn-corpus-evidence-v1"


class EvidenceCorpusError(RuntimeError):
    """Base error for corpus and shadow input failures."""


class LessonCitationError(EvidenceCorpusError):
    """A lesson source hash or review span does not verify."""


class EvidenceIdentityMismatch(EvidenceCorpusError):
    """A corpus input identity disagrees with its immutable content."""


def _corpus_sequence(value: Any, label: str) -> Tuple[Any, ...]:
    """Require one explicit JSON array shape at a corpus boundary."""

    if not isinstance(value, (tuple, list)):
        raise SearchValidationError(f"{label} must be an array")
    try:
        return tuple(value)
    except (TypeError, ValueError) as exc:
        raise SearchValidationError(f"{label} must be an array") from exc


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
    entries: Tuple["CorpusEvidence", ...]
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
            lanes = _corpus_sequence(
                self.selected_lanes, "corpus generation selected lanes"
            )
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch(
                "corpus generation selected lanes are invalid"
            ) from exc
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
            source_identities = _corpus_sequence(
                self.source_identities, "corpus source identities"
            )
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch(
                "corpus source identities are invalid"
            ) from exc
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

        # The durable in-memory generation keeps the validated type boundary:
        # entries are canonical sorted CorpusEvidence records, never raw
        # mappings. Each record revalidated its own content address at its
        # own construction, including through from_dict and replace().
        try:
            raw_entries = _corpus_sequence(
                self.entries, "corpus generation entries"
            )
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch(str(exc)) from exc
        for entry in raw_entries:
            if not isinstance(entry, CorpusEvidence):
                raise EvidenceIdentityMismatch(
                    "corpus generation entries must be typed evidence records"
                )
        entry_ids = [entry.evidence_id for entry in raw_entries]
        if len(set(entry_ids)) != len(entry_ids):
            raise EvidenceIdentityMismatch("corpus evidence IDs must be unique")
        ordered_entries = tuple(
            entry
            for _identity, entry in sorted(
                zip(entry_ids, raw_entries), key=lambda item: item[0]
            )
        )
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
        if not isinstance(data["entries"], (list, tuple)):
            raise EvidenceIdentityMismatch(
                "corpus generation entries must be an array"
            )
        try:
            data["integration_gate"] = IntegrationGateReceipt.from_dict(
                data["integration_gate"]
            )
            data["artifact"] = ArtifactRef.from_dict(data["artifact"])
            data["entries"] = tuple(
                CorpusEvidence.from_dict(item) for item in data["entries"]
            )
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
            "entries": [entry.to_dict() for entry in self.entries],
            "artifact": self.artifact.to_dict(),
        }


def _corpus_generation_payload(
    *,
    schema_identity: str,
    integration_gate: IntegrationGateReceipt,
    source_identities: Sequence[str],
    entries: Sequence["CorpusEvidence"],
) -> dict[str, Any]:
    """Return the one canonical payload used by build and direct validation.

    Entries serialize at this boundary: the durable payload and replay both
    see the same typed-record dictionaries.
    """

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
        "entries": [entry.to_dict() for entry in entries],
    }


_ENTRY_OUTCOMES = {
    "draft_landed": ("accepted",),
    "first_divergence": ("positive", "refused"),
    "lesson": ("accepted",),
    "scorer": ("accepted",),
    "negative": ("negative",),
}


_CORPUS_VARIANT_FIELDS = (
    "recipient_id",
    "compiler_identity",
    "tool_identity",
    "target_identity",
    "evaluator_identity",
    "config_identity",
    "lane",
    "schema_identity",
    "scorer_algorithm",
    "pattern_id",
    "scorer",
    "citations",
    "draft_landed",
    "idiom",
    "first_divergence",
    "refusal_receipt",
    "reason_code",
)

# The factories emit a closed set of discriminated shapes.  Keeping this
# table explicit prevents a self-consistent hybrid record, such as a lesson
# carrying scorer and divergence payloads, from acquiring a durable identity.
_CORPUS_VARIANTS = {
    ("draft_landed", "accepted"): {
        "allowed": frozenset(
            {
                "recipient_id",
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "evaluator_identity",
                "config_identity",
                "scorer",
                "draft_landed",
                "idiom",
            }
        ),
        "required": frozenset(
            {
                "recipient_id",
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "evaluator_identity",
                "config_identity",
                "scorer",
                "draft_landed",
                "idiom",
            }
        ),
    },
    ("negative", "negative"): {
        "allowed": frozenset(
            {
                "recipient_id",
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "evaluator_identity",
                "config_identity",
                "scorer",
                "draft_landed",
                "first_divergence",
                "refusal_receipt",
                "reason_code",
            }
        ),
        "required": frozenset(
            {
                "recipient_id",
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "evaluator_identity",
                "config_identity",
                "draft_landed",
                "refusal_receipt",
                "reason_code",
            }
        ),
    },
    ("first_divergence", "positive"): {
        "allowed": frozenset(
            {
                "recipient_id",
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "evaluator_identity",
                "config_identity",
                "lane",
                "schema_identity",
                "scorer_algorithm",
                "pattern_id",
                "first_divergence",
            }
        ),
        "required": frozenset(
            {
                "recipient_id",
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "evaluator_identity",
                "config_identity",
                "lane",
                "schema_identity",
                "scorer_algorithm",
                "pattern_id",
                "first_divergence",
            }
        ),
    },
    ("first_divergence", "refused"): {
        "allowed": frozenset(
            {
                "recipient_id",
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "evaluator_identity",
                "config_identity",
                "lane",
                "schema_identity",
                "scorer_algorithm",
                "pattern_id",
                "first_divergence",
                "refusal_receipt",
                "reason_code",
            }
        ),
        "required": frozenset(
            {
                "recipient_id",
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "config_identity",
                "lane",
                "schema_identity",
                "scorer_algorithm",
                "pattern_id",
                "first_divergence",
                "refusal_receipt",
                "reason_code",
            }
        ),
    },
    ("lesson", "accepted"): {
        "allowed": frozenset({"citations"}),
        "required": frozenset({"citations"}),
    },
    ("scorer", "accepted"): {
        "allowed": frozenset(
            {
                "compiler_identity",
                "evaluator_identity",
                "target_identity",
                "scorer",
            }
        ),
        "required": frozenset(
            {"compiler_identity", "evaluator_identity", "target_identity", "scorer"}
        ),
    },
}


def _corpus_field_present(value: Any) -> bool:
    """Return whether a discriminated payload field carries a variant."""

    if value is None:
        return False
    if isinstance(value, (str, bytes, bytearray)):
        return bool(value)
    if isinstance(value, (Mapping, list, tuple, set, frozenset)):
        return bool(value)
    return True


def _validate_corpus_entry_shape(entry: Mapping[str, Any]) -> None:
    """Reject entries whose fields contradict their exact kind and outcome."""

    kind = entry.get("kind")
    outcome = entry.get("outcome")
    variant = _CORPUS_VARIANTS.get((kind, outcome))
    if variant is None:
        raise EvidenceIdentityMismatch(
            f"corpus entry kind/outcome is not a production variant: {kind!r}/{outcome!r}"
        )
    allowed = variant["allowed"]
    required = variant["required"]
    contradictory = [
        name
        for name in _CORPUS_VARIANT_FIELDS
        if name not in allowed and _corpus_field_present(entry.get(name))
    ]
    if contradictory:
        raise EvidenceIdentityMismatch(
            "corpus "
            + kind
            + "/"
            + outcome
            + " entry carries unrelated fields: "
            + ", ".join(contradictory)
        )
    missing = [
        name
        for name in required
        if not _corpus_field_present(entry.get(name))
    ]
    if missing:
        raise EvidenceIdentityMismatch(
            "corpus "
            + kind
            + "/"
            + outcome
            + " entry is missing required fields: "
            + ", ".join(sorted(missing))
        )
    if kind in {"draft_landed", "negative"}:
        pairs = entry.get("draft_landed")
        if not isinstance(pairs, (tuple, list)) or len(pairs) != 1:
            raise EvidenceIdentityMismatch(
                "a " + kind + " entry must carry exactly one draft-landed pair"
            )
    if kind == "lesson":
        citations = entry.get("citations")
        if not isinstance(citations, (tuple, list)) or len(citations) != 1:
            raise EvidenceIdentityMismatch(
                "a lesson entry must carry exactly one lesson citation"
            )
    if kind == "scorer":
        scorers = entry.get("scorer")
        if not isinstance(scorers, Mapping):
            raise EvidenceIdentityMismatch("a scorer entry must carry its taxonomy")
    # Acceptance and refusal are mutually exclusive dispositions: a positive
    # record cannot carry a refusal reason or receipt, and a refused or
    # negative record must carry the typed refusal receipt whose reason it
    # names and can never claim an idiom as if it had been promoted.
    reason_code = entry.get("reason_code")
    if outcome in ("accepted", "positive"):
        if reason_code is not None:
            raise EvidenceIdentityMismatch(
                "an accepted or positive corpus entry cannot carry a refusal reason"
            )
        if entry.get("refusal_receipt") is not None:
            raise EvidenceIdentityMismatch(
                "an accepted or positive corpus entry cannot carry a refusal receipt"
            )
    if outcome in ("negative", "refused"):
        receipt = entry.get("refusal_receipt")
        if not isinstance(receipt, Mapping) or not receipt.get("receipt_id"):
            raise EvidenceIdentityMismatch(
                "a negative or refused corpus entry must carry its refusal receipt"
            )
        if receipt.get("reason_code") != reason_code:
            raise EvidenceIdentityMismatch(
                "corpus refusal reason differs from its refusal receipt"
            )
        if not reason_code:
            raise EvidenceIdentityMismatch(
                "a negative or refused corpus entry must name its reason"
            )


def build_corpus_generation(
    entries: Iterable["CorpusEvidence"],
    *,
    integration_gate: IntegrationGateReceipt,
    schema_identity: str,
    archive: ContentAddressedArchive,
) -> CorpusGeneration:
    """Publish one corpus generation bound to a validated integration receipt.

    The canonical Task 8.2 validator decides whether the receipt is missing,
    changed or otherwise invalid, and is called exactly once, before any
    entry is read. Entries must be typed corpus evidence; the generation's
    source set is derived mechanically from each entry's declared support
    plus the identities its nested records are required to carry, so a
    caller-maintained partial list can no longer hide nested provenance.
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
    try:
        entry_values = tuple(entries)
    except (TypeError, ValueError) as exc:
        raise EvidenceIdentityMismatch(
            "corpus entries must be an iterable of typed evidence records"
        ) from exc
    typed_entries: list[CorpusEvidence] = []
    entry_ids: list[str] = []
    derived_sources: Set[str] = set()
    for entry in entry_values:
        if not isinstance(entry, CorpusEvidence):
            raise EvidenceIdentityMismatch(
                "corpus evidence must be typed records; build evidence through "
                "the typed factories before publication"
            )
        typed_entries.append(entry)
        entry_ids.append(entry.evidence_id)
        # Hash identities feed the generation's source set; lineage labels
        # stay provenance on their own entries. The required-support
        # derivation contributes nested identities (citation sources, spans,
        # taxonomy, pairs, idioms, receipts, pattern references) even when a
        # caller forgot to repeat them in the hand-maintained support list.
        for identity in (
            set(entry.support_identities) | _required_support_identities(entry)
        ):
            if identity.startswith("sha256:"):
                derived_sources.add(identity)
    if len(set(entry_ids)) != len(entry_ids):
        raise EvidenceIdentityMismatch("corpus evidence IDs must be unique")
    ordered_entries = tuple(
        entry
        for _identity, entry in sorted(
            zip(entry_ids, typed_entries), key=lambda item: item[0]
        )
    )
    source_identities: tuple[str, ...] = tuple(sorted(derived_sources))
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
        try:
            inputs = _corpus_sequence(
                self.input_identities, "refusal input identities"
            )
            observed = _corpus_sequence(
                self.observed_identities, "refusal observed identities"
            )
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch(str(exc)) from exc
        for name, values in (("input", inputs), ("observed", observed)):
            for value in values:
                if not isinstance(value, str) or not value:
                    raise EvidenceIdentityMismatch(
                        f"refusal {name} identities must be nonempty strings"
                    )
        # These are set-like identity collections. Canonicalizing them here
        # means permutations and duplicate observations cannot mint distinct
        # refusal identities for the same operation.
        inputs = tuple(sorted(set(inputs)))
        observed = tuple(sorted(set(observed)))
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

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceRefusalReceipt":
        fields = (
            "receipt_id",
            "operation",
            "reason_code",
            "input_identities",
            "observed_identities",
            "new_generation_required",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise EvidenceIdentityMismatch(
                "refusal receipt fields do not match its protocol"
            )
        try:
            flag = value["new_generation_required"]
            if not isinstance(flag, bool):
                raise TypeError("new_generation_required must be a boolean")
            return cls(
                receipt_id=value["receipt_id"],
                operation=value["operation"],
                reason_code=value["reason_code"],
                input_identities=value["input_identities"],
                observed_identities=value["observed_identities"],
                new_generation_required=flag,
            )
        except EvidenceIdentityMismatch:
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch(
                "refusal receipt payload is invalid: " + str(exc)
            ) from exc


def _evidence_identity_payload(
    *,
    kind: str,
    outcome: str,
    recipient_id: str | None,
    compiler_identity: str | None,
    tool_identity: str | None,
    target_identity: str | None,
    evaluator_identity: str | None,
    config_identity: str | None,
    lane: str | None,
    schema_identity: str | None,
    scorer_algorithm: str | None,
    pattern_id: str | None,
    scorer: "ScorerTaxonomy | None",
    citations: Tuple[LessonCitation, ...],
    draft_landed: Tuple[DraftLandedObservation, ...],
    idiom: "CompilerIdiomObservation | None",
    first_divergence: FirstDivergence | None,
    refusal_receipt: "EvidenceRefusalReceipt | None",
    support_identities: Tuple[str, ...],
    reason_code: str | None,
) -> dict[str, Any]:
    """Return the one canonical evidence identity payload.

    Both the factory and the record's own ``identity_payload`` build the
    payload through this function, so the content address cannot drift
    between construction paths. Support identities are canonicalized here as
    a sorted unique set: caller order can never create a second identity.
    """

    return {
        "protocol": CORPUS_EVIDENCE_PROTOCOL,
        "kind": kind,
        "outcome": outcome,
        "recipient_id": recipient_id,
        "compiler_identity": compiler_identity,
        "tool_identity": tool_identity,
        "target_identity": target_identity,
        "evaluator_identity": evaluator_identity,
        "config_identity": config_identity,
        "lane": lane,
        "schema_identity": schema_identity,
        "scorer_algorithm": scorer_algorithm,
        "pattern_id": pattern_id,
        "scorer": scorer.to_dict() if scorer else None,
        "citations": [item.to_dict() for item in citations],
        "draft_landed": [item.to_dict() for item in draft_landed],
        "idiom": idiom.to_dict() if idiom else None,
        "first_divergence": (
            first_divergence.to_dict() if first_divergence is not None else None
        ),
        "refusal_receipt": (
            refusal_receipt.to_dict() if refusal_receipt is not None else None
        ),
        "support_identities": sorted(set(support_identities)),
        "reason_code": reason_code,
    }


def _required_support_identities(evidence: "CorpusEvidence") -> Set[str]:
    """Mechanically derive the identities the record's payload carries.

    One derivation serves direct-evidence validation and the generation's
    source derivation: a nested citation, scorer taxonomy, draft-landed pair,
    idiom observation, refusal receipt, or pattern reference contributes its
    immutable identity whether or not the caller remembered to repeat it in
    the hand-maintained support list. Validation refuses when a required
    identity is missing; the generation derivation additionally unions this
    set with the declared support so no nested identity is silently omitted.
    """

    required: Set[str] = set()
    for citation in evidence.citations:
        required.add(citation.source.content_hash)
        required.add(citation.span_identity)
    if evidence.scorer is not None:
        required.add(evidence.scorer.taxonomy_id)
        # The taxonomy id binds the vectors, but the vectors' own immutable
        # object, mismatch and diagnostic artifacts are also evidence that a
        # generation consumer must be able to reconstruct.  Require every
        # identity carried by either nested score vector at this boundary.
        for vector in (evidence.scorer.before, evidence.scorer.after):
            for identity in (vector.object_hash, vector.mismatch_signature):
                if identity:
                    required.add(identity)
            if vector.diagnostic_artifact is not None:
                required.add(vector.diagnostic_artifact.content_hash)
    for pair in evidence.draft_landed:
        required.add(pair.pair_hash)
        measured = (pair.measurement or {}).get("evidence")
        if isinstance(measured, str) or (
            measured is not None and not isinstance(measured, (tuple, list))
        ):
            raise SearchValidationError(
                "draft-landed measurement evidence must be a sequence of identities"
            )
        if measured:
            for identity in measured:
                if isinstance(identity, str) and identity:
                    required.add(identity)
    if evidence.idiom is not None:
        required.add(evidence.idiom.observation_id)
    if evidence.refusal_receipt is not None:
        required.add(evidence.refusal_receipt.receipt_id)
    if evidence.pattern_id:
        required.add(evidence.pattern_id)
    return required


def _citation_from_dict(value: Any) -> LessonCitation:
    if not isinstance(value, Mapping):
        raise EvidenceIdentityMismatch("a lesson citation must be an object")
    try:
        masking = value["absence_masking"]
        return LessonCitation(
            citation_id=value["citation_id"],
            source=ArtifactRef.from_dict(value["source"]),
            section=value["section"],
            line_start=value["line_start"],
            line_end=value["line_end"],
            span_identity=value["span_identity"],
            rule_id=value["rule_id"],
            absence_masking=(
                AbsenceMaskingClaim(
                    masking["opcode"], tuple(masking["masks"]), masking["scope"]
                )
                if masking is not None
                else None
            ),
        )
    except EvidenceIdentityMismatch:
        raise
    except (
        AttributeError,
        SearchValidationError,
        TypeError,
        ValueError,
        KeyError,
    ) as exc:
        raise EvidenceIdentityMismatch(
            "lesson citation payload is invalid: " + str(exc)
        ) from exc


def _draft_landed_from_dict(value: Any) -> DraftLandedObservation:
    if not isinstance(value, Mapping):
        raise EvidenceIdentityMismatch("a draft-landed entry must be an object")
    try:
        return DraftLandedObservation(
            recipient_id=value["recipient_id"],
            draft=ArtifactRef.from_dict(value["draft"]),
            landed=ArtifactRef.from_dict(value["landed"]),
            landing_commit=value["landing_commit"],
            compiler_identity=value["compiler_identity"],
            grouped_patches=tuple(
                GroupedPatch.from_dict(item) for item in value["grouped_patches"]
            ),
            evidence=tuple(value["evidence"]),
            draft_commit=value["draft_commit"],
            draft_ref=value["draft_ref"],
            landing_ref=value["landing_ref"],
            tool_identity=value["tool_identity"],
            config_identity=value["config_identity"],
            measurement=dict(value["measurement"] or {}),
        )
    except EvidenceIdentityMismatch:
        raise
    except (
        AttributeError,
        SearchValidationError,
        TypeError,
        ValueError,
        KeyError,
    ) as exc:
        raise EvidenceIdentityMismatch(
            "draft-landed payload is invalid: " + str(exc)
        ) from exc


@dataclass(frozen=True)
class CorpusEvidence:
    """One corpus record: a promotion, a recurrence, or negative evidence.

    Genuinely content-addressed: ``evidence_id`` is the canonical hash of the
    complete typed payload under the fixed ``sotn-corpus-evidence-v1``
    protocol namespace, recomputed and enforced on every construction path,
    including direct construction. Every nested record is stored typed; raw
    mappings are refused at this boundary. A refused or negative record must
    embed the typed refusal receipt whose reason it names, and its support
    set must contain every identity its nested records mechanically carry.
    """

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
    lane: str | None = None
    schema_identity: str | None = None
    scorer_algorithm: str | None = None
    pattern_id: str | None = None
    refusal_receipt: EvidenceRefusalReceipt | None = None

    def __post_init__(self) -> None:
        try:
            if not isinstance(self.kind, str) or not self.kind:
                raise SearchValidationError("corpus kind must be a nonempty string")
            if self.outcome not in _ENTRY_OUTCOMES.get(self.kind, ()):
                raise SearchValidationError(
                    f"corpus outcome {self.outcome!r} is not valid for kind {self.kind!r}"
                )
            if self.recipient_id is not None and (
                not isinstance(self.recipient_id, str) or not self.recipient_id
            ):
                raise SearchValidationError(
                    "corpus recipient id must be a nonempty string or null"
                )
            for name in (
                "compiler_identity",
                "tool_identity",
                "target_identity",
                "evaluator_identity",
                "config_identity",
                "schema_identity",
                "pattern_id",
            ):
                value = getattr(self, name)
                if value is not None:
                    validate_hash(value, name)
            if self.lane is not None and (
                not isinstance(self.lane, str) or self.lane not in LANES
            ):
                raise SearchValidationError(
                    "corpus lane must be a known lane or null"
                )
            if self.scorer_algorithm is not None and (
                not isinstance(self.scorer_algorithm, str)
                or not self.scorer_algorithm
            ):
                raise SearchValidationError(
                    "corpus scorer algorithm must be a nonempty string or null"
                )
            if not isinstance(self.scorer, (ScorerTaxonomy, type(None))):
                raise SearchValidationError("corpus scorer must be typed or null")
            citations = _corpus_sequence(self.citations, "corpus citations")
            for citation in citations:
                if not isinstance(citation, LessonCitation):
                    raise SearchValidationError(
                        "corpus citations must be typed lesson citations"
                    )
            pairs = _corpus_sequence(
                self.draft_landed, "corpus draft-landed observations"
            )
            for pair in pairs:
                if not isinstance(pair, DraftLandedObservation):
                    raise SearchValidationError(
                        "corpus draft-landed entries must be typed observations"
                    )
            if self.idiom is not None and not isinstance(
                self.idiom, CompilerIdiomObservation
            ):
                raise SearchValidationError("corpus idiom must be typed or null")
            divergence = self.first_divergence
            if divergence is not None and not isinstance(
                divergence, FirstDivergence
            ):
                raise SearchValidationError(
                    "corpus first divergence must be typed or null"
                )
            receipt = self.refusal_receipt
            if receipt is not None and not isinstance(
                receipt, EvidenceRefusalReceipt
            ):
                raise SearchValidationError(
                    "corpus refusal receipt must be typed or null"
                )
            # Cross-validate identities the nested records also carry: a
            # record must not state one identity and embed another.
            if self.scorer is not None:
                if (
                    self.evaluator_identity is not None
                    and self.evaluator_identity != self.scorer.evaluator_identity
                ) or (
                    self.target_identity is not None
                    and self.target_identity != self.scorer.target_identity
                ):
                    raise SearchValidationError(
                        "corpus scorer taxonomy identities differ from the record"
                    )
            for pair in pairs:
                if (
                    pair.recipient_id != self.recipient_id
                    or pair.compiler_identity != self.compiler_identity
                ):
                    raise SearchValidationError(
                        "corpus draft-landed pair identities differ from the record"
                    )
                if (pair.tool_identity or None) != (self.tool_identity or None) or (
                    (pair.config_identity or None)
                    != (self.config_identity or None)
                ):
                    raise SearchValidationError(
                        "corpus draft-landed pair provenance differs from the record"
                    )
            if self.idiom is not None:
                if self.idiom.compiler_identity != self.compiler_identity or (
                    (self.idiom.tool_identity or None)
                    != (self.tool_identity or None)
                    or (self.idiom.config_identity or None)
                    != (self.config_identity or None)
                ):
                    raise SearchValidationError(
                        "corpus idiom provenance differs from the record"
                    )
            if receipt is not None and receipt.reason_code != self.reason_code:
                raise SearchValidationError(
                    "corpus refusal reason differs from its refusal receipt"
                )
            if self.reason_code is not None and (
                not isinstance(self.reason_code, str) or not self.reason_code
            ):
                raise SearchValidationError(
                    "corpus reason code must be a nonempty string or null"
                )
            if not isinstance(self.support_identities, (tuple, list)):
                raise SearchValidationError(
                    "corpus support identities must be a sequence of strings"
                )
            raw_supports = _corpus_sequence(
                self.support_identities, "corpus support identities"
            )
            for item in raw_supports:
                if not isinstance(item, str) or not item:
                    raise SearchValidationError(
                        "corpus support identities must be nonempty strings"
                    )
            # Set-like support is canonicalized, not trusted: input order
            # cannot create a second evidence identity.
            supports = tuple(sorted(set(raw_supports)))
            object.__setattr__(self, "citations", citations)
            object.__setattr__(self, "draft_landed", pairs)
            object.__setattr__(self, "support_identities", supports)
            required = _required_support_identities(self)
            missing = sorted(required - set(supports))
            if missing:
                raise SearchValidationError(
                    "corpus evidence support is missing required identities: "
                    + ", ".join(missing)
                )
            _validate_corpus_entry_shape(self.identity_payload())
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch(str(exc)) from exc
        expected_id = hash_canonical(self.identity_payload())
        if self.evidence_id != expected_id:
            raise EvidenceIdentityMismatch(
                "corpus evidence_id does not match the exact evidence payload"
            )

    def identity_payload(self) -> dict[str, Any]:
        return _evidence_identity_payload(
            kind=self.kind,
            outcome=self.outcome,
            recipient_id=self.recipient_id,
            compiler_identity=self.compiler_identity,
            tool_identity=self.tool_identity,
            target_identity=self.target_identity,
            evaluator_identity=self.evaluator_identity,
            config_identity=self.config_identity,
            lane=self.lane,
            schema_identity=self.schema_identity,
            scorer_algorithm=self.scorer_algorithm,
            pattern_id=self.pattern_id,
            scorer=self.scorer,
            citations=self.citations,
            draft_landed=self.draft_landed,
            idiom=self.idiom,
            first_divergence=self.first_divergence,
            refusal_receipt=self.refusal_receipt,
            support_identities=self.support_identities,
            reason_code=self.reason_code,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CorpusEvidence":
        fields = (
            "protocol",
            "evidence_id",
            "kind",
            "outcome",
            "recipient_id",
            "compiler_identity",
            "tool_identity",
            "target_identity",
            "evaluator_identity",
            "config_identity",
            "lane",
            "schema_identity",
            "scorer_algorithm",
            "pattern_id",
            "scorer",
            "citations",
            "draft_landed",
            "idiom",
            "first_divergence",
            "refusal_receipt",
            "support_identities",
            "reason_code",
        )
        if not isinstance(value, Mapping) or set(value) != set(fields):
            raise EvidenceIdentityMismatch(
                "corpus evidence fields do not match its protocol"
            )
        if value["protocol"] != CORPUS_EVIDENCE_PROTOCOL:
            raise EvidenceIdentityMismatch(
                "unsupported corpus evidence protocol: " + str(value["protocol"])
            )
        for name in ("citations", "draft_landed", "support_identities"):
            if not isinstance(value[name], (list, tuple)):
                raise EvidenceIdentityMismatch(
                    f"corpus evidence {name} must be an array"
                )
        try:
            scorer = (
                ScorerTaxonomy.from_dict(value["scorer"])
                if value["scorer"] is not None
                else None
            )
            citations = tuple(
                _citation_from_dict(item) for item in value["citations"]
            )
            draft_landed = tuple(
                _draft_landed_from_dict(item)
                for item in value["draft_landed"]
            )
            idiom = (
                CompilerIdiomObservation.from_dict(value["idiom"])
                if value["idiom"] is not None
                else None
            )
            divergence = (
                FirstDivergence.from_dict(value["first_divergence"])
                if value["first_divergence"] is not None
                else None
            )
            receipt = (
                EvidenceRefusalReceipt.from_dict(value["refusal_receipt"])
                if value["refusal_receipt"] is not None
                else None
            )
            return cls(
                evidence_id=value["evidence_id"],
                kind=value["kind"],
                outcome=value["outcome"],
                recipient_id=value["recipient_id"],
                compiler_identity=value["compiler_identity"],
                tool_identity=value["tool_identity"],
                target_identity=value["target_identity"],
                evaluator_identity=value["evaluator_identity"],
                config_identity=value["config_identity"],
                lane=value["lane"],
                schema_identity=value["schema_identity"],
                scorer_algorithm=value["scorer_algorithm"],
                pattern_id=value["pattern_id"],
                scorer=scorer,
                citations=citations,
                draft_landed=draft_landed,
                idiom=idiom,
                first_divergence=divergence,
                refusal_receipt=receipt,
                support_identities=value["support_identities"],
                reason_code=value["reason_code"],
            )
        except EvidenceIdentityMismatch:
            raise
        except (
            AttributeError,
            SearchValidationError,
            TypeError,
            ValueError,
            KeyError,
        ) as exc:
            raise EvidenceIdentityMismatch(
                "corpus evidence payload is invalid: " + str(exc)
            ) from exc


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
    lane: str | None = None,
    schema_identity: str | None = None,
    scorer_algorithm: str | None = None,
    pattern_id: str | None = None,
    refusal_receipt: EvidenceRefusalReceipt | None = None,
) -> CorpusEvidence:
    """Build one corpus record with its content-addressed evidence id.

    The id is computed from the same shared payload builder the record's own
    ``identity_payload`` uses, then re-verified by the constructor: there is
    no blank-id plus ``object.__setattr__`` window in which an unaddressed
    record can escape.
    """

    try:
        citation_values = _corpus_sequence(citations, "corpus citations")
        pair_values = _corpus_sequence(
            draft_landed, "corpus draft-landed observations"
        )
        support_values = _corpus_sequence(
            support_identities, "corpus support identities"
        )
    except SearchValidationError as exc:
        raise EvidenceIdentityMismatch(str(exc)) from exc
    payload = _evidence_identity_payload(
        kind=kind,
        outcome=outcome,
        recipient_id=recipient_id,
        compiler_identity=compiler_identity,
        tool_identity=tool_identity,
        target_identity=target_identity,
        evaluator_identity=evaluator_identity,
        config_identity=config_identity,
        lane=lane,
        schema_identity=schema_identity,
        scorer_algorithm=scorer_algorithm,
        pattern_id=pattern_id,
        scorer=scorer,
        citations=citation_values,
        draft_landed=pair_values,
        idiom=idiom,
        first_divergence=first_divergence,
        refusal_receipt=refusal_receipt,
        support_identities=support_values,
        reason_code=reason_code,
    )
    return CorpusEvidence(
        evidence_id=hash_canonical(payload),
        kind=kind,
        outcome=outcome,
        recipient_id=recipient_id,
        compiler_identity=compiler_identity,
        tool_identity=tool_identity,
        target_identity=target_identity,
        evaluator_identity=evaluator_identity,
        config_identity=config_identity,
        scorer=scorer,
        citations=citation_values,
        draft_landed=pair_values,
        idiom=idiom,
        first_divergence=first_divergence,
        support_identities=support_values,
        reason_code=reason_code,
        lane=lane,
        schema_identity=schema_identity,
        scorer_algorithm=scorer_algorithm,
        pattern_id=pattern_id,
        refusal_receipt=refusal_receipt,
    )


@dataclass(frozen=True)
class PromotionAccepted:
    """A proven compiler-bound improvement over one draft-landed pair."""

    observation: CompilerIdiomObservation
    evidence: CorpusEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.observation, CompilerIdiomObservation):
            raise EvidenceIdentityMismatch(
                "an accepted promotion needs a typed idiom observation"
            )
        if not isinstance(self.evidence, CorpusEvidence):
            raise EvidenceIdentityMismatch(
                "an accepted promotion needs typed corpus evidence"
            )
        if self.evidence.kind != "draft_landed" or self.evidence.outcome != "accepted":
            raise EvidenceIdentityMismatch(
                "an accepted promotion must carry accepted draft-landed evidence"
            )
        if self.evidence.idiom != self.observation:
            raise EvidenceIdentityMismatch(
                "accepted promotion evidence carries a different idiom observation"
            )
        if len(self.evidence.draft_landed) != 1:
            raise EvidenceIdentityMismatch(
                "accepted promotion evidence must carry exactly one draft-landed pair"
            )
        # The observation is a pure function of the measured pair: rebuilding
        # it proves the exposed observation is the one the evidence supports
        # rather than an unrelated observation with the same label.
        if make_idiom_observation(self.evidence.draft_landed[0]) != self.observation:
            raise EvidenceIdentityMismatch(
                "the exposed idiom observation is not derived from the "
                "evidence's measured pair"
            )


@dataclass(frozen=True)
class PromotionRefused:
    """A refused promotion retained as typed negative evidence."""

    receipt: EvidenceRefusalReceipt
    evidence: CorpusEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, EvidenceRefusalReceipt):
            raise EvidenceIdentityMismatch(
                "a refused promotion needs a typed refusal receipt"
            )
        if not isinstance(self.evidence, CorpusEvidence):
            raise EvidenceIdentityMismatch(
                "a refused promotion needs typed corpus evidence"
            )
        if self.evidence.kind != "negative" or self.evidence.outcome != "negative":
            raise EvidenceIdentityMismatch(
                "a refused promotion must carry negative evidence"
            )
        if self.evidence.refusal_receipt != self.receipt:
            raise EvidenceIdentityMismatch(
                "refused promotion evidence does not embed its own refusal receipt"
            )


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
    # The receipt identity covers the exact inputs and observations that
    # caused the refusal, including the evaluator binding and, when a scorer
    # boundary was reached, the taxonomy that was measured.
    input_identities = tuple(
        sorted(
            set(
                identity
                for identity in (
                    pair.pair_hash,
                    target_identity,
                    evaluator_identity,
                    before.object_hash,
                    after.object_hash,
                )
                if identity
            )
        )
    )
    observed_identities = tuple(
        sorted(
            set(
                identity
                for identity in (
                    before.compiler_identity,
                    after.compiler_identity,
                    scorer.taxonomy_id if scorer is not None else None,
                )
                if identity
            )
        )
    )
    receipt = EvidenceRefusalReceipt(
        receipt_id=hash_canonical(
            {
                "protocol": "sotn-evidence-refusal-v1",
                "operation": "promote_draft_landed",
                "reason_code": reason_code,
                "input_identities": list(input_identities),
                "observed_identities": list(observed_identities),
                "new_generation_required": False,
            }
        ),
        operation="promote_draft_landed",
        reason_code=reason_code,
        input_identities=input_identities,
        observed_identities=observed_identities,
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
        support_identities=tuple(
            sorted(
                set(
                    identity
                    for identity in (
                        pair.pair_hash,
                        scorer.taxonomy_id if scorer is not None else None,
                        before.object_hash,
                        before.mismatch_signature,
                        (
                            before.diagnostic_artifact.content_hash
                            if before.diagnostic_artifact is not None
                            else None
                        ),
                        after.object_hash,
                        after.mismatch_signature,
                        (
                            after.diagnostic_artifact.content_hash
                            if after.diagnostic_artifact is not None
                            else None
                        ),
                        receipt.receipt_id,
                    )
                    if identity
                )
            )
        ),
        reason_code=reason_code,
        refusal_receipt=receipt,
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
        sorted(
            set(
                identity
                for identity in (
                    pair.pair_hash,
                    measured_pair.pair_hash,
                    target_object_hash,
                    target_checksum,
                    taxonomy.taxonomy_id,
                    before.object_hash,
                    before.mismatch_signature,
                    (
                        before.diagnostic_artifact.content_hash
                        if before.diagnostic_artifact is not None
                        else None
                    ),
                    after.object_hash,
                    after.mismatch_signature,
                    (
                        after.diagnostic_artifact.content_hash
                        if after.diagnostic_artifact is not None
                        else None
                    ),
                    observation.observation_id,
                    *measurement.evidence,
                )
                if identity
            )
        )
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
    artifact_root: str | os.PathLike[str],
    min_independent_lineages: int = 2,
) -> Tuple[CorpusEvidence, ...]:
    """Extract recurring divergence evidence the completed contexts support.

    A recommendation becomes corpus evidence only when the report's own
    artifact verifies against its published archive bytes, every source
    ledger it cites was loaded as a completed lineage context, the contexts
    agree with the recommendation's exact identity tuple, every lineage id
    names a supplied context run, and at least ``min_independent_lineages``
    distinct context runs contributed. A diagnostic ledger refuses the
    recommendation as typed evidence with incomplete provenance instead of
    fabricating a promotion-grade hypothesis. Positive and refused records
    carry the full recurrence identity (lane, schema, scorer algorithm,
    pattern id) and bind the report artifact, source ledgers, lineage ids,
    and their refusal receipt, so the durable corpus can reconstruct the
    exact grouping decision.
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
    # Durable existence layer: the in-memory report is self-consistent by
    # construction, but its recommendations may be read only after the
    # published artifact bytes verify in their archive. No context is
    # consumed and no evidence is produced before this call.
    try:
        load_report_artifact(
            report, artifact_root=artifact_root, expected_hash=report.report_id
        )
    except PatternArtifactError:
        # Missing or corrupt report bytes are part of the public corpus
        # boundary's documented artifact error surface. Other pattern-domain
        # failures are translated below so callers never need to import the
        # pattern module merely to handle malformed recurrence input.
        raise
    except PatternInputError as exc:
        raise EvidenceIdentityMismatch(
            "report artifact verification failed: " + str(exc)
        ) from exc
    try:
        context_values = _corpus_sequence(contexts, "lineage contexts")
    except SearchValidationError as exc:
        raise EvidenceIdentityMismatch(str(exc)) from exc
    by_ledger: dict[str, CompletedLineageContext | CompletedLineageDiagnostic] = {}
    for context in context_values:
        if not isinstance(
            context, (CompletedLineageContext, CompletedLineageDiagnostic)
        ):
            raise EvidenceIdentityMismatch(
                "lineage contexts must be the typed context or diagnostic records"
            )
        if context.ledger_identity in by_ledger:
            raise EvidenceIdentityMismatch(
                "two lineage contexts cite ledger identity "
                + context.ledger_identity
            )
        by_ledger[context.ledger_identity] = context
    report_identity = report.artifact.content_hash
    entries: list[CorpusEvidence] = []

    def _refusal_entry(
        *,
        recommendation: Mapping[str, Any],
        divergence: FirstDivergence,
        source_ledgers: Tuple[str, ...],
        lineage_ids: Tuple[str, ...],
        reason_code: str,
        evaluator_identity: str | None,
        observed: Sequence[str],
    ) -> CorpusEvidence:
        input_identities = tuple(
            sorted(set(source_ledgers) | set(lineage_ids) | {report_identity})
        )
        observed_values = set(observed)
        for identity in (
            recommendation.get("compiler_identity"),
            recommendation.get("config_identity"),
            recommendation.get("schema_identity"),
            recommendation.get("lane_tool_identity"),
            recommendation.get("target_identity"),
            evaluator_identity,
        ):
            if identity:
                observed_values.add(identity)
        observed_identities = tuple(sorted(observed_values))
        receipt = EvidenceRefusalReceipt(
            receipt_id=hash_canonical(
                {
                    "protocol": "sotn-evidence-refusal-v1",
                    "operation": "collect_recurring_first_divergence",
                    "reason_code": reason_code,
                    "input_identities": list(input_identities),
                    "observed_identities": list(observed_identities),
                    "new_generation_required": False,
                }
            ),
            operation="collect_recurring_first_divergence",
            reason_code=reason_code,
            input_identities=input_identities,
            observed_identities=observed_identities,
            new_generation_required=False,
        )
        return _make_corpus_evidence(
            kind="first_divergence",
            outcome="refused",
            recipient_id=recommendation["recipient_id"],
            compiler_identity=recommendation["compiler_identity"],
            tool_identity=recommendation["lane_tool_identity"],
            target_identity=recommendation["target_identity"],
            config_identity=recommendation["config_identity"],
            evaluator_identity=evaluator_identity,
            lane=recommendation["lane"],
            schema_identity=recommendation["schema_identity"],
            scorer_algorithm=recommendation["scorer_algorithm"],
            pattern_id=recommendation["pattern_id"],
            first_divergence=divergence,
            support_identities=tuple(
                sorted(
                    set(source_ledgers)
                    | set(lineage_ids)
                    | {report_identity, recommendation["pattern_id"], receipt.receipt_id}
                )
            ),
            reason_code=reason_code,
            refusal_receipt=receipt,
        )

    for recommendation in report.recommendations:
        # The shared strict production validator: a report that reached this
        # boundary already validated its recommendations at construction, so
        # this re-check is defense in depth for the corpus domain boundary.
        try:
            validate_search_recommendation(recommendation)
        except PatternInputError as exc:
            raise EvidenceIdentityMismatch(
                "recommendation does not match the production schema: " + str(exc)
            ) from exc
        divergence_raw = recommendation["first_divergence"]
        if not divergence_raw:
            continue
        try:
            divergence = FirstDivergence.from_dict(divergence_raw)
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise EvidenceIdentityMismatch(
                "recommendation first divergence is invalid: " + str(exc)
            ) from exc
        try:
            source_ledgers = _corpus_sequence(
                recommendation["source_ledgers"],
                "recommendation source ledgers",
            )
            lineage_ids = _corpus_sequence(
                recommendation["lineage_ids"],
                "recommendation lineage ids",
            )
        except SearchValidationError as exc:
            raise EvidenceIdentityMismatch(str(exc)) from exc
        common: dict[str, Any] = {
            "recipient_id": recommendation["recipient_id"],
            "compiler_identity": recommendation["compiler_identity"],
            "tool_identity": recommendation["lane_tool_identity"],
            "target_identity": recommendation["target_identity"],
            "config_identity": recommendation["config_identity"],
            "lane": recommendation["lane"],
            "schema_identity": recommendation["schema_identity"],
            "scorer_algorithm": recommendation["scorer_algorithm"],
            "pattern_id": recommendation["pattern_id"],
            "first_divergence": divergence,
        }
        observed = tuple(sorted(set(source_ledgers) & set(by_ledger)))

        if any(ledger not in by_ledger for ledger in source_ledgers):
            entries.append(
                _refusal_entry(
                    recommendation=recommendation,
                    divergence=divergence,
                    source_ledgers=source_ledgers,
                    lineage_ids=lineage_ids,
                    reason_code="missing_lineage_context",
                    evaluator_identity=None,
                    observed=observed,
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
                _refusal_entry(
                    recommendation=recommendation,
                    divergence=divergence,
                    source_ledgers=source_ledgers,
                    lineage_ids=lineage_ids,
                    reason_code=diagnostics[0].reason_code,
                    evaluator_identity=None,
                    observed=observed,
                )
            )
            continue
        contexts_for = [by_ledger[ledger] for ledger in source_ledgers]
        incompatible = False
        for context in contexts_for:
            assert isinstance(context, CompletedLineageContext)
            # The exact (lane, lane_tool_identity) pair must be bound in the
            # context: a tool identity that merely belongs to some other lane
            # of the same run is not compatibility evidence.
            lane_pair = (
                recommendation["lane"],
                recommendation["lane_tool_identity"],
            )
            if (
                context.compiler_identity != recommendation["compiler_identity"]
                or context.config_identity != recommendation["config_identity"]
                or context.schema_identity != recommendation["schema_identity"]
                or recommendation["scorer_algorithm"]
                not in context.scorer_algorithms
                or lane_pair not in context.lane_tool_identities
                or (
                    recommendation["recipient_id"],
                    recommendation["target_identity"],
                )
                not in context.recipient_target_identities
                or context.evaluator_identity != recommendation["evaluator_identity"]
            ):
                incompatible = True
                break
        if incompatible:
            entries.append(
                _refusal_entry(
                    recommendation=recommendation,
                    divergence=divergence,
                    source_ledgers=source_ledgers,
                    lineage_ids=lineage_ids,
                    reason_code="incompatible_lineage_context",
                    evaluator_identity=recommendation["evaluator_identity"],
                    observed=observed,
                )
            )
            continue
        # Independence is proven from the completed contexts themselves, not
        # from two arbitrary lineage strings: every lineage id must name one
        # of the context runs that backed this recommendation, and the
        # distinct context runs must reach the independence threshold.
        context_run_ids = {context.run_id for context in contexts_for}
        contributing_run_ids: set[str] = set()
        unbacked = []
        for lineage in lineage_ids:
            if not isinstance(lineage, str) or ":" not in lineage:
                unbacked.append(lineage)
                continue
            run_id = lineage.split(":", 1)[0]
            if run_id not in context_run_ids:
                unbacked.append(lineage)
                continue
            contributing_run_ids.add(run_id)
        # Every completed context cited by the report must contribute at least
        # one lineage observation. Otherwise citing an unused second context
        # would falsely satisfy the independence threshold.
        if unbacked or contributing_run_ids != context_run_ids:
            entries.append(
                _refusal_entry(
                    recommendation=recommendation,
                    divergence=divergence,
                    source_ledgers=source_ledgers,
                    lineage_ids=lineage_ids,
                    reason_code="unverified_lineage_identity",
                    evaluator_identity=recommendation["evaluator_identity"],
                    observed=observed,
                )
            )
            continue
        if len(contributing_run_ids) < min_independent_lineages:
            continue
        support = tuple(
            sorted(
                set(source_ledgers)
                | set(lineage_ids)
                | {report_identity, recommendation["pattern_id"]}
            )
        )
        entries.append(
            _make_corpus_evidence(
                kind="first_divergence",
                outcome="positive",
                evaluator_identity=recommendation["evaluator_identity"],
                support_identities=support,
                reason_code=None,
                **common,
            )
        )
    return tuple(entries)


__all__ = [
    "CORPUS_EVIDENCE_PROTOCOL",
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
