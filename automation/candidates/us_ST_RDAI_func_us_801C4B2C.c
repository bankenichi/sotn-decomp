/* PRESERVED NONMATCHING MODEL SEED
   record : us:ST/RDAI:func_us_801C4B2C
   attempt: 4/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ)
   search : exhausted at best score 950 after 5362 iterations and 3
            promotions, with no improvement for the final 2774 iterations.
            This file is the original model seed, not necessarily the promoted
            best-scoring body. Structural re-derivation is required before
            another permutation pass.
   content: WHOLE FILE (directly importable)
   import : use the sotn-cmd permuter_import connector with this file and
            asm/us/st/rdai/nonmatchings/func_44b2c/func_us_801C4B2C.s
   Do NOT apply this to the tree as-is; it does not match.
   It is preserved as evidence and as a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rdai.h"

void func_us_801C4B2C(void) {
    Entity* entity = g_CurrentEntity;
    Primitive* prim = entity->ext.prim;
    s32 i = 0;

    do {
        Primitive* next = prim->next;
        s32 avgX = (prim->x0 + next->x2) / 2;
        s32 avgY = (prim->y0 + next->y2) / 2;
        s32 diffX = prim->x2 - avgX;
        s32 diffY = prim->y2 - avgY;
        s32 adjustedDiffX = diffX < 0 ? diffX + 7 : diffX;
        s32 adjustedDiffY = diffY < 0 ? diffY + 7 : diffY;
        s16 newX = (adjustedDiffX >> 3) + avgX;
        s16 newY = (adjustedDiffY >> 3) + avgY;

        prim->x2 = newX;
        next->x0 = newX;
        prim->y2 = newY;
        next->y0 = newY;

        avgX = (prim->x1 + next->x3) / 2;
        avgY = (prim->y1 + next->y3) / 2;
        diffX = prim->x3 - avgX;
        diffY = prim->y3 - avgY;
        adjustedDiffX = diffX < 0 ? diffX + 7 : diffX;
        adjustedDiffY = diffY < 0 ? diffY + 7 : diffY;
        newX = (adjustedDiffX >> 3) + avgX;
        newY = (adjustedDiffY >> 3) + avgY;

        prim->x3 = newX;
        next->x1 = newX;
        prim->y3 = newY;
        prim = next;
        prim->y1 = newY;
        i++;
    } while (i < 7);
}
