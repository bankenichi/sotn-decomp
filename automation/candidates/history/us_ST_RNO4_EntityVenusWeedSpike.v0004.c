/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO4:EntityVenusWeedSpike
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_venus_weed.h
   target : src/st/rno4/e_blue_venus_weed.c
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
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetupPrimsForEntitySpriteParts();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", SetupPrimsForEntitySpriteParts);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeed);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedFlower);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedTendril);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedDart);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitVenusWeedFlower;
extern GameApi g_api;
extern Primitive g_PrimBuf[];

void EntityVenusWeedSpike(Entity* self) {
    const int SpikeParts = 5;

    typedef enum Step {
        INIT = 0,
        EXTEND = 1,
    };

    Primitive* prim;
    Primitive* primItr;
    Primitive* primNext;
    s32 primIdx;
    Entity* entity;
    s16 clut;

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitVenusWeedFlower);

        self->flags |= FLAG_UNK_2000 | FLAG_UNK_00200000;
        self->hitboxState = 0;
        self->palette = PAL_FLAG(SPIKE_CLUT_START);

        primIdx = g_api.AllocPrimitives(PRIM_GT4, SpikeParts);
        if (primIdx == -1) {
            DestroyEntity(self);
            break;
        } else {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIdx;
            prim = &g_PrimBuf[primIdx];
            self->ext.venusWeedSpike.firstPart = prim;

            entity = self->ext.venusWeedSpike.flower;
            entity--;
            prim = self->ext.venusWeedSpike.firstPart;


            prim = SetupPrimsForEntitySpriteParts(entity, prim);



            for (primItr = entity->ext.venusWeedSpike.firstPart;
                 primItr != NULL; primItr = primItr->next, prim = primNext) {
                primNext = prim->next;

                *prim = *primItr;
                prim->next = primNext;
                prim->priority = primItr->priority + 1;
            }
        }


        entity = entity + 1;
        self->animCurFrame = entity->animCurFrame;
        self->zPriority = entity->zPriority + 1;

    case EXTEND:
        clut = self->palette & 0xFFF;



        prim = self->ext.venusWeedSpike.firstPart;
        while (prim != NULL) {
            prim->clut = clut;
            prim->drawMode = DRAW_UNK02;

            prim = prim->next;
        }


        entity = self->ext.venusWeedSpike.flower;
        self->animCurFrame = entity->animCurFrame;
        self->palette++;
        clut = self->palette & 0xFFF;
        if (clut > SPIKE_CLUT_END) {
            DestroyEntity(self);
        } else {
            if (entity->entityId != E_VENUS_WEED_FLOWER) {
                DestroyEntity(self);
            }
        }
        break;
    }
}

