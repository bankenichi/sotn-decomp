"""Focused tests for immutable compiler idiom records and patches."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation.compiler_idioms import (  # noqa: E402
    CompilerIdiomError,
    CompilerIdiomObservation,
    DraftLandedObservation,
    MeasurementError,
    deduplicate_idioms,
    make_grouped_patch,
    make_idiom_observation,
    measure_improvement,
    operator_records_for_patch,
    replay_grouped_patch,
    source_hash,
)
from automation.search_types import ArtifactRef  # noqa: E402


COMPILER = "sha256:" + "1" * 64
TOOL = "sha256:" + "2" * 64
CONFIG = "sha256:" + "3" * 64
TARGET = "sha256:" + "4" * 64


class TestCompilerIdioms(unittest.TestCase):
    def test_grouped_patch_keeps_separated_hunks_atomic_and_replayable(self) -> None:
        before = (
            "int f(int x) {\n"
            "    int value = x;\n"
            "    if (x > 0) {\n"
            "        value += 1;\n"
            "    }\n"
            "    return value;\n"
            "}\n"
        )
        after = before.replace("int value", "int result").replace(
            "return value;", "return result + 1;"
        )
        first = make_grouped_patch(before, after)
        retry = make_grouped_patch(before, after)
        self.assertEqual(first, retry)
        self.assertTrue(first.atomic)
        self.assertEqual(len(first.hunks), 2)
        replay = replay_grouped_patch(before, first)
        self.assertEqual(replay.status, "applied")
        self.assertEqual(replay.source, after)
        self.assertEqual(replay.source_hash, source_hash(after))

    def test_grouped_patch_rejects_unimplemented_formats(self) -> None:
        with self.assertRaises(CompilerIdiomError):
            make_grouped_patch("int f(void) { return 0; }\n", "int f(void) { return 1; }\n", patch_format="ast")
        with self.assertRaises(CompilerIdiomError):
            make_grouped_patch("int f(void) { return 0; }\n", "int f(void) { return 1; }\n", patch_format="canonical_tokens")

    def test_operator_records_retain_exact_text_and_stable_ids(self) -> None:
        patch = make_grouped_patch("int f(void) { return 0; }\n", "int f(void) { return 1; }\n")
        first = operator_records_for_patch(patch)
        retry = operator_records_for_patch(make_grouped_patch(
            "int f(void) { return 0; }\n", "int f(void) { return 1; }\n"
        ))
        self.assertEqual(first, retry)
        self.assertEqual(len(first), 1)
        self.assertIn("return 0", first[0].before)
        self.assertIn("return 1", first[0].after)

    def test_measurement_requires_lower_score_or_exact_target_hash(self) -> None:
        improved = measure_improvement(
            {"total": 80, "object_hash": "sha256:" + "5" * 64},
            {"total": 10, "object_hash": TARGET},
            target_object_hash=TARGET,
            evaluator_identity=COMPILER,
        )
        self.assertIsNotNone(improved)
        self.assertTrue(improved.improved)
        self.assertTrue(improved.exact)
        self.assertEqual(improved.kind, "score")
        self.assertIsNone(measure_improvement({"total": 10}, {"total": 10}))
        with self.assertRaises(MeasurementError):
            measure_improvement(
                {"total": 2},
                {"total": 1},
                target_object_hash="not-a-hash",
            )

    def test_observation_round_trip_and_dedup_support(self) -> None:
        before = "int f(void) { return 0; }\n"
        after = "int f(void) { return 1; }\n"
        patch = make_grouped_patch(before, after)
        measurement = measure_improvement(
            {"total": 5}, {"total": 2, "object_hash": TARGET}, target_object_hash=TARGET
        )
        assert measurement is not None
        draft = ArtifactRef(source_hash(before), "draft.c", "text/x-c", len(before.encode()))
        landed = ArtifactRef(source_hash(after), "landed.c", "text/x-c", len(after.encode()))
        pair = DraftLandedObservation(
            recipient_id="us:TEST:Function",
            draft=draft,
            landed=landed,
            landing_commit="a" * 40,
            compiler_identity=COMPILER,
            grouped_patches=(patch,),
            evidence=("draft:" + draft.content_hash, "landing-commit:" + "a" * 40),
            tool_identity=TOOL,
            config_identity=CONFIG,
            measurement=measurement.to_dict(),
        )
        first = make_idiom_observation(pair)
        second = make_idiom_observation(pair)
        restored = CompilerIdiomObservation.from_dict(first.to_dict())
        self.assertEqual(restored, first)
        merged = deduplicate_idioms((first, second))
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].support_count, 1)
        self.assertEqual(first.to_json(), restored.to_json())

        tampered = first.to_dict()
        tampered["observation_id"] = "sha256:" + "f" * 64
        with self.assertRaises(CompilerIdiomError):
            CompilerIdiomObservation.from_dict(tampered)

    def test_same_exact_operator_merges_across_source_bases(self) -> None:
        before = "int f(void) {\n    int value = 0;\n    int padding = 0;\n    return value;\n}\n"
        after = "int f(void) {\n    int result = 0;\n    int padding = 0;\n    return result + 1;\n}\n"
        before_two = "int g(void) {\n    int value = 0;\n    int padding = 0;\n    return value;\n}\n"
        after_two = "int g(void) {\n    int result = 0;\n    int padding = 0;\n    return result + 1;\n}\n"
        patch = make_grouped_patch(before, after)
        patch_two = make_grouped_patch(before_two, after_two)
        measurement = measure_improvement({"total": 5}, {"total": 2})
        assert measurement is not None
        first_pair = DraftLandedObservation(
            recipient_id="us:TEST:Function",
            draft=ArtifactRef(source_hash(before), "draft-f.c", "text/x-c", len(before.encode())),
            landed=ArtifactRef(source_hash(after), "landed-f.c", "text/x-c", len(after.encode())),
            landing_commit="a" * 40,
            compiler_identity=COMPILER,
            grouped_patches=(patch,),
            evidence=("pair:f",),
            measurement=measurement.to_dict(),
        )
        second_pair = DraftLandedObservation(
            recipient_id="us:TEST:Function",
            draft=ArtifactRef(source_hash(before_two), "draft-g.c", "text/x-c", len(before_two.encode())),
            landed=ArtifactRef(source_hash(after_two), "landed-g.c", "text/x-c", len(after_two.encode())),
            landing_commit="b" * 40,
            compiler_identity=COMPILER,
            grouped_patches=(patch_two,),
            evidence=("pair:g",),
            measurement=measurement.to_dict(),
        )
        merged = deduplicate_idioms((make_idiom_observation(first_pair), make_idiom_observation(second_pair)))
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].support_count, 2)
        self.assertEqual(merged[0].identity, merged[0].observation_id)


if __name__ == "__main__":
    unittest.main()
