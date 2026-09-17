/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO4:EntityVenusWeedTendril
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_venus_weed.h
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
void SetStep(u8 step);
void InitializeEntity(u16 arg0[]);
s32 UnkCollisionFunc3(s16* sensors);
s32 Random();
u8 AnimateEntity(u8 frames[], Entity* entity);
s32 UnkCollisionFunc2(s16* posX);
int abs(int x);
void SetSubStep(u8 step_s);
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define LOH(x) (*(s16*)&(x))
#define SPIKE_SPRITES D_us_801BE9C4
extern signed short* SPIKE_SPRITES[];

static Primitive* SetupPrimsForEntitySpriteParts(
    Entity* entity, Primitive* prim) {
    s16 y;
    s32 spritePartCount;
    s16 x;
    u8 spriteU0;
    u8 spriteV0;
    s16* spriteData;
    s32 i;
    u8 spriteU1;
    s16 spriteDestX;
    s16 spriteDestY;
    s16 spriteDestW;
    s16 spriteDestH;
    s16 spriteFlags;
    u8 spriteV1;
    s32 xFlip;

    spriteData = SPIKE_SPRITES[entity->animCurFrame];
    spritePartCount = *spriteData;
    spriteData++;

    for (i = 0; i < spritePartCount; i++, spriteData += 11) {
        spriteFlags = spriteData[0];
        spriteDestX = spriteData[1];
        spriteDestY = spriteData[2];
        spriteDestW = spriteData[3];
        spriteDestH = spriteData[4];

        // Adjust sprite position to respect sprite flags
        if (spriteFlags & 4) {
            spriteDestW -= 1;
            if (spriteFlags & 2) {
                spriteDestX += 1;
            }
        }
        if (spriteFlags & 8) {
            spriteDestH -= 1;
            if (spriteFlags & 1) {
                spriteDestY += 1;
            }
        }
        if (spriteFlags & 0x10) {
            spriteDestW -= 1;
            if (!(spriteFlags & 2)) {
                spriteDestX += 1;
            }
        }
        if (spriteFlags & 0x20) {
            spriteDestH -= 1;
            if (!(spriteFlags & 1)) {
                spriteDestY += 1;
            }
        }

        // Calculate sprite position to respect facing
        x = entity->posX.i.hi;
        y = entity->posY.i.hi;
        if (entity->facingLeft) {
            x -= spriteDestX;
        } else {
            x += spriteDestX;
        }
        y += spriteDestY;

        // Set sprite position to respect the above, plus sprite dimensions
        if (entity->facingLeft) {
            LOH(prim->x0) = x - spriteDestW + 1;
            LOH(prim->y0) = y;
            LOH(prim->x1) = x + 1;
            LOH(prim->y1) = y;
            LOH(prim->x2) = x - spriteDestW + 1;
            LOH(prim->y2) = y + spriteDestH;
            LOH(prim->x3) = x + 1;
            LOH(prim->y3) = y + spriteDestH;
        } else {
            LOH(prim->x0) = x;
            LOH(prim->y0) = y;
            LOH(prim->x1) = x + spriteDestW;
            LOH(prim->y1) = y;
            LOH(prim->x2) = x;
            LOH(prim->y2) = y + spriteDestH;
            LOH(prim->x3) = x + spriteDestW;
            LOH(prim->y3) = y + spriteDestH;
        }

        // Entity-relative clut
        prim->clut = entity->palette + spriteData[5];

        spriteU0 = spriteData[7];
        spriteV0 = spriteData[8];
        spriteU1 = spriteData[9];
        spriteV1 = spriteData[10];

        // Adjust sprite UVs to respect sprite flags
        if (spriteFlags & 4) {
            spriteU1--;
        }
        if (spriteFlags & 8) {
            spriteV1--;
        }
        if (spriteFlags & 0x10) {
            spriteU0++;
        }
        if (spriteFlags & 0x20) {
            spriteV0++;
        }

        // Set sprite UVs to respect the above, plus facing
        xFlip = (spriteFlags & 2) ^ entity->facingLeft;
        if (!xFlip) {
            if (!(spriteFlags & 1)) {
                prim->u0 = spriteU0;
                prim->v0 = spriteV0;
                prim->u1 = spriteU1;
                prim->v1 = spriteV0;
                prim->u2 = spriteU0;
                prim->v2 = spriteV1;
                prim->u3 = spriteU1;
                prim->v3 = spriteV1;
            } else {
                prim->u0 = spriteU0;
                prim->v0 = spriteV1 - 1;
                prim->u1 = spriteU1;
                prim->v1 = spriteV1 - 1;
                prim->u2 = spriteU0;
                prim->v2 = spriteV0 - 1;
                prim->u3 = spriteU1;
                prim->v3 = spriteV0 - 1;
            }
        } else {
            if (!(spriteFlags & 1)) {
                prim->u0 = spriteU1 - 1;
                prim->v0 = spriteV0;
                prim->u1 = spriteU0 - 1;
                prim->v1 = spriteV0;
                prim->u2 = spriteU1 - 1;
                prim->v2 = spriteV1;
                prim->u3 = spriteU0 - 1;
                prim->v3 = spriteV1;
            } else {
                prim->u0 = spriteU1 - 1;
                prim->v0 = spriteV1 - 1;
                prim->u1 = spriteU0 - 1;
                prim->v1 = spriteV1 - 1;
                prim->u2 = spriteU1 - 1;
                prim->v2 = spriteV0 - 1;
                prim->u3 = spriteU0 - 1;
                prim->v3 = spriteV0 - 1;
            }
        }

        prim->tpage = 0x14;
        // Entity-relative z priority
        prim->priority = entity->zPriority + 1;

        // Next!
        prim = prim->next;
    }
    return prim;
}


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
    const int InitDistRandRangeX = 0x1F; // Must be a "full flags" value
#else
    const int InitDistRandRangeX = 0xF; // Must be a "full flags" value
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
        // Calculate target x positions
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
        UnkCollisionFunc2(WalkSensors_Tendril); // "Walk", respecting walls/etc

#if defined(BLUE)
        entity = &PLAYER;
        x = entity->posX.i.hi - self->posX.i.hi;
        if (abs(x) > 24) {
            // Set velocity according to remaining distance
            entity = self - 1 - self->params; // Flower
            x = entity->posX.i.hi + self->ext.venusWeedTendril.targetX;
            x -= self->posX.i.hi; // Remaining distance
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
        // Set velocity according to remaining distance
        entity = self - 1 - self->params; // Flower
        x = entity->posX.i.hi + self->ext.venusWeedTendril.targetX;
        x -= self->posX.i.hi; // Remaining distance

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
                SetSubStep(1); // go to next one, but varies
            }
            break;
#if !defined(BLUE)
        case VENUS_WEED_TENDRIL_ATTACK_DELAY:
            if (self->ext.venusWeedTendril.timer) {
                self->ext.venusWeedTendril.timer--;
                break;
            }
            self->step_s++;
            // Fallthrough
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
            entity = self - 1 - self->params; // Flower
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

    // Update the hitbox based on the current animation frame
    hitboxData = HitboxData_Tendril;
    hitboxIndex = HitboxIndices_Tendril[self->animCurFrame - 0x22];
    hitboxData += hitboxIndex * 4; // 4 entries per index
    self->hitboxOffX = *hitboxData++;
    self->hitboxOffY = *hitboxData++;
    self->hitboxWidth = *hitboxData++;
    self->hitboxHeight = *hitboxData++;
}


INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedDart);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedSpike);
