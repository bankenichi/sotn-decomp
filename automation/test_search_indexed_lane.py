"""Focused tests for archive-backed indexed donor lane adapters."""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ArtifactRef
from automation.search_coordinator import SearchCoordinator, TaskResult
from automation.search_donor_query import (
    DonorQuery,
    DonorQueryResult,
    DonorSemanticClaim,
    bind_donor_query,
    query_donor_index,
)
from automation.search_indexed_lane import indexed_lane_adapter
from automation.search_lanes import (
    CandidateIdentityMismatch,
    LaneCandidate,
    LaneError,
    LaneAdapters,
    Recipient,
    SubsetViolation,
    run_lane,
)
from automation.search_recovery import recover_run
from automation.search_types import CandidateRecord, hash_bytes, hash_canonical
from automation.test_search_donor_query import _index_fixture, _query
from automation.test_search_lanes import make_manifest


TARGET_BODY = "int fn(void) { return 9; }\n"


def recipient() -> Recipient:
    return Recipient(
        recipient_id="us:ST:fn",
        overlay="ST",
        function="fn",
        metadata={"target_file": "src/lane.c"},
    )


def target_candidate(item: Recipient, lane: str) -> LaneCandidate:
    source = TARGET_BODY
    candidate_id = hash_bytes(source.encode("utf-8"))
    artifact = ArtifactRef(
        candidate_id,
        "artifacts/sources/" + candidate_id.removeprefix("sha256:") + ".c",
        "text/x-c",
        len(source.encode("utf-8")),
    )
    record = CandidateRecord(
        candidate_id=candidate_id,
        recipient_id=item.recipient_id,
        source_artifact=artifact,
        parent_candidate_ids=(),
        mutation_id=None,
        lane=lane,
        depth=0,
        evaluation=None,
        status="materialized",
    )
    return LaneCandidate(record, source)


