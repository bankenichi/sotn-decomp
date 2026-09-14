"""Incomplete-handoff recovery for task-bound permuter seed decisions.

Covers IR5's remaining gap: a seed-handoff decision published before a crash
must rederive identically after recovery instead of duplicating or refusing.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ArchiveError, ContentAddressedArchive
from automation.search_coordinator import LANE_TIERS, _task_identity, _task_seed
from automation.search_ledger import AppendOnlyLedger
from automation.search_permuter_lanes import (
    PERMUTER_RANDOM_LANE,
    build_permuter_provider,
    default_permuter_config,
)
from automation.search_seed_handoff import TOOL_KEY, SeedHandoffError, bind_task_provider
from automation.search_types import SearchTask, hash_bytes
from automation.test_search_permuter_lanes import (
    binding_fixture,
    input_fixture,
    manifest as lane_manifest,
)


def _manifest_with_handoff(lane):
    """Lane fixture manifest with the seed-handoff tool bound."""
    base = lane_manifest(lane)
    return replace(
        base,
        tool_identities={**base.tool_identities, TOOL_KEY: hash_bytes(b"seed-handoff-tool")},
    )


def _scheduled_task(typed_manifest, lane):
    """Deterministically identified execute_lane task for the fixture input."""
    recipient = typed_manifest.queue_record_ids[0]
    tier = LANE_TIERS[lane]
    task_id = _task_identity(
        typed_manifest.run_id, recipient, lane, tier, "execute_lane", (),
        0, typed_manifest.config_identity,
    )
    return SearchTask(
        task_id=task_id,
        recipient_id=recipient,
        lane=lane,
        tier=tier,
        operation="execute_lane",
        parent_candidate_ids=(),
        budget_ordinal=0,
        task_seed=_task_seed(typed_manifest.run_seed, task_id),
        config_identity=typed_manifest.config_identity,
        state="scheduled",
    )


def _provider(directory, lane=PERMUTER_RANDOM_LANE):
    archive = ContentAddressedArchive(directory)
    typed_manifest = _manifest_with_handoff(lane)
    model_input = input_fixture(archive, lane_manifest(lane))
    binding = binding_fixture(archive, lane)
    provider = build_permuter_provider(
        lane,
        typed_manifest,
        {model_input.recipient_id: model_input},
        archive=archive,
        binding=binding,
        config=default_permuter_config(lane),
    )
    return archive, typed_manifest, model_input, provider


def _events_for(directory, archive, typed_manifest, scheduled):
    ledger = AppendOnlyLedger(Path(directory) / "ledger.jsonl", archive=archive)
    ledger.start_run(typed_manifest)
    ledger.append_event("task_scheduled", scheduled)
    return ledger.verify()


class SeedHandoffRecoveryTests(unittest.TestCase):
    def test_incomplete_handoff_rebinds_identically(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, typed_manifest, model_input, provider = _provider(directory)
            scheduled = _scheduled_task(typed_manifest, PERMUTER_RANDOM_LANE)
            events = _events_for(directory, archive, typed_manifest, scheduled)
            # First bind publishes the fallback decision: no measured parent
            # exists yet, so the frozen factory seed is retained.
            first = bind_task_provider(provider, scheduled, events)
            handoff_dir = Path(directory) / "artifacts" / "seed-handoffs"
            self.assertEqual(len(list(handoff_dir.glob("*.json"))), 1)
            # Simulate a crash after publication but before worker start by
            # dropping every in-memory object, then rebuild the provider
            # from the same durable archive and rebind the started task.
            del provider
            _, _, _, recovered = _provider(directory)
            second = bind_task_provider(
                recovered, replace(scheduled, state="started"), events
            )
            self.assertEqual(second._seed_handoff, first._seed_handoff)
            self.assertEqual(len(list(handoff_dir.glob("*.json"))), 1)
            self.assertEqual(second._task_input.seed_source, model_input.seed_source)
            binding = second._task_input.metadata["seed_handoff"]
            self.assertEqual(binding["task_id"], scheduled.task_id)
            self.assertIsNone(binding["selected"])

    def test_handoff_for_outside_recipient_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, typed_manifest, _, provider = _provider(directory)
            scheduled = _scheduled_task(typed_manifest, PERMUTER_RANDOM_LANE)
            events = _events_for(directory, archive, typed_manifest, scheduled)
            foreign_id = "us:ST:func_outside_subset"
            foreign = replace(
                scheduled,
                recipient_id=foreign_id,
                task_id=_task_identity(
                    typed_manifest.run_id, foreign_id, scheduled.lane,
                    scheduled.tier, scheduled.operation, (), 0,
                    typed_manifest.config_identity,
                ),
            )
            with self.assertRaises(SeedHandoffError):
                bind_task_provider(provider, foreign, events)

    def test_tampered_handoff_archive_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, typed_manifest, _, provider = _provider(directory)
            scheduled = _scheduled_task(typed_manifest, PERMUTER_RANDOM_LANE)
            events = _events_for(directory, archive, typed_manifest, scheduled)
            bind_task_provider(provider, scheduled, events)
            handoff_dir = Path(directory) / "artifacts" / "seed-handoffs"
            (path,) = list(handoff_dir.glob("*.json"))
            raw = path.read_bytes()
            # Flip the opening byte without renaming the file, so the
            # content hash no longer matches the artifact filename.
            path.write_bytes(bytes((raw[0] ^ 1,)) + raw[1:])
            with self.assertRaises(ArchiveError):
                bind_task_provider(provider, scheduled, events)


if __name__ == "__main__":
    unittest.main()
