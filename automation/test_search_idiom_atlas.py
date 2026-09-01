"""Focused tests for the idiom_atlas production provider."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ArtifactRef, ContentAddressedArchive
from automation.search_idiom_atlas import (
    IDIOM_LANE,
    IdiomAtlasArtifactError,
    IdiomAtlasBudgetError,
    IdiomAtlasInputError,
    IdiomAtlasProvider,
    IdiomAtlasSubsetViolation,
    IdiomAtlasTargetInput,
    build_idiom_atlas_provider,
    idiom_atlas_adapters,
)
from automation.compiler_idioms import (
    DraftLandedObservation,
    make_grouped_patch,
    measure_improvement,
)
from automation.search_evidence_corpus import promote_draft_landed
from automation.search_lanes import Recipient
from automation.search_patterns import CompletedLineageContext
from automation.search_types import (
    TIERS,
    ScoreComponents,
    ScoreVector,
    canonical_subset_identity,
)


def _hash(seed: str) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _commit(seed: str) -> str:
    import hashlib

    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:40]


RECIPIENT = "us:TEST:func_test_one"
DRAFT_TEXT = "int f(void) {\n    return a + (b + c);\n}\n"
LANDED_TEXT = "int f(void) {\n    return a + b + c;\n}\n"
SECOND_LANDED_TEXT = "int f(void) {\n    return (a + b) + c;\n}\n"
PORTED_DRAFT_TEXT = "/* header */\n" + DRAFT_TEXT
PORTED_LANDED_TEXT = "/* header */\n" + LANDED_TEXT
UNRELATED_TEXT = "int unrelated(void) {\n    return 7;\n}\n"

COMPILER = _hash("compiler")
OTHER_COMPILER = _hash("other-compiler")
CONFIG = _hash("config")
TOOL = _hash("tool-idiom-atlas")
EVALUATOR = _hash("evaluator")
TARGET = _hash("target")


def _manifest(*, budget_limit: int = 4, lane_selected: bool = True, tool: bool = True) -> dict:
    lanes = (IDIOM_LANE,) if lane_selected else ()
    tools = {IDIOM_LANE: TOOL} if tool else {}
    return {
        "run_id": "idiomatlasfixture0000000000000000000000000000run",
        "created_at": "2026-08-31T00:00:00Z",
        "parent_run": None,
        "queue_record_ids": [RECIPIENT],
        "function_ids": ["func_test_one"],
        "subset_identity": canonical_subset_identity([RECIPIENT]),
        "queue_evidence_identity": _hash("queue-evidence"),
        "selected_lanes": list(lanes),
        "source_identity": _hash("source"),
        "target_identities": {RECIPIENT: TARGET},
        "compiler_identity": COMPILER,
        "tool_identities": tools,
        "config_identity": CONFIG,
        "schema_identity": _hash("schema"),
        "run_seed": 0,
        "epoch_size": 1,
        "frontier_cap": 1,
        "coordinator_budget": {"unit": "tasks", "limit": 8, "consumed": 0},
        "lane_budgets": {
            IDIOM_LANE: {"unit": "candidates", "limit": budget_limit, "consumed": 0}
        },
        "tier_order": list(TIERS),
    }


def _score_vector(total: int, object_seed: str, compiler_identity: str = COMPILER) -> ScoreVector:
    return ScoreVector(
        compile_status="success",
        elapsed_ms=1,
        total=total,
        components=ScoreComponents(1, 0, 0, 0, 0),
        weights=ScoreComponents(1, 1, 1, 1, 1),
        object_hash=_hash(object_seed),
        mismatch_signature=_hash("sig-" + object_seed),
        first_divergence=None,
        target_instruction_count=3,
        candidate_instruction_count=3,
        diagnostic_artifact=None,
        scorer_algorithm="difflib",
        compiler_identity=compiler_identity,
    )


def _accepted_entry(
    archive: ContentAddressedArchive,
    *,
    before_text: str = DRAFT_TEXT,
    after_text: str = LANDED_TEXT,
    compiler_identity: str = COMPILER,
    archived: bool = True,
):
    if archived:
        before_ref = archive.put_text(before_text)
        after_ref = archive.put_text(after_text)
    else:
        before_ref = ArtifactRef(
            _hash("absent-before"),
            f"artifacts/sources/{_hash('absent-before').removeprefix('sha256:')}.c",
            "text/x-c",
            len(before_text.encode("utf-8")),
        )
        after_ref = archive.put_text(after_text)
    measurement = measure_improvement(
        {"total": 10, "compile_status": "success"},
        {"total": 4, "compile_status": "success"},
        evaluator_identity=EVALUATOR,
    )
    pair = DraftLandedObservation(
        recipient_id=RECIPIENT,
        draft=before_ref,
        landed=after_ref,
        landing_commit=_commit("landing"),
        compiler_identity=compiler_identity,
        grouped_patches=(make_grouped_patch(before_text, after_text),),
        evidence=("fixture-evidence",),
        tool_identity=TOOL,
        config_identity=CONFIG,
        measurement=measurement.to_dict(),
    )
    promoted = promote_draft_landed(
        pair,
        _score_vector(10, "before", compiler_identity),
        _score_vector(4, "after", compiler_identity),
        evaluator_identity=EVALUATOR,
        target_identity=TARGET,
    )
    return promoted.evidence


def _negative_promotion_entry():
    # A promotion with no measured improvement retains typed negative evidence
    # and never produces an idiom, so atlas selection must skip it.
    draft_ref = ArtifactRef(
        _hash("negative-draft"),
        f"artifacts/sources/{_hash('negative-draft').removeprefix('sha256:')}.c",
        "text/x-c",
        len(DRAFT_TEXT.encode("utf-8")),
    )
    landed_ref = ArtifactRef(
        _hash("negative-landed"),
        f"artifacts/sources/{_hash('negative-landed').removeprefix('sha256:')}.c",
        "text/x-c",
        len(LANDED_TEXT.encode("utf-8")),
    )
    pair = DraftLandedObservation(
        recipient_id=RECIPIENT,
        draft=draft_ref,
        landed=landed_ref,
        landing_commit=_commit("landing"),
        compiler_identity=COMPILER,
        grouped_patches=(make_grouped_patch(DRAFT_TEXT, LANDED_TEXT),),
        evidence=("fixture-negative",),
        tool_identity=TOOL,
        config_identity=CONFIG,
    )
    refused = promote_draft_landed(
        pair,
        _score_vector(4, "before"),
        _score_vector(4, "after"),
        evaluator_identity=EVALUATOR,
        target_identity=TARGET,
    )
    return refused.evidence


def _context(compiler_identity: str = COMPILER) -> CompletedLineageContext:
    return CompletedLineageContext(
        ledger_identity=_hash("ledger-" + compiler_identity),
        run_id="idiomatlasfixture000000000000000000000000context",
        compiler_identity=compiler_identity,
        config_identity=CONFIG,
        schema_identity=_hash("schema"),
        scorer_algorithms=("difflib",),
        lane_tool_identities=((IDIOM_LANE, TOOL),),
        recipient_target_identities=((RECIPIENT, TARGET),),
        evaluator_identity=EVALUATOR,
    )


class IdiomAtlasFixture:
    """Shared archive-backed fixture state for one test."""

    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.archive = ContentAddressedArchive(Path(self._temporary.name))
        self.draft_ref = self.archive.put_text(DRAFT_TEXT)

    def close(self) -> None:
        self._temporary.cleanup()

    def target(self, *, draft_bytes=None) -> IdiomAtlasTargetInput:
        if draft_bytes is None:
            draft_bytes = DRAFT_TEXT.encode("utf-8")
            reference = self.draft_ref
        else:
            reference = self.archive.put_bytes(
                draft_bytes, category="sources", suffix=".c", media_type="text/x-c"
            )
        return IdiomAtlasTargetInput(
            recipient_id=RECIPIENT,
            target_identity=TARGET,
            draft_artifact=reference,
            draft_bytes=draft_bytes,
        )


class BuildAndReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = IdiomAtlasFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_exact_replay_produces_measured_candidate(self) -> None:
        entry = _accepted_entry(self.fixture.archive)
        provider = build_idiom_atlas_provider(
            _manifest(),
            [self.fixture.target()],
            [entry],
            [_context()],
            archive=self.fixture.archive,
        )
        self.assertEqual(provider.lane, IDIOM_LANE)
        self.assertEqual(len(provider.idioms), 1)
        result = provider.callback(Recipient.from_dict({"recipient_id": RECIPIENT}))
        self.assertEqual(result["completion_reason"], "matched_pending_oracle")
        self.assertIsNone(result.get("refusal_code"))
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate.candidate_id, _hash(LANDED_TEXT))
        self.assertEqual(candidate.source, LANDED_TEXT)
        self.assertEqual(candidate.record.lane, IDIOM_LANE)
        edge = candidate.provenance[0]
        self.assertEqual(edge["replay_modes"], ("exact",))
        self.assertEqual(edge["base_source_identity"], self.fixture.draft_ref.content_hash)
        self.assertIn(edge["idiom_observation_id"], result["input_identities"])
        self.assertIn(self.fixture.draft_ref.content_hash, result["input_identities"])
        self.assertIn(provider.provider_identity, result["input_identities"])
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(dict(result["rejection_counts"]), {})

    def test_identical_corpus_idioms_deduplicate(self) -> None:
        entry = _accepted_entry(self.fixture.archive)
        twin = _accepted_entry(self.fixture.archive)
        provider = build_idiom_atlas_provider(
            _manifest(),
            [self.fixture.target()],
            [entry, twin],
            [_context()],
            archive=self.fixture.archive,
        )
        self.assertEqual(len(provider.idioms), 1)
        result = provider.callback(Recipient.from_dict({"recipient_id": RECIPIENT}))
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(dict(result["rejection_counts"]), {})

    def test_provider_build_is_deterministic_under_reordered_inputs(self) -> None:
        entry = _accepted_entry(self.fixture.archive)
        other = _accepted_entry(
            self.fixture.archive,
            before_text=DRAFT_TEXT,
            after_text=SECOND_LANDED_TEXT,
        )
        first = build_idiom_atlas_provider(
            _manifest(),
            [self.fixture.target()],
            [entry, other],
            [_context()],
            archive=self.fixture.archive,
        )
        second = build_idiom_atlas_provider(
            _manifest(),
            [self.fixture.target()],
            [other, entry],
            [_context()],
            archive=self.fixture.archive,
        )
        self.assertEqual(first.provider_identity, second.provider_identity)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_ported_replay_applies_context_anchored_idiom(self) -> None:
        entry = _accepted_entry(self.fixture.archive)
        target = self.fixture.target(draft_bytes=PORTED_DRAFT_TEXT.encode("utf-8"))
        provider = build_idiom_atlas_provider(
            _manifest(), [target], [entry], [_context()], archive=self.fixture.archive
        )
        result = provider.callback(Recipient.from_dict({"recipient_id": RECIPIENT}))
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate.source, PORTED_LANDED_TEXT)
        self.assertEqual(candidate.provenance[0]["replay_modes"], ("ported",))

    def test_budget_limit_overflows_deterministically(self) -> None:
        entry = _accepted_entry(self.fixture.archive)
        other = _accepted_entry(
            self.fixture.archive,
            before_text=DRAFT_TEXT,
            after_text=SECOND_LANDED_TEXT,
        )
        provider = build_idiom_atlas_provider(
            _manifest(budget_limit=1),
            [self.fixture.target()],
            [entry, other],
            [_context()],
            archive=self.fixture.archive,
        )
        result = provider.callback(Recipient.from_dict({"recipient_id": RECIPIENT}))
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["completion_reason"], "budget_exhausted")
        self.assertIsNone(result.get("refusal_code"))
        self.assertEqual(dict(result["rejection_counts"])["budget_exhausted"], 1)


class ApplicabilityRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = IdiomAtlasFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def _result(self, **kwargs) -> dict:
        entry = kwargs.pop("entry", _accepted_entry(self.fixture.archive))
        contexts = kwargs.pop("contexts", [_context()])
        manifest = kwargs.pop("manifest", _manifest())
        target = kwargs.pop("target", None) or self.fixture.target(
            draft_bytes=kwargs.pop("draft_bytes", None)
        )
        provider = build_idiom_atlas_provider(
            manifest, [target], [entry], contexts, archive=self.fixture.archive
        )
        return dict(
            provider.callback(Recipient.from_dict({"recipient_id": RECIPIENT}))
        )

    def test_compiler_mismatch_idiom_is_never_applied(self) -> None:
        entry = _accepted_entry(self.fixture.archive, compiler_identity=OTHER_COMPILER)
        result = self._result(entry=entry)
        self.assertEqual(result["candidates"], ())
        self.assertEqual(result["completion_reason"], "inapplicable")
        self.assertEqual(result["refusal_code"], "idiom_atlas_no_applicable_idiom")
        self.assertEqual(dict(result["rejection_counts"])["compiler_mismatch"], 1)

    def test_idiom_without_completed_lineage_support_is_never_applied(self) -> None:
        result = self._result(contexts=[_context(compiler_identity=OTHER_COMPILER)])
        self.assertEqual(result["candidates"], ())
        self.assertEqual(result["completion_reason"], "inapplicable")
        self.assertEqual(dict(result["rejection_counts"])["no_lineage_support"], 1)

    def test_patch_conflict_is_a_typed_rejection(self) -> None:
        result = self._result(draft_bytes=UNRELATED_TEXT.encode("utf-8"))
        self.assertEqual(result["candidates"], ())
        self.assertEqual(result["completion_reason"], "inapplicable")
        self.assertEqual(dict(result["rejection_counts"])["patch_conflict"], 1)

    def test_negative_corpus_evidence_leaves_the_atlas_empty(self) -> None:
        result = self._result(entry=_negative_promotion_entry())
        self.assertEqual(result["candidates"], ())
        self.assertEqual(result["completion_reason"], "inapplicable")
        self.assertEqual(result["refusal_code"], "idiom_atlas_corpus_empty")
        self.assertEqual(result["attempts"], 0)


class BuildRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = IdiomAtlasFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def _entry(self):
        return _accepted_entry(self.fixture.archive)

    def test_unarchived_idiom_artifact_refuses_the_build(self) -> None:
        with self.assertRaises(IdiomAtlasArtifactError):
            build_idiom_atlas_provider(
                _manifest(),
                [self.fixture.target()],
                [_accepted_entry(self.fixture.archive, archived=False)],
                [_context()],
                archive=self.fixture.archive,
            )

    def test_target_outside_manifest_subset_refuses(self) -> None:
        target = IdiomAtlasTargetInput(
            recipient_id="us:TEST:func_other",
            target_identity=TARGET,
            draft_artifact=self.fixture.draft_ref,
            draft_bytes=DRAFT_TEXT.encode("utf-8"),
        )
        with self.assertRaises(IdiomAtlasSubsetViolation):
            build_idiom_atlas_provider(
                _manifest(), [target], [self._entry()], [_context()],
                archive=self.fixture.archive,
            )

    def test_target_identity_mismatch_refuses(self) -> None:
        target = IdiomAtlasTargetInput(
            recipient_id=RECIPIENT,
            target_identity=_hash("other-target"),
            draft_artifact=self.fixture.draft_ref,
            draft_bytes=DRAFT_TEXT.encode("utf-8"),
        )
        with self.assertRaises(IdiomAtlasArtifactError):
            build_idiom_atlas_provider(
                _manifest(), [target], [self._entry()], [_context()],
                archive=self.fixture.archive,
            )

    def test_unselected_lane_refuses(self) -> None:
        with self.assertRaises(IdiomAtlasInputError):
            build_idiom_atlas_provider(
                _manifest(lane_selected=False),
                [self.fixture.target()],
                [self._entry()],
                [_context()],
                archive=self.fixture.archive,
            )

    def test_missing_tool_identity_refuses(self) -> None:
        with self.assertRaises(IdiomAtlasInputError):
            build_idiom_atlas_provider(
                _manifest(tool=False),
                [self.fixture.target()],
                [self._entry()],
                [_context()],
                archive=self.fixture.archive,
            )

    def test_unsupported_budget_unit_refuses(self) -> None:
        manifest = _manifest()
        manifest["lane_budgets"] = {
            IDIOM_LANE: {"unit": "seconds", "limit": 4, "consumed": 0}
        }
        with self.assertRaises(IdiomAtlasBudgetError):
            build_idiom_atlas_provider(
                manifest,
                [self.fixture.target()],
                [self._entry()],
                [_context()],
                archive=self.fixture.archive,
            )

    def test_empty_lineage_evidence_refuses(self) -> None:
        with self.assertRaises(IdiomAtlasInputError):
            build_idiom_atlas_provider(
                _manifest(),
                [self.fixture.target()],
                [self._entry()],
                [],
                archive=self.fixture.archive,
            )

    def test_untyped_corpus_entry_refuses(self) -> None:
        with self.assertRaises(IdiomAtlasInputError):
            build_idiom_atlas_provider(
                _manifest(),
                [self.fixture.target()],
                [{"kind": "draft_landed", "outcome": "accepted"}],
                [_context()],
                archive=self.fixture.archive,
            )


class RecordAndCallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = IdiomAtlasFixture()
        self.entry = _accepted_entry(self.fixture.archive)
        self.provider = build_idiom_atlas_provider(
            _manifest(),
            [self.fixture.target()],
            [self.entry],
            [_context()],
            archive=self.fixture.archive,
        )

    def tearDown(self) -> None:
        self.fixture.close()

    def test_callback_is_replay_safe(self) -> None:
        recipient = Recipient.from_dict({"recipient_id": RECIPIENT})
        first = self.provider.callback(recipient)
        first["attempts"] = 99
        second = self.provider.callback(recipient)
        self.assertIsNot(first, second)
        self.assertEqual(second["attempts"], 1)
        self.assertEqual(second["candidates"], first["candidates"])

    def test_callback_refuses_outside_subset_and_untyped_input(self) -> None:
        with self.assertRaises(IdiomAtlasSubsetViolation):
            self.provider.callback(Recipient.from_dict({"recipient_id": "us:TEST:func_x"}))
        with self.assertRaises(IdiomAtlasInputError):
            self.provider.callback({"recipient_id": RECIPIENT})

    def test_adapter_mapping_and_helpers(self) -> None:
        adapters = idiom_atlas_adapters(
            _manifest(),
            [self.fixture.target()],
            [self.entry],
            [_context()],
            archive=self.fixture.archive,
        )
        self.assertEqual(set(adapters), {IDIOM_LANE})
        result = adapters[IDIOM_LANE](Recipient.from_dict({"recipient_id": RECIPIENT}))
        self.assertEqual(result["completion_reason"], "matched_pending_oracle")
        with self.assertRaises(IdiomAtlasInputError):
            idiom_atlas_adapters(
                _manifest(lane_selected=False),
                [self.fixture.target()],
                [self.entry],
                [_context()],
                archive=self.fixture.archive,
            )

    def test_target_input_rejects_noncanonical_artifacts(self) -> None:
        forged = ArtifactRef(
            self.fixture.draft_ref.content_hash,
            "artifacts/sources/forged.c",
            "text/x-c",
            self.fixture.draft_ref.byte_size,
        )
        with self.assertRaises(IdiomAtlasArtifactError):
            IdiomAtlasTargetInput(
                recipient_id=RECIPIENT,
                target_identity=TARGET,
                draft_artifact=forged,
                draft_bytes=DRAFT_TEXT.encode("utf-8"),
            )
        with self.assertRaises(IdiomAtlasArtifactError):
            IdiomAtlasTargetInput(
                recipient_id=RECIPIENT,
                target_identity=TARGET,
                draft_artifact=self.fixture.draft_ref,
                draft_bytes=b"mutated",
            )
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasTargetInput(
                recipient_id="gba:TEST:func_test_one",
                target_identity=TARGET,
                draft_artifact=self.fixture.draft_ref,
                draft_bytes=DRAFT_TEXT.encode("utf-8"),
            )

    def test_provider_direct_construction_refuses_forged_results(self) -> None:
        recipient = self.provider.target_inputs[0]
        forged_result = dict(self.provider.results[0][1])
        forged_result["unknown_field"] = 1
        foreign_result = {
            "candidates": (),
            "attempts": 0,
            "input_identities": (self.provider.provider_identity,),
            "provenance": (),
            "rejection_counts": {},
            "completion_reason": "inapplicable",
            "refusal_code": "fixture",
            "reason": "a candidate-free result for a recipient outside the subset",
        }
        common = dict(
            lane=IDIOM_LANE,
            manifest_identity=self.provider.manifest_identity,
            config_identity=self.provider.config_identity,
            tool_identity=self.provider.tool_identity,
            provider_identity=self.provider.provider_identity,
            target_inputs=self.provider.target_inputs,
            idioms=self.provider.idioms,
            lineage_contexts=self.provider.lineage_contexts,
        )
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasProvider(results=((recipient.recipient_id, forged_result),), **common)
        with self.assertRaises(IdiomAtlasSubsetViolation):
            IdiomAtlasProvider(
                results=(("us:TEST:func_other", foreign_result),), **common
            )
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasProvider(
                results=self.provider.results,
                target_inputs=(),
                **{key: value for key, value in common.items() if key != "target_inputs"},
            )

    def test_provider_round_trip_replays_without_mining(self) -> None:
        state = self.provider.to_dict()
        encoded = json.dumps(state, sort_keys=True)
        fresh_archive = ContentAddressedArchive(self.fixture.archive.run_root)
        with mock.patch(
            "automation.search_idiom_atlas.replay_grouped_patch",
            side_effect=AssertionError("reconstruction must not replay patches"),
        ), mock.patch(
            "automation.search_idiom_atlas.port_grouped_patch",
            side_effect=AssertionError("reconstruction must not port patches"),
        ):
            restored = IdiomAtlasProvider.from_dict(
                json.loads(encoded), archive=fresh_archive
            )
        self.assertEqual(restored.to_dict(), state)
        recipient = Recipient.from_dict({"recipient_id": RECIPIENT})
        self.assertEqual(restored.callback(recipient), self.provider.callback(recipient))
        restored_candidate = restored.callback(recipient)["candidates"][0]
        self.assertEqual(restored_candidate.record.parent_candidate_ids, ())
        self.assertEqual(restored_candidate.record.depth, 0)
        self.assertEqual(
            restored_candidate.provenance[0]["base_source_identity"],
            self.fixture.draft_ref.content_hash,
        )

    def test_provider_reconstruction_rejects_archive_corruption_and_missing(self) -> None:
        state = self.provider.to_dict()
        target_path = self.fixture.archive.resolve(self.fixture.draft_ref)
        target_path.write_bytes(b"corrupt target")
        with self.assertRaises(IdiomAtlasArtifactError):
            IdiomAtlasProvider.from_dict(state, archive=self.fixture.archive)

        self.tearDown()
        self.setUp()
        self.entry = _accepted_entry(self.fixture.archive)
        self.provider = build_idiom_atlas_provider(
            _manifest(),
            [self.fixture.target()],
            [self.entry],
            [_context()],
            archive=self.fixture.archive,
        )
        state = self.provider.to_dict()
        idiom_artifact = self.entry.idiom.before
        self.fixture.archive.resolve(idiom_artifact).unlink()
        with self.assertRaises(IdiomAtlasArtifactError):
            IdiomAtlasProvider.from_dict(state, archive=self.fixture.archive)

    def test_provider_reconstruction_rejects_injection_and_forged_identities(self) -> None:
        state = self.provider.to_dict()
        injected = json.loads(json.dumps(state))
        injected["callback"] = "callable injection"
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasProvider.from_dict(injected, archive=self.fixture.archive)

        injected = json.loads(json.dumps(state))
        injected["target_inputs"][0]["draft_artifact"]["path"] = "../../outside.c"
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasProvider.from_dict(injected, archive=self.fixture.archive)

        for field in (
            "manifest_identity",
            "config_identity",
            "tool_identity",
            "provider_identity",
        ):
            forged = json.loads(json.dumps(state))
            forged[field] = _hash("forged-" + field)
            with self.subTest(field=field):
                with self.assertRaises(IdiomAtlasInputError):
                    IdiomAtlasProvider.from_dict(forged, archive=self.fixture.archive)

    def test_provider_reconstruction_rejects_altered_corpus_lineage_and_duplicates(self) -> None:
        state = self.provider.to_dict()
        altered_corpus = json.loads(json.dumps(state))
        altered_corpus["idioms"][0]["measurement"]["total"] = 999
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasProvider.from_dict(altered_corpus, archive=self.fixture.archive)

        altered_lineage = json.loads(json.dumps(state))
        altered_lineage["lineage_contexts"][0]["evaluator_identity"] = _hash(
            "forged-evaluator"
        )
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasProvider.from_dict(altered_lineage, archive=self.fixture.archive)

        duplicate_target = json.loads(json.dumps(state))
        duplicate_target["target_inputs"].append(duplicate_target["target_inputs"][0])
        with self.assertRaises(IdiomAtlasSubsetViolation):
            IdiomAtlasProvider.from_dict(duplicate_target, archive=self.fixture.archive)

        mismatched_result = json.loads(json.dumps(state))
        mismatched_result["results"][0]["candidate_ids"] = []
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasProvider.from_dict(mismatched_result, archive=self.fixture.archive)

    def test_provider_reconstruction_preserves_fail_closed_lineage_requirement(self) -> None:
        state = self.provider.to_dict()
        state["lineage_contexts"] = []
        with self.assertRaises(IdiomAtlasInputError):
            IdiomAtlasProvider.from_dict(state, archive=self.fixture.archive)


if __name__ == "__main__":
    unittest.main()
