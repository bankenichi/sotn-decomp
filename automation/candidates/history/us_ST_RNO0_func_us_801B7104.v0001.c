/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO0:func_us_801B7104
   score  : 5750
   receipt: nonmatchings/.adapt-scores/20260824-195225-1950-050609/func_us_801B7104/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno0/func_us_801b7104.c
   asm    : asm/us/st/rno0/nonmatchings/func_us_801b7104/func_us_801B7104.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Primitive g_PrimBuf[];

extern EInit RNO0_EInitCommon;
extern u8 D_us_80180FDC[];
extern s16 D_us_80180FE8[];

void func_us_801B7104(Entity* self) {
    Primitive* prim;
    u8* dataPtr;
    s16* coordData;
    s16 primIndex;
    s16 step;
    s16 params;
    s16 posX;
    s16 posY;
    s16 i;

    step = self->step;
    params = self->params;

    if (step == 0) {
        InitializeEntity(RNO0_EInitCommon);
        self->animCurFrame = 0;
        self->zPriority = 0x9E;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 3);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->primIndex = primIndex;
        self->flags |= 0x800000;
        prim = &g_PrimBuf[primIndex];
        dataPtr = (u8*)D_us_80180FDC;
        while (prim != NULL) {
            prim->tpage = 0xF;
            prim->clut = 0x3E;
            prim->u0 = prim->u2 = dataPtr[0];
            prim->u1 = prim->u3 = dataPtr[1];
            prim->v0 = prim->v1 = dataPtr[2];
            prim->v2 = prim->v3 = dataPtr[3];
            prim->drawMode = 2;
            prim->priority = self->zPriority + 1;
            prim = prim->next;
            dataPtr += 4;
        }
        self->step = 3;
    }

    if (step != 2) {
        coordData = (s16*)((u8*)D_us_80180FE8 + (((params * 2) + 1) * 0x18));
        prim = &g_PrimBuf[self->primIndex];
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;
        while (prim != NULL) {
            prim->x0 = prim->x2 = posX + coordData[0];
            prim->x1 = prim->x3 = posX + coordData[2];
            prim->y0 = prim->y1 = posY + coordData[4];
            prim->y2 = prim->y3 = posY + coordData[6];
            prim = prim->next;
            coordData += 8;
        }
    }
}
