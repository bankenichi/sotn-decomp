"""Task 0 tests: consuming the canonical Task 8.2 integration prerequisite."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

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
    run_instrumented,
)
from automation.search_run_factory import create_instrumented_run
from automation import search_run_factory as _factory
from automation.search_types import (
    ArtifactRef,
    FirstDivergence,
    LANES,
    ScoreComponents,
    ScoreVector,
    RunManifest,
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


def _factory_gate(archive: ContentAddressedArchive, *, multi_record: bool = False):
    """Create a real factory run and move its durable root under ``archive``."""

    base = archive.run_root.parent
    repo = base / (
        ("factory-repo-many-" if multi_record else "factory-repo-one-")
        + archive.run_root.name
    )
    (repo / "src").mkdir(parents=True)
    (repo / "include").mkdir()
    (repo / "automation" / "mcp").mkdir(parents=True)
    (repo / "tools" / "sotn_permuter").mkdir(parents=True)
    (repo / "src" / "source.c").write_text("int source;\n", encoding="utf-8")
    (repo / "include" / "header.h").write_text("#define X 1\n", encoding="utf-8")
    modules = (
        "search_lanes.py",
        "search_supervisor.py",
        "search_run_factory.py",
        "search_coordinator.py",
        "search_types.py",
        "search_archive.py",
        "search_recovery.py",
        "upstream_harvest.py",
        "shim_sweep.py",
        "asm_twin_finder.py",
        "transplant.py",
    )
    for module in modules:
        (repo / "automation" / module).write_text(
            f"{module.replace('.', '_')} = 1\n", encoding="utf-8"
        )
    (repo / "automation" / "mcp" / "commands_client.py").write_text(
        "COMMANDS = 1\n", encoding="utf-8"
    )
    (repo / "automation" / "search-ledger.schema.json").write_text(
        "{}\n", encoding="utf-8"
    )
    (repo / "tools" / "sotn_permuter" / "permuter_settings.us.toml").write_text(
        "compiler_command = 'cc | ld'\n", encoding="utf-8"
    )
    ids = (
        "us:ST/RNO0:func_a",
        "us:ST/RNO1:func_b",
    ) if multi_record else ("us:ST/RNO0:func_a",)
    records = []
    for record_id in ids:
        _build, overlay, function = record_id.split(":", 2)
        unit = "unit_a" if function == "func_a" else "unit_b"
        asm = repo / "asm" / "us" / Path(*overlay.lower().split("/")) / "nonmatchings" / unit
        obj = repo / "build" / "us" / "src" / Path(*overlay.lower().split("/"))
        asm.mkdir(parents=True)
        obj.mkdir(parents=True)
        (asm / f"{function}.s").write_text(f"{function}:\n\tnop\n", encoding="utf-8")
        (obj / f"{unit}.c.o").write_bytes((function + " object\n").encode("ascii"))
        records.append({
            "id": record_id,
            "build": "us",
            "overlay": overlay,
            "function": function,
            "status": "todo",
            "claimed_by": "none",
            "notes": "fixture evidence",
            "updated_at": "2026-08-28T00:00:00Z",
        })
    result = create_instrumented_run(
        "gate-many" if multi_record else "gate-one",
        ids,
        [LANES[0]],
        repo=repo,
        queue_reader=lambda: records,
        compiler_identity_resolver=lambda _path: digest("compiler"),
        now=lambda: "2026-08-28T00:00:00Z",
    )
    run_root = Path(result["run_root"])
    run_manifest = run_root / "manifest.json"
    run_value = RunManifest.from_dict(result["manifest"])
    with patch.object(
        _factory,
        "_compiler_identity",
        return_value=(run_value.compiler_identity, {"identity": run_value.compiler_identity}),
    ):
        run_result = run_instrumented(
            run_manifest,
            adapters={},
            lease_path=base / "gate-lease.json",
        )
    if "integration_gate" not in run_result:
        raise AssertionError("completed factory runs must return an integration gate")
    if run_root != archive.run_root:
        shutil.move(str(run_root), str(archive.run_root))
    moved_manifest = archive.run_root / "manifest.json"
    receipt = archive_integration_gate(moved_manifest, archive=archive)
    load_integration_gate(receipt.to_dict(), archive=archive)
    return receipt


def fixture_gate(archive: ContentAddressedArchive, *, queue_evidence_identity: str | None = None):
    """Return a receipt from real factory-shaped archived run evidence."""

    del queue_evidence_identity
    return _factory_gate(archive)


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
            archive_a = ContentAddressedArchive(Path(directory) / "archive-a")
            archive_b = ContentAddressedArchive(Path(directory) / "archive-b")
            original = fixture_gate(archive_a)
            altered = fixture_gate(archive_b)
            first = build_corpus_generation(
                (),
                integration_gate=original,
                schema_identity=digest("schema"),
                archive=archive_a,
            )
            second = build_corpus_generation(
                (),
                integration_gate=altered,
                schema_identity=digest("schema"),
                archive=archive_b,
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

    def test_gate_validation_precedes_the_first_entry_consumption(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            order = []

            class TrackedEntries:
                def __iter__(self):
                    order.append("entries")
                    return iter(())

            def checked(_receipt, *, archive):
                del archive
                order.append("gate")

            with patch(
                "automation.search_evidence_corpus.validate_integration_gate",
                side_effect=checked,
            ) as validator:
                build_corpus_generation(
                    TrackedEntries(),
                    integration_gate=gate,
                    schema_identity=digest("schema"),
                    archive=archive,
                )
            self.assertEqual(validator.call_count, 1)
            self.assertEqual(order, ["gate", "entries"])

    def test_direct_generation_forgery_is_refused_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            generation = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            with self.assertRaises(EvidenceIdentityMismatch):
                replace(
                    generation,
                    queue_evidence_identity=digest("forged-queue-evidence"),
                )
            with self.assertRaises(EvidenceIdentityMismatch):
                replace(generation, generation_id=digest("forged-generation"))
            with self.assertRaises(EvidenceIdentityMismatch):
                replace(
                    generation,
                    artifact=replace(
                        generation.artifact,
                        byte_size=generation.artifact.byte_size + 1,
                    ),
                )

    def test_from_dict_generation_provenance_forgery_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            generation = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            forged = generation.to_dict()
            forged["connector_identity"] = digest("forged-connector")
            with self.assertRaises(EvidenceIdentityMismatch):
                CorpusGeneration.from_dict(forged)
            forged = generation.to_dict()
            forged["integration_gate"] = dict(forged["integration_gate"])
            forged["integration_gate"]["queue_evidence_identity"] = digest(
                "forged-gate-queue"
            )
            with self.assertRaises(EvidenceIdentityMismatch):
                CorpusGeneration.from_dict(forged)


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
        with self.assertRaisesRegex(LessonCitationError, "exact"):
            make_lesson_citation(
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
        verify_lesson_citation(citation, source_bytes)

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

    def test_direct_citation_forgery_reapplies_source_and_anchor_invariants(self):
        source_bytes = _LESSON_PATH.read_bytes()
        citation = self.lesson_citation(source_bytes)
        with self.assertRaises(LessonCitationError):
            verify_lesson_citation(
                replace(
                    citation,
                    source=ArtifactRef(
                        citation.source.content_hash,
                        "sources/OTHER.md",
                        "text/markdown",
                        citation.source.byte_size,
                    ),
                ),
                source_bytes,
            )
        with self.assertRaises(LessonCitationError):
            verify_lesson_citation(
                replace(
                    citation,
                    source=ArtifactRef(
                        citation.source.content_hash,
                        citation.source.path,
                        "text/plain",
                        citation.source.byte_size,
                    ),
                ),
                source_bytes,
            )
        with self.assertRaises(LessonCitationError):
            verify_lesson_citation(
                replace(
                    citation,
                    source=ArtifactRef(
                        citation.source.content_hash,
                        citation.source.path,
                        citation.source.media_type,
                        citation.source.byte_size + 1,
                    ),
                ),
                source_bytes,
            )
        with self.assertRaises(LessonCitationError):
            verify_lesson_citation(
                replace(citation, rule_id="another.valid.rule"),
                source_bytes,
            )

    def test_invalid_utf8_and_changed_line_endings_are_refused(self):
        source_bytes = _LESSON_PATH.read_bytes()
        invalid = source_bytes + b"\xff"
        citation = replace(
            self.lesson_citation(source_bytes),
            source=ArtifactRef(
                digest("invalid-utf8"),
                "sources/MATCHING-LESSONS.md",
                "text/markdown",
                len(invalid),
            ),
        )
        with self.assertRaises(LessonCitationError):
            verify_lesson_citation(citation, invalid)

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

    def test_direct_and_parsed_taxonomy_forgery_uses_identity_mismatch(self):
        compiler = digest("compiler")
        before = fixture_score(total=12, compiler_identity=compiler)
        after = fixture_score(total=4, compiler_identity=compiler)
        taxonomy = make_scorer_taxonomy(
            before,
            after,
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        with self.assertRaises(EvidenceIdentityMismatch):
            ScorerTaxonomy(
                taxonomy.taxonomy_id,
                before,
                replace(after, scorer_algorithm="levenshtein"),
                taxonomy.evaluator_identity,
                taxonomy.target_identity,
            )
        forged = taxonomy.to_dict()
        forged["evaluator_identity"] = digest("other-evaluator")
        with self.assertRaises(EvidenceIdentityMismatch):
            ScorerTaxonomy.from_dict(forged)
        forged = taxonomy.to_dict()
        forged.pop("target_identity")
        with self.assertRaises(EvidenceIdentityMismatch):
            ScorerTaxonomy.from_dict(forged)

        invalid_before = fixture_score(total=12, compiler_identity=compiler)
        object.__setattr__(invalid_before, "compiler_identity", "not-a-hash")
        with self.assertRaises(EvidenceIdentityMismatch):
            ScorerTaxonomy(
                taxonomy.taxonomy_id,
                invalid_before,
                after,
                taxonomy.evaluator_identity,
                taxonomy.target_identity,
            )


if __name__ == "__main__":
    unittest.main()
