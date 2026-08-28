import hashlib
import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_mutations import make_grouped_patch, replay_grouped_patch


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "automation" / "fixtures" / "search" / "func_us_801B001C"

SOURCE_BY_FIXTURE = {
    "base.c": "hypothesis-a0-params.c",
    "combined-score-10.c": "hypothesis-combined-70s.c",
    "final-score-0.c": "hypothesis-score-zero.c",
    "sibling-case-order.c": "hypothesis-case-param-first.c",
    "sibling-declaration-order.c": "hypothesis-decl-interleave.c",
    "sibling-parameter-order.c": "hypothesis-register-params.c",
    "sibling-register-layout.c": "hypothesis-fixed-register-order.c",
    "hypothesis-combined-70s.c": "hypothesis-combined-70s.c",
    "hypothesis-score-zero.c": "hypothesis-score-zero.c",
}

PRESERVED_SCORES = {
    "combined-score-10.c": 10,
    "final-score-0.c": 0,
}


def sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


class TestHistoricalFixture(unittest.TestCase):
    def test_fixture_metadata_keeps_preserved_lineage_boundary(self):
        metadata = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["fixture_kind"], "historical-body-fixture")
        self.assertFalse(metadata["original_permuter_lineage_available"])
        self.assertEqual(metadata["source_root"], "nonmatchings/func_us_801B001C")
        self.assertIn("unavailable", metadata["source_note"])
        self.assertIn("does not infer parentage", metadata["source_note"])
        self.assertEqual(set(metadata["sources"]), set(SOURCE_BY_FIXTURE))

        # The original paths and full-source digests are preserved as provenance
        # fields.  The original nonmatchings checkout is intentionally not
        # required: the tracked body is the only content this test can validate.
        for fixture_name, source_name in SOURCE_BY_FIXTURE.items():
            record = metadata["sources"][fixture_name]
            self.assertEqual(
                record["path"],
                "nonmatchings/func_us_801B001C/" + source_name,
            )
            self.assertRegex(
                record["source_sha256"],
                r"^sha256:[0-9a-f]{64}$",
            )
            fixture_body = (ROOT / fixture_name).read_text(encoding="utf-8")
            self.assertEqual(record["body_bytes"], len(fixture_body.encode("utf-8")))
            self.assertEqual(record["body_sha256"], sha256(fixture_body))

        self.assertEqual(set(metadata["score_evidence"]), set(PRESERVED_SCORES))
        for fixture_name, expected_score in PRESERVED_SCORES.items():
            evidence = metadata["score_evidence"][fixture_name]
            self.assertEqual(evidence["score"], expected_score)
            self.assertTrue(
                evidence["source"].startswith("nonmatchings/.adapt-scores/")
            )
            self.assertTrue(evidence["source"].endswith("/adapt-score.json"))
            self.assertIn(SOURCE_BY_FIXTURE[fixture_name], evidence["provenance"])

    def test_fixture_bodies_are_preserved_function_bodies(self):
        for path in ROOT.glob("*.c"):
            body = path.read_text(encoding="utf-8")
            self.assertIn("void func_us_801B001C(Entity* self)", body)
            self.assertNotIn("historical_fixture", body)

    def test_final_two_hunk_mutation_is_atomic(self):
        before = (ROOT / "combined-score-10.c").read_text(encoding="utf-8")
        after = (ROOT / "final-score-0.c").read_text(encoding="utf-8")
        patch = make_grouped_patch(before, after)
        self.assertTrue(patch.atomic)
        self.assertGreaterEqual(len(patch.hunks), 2)
        replay = replay_grouped_patch(before, patch)
        self.assertEqual(replay.source, after)



if __name__ == "__main__":
    unittest.main()
