import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_mutations import (
    apply_grouped_patch,
    make_grouped_patch,
    make_mutation_event,
    minimize_grouped_patch,
    recombine_grouped_patches,
    replay_grouped_patch,
    _preserved,
)
from automation.search_types import ScoreComponents, ScoreVector, hash_bytes


def score(total):
    return ScoreVector(
        "success", 0, total, ScoreComponents(0, 0, 0, 0, 0), ScoreComponents(1, 1, 1, 1, 1),
        hash_bytes(str(total).encode()), hash_bytes(b"signature"), None, 1, 1, None,
        "difflib", hash_bytes(b"compiler"),
    )


class TestSearchMutations(unittest.TestCase):
    def test_exact_replay_and_atomic_conflict(self):
        before = "int f(void) {\n    int x = 1;\n    return x;\n}\n"
        after = "int f(void) {\n    int x = 2;\n    return x + 1;\n}\n"
        patch = make_grouped_patch(before, after)
        replay = replay_grouped_patch(before, patch)
        self.assertEqual(replay.status, "applied")
        self.assertEqual(replay.source, after)
        changed = before.replace("int x = 1", "int x = 9")
        conflict = replay_grouped_patch(changed, patch)
        self.assertEqual(conflict.status, "conflict")
        self.assertIsNone(conflict.source)

    def test_two_hunks_are_one_group_and_recombine(self):
        before = "a\nb\nc\nd\ne\n"
        after = "a\nB\nc\nd\nE\n"
        patch = make_grouped_patch(before, after)
        self.assertTrue(patch.atomic)
        self.assertEqual(len(patch.hunks), 2)
        recombined = recombine_grouped_patches(before, (patch,))
        self.assertEqual(recombined.status, "applied")
        self.assertEqual(recombined.source, after)
        event = make_mutation_event(
            parent_candidate_id=hash_bytes(b"parent"), recipient_id="record-1",
            lane="permuter_recombine", pass_kind="recombine", mutation_seed=3,
            grouped_patch=patch, result_source_hash=hash_bytes(after.encode()),
        )
        self.assertEqual(event.grouped_patch.patch_id, patch.patch_id)
        self.assertEqual(event.replay_status, "applied")

    def test_minimization_is_bounded(self):
        before = "a\nb\nc\nd\n"
        after = "A\nb\nc\nD\n"
        patch = make_grouped_patch(before, after)
        result = minimize_grouped_patch(
            before, patch, lambda source: score(1), preservation="no_worse_scalar", max_evaluations=1
        )
        self.assertEqual(result.evaluations, 1)
        self.assertTrue(result.exhausted)
        self.assertTrue(result.patch.atomic)

    def test_preservation_never_accepts_missing_before_and_after_artifacts(self):
        failed_before = ScoreVector(
            "failed", 1, None, ScoreComponents(0, 0, 0, 0, 0),
            ScoreComponents(1, 1, 1, 1, 1), None, None, None, 3, None, None,
            "difflib", hash_bytes(b"compiler"),
        )
        failed_after = ScoreVector(
            "failed", 1, None, ScoreComponents(0, 0, 0, 0, 0),
            ScoreComponents(1, 1, 1, 1, 1), None, None, None, 3, None, None,
            "difflib", hash_bytes(b"compiler"),
        )
        self.assertFalse(_preserved(failed_before, failed_after, "object_hash"))
        self.assertFalse(_preserved(failed_before, failed_after, "full_score_vector"))


if __name__ == "__main__":
    unittest.main()
