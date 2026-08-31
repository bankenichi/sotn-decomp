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
from automation.compiler_idioms import DraftLandedObservation
from automation.search_evidence_corpus import (
    AbsenceMaskingClaim,
    CORPUS_EVIDENCE_PROTOCOL,
    CorpusEvidence,
    CorpusGeneration,
    EvidenceIdentityMismatch,
    EvidenceRefusalReceipt,
    LessonCitationError,
    PromotionAccepted,
    PromotionRefused,
    ScorerTaxonomy,
    build_corpus_generation,
    collect_recurring_first_divergence,
    make_lesson_citation,
    make_scorer_taxonomy,
    promote_draft_landed,
    scorer_taxonomy_identity_payload,
    verify_lesson_citation,
    _make_corpus_evidence,
    _required_support_identities,
)
from automation.search_patterns import (
    CompletedLineageContext,
    CompletedLineageDiagnostic,
    PatternArtifactError,
    PatternInputError,
    SearchPatternReport,
    _lineage_key,
    _report_payload,
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
    GroupedPatch,
    LANES,
    PatchHunk,
    ScoreComponents,
    ScoreVector,
    RunManifest,
    canonical_bytes,
    hash_bytes,
    hash_canonical,
)
from automation.test_search_schema import manifest


def digest(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


def taxonomy_support(taxonomy: ScorerTaxonomy) -> tuple[str, ...]:
    """Return every nested score identity required by the corpus boundary."""

    return (
        taxonomy.taxonomy_id,
        taxonomy.before.object_hash,
        taxonomy.before.mismatch_signature,
        taxonomy.after.object_hash,
        taxonomy.after.mismatch_signature,
    )


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
            def _refusal_entry(target_index: int, candidate_index: int):
                # Typed evidence only: build_corpus_generation refuses raw
                # mappings, so the entry carries its refusal receipt and
                # content address from the typed factory.
                receipt = EvidenceRefusalReceipt(
                    receipt_id=hash_canonical(
                        {
                            "protocol": "sotn-evidence-refusal-v1",
                            "operation": "collect_recurring_first_divergence",
                            "reason_code": "missing_evaluator_identity",
                            "input_identities": [],
                            "observed_identities": [],
                            "new_generation_required": False,
                        }
                    ),
                    operation="collect_recurring_first_divergence",
                    reason_code="missing_evaluator_identity",
                    input_identities=(),
                    observed_identities=(),
                    new_generation_required=False,
                )
                return _make_corpus_evidence(
                    kind="first_divergence",
                    outcome="refused",
                    recipient_id="us:ST:fn",
                    compiler_identity=digest("compiler"),
                    tool_identity=digest("tool:cfg_dataflow"),
                    target_identity=digest("target"),
                    config_identity=digest("config"),
                    first_divergence=FirstDivergence(
                        target_index, candidate_index, "lw", "sw"
                    ),
                    reason_code="missing_evaluator_identity",
                    lane="cfg_dataflow",
                    schema_identity=digest("schema"),
                    scorer_algorithm="difflib",
                    pattern_id=digest("pattern"),
                    refusal_receipt=receipt,
                    support_identities=(receipt.receipt_id, digest("pattern")),
                )

            third = build_corpus_generation(
                (_refusal_entry(1, 2), _refusal_entry(3, 4)),
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


def fixture_pair() -> DraftLandedObservation:
    """One provenance-proven draft-landed pair for promotion gating."""

    draft_hash = digest("pair-draft")
    landed_hash = digest("pair-landed")
    draft = ArtifactRef(
        draft_hash,
        "artifacts/sources/" + draft_hash[7:] + ".c",
        "text/x-c",
        30,
    )
    landed = ArtifactRef(
        landed_hash,
        "artifacts/sources/" + landed_hash[7:] + ".c",
        "text/x-c",
        30,
    )
    hunk = PatchHunk(0, "return 0;\n", "return 1;\n", (), ())
    patch_payload = {
        "format": "line_context",
        "base_source_hash": draft_hash,
        "atomic": True,
        "hunks": [hunk],
    }
    grouped_patch = GroupedPatch(
        patch_id=hash_canonical(patch_payload),
        format="line_context",
        base_source_hash=draft_hash,
        atomic=True,
        hunks=(hunk,),
    )
    return DraftLandedObservation(
        recipient_id="us:ST:fn",
        draft=draft,
        landed=landed,
        landing_commit="a" * 40,
        compiler_identity=digest("compiler"),
        grouped_patches=(grouped_patch,),
        evidence=("landing-commit-verified",),
        tool_identity=digest("tool:cfg_dataflow"),
        config_identity=digest("config"),
    )


def _fixture_recommendation(**overrides) -> dict:
    """One full production-shaped recommendation with stable identities.

    The shape is exactly what ``mine_completed_lineages`` emits, including
    the pattern id recomputed from the canonical lineage key, so the strict
    shared validator accepts it without being weakened.
    """

    recommendation = {
        "pass_kind": None,
        "patch_id": None,
        "lane": "cfg_dataflow",
        "overlay": "st",
        "function_archetype": "generic",
        "first_divergence": FirstDivergence(2, 3, "lw", "sw").to_dict(),
        "compiler_identity": digest("compiler"),
        "config_identity": digest("config"),
        "schema_identity": digest("schema"),
        "scorer_algorithm": "difflib",
        "lane_tool_identity": digest("tool:cfg_dataflow"),
        "recipient_id": "us:ST:fn",
        "target_identity": digest("target:us:ST:fn"),
        "evaluator_identity": digest("search-evaluator"),
        "sample_count": 4,
        "successes": 3,
        "failures": 1,
        "success_rate": round(3 / 4, 6),
        "source_ledgers": sorted(
            [digest("ledger-a"), digest("ledger-b")]
        ),
        "lineage_ids": [
            "run-a:task-a",
            "run-a:task-b",
            "run-b:task-a",
            "run-b:task-b",
        ],
    }
    recommendation.update(overrides)
    recommendation["pattern_id"] = hash_canonical(
        {
            "key": list(
                _lineage_key(
                    pass_kind=recommendation["pass_kind"],
                    patch_id=recommendation["patch_id"],
                    lane=recommendation["lane"],
                    overlay=recommendation["overlay"],
                    archetype=recommendation["function_archetype"],
                    first_divergence=recommendation["first_divergence"],
                    compiler_identity=recommendation["compiler_identity"],
                    config_identity=recommendation["config_identity"],
                    schema_identity=recommendation["schema_identity"],
                    scorer_algorithm=recommendation["scorer_algorithm"],
                    lane_tool_identity=recommendation["lane_tool_identity"],
                    recipient_id=recommendation["recipient_id"],
                    target_identity=recommendation["target_identity"],
                    evaluator_identity=recommendation["evaluator_identity"],
                )
            )
        }
    )
    return recommendation


def fixture_pattern_report(recommendation, archive) -> SearchPatternReport:
    """A published, content-addressed report carrying one recommendation.

    The canonical bytes go through a real content-addressed archive so the
    recurrence boundary's durable existence layer can verify them; the
    fabricated-ArtifactRef shortcut would hide R25 defects.
    """

    ledgers = tuple(sorted(set(recommendation["source_ledgers"])))
    payload = _report_payload(ledgers, [recommendation])
    artifact = archive.put_bytes(
        canonical_bytes(payload),
        category="pattern_reports",
        suffix=".json",
        media_type="application/json",
    )
    return SearchPatternReport(
        hash_canonical(payload), ledgers, (recommendation,), artifact
    )


def fixture_context(ledger: str, run_id: str, **overrides) -> CompletedLineageContext:
    """One compatible completed lineage context with stable identities."""

    values = {
        "ledger_identity": digest(ledger),
        "run_id": run_id,
        "compiler_identity": digest("compiler"),
        "config_identity": digest("config"),
        "schema_identity": digest("schema"),
        "scorer_algorithms": ("difflib",),
        "lane_tool_identities": (
            ("cfg_dataflow", digest("tool:cfg_dataflow")),
        ),
        "recipient_target_identities": (
            ("us:ST:fn", digest("target:us:ST:fn")),
        ),
        "evaluator_identity": digest("search-evaluator"),
    }
    values.update(overrides)
    return CompletedLineageContext(**values)


class PromotionAndRecurrenceTests(unittest.TestCase):
    def test_promotion_requires_compiler_bound_improvement(self) -> None:
        pair = fixture_pair()
        before = fixture_score(total=14, compiler_identity=pair.compiler_identity)
        after = fixture_score(total=7, compiler_identity=pair.compiler_identity)
        accepted = promote_draft_landed(
            pair,
            before,
            after,
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            target_object_hash=digest("target-object"),
        )
        self.assertIsInstance(accepted, PromotionAccepted)
        assert isinstance(accepted, PromotionAccepted)
        self.assertIs(accepted.observation.measurement["improved"], True)
        # DraftLandedObservation.pair_hash covers the measurement, so the
        # observation's supporting hash binds the measured pair while the
        # original pre-measurement pair hash stays in evidence provenance.
        self.assertIn(
            replace(pair, measurement=dict(accepted.observation.measurement)).pair_hash,
            accepted.observation.supporting_pair_hashes,
        )
        self.assertIn(pair.pair_hash, accepted.evidence.support_identities)
        self.assertIsInstance(accepted.evidence, CorpusEvidence)
        self.assertEqual(accepted.evidence.outcome, "accepted")
        self.assertIsNotNone(accepted.evidence.scorer)
        self.assertIsNotNone(accepted.evidence.idiom)

    def test_worse_candidate_is_retained_as_negative_refusal_evidence(self) -> None:
        pair = fixture_pair()
        refused = promote_draft_landed(
            pair,
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        self.assertIsInstance(refused, PromotionRefused)
        assert isinstance(refused, PromotionRefused)
        self.assertEqual(refused.receipt.reason_code, "no_measured_improvement")
        self.assertEqual(refused.evidence.kind, "negative")
        self.assertEqual(refused.evidence.outcome, "negative")
        self.assertIsNone(refused.evidence.idiom)
        self.assertIsNotNone(refused.evidence.scorer)

    def test_compiler_and_scorer_mismatches_are_refused(self) -> None:
        pair = fixture_pair()
        with self.assertRaisesRegex(EvidenceIdentityMismatch, "score vector"):
            promote_draft_landed(
                pair,
                "not-a-vector",
                fixture_score(total=7, compiler_identity=pair.compiler_identity),
                evaluator_identity=digest("search-evaluator"),
                target_identity=digest("target"),
            )
        mismatched = promote_draft_landed(
            pair,
            fixture_score(total=14, compiler_identity=digest("other-compiler")),
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        self.assertIsInstance(mismatched, PromotionRefused)
        self.assertEqual(mismatched.receipt.reason_code, "compiler_mismatch")
        boundary = promote_draft_landed(
            pair,
            fixture_score(
                total=14,
                compiler_identity=pair.compiler_identity,
                scorer_algorithm="levenshtein",
            ),
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        self.assertIsInstance(boundary, PromotionRefused)
        self.assertEqual(boundary.receipt.reason_code, "scorer_boundary_mismatch")

    def test_recurring_first_divergence_needs_two_compatible_completed_lineages(self) -> None:
        first = FirstDivergence(2, 3, "lw", "sw")
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            recommendation = _fixture_recommendation()
            report = fixture_pattern_report(recommendation, archive)
            contexts = (
                fixture_context("ledger-a", "run-a"),
                fixture_context("ledger-b", "run-b"),
            )
            entries = collect_recurring_first_divergence(
                report, contexts, artifact_root=archive.run_root
            )
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.first_divergence, first)
        self.assertIn(digest("ledger-a"), entry.support_identities)
        self.assertIn(digest("ledger-b"), entry.support_identities)
        self.assertIn(report.artifact.content_hash, entry.support_identities)
        self.assertIn(recommendation["pattern_id"], entry.support_identities)
        self.assertEqual(entry.tool_identity, digest("tool:cfg_dataflow"))
        self.assertEqual(entry.target_identity, digest("target:us:ST:fn"))
        self.assertEqual(entry.evaluator_identity, digest("search-evaluator"))
        # R22: the full recurrence grouping identity is on the record.
        self.assertEqual(entry.lane, "cfg_dataflow")
        self.assertEqual(entry.schema_identity, digest("schema"))
        self.assertEqual(entry.scorer_algorithm, "difflib")
        self.assertEqual(entry.pattern_id, recommendation["pattern_id"])

    def test_missing_evaluator_lineage_is_typed_refusal(self) -> None:
        first = FirstDivergence(2, 3, "lw", "sw")
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(_fixture_recommendation(), archive)
            diagnostic = CompletedLineageDiagnostic(
                ledger_identity=digest("ledger-a"),
                run_id="run-a",
                reason_code="missing_evaluator_identity",
                # R15 canonical form: observed identities are sorted and unique.
                observed_identities=tuple(
                    sorted(
                        (
                            digest("compiler"),
                            digest("config"),
                            digest("schema"),
                            digest("tool:cfg_dataflow"),
                            digest("target:us:ST:fn"),
                        )
                    )
                ),
            )
            entries = collect_recurring_first_divergence(
                report,
                (diagnostic, fixture_context("ledger-b", "run-b")),
                artifact_root=archive.run_root,
            )
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.outcome, "refused")
        self.assertEqual(entry.reason_code, "missing_evaluator_identity")
        self.assertEqual(entry.first_divergence, first)
        self.assertEqual(entry.tool_identity, digest("tool:cfg_dataflow"))
        self.assertEqual(entry.target_identity, digest("target:us:ST:fn"))
        self.assertIsNone(entry.evaluator_identity)
        # R20/R22: the refusal keeps its receipt and full recurrence identity.
        self.assertIsInstance(entry.refusal_receipt, EvidenceRefusalReceipt)
        self.assertEqual(
            entry.refusal_receipt.reason_code, "missing_evaluator_identity"
        )
        self.assertIn(entry.refusal_receipt.receipt_id, entry.support_identities)
        self.assertEqual(entry.lane, "cfg_dataflow")
        self.assertEqual(entry.pattern_id, _fixture_recommendation()["pattern_id"])
        self.assertIn(report.artifact.content_hash, entry.support_identities)

    def test_single_lineage_recommendation_produces_no_positive_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(
                _fixture_recommendation(
                    source_ledgers=[digest("ledger-a")],
                    lineage_ids=["run-a:task-a"],
                    sample_count=1,
                    successes=1,
                    failures=0,
                    success_rate=1.0,
                ),
                archive,
            )
            entries = collect_recurring_first_divergence(
                report,
                (fixture_context("ledger-a", "run-a"),),
                artifact_root=archive.run_root,
            )
        self.assertEqual(entries, ())

    def test_incompatible_lineage_context_is_typed_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(_fixture_recommendation(), archive)
            mismatched = fixture_context(
                "ledger-a", "run-a", compiler_identity=digest("other-compiler")
            )
            entries = collect_recurring_first_divergence(
                report,
                (mismatched, fixture_context("ledger-b", "run-b")),
                artifact_root=archive.run_root,
            )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].outcome, "refused")
        self.assertEqual(entries[0].reason_code, "incompatible_lineage_context")
        self.assertEqual(
            entries[0].evaluator_identity, digest("search-evaluator")
        )
        self.assertIsInstance(entries[0].refusal_receipt, EvidenceRefusalReceipt)

    def test_lineage_ids_must_name_supplied_context_runs(self) -> None:
        # R23/R25: independence comes from the completed contexts, not from
        # two arbitrary lineage strings. The recommendation cites lineage ids
        # from runs that were never supplied as contexts.
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(
                _fixture_recommendation(
                    lineage_ids=["run-x:task-a", "run-y:task-b"],
                    sample_count=2,
                    successes=2,
                    failures=0,
                    success_rate=1.0,
                ),
                archive,
            )
            entries = collect_recurring_first_divergence(
                report,
                (fixture_context("ledger-a", "run-a"), fixture_context("ledger-b", "run-b")),
                artifact_root=archive.run_root,
            )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].outcome, "refused")
        self.assertEqual(entries[0].reason_code, "unverified_lineage_identity")

    def test_two_cited_runs_need_a_lineage_from_each_run(self) -> None:
        # Two distinct lineage ids from run A cannot make a recommendation
        # citing runs A and B independent. Run B must contribute an observed
        # lineage id before the recurrence threshold can be satisfied.
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(
                _fixture_recommendation(
                    lineage_ids=["run-a:task-a", "run-a:task-b"],
                    sample_count=2,
                    successes=2,
                    failures=0,
                    success_rate=1.0,
                ),
                archive,
            )
            entries = collect_recurring_first_divergence(
                report,
                (fixture_context("ledger-a", "run-a"), fixture_context("ledger-b", "run-b")),
                artifact_root=archive.run_root,
            )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].outcome, "refused")
        self.assertEqual(entries[0].reason_code, "unverified_lineage_identity")

    def test_malformed_context_collections_use_the_evidence_error_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(_fixture_recommendation(), archive)
            for invalid in (None, 0, False, ""):
                with self.subTest(contexts=invalid):
                    with self.assertRaises(EvidenceIdentityMismatch):
                        collect_recurring_first_divergence(
                            report,
                            invalid,
                            artifact_root=archive.run_root,
                        )

    def test_one_run_with_two_tasks_is_not_independent(self) -> None:
        # Two lineage ids from ONE run are not two independent lineages: the
        # distinct context-run count decides, not the string count.
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(
                _fixture_recommendation(
                    lineage_ids=["run-a:task-a", "run-a:task-b"],
                    sample_count=2,
                    successes=2,
                    failures=0,
                    success_rate=1.0,
                ),
                archive,
            )
            entries = collect_recurring_first_divergence(
                report,
                (fixture_context("ledger-a", "run-a"), fixture_context("ledger-b", "run-a")),
                artifact_root=archive.run_root,
            )
        self.assertEqual(entries, ())


