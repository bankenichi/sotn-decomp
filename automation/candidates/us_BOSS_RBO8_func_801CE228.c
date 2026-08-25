/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO8:func_801CE228
   source : upstream/master:src/st/giantbro_helpers_2.h
   target : src/boss/rbo8/unk_1546C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo8.h"

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", EntityBreakable);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_us_801955A0);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_us_801955F8);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_801CE1E8);

void func_801CE228() {
    s32 i;
     
     
     
     
     
     
     
     
     
    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", polarPlacePartsList);
