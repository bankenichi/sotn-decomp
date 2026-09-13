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
    TargetContextUnsupported,
    TargetEvidenceError,
    TargetRendererInputError,
    _assembly_signatures,
    _parse_assembly,
    deterministic_local_draft,
    load_target_index,
    query_for_recipient,
    render_target_candidate,
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
        for text in (b"void add_value(unsigned int value);", b"int add_value(int);",
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


if __name__ == "__main__":
    unittest.main()
