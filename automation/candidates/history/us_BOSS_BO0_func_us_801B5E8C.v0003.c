/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801B5E8C
   attempt: 3/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/boss/bo0/nonmatchings/2D26C/func_us_801B5E8C.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo0.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
int rcos(int a);
int rsin(int a);

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_us_801B163C();
extern int func_us_801B171C();

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

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5E08);

void func_us_801B5E8C(void) {
    Entity* entity = g_CurrentEntity;
    s32 sp10 = 0;
    u16 var_fp = entity->posX.i.hi;
    u16 sp30 = entity->posY.i.hi;
    u16* var_s4 = (u16*)&entity->ext.venusWeedTendril.pad_7C[0xC];
    Primitive* var_s2 = (Primitive*)entity->ext.venusWeedTendril.pad_7C;
    s16 var_s3 = -0x180;
    u16 var_s6, var_s7;
    u16 sp18, sp20, sp28, sp38, sp40, sp48;

    do {
            s32 temp_v1_3;
            s32 temp_s0_4;
            s32 temp_s5;
            s32 temp_s0_5;
        s16 temp_v1 = *var_s4;
        s16 temp_s0 = ((var_s3 + temp_v1) / 2) + 0x400;
        s16 var_s3_2 = temp_s0;
        s16 temp_s0_2 = temp_s0 - temp_v1;
        s16 temp_s0_3 = ((rcos(temp_s0_2) * 6) >> 12) + 8;
        s32 temp_v1_2 = rcos(temp_s0_2) * 6;
        s16 var_s1 = 8 - (temp_v1_2 >> 12);

        sp18 = sp20;
        sp38 = sp40;
        sp28 = var_s6;
        sp48 = var_s7;

        if (sp10 == 0) {
            var_s1 = 0xC;
            var_s3_2 = 0x260;
        }

        temp_v1_3 = ((s16)entity->ext.venusWeedTendril.timer / 2) + 0x800;
        temp_s0_4 = (temp_s0_3 * temp_v1_3) >> 12;
        temp_s5 = (var_s1 * temp_v1_3) >> 12;

        if (entity->facingLeft != 0) {
            var_s3_2 = 0x800 - var_s3_2;
        }

        sp20 = var_fp + ((temp_s0_4 * rcos(var_s3_2)) >> 12);
        sp40 = sp30 - ((temp_s0_4 * rsin(var_s3_2)) >> 12);
        var_s6 = var_fp - ((temp_s5 * rcos(var_s3_2)) >> 12);
        var_s7 = sp30 + ((temp_s5 * rsin(var_s3_2)) >> 12);

        temp_s0_5 = ((s16)entity->ext.venusWeedTendril.timer * 0xB) >> 12;

        if (entity->facingLeft == 0) {
            var_fp += (temp_s0_5 * rcos(*var_s4)) >> 12;
        } else {
            var_fp -= (temp_s0_5 * rcos(*var_s4)) >> 12;
        }

        var_s3 = *var_s4;
        sp30 -= (temp_s0_5 * rsin(*var_s4)) >> 12;

        if (sp10 != 0) {
            var_s2->tpage = 0x14;
            var_s2->clut = 0x20B;
            var_s2->x0 = sp18;
            var_s2->x2 = sp28;
            var_s2->y0 = sp38;
            var_s2->y2 = sp48;
            var_s2->x3 = var_s6;
            var_s2->x1 = sp20;
            var_s2->y3 = var_s7;
            var_s2->y1 = sp40;
            var_s2 = var_s2->next;
        }

        var_s4 = &var_s4[1];
        sp10++;
    } while (sp10 < 9);
}

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
