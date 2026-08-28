import unittest
from dataclasses import replace
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_frontier import (
    BoundedParetoFrontier,
    CandidateGraph,
    CrossRecipientCacheError,
    RecipientLocalEvaluationCache,
    SearchFrontier,
    dominates,
)
from automation.search_types import (
    ArtifactRef,
    CandidateRecord,
    EvaluationEvent,
    ScoreComponents,
    ScoreDeltas,
    ScoreVector,
    SearchValidationError,
    hash_bytes,
)


def vector(values, total, signature):
    return ScoreVector(
        "success", 1, total, ScoreComponents(*values), ScoreComponents(1, 1, 1, 1, 1),
        hash_bytes(str(values).encode()),
        hash_bytes(signature.encode()), None, 5, 5, None, "difflib", hash_bytes(b"compiler"),
    )


def candidate(number, values, total, signature, recipient="record-1"):
    source_hash = hash_bytes(("source-" + str(number)).encode())
    artifact = ArtifactRef(source_hash, "artifacts/sources/" + source_hash[7:] + ".c", "text/x-c", 1)
    return CandidateRecord(
        source_hash, recipient, artifact, (), None,
        "permuter_random", 0, vector(values, total, signature), "evaluated",
    )


class TestSearchFrontier(unittest.TestCase):
    def test_dominance_and_scalar_elite_are_independent(self):
        a = candidate(1, (0, 2, 0, 0, 0), 10, "a")
        b = candidate(2, (1, 0, 0, 0, 0), 20, "b")
        self.assertFalse(dominates(a.evaluation, b.evaluation))
        frontier = BoundedParetoFrontier(cap=2)
        frontier.consider(a)
        frontier.consider(b)
        self.assertEqual(frontier.scalar_elite_id, a.candidate_id)
        self.assertEqual(set(frontier.pareto_ids), {a.candidate_id, b.candidate_id})

    def test_cache_is_recipient_local(self):
        cache = RecipientLocalEvaluationCache()
        key = cache.put("record-1", hash_bytes(b"candidate"), hash_bytes(b"evaluator"), 3)
        self.assertEqual(cache.get_by_key(key, recipient_id="record-1"), 3)
        self.assertIsNone(cache.get("record-2", hash_bytes(b"candidate"), hash_bytes(b"evaluator")))
        with self.assertRaises(CrossRecipientCacheError):
            cache.get_by_key(key, recipient_id="record-2")

    def test_cap_is_bounded_and_signature_diversity_survives(self):
        frontier = BoundedParetoFrontier(cap=2)
        first = candidate(1, (0, 0, 0, 0, 1), 1, "first")
        second = candidate(2, (0, 0, 0, 1, 0), 2, "second")
        third = candidate(3, (0, 0, 1, 0, 0), 3, "third")
        for item in (third, first, second):
            frontier.consider(item)
        self.assertLessEqual(len(frontier.pareto_ids), 2)
        self.assertEqual(frontier.scalar_elite_id, first.candidate_id)
        self.assertIn(first.candidate_id, frontier.pareto_ids)

    def test_frontier_slots_are_recipient_local(self):
        first = candidate(1, (0, 2, 0, 0, 0), 10, "a", recipient="record-1")
        second = candidate(2, (1, 0, 0, 0, 0), 1, "b", recipient="record-2")
        frontier = BoundedParetoFrontier(cap=1)
        frontier.consider(first)
        frontier.consider(second)
        self.assertEqual(frontier.scalar_elite_for("record-1"), first.candidate_id)
        self.assertEqual(frontier.scalar_elite_for("record-2"), second.candidate_id)
        self.assertEqual(frontier.pareto_for("record-1"), (first.candidate_id,))
        self.assertEqual(frontier.pareto_for("record-2"), (second.candidate_id,))
        self.assertIsNone(frontier.scalar_elite_id)
        self.assertEqual(frontier.pareto_ids, ())

    def test_add_evaluation_updates_previously_unevaluated_candidate(self):
        source_hash = hash_bytes(b"pending-source")
        artifact = ArtifactRef(source_hash, "artifacts/sources/" + source_hash[7:] + ".c", "text/x-c", 14)
        pending = CandidateRecord(
            source_hash, "record-1", artifact, (), None, "upstream_current", 0, None, "materialized"
        )
        after = vector((0, 0, 0, 0, 0), 0, "zero")
        cache_key = RecipientLocalEvaluationCache.key_for("record-1", source_hash, after.compiler_identity)
        event = EvaluationEvent(
            "task-eval", "record-1", source_hash, None, None, after,
            ScoreDeltas(0, 0, 0, 0, 0, 0), cache_key, "zero_pending_oracle",
        )
        frontier = SearchFrontier(cap=2)
        frontier.add_candidate(pending)
        decision = frontier.add_evaluation(event)
        self.assertIsNotNone(decision)
        updated = frontier.graph.get(source_hash)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.evaluation, after)
        self.assertEqual(frontier.scalar_elite_for("record-1"), source_hash)

    def test_candidate_graph_rejects_conflicting_same_id_metadata(self):
        first = candidate(9, (0, 0, 0, 0, 0), 0, "first")
        graph = CandidateGraph()
        graph.add(first)
        with self.assertRaises(Exception):
            graph.add(replace(first, recipient_id="record-2"))


if __name__ == "__main__":
    unittest.main()
