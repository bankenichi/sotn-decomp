/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCHI:EntitySlogra
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/np3/slogra.c
   target : src/st/rchi/e_slogra.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void SetStep(u8 step);
void PlaySfxPositional(s32 arg0);
void DestroyEntity(Entity*);
u8 GetSideToPlayer();
void CreateEntityFromCurrentEntity(u16, Entity*);
s32 UnkCollisionFunc3(s16* sensors);
u8 AnimateEntity(u8 frames[], Entity* entity);
s16 GetDistanceToPlayerX();
s32 UnkCollisionFunc2(s16* posX);
s32 Random();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void SetSubStep(u8 step_s);
void MoveEntity();
/* End permuter-seed writer declarations. */

// EntitySlograSpear and EntitySlograSpearProjectile each failed to build on
// one of these names. g_EInitSlograSpear is defined by THIS overlay at
// src/st/rchi/e_init.c:94; g_Entities_224 is the shared src/st/e_imp.h:9.
extern EInit g_EInitSlograSpear;
extern Entity g_Entities_224[];

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern u8 g_CastleFlags[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern u32 g_Timer;

void EntitySlogra(Entity* self) {
    Entity* otherEnt;
    s32 unusedCollResult;
    s8* hitbox;
    u8* animation;

    self->ext.GS_Props.pickupFlag = 0;

    if (self->step) {
        if ((self->hitFlags & 3) && (self->step != SLOGRA_KNOCKBACK)) {
            SetStep(SLOGRA_KNOCKBACK);
        }
        if (!self->ext.GS_Props.nearDeath) {
            if ((self->hitPoints < g_api.enemyDefs[243].hitPoints / 4) &&
                (self->step != SLOGRA_LOSE_SPEAR)) {
                self->hitboxState = 0;
                PlaySfxPositional(SFX_SLOGRA_ROAR_DEFEAT);
                SetStep(SLOGRA_LOSE_SPEAR);
            }
        }
        otherEnt = self + 8;
        if (otherEnt->ext.GS_Props.grabedAscending) {
            if (self->step != SLOGRA_DYING &&
                self->step != SLOGRA_GAIBON_COMBO_ATTACK) {
                SetStep(SLOGRA_GAIBON_COMBO_ATTACK);
            }
        }
        if (slograGaibonRetreat) {
            self->hitboxState = 0;
            if (self->step != SLOGRA_GAIBON_RETREAT) {
                SetStep(SLOGRA_GAIBON_RETREAT);
            }
        }
    }

    switch (self->step) {
    case SLOGRA_INIT:
        if (g_CastleFlags[SLO_GAI_DEFEATED]) {
            DestroyEntity(self);
            return;
        }
        if (g_CastleFlags[SLO_GAI_RETREATED]) {
            DestroyEntity(self);
            return;
        }
        InitializeEntity(g_EInitSlograNP3);
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        otherEnt = self + 1;
        CreateEntityFromCurrentEntity(E_ID(SLOGRA_SPEAR), otherEnt);

    case SLOGRA_FLOOR_ALIGN:
        if (UnkCollisionFunc3(sensors1) & 1) {
            SetStep(SLOGRA_IDLE);
        }
        break;

    case SLOGRA_IDLE:
        AnimateEntity(anim2, self);
        if (GetDistanceToPlayerX() < 96) {
            SetStep(SLOGRA_WALKING_WITH_SPEAR);
        }
        break;

    case SLOGRA_TAUNT_WITH_SPEAR:
        if (AnimateEntity(anim2, self) == 0) {
            SetStep(SLOGRA_WALKING_WITH_SPEAR);
        }
        break;

    case SLOGRA_WALKING_WITH_SPEAR:
        if (!self->step_s) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            if (self->ext.GS_Props.attackMode) {
                self->ext.GS_Props.flag = 1;
            } else {
                self->ext.GS_Props.flag = 0;
            }
            self->ext.GS_Props.timer = 128;
            self->step_s++;
        }
        AnimateEntity(anim1, self);
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        if (self->facingLeft ^ self->ext.GS_Props.flag) {
            self->velocityX = FIX(0.75);
        } else {
            self->velocityX = FIX(-0.75);
        }
        UnkCollisionFunc2(sensors2);
        if (!self->ext.GS_Props.flag) {
            if (GetDistanceToPlayerX() < 72) {
                if (!self->ext.GS_Props.attackMode) {
                    self->ext.GS_Props.timer = 1;
                } else {
                    self->ext.GS_Props.flag ^= 1;
                }
            }
        }
        if (self->ext.GS_Props.flag) {
            if (GetDistanceToPlayerX() > 112) {
                if (self->ext.GS_Props.attackMode) {
                    self->ext.GS_Props.timer = 1;
                } else {
                    self->ext.GS_Props.flag ^= 1;
                }
            }
        }
        if ((Random() & 0x3F) == 0) {
            SetStep(SLOGRA_TAUNT_WITH_SPEAR);
        }
        if (!--self->ext.GS_Props.timer) {
            if (self->ext.GS_Props.attackMode) {
                SetStep(SLOGRA_SPEAR_FIRE);
            } else {
                SetStep(SLOGRA_SPEAR_POKE);
            }
            self->ext.GS_Props.attackMode ^= 1;
        }
        break;

    case SLOGRA_SPEAR_POKE:
        if (!self->step_s) {
            PlaySfxPositional(SFX_SLOGRA_ROAR);
            self->step_s++;
        }
        if (AnimateEntity(anim6, self) == 0) {
            SetStep(SLOGRA_WALKING_WITH_SPEAR);
        }
        if (!self->poseTimer && self->pose == 4) {
            PlaySfxPositional(SFX_BOSS_WING_FLAP);
        }
        break;

    case SLOGRA_SPEAR_FIRE:
        switch (self->step_s) {
        case SLOGRA_FIRE_FACE_PLAYER:
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            self->step_s++;

        case SLOGRA_FIRE_PROJECTILE:
            if (AnimateEntity(anim3, self) == 0) {
                PlaySfxPositional(SFX_FM_EXPLODE_SWISHES);
                otherEnt = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (otherEnt != NULL) {
                    CreateEntityFromEntity(
                        E_ID(SLOGRA_SPEAR_PROJECTILE), self, otherEnt);
                    if (self->facingLeft) {
                        otherEnt->posX.i.hi += 68;
                    } else {
                        otherEnt->posX.i.hi -= 68;
                    }
                    otherEnt->posY.i.hi -= 6;
                    otherEnt->facingLeft = self->facingLeft;
                    otherEnt->zPriority = self->zPriority + 1;
                }
                SetSubStep(SLOGRA_FIRE_COOLDOWN);
            }
            break;

        case SLOGRA_FIRE_COOLDOWN:
            if (AnimateEntity(anim4, self) == 0) {
                SetSubStep(SLOGRA_FIRE_END);
            }
            break;

        case SLOGRA_FIRE_END:
            if (AnimateEntity(anim5, self) == 0) {
                SetStep(SLOGRA_WALKING_WITH_SPEAR);
            }
            break;
        }
        break;

    case SLOGRA_KNOCKBACK:
        if (!self->step_s) {
            PlaySfxPositional(SFX_SLOGRA_PAIN_B);
            self->step_s++;
        }
        if (self->ext.GS_Props.nearDeath) {
            animation = anim11;
        } else {
            animation = anim7;
        }
        if (AnimateEntity(animation, self) == 0) {
            SetStep(SLOGRA_WALKING_WITH_SPEAR);
            if (self->ext.GS_Props.nearDeath) {
                SetStep(SLOGRA_TAUNT_WITHOUT_SPEAR);
            }
        }
        break;

    case SLOGRA_LOSE_SPEAR:
        if (AnimateEntity(anim8, self) == 0) {
            slograGaibonRetreat = 1;
            SetStep(SLOGRA_GAIBON_RETREAT);
        }
        if (self->pose > 1) {
            self->ext.GS_Props.nearDeath = 1;
        }
        break;

    case SLOGRA_TAUNT_WITHOUT_SPEAR:
        if (AnimateEntity(anim10, self) == 0) {
            SetStep(SLOGRA_WALKING_WITHOUT_SPEAR);
        }
        break;

    case SLOGRA_WALKING_WITHOUT_SPEAR:
        if (!self->step_s) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            self->ext.GS_Props.flag = 1;
            self->ext.GS_Props.timer = 128;
            self->step_s++;
        }

        AnimateEntity(anim9, self);
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        if (self->facingLeft ^ self->ext.GS_Props.flag) {
            self->velocityX = FIX(0.75);
        } else {
            self->velocityX = FIX(-0.75);
        }

        UnkCollisionFunc2(sensors2);
        if (!self->ext.GS_Props.flag) {
            if (GetDistanceToPlayerX() < 72) {
                self->ext.GS_Props.flag ^= 1;
            }
        }
        if (self->ext.GS_Props.flag) {
            if (GetDistanceToPlayerX() > 112) {
                self->ext.GS_Props.flag ^= 1;
            }
        }
        if ((Random() & 0x3F) == 0) {
            SetStep(SLOGRA_TAUNT_WITHOUT_SPEAR);
        }
        if (!--self->ext.GS_Props.timer) {
            SetStep(SLOGRA_ATTACK);
        }
        break;

    case SLOGRA_ATTACK: // Attack without spear
        if (AnimateEntity(anim12, self) == 0) {
            SetStep(SLOGRA_WALKING_WITHOUT_SPEAR);
        }
        if (!self->poseTimer && self->pose == 7) {
            PlaySfxPositional(SFX_BONE_THROW);
        }
        break;

    case SLOGRA_GAIBON_COMBO_ATTACK: // Unused
        switch (self->step_s) {
        case SLOGRA_COMBO_ATTACK_START:
            otherEnt = self + 8;
            if (!otherEnt->ext.GS_Props.grabedAscending) {
                self->velocityX = 0;
                self->velocityY = 0;
                self->step_s++;
            }
            break;

        case SLOGRA_COMBO_ATTACK_PLUNGE:
            if (self->ext.GS_Props.nearDeath) {
                animation = anim13;
            } else {
                animation = anim15;
            }
            AnimateEntity(animation, self);

            if (UnkCollisionFunc3(sensors1) & 1) {
                g_api.ShakeCamera(SHAKE_Y_SMALL);
                self->ext.GS_Props.timer = 16;
                self->step_s++;
            }
            break;

        case SLOGRA_COMBO_ATTACK_COOLDOWN:
            if (!--self->ext.GS_Props.timer) {
                SetStep(SLOGRA_WALKING_WITH_SPEAR);
                if (self->ext.GS_Props.nearDeath) {
                    SetStep(SLOGRA_WALKING_WITHOUT_SPEAR);
                }
            }
            break;
        }
        break;

    case SLOGRA_GAIBON_RETREAT:
        if (self->ext.GS_Props.nearDeath) {
            animation = anim10;
        } else {
            animation = anim2;
        }
        AnimateEntity(animation, self);
        break;

    case SLOGRA_DYING: // Unused
        switch (self->step_s) {
        case SLOGRA_DYING_START:
            self->hitboxState = 0;
            if (!self->ext.GS_Props.nearDeath) {
                self->ext.GS_Props.nearDeath = 1;
            }
            self->ext.GS_Props.timer = 64;
            PlaySfxPositional(SFX_STUTTER_EXPLODE_A);
            g_CastleFlags[SLO_GAI_RETREATED] |= 1;
            self->step_s++;

        case SLOGRA_DYING_EXPLODING:
            unusedCollResult = UnkCollisionFunc3(sensors1);
            AnimateEntity(anim14, self);
            if ((g_Timer & 3) == 0) {
                otherEnt = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (otherEnt != NULL) {
                    CreateEntityFromEntity(E_EXPLOSION, self, otherEnt);
                    otherEnt->posX.i.hi += (Random() & 31) - 16;
                    otherEnt->posY.i.hi += (Random() & 31) - 16;
                    otherEnt->zPriority = self->zPriority + 1;
                    otherEnt->params = 1;
                }
            }
            if (!--self->ext.GS_Props.timer) {
                self->step_s++;
            }
            break;

        case SLOGRA_DYING_END:
            otherEnt = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (otherEnt != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, otherEnt);
                otherEnt->posY.i.hi += 16;
                otherEnt->params = 3;
            }
            DestroyEntity(self);
            return;
        }
        break;

    case SLOGRA_DEBUG:
