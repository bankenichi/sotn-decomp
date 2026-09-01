"""Focused parity tests for the shared assembly semantic selector."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_semantic_signatures import (
    SemanticInstruction,
    assembly_signatures,
    classify_instruction,
    dataflow_profile,
    has_numeric_branch_target,
    normalize_operands,
)


class SemanticSignatureTests(unittest.TestCase):
    def test_mips_numeric_branch_is_omitted_without_losing_safe_records(self) -> None:
        safe = (
            SemanticInstruction("addiu", "$t0, $zero, 1"),
            SemanticInstruction("jal", "helper"),
            SemanticInstruction("jr", "$ra"),
        )
        with_forbidden_branch = (
            safe[0],
            SemanticInstruction("beq", "$t0, $zero, 0x10"),
            safe[1],
            safe[2],
        )
        self.assertTrue(has_numeric_branch_target("beq", "$t0, $zero, 0x10"))
        self.assertEqual(assembly_signatures(safe), assembly_signatures(with_forbidden_branch))
        self.assertEqual(normalize_operands("lw", "$t0, 4($sp)"), "REG,MEM")
        self.assertEqual(
            dataflow_profile(with_forbidden_branch),
            {"calls": ("jal",), "loads": 0, "stores": 0, "returns": 1},
        )

    def test_arm_like_roles_and_numeric_bl_follow_the_same_policy(self) -> None:
        instructions = (
            SemanticInstruction("ldr", "r0, [r1, #4]"),
            SemanticInstruction("bl", "#0x20"),
            SemanticInstruction("bx", "lr"),
            SemanticInstruction("ret", ""),
        )
        self.assertTrue(has_numeric_branch_target("bl", "#0x20"))
        self.assertEqual(normalize_operands("ldr", "r0, [r1, #4]"), "REG,MEM")
        self.assertEqual(
            dataflow_profile(instructions),
            {"calls": (), "loads": 1, "stores": 0, "returns": 2},
        )
        self.assertTrue(classify_instruction("bl", "helper").call)
        self.assertFalse(classify_instruction("lsl", "r0, r1, #2").load)
        self.assertTrue(classify_instruction("bx", "lr").is_return)
        self.assertFalse(classify_instruction("bx", "r3").is_return)
        self.assertTrue(classify_instruction("jr", "$ra").is_return)
        self.assertFalse(classify_instruction("jr", "$t9").is_return)
        self.assertFalse(classify_instruction("lui", "$t0, 0x1").load)

    def test_saturn_sh_like_memory_moves_calls_and_returns_are_exact(self) -> None:
        instructions = (
            SemanticInstruction("mov.l", "@r1, r0"),
            SemanticInstruction("mov.b", "r0, @r2"),
            SemanticInstruction("bsr", "0x10"),
            SemanticInstruction("jsr", "@r3"),
            SemanticInstruction("rts", ""),
        )
        self.assertTrue(has_numeric_branch_target("bsr", "0x10"))
        self.assertEqual(
            dataflow_profile(instructions),
            {"calls": ("jsr",), "loads": 1, "stores": 1, "returns": 1},
        )
        self.assertFalse(classify_instruction("sll", "r0, r1").store)
        self.assertTrue(classify_instruction("mov.l", "@r1, r0").load)
        self.assertTrue(classify_instruction("mov.b", "r0, @r2").store)



    def test_shared_policy_filters_directives_and_relocations_by_mnemonic_or_operand(self) -> None:
        safe = (
            SemanticInstruction("add", "r0, r1, r2"),
            SemanticInstruction("rte", ""),
        )
        annotated = (
            SemanticInstruction("dc.w", "0x1234"),
            SemanticInstruction("R_MIPS_HI16", "symbol"),
            SemanticInstruction("add", "r0, r1, r2"),
            SemanticInstruction(".reloc", "0, R_MIPS_LO16, symbol"),
            SemanticInstruction("rte", ""),
        )
        self.assertEqual(assembly_signatures(safe), assembly_signatures(annotated))
        self.assertTrue(classify_instruction("rte", "").is_return)
        self.assertTrue(classify_instruction("bal", "helper").call)
        self.assertTrue(classify_instruction("blr", "x30").call)

    def test_parser_marked_unsupported_records_are_not_signature_input(self) -> None:
        safe = (
            SemanticInstruction("add", "r0, r1, r2"),
            SemanticInstruction("ret", ""),
        )
        annotated = (
            SemanticInstruction(".word", "0x1234", unsupported=True),
            safe[0],
            SemanticInstruction("R_MIPS_HI16", "symbol", unsupported=True),
            safe[1],
        )
        self.assertEqual(assembly_signatures(safe), assembly_signatures(annotated))


if __name__ == "__main__":
    unittest.main()
