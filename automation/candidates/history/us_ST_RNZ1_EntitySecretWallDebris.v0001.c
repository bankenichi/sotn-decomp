/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntitySecretWallDebris
   source : upstream/master:src/st/nz0/e_left_secret_room_wall.c
   target : src/st/rnz1/unk_276A8.c
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
s32 Random();
int rcos(int a);
int rsin(int a);
void MoveEntity();
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysLarge);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearHorizontal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearVertical);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

void EntitySecretWallDebris(Entity* self) {
    Collider collider;
    Entity* newEntity;
    s32 range;
    s16 angle;
    s32 i;
    s32 x;
    s32 y;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnemy3);
        self->drawFlags = ENTITY_ROTATE;

        if (Random() & 1) {
            self->animCurFrame = 1;
        } else {
            self->animCurFrame = 2;
        }

        range = (Random() & 0x1F) + 16;
        angle = ((Random() & 0x3F) * 16) + 0xC00;
        if (self->params) {
            self->animCurFrame = 3;
            range = (Random() & 0x1F) + 16;
            angle = (Random() * 6) + 0x900;
        }

        self->velocityX = range * rcos(angle);
        self->velocityY = range * rsin(angle);
        if (self->velocityX < 0) {
            self->facingLeft = 1;
        }
    case 1:
        MoveEntity();
        self->rotate += 0x20;
        if (self->params) {
            self->rotate += 0x20;
        }

        self->velocityY += FIX(0.125);
        x = self->posX.i.hi;
        y = self->posY.i.hi + 6;
        g_api.CheckCollision(x, y, &collider, 0);
        if (collider.effects & EFFECT_SOLID) {
            self->posY.i.hi += collider.unk18;
            if (!self->params) {
                PlaySfxPositional(SFX_WALL_DEBRIS_B);
                for (i = 0; i < 2; i++) {
                    newEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                    if (newEntity != NULL) {
                        CreateEntityFromEntity(
                            E_ID(WALL_DEBRIS), self, newEntity);
                        newEntity->params = 1;
                    }
                }
                DestroyEntity(self);
                break;
            }
            if (self->velocityY < FIX(0.5)) {
                newEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (newEntity != NULL) {
                    CreateEntityFromEntity(
                        E_INTENSE_EXPLOSION, self, newEntity);
                    newEntity->params = 16;
                }
                DestroyEntity(self);
                break;
            }
            self->velocityY = -self->velocityY * 2 / 3;
        }
        break;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWaterForeground);
