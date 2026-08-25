/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntityVenusWeedDart
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
int rcos(int a);
int rsin(int a);
void MoveEntity();
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", SetupPrimsForEntitySpriteParts);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeed);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedFlower);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedTendril);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitVenusWeedDart;
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityVenusWeedDart(Entity* self) {
    const int AnimFrameIndexInit = 0x37;
    const int StartSpeed = 0x8000;
    const int SpeedMax = 0x60000;
    const int AccelInc = 0x800;
    const int AccelMax = 0x10000;
    const int ClutIdxWallHit = 0x20;
    const int ClutIdxPlayerHit = 0x00;
    const int ClutIdxMax = 0x30;

    typedef enum Step {
        INIT = 0,
        FLY = 1,
        DECAY = 2,
        DEATH = 3,
    };

    Collider collider;
    Entity* entity;
    s16 rot;
    s32 x;
    s32 speed;
    s32 y;

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitVenusWeedDart);
        self->animCurFrame = AnimFrameIndexInit;
        self->drawFlags = ENTITY_ROTATE;
        rot = self->rotate;
        self->hitboxOffX = (rcos(rot) * 6) >> 0xC;
        self->hitboxOffY = (rsin(rot) * 6) >> 0xC;
        self->ext.venusWeedDart.nextPosDeltaX = rcos(rot) << 3 >> 0xC;
        self->ext.venusWeedDart.nextPosDeltaY = rsin(rot) << 3 >> 0xC;
        self->ext.venusWeedDart.speed = StartSpeed;
         
    case FLY:
        MoveEntity();

        rot = self->rotate;
        speed = self->ext.venusWeedDart.speed;
        self->velocityX = (speed * rcos(rot)) >> 0xC;
        self->velocityY = (speed * rsin(rot)) >> 0xC;
        self->ext.venusWeedDart.speed += self->ext.venusWeedDart.accel;
        self->ext.venusWeedDart.accel += (self->params + 1) * AccelInc;
        if (self->ext.venusWeedDart.accel > AccelMax) {
            self->ext.venusWeedDart.accel = AccelMax;
        }
        if (self->ext.venusWeedDart.speed > SpeedMax) {
            self->ext.venusWeedDart.speed = SpeedMax;
        }

        x = self->posX.i.hi + self->ext.venusWeedDart.nextPosDeltaX;
        y = self->posY.i.hi + self->ext.venusWeedDart.nextPosDeltaY;
        g_api.CheckCollision(x, y, &collider, 0);
        if (collider.effects & EFFECT_SOLID) {
            PlaySfxPositional(SFX_STOMP_HARD_E);
             
            if (self->velocityY > 0) {
                self->posY.i.hi += collider.unk18;
            }
            if (self->velocityY < 0) {
                self->posY.i.hi += collider.unk20;
            }
            self->hitboxState = 0;
            self->ext.venusWeedDart.clutIndex = ClutIdxWallHit;
            SetStep(DEATH);
        }
        if (self->hitFlags & 0x80) {
            entity = &PLAYER;
            self->ext.venusWeedDart.nextPosDeltaX =
                entity->posX.i.hi - self->posX.i.hi;
            self->ext.venusWeedDart.nextPosDeltaY =
                entity->posY.i.hi - self->posY.i.hi;
            self->ext.venusWeedDart.clutIndex = ClutIdxPlayerHit;
            self->hitboxState = 0;
            SetStep(DECAY);
            break;
        }
        if (self->hitParams) {
            self->flags & FLAG_DEAD;  
        }
        break;

    case DECAY:
        if (!(self->palette & PAL_UNK_FLAG)) {
            self->ext.venusWeedDart.clutIndex++;
            self->palette = self->ext.venusWeedDart.clutIndex + DART_CLUT_START;

            if (self->palette > PLANT_CLUT - 1) {
                self->palette = PLANT_CLUT - 1;
            }
        }
        if (self->ext.venusWeedDart.clutIndex > ClutIdxMax) {
            self->flags |= FLAG_DEAD;
        }

         
        entity = &PLAYER;
        self->posX.i.hi =
            entity->posX.i.hi - self->ext.venusWeedDart.nextPosDeltaX;
        self->posY.i.hi =
            entity->posY.i.hi - self->ext.venusWeedDart.nextPosDeltaY;
        break;

    case DEATH:
        if (!--self->ext.venusWeedDart.clutIndex) {
            self->flags |= FLAG_DEAD;
        }
        break;
    }

     
    if (self->flags & FLAG_DEAD) {
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->params = 0;
        }
        DestroyEntity(self);
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedSpike);
