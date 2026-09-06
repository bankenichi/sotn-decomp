"""Behavioral strategy and durable evaluation regressions."""
from __future__ import annotations
import sys
from pathlib import Path
import unittest
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.search_permuter_worker import execute_strategy
from automation.test_search_mutations import score

class StrategyTests(unittest.TestCase):
    def test_worker_session_lock_refuses_overlap_and_releases_after_exit(self):
        from automation.search_process_lock import worker_session_lock, WorkerStillRunning
        from automation.search_types import hash_bytes
        with tempfile.TemporaryDirectory() as directory:
            root, session = Path(directory), hash_bytes(b"worker")
            with worker_session_lock(root, session):
                with self.assertRaises(WorkerStillRunning):
                    with worker_session_lock(root, session):
                        self.fail("second worker acquired the active session")
            with worker_session_lock(root, session):
                pass

    def test_preserved_sources_cannot_cross_recipient_overlays(self):
        from automation.search_source_context import candidate_belongs_to_recipient
        recipient = "us:ST/RNZ1:SpikesApplyDamage"
        self.assertFalse(candidate_belongs_to_recipient(
            "record : us:ST/RNO2:SpikesApplyDamage\n", Path("SpikesApplyDamage.c"), recipient))
        self.assertFalse(candidate_belongs_to_recipient(
            "void SpikesApplyDamage(void) {}", Path("us_ST_RNO2_SpikesApplyDamage.v0001.c"), recipient))
        self.assertTrue(candidate_belongs_to_recipient(
            "record : " + recipient + "\n", Path("SpikesApplyDamage.c"), recipient))

    def test_targeted_requests_restricted_mutations_and_random_does_not(self):
        for strategy in ("random", "targeted"):
            calls, measured = [], []
            def mutate(operation, donor, targeted):
                calls.append((operation, donor, targeted))
                return "new source", {"pass_kind": "fixture"}
            execute_strategy("base", mutate, lambda s, p: measured.append((s, p)),
                             strategy=strategy, operation=7)
            self.assertEqual(calls, [(7, 0, strategy == "targeted")])
            self.assertEqual(measured[0][1]["strategy"], strategy)

    def test_recombination_applies_two_independent_donor_changes(self):
        base = "".join(f"line {n}\n" for n in range(20))
        first, second = base.replace("line 1\n", "donor one\n"), base.replace("line 18\n", "donor two\n")
        measured = []
        result = execute_strategy(
            base, lambda op, donor, targeted: ((first, second)[donor], {"donor": donor}),
            lambda s, p: measured.append(s), strategy="recombine", operation=3,
        )
        self.assertEqual(len(measured), 1)
        self.assertIn("donor one", measured[0])
        self.assertIn("donor two", measured[0])
        self.assertEqual(len(result["parents"]), 2)
        self.assertEqual(result["conflict_patch_ids"], [])

    def test_recombination_conflict_is_retained_without_fabricated_evaluation(self):
        base = "int x;\n"
        measured = []
        result = execute_strategy(
            base, lambda op, donor, targeted: (("int a;\n", "int b;\n")[donor], {}),
            lambda s, p: measured.append(s), strategy="recombine", operation=0,
        )
        self.assertEqual(measured, [])
        self.assertTrue(result["conflict_patch_ids"])

    def test_ddmin_removes_a_measured_nonessential_hunk(self):
        base = "".join(f"line {n}\n" for n in range(20))
        changed = base.replace("line 1\n", "first change\n").replace("line 18\n", "last change\n")
        measured = []
        def evaluate(source, provenance):
            measured.append(source)
            return score(1)
        result = execute_strategy(
            base, lambda *_: (changed, {}), evaluate, strategy="ddmin", operation=0,
        )
        self.assertGreater(len(measured), 1)
        self.assertEqual(len(result["removed_ordinals"]), 1)
        self.assertEqual(len(result["minimized_patch"]["hunks"]), 1)

if __name__ == "__main__":
    unittest.main()
