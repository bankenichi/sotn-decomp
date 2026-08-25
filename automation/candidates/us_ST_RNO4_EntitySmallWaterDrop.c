/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntitySmallWaterDrop
   source : upstream/master:src/st/water_effects.h
   target : src/st/rno4/unk_52ED0.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
s32 Random();
void MoveEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_pspeu_0924B480);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntityAlucardWaterEffect);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntitySplashWater);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntitySurfacingWater);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntitySideWaterSplash);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCommon;

void EntitySmallWaterDrop(Entity* self) {
    u16 params = self->params;
    s16 upperParams = params & 0xFF00;
    Primitive *prim, *prim2;
    s32 primIndex;
    s32 xVel;
    s16 x, y;

    params &= 0xFF;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        primIndex = g_api.AllocPrimitives(PRIM_TILE, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];

        x = self->posX.i.hi;
        y = self->posY.i.hi;
        y -= Random() & 3;

        if (upperParams > 0) {
            x += Random() & 3;
        } else {
            x -= Random() & 3;
        }
        self->posX.i.hi = x;
        self->posY.i.hi = y;

        while (prim != NULL) {
            prim->u0 = 2;
            prim->v0 = 2;
            prim->x0 = x;
            prim->y0 = y;
            prim->r0 = 96;
            prim->g0 = 96;
            prim->b0 = 128;
            prim->priority = self->zPriority + 2;
            prim->drawMode =
                DRAW_TPAGE2 | DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;
            prim = prim->next;
        }
        xVel = g_SmallWaterDropVel[params * 2];
        if (upperParams > 0) {
            xVel = -xVel;
        }
        self->velocityX = xVel + (upperParams * 16);
        self->velocityY = g_SmallWaterDropVel[params * 2 + 1];
        self->ext.waterEffects.accelY = FIX(0.25);
        break;

    case 1:
        MoveEntity(self);
        self->velocityY += self->ext.waterEffects.accelY;
        break;
    }

    x = self->posX.i.hi;
    y = self->posY.i.hi;

    prim = &g_PrimBuf[self->primIndex];
    prim->x0 = x;
    prim->y0 = y;
    if (prim->b0 >= 8) {
        prim->b0 -= 8;
        prim->r0 = prim->g0 -= 6;
    } else {
        DestroyEntity(self);
        return;
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntityWaterDrop);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D511C);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D58FC);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D5BA4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", StepTowards);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D5DC8);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D5E90);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D68E0);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D6B8C);
