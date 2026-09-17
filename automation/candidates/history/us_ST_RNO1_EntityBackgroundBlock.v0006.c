/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO1:EntityBackgroundBlock
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rno1/unk_25E28.c
   target : src/st/rno1/unk_25E28.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
u8 AnimateEntity(u8 frames[], Entity* entity);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCommon;
extern GameApi g_api;
extern Primitive g_PrimBuf[];

void EntityBackgroundBlock(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    Rno1BackgroundBlockInit* init;

    init = &BackgroundBlockInit[self->params];

    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = init->animSet;
        self->zPriority = init->zPriority;
        self->unk5A = init->unk5A;
        self->palette = init->palette;
        self->drawFlags = init->drawFlags;
        self->blendMode = init->blendMode;
        if (init->flags) {
            self->flags = init->flags;
        }

        if (self->params == 6) {
            primIndex = g_api.AllocPrimitives(PRIM_TILE, 1);
            if (primIndex == -1) {
                DestroyEntity(self);
                return;
            }

            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            prim->u0 = 0x30;
            prim->v0 = 0x50;
            prim->r0 = prim->g0 = prim->b0 = 0x10;
            prim->x0 = self->posX.i.hi - 0x30;
            prim->y0 = self->posY.i.hi - 0x28;
            prim->priority = self->zPriority - 1;
            prim->drawMode = DRAW_UNK02;
        }
    }

    AnimateEntity(init->animFrames, self);
}
