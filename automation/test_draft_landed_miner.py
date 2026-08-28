"""Focused positive and adversarial tests for the provenance miner."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation.compiler_idioms import source_hash  # noqa: E402
from automation.draft_landed_miner import (  # noqa: E402
    MappingCommitResolver,
    DraftLandedMiner,
    ProviderError,
    RefusalCode,
    VerifiedCommit,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "search" / "draft_landed" / "pair.json"


def _identity(value: str) -> str:
    return "sha256:" + value * 64


def _case() -> tuple[list[dict], list[dict], list[dict], MappingCommitResolver]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rid = data["recipient_id"]
    draft = data["draft"].encode("utf-8")
    landed = data["landed"].encode("utf-8")
    draft_hash = source_hash(draft)
    landed_hash = source_hash(landed)
    draft_commit = data["draft_commit"]
    landing_commit = data["landing_commit"]
    compiler = data["compiler_identity"]
    tool = data["tool_identity"]
    config = data["config_identity"]
    history = [{
        "recipient_id": rid,
        "draft": {
            "path": data["draft_path"],
            "content_hash": draft_hash,
            "byte_size": len(draft),
            "media_type": "text/x-c",
            "generation_id": "generation-1",
        },
        "compiler_identity": compiler,
        "tool_identity": tool,
        "config_identity": config,
        "draft_commit": draft_commit,
    }]
    landing = [{
        "recipient_id": rid,
        "landing": {
            "path": data["landed_path"],
            "content_hash": landed_hash,
            "byte_size": len(landed),
            "media_type": "text/x-c",
        },
        "landing_commit": landing_commit,
        "compiler_identity": compiler,
        "tool_identity": tool,
        "config_identity": config,
        "score_before": {"total": 80, "object_hash": _identity("5")},
        "score_after": {"total": 10, "object_hash": data["target_object"]},
        "target_object_hash": data["target_object"],
        "verified": True,
    }]
    queue = [{
        "recipient_id": rid,
        "draft_hash": draft_hash,
        "draft_generation": "generation-1",
        "landing_commit": landing_commit,
        "compiler_identity": compiler,
        "tool_identity": tool,
        "config_identity": config,
    }]
    resolver = MappingCommitResolver({
        draft_commit: VerifiedCommit(draft_commit, files={data["draft_path"]: draft}),
        landing_commit: VerifiedCommit(landing_commit, files={data["landed_path"]: landed}),
    })
    return history, queue, landing, resolver


class TestDraftLandedMiner(unittest.TestCase):
    def test_complete_pair_emits_atomic_measured_idiom(self) -> None:
        history, queue, landing, resolver = _case()
        miner = DraftLandedMiner(
            resolver,
            compiler_identity=_case()[0][0]["compiler_identity"],
            tool_identity=_case()[0][0]["tool_identity"],
            config_identity=_case()[0][0]["config_identity"],
        )
        result = miner.mine(history, queue, landing)
        self.assertEqual(len(result.observations), 1, result.to_json())
        self.assertEqual(len(result.idioms), 1, result.to_json())
        observation = result.observations[0]
        self.assertEqual(observation.landing_commit, "2" * 40)
        self.assertEqual(len(observation.grouped_patches), 1)
        self.assertEqual(len(observation.grouped_patches[0].hunks), 2)
        self.assertIn("landing-commit:" + "2" * 40, observation.evidence)
        self.assertIn("draft-commit:" + "1" * 40, observation.evidence)
        self.assertTrue(observation.measurement["improved"])
        self.assertEqual(result.idioms[0].support_count, 1)

    def test_landing_identity_can_bind_pair_when_draft_omits_it(self) -> None:
        history, queue, landing, resolver = _case()
        history[0].pop("compiler_identity")
        queue[0].pop("compiler_identity")
        result = DraftLandedMiner(resolver).mine(history, queue, landing)
        self.assertEqual(len(result.observations), 1, result.to_json())
        self.assertEqual(len(result.idioms), 1, result.to_json())

    def test_input_order_restart_and_duplicate_replay_are_identical(self) -> None:
        history, queue, landing, resolver = _case()
        miner = DraftLandedMiner(resolver)
        first = miner.mine(history, queue, landing)
        shuffled_history = list(reversed(history))
        shuffled_queue = list(reversed(queue))
        shuffled_landing = list(reversed(landing))
        second = miner.replay(shuffled_history + history, shuffled_queue + queue, shuffled_landing + landing)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.observations[0].pair_hash, second.observations[0].pair_hash)

    def test_duplicate_evidence_merges_to_one_support_identity(self) -> None:
        history, queue, landing, resolver = _case()
        duplicate_queue = copy.deepcopy(queue[0])
        duplicate_queue["evidence_id"] = _identity("6")
        miner = DraftLandedMiner(resolver)
        first = miner.mine(history, [queue[0], duplicate_queue], landing)
        second = miner.mine(history, [duplicate_queue, queue[0]], list(reversed(landing)))
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(len(first.observations), 1)
        self.assertEqual(len(first.idioms), 1)
        self.assertEqual(first.idioms[0].support_count, 1)

    def test_conflicting_duplicate_measurement_or_ref_refuses_order_independently(self) -> None:
        history, queue, landing, resolver = _case()
        landing[0].pop("score_before")
        landing[0].pop("score_after")
        landing[0].pop("target_object_hash")
        queue[0]["before_score"] = {"total": 80}
        queue[0]["after_score"] = {"total": 10}
        conflicting_queue = copy.deepcopy(queue[0])
        conflicting_queue["after_score"] = {"total": 20}
        miner = DraftLandedMiner(resolver)
        first = miner.mine(history, [queue[0], conflicting_queue], landing)
        second = miner.mine(history, [conflicting_queue, queue[0]], landing)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertFalse(first.observations)
        self.assertFalse(first.idioms)
        self.assertIn(RefusalCode.DUPLICATE_CONFLICT, {item.code for item in first.refusals})

        history, queue, landing, resolver = _case()
        landing_a = copy.deepcopy(landing[0])
        landing_a["provenance_id"] = _identity("7")
        landing_a["landing_ref"] = "branch-a"
        landing_b = copy.deepcopy(landing[0])
        landing_b["provenance_id"] = _identity("8")
        landing_b["landing_ref"] = "branch-b"
        queue_a = copy.deepcopy(queue[0])
        queue_a["landing_id"] = landing_a["provenance_id"]
        queue_b = copy.deepcopy(queue[0])
        queue_b["landing_id"] = landing_b["provenance_id"]
        first = DraftLandedMiner(resolver).mine(
            history, [queue_a, queue_b], [landing_a, landing_b]
        )
        second = DraftLandedMiner(resolver).mine(
            history, [queue_b, queue_a], [landing_b, landing_a]
        )
        self.assertEqual(first.to_json(), second.to_json())
        self.assertFalse(first.observations)
        self.assertFalse(first.idioms)
        self.assertIn(RefusalCode.DUPLICATE_CONFLICT, {item.code for item in first.refusals})

    def test_two_draft_generations_without_selector_refuse(self) -> None:
        history, queue, landing, resolver = _case()
        second = copy.deepcopy(history[0])
        second["draft"]["generation_id"] = "generation-2"
        second["draft"]["content_hash"] = source_hash(b"another draft\n")
        second["draft_commit"] = "3" * 40
        resolver = MappingCommitResolver({
            "1" * 40: VerifiedCommit("1" * 40, files={history[0]["draft"]["path"]: b""}),
            "2" * 40: VerifiedCommit("2" * 40, files={landing[0]["landing"]["path"]: b""}),
            "3" * 40: VerifiedCommit("3" * 40, files={second["draft"]["path"]: b"another draft\n"}),
        })
        queue[0].pop("draft_generation")
        queue[0].pop("draft_hash")
        result = DraftLandedMiner(resolver).mine(history + [second], queue, landing)
        self.assertFalse(result.idioms)
        self.assertIn(RefusalCode.AMBIGUOUS_DRAFT, {item.code for item in result.refusals})

    def test_missing_commit_and_adjacency_alone_do_not_claim_success(self) -> None:
        history, queue, landing, resolver = _case()
        landing[0].pop("landing_commit")
        queue[0].pop("landing_commit")
        result = DraftLandedMiner(resolver).mine(history, queue, landing)
        self.assertFalse(result.observations)
        self.assertIn(RefusalCode.MISSING_LANDING_COMMIT, {item.code for item in result.refusals})

        history, queue, landing, resolver = _case()
        landing[0].pop("score_before")
        landing[0].pop("score_after")
        landing[0].pop("target_object_hash")
        result = DraftLandedMiner(resolver).mine(history, queue, landing)
        self.assertEqual(len(result.observations), 1)
        self.assertFalse(result.idioms)
        self.assertIn(RefusalCode.UNMEASURED, {item.code for item in result.refusals})

    def test_corrupt_blob_and_mismatched_identity_refuse_closed(self) -> None:
        history, queue, landing, resolver = _case()
        bad = MappingCommitResolver({
            "1" * 40: VerifiedCommit("1" * 40, files={history[0]["draft"]["path"]: b"corrupt\n"}),
            "2" * 40: VerifiedCommit("2" * 40, files={landing[0]["landing"]["path"]: b"corrupt\n"}),
        })
        result = DraftLandedMiner(bad).mine(history, queue, landing)
        self.assertFalse(result.observations)
        self.assertIn(RefusalCode.CORRUPT_ARTIFACT, {item.code for item in result.refusals})

        history, queue, landing, resolver = _case()
        history[0]["compiler_identity"] = _identity("9")
        result = DraftLandedMiner(resolver).mine(history, queue, landing)
        self.assertFalse(result.observations)
        self.assertIn(RefusalCode.IDENTITY_MISMATCH, {item.code for item in result.refusals})

    def test_provider_requires_full_immutable_commit_identity(self) -> None:
        with self.assertRaises(ProviderError):
            MappingCommitResolver({"main": {"src/f.c": b"x"}})

    def test_internal_type_errors_are_not_retried(self) -> None:
        history, queue, landing, resolver = _case()

        class TypeErrorBlobProvider:
            def __init__(self, base):
                self.base = base
                self.calls = 0

            def resolve_commit(self, ref):
                commit = self.base.resolve_commit(ref)
                return VerifiedCommit(commit.commit_id, ref=commit.ref)

            def read_blob(self, commit, path):
                self.calls += 1
                raise TypeError("internal blob type error")

        provider = TypeErrorBlobProvider(resolver)
        result = DraftLandedMiner(provider).mine(history, queue, landing)
        self.assertEqual(provider.calls, 1)
        self.assertIn(RefusalCode.PROVIDER_FAILURE, {item.code for item in result.refusals})

        class TypeErrorEvaluator:
            def __init__(self):
                self.calls = 0

            def __call__(self, draft_source, landed_source):
                self.calls += 1
                raise TypeError("internal evaluator type error")

        evaluator = TypeErrorEvaluator()
        result = DraftLandedMiner(resolver, evaluator=evaluator).mine(history, queue, landing)
        self.assertEqual(evaluator.calls, 1)
        self.assertIn(RefusalCode.UNMEASURED, {item.code for item in result.refusals})


if __name__ == "__main__":
    unittest.main()
