/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO2:func_us_801B5EE4
   score  : 5
   receipt: nonmatchings/.adapt-scores/20260824-234458-62298-996097/func_us_801B5EE4/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno2/unk_3459C.c
   asm    : asm/us/st/rno2/nonmatchings/unk_3459C/func_us_801B5EE4.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
s32 Random();
int abs(int x);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AB9EC_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B5FB8_from_no2);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AC54C_from_bo0);

static void func_us_801AC73C_from_bo0(Primitive* prim) {
    s32 x, y;

    if (!prim->g3) {
        prim->u0 = 1;
        prim->v0 = 1;
        prim->r0 = 0x80;
        prim->g0 = 0x80;
        prim->b0 = 0xC0;
        prim->drawMode = DRAW_UNK02;
        prim->x0 = g_CurrentEntity->posX.i.hi;
        prim->y0 = g_CurrentEntity->posY.i.hi + 8;
        prim->x1 = 0;
        prim->y1 = 0;
        LOW(prim->x2) = 0x7000 - ((Random() & 7) << 0xD);
        LOW(prim->x3) = 0x7000 - ((Random() & 7) << 0xD);
        prim->g3 = 1;
        prim->r3 = 0x20;
    }
#ifdef VERSION_US
    x = (prim->x0 << 0x10) + (u16)prim->x1;
#else
    x = (prim->x0 << 0x10) + prim->x1;
#endif
    x += LOW(prim->x2);
    prim->x0 = HIHU(x);
    prim->x1 = LOHU(x);
#ifdef VERSION_US
    y = (prim->y0 << 0x10) + (u16)prim->y1;
#else
    y = (prim->y0 << 0x10) + prim->y1;
#endif
    y += LOW(prim->x3);
    prim->y0 = HIH(y);
    prim->y1 = LOH(y);
    LOW(prim->x3) += 0x2000;
    prim->r3 -= 1;
    if (!prim->r3) {
        prim->g3 = 0;
        prim->drawMode = DRAW_HIDE;
        prim->p3 = 0;
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B68EC_from_no2);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", EntityPrisoner);

#define false 0
#define true 1

static bool func_us_801B5EE4(Entity* self) {
    s16 distanceX;
    s16 diffX;
    s16 distanceY;
    s16 diffY;

    diffX = PLAYER.posX.i.hi - self->posX.i.hi;
    distanceX = abs(diffX);
    if (distanceX > 16) {
        return false;
    }

    diffY = PLAYER.posY.i.hi - self->posY.i.hi;
    distanceY = abs(diffY);
    if (distanceY > 32) {
        return false;
    }

    return true;
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", EntitySealedDoor);
