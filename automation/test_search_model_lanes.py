"""Focused acceptance tests for the durable model lane adapters."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_model_lanes import (
    MODEL_EXPENSIVE_LANE,
    MODEL_FLEET_LANE,
    ArchivedModelTargetInput,
    ModelBinding,
    ModelArtifactError,
    ModelInputError,
    ModelInvalidResponse,
    ModelLaneProvider,
    ModelProviderProtocolError,
    ModelRefused,
    ModelReplayError,
    ModelResponse,
    ModelSubsetViolation,
    ModelTimeout,
    MODEL_FAULT_AFTER_CALLBACK,
    MODEL_FAULT_AFTER_REQUEST,
    MODEL_FAULT_AFTER_RESPONSE,
    MODEL_FAULT_AFTER_RESULT,
    MODEL_FAULT_BEFORE_CALLBACK,
    MODEL_FAULT_BEFORE_REQUEST,
    build_model_expensive_provider,
    build_model_fleet_provider,
    model_lane_adapters,
)
from automation.search_types import (
    Budget,
    RunManifest,
    canonical_subset_identity,
    hash_bytes,
    hash_canonical,
    TIER_ORDER,
)


RECIPIENT = "us:MODEL:func_model_one"
OTHER_RECIPIENT = "us:MODEL:func_model_two"
TARGET_BYTES = b"void func_model_one(void) { return; }\n"
CONTEXT_BYTES = b"target context is archived\n"


def _hash(value: Any) -> str:
    return hash_canonical(value)


def _manifest(
    lane: str = MODEL_FLEET_LANE,
    *,
    budget_limit: int = 4,
    target_ids: Tuple[str, ...] = (RECIPIENT,),
) -> RunManifest:
    config = _hash({"config": "model-fixture"})
    tool = _hash({"tool": lane})
    ids = tuple(sorted(target_ids))
    return RunManifest(
        run_id="model-lane-test",
        created_at="2026-08-31T20:00:00+00:00",
        parent_run=None,
        queue_record_ids=ids,
        function_ids=ids,
        subset_identity=canonical_subset_identity(ids),
        queue_evidence_identity=_hash({"queue": ids}),
        selected_lanes=(lane,),
        source_identity=_hash({"source": "fixture"}),
        target_identities={item: _hash({"target": item}) for item in ids},
        compiler_identity=_hash({"compiler": "fixture"}),
        tool_identities={lane: tool},
        config_identity=config,
        schema_identity=_hash({"schema": "fixture"}),
        run_seed=7,
        epoch_size=1,
        frontier_cap=4,
        coordinator_budget=Budget("tasks", 8, 0),
        lane_budgets={lane: Budget("candidates", budget_limit, 0)},
        tier_order=TIER_ORDER,
    )


def _target(archive: ContentAddressedArchive, recipient: str = RECIPIENT) -> ArchivedModelTargetInput:
    target_ref = archive.put_bytes(
        TARGET_BYTES,
        category="target-assembly",
        suffix=".s",
        media_type="text/x-asm",
    )
    context_ref = archive.put_bytes(
        CONTEXT_BYTES,
        category="contexts",
        suffix=".txt",
        media_type="text/plain",
    )
    return ArchivedModelTargetInput(
        recipient_id=recipient,
        target_identity=_manifest(target_ids=(recipient,)).target_identities[recipient],
        target_artifact=target_ref,
        target_bytes=TARGET_BYTES,
        symbol=recipient.rsplit(":", 1)[-1],
        platform="us",
        context_artifacts=(context_ref,),
        context_bytes=(CONTEXT_BYTES,),
        metadata={"evidence": "fixture"},
    )


def _binding(manifest: RunManifest, lane: str = MODEL_FLEET_LANE, max_candidates: int = 4) -> ModelBinding:
    template = "Recover {symbol} ({target_identity}) on {platform}.\n{context}"
    return ModelBinding(
        provider_identity=_hash({"provider": "fixture", "lane": lane}),
        model_identity=_hash({"model": "fixture-model"}),
        model_name="fixture-model",
        prompt_identity=hash_bytes(template.encode("utf-8")),
        prompt_template=template,
        reasoning_identity=_hash({"reasoning": "medium"}),
        reasoning="medium",
        config_identity=manifest.config_identity,
        tool_identity=manifest.tool_identities[lane],
        max_candidates=max_candidates,
        max_response_bytes=65536,
    )


class FixtureProvider:
    def __init__(self, response_text: str = "", status: str = "ok") -> None:
        self.response_text = response_text or '{"candidates":[{"source":"int answer(void) { return 1; }"}]}'
        self.status = status
        self.calls = []

    def invoke(self, request, *, prompt: str, contexts: Tuple[bytes, ...]) -> ModelResponse:
        self.calls.append((request.request_id, prompt, contexts))
        return ModelResponse(
            request_id=request.request_id,
            status=self.status,
            response_text=self.response_text,
        )


class RaisingTimeoutProvider:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, request, *, prompt: str, contexts: Tuple[bytes, ...]) -> ModelResponse:
        self.calls += 1
        raise ModelTimeout("provider deadline reached")


class ModelProviderBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.archive = ContentAddressedArchive(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_fleet_success_is_an_ordinary_proposal_result(self) -> None:
        manifest = _manifest()
        provider = FixtureProvider()
        lane = build_model_fleet_provider(
            manifest,
            [_target(self.archive)],
            _binding(manifest),
            archive=self.archive,
            provider=provider,
        )
        self.assertEqual(provider.calls[0][0], lane.handoffs[0].request.request_id)
        result = lane.callback(
            __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict(
                {"recipient_id": RECIPIENT}
            )
        )
        self.assertEqual(result["completion_reason"], "search_space_exhausted")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["candidates"][0].record.lane, MODEL_FLEET_LANE)
        self.assertEqual(result["model_provider_identity"], lane.binding.provider_identity)
        self.assertEqual(result["prompt_identity"], lane.binding.prompt_identity)
        self.assertEqual(result["config_identity"], manifest.config_identity)
        self.assertEqual(result["tool_identity"], manifest.tool_identities[MODEL_FLEET_LANE])
        self.assertEqual(len(lane.handoffs), 1)
        self.assertIsNotNone(lane.handoffs[0].request.request_artifact)
        self.assertIsNotNone(lane.handoffs[0].response.response_artifact)
        self.assertEqual(lane.handoffs[0].response.status, "ok")

    def test_expensive_lane_uses_same_contract_with_its_own_binding(self) -> None:
        manifest = _manifest(MODEL_EXPENSIVE_LANE)
        lane = build_model_expensive_provider(
            manifest,
            [_target(self.archive)],
            _binding(manifest, MODEL_EXPENSIVE_LANE),
            archive=self.archive,
            provider=FixtureProvider(),
        )
        self.assertEqual(lane.lane, MODEL_EXPENSIVE_LANE)
        result = lane.callback(
            __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict(
                {"recipient_id": RECIPIENT}
            )
        )
        self.assertEqual(result["candidates"][0].record.lane, MODEL_EXPENSIVE_LANE)

    def test_model_lane_adapters_returns_only_selected_ordinary_callbacks(self) -> None:
        manifest = _manifest()
        adapters = model_lane_adapters(
            manifest,
            [_target(self.archive)],
            {MODEL_FLEET_LANE: _binding(manifest)},
            archive=self.archive,
            providers={MODEL_FLEET_LANE: FixtureProvider()},
        )
        self.assertEqual(set(adapters), {MODEL_FLEET_LANE})
        with self.assertRaises(ModelInputError):
            model_lane_adapters(
                manifest,
                [_target(self.archive)],
                {MODEL_FLEET_LANE: _binding(manifest), "not-a-lane": _binding(manifest)},
                archive=self.archive,
            )


class ModelReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.archive = ContentAddressedArchive(Path(self.temp.name))
        self.manifest = _manifest(budget_limit=3)
        self.binding = _binding(self.manifest, max_candidates=3)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_durable_handoff_prevents_provider_reinvocation_and_round_trips_bytes(self) -> None:
        first_provider = FixtureProvider(
            '{"candidates":[{"source":"int b(void) { return 2; }"},{"source":"int a(void) { return 1; }"}]}'
        )
        first = build_model_fleet_provider(
            self.manifest,
            [_target(self.archive)],
            self.binding,
            archive=self.archive,
            provider=first_provider,
        )
        state_bytes = __import__("automation.search_types", fromlist=["canonical_bytes"]).canonical_bytes(first.to_dict())
        rebuilt = ModelLaneProvider.from_dict(first.to_dict(), archive=self.archive)
        self.assertEqual(state_bytes, __import__("automation.search_types", fromlist=["canonical_bytes"]).canonical_bytes(rebuilt.to_dict()))
        second_provider = FixtureProvider(
            '{"candidates":[{"source":"this must not be called"}]}'
        )
        replay = build_model_fleet_provider(
            self.manifest,
            [_target(self.archive)],
            self.binding,
            archive=self.archive,
            provider=second_provider,
            durable_results=first.handoffs,
        )
        self.assertEqual(second_provider.calls, [])
        self.assertEqual(first.to_dict(), replay.to_dict())
        self.assertEqual(first.callback(
            __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict({"recipient_id": RECIPIENT})
        )["attempts"], 2)

    def test_deduplication_is_canonical_and_budget_caps_attempts(self) -> None:
        manifest = _manifest(budget_limit=1)
        binding = _binding(manifest, max_candidates=4)
        output = '{"candidates":[{"source":"z"},{"source":"z"},{"source":"a"}]}'
        lane = build_model_fleet_provider(
            manifest,
            [_target(self.archive)],
            binding,
            archive=self.archive,
            provider=FixtureProvider(output),
        )
        result = lane.callback(
            __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict({"recipient_id": RECIPIENT})
        )
        self.assertEqual(result["attempts"], 1)
        self.assertLessEqual(result["attempts"], manifest.lane_budgets[MODEL_FLEET_LANE].limit)
        self.assertEqual(result["model_overflow_observations"], 1)
        self.assertEqual(result["rejection_counts"]["duplicate_candidate"], 1)
        self.assertEqual(result["completion_reason"], "budget_exhausted")

    def test_zero_budget_is_typed_and_does_not_call_provider(self) -> None:
        manifest = _manifest(budget_limit=0)
        provider = FixtureProvider()
        lane = build_model_fleet_provider(
            manifest,
            [_target(self.archive)],
            _binding(manifest),
            archive=self.archive,
            provider=provider,
        )
        result = lane.callback(
            __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict({"recipient_id": RECIPIENT})
        )
        self.assertEqual(provider.calls, [])
        self.assertEqual(result["refusal_code"], "model_budget_exhausted")
        self.assertEqual(result["attempts"], 0)

    def test_missing_provider_is_typed_unavailable_without_live_fallback(self) -> None:
        lane = build_model_fleet_provider(
            self.manifest,
            [_target(self.archive)],
            self.binding,
            archive=self.archive,
            provider=None,
        )
        result = lane.callback(
            __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict({"recipient_id": RECIPIENT})
        )
        self.assertEqual(result["completion_reason"], "inapplicable")
        self.assertEqual(result["refusal_code"], "model_provider_unavailable")
        self.assertEqual(len(lane.handoffs), 1)
        self.assertEqual(lane.handoffs[0].response.status, "unavailable")

    def test_provider_timeout_is_typed(self) -> None:
        lane = build_model_fleet_provider(
            self.manifest,
            [_target(self.archive)],
            self.binding,
            archive=self.archive,
            provider=RaisingTimeoutProvider(),
        )
        result = lane.callback(
            __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict({"recipient_id": RECIPIENT})
        )
        self.assertEqual(result["refusal_code"], "model_provider_timeout")
        self.assertEqual(result["completion_reason"], "inapplicable")

    def test_invalid_provider_json_is_typed_invalid(self) -> None:
        lane = build_model_fleet_provider(
            self.manifest,
            [_target(self.archive)],
            self.binding,
            archive=self.archive,
            provider=FixtureProvider("not-json"),
        )
        result = lane.callback(
            __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict({"recipient_id": RECIPIENT})
        )
        self.assertEqual(result["refusal_code"], "model_provider_invalid_response")
        self.assertEqual(result["completion_reason"], "inapplicable")


class ModelRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.archive = ContentAddressedArchive(Path(self.temp.name))
        self.manifest = _manifest()
        self.binding = _binding(self.manifest)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_target_outside_manifest_subset_refuses(self) -> None:
        target = _target(self.archive, OTHER_RECIPIENT)
        with self.assertRaises(ModelSubsetViolation):
            build_model_fleet_provider(
                self.manifest, [target], self.binding, archive=self.archive, provider=FixtureProvider()
            )

    def test_wrong_manifest_target_identity_refuses(self) -> None:
        target = replace(target := _target(self.archive), target_identity=_hash({"other": True}))
        with self.assertRaises(ModelArtifactError):
            build_model_fleet_provider(
                self.manifest, [target], self.binding, archive=self.archive, provider=FixtureProvider()
            )

    def test_corrupt_archived_target_refuses(self) -> None:
        target = _target(self.archive)
        path = self.archive.resolve(target.target_artifact)
        path.write_bytes(b"corrupt")
        with self.assertRaises(Exception):
            build_model_fleet_provider(
                self.manifest, [target], self.binding, archive=self.archive, provider=FixtureProvider()
            )

    def test_untyped_callback_injection_is_rejected(self) -> None:
        with self.assertRaises(ModelProviderProtocolError):
            build_model_fleet_provider(
                self.manifest,
                [_target(self.archive)],
                self.binding,
                archive=self.archive,
                provider=lambda request: ModelResponse(request.request_id, "ok"),
            )

    def test_binding_and_manifest_identity_mismatch_refuses(self) -> None:
        changed = replace(self.binding, config_identity=_hash({"different": True}))
        with self.assertRaises(ModelInputError):
            build_model_fleet_provider(
                self.manifest, [_target(self.archive)], changed, archive=self.archive, provider=FixtureProvider()
            )

    def test_callback_requires_typed_recipient_and_exact_subset(self) -> None:
        lane = build_model_fleet_provider(
            self.manifest,
            [_target(self.archive)],
            self.binding,
            archive=self.archive,
            provider=FixtureProvider(),
        )
        with self.assertRaises(ModelInputError):
            lane.callback({"recipient_id": RECIPIENT})
        with self.assertRaises(ModelSubsetViolation):
            lane.callback(
                __import__("automation.search_lanes", fromlist=["Recipient"]).Recipient.from_dict(
                    {"recipient_id": OTHER_RECIPIENT}
                )
            )

    def test_target_serialization_requires_complete_bytes(self) -> None:
        target = _target(self.archive)
        value = target.to_dict()
        value.pop("target_bytes")
        with self.assertRaises(ModelInputError):
            ArchivedModelTargetInput.from_dict(value)


class EmptyProvider:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, request, *, prompt: str, contexts: Tuple[bytes, ...]) -> ModelResponse:
        self.calls += 1
        return ModelResponse(request.request_id, "ok", response_text="")


class RaisingRefusalProvider:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, request, *, prompt: str, contexts: Tuple[bytes, ...]) -> ModelResponse:
        self.calls += 1
        raise ModelRefused("explicit provider refusal")


class ModelArchiveReplayAndBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.archive = ContentAddressedArchive(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_archive_is_authoritative_without_caller_handoff_injection(self) -> None:
        manifest = _manifest(budget_limit=2)
        binding = _binding(manifest, max_candidates=2)
        first_provider = FixtureProvider()
        first = build_model_fleet_provider(
            manifest, [_target(self.archive)], binding, archive=self.archive, provider=first_provider
        )
        second_provider = FixtureProvider('{"candidates":[{"source":"must not run"}]}')
        replay = build_model_fleet_provider(
            manifest, [_target(self.archive)], binding, archive=self.archive, provider=second_provider
        )
        self.assertEqual(second_provider.calls, [])
        self.assertEqual(first.to_dict(), replay.to_dict())
        self.assertEqual(replay.external_calls_consumed, 1)

    def test_one_shot_fault_boundaries_leave_replay_safe_pending_or_terminal_state(self) -> None:
        pending_points = {
            MODEL_FAULT_AFTER_REQUEST,
            MODEL_FAULT_BEFORE_CALLBACK,
            MODEL_FAULT_AFTER_CALLBACK,
            MODEL_FAULT_AFTER_RESPONSE,
        }
        for point in (
            MODEL_FAULT_BEFORE_REQUEST,
            MODEL_FAULT_AFTER_REQUEST,
            MODEL_FAULT_BEFORE_CALLBACK,
            MODEL_FAULT_AFTER_CALLBACK,
            MODEL_FAULT_AFTER_RESPONSE,
            MODEL_FAULT_AFTER_RESULT,
        ):
            with self.subTest(point=point):
                with tempfile.TemporaryDirectory() as root:
                    archive = ContentAddressedArchive(Path(root))
                    manifest = _manifest(budget_limit=2)
                    binding = _binding(manifest, max_candidates=2)
                    seen = []

                    def fault(value: str, *, target=point) -> None:
                        seen.append(value)
                        if value == target:
                            raise RuntimeError("simulated process loss")

                    provider = FixtureProvider()
                    with self.assertRaises(RuntimeError):
                        build_model_fleet_provider(
                            manifest,
                            [_target(archive, RECIPIENT)],
                            binding,
                            archive=archive,
                            provider=provider,
                            fault_hook=fault,
                        )
                    replay_provider = FixtureProvider('{"candidates":[{"source":"must not run"}]}')
                    replay = build_model_fleet_provider(
                        manifest,
                        [_target(archive, RECIPIENT)],
                        binding,
                        archive=archive,
                        provider=replay_provider,
                    )
                    expected_calls = 1 if point == MODEL_FAULT_BEFORE_REQUEST else 0
                    self.assertEqual(len(replay_provider.calls), expected_calls)
                    if point in pending_points:
                        self.assertEqual(replay.results[0][1]["refusal_code"], "model_request_pending")
                        self.assertEqual(len(replay.pending_requests), 1)
                    elif point == MODEL_FAULT_AFTER_RESULT:
                        self.assertEqual(replay.results[0][1]["completion_reason"], "search_space_exhausted")
                    else:
                        self.assertEqual(len(replay.handoffs), 1)

    def test_external_call_budget_charges_unavailable_and_refuses_later_recipients(self) -> None:
        manifest = _manifest(
            budget_limit=1,
            target_ids=(RECIPIENT, OTHER_RECIPIENT),
        )
        binding = _binding(manifest, max_candidates=4)
        provider = FixtureProvider(status="unavailable")
        lane = build_model_fleet_provider(
            manifest,
            [_target(self.archive, RECIPIENT), _target(self.archive, OTHER_RECIPIENT)],
            binding,
            archive=self.archive,
            provider=provider,
        )
        calls = provider.calls if isinstance(provider.calls, int) else len(provider.calls)
        self.assertEqual(calls, 1)
        self.assertEqual(lane.external_calls_consumed, 1)
        by_recipient = dict(lane.results)
        self.assertEqual(by_recipient[RECIPIENT]["refusal_code"], "model_provider_unavailable")
        self.assertEqual(
            by_recipient[OTHER_RECIPIENT]["refusal_code"],
            "model_external_call_budget_exhausted",
        )
        self.assertEqual(by_recipient[OTHER_RECIPIENT]["external_call_consumed"], 0)

    def test_external_call_budget_charges_refused_timeout_invalid_and_empty(self) -> None:
        cases = (
            ("refused", RaisingRefusalProvider()),
            ("timeout", RaisingTimeoutProvider()),
            ("invalid", FixtureProvider("not-json")),
            ("empty", EmptyProvider()),
        )
        for label, provider in cases:
            with self.subTest(status=label):
                with tempfile.TemporaryDirectory() as root:
                    archive = ContentAddressedArchive(Path(root))
                    manifest = _manifest(
                        budget_limit=1,
                        target_ids=(RECIPIENT, OTHER_RECIPIENT),
                    )
                    binding = _binding(manifest, max_candidates=4)
                    lane = build_model_fleet_provider(
                        manifest,
                        [_target(archive, RECIPIENT), _target(archive, OTHER_RECIPIENT)],
                        binding,
                        archive=archive,
                        provider=provider,
                    )
                    self.assertEqual(lane.external_calls_consumed, 1)
                    calls = provider.calls if isinstance(provider.calls, int) else len(provider.calls)
                    self.assertEqual(calls, 1)
                    self.assertEqual(
                        dict(lane.results)[OTHER_RECIPIENT]["refusal_code"],
                        "model_external_call_budget_exhausted",
                    )

    def test_cross_subset_archive_request_is_refused_without_provider_call(self) -> None:
        manifest = _manifest(
            budget_limit=2,
            target_ids=(RECIPIENT, OTHER_RECIPIENT),
        )
        binding = _binding(manifest, max_candidates=2)
        first = build_model_fleet_provider(
            manifest,
            [_target(self.archive, RECIPIENT)],
            binding,
            archive=self.archive,
            provider=FixtureProvider(),
        )
        self.assertEqual(len(first.handoffs), 1)
        replay_provider = FixtureProvider()
        with self.assertRaises(ModelReplayError):
            build_model_fleet_provider(
                manifest,
                [_target(self.archive, OTHER_RECIPIENT)],
                binding,
                archive=self.archive,
                provider=replay_provider,
            )
        self.assertEqual(replay_provider.calls, [])

    def test_corrupt_request_archive_is_refused_before_provider_call(self) -> None:
        manifest = _manifest(budget_limit=2)
        binding = _binding(manifest, max_candidates=2)
        first = build_model_fleet_provider(
            manifest,
            [_target(self.archive)],
            binding,
            archive=self.archive,
            provider=FixtureProvider(),
        )
        request_path = self.archive.resolve(first.handoffs[0].request.request_artifact)
        request_path.write_bytes(b"forged")
        replay_provider = FixtureProvider()
        with self.assertRaises(ModelArtifactError):
            build_model_fleet_provider(
                manifest,
                [_target(self.archive)],
                binding,
                archive=self.archive,
                provider=replay_provider,
            )
        self.assertEqual(replay_provider.calls, [])


if __name__ == "__main__":
    unittest.main()
