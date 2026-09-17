/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO4:EntityBreakableWallDebris
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rno4/e_breakable_wall.c
   target : src/st/rno4/e_breakable_wall.c
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
s32 Random();
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitParticle;
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityBreakableWallDebris(Entity* self) {
    Collider collider;
    Entity* debris;





    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);
        self->drawFlags = ENTITY_ROTATE;
        self->animSet = ANIMSET_OVL(1);
        if (Random() & 1) {
            self->animCurFrame = 0x26;
        } else {
            self->animCurFrame = 0x27;
        }
        if (self->velocityX < 0) {
            self->facingLeft = 1;
        }
        /* fall through */
    case 1:
        MoveEntity();






        {
            u16 rotation = self->rotate;
            self->rotate = rotation + 0x20;
            if (self->params != 0) {
                self->rotate = rotation + 0x40;
            }
        }

        self->velocityY += FIX(0.125);





        g_api.CheckCollision(
            self->posX.i.hi, self->posY.i.hi + 6, &collider, 0);

        if (collider.effects & EFFECT_SOLID) {





            self->posY.i.hi = (u16)self->posY.i.hi + (u16)collider.unk18;
            if (self->velocityY <= 0x7FFF) {
                debris = AllocEntity(&g_Entities[224], &g_Entities[256]);

                if (debris != 0) {
                    CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, debris);
                    debris->params = 0x10;
                }
                DestroyEntity(self);
                return;
            }
            self->velocityY = (-self->velocityY * 2) / 3;
        }
        break;
    }
}