#include "../pad2_anim_debug.h"
    }
    hitbox = slograHitboxes;
    hitbox += 4 * slograHitboxIdx[self->animCurFrame];
    self->hitboxOffX = *hitbox++;
    self->hitboxOffY = *hitbox++;
    self->hitboxWidth = *hitbox++;
    self->hitboxHeight = *hitbox++;
}


#define ENTITY_ROTATE 4
#define FLAG_DESTROY_IF_OUT_OF_CAMERA 2147483648
#define SFX_ARROW_SHOT_A 1573
extern s8 g_SlograSpearHitboxes[];
extern u8 g_SlograSpearHitboxIdx[];
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void EntitySlograSpear(Entity* self) {
    s32 animFrame;
    Entity* slogra;
    s8* hitbox;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitSlograSpear);

    case 1:
        slogra = self - 1;
        self->facingLeft = slogra->facingLeft;
        self->posX.i.hi = slogra->posX.i.hi;
        self->posY.i.hi = slogra->posY.i.hi;
        animFrame = slogra->animCurFrame;
        hitbox = g_SlograSpearHitboxes;
        hitbox += 4 * g_SlograSpearHitboxIdx[animFrame];
        self->hitboxOffX = *hitbox++;
        self->hitboxOffY = *hitbox++;
        self->hitboxWidth = *hitbox++;
        self->hitboxHeight = *hitbox++;
        if (slogra->ext.GS_Props.nearDeath) {
            self->step++;
        }
        break;

    case 2:
        switch (self->step_s) {
        case 0:
            self->drawFlags = ENTITY_ROTATE;
            self->hitboxState = 0;
            if (self->facingLeft) {
                self->velocityX = FIX(-2.25);
            } else {
                self->velocityX = FIX(2.25);
            }
            self->velocityY = FIX(-4);
            self->animCurFrame = 35;
            self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA;
            self->step_s++;

        case 1:
            MoveEntity();
            self->velocityY += FIX(0.15625);
            self->rotate += 0x80;
            if (!(self->rotate & 0xFFF)) {
                PlaySfxPositional(SFX_ARROW_SHOT_A);
            }
        }
    }
}

INCLUDE_ASM("st/rchi/nonmatchings/e_slogra", EntitySlograSpearProjectile);
