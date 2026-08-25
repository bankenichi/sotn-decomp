/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:EntityKarasumanFeatherAttack
   source : upstream/master:src/st/nz1/e_karasuman.c
   target : src/st/rno2/unk_439A4.c
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
int rcos(int a);
int rsin(int a);
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C39A4);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4960);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4C0C);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4EA8);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasuman);

void EntityKarasumanFeatherAttack(Entity* self) {
    Entity* entity;
    s16 angle;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitKarasumanFeatherAttack);
        self->animCurFrame = 59;
        self->drawFlags |= ENTITY_ROTATE;
        if (Random() & 1) {
            self->facingLeft = true;
        }

        angle = (Random() * 4) - FLT(0.125);
        self->rotate = angle;
        angle = self->rotate;
        if (!self->facingLeft) {
            angle = FLT(0.5) - angle;
        }
        self->velocityX = 96 * rcos(angle);
        self->velocityY = -96 * rsin(angle);
        self->posX.i.hi += FLT_TO_I(32 * rcos(angle));
        self->posY.i.hi += FLT_TO_I(-32 * rsin(angle));
         
    case 1:
        MoveEntity();
        if (self->flags & FLAG_DEAD) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, entity);
                entity->params = 1;
            }
            DestroyEntity(self);
        }
        break;
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanOrbAttack);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanRavenAttack);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanFeather);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanRavenAbsorb);
