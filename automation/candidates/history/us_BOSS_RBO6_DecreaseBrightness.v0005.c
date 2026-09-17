/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO6:DecreaseBrightness
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/cat/e_spikes.c
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

    // Starting at prim->r0, update r0,g0,b0
    // Then we skip 0xC bytes of the prim to take us to r1,g1,b1
    // and so on for r2,g2,b2 and r3,g3,b3
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
