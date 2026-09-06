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
    REPOSITORY_COMPILE_WRAPPER_BYTES,
    _ALGORITHM_MAP,
    _stable_seed,
    build_permuter_executor,
    vendored_runner_identity,
    vendored_tree_identity,
)
from automation.search_types import (
    ArtifactRef,
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
        compiler_identity=config.evaluator_identity,
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
    script = REPOSITORY_COMPILE_WRAPPER_BYTES
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
    seed: str | None = None,
):
    lane = PERMUTER_RANDOM_LANE
    archive = ContentAddressedArchive(directory)
    typed_manifest = make_manifest(lane, config=config)
    item = make_input(archive, typed_manifest, **({"seed": seed} if seed is not None else {}))
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

    def test_real_executor_compiles_and_archives_actual_target_scores(self):
        from automation.compiler_corpus import _pipeline, _compile_source, DEFAULT_CONFIG_PATH
        from automation.search_permuter_worker import load_events
        with tempfile.TemporaryDirectory() as directory:
            pipeline = _pipeline(config_path=DEFAULT_CONFIG_PATH)
            config = PermuterLaneConfig(
                lane=PERMUTER_RANDOM_LANE, algorithm="random",
                evaluator_identity=pipeline.identity.identity,
                max_iterations=12, checkpoint_interval=1,
            )
            archive, typed_manifest, item, _, provider, request, executor, recipient = make_fixture(
                directory, config=config, runtime=True,
                seed='#include "stage.h"\nint func_permuter_executor_test(int x) { int y = x + 1; if (y > 3) y = y * 2; return y; }\n',
            )
            executor.timeout_seconds = 45
            with tempfile.TemporaryDirectory() as compile_dir:
                obj = _compile_source(
                    "int func_permuter_executor_test(void) { return 2; }",
                    pipeline, Path(compile_dir), name="target",
                )[0].read_bytes()
            executor.runtime = replace(
                executor.runtime, target_object_artifact=archive.put_object(obj),
                target_object_bytes=obj, compiler_type="gcc",
            )
            response = executor(request)
            # Simulate launcher loss after the worker persisted its evaluations
            # but before the provider could publish the response/result chain.
            PermuterHandoffStore(archive).put_request(request)
            provider.executor_callback = executor
            recovered = provider.run(recipient)
            self.assertNotEqual(recovered.status, "handoff_pending")
            events = load_events(archive, request.session_identity)
            self.assertGreater(len(events), 0)
            self.assertEqual(response["iterations"], len(events))
            for reference, event in events:
                self.assertEqual(event["score"]["compiler_identity"], pipeline.identity.identity)
                self.assertIsNotNone(event["object"])
                self.assertEqual(event["strategy"], "random")
                if event["provenance"].get("kind") == "seed_baseline":
                    self.assertEqual(archive.verify(ArtifactRef.from_dict(event["source"])).decode(), item.seed_source)
                else:
                    self.assertEqual(event["provenance"]["mutation"]["after_source"],
                                     archive.verify(ArtifactRef.from_dict(event["source"])).decode())
            self.assertEqual(response["candidates"][0]["provenance"]["evaluation_artifact"],
                             events[0][0].to_dict())
            from automation.search_permuter_lanes import _normalize_response, _checkpoint_for
            typed_response = _normalize_response(response, request)
            checkpoint = _checkpoint_for(request, typed_response, typed_response.candidates)
            PermuterHandoffStore(archive).put_checkpoint(checkpoint)
            resume = provider._request(item, "resume", checkpoint)
            resumed = executor(resume)
            all_events = load_events(archive, request.session_identity)
            self.assertEqual(all_events[:len(events)], events)
            self.assertGreater(len(all_events), len(events))
            self.assertEqual(resumed["iterations"], len(all_events) - len(events))
            self.assertTrue(any(event["source"]["byte_size"] > 65536 for _, event in all_events))
            # A later process failure must preserve this exact measured prefix.
            failed = executor._parse_output(
                request, archive.run_root, frozenset(), output="worker failed after evaluation",
                returncode=1, controlled_stop=False, runner_algorithm="random", runner_seed=17,
            )
            self.assertEqual(failed["status"], "refused")
            self.assertEqual(failed["iterations"], len(all_events))
            self.assertEqual(failed["state"]["evaluation_artifacts"], [ref.to_dict() for ref, _ in all_events])
            # Re-entering the same completed phase reads durable scores. A
            # compiler failure here would prove unwanted recompilation.
            from automation import search_permuter_worker as worker
            phase = archive.run_root / resume.scratch_path / ("resume-" + resume.request_identity[7:23])
            with patch.object(worker, "compile_against_object", side_effect=AssertionError("recompiled")):
                replay = worker.run(phase, archive.run_root)
            self.assertEqual(replay["absolute_iterations"], len(all_events))
            from automation.search_evaluator import permuter_measurements
            measurements = permuter_measurements(typed_manifest, archive)
            self.assertEqual(len(measurements[(recipient.recipient_id, request.lane)]), len(all_events))

    def test_invalid_seed_is_measured_before_mutation_and_reaches_failure_receipt(self):
        from automation.compiler_corpus import _pipeline, _compile_source
        from automation.search_evaluator import permuter_measurements
        from automation.search_lanes import run_lane
        pipeline = _pipeline()
        config = PermuterLaneConfig(
            lane=PERMUTER_RANDOM_LANE, algorithm="random",
            evaluator_identity=pipeline.identity.identity, max_iterations=8,
        )
        with tempfile.TemporaryDirectory() as directory:
            archive, typed_manifest, _, _, provider, _, executor, recipient = make_fixture(
                directory, config=config, runtime=True,
                seed="int func_permuter_executor_test(void) { return MISSING_SEED_CONSTANT; }\n",
            )
            with tempfile.TemporaryDirectory() as scratch:
                target = _compile_source(
                    "int func_permuter_executor_test(void) { return 2; }", pipeline,
                    Path(scratch), name="target",
                )[0].read_bytes()
            executor.runtime = replace(executor.runtime,
                target_object_artifact=archive.put_object(target), target_object_bytes=target)
            provider.executor_callback = executor
            result = provider.run(recipient)
            self.assertEqual(result.status, "refused")
            self.assertEqual(result.refusal_code, "seed_compile_failed", result.reason)
            self.assertEqual(result.iterations, 1)
            measured = permuter_measurements(typed_manifest, archive)[(recipient.recipient_id, config.lane)]
            self.assertEqual(len(measured), 1)
            self.assertEqual(next(iter(measured.values()))[0].compile_status, "failed")
            outcome = run_lane(typed_manifest, config.lane, [recipient],
                               adapters={config.lane: provider}).outcomes[0]
            self.assertFalse(outcome.inapplicable)
            self.assertEqual(outcome.receipt.completion_reason, "execution_failed")
            self.assertEqual(outcome.receipt.rejection_counts["seed_compile_failed"], 1)


    def test_runtime_accepts_binary_object_bytes_with_nuls(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory))
            original = make_runtime(archive, digest("evaluator"))
            target = bytes.fromhex("7f454c4601000000")
            runtime = replace(
                original, target_object_artifact=archive.put_object(target), target_object_bytes=target,
            )
            runtime.verify(archive)
            self.assertEqual(runtime.target_object_bytes, target)



    def test_complete_executor_parses_process_result_in_declared_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _archive, _manifest, _item, _binding, _provider, request, executor, _recipient = make_fixture(
                directory, runtime=True
            )
            # The tuple contract is independent of the structured event format.
            with (
                patch.object(executor, "_run_process", return_value=(0, "process output", False)),
                patch.object(executor, "_parse_output", return_value={"verified": True}) as parse,
            ):
                response = executor(request)
            self.assertEqual(response, {"verified": True})
            self.assertEqual(parse.call_args.kwargs["output"], "process output")
            self.assertEqual(parse.call_args.kwargs["returncode"], 0)
            self.assertIs(parse.call_args.kwargs["controlled_stop"], False)

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

    def test_compiler_invocation_is_structured_and_rejects_caller_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, _binding, _provider, _request, executor, _recipient = make_fixture(
                directory, runtime=True
            )
            runtime = executor.runtime
            serialized = runtime.to_dict()
            self.assertEqual(serialized["compiler_executable"], "python3")
            self.assertEqual(serialized["compiler_argv_template"], ["{input}", "-o", "{output}"])
            self.assertEqual(serialized["input_location"], "argv[0]")
            self.assertEqual(serialized["output_location"], "argv[2]")
            for field, changed in (
                ("compiler_executable", "/usr/bin/python3"),
                ("compiler_argv_template", ["{output}", "-o", "{input}"]),
                ("compiler_environment", {"PATH": "/tmp"}),
                ("wrapper_identity", digest("caller wrapper")),
            ):
                with self.subTest(field=field):
                    forged = dict(serialized)
                    forged[field] = changed
                    with self.assertRaises(PermuterExecutorInputError):
                        PermuterRuntimeBinding.from_dict(forged, archive=archive)

            for script in (
                b'#!/bin/sh\nexec /usr/bin/python3 -c "import os; os.remove(\'victim\')" "$@"\n',
                b'#!/bin/sh\necho changed > /tmp/permuter-owned\nexec cc "$@"\n',
            ):
                with self.subTest(script=script):
                    artifact = archive.put_bytes(
                        script,
                        category="permuter-runtime",
                        suffix=".sh",
                        media_type="text/x-shellscript",
                    )
                    with self.assertRaises(PermuterExecutorInputError):
                        replace(
                            runtime,
                            compile_script_artifact=artifact,
                            compile_script_bytes=script,
                        )

    def test_executor_timeout_and_checkpoint_booleans_are_identity_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _manifest, _item, binding, _provider, request, executor, _recipient = make_fixture(
                directory, runtime=True
            )
            changed_timeout = PermuterExecutor(
                archive,
                binding,
                runtime=executor.runtime,
                timeout_seconds=11,
            )
            self.assertNotEqual(executor.identity, changed_timeout.identity)
            forged = executor.to_dict()
            forged["timeout_seconds"] = 11
            with self.assertRaises(PermuterExecutorInputError):
                PermuterExecutor.from_dict(forged, archive=archive)

            state = {
                "protocol": "sotn-permuter-checkpoint-v1",
                "lane": request.lane,
                "phase": "start",
                "session_identity": request.session_identity,
                "request_identity": request.request_identity,
                "scratch_identity": request.scratch_identity,
                "iterations": 0,
                "candidates": [],
                "state": {},
                "stopped": "false",
                "stop_reason": "",
                "checkpoint_identity": digest("forged checkpoint"),
            }
            with self.assertRaises(Exception):
                PermuterCheckpoint.from_dict(state)

    def test_windows_termination_targets_wsl_descendant_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _archive, _manifest, _item, _binding, _provider, _request, executor, _recipient = make_fixture(
                directory
            )
            process = SimpleNamespace(pid=2718, wait=lambda timeout: None)
            result = SimpleNamespace(returncode=0, stdout="", stderr="")
            with (
                patch.object(executor_module.os, "name", "nt"),
                patch("automation.search_permuter_executor.subprocess.run", return_value=result) as run,
            ):
                executor._terminate(process)
            self.assertEqual(run.call_args.args[0], ["taskkill.exe", "/PID", "2718", "/T", "/F"])
            self.assertFalse(run.call_args.kwargs["shell"])

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
            self.assertEqual(scratch.parent.parent, archive.run_root / "permuter-scratch" / request.lane)
            self.assertTrue(scratch.name.startswith("start-"))
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
            # Legacy directory labels cannot supply measured chronology.
            with self.assertRaisesRegex(PermuterExecutorInvalidResponse, "structured terminal"):
                executor._parse_output(
                    request, scratch, before, "iteration 1, 0 errors, score = 7\\n",
                    0, False, _ALGORITHM_MAP[request.algorithm], seed,
                )

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
            with self.assertRaisesRegex(PermuterExecutorInvalidResponse, "structured terminal"):
                executor._parse_output(
                    resume_request, scratch, before, "iteration 1, 0 errors, score = 5",
                    0, False, _ALGORITHM_MAP[resume_request.algorithm], runner_seed,
                )
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
