/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO6:PrimToggleVisibility
   source : upstream/master:src/st/prim_helpers.h
   target : src/boss/rbo6/prim_helpers.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UnkPrimHelper);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", UpdateAnimation);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", FindFirstUnkPrim);

INCLUDE_ASM("boss/rbo6/nonmatchings/prim_helpers", FindFirstUnkPrim2);

Primitive* PrimToggleVisibility(Primitive* prim, s32 count) {
    s32 i;
    u8 isVisible;

    if (prim->p3) {
        prim->p3 = false;
    } else {
        prim->p3 = true;
    }

    for (i = 0; i < count; i++) {
        if (prim->p3) {
            prim->drawMode &= ~DRAW_HIDE;
            isVisible = false;
        } else {
            prim->drawMode |= DRAW_HIDE;
            isVisible = true;
        }

        prim = prim->next;
        if (prim == NULL) {
             
            if (true) {
                return NULL;
            }
        }

        prim->p3 = isVisible;
    }

    return prim;
}

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
