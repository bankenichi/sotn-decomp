"""Focused tests for target-derived indexed query and rendering boundaries."""

from __future__ import annotations

import sys
import ctypes
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_donor_query import DonorSemanticClaim
from automation.search_lanes import DonorEvidence, LaneCandidate, Recipient
from automation.search_semantic_signatures import SemanticInstruction, assembly_signatures
from automation.search_target_renderer import (
    DEFAULT_LIMITS,
    RendererLimits,
    TargetContextUnsupported,
    TargetEvidenceError,
    TargetRendererInputError,
    _assembly_signatures,
    _parse_assembly,
    deterministic_local_draft,
    load_target_index,
    query_for_recipient,
    render_target_candidate,
    _canonical_reg,
    loop_regions,
    region_flow,
)
from automation.search_types import RunManifest, hash_bytes, hash_canonical
from automation.test_search_donor_index import digest
from automation.test_search_lanes import make_manifest


RECIPIENT_ID = "us:ST:fn"
TARGET_ASM = b"""/* 0 80000000 24020007 */ addiu $v0, $zero, 7
/* 4 80000004 03E00008 */ jr $ra
/* 8 80000008 00000000 */ nop
"""


def _recipient() -> Recipient:
    return Recipient(
        recipient_id=RECIPIENT_ID,
        overlay="ST",
        function="fn",
        metadata={"target_file": "asm/us/st/fn.s"},
    )


def _target_fixture(
    assembly: bytes = TARGET_ASM,
    *,
    context_bytes: bytes | None = None,
    compiler_identity: str | None = None,
    instruction_signature: str | None = None,
    cfg_signature: str | None = None,
    dataflow_signature: str | None = None,
):
    temp = tempfile.TemporaryDirectory(prefix="target-renderer-")
    archive = ContentAddressedArchive(Path(temp.name) / "run")
    assembly_ref = archive.put_bytes(
        assembly,
        category="target-assembly",
        suffix=".s",
        media_type="text/x-asm",
    )
    object_ref = archive.put_bytes(
        b"target object",
        category="target-object",
        suffix=".o",
        media_type="application/octet-stream",
    )
    derived_instruction, derived_cfg, derived_dataflow = _assembly_signatures(
        _parse_assembly(assembly.decode("utf-8"))
    )
    target_doc = {
        "artifact_type": "sotn-search-target-evidence",
        "assembly": {
            "artifact": assembly_ref.to_dict(),
            "content_hash": hash_bytes(assembly),
            "path": "asm/us/st/fn.s",
            "byte_size": len(assembly),
        },
        "object": {
            "artifact": object_ref.to_dict(),
            "content_hash": object_ref.content_hash,
            "path": "build/us/src/st/fn.o",
            "byte_size": object_ref.byte_size,
        },
        "record_id": RECIPIENT_ID,
        "schema_version": "1.0.0",
        "symbol": "fn",
        "instruction_signature": (
            derived_instruction if instruction_signature is None else instruction_signature
        ),
        "cfg_signature": derived_cfg if cfg_signature is None else cfg_signature,
        "dataflow_signature": (
            derived_dataflow if dataflow_signature is None else dataflow_signature
        ),
        "declarations": {"return_type": "int"},
    }
    compiler_identity = compiler_identity or RunManifest.from_dict(make_manifest(RECIPIENT_ID)).compiler_identity
    if context_bytes is not None:
        from automation.search_source_context import target_declaration, TARGET_CONTEXT_PROTOCOL
        facts, status = target_declaration(context_bytes.decode(), "fn")
        context_refs = {key: archive.put_bytes(context_bytes, category=category, suffix=".c", media_type="text/x-c").to_dict()
                        for key, category in (("input", "target-context-input"), ("preprocessed", "target-context"))}
        target_doc["declarations"] = {**facts, "context_evidence": {
            "protocol": TARGET_CONTEXT_PROTOCOL, "record_id": RECIPIENT_ID,
            "compiler_identity": compiler_identity, "path": "src/st/st.c", "status": status, **context_refs}}
    target_identity = hash_canonical(target_doc)
    manifest = replace(
        RunManifest.from_dict(make_manifest(RECIPIENT_ID)),
        target_identities={RECIPIENT_ID: target_identity},
        compiler_identity=compiler_identity,
    )
    target_evidence_ref = archive.put_json(
        target_doc,
        category="target-evidence",
        suffix=".json",
    )
    target_index_document = {
        "artifact_type": "sotn-search-target-index",
        "schema_version": "1.0.0",
        "records": [
            {
                "record_id": RECIPIENT_ID,
                "target_identity": target_identity,
                "target_evidence": target_evidence_ref.to_dict(),
            }
        ],
    }
    archive.put_json(
        target_index_document,
        category="target-index",
        suffix=".json",
    )
    return temp, archive, manifest, load_target_index(archive, manifest)


def _claim() -> DonorSemanticClaim:
    evidence = DonorEvidence(
        donor_id="hd:ST:fn",
        recipient_id=RECIPIENT_ID,
        version="hd",
        source="artifacts/donor.s",
        match_kind="instruction_shape",
        signature="sig:fn",
        symbol="fn",
        instruction_signature="ins:target",
        cfg_signature="cfg:target",
        dataflow_signature="flow:target",
        declarations={"return_type": "int"},
        constants={"literal": 7},
        compatible=True,
    )
    return DonorSemanticClaim.from_evidence(evidence)



# Authored from the local SOTN assembly format and MIPS instruction semantics.
SWITCH_ASM = """.set noat
.set noreorder
.section .rodata
.align 2
glabel jtbl_fixture
.word .Lfirst
.word .Lsecond
.word .Lfirst
.size jtbl_fixture, . - jtbl_fixture
.section .text
glabel fn
sltiu $v0, $a0, 3
beqz $v0, .Ldefault
sll $v0, $a0, 2
lui $at, %hi(jtbl_fixture)
addu $at, $at, $v0
lw $v0, %lo(jtbl_fixture)($at)
nop
jr $v0
nop
.Lfirst:
addiu $v0, $a1, 3
jr $ra
addiu $v0, $v0, 1
.Lsecond:
addiu $v0, $a1, -7
jr $ra
nop
.Ldefault:
addiu $v0, $a1, 100
jr $ra
nop
.size fn, . - fn
"""
SWITCH_DECLARATIONS = {
    "return_type": "unsigned int",
    "parameters": [{"type": "unsigned int", "name": "selector"},
                   {"type": "unsigned int", "name": "bias"}],
}


class IndependentSwitchTests(unittest.TestCase):
    def test_local_table_produces_archived_candidate_and_replays(self):
        context = b"unsigned int fn(unsigned int selector, unsigned int bias);"
        temp, archive, manifest, index = _target_fixture(SWITCH_ASM.encode(), context_bytes=context)
        try:
            result = render_target_candidate(manifest, index, _recipient(), (_claim(),), lane="cfg_dataflow")
            self.assertIsInstance(result, LaneCandidate)
            self.assertIn("switch (", result.source)
            self.assertIn("case 0:", result.source)
            self.assertIn("case 2:", result.source)
            self.assertNotIn("jtbl_fixture", result.source)
            replay = render_target_candidate(manifest, load_target_index(archive, manifest),
                                             _recipient(), (_claim(),), lane="cfg_dataflow")
            self.assertEqual(result, replay)
        finally:
            temp.cleanup()

    def test_real_us_dispatch_and_unreachable_alignment_word(self):
        from automation.search_mips_switch import recover_dispatches, split_local_tables
        from automation.search_target_renderer import _strip_assembly_comment
        sample = Path(__file__).resolve().parents[1] / "asm/us/boss/bo0/nonmatchings/2D26C/func_us_801AE858.s"
        if not sample.is_file():
            self.skipTest("generated US assembly unavailable")
        code, tables = split_local_tables(sample.read_text(), _strip_assembly_comment)
        dispatches = recover_dispatches(_parse_assembly(code, retain_relocations=True), tables)
        self.assertEqual(len(dispatches), 1)
        dispatch = next(iter(dispatches.values()))
        self.assertEqual(dispatch.targets, (".Lus_801AE8B4", ".Lus_801AEB90", ".Lus_801AEBE0",
                                           ".Lus_801AEC64", ".Lus_801AEE48"))
        # Recovering the dispatch does not make this large function renderable.
        self.assertIsNone(deterministic_local_draft(sample.read_text(), symbol="fn",
                                                   declarations=SWITCH_DECLARATIONS))

    def test_register_spellings_and_guard_forms_preserve_switch(self):
        variants = [
            SWITCH_ASM.replace("beqz $v0, .Ldefault", "beq $zero, $v0, .Ldefault"),
            SWITCH_ASM.replace("addu $at, $at, $v0", "addu $at, $v0, $at"),
            SWITCH_ASM.replace(".size jtbl_fixture", ".word 0x00000000\n.size jtbl_fixture"),
            SWITCH_ASM.replace("$at", "$1"),
            SWITCH_ASM.replace("$a0", "r4").replace("$v0", "r2"),
        ]
        for assembly in variants:
            self.assertIsNotNone(deterministic_local_draft(assembly, symbol="fn",
                                                          declarations=SWITCH_DECLARATIONS))
        for replacement in (".word 0", ".word 0x00000000"):
            bad = SWITCH_ASM.replace(".word .Lsecond", replacement)
            self.assertIsNone(deterministic_local_draft(bad, symbol="fn", declarations=SWITCH_DECLARATIONS))

    def test_compiled_cases_default_and_selector_normalization(self):
        compiler = shutil.which("gcc") or shutil.which("cc")
        if not compiler:
            self.skipTest("host C compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="switch-semantics-") as directory:
            root = Path(directory)
            sources = []
            for name, assembly in (("direct", SWITCH_ASM),
                                   ("normalized", SWITCH_ASM.replace(
                                       "sltiu $v0, $a0, 3", "addiu $a0, $a0, -3\nsltiu $v0, $a0, 3"))):
                source = deterministic_local_draft(assembly, symbol=name, declarations=SWITCH_DECLARATIONS)
                self.assertIsNotNone(source)
                sources.append(source)
            (root / "cases.c").write_text("\n".join(sources), encoding="utf-8")
            subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC",
                            str(root / "cases.c"), "-o", str(root / "cases.so")], check=True,
                           capture_output=True, text=True)
            library = ctypes.CDLL(str(root / "cases.so"))
            for name, offset in (("direct", 0), ("normalized", 3)):
                function = getattr(library, name)
                function.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
                function.restype = ctypes.c_uint32
                for selector in (0, 1, 2, 3, 4, 5, 6, 0x7fffffff, 0x80000000, 0xffffffff):
                    index = (selector - offset) & 0xffffffff
                    for bias in (0, 1, 0x7fffffff, 0x80000000, 0xffffffff):
                        expected = (bias + (4 if index in (0, 2) else -7 if index == 1 else 100)) & 0xffffffff
                        self.assertEqual(function(selector, bias), expected, (name, selector, bias))

    def test_unproved_switches_refuse_instead_of_erasing_data(self):
        bad = {
            "wrong bound": SWITCH_ASM.replace("$a0, 3", "$a0, 4"),
            "wrong index": SWITCH_ASM.replace("sll $v0, $a0", "sll $v0, $a1"),
            "wrong scale": SWITCH_ASM.replace("$a0, 2", "$a0, 1"),
            "wrong table": SWITCH_ASM.replace("%lo(jtbl_fixture)", "%lo(other_table)"),
            "missing load delay": SWITCH_ASM.replace("nop\njr $v0", "jr $v0"),
            "jump slot side effect": SWITCH_ASM.replace("jr $v0\nnop", "jr $v0\naddiu $a1, $a1, 1"),
            "unknown target": SWITCH_ASM.replace(".word .Lsecond", ".word .Lexternal"),
            "table expression": SWITCH_ASM.replace(".word .Lsecond", ".word .Lsecond + 4"),
            "writable table": SWITCH_ASM.replace(".section .rodata", ".section .data"),
            "backward case": SWITCH_ASM.replace("glabel fn\nsltiu", "glabel fn\n.Lentry:\nsltiu").replace(
                ".word .Lsecond", ".word .Lentry"),
            "dispatch interior entry": SWITCH_ASM.replace("lui $at", ".Linside:\nlui $at"),
            "address value escapes": SWITCH_ASM.replace("addiu $v0, $a1, 3", "addu $v0, $at, $zero"),
            "jump value escapes": SWITCH_ASM.replace("addiu $v0, $a1, 3", "addiu $a1, $a1, 3"),
            "extra data": SWITCH_ASM.replace(".section .text", ".byte 17\n.section .text"),
            "duplicate table": SWITCH_ASM.replace(".section .text", "glabel jtbl_fixture\n.word .Lfirst\n.section .text"),
        }
        for reason, assembly in bad.items():
            with self.subTest(reason=reason):
                self.assertIsNone(deterministic_local_draft(assembly, symbol="fn", declarations=SWITCH_DECLARATIONS))


