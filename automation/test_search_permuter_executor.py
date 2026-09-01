from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_lanes import Recipient
from automation.search_permuter_lanes import (
    ArchivedPermuterInput,
    PERMUTER_RANDOM_LANE,
    PermuterCheckpoint,
    PermuterHandoffStore,
    PermuterLaneConfig,
    PermuterToolBinding,
    build_permuter_random_provider,
    default_permuter_config,
)
import automation.search_permuter_executor as executor_module
from automation.search_permuter_executor import (
    PermuterExecutor,
    PermuterExecutorInputError,
    PermuterExecutorInvalidResponse,
    PermuterExecutorUnavailable,
    PermuterRuntimeBinding,
    _ALGORITHM_MAP,
    _stable_seed,
    build_permuter_executor,
    vendored_runner_identity,
    vendored_tree_identity,
)
from automation.search_types import (
    Budget,
    RunManifest,
    canonical_subset_identity,
    hash_bytes,
    hash_canonical,
)


def digest(value: str) -> str:
    return hash_bytes(value.encode("utf-8"))


def make_manifest(
    lane: str = PERMUTER_RANDOM_LANE,
    *,
    run_id: str = "permuter-executor-tests",
    config: PermuterLaneConfig | None = None,
) -> RunManifest:
    record_id = "us:ST:func_permuter_executor_test"
    config = config or default_permuter_config(lane)
    return RunManifest(
        run_id=run_id,
        created_at="2026-08-31T00:00:00Z",
        parent_run=None,
        queue_record_ids=(record_id,),
        function_ids=(record_id,),
        subset_identity=canonical_subset_identity((record_id,)),
        queue_evidence_identity=digest("queue:" + record_id),
        selected_lanes=(lane,),
        source_identity=digest("source:" + run_id),
        target_identities={record_id: digest("target:" + record_id)},
        compiler_identity=digest("compiler:" + run_id),
        tool_identities={lane: digest("manifest-tool:" + lane)},
        config_identity=config.identity,
        schema_identity=digest("schema:" + run_id),
        run_seed=17,
        epoch_size=4,
        frontier_cap=16,
        coordinator_budget=Budget("tasks", 4, 0),
        lane_budgets={lane: Budget("attempts", config.max_calls, 0)},
        tier_order=(
            "exact_deterministic",
            "structural_dependency",
            "cheap_generated",
            "compiler_guided",
            "model",
        ),
    )


