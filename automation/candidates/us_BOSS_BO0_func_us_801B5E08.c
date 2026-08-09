/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801B5E08
   attempt: 2/4
   model  : opencode/laguna-s-2.1-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/boss/bo0/nonmatchings/2D26C/func_us_801B5E08.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo0.h"

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD26C);

// Checks whether the tile at (x, y) is solid ground.
s32 func_us_801AD2F0(s16 x, s16 y) {
    Collider col;

    g_api.CheckCollision(x, y, &col, 0);
    return col.effects & EFFECT_SOLID;
}

INCLUDE_RODATA("boss/bo0/nonmatchings/2D26C", D_us_801A9344);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD338);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AE858);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF31C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF604);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF8C0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AFAF4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", EntityOlroxAfterImage);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B001C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B053C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B088C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B0930);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B13A8);

void func_us_801B1590(u8 step) {
    ET_B0_Unk* temp = (ET_B0_Unk*)g_CurrentEntity->ext.b0Unk.unk80;

    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;

    temp->childPalette = 0;
    temp = (ET_B0_Unk*)temp->parent;
    temp->childPalette = 0;
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B15BC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B163C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B171C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B17BC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1864);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1950);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B19FC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1B30);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1C60);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1CE0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1DDC);

s32 func_us_801B1E5C(void *arg0)
{
  void *entity = arg0;
  s32 result1;
  s32 result2;
  void *child = *((void **) (((char *) entity) + 0x18));
  func_us_801B163C(&g_CurrentEntity->ext.venusWeed.pad_90, 0, 0xC);
  result1 = func_us_801B171C(entity, -0x40, 0x40, 0x60);
 do { result2 = func_us_801B171C(child, -0x200, 0x280, 0x50); return (result1 + result2) == 2; } while (0);
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1EDC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1F5C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2044);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B20F4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2178);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B21F0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B24CC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2690);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B30AC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B365C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5470);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B551C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5D6C);

/* Iterates through 8 consecutive entries (4 bytes apart) starting at base,
   calling a hit/collision test against each target s16 and the angle arg2.
   Returns 1 if all 8 tests succeeded, 0 if any failed. */
s32 func_us_801B163C(s32, s16, s16);

s32 func_us_801B5E08(s32 base, s16 *targets, s16 angle)
{
    s32 index;      /* loop counter 0..7 */
    s32 all_hit;    /* 1 if every test passed, cleared to 0 on any failure */

    all_hit = 1;
    index = 0;
    do {
        index += 1;
        /* base advances by 4 per iteration; targets by 2 (s16 stride) */
        if (func_us_801B163C(base, *targets, angle) == 0) {
            all_hit = 0;   /* one failure means the whole set fails */
        }
        base += 4;
        targets += 1;
    } while (index < 8);

    return all_hit;
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5E8C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B619C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B6520);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B65C0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B6CA4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B76E4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7BAC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7C44);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7CC8);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8794);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B888C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8970);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8B64);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8D8C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B9BEC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA030);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA128);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA4AC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA724);