class TargetQueryTests(unittest.TestCase):
    def test_query_uses_archived_target_only_and_binds_recipient(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            query = query_for_recipient(manifest, target_index, _recipient())
            self.assertEqual(query.recipient_id, RECIPIENT_ID)
            self.assertIsNone(query.version)
            self.assertIsNone(query.source_path)
            self.assertEqual(query.symbol, "fn")
            context = target_index.records[0]
            self.assertEqual(query.instruction_signature, context.instruction_signature)
            self.assertEqual(query.cfg_signature, context.cfg_signature)
            self.assertEqual(query.dataflow_signature, context.dataflow_signature)
            self.assertEqual(query.compiler_identity, manifest.compiler_identity)
            self.assertEqual(query.config_identity, manifest.config_identity)
        finally:
            temp.cleanup()

    def test_wrong_recipient_target_cannot_be_selected(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            with self.assertRaises(TargetRendererInputError):
                query_for_recipient(
                    manifest,
                    target_index,
                    Recipient("us:ST:other", "ST", "other"),
                )
        finally:
            temp.cleanup()

    def test_stored_target_signatures_must_match_archived_assembly(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture(
            instruction_signature="sha256:" + "0" * 64,
        )
        try:
            with self.assertRaises(TargetEvidenceError):
                query_for_recipient(manifest, target_index, _recipient())
        finally:
            temp.cleanup()

    def test_renderer_signatures_use_shared_cross_platform_normalizer(self) -> None:
        assembly = (
            "ldr r0, [r1, #4]\n"
            "bl #0x20\n"
            "add r0, r0, r2\n"
            "ret\n"
        )
        parsed = _parse_assembly(assembly)
        expected = assembly_signatures(
            tuple(
                SemanticInstruction(item.mnemonic, item.operands, item.unsupported)
                for item in parsed
            )
        )
        self.assertEqual(_assembly_signatures(parsed), expected)
        self.assertTrue(any(item.unsupported for item in parsed))

    def test_numeric_branch_refusal_preserves_shared_cross_platform_signatures(self) -> None:
        cases = (
            "beq $a0, $zero, 4\njr $ra\nnop\n",
            "b.eq #4\nbx lr\n",
            "bt 4\nrts\n",
        )
        for assembly in cases:
            with self.subTest(assembly=assembly):
                parsed = _parse_assembly(assembly)
                expected = assembly_signatures(
                    tuple(
                        SemanticInstruction(
                            item.mnemonic,
                            item.operands,
                            item.unsupported,
                        )
                        for item in parsed
                    )
                )
                self.assertEqual(_assembly_signatures(parsed), expected)
                self.assertTrue(any(item.unsupported for item in parsed))
                self.assertIsNone(
                    deterministic_local_draft(
                        assembly,
                        symbol="numeric_branch",
                        declarations={"return_type": "int"},
                    )
                )

    def test_deterministic_draft_maps_abi_registers_to_declared_parameter_positions(self) -> None:
        one = deterministic_local_draft(
            "addiu $v0, $a0, 1\njr $ra\nnop\n",
            symbol="one",
            declarations={
                "return_type": "int",
                "parameters": [{"type": "int", "name": "count"}],
            },
        )
        self.assertIsNotNone(one)
        self.assertIn("int one(int count)", one)
        self.assertIn("(unsigned int)count", one)
        self.assertNotIn("a0", one or "")
        extracted = deterministic_local_draft(
            ".set noat\n.set noreorder\nglabel one\naddiu $v0, $a0, 1\njr $ra\nnop\n",
            symbol="one", declarations={"return_type": "int", "parameters": [{"type": "int", "name": "count"}]},
        )
        self.assertEqual(extracted, one)
        self.assertIsNone(deterministic_local_draft(
            ".word 1\naddiu $v0, $zero, 1\njr $ra\nnop\n", symbol="embedded_data",
        ))

        many = deterministic_local_draft(
            "addu $v0, $a0, $a1\njr $ra\nnop\n",
            symbol="many",
            declarations={
                "return_type": "int",
                "parameters": [
                    {"type": "int", "name": "left_value"},
                    {"type": "int", "name": "right_value"},
                ],
            },
        )
        self.assertIsNotNone(many)
        self.assertIn("int many(int left_value, int right_value)", many)
        self.assertIn("(unsigned int)left_value", many)
        self.assertIn("(unsigned int)right_value", many)
        self.assertNotIn("a0", many or "")
        self.assertNotIn("a1", many or "")

        # Without target declaration positions the renderer must refuse rather
        # than inventing C parameters named after ABI registers.
        self.assertIsNone(
            deterministic_local_draft(
                "move $v0, $a0\njr $ra\nnop\n",
                symbol="missing_declarations",
            )
        )


    def test_or_immediate_preserves_overlapping_bits(self) -> None:
        source = deterministic_local_draft(
            "ori $v0, $a0, 1\njr $ra\nnop\n",
            symbol="flags",
            declarations={
                "return_type": "unsigned int",
                "parameters": [{"type": "unsigned int", "name": "value"}],
            },
        )
        self.assertIsNotNone(source)
        self.assertIn("unsigned int flags(unsigned int value)", source)
        self.assertIn(" | ", source)
        # At value=1 addition would produce 2; OR must preserve the set bit.
        self.assertEqual(1 | 1, 1)

    def test_stack_data_operations_are_not_silently_dropped(self) -> None:
        for instruction in ("lw $v0, 16($sp)", "sw $a0, 16($sp)",
                            "lw $a0, 16($sp)"):
            with self.subTest(instruction=instruction):
                source = deterministic_local_draft(
                    "li $v0, 7\n" + instruction + "\njr $ra\nnop\n",
                    symbol="stack_value",
                    declarations={"return_type": "int"},
                )
                self.assertIsNone(source)


class DirectCallTests(unittest.TestCase):
    PROLOGUE = "addiu $sp, $sp, -24\nsw $ra, 20($sp)\nsw $s0, 16($sp)\n"
    EPILOGUE = "lw $ra, 20($sp)\nlw $s0, 16($sp)\njr $ra\naddiu $sp, $sp, 24\n"
    CONTEXT = b"unsigned int add_value(unsigned int value);\nunsigned int subtract_value(unsigned int value);\nvoid record_value(unsigned int value);\n"

    def declarations(self, assembly):
        from automation.search_source_context import renderer_declarations
        return renderer_declarations({"return_type": "unsigned int", "parameters": [
            {"type": "unsigned int", "name": "value"}]}, assembly.encode(), self.CONTEXT)

    def test_compiled_direct_calls_preserve_side_effects_arguments_and_saved_values(self):
        compiler = shutil.which("gcc")
        if compiler is None:
            self.skipTest("host fixture compiler unavailable")
        p, e = self.PROLOGUE, self.EPILOGUE
        cases = {
            "saved_argument": (p + "move $s0, $a0\njal add_value\naddiu $a0, $a0, 1\naddu $v0, $v0, $s0\n" + e,
                               lambda x: (2*x+4, 1, x+1)),
            "two_calls": (p + "jal add_value\naddiu $a0, $a0, 1\nmove $s0, $v0\nmove $a0, $v0\njal add_value\naddiu $a0, $a0, 1\naddu $v0, $v0, $s0\n" + e,
                          lambda x: (2*x+12, 2, (x+1)*17+x+5)),
            "branch_call": (p + "beqz $a0, .Lzero\nli $a0, 5\njal add_value\nnop\nb .Ljoin\nnop\n.Lzero:\njal subtract_value\nnop\n.Ljoin:\n" + e,
                            lambda x: (8 if x else 2, 1, 5 if x else 1005)),
            "ignored_and_void": (p + "jal add_value\nnop\njal record_value\nli $a0, 7\nli $v0, 5\n" + e,
                                 lambda x: (5, 2, x*17+7)),
        }
        sources = ["unsigned int effects, trace;",
            "unsigned int add_value(unsigned int x) { effects++; trace = trace*17U+x; return x+3U; }",
            "unsigned int subtract_value(unsigned int x) { effects++; trace = trace*17U+x+1000U; return x-3U; }",
            "void record_value(unsigned int x) { effects++; trace = trace*17U+x; }"]
        for name, (assembly, _) in cases.items():
            draft = deterministic_local_draft(assembly, symbol=name, declarations=self.declarations(assembly))
            self.assertIsNotNone(draft, name)
            self.assertNotIn("$", draft)
            sources.append(draft)
        with tempfile.TemporaryDirectory() as directory:
            source, library = Path(directory) / "calls.c", Path(directory) / "calls.so"
            source.write_text("\n".join(sources))
            result = subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC", str(source), "-o", str(library)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            compiled = ctypes.CDLL(str(library))
            effects = ctypes.c_uint32.in_dll(compiled, "effects")
            trace = ctypes.c_uint32.in_dll(compiled, "trace")
            for name, (_, expected) in cases.items():
                function = getattr(compiled, name)
                function.argtypes, function.restype = [ctypes.c_uint32], ctypes.c_uint32
                for x in (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
                    effects.value = trace.value = 0
                    value = function(x)
                    wanted = tuple(item & 0xFFFFFFFF for item in expected(x))
                    self.assertEqual((value, effects.value, trace.value), wanted, (name, x))

    def test_unnamed_callee_prototype_renders_types_only(self):
        from automation.search_source_context import renderer_declarations
        p, e = self.PROLOGUE, self.EPILOGUE
        assembly = p + "jal add_value\nnop\n" + e
        context = b"unsigned int add_value(unsigned int);\n"
        facts = renderer_declarations({"return_type": "unsigned int", "parameters": [
            {"type": "unsigned int", "name": "value"}]}, assembly.encode(), context)
        self.assertEqual(facts["call_declarations"]["add_value"]["status"], "declared")
        source = deterministic_local_draft(assembly, symbol="caller", declarations=facts)
        self.assertIsNotNone(source)
        self.assertIn("add_value(", source)

    def test_narrow_caller_signature_renders(self):
        declarations = {"return_type": "u8",
                        "parameters": [{"type": "s16", "name": "sfxId"}]}
        source = deterministic_local_draft(
            "move $v0, $a0\njr $ra\nnop\n",
            symbol="fn", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertIn("return", source)
    def test_call_abi_and_stack_refusals(self):
        p, e = self.PROLOGUE, self.EPILOGUE
        good = p + "jal add_value\nnop\n" + e
        invalid = [
            good.replace("add_value", "unknown"),
            good.replace("jal add_value", "jalr $t9"),
            good.replace("sw $ra, 20($sp)", "nop"),
            good.replace("sw $ra, 20($sp)", "nop").replace("jal add_value\nnop", "jal add_value\nsw $ra, 20($sp)"),
            good.replace("lw $ra, 20($sp)", "nop"),
            good.replace("20($sp)", "12($sp)"),
            good.replace("addiu $sp, $sp, 24", "nop"),
            good.replace("jal add_value\nnop", "jal add_value\njal add_value"),
            p + "jal add_value\nnop\naddu $v0, $v0, $a0\n" + e,
            p + "move $s0, $a0\njal add_value\nnop\n" + e.replace("lw $s0, 16($sp)", "nop"),
            p + "jal add_value\nlw $a0, 16($sp)\n" + e,
            p + "lw $a0, 16($sp)\naddu $v0, $a0, $a0\n" + e,
            (p + "lw $a0, 16($sp)\naddu $v0, $a0, $a0\n" + e).replace("$", ""),
            p + "lw $v0, 0($a0)\nnop\n" + e,
        ]
        for assembly in invalid:
            with self.subTest(assembly=assembly):
                self.assertIsNone(deterministic_local_draft(assembly, symbol="caller", declarations=self.declarations(assembly)))
        # Unnamed declarations now declare with positional names, so the
        # arity case below carries the ABI-mismatch refusal instead.
        for text in (b"void add_value(unsigned int value);", b"int add_value(int x, int y);",
                     b"int add_value(int x); int add_value(unsigned int x);", b"int add_value(void* p);"):
            from automation.search_source_context import renderer_declarations
            facts = renderer_declarations(self.declarations(good), good.encode(), text)
            self.assertIsNone(deterministic_local_draft(good, symbol="caller", declarations=facts))


class LeafControlFlowTests(unittest.TestCase):
    def test_compiled_leaf_behavior_includes_delay_slots_and_word_boundaries(self):
        compiler = shutil.which("gcc")
        if compiler is None:
            self.skipTest("host fixture compiler unavailable")
        cases = {
            "select_value": (
                "bne $a0, $zero, .Lnonzero\naddiu $v0, $a1, 1\njr $ra\nnop\n.Lnonzero:\njr $ra\nsubu $v0, $zero, $v0\n",
                lambda x, y: -(y + 1) if x else y + 1),
            "old_predicate": (
                "beq $a0, $zero, .Lzero\naddiu $a0, $a0, 1\nmove $v0, $a0\njr $ra\nnop\n.Lzero:\njr $ra\naddiu $v0, $a0, 7\n",
                lambda x, y: 8 if x == 0 else x + 1),
            "absolute_word": (
                "slti $t0, $a0, 0\nbeqz $t0, .Lpositive\nnop\nsubu $v0, $zero, $a0\nb .Ljoin\nnop\n.Lpositive:\nmove $v0, $a0\n.Ljoin:\njr $ra\nnop\n",
                lambda x, y: -x if x & 0x80000000 else x),
            "shift_word": (
                "sra $t0, $a0, 3\nxori $t0, $t0, 170\nsll $v0, $t0, 1\njr $ra\naddiu $v0, $v0, -1\n",
                lambda x, y: (((ctypes.c_int32(x).value >> 3) ^ 170) << 1) - 1),
            "unsigned_compare": (
                "sltiu $v0, $a0, -1\njr $ra\nnop\n",
                lambda x, y: int(x < 0xFFFFFFFF)),
            "constant_wrap": (
                "li $t0, 2147483647\naddiu $t0, $t0, 1\nsll $v0, $t0, 1\njr $ra\naddiu $v0, $v0, -1\n",
                lambda x, y: 0xFFFFFFFF),
        }
        declarations = {"return_type": "unsigned int", "parameters": [
            {"type": "unsigned int", "name": "value"}, {"type": "unsigned int", "name": "other"}]}
        sources = []
        for name, (assembly, _) in cases.items():
            draft = deterministic_local_draft(assembly, symbol=name, declarations=declarations)
            self.assertIsNotNone(draft, name)
            self.assertNotIn("$", draft)
            self.assertNotIn(".L", draft)
            sources.append(draft)
        with tempfile.TemporaryDirectory() as directory:
            source, library = Path(directory) / "leaf.c", Path(directory) / "leaf.so"
            source.write_text("\n".join(sources))
            result = subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC", str(source), "-o", str(library)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            compiled = ctypes.CDLL(str(library))
            for name, (_, expected) in cases.items():
                function = getattr(compiled, name)
                function.argtypes, function.restype = [ctypes.c_uint32, ctypes.c_uint32], ctypes.c_uint32
                for x in (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
                    for y in (0, 1, 0x7FFFFFFF, 0xFFFFFFFF):
                        self.assertEqual(function(x, y), expected(x, y) & 0xFFFFFFFF, (name, x, y))

    def test_refuses_incomplete_or_unsafe_leaf_control_flow(self):
        invalid = (
            "li $v0, 1\njr $ra",  # missing slot
            "li $v0, 1\njr $ra\nnop\nli $v0, 2",  # code after return
            ".Lloop:\nb .Lloop\nnop",  # loop
            "b .Lmissing\nnop\nli $v0, 1\njr $ra\nnop",  # absent label
            "b .Lslot\n.Lslot:\nli $v0, 1\njr $ra\nnop",  # slot entry
            "b .Ldone\njr $ra\n.Ldone:\njr $ra\nnop",  # branch in slot
            "li $v0, 1\njal helper\nnop\njr $ra\nnop",
            "lw $v0, 0($a0)\njr $ra\nnop",
            "move $v0, $t0\njr $ra\nnop",  # undefined value
            "li $v0, 1\n.Lsame:\nnop\n.Lsame:\njr $ra\nnop",
            "li $v0, 1\n.Lalias:\n.Lother:\njr $ra\nnop",
            "li $v0, 1\nnop\n",  # missing return
            "li $v0, 1\nsll $v0, $v0, 32\njr $ra\nnop",
        )
        for assembly in invalid:
            with self.subTest(assembly=assembly):
                self.assertIsNone(deterministic_local_draft(assembly, symbol="bad"))
        self.assertIsNone(deterministic_local_draft("move $v0, $a0\njr $ra\nnop", symbol="wide", declarations={"parameters": [{"type": "double", "name": "value"}]}))

    def test_branch_draft_is_not_reduced_to_one_synthesis_expression(self):
        from automation.search_provider_factory import prepare_provider_inputs
        assembly = b"li $t0, 1\nbeqz $t0, .Lzero\nnop\nli $v0, 7\njr $ra\nnop\n.Lzero:\nli $v0, 9\njr $ra\nnop\n"
        prepared = prepare_provider_inputs(Path.cwd(), ("bounded_synthesis",), {RECIPIENT_ID: (assembly, b"obj")}, {})
        self.assertIn("if (", prepared[RECIPIENT_ID]["seed"])
        self.assertEqual(prepared[RECIPIENT_ID]["expressions"], ())


class TargetRendererTests(unittest.TestCase):
    def test_rendering_is_deterministic_and_target_derived(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            first = render_target_candidate(
                manifest,
                target_index,
                _recipient(),
                (_claim(),),
                lane="multi_donor",
            )
            second = render_target_candidate(
                manifest,
                target_index,
                _recipient(),
                (_claim(),),
                lane="multi_donor",
            )
            self.assertIsInstance(first, LaneCandidate)
            self.assertEqual(first.to_dict(), second.to_dict())
            self.assertIn("return 7;", first.source)
            self.assertNotIn("artifacts/donor.s", first.source)
        finally:
            temp.cleanup()

    def test_donor_evidence_and_unarchived_source_cannot_reach_renderer(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            with self.assertRaises(TargetRendererInputError):
                render_target_candidate(
                    manifest,
                    target_index,
                    _recipient(),
                    (DonorEvidence(
                        donor_id="hd:ST:fn",
                        recipient_id=RECIPIENT_ID,
                        version="hd",
                        source="donor.c",
                        match_kind="instruction_shape",
                        signature="sig:fn",
                    ),),
                )
            unarchived = {
                "records": [
                    {
                        "record_id": RECIPIENT_ID,
                        "target_identity": target_index.records[0].target_identity,
                        "target_evidence": {
                            "record_id": RECIPIENT_ID,
                            "assembly": {
                                "path": "asm/us/st/fn.s",
                                "text": TARGET_ASM.decode(),
                            },
                        },
                    }
                ]
            }
            with self.assertRaises(TargetRendererInputError):
                render_target_candidate(
                    manifest, unarchived, _recipient(), (_claim(),)
                )
        finally:
            temp.cleanup()

    def test_forbidden_semantic_provenance_cannot_reach_renderer(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            base_claim = _claim()
            forged_declarations = {"register": "a0"}
            forged = replace(
                base_claim,
                declarations=forged_declarations,
                claim_identity=hash_canonical(
                    {
                        **base_claim.identity_payload(),
                        "declarations": forged_declarations,
                    }
                ),
            )
            with self.assertRaises(TargetRendererInputError):
                render_target_candidate(
                    manifest,
                    target_index,
                    _recipient(),
                    (forged,),
                )
            parameter_declarations = {
                    "return_type": "int",
                    "parameters": [{"type": "int", "name": "a0"}],
            }
            forged_parameter = replace(
                base_claim,
                declarations=parameter_declarations,
                claim_identity=hash_canonical(
                    {
                        **base_claim.identity_payload(),
                        "declarations": parameter_declarations,
                    }
                ),
            )
            with self.assertRaises(TargetRendererInputError):
                render_target_candidate(
                    manifest,
                    target_index,
                    _recipient(),
                    (forged_parameter,),
                )
        finally:
            temp.cleanup()

    def test_complex_target_returns_typed_unsupported_context(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture(
            b"fn:\n\tbeq $a0, $zero, .Ldone\n\t nop\n.Ldone:\n\tjr $ra\n\t nop\n"
        )
        try:
            refusal = render_target_candidate(
                manifest, target_index, _recipient(), (_claim(),)
            )
            self.assertIsInstance(refusal, TargetContextUnsupported)
            self.assertEqual(refusal.refusal_code, "target_context_unsupported")
            self.assertEqual(refusal.query.recipient_id, RECIPIENT_ID)
            self.assertIn(refusal.query.query_identity, refusal.input_identities)
            self.assertTrue(refusal.provenance)
            self.assertEqual(refusal.provenance[0]["recipient_id"], RECIPIENT_ID)
            self.assertEqual(refusal.provenance[0]["lane"], "multi_donor")
            self.assertEqual(
                refusal.provenance[0]["claim_identities"],
                [claim.claim_identity for claim in (_claim(),)],
            )
        finally:
            temp.cleanup()

    def test_mips_dispatch_and_delay_slot_entry_remain_typed_refusals(self):
        # Bounds alone do not prove an indirect table's targets or supported C
        # lowering. Entering a delay slot also bypasses ordinary branch rules.
        cases = {
            "bounded_indirect_dispatch": (
                b"sltiu $t0, $a0, 2\nbeq $t0, $zero, .Ldefault\nnop\n"
                b"sll $t1, $a0, 2\naddu $t1, $a1, $t1\n"
                b"lw $t2, 0($t1)\nnop\njr $t2\nnop\n"
                b".Ldefault:\njr $ra\nli $v0, 3\n"
            ),
            "delay_slot_entry": (
                b"b .Lslot\nnop\nbeqz $a0, .Ldone\n"
                b".Lslot:\nli $v0, 7\n.Ldone:\njr $ra\nnop\n"
            ),
            "merge_load_pair": (
                b"lwl $v0, 3($a1)\nlwr $v0, 0($a1)\nnop\njr $ra\nnop\n"
            ),
        }
        context = b"int fn(unsigned int index, unsigned int* table);\n"
        for name, assembly in cases.items():
            with self.subTest(case=name):
                temp, _archive, manifest, target_index = _target_fixture(
                    assembly, context_bytes=context,
                )
                try:
                    result = render_target_candidate(
                        manifest, target_index, _recipient(), (_claim(),),
                        lane="cfg_dataflow",
                    )
                    self.assertIsInstance(result, TargetContextUnsupported)
                    self.assertEqual(result.refusal_code, "target_context_unsupported")
                    self.assertEqual(result.recipient_id, RECIPIENT_ID)
                    self.assertIn(hash_bytes(assembly), result.input_identities)
                    self.assertEqual(result.provenance[0]["lane"], "cfg_dataflow")
                    self.assertEqual(result.provenance[0]["source_identity"], hash_bytes(assembly))
                    self.assertEqual(result.provenance[0]["claim_identities"], [_claim().claim_identity])
                finally:
                    temp.cleanup()

        # The same archive path must still emit an ordinary forward branch.
        # Otherwise missing context could explain all the refusals above.
        assembly = (
            b"beqz $a0, .Lzero\nli $v0, 11\njr $ra\nnop\n"
            b".Lzero:\njr $ra\nli $v0, 7\n"
        )
        temp, _archive, manifest, target_index = _target_fixture(
            assembly, context_bytes=context,
        )
        try:
            result = render_target_candidate(
                manifest, target_index, _recipient(), (_claim(),), lane="cfg_dataflow",
            )
            self.assertIsInstance(result, LaneCandidate)
            self.assertEqual(result.record.recipient_id, RECIPIENT_ID)
            self.assertEqual(result.provenance[0]["source_identity"], hash_bytes(assembly))
        finally:
            temp.cleanup()

    def test_forbidden_branch_displacement_is_typed_unsupported_context(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture(
            b"beq $a0, $zero, 4\n"
            b"jr $ra\n"
            b"nop\n"
        )
        try:
            refusal = render_target_candidate(
                manifest, target_index, _recipient(), (_claim(),), lane="cfg_dataflow"
            )
            self.assertIsInstance(refusal, TargetContextUnsupported)
            self.assertEqual(refusal.refusal_code, "target_context_unsupported")
            self.assertEqual(refusal.provenance[0]["lane"], "cfg_dataflow")
        finally:
            temp.cleanup()




class ApiPointerCallTests(unittest.TestCase):
    API_ASM = (
        "addiu $sp, $sp, -24\n"
        "sw $ra, 20($sp)\n"
        "sw $s0, 16($sp)\n"
        "lui $v0, %hi(g_api_TestCall)\n"
        "lw $v0, %lo(g_api_TestCall)($v0)\n"
        "nop\n"
        "ori $a0, $zero, 4\n"
        "jalr $v0\n"
        "ori $a1, $zero, 1\n"
        "lw $ra, 20($sp)\n"
        "lw $s0, 16($sp)\n"
        "jr $ra\n"
        "addiu $sp, $sp, 24\n"
    )
    API_DECLS = {
        "return_type": "void",
        "parameters": [],
        "api_declarations": {
            "g_api_TestCall": {
                "return_type": "void",
                "parameters": [
                    {"type": "s32", "name": "x"},
                    {"type": "s32", "name": "y"}],
                "status": "declared",
            },
        },
    }

    def test_api_relocation_is_supported_shape(self):
        instructions = _parse_assembly(self.API_ASM)
        self.assertTrue(instructions)
        self.assertFalse(any(item.unsupported for item in instructions))
        other = _parse_assembly("lui $v0, %hi(other_symbol)\n")
        self.assertTrue(any(item.unsupported for item in other))

    def test_api_call_renders_pointer_call(self):
        source = deterministic_local_draft(
            self.API_ASM, symbol="fn", declarations=self.API_DECLS)
        self.assertIsNotNone(source)
        self.assertIn("g_api_TestCall(", source)
        self.assertIn("extern void (*g_api_TestCall)(s32, s32);", source)
        self.assertNotIn("%hi", source)
        self.assertNotIn("jalr", source)

    def test_api_call_refusals(self):
        cases = {}
        missing = dict(self.API_DECLS)
        missing["api_declarations"] = {}
        cases["missing_table"] = (self.API_ASM, missing)
        undeclared = {
            "return_type": "void", "parameters": [],
            "api_declarations": {
                "g_api_TestCall": {"status": "declaration_missing"}}}
        cases["undeclared"] = (self.API_ASM, undeclared)
        unpaired = self.API_ASM.replace(
            "lw $v0, %lo(g_api_TestCall)($v0)",
            "lw $v0, %lo(g_api_TestCall)($at)")
        cases["unpaired_halves"] = (unpaired, self.API_DECLS)
        clobbered = self.API_ASM.replace(
            "nop\nori $a0", "or $v0, $zero, $zero\nnop\nori $a0")
        cases["clobbered_hi"] = (clobbered, self.API_DECLS)
        noframe = "\n".join(
            line for line in self.API_ASM.splitlines()
            if "addiu $sp" not in line and "sw $ra" not in line
            and "lw $ra" not in line).replace(
            "jr $ra\n", "jr $ra\n")
        cases["missing_frame"] = (noframe, self.API_DECLS)
        data_ptr = {
            "return_type": "void", "parameters": [],
            "api_declarations": {
                "g_api_TestCall": {"status": "unsupported_declaration"}}}
        cases["data_pointer"] = (self.API_ASM, data_ptr)
        for name, (assembly, declarations) in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(
                    deterministic_local_draft(
                        assembly, symbol="fn", declarations=declarations))

    def test_dominant_alloc_primitives_shape_renders(self):
        assembly = (
            "addiu $sp, $sp, -24\nsw $ra, 20($sp)\nsw $s0, 16($sp)\n"
            "lui $v0, %hi(g_api_AllocPrimitives)\n"
            "lw $v0, %lo(g_api_AllocPrimitives)($v0)\n"
            "nop\nori $a0, $zero, 4\njalr $v0\nori $a1, $zero, 1\n"
            "sll $v0, $v0, 16\nsra $v0, $v0, 16\n"
            "lw $ra, 20($sp)\nlw $s0, 16($sp)\njr $ra\naddiu $sp, $sp, 24\n"
        )
        declarations = {
            "return_type": "void", "parameters": [],
            "api_declarations": {
                "g_api_AllocPrimitives": {
                    "return_type": "s16",
                    "parameters": [
                        {"type": "PrimitiveType", "name": "type"},
                        {"type": "s32", "name": "count"}],
                    "status": "declared",
                },
            },
        }
        source = deterministic_local_draft(assembly, symbol="fn", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertIn("g_api_AllocPrimitives(", source)
        self.assertIn("extern s16 (*g_api_AllocPrimitives)(PrimitiveType, s32);", source)

    def test_unnamed_api_parameters_render_types_only(self):
        assembly = self.API_ASM.replace("g_api_TestCall", "g_api_FreePrimitives")
        declarations = {
            "return_type": "void", "parameters": [],
            "api_declarations": {
                "g_api_FreePrimitives": {
                    "return_type": "void",
                    "parameters": [{"type": "s32", "name": "arg0"}],
                    "status": "declared",
                },
            },
        }
        source = deterministic_local_draft(assembly, symbol="fn", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertIn("g_api_FreePrimitives(", source)

    def test_plain_jalr_without_api_remains_refusal(self):
        assembly = (
            "addiu $sp, $sp, -24\nsw $ra, 20($sp)\n"
            "addu $v0, $a0, $zero\nnop\n"
            "jalr $v0\nnop\n"
            "lw $ra, 20($sp)\njr $ra\naddiu $sp, $sp, 24\n"
        )
        self.assertIsNone(deterministic_local_draft(
            assembly, symbol="fn", declarations=self.API_DECLS))


class DataAddressTests(unittest.TestCase):
    DATA_ASM = (
        "lui $v0, %hi(D_us_1)\n"
        "addiu $v0, $v0, %lo(D_us_1)\n"
        "jr $ra\n"
        "nop\n"
    )
    CONTEXT = b"typedef signed short s16;\nextern s16 D_us_1[4];\n"

    def _decls(self, **override):
        from automation.search_target_layout import pointer_layouts
        layouts = pointer_layouts(self.CONTEXT, ["s16*"])
        self.assertIn("s16*", layouts)
        base = {
            "return_type": "s16*",
            "parameters": [],
            "pointer_layouts": layouts,
            "data_declarations": {
                "D_us_1": {"type": "s16", "dims": "[4]", "status": "declared"},
            },
        }
        base.update(override)
        return base

    def test_data_relocation_is_supported_shape(self):
        instructions = _parse_assembly(self.DATA_ASM)
        self.assertTrue(instructions)
        self.assertFalse(any(item.unsupported for item in instructions))
        other = _parse_assembly("lui $v0, %hi(other_symbol)\n")
        self.assertTrue(any(item.unsupported for item in other))

    def test_data_address_renders_extern_and_return(self):
        source = deterministic_local_draft(
            self.DATA_ASM, symbol="fn", declarations=self._decls())
        self.assertIsNotNone(source)
        self.assertIn("extern s16 D_us_1[4];", source)
        self.assertIn("return D_us_1;", source)
        self.assertNotIn("%hi", source)
        self.assertNotIn("%lo", source)

    def test_data_address_refusals(self):
        cases = {}
        cases["missing_table"] = (self.DATA_ASM, {
            "return_type": "s16*", "parameters": [],
            "pointer_layouts": self._decls()["pointer_layouts"]})
        cases["undeclared"] = (self.DATA_ASM, self._decls(
            data_declarations={"D_us_1": {"status": "declaration_missing"}}))
        unpaired = self.DATA_ASM.replace("%lo(D_us_1)", "%lo(D_us_2)")
        cases["unpaired_halves"] = (unpaired, self._decls())
        clobbered = self.DATA_ASM.replace(
            "addiu $v0", "or $v0, $zero, $zero\naddiu $v0", 1)
        cases["clobbered_hi"] = (clobbered, self._decls())
        scalar_context = b"typedef signed short s16;\nextern s16 D_us_1;\n"
        from automation.search_target_layout import pointer_layouts as _layouts
        scalar_layouts = _layouts(scalar_context, ["s16*"])
        cases["scalar_address_of"] = (
            self.DATA_ASM, {
                "return_type": "s16*", "parameters": [],
                "pointer_layouts": scalar_layouts,
                "data_declarations": {
                    "D_us_1": {"type": "s16", "dims": "", "status": "declared"}},
            })
        for name, (assembly, declarations) in cases.items():
            with self.subTest(case=name):
                if name == "scalar_address_of":
                    rendered = deterministic_local_draft(
                        assembly, symbol="fn", declarations=declarations)
                    self.assertIsNotNone(rendered)
                    self.assertIn("extern s16 D_us_1;", rendered)
                    self.assertIn("return (&D_us_1);", rendered)
                else:
                    self.assertIsNone(deterministic_local_draft(
                        assembly, symbol="fn", declarations=declarations))




class GlobalAddressTests(unittest.TestCase):
    GLOBAL_ASM = (
        "lui $v0, %hi(g_Buf)\n"
        "addiu $v0, $v0, %lo(g_Buf)\n"
        "jr $ra\n"
        "nop\n"
    )
    CONTEXT = b"typedef struct { int x; int y; } Buf;\nextern Buf g_Buf[4];\n"

    def _decls(self, **override):
        from automation.search_target_layout import pointer_layouts
        layouts = pointer_layouts(self.CONTEXT, ["Buf*"])
        self.assertIn("Buf*", layouts)
        base = {
            "return_type": "Buf*",
            "parameters": [],
            "pointer_layouts": layouts,
            "global_declarations": {
                "g_Buf": {"type": "Buf", "dims": "[4]", "status": "declared"},
            },
        }
        base.update(override)
        return base

    def test_global_relocation_is_supported_shape(self):
        instructions = _parse_assembly(self.GLOBAL_ASM)
        self.assertTrue(instructions)
        self.assertFalse(any(item.unsupported for item in instructions))
        other = _parse_assembly("lui $v0, %hi(other_symbol)\n")
        self.assertTrue(any(item.unsupported for item in other))

    def test_global_address_renders_extern_and_return(self):
        source = deterministic_local_draft(
            self.GLOBAL_ASM, symbol="fn", declarations=self._decls())
        self.assertIsNotNone(source)
        self.assertIn("extern Buf g_Buf[4];", source)
        self.assertIn("return g_Buf;", source)
        self.assertNotIn("%hi", source)
        self.assertNotIn("%lo", source)

    def test_global_address_refusals(self):
        cases = {}
        cases["missing_table"] = (self.GLOBAL_ASM, {
            "return_type": "Buf*", "parameters": [],
            "pointer_layouts": self._decls()["pointer_layouts"]})
        cases["undeclared"] = (self.GLOBAL_ASM, self._decls(
            global_declarations={"g_Buf": {"status": "declaration_missing"}}))
        unpaired = self.GLOBAL_ASM.replace("%lo(g_Buf)", "%lo(g_Other)")
        cases["unpaired_halves"] = (unpaired, self._decls())
        for name, (assembly, declarations) in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(deterministic_local_draft(
                    assembly, symbol="fn", declarations=declarations))



class LinkerAbsoluteTests(unittest.TestCase):
    LINKER_ASM = (
        "lui $v0, %hi(PLAYER_posX_i_hi)\n"
        "lhu $v0, %lo(PLAYER_posX_i_hi)($v0)\n"
        "jr $ra\n"
        "nop\n"
    )

    def test_linker_scalar_load_derives_width_extern(self):
        source = deterministic_local_draft(
            self.LINKER_ASM, symbol="fn",
            declarations={"return_type": "unsigned int", "parameters": []})
        self.assertIsNotNone(source)
        self.assertIn("extern u16 PLAYER_posX_i_hi;", source)
        self.assertIn("PLAYER_posX_i_hi", source)
        self.assertNotIn("%hi", source)

    def test_linker_refusals(self):
        store = self.LINKER_ASM.replace("lhu $v0,", "sh $v0,")
        self.assertIsNone(deterministic_local_draft(
            store, symbol="fn",
            declarations={"return_type": "unsigned int", "parameters": []}))
        unpaired = self.LINKER_ASM.replace("%lo(PLAYER_posX_i_hi)", "%lo(PLAYER_posY_i_hi)")
        self.assertIsNone(deterministic_local_draft(
            unpaired, symbol="fn",
            declarations={"return_type": "unsigned int", "parameters": []}))
        conflict = (
            "lui $v0, %hi(PLAYER_posX_i_hi)\n"
            "lhu $v0, %lo(PLAYER_posX_i_hi)($v0)\n"
            "nop\n"
            "lui $v1, %hi(PLAYER_posX_i_hi)\n"
            "lb $v1, %lo(PLAYER_posX_i_hi)($v1)\n"
            "addu $v0, $v0, $v1\n"
            "jr $ra\n"
            "nop\n"
        )
        self.assertIsNone(deterministic_local_draft(
            conflict, symbol="fn",
            declarations={"return_type": "unsigned int", "parameters": []}))

    def test_linker_declared_address_renders(self):
        from automation.search_target_layout import pointer_layouts
        context = b"typedef unsigned short u16;\nextern u16 RIC_step;\n"
        layouts = pointer_layouts(context, ["u16*"])
        self.assertIn("u16*", layouts)
        assembly = (
            "lui $v0, %hi(RIC_step)\n"
            "addiu $v0, $v0, %lo(RIC_step)\n"
            "jr $ra\n"
            "nop\n"
        )
        declarations = {
            "return_type": "u16*", "parameters": [],
            "pointer_layouts": layouts,
            "linker_declarations": {
                "RIC_step": {"type": "u16", "dims": "", "status": "declared"}},
        }
        source = deterministic_local_draft(assembly, symbol="fn", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertIn("extern u16 RIC_step;", source)
        self.assertIn("return (&RIC_step);", source)


class GlobalOffsetTests(unittest.TestCase):
    CONTEXT = b"typedef unsigned char u8;\nextern u8 g_CastleFlags[768];\n"

    def _decls(self):
        from automation.search_target_layout import pointer_layouts
        layouts = pointer_layouts(self.CONTEXT, ["u8*"])
        self.assertIn("u8*", layouts)
        self.assertEqual(layouts["u8*"]["size"], 1)
        return {
            "return_type": "unsigned int", "parameters": [],
            "pointer_layouts": layouts,
            "global_declarations": {
                "g_CastleFlags": {"type": "u8", "dims": "[768]", "status": "declared"}},
        }

    def test_offset_address_renders_pointer_plus_index(self):
        assembly = (
            "lui $v0, %hi(g_CastleFlags + 0x20)\n"
            "addiu $v0, $v0, %lo(g_CastleFlags + 0x20)\n"
            "jr $ra\n"
            "nop\n"
        )
        source = deterministic_local_draft(assembly, symbol="fn", declarations={
            "return_type": "u8*", "parameters": [],
            "pointer_layouts": self._decls()["pointer_layouts"],
            "global_declarations": self._decls()["global_declarations"]})
        self.assertIsNotNone(source)
        self.assertIn("extern u8 g_CastleFlags[768];", source)
        self.assertIn("g_CastleFlags", source)
        self.assertNotIn("%hi", source)

    def test_offset_byte_load_renders_index(self):
        assembly = (
            "lui $v0, %hi(g_CastleFlags + 0x20)\n"
            "lbu $v0, %lo(g_CastleFlags + 0x20)($v0)\n"
            "jr $ra\n"
            "nop\n"
        )
        source = deterministic_local_draft(assembly, symbol="fn", declarations=self._decls())
        self.assertIsNotNone(source)
        self.assertIn("g_CastleFlags[32]", source)

    def test_offset_refusals(self):
        wide = (
            "lui $v0, %hi(g_CastleFlags + 0x20)\n"
            "lw $v0, %lo(g_CastleFlags + 0x20)($v0)\n"
            "jr $ra\n"
            "nop\n"
        )
        self.assertIsNone(deterministic_local_draft(wide, symbol="fn", declarations=self._decls()))
        store = (
            "lui $v0, %hi(g_CastleFlags + 0x20)\n"
            "sb $a0, %lo(g_CastleFlags + 0x20)($v0)\n"
            "jr $ra\n"
            "nop\n"
        )
        self.assertIsNone(deterministic_local_draft(store, symbol="fn", declarations=self._decls()))
        unpaired = (
            "lui $v0, %hi(g_CastleFlags + 0x20)\n"
            "lbu $v0, %lo(g_CastleFlags + 0x21)($v0)\n"
            "jr $ra\n"
            "nop\n"
        )
        self.assertIsNone(deterministic_local_draft(unpaired, symbol="fn", declarations=self._decls()))


class LoopRegionTests(unittest.TestCase):
    DO_WHILE = ("li $v0, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                "bne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")

    def _regions(self, assembly):
        return loop_regions(_parse_assembly(assembly))

    def test_straight_code_has_no_regions(self):
        admitted, refused = self._regions("addu $v0, $a0, $a1\njr $ra\nnop\n")
        self.assertEqual((admitted, refused), ([], []))

    def test_do_while_admits_one_region(self):
        admitted, refused = self._regions(self.DO_WHILE)
        self.assertEqual(refused, [])
        self.assertEqual(len(admitted), 1)
        region = admitted[0]
        self.assertLess(region["start"], region["branch"])
        self.assertEqual(region["slot"], region["branch"] + 1)

    def test_while_forms_admit_with_kind_and_exit(self):
        while_latch = (".Ltop:\naddiu $v0, $v0, 1\n"
                       "beq $v0, $a0, .Lexit\nnop\n"
                       "b .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        admitted, refused = self._regions(while_latch)
        self.assertEqual(refused, [])
        self.assertEqual([(region["kind"], region["exit"]) for region in admitted], [("while", 1)])
        do_break = (".Ltop:\naddiu $v0, $v0, 1\n"
                    "beq $v0, $a1, .Lexit\nnop\n"
                    "addiu $v1, $v1, 1\nbne $v0, $a0, .Ltop\nnop\n"
                    ".Lexit:\njr $ra\nnop\n")
        admitted, refused = self._regions(do_break)
        self.assertEqual(refused, [])
        self.assertEqual([(region["kind"], region["exit"]) for region in admitted], [("do-break", 1)])
        spin = "bne $v0, $a0, .Ls\n.Ls:\nnop\njr $ra\nnop\n"
        self.assertEqual(self._regions(spin), ([], ["delay-entry"]))
        no_exit = ".Ltop:\naddiu $v0, $v0, 1\nb .Ltop\nnop\njr $ra\nnop\n"
        self.assertEqual(self._regions(no_exit), ([], ["while-no-exit"]))
        multi_exit = (".Ltop:\naddiu $v0, $v0, 1\n"
                      "beq $v0, $a1, .Lexit\nnop\n"
                      "beq $v0, $a2, .Lexit\nnop\n"
                      "b .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        admitted, refused = self._regions(multi_exit)
        self.assertEqual(refused, [])
        self.assertEqual(
            [(region["kind"], region["exit"], region["exits"]) for region in admitted],
            [("while", 1, [1, 3])])

    def test_multi_exit_shared_continuation_admits(self):
        multi = (".Ltop:\naddiu $v0, $v0, 1\n"
                 "beq $v0, $a1, .Lexit\nnop\n"
                 "beq $v0, $a2, .Lexit\nnop\n"
                 "bne $v0, $a0, .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        admitted, refused = self._regions(multi)
        self.assertEqual(refused, [])
        self.assertEqual(len(admitted), 1)
        self.assertEqual(admitted[0]["kind"], "do-break")
        self.assertEqual(admitted[0]["exits"], [1, 3])
        self.assertEqual(admitted[0]["exit"], 1)

    def test_multi_exit_split_continuation_refuses(self):
        split = (".Ltop:\naddiu $v0, $v0, 1\n"
                 "beq $v0, $a1, .Lexit\nnop\n"
                 "beq $v0, $a2, .Lfar\nnop\n"
                 "bne $v0, $a0, .Ltop\nnop\n.Lexit:\naddiu $v1, $v1, 1\n"
                 ".Lfar:\njr $ra\nnop\n")
        self.assertEqual(self._regions(split), ([], ["multi-exit"]))

    def test_multi_exit_shared_nonlocal_refuses(self):
        far = (".Ltop:\naddiu $v0, $v0, 1\n"
               "beq $v0, $a1, .Lfar\nnop\n"
               "beq $v0, $a2, .Lfar\nnop\n"
               "bne $v0, $a0, .Ltop\nnop\naddiu $v1, $v1, 1\n"
               ".Lfar:\njr $ra\nnop\n")
        self.assertEqual(self._regions(far)[1], ["nonlocal-exit"])

    def test_multi_exit_with_join_stays_refused(self):
        join_multi = (".Ltop:\naddiu $v0, $v0, 1\n"
                      "beq $v0, $a1, .Lskip\nnop\n.Lskip:\n"
                      "beq $v0, $a2, .Lexit\nnop\n"
                      "beq $v0, $a3, .Lexit\nnop\n"
                      "bne $v0, $a0, .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        self.assertEqual(self._regions(join_multi)[1], ["branch-in-loop"])

    def test_inner_control_and_outside_entry_refuse(self):
        bare_join = (".Ltop:\naddiu $v0, $v0, 1\n"
                     "beq $v0, $a1, .Lskip\nnop\n.Lskip:\n"
                     "bne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")
        admitted, refused = self._regions(bare_join)
        self.assertEqual(refused, [])
        self.assertEqual(len(admitted), 1)
        jump_out = (".Ltop:\naddiu $v0, $v0, 1\n"
                    "b .Lfar\nnop\naddiu $v1, $v1, 1\n"
                    "bne $v0, $a0, .Ltop\nnop\n.Lfar:\njr $ra\nnop\n")
        self.assertEqual(self._regions(jump_out)[1], ["branch-in-loop"])
        entry = ("beq $a0, $zero, .Ltop\nnop\n"
                 "addiu $v0, $zero, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                 "bne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")
        self.assertEqual(self._regions(entry)[1], ["outside-entry"])

    def test_disjoint_regions_admit_and_shared_slot_refuses_entry(self):
        two = (".La:\naddiu $v0, $v0, 1\n"
               "bne $v0, $a0, .La\nnop\n"
               ".Lb:\naddiu $v1, $v1, 1\n"
               "bne $v1, $a1, .Lb\nnop\njr $ra\nnop\n")
        admitted, refused = self._regions(two)
        self.assertEqual(refused, [])
        self.assertEqual(len(admitted), 2)
        mid = ("beq $a1, $zero, .Lmid\nnop\n.La:\naddiu $v0, $v0, 1\n"
               ".Lmid:\naddiu $v1, $v1, 1\n"
               "bne $v0, $a0, .La\nnop\njr $ra\nnop\n")
        self.assertEqual(self._regions(mid), ([], ["outside-entry"]))

    def test_barred_ops_and_delay_control_refuse(self):
        mult = (".Ltop:\nmult $v0, $a0\naddiu $v0, $v0, 1\n"
                "bne $v0, $a1, .Ltop\nnop\njr $ra\nnop\n")
        self.assertEqual(self._regions(mult)[1], ["barred-op"])
        call = (".Ltop:\njal TestCallee\nnop\naddiu $v0, $v0, 1\n"
                "bne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")
        self.assertEqual(self._regions(call)[1], ["call-in-loop"])
        nested_loop = (".Louter:\nnop\n.Linner:\naddiu $v0, $v0, 1\n"
                       "bne $v0, $a0, .Linner\nnop\n"
                       "addiu $v1, $v1, 1\n"
                       "bne $v1, $a1, .Louter\nnop\njr $ra\nnop\n")
        self.assertEqual(self._regions(nested_loop)[1], ["nested-loop"])
        slot_branch = (".Ltop:\naddiu $v0, $v0, 1\n"
                       "bne $v0, $a0, .Ltop\nbeq $zero, $zero, .Lfar\n"
                       "nop\n.Lfar:\njr $ra\nnop\n")

    def test_region_flow_tracks_order_and_fresh_loads(self):
        instructions = _parse_assembly(
            "li $v0, 5\nlw $v1, 0($a0)\nsw $v1, 0($a1)\n"
            "beq $v0, $v1, .Lx\nnop\n.Lx:\njr $ra\nnop\n")
        reads, writes, pure, read_first = region_flow(instructions, 0, 4)
        self.assertEqual(writes, {"v0", "v1"})
        self.assertEqual(reads, {"a0", "a1", "v0", "v1"})
        self.assertEqual(pure, {"v0"})
        self.assertEqual(read_first, {"a0", "a1"})
        li = region_flow(instructions, 0, 1)
        self.assertEqual(li, (set(), {"v0"}, {"v0"}, set()))
        self.assertEqual(region_flow(instructions, 4, 4), (set(), set(), set(), set()))
        self.assertEqual(region_flow(None, 0, 4), (set(), set(), set(), set()))

    def test_canonical_reg_matches_machine_spellings(self):
        self.assertEqual(_canonical_reg("$4"), "a0")
        self.assertEqual(_canonical_reg("$A0"), "a0")
        self.assertEqual(_canonical_reg("$r16"), "s0")
        self.assertEqual(_canonical_reg("$sp"), "sp")
        self.assertEqual(_canonical_reg("$zero"), "zero")


class LoopLoweringTests(unittest.TestCase):
    def assert_program(self, assembly, declarations, harness, context=b""):
        """Run independent expected behavior out of process so bad loops time out."""
        from automation.search_source_context import renderer_declarations
        compiler = shutil.which("gcc") or shutil.which("cc")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        facts = renderer_declarations(declarations, assembly.encode(), context)
        source = deterministic_local_draft(assembly, symbol="fn", declarations=facts)
        self.assertIsNotNone(source)
        with tempfile.TemporaryDirectory(prefix="loop-review-") as directory:
            root = Path(directory)
            (root / "fixture.c").write_text(context.decode() + source + harness)
            compiled = subprocess.run(
                [compiler, "-std=c89", "-O2", "-Wall", "-Werror",
                 str(root / "fixture.c"), "-o", str(root / "fixture")],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(compiled.returncode, 0, compiled.stderr + source)
            ran = subprocess.run([str(root / "fixture")], timeout=3)
            self.assertEqual(ran.returncode, 0, source)

    def test_latch_uses_pre_delay_value(self):
        assembly = ("li $v0, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                    "bne $v0, $a0, .Ltop\naddiu $v0, $v0, 1\n"
                    "jr $ra\nnop\n")
        self.assert_program(assembly, self.COUNTER_DECLS,
                            "int main(void) { return fn(3) != 4; }\n")

    def test_zero_trip_executes_exit_delay_slot(self):
        assembly = ("li $v0, 0\n.Ltop:\nbeqz $a0, .Lexit\n"
                    "addiu $v0, $v0, 1\naddiu $a0, $a0, -1\n"
                    "b .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        self.assert_program(assembly, self.COUNTER_DECLS,
                            "int main(void) { return fn(0) != 1 || fn(3) != 4; }\n")

    def test_while_preserves_live_out_without_in_loop_read(self):
        assembly = ("li $v0, 0\n.Ltop:\nbeqz $a0, .Lexit\nnop\n"
                    "li $v0, 7\naddiu $a0, $a0, -1\nb .Ltop\nnop\n"
                    ".Lexit:\njr $ra\nnop\n")
        self.assert_program(assembly, self.COUNTER_DECLS,
                            "int main(void) { return fn(0) != 0 || fn(3) != 7; }\n")

    def test_conditional_write_carries_previous_iteration(self):
        assembly = ("li $v0, 0\nli $v1, 0\nli $t1, 0\n.Ltop:\n"
                    "addiu $v1, $v1, 1\nandi $t0, $v1, 1\n"
                    "beqz $t0, .Ljoin\nnop\nmove $t1, $v1\n.Ljoin:\n"
                    "addu $v0, $v0, $t1\nbne $v1, $a0, .Ltop\nnop\n"
                    "jr $ra\nnop\n")
        self.assert_program(assembly, self.COUNTER_DECLS,
                            "int main(void) { return fn(4) != 8 || fn(6) != 18; }\n")

    def test_join_initialization_uses_this_iterations_load(self):
        assembly = ("li $v0, 0\n.Ltop:\nlw $t0, 0($a0)\nnop\n"
                    "beqz $t0, .Lskip\nnop\nli $t0, 7\n.Lskip:\n"
                    "addu $v0, $v0, $t0\naddiu $a0, $a0, 4\n"
                    "addiu $a1, $a1, -1\nbnez $a1, .Ltop\nnop\n"
                    "jr $ra\nnop\n")
        decls = {"return_type": "unsigned int", "parameters": [
            {"type": "unsigned int*", "name": "p"},
            {"type": "unsigned int", "name": "n"}]}
        self.assert_program(assembly, decls,
                            "int main(void) { unsigned int a[3] = {0, 1, 0}; return fn(a, 3) != 7; }\n")

    def test_loop_load_redefines_carried_value(self):
        assembly = ("li $v0, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                    "lw $v0, 0($a0)\naddiu $a0, $a0, 4\n"
                    "bnez $v0, .Ltop\nnop\njr $ra\nnop\n")
        decls = {"return_type": "unsigned int",
                 "parameters": [{"type": "unsigned int*", "name": "p"}]}
        self.assert_program(assembly, decls,
                            "int main(void) { unsigned int a[2] = {3, 0}; return fn(a) != 0; }\n")

    CALL_PREFIX = ("addiu $sp, $sp, -32\nsw $ra, 28($sp)\n"
                   "sw $s0, 24($sp)\nsw $s1, 20($sp)\n"
                   "move $s0, $a0\nli $s1, 0\n")
    CALL_SUFFIX = ("move $v0, $s1\nlw $s1, 20($sp)\nlw $s0, 24($sp)\n"
                   "lw $ra, 28($sp)\nnop\njr $ra\naddiu $sp, $sp, 32\n")

    def test_loop_calls_have_fresh_results_and_saved_carriers(self):
        for call, context in (
            ("jal callee\n", b"unsigned int callee(unsigned int n);\n"),
            ("lui $v0, %hi(g_api_Test)\nlw $v0, %lo(g_api_Test)($v0)\n"
             "nop\njalr $v0\n", b"unsigned int (*g_api_Test)(unsigned int n);\n"),
        ):
            with self.subTest(call=call):
                assembly = (self.CALL_PREFIX + ".Ltop:\n" + call +
                            "move $a0, $s0\naddu $s1, $s1, $v0\n"
                            "addiu $s0, $s0, -1\nbnez $s0, .Ltop\nnop\n" + self.CALL_SUFFIX)
                harness = ("static unsigned int calls;\n"
                           "unsigned int callee(unsigned int n) { ++calls; return n + calls; }\n")
                if "jalr" in call:
                    harness += "unsigned int (*g_api_Test)(unsigned int) = callee;\n"
                harness += "int main(void) { return fn(3) != 12 || calls != 3; }\n"
                self.assert_program(assembly, self.COUNTER_DECLS, harness, context)

    def test_loop_call_return_can_feed_the_next_iteration(self):
        assembly = (self.CALL_PREFIX + "li $v0, 0\n.Ltop:\nmove $a0, $v0\n"
                    "jal callee\nnop\naddiu $s0, $s0, -1\n"
                    "bnez $s0, .Ltop\nnop\nmove $s1, $v0\n" + self.CALL_SUFFIX)
        self.assert_program(assembly, self.COUNTER_DECLS,
                            "unsigned int callee(unsigned int n) { return n + 2; }\n"
                            "int main(void) { return fn(3) != 6; }\n",
                            b"unsigned int callee(unsigned int n);\n")

    def test_loop_call_archived_target_reconstruction(self):
        assembly = (self.CALL_PREFIX + ".Ltop:\njal callee\nmove $a0, $s0\n"
                    "addu $s1, $s1, $v0\naddiu $s0, $s0, -1\n"
                    "bnez $s0, .Ltop\nnop\n" + self.CALL_SUFFIX)
        context = b"unsigned int fn(unsigned int n);\nunsigned int callee(unsigned int n);\n"
        temp, archive, manifest, index = _target_fixture(assembly.encode(), context_bytes=context)
        try:
            candidate = render_target_candidate(manifest, index, _recipient(), (_claim(),), lane="cfg_dataflow")
            self.assertIsInstance(candidate, LaneCandidate)
            self.assertIn("callee(", candidate.source)
            self.assertIn("do {", candidate.source)
            replay = render_target_candidate(manifest, load_target_index(archive, manifest),
                                             _recipient(), (_claim(),), lane="cfg_dataflow")
            self.assertEqual(candidate, replay)
        finally:
            temp.cleanup()

    def test_conditional_void_call_and_zero_trip(self):
        assembly = (self.CALL_PREFIX + ".Ltop:\nbeqz $s0, .Lexit\nnop\n"
                    "andi $v0, $s0, 1\nbeqz $v0, .Lskip\nnop\n"
                    "jal callee\nmove $a0, $s0\n.Lskip:\n"
                    "addiu $s1, $s1, 1\naddiu $s0, $s0, -1\n"
                    "b .Ltop\nnop\n.Lexit:\n" + self.CALL_SUFFIX)
        self.assert_program(assembly, self.COUNTER_DECLS,
                            "static unsigned int sum;\n"
                            "void callee(unsigned int n) { sum += n; }\n"
                            "int main(void) { return fn(0) != 0 || sum != 0 || fn(4) != 4 || sum != 4; }\n",
                            b"void callee(unsigned int n);\n")

    MULTI_ASM = ("li $v0, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                 "beq $v0, $a1, .Lexit\nnop\n"
                 "beq $v0, $a2, .Lexit\nnop\n"
                 "bne $v0, $a0, .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
    MULTI_DECLS = {
        "return_type": "unsigned int",
        "parameters": [{"type": "unsigned int", "name": "limit"},
                       {"type": "unsigned int", "name": "stop1"},
                       {"type": "unsigned int", "name": "stop2"}],
    }

    def test_multi_break_renders_two_breaks(self):
        source = deterministic_local_draft(
            self.MULTI_ASM, symbol="fn", declarations=self.MULTI_DECLS)
        self.assertIsNotNone(source)
        self.assertEqual(source.count("break;"), 2)
        self.assertIn("do {", source)

    def test_multi_break_counts_with_either_limit(self):
        self.assert_program(
            self.MULTI_ASM, self.MULTI_DECLS,
            "int main(void) { return fn(5, 9, 9) != 5 || fn(9, 2, 9) != 2 || fn(9, 9, 4) != 4; }\n")

    def test_multi_break_while_form_counts(self):
        assembly = ("li $v0, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                    "beq $v0, $a1, .Lexit\nnop\n"
                    "beq $v0, $a2, .Lexit\nnop\n"
                    "b .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        self.assert_program(
            assembly, self.MULTI_DECLS,
            "int main(void) { return fn(9, 3, 9) != 3 || fn(9, 9, 2) != 2; }\n")

    def test_loop_call_refuses_clobbered_values_and_unsafe_frames(self):
        from automation.search_source_context import renderer_declarations
        context = b"unsigned int callee(unsigned int n);\n"
        safe = (self.CALL_PREFIX + ".Ltop:\njal callee\nmove $a0, $s0\n"
                "addiu $s0, $s0, -1\nbnez $s0, .Ltop\nnop\n" + self.CALL_SUFFIX)
        cases = {
            "undeclared": (safe, b""),
            "backedge_volatile": (safe.replace("move $a0, $s0", "nop"), context),
            "same_iteration_volatile": (safe.replace("addiu $s0, $s0, -1", "addu $s1, $s1, $a0\naddiu $s0, $s0, -1"), context),
            "frame": (safe.replace("-32", "-8").replace("28($sp)", "4($sp)"), context),
            "home_area": (safe.replace("sw $s0, 24($sp)", "sw $s0, 0($sp)").replace("lw $s0, 24($sp)", "lw $s0, 0($sp)"), context),
            "loop_stack_write": (safe.replace(".Ltop:\n", ".Ltop:\nsw $s1, 16($sp)\n"), context),
            "unbound_indirect": (safe.replace("jal callee", "jalr $s0"), context),
            "control_delay": (safe.replace("jal callee\nmove $a0, $s0", "jal callee\njal callee"), context),
        }
        for name, (assembly, declarations) in cases.items():
            with self.subTest(case=name):
                facts = renderer_declarations(self.COUNTER_DECLS, assembly.encode(), declarations)
                self.assertIsNone(deterministic_local_draft(assembly, symbol="fn", declarations=facts))

    def test_inner_branch_uses_predicate_before_slot_overwrite(self):
        assembly = ("li $v0, 0\nli $v1, 0\n.Ltop:\naddiu $v1, $v1, 1\n"
                    "andi $t0, $v1, 1\nbeqz $t0, .Lskip\nli $t0, 0\n"
                    "addiu $v0, $v0, 1\n.Lskip:\nbne $v1, $a0, .Ltop\nnop\n"
                    "jr $ra\nnop\n")
        self.assert_program(assembly, self.COUNTER_DECLS,
                            "int main(void) { return fn(6) != 3; }\n")

    def test_loop_exit_cannot_silently_skip_instructions(self):
        assembly = ("li $v0, 0\n.Ltop:\nbeqz $a0, .Lexit\nnop\n"
                    "addiu $a0, $a0, -1\nb .Ltop\nnop\n"
                    "li $v0, 99\n.Lexit:\njr $ra\nnop\n")
        self.assertIsNone(deterministic_local_draft(assembly, symbol="fn", declarations=self.COUNTER_DECLS))

    COUNTER_ASM = ("li $v0, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                   "bne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")
    COUNTER_DECLS = {
        "return_type": "unsigned int",
        "parameters": [{"type": "unsigned int", "name": "n"}],
    }

    def test_counter_loop_renders_do_while(self):
        source = deterministic_local_draft(
            self.COUNTER_ASM, symbol="fn", declarations=self.COUNTER_DECLS)
        self.assertIsNotNone(source)
        self.assertIn("do {", source)
        self.assertIn("while (", source)
        self.assertNotIn("%hi", source)
        self.assertNotIn("$", source)

    def test_counter_loop_counts_host_exact(self):
        compiler = shutil.which("gcc") or shutil.which("cc")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        source = deterministic_local_draft(
            self.COUNTER_ASM, symbol="count", declarations=self.COUNTER_DECLS)
        self.assertIsNotNone(source)
        with tempfile.TemporaryDirectory(prefix="loop-semantics-") as directory:
            root = Path(directory)
            (root / "count.c").write_text(source, encoding="utf-8")
            subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC",
                            str(root / "count.c"), "-o", str(root / "count.so")], check=True,
                           capture_output=True, text=True)
            function = ctypes.CDLL(str(root / "count.so")).count
            function.argtypes, function.restype = [ctypes.c_uint32], ctypes.c_uint32
            self.assertEqual(function(5), 5)
            self.assertEqual(function(1), 1)

    def test_sum_loop_walks_pointer(self):
        from automation.search_target_layout import pointer_layouts
        context = b"typedef signed short s16;\n"
        layouts = pointer_layouts(context, ["s16*"])
        self.assertIn("s16*", layouts)
        assembly = ("li $v0, 0\n.Ltop:\nlh $v1, 0($a0)\nnop\n"
                    "addu $v0, $v0, $v1\naddiu $a0, $a0, 2\n"
                    "addiu $a1, $a1, -1\nbnez $a1, .Ltop\nnop\n"
                    "jr $ra\nnop\n")
        declarations = {
            "return_type": "unsigned int", "parameters": [],
            "pointer_layouts": layouts,
            "global_declarations": {},
        }
        target = dict(declarations)
        target["parameters"] = [{"type": "s16*", "name": "p"}, {"type": "unsigned int", "name": "n"}]
        source = deterministic_local_draft(assembly, symbol="fn", declarations=target)
        self.assertIsNotNone(source)
        self.assertIn("do {", source)
        header = "typedef signed short s16;\n"
        compiler = shutil.which("gcc") or shutil.which("cc")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="loop-sum-") as directory:
            root = Path(directory)
            (root / "sum.c").write_text(header + source, encoding="utf-8")
            subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC",
                            str(root / "sum.c"), "-o", str(root / "sum.so")], check=True,
                           capture_output=True, text=True)
            function = ctypes.CDLL(str(root / "sum.so")).fn
            array = (ctypes.c_int16 * 3)(1, 2, 3)
            function.argtypes = [ctypes.POINTER(ctypes.c_int16), ctypes.c_uint32]
            function.restype = ctypes.c_uint32
            self.assertEqual(function(array, 3), 6)

    def test_store_loop_renders(self):
        from automation.search_target_layout import pointer_layouts
        context = b"typedef unsigned char u8;\n"
        layouts = pointer_layouts(context, ["u8*"])
        self.assertIn("u8*", layouts)
        assembly = ("li $v0, 0\n.Ltop:\nsb $a1, 0($a0)\n"
                    "addiu $a0, $a0, 1\naddiu $v0, $v0, 1\n"
                    "bne $v0, $a2, .Ltop\nnop\njr $ra\nnop\n")
        declarations = {
            "return_type": "void",
            "parameters": [{"type": "u8*", "name": "p"}, {"type": "unsigned int", "name": "v"}, {"type": "unsigned int", "name": "n"}],
            "pointer_layouts": layouts,
        }
        source = deterministic_local_draft(assembly, symbol="fn", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertIn("do {", source)
        header = "typedef unsigned char u8;\n"
        compiler = shutil.which("gcc") or shutil.which("cc")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="loop-store-") as directory:
            root = Path(directory)
            (root / "fill.c").write_text(header + source, encoding="utf-8")
            subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC",
                            str(root / "fill.c"), "-o", str(root / "fill.so")], check=True,
                           capture_output=True, text=True)
            function = ctypes.CDLL(str(root / "fill.so")).fn
            buffer = (ctypes.c_uint8 * 4)(0, 0, 0, 0)
            function.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint32, ctypes.c_uint32]
            function.restype = None
            function(buffer, 7, 4)
            self.assertEqual(list(buffer), [7, 7, 7, 7])

    def _compile_and_load(self, source, name, directory):
        compiler = shutil.which("gcc") or shutil.which("cc")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        root = Path(directory)
        (root / (name + ".c")).write_text(source, encoding="utf-8")
        subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC",
                        str(root / (name + ".c")), "-o", str(root / (name + ".so"))], check=True,
                        capture_output=True, text=True)
        return ctypes.CDLL(str(root / (name + ".so")))

    def test_while_exit_middle_sums_until_sentinel(self):
        from automation.search_target_layout import pointer_layouts
        layouts = pointer_layouts(b"typedef signed short s16;\n", ["s16*"])
        self.assertIn("s16*", layouts)
        assembly = ("li $v0, 0\n.Ltop:\nlh $v1, 0($a0)\nnop\n"
                    "bltz $v1, .Lexit\naddu $v0, $v0, $v1\n"
                    "addiu $a0, $a0, 2\nb .Ltop\nnop\n"
                    ".Lexit:\njr $ra\nnop\n")
        declarations = {
            "return_type": "unsigned int",
            "parameters": [{"type": "s16*", "name": "p"}],
            "pointer_layouts": layouts,
        }
        source = deterministic_local_draft(assembly, symbol="fn", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertIn("if (", source)
        self.assertIn("break;", source)
        self.assertIn("while (1);", source)
        with tempfile.TemporaryDirectory(prefix="loop-while-") as directory:
            library = self._compile_and_load("typedef signed short s16;\n" + source, "fn", directory)
            function = library.fn
            array = (ctypes.c_int16 * 3)(3, 4, -1)
            function.argtypes = [ctypes.POINTER(ctypes.c_int16)]
            function.restype = ctypes.c_uint32
            self.assertEqual(function(array), 6)

    def test_exit_first_while_is_zero_trip_capable(self):
        assembly = ("li $v0, 0\n.Ltop:\nbeq $a1, $zero, .Lexit\nnop\n"
                    "addu $v0, $v0, $a0\naddiu $a1, $a1, -1\n"
                    "b .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        declarations = {
            "return_type": "unsigned int",
            "parameters": [{"type": "unsigned int", "name": "v"},
                           {"type": "unsigned int", "name": "n"}],
        }
        source = deterministic_local_draft(assembly, symbol="fn", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertNotIn("do {", source)
        self.assertIn("while (", source)
        with tempfile.TemporaryDirectory(prefix="loop-zerotrip-") as directory:
            library = self._compile_and_load(source, "fn", directory)
            function = library.fn
            function.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
            function.restype = ctypes.c_uint32
            self.assertEqual(function(10, 3), 30)
            self.assertEqual(function(10, 0), 0)

    def test_do_break_counts_with_early_exit(self):
        assembly = ("li $v0, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                    "beq $v0, $a1, .Lexit\nnop\n"
                    "bne $v0, $a0, .Ltop\nnop\n"
                    ".Lexit:\njr $ra\nnop\n")
        declarations = {
            "return_type": "unsigned int",
            "parameters": [{"type": "unsigned int", "name": "n"},
                           {"type": "unsigned int", "name": "lim"}],
        }
        source = deterministic_local_draft(assembly, symbol="fn", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertIn("break;", source)
        with tempfile.TemporaryDirectory(prefix="loop-dobreak-") as directory:
            library = self._compile_and_load(source, "fn", directory)
            function = library.fn
            function.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
            function.restype = ctypes.c_uint32
            self.assertEqual(function(5, 3), 3)
            self.assertEqual(function(5, 9), 5)

    def test_scratch_temp_needs_no_entry(self):
        assembly = ("li $v0, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                    "andi $t0, $v0, 3\nbne $t0, $zero, .Ltop\nnop\n"
                    "jr $ra\nnop\n")
        source = deterministic_local_draft(
            assembly, symbol="fn", declarations=self.COUNTER_DECLS)
        self.assertIsNotNone(source)
        self.assertIn("do {", source)
        with tempfile.TemporaryDirectory(prefix="loop-scratch-") as directory:
            library = self._compile_and_load(source, "fn", directory)
            function = library.fn
            function.argtypes = [ctypes.c_uint32]
            function.restype = ctypes.c_uint32
            self.assertEqual(function(99), 4)

    def test_in_loop_branch_merges_divergent_values(self):
        assembly = ("li $v0, 0\nli $v1, 0\nli $t1, 0\n.Ltop:\n"
                    "addiu $v1, $v1, 1\nandi $t0, $v1, 1\n"
                    "beq $t0, $zero, .Leven\nnop\n"
                    "addu $t1, $v1, $zero\n.Leven:\n"
                    "addu $v0, $v0, $t1\nbne $v1, $a0, .Ltop\nnop\n"
                    "jr $ra\nnop\n")
        source = deterministic_local_draft(
            assembly, symbol="fn", declarations=self.COUNTER_DECLS)
        self.assertIsNotNone(source)
        self.assertIn("if (", source)
        with tempfile.TemporaryDirectory(prefix="loop-join-") as directory:
            library = self._compile_and_load(source, "fn", directory)
            function = library.fn
            function.argtypes = [ctypes.c_uint32]
            function.restype = ctypes.c_uint32
            self.assertEqual(function(3), 5)
            self.assertEqual(function(1), 1)

    def test_while_refusals(self):
        decls = self.COUNTER_DECLS
        spin = ".Ltop:\naddiu $v0, $v0, 1\nb .Ltop\nnop\njr $ra\nnop\n"
        self.assertIsNone(deterministic_local_draft(spin, symbol="fn", declarations=decls))
        multi = (".Ltop:\naddiu $v0, $v0, 1\n"
                 "beq $v0, $a1, .Lexit\nnop\n"
                 "beq $v0, $a2, .Lexit\nnop\n"
                 "b .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        self.assertIsNone(deterministic_local_draft(multi, symbol="fn", declarations=decls))

    def test_loop_refusals(self):
        cases = {}
        nested = (".Louter:\nnop\n.Linner:\naddiu $v0, $v0, 1\n"
                  "bne $v0, $a0, .Linner\nnop\n"
                  "addiu $v1, $v1, 1\n"
                  "bne $v1, $a1, .Louter\nnop\njr $ra\nnop\n")
        cases["nested"] = nested
        call = ("li $v0, 0\n.Ltop:\njal TestCallee\nnop\n"
                "addiu $v0, $v0, 1\nbne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")
        cases["call_in_loop"] = call
        mult = ("li $v0, 0\n.Ltop:\nmult $v0, $a0\n"
                "addiu $v0, $v0, 1\nbne $v0, $a1, .Ltop\nnop\njr $ra\nnop\n")
        cases["mult_in_loop"] = mult
        while_shape = (".Ltop:\naddiu $v0, $v0, 1\n"
                       "beq $v0, $a0, .Lexit\nnop\n"
                       "b .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        cases["while_shape"] = while_shape
        marker = ("li $v0, 0\n.Ltop:\naddu $v0, $v0, $ra\n"
                  "bne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")
        cases["marker_entry"] = marker
        hazard = ("li $v0, 0\nli $v1, 0\n.Ltop:\n"
                  "addu $v0, $v0, $v1\naddiu $v1, $v1, 1\n"
                  "bne $v0, $a0, .Ltop\nlw $v1, 0($a1)\n"
                  "jr $ra\nnop\n")
        cases["delay_hazard"] = hazard
        for name, assembly in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(deterministic_local_draft(
                    assembly, symbol="fn", declarations=self.COUNTER_DECLS))


class VariableLimitsTests(unittest.TestCase):
    LEAF_DECLS = {
        "return_type": "unsigned int",
        "parameters": [],
    }

    @staticmethod
    def _leaf(adds):
        return "li $v0, 0\n" + "addiu $v0, $v0, 1\n" * adds + "jr $ra\nnop\n"

    def test_canonical_defaults_match_previous_constants(self):
        self.assertEqual(DEFAULT_LIMITS, RendererLimits(
            max_instructions=64, path_budget=256,
            max_expression=4096, max_body=65536))

    def test_instruction_boundary_is_exact(self):
        # li + 61 adds + jr + nop is exactly 64 and renders by default.
        self.assertIsNotNone(deterministic_local_draft(
            self._leaf(61), symbol="fn", declarations=self.LEAF_DECLS))
        # 65 and 66 instructions refuse without explicit wider bounds.
        self.assertIsNone(deterministic_local_draft(
            self._leaf(62), symbol="fn", declarations=self.LEAF_DECLS))
        self.assertIsNone(deterministic_local_draft(
            self._leaf(63), symbol="fn", declarations=self.LEAF_DECLS))

    def test_raised_cap_renders_and_computes(self):
        compiler = shutil.which("gcc") or shutil.which("cc")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        assembly = self._leaf(70)
        self.assertIsNone(deterministic_local_draft(
            assembly, symbol="fn", declarations=self.LEAF_DECLS))
        for limits in (RendererLimits(max_instructions=96), {"max_instructions": 96}):
            source = deterministic_local_draft(
                assembly, symbol="big", declarations=self.LEAF_DECLS, limits=limits)
            self.assertIsNotNone(source)
            self.assertNotIn("$", source)
        with tempfile.TemporaryDirectory(prefix="limits-semantics-") as directory:
            root = Path(directory)
            (root / "big.c").write_text(source, encoding="utf-8")
            subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC",
                            str(root / "big.c"), "-o", str(root / "big.so")], check=True,
                           capture_output=True, text=True)
            function = ctypes.CDLL(str(root / "big.so")).big
            function.argtypes, function.restype = [], ctypes.c_uint32
            self.assertEqual(function(), 70)

    def test_tiny_budget_terminates_with_refusal(self):
        self.assertIsNone(deterministic_local_draft(
            SWITCH_ASM, symbol="fn", declarations=SWITCH_DECLARATIONS,
            limits=RendererLimits(path_budget=1)))
        self.assertIsNotNone(deterministic_local_draft(
            SWITCH_ASM, symbol="fn", declarations=SWITCH_DECLARATIONS))

    def test_invalid_limits_raise(self):
        good = self._leaf(1)
        for bad in ({"max_instructions": 0}, {"max_instructions": 513},
                    {"path_budget": 0}, {"path_budget": 4097},
                    {"max_expression": 512}, {"max_expression": 20000},
                    {"max_body": 1000}, {"max_body": 300000},
                    {"unknown_field": 1}, "96", 96):
            with self.subTest(limits=bad):
                with self.assertRaises(TargetRendererInputError):
                    deterministic_local_draft(
                        good, symbol="fn", declarations=self.LEAF_DECLS, limits=bad)

    def test_negu_renders_and_computes(self):
        compiler = shutil.which("gcc") or shutil.which("cc")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        declarations = {"return_type": "unsigned int",
                        "parameters": [{"type": "unsigned int", "name": "value"}]}
        source = deterministic_local_draft(
            "negu $v0, $a0\njr $ra\nnop\n",
            symbol="negate", declarations=declarations)
        self.assertIsNotNone(source)
        self.assertNotIn("$", source)
        # The trapping `neg` pseudo-instruction stays a refusal.
        self.assertIsNone(deterministic_local_draft(
            "neg $v0, $a0\njr $ra\nnop\n",
            symbol="negate", declarations=declarations))
        with tempfile.TemporaryDirectory(prefix="negu-semantics-") as directory:
            root = Path(directory)
            (root / "neg.c").write_text(source, encoding="utf-8")
            subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC",
                            str(root / "neg.c"), "-o", str(root / "neg.so")], check=True,
                           capture_output=True, text=True)
            function = ctypes.CDLL(str(root / "neg.so")).negate
            function.argtypes, function.restype = [ctypes.c_uint32], ctypes.c_uint32
            for value in (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
                self.assertEqual(function(value), (0 - value) & 0xFFFFFFFF)

    def test_empty_directives_skip_but_data_still_refuses(self):
        assembly = ApiPointerCallTests.API_ASM + ".size fn, . - fn\n.ent fn\n.end fn\n"
        self.assertIsNotNone(deterministic_local_draft(
            assembly, symbol="fn", declarations=ApiPointerCallTests.API_DECLS))
        self.assertIsNone(deterministic_local_draft(
            ApiPointerCallTests.API_ASM + ".word 0x12345678\n",
            symbol="fn", declarations=ApiPointerCallTests.API_DECLS))




class MultDivTests(unittest.TestCase):
    DECLS = {"return_type": "unsigned int", "parameters": [
        {"type": "unsigned int", "name": "x"},
        {"type": "unsigned int", "name": "y"}]}

    def _compile_and_load(self, directory, name, source):
        compiler = shutil.which("gcc") or shutil.which("cc")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        root = Path(directory)
        (root / (name + ".c")).write_text(source, encoding="utf-8")
        subprocess.run([compiler, "-std=c89", "-O2", "-Wall", "-Werror", "-shared", "-fPIC",
                        str(root / (name + ".c")), "-o", str(root / (name + ".so"))], check=True,
                       capture_output=True, text=True)
        return ctypes.CDLL(str(root / (name + ".so")))

    def test_mult_lo_computes_low_word(self):
        source = deterministic_local_draft(
            "mult $a0, $a1\nmflo $v0\njr $ra\nnop\n",
            symbol="mul_lo", declarations=self.DECLS)
        self.assertIsNotNone(source)
        with tempfile.TemporaryDirectory(prefix="mult-semantics-") as directory:
            function = self._compile_and_load(directory, "mul_lo", source).mul_lo
            function.argtypes, function.restype = [ctypes.c_uint32] * 2, ctypes.c_uint32
            for x in (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
                for y in (0, 1, 3, 0x80000000, 0xFFFFFFFF):
                    self.assertEqual(function(x, y), (x * y) & 0xFFFFFFFF, (x, y))

    def test_multu_hi_computes_high_word(self):
        source = deterministic_local_draft(
            "multu $a0, $a1\nmfhi $v0\njr $ra\nnop\n",
            symbol="mul_hi", declarations=self.DECLS)
        self.assertIsNotNone(source)
        with tempfile.TemporaryDirectory(prefix="multu-semantics-") as directory:
            function = self._compile_and_load(directory, "mul_hi", source).mul_hi
            function.argtypes, function.restype = [ctypes.c_uint32] * 2, ctypes.c_uint32
            for x in (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
                for y in (0, 1, 3, 0x80000000, 0xFFFFFFFF):
                    self.assertEqual(function(x, y), (x * y) >> 32, (x, y))

    def test_div_guard_shape_computes_quotient(self):
        assembly = ("divu $zero, $a0, $a1\nbnez $a1, .Lok\nnop\nbreak 7\n"
                    ".Lok:\nmflo $v0\njr $ra\nnop\n")
        source = deterministic_local_draft(assembly, symbol="div_q", declarations=self.DECLS)
        self.assertIsNotNone(source)
        with tempfile.TemporaryDirectory(prefix="div-semantics-") as directory:
            function = self._compile_and_load(directory, "div_q", source).div_q
            function.argtypes, function.restype = [ctypes.c_uint32] * 2, ctypes.c_uint32
            for x in (0, 1, 7, 100, 0xFFFFFFFF):
                for y in (1, 3, 7, 0x80000000, 0xFFFFFFFF):
                    self.assertEqual(function(x, y), x // y, (x, y))

    def test_div_remainder_and_signed_shapes(self):
        remainder = deterministic_local_draft(
            "divu $zero, $a0, $a1\nmfhi $v0\njr $ra\nnop\n",
            symbol="div_r", declarations=self.DECLS)
        self.assertIsNotNone(remainder)
        signed = {"return_type": "int", "parameters": [
            {"type": "int", "name": "x"}, {"type": "int", "name": "y"}]}
        quotient = deterministic_local_draft(
            "div $zero, $a0, $a1\nmflo $v0\njr $ra\nnop\n",
            symbol="sdiv_q", declarations=signed)
        self.assertIsNotNone(quotient)
        self.assertIn("/", quotient)

    def test_hilo_refusals(self):
        cases = {
            "mflo_without_mult": "mflo $v0\njr $ra\nnop\n",
            "mfhi_without_mult": "mfhi $v0\njr $ra\nnop\n",
            "mthi": "mthi $a0\njr $ra\nmove $v0, $a0\n",
            "mtlo": "mtlo $a0\njr $ra\nmove $v0, $a0\n",
            "div_nonzero_rd": "div $t0, $a0, $a1\nmflo $v0\njr $ra\nnop\n",
            "mult_arity": "mult $a0\nmflo $v0\njr $ra\nnop\n",
            "break_too_large": "break 0x1000000\njr $ra\nmove $v0, $a0\n",
        }
        for name, assembly in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(deterministic_local_draft(
                    assembly, symbol="fn", declarations=self.DECLS))


if __name__ == "__main__":
    unittest.main()