def make_input(
    archive: ContentAddressedArchive,
    typed_manifest: RunManifest,
    *,
    seed: str = "int func_permuter_executor_test(void) { return 1; }\n",
    assembly: str = "func_permuter_executor_test:\n  jr $ra\n  nop\n",
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


def make_binding(archive: ContentAddressedArchive, lane: str) -> PermuterToolBinding:
    vendor_root = Path(__file__).resolve().parents[1] / "tools" / "decomp-permuter"
    runner = (vendor_root / "permuter.py").read_bytes()
    weights = (vendor_root / "default_weights.toml").read_bytes()
    runner_artifact = archive.put_bytes(
        runner,
        category="permuter-vendor",
        suffix=".py",
        media_type="text/x-python",
    )
    weights_artifact = archive.put_bytes(
        weights,
        category="permuter-vendor",
        suffix=".toml",
        media_type="application/toml",
    )
    return PermuterToolBinding(
        lane=lane,
        vendor_revision=vendored_tree_identity(vendor_root),
        algorithm=default_permuter_config(lane).algorithm,
        algorithm_identity=default_permuter_config(lane).algorithm_identity,
        tool_artifact=runner_artifact,
        tool_bytes=runner,
        weights_artifact=weights_artifact,
        weights_bytes=weights,
    )


def make_runtime(
    archive: ContentAddressedArchive,
    evaluator_identity: str,
) -> PermuterRuntimeBinding:
    script = b"#!/bin/sh\nexec cc \"$@\"\n"
    script_artifact = archive.put_bytes(
        script,
        category="permuter-runtime",
        suffix=".sh",
        media_type="text/x-shellscript",
    )
    object_bytes = b"immutable target object fixture\n"
    object_artifact = archive.put_object(object_bytes)
    return PermuterRuntimeBinding(
        evaluator_identity=evaluator_identity,
        compile_script_artifact=script_artifact,
        compile_script_bytes=script,
        compiler_type="base",
        function_name="func_permuter_executor_test",
        target_object_artifact=object_artifact,
        target_object_bytes=object_bytes,
    )


def make_fixture(
    directory: str,
    *,
    config: PermuterLaneConfig | None = None,
    runtime: bool = False,
):
    lane = PERMUTER_RANDOM_LANE
    archive = ContentAddressedArchive(directory)
    typed_manifest = make_manifest(lane, config=config)
    item = make_input(archive, typed_manifest)
    binding = make_binding(archive, lane)
    provider = build_permuter_random_provider(
        typed_manifest,
        {item.recipient_id: item},
        archive=archive,
        binding=binding,
        config=config,
        executor_callback=lambda request: {"candidates": []},
    )
    request = provider._request(item, "start")
    owned_runtime = make_runtime(archive, request.evaluator_identity) if runtime else None
    executor = build_permuter_executor(
        archive,
        binding,
        runtime=owned_runtime,
        timeout_seconds=10,
    )
    recipient = Recipient(item.recipient_id, "ST", "func_permuter_executor_test")
    return archive, typed_manifest, item, binding, provider, request, executor, recipient


class PermuterExecutorTests(unittest.TestCase):
    def test_production_builder_is_a_real_typed_callable_without_callback_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = make_fixture(directory)
            executor = fixture[6]
            self.assertTrue(callable(executor))
            self.assertFalse(hasattr(executor, "executor_callback"))
            self.assertTrue(callable(executor.execute))
            serialized = executor.to_dict()
            self.assertEqual(serialized["executor_identity"], executor.identity)
            self.assertIsNone(serialized["runtime"])

    def test_executor_round_trip_rechecks_archive_binding_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, _binding, _provider, _request, executor, _recipient = make_fixture(
                directory, runtime=True
            )
            serialized = executor.to_dict()
            rebuilt = PermuterExecutor.from_dict(serialized, archive=archive)
            self.assertEqual(rebuilt.to_dict(), serialized)
            forged = dict(serialized)
            forged["runner_relative_path"] = "tools/other-runner.py"
            with self.assertRaises(PermuterExecutorInputError):
                PermuterExecutor.from_dict(forged, archive=archive)

    def test_real_vendor_preflight_fails_closed_when_runtime_inputs_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, binding, _provider, request, executor, _recipient = make_fixture(directory)
            report = executor.preflight(request)
            self.assertEqual(report.status, "unavailable")
            self.assertEqual(report.refusal_code, "permuter_runner_inputs_unavailable")
            self.assertEqual(report.runner_identity, vendored_runner_identity(executor.vendor_root))
            self.assertEqual(report.vendor_revision, binding.vendor_revision)
            self.assertIn("archive-bound compile script", report.reason)
            with self.assertRaises(PermuterExecutorUnavailable):
                executor(request)
            self.assertTrue(executor.vendor_root.is_dir())

    def test_real_vendor_preflight_is_ready_with_archive_runtime_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _archive, _manifest, _item, _binding, _provider, request, executor, _recipient = make_fixture(
                directory, runtime=True
            )
            report = executor.preflight(request)
            self.assertTrue(report.ready)
            self.assertEqual(report.platform, "native-posix")
            self.assertEqual(report.runtime_identity, executor.runtime.runtime_identity)

    def test_runtime_binding_round_trip_is_archive_backed_and_strict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, _binding, _provider, _request, executor, _recipient = make_fixture(
                directory, runtime=True
            )
            runtime = executor.runtime
            rebuilt = PermuterRuntimeBinding.from_dict(runtime.to_dict(), archive=archive)
            self.assertEqual(rebuilt, runtime)
            forged = dict(runtime.to_dict())
            forged["unexpected"] = True
            with self.assertRaises(PermuterExecutorInputError):
                PermuterRuntimeBinding.from_dict(forged, archive=archive)

    def test_materialization_uses_verified_vendor_snapshot_and_parser_is_typed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, _binding, _provider, request, executor, _recipient = make_fixture(
                directory, runtime=True
            )
            seed_bytes, target_bytes = executor._verify_request(request)
            runner_bytes, weights_bytes = executor._verify_binding()
            scratch, vendor, seed = executor._materialize(
                request,
                seed_bytes,
                target_bytes,
                runner_bytes,
                weights_bytes,
                {},
            )
            self.assertEqual(scratch.parent, archive.run_root / "permuter-scratch" / request.lane)
            self.assertTrue((vendor / "permuter.py").is_file())
            self.assertEqual((vendor / "permuter.py").read_bytes(), runner_bytes)
            self.assertEqual((vendor / "default_weights.toml").read_bytes(), weights_bytes)
            self.assertFalse((scratch / "scratch-root").exists())
            marker = json.loads((scratch / "executor-request.json").read_text())
            self.assertEqual(marker["request_identity"], request.request_identity)
            before = frozenset(path.name for path in scratch.iterdir())
            output = scratch / "output-7-1"
            output.mkdir()
            source = "int func_permuter_executor_test(void) { return 7; }\n"
            (output / "source.c").write_text(source)
            (output / "score.txt").write_text("7\n")
            (output / "diff.txt").write_text("diff\n")
            response = executor._parse_output(
                request,
                scratch,
                before,
                "iteration 1, 0 errors, score = 7\n",
                0,
                False,
                _ALGORITHM_MAP[request.algorithm],
                seed,
            )
            self.assertEqual(response["status"], "completed")
            self.assertEqual(response["iterations"], 1)
            self.assertEqual(response["best_score"], 7.0)
            self.assertEqual(response["candidates"][0]["source"], source)
            self.assertEqual(response["candidates"][0]["provenance"]["runner_seed"], seed)

    def test_parser_rejects_score_file_forgery_and_iteration_overflow(self) -> None:
        config = PermuterLaneConfig(
            lane=PERMUTER_RANDOM_LANE,
            algorithm="random",
            max_iterations=3,
        )
        with tempfile.TemporaryDirectory() as directory:
            _archive, _manifest, _item, _binding, _provider, request, executor, _recipient = make_fixture(
                directory, config=config, runtime=True
            )
            seed_bytes, target_bytes = executor._verify_request(request)
            runner_bytes, weights_bytes = executor._verify_binding()
            scratch, _vendor, seed = executor._materialize(
                request, seed_bytes, target_bytes, runner_bytes, weights_bytes, {}
            )
            before = frozenset(path.name for path in scratch.iterdir())
            output = scratch / "output-4-1"
            output.mkdir()
            (output / "source.c").write_text("int func_permuter_executor_test(void) { return 4; }\n")
            (output / "score.txt").write_text("5\n")
            with self.assertRaises(PermuterExecutorInvalidResponse):
                executor._parse_output(
                    request,
                    scratch,
                    before,
                    "iteration 1, 0 errors, score = 4\n",
                    0,
                    False,
                    "difflib",
                    seed,
                )
            (output / "score.txt").write_text("4\n")
            with self.assertRaises(PermuterExecutorInvalidResponse):
                executor._parse_output(
                    request,
                    scratch,
                    before,
                    "iteration 4, 0 errors, score = 4\n",
                    0,
                    False,
                    "difflib",
                    seed,
                )

            (output / "source.c").write_bytes(b"int func_permuter_executor_test(void) {\x00 return 4; }\n")
            with self.assertRaises(PermuterExecutorInvalidResponse):
                executor._parse_output(
                    request,
                    scratch,
                    before,
                    "iteration 1, 0 errors, score = 4\n",
                    0,
                    False,
                    "difflib",
                    seed,
                )

    def test_controlled_process_stop_enforces_iteration_bound(self) -> None:
        config = PermuterLaneConfig(
            lane=PERMUTER_RANDOM_LANE,
            algorithm="random",
            max_iterations=2,
        )
        with tempfile.TemporaryDirectory() as directory:
            _archive, _manifest, _item, _binding, _provider, request, executor, _recipient = make_fixture(
                directory, config=config
            )
            command = [
                sys.executable,
                "-u",
                "-c",
                "import time\n"
                "for i in range(1, 100):\n"
                " print(f'iteration {i}, 0 errors, score = 1', flush=True)\n"
                " time.sleep(0.05)\n",
            ]
            returncode, output, controlled_stop = executor._run_process(
                command,
                None,
                request,
                iteration_limit=request.start_iteration + request.max_iterations,
            )
            self.assertTrue(controlled_stop)
            self.assertIn("iteration 2,", output)
            self.assertNotIn("iteration 20,", output)
            self.assertNotEqual(returncode, 0)

    def test_resume_checkpoint_is_verified_as_an_archive_document(self) -> None:
        config = PermuterLaneConfig(
            lane=PERMUTER_RANDOM_LANE,
            algorithm="random",
            max_iterations=8,
        )
        with tempfile.TemporaryDirectory() as directory:
            archive, manifest, item, binding, provider, start_request, executor, _recipient = make_fixture(
                directory, config=config, runtime=True
            )
            state = {
                "protocol": "sotn-permuter-executor-state-v1",
                "runner_algorithm": _ALGORITHM_MAP[start_request.algorithm],
                "runner_seed": _stable_seed(start_request),
            }
            checkpoint_payload = {
                "protocol": "sotn-permuter-checkpoint-v1",
                "lane": start_request.lane,
                "phase": "start",
                "session_identity": start_request.session_identity,
                "request_identity": start_request.request_identity,
                "scratch_identity": start_request.scratch_identity,
                "iterations": 2,
                "candidates": [],
                "state": state,
                "stopped": True,
                "stop_reason": "operator_stop",
            }
            checkpoint_payload["checkpoint_identity"] = hash_canonical(checkpoint_payload)
            checkpoint = PermuterCheckpoint.from_dict(checkpoint_payload)
            store = PermuterHandoffStore(archive)
            checkpoint_artifact = store.put_checkpoint(checkpoint)
            self.assertEqual(checkpoint_artifact.content_hash, hash_canonical(checkpoint.to_dict()))
            resume_request = provider._request(item, "resume", checkpoint)
            self.assertEqual(executor._checkpoint_state(resume_request), state)
            seed_bytes, target_bytes = executor._verify_request(resume_request)
            runner_bytes, weights_bytes = executor._verify_binding()
            scratch, _vendor, runner_seed = executor._materialize(
                resume_request,
                seed_bytes,
                target_bytes,
                runner_bytes,
                weights_bytes,
                state,
            )
            before = frozenset(path.name for path in scratch.iterdir())
            output = scratch / "output-5-1"
            output.mkdir()
            (output / "source.c").write_text(
                "int func_permuter_executor_test(void) { return 5; }\n"
            )
            (output / "score.txt").write_text("5\n")
            resumed = executor._parse_output(
                resume_request,
                scratch,
                before,
                "iteration 1, 0 errors, score = 5\n",
                0,
                False,
                _ALGORITHM_MAP[resume_request.algorithm],
                runner_seed,
            )
            self.assertEqual(resumed["iterations"], 1)
            self.assertEqual(resumed["state"]["absolute_iterations"], 3)
            forged = dict(checkpoint.to_dict())
            forged["stop_reason"] = "forged"
            archive.resolve(checkpoint_artifact).unlink()
            archive.put_json(forged, category="permuter-checkpoints", suffix=".json")
            with self.assertRaises(PermuterExecutorInputError):
                executor._checkpoint_state(resume_request)

    def test_forged_vendor_revision_is_refused_before_runner_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, binding, _provider, request, _executor, _recipient = make_fixture(
                directory
            )
            forged_binding = replace(binding, vendor_revision=digest("forged vendor"))
            executor = PermuterExecutor(archive, forged_binding, timeout_seconds=10)
            with self.assertRaises(PermuterExecutorInputError):
                executor.preflight(request)

    def test_missing_archive_tool_is_reported_as_typed_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, binding, _provider, request, executor, _recipient = make_fixture(
                directory
            )
            archive.resolve(binding.tool_artifact).unlink()
            report = executor.preflight(request)
            self.assertEqual(report.status, "unavailable")
            self.assertEqual(report.refusal_code, "permuter_provider_unavailable")
            self.assertIn("absent or corrupt", report.reason)

    def test_request_config_identity_and_scratch_path_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, binding, _provider, request, _executor, _recipient = make_fixture(
                directory
            )
            class ForgedRequest:
                pass

            executor = PermuterExecutor(archive, binding, timeout_seconds=10)
            with self.assertRaises(PermuterExecutorInputError):
                executor._verify_request(ForgedRequest())
            payload = dict(request.identity_payload())
            payload["scratch_path"] = request.scratch_path + "/escape"
            idempotency_key = hash_canonical(payload)
            request_identity = hash_canonical(
                {
                    "protocol": "sotn-permuter-request-v1",
                    "idempotency_key": idempotency_key,
                    "payload": payload,
                }
            )
            forged = replace(
                request,
                scratch_path=payload["scratch_path"],
                idempotency_key=idempotency_key,
                request_identity=request_identity,
            )
            with self.assertRaises(PermuterExecutorInputError):
                executor._verify_request(forged)

    def test_windows_wsl_translation_uses_argv_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _archive, _manifest, _item, _binding, _provider, _request, executor, _recipient = make_fixture(
                directory
            )
            result = SimpleNamespace(returncode=0, stdout="/mnt/c/fixture\n")
            with (
                patch.object(executor_module.os, "name", "nt"),
                patch("automation.search_permuter_executor.shutil.which", return_value="wsl.exe"),
                patch("automation.search_permuter_executor.subprocess.run", return_value=result) as run,
            ):
                translated = executor._wsl_path(Path("C:/fixture/run"))
            self.assertEqual(translated, "/mnt/c/fixture")
            self.assertEqual(run.call_args.args[0][-1], "C:\\fixture\\run")
            self.assertFalse(run.call_args.kwargs["shell"])

if __name__ == "__main__":
    unittest.main()
