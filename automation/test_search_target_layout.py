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


# Prefix host-call helpers: libc exports advance(), which ELF interposition
# can select instead of an identically named fixture helper.
POINTER_HEADER = "typedef struct Node { unsigned int value; struct Node* next; unsigned int* data; } Node; typedef Node Alias; typedef struct Opaque Opaque;\n"


def pointer_draft(assembly, declaration="unsigned int fn(Node* p, Node* q)", header=POINTER_HEADER):
    context = (header + declaration + ";\nNode* fixture_advance(Node* p);\nNode* fixture_mutate(Node* p);\n").encode()
    facts, status = target_declaration(context.decode(), "fn")
    assert status == "declared"
    return deterministic_local_draft(assembly, symbol="fn", declarations=renderer_declarations(facts, assembly.encode(), context))


class PointerMemberTests(unittest.TestCase):
    def test_aliases_cycles_pointer_arrays_and_opaque_types(self):
        layouts = pointer_layouts(POINTER_HEADER.encode(), ["Node*", "Alias*", "const Node*", "Node**", "Opaque*"])
        self.assertEqual(layouts["Node*"], layouts["Alias*"])
        self.assertEqual(layouts["Node*"]["canonical"], "struct Node*")
        self.assertEqual(layouts["Node*"]["size"], 12)
        self.assertEqual(layouts["Node**"]["size"], 4)
        self.assertEqual(layouts["Node**"]["members"][0]["pointer_type"], "struct Node*")
        self.assertEqual(layouts["Opaque*"]["size"], 0)
        self.assertLess(len(layouts), 16)
        self.assertIsNotNone(pointer_draft("jr $ra\nmove $v0, $a0\n", "Opaque* fn(Opaque* p)"))
        self.assertIsNotNone(pointer_draft("lw $v0, 4($a0)\nnop\njr $ra\nnop\n", "Node* fn(const Node* p)"))
        # A const containing object does not make the pointed-to object const.
        self.assertEqual(layouts["const Node*"]["members"][1]["pointer_type"], "struct Node*")
        self.assertFalse(layouts["const Node*"]["members"][1]["writable"])
        scoped = pointer_layouts(b"void helper(struct Local { int value; }* p);", ["struct Local*"])
        self.assertEqual(scoped["struct Local*"]["size"], 0)

    def test_pointer_safety_boundaries(self):
        cases = [
            ("lw $v0, 4($a0)\nnop\njr $ra\nnop\n", "unsigned int fn(Node* p)", POINTER_HEADER),
            ("lh $v0, 4($a0)\nnop\njr $ra\nnop\n", "unsigned int fn(Node* p)", POINTER_HEADER),
            ("li $v0, 4096\njr $ra\nnop\n", "Node* fn(void)", POINTER_HEADER),
            ("sw $a1, 4($a0)\njr $ra\nli $v0, 0\n", "int fn(Node* p, unsigned int q)", POINTER_HEADER),
            ("sw $a1, 4($a0)\njr $ra\nli $v0, 0\n", "int fn(Node* p, unsigned int* q)", POINTER_HEADER),
            ("sw $a1, 4($a0)\njr $ra\nli $v0, 0\n", "int fn(const Node* p, Node* q)", POINTER_HEADER),
            ("addiu $v0, $a0, 4\njr $ra\nnop\n", "Opaque* fn(Opaque* p)", POINTER_HEADER),
            ("addiu $v0, $a0, 4\njr $ra\nnop\n", "Node* fn(Node* p)", POINTER_HEADER),
            ("addu $v0, $a0, $a1\njr $ra\nnop\n", "Node* fn(Node* p, unsigned int q)", POINTER_HEADER),
            ("lw $t0, 4($a0)\nlw $v0, 0($t0)\nnop\njr $ra\nnop\n", "unsigned int fn(Node* p)", POINTER_HEADER),
            ("lw $v0, 0($a0)\nnop\njr $ra\nnop\n", "Node* fn(Node* p)", "typedef union Node { int* x; int* y; } Node;"),
            ("lw $v0, 0($a0)\nnop\njr $ra\nnop\n", "Node* fn(Node* p)", "typedef struct Node { void (*callback)(void); } Node;"),
            ("sw $zero, 0($a0)\njr $ra\nli $v0, 0\n", "int fn(Node* p)", "typedef struct Node { int* const fixed; } Node;"),
        ]
        for assembly, declaration, header in cases:
            with self.subTest(assembly=assembly, declaration=declaration):
                self.assertIsNone(pointer_draft(assembly, declaration, header))

    def test_compiled_pointer_values_preserve_aliases_calls_and_host_width(self):
        compiler = shutil.which("gcc")
        if compiler is None:
            self.skipTest("host fixture compiler unavailable")
        prologue = "addiu $sp, $sp, -24\nsw $ra, 20($sp)\nsw $s0, 16($sp)\n"
        epilogue = "lw $ra, 20($sp)\nlw $s0, 16($sp)\njr $ra\naddiu $sp, $sp, 24\n"
        cases = {
            "chase": ("lw $t0, 4($a0)\nnop\nlw $v0, 0($t0)\nnop\njr $ra\nnop\n", "unsigned int fn(Node* p)"),
            "captured_alias": ("lw $t0, 4($a0)\nsw $a1, 4($a0)\nlw $v0, 0($t0)\nnop\njr $ra\nnop\n", "unsigned int fn(Node* p, Node* q)"),
            "null_next": ("lw $t0, 4($a0)\nnop\nbeqz $t0, .Lnull\nli $v0, 7\nlw $v0, 0($t0)\nnop\njr $ra\nnop\n.Lnull:\njr $ra\nnop\n", "unsigned int fn(Node* p)"),
            "clear_return": ("lw $v0, 4($a0)\nsw $zero, 4($a0)\njr $ra\nnop\n", "Node* fn(Node* p)"),
            "pointer_store": ("sw $a1, 4($a0)\njr $ra\nmove $v0, $a1\n", "Node* fn(Node* p, Alias* q)"),
            "call_result": (prologue + "jal fixture_advance\nnop\n" + epilogue, "Alias* fn(Node* p)"),
            "ignored_call": (prologue + "jal fixture_advance\nnop\nli $v0, 17\n" + epilogue, "unsigned int fn(Node* p)"),
            "captured_call": (prologue + "lw $s0, 4($a0)\nnop\njal fixture_mutate\nnop\nlw $v0, 0($s0)\nnop\n" + epilogue, "unsigned int fn(Node* p)"),
            "advance_element": ("addiu $v0, $a0, 12\njr $ra\nnop\n", "Node* fn(Node* p)"),
            "retreat_element": ("li $t0, 12\nsubu $v0, $a0, $t0\njr $ra\nnop\n", "Node* fn(Node* p)"),
            "zero_copy": ("addu $v0, $zero, $a0\njr $ra\nnop\n", "Alias* fn(Node* p)"),
            "pointer_array": ("lw $v0, 4($a0)\nnop\njr $ra\nnop\n", "Node* fn(Node** p)"),
            "data_pointer": ("lw $t0, 8($a0)\nnop\naddiu $t0, $t0, 4\nlw $v0, 0($t0)\nnop\njr $ra\nnop\n", "unsigned int fn(Node* p)"),
            "null_return": ("jr $ra\nmove $v0, $zero\n", "Node* fn(void)"),
        }
        sources = [POINTER_HEADER, "unsigned int effects; Node* fixture_advance(Node* p) { effects++; return p->next; } Node* fixture_mutate(Node* p) { effects++; p->next = 0; return p; }"]
        for name, (assembly, declaration) in cases.items():
            generated = pointer_draft(assembly, declaration)
            self.assertIsNotNone(generated, name)
            sources.append(generated.replace(" fn(", " " + name + "("))
        with tempfile.TemporaryDirectory() as directory:
            source, library = Path(directory) / "pointers.c", Path(directory) / "pointers.so"
            source.write_text("\n".join(sources))
            built = subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC", str(source), "-o", str(library)], capture_output=True, timeout=30)
            self.assertEqual(built.returncode, 0, built.stderr.decode())
            compiled = ctypes.CDLL(str(library))
            class Node(ctypes.Structure):
                pass
            Node._fields_ = [("value", ctypes.c_uint32), ("next", ctypes.POINTER(Node)), ("data", ctypes.POINTER(ctypes.c_uint32))]
            nodes = (Node * 2)()
            first, second = ctypes.pointer(nodes[0]), ctypes.pointer(nodes[1])
            first_address, second_address = ctypes.addressof(nodes[0]), ctypes.addressof(nodes[1])
            for name, (_, declaration) in cases.items():
                function = getattr(compiled, name)
                function.restype = ctypes.c_uint32 if declaration.startswith("unsigned") else ctypes.c_void_p
                function.argtypes = [] if "(void)" in declaration else [ctypes.c_void_p] * (2 if "," in declaration else 1)
            for value in (0, 1, 0x7fffffff, 0x80000000, 0xffffffff):
                nodes[1].value = value
                nodes[0].next = second
                self.assertEqual(compiled.chase(first), value)
                self.assertEqual(compiled.captured_alias(first, first), value)
                self.assertEqual(ctypes.addressof(nodes[0].next.contents), first_address)
                nodes[0].next = second
                self.assertEqual(compiled.call_result(first), second_address)
                self.assertEqual(compiled.ignored_call(first), 17)
                self.assertEqual(compiled.captured_call(first), value)
                self.assertFalse(nodes[0].next)
                self.assertEqual(compiled.null_next(first), 7)
                self.assertEqual(compiled.pointer_store(first, second), second_address)
                self.assertEqual(compiled.null_next(first), value)
                self.assertEqual(compiled.clear_return(first), second_address)
                self.assertFalse(nodes[0].next)
            self.assertEqual(ctypes.c_uint32.in_dll(compiled, "effects").value, 15)
            self.assertEqual(compiled.advance_element(first), second_address)
            self.assertEqual(compiled.retreat_element(second), first_address)
            self.assertEqual(compiled.zero_copy(first), first_address)
            pointers = (ctypes.POINTER(Node) * 2)(first, second)
            self.assertEqual(compiled.pointer_array(pointers), second_address)
            words = (ctypes.c_uint32 * 2)(17, 29)
            nodes[0].data = words
            self.assertEqual(compiled.data_pointer(first), 29)
            self.assertIsNone(compiled.null_return())


if __name__ == "__main__":
    unittest.main()
