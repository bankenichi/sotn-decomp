"""Real target compiler wrapper execution and refusal boundaries."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.compiler_corpus import ROOT, pipeline_identity, _normalized_disassembly
from automation.search_permuter_executor import REPOSITORY_COMPILE_WRAPPER_BYTES


class CompileDriverTests(unittest.TestCase):
    def test_real_us_preprocessor_captures_header_types_in_private_context(self):
        from automation.compiler_corpus import DEFAULT_CONFIG_PATH
        from automation.search_source_context import preprocess_target_context, target_declaration
        source = b'#include "common.h"\n#ifdef VERSION_PSP\n#error foreign target\n#endif\nint fixture_context(Entity* self) { return self->posX.i.hi; }\n'
        identity = pipeline_identity().identity
        context = preprocess_target_context(ROOT, source, ROOT / "src/st/no0", identity, DEFAULT_CONFIG_PATH)
        facts, status = target_declaration(context.decode(), "fixture_context")
        self.assertEqual(status, "declared")
        self.assertEqual(facts, {"return_type": "int", "parameters": [{"type": "Entity*", "name": "self"}]})
        self.assertNotIn(b'#include', context)

    def test_generated_leaf_branch_compiles_with_actual_psx_toolchain(self):
        from automation.search_target_renderer import deterministic_local_draft
        draft = deterministic_local_draft(
            "bltz $a0, .Lnegative\naddiu $v0, $a0, 1\njr $ra\nnop\n.Lnegative:\njr $ra\nsubu $v0, $zero, $v0\n",
            symbol="leaf_branch", declarations={"return_type": "int", "parameters": [{"type": "int", "name": "value"}]},
        )
        self.assertIsNotNone(draft)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper, source, output = root / "compile.sh", root / "leaf.c", root / "leaf.o"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            source.write_text(draft)
            result = subprocess.run([str(wrapper), str(source), "-o", str(output)], env={
                **os.environ, "SOTN_REPO_ROOT": str(ROOT),
                "SOTN_COMPILER_IDENTITY": pipeline_identity().identity, "TMPDIR": directory,
            }, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows, count = _normalized_disassembly(output, symbol="leaf_branch")
            self.assertGreater(count, 0)
            self.assertIn("jr", rows)

    def test_fixed_wrapper_compiles_psx_object_and_refuses_compiler_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper = root / "compile.sh"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            source, output = root / "candidate.c", root / "candidate.o"
            source.write_text("int f(int x) { return x + 1; }")
            environment = {
                **os.environ, "SOTN_REPO_ROOT": str(ROOT),
                "SOTN_COMPILER_IDENTITY": pipeline_identity().identity, "TMPDIR": directory,
            }
            result = subprocess.run(
                [str(wrapper), str(source), "-o", str(output)],
                env=environment, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows, count = _normalized_disassembly(output, symbol="f")
            self.assertGreater(count, 0)
            self.assertIn("v0", rows)
            before = output.read_bytes()
            environment["SOTN_COMPILER_IDENTITY"] = "sha256:" + "0" * 64
            refused = subprocess.run(
                [str(wrapper), str(source), "-o", str(output)],
                env=environment, capture_output=True, timeout=60,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"identity differs", refused.stderr)
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
