/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO6:PrimDecreaseBrightness
   source : upstream/master:src/dra/84B88.c
   target : src/boss/rbo6/prim_helpers.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UnkPrimHelper);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UpdateAnimation);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", FindFirstUnkPrim);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", FindFirstUnkPrim2);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", PrimToggleVisibility);

void PrimResetNext(Primitive* prim) {
    prim->p1 = 0;
    prim->p2 = 0;
    prim->p3 = 0;
    prim->next->x1 = 0;
    prim->next->y1 = 0;
    prim->next->y0 = 0;
    prim->next->x0 = 0;
    prim->next->clut = 0;
    LOHU(prim->next->u0) = 0;
    LOHU(prim->next->b1) = 0;
    LOHU(prim->next->r1) = 0;
    LOHU(prim->next->u1) = 0;
    prim->next->tpage = 0;
    LOHU(prim->next->r2) = 0;
    LOHU(prim->next->b2) = 0;
    prim->next->u2 = 0;
    prim->next->v2 = 0;
    prim->next->r3 = 0;
    prim->next->b3 = 0;
    prim->next->x2 = 0;
    prim->next->y2 = 0;
}

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UnkPolyFunc2);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UnkPolyFunc0);

u8 PrimDecreaseBrightness(Primitive* prim, u8 amount) {
    s32 i;
    s32 j;
    u8* colorPtr;    
    u8* channelPtr;  
    u8 isEnd;

    isEnd = 0;
    colorPtr = &prim->r0;
    for (i = 0; i < 4; colorPtr += OFF(Primitive, r1) - OFF(Primitive, r0),
        i++) {
        for (j = 0; j < 3; j++) {
            channelPtr =
                &colorPtr[j];  
            *channelPtr -= amount;

            if (*channelPtr < 16) {
                *channelPtr = 16;
            } else {
                isEnd |= 1;
            }
        }
    }
    return isEnd;
}
