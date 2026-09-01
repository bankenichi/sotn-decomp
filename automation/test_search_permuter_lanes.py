from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive, InjectedArchiveFault
from automation.search_lanes import Recipient
from automation.search_permuter_lanes import (
    ArchivedPermuterInput,
    PERMUTER_DDMIN_LANE,
    PERMUTER_LANES,
    PERMUTER_RANDOM_LANE,
    PERMUTER_RECOMBINE_LANE,
    PERMUTER_TARGETED_LANE,
    PermuterLaneConfig,
    PermuterProviderHandoffError,
    PermuterProviderInputError,
    PermuterProviderInvalidResponse,
    PermuterProviderRefused,
    PermuterProviderTimeout,
    PermuterProviderUnavailable,
    PermuterToolBinding,
    build_permuter_ddmin_provider,
    build_permuter_lane_adapters,
    build_permuter_provider,
    build_permuter_random_provider,
    build_permuter_recombine_provider,
    build_permuter_targeted_provider,
    default_permuter_config,
)
from automation.search_types import (
    Budget,
    RunManifest,
    canonical_subset_identity,
    hash_bytes,
)


def digest(value: str) -> str:
    return hash_bytes(value.encode("utf-8"))


def manifest(lane: str, *, run_id: str = "permuter-tests") -> RunManifest:
    record_id = "us:ST:func_permuter_test"
    return RunManifest(
        run_id=run_id,
        created_at="2026-08-31T00:00:00Z",
        parent_run=None,
        queue_record_ids=(record_id,),
        function_ids=(record_id,),
        subset_identity=canonical_subset_identity((record_id,)),
        queue_evidence_identity=digest("queue:" + record_id),
        selected_lanes=(lane,),
        source_identity=digest("source"),
        target_identities={record_id: digest("target:" + record_id)},
        compiler_identity=digest("compiler"),
        tool_identities={lane: digest("dispatch-tool:" + lane)},
        config_identity=digest("config"),
        schema_identity=digest("schema"),
        run_seed=17,
        epoch_size=4,
        frontier_cap=16,
        coordinator_budget=Budget("tasks", 4, 0),
        lane_budgets={lane: Budget("attempts", 4, 0)},
        tier_order=(
            "exact_deterministic",
            "structural_dependency",
            "cheap_generated",
            "compiler_guided",
            "model",
        ),
    )


def input_fixture(
    archive: ContentAddressedArchive,
    typed_manifest: RunManifest,
    *,
    seed: str = "int func_permuter_test(void) { return 1; }\n",
    assembly: str = "func_permuter_test:\n  jr $ra\n  nop\n",
) -> ArchivedPermuterInput:
    record_id = typed_manifest.queue_record_ids[0]
    seed_artifact = archive.put_text(
        seed,
        category="permuter-input",
        suffix=".c",
        media_type="text/x-c",
    )
    target_artifact = archive.put_text(
        assembly,
        category="permuter-input",
        suffix=".s",
        media_type="text/x-asm",
    )
    return ArchivedPermuterInput(
        recipient_id=record_id,
        target_identity=typed_manifest.target_identities[record_id],
        seed_artifact=seed_artifact,
        seed_source=seed,
        target_artifact=target_artifact,
        target_assembly=assembly,
        metadata={"platform": "us", "fixture": "immutable"},
    )


def binding_fixture(
    archive: ContentAddressedArchive,
    lane: str,
    *,
    available: bool = True,
) -> PermuterToolBinding:
    config = default_permuter_config(lane)
    tool = b"vendored decomp-permuter tool fixture\n"
    weights = b"weights-v1\n"
    tool_artifact = archive.put_bytes(
        tool,
        category="permuter-vendor",
        suffix=".tool",
        media_type="application/octet-stream",
    )
    weights_artifact = archive.put_bytes(
        weights,
        category="permuter-vendor",
        suffix=".weights",
        media_type="application/octet-stream",
    )
    return PermuterToolBinding(
        lane=lane,
        vendor_revision=digest("vendored-revision"),
        algorithm=config.algorithm,
        tool_artifact=tool_artifact,
        tool_bytes=tool,
        weights_artifact=weights_artifact,
        weights_bytes=weights,
        available=available,
        unavailable_reason="fixture binding unavailable" if not available else "",
    )


