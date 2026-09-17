/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCHI:EntityBreakableWallDebris
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rchi/e_rchi_breakable_wall_debris.h
   target : src/st/rchi/e_breakable_wall.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

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

/*
 * The reverse-stage wall mirrors velocity, tile traversal, positions, and map
 * coordinates throughout both functions; it is not a constants-only CHI port.
 */
// EntityBreakableWallDebris's candidate failed to build on this name alone.
// Declared in the shared src/st/e_fire_warg.h:11. An unused extern emits no
// code; this only removes the wall the retry would hit again.
extern EInit g_EInitCommon;

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180648;
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityBreakableWallDebris(Entity* self) {
    typedef enum Step {
        INIT = 0,
        CHECK_FLAG = 1,
        MOVEMENT = 2,
    } Step;

    Collider col;
    Entity* entity;
    s16 posX, posY;
    s32 i;

    switch (self->step) {
    case INIT:
        InitializeEntity(D_us_80180648);
        self->animCurFrame = self->params & 0xFF;
        self->drawFlags = ENTITY_ROTATE;
        self->zPriority = 0x69;
        if (self->rotate & 1) {
            self->facingLeft = true;
            self->rotate &= 0xFFF0;
        }

        self->velocityX = (-(Random() & 0xF)) << 0xC;
        if (self->animCurFrame == 0xD) {
            self->velocityX -= FIX(0.25);
        }
        self->velocityY = ((Random() & 7) << 0xB) - FIX(0.25);
        if (self->animCurFrame < 0xB) {
            self->velocityY -= FIX(1);
        }
        self->ext.breakableDebris.rotSpeed = ((Random() & 3) + 1) * 0x20;
        break;

    case CHECK_FLAG:
        if (self->params & 0x100) {
            self->params &= 0xFF;
            self->step++;
        }
        break;

    case MOVEMENT:
        self->rotate += self->ext.breakableDebris.rotSpeed;
        MoveEntity();
        self->velocityY += FIX(0.125);

        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 6;
        g_api.CheckCollision(posX, posY, &col, 0);
        if (col.effects & EFFECT_SOLID) {
            self->posY.i.hi += col.unk18;
            if (self->animCurFrame > 0xB) {
                for (i = 0; i < 2; i++) {
                    entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                    if (entity != NULL) {
                        CreateEntityFromEntity(
                            E_ID(BREAKABLE_WALL_DEBRIS), self, entity);
                        entity->params = (Random() & 3) + 9;
                        entity->params |= 0x100;
                    }
                }
                DestroyEntity(self);
                return;
            }

            if (self->velocityY < FIX(0.5)) {
                entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (entity != NULL) {
                    CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, entity);
                    entity->params = 0x10;
                    entity->params |= 0xC000;
                }
                DestroyEntity(self);
                return;
            }

            self->velocityY = -self->velocityY * 2 / 3;
        }
        break;
    }
}


INCLUDE_ASM("st/rchi/nonmatchings/e_breakable_wall", EntityBreakableWall);