class IndexedLaneAdapterTests(unittest.TestCase):
    def test_adapter_binds_once_and_renders_only_semantic_claims(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            query_calls = []
            renderer_calls = []

            def query_for(received: Recipient) -> DonorQuery:
                query_calls.append(received.recipient_id)
                return _query(recipient_id=received.recipient_id)

            def render(received: Recipient, claims: tuple[DonorSemanticClaim, ...]):
                renderer_calls.append((received, claims))
                self.assertTrue(all(isinstance(claim, DonorSemanticClaim) for claim in claims))
                self.assertTrue(all(not hasattr(claim, "source") for claim in claims))
                self.assertTrue(all(not hasattr(claim, "body") for claim in claims))
                self.assertTrue(all(not hasattr(claim, "metadata") for claim in claims))
                return target_candidate(received, "cfg_dataflow")

            with patch(
                "automation.search_indexed_lane.bind_donor_query",
                wraps=bind_donor_query,
            ) as binder:
                adapter = indexed_lane_adapter(
                    index,
                    lane="cfg_dataflow",
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                    query_for=query_for,
                    render_target_context=render,
                )
                first = adapter(item)
                second = adapter(item)

            self.assertEqual(binder.call_count, 1)
            self.assertEqual(query_calls, [item.recipient_id, item.recipient_id])
            self.assertEqual(len(renderer_calls), 2)
            self.assertEqual(first["candidates"], second["candidates"])
            self.assertEqual(first["completion_reason"], "matched_pending_oracle")

    def test_renderer_receives_one_claim_per_identity_deterministically(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            rendered_claims = []

            def render(received: Recipient, claims: tuple[DonorSemanticClaim, ...]):
                rendered_claims.append(tuple(claim.claim_identity for claim in claims))
                return target_candidate(received, "multi_donor")

            adapter = indexed_lane_adapter(
                index,
                lane="multi_donor",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda received: _query(recipient_id=received.recipient_id),
                render_target_context=render,
            )
            first = adapter(item)
            second = adapter(item)

            self.assertEqual(len(index.entries), 4)
            self.assertEqual(len(rendered_claims), 2)
            self.assertEqual(rendered_claims[0], rendered_claims[1])
            self.assertEqual(rendered_claims[0], tuple(sorted(set(rendered_claims[0]))))
            self.assertEqual(len(rendered_claims[0]), 1)
            self.assertEqual(first, second)

    def test_matched_provenance_contains_query_hits_revisions_generation_and_artifact(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            query = _query(recipient_id=item.recipient_id)
            adapter = indexed_lane_adapter(
                index,
                lane="multi_donor",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda _item: query,
                render_target_context=lambda received, _claims: target_candidate(
                    received, "multi_donor"
                ),
            )
            raw = adapter(item)
            summary = raw["provenance"][0]

            self.assertEqual(summary["query_identity"], query.query_identity)
            self.assertEqual(summary["status"], "matched")
            self.assertEqual(summary["generation_id"], index.generation_id)
            self.assertEqual(summary["artifact"], index.artifact.to_dict())
            self.assertEqual(summary["provenance_artifact"], index.artifact.to_dict())
            self.assertEqual(
                summary["artifact_identity"],
                hash_canonical(index.artifact.to_dict()),
            )
            self.assertEqual(summary["receipt"], None)
            self.assertEqual(len(summary["entry_ids"]), len(summary["revision_identities"]))
            self.assertEqual(
                {
                    item["entry_id"]
                    for item in raw["provenance"]
                    if "entry_id" in item
                },
                set(summary["entry_ids"]),
            )
            self.assertTrue(
                all(
                    item["revision_identity"]
                    for item in raw["provenance"]
                    if "revision_identity" in item
                )
            )

    def test_empty_incompatible_ambiguous_and_stale_results_refuse_without_rendering(self) -> None:
        cases = (
            ("empty", None, lambda _index: _query(symbol="missing"), "donor_query_empty"),
            (
                "incompatible",
                lambda _revision, evidence: replace(evidence, compatible=False),
                lambda _index: _query(),
                "donor_query_incompatible",
            ),
            (
                "ambiguous",
                lambda revision, evidence: replace(
                    evidence, signature="sig:" + revision.version
                ),
                lambda _index: _query(),
                "donor_query_ambiguous",
            ),
        )
        for status, builder, make_query, refusal_code in cases:
            with self.subTest(status=status):
                with _index_fixture(builder) as (
                    index,
                    archive,
                    gate_archive,
                    _gate,
                    _calls,
                    _sources,
                ):
                    item = recipient()
                    query_calls = []
                    render_calls = []
                    query = make_query(index)

                    def query_for(received: Recipient) -> DonorQuery:
                        query_calls.append(received.recipient_id)
                        return query

                    def render(received: Recipient, _claims):
                        render_calls.append(received.recipient_id)
                        return target_candidate(received, "cfg_dataflow")

                    adapter = indexed_lane_adapter(
                        index,
                        lane="cfg_dataflow",
                        expected_binding=index.binding,
                        index_archive=archive,
                        integration_archive=gate_archive,
                        query_for=query_for,
                        render_target_context=render,
                    )
                    raw = adapter(item)
                    self.assertEqual(raw["candidates"], ())
                    self.assertEqual(raw["refusal_code"], refusal_code)
                    self.assertEqual(raw["provenance"][0]["status"], status)
                    self.assertEqual(raw["completion_reason"], "search_space_exhausted")
                    self.assertEqual(query_calls, [item.recipient_id])
                    self.assertEqual(render_calls, [])
                    if status == "empty":
                        self.assertIsNone(raw["provenance"][0]["receipt"])
                    else:
                        self.assertIsInstance(raw["provenance"][0]["receipt"], dict)

        with _index_fixture() as (
            index,
            archive,
            gate_archive,
            _gate,
            _calls,
            _sources,
        ):
            item = recipient()
            expected = replace(index.binding, generation_ordinal=2)
            adapter = indexed_lane_adapter(
                index,
                lane="cfg_dataflow",
                expected_binding=expected,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda _item: _query(),
                render_target_context=lambda received, _claims: target_candidate(
                    received, "cfg_dataflow"
                ),
            )
            raw = adapter(item)
            self.assertEqual(raw["candidates"], ())
            self.assertEqual(raw["refusal_code"], "donor_query_stale")
            self.assertEqual(raw["provenance"][0]["status"], "stale")
            self.assertEqual(raw["completion_reason"], "inapplicable")
            self.assertIsInstance(raw["provenance"][0]["receipt"], dict)

    def test_provenance_and_inputs_bind_claim_and_refusal_identities(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            adapter = indexed_lane_adapter(
                index,
                lane="cfg_dataflow",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda received: _query(recipient_id=received.recipient_id),
                render_target_context=lambda received, _claims: target_candidate(
                    received, "cfg_dataflow"
                ),
            )
            raw = adapter(item)
            summary = raw["provenance"][0]
            claim_ids = summary["claim_identities"]
            self.assertEqual(claim_ids, sorted(set(claim_ids)))
            self.assertEqual(summary["lane"], "cfg_dataflow")
            self.assertEqual(summary["recipient_id"], item.recipient_id)
            self.assertTrue(set(claim_ids).issubset(raw["input_identities"]))
            for edge in raw["provenance"]:
                self.assertEqual(edge["lane"], "cfg_dataflow")
                self.assertEqual(edge["recipient_id"], item.recipient_id)
            self.assertTrue(
                all(
                    edge["claim_identity"] in claim_ids
                    for edge in raw["provenance"]
                    if "claim_identity" in edge
                )
            )

        def incompatible(_revision, evidence):
            return replace(evidence, compatible=False)

        with _index_fixture(incompatible) as (
            index,
            archive,
            gate_archive,
            _gate,
            _calls,
            _sources,
        ):
            item = recipient()
            adapter = indexed_lane_adapter(
                index,
                lane="cfg_dataflow",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda received: _query(recipient_id=received.recipient_id),
                render_target_context=lambda received, _claims: target_candidate(
                    received, "cfg_dataflow"
                ),
            )
            raw = adapter(item)
            summary = raw["provenance"][0]
            receipt = summary["receipt"]
            self.assertEqual(summary["claim_identities"], [])
            self.assertIsInstance(receipt, dict)
            self.assertIn(receipt["receipt_id"], raw["input_identities"])
            self.assertEqual(summary["lane"], "cfg_dataflow")
            self.assertEqual(summary["recipient_id"], item.recipient_id)

    def test_rejects_query_recipient_mismatch_before_rendering(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            render_calls = []
            adapter = indexed_lane_adapter(
                index,
                lane="multi_donor",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda _item: _query(recipient_id="other:ST:fn"),
                render_target_context=lambda received, _claims: render_calls.append(received),
            )
            with self.assertRaises(SubsetViolation):
                adapter(recipient())
            self.assertEqual(render_calls, [])

    def test_rejects_renderer_recipient_and_lane_mismatches(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            other = Recipient("other:ST:fn", "ST", "fn")
            adapter = indexed_lane_adapter(
                index,
                lane="cfg_dataflow",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda _item: _query(),
                render_target_context=lambda _received, _claims: target_candidate(
                    other, "cfg_dataflow"
                ),
            )
            with self.assertRaises(SubsetViolation):
                adapter(item)

            adapter = indexed_lane_adapter(
                index,
                lane="cfg_dataflow",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda _item: _query(),
                render_target_context=lambda received, _claims: target_candidate(
                    received, "multi_donor"
                ),
            )
            with self.assertRaises(LaneError):
                adapter(item)

    def test_rejects_renderer_source_identity_mismatch(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            forged = target_candidate(item, "multi_donor")
            object.__setattr__(forged, "source", "int fn(void) { return 10; }\n")
            adapter = indexed_lane_adapter(
                index,
                lane="multi_donor",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda _item: _query(),
                render_target_context=lambda _received, _claims: forged,
            )
            with self.assertRaises(CandidateIdentityMismatch):
                adapter(item)

    def test_renderer_requires_canonical_source_artifact_metadata(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            valid = target_candidate(item, "multi_donor")
            artifact = valid.candidate.source_artifact
            cases = (
                (
                    "path",
                    LaneCandidate(
                        replace(
                            valid.candidate,
                            source_artifact=replace(
                                artifact,
                                path="artifacts/sources/not-the-candidate.c",
                            ),
                        ),
                        valid.source,
                    ),
                ),
                (
                    "media_type",
                    LaneCandidate(
                        replace(
                            valid.candidate,
                            source_artifact=replace(
                                artifact,
                                media_type="application/json",
                            ),
                        ),
                        valid.source,
                    ),
                ),
                (
                    "byte_size",
                    LaneCandidate(
                        replace(
                            valid.candidate,
                            source_artifact=replace(
                                artifact,
                                byte_size=artifact.byte_size + 1,
                            ),
                        ),
                        valid.source,
                    ),
                ),
                ("missing_source", LaneCandidate(valid.candidate, "")),
            )
            for name, forged in cases:
                with self.subTest(name=name):
                    adapter = indexed_lane_adapter(
                        index,
                        lane="multi_donor",
                        expected_binding=index.binding,
                        index_archive=archive,
                        integration_archive=gate_archive,
                        query_for=lambda _item: _query(),
                        render_target_context=lambda _received, _claims, value=forged: value,
                    )
                    with self.assertRaises(CandidateIdentityMismatch):
                        adapter(item)

    def test_rejects_query_artifact_metadata_mismatch_before_rendering(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            query = _query()
            valid = query_donor_index(
                index,
                query,
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            forged = replace(
                valid,
                provenance_artifact=replace(
                    valid.provenance_artifact,
                    byte_size=valid.provenance_artifact.byte_size + 1,
                ),
            )
            render_calls = []
            with patch(
                "automation.search_indexed_lane.bind_donor_query",
                return_value=lambda _query: forged,
            ):
                adapter = indexed_lane_adapter(
                    index,
                    lane="cfg_dataflow",
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                    query_for=lambda _item: query,
                    render_target_context=lambda received, _claims: render_calls.append(
                        received
                    ),
                )
                with self.assertRaises(LaneError):
                    adapter(recipient())
            self.assertEqual(render_calls, [])

    def test_rejects_unsupported_lane_and_renderer_shape(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            with self.assertRaises(LaneError):
                indexed_lane_adapter(
                    index,
                    lane="upstream_current",
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                    query_for=lambda _item: _query(),
                    render_target_context=lambda _received, _claims: (),
                )
            adapter = indexed_lane_adapter(
                index,
                lane="cfg_dataflow",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda _item: _query(),
                render_target_context=lambda _received, _claims: {"candidate": "invalid"},
            )
            with self.assertRaises(LaneError):
                adapter(recipient())

    def test_matched_candidate_reaches_ordinary_lane_and_coordinator_recovery(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            manifest = make_manifest(item.recipient_id)
            adapter = indexed_lane_adapter(
                index,
                lane="cfg_dataflow",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda received: _query(recipient_id=received.recipient_id),
                render_target_context=lambda received, _claims: target_candidate(
                    received, "cfg_dataflow"
                ),
            )
            batch = run_lane(
                manifest,
                "cfg_dataflow",
                {item.recipient_id: item},
                adapters=LaneAdapters.from_mapping({"cfg_dataflow": adapter}),
                repo_root=archive.run_root.parent,
            )
            self.assertEqual(len(batch.candidates), 1)
            self.assertEqual(batch[0].candidates[0].recipient_id, item.recipient_id)
            self.assertTrue(
                any(
                    entry.get("generation_id") == index.generation_id
                    for entry in batch[0].provenance
                )
            )

            run_root = archive.run_root.parent / "coordinator"
            coordinator = SearchCoordinator(run_root, manifest)
            for prior_lane in (
                "upstream_current",
                "upstream_pinned",
                "upstream_open_pr",
                "mipsmatch_exact",
                "preserved_candidate",
            ):
                coordinator.complete_tier(
                    item.recipient_id,
                    "exact_deterministic",
                    lane=prior_lane,
                )
            for prior_lane in (
                "shared_header",
                "transplant",
                "whole_tu",
                "dependency_closure",
                "multi_donor",
            ):
                coordinator.complete_tier(
                    item.recipient_id,
                    "structural_dependency",
                    lane=prior_lane,
                )
            task = coordinator.create_task(
                recipient_id=item.recipient_id,
                lane="cfg_dataflow",
                operation="indexed-donor",
                budget_ordinal=0,
            )
            coordinator.schedule_task(task)
            coordinator.commit_epoch(
                (
                    TaskResult(
                        task_id=task.task_id,
                        candidate=batch.candidates[0].candidate,
                        source=batch.candidates[0].source,
                    ),
                )
            )
            recovered = recover_run(run_root)
            self.assertIn(task.task_id, recovered.completed_task_ids)


if __name__ == "__main__":
    unittest.main()
