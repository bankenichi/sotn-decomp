from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.m2c_revision_executor import (
    M2C_EXECUTOR_PROTOCOL,
    M2C_TARGET_MAP,
    M2CExecutorInputError,
    M2CExecutorInvalidResponse,
    M2CExecutorInapplicable,
    M2CExecutorTimeout,
    M2CExecutionResult,
    M2CRevisionExecutor,
    build_m2c_revision_executor,
)
from automation.m2c_revision_matrix import M2CRevisionPin
from automation.m2c_revision_provider import (
    CURRENT_M2C_REVISION,
    M2CRevisionIdentity,
    make_invocation,
)
from automation.search_archive import ContentAddressedArchive
from automation.search_types import hash_bytes


def ident(label: str) -> str:
    return hash_bytes(("m2c-executor-test:" + label).encode("utf-8"))


RUNNER = b"""import sys
if '--help' in sys.argv:
    print('m2c decompiler help')
else:
    print('int generated(void) { return 1; }')
"""
ASSEMBLY = b"generated:\n  jr $ra\n  nop\n"
CONTEXT = b"typedef int s32;\n"


def make_fixture(directory: str, *, recipient: str = "us:ST:generated"):
    archive = ContentAddressedArchive(Path(directory) / "run")
    source = archive.put_bytes(
        b"pinned m2c revision source\n",
        category="m2c-revision-sources",
        suffix=".txt",
        media_type="text/plain",
    )
    tool = archive.put_bytes(
        RUNNER,
        category="m2c-revision-tools",
        suffix=".py",
        media_type="text/x-python",
    )
    revision = M2CRevisionIdentity(
        revision_id=CURRENT_M2C_REVISION,
        tree_identity=ident("tree"),
        provider_identity=ident("provider"),
        executable_identity=tool.content_hash,
        config_identity=ident("m2c-config"),
        clean=True,
        detached=True,
    )
    pin = M2CRevisionPin(
        revision=revision,
        source_artifact=source,
        tool_artifact=tool,
        runner_identity=tool.content_hash,
    )
    assembly = archive.put_bytes(
        ASSEMBLY,
        category="m2c-inputs",
        suffix=".s",
        media_type="text/x-asm",
    )
    context = archive.put_bytes(
        CONTEXT,
        category="m2c-inputs",
        suffix=".c",
        media_type="text/x-c",
    )
    archive_identity = ident("archive")
    subset_identity = ident("subset")
    invocation = make_invocation(
        revision_id=revision.revision_id,
        tree_identity=revision.tree_identity,
        provider_identity=revision.provider_identity,
        recipient_id=recipient,
        assembly_artifact=assembly,
        context_artifacts=(context,),
        switches=("--stack-structs",),
        target_identity=ident("target:" + recipient.split(":", 1)[0]),
        compiler_identity=ident("compiler"),
        tool_identity=revision.executable_identity,
        evaluator_identity=ident("evaluator"),
        scorer_taxonomy_identity=ident("scorer"),
        config_identity=revision.config_identity,
        integration_gate_id=ident("gate"),
        integration_gate_artifact_id=ident("gate-artifact"),
        subset_identity=subset_identity,
        queue_evidence_identity=ident("queue"),
        archive_identity=archive_identity,
        ordinal=0,
    )
    executor = build_m2c_revision_executor(
        archive,
        pin,
        archive_identity=archive_identity,
        manifest_identity=ident("manifest"),
        subset_identity=subset_identity,
        config_identity=revision.config_identity,
        tool_identity=revision.executable_identity,
        timeout_seconds=10,
    )
    return archive, pin, invocation, executor


