/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntitySideWaterSplash
   source : upstream/master:src/st/water_effects.h
   target : src/st/rnz1/unk_37BF8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
int rcos(int a);
int rsin(int a);
void MoveEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", func_pspeu_0924B480);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntityAlucardWaterEffect);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySplashWater);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySurfacingWater);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCommon;
extern u16 g_WaterSounds[];

void EntitySideWaterSplash(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 velY;
    u16 params;
    s16 angle;
    s32 velX;
    s16 y;
    s16 x;
    s32* speedPtr;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        while (prim != NULL) {
            prim->u0 = prim->u2 = 0xF0;
            prim->u1 = prim->u3 = 0xFF;
            prim->v0 = prim->v1 = 0;
            prim->v2 = prim->v3 = 0xF;
            prim->clut = PAL_CC_STONE_EFFECT;
            prim->tpage = 0x1A;
            PGREY(prim, 0) = PGREY(prim, 1) = 128;
            PGREY(prim, 2) = PGREY(prim, 3) = 128;

            prim->p1 = 0;
            prim->priority = self->zPriority + 2;
            prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS |
                             DRAW_UNK02 | DRAW_TRANSP;
            prim = prim->next;
        }
        params = self->params;
        if (!(params & 0xF)) {
            g_api.PlaySfx(g_WaterSounds[0]);
        }
        angle = g_SideWaterAngles[(params >> 4) & 0xF];
         
        speedPtr = &g_SideWaterSpeeds[(params & 0xF) * 2];
        velX = rcos(angle) * *speedPtr;
        velY = rsin(angle + 0x800) * *speedPtr++;  
         
        velX += rsin(angle) * *speedPtr;
        velY += rcos(angle) * *speedPtr;
        velX += (s16)(params & 0xFF00) * 4;
        self->velocityX = velX;
        self->velocityY = velY;
        self->ext.waterEffects.accelY = FIX(22.0 / 128);
        break;

    case 1:
        MoveEntity(self);
        self->velocityY += self->ext.waterEffects.accelY;
        break;
    }

    x = self->posX.i.hi;
    y = self->posY.i.hi;

    prim = &g_PrimBuf[self->primIndex];
    while (prim != NULL) {
        prim->x0 = prim->x2 = x - (prim->p1 / 2) - 4;
        prim->x1 = prim->x3 = x + (prim->p1 / 2) + 4;
        prim->y0 = prim->y1 = y - (prim->p1 / 2) - 4;
        prim->y2 = prim->y3 = y + (prim->p1 / 2) + 4;
        if (prim->b1 >= 3) {
            prim->b1 -= 3;
        } else {
            DestroyEntity(self);
            return;
        }
        PGREY(prim, 0) = PGREY(prim, 1);
        if (prim->b3 >= 4) {
            prim->b3 -= 4;
        }
        PGREY(prim, 2) = PGREY(prim, 3);
        prim->p1++;
        prim = prim->next;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySmallWaterDrop);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntityWaterDrop);
