"""Focused regressions for the immutable donor-index query boundary."""

from __future__ import annotations

import sys
import tempfile
import unittest
from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_donor_index import DonorIndexBinding, DonorIndexEntry
from automation.search_donor_query import (
    DonorAmbiguityReceipt,
    DonorIncompatibilityReceipt,
    DonorQuery,
    DonorQueryArtifactError,
    DonorQueryIdentityMismatch,
    DonorQueryInputError,
    DonorQueryResult,
    DonorSemanticClaim,
    DonorStaleReceipt,
    bind_donor_query,
    make_donor_query,
    query_donor_index,
    replay_donor_query_result,
)
from automation.search_supervisor import IntegrationGateError
from automation.search_types import canonical_bytes, hash_bytes, hash_canonical
from automation.test_search_donor_index import (
    digest,
    donor_evidence,
    fixture_revisions,
    mint_gate,
)


def _query(**overrides) -> DonorQuery:
    values = {
        "recipient_id": "us:ST:fn",
        "version": None,
        "source_path": None,
        "symbol": "fn",
        "instruction_signature": None,
        "cfg_signature": None,
        "dataflow_signature": None,
        "compiler_identity": digest("compiler"),
        "config_identity": digest("index-config"),
        "limit": 8,
    }
    values.update(overrides)
    return make_donor_query(**values)


@contextmanager
def _index_fixture(builder=None):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        archive = ContentAddressedArchive(root / "index")
        revisions, sources = fixture_revisions(archive)
        gate, gate_archive = mint_gate(root)
        calls: Counter = Counter()

        def scan_revision(revision):
            calls[revision.version] += 1
            evidence = donor_evidence(revision, sources[revision.version])
            if builder is not None:
                evidence = builder(revision, evidence)
            return (evidence,)

        from automation.search_donor_index import build_donor_index

        index = build_donor_index(
            revisions,
            integration_gate=gate,
            integration_archive=gate_archive,
            scan_revision=scan_revision,
            indexer_identity=digest("indexer"),
            indexer_source_identity=digest("indexer-source"),
            config_identity=digest("index-config"),
            signature_identity=digest("signature"),
            schema_identity=digest("donor-schema"),
            generation_ordinal=1,
            archive=archive,
        )
        yield index, archive, gate_archive, gate, calls, sources


