/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO4:EntityVenusWeedFlower
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
int FntPrint(const char* id, ...);
void PlaySfxPositional(s32 arg0);
void SetStep(u8 step);
void InitializeEntity(u16 arg0[]);
u8 AnimateEntity(u8 frames[], Entity* entity);
u8 GetSideToPlayer();
s16 GetDistanceToPlayerX();
void SetSubStep(u8 step_s);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
long ratan2(long y, long x);
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

    enum Step {
        INIT,
        GROW,
        REVEAL,
        IDLE,
        SPIKES,
        DARTS,
        DEATH = 8,
    };

    enum Spikes_Substep {
        SPIKES_INIT,
#if defined(BLUE)
        SPIKES_1,
#endif
        SPIKES_CHARGE,
        SPIKES_SPAWN,
        SPIKES_LAUNCH,
        SPIKES_ANIM_RESET,
        SPIKES_RESET_TO_IDLE,
    };

    enum Darts_Substep {
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

#if defined(BLUE)
    FntPrint("arla_step %x\n", self->step);
    FntPrint("arla_color %x\n", self->palette);
#endif

    // Hurt check
    if (self->hitFlags & 3) {
        PlaySfxPositional(SFX_VENUS_WEED_HURT);

        // Tell root to wiggle for a bit
        entity = self - 1; // Root
        entity->ext.venusWeed.wiggleT = 0x40;
    }
    // Death check
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
            // Tell root to idle
            entity = self - 1; // Root
            entity->step = VENUS_WEED_IDLE;
            entity->step_s = 0;

            SetStep(IDLE);
        }
        break;

    case IDLE:
        // Init
        if (!self->step_s) {
            self->ext.venusWeedFlower.triggerAttack = 1;
            self->step_s++;
        }

        // Animate, occasionally turning to face player
        if (AnimateEntity(AnimFrames_FlowerPulse, self) == 0) {
            self->facingLeft = GetSideToPlayer() & 1;
        }

        // Only once, when entering IDLE state
        if (!--self->ext.venusWeedFlower.triggerAttack) {
            // Face player
            self->facingLeft = GetSideToPlayer() & 1;
            // Blue chooses by distance, non-blue alternates
#if defined(BLUE)
            SetStep(DARTS);
            if (GetDistanceToPlayerX() < 64) {
                SetStep(SPIKES);
            }
#else
            if (self->ext.venusWeedFlower.nextAttackIsDarts) {
                SetStep(DARTS);
            } else {
                SetStep(SPIKES);
            }
            // Toggle between darts and tendril spikes attacks
            self->ext.venusWeedFlower.nextAttackIsDarts ^= 1;
#endif
        }
        break;

    case SPIKES:
        switch (self->step_s) {
        case SPIKES_INIT:

#if defined(BLUE)
            self->ext.venusWeedFlower.unk93 = 0;
#else
            // Set root entity to attack
            entity = self - 1; // Root
            entity->step = VENUS_WEED_ATTACK;
            entity->step_s = 0;
#endif

            // Set tendrils to attack
            entity = self + 1; // Tendrils start
            for (i = 0; i < TENDRIL_COUNT; i++, entity++) {
#if defined(BLUE)
                entity->ext.venusWeedFlower.unk93 = 1;
#else
                entity->step = VENUS_WEED_TENDRIL_ATTACK;
                entity->step_s = VENUS_WEED_TENDRIL_ATTACK_INIT;
#endif
            }

            self->step_s++;
            // fallthrough
#if defined(BLUE)
        case SPIKES_1:
            AnimateEntity(AnimFrames_FlowerPulse, self);
            if (self->ext.venusWeedFlower.unk93 == 8) {
                entity = self - 1;
                entity->step = 5;
                entity->step_s = 0;
                SetSubStep(SPIKES_CHARGE);
            }
            break;
#endif
        case SPIKES_CHARGE:
            if (!AnimateEntity(AnimFrames_FlowerAttackSpikesCharge, self)) {
                SetSubStep(SPIKES_SPAWN);
            }
            break;
        case SPIKES_SPAWN:
            PlaySfxPositional(SFX_GLASS_SHARDS);

            // Spawn spikes
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_VENUS_WEED_SPIKE, self, entity);
                entity->facingLeft = self->facingLeft;
                entity->ext.venusWeedSpike.flower = self;
            }
            self->step_s++;
            // fallthrough
        case SPIKES_LAUNCH:
            if (AnimateEntity(AnimFrames_FlowerAttackSpikesLaunch, self) == 0) {
                entity = self + 1; // Tendrils start
#if !defined(BLUE)
                if (g_Timer & 1) {
                    spikeStartTimeOffsetIndex = 0;
                } else {
                    spikeStartTimeOffsetIndex = 4;
                }
#endif
                for (i = 0; i < TENDRIL_COUNT; i++, entity++) {
#if defined(BLUE)
                    entity->ext.venusWeedTendril.spikeStartTimeOffsetIndex = 1;
#else
                    entity->ext.venusWeedTendril.spikeStartTimeOffsetIndex =
                        spikeStartTimeOffsetIndex + 1;
                    spikeStartTimeOffsetIndex++;
                    spikeStartTimeOffsetIndex &= 0x7;
#endif
                }
                SetSubStep(SPIKES_ANIM_RESET);
            }
            break;

        case SPIKES_ANIM_RESET: // Anim: Reset to idle
            if (AnimateEntity(AnimFrames_FlowerAttackSpikesReset, self) == 0) {
                SetSubStep(SPIKES_RESET_TO_IDLE);
            }
            break;

        case SPIKES_RESET_TO_IDLE:
            // Tell root to idle
            entity = self - 1; // Root
            entity->step = VENUS_WEED_IDLE;

            SetStep(IDLE);
            break;
        }
