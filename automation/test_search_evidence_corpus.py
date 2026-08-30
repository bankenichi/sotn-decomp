"""Task 0 tests: consuming the canonical Task 8.2 integration prerequisite."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_evidence_corpus import (
    CorpusGeneration,
    build_corpus_generation,
)
from automation.search_supervisor import (
    EVALUATOR_TOOL_KEY,
    INSTRUMENTED_MODE,
    IntegrationGateError,
    MODE_TOOL_KEY,
    archive_integration_gate,
    load_integration_gate,
    mode_identity,
)
from automation.search_types import hash_bytes
from automation.test_search_schema import manifest


def digest(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


def gate_manifest(*, queue_evidence_identity: str | None = None):
    """Return a factory-shaped manifest bound for one integration run."""

    base = manifest()
    tools = dict(base.tool_identities)
    tools[MODE_TOOL_KEY] = mode_identity(INSTRUMENTED_MODE)
    tools["search_coordinator"] = digest("coordinator")
    tools[EVALUATOR_TOOL_KEY] = digest("search-evaluator")
    tools["full_oracle"] = digest("full-oracle")
    lanes = ("cfg_dataflow",)
    value = replace(
        base,
        selected_lanes=lanes,
        tool_identities=tools,
        lane_budgets={"cfg_dataflow": base.lane_budgets["cfg_dataflow"]},
    )
    if queue_evidence_identity is not None:
        value = replace(value, queue_evidence_identity=queue_evidence_identity)
    return value


def fixture_gate(archive: ContentAddressedArchive, *, queue_evidence_identity: str | None = None):
    """Archive and canonically validate one Task 8.2 integration receipt.

    Altered identities produce a distinct archived receipt; nothing mutates a
    receipt in memory.
    """

    receipt = archive_integration_gate(
        gate_manifest(queue_evidence_identity=queue_evidence_identity),
        archive=archive,
    )
    load_integration_gate(receipt.to_dict(), archive=archive)
    return receipt


def fixture_gate_with_corrupt_receipt_artifact(
    archive: ContentAddressedArchive,
):
    receipt = fixture_gate(archive)
    path = archive.resolve(receipt.receipt_artifact)
    path.write_bytes(b"x" * receipt.receipt_artifact.byte_size)
    return receipt


class CanonicalGateConsumerTests(unittest.TestCase):
    def test_missing_canonical_gate_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            with self.assertRaisesRegex(IntegrationGateError, "integration gate"):
                build_corpus_generation(
                    (),
                    integration_gate=None,
                    schema_identity=digest("schema"),
                    archive=archive,
                )

    def test_changed_valid_gate_creates_a_distinct_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            original = fixture_gate(archive)
            altered = fixture_gate(
                archive,
                queue_evidence_identity=digest("changed-queue-evidence"),
            )
            first = build_corpus_generation(
                (),
                integration_gate=original,
                schema_identity=digest("schema"),
                archive=archive,
            )
            second = build_corpus_generation(
                (),
                integration_gate=altered,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertNotEqual(first.generation_id, second.generation_id)

    def test_corrupt_canonical_gate_artifact_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            corrupt = fixture_gate_with_corrupt_receipt_artifact(archive)
            with self.assertRaisesRegex(IntegrationGateError, "receipt artifact"):
                build_corpus_generation(
                    (),
                    integration_gate=corrupt,
                    schema_identity=digest("schema"),
                    archive=archive,
                )

    def test_generation_retains_complete_canonical_gate_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            generation = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertIsInstance(generation, CorpusGeneration)
            self.assertEqual(generation.integration_gate.to_dict(), gate.to_dict())
            self.assertEqual(generation.integration_gate_id, gate.gate_id)
            self.assertEqual(
                generation.manifest_artifact_identity,
                gate.manifest_artifact_identity,
            )
            self.assertEqual(generation.subset_identity, gate.subset_identity)
            self.assertEqual(
                generation.queue_evidence_identity,
                gate.queue_evidence_identity,
            )
            self.assertEqual(tuple(generation.selected_lanes), gate.selected_lanes)
            self.assertEqual(
                generation.coordinator_identity,
                gate.coordinator_identity,
            )
            self.assertEqual(
                generation.connector_identity,
                gate.connector_identity,
            )
            payload = json.loads(archive.verify(generation.artifact).decode("utf-8"))
            self.assertEqual(
                payload["integration_gate"]["gate_id"],
                gate.gate_id,
            )
            self.assertEqual(
                payload["integration_gate"]["receipt_artifact"],
                gate.receipt_artifact.to_dict(),
            )
            self.assertEqual(
                payload["integration_gate"]["manifest_artifact_identity"],
                gate.manifest_artifact_identity,
            )
            self.assertEqual(
                payload["integration_gate"]["subset_identity"],
                gate.subset_identity,
            )
            self.assertEqual(
                tuple(payload["integration_gate"]["selected_lanes"]),
                gate.selected_lanes,
            )
            self.assertEqual(
                payload["integration_gate"]["coordinator_identity"],
                gate.coordinator_identity,
            )
            self.assertEqual(
                payload["integration_gate"]["connector_identity"],
                gate.connector_identity,
            )

    def test_generation_identity_covers_schema_and_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "archive")
            gate = fixture_gate(archive)
            first = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            second = build_corpus_generation(
                (),
                integration_gate=gate,
                schema_identity=digest("other-schema"),
                archive=archive,
            )
            third = build_corpus_generation(
                ({"evidence_id": digest("entry-1"), "kind": "lesson"},
                 {"evidence_id": digest("entry-2"), "kind": "refusal"}),
                integration_gate=gate,
                schema_identity=digest("schema"),
                archive=archive,
            )
            self.assertNotEqual(first.generation_id, second.generation_id)
            self.assertNotEqual(first.generation_id, third.generation_id)
            self.assertEqual(len(third.entries), 2)


if __name__ == "__main__":
    unittest.main()