class GenerationPublicationTests(unittest.TestCase):
    """Task 4: one immutable generation from every corpus evidence kind."""

    def full_entry_set(self, archive: ContentAddressedArchive):
        gate = fixture_gate(archive)
        lesson_bytes = _LESSON_PATH.read_bytes()
        citation = make_lesson_citation(
            lesson_source(lesson_bytes),
            lesson_bytes,
            section="§2",
            line_start=146,
            line_end=178,
            rule_id="argument-width.absent-andi",
            absence_masking=AbsenceMaskingClaim(
                opcode="andi", masks=("0xff", "0xffff"), scope="argument-use"
            ),
        )
        # The required-support derivation demands the citation's source
        # artifact hash and span identity in the support set.
        lesson_entry = _make_corpus_evidence(
            kind="lesson",
            outcome="accepted",
            citations=(citation,),
            support_identities=(
                citation.span_identity,
                citation.source.content_hash,
            ),
        )
        compiler = digest("compiler")
        taxonomy = make_scorer_taxonomy(
            fixture_score(total=12, compiler_identity=compiler),
            fixture_score(total=4, compiler_identity=compiler),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        scorer_entry = _make_corpus_evidence(
            kind="scorer",
            outcome="accepted",
            compiler_identity=compiler,
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            scorer=taxonomy,
            support_identities=taxonomy_support(taxonomy),
        )
        pair = fixture_pair()
        accepted = promote_draft_landed(
            pair,
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            target_object_hash=digest("target-object"),
        )
        assert isinstance(accepted, PromotionAccepted)
        refused = promote_draft_landed(
            pair,
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        assert isinstance(refused, PromotionRefused)
        report = fixture_pattern_report(_fixture_recommendation(), archive)
        contexts = (
            fixture_context("ledger-a", "run-a"),
            fixture_context("ledger-b", "run-b"),
        )
        recurring = collect_recurring_first_divergence(
            report, contexts, artifact_root=archive.run_root
        )
        assert len(recurring) == 1
        diagnostic = CompletedLineageDiagnostic(
            ledger_identity=digest("ledger-a"),
            run_id="run-a",
            reason_code="missing_evaluator_identity",
            observed_identities=tuple(
                sorted(
                    (
                        digest("compiler"),
                        digest("config"),
                        digest("schema"),
                        digest("tool:cfg_dataflow"),
                        digest("target:us:ST:fn"),
                    )
                )
            ),
        )
        refused_recurrence = collect_recurring_first_divergence(
            report,
            (diagnostic, fixture_context("ledger-b", "run-b")),
            artifact_root=archive.run_root,
        )
        assert len(refused_recurrence) == 1
        entries = (
            lesson_entry,
            scorer_entry,
            accepted.evidence,
            refused.evidence,
            recurring[0],
            refused_recurrence[0],
        )
        return gate, entries, report, (lesson_entry, scorer_entry)

    def test_generation_publishes_every_kind_and_derives_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate, entries, _report, _inputs = self.full_entry_set(archive)
            generation = build_corpus_generation(
                entries,
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertEqual(len(generation.entries), 6)
            # R26: the durable generation keeps typed evidence records.
            self.assertTrue(
                all(
                    isinstance(entry, CorpusEvidence)
                    for entry in generation.entries
                )
            )
            # R27: the source set is the mechanical union of each entry's
            # declared support and its required nested identities.
            expected_sources = sorted(
                {
                    identity
                    for entry in generation.entries
                    for identity in (
                        set(entry.support_identities)
                        | _required_support_identities(entry)
                    )
                    if identity.startswith("sha256:")
                }
            )
            self.assertEqual(
                generation.source_identities, tuple(expected_sources)
            )
            payload = json.loads(
                archive.verify(generation.artifact).decode("utf-8")
            )
            self.assertEqual(
                payload["source_identities"], list(expected_sources)
            )
            self.assertEqual(
                payload["integration_gate_id"], gate.gate_id
            )
            # R28: the evidence protocol namespace survives serialization so
            # replay can select and reject schema versions explicitly.
            self.assertEqual(
                {entry["protocol"] for entry in payload["entries"]},
                {CORPUS_EVIDENCE_PROTOCOL},
            )
            # Replay reconstructs an equal typed generation from the record.
            replayed = CorpusGeneration.from_dict(generation.to_dict())
            self.assertEqual(replayed, generation)
            self.assertTrue(
                all(
                    isinstance(entry, CorpusEvidence)
                    for entry in replayed.entries
                )
            )

    def test_refusal_receipts_survive_publication_and_replay(self) -> None:
        # R20: the content-addressed refusal receipt is part of the negative
        # evidence payload, so the published generation reproduces the exact
        # refusal, not merely a reason string.
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate, entries, _report, _inputs = self.full_entry_set(archive)
            generation = build_corpus_generation(
                entries,
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            negative = [
                entry
                for entry in generation.entries
                if entry.outcome in ("negative", "refused")
            ]
            self.assertEqual(len(negative), 2)
            for entry in negative:
                self.assertIsNotNone(entry.refusal_receipt)
                self.assertIn(
                    entry.refusal_receipt.receipt_id, entry.support_identities
                )
                self.assertEqual(
                    entry.reason_code, entry.refusal_receipt.reason_code
                )
                receipt_payload = entry.refusal_receipt.to_dict()
                self.assertEqual(
                    receipt_payload["receipt_id"],
                    hash_canonical(
                        {
                            "protocol": "sotn-evidence-refusal-v1",
                            "operation": receipt_payload["operation"],
                            "reason_code": receipt_payload["reason_code"],
                            "input_identities": receipt_payload["input_identities"],
                            "observed_identities": receipt_payload[
                                "observed_identities"
                            ],
                            "new_generation_required": receipt_payload[
                                "new_generation_required"
                            ],
                        }
                    ),
                )
            replayed = CorpusGeneration.from_dict(generation.to_dict())
            for original in negative:
                match = [
                    entry
                    for entry in replayed.entries
                    if entry.evidence_id == original.evidence_id
                ]
                self.assertEqual(len(match), 1)
                self.assertEqual(
                    match[0].refusal_receipt, original.refusal_receipt
                )

    def test_generation_is_deterministic_under_entry_reversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate, entries, _report, _inputs = self.full_entry_set(archive)
            first = build_corpus_generation(
                entries,
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            second = build_corpus_generation(
                tuple(reversed(entries)),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertEqual(first.generation_id, second.generation_id)
            self.assertEqual(first.artifact.content_hash, second.artifact.content_hash)
            self.assertEqual(first.artifact, second.artifact)

    def test_generation_build_is_read_only_over_its_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate, entries, report, inputs = self.full_entry_set(archive)
            before_gate = gate.to_dict()
            before_entries = [entry.to_dict() for entry in entries]
            before_report = report.to_dict()
            before_inputs = [entry.to_dict() for entry in inputs]
            build_corpus_generation(
                entries,
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertEqual(gate.to_dict(), before_gate)
            self.assertEqual(
                [entry.to_dict() for entry in entries], before_entries
            )
            self.assertEqual(report.to_dict(), before_report)
            self.assertEqual(
                [entry.to_dict() for entry in inputs], before_inputs
            )

    def test_entry_shape_contradictions_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            with self.assertRaises(EvidenceIdentityMismatch):
                build_corpus_generation(
                    (_make_corpus_evidence(
                        kind="draft_landed",
                        outcome="accepted",
                        recipient_id="us:ST:fn",
                    ),),
                    integration_gate=gate,
                    schema_identity=digest("schema"),
                    archive=archive,
                )
            with self.assertRaises(EvidenceIdentityMismatch):
                build_corpus_generation(
                    (_make_corpus_evidence(
                        kind="unknown-kind",
                        outcome="accepted",
                    ),),
                    integration_gate=gate,
                    schema_identity=digest("schema"),
                    archive=archive,
                )

    def test_duplicate_evidence_ids_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            taxonomy = make_scorer_taxonomy(
                fixture_score(total=12, compiler_identity=digest("compiler")),
                fixture_score(total=4, compiler_identity=digest("compiler")),
                evaluator_identity=digest("search-evaluator"),
                target_identity=digest("target"),
            )
            entry = _make_corpus_evidence(
                kind="scorer",
                outcome="accepted",
                compiler_identity=digest("compiler"),
                evaluator_identity=digest("search-evaluator"),
                target_identity=digest("target"),
                scorer=taxonomy,
                support_identities=taxonomy_support(taxonomy),
            )
            with self.assertRaises(EvidenceIdentityMismatch):
                build_corpus_generation(
                    (entry, entry),
                    integration_gate=gate,
                    schema_identity=digest("schema"),
                    archive=archive,
                )


class EvidenceAddressingTests(unittest.TestCase):
    """Assigned corrections: content addressing and boundary validation."""

    @staticmethod
    def _scorer_entry() -> CorpusEvidence:
        taxonomy = make_scorer_taxonomy(
            fixture_score(total=12, compiler_identity=digest("compiler")),
            fixture_score(total=4, compiler_identity=digest("compiler")),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        return _make_corpus_evidence(
            kind="scorer",
            outcome="accepted",
            compiler_identity=digest("compiler"),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            scorer=taxonomy,
            support_identities=taxonomy_support(taxonomy),
        )

    def test_direct_evidence_id_forgery_is_refused(self) -> None:
        entry = self._scorer_entry()
        with self.assertRaises(EvidenceIdentityMismatch):
            replace(entry, evidence_id=digest("forged"))

    def test_generation_rejects_tampered_raw_entry_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            entry = self._scorer_entry()
            tampered = dict(entry.to_dict())
            tampered["evidence_id"] = digest("forged")
            with self.assertRaises(EvidenceIdentityMismatch):
                build_corpus_generation(
                    (tampered,),
                    integration_gate=gate,
                    schema_identity=digest("schema"),
                    archive=archive,
                )

    def test_generation_accepts_typed_evidence_only(self) -> None:
        # R26: build accepts typed evidence only, and replay through
        # from_dict reconstructs typed entries while a forged raw-mapping
        # entry refuses instead of being stored.
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            entry = self._scorer_entry()
            with self.assertRaises(EvidenceIdentityMismatch):
                build_corpus_generation(
                    (entry.to_dict(),),
                    integration_gate=gate,
                    schema_identity=digest("schema"),
                    archive=archive,
                )
            generation = build_corpus_generation(
                (entry,),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertTrue(
                all(isinstance(item, CorpusEvidence) for item in generation.entries)
            )
            replayed = CorpusGeneration.from_dict(generation.to_dict())
            self.assertEqual(replayed, generation)
            forged = generation.to_dict()
            forged["entries"] = [dict(forged["entries"][0])]
            forged["entries"][0]["compiler_identity"] = digest("other-compiler")
            with self.assertRaises(EvidenceIdentityMismatch):
                CorpusGeneration.from_dict(forged)

    def test_exact_variant_shapes_hold_for_direct_and_replay_inputs(self) -> None:
        entry = self._scorer_entry()
        lesson_bytes = _LESSON_PATH.read_bytes()
        citation = make_lesson_citation(
            lesson_source(lesson_bytes),
            lesson_bytes,
            section="§2",
            line_start=146,
            line_end=178,
            rule_id="argument-width.absent-andi",
            absence_masking=AbsenceMaskingClaim(
                opcode="andi", masks=("0xff", "0xffff"), scope="argument-use"
            ),
        )
        hybrid_support = (
            *entry.support_identities,
            citation.span_identity,
            citation.source.content_hash,
        )
        # A scorer with a lesson citation is a contradictory hybrid even when
        # every nested object is otherwise valid and content-addressed.
        with self.assertRaises(EvidenceIdentityMismatch):
            replace(
                entry,
                citations=(citation,),
                support_identities=hybrid_support,
            )
        replay_hybrid = entry.to_dict()
        replay_hybrid["citations"] = [citation.to_dict()]
        replay_hybrid["support_identities"] = list(hybrid_support)
        replay_hybrid["evidence_id"] = hash_canonical(
            {key: value for key, value in replay_hybrid.items() if key != "evidence_id"}
        )
        with self.assertRaises(EvidenceIdentityMismatch):
            CorpusEvidence.from_dict(replay_hybrid)

        pair = fixture_pair()
        refused = promote_draft_landed(
            pair,
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        assert isinstance(refused, PromotionRefused)
        with self.assertRaises(EvidenceIdentityMismatch):
            replace(refused.evidence, draft_landed=())
        replay_missing_pair = refused.evidence.to_dict()
        replay_missing_pair["draft_landed"] = []
        replay_missing_pair["evidence_id"] = hash_canonical(
            {
                key: value
                for key, value in replay_missing_pair.items()
                if key != "evidence_id"
            }
        )
        with self.assertRaises(EvidenceIdentityMismatch):
            CorpusEvidence.from_dict(replay_missing_pair)

    def test_nonproduction_draft_negative_variant_is_refused_direct_and_replay(self) -> None:
        pair = fixture_pair()
        refused = promote_draft_landed(
            pair,
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        assert isinstance(refused, PromotionRefused)
        with self.assertRaises(EvidenceIdentityMismatch):
            _make_corpus_evidence(
                kind="draft_landed",
                outcome="negative",
                recipient_id=pair.recipient_id,
                compiler_identity=pair.compiler_identity,
                tool_identity=pair.tool_identity,
                target_identity=digest("target"),
                evaluator_identity=digest("search-evaluator"),
                config_identity=pair.config_identity,
                scorer=refused.evidence.scorer,
                draft_landed=(pair,),
                first_divergence=refused.evidence.first_divergence,
                reason_code=refused.evidence.reason_code,
                refusal_receipt=refused.receipt,
                support_identities=refused.evidence.support_identities,
            )
        replay = refused.evidence.to_dict()
        replay["kind"] = "draft_landed"
        replay["evidence_id"] = hash_canonical(
            {key: value for key, value in replay.items() if key != "evidence_id"}
        )
        with self.assertRaises(EvidenceIdentityMismatch):
            CorpusEvidence.from_dict(replay)

    def test_factory_bound_identities_cannot_be_omitted(self) -> None:
        pair = fixture_pair()
        accepted = promote_draft_landed(
            pair,
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            target_object_hash=digest("target-object"),
        )
        refused = promote_draft_landed(
            pair,
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        assert isinstance(accepted, PromotionAccepted)
        assert isinstance(refused, PromotionRefused)
        required = (
            "recipient_id",
            "compiler_identity",
            "tool_identity",
            "target_identity",
            "evaluator_identity",
            "config_identity",
        )
        for evidence in (accepted.evidence, refused.evidence):
            for field in required:
                with self.subTest(kind=evidence.kind, field=field):
                    with self.assertRaises(EvidenceIdentityMismatch):
                        replace(evidence, **{field: None})
                    replay = evidence.to_dict()
                    replay[field] = None
                    replay["evidence_id"] = hash_canonical(
                        {
                            key: value
                            for key, value in replay.items()
                            if key != "evidence_id"
                        }
                    )
                    with self.assertRaises(EvidenceIdentityMismatch):
                        CorpusEvidence.from_dict(replay)

    def test_malformed_corpus_collections_use_the_evidence_error_boundary(self) -> None:
        entry = self._scorer_entry()
        for field in ("citations", "draft_landed", "support_identities"):
            for invalid in (None, 0, False, ""):
                with self.subTest(field=field, value=invalid):
                    forged = entry.to_dict()
                    forged[field] = invalid
                    with self.assertRaises(EvidenceIdentityMismatch):
                        CorpusEvidence.from_dict(forged)
                    with self.assertRaises(EvidenceIdentityMismatch):
                        replace(entry, **{field: invalid})

    def test_refusal_identity_sets_are_sorted_unique_and_content_addressed(self) -> None:
        first_values = (digest("z-input"), digest("a-input"), digest("a-input"))
        second_values = (digest("a-input"), digest("z-input"))

        def receipt(values):
            canonical = tuple(sorted(set(values)))
            payload = {
                "protocol": "sotn-evidence-refusal-v1",
                "operation": "fixture-refusal",
                "reason_code": "fixture_reason",
                "input_identities": list(canonical),
                "observed_identities": list(canonical),
                "new_generation_required": False,
            }
            return EvidenceRefusalReceipt(
                receipt_id=hash_canonical(payload),
                operation="fixture-refusal",
                reason_code="fixture_reason",
                input_identities=values,
                observed_identities=values,
                new_generation_required=False,
            )

        first = receipt(first_values)
        second = receipt(second_values)
        self.assertEqual(first, second)
        self.assertEqual(first.input_identities, second_values)
        self.assertEqual(first.observed_identities, second_values)
        for field in ("input_identities", "observed_identities"):
            for invalid in (None, 0, False, ""):
                with self.subTest(field=field, value=invalid):
                    with self.assertRaises(EvidenceIdentityMismatch):
                        replace(first, **{field: invalid})

    def test_generation_entries_reject_falsey_non_sequences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            generation = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            for invalid in (None, 0, False, ""):
                with self.subTest(entries=invalid):
                    with self.assertRaises(EvidenceIdentityMismatch):
                        replace(generation, entries=invalid)

    def test_missing_required_support_is_refused_and_derived_for_sources(self) -> None:
        # R27: a caller-maintained partial support list cannot hide nested
        # provenance. The taxonomy identity is required at the record
        # boundary, and the generation derivation supplies it mechanically.
        taxonomy = make_scorer_taxonomy(
            fixture_score(total=12, compiler_identity=digest("compiler")),
            fixture_score(total=4, compiler_identity=digest("compiler")),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        for missing in taxonomy_support(taxonomy):
            supports = tuple(
                identity
                for identity in taxonomy_support(taxonomy)
                if identity != missing
            )
            with self.subTest(missing=missing):
                with self.assertRaisesRegex(
                    EvidenceIdentityMismatch, "required identities"
                ):
                    _make_corpus_evidence(
                        kind="scorer",
                        outcome="accepted",
                        compiler_identity=digest("compiler"),
                        evaluator_identity=digest("search-evaluator"),
                        target_identity=digest("target"),
                        scorer=taxonomy,
                        support_identities=supports,
                    )

    def test_evidence_protocol_namespace_is_enforced(self) -> None:
        # R28: the fixed protocol field is part of the identity payload and
        # of serialized evidence, so replay can reject other schema versions.
        entry = self._scorer_entry()
        payload = entry.to_dict()
        self.assertEqual(payload["protocol"], CORPUS_EVIDENCE_PROTOCOL)
        self.assertEqual(
            entry.evidence_id,
            hash_canonical(
                {
                    key: value
                    for key, value in payload.items()
                    if key != "evidence_id"
                }
            ),
        )
        forged = dict(payload)
        forged["protocol"] = "sotn-corpus-evidence-v2"
        with self.assertRaisesRegex(EvidenceIdentityMismatch, "protocol"):
            CorpusEvidence.from_dict(forged)

    def test_support_order_cannot_create_a_second_identity(self) -> None:
        # R22 canonicalization: set-like support input order is normalized.
        taxonomy = make_scorer_taxonomy(
            fixture_score(total=12, compiler_identity=digest("compiler")),
            fixture_score(total=4, compiler_identity=digest("compiler")),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        extra = (digest("extra-identity"), digest("aux-identity"))
        nested = taxonomy_support(taxonomy)
        first = _make_corpus_evidence(
            kind="scorer",
            outcome="accepted",
            compiler_identity=digest("compiler"),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            scorer=taxonomy,
            support_identities=(*nested, *extra),
        )
        second = _make_corpus_evidence(
            kind="scorer",
            outcome="accepted",
            compiler_identity=digest("compiler"),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            scorer=taxonomy,
            support_identities=(extra[1], *reversed(nested), extra[0]),
        )
        self.assertEqual(first, second)

    def test_accepted_entry_cannot_carry_a_refusal_reason(self) -> None:
        with self.assertRaises(EvidenceIdentityMismatch):
            _make_corpus_evidence(
                kind="draft_landed",
                outcome="accepted",
                recipient_id="us:ST:fn",
                scorer=make_scorer_taxonomy(
                    fixture_score(total=12, compiler_identity=digest("compiler")),
                    fixture_score(total=4, compiler_identity=digest("compiler")),
                    evaluator_identity=digest("search-evaluator"),
                    target_identity=digest("target"),
                ),
                reason_code="no_measured_improvement",
            )

    def test_negative_entry_cannot_claim_an_idiom(self) -> None:
        pair = fixture_pair()
        accepted = promote_draft_landed(
            pair,
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        assert isinstance(accepted, PromotionAccepted)
        receipt = EvidenceRefusalReceipt(
            receipt_id=hash_canonical(
                {
                    "protocol": "sotn-evidence-refusal-v1",
                    "operation": "promote_draft_landed",
                    "reason_code": "no_measured_improvement",
                    "input_identities": [],
                    "observed_identities": [],
                    "new_generation_required": False,
                }
            ),
            operation="promote_draft_landed",
            reason_code="no_measured_improvement",
            input_identities=(),
            observed_identities=(),
            new_generation_required=False,
        )
        with self.assertRaises(EvidenceIdentityMismatch):
            _make_corpus_evidence(
                kind="negative",
                outcome="negative",
                recipient_id=pair.recipient_id,
                compiler_identity=pair.compiler_identity,
                tool_identity=pair.tool_identity,
                target_identity=digest("target"),
                evaluator_identity=digest("search-evaluator"),
                config_identity=pair.config_identity,
                scorer=accepted.evidence.scorer,
                draft_landed=(pair,),
                idiom=accepted.observation,
                reason_code="no_measured_improvement",
                refusal_receipt=receipt,
                support_identities=tuple(
                    sorted(
                        set(accepted.evidence.support_identities)
                        | {receipt.receipt_id, pair.pair_hash}
                    )
                ),
            )

    def test_refused_evidence_requires_its_receipt(self) -> None:
        # R20: a refused record without its typed receipt is not publishable
        # negative evidence; the reason alone is forgeable.
        with self.assertRaisesRegex(EvidenceIdentityMismatch, "refusal[_ ]receipt"):
            _make_corpus_evidence(
                kind="first_divergence",
                outcome="refused",
                recipient_id="us:ST:fn",
                compiler_identity=digest("compiler"),
                tool_identity=digest("tool:cfg_dataflow"),
                target_identity=digest("target"),
                config_identity=digest("config"),
                lane="cfg_dataflow",
                schema_identity=digest("schema"),
                scorer_algorithm="difflib",
                pattern_id=digest("pattern"),
                first_divergence=FirstDivergence(1, 2, "lw", "sw"),
                reason_code="missing_evaluator_identity",
                support_identities=(digest("pattern"),),
            )

    def test_receipt_reason_must_match_the_evidence_reason(self) -> None:
        receipt = EvidenceRefusalReceipt(
            receipt_id=hash_canonical(
                {
                    "protocol": "sotn-evidence-refusal-v1",
                    "operation": "collect_recurring_first_divergence",
                    "reason_code": "missing_evaluator_identity",
                    "input_identities": [],
                    "observed_identities": [],
                    "new_generation_required": False,
                }
            ),
            operation="collect_recurring_first_divergence",
            reason_code="missing_evaluator_identity",
            input_identities=(),
            observed_identities=(),
            new_generation_required=False,
        )
        with self.assertRaisesRegex(
            EvidenceIdentityMismatch, "refusal receipt"
        ):
            _make_corpus_evidence(
                kind="first_divergence",
                outcome="refused",
                first_divergence=FirstDivergence(1, 2, "lw", "sw"),
                reason_code="incompatible_lineage_context",
                refusal_receipt=receipt,
                support_identities=(receipt.receipt_id,),
            )


class PromotionWrapperTests(unittest.TestCase):
    """R29: the promotion wrappers enforce their paired records."""

    def test_accepted_wrapper_rejects_unrelated_evidence(self) -> None:
        pair = fixture_pair()
        accepted = promote_draft_landed(
            pair,
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            target_object_hash=digest("target-object"),
        )
        assert isinstance(accepted, PromotionAccepted)
        other_pair = replace(pair, landing_commit="b" * 40)
        other = promote_draft_landed(
            other_pair,
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
            target_object_hash=digest("target-object"),
        )
        assert isinstance(other, PromotionAccepted)
        with self.assertRaises(EvidenceIdentityMismatch):
            PromotionAccepted(
                observation=other.observation, evidence=accepted.evidence
            )
        with self.assertRaises(EvidenceIdentityMismatch):
            PromotionAccepted(
                observation=accepted.observation, evidence=other.evidence
            )
        negative = promote_draft_landed(
            pair,
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        assert isinstance(negative, PromotionRefused)
        with self.assertRaises(EvidenceIdentityMismatch):
            PromotionAccepted(
                observation=accepted.observation, evidence=negative.evidence
            )
        # The honest wrapper still constructs.
        self.assertIsInstance(
            PromotionAccepted(
                observation=accepted.observation, evidence=accepted.evidence
            ),
            PromotionAccepted,
        )

    def test_refused_wrapper_rejects_mismatched_receipt_or_evidence(self) -> None:
        pair = fixture_pair()
        refused = promote_draft_landed(
            pair,
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        assert isinstance(refused, PromotionRefused)
        other = promote_draft_landed(
            replace(pair, landing_commit="c" * 40),
            fixture_score(total=7, compiler_identity=pair.compiler_identity),
            fixture_score(total=14, compiler_identity=pair.compiler_identity),
            evaluator_identity=digest("search-evaluator"),
            target_identity=digest("target"),
        )
        assert isinstance(other, PromotionRefused)
        with self.assertRaises(EvidenceIdentityMismatch):
            PromotionRefused(receipt=other.receipt, evidence=refused.evidence)
        with self.assertRaises(EvidenceIdentityMismatch):
            PromotionRefused(receipt=refused.receipt, evidence=other.evidence)
        self.assertIsInstance(
            PromotionRefused(receipt=refused.receipt, evidence=refused.evidence),
            PromotionRefused,
        )


class RecurrenceBoundaryTests(unittest.TestCase):
    def test_duplicate_lineage_contexts_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(_fixture_recommendation(), archive)
            with self.assertRaises(EvidenceIdentityMismatch):
                collect_recurring_first_divergence(
                    report,
                    (fixture_context("ledger-a", "run-a"),) * 2,
                    artifact_root=archive.run_root,
                )

    def test_string_source_ledgers_are_refused_at_the_report_boundary(self) -> None:
        # R23: the strict production validator refuses a string where a
        # sequence of source ledgers belongs; nothing decomposes it into
        # characters downstream.
        recommendation = _fixture_recommendation(source_ledgers="ledger-a")
        ledgers = (digest("ledger-a"), digest("ledger-b"))
        payload = _report_payload(ledgers, [recommendation])
        with self.assertRaises(PatternInputError):
            SearchPatternReport(
                hash_canonical(payload),
                ledgers,
                (recommendation,),
                ArtifactRef(
                    hash_bytes(canonical_bytes(payload)),
                    "artifacts/pattern_reports/forged.json",
                    "application/json",
                    len(canonical_bytes(payload)),
                ),
            )

    def test_malformed_divergence_is_refused(self) -> None:
        recommendation = _fixture_recommendation(first_divergence="not-a-divergence")
        ledgers = tuple(recommendation["source_ledgers"])
        payload = _report_payload(ledgers, [recommendation])
        with self.assertRaises(PatternInputError):
            SearchPatternReport(
                hash_canonical(payload),
                ledgers,
                (recommendation,),
                ArtifactRef(
                    hash_bytes(canonical_bytes(payload)),
                    "artifacts/pattern_reports/forged.json",
                    "application/json",
                    len(canonical_bytes(payload)),
                ),
            )

    def test_cross_lane_tool_pair_is_refused(self) -> None:
        # The recommendation borrows the cfg_dataflow tool identity while
        # claiming the upstream_current lane: the exact lane pair is bound in
        # the context, so this refuses as incompatible rather than accepting
        # on tool identity alone.
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(
                _fixture_recommendation(lane="upstream_current"),
                archive,
            )
            entries = collect_recurring_first_divergence(
                report,
                (fixture_context("ledger-a", "run-a"), fixture_context("ledger-b", "run-b")),
                artifact_root=archive.run_root,
            )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].outcome, "refused")
        self.assertEqual(entries[0].reason_code, "incompatible_lineage_context")
        self.assertEqual(entries[0].lane, "upstream_current")

    def test_forged_pattern_id_is_refused_at_the_report_boundary(self) -> None:
        # R23: pattern_id must be recomputable from the canonical lineage
        # key; a recommendation cannot mint an arbitrary id.
        recommendation = _fixture_recommendation()
        recommendation["pattern_id"] = digest("forged-pattern")
        ledgers = tuple(recommendation["source_ledgers"])
        payload = _report_payload(ledgers, [recommendation])
        with self.assertRaises(PatternInputError):
            SearchPatternReport(
                hash_canonical(payload),
                ledgers,
                (recommendation,),
                ArtifactRef(
                    hash_bytes(canonical_bytes(payload)),
                    "artifacts/pattern_reports/forged.json",
                    "application/json",
                    len(canonical_bytes(payload)),
                ),
            )

    def test_missing_report_artifact_is_refused_before_any_consumption(self) -> None:
        # R25: the recurrence boundary verifies the report's durable bytes
        # before reading recommendations or consuming contexts.
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(_fixture_recommendation(), archive)

            class ExplodingContexts:
                def __iter__(self):
                    raise AssertionError("contexts must not be consumed")

            with self.assertRaises(PatternArtifactError):
                collect_recurring_first_divergence(
                    report,
                    ExplodingContexts(),
                    artifact_root=Path(directory) / "empty-archive",
                )

    def test_corrupt_report_artifact_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "reports")
            report = fixture_pattern_report(_fixture_recommendation(), archive)
            path = archive.resolve(report.artifact)
            path.write_bytes(b"corrupt bytes")
            with self.assertRaises(PatternArtifactError):
                collect_recurring_first_divergence(
                    report,
                    (fixture_context("ledger-a", "run-a"),),
                    artifact_root=archive.run_root,
                )


if __name__ == "__main__":
    unittest.main()