class M2CRevisionExecutorTests(unittest.TestCase):
    def test_current_pin_preflight_runs_archive_bound_runner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _archive, pin, _invocation, executor = make_fixture(directory)
            report = executor.preflight()
            self.assertEqual(report.status, "ready")
            self.assertEqual(report.revision_id, CURRENT_M2C_REVISION)
            self.assertEqual(report.pin_identity, pin.pin_identity)
            self.assertEqual(report.target_map, dict(M2C_TARGET_MAP))
            self.assertEqual(report.platform, "native-posix")

    def test_native_argv_is_fixed_shell_free_and_request_is_durable_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _pin, invocation, executor = make_fixture(directory)
            seen = {}

            class FakeProcess:
                pid = 4242
                returncode = 0

                def communicate(self, timeout=None):
                    seen["request_files"] = sorted(
                        p.name for p in (archive.run_root / "artifacts" / "m2c-executor-requests").glob("*.json")
                    )
                    seen["timeout"] = timeout
                    return b"int generated(void) { return 1; }\n", b""

                def terminate(self):
                    seen["terminated"] = True

                def kill(self):
                    seen["killed"] = True

                def wait(self, timeout=None):
                    return 0

            with patch("automation.m2c_revision_executor.subprocess.Popen", return_value=FakeProcess()) as popen:
                result = executor.execute(invocation, assembly=ASSEMBLY, contexts=(CONTEXT,))
            self.assertIsInstance(result, M2CExecutionResult)
            self.assertEqual(result.status, "success")
            self.assertTrue(seen["request_files"])
            argv = popen.call_args.args[0]
            self.assertEqual(argv[0], sys.executable)
            self.assertIn("--no-cache", argv)
            self.assertIn("--target", argv)
            self.assertEqual(argv[argv.index("--target") + 1], "mips-ido-c")
            self.assertIn("--context", argv)
            self.assertIn("--stack-structs", argv)
            self.assertFalse(popen.call_args.kwargs["shell"])
            self.assertEqual(seen["timeout"], 10)

    def test_windows_wsl_argv_uses_safe_wsl_hop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _archive, _pin, invocation, executor = make_fixture(directory)
            seen = {}

            class FakeProcess:
                pid = 4243
                returncode = 0

                def communicate(self, timeout=None):
                    return b"int generated(void) { return 1; }\n", b""

                def terminate(self):
                    pass

                def kill(self):
                    pass

                def wait(self, timeout=None):
                    return 0

            def fake_run(argv, **kwargs):
                seen.setdefault("translations", []).append(argv)
                return type("Completed", (), {"returncode": 0, "stdout": "/mnt/c/safe", "stderr": ""})()

            with patch("automation.m2c_revision_executor.os.name", "nt"), patch(
                "automation.m2c_revision_executor.shutil.which", return_value="wsl.exe"
            ), patch("automation.m2c_revision_executor.subprocess.run", side_effect=fake_run), patch(
                "automation.m2c_revision_executor.subprocess.Popen", return_value=FakeProcess()
            ) as popen:
                result = executor.execute(invocation, assembly=ASSEMBLY, contexts=(CONTEXT,))
            self.assertEqual(result.status, "success")
            argv = popen.call_args.args[0]
            self.assertEqual(argv[:6], ["wsl.exe", "--cd", "/mnt/c/safe", "--exec", "python3", "-B"])
            self.assertIn("-u", argv)
            self.assertIn("--target", argv)
            self.assertEqual(argv[argv.index("--target") + 1], "mips-ido-c")
            self.assertFalse(popen.call_args.kwargs["shell"])
            self.assertTrue(seen["translations"])

    def test_round_trip_rechecks_artifacts_without_archive_writes_or_runner_calls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _pin, _invocation, executor = make_fixture(directory)
            serialized = executor.to_dict()
            with patch.object(archive, "put_bytes", side_effect=AssertionError("reconstruction wrote bytes")), patch.object(
                archive, "put_json", side_effect=AssertionError("reconstruction wrote json")
            ), patch("automation.m2c_revision_executor.subprocess.Popen", side_effect=AssertionError("reconstruction ran m2c")):
                rebuilt = M2CRevisionExecutor.from_dict(serialized, archive=archive)
            self.assertEqual(rebuilt.to_dict(), serialized)
            self.assertEqual(serialized["protocol"], M2C_EXECUTOR_PROTOCOL)

    def test_corrupt_and_forged_state_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, pin, _invocation, executor = make_fixture(directory)
            serialized = executor.to_dict()
            forged = json.loads(json.dumps(serialized))
            forged["unexpected"] = True
            with self.assertRaises(M2CExecutorInputError):
                M2CRevisionExecutor.from_dict(forged, archive=archive)
            forged = json.loads(json.dumps(serialized))
            forged["pin"]["tool_artifact"]["path"] = "checkout/m2c.py"
            with self.assertRaises(M2CExecutorInputError):
                M2CRevisionExecutor.from_dict(forged, archive=archive)
            archive.resolve(pin.tool_artifact).write_bytes(b"forged tool")
            with self.assertRaises(M2CExecutorInputError):
                M2CRevisionExecutor.from_dict(serialized, archive=archive)

    def test_saturn_is_typed_inapplicable_without_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _pin, _invocation, executor = make_fixture(directory, recipient="saturn:ST:generated")
            invocation = make_fixture(directory, recipient="saturn:ST:generated")[2]
            with patch("automation.m2c_revision_executor.subprocess.Popen", side_effect=AssertionError("SH is unavailable")):
                result = executor.execute(invocation, assembly=ASSEMBLY, contexts=(CONTEXT,))
            self.assertEqual(result.status, "inapplicable")
            self.assertEqual(result.reason_code, "m2c_target_inapplicable")
            with self.assertRaises(M2CExecutorInapplicable):
                executor.generate_draft(invocation, assembly=ASSEMBLY, contexts=(CONTEXT,))

    def test_timeout_and_output_bounds_are_typed_and_durable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive, _pin, invocation, executor = make_fixture(directory)

            class TimeoutProcess:
                pid = 4244
                returncode = None

                def communicate(self, timeout=None):
                    raise __import__("subprocess").TimeoutExpired(["m2c"], timeout)

                def terminate(self):
                    pass

                def kill(self):
                    pass

                def wait(self, timeout=None):
                    return -9

            with patch("automation.m2c_revision_executor.subprocess.Popen", return_value=TimeoutProcess()):
                result = executor.execute(invocation, assembly=ASSEMBLY, contexts=(CONTEXT,))
            self.assertEqual(result.status, "timeout")
            with self.assertRaises(M2CExecutorTimeout):
                executor.generate_draft(invocation, assembly=ASSEMBLY, contexts=(CONTEXT,))

        with tempfile.TemporaryDirectory() as directory:
            archive, _pin, invocation, executor = make_fixture(directory)

            class OutputProcess:
                pid = 4245
                returncode = 0

                def communicate(self, timeout=None):
                    return b"too much output", b""

                def terminate(self):
                    pass

                def kill(self):
                    pass

                def wait(self, timeout=None):
                    return 0

            bounded = build_m2c_revision_executor(
                archive,
                _pin,
                archive_identity=executor.archive_identity,
                manifest_identity=executor.manifest_identity,
                subset_identity=executor.subset_identity,
                config_identity=executor.config_identity,
                tool_identity=executor.tool_identity,
                timeout_seconds=10,
                max_output_bytes=4,
            )
            with patch("automation.m2c_revision_executor.subprocess.Popen", return_value=OutputProcess()):
                result = bounded.execute(invocation, assembly=ASSEMBLY, contexts=(CONTEXT,))
            self.assertEqual(result.status, "invalid")
            with self.assertRaises(M2CExecutorInvalidResponse):
                bounded.generate_draft(invocation, assembly=ASSEMBLY, contexts=(CONTEXT,))


if __name__ == "__main__":
    unittest.main()
