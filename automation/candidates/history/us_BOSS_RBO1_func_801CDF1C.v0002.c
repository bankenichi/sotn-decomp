/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO1:func_801CDF1C
   source : upstream/master:src/boss/rbo8_psp/unk_DEB8.c
   target : src/boss/rbo1/unk_12274.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void func_801CDD80(s16* entOffsets, unkStr_801CDD80* arg1);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", EntityBreakable);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801923A8);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80192C5C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80192F84);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801936FC);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80193C2C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80193E24);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80194108);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_8019ED80_from_rbo2);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", polarPlacePartsWithAngvel);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CDD00);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CDD80);

void func_801CDF1C(s16 entIndices[], unkStr_801CDD80* arg1, s32 arg2) {

    arg1 += (u16)g_CurrentEntity->ext.GH_Props.unkB0[arg2];

    if (!g_CurrentEntity->ext.GH_Props.unkB4[arg2]) {
        func_801CDD80(entIndices, arg1);
        g_CurrentEntity->ext.GH_Props.unkB4[arg2] = arg1->unk0;
    }
    if (!--g_CurrentEntity->ext.GH_Props.unkB4[arg2]) {
        arg1++;
        if (!arg1->unk0) {
            g_CurrentEntity->ext.GH_Props.unkB0[arg2] = 0;
        } else {
            ++g_CurrentEntity->ext.GH_Props.unkB0[arg2];
        }
    }
}

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CE1E8);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CE228);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", polarPlacePartsList);

// decompiled in src/boss/bo1/e_explosion_flame.c
INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_8019D260_from_rcen);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801947E4);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80194C50);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", EntityBossRoomBlock);