#if !defined(BLUE)
        // Cycle clut; this block is in different places on the two versions
        if (self->ext.venusWeedFlower.clutOffset) {
            entity = self - 1; // Root
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
#endif
        break;

    case DARTS:
        switch (self->step_s) {
        case DARTS_INIT:
            entity = self - 1; // Root
            entity->step = 6;  // Non-existent state: "Do nothing"
            entity->step_s = 0;

            self->step_s += 1;
            // fallthrough
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
            // fallthrough
        case DARTS_LAUNCH:
            if (AnimateEntity(AnimFrames_FlowerAttackDartsLaunch, self) == 0) {
                self->step_s++;
            }
            if (!self->poseTimer && self->pose == DartsSfxpose) {
                PlaySfxPositional(SFX_ARROW_SHOT_B);

                // Calculate launch start pos
                if (self->facingLeft) {
                    x = self->posX.i.hi - DartsLaunchPosOffsetX;
                } else {
                    x = self->posX.i.hi + DartsLaunchPosOffsetX;
                }
                y = self->posY.i.hi - DartsLaunchPosOffsetY;

                // Calculate launch angle and delta between darts
                entity = &PLAYER;
                rot = ratan2(entity->posY.i.hi - y, entity->posX.i.hi - x);
                if (self->facingLeft) {
                    if (rot < 0) { // Angled up
                        if (rot > -DartsAngleLeft + DartsAngleMaxUp) {
                            rot = -DartsAngleLeft + DartsAngleMaxUp;
                        }
                        rotDelta = -DartsAngleDelta; // More up
                    } else {                         // Angled down
                        if (rot < DartsAngleLeft - DartsAngleMaxDown) {
                            rot = DartsAngleLeft - DartsAngleMaxDown;
                        }
                        rotDelta = DartsAngleDelta; // More down
                    }
                } else if (rot < 0) { // Angled up
                    if (rot < -DartsAngleMaxUp) {
                        rot = -DartsAngleMaxUp;
                    }
                    rotDelta = DartsAngleDelta; // More up
                } else {                        // Angled down
                    if (rot > DartsAngleMaxDown) {
                        rot = DartsAngleMaxDown;
                    }
                    rotDelta = -DartsAngleDelta; // More down
                }

                // Spawn darts
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
            entity = self - 1; // Root
            entity->step = VENUS_WEED_IDLE;
            SetStep(IDLE);
        }
        break;

    case DEATH:
        // Kill tendrils
        entity = self + 1; // Tendrils start
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

        // Kill root
        entity = self - 1; // Root
        entity->flags |= FLAG_DEAD;

        DestroyEntity(self);
        return;
    }
#if defined(BLUE)
    // Cycle clut; this block is in different places on the two versions
    if (self->ext.venusWeedFlower.clutOffset) {
        entity = self - 1; // Root
        entity->ext.venusWeed.triggerAttack = true;
        if (!(self->palette & PAL_UNK_FLAG)) {
            self->palette += self->ext.venusWeedFlower.clutOffset >> 4;
            self->ext.venusWeedFlower.clutOffset &= 0xF;
            if (self->palette > 0x24f) {
                self->palette = 0x24f;
            }
        }
    }
#endif
}


INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedTendril);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedDart);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedSpike);
