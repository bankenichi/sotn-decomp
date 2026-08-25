/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO7:func_us_80194338_from_rbo0
   source : upstream/master:src/boss/bo7_psp/unk_E700.c
   target : src/boss/bo7/unk_14CE0.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

bool func_us_80194338_from_rbo0(s16* offsets) {
    s32 posY;

    offsets++;
    posY = g_CurrentEntity->posY.i.hi + *offsets + g_Tilemap.scrollY.i.hi;
    posY = 0xD0 - posY;
    if (posY <= 0) {
        g_CurrentEntity->posY.i.hi += posY;
        g_CurrentEntity->velocityX = 0;
        g_CurrentEntity->velocityY = 0;
        return true;
    }
    return false;
}

INCLUDE_ASM("boss/bo7/nonmatchings/unk_14CE0", func_us_80194D3C);

INCLUDE_ASM("boss/bo7/nonmatchings/unk_14CE0", func_us_801959E0);

INCLUDE_ASM("boss/bo7/nonmatchings/unk_14CE0", func_us_80195AF0);

INCLUDE_ASM("boss/bo7/nonmatchings/unk_14CE0", func_us_80195C50);

INCLUDE_ASM("boss/bo7/nonmatchings/unk_14CE0", func_us_801963D8);
