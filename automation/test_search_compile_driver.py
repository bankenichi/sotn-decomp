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

    def test_named_entity_layout_and_draft_compile_with_actual_us_headers(self):
        from automation.compiler_corpus import DEFAULT_CONFIG_PATH
        from automation.search_source_context import preprocess_target_context, renderer_declarations, target_declaration
        from automation.search_target_renderer import deterministic_local_draft
        source = b'#include "game.h"\nint fixture_member(Entity* self);\n'
        identity = pipeline_identity().identity
        context = preprocess_target_context(ROOT, source, ROOT / "src/st/no0", identity, DEFAULT_CONFIG_PATH)
        assembly = b"lh $v0, 2($a0)\nnop\njr $ra\nnop\n"
        facts, _ = target_declaration(context.decode(), "fixture_member")
        facts = renderer_declarations(facts, assembly, context)
        self.assertIn("Entity*", facts["pointer_layouts"])
        self.assertEqual(facts["pointer_layouts"]["Entity*"]["size"], 0xBC)
        members = facts["pointer_layouts"]["Entity*"]["members"]
        self.assertIn((".posX.i.hi", 2, 2), [(m["path"], m["offset"], m["width"]) for m in members])
        draft = deterministic_local_draft(assembly, symbol="fixture_member", declarations=facts)
        self.assertIsNotNone(draft)
        self.assertIn(".posX.i.hi", draft)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper, candidate, output = root / "compile.sh", root / "member.c", root / "member.o"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            # Compile-time assertions check both member offset and US pointer width.
            candidate.write_text(facts["type_declarations"] +
                'typedef char entity_size[(sizeof(Entity) == 0xBC) ? 1 : -1];\n'
                'typedef char pointer_width[(sizeof(Entity*) == 4) ? 1 : -1];\n'
                'typedef char member_offset[((unsigned int)&((Entity*)0)->posX.i.hi == 2) ? 1 : -1];\n' + draft)
            result = subprocess.run([str(wrapper), str(candidate), "-o", str(output)], env={
                **os.environ, "SOTN_REPO_ROOT": str(ROOT), "SOTN_COMPILER_IDENTITY": identity, "TMPDIR": directory,
            }, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows, count = _normalized_disassembly(output, symbol="fixture_member")
            self.assertGreater(count, 0)
            self.assertIn("lh", rows)

    def test_chained_entity_pointer_and_pointer_return_compile_from_us_archive(self):
        from automation.compiler_corpus import DEFAULT_CONFIG_PATH
        from automation.search_source_context import preprocess_target_context, renderer_declarations, target_declaration
        from automation.search_target_renderer import deterministic_local_draft
        source = b'#include "game.h"\nint parent_x(Entity* self);\nEntity* parent_pointer(Entity* self);\n'
        identity = pipeline_identity().identity
        context = preprocess_target_context(ROOT, source, ROOT / "src/st/no0", identity, DEFAULT_CONFIG_PATH)
        cases = {
            "parent_x": b"lw $t0, 92($a0)\nnop\nlh $v0, 2($t0)\nnop\njr $ra\nnop\n",
            "parent_pointer": b"lw $v0, 92($a0)\nnop\njr $ra\nnop\n",
        }
        drafts = []
        for symbol, assembly in cases.items():
            facts, status = target_declaration(context.decode(), symbol)
            self.assertEqual(status, "declared")
            facts = renderer_declarations(facts, assembly, context)
            parent = next(m for m in facts["pointer_layouts"]["Entity*"]["members"] if m["path"] == ".parent")
            self.assertEqual((parent["offset"], parent["width"], parent["pointer_type"]), (0x5C, 4, "struct Entity*"))
            draft = deterministic_local_draft(assembly, symbol=symbol, declarations=facts)
            self.assertIsNotNone(draft)
            self.assertIn(".parent", draft)
            drafts.append(draft)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper, candidate, output = root / "compile.sh", root / "parent.c", root / "parent.o"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            candidate.write_text(facts["type_declarations"] +
                'typedef char parent_offset[((unsigned int)&((Entity*)0)->parent == 0x5C) ? 1 : -1];\n' + "\n".join(drafts))
            result = subprocess.run([str(wrapper), str(candidate), "-o", str(output)], env={
                **os.environ, "SOTN_REPO_ROOT": str(ROOT), "SOTN_COMPILER_IDENTITY": identity, "TMPDIR": directory,
            }, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            for symbol in cases:
                rows, count = _normalized_disassembly(output, symbol=symbol)
                self.assertGreater(count, 0)
                self.assertIn("lw", rows)
                if symbol == "parent_x":
                    self.assertIn("lh", rows)

    def test_generated_direct_call_compiles_with_actual_psx_toolchain(self):
        from automation.search_target_renderer import deterministic_local_draft
        from automation.search_source_context import renderer_declarations
        assembly = b"addiu $sp, $sp, -24\nsw $ra, 20($sp)\nsw $s0, 16($sp)\nmove $s0, $a0\njal callee\naddiu $a0, $a0, 1\naddu $v0, $v0, $s0\nlw $ra, 20($sp)\nlw $s0, 16($sp)\njr $ra\naddiu $sp, $sp, 24\n"
        facts = renderer_declarations({"return_type": "int", "parameters": [{"type": "int", "name": "value"}]},
                                      assembly, b"int callee(int value);")
        draft = deterministic_local_draft(assembly, symbol="call_wrapper", declarations=facts)
        self.assertIsNotNone(draft)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper, source, output = root / "compile.sh", root / "caller.c", root / "caller.o"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            source.write_text(draft)
            result = subprocess.run([str(wrapper), str(source), "-o", str(output)], env={
                **os.environ, "SOTN_REPO_ROOT": str(ROOT),
                "SOTN_COMPILER_IDENTITY": pipeline_identity().identity, "TMPDIR": directory,
            }, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows, count = _normalized_disassembly(output, symbol="call_wrapper")
            self.assertGreater(count, 0)
            self.assertIn("jal", rows)

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
