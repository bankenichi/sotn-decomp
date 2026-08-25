/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO6:FindFirstUnkPrim2
   source : upstream/master:src/st/prim_helpers.h
   target : src/boss/rbo6/prim_helpers.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UnkPrimHelper);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UpdateAnimation);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", FindFirstUnkPrim);

Primitive* FindFirstUnkPrim2(Primitive* prim, u8 index) {
    int i;
    Primitive* primLocal = prim;

    while (primLocal != NULL) {
        if (!primLocal->p3) {
            prim = primLocal;
            for (i = 1; i < index; i++) {
                primLocal = primLocal->next;
                if (!primLocal) {
                    return NULL;
                }

                if (primLocal->p3) {
                    break;
                }
            }

            if (i == index) {
                return prim;
            }
        }
        primLocal = primLocal->next;
    }
    return NULL;
}

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
