/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO6:DecreaseBrightness
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/cat/e_spikes.c
   target : src/boss/rbo6/unk_2362C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A362C);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A367C);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A37B4);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A399C);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A3BE0);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A4028);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A9208_from_bo6);

s32 DecreaseBrightness(Primitive* prim, u8 brightnessOffset) {
    s32 newColor;
    s32 i;
    s32 j;
    u8* rgbVal;
    u8* rPtr;
    s32 ret;

    ret = 0;

     
     
     
    rPtr = &prim->r0;
    for (i = 0; i < 4; i++) {
        for (j = 0; j < 3; j++) {
            rgbVal = &rPtr[j];
            newColor = *rgbVal;
            newColor += brightnessOffset;
            if (newColor > 0x68) {
                newColor = 0x68;
            } else {
                ret |= 1;
            }
            *rgbVal = newColor;
        }
        rPtr += 0xC;
    }
    return ret;
}

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A4594);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A4F14);
