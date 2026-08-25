/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntityKillerFish
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/no4/e_killer_fish.c
   target : src/st/rno4/e_killer_fish.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
extern int rand(void);
void MoveEntity();
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitKillerFish;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityKillerFish(Entity* self) {
    Entity* entity;
    s16* ptr;
    s32 i;
    u16 params;

    if (self->flags & FLAG_DEAD && self->step != 4) {
        SetStep(4);
    }

    params = self->params;
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitKillerFish);
        self->facingLeft = params & 1;
        break;
    case 1:
         
         
        if (!AnimateEntity(anim_iddle, self) && !(rand() & 3)) {
            SetStep(2);
            self->ext.killerFish.swimTimer = 0x100;
        }
        break;
    case 2:
         
        if (AnimateEntity(anim_swim, self) & 0x80 &&
            (self->pose == 3 || self->pose == 7)) {
            if (self->facingLeft) {
                self->velocityX = FIX(1.5);
            } else {
                self->velocityX = FIX(-1.5);
            }
        }
        if (self->velocityX != 0) {
            if (self->facingLeft) {
                self->velocityX -= FIX(0.015625);
            } else {
                self->velocityX += FIX(0.015625);
            }
        }
        MoveEntity();
        if (!--self->ext.killerFish.swimTimer) {
            self->velocityX = 0;
            SetStep(3);
        }
        break;
    case 3:
         
        if (!AnimateEntity(anim_rotate, self)) {
            if (self->ext.killerFish.swimCount++ & 1) {
                 
                SetStep(1);
            } else {
                 
                self->ext.killerFish.swimTimer = 0x100;
                SetStep(2);
            }
            self->animCurFrame = 1;
            self->facingLeft ^= 1;
            if (self->facingLeft) {
                self->posX.i.hi += 8;
            } else {
                self->posX.i.hi -= 8;
            }
        }
        break;
    case 4:
         
        PlaySfxPositional(SFX_EXPLODE_B);
        ptr = death_puff_positions[0];

        for (i = 0; i < LEN(death_puff_positions); i++) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity == NULL) {
                break;
            }
            CreateEntityFromCurrentEntity(E_ID(KILLER_FISH_DEATH_PUFF), entity);
            if (self->facingLeft) {
                entity->posX.i.hi += *ptr++;
            } else {
                entity->posX.i.hi -= *ptr++;
            }
            entity->posY.i.hi += *ptr++;
        }

        DestroyEntity(self);
        return;
    }

    params = self->animCurFrame;
    if (params == 9) {
         
        self->hitboxWidth = 6;
        self->hitboxOffX = -0xA;
    } else {
        self->hitboxWidth = 0x14;
        self->hitboxOffX = 0;
        if (params >= 10 && params < 13) {
            self->hitboxWidth = 0x10;
            self->hitboxOffX = 4;
        }
    }
    self->hitboxOffY = 2;
    self->hitboxHeight = 8;
}

#define BLEND_ADD 32
#define BLEND_TRANSP 16
#define ENTITY_OPACITY 8
extern u8 D_us_8018176C[28];
extern EInit g_EInitParticle;
extern struct Entity;
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);

void EntityKillerFishDeathPuff(Entity* self) {
    if (!self->step) {
        InitializeEntity(g_EInitParticle);
        self->pose = 0;
        self->poseTimer = 0;
        self->animSet = 0xE;
        self->unk5A = 0x79;
        self->palette = 0x2E8;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = 0x60;
        if (self->params & 0xFF00) {
            self->zPriority = (self->params & 0xFF00) >> 8;
        }
        self->velocityY += -0x8000 - 0x8000;
        return;
    }

    self->posY.val += self->velocityY;
    if (!AnimateEntity(D_us_8018176C, self)) {
        DestroyEntity(self);
    }
}
