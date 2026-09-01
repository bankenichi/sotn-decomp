#!/usr/bin/env python3
"""Focused production-provider registry regressions."""

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_generated_lanes import ArchivedTargetInput, build_bounded_synthesis_provider
from automation.search_lanes import LaneAdapters, Recipient
from automation.search_provider_lanes import (
    EXTERNAL_LANES,
    LANE_PROVIDER_REGISTRY,
    PROVIDER_STATE_CATEGORY,
    ProviderRegistryError,
    provider_state_document,
    reconstruct_lane_adapters,
    verify_lane_provider,
)
from automation.search_types import canonical_subset_identity, hash_bytes
from automation.test_search_schema import manifest


class ProviderRegistryTests(unittest.TestCase):
    def indexed_manifest(self):
        base = manifest()
        tools = dict(base.tool_identities)
        tools["indexed_runtime"] = hash_bytes(b"runtime")
        return replace(
            base,
            selected_lanes=("multi_donor", "cfg_dataflow"),
            tool_identities=tools,
            lane_budgets={
                "multi_donor": base.lane_budgets["multi_donor"],
                "cfg_dataflow": base.lane_budgets["cfg_dataflow"],
            },
        )

    @staticmethod
    def canonical_root(base: Path) -> Path:
        root = base / "nonmatchings" / "func_a" / "search-runs" / "run-a"
        root.mkdir(parents=True)
        return root

    @staticmethod
    def bounded_fixture(base: Path):
        """Build one real typed provider and its canonical archive envelope."""

        record_id = "us:ST:fn"
        base_manifest = manifest()
        value = replace(
            base_manifest,
            run_id="run-bounded",
            queue_record_ids=(record_id,),
            function_ids=(record_id,),
            subset_identity=canonical_subset_identity((record_id,)),
            target_identities={record_id: hash_bytes(b"target:" + record_id.encode())},
            selected_lanes=("bounded_synthesis",),
            tool_identities={
                "bounded_synthesis": base_manifest.tool_identities["bounded_synthesis"]
            },
            lane_budgets={"bounded_synthesis": base_manifest.lane_budgets["bounded_synthesis"]},
        )
        root = base / "nonmatchings" / "func_a" / "search-runs" / value.run_id
        root.mkdir(parents=True)
        archive = ContentAddressedArchive(root)
        assembly = b"fn:\n  jr $ra\n"
        target = ArchivedTargetInput(
            recipient_id=record_id,
            target_identity=value.target_identities[record_id],
            target_artifact=archive.put_bytes(
                assembly,
                category="target-assembly",
                suffix=".s",
                media_type="text/x-asm",
            ),
            target_bytes=assembly,
            symbol="fn",
            platform="us",
        )
        provider = build_bounded_synthesis_provider(
            value,
            (target,),
            archive=archive,
        )
        state = provider_state_document(value, {"bounded_synthesis": provider})
        archive.put_json(state, category=PROVIDER_STATE_CATEGORY)
        return value, root, archive, provider

    def test_indexed_builder_is_selected_once_for_both_lanes(self):
        value = self.indexed_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = self.canonical_root(Path(directory))
            callbacks = LaneAdapters(
                multi_donor=lambda _recipient: (),
                cfg_dataflow=lambda _recipient: (),
            )
            with patch(
                "automation.search_provider_lanes._indexed_provider",
                return_value=callbacks,
            ) as builder, patch.dict(
                "automation.search_provider_lanes.LANE_PROVIDER_REGISTRY",
                {
                    "multi_donor": builder,
                    "cfg_dataflow": builder,
                },
                clear=True,
            ):
                result = reconstruct_lane_adapters(value, root)
            self.assertIsNotNone(result.multi_donor)
            self.assertIsNotNone(result.cfg_dataflow)
            self.assertEqual(builder.call_count, 1)

    def test_factory_production_rejects_callback_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.canonical_root(Path(directory))
            with self.assertRaisesRegex(ProviderRegistryError, "reject caller"):
                reconstruct_lane_adapters(
                    self.indexed_manifest(),
                    root,
                    caller_adapters={"multi_donor": lambda _recipient: ()},
                )

    def test_empty_legacy_adapter_mapping_is_not_an_override(self):
        value = self.indexed_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = self.canonical_root(Path(directory))
            callbacks = LaneAdapters(
                multi_donor=lambda _recipient: (),
                cfg_dataflow=lambda _recipient: (),
            )
            with patch(
                "automation.search_provider_lanes._indexed_provider",
                return_value=callbacks,
            ) as builder, patch.dict(
                "automation.search_provider_lanes.LANE_PROVIDER_REGISTRY",
                {"multi_donor": builder, "cfg_dataflow": builder},
                clear=True,
            ):
                result = reconstruct_lane_adapters(
                    value,
                    root,
                    caller_adapters={},
                )
            self.assertIsNotNone(result.multi_donor)

    def test_missing_runtime_identity_fails_closed(self):
        value = self.indexed_manifest()
        tools = dict(value.tool_identities)
        del tools["indexed_runtime"]
        value = replace(value, tool_identities=tools)
        with tempfile.TemporaryDirectory() as directory:
            root = self.canonical_root(Path(directory))
            with self.assertRaisesRegex(ProviderRegistryError, "valid runtime"):
                reconstruct_lane_adapters(value, root)

    def test_verifier_reconstructs_the_same_registry_path(self):
        value = self.indexed_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = self.canonical_root(Path(directory))
            callbacks = LaneAdapters(
                multi_donor=lambda _recipient: (),
                cfg_dataflow=lambda _recipient: (),
            )
            with patch(
                "automation.search_provider_lanes._indexed_provider",
                return_value=callbacks,
            ) as builder, patch.dict(
                "automation.search_provider_lanes.LANE_PROVIDER_REGISTRY",
                {
                    "multi_donor": builder,
                    "cfg_dataflow": builder,
                },
                clear=True,
            ):
                verify_lane_provider(value, root)
            self.assertEqual(builder.call_count, 1)

    def test_registry_declares_exact_canonical_external_lanes_and_shared_builders(self):
        self.assertEqual(
            tuple(lane for lane in EXTERNAL_LANES if lane in LANE_PROVIDER_REGISTRY),
            EXTERNAL_LANES,
        )
        self.assertNotIn("permuter_baseline", LANE_PROVIDER_REGISTRY)
        self.assertNotIn("permuter_randomizer", LANE_PROVIDER_REGISTRY)
        self.assertNotIn("permuter_weights", LANE_PROVIDER_REGISTRY)
        self.assertNotIn("permuter_derived", LANE_PROVIDER_REGISTRY)
        self.assertIs(
            LANE_PROVIDER_REGISTRY["m2c_ensemble"],
            LANE_PROVIDER_REGISTRY["bounded_synthesis"],
        )
        self.assertIs(
            LANE_PROVIDER_REGISTRY["permuter_random"],
            LANE_PROVIDER_REGISTRY["permuter_ddmin"],
        )
        self.assertIs(
            LANE_PROVIDER_REGISTRY["model_fleet"],
            LANE_PROVIDER_REGISTRY["model_expensive"],
        )

    def test_bounded_provider_round_trips_from_archive_without_mining(self):
        with tempfile.TemporaryDirectory() as directory:
            value, root, _archive, provider = self.bounded_fixture(Path(directory))
            recipient = Recipient("us:ST:fn", "ST", "fn")
            expected = provider.callback(recipient)
            with patch(
                "automation.search_provider_lanes.GeneratedLaneProvider.from_dict",
                wraps=__import__(
                    "automation.search_generated_lanes",
                    fromlist=["GeneratedLaneProvider"],
                ).GeneratedLaneProvider.from_dict,
            ) as reconstruct:
                adapters = reconstruct_lane_adapters(value, root)
                replayed = adapters.bounded_synthesis(recipient)
            self.assertEqual(replayed, expected)
            self.assertEqual(reconstruct.call_count, 1)

    def test_state_unknown_or_forged_fields_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            value, root, archive, _provider = self.bounded_fixture(Path(directory))
            state_ref = next(
                path for path in (root / "artifacts" / PROVIDER_STATE_CATEGORY).iterdir()
                if path.suffix == ".json"
            )
            decoded = __import__("json").loads(state_ref.read_text(encoding="utf-8"))
            decoded["unexpected"] = True
            archive.put_json(decoded, category=PROVIDER_STATE_CATEGORY)
            with self.assertRaisesRegex(ProviderRegistryError, "unknown or missing"):
                reconstruct_lane_adapters(value, root)

    def test_missing_state_artifact_and_callback_injection_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            value, root, _archive, _provider = self.bounded_fixture(Path(directory))
            for path in (root / "artifacts" / PROVIDER_STATE_CATEGORY).iterdir():
                path.unlink()
            with self.assertRaisesRegex(ProviderRegistryError, "missing"):
                reconstruct_lane_adapters(value, root)
            with self.assertRaisesRegex(ProviderRegistryError, "reject caller"):
                reconstruct_lane_adapters(
                    value,
                    root,
                    caller_adapters={"upstream_current": lambda _recipient: ()},
                )

    def test_repeated_verification_reads_only_and_never_invokes_replayed_callback(self):
        with tempfile.TemporaryDirectory() as directory:
            value, root, archive, _provider = self.bounded_fixture(Path(directory))
            writes = []
            callback_calls = []
            original_put_json = archive.put_json
            with patch.object(
                archive,
                "put_json",
                side_effect=lambda *args, **kwargs: writes.append((args, kwargs)) or original_put_json(*args, **kwargs),
            ), patch(
                "automation.search_provider_lanes.GeneratedLaneProvider.from_dict",
                wraps=__import__(
                    "automation.search_generated_lanes",
                    fromlist=["GeneratedLaneProvider"],
                ).GeneratedLaneProvider.from_dict,
            ) as reconstruct:
                verify_lane_provider(value, root)
                verify_lane_provider(value, root)
            self.assertEqual(writes, [])
            self.assertEqual(reconstruct.call_count, 2)
            self.assertEqual(callback_calls, [])


if __name__ == "__main__":
    unittest.main()