def provider_fixture(
    directory: str,
    lane: str = PERMUTER_RANDOM_LANE,
    *,
    callback=None,
    config: PermuterLaneConfig | None = None,
):
    archive = ContentAddressedArchive(directory)
    typed_manifest = manifest(lane)
    model_input = input_fixture(archive, typed_manifest)
    binding = binding_fixture(archive, lane)
    provider = build_permuter_provider(
        lane,
        typed_manifest,
        {model_input.recipient_id: model_input},
        archive=archive,
        binding=binding,
        config=config,
        executor_callback=callback,
    )
    return archive, typed_manifest, model_input, binding, provider


class PermuterLaneTests(unittest.TestCase):
    def test_all_four_factories_bind_distinct_algorithms(self) -> None:
        for lane, builder in (
            (PERMUTER_RANDOM_LANE, build_permuter_random_provider),
            (PERMUTER_TARGETED_LANE, build_permuter_targeted_provider),
            (PERMUTER_RECOMBINE_LANE, build_permuter_recombine_provider),
            (PERMUTER_DDMIN_LANE, build_permuter_ddmin_provider),
        ):
            with self.subTest(lane=lane), tempfile.TemporaryDirectory() as directory:
                archive = ContentAddressedArchive(directory)
                typed_manifest = manifest(lane, run_id="factory-" + lane)
                item = input_fixture(archive, typed_manifest)
                binding = binding_fixture(archive, lane)
                seen = []

                def executor(request):
                    seen.append(request)
                    return {"iterations": 1, "candidates": []}

                provider = builder(
                    typed_manifest,
                    {item.recipient_id: item},
                    archive=archive,
                    binding=binding,
                    executor_callback=executor,
                )
                result = provider.run(Recipient(item.recipient_id, "ST", "func_permuter_test"))
                self.assertEqual(result.lane, lane)
                self.assertEqual(result.algorithm, default_permuter_config(lane).algorithm)
                self.assertEqual(len(seen), 1)
                request = seen[0]
                self.assertEqual(request.lane, lane)
                self.assertEqual(request.algorithm, result.algorithm)
                self.assertTrue(request.vendor_revision.startswith("sha256:"))
                self.assertTrue(request.tool_identity.startswith("sha256:"))
                self.assertTrue(request.weights_identity.startswith("sha256:"))
                self.assertTrue(request.algorithm_identity.startswith("sha256:"))
                self.assertTrue(request.scratch_identity.startswith("sha256:"))
                self.assertNotIn("\\", request.scratch_path)
                self.assertTrue(request.scratch_path.startswith("permuter-scratch/"))

    def test_archived_seed_and_target_bytes_are_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest(PERMUTER_RANDOM_LANE)
            item = input_fixture(archive, typed_manifest)
            binding = binding_fixture(archive, PERMUTER_RANDOM_LANE)
            changed = ArchivedPermuterInput(
                recipient_id=item.recipient_id,
                target_identity=item.target_identity,
                seed_artifact=item.seed_artifact,
                seed_source=item.seed_source + "changed",
                target_artifact=item.target_artifact,
                target_assembly=item.target_assembly,
                metadata=item.metadata,
            )
            provider = build_permuter_random_provider(
                typed_manifest,
                {item.recipient_id: changed},
                archive=archive,
                binding=binding,
                executor_callback=lambda request: {"candidates": []},
            )
            with self.assertRaises(Exception) as error:
                provider.run(Recipient(item.recipient_id, "ST", "func_permuter_test"))
            self.assertIn("seed bytes differ", str(error.exception))

    def test_deduplicates_candidates_and_charges_unique_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def executor(request):
                calls.append(request)
                return {
                    "iterations": 7,
                    "candidates": [
                        {"source": "int f(void) { return 2; }\n", "score": 50, "iteration": 7},
                        {"source": "int f(void) { return 1; }\n", "score": 70, "iteration": 3},
                        {"source": "int f(void) { return 2; }\n", "score": 40, "iteration": 6},
                    ],
                    "state": {"rng": 42, "cursor": 7},
                    "best_score": 40,
                }

            archive, typed_manifest, item, binding, provider = provider_fixture(
                directory, callback=executor
            )
            result = provider.run(Recipient(item.recipient_id, "ST", "func_permuter_test"))
            self.assertEqual(len(calls), 1)
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.iterations, 7)
            self.assertEqual(result.budget.calls_consumed, 1)
            self.assertEqual(result.budget.candidates_consumed, 2)
            self.assertEqual(
                tuple(candidate.candidate_id for candidate in result.candidates),
                tuple(sorted(candidate.candidate_id for candidate in result.candidates)),
            )
            candidate_two = next(
                candidate for candidate in result.candidates
                if candidate.source == "int f(void) { return 2; }\n"
            )
            self.assertEqual(candidate_two.score, 40)
            self.assertEqual(result.to_discovery()["candidate_ids"], [
                candidate.candidate_id for candidate in result.candidates
            ])
            self.assertTrue(result.provenance)
            for edge in result.provenance:
                self.assertEqual(edge["lane"], PERMUTER_RANDOM_LANE)
                self.assertEqual(edge["recipient_id"], item.recipient_id)
                self.assertIn("scratch_identity", edge)
                self.assertIn("checkpoint_identity", edge)
            self.assertTrue(archive.resolve(result.checkpoint_artifact).is_file())

    def test_stop_checkpoint_resume_is_exact_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def executor(request):
                calls.append(request)
                if request.phase == "start":
                    return {
                        "status": "stopped",
                        "iterations": 5,
                        "candidates": [{"source": "int f(void) { return 1; }\n", "score": 80}],
                        "state": {"cursor": 5, "seed": "abc"},
                        "stop_reason": "operator_stop",
                    }
                return {
                    "status": "completed",
                    "iterations": 3,
                    "candidates": [{"source": "int f(void) { return 0; }\n", "score": 20}],
                    "state": {"cursor": 8, "seed": "abc"},
                }

            archive, typed_manifest, item, binding, provider = provider_fixture(
                directory,
                callback=executor,
                config=PermuterLaneConfig(
                    lane=PERMUTER_RANDOM_LANE,
                    algorithm="random",
                    max_calls=2,
                    max_iterations=10,
                    max_candidates=4,
                ),
            )
            recipient = Recipient(item.recipient_id, "ST", "func_permuter_test")
            stopped = provider.run(recipient)
            self.assertEqual(stopped.status, "stopped")
            self.assertEqual(stopped.completion_reason, "operator_stop")
            self.assertEqual(stopped.budget.calls_consumed, 1)
            self.assertEqual(stopped.budget.iterations_consumed, 5)
            self.assertEqual(len(calls), 1)
            resumed = provider.resume(recipient)
            self.assertEqual(resumed.status, "completed")
            self.assertEqual(resumed.phase, "resume")
            self.assertEqual(resumed.budget.calls_consumed, 2)
            self.assertEqual(resumed.budget.iterations_consumed, 8)
            self.assertEqual(len(resumed.candidates), 2)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[1].prior_checkpoint_identity, stopped.checkpoint_identity)
            self.assertEqual(calls[1].start_iteration, 5)
            replayed = provider.replay(recipient, resume=True)
            self.assertEqual(replayed, resumed)
            self.assertEqual(len(calls), 2)

    def test_crash_after_response_or_result_replays_without_executor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def fault(point, path):
                if point == "after_artifact_rename" and "permuter-results" in path.as_posix():
                    raise InjectedArchiveFault("simulated result publication crash")

            def executor(request):
                calls.append(request)
                return {
                    "iterations": 2,
                    "candidates": [{"source": "int f(void) { return 9; }\n"}],
                    "state": {"cursor": 2},
                }

            archive = ContentAddressedArchive(directory, fault_hook=fault)
            typed_manifest = manifest(PERMUTER_RANDOM_LANE)
            item = input_fixture(archive, typed_manifest)
            binding = binding_fixture(archive, PERMUTER_RANDOM_LANE)
            provider = build_permuter_random_provider(
                typed_manifest,
                {item.recipient_id: item},
                archive=archive,
                binding=binding,
                executor_callback=executor,
            )
            recipient = Recipient(item.recipient_id, "ST", "func_permuter_test")
            with self.assertRaises(PermuterProviderHandoffError):
                provider.run(recipient)
            self.assertEqual(len(calls), 1)

            recovered_archive = ContentAddressedArchive(directory)
            recovered = build_permuter_random_provider(
                typed_manifest,
                {item.recipient_id: item},
                archive=recovered_archive,
                binding=binding,
                executor_callback=lambda request: (_ for _ in ()).throw(
                    AssertionError("executor was reinvoked")
                ),
            )
            result = recovered.run(recipient)
            self.assertEqual(result.status, "completed")
            self.assertEqual(len(calls), 1)
            self.assertEqual(result.candidates[0].source, "int f(void) { return 9; }\n")

    def test_internal_type_error_is_propagated_once_and_retry_is_pending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def executor(request):
                calls.append(request)
                raise TypeError("executor implementation failure")

            archive, typed_manifest, item, binding, provider = provider_fixture(
                directory, callback=executor
            )
            recipient = Recipient(item.recipient_id, "ST", "func_permuter_test")
            with self.assertRaisesRegex(TypeError, "implementation failure"):
                provider.run(recipient)
            self.assertEqual(len(calls), 1)
            pending = provider.run(recipient)
            self.assertEqual(pending.status, "handoff_pending")
            self.assertEqual(len(calls), 1)

    def test_typed_provider_outcomes_are_durable(self) -> None:
        cases = (
            (PermuterProviderUnavailable, "unavailable"),
            (PermuterProviderRefused, "refused"),
            (PermuterProviderTimeout, "timeout"),
            (PermuterProviderInvalidResponse, "invalid_response"),
        )
        for index, (error_type, expected_status) in enumerate(cases):
            with self.subTest(expected_status=expected_status), tempfile.TemporaryDirectory() as directory:
                calls = []

                def executor(request, error_type=error_type):
                    calls.append(request)
                    raise error_type("fixture " + expected_status)

                archive, typed_manifest, item, binding, provider = provider_fixture(
                    directory, callback=executor
                )
                recipient = Recipient(item.recipient_id, "ST", "func_permuter_test")
                result = provider.run(recipient)
                self.assertEqual(result.status, expected_status)
                self.assertEqual(result.budget.calls_consumed, 1)
                self.assertTrue(result.refusal_code)
                self.assertEqual(len(calls), 1)
                replay = provider.replay(recipient)
                self.assertEqual(replay, result)
                self.assertEqual(len(calls), 1)

    def test_invalid_response_is_typed_durable_and_candidate_bound_is_hard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            def executor(request):
                return {
                    "iterations": 1,
                    "candidates": [
                        {"source": f"int f(void) {{ return {i}; }}\n"}
                        for i in range(9)
                    ],
                }

            config = PermuterLaneConfig(
                lane=PERMUTER_RANDOM_LANE,
                algorithm="random",
                max_candidates=8,
            )
            archive, typed_manifest, item, binding, provider = provider_fixture(
                directory, callback=executor, config=config
            )
            recipient = Recipient(item.recipient_id, "ST", "func_permuter_test")
            result = provider.run(recipient)
            self.assertEqual(result.status, "invalid_response")
            self.assertEqual(result.budget.candidates_consumed, 0)
            self.assertEqual(result.budget.calls_consumed, 1)
            self.assertEqual(provider.replay(recipient), result)

    def test_explicit_stop_then_resume_uses_durable_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def executor(request):
                calls.append(request)
                return {
                    "iterations": 2,
                    "candidates": [{"source": "int f(void) { return 3; }\n"}],
                    "state": {"cursor": 2},
                }

            archive, typed_manifest, item, binding, provider = provider_fixture(
                directory, callback=executor
            )
            recipient = Recipient(item.recipient_id, "ST", "func_permuter_test")
            stopped = provider.stop(recipient, reason="human stop")
            self.assertEqual(stopped.status, "stopped")
            self.assertEqual(stopped.budget.calls_consumed, 0)
            self.assertEqual(len(calls), 0)
            resumed = provider.resume(recipient)
            self.assertEqual(resumed.status, "completed")
            self.assertEqual(resumed.budget.calls_consumed, 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].start_iteration, 0)

    def test_missing_binding_is_a_typed_unavailable_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest(PERMUTER_RANDOM_LANE)
            item = input_fixture(archive, typed_manifest)
            provider = build_permuter_random_provider(
                typed_manifest,
                {item.recipient_id: item},
                archive=archive,
                executor_callback=lambda request: {"candidates": []},
            )
            result = provider.run(Recipient(item.recipient_id, "ST", "func_permuter_test"))
            self.assertEqual(result.status, "unavailable")
            self.assertEqual(result.refusal_code, "permuter_provider_unavailable")
            self.assertEqual(result.budget.calls_consumed, 0)

    def test_factory_adapters_cover_only_selected_permuter_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            selected = (PERMUTER_TARGETED_LANE,)
            typed_manifest = manifest(PERMUTER_TARGETED_LANE)
            item = input_fixture(archive, typed_manifest)
            binding = binding_fixture(archive, PERMUTER_TARGETED_LANE)
            adapters = build_permuter_lane_adapters(
                typed_manifest,
                [item],
                archive=archive,
                bindings={PERMUTER_TARGETED_LANE: binding},
                executors={
                    PERMUTER_TARGETED_LANE: lambda request: {
                        "iterations": 1,
                        "candidates": [{"source": "int f(void) { return 4; }\n"}],
                    }
                },
            )
            self.assertEqual(set(adapters), set(selected))
            discovery = adapters[PERMUTER_TARGETED_LANE](
                Recipient(item.recipient_id, "ST", "func_permuter_test")
            )
            self.assertEqual(len(discovery["candidates"]), 1)
            self.assertIn("result_identity", discovery)
            self.assertNotIn("queue", discovery)
            self.assertNotIn("repo_root", discovery)

    def test_reordered_input_sequence_has_same_provider_identity(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first_archive = ContentAddressedArchive(first_directory)
            second_archive = ContentAddressedArchive(second_directory)
            typed_manifest = manifest(PERMUTER_RECOMBINE_LANE)
            first_item = input_fixture(first_archive, typed_manifest)
            second_item = input_fixture(second_archive, typed_manifest)
            first_binding = binding_fixture(first_archive, PERMUTER_RECOMBINE_LANE)
            second_binding = binding_fixture(second_archive, PERMUTER_RECOMBINE_LANE)
            first = build_permuter_recombine_provider(
                typed_manifest,
                [first_item],
                archive=first_archive,
                binding=first_binding,
                executor_callback=lambda request: {"candidates": []},
            )
            second = build_permuter_recombine_provider(
                typed_manifest,
                list(reversed([second_item])),
                archive=second_archive,
                binding=second_binding,
                executor_callback=lambda request: {"candidates": []},
            )
            self.assertEqual(first.provider_identity, second.provider_identity)
            self.assertEqual(first.to_dict(), second.to_dict())

    def test_checkpoint_and_result_serialization_reject_identity_forgery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, typed_manifest, item, binding, provider = provider_fixture(
                directory, callback=lambda request: {
                    "iterations": 1,
                    "candidates": [{"source": "int f(void) { return 5; }\n"}],
                }
            )
            result = provider.run(Recipient(item.recipient_id, "ST", "func_permuter_test"))
            forged = result.to_dict()
            forged["result_identity"] = digest("forged")
            with self.assertRaises(Exception):
                type(result).from_dict(forged)


    def test_provider_round_trip_reconstructs_verified_state_without_executor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def executor(request):
                calls.append(request)
                return {
                    "iterations": 2,
                    "candidates": [{"source": "int f(void) { return 6; }\n"}],
                    "state": {"cursor": 2},
                }

            archive, typed_manifest, item, binding, provider = provider_fixture(
                directory, callback=executor
            )
            recipient = Recipient(item.recipient_id, "ST", "func_permuter_test")
            result = provider.run(recipient)
            state = provider.to_dict()
            self.assertIn("manifest", state)
            self.assertIn("config", state)
            self.assertIn("binding", state)
            self.assertIn("inputs", state)
            self.assertNotIn("executor_callback", state)

            reconstructed = type(provider).from_dict(state, archive=archive)
            self.assertEqual(reconstructed.to_dict(), state)
            replayed = reconstructed.replay(recipient)
            self.assertEqual(replayed, result)
            self.assertEqual(len(calls), 1)

            forged = dict(state)
            forged["binding"] = dict(state["binding"])
            forged["binding"]["tool_identity"] = digest("forged-tool")
            with self.assertRaises(PermuterProviderInputError):
                type(provider).from_dict(forged, archive=archive)

    def test_provider_round_trip_rejects_corrupt_archive_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, typed_manifest, item, binding, provider = provider_fixture(
                directory, callback=lambda request: {"candidates": []}
            )
            state = provider.to_dict()
            seed_path = archive.resolve(item.seed_artifact)
            original = seed_path.read_bytes()
            try:
                seed_path.write_bytes(original + b"corrupt")
                with self.assertRaises(PermuterProviderInputError):
                    type(provider).from_dict(state, archive=archive)
            finally:
                seed_path.write_bytes(original)



if __name__ == "__main__":
    unittest.main()
