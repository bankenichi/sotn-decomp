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
    def test_loop_calls_compile_with_actual_psx_toolchain(self):
        from automation.search_target_renderer import deterministic_local_draft
        from automation.search_source_context import renderer_declarations
        from automation.test_search_target_renderer import LoopLoweringTests
        drafts = []
        for name, call, context in (
            ("loop_direct", "jal callee\n", b"unsigned int callee(unsigned int n);\n"),
            ("loop_api", "lui $v0, %hi(g_api_Test)\nlw $v0, %lo(g_api_Test)($v0)\nnop\njalr $v0\n",
             b"unsigned int (*g_api_Test)(unsigned int n);\n"),
        ):
            assembly = (LoopLoweringTests.CALL_PREFIX + ".Ltop:\n" + call +
                        "move $a0, $s0\naddu $s1, $s1, $v0\naddiu $s0, $s0, -1\n"
                        "bnez $s0, .Ltop\nnop\n" + LoopLoweringTests.CALL_SUFFIX)
            facts = renderer_declarations(LoopLoweringTests.COUNTER_DECLS, assembly.encode(), context)
            draft = deterministic_local_draft(assembly, symbol=name, declarations=facts)
            self.assertIsNotNone(draft)
            drafts.append(draft)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper, source, output = root / "compile.sh", root / "loops.c", root / "loops.o"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            source.write_text("\n".join(drafts))
            result = subprocess.run([str(wrapper), str(source), "-o", str(output)], env={
                **os.environ, "SOTN_REPO_ROOT": str(ROOT),
                "SOTN_COMPILER_IDENTITY": pipeline_identity().identity, "TMPDIR": directory,
            }, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b"")
            for symbol, opcode in (("loop_direct", "jal"), ("loop_api", "jalr")):
                rows, count = _normalized_disassembly(output, symbol=symbol)
                self.assertGreater(count, 0)
                self.assertIn(opcode, rows)

    def test_target_pointer_declaration_exact_and_refusals(self):
        from automation.search_source_context import target_pointer_declaration
        text = ("extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);\n"
                "static int ignored(int x) { return x; }\n")
        facts, status = target_pointer_declaration(text, "g_api_AllocPrimitives")
        self.assertEqual(status, "declared")
        self.assertEqual(facts, {"return_type": "s16", "parameters": [
            {"type": "PrimitiveType", "name": "type"},
            {"type": "s32", "name": "count"}]})
        self.assertEqual(target_pointer_declaration(text, "g_api_Missing"),
                         ({}, "declaration_missing"))
        self.assertEqual(target_pointer_declaration(
            "extern void (*f)(void);\nextern s32 (*f)(void);\n", "f")[1],
            "ambiguous_declaration")
        # A data pointer is not a callable API surface.
        self.assertEqual(target_pointer_declaration(
            "extern s16 *g_api_Data;\n", "g_api_Data")[1],
            "unsupported_declaration")
        # A function returning a pointer is not a supported ABI shape.
        self.assertEqual(target_pointer_declaration(
            "extern int *(*f)(int x);\n", "f")[1],
            "unsupported_declaration")
        # Local scopes never supply API facts.
        self.assertEqual(target_pointer_declaration(
            "void g(void) { extern int (*f)(int x); }\n", "f")[1],
            "declaration_missing")
        # A plain function is not a pointer declarator.
        self.assertEqual(target_pointer_declaration(
            "extern s16 callee(s32 x);\n", "callee")[1],
            "declaration_missing")
        self.assertEqual(target_pointer_declaration(text, "not an identifier")[1],
                         "declaration_missing")
        unnamed, status = target_pointer_declaration(
            "extern void (*g_api_FreePrimitives)(s32);\n", "g_api_FreePrimitives")
        self.assertEqual(status, "declared")
        self.assertEqual(unnamed["parameters"], [{"type": "s32", "name": "arg0"}])
        multi, status = target_pointer_declaration(
            "extern s16 (*g_api_func)(s32, s32);\n", "g_api_func")
        self.assertEqual(status, "declared")
        self.assertEqual([p["name"] for p in multi["parameters"]], ["arg0", "arg1"])
        # Synthesized names never collide silently; collisions refuse.
        self.assertEqual(target_pointer_declaration(
            "extern void (*g_api_Collide)(s32 arg1, s32);\n", "g_api_Collide")[1],
            "unsupported_declaration")

    def test_target_declaration_unnamed_parameters(self):
        from automation.search_source_context import target_declaration
        facts, status = target_declaration("void DestroyEntity(Entity*);\n", "DestroyEntity")
        self.assertEqual(status, "declared")
        self.assertEqual(facts["parameters"], [{"type": "Entity*", "name": "arg0"}])
        multi, status = target_declaration("int f(int, unsigned int);\n", "f")
        self.assertEqual(status, "declared")
        self.assertEqual([p["name"] for p in multi["parameters"]], ["arg0", "arg1"])
        # Named behavior is unchanged.
        named, status = target_declaration("int f(int x);\n", "f")
        self.assertEqual(status, "declared")
        self.assertEqual(named["parameters"], [{"type": "int", "name": "x"}])
        # Collisions, varargs and empty lists still refuse.
        self.assertEqual(target_declaration("void f(s32 arg1, s32);\n", "f")[1],
                         "unsupported_declaration")
        self.assertEqual(target_declaration("void f(int, ...);\n", "f")[1],
                         "unsupported_declaration")
        self.assertEqual(target_declaration("void f();\n", "f")[1],
                         "unsupported_declaration")
    def test_target_data_declaration_exact_and_refusals(self):
        from automation.search_source_context import target_data_declaration
        facts, status = target_data_declaration("extern s16 D_us_1[4];\n", "D_us_1")
        self.assertEqual(status, "declared")
        self.assertEqual(facts, {"type": "s16", "dims": "[4]", "static": False})
        definition, status = target_data_declaration(
            "EInit D_us_2 = {1, 2};\n", "D_us_2")
        self.assertEqual(status, "declared")
        self.assertEqual(definition, {"type": "EInit", "dims": "", "static": False})
        static, status = target_data_declaration("static u16 D_us_3[];\n", "D_us_3")
        self.assertEqual(status, "declared")
        self.assertTrue(static["static"])
        pointer, status = target_data_declaration("extern s16 *D_us_4;\n", "D_us_4")
        self.assertEqual(status, "declared")
        self.assertEqual(pointer["type"], "s16*")
        self.assertEqual(target_data_declaration("extern s16 D_us_5[x];\n", "D_us_5")[1],
                         "unsupported_declaration")
        self.assertEqual(target_data_declaration(
            "extern s16 D_us_6;\nextern s32 D_us_6;\n", "D_us_6")[1],
            "ambiguous_declaration")
        self.assertEqual(target_data_declaration("int D_us_7;\n", "D_us_8")[1],
                         "declaration_missing")
        self.assertEqual(target_data_declaration(
            "void g(void) { extern s16 D_us_9[4]; }\n", "D_us_9")[1],
            "declaration_missing")

    def test_data_member_projection_exact_and_refusals(self):
        from automation.search_source_context import _data_member_names, renderer_declarations
        assembly = (b"lui $a0, %hi(D_us_1)\naddiu $a0, $a0, %lo(D_us_1)\n"
                    b"jalr $v0\nnop\njr $ra\nnop\n")
        self.assertEqual(_data_member_names(assembly.decode()), ["D_us_1"])
        self.assertEqual(_data_member_names("lui $v0, %hi(g_Other)\nnop\n"), [])
        context = b"typedef signed short s16;\nextern s16 D_us_1[4];\n"
        facts = renderer_declarations({"return_type": "void", "parameters": []},
                                      assembly, context)
        self.assertEqual(facts["data_declarations"]["D_us_1"]["status"], "declared")
        self.assertEqual(facts["data_declarations"]["D_us_1"]["type"], "s16")
        self.assertIn("s16*", facts["pointer_layouts"])
        sibling = renderer_declarations({"return_type": "void", "parameters": []},
                                        assembly, b"int x;\n", [b"extern s16 D_us_1[4];\n"])
        self.assertEqual(sibling["data_declarations"]["D_us_1"]["status"], "declared")
        static_sibling = renderer_declarations(
            {"return_type": "void", "parameters": []}, assembly, b"int x;\n",
            [b"static s16 D_us_1[4];\n"])
        self.assertEqual(static_sibling["data_declarations"]["D_us_1"]["status"],
                         "unsupported_declaration")
        missing = renderer_declarations({"return_type": "void", "parameters": []},
                                        assembly, b"int x;\n")
        self.assertEqual(missing["data_declarations"]["D_us_1"]["status"],
                         "declaration_missing")
    def test_global_member_projection_exact_and_refusals(self):
        from automation.search_source_context import _global_member_names, renderer_declarations
        assembly = (b"lui $a1, %hi(g_Entities)\naddiu $a1, $a1, %lo(g_Entities)\n"
                    b"jr $ra\nnop\n")
        self.assertEqual(_global_member_names(assembly.decode()), ["g_Entities"])
        self.assertEqual(_global_member_names("lui $v0, %hi(g_api_Test)\naddiu $v0, $v0, %lo(g_api_Test)\n"), [])
        self.assertEqual(_global_member_names("lui $v0, %hi(g_OnlyHi)\nnop\n"), [])
        self.assertEqual(_global_member_names(""), [])
        context = b"typedef struct { int x; } Entity;\nextern Entity g_Entities[256];\n"
        facts = renderer_declarations({"return_type": "void", "parameters": []},
                                      assembly, context)
        self.assertEqual(facts["global_declarations"]["g_Entities"]["status"], "declared")
        self.assertEqual(facts["global_declarations"]["g_Entities"]["type"], "Entity")
        self.assertIn("Entity*", facts["pointer_layouts"])
        missing = renderer_declarations({"return_type": "void", "parameters": []},
                                        assembly, b"int x;\n")
        self.assertEqual(missing["global_declarations"]["g_Entities"]["status"],
                         "declaration_missing")
    def test_linker_member_names_and_projection(self):
        from automation.search_source_context import _global_member_names, _linker_member_names, renderer_declarations
        self.assertEqual(_linker_member_names("lui $v0, %hi(PLAYER_posX_i_hi)\naddiu $v0, $v0, %lo(PLAYER_posX_i_hi)\n"), ["PLAYER_posX_i_hi"])
        self.assertEqual(_linker_member_names("lui $v0, %hi(g_Other)\naddiu $v0, $v0, %lo(g_Other)\n"), [])
        self.assertEqual(_linker_member_names("lui $v0, %hi(g_api_Test)\naddiu $v0, $v0, %lo(g_api_Test)\n"), [])
        self.assertEqual(_global_member_names("lui $v0, %hi(g_Flags + 0x20)\naddiu $v0, $v0, %lo(g_Flags + 0x20)\n"), ["g_Flags"])
        assembly = b"lui $v0, %hi(RIC_step)\nlhu $v0, %lo(RIC_step)($v0)\njr $ra\nnop\n"
        context = b"extern unsigned short RIC_step;\n"
        facts = renderer_declarations({"return_type": "void", "parameters": []}, assembly, context)
        self.assertEqual(facts["linker_declarations"]["RIC_step"]["status"], "declared")
        missing = renderer_declarations({"return_type": "void", "parameters": []}, assembly, b"int x;\n")
        self.assertEqual(missing["linker_declarations"]["RIC_step"]["status"], "declaration_missing")
    def test_sibling_global_linker_callee_fallback_and_consensus(self):
        from automation.search_source_context import renderer_declarations
        g_asm = (b"lui $a1, %hi(g_Things)\naddiu $a1, $a1, %lo(g_Things)\n"
                 b"jr $ra\nnop\n")
        ctx = b"typedef struct { int x; } Thing;\n"
        sib = b"extern Thing g_Things[8];\n"
        facts = renderer_declarations({"return_type": "void", "parameters": []},
                                      g_asm, ctx, [sib])
        self.assertEqual(facts["global_declarations"]["g_Things"]["status"], "declared")
        self.assertEqual(facts["global_declarations"]["g_Things"]["type"], "Thing")
        bad = renderer_declarations({"return_type": "void", "parameters": []}, g_asm, ctx,
                                    [sib, b"extern int g_Things;\n"])
        self.assertEqual(bad["global_declarations"]["g_Things"]["status"],
                         "ambiguous_declaration")
        static = renderer_declarations({"return_type": "void", "parameters": []}, g_asm, ctx,
                                       [b"static Thing g_Things[8];\n"])
        self.assertEqual(static["global_declarations"]["g_Things"]["status"],
                         "unsupported_declaration")
        l_asm = (b"lui $v0, %hi(RIC_step)\nlhu $v0, %lo(RIC_step)($v0)\n"
                 b"jr $ra\nnop\n")
        l_facts = renderer_declarations({"return_type": "void", "parameters": []}, l_asm,
                                        b"int x;\n", [b"extern unsigned short RIC_step;\n"])
        self.assertEqual(l_facts["linker_declarations"]["RIC_step"]["status"], "declared")
        c_asm = b"jal helper\nnop\njr $ra\nnop\n"
        c_facts = renderer_declarations({"return_type": "void", "parameters": []}, c_asm,
                                        b"int x;\n", [b"int helper(int v);\n"])
        self.assertEqual(c_facts["call_declarations"]["helper"]["status"], "declared")
        self.assertEqual(c_facts["call_declarations"]["helper"]["parameters"],
                         [{"type": "int", "name": "v"}])

    def test_header_global_callee_fallback_and_poison(self):
        from automation.search_source_context import renderer_declarations
        g_asm = (b"lui $a1, %hi(g_Things)\naddiu $a1, $a1, %lo(g_Things)\n"
                 b"jr $ra\nnop\n")
        ctx = b"typedef struct { int x; } Thing;\n"
        facts = renderer_declarations({"return_type": "void", "parameters": []},
                                      g_asm, ctx, [], [b"extern Thing g_Things[8];\n"])
        self.assertEqual(facts["global_declarations"]["g_Things"]["status"], "declared")
        split = renderer_declarations({"return_type": "void", "parameters": []}, g_asm, ctx,
                                      [b"extern int g_Things;\n"],
                                      [b"extern Thing g_Things[8];\n"])
        self.assertEqual(split["global_declarations"]["g_Things"]["status"],
                         "ambiguous_declaration")
        static = renderer_declarations({"return_type": "void", "parameters": []}, g_asm, ctx,
                                       [], [b"static Thing g_Things[8];\n"])
        self.assertEqual(static["global_declarations"]["g_Things"]["status"],
                         "unsupported_declaration")
        c_asm = b"jal helper\nnop\njr $ra\nnop\n"
        c_facts = renderer_declarations({"return_type": "void", "parameters": []}, c_asm,
                                        b"int x;\n", [], [b"void helper(int);\n"])
        self.assertEqual(c_facts["call_declarations"]["helper"]["status"], "declared")

    def test_api_member_projection_exact_and_refusals(self):
        from automation.search_source_context import _api_member_names, renderer_declarations
        assembly = (b"lui $v0, %hi(g_api_AllocPrimitives)\n"
                    b"lw $v0, %lo(g_api_AllocPrimitives)($v0)\n"
                    b"nop\njalr $v0\nnop\njr $ra\nnop\n")
        self.assertEqual(_api_member_names(assembly.decode()), ["g_api_AllocPrimitives"])
        self.assertEqual(_api_member_names("lui $v0, %hi(g_api_OnlyHi)\nnop\n"), [])
        self.assertEqual(_api_member_names("lw $v0, %lo(g_api_OnlyLo)($v0)\nnop\n"), [])
        self.assertEqual(_api_member_names(""), [])
        context = (b"typedef unsigned int u32;\n"
                   b"extern short (*g_api_AllocPrimitives)(int type, s32 count);\n")
        facts = renderer_declarations({"return_type": "int", "parameters": []},
                                      assembly, context)
        self.assertEqual(facts["api_declarations"]["g_api_AllocPrimitives"]["status"],
                         "declared")
        self.assertEqual(
            facts["api_declarations"]["g_api_AllocPrimitives"]["parameters"],
            [{"type": "int", "name": "type"}, {"type": "s32", "name": "count"}])
        self.assertNotIn("call_declarations", facts)
        missing = renderer_declarations(
            {"return_type": "int", "parameters": []}, assembly, b"int x;\n")
        self.assertEqual(missing["api_declarations"]["g_api_AllocPrimitives"]["status"],
                         "declaration_missing")

    def test_variable_limits_and_negu_compile_with_actual_psx_toolchain(self):
        from automation.search_target_renderer import RendererLimits, deterministic_local_draft
        negu_asm = "negu $v0, $a0\njr $ra\nnop\n"
        negu_decls = {"return_type": "unsigned int",
                      "parameters": [{"type": "unsigned int", "name": "value"}]}
        big_asm = "li $v0, 0\n" + "addiu $v0, $v0, 1\n" * 70 + "jr $ra\nnop\n"
        big_decls = {"return_type": "unsigned int", "parameters": []}
        cases = (("negu_fn", negu_asm, negu_decls, None),
                 ("big_fn", big_asm, big_decls, RendererLimits(max_instructions=96)))
        drafts = []
        for name, assembly, declarations, limits in cases:
            draft = deterministic_local_draft(
                assembly, symbol=name, declarations=declarations, limits=limits)
            self.assertIsNotNone(draft)
            drafts.append(draft)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper, source, output = root / "compile.sh", root / "limits.c", root / "limits.o"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            source.write_text("\n".join(drafts), encoding="utf-8")
            result = subprocess.run([str(wrapper), str(source), "-o", str(output)], env={
                **os.environ, "SOTN_REPO_ROOT": str(ROOT),
                "SOTN_COMPILER_IDENTITY": pipeline_identity().identity, "TMPDIR": directory,
            }, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("negu_fn", "big_fn"):
                _rows, count = _normalized_disassembly(output, symbol=name)
                self.assertGreater(count, 0)

    def test_mult_div_break_shapes_reproduced_by_actual_psx_toolchain(self):
        from automation.search_target_renderer import deterministic_local_draft
        decls = {"return_type": "unsigned int", "parameters": [
            {"type": "unsigned int", "name": "x"}, {"type": "unsigned int", "name": "y"}]}
        prod = deterministic_local_draft(
            "mult $a0, $a1\nmflo $v0\njr $ra\nnop\n",
            symbol="md_prod", declarations=decls)
        guarded = deterministic_local_draft(
            "divu $zero, $a0, $a1\nbnez $a1, .Lok\nnop\nbreak 7\n.Lok:\n"
            "mflo $v0\njr $ra\nnop\n",
            symbol="md_guard", declarations=decls)
        self.assertIsNotNone(prod)
        self.assertIsNotNone(guarded)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper, source, output = root / "compile.sh", root / "md.c", root / "md.o"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            source.write_text(prod + "\n" + guarded, encoding="utf-8")
            result = subprocess.run([str(wrapper), str(source), "-o", str(output)], env={
                **os.environ, "SOTN_REPO_ROOT": str(ROOT),
                "SOTN_COMPILER_IDENTITY": pipeline_identity().identity, "TMPDIR": directory,
            }, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows, _ = _normalized_disassembly(output, symbol="md_prod")
            self.assertIn("mult", rows)
            self.assertIn("mflo", rows)
            rows, _ = _normalized_disassembly(output, symbol="md_guard")
            self.assertIn("divu", rows)
            self.assertIn("break", rows)
            self.assertIn("mflo", rows)

    def test_recovered_switch_compiles_with_actual_psx_toolchain(self):
        from automation.search_target_renderer import deterministic_local_draft
        from automation.test_search_target_renderer import SWITCH_ASM, SWITCH_DECLARATIONS
        draft = deterministic_local_draft(SWITCH_ASM, symbol="switch_fixture", declarations=SWITCH_DECLARATIONS)
        self.assertIsNotNone(draft)
        self.assertIn("switch (", draft)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper, source, output = root / "compile.sh", root / "switch.c", root / "switch.o"
            wrapper.write_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
            wrapper.chmod(0o700)
            source.write_text(draft, encoding="utf-8")
            result = subprocess.run([str(wrapper), str(source), "-o", str(output)], env={
                **os.environ, "SOTN_REPO_ROOT": str(ROOT),
                "SOTN_COMPILER_IDENTITY": pipeline_identity().identity, "TMPDIR": directory,
            }, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            _rows, count = _normalized_disassembly(output, symbol="switch_fixture")
            self.assertGreater(count, 0)


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
