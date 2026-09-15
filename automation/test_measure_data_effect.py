"""Focused tests for the data-effect remeasurement helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.measure_data_effect import classify_file, derive_record, is_pool_member


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


if __name__ == "__main__":
    unittest.main()
