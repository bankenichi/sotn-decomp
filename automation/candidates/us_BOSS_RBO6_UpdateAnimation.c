/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO6:UpdateAnimation
   source : upstream/master:src/st/prim_helpers.h
   target : src/boss/rbo6/prim_helpers.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UnkPrimHelper);

s32 UpdateAnimation(u8* texAnimations, Primitive* prim) {
    u16 sp0;
    u16 tempUv;
    s32 retVal = 0;
    u8 index = prim->p1 * 5;
    u8* nextAnimation = &texAnimations[index];

    if (!prim->p2) {
        if (*nextAnimation) {
            if (*nextAnimation == 0xFF) {
                return 0;
            }
            prim->p2 = *nextAnimation++;
            tempUv = nextAnimation[0] + (nextAnimation[1] << 8);
            nextAnimation += 2;
            sp0 = nextAnimation[0] + (nextAnimation[1] << 8);
            LOH(prim->u0) = tempUv;
            LOH(prim->u1) = tempUv + *((u8*)(&sp0));
            LOH(prim->u2) = tempUv + (*((u8*)&sp0 + 1) << 8);
            LOH(prim->u3) = tempUv + sp0;
            prim->p1++;
            retVal = (retVal | 0x80) & 0xFFFF;
        } else {
            prim->p1 = 0;
            prim->p2 = 0;
            nextAnimation = &texAnimations[0];
            prim->p2 = *nextAnimation++;
            tempUv = nextAnimation[0] + (nextAnimation[1] << 8);
            nextAnimation += 2;
            sp0 = nextAnimation[0] + (nextAnimation[1] << 8);
            LOH(prim->u0) = tempUv;
            LOH(prim->u1) = tempUv + (*(u8*)&sp0);
            LOH(prim->u2) = tempUv + (*((u8*)&sp0 + 1) << 8);
            LOH(prim->u3) = tempUv + sp0;
            prim->p1++;
            return 0;
        }
    }

    prim->p2--;
#ifndef VERSION_PSP
    retVal |= 1;
#endif
    retVal = (retVal | 1) & 0xFFFF;
    return retVal & 0xFF;
}

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

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", PrimDecreaseBrightness);
