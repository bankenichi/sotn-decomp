"""Behavioral strategy and durable evaluation regressions."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import unittest
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.search_archive import ContentAddressedArchive
from automation.search_permuter_worker import (
    PROTOCOL,
    best_so_far_improvements,
    execute_strategy,
    load_events,
)
from automation.search_types import (
    ScoreComponents,
    ScoreVector,
    canonical_bytes,
    hash_bytes,
)
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


def _failed_score():
    """A failed compilation score carries no total and never improves."""
    return ScoreVector(
        "failed", 1, None, ScoreComponents(0, 0, 0, 0, 0),
        ScoreComponents(1, 1, 1, 1, 1), None, None, None, None, None, None,
        "difflib", hash_bytes(b"compiler"),
    )


def _publish_event(archive, session, iteration, score_vector, source_text=None):
    """Publish one canonical evaluation event and return its artifact ref."""
    source = archive.put_source(source_text or f"int fixture_{iteration}(void) {{ return {iteration}; }}\n")
    event = {
        "protocol": PROTOCOL,
        "session_identity": session,
        "iteration": iteration,
        "evaluator_identity": hash_bytes(b"evaluator"),
        "target_identity": hash_bytes(b"target"),
        "strategy": "random",
        "provenance": {"strategy": "random", "operation": iteration},
        "source": source.to_dict(),
        "object": None,
        "disassembly": None,
        "diagnostic": None,
        "score": score_vector.to_dict(),
    }
    return archive.put_json(event, category="permuter-evaluations")


class EventIntegrityTests(unittest.TestCase):
    def test_valid_sequence_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            session = hash_bytes(b"session-valid")
            for iteration, total in enumerate((100, 90, 80), start=1):
                _publish_event(archive, session, iteration, score(total))
            events = load_events(archive, session)
            self.assertEqual([event["iteration"] for _, event in events], [1, 2, 3])

    def test_tampered_content_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            session = hash_bytes(b"session-tamper")
            _publish_event(archive, session, 1, score(100))
            evaluation_dir = Path(directory) / "artifacts" / "permuter-evaluations"
            (path,) = list(evaluation_dir.glob("*.json"))
            document = json.loads(path.read_bytes())
            # Rewrite a canonical event with a forged best score under the
            # original filename. The canonical check alone cannot refuse it
            # because the bytes are canonical; only the filename binding can.
            document["score"] = score(0).to_dict()
            path.write_bytes(canonical_bytes(document))
            # The forged bytes are canonical, so only the filename binding
            # can refuse them; assert that to keep the test honest.
            raw = path.read_bytes()
            self.assertEqual(raw, canonical_bytes(json.loads(raw)))
            with self.assertRaises(ValueError):
                load_events(archive, session)

    def test_renamed_file_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            session = hash_bytes(b"session-rename")
            _publish_event(archive, session, 1, score(100))
            evaluation_dir = Path(directory) / "artifacts" / "permuter-evaluations"
            (path,) = list(evaluation_dir.glob("*.json"))
            path.rename(path.with_name("0" * 64 + ".json"))
            with self.assertRaises(ValueError):
                load_events(archive, session)

    def test_gap_in_sequence_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            session = hash_bytes(b"session-gap")
            refs = [
                _publish_event(archive, session, iteration, score(100))
                for iteration in (1, 2, 3)
            ]
            # Delete the middle evaluation file to leave iterations 1 and 3.
            archive.resolve(refs[1]).unlink()
            with self.assertRaises(ValueError):
                load_events(archive, session)

    def test_duplicate_iteration_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            session = hash_bytes(b"session-duplicate")
            _publish_event(archive, session, 1, score(100))
            _publish_event(archive, session, 1, score(90))
            with self.assertRaises(ValueError):
                load_events(archive, session)

    def test_noncanonical_event_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            session = hash_bytes(b"session-noncanonical")
            ref = _publish_event(archive, session, 1, score(100))
            path = archive.resolve(ref)
            document = json.loads(path.read_bytes())
            # Re-serialize with whitespace so the bytes are valid JSON but not
            # the canonical form the loader requires. Rewrite under the new
            # content hash so only the canonical check can refuse it.
            pretty = json.dumps(document, indent=2, sort_keys=True).encode("utf-8")
            path.unlink()
            digest = hashlib.sha256(pretty).hexdigest()
            (path.parent / (digest + ".json")).write_bytes(pretty)
            with self.assertRaises(ValueError):
                load_events(archive, session)

    def test_other_session_events_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            first, second = hash_bytes(b"session-a"), hash_bytes(b"session-b")
            for iteration in (1, 2):
                _publish_event(archive, first, iteration, score(100))
                _publish_event(archive, second, iteration, score(50))
            events = load_events(archive, first)
            self.assertEqual([event["iteration"] for _, event in events], [1, 2])
            self.assertTrue(all(event["session_identity"] == first for _, event in events))

    def test_sparse_improvements_stay_attributable(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            session = hash_bytes(b"session-sparse")
            totals = [100, 90, 90, 80, None, 80, 70]
            for iteration, total in enumerate(totals, start=1):
                vector = _failed_score() if total is None else score(total)
                _publish_event(archive, session, iteration, vector)
            events = load_events(archive, session)
            improvements = best_so_far_improvements(events)
            self.assertEqual(
                [(entry["iteration"], entry["total"]) for entry in improvements],
                [(1, 100), (2, 90), (4, 80), (7, 70)],
            )
            for entry in improvements:
                self.assertIn("evaluation_artifact", entry)
                self.assertIn("source", entry)

    def test_ties_and_failures_never_improve(self):
        self.assertEqual(best_so_far_improvements([]), [])
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            session = hash_bytes(b"session-ties")
            for iteration, vector in enumerate(
                (_failed_score(), _failed_score()), start=1
            ):
                _publish_event(archive, session, iteration, vector)
            events = load_events(archive, session)
            self.assertEqual(best_so_far_improvements(events), [])

if __name__ == "__main__":
    unittest.main()
