"""Task 0 tests: consuming the canonical Task 8.2 integration prerequisite."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_evidence_corpus import (
    AbsenceMaskingClaim,
    CorpusGeneration,
    EvidenceIdentityMismatch,
    LessonCitationError,
    ScorerTaxonomy,
    build_corpus_generation,
    make_lesson_citation,
    make_scorer_taxonomy,
    scorer_taxonomy_identity_payload,
    verify_lesson_citation,
)
from automation.search_supervisor import (
    EVALUATOR_TOOL_KEY,
    INSTRUMENTED_MODE,
    IntegrationGateError,
    MODE_TOOL_KEY,
    archive_integration_gate,
    load_integration_gate,
    mode_identity,
)
from automation.search_types import (
    ArtifactRef,
    FirstDivergence,
    ScoreComponents,
    ScoreVector,
    hash_bytes,
    hash_canonical,
)
from automation.test_search_schema import manifest


def digest(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


_LESSON_PATH = Path(__file__).resolve().parent.parent / "MATCHING-LESSONS.md"


def lesson_source(source_bytes: bytes) -> ArtifactRef:
    return ArtifactRef(
        hash_bytes(source_bytes),
        "sources/MATCHING-LESSONS.md",
        "text/markdown",
        len(source_bytes),
    )


def fixture_score(
    *,
    total: int,
    compiler_identity: str,
    divergence: FirstDivergence | None = None,
    scorer_algorithm: str = "difflib",
) -> ScoreVector:
    """A valid successful score vector with every required component."""

    return ScoreVector(
        compile_status="success",
        elapsed_ms=1,
        total=total,
        components=ScoreComponents(0, 0, 0, 2 if total else 0, 3 if total else 0),
        weights=ScoreComponents(1, 5, 60, 100, 100),
        object_hash=digest(f"object-{total}"),
        mismatch_signature=digest(f"signature-{total}"),
        first_divergence=divergence,
        target_instruction_count=12,
        candidate_instruction_count=11,
        diagnostic_artifact=None,
        scorer_algorithm=scorer_algorithm,
        compiler_identity=compiler_identity,
    )


def gate_manifest(*, queue_evidence_identity: str | None = None):
    """Return a factory-shaped manifest bound for one integration run."""

    base = manifest()
    tools = dict(base.tool_identities)
    tools[MODE_TOOL_KEY] = mode_identity(INSTRUMENTED_MODE)
    tools["search_coordinator"] = digest("coordinator")
    tools[EVALUATOR_TOOL_KEY] = digest("search-evaluator")
    tools["full_oracle"] = digest("full-oracle")
    lanes = ("cfg_dataflow",)
    value = replace(
        base,
        selected_lanes=lanes,
        tool_identities=tools,
        lane_budgets={"cfg_dataflow": base.lane_budgets["cfg_dataflow"]},
    )
    if queue_evidence_identity is not None:
        value = replace(value, queue_evidence_identity=queue_evidence_identity)
    return value


def fixture_gate(archive: ContentAddressedArchive, *, queue_evidence_identity: str | None = None):
    """Archive and canonically validate one Task 8.2 integration receipt.

    Altered identities produce a distinct archived receipt; nothing mutates a
    receipt in memory.
    """

    receipt = archive_integration_gate(
        gate_manifest(queue_evidence_identity=queue_evidence_identity),
        archive=archive,
    )
    load_integration_gate(receipt.to_dict(), archive=archive)
    return receipt


def fixture_gate_with_corrupt_receipt_artifact(
    archive: ContentAddressedArchive,
):
    receipt = fixture_gate(archive)
    path = archive.resolve(receipt.receipt_artifact)
    path.write_bytes(b"x" * receipt.receipt_artifact.byte_size)
    return receipt


class CanonicalGateConsumerTests(unittest.TestCase):
    def test_missing_canonical_gate_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            with self.assertRaisesRegex(IntegrationGateError, "integration gate"):
                build_corpus_generation(
                    (),
                    integration_gate=None,
                    schema_identity=digest("schema"),
                    archive=archive,
                )

    def test_changed_valid_gate_creates_a_distinct_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            original = fixture_gate(archive)
            altered = fixture_gate(
                archive,
                queue_evidence_identity=digest("changed-queue-evidence"),
            )
            first = build_corpus_generation(
                (),
                integration_gate=original,
                schema_identity=digest("schema"),
                archive=archive,
            )
            second = build_corpus_generation(
                (),
                integration_gate=altered,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertNotEqual(first.generation_id, second.generation_id)

    def test_corrupt_canonical_gate_artifact_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            corrupt = fixture_gate_with_corrupt_receipt_artifact(archive)
            with self.assertRaisesRegex(IntegrationGateError, "receipt artifact"):
                build_corpus_generation(
                    (),
                    integration_gate=corrupt,
                    schema_identity=digest("schema"),
                    archive=archive,
                )

    def test_generation_retains_complete_canonical_gate_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            generation = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertIsInstance(generation, CorpusGeneration)
            self.assertEqual(generation.integration_gate.to_dict(), gate.to_dict())
            self.assertEqual(generation.integration_gate_id, gate.gate_id)
            self.assertEqual(
                generation.manifest_artifact_identity,
                gate.manifest_artifact_identity,
            )
            self.assertEqual(generation.subset_identity, gate.subset_identity)
            self.assertEqual(
                generation.queue_evidence_identity,
                gate.queue_evidence_identity,
            )
            self.assertEqual(tuple(generation.selected_lanes), gate.selected_lanes)
            self.assertEqual(
                generation.coordinator_identity,
                gate.coordinator_identity,
            )
            self.assertEqual(
                generation.connector_identity,
                gate.connector_identity,
            )
            payload = json.loads(archive.verify(generation.artifact).decode("utf-8"))
            self.assertEqual(
                payload["integration_gate"]["gate_id"],
                gate.gate_id,
            )
            self.assertEqual(
                payload["integration_gate"]["receipt_artifact"],
                gate.receipt_artifact.to_dict(),
            )
            self.assertEqual(
                payload["integration_gate"]["manifest_artifact_identity"],
                gate.manifest_artifact_identity,
            )
            self.assertEqual(
                payload["integration_gate"]["subset_identity"],
                gate.subset_identity,
            )
            self.assertEqual(
                tuple(payload["integration_gate"]["selected_lanes"]),
                gate.selected_lanes,
            )
            self.assertEqual(
                payload["integration_gate"]["coordinator_identity"],
                gate.coordinator_identity,
            )
            self.assertEqual(
                payload["integration_gate"]["connector_identity"],
                gate.connector_identity,
            )

    def test_generation_identity_covers_schema_and_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            first = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            second = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("other-schema"),
                archive=archive,
            )
            third = build_corpus_generation(
                ({"evidence_id": digest("entry-1"), "kind": "lesson"},
                 {"evidence_id": digest("entry-2"), "kind": "refusal"}),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertNotEqual(first.generation_id, second.generation_id)
            self.assertNotEqual(first.generation_id, third.generation_id)
            self.assertEqual(len(third.entries), 2)


class LessonCitationAndTaxonomyTests(unittest.TestCase):
    def lesson_citation(self, source_bytes: bytes):
        return make_lesson_citation(
            lesson_source(source_bytes),
            source_bytes,
            section="§2",
            line_start=146,
            line_end=178,
            rule_id="argument-width.absent-andi",
            absence_masking=AbsenceMaskingClaim(
                opcode="andi",
                masks=("0xff", "0xffff"),
                scope="argument-use",
            ),
        )

    def test_section_two_absent_masking_is_span_bound(self):
        source_bytes = _LESSON_PATH.read_bytes()
        citation = self.lesson_citation(source_bytes)
        verify_lesson_citation(citation, source_bytes)
        lines = source_bytes.splitlines(keepends=True)
        self.assertEqual(
            citation.span_identity,
            hash_bytes(b"".join(lines[145:178])),
        )
        self.assertEqual(
            citation.absence_masking,
            AbsenceMaskingClaim("andi", ("0xff", "0xffff"), "argument-use"),
        )
        self.assertNotIn("excerpt", citation.to_dict())

    def test_changed_lesson_bytes_are_refused(self):
        source_bytes = _LESSON_PATH.read_bytes()
        citation = self.lesson_citation(source_bytes)
        with self.assertRaisesRegex(LessonCitationError, "source content hash"):
            verify_lesson_citation(citation, source_bytes + b"\n")

    def test_changed_line_bounds_change_the_citation_identity(self):
        source_bytes = _LESSON_PATH.read_bytes()
        citation = self.lesson_citation(source_bytes)
        moved = make_lesson_citation(
            lesson_source(source_bytes),
            source_bytes,
            section="§2",
            line_start=147,
            line_end=178,
            rule_id="argument-width.absent-andi",
            absence_masking=AbsenceMaskingClaim(
                opcode="andi", masks=("0xff", "0xffff"), scope="argument-use"
            ),
        )
        self.assertNotEqual(citation.citation_id, moved.citation_id)
        self.assertNotEqual(citation.span_identity, moved.span_identity)

    def test_deviating_absence_claims_are_refused(self):
        source_bytes = _LESSON_PATH.read_bytes()
        with self.assertRaisesRegex(LessonCitationError, "absence claim"):
            make_lesson_citation(
                lesson_source(source_bytes),
                source_bytes,
                section="§2",
                line_start=146,
                line_end=178,
                rule_id="argument-width.absent-andi",
                absence_masking=AbsenceMaskingClaim(
                    opcode="andi", masks=("0xffff",), scope="argument-use"
                ),
            )
        with self.assertRaisesRegex(LessonCitationError, "section"):
            make_lesson_citation(
                lesson_source(source_bytes),
                source_bytes,
                section="§3",
                line_start=146,
                line_end=178,
                rule_id="argument-width.absent-andi",
                absence_masking=AbsenceMaskingClaim(
                    opcode="andi", masks=("0xff", "0xffff"), scope="argument-use"
                ),
            )

    def test_span_past_the_lesson_end_is_refused(self):
        source_bytes = _LESSON_PATH.read_bytes()
        with self.assertRaisesRegex(LessonCitationError, "exceeds"):
            make_lesson_citation(
                lesson_source(source_bytes),
                source_bytes,
                section="§2",
                line_start=1,
                line_end=len(source_bytes.splitlines()) + 5,
                rule_id="argument-width.absent-andi",
            )

    def test_scorer_taxonomy_retains_components_weights_and_divergence(self):
        before = fixture_score(
            total=12,
            compiler_identity=digest("compiler"),
            divergence=FirstDivergence(1, 1, "lw", "addiu"),
        )
        after = fixture_score(
            total=4,
            compiler_identity=digest("compiler"),
            divergence=None,
        )
        taxonomy = make_scorer_taxonomy(
            before,
            after,
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        self.assertIsInstance(taxonomy, ScorerTaxonomy)
        self.assertEqual(
            taxonomy.before.components.to_dict(), before.components.to_dict()
        )
        self.assertEqual(
            taxonomy.after.weights.to_dict(), after.weights.to_dict()
        )
        self.assertIsNotNone(taxonomy.before.first_divergence)
        self.assertEqual(
            taxonomy.taxonomy_id,
            hash_canonical(scorer_taxonomy_identity_payload(taxonomy)),
        )
        self.assertEqual(taxonomy.to_dict()["taxonomy_id"], taxonomy.taxonomy_id)
        self.assertEqual(taxonomy.to_dict()["before"], before.to_dict())
        self.assertEqual(taxonomy.to_dict()["after"], after.to_dict())

    def test_taxonomy_mutations_change_or_refuse_the_identity(self):
        compiler = digest("compiler")
        before = fixture_score(
            total=12,
            compiler_identity=compiler,
            divergence=FirstDivergence(1, 1, "lw", "addiu"),
        )
        after = fixture_score(total=4, compiler_identity=compiler)
        taxonomy = make_scorer_taxonomy(
            before,
            after,
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        diverged_after = fixture_score(
            total=4,
            compiler_identity=compiler,
            divergence=FirstDivergence(2, 2, "sw", "move"),
        )
        self.assertNotEqual(
            taxonomy.taxonomy_id,
            make_scorer_taxonomy(
                before,
                diverged_after,
                evaluator_identity=digest("search-evaluator"),
                target_identity=digest("target"),
            ).taxonomy_id,
        )
        heavier_after = replace(
            after, weights=ScoreComponents(2, 5, 60, 100, 100)
        )
        self.assertNotEqual(
            taxonomy.taxonomy_id,
            make_scorer_taxonomy(
                before,
                heavier_after,
                evaluator_identity=digest("search-evaluator"),
                target_identity=digest("target"),
            ).taxonomy_id,
        )
        with self.assertRaises(EvidenceIdentityMismatch):
            make_scorer_taxonomy(
                replace(before, compiler_identity=digest("other-compiler")),
                after,
                evaluator_identity=digest("search-evaluator"),
                target_identity=digest("target"),
            )


if __name__ == "__main__":
    unittest.main()
