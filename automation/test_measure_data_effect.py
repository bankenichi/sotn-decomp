"""Focused tests for the data-effect remeasurement helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.measure_data_effect import classify_file, derive_record, has_loop_shape, instruction_count, is_pool_member, loop_latches, resolve_limits, size_bucket


class RemeasureHelperTests(unittest.TestCase):
    def test_pool_membership_needs_jalr_and_paired_api(self):
        good = ("lui $v0, %hi(g_api_Test)\n"
                "lw $v0, %lo(g_api_Test)($v0)\n"
                "nop\njalr $v0\nnop\n")
        self.assertTrue(is_pool_member(good))
        self.assertFalse(is_pool_member(good.replace("jalr $v0", "jal $v0")))
        self.assertFalse(is_pool_member("lui $v0, %hi(g_api_OnlyHi)\njalr $v0\nnop\n"))
        self.assertFalse(is_pool_member(""))
        splat = ("    /* 3A2B8 801BA2B8 09F84000 */  lui $v0, %hi(g_api_Test)\n"
                 "    /* 3A2BC 801BA2BC 00000000 */  lw $v0, %lo(g_api_Test)($v0)\n"
                 "    /* 3A2C0 801BA2C0 00000000 */  nop\n"
                 "    /* 3A2C4 801BA2C4 09F84000 */  jalr $v0\n"
                 "    /* 3A2C8 801BA2C8 00000000 */  nop\n")
        self.assertTrue(is_pool_member(splat))
        self.assertFalse(is_pool_member(None))

    def test_classify_sorts_names_into_harness_classes(self):
        text = ("lui $a0, %hi(D_us_1)\naddiu $a0, $a0, %lo(D_us_1)\n"
                "lui $a1, %hi(g_Buf)\naddiu $a1, $a1, %lo(g_Buf)\n"
                "lui $v0, %hi(g_api_Test)\nlw $v0, %lo(g_api_Test)($v0)\n"
                "lui $v1, %hi(PLAYER_posX_i_hi)\nlhu $v1, %lo(PLAYER_posX_i_hi)($v1)\n"
                "lui $at, %hi(jtbl_us_1)\n")
        classes = classify_file(text)
        self.assertEqual(classes["d_star"], ["D_us_1"])
        self.assertEqual(classes["g_star"], ["g_Buf"])
        self.assertEqual(classes["g_api"], ["g_api_Test"])
        self.assertEqual(classes["linker"], ["PLAYER_posX_i_hi"])
        self.assertEqual(classes["jtbl"], ["jtbl_us_1"])
        self.assertEqual(classes["other"], [])

    def test_classify_reports_unknown_names_as_other(self):
        text = "lui $v0, %hi(mystery_sym)\naddiu $v0, $v0, %lo(mystery_sym)\n"
        classes = classify_file(text)
        self.assertEqual(classes["other"], ["mystery_sym"])

    def test_derive_record_maps_paths_to_ids(self):
        self.assertEqual(
            derive_record("asm/us/st/rnz1/nonmatchings/unk_3BE58/func_us_801BC650.s"),
            ("us:ST/RNZ1:func_us_801BC650", "ST/RNZ1"))
        self.assertEqual(
            derive_record("asm/us/boss/bo0/nonmatchings/e_init/func_us_801ABFE0.s"),
            ("us:BOSS/BO0:func_us_801ABFE0", "BOSS/BO0"))
        self.assertIsNone(derive_record("asm/us/st/func.s"))
        self.assertIsNone(derive_record("elsewhere/func_us_1.s"))
        self.assertIsNone(derive_record(""))

    def test_resolve_limits_maps_names_and_refuses(self):
        from automation.search_target_renderer import DEFAULT_LIMITS
        self.assertIsNone(resolve_limits("default"))
        raised = resolve_limits("raised")
        self.assertEqual(raised.max_instructions, 512)
        self.assertEqual(raised.path_budget, 4096)
        self.assertEqual(raised.max_expression, 16384)
        self.assertEqual(raised.max_body, 262144)
        self.assertGreater(raised.max_instructions, DEFAULT_LIMITS.max_instructions)
        with self.assertRaises(ValueError):
            resolve_limits("turbo")

    def test_instruction_count_and_size_buckets(self):
        self.assertEqual(instruction_count("jr $ra\nnop\n"), 2)
        self.assertIsNone(instruction_count(None))
        self.assertEqual(size_bucket(None), "unparseable")
        self.assertEqual(size_bucket(64), "<=64")
        self.assertEqual(size_bucket(65), "65-128")
        self.assertEqual(size_bucket(256), "129-256")
        self.assertEqual(size_bucket(512), "257-512")
        self.assertEqual(size_bucket(513), ">512")

    def test_has_loop_shape_mirrors_renderer_rule(self):
        straight = "addu $v0, $a0, $a1\njr $ra\nnop\n"
        self.assertFalse(has_loop_shape(straight))
        forward = ("beq $v0, $zero, .Lend\nnop\n"
                   "addiu $v0, $v0, 1\n.Lend:\njr $ra\nnop\n")
        self.assertFalse(has_loop_shape(forward))
        loop = ("addiu $v0, $zero, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                "bne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")
        self.assertTrue(has_loop_shape(loop))
        self.assertFalse(has_loop_shape(""))
        self.assertFalse(has_loop_shape(None))

    def test_loop_latches_classify_latch_forms(self):
        do_while = ("addiu $v0, $zero, 0\n.Ltop:\naddiu $v0, $v0, 1\n"
                    "bne $v0, $a0, .Ltop\nnop\njr $ra\nnop\n")
        self.assertEqual(loop_latches(do_while),
                         {"total": 1, "conditional": True, "unconditional": False})
        while_latch = (".Ltop:\naddiu $v0, $v0, 1\n"
                       "beq $v0, $a0, .Lexit\nnop\n"
                       "b .Ltop\nnop\n.Lexit:\njr $ra\nnop\n")
        self.assertEqual(loop_latches(while_latch),
                         {"total": 1, "conditional": False, "unconditional": True})
        nested = (".Louter:\n.Linner:\naddiu $v0, $v0, 1\n"
                   "bne $v0, $a0, .Linner\nnop\n"
                   "addiu $v1, $v1, 1\n"
                   "bne $v1, $a1, .Louter\nnop\njr $ra\nnop\n")
        self.assertEqual(loop_latches(nested)["total"], 2)
        self.assertFalse(has_loop_shape("addu $v0, $a0, $a1\njr $ra\nnop\n"))
        self.assertEqual(loop_latches(""), {"total": 0, "conditional": False, "unconditional": False})
        self.assertEqual(loop_latches(None), {"total": 0, "conditional": False, "unconditional": False})


if __name__ == "__main__":
    unittest.main()