class DonorQueryBindingTests(unittest.TestCase):
    def test_bound_query_is_read_only_ranked_and_preserves_original_evidence(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, calls, _sources):
            query = _query()
            with patch("automation.search_donor_query.validate_integration_gate", wraps=None) as validator:
                validator.side_effect = lambda receipt, *, archive: __import__(
                    "automation.search_supervisor", fromlist=["validate_integration_gate"]
                ).validate_integration_gate(receipt, archive=archive)
                bound = bind_donor_query(
                    index,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )
                result = bound(query)
            self.assertEqual(validator.call_count, 1)
            self.assertEqual(result.status, "matched")
            self.assertEqual(result.hits[0].rank, 0)
            self.assertEqual(result.hits[0].match_kind, "exact_symbol_path")
            self.assertIs(result.donors[0], result.hits[0].entry.evidence)
            self.assertIs(result.donors[0], index.entries[0].evidence)
            self.assertEqual(sum(calls.values()), 4)
            self.assertEqual(
                query_donor_index(
                    index,
                    query,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                ).to_dict(),
                result.to_dict(),
            )

    def test_all_four_rank_classes_are_fixed_and_version_filter_is_exact(self) -> None:
        def rank_fixture(revision, evidence):
            if revision.version == "us":
                return evidence
            if revision.version == "hd":
                return replace(evidence, symbol="other")
            if revision.version == "pspeu":
                return replace(evidence, symbol="other", instruction_signature="other")
            return replace(
                evidence,
                symbol="other",
                instruction_signature="other",
                cfg_signature="other",
            )

        with _index_fixture(rank_fixture) as (index, archive, gate_archive, _gate, _calls, _sources):
            expectations = (
                ("us", {"symbol": "fn"}, 0, "exact_symbol_path"),
                ("hd", {"instruction_signature": "ins:fn"}, 1, "instruction_shape"),
                ("pspeu", {"cfg_signature": "cfg:fn"}, 2, "cfg"),
                ("saturn", {"dataflow_signature": "flow:fn"}, 3, "dataflow"),
            )
            for version, selectors, rank, kind in expectations:
                query_values = {
                    "version": version,
                    "symbol": None,
                    "instruction_signature": None,
                    "cfg_signature": None,
                    "dataflow_signature": None,
                }
                query_values.update(selectors)
                result = query_donor_index(
                    index,
                    _query(**query_values),
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )
                self.assertEqual(result.status, "matched")
                self.assertEqual([(hit.rank, hit.match_kind) for hit in result.hits], [(rank, kind)])
            fallback = query_donor_index(
                index,
                _query(
                    version="hd",
                    source_path=_sources["us"].path,
                    symbol=None,
                    instruction_signature="ins:fn",
                ),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(fallback.status, "matched")
            self.assertEqual(fallback.hits[0].match_kind, "instruction_shape")
            self.assertEqual(fallback.hits[0].rank, 1)

    def test_empty_incompatible_ambiguity_and_limit_are_distinct(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            empty = query_donor_index(
                index,
                _query(symbol="missing"),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(empty.status, "empty")
            self.assertIsNone(empty.receipt)

            limited = query_donor_index(
                index,
                _query(limit=1),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(limited.status, "matched")
            self.assertEqual(len(limited.hits), 1)

        def incompatible(_revision, evidence):
            return replace(evidence, compatible=False)

        with _index_fixture(incompatible) as (index, archive, gate_archive, _gate, _calls, _sources):
            result = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(result.status, "incompatible")
            self.assertIsInstance(result.receipt, DonorIncompatibilityReceipt)
            self.assertEqual(len(result.receipt.entry_ids), 4)

        def conflicting(revision, evidence):
            return replace(evidence, signature="sig:" + revision.version)

        with _index_fixture(conflicting) as (index, archive, gate_archive, _gate, _calls, _sources):
            result = query_donor_index(
                index,
                _query(limit=1),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(result.status, "ambiguous")
            self.assertIsInstance(result.receipt, DonorAmbiguityReceipt)
            self.assertEqual(len(result.receipt.entry_ids), 4)

    def test_stale_expected_binding_is_a_typed_result(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            expected = replace(index.binding, generation_ordinal=2)
            result = query_donor_index(
                index,
                _query(),
                expected_binding=expected,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(result.status, "stale")
            self.assertIsInstance(result.receipt, DonorStaleReceipt)
            self.assertEqual(result.receipt.expected_binding, expected)
            self.assertEqual(result.receipt.observed_binding, index.binding)
            self.assertFalse(result.hits)
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(result.receipt, receipt_id=digest("forged-stale-receipt"))

    def test_stale_compiler_and_config_bindings_accept_matching_old_queries(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            old_compiler = replace(index.binding, compiler_identity=digest("old-compiler"))
            compiler_query = _query(compiler_identity=digest("old-compiler"))
            compiler_result = query_donor_index(
                index,
                compiler_query,
                expected_binding=old_compiler,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(compiler_result.status, "stale")
            self.assertEqual(compiler_result.receipt.expected_binding, old_compiler)

            old_config = replace(index.binding, config_identity=digest("old-config"))
            config_query = _query(config_identity=digest("old-config"))
            config_result = query_donor_index(
                index,
                config_query,
                expected_binding=old_config,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(config_result.status, "stale")
            self.assertEqual(config_result.receipt.expected_binding, old_config)

            bound = bind_donor_query(
                index,
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            with self.assertRaises(DonorQueryIdentityMismatch):
                bound(_query(compiler_identity=digest("other-compiler")))
            with self.assertRaises(DonorQueryIdentityMismatch):
                bound(_query(config_identity=digest("other-config")))

    def test_stale_check_precedes_entry_consumption(self) -> None:
        class ExplodingEntries:
            def __iter__(self):
                raise AssertionError("stale query consumed donor entries")

        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            expected = replace(index.binding, generation_ordinal=2)
            bound = bind_donor_query(
                index,
                expected_binding=expected,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            object.__setattr__(index, "entries", ExplodingEntries())
            result = bound(_query())
            self.assertEqual(result.status, "stale")

    def test_compiler_mismatch_is_rejected_before_query_entries_are_consumed(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            supervisor = __import__(
                "automation.search_supervisor", fromlist=["validate_integration_gate"]
            )
            original = supervisor.validate_integration_gate
            manifest = original(index.binding.integration_gate, archive=gate_archive)
            forged = replace(manifest, compiler_identity=digest("other-compiler"))
            with patch("automation.search_donor_query.validate_integration_gate", return_value=forged) as validator:
                with self.assertRaises(DonorQueryIdentityMismatch):
                    bind_donor_query(
                        index,
                        expected_binding=index.binding,
                        index_archive=archive,
                        integration_archive=gate_archive,
                    )
            self.assertEqual(validator.call_count, 1)

    def test_reordered_or_duplicate_structural_differences_share_a_claim(self) -> None:
        def canonical_claim(_revision, evidence):
            return replace(evidence, structural_differences=("z", "a", "z"))

        with _index_fixture(canonical_claim) as (index, archive, gate_archive, _gate, _calls, _sources):
            claims = tuple(
                DonorSemanticClaim.from_evidence(entry.evidence)
                for entry in index.entries
            )
            self.assertTrue(all(claim == claims[0] for claim in claims))
            result = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(result.status, "matched")
            self.assertEqual({hit.claim_identity for hit in result.hits}, {claims[0].claim_identity})

    def test_missing_corrupt_and_noncanonical_index_artifact_are_stable_errors(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            archive.resolve(index.artifact).unlink()
            with self.assertRaises(DonorQueryArtifactError):
                bind_donor_query(
                    index,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )

        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            archive.resolve(index.artifact).write_bytes(b"corrupt")
            with self.assertRaises(DonorQueryArtifactError):
                bind_donor_query(
                    index,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )

        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            with patch.object(archive, "verify", return_value=b"different canonical bytes"):
                with self.assertRaises(DonorQueryArtifactError):
                    bind_donor_query(
                        index,
                        expected_binding=index.binding,
                        index_archive=archive,
                        integration_archive=gate_archive,
                    )

    def test_corrupt_gate_history_is_rejected_and_never_falls_back_to_stale(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, gate, _calls, _sources):
            gate_archive.resolve(gate.receipt_artifact).write_bytes(b"corrupt gate")
            with self.assertRaises(IntegrationGateError):
                bind_donor_query(
                    index,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )


class DonorQueryRecordTests(unittest.TestCase):
    def test_query_identity_and_limit_boundaries_are_content_addressed(self) -> None:
        query = _query()
        self.assertEqual(DonorQuery.from_dict(query.to_dict()), query)
        forged = query.to_dict()
        forged["query_identity"] = digest("forged-query")
        with self.assertRaises(DonorQueryIdentityMismatch):
            DonorQuery.from_dict(forged)
        for limit in (0, 9, True):
            with self.assertRaises(DonorQueryInputError):
                _query(limit=limit)
        with self.assertRaises(DonorQueryInputError):
            _query(version="unknown")
        with self.assertRaises(DonorQueryInputError):
            _query(symbol=None, instruction_signature=None, cfg_signature=None, dataflow_signature=None)

    def test_semantic_claim_excludes_provenance_and_rejects_direct_forgery(self) -> None:
        with _index_fixture() as (index, _archive, _gate_archive, _gate, _calls, _sources):
            evidence = index.entries[0].evidence
            claim = DonorSemanticClaim.from_evidence(evidence)
            payload = claim.identity_payload()
            self.assertNotIn("donor_id", payload)
            self.assertNotIn("version", payload)
            self.assertNotIn("source", payload)
            self.assertNotIn("body", payload)
            self.assertNotIn("metadata", payload)
            self.assertEqual(
                claim,
                DonorSemanticClaim.from_evidence(index.entries[1].evidence),
            )
            self.assertEqual(
                DonorSemanticClaim.from_dict(claim.to_dict()),
                claim,
            )
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(claim, claim_identity=digest("forged-claim"))
            with self.assertRaises(DonorQueryInputError):
                replace(claim, compatible=1)

    def test_result_renderer_claim_projection_is_typed_and_deduplicated(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            result = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            claims = result.semantic_claims
            self.assertEqual(len(claims), 1)
            self.assertIsInstance(claims[0], DonorSemanticClaim)
            self.assertEqual(
                tuple(item.claim_identity for item in claims),
                tuple(sorted({hit.claim_identity for hit in result.hits})),
            )
            self.assertNotIn("source", claims[0].to_dict())
            self.assertNotIn("body", claims[0].to_dict())
            self.assertEqual(
                query_donor_index(
                    index,
                    _query(symbol="missing"),
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                ).semantic_claims,
                (),
            )

    def test_public_hit_receipt_and_result_records_reject_forgeries(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            result = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            hit = result.hits[0]
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(hit, match_kind="cfg")
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(hit, claim_identity=digest("forged-hit"))
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(result, status="ambiguous")
            with self.assertRaises(DonorQueryInputError):
                replace(result, status="unknown")

        def conflicting(revision, evidence):
            return replace(evidence, signature="sig:" + revision.version)

        with _index_fixture(conflicting) as (index, archive, gate_archive, _gate, _calls, _sources):
            ambiguous = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertIsInstance(ambiguous.receipt, DonorAmbiguityReceipt)
            self.assertEqual(
                replay_donor_query_result(
                    index,
                    ambiguous.to_dict(),
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                ).to_dict(),
                ambiguous.to_dict(),
            )
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(ambiguous.receipt, receipt_id=digest("forged-receipt"))
            with self.assertRaises(DonorQueryInputError):
                replace(ambiguous.receipt, entry_ids=(ambiguous.receipt.entry_ids[0],))
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(ambiguous.receipt, reason_code="other_reason")

        def incompatible(_revision, evidence):
            return replace(evidence, compatible=False)

        with _index_fixture(incompatible) as (index, archive, gate_archive, _gate, _calls, _sources):
            incompatible_result = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertIsInstance(incompatible_result.receipt, DonorIncompatibilityReceipt)
            self.assertEqual(
                replay_donor_query_result(
                    index,
                    incompatible_result.to_dict(),
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                ).to_dict(),
                incompatible_result.to_dict(),
            )
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(incompatible_result.receipt, receipt_id=digest("forged-receipt"))
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(incompatible_result.receipt, reasons=("other_reason",))

    def test_direct_matched_result_rejects_incompatible_donor_evidence(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            result = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            hit = result.hits[0]
            evidence = replace(hit.entry.evidence, compatible=False)
            entry = DonorIndexEntry.from_evidence(hit.entry.revision, evidence)
            forged_hit = replace(
                hit,
                claim_identity=DonorSemanticClaim.from_evidence(evidence).claim_identity,
                entry=entry,
            )
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(result, hits=(forged_hit,), donors=(evidence,))

    def test_direct_matched_result_rejects_conflicting_claims(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            result = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            first = result.hits[0]
            evidence = replace(first.entry.evidence, signature="conflicting-signature")
            entry = DonorIndexEntry.from_evidence(first.entry.revision, evidence)
            conflicting_hit = replace(
                first,
                claim_identity=DonorSemanticClaim.from_evidence(evidence).claim_identity,
                entry=entry,
            )
            hits = tuple(
                sorted(
                    (first, conflicting_hit),
                    key=lambda item: (item.rank, item.entry.entry_id),
                )
            )
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(result, hits=hits, donors=tuple(hit.donor for hit in hits))

    def test_direct_stale_result_requires_expected_compiler_and_config(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            cases = (
                ("compiler_identity", digest("stale-compiler")),
                ("config_identity", digest("stale-config")),
            )
            for field, stale_identity in cases:
                with self.subTest(field=field):
                    expected = replace(index.binding, **{field: stale_identity})
                    query = _query(**{field: stale_identity})
                    stale = query_donor_index(
                        index,
                        query,
                        expected_binding=expected,
                        index_archive=archive,
                        integration_archive=gate_archive,
                    )
                    self.assertEqual(stale.status, "stale")
                    forged_query = _query()
                    receipt = stale.receipt
                    self.assertIsInstance(receipt, DonorStaleReceipt)
                    forged_receipt = replace(
                        receipt,
                        query_identity=forged_query.query_identity,
                        receipt_id=hash_canonical(
                            {
                                **receipt.identity_payload(),
                                "query_identity": forged_query.query_identity,
                            }
                        ),
                    )
                    with self.assertRaises(DonorQueryIdentityMismatch):
                        DonorQueryResult(
                            status="stale",
                            query=forged_query,
                            query_identity=forged_query.query_identity,
                            generation_id=stale.generation_id,
                            hits=(),
                            donors=(),
                            receipt=forged_receipt,
                            provenance_artifact=stale.provenance_artifact,
                        )

    def test_replay_requires_durable_authority_and_rejects_result_forgeries(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            result = query_donor_index(
                index,
                _query(),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            encoded = result.to_dict()

            forged_identity = dict(encoded)
            forged_identity["query_identity"] = digest("forged-result-query")
            with self.assertRaises(DonorQueryIdentityMismatch):
                replay_donor_query_result(
                    index,
                    forged_identity,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )

            wrong_query = _query(symbol="other")
            with self.assertRaises(DonorQueryIdentityMismatch):
                replace(
                    result,
                    query=wrong_query,
                    query_identity=wrong_query.query_identity,
                )

            over_limit = dict(encoded)
            limited_query = _query(limit=1)
            over_limit["query"] = limited_query.to_dict()
            over_limit["query_identity"] = limited_query.query_identity
            with self.assertRaises(DonorQueryIdentityMismatch):
                replay_donor_query_result(
                    index,
                    over_limit,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )

            forbidden_receipt = dict(encoded)
            forbidden_receipt["receipt"] = {"forged": True}
            with self.assertRaises(DonorQueryIdentityMismatch):
                replay_donor_query_result(
                    index,
                    forbidden_receipt,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )

            bad_artifact = dict(encoded)
            bad_artifact["provenance_artifact"] = dict(encoded["provenance_artifact"])
            bad_artifact["provenance_artifact"]["byte_size"] += 1
            with self.assertRaises(DonorQueryIdentityMismatch):
                replay_donor_query_result(
                    index,
                    bad_artifact,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )

            substituted = dict(encoded)
            substituted["hits"] = list(encoded["hits"])
            substituted["hits"][0] = dict(substituted["hits"][0])
            substituted["hits"][0]["entry"] = substituted["hits"][1]["entry"]
            with self.assertRaises(DonorQueryIdentityMismatch):
                replay_donor_query_result(
                    index,
                    substituted,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )

            empty = query_donor_index(
                index,
                _query(symbol="missing"),
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            empty_payload = empty.to_dict()
            empty_payload["receipt"] = {"forged": True}
            with self.assertRaises(DonorQueryIdentityMismatch):
                replay_donor_query_result(
                    index,
                    empty_payload,
                    expected_binding=index.binding,
                    index_archive=archive,
                    integration_archive=gate_archive,
                )

    def test_reversed_input_order_and_roundtrip_are_deterministic(self) -> None:
        with _index_fixture() as (index, archive, gate_archive, _gate, _calls, _sources):
            bound = bind_donor_query(
                index,
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            result_a = bound(_query())
            result_b = bound(_query())
            self.assertEqual(result_a.to_dict(), result_b.to_dict())
            self.assertEqual(
                [hit.entry.entry_id for hit in result_a.hits],
                sorted(hit.entry.entry_id for hit in result_a.hits),
            )
            # Round-trip the result after preserving the hit-owned donor
            # references.  The result constructor refuses independently
            # copied donor objects.
            encoded = result_a.to_dict()
            with self.assertRaises(DonorQueryInputError):
                DonorQueryResult.from_dict(encoded)
            decoded = replay_donor_query_result(
                index,
                encoded,
                expected_binding=index.binding,
                index_archive=archive,
                integration_archive=gate_archive,
            )
            self.assertEqual(decoded.to_dict(), encoded)
            self.assertIs(decoded.donors[0], index.entries[0].evidence)


if __name__ == "__main__":
    unittest.main()
