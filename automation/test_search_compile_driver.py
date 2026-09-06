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
