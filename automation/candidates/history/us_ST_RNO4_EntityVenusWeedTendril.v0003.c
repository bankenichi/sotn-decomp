/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:ST/RNO4:EntityVenusWeedTendril
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
s32 Random();
int abs(int x);
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int UnkCollisionFunc3();
extern int AnimateEntity();
extern int UnkCollisionFunc2();
extern int SetSubStep();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", SetupPrimsForEntitySpriteParts);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeed);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedFlower);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitVenusWeedTendril;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityVenusWeedTendril(Entity* self) {
    const int InitDistMinX = 0x18;
#if defined(BLUE)
    const int InitDistRandRangeX = 0x1F;  
#else
    const int InitDistRandRangeX = 0xF;  
#endif
    const int SpikeSfxpose = 0xA;

    s32 x;
    s8* hitboxData;
    Entity* entity;
    u32 hitboxIndex;

    if ((self->flags & FLAG_DEAD) && (self->step < VENUS_WEED_TENDRIL_DEATH)) {
        SetStep(VENUS_WEED_TENDRIL_DEATH);
    }

    switch (self->step) {
    case VENUS_WEED_TENDRIL_INIT:
        InitializeEntity(g_EInitVenusWeedTendril);
        self->animCurFrame = 0;
        break;

    case VENUS_WEED_TENDRIL_DROP_TO_GROUND:
        if (UnkCollisionFunc3(PhysicsSensors) & 1) {
            SetStep(VENUS_WEED_TENDRIL_MOVE_TO_RANDOM_POSITION);
        }
        break;

    case VENUS_WEED_TENDRIL_MOVE_TO_RANDOM_POSITION:
         
        if (!self->step_s) {
#if defined(BLUE)
            x = self->params * 0x20 - (TENDRIL_COUNT - 1) * 0x10;
#else
            x = self->params * 2 - (TENDRIL_COUNT - 1);
            x = x * x;
            if (self->params < (TENDRIL_COUNT / 2)) {
                x = -x;
            }
#endif
            if (x > 0) {
                x += InitDistMinX;
            } else {
                x -= InitDistMinX;
            }
            x += (Random() & (InitDistRandRangeX * 2 + 1)) - InitDistRandRangeX;
            self->ext.venusWeedTendril.targetX = x;
            self->step_s++;
        }

        AnimateEntity(AnimFrames_TendrilBounce, self);
        UnkCollisionFunc2(WalkSensors_Tendril);  

#if defined(BLUE)
        entity = &PLAYER;
        x = entity->posX.i.hi - self->posX.i.hi;
        if (abs(x) > 24) {
             
            entity = self - 1 - self->params;  
            x = entity->posX.i.hi + self->ext.venusWeedTendril.targetX;
            x -= self->posX.i.hi;  
        }
        if (abs(x) < 2) {
            SetStep(VENUS_WEED_TENDRIL_STEP5);
        } else if (x > 0) {
            self->velocityX = (abs(x) << 0xC);
        } else {
            self->velocityX = (-(abs(x) << 0xC));
        }
        if (self->ext.venusWeedTendril.unk93) {
            self->ext.venusWeedTendril.unk93 = 0;
            entity = self - 1 - self->params;
            entity->ext.venusWeedTendril.unk93++;
            SetStep(VENUS_WEED_TENDRIL_ATTACK);
        }
        break;
    case VENUS_WEED_TENDRIL_STEP5:
        if (AnimateEntity(D_pspeu_09258EA0, self) == 0) {
            SetStep(VENUS_WEED_TENDRIL_ATTACK);
            self->step_s = 1;
            self->pose = 8;
        }
#else
         
        entity = self - 1 - self->params;  
        x = entity->posX.i.hi + self->ext.venusWeedTendril.targetX;
        x -= self->posX.i.hi;  

        if (abs(x) < 2) {
            self->step_s--;
        } else if (x > 0) {
            self->velocityX = (abs(x) << 0xC) / 4;
        } else {
            self->velocityX = (-(abs(x) << 0xC)) / 4;
        }
#endif
        break;
    case VENUS_WEED_TENDRIL_ATTACK:
        switch (self->step_s) {
        case VENUS_WEED_TENDRIL_ATTACK_INIT:
            AnimateEntity(AnimFrames_TendrilBounce, self);
            if (self->ext.venusWeedTendril.spikeStartTimeOffsetIndex) {
#if !defined(BLUE)
                self->ext.venusWeedTendril.timer = TendrilSpikeStartTimeOffset
                    [self->ext.venusWeedTendril.spikeStartTimeOffsetIndex - 1];
#endif
                self->ext.venusWeedTendril.spikeStartTimeOffsetIndex = 0;
                SetSubStep(1);  
            }
            break;
#if !defined(BLUE)
        case VENUS_WEED_TENDRIL_ATTACK_DELAY:
            if (self->ext.venusWeedTendril.timer) {
                self->ext.venusWeedTendril.timer--;
                break;
            }
            self->step_s++;
             
#endif
        case VENUS_WEED_TENDRIL_ATTACK_CHARGE:
            if (AnimateEntity(AnimFrames_TendrilAttackCharge, self) == 0) {
                SetSubStep(VENUS_WEED_TENDRIL_ATTACK_LAUNCH);
            }
            if (!self->poseTimer && self->pose == SpikeSfxpose) {
                PlaySfxPositional(SFX_VENUS_WEED_CHARGE_ATTACK);
            }
            break;

        case VENUS_WEED_TENDRIL_ATTACK_LAUNCH:
            if (AnimateEntity(AnimFrames_TendrilAttackLaunch, self) == 0) {
                SetStep(VENUS_WEED_TENDRIL_MOVE_TO_RANDOM_POSITION);
            }
            break;
        }
        if (self->hitFlags & 0x80) {
            entity = self - 1 - self->params;  
            entity->ext.venusWeedFlower.clutOffset++;
        }
        break;

    case VENUS_WEED_TENDRIL_DEATH:
        if (!self->step_s) {
            self->ext.venusWeedTendril.timer = self->params * 8 +
#if defined(BLUE)
                                               1;
#else
                                               8;
#endif
            self->step_s++;
        }
        if (!--self->ext.venusWeedTendril.timer) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, entity);
                entity->params = 2;
                entity->posY.i.hi -= 0xC;
            }
            PlaySfxPositional(SFX_EXPLODE_B);
            DestroyEntity(self);
            return;
        }
        break;
    }

     
    hitboxData = HitboxData_Tendril;
    hitboxIndex = HitboxIndices_Tendril[self->animCurFrame - 0x22];
    hitboxData += hitboxIndex * 4;  
    self->hitboxOffX = *hitboxData++;
    self->hitboxOffY = *hitboxData++;
    self->hitboxWidth = *hitboxData++;
    self->hitboxHeight = *hitboxData++;
}

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedDart);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedSpike);
