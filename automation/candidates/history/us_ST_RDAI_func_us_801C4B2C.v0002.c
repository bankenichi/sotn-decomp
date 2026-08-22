/* READ-ONLY MODEL RECONCILIATION SCRATCH
   record: us:ST/RDAI:func_us_801C4B2C
   source: Luna xhigh advanced-context response for ROADMAP #232
   This file is not match evidence and must not be applied directly. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "../../../src/st/rdai/rdai.h"

void func_us_801C4B2C(void) {
    Primitive* prim;
    s32 i;

    prim = g_CurrentEntity->ext.prim;
    i = 0;

    do {
        Primitive* next;
        s32 avgX;
        s32 avgY;
        s32 diffX;
        s32 diffY;
        s32 newX;
        s32 newY;

        next = prim->next;

        avgX = (prim->x0 + next->x2) / 2;
        avgY = (prim->y0 + next->y2) / 2;
        diffX = prim->x2 - avgX;
        diffY = prim->y2 - avgY;

        if (diffX < 0) {
            diffX += 7;
        }
        if (diffY < 0) {
            diffY += 7;
        }

        newX = (diffX >> 3) + avgX;
        newY = (diffY >> 3) + avgY;

        prim->x2 = newX;
        next->x0 = newX;
        prim->y2 = newY;
        next->y0 = newY;

        avgX = (prim->x1 + next->x3) / 2;
        avgY = (prim->y1 + next->y3) / 2;
        diffX = prim->x3 - avgX;
        diffY = prim->y3 - avgY;

        if (diffX < 0) {
            diffX += 7;
        }
        if (diffY < 0) {
            diffY += 7;
        }

        newX = (diffX >> 3) + avgX;
        newY = (diffY >> 3) + avgY;

        prim->x3 = newX;
        next->x1 = newX;
        prim->y3 = newY;

        prim = next;
        prim->y1 = newY;
        i++;
    } while (i < 7);
}
