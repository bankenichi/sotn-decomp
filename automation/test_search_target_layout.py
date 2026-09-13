"""US named memory lowering, alias ordering and conservative ABI boundaries."""
import ctypes
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.search_source_context import renderer_declarations, target_declaration
from automation.search_target_renderer import deterministic_local_draft
from automation.search_target_layout import pointer_layouts


HEADER = "typedef struct { signed char byte; unsigned char flag; short half; unsigned int word; short array[2]; } Item;\n"


def draft(assembly, declaration="unsigned int fn(Item* p, Item* q)", header=HEADER):
    context = (header + declaration + ";\nvoid touch(Item* p);\n").encode()
    facts, status = target_declaration(context.decode(), "fn")
    assert status == "declared"
    return deterministic_local_draft(assembly, symbol="fn", declarations=renderer_declarations(facts, assembly.encode(), context))


class LayoutTests(unittest.TestCase):
    def test_named_layout_and_qualifiers_come_from_exact_context(self):
        layouts = pointer_layouts((HEADER + "typedef const Item Frozen;\n").encode(), ["Item*", "Frozen*", "u32*"])
        self.assertEqual(layouts["Item*"]["size"], 12)
        self.assertEqual([(m["path"], m["offset"], m["width"]) for m in layouts["Item*"]["members"]],
                         [(".byte", 0, 1), (".flag", 1, 1), (".half", 2, 2), (".word", 4, 4), (".array[0]", 8, 2), (".array[1]", 10, 2)])
        self.assertTrue(all(not m["writable"] for m in layouts["Frozen*"]["members"]))
        # Missing aliases must not be invented by the decompiler's defaults.
        self.assertNotIn("u32*", layouts)
        self.assertEqual(pointer_layouts(b"int broken(unknown_type x);", ["Item*"]), {})

    def test_refuses_ambiguous_partial_unaligned_const_and_pointer_integer_access(self):
        cases = [
            ("lw $v0, 2($a0)\nnop\njr $ra\nnop\n", {}, "unaligned"),
            ("lw $v0, 12($a0)\nnop\njr $ra\nnop\n", {}, "out of object"),
            ("lb $v0, 4($a0)\nnop\njr $ra\nnop\n", {}, "partial member"),
            ("lw $v0, 4($a0)\naddu $v0, $v0, $v0\njr $ra\nnop\n", {}, "load delay"),
            ("jr $ra\nlw $v0, 4($a0)\n", {}, "load in control slot"),
            ("sw $zero, 4($a0)\njr $ra\nli $v0, 0\n", {"declaration": "int fn(const Item* p)"}, "const"),
            ("addu $v0, $a0, $a1\njr $ra\nnop\n", {}, "pointer arithmetic"),
            ("lw $v0, 0($a0)\nnop\njr $ra\nnop\n", {"header": "typedef union { int x; int y; } Item;"}, "ambiguous union"),
            ("lw $v0, 0($a0)\nnop\njr $ra\nnop\n", {"header": "typedef struct { int x:3; int y; } Item;"}, "bitfield"),
        ]
        for assembly, options, label in cases:
            with self.subTest(label=label):
                self.assertIsNone(draft(assembly, **options))

    def test_compiled_memory_operations_preserve_values_aliasing_and_call_order(self):
        compiler = shutil.which("gcc")
        if compiler is None:
            self.skipTest("host fixture compiler unavailable")
        prologue = "addiu $sp, $sp, -24\nsw $ra, 20($sp)\nsw $s0, 16($sp)\n"
        epilogue = "lw $ra, 20($sp)\nlw $s0, 16($sp)\njr $ra\naddiu $sp, $sp, 24\n"
        cases = {
            "alias": "lw $t0, 4($a0)\nsw $zero, 4($a1)\nlw $v0, 4($a0)\nnop\naddu $v0, $v0, $t0\njr $ra\nnop\n",
            "signed_load": "lb $t0, 0($a0)\nlh $v0, 2($a0)\nnop\naddu $v0, $v0, $t0\njr $ra\nnop\n",
            "unsigned_load": "lbu $t0, 0($a0)\nlhu $v0, 2($a0)\nnop\naddu $v0, $v0, $t0\njr $ra\nnop\n",
            "store": "li $t0, 65535\nsh $t0, 10($a0)\nlh $v0, 10($a0)\nnop\njr $ra\nsb $t0, 1($a0)\n",
            "call": prologue + "move $s0, $a0\njal touch\nsw $zero, 4($a0)\nlw $v0, 4($s0)\nnop\n" + epilogue,
            "branch": "beqz $a0, .Lnull\nli $v0, 7\nlw $v0, 4($a0)\nnop\njr $ra\nnop\n.Lnull:\njr $ra\nnop\n",
            "move_pointer": "move $t0, $a0\nlw $v0, 4($t0)\nnop\njr $ra\nnop\n",
        }
        sources = [HEADER, "unsigned int effects; void touch(Item* p) { effects++; p->word += 19; }"]
        for name, assembly in cases.items():
            generated = draft(assembly)
            self.assertIsNotNone(generated, name)
            sources.append(generated.replace(" fn(", " " + name + "("))
        scalar = draft("lw $v0, 4($a0)\nnop\njr $ra\nnop\n", "unsigned int fn(unsigned int* p)")
        self.assertIsNotNone(scalar)
        sources.append(scalar.replace(" fn(", " scalar("))
        with tempfile.TemporaryDirectory() as directory:
            source, library = Path(directory) / "memory.c", Path(directory) / "memory.so"
            source.write_text("\n".join(sources))
            built = subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC", str(source), "-o", str(library)], capture_output=True, timeout=30)
            self.assertEqual(built.returncode, 0, built.stderr.decode())
            compiled = ctypes.CDLL(str(library))
            class Item(ctypes.Structure):
                _fields_ = [("byte", ctypes.c_int8), ("flag", ctypes.c_uint8), ("half", ctypes.c_int16), ("word", ctypes.c_uint32), ("array", ctypes.c_int16 * 2)]
            for name in cases:
                function = getattr(compiled, name)
                function.argtypes, function.restype = [ctypes.POINTER(Item)] * 2, ctypes.c_uint32
            for value in (0, 1, 0x7fffffff, 0x80000000, 0xffffffff):
                item = Item(-128, 0, -32768, value)
                other = Item()
                self.assertEqual(compiled.alias(ctypes.byref(item), ctypes.byref(other)), 2 * value & 0xffffffff)
                self.assertEqual(compiled.alias(ctypes.byref(item), ctypes.byref(item)), value)
                self.assertEqual(item.word, 0)
                self.assertEqual(compiled.signed_load(ctypes.byref(item), None), (-128 - 32768) & 0xffffffff)
                self.assertEqual(compiled.unsigned_load(ctypes.byref(item), None), 128 + 32768)
                self.assertEqual(compiled.store(ctypes.byref(item), None), 0xffffffff)
                self.assertEqual((item.flag, item.array[1]), (255, -1))
                self.assertEqual(compiled.call(ctypes.byref(item), None), 19)
                self.assertEqual(compiled.branch(None, None), 7)
                self.assertEqual(compiled.branch(ctypes.byref(item), None), 19)
                self.assertEqual(compiled.move_pointer(ctypes.byref(item), None), 19)
            self.assertEqual(ctypes.c_uint32.in_dll(compiled, "effects").value, 5)
            compiled.scalar.argtypes, compiled.scalar.restype = [ctypes.POINTER(ctypes.c_uint32)], ctypes.c_uint32
            self.assertEqual(compiled.scalar((ctypes.c_uint32 * 2)(5, 17)), 17)


if __name__ == "__main__":
    unittest.main()
