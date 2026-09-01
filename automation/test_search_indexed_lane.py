"""Focused tests for archive-backed indexed donor lane adapters."""

from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ArtifactRef, ContentAddressedArchive
from automation.search_coordinator import SearchCoordinator, TaskResult
from automation.search_donor_query import (
    DonorQuery,
    DonorQueryResult,
    DonorSemanticClaim,
    bind_donor_query,
    query_donor_index,
)
from automation.search_indexed_lane import (
    _renderer_source_identity,
    _runtime_archive_root,
    _validate_runtime_binding,
    _target_context_callbacks,
    indexed_lane_adapter,
    production_indexed_adapters,
)
from automation.search_indexed_runtime import IndexedRuntimeGeneration
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
from automation.search_types import CandidateRecord, RunManifest, hash_bytes, hash_canonical
from automation.test_search_donor_query import _index_fixture, _query
from automation.test_search_lanes import make_manifest
from automation.test_search_target_renderer import _target_fixture
from automation.search_target_renderer import (
    TARGET_RENDERER_IDENTITY,
    _assembly_signatures,
    _parse_assembly,
    TargetContextUnsupported,
)
from automation.test_search_target_renderer import TARGET_ASM


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

    def test_refused_then_matched_retry_does_not_consume_stale_target_query(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            manifest = RunManifest.from_dict(make_manifest(item.recipient_id))
            first_query = _query(symbol="missing")
            matched_query = _query(symbol="fn")
            query_values = iter((first_query, matched_query))
            query_calls = []
            rendered_queries = []

            def query_for(_manifest, _target_index, _received):
                query = next(query_values)
                query_calls.append(query)
                return query

            def render_target(
                _manifest,
                _target_index,
                received,
                _claims,
                *,
                lane,
                query,
            ):
                rendered_queries.append(query)
                return target_candidate(received, lane)

            with patch(
                "automation.search_target_renderer.query_for_recipient",
                side_effect=query_for,
            ), patch(
                "automation.search_target_renderer.render_target_candidate",
                side_effect=render_target,
            ):
                query_callback, render_callback = _target_context_callbacks(
                    manifest,
                    None,
                    lane="cfg_dataflow",
                )
                adapter = indexed_lane_adapter(
                    index,
                    lane="cfg_dataflow",
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                    query_for=query_callback,
                    render_target_context=render_callback,
                )
                first = adapter(item)
                second = adapter(item)

            self.assertEqual(first["candidates"], ())
            self.assertEqual(first["refusal_code"], "donor_query_empty")
            self.assertEqual(len(second["candidates"]), 1)
            self.assertEqual(query_calls, [first_query, matched_query])
            self.assertEqual(rendered_queries, [matched_query])
            self.assertIs(rendered_queries[0], matched_query)

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

    def test_rejects_renderer_candidate_source_identity_mismatch(self) -> None:
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

    def test_runtime_binding_requires_protocol_and_manifest_renderer_source_identities(self) -> None:
        with _index_fixture() as (index, _archive, _gate_archive, _gate, _calls, _sources):
            item = recipient()
            runtime_id = hash_bytes(b"renderer-binding-runtime")
            renderer_source_identity = hash_bytes(b"archived-target-renderer-source")
            manifest = RunManifest.from_dict(make_manifest(item.recipient_id))
            manifest = replace(
                manifest,
                compiler_identity=index.binding.compiler_identity,
                config_identity=index.binding.config_identity,
                tool_identities={
                    **manifest.tool_identities,
                    "runtime_id": runtime_id,
                    "search_target_renderer": renderer_source_identity,
                },
            )
            binding = SimpleNamespace(
                donor_index_generation_id=index.generation_id,
                donor_index_artifact=index.artifact,
                compiler_identity=index.binding.compiler_identity,
                config_identity=index.binding.config_identity,
                renderer_identity=TARGET_RENDERER_IDENTITY,
                renderer_source_identity=renderer_source_identity,
            )
            runtime = SimpleNamespace(runtime_id=runtime_id, binding=binding)
            _validate_runtime_binding(runtime, index, manifest=manifest)

            forged_binding_values = vars(binding).copy()
            forged_binding_values["renderer_source_identity"] = hash_bytes(
                b"forged-renderer-source"
            )
            forged_binding = SimpleNamespace(**forged_binding_values)
            with self.assertRaises(LaneError):
                _validate_runtime_binding(
                    SimpleNamespace(runtime_id=runtime_id, binding=forged_binding),
                    index,
                    manifest=manifest,
                )

            missing_binding = SimpleNamespace(**vars(binding))
            del missing_binding.renderer_source_identity
            with self.assertRaises(LaneError):
                _validate_runtime_binding(
                    SimpleNamespace(runtime_id=runtime_id, binding=missing_binding),
                    index,
                    manifest=manifest,
                )

            invalid_protocol = SimpleNamespace(**vars(binding))
            invalid_protocol.renderer_identity = "renderer-protocol-is-not-a-hash"
            with self.assertRaises(LaneError):
                _validate_runtime_binding(
                    SimpleNamespace(runtime_id=runtime_id, binding=invalid_protocol),
                    index,
                    manifest=manifest,
                )

            with tempfile.TemporaryDirectory() as directory:
                renderer_root = Path(directory) / "automation"
                renderer_root.mkdir()
                renderer_path = renderer_root / "search_target_renderer.py"
                renderer_path.write_bytes(b"renderer source bytes")
                derived_source_identity = _renderer_source_identity(Path(directory))
                with self.assertRaises(LaneError):
                    _validate_runtime_binding(
                        runtime,
                        index,
                        manifest=manifest,
                        renderer_source_identity=derived_source_identity,
                    )

                bound_manifest = replace(
                    manifest,
                    tool_identities={
                        **manifest.tool_identities,
                        "search_target_renderer": derived_source_identity,
                    },
                )
                bound_values = vars(binding).copy()
                bound_values["renderer_source_identity"] = derived_source_identity
                _validate_runtime_binding(
                    SimpleNamespace(
                        runtime_id=runtime_id,
                        binding=SimpleNamespace(**bound_values),
                    ),
                    index,
                    manifest=bound_manifest,
                    renderer_source_identity=derived_source_identity,
                )

    def test_runtime_archive_root_requires_canonical_factory_search_run(self) -> None:
        runtime = SimpleNamespace(runtime_id=hash_bytes(b"runtime-path"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "nonmatchings" / "anchor" / "search-runs" / "run-path"
            canonical.mkdir(parents=True)
            self.assertEqual(
                _runtime_archive_root(runtime, ContentAddressedArchive(canonical)),
                root
                / "nonmatchings"
                / "search-evidence"
                / "indexed-runtimes"
                / runtime.runtime_id.removeprefix("sha256:"),
            )
            noncanonical = root / "nonmatchings" / "not-a-factory-run"
            noncanonical.mkdir(parents=True)
            archive = ContentAddressedArchive(noncanonical)
            with self.assertRaises(LaneError):
                _runtime_archive_root(runtime, archive)

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

    def test_target_context_refusal_is_an_ordinary_typed_lane_refusal(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            item = recipient()
            query = _query(recipient_id=item.recipient_id)
            refusal = TargetContextUnsupported(
                recipient_id=item.recipient_id,
                query=query,
                target_identity=hash_bytes(b"target-identity"),
                target_artifact_identity=hash_bytes(b"target-evidence"),
                reason="unsupported branch shape",
                input_identities=(query.query_identity,),
                provenance=(
                    {
                        "kind": "target_context",
                        "source": "asm/us/st/fn.s",
                        "source_identity": hash_bytes(b"target-assembly"),
                        "input_identity": query.query_identity,
                    },
                ),
            )
            renderer_calls = []

            def render(received, _claims):
                renderer_calls.append(received.recipient_id)
                return refusal

            adapter = indexed_lane_adapter(
                index,
                lane="multi_donor",
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
                query_for=lambda _item: query,
                render_target_context=render,
            )
            raw = adapter(item)
            self.assertEqual(raw["candidates"], ())
            self.assertEqual(raw["refusal_code"], "target_context_unsupported")
            self.assertEqual(raw["completion_reason"], "inapplicable")
            self.assertIn(query.query_identity, raw["input_identities"])
            self.assertEqual(renderer_calls, [item.recipient_id])
            self.assertTrue(
                any(edge["kind"] == "target_context" for edge in raw["provenance"])
            )

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

    def test_production_indexed_adapters_require_typed_manifest_bound_runtime(self) -> None:
        # An untyped value must not become a production runtime merely because
        # it carries a valid donor index and caller-supplied archive handles.
        # Those injected handles belong to the lower-level testable adapter.
        target_instruction, target_cfg, target_dataflow = _assembly_signatures(
            _parse_assembly(TARGET_ASM.decode("utf-8"))
        )

        def target_signature_fixture(_revision, evidence):
            return replace(
                evidence,
                instruction_signature=target_instruction,
                cfg_signature=target_cfg,
                dataflow_signature=target_dataflow,
            )

        with _index_fixture(target_signature_fixture) as (
            index,
            index_archive,
            integration_archive,
            _gate,
            _calls,
            _sources,
        ):
            (
                _target_temp,
                run_archive,
                target_manifest,
                _target_index,
            ) = _target_fixture()
            try:
                manifest = replace(
                    target_manifest,
                    compiler_identity=index.binding.compiler_identity,
                    config_identity=index.binding.config_identity,
                )
                runtime_id = hash_bytes(b"indexed-runtime")
                runtime = SimpleNamespace(
                    runtime_id=runtime_id,
                    binding=SimpleNamespace(
                        donor_index_generation_id=index.generation_id,
                        donor_index_artifact=index.artifact,
                        compiler_identity=index.binding.compiler_identity,
                        config_identity=index.binding.config_identity,
                        renderer_identity=TARGET_RENDERER_IDENTITY,
                    ),
                    donor_index=index,
                    index_archive=index_archive,
                    integration_archive=integration_archive,
                )
                manifest = replace(
                    manifest,
                    tool_identities={
                        **manifest.tool_identities,
                        "indexed_runtime": runtime_id,
                    },
                )
                with self.assertRaises(LaneError):
                    production_indexed_adapters(
                        manifest,
                        runtime,
                        run_archive,
                    )
            finally:
                _target_temp.cleanup()

    def test_production_adapters_refuse_unbound_or_injected_runtime_inputs(self) -> None:
        target_instruction, target_cfg, target_dataflow = _assembly_signatures(
            _parse_assembly(TARGET_ASM.decode("utf-8"))
        )

        def target_signature_fixture(_revision, evidence):
            return replace(
                evidence,
                instruction_signature=target_instruction,
                cfg_signature=target_cfg,
                dataflow_signature=target_dataflow,
            )

        with _index_fixture(target_signature_fixture) as (
            index,
            index_archive,
            integration_archive,
            _gate,
            _calls,
            _sources,
        ):
            _target_temp, run_archive, target_manifest, _target_index = _target_fixture()
            try:
                manifest = replace(
                    target_manifest,
                    compiler_identity=index.binding.compiler_identity,
                    config_identity=index.binding.config_identity,
                )
                runtime_id = hash_bytes(b"indexed-runtime-negative")
                binding = SimpleNamespace(
                    donor_index_generation_id=index.generation_id,
                    donor_index_artifact=index.artifact,
                    compiler_identity=index.binding.compiler_identity,
                    config_identity=index.binding.config_identity,
                    renderer_identity=TARGET_RENDERER_IDENTITY,
                )
                base = {
                    "runtime_id": runtime_id,
                    "binding": binding,
                    "donor_index": index,
                    "index_archive": index_archive,
                    "integration_archive": integration_archive,
                }
                manifest = replace(
                    manifest,
                    tool_identities={
                        **manifest.tool_identities,
                        "indexed_runtime": runtime_id,
                    },
                )

                missing_archive = dict(base)
                missing_archive.pop("index_archive")
                with self.assertRaises(LaneError):
                    production_indexed_adapters(
                        manifest,
                        SimpleNamespace(**missing_archive),
                        run_archive,
                    )

                injected = dict(base)
                injected["query_for"] = lambda _recipient: None
                with self.assertRaises(LaneError):
                    production_indexed_adapters(
                        manifest,
                        SimpleNamespace(**injected),
                        run_archive,
                    )

                wrong_manifest = replace(
                    manifest,
                    tool_identities={
                        **manifest.tool_identities,
                        "indexed_runtime": hash_bytes(b"different-runtime"),
                    },
                )
                with self.assertRaises(LaneError):
                    production_indexed_adapters(wrong_manifest, SimpleNamespace(**base), run_archive)

                arbitrary_typed_runtime = object.__new__(IndexedRuntimeGeneration)
                object.__setattr__(arbitrary_typed_runtime, "untrusted_path", "runtime.json")
                with self.assertRaises(LaneError):
                    production_indexed_adapters(
                        manifest,
                        arbitrary_typed_runtime,
                        run_archive,
                    )
            finally:
                _target_temp.cleanup()


if __name__ == "__main__":
    unittest.main()
