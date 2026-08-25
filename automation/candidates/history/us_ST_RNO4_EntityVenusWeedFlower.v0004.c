/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO4:EntityVenusWeedFlower
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
void PlaySfxPositional(s32 arg0);
void InitializeEntity(u16 arg0[]);
s32 GetSideToPlayer(void);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
long ratan2(long y, long x);
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int AnimateEntity();
extern int SetSubStep();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", SetupPrimsForEntitySpriteParts);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeed);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitVenusWeedFlower;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern u32 g_Timer;

void EntityVenusWeedFlower(Entity* self) {
    const int HitboxOffsetX = 6;
    const int HitboxOffsetY = -16;
    const int HitboxWidth = 14;
    const int HitboxHeight = 14;
    const int AnimFrameInit = 1;
    const int GrowSpeed = 6;
    const int GrowLimit = 0x100;
    const int DartsSfxpose = 3;
    const int DartsLaunchPosOffsetX = 0x18;
    const int DartsLaunchPosOffsetY = 0x18;
    const int DartsAngleLeft = 0x800;
    const int DartsAngleMaxUp = 0x380;
    const int DartsAngleMaxDown = 0x300;
    const int DartsAngleDelta = 0x60;
    const int DartsCount = 5;

    typedef enum Step {
        INIT,
        GROW,
        REVEAL,
        IDLE,
        SPIKES,
        DARTS,
        DEATH = 8,
    };

    typedef enum Spikes_Substep {
        SPIKES_INIT,



        SPIKES_CHARGE,
        SPIKES_SPAWN,
        SPIKES_LAUNCH,
        SPIKES_ANIM_RESET,
        SPIKES_RESET_TO_IDLE,
    };

    typedef enum Darts_Substep {
        DARTS_INIT,
        DARTS_DELAY,
        DARTS_CHARGE,
        DARTS_LAUNCH,
        DARTS_RESET_TO_IDLE,
    };

    Entity* entity;
    s32 x;
    s16 rot;
    s32 i;
    s32 rotDelta;
    s32 spikeStartTimeOffsetIndex;
    s32 y;







    if (self->hitFlags & 3) {
        PlaySfxPositional(SFX_VENUS_WEED_HURT);


        entity = self - 1;
        entity->ext.venusWeed.wiggleT = 0x40;
    }

    if ((self->flags & FLAG_DEAD) && (self->step < DEATH)) {
        PlaySfxPositional(SFX_VENUS_WEED_DEATH);
        SetStep(DEATH);
    }

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitVenusWeedFlower);
        self->hitboxOffX = HitboxOffsetX;
        self->hitboxOffY = HitboxOffsetY;
        self->hitboxWidth = HitboxWidth;
        self->hitboxHeight = HitboxHeight;
        self->animCurFrame = AnimFrameInit;
        self->drawFlags |= ENTITY_SCALEX | ENTITY_SCALEY;
        self->scaleX = self->scaleY = 0;
        self->hitboxState = 0;
        break;

    case GROW:
        self->scaleX = self->scaleY += GrowSpeed;
        if (self->scaleX >= GrowLimit) {
            self->drawFlags = ENTITY_DEFAULT;
            self->hitboxState = 3;

            PlaySfxPositional(SFX_MAGIC_WEAPON_APPEAR_A);
            SetStep(REVEAL);
        }
        break;

    case REVEAL:
        if (AnimateEntity(AnimFrames_Reveal, self) == 0) {

            entity = self - 1;
            entity->step = VENUS_WEED_IDLE;
            entity->step_s = 0;

            SetStep(IDLE);
        }
        break;

    case IDLE:

        if (!self->step_s) {
            self->ext.venusWeedFlower.triggerAttack = 1;
            self->step_s++;
        }


        if (AnimateEntity(AnimFrames_FlowerPulse, self) == 0) {
            self->facingLeft = GetSideToPlayer() & 1;
        }


        if (!--self->ext.venusWeedFlower.triggerAttack) {

            self->facingLeft = GetSideToPlayer() & 1;







            if (self->ext.venusWeedFlower.nextAttackIsDarts) {
                SetStep(DARTS);
            } else {
                SetStep(SPIKES);
            }

            self->ext.venusWeedFlower.nextAttackIsDarts ^= 1;

        }
        break;

    case SPIKES:
        switch (self->step_s) {
        case SPIKES_INIT:





            entity = self - 1;
            entity->step = VENUS_WEED_ATTACK;
            entity->step_s = 0;



            entity = self + 1;
            for (i = 0; i < TENDRIL_COUNT; i++, entity++) {



                entity->step = VENUS_WEED_TENDRIL_ATTACK;
                entity->step_s = VENUS_WEED_TENDRIL_ATTACK_INIT;

            }

            self->step_s++;












        case SPIKES_CHARGE:
            if (!AnimateEntity(AnimFrames_FlowerAttackSpikesCharge, self)) {
                SetSubStep(SPIKES_SPAWN);
            }
            break;
        case SPIKES_SPAWN:
            PlaySfxPositional(SFX_GLASS_SHARDS);


            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_VENUS_WEED_SPIKE, self, entity);
                entity->facingLeft = self->facingLeft;
                entity->ext.venusWeedSpike.flower = self;
            }
            self->step_s++;

        case SPIKES_LAUNCH:
            if (AnimateEntity(AnimFrames_FlowerAttackSpikesLaunch, self) == 0) {
                entity = self + 1;

                if (g_Timer & 1) {
                    spikeStartTimeOffsetIndex = 0;
                } else {
                    spikeStartTimeOffsetIndex = 4;
                }

                for (i = 0; i < TENDRIL_COUNT; i++, entity++) {



                    entity->ext.venusWeedTendril.spikeStartTimeOffsetIndex =
                        spikeStartTimeOffsetIndex + 1;
                    spikeStartTimeOffsetIndex++;
                    spikeStartTimeOffsetIndex &= 0x7;

                }
                SetSubStep(SPIKES_ANIM_RESET);
            }
            break;

        case SPIKES_ANIM_RESET:
            if (AnimateEntity(AnimFrames_FlowerAttackSpikesReset, self) == 0) {
                SetSubStep(SPIKES_RESET_TO_IDLE);
            }
            break;

        case SPIKES_RESET_TO_IDLE:

            entity = self - 1;
            entity->step = VENUS_WEED_IDLE;

            SetStep(IDLE);
            break;
        }


        if (self->ext.venusWeedFlower.clutOffset) {
            entity = self - 1;
            entity->ext.venusWeed.triggerAttack = true;
            if (!(self->palette & PAL_UNK_FLAG)) {
                self->palette += self->ext.venusWeedFlower.clutOffset;
                if (self->palette > 0x219) {
                    self->palette = 0x219;
                }
                self->ext.venusWeedFlower.clutOffset = 0;
                return;
            }
        }

        break;

    case DARTS:
        switch (self->step_s) {
        case DARTS_INIT:
            entity = self - 1;
            entity->step = 6;
            entity->step_s = 0;

            self->step_s += 1;

        case DARTS_DELAY:
            if (AnimateEntity(AnimFrames_FlowerAttackDartsCharge, self) == 0) {
                SetSubStep(DARTS_CHARGE);
            }
            break;

        case DARTS_CHARGE:
            PlaySfxPositional(SFX_GLASS_SHARDS);
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_VENUS_WEED_SPIKE, self, entity);
                entity->facingLeft = self->facingLeft;
                entity->ext.venusWeedSpike.flower = self;
            }
            self->step_s++;

        case DARTS_LAUNCH:
            if (AnimateEntity(AnimFrames_FlowerAttackDartsLaunch, self) == 0) {
                self->step_s++;
            }
            if (!self->poseTimer && self->pose == DartsSfxpose) {
                PlaySfxPositional(SFX_ARROW_SHOT_B);


                if (self->facingLeft) {
                    x = self->posX.i.hi - DartsLaunchPosOffsetX;
                } else {
                    x = self->posX.i.hi + DartsLaunchPosOffsetX;
                }
                y = self->posY.i.hi - DartsLaunchPosOffsetY;


                entity = &PLAYER;
                rot = ratan2(entity->posY.i.hi - y, entity->posX.i.hi - x);
                if (self->facingLeft) {
                    if (rot < 0) {
                        if (rot > -DartsAngleLeft + DartsAngleMaxUp) {
                            rot = -DartsAngleLeft + DartsAngleMaxUp;
                        }
                        rotDelta = -DartsAngleDelta;
                    } else {
                        if (rot < DartsAngleLeft - DartsAngleMaxDown) {
                            rot = DartsAngleLeft - DartsAngleMaxDown;
                        }
                        rotDelta = DartsAngleDelta;
                    }
                } else if (rot < 0) {
                    if (rot < -DartsAngleMaxUp) {
                        rot = -DartsAngleMaxUp;
                    }
                    rotDelta = DartsAngleDelta;
                } else {
                    if (rot > DartsAngleMaxDown) {
                        rot = DartsAngleMaxDown;
                    }
                    rotDelta = -DartsAngleDelta;
                }


                for (i = 0; i < DartsCount; i++) {
                    entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
                    if (entity != NULL) {
                        CreateEntityFromEntity(E_VENUS_WEED_DART, self, entity);
                        entity->rotate = rot;
                        entity->params = i;
                        entity->posX.i.hi = x;
                        entity->posY.i.hi -= DartsLaunchPosOffsetY;
                    }
                    rot += rotDelta;
                }
            }
            break;

        case DARTS_RESET_TO_IDLE:
            entity = self - 1;
            entity->step = VENUS_WEED_IDLE;
            SetStep(IDLE);
        }
        break;

    case DEATH:

        entity = self + 1;
        for (i = 0; i < TENDRIL_COUNT; i++, entity++) {
            entity->flags |= FLAG_DEAD;
        }

        PlaySfxPositional(SFX_FM_EXPLODE_B);
        self->hitboxState = 0;

        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->params = 3;
        }


        entity = self - 1;
        entity->flags |= FLAG_DEAD;

        DestroyEntity(self);
        return;
    }














}


INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedTendril);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedDart);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedSpike);
