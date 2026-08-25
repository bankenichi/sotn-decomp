/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:func_pspeu_0924B480
   source : upstream/master:src/st/water_effects_rev.h
   target : src/st/rnz1/unk_37BF8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern s16 g_WaterXTbl[];

u16 func_pspeu_0924B480(s16 arg0, s16 arg1, s16 arg2, s16* arg3) {
    s16 temp_s2;
    s16 temp;
    s16* ptr;

    ptr = &g_WaterXTbl[arg0 * 8];
    arg1 -= (g_Tilemap.width - *ptr++);
    temp_s2 = *ptr++;
    arg1 += temp_s2;
    if (arg1 < 0) {
        return 0;
    }
    *arg3++ = arg1;

    temp = temp_s2 - arg1;
    if (temp <= 0) {
        return 0;
    }
    temp_s2 = temp;
    *arg3 = temp;

    temp = g_splashAspects[*ptr++];
    if (temp) {
        temp = temp_s2 / temp;
    } else {
        temp = 0;
    }

    temp = temp + (g_Tilemap.height - *ptr++);
    if (temp < arg2) {
        return 0;
    }
    if (arg2 <= (g_Tilemap.height - *ptr++)) {
        return 0;
    }
    return ((temp + 0x7FFF) + 1) - arg2;
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntityAlucardWaterEffect);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySplashWater);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySurfacingWater);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySideWaterSplash);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySmallWaterDrop);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntityWaterDrop);
