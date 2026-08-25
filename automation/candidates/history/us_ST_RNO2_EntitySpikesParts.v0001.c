/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:EntitySpikesParts
   source : upstream/master:src/st/e_spikes.h
   target : src/st/rno2/e_spikes.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
s32 Random();
void MoveEntity();
int abs(int x);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesDust);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;

void EntitySpikesParts(Entity* self) {
    Collider collider;
    s16 posX, posY;
    u8 params;

    switch (self->step) {
    case SPIKES_PARTS_INIT:
        InitializeEntity(g_EInitEnvironment);
#ifdef SPIKES_PARTS_FRAME
        self->animCurFrame = SPIKES_PARTS_FRAME;
#endif
        self->drawFlags |= ENTITY_ROTATE;
        self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA |
                       FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA;
        self->zPriority = 160;
        self->velocityX = 0;
        self->velocityY = 0;
        self->rotate = 0;
        self->ext.spikes.rotate = 0;
#ifdef HAS_ORIENTATIONS
        params = (self->params & 0xFF00) >> 8;
#else
        params = self->params;
#endif
        if (params & 1) {
            self->velocityX = FIX(0.5);
            self->rotate += ROT(1.40625);
            self->ext.spikes.rotate += 8;  
        }
        if (params & 2) {
            self->velocityX = FIX(-0.5);
            self->rotate -= ROT(1.40625);
            self->ext.spikes.rotate -= 8;
        }
#ifdef HAS_ORIENTATIONS
        params = self->params & 0xFF;
        if (params & SPIKES_POINT_LEFT) {
            self->velocityX -= FIX(0.75);
            self->rotate -= ROT(90);
            self->ext.spikes.rotate += ROT(5.625);
        }
        if (params & SPIKES_POINT_RIGHT) {
            self->velocityX += FIX(0.75);
            self->rotate += ROT(90);
            self->ext.spikes.rotate -= ROT(5.625);
        }
        if (params & SPIKES_ON_CEILING) {
            self->velocityY += FIX(0.75);
            self->rotate -= ROT(180);
        }
        if (params & SPIKES_ON_FLOOR) {
            self->velocityY -= FIX(2.5);
        }
#else
        self->velocityY += FIX(0.75);
#endif
        self->velocityX += ((Random() & 3) << 13) - FIX(0.1875);
        self->velocityY += ((Random() & 3) << 13) - FIX(0.1875);
         
         
        self->ext.spikes.rotate += ((Random() & 3) * 16) - 24;
        break;
    case SPIKES_PARTS_MOVE:
        MoveEntity();
        self->velocityY += FIX(0.15625);
        self->rotate += self->ext.spikes.rotate;
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;
        g_api.CheckCollision(posX, posY, &collider, 0);
        if (collider.effects) {
            if (collider.effects & EFFECT_SOLID) {
                self->velocityY = -self->velocityY / 2;
                self->ext.spikes.rotate *= 4;
            }
            if (collider.effects & EFFECT_UNK_0002) {
                self->velocityX = -self->velocityX;
            }
            if (abs(self->velocityY) < FIX(0.1875)) {
                DestroyEntity(self);
            }
        }
        break;
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", SpikesBreak);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", SpikesApplyDamage);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikes);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesDamage);

INCLUDE_RODATA("st/rno2/nonmatchings/e_spikes", D_us_801B1C4C);
