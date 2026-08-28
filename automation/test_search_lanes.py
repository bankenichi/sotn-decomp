"""Focused tests for the read-only search lane adapters."""

from __future__ import annotations

from dataclasses import replace

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_lanes import (
    DETERMINISTIC_LANES,
    AdapterSignatureError,
    CandidateIdentityMismatch,
    LaneError,
    LaneAdapters,
    LaneReceiptProposal,
    ReadOnlyViolation,
    Recipient,
    SubsetViolation,
    UnsafeSemanticConstant,
    gather_donors,
    is_safe_semantic_constant,
    mipsmatch_fingerprint,
    mipsmatch_scan,
    reject_unsafe_semantic_constant,
    run_lane,
    run_lanes,
    _extract_function,
    _candidate_from_value,
    _identity,
    _provenance,
    _read_repo_text,
)
from automation.search_coordinator import SearchCoordinator
from automation.search_types import (
    ArtifactRef,
    Budget,
    CandidateRecord,
    canonical_subset_identity,
    LANES,
    RunManifest,
    hash_bytes,
    hash_canonical,
)


BODY = "int func_lane(void) { return 7; }\n"


def digest(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


def make_manifest(*record_ids: str):
    base = RunManifest(
        run_id="run-lanes",
        created_at="2026-08-27T00:00:00Z",
        parent_run=None,
        queue_record_ids=tuple(sorted(record_ids)),
        function_ids=tuple(sorted(record_ids)),
        subset_identity=canonical_subset_identity(sorted(record_ids)),
        queue_evidence_identity=digest("queue-evidence-" + ",".join(sorted(record_ids))),
        selected_lanes=LANES,
        source_identity=digest("lane-source"),
        target_identities={record_id: digest("target-" + record_id) for record_id in record_ids},
        compiler_identity=digest("lane-compiler"),
        tool_identities={
            "lane-test": digest("lane-tool"),
            **{lane: digest("lane-tool-" + lane) for lane in LANES},
        },
        config_identity=digest("lane-config"),
        schema_identity=digest("lane-schema"),
        run_seed=17,
        epoch_size=2,
        frontier_cap=8,
        coordinator_budget=Budget("tasks", 64, 0),
        lane_budgets={lane: Budget("attempts", 16, 0) for lane in LANES},
        tier_order=(
            "exact_deterministic",
            "structural_dependency",
            "cheap_generated",
            "compiler_guided",
            "model",
        ),
    )
    return base.to_dict()


def recipient(record_id: str = "record-1") -> Recipient:
    return Recipient(
        recipient_id=record_id,
        overlay="no0",
        function="func_lane",
        metadata={"target_file": "src/lane.c"},
    )


class TestSearchLanes(unittest.TestCase):
    def test_manifest_requires_all_immutable_identities_and_rejects_bad_tools(self) -> None:
        manifest = make_manifest("record-1")
        for field in ("source_identity", "config_identity", "compiler_identity"):
            with self.subTest(field=field):
                missing = dict(manifest)
                missing.pop(field)
                with self.assertRaises(LaneError):
                    run_lane(
                        missing,
                        "upstream_current",
                        {"record-1": recipient()},
                        adapters={"upstream_current": lambda _item: ()},
                    )

        invalid_tools = dict(manifest)
        invalid_tools["tool_identities"] = {
            "lane-test": digest("lane-tool"),
            "invalid-tool": "tool-name-is-not-a-content-hash",
        }
        with self.assertRaises(LaneError):
            run_lane(
                invalid_tools,
                "upstream_current",
                {"record-1": recipient()},
                adapters={"upstream_current": lambda _item: ()},
            )

    def test_identity_never_hashes_paths_or_mutable_refs(self) -> None:
        with self.assertRaises(LaneError):
            _identity("relative/source.c")
        with self.assertRaises(LaneError):
            _identity("upstream/master")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.c"
            source.write_bytes(BODY.encode("utf-8"))
            self.assertEqual(
                _identity("source.c", root=root),
                hash_bytes(BODY.encode("utf-8")),
            )
            with self.assertRaises(LaneError):
                _provenance(
                    lane="upstream_current",
                    recipient=recipient(),
                    kind="unresolved",
                    source="missing/source.c",
                    root=root,
                )

    def test_upstream_mutable_ref_is_typed_refusal_and_resolver_is_explicit(self) -> None:
        manifest = make_manifest("record-1")
        seen = []

        def fetcher(ref: str, path: str, item: Recipient):
            seen.append((ref, path, item.recipient_id))
            return BODY

        mutable = run_lane(
            manifest,
            "upstream_current",
            {"record-1": recipient()},
            options={
                "upstream_paths": {"record-1": "reference/no0.c"},
                "current_ref": "upstream/master",
                "upstream_fetch": fetcher,
            },
        )[0]
        self.assertEqual(mutable.refusal.code, "unresolved_immutable_ref")
        self.assertEqual(seen, [])

        resolved = run_lane(
            manifest,
            "upstream_current",
            {"record-1": recipient()},
            options={
                "upstream_paths": {"record-1": "reference/no0.c"},
                "current_ref": "upstream/master",
                "upstream_ref_resolver": lambda ref, item: {
                    "ref": ref,
                    "commit_identity": digest("resolved-current"),
                },
                "upstream_fetch": fetcher,
            },
        )[0]
        self.assertEqual(resolved.receipt.completion_reason, "matched_pending_oracle")
        self.assertEqual(
            seen,
            [("upstream/master", "reference/no0.c", "record-1")],
        )

    def test_shared_header_candidate_is_exact_body_with_full_header_provenance(self) -> None:
        manifest = make_manifest("record-1")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "src" / "lane.c"
            target.parent.mkdir(parents=True)
            target.write_text("INCLUDE_ASM(\"lane\", func_lane);\n", encoding="utf-8")
            header = root / "include" / "shared.h"
            header.parent.mkdir(parents=True)
            header_text = (
                "#define HEADER_VALUE 7\n"
                "int unrelated(void) { return 0; }\n"
                + BODY
            )
            header.write_text(header_text, encoding="utf-8")

            class Sweep:
                @staticmethod
                def shared_headers():
                    return {"shared": header}

                @staticmethod
                def stage_files():
                    return [target]

                @staticmethod
                def build_peer_map(_headers, _files):
                    return (
                        {"lane": {"shared": ["peer"]}},
                        {
                            target: {
                                "stage": "no0",
                                "stub_fns": ["func_lane"],
                            }
                        },
                    )

                @staticmethod
                def read(path):
                    return Path(path).read_text(encoding="utf-8")

                @staticmethod
                def header_risks_text(_text):
                    return []

            with patch("automation.search_lanes._load_module", return_value=Sweep):
                batch = run_lane(
                    manifest,
                    "shared_header",
                    {"record-1": recipient()},
                    repo_root=root,
                )
            self.assertEqual(len(batch.candidates), 1)
            candidate = batch.candidates[0]
            body = BODY.rstrip("\n")
            self.assertEqual(candidate.source, body)
            self.assertEqual(candidate.candidate_id, hash_bytes(body.encode("utf-8")))
            self.assertNotEqual(candidate.candidate_id, hash_bytes(header_text.encode("utf-8")))
            evidence = next(
                item
                for item in candidate.provenance
                if item.get("kind") == "shared_header_viability"
            )
            self.assertEqual(
                evidence["source_identity"],
                hash_bytes(header.read_bytes()),
            )
            self.assertEqual(evidence["input_identity"], evidence["source_identity"])

    def test_subset_is_exact_and_never_uses_queue_fallback(self) -> None:
        manifest = make_manifest("record-1", "record-2")
        selected = {"record-1": recipient("record-1")}
        with self.assertRaises(SubsetViolation):
            run_lane(manifest, "upstream_current", selected)
        with self.assertRaises(SubsetViolation):
            run_lane(manifest, "upstream_current", None)
        with self.assertRaises(SubsetViolation):
            run_lane(
                make_manifest("record-1"),
                "upstream_current",
                {"record-1": recipient("record-1"), "record-2": recipient("record-2")},
            )

    def test_callbacks_receive_only_explicit_sorted_recipients(self) -> None:
        manifest = make_manifest("record-2", "record-1")
        seen = []

        def callback(item: Recipient):
            seen.append(item.recipient_id)
            return {
                "candidates": [{"body": BODY}],
                "provenance": [{
                    "reference_id": item.recipient_id + "-source",
                    "source_identity": hash_bytes(BODY.encode("utf-8")),
                    "input_identity": hash_bytes(BODY.encode("utf-8")),
                }],
                "input_identities": [digest(item.recipient_id + "-input")],
                "completion_reason": "matched_pending_oracle",
            }

        batch = run_lane(
            manifest,
            "upstream_current",
            {
                "record-1": recipient("record-1"),
                "record-2": recipient("record-2"),
            },
            adapters=LaneAdapters(upstream_current=callback),
        )
        self.assertEqual(seen, ["record-1", "record-2"])
        self.assertEqual(
            [item.recipient_id for item in batch.outcomes],
            ["record-1", "record-2"],
        )
        self.assertEqual(len(batch.candidates), 2)
        self.assertTrue(all(item.receipt.complete for item in batch.outcomes))
        self.assertTrue(
            all(item.receipt.completion_reason == "matched_pending_oracle" for item in batch.outcomes)
        )
        for candidate in batch.candidates:
            self.assertEqual(candidate.candidate_id, candidate.candidate.source_artifact.content_hash)
            self.assertTrue(candidate.provenance)
            self.assertTrue(all("input_identity" in entry for entry in candidate.provenance))

    def test_upstream_current_and_pinned_use_explicit_refs(self) -> None:
        manifest = make_manifest("record-1")
        seen = []

        def fetcher(ref: str, path: str, item: Recipient):
            seen.append((ref, path, item.recipient_id))
            return "int func_lane(void) { return 9; }\n"

        current = run_lane(
            manifest,
            "upstream_current",
            {"record-1": recipient()},
            options={
                "upstream_paths": {"record-1": "reference/no0.c"},
                "current_ref": digest("current-commit"),
                "upstream_fetch": fetcher,
            },
        )[0]
        self.assertEqual(current.receipt.completion_reason, "matched_pending_oracle")
        self.assertEqual(current.candidates[0].source, "int func_lane(void) { return 9; }")
        self.assertEqual(seen, [(digest("current-commit"), "reference/no0.c", "record-1")])
        self.assertEqual(
            current.candidates[0].provenance[0]["reference_id"],
            digest("current-commit") + ":reference/no0.c",
        )

        pinned = run_lane(
            manifest,
            "upstream_pinned",
            {"record-1": recipient()},
            options={
                "upstream_paths": {"record-1": "reference/no0.c"},
                "pinned_refs": {"record-1": digest("pinned-commit")},
                "upstream_fetch": fetcher,
            },
        )[0]
        self.assertEqual(pinned.receipt.completion_reason, "matched_pending_oracle")
        self.assertEqual(seen[-1][0], digest("pinned-commit"))

        missing_ref = run_lane(
            manifest,
            "upstream_pinned",
            {"record-1": recipient()},
            options={
                "upstream_paths": {"record-1": "reference/no0.c"},
                "upstream_fetch": fetcher,
            },
        )[0]
        self.assertEqual(missing_ref.refusal.code, "missing_pinned_ref")
        self.assertEqual(missing_ref.receipt.completion_reason, "inapplicable")

    def test_read_only_boundary_rejects_write_authority(self) -> None:
        manifest = make_manifest("record-1")
        with self.assertRaises(ReadOnlyViolation):
            run_lane(
                manifest,
                "upstream_current",
                {"record-1": recipient()},
                read_only=False,
            )
        with self.assertRaises(ReadOnlyViolation):
            run_lane(
                manifest,
                "upstream_current",
                {"record-1": recipient()},
                apply=True,
            )
        with self.assertRaises(ReadOnlyViolation):
            run_lane(
                manifest,
                "upstream_current",
                {"record-1": recipient()},
                options={"queue_report": True},
            )

    def test_provider_typeerror_is_not_retried_and_wrong_signature_is_typed(self) -> None:
        manifest = make_manifest("record-1")
        calls = []

        def provider(item: Recipient):
            calls.append(item.recipient_id)
            raise TypeError("provider body failure")

        with self.assertRaisesRegex(TypeError, "provider body failure"):
            run_lane(
                manifest,
                "upstream_current",
                {"record-1": recipient()},
                adapters={"upstream_current": provider},
            )
        self.assertEqual(calls, ["record-1"])

        def wrong_shape(_first, _second):
            return ()

        with self.assertRaises(AdapterSignatureError):
            run_lane(
                manifest,
                "upstream_current",
                {"record-1": recipient()},
                adapters={"upstream_current": wrong_shape},
            )

    def test_candidate_record_identity_disagreement_is_rejected(self) -> None:
        manifest = make_manifest("record-1")
        source_hash = hash_bytes(BODY.encode("utf-8"))
        record = CandidateRecord(
            candidate_id=source_hash,
            recipient_id="record-1",
            source_artifact=ArtifactRef(
                content_hash=source_hash,
                path="candidate.c",
                media_type="text/x-c",
                byte_size=len(BODY.encode("utf-8")),
            ),
            parent_candidate_ids=(),
            mutation_id=None,
            lane="upstream_current",
            depth=0,
            evaluation=None,
            status="materialized",
        )
        wrapped = {
            "candidate": record.to_dict(),
            "source": "int func_lane(void) { return 8; }\n",
        }
        with self.assertRaises(CandidateIdentityMismatch):
            _candidate_from_value(
                wrapped,
                lane="upstream_current",
                recipient=recipient(),
                root=Path(__file__).resolve().parent.parent,
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "candidate.c"
            artifact.write_text("int func_lane(void) { return 8; }\n", encoding="utf-8")
            with self.assertRaises(CandidateIdentityMismatch):
                _candidate_from_value(
                    record,
                    lane="upstream_current",
                    recipient=recipient(),
                    root=root,
                )

    def test_empty_explicit_subset_is_a_noop_with_selected_lanes(self) -> None:
        base = RunManifest.from_dict(make_manifest("record-1"))
        empty = replace(
            base,
            run_id="run-empty-lanes",
            queue_record_ids=(),
            function_ids=(),
            subset_identity=canonical_subset_identity(()),
            queue_evidence_identity=digest("queue-evidence-empty"),
            target_identities={},
            selected_lanes=("upstream_current", "mipsmatch_exact"),
            lane_budgets={
                lane: base.lane_budgets[lane]
                for lane in ("upstream_current", "mipsmatch_exact")
            },
        )
        called = []
        result = run_lanes(
            empty,
            ["mipsmatch_exact", "upstream_current"],
            {},
            adapters={
                "mipsmatch_exact": lambda _item: called.append("mipsmatch_exact"),
                "upstream_current": lambda _item: called.append("upstream_current"),
            },
        )
        self.assertEqual([batch.lane for batch in result.batches], [
            "mipsmatch_exact", "upstream_current",
        ])
        self.assertEqual(tuple(result.batches[0].outcomes), ())
        self.assertEqual(tuple(result.batches[1].outcomes), ())
        self.assertEqual(called, [])

    def test_unselected_lane_cannot_run_even_with_a_valid_subset(self) -> None:
        base = RunManifest.from_dict(make_manifest("record-1"))
        narrow = replace(
            base,
            selected_lanes=("upstream_current",),
            lane_budgets={"upstream_current": base.lane_budgets["upstream_current"]},
        )
        with self.assertRaises(LaneError):
            run_lane(
                narrow,
                "mipsmatch_exact",
                {"record-1": recipient()},
                adapters={"mipsmatch_exact": lambda _item: ()},
            )

    def test_symlink_escape_is_rejected_after_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            external = Path(outside) / "outside.c"
            external.write_text(BODY, encoding="utf-8")
            link = root / "linked.c"
            try:
                link.symlink_to(external)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("symlinks unavailable: " + str(exc))
            self.assertEqual(_read_repo_text("linked.c", root), ("", ""))

    def test_c_definition_extraction_ignores_comment_and_literal_braces(self) -> None:
        text = (
            "/* int func_lane(void) { return 0; } */\n"
            "const char *fake = \"func_lane() { not a definition }\";\n"
            "int func_lane(void) {\n"
            "    char close = '}'; /* } */\n"
            "    if (close) { return 7; }\n"
            "}\n"
        )
        expected = (
            "int func_lane(void) {\n"
            "    char close = '}'; /* } */\n"
            "    if (close) { return 7; }\n"
            "}"
        )
        self.assertEqual(_extract_function(text, "func_lane"), expected)

    def test_lane_budget_is_manifest_defined_and_receipt_is_only_a_proposal(self) -> None:
        manifest = make_manifest("record-1")
        missing_budget = dict(manifest)
        missing_budget["lane_budgets"] = dict(missing_budget["lane_budgets"])
        missing_budget["lane_budgets"].pop("upstream_current")
        with self.assertRaises(LaneError):
            run_lane(
                missing_budget,
                "upstream_current",
                {"record-1": recipient()},
                adapters={"upstream_current": lambda _item: ()},
            )

        bounded = make_manifest("record-1")
        bounded["lane_budgets"]["upstream_current"] = {
            "unit": "attempts",
            "limit": 1,
            "consumed": 0,
        }
        outcome = run_lane(
            bounded,
            "upstream_current",
            {"record-1": recipient()},
            adapters={
                "upstream_current": lambda _item: {
                    "candidates": [{"body": BODY}],
                    "attempts": 3,
                    "completion_reason": "search_space_exhausted",
                }
            },
        )[0]
        self.assertEqual(outcome.receipt.budget.limit, 1)
        self.assertEqual(outcome.receipt.budget.consumed, 1)
        self.assertEqual(outcome.receipt.attempts, 3)
        self.assertEqual(outcome.receipt.completion_reason, "budget_exhausted")
        self.assertFalse(outcome.receipt.materialized)
        self.assertNotIn("receipt_artifact", outcome.receipt.to_dict())
        self.assertIsInstance(outcome.receipt, LaneReceiptProposal)

    def test_receipt_proposal_interoperates_with_coordinator(self) -> None:
        manifest = make_manifest("record-1")
        coordinator_manifest = dict(manifest)
        outcome = run_lane(
            manifest,
            "upstream_current",
            {"record-1": recipient()},
            adapters={
                "upstream_current": lambda _item: {
                    "candidates": [],
                    "refusal_code": "no_definition",
                    "completion_reason": "inapplicable",
                    "reason": "no definition in this test",
                }
            },
        )[0]
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, RunManifest.from_dict(coordinator_manifest))
            receipt = coordinator.record_exhaustion(**outcome.receipt.to_coordinator_kwargs())
        self.assertEqual(receipt.receipt_id, outcome.receipt.receipt_id)
        self.assertEqual(receipt.input_identities, outcome.receipt.input_identities)

    def test_typed_inapplicable_receipt_is_preserved(self) -> None:
        manifest = make_manifest("record-1")

        def no_evidence(_item: Recipient):
            return {
                "candidates": [],
                "refusal_code": "no_definition",
                "reason": "producer has no exact definition",
                "completion_reason": "inapplicable",
                "rejection_counts": {"no_definition": 1},
            }

        outcome = run_lane(
            manifest,
            "upstream_current",
            {"record-1": recipient()},
            adapters={"upstream_current": no_evidence},
        )[0]
        self.assertEqual(outcome.receipt.completion_reason, "inapplicable")
        self.assertEqual(outcome.refusal.code, "no_definition")
        self.assertEqual(outcome.receipt.best_candidate_ids, ())
        self.assertEqual(dict(outcome.receipt.rejection_counts)["no_definition"], 1)

    def test_mipsmatch_exact_deduplicates_and_keeps_provenance(self) -> None:
        manifest = make_manifest("record-1")
        fixture = "automation/fixtures/search/mipsmatch-exact.json"
        duplicate_rows = [
            {
                "target_file": "src/lane.c",
                "target_function": "func_lane",
                "disposition": "exact-copy-a",
                "source_identity": hash_bytes(BODY.encode("utf-8")),
            },
            {
                "target_file": "src/lane.c",
                "target_function": "func_lane",
                "disposition": "exact-copy-b",
                "source_identity": hash_bytes(BODY.encode("utf-8")),
            },
        ]
        batch = run_lane(
            manifest,
            "mipsmatch_exact",
            {"record-1": recipient()},
            options={
                "mipsmatch_fixture": fixture,
                "duplicate_provenance": duplicate_rows,
            },
        )
        self.assertEqual(len(batch.candidates), 1)
        candidate = batch.candidates[0]
        self.assertEqual(candidate.source, BODY)
        exact_edges = [
            edge for edge in candidate.provenance if edge.get("kind") == "mipsmatch_exact"
        ]
        self.assertEqual(len(exact_edges), 2)
        self.assertEqual(
            len(exact_edges[0]["duplicate_provenance"]),
            2,
        )
        self.assertEqual(batch[0].receipt.completion_reason, "matched_pending_oracle")
        self.assertEqual(
            batch[0].receipt.best_candidate_ids,
            (candidate.candidate_id,),
        )
        repeat = run_lane(
            manifest,
            "mipsmatch_exact",
            {"record-1": recipient()},
            options={
                "mipsmatch_fixture": fixture,
                "duplicate_provenance": duplicate_rows,
            },
        )
        self.assertEqual(repeat[0].receipt.receipt_id, batch[0].receipt.receipt_id)
        self.assertEqual(repeat[0].candidates[0].candidate_id, candidate.candidate_id)

    def test_mipsmatch_scan_filters_only_exact_target(self) -> None:
        exact = json.loads(
            (Path(__file__).resolve().parent / "fixtures" / "search" / "mipsmatch-exact.json").read_text(
                encoding="utf-8"
            )
        )[0]
        rows = [
            exact,
            dict(exact, recipient_id="record-2"),
            dict(exact, exact=False, fingerprint_equal=False, match_kind="near"),
            dict(
                exact,
                recipient_id="record-1",
                exact=None,
                fingerprint_equal=None,
                target_fingerprint=None,
                candidate_fingerprint=None,
            ),
            dict(exact, recipient_id="record-1", exact=True, fingerprint="not-a-hash"),
            dict(
                exact,
                recipient_id="record-1",
                exact=False,
                fingerprint_equal=True,
            ),
            dict(exact, recipient_id="record-1", candidate_fingerprint=digest("different")),
            dict(exact, recipient_id="record-1", map_content_hash=digest("changed-map")),
            dict(exact, recipient_id="record-1", map_content=None, map_content_hash=None),
            dict(exact, recipient_id=None),
        ]
        selected = mipsmatch_scan(rows, target_recipient_id="record-1")
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["match_kind"], "exact")
        proof_row = dict(exact)
        proof_row.pop("exact")
        proof_row.pop("fingerprint_equal")
        proof_row["exact_proof"] = {"fingerprint_equal": True}
        self.assertEqual(
            len(mipsmatch_scan([proof_row], target_recipient_id="record-1")),
            1,
        )
        missing_reference = dict(exact, map_content=None, map_content_hash=None)
        outcome = run_lane(
            make_manifest("record-1"),
            "mipsmatch_exact",
            {"record-1": recipient()},
            options={"mipsmatch_matches": [missing_reference]},
        )[0]
        self.assertEqual(outcome.candidates, ())
        self.assertEqual(
            outcome.receipt.rejection_counts["missing_reference_identity"],
            1,
        )
        operation = mipsmatch_fingerprint(
            "build/map",
            "build/game.elf",
            map_content="map bytes",
            elf_content="elf bytes",
            tool_content="mipsmatch tool",
        )
        self.assertTrue(operation["read_only"])
        with self.assertRaises(LaneError):
            mipsmatch_fingerprint(
                "build/map",
                "build/game.elf",
                map_content="map bytes",
                elf_content="elf bytes",
                tool_identity=digest("different-tool"),
                tool_content="mipsmatch tool",
            )
        self.assertNotEqual(
            operation["reference_identity"],
            mipsmatch_fingerprint(
                "build/map",
                "build/game.elf",
                map_content="changed map bytes",
                elf_content="elf bytes",
                tool_content="mipsmatch tool",
            )["reference_identity"],
        )
        self.assertEqual(
            operation["reference_identity"],
            mipsmatch_fingerprint(
                "other/map",
                "other/game.elf",
                map_content="map bytes",
                elf_content="elf bytes",
                tool_content="mipsmatch tool",
            )["reference_identity"],
        )

    def test_mipsmatch_fixture_identities_are_content_linked(self) -> None:
        fixture = json.loads(
            (Path(__file__).resolve().parent / "fixtures" / "search" / "mipsmatch-exact.json").read_text(
                encoding="utf-8"
            )
        )
        exact_rows = [row for row in fixture if row.get("exact") is True]
        self.assertEqual(len(exact_rows), 2)
        for row in exact_rows:
            operation = mipsmatch_fingerprint(
                "ignored/map/path",
                "ignored/elf/path",
                map_content=row["map_content"],
                elf_content=row["elf_content"],
                tool_content=row["tool_content"],
            )
            self.assertEqual(row["map_content_hash"], operation["map_content_hash"])
            self.assertEqual(row["elf_content_hash"], operation["elf_content_hash"])
            self.assertEqual(row["tool_identity"], operation["tool_identity"])
            self.assertEqual(row["reference_identity"], operation["reference_identity"])
            self.assertEqual(row["reference_id"], row["reference_identity"])
            self.assertEqual(row["body_hash"], hash_bytes(row["body"].encode("utf-8")))
            self.assertEqual(row["target_fingerprint"], row["candidate_fingerprint"])

        donors = json.loads(
            (Path(__file__).resolve().parent / "fixtures" / "search" / "multi-donor.json").read_text(
                encoding="utf-8"
            )
        )
        for donor in donors:
            self.assertEqual(
                donor["source_identity"],
                hash_bytes(donor["body"].encode("utf-8")),
            )

    def test_donor_ordering_is_stable_and_exactly_deduplicated(self) -> None:
        path = Path(__file__).resolve().parent / "fixtures" / "search" / "multi-donor.json"
        donors = json.loads(path.read_text(encoding="utf-8"))
        ordered = gather_donors(recipient(), donors + [dict(donors[-1])])
        self.assertEqual(
            [item.donor_id for item in ordered],
            ["donor-symbol", "donor-instruction", "donor-cfg", "donor-dataflow"],
        )
        batch = run_lane(
            make_manifest("record-1"),
            "multi_donor",
            {"record-1": recipient()},
            options={"donors": donors},
        )
        self.assertEqual(len(batch.candidates), 1)
        self.assertEqual(batch[0].receipt.completion_reason, "matched_pending_oracle")
        self.assertGreaterEqual(
            len([item for item in batch[0].provenance if item.get("kind") == "semantic_donor"]),
            4,
        )

    def test_unsafe_register_and_branch_values_are_refused(self) -> None:
        self.assertFalse(is_safe_semantic_constant("$t0"))
        self.assertFalse(is_safe_semantic_constant("0x10", label="branch_displacement"))
        self.assertFalse(is_safe_semantic_constant("beq $t0, $t1, 4"))
        self.assertTrue(is_safe_semantic_constant(7))
        with self.assertRaises(UnsafeSemanticConstant):
            reject_unsafe_semantic_constant("$4")
        with self.assertRaises(UnsafeSemanticConstant):
            reject_unsafe_semantic_constant(4, label="branch_offset")

        unsafe = [{
            "donor_id": "unsafe-register",
            "recipient_id": "record-1",
            "version": "v1",
            "source": "corpus/unsafe.c",
            "match_kind": "symbol",
            "signature": "unsafe-sig",
            "symbol": "func_lane",
            "body": BODY,
            "constants": {"raw_register": "$t0"},
        }]
        outcome = run_lane(
            make_manifest("record-1"),
            "multi_donor",
            {"record-1": recipient()},
            options={"donors": unsafe},
        )[0]
        self.assertEqual(outcome.candidates, ())
        self.assertEqual(outcome.refusal.code, "unsafe_semantic_constant")
        self.assertEqual(outcome.receipt.completion_reason, "search_space_exhausted")
        self.assertGreaterEqual(
            dict(outcome.receipt.rejection_counts)["unsafe_semantic_constant"],
            1,
        )

    def test_incompatible_and_conflicting_donors_are_typed_refusals(self) -> None:
        manifest = make_manifest("record-1")
        incompatible = [{
            "donor_id": "incompatible",
            "recipient_id": "record-1",
            "version": "v1",
            "source": "corpus/incompatible.c",
            "match_kind": "symbol",
            "signature": "incompatible-sig",
            "symbol": "func_lane",
            "body": BODY,
            "compatible": False,
        }]
        incompatible_outcome = run_lane(
            manifest,
            "multi_donor",
            {"record-1": recipient()},
            options={"donors": incompatible},
        )[0]
        self.assertEqual(incompatible_outcome.candidates, ())
        self.assertEqual(incompatible_outcome.refusal.code, "incompatible_donor")
        self.assertEqual(
            incompatible_outcome.receipt.completion_reason,
            "search_space_exhausted",
        )

        conflicting = [
            {
                "donor_id": "decl-a",
                "recipient_id": "record-1",
                "match_kind": "symbol",
                "signature": "decl-a",
                "symbol": "func_lane",
                "body": BODY,
                "source_identity": hash_bytes(BODY.encode("utf-8")),
                "declarations": {"return_type": "int"},
            },
            {
                "donor_id": "decl-b",
                "recipient_id": "record-1",
                "match_kind": "symbol",
                "signature": "decl-b",
                "symbol": "func_lane",
                "body": BODY,
                "source_identity": hash_bytes(BODY.encode("utf-8")),
                "declarations": {"return_type": "void"},
            },
        ]
        conflict_outcome = run_lane(
            manifest,
            "multi_donor",
            {"record-1": recipient()},
            options={"donors": conflicting},
        )[0]
        self.assertEqual(conflict_outcome.candidates, ())
        self.assertEqual(conflict_outcome.refusal.code, "conflicting_declaration")
        self.assertTrue(conflict_outcome.refusal.evidence)
        self.assertEqual(
            conflict_outcome.receipt.completion_reason,
            "search_space_exhausted",
        )

    def test_run_lanes_requires_explicit_unique_lane_list(self) -> None:
        manifest = make_manifest("record-1")
        recipients = {"record-1": recipient()}
        with self.assertRaises(SubsetViolation):
            run_lanes(manifest, ["upstream_current"], None)
        with self.assertRaises(ValueError):
            # validate_lane rejects the unknown name with the schema exception,
            # so this branch documents that no arbitrary lane can be dispatched.
            run_lanes(manifest, ["unknown_lane"], recipients)
        run = run_lanes(
            manifest,
            ["upstream_current", "mipsmatch_exact"],
            recipients,
            adapters={
                "upstream_current": lambda _item: {
                    "candidates": [{"body": BODY}],
                    "completion_reason": "matched_pending_oracle",
                }
            },
        )
        self.assertEqual([item.lane for item in run.batches], ["upstream_current", "mipsmatch_exact"])
        self.assertEqual(tuple(DETERMINISTIC_LANES[:2]), ("upstream_current", "upstream_pinned"))

if __name__ == "__main__":
    unittest.main()
