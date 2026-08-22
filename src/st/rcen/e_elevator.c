// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rcen.h"

// Unused on PSP, see UnusedPrimFunction in CEN
INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", func_us_8019FD4C);

static s16 func_801904B8(Primitive* prim, s16 dy) {
    prim->drawMode = DRAW_UNK02;
    prim->u0 = prim->u2 = 0x50;
    prim->u1 = prim->u3 = 0x60;
    prim->x0 = prim->x2 = g_CurrentEntity->posX.i.hi - 8;
    prim->x1 = prim->x3 = g_CurrentEntity->posX.i.hi + 8;
    prim->v2 = prim->v3 = 38;
    prim->y2 = prim->y3 = dy;
    dy += 32;
    prim->v0 = prim->v1 = 6;
    prim->y0 = prim->y1 = dy;
    if (dy >= 0x101) {
        dy = 0;
    }
    return dy;
}

INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", func_us_8019FE9C);

INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", EntityUnkId1B);
