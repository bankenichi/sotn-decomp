/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCHI:EntityGaibon
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/np3/gaibon.c
   target : src/st/rchi/e_gaibon.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int abs(int x);
void SetStep(u8 step);
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
u8 GetSideToPlayer();
void CreateEntityFromCurrentEntity(u16, Entity*);
u8 AnimateEntity(u8 frames[], Entity* entity);
void PlaySfxPositional(s32 arg0);
s16 GetDistanceToPlayerX();
s32 GetDistanceToPlayerY(void);
long ratan2(long y, long x);
int rcos(int a);
int rsin(int a);
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 UnkCollisionFunc3(s16* sensors);
void SetSubStep(u8 step_s);
s32 Random();
/* End permuter-seed writer declarations. */

// Defined in this overlay at src/st/rchi/e_init.c:96. EntityGaibonLeg needs
// it and the permuter cannot add a declaration, so its score-0 result sat in
// `deferred` reading as PERMUTER_EXHAUSTED until this line existed.
//
// Deliberately NOT taken from src/st/nz0/nz0.h:152, which is the only other
// place the name appears. EInit objects are overlay-local data; borrowing
// NZ0's would name a different object.
extern EInit g_EInitGaibon;
// EntitySmallGaibonProjectile's candidate failed to build on this name alone.
// Declared in the shared src/st/e_armor_lord.h:2.
extern EInit g_EInitInteractable;

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern u8 g_CastleFlags[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityGaibon(Entity* self) {
    Collider collider;
    Entity* other;
    s16 angle;
    s8* hitboxPtr;
    s32 xVar;
    s32 yVar;
    s32 speed;
    s32 speedLimit;

    if (self->step) {
        if (!self->ext.GS_Props.nearDeath) {
            if (self->hitPoints < g_api.enemyDefs[0xFE].hitPoints / 2) {
                self->ext.GS_Props.nearDeath = 1;
                xVar = self->posX.i.hi - 0x80;
                if (abs(xVar) < 0x60) {
                    self->hitboxState = 0;
                    SetStep(GAIBON_NEAR_DEATH);
                }
            }
        }
        if (!(self->flags & FLAG_DEAD) || (self->step >= GAIBON_NEAR_DEATH)) {
            other = &SLOGRA;
            if (other->ext.GS_Props.pickupFlag &&
                self->step < GAIBON_LANDING_AFTER_SHOOTING) {
                SetStep(GAIBON_PICKUP_SLOGRA);
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
    case GAIBON_INIT:
        if (g_CastleFlags[SLO_GAI_DEFEATED]) {
            DestroyEntity(self);
            return;
        }
        if (g_CastleFlags[SLO_GAI_RETREATED]) {
            DestroyEntity(self);
            return;
        }
        InitializeEntity(g_EInitGaibonNP3);
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        other = self + 1;
        CreateEntityFromCurrentEntity(E_ID(GAIBON_LEG), other);
        other->zPriority = self->zPriority + 4;
        SetStep(GAIBON_IDLE);
        break;

    case GAIBON_IDLE:
        AnimateEntity(anim1, self);
        if (!self->poseTimer && self->pose == 1) {
            PlaySfxPositional(SFX_WING_FLAP_B);
        }
        if (GetDistanceToPlayerX() < 0x60 && GetDistanceToPlayerY() < 0x60) {
            SetStep(GAIBON_FLY_TOWARDS_PLAYER);
        }
        break;
    case GAIBON_FLY_TOWARDS_PLAYER:
        switch (self->step_s) {
        case GAIBON_FLY_TOWARDS_PLAYER_BEGIN:
            self->facingLeft = (GetSideToPlayer() & 1) ^
                               1; // Results in facing away from player
            other = &PLAYER;
            xVar = other->posX.i.hi;
            yVar = other->posY.i.hi - 0x20;
            xVar -= self->posX.i.hi;
            yVar -= self->posY.i.hi;
            self->ext.GS_Props.angle = ratan2(yVar, xVar);
            self->ext.GS_Props.speed = 0;
            self->ext.GS_Props.timer = 0x60;
            if (self->ext.GS_Props.nearDeath) {
                self->ext.GS_Props.timer = 0x30;
            }
            self->step_s++;
            /* fallthrough */
        case GAIBON_FLY_TOWARDS_PLAYER_MOVEMENT:
            speedLimit = FIX(2);
            if (self->ext.GS_Props.nearDeath) {
                speedLimit *= 2;
            }
            self->ext.GS_Props.speed += FIX(5.0 / 128);
            if (self->ext.GS_Props.speed >= speedLimit) {
                self->ext.GS_Props.speed = speedLimit;
            }
            speed = self->ext.GS_Props.speed;
            self->velocityX = (speed * rcos(self->ext.GS_Props.angle)) >> 0xC;
            self->velocityY = (speed * rsin(self->ext.GS_Props.angle)) >> 0xC;
            MoveEntity();
            AnimateEntity(anim1, self);
            if (!self->poseTimer && self->pose == 1) {
                PlaySfxPositional(SFX_WING_FLAP_B);
            }
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            if (!(--self->ext.GS_Props.timer)) {
                self->step_s++;
            }
            break;
        case GAIBON_FLY_TOWARDS_PLAYER_END:
            MoveEntity();
            self->velocityX -= self->velocityX / 32;
            self->velocityY -= self->velocityY / 32;
            if (!AnimateEntity(anim2, self)) {
                SetStep(GAIBON_FLY_SHOOT_FIREBALLS);
            }
            if (!self->poseTimer && self->pose == 1) {
                PlaySfxPositional(SFX_WING_FLAP_B);
            }
            break;
        }
        break;
    case GAIBON_FLY_SHOOT_FIREBALLS:
        switch (self->step_s) {
        case GAIBON_FLY_SHOOT_FIREBALLS_BEGIN:
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            other = &PLAYER;
            xVar = other->posX.i.hi;
            if (GetSideToPlayer() & 1) {
                xVar += 0x60;
            } else {
                xVar -= 0x60;
            }
            yVar = other->posY.i.hi - 0x80;
            xVar -= self->posX.i.hi;
            yVar -= self->posY.i.hi;
            self->ext.GS_Props.angle = ratan2(yVar, xVar);
            self->ext.GS_Props.speed = 0;
            self->ext.GS_Props.timer = 80;
            if (self->ext.GS_Props.nearDeath) {
                self->ext.GS_Props.timer = 40;
            }
            self->step_s++;
            /* fallthrough */
        case GAIBON_FLY_SHOOT_FIREBALLS_MOVING_SHOOTING:
            speedLimit = FIX(2);
            if (self->ext.GS_Props.nearDeath) {
                speedLimit *= 2;
            }
            self->ext.GS_Props.speed += FIX(5.0 / 128);
            if (self->ext.GS_Props.speed >= speedLimit) {
                self->ext.GS_Props.speed = speedLimit;
            }
            speed = self->ext.GS_Props.speed;
            self->velocityX = (speed * rcos(self->ext.GS_Props.angle)) >> 0xC;
            self->velocityY = (speed * rsin(self->ext.GS_Props.angle)) >> 0xC;
            MoveEntity();
            AnimateEntity(anim3, self);
            if (!self->poseTimer && self->pose == 1) {
                PlaySfxPositional(SFX_WING_FLAP_B);
            }
            // Reuse of speedLimit variable, unrelated to speed
            speedLimit = 0xF;
            if (self->ext.GS_Props.nearDeath) {
                speedLimit = 7;
            }
            if (!(self->ext.GS_Props.timer & speedLimit)) {
                other = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (other != NULL) {
                    CreateEntityFromEntity(
                        E_ID(GAIBON_SMALL_FIREBALL), self, other);
                    PlaySfxPositional(SFX_EXPLODE_FAST_A);
                    other->posY.i.hi -= 2;
                    if (self->facingLeft) {
                        other->posX.i.hi += 12;
                        other->rotate = 0x220;
                    } else {
                        other->posX.i.hi -= 12;
                        other->rotate = 0x5E0;
                    }
                    other->zPriority = (self->zPriority + 1);
                }
            }
            if (!--self->ext.GS_Props.timer) {
                self->step_s++;
            }
            break;
        case GAIBON_FLY_SHOOT_FIREBALLS_END:
            MoveEntity();
            self->velocityX -= self->velocityX / 32;
            self->velocityY -= self->velocityY / 32;
            if (AnimateEntity(anim2, self) == 0) {
                xVar = self->posX.i.hi - 0x80;
                if (abs(xVar) < 0x60) {
                    SetStep(GAIBON_LANDING_AFTER_SHOOTING);
                } else {
                    SetStep(GAIBON_FLY_TOWARDS_PLAYER);
                }
                if (self->ext.GS_Props.nearDeath) {
                    SetStep(GAIBON_FLY_SHOOT_BIG_FIREBALL);
                }
            }
            if (!self->poseTimer && self->pose == 1) {
                PlaySfxPositional(SFX_WING_FLAP_B);
            }
            break;
        }
        break;
    case GAIBON_LANDING_AFTER_SHOOTING:
        switch (self->step_s) {
        case GAIBON_LANDING_AFTER_SHOOTING_SETUP:
            self->animCurFrame = 9;
            self->velocityX = 0;
            self->velocityY = 0;
            self->step_s++;
            /* fallthrough */
        case GAIBON_FALLING_WITHOUT_MAP_COLLISION:
            MoveEntity();
            self->velocityY += FIX(12.0 / 128);
            other = &PLAYER;
            // We enter the version with collision only if
            // the player's Y position minus ours is less than 48?
            // So if the player is 48 or more below us, there is no collision.
            // Weird!
            yVar = other->posY.i.hi - self->posY.i.hi;
            if (yVar < 48) {
                self->step_s++;
            }
            break;
        case GAIBON_FALLING_WITH_MAP_COLLISION:
            MoveEntity();
            self->velocityY += FIX(12.0 / 128);
            xVar = self->posX.i.hi;
            yVar = self->posY.i.hi + 28;
            g_api.CheckCollision(xVar, yVar, &collider, 0);
            if (collider.effects & EFFECT_SOLID) {
                self->posY.i.hi += collider.unk18;
                self->step_s++;
            }
            break;
        case GAIBON_FALLING_ON_GROUND:
            if (AnimateEntity(anim5, self) == 0) {
                SetStep(GAIBON_SHOOT_FROM_GROUND);
            }
            break;
        }
        break;
    case GAIBON_SHOOT_FROM_GROUND:
        switch (self->step_s) {
        case GAIBON_SHOOT_FROM_GROUND_FACE_PLAYER:
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            self->step_s++;
            /* fallthrough */
        case GAIBON_SHOOT_FROM_GROUND_FACE_SETUP:
            if (AnimateEntity(anim6, self) == 0) {
                self->ext.GS_Props.timer = 64;
                if (self->ext.GS_Props.nearDeath) {
                    self->ext.GS_Props.timer *= 2;
                }
                self->step_s++;
            }
            break;
        case GAIBON_SHOOT_FROM_GROUND_FACE_SHOOTING:
            if (!(self->ext.GS_Props.timer & 0xF)) {
                other = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (other != NULL) {
                    if (!self->ext.GS_Props.nearDeath) {
                        CreateEntityFromEntity(
                            E_ID(GAIBON_SMALL_FIREBALL), self, other);
                        PlaySfxPositional(SFX_EXPLODE_FAST_A);
                    } else {
                        CreateEntityFromEntity(
                            E_ID(GAIBON_BIG_FIREBALL), self, other);
                        PlaySfxPositional(SFX_EXPLODE_B);
                    }
                    other->posY.i.hi -= 6;
                    if (self->facingLeft) {
                        other->posX.i.hi += 16;
                        other->rotate = 0;
                    } else {
                        other->posX.i.hi -= 16;
                        other->rotate = 0x800;
                    }
                    other->zPriority = self->zPriority + 1;
                }
            }
            if (!--self->ext.GS_Props.timer) {
                SetStep(GAIBON_FLY_TOWARDS_PLAYER);
            }
            break;
        }
        break;
    case GAIBON_FLY_SHOOT_BIG_FIREBALL:
        switch (self->step_s) {
        case GAIBON_FLY_SHOOT_BIG_FIREBALL_SETUP:
            if (AnimateEntity(anim7, self) == 0) {
                self->step_s++;
            }
            break;
        case GAIBON_FLY_SHOOT_BIG_FIREBALL_SHOOTING:
            other = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (other != NULL) {
                other = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (other != NULL) {
                    PlaySfxPositional(SFX_EXPLODE_B);
                    CreateEntityFromEntity(
                        E_ID(GAIBON_BIG_FIREBALL), self, other);
                    other->posY.i.hi -= 2;
                    if (self->facingLeft) {
                        other->posX.i.hi += 12;
                        other->rotate = 0x220;

                    } else {
                        other->posX.i.hi -= 12;
                        other->rotate = 0x5E0;
                    }
                    other->zPriority = self->zPriority + 1;
                }
            }
            self->velocityY = FIX(-2);
            if (self->facingLeft) {
                self->velocityX = FIX(-2);
            } else {
                self->velocityX = FIX(2);
            }
            self->ext.GS_Props.timer = 32;
            self->step_s++;
            /* fallthrough */
        case GAIBON_FLY_SHOOT_BIG_FIREBALL_END:
            MoveEntity();
            self->velocityX -= self->velocityX / 16;
            self->velocityY -= self->velocityY / 16;
            if (!--self->ext.GS_Props.timer) {
                xVar = self->posX.i.hi - 0x80;
                if (abs(xVar) < 0x60) {
                    SetStep(GAIBON_LANDING_AFTER_SHOOTING);
                } else {
                    SetStep(GAIBON_FLY_TOWARDS_PLAYER);
                }
            }
            break;
        }
        break;
    case GAIBON_PICKUP_SLOGRA:
        switch (self->step_s) {
        case GAIBON_PICKUP_SLOGRA_SETUP:
            other = &SLOGRA;
            xVar = other->posX.i.hi - self->posX.i.hi;
            if (xVar > 0) {
                self->facingLeft = 1;
            } else {
                self->facingLeft = 0;
            }
            self->ext.GS_Props.speed = 0;
            self->step_s++;
            /* fallthrough */
        case GAIBON_PICKUP_SLOGRA_MOVING:
            other = &SLOGRA;
            xVar = other->posX.i.hi - self->posX.i.hi;
            yVar = other->posY.i.hi - (self->posY.i.hi + 0x1C);
            angle = ratan2(yVar, xVar);
            self->ext.GS_Props.speed += FIX(0.5);
            if (self->ext.GS_Props.speed >= FIX(3.5)) {
                self->ext.GS_Props.speed = FIX(3.5);
            }
            speed = self->ext.GS_Props.speed;
            self->velocityX = (speed * rcos(angle)) >> 0xC;
            self->velocityY = (speed * rsin(angle)) >> 0xC;
            MoveEntity();
            if (abs(xVar) < 8 && abs(yVar) < 8) {
                self->ext.GS_Props.grabedAscending = 1;
                self->velocityX = 0;
                self->velocityY = 0;
                self->step_s++;
            }
            if (!other->ext.GS_Props.pickupFlag) {
                self->ext.GS_Props.grabedAscending = 0;
                SetStep(GAIBON_FLY_SHOOT_FIREBALLS);
            }
            break;
        case GAIBON_PICKUP_SLOGRA_ASCENDING:
            AnimateEntity(anim4, self);
            if (!self->poseTimer && self->pose == 1) {
                PlaySfxPositional(SFX_WING_FLAP_B);
            }
            MoveEntity();
            self->velocityY -= FIX(5.0 / 128);
            if (self->velocityY < FIX(-2)) {
                self->velocityY = FIX(-2);
            }
            other = &SLOGRA;
            other->posX.i.hi = self->posX.i.hi;
            other->posY.i.hi = self->posY.i.hi + 28;
            self->ext.GS_Props.grabedAscending = 1;
            if (self->posY.i.hi < 0) {
                self->velocityX = 0;
                self->velocityY = 0;
                self->ext.GS_Props.timer = 96;
                self->step_s++;
            }
            break;
        case GAIBON_PICKUP_SLOGRA_AIMING:
            AnimateEntity(anim4, self);
            if (!self->poseTimer && self->pose == 1) {
                PlaySfxPositional(SFX_WING_FLAP_B);
            }
            if (GetSideToPlayer() & 1) {
                self->velocityX -= FIX(5.0 / 128);
            } else {
                self->velocityX += FIX(5.0 / 128);
            }
            if (self->velocityX < FIX(-2)) {
                self->velocityX = FIX(-2);
            }
            if (self->velocityX > FIX(2)) {
                self->velocityX = FIX(2);
            }
            MoveEntity();
            other = &SLOGRA;
            other->posX.i.hi = self->posX.i.hi;
            other->posY.i.hi = self->posY.i.hi + 28;
            other->velocityY = 0;
            self->ext.GS_Props.grabedAscending = 0;
            if (!--self->ext.GS_Props.timer) {
                self->step_s++;
            }
            break;
        case GAIBON_PICKUP_SLOGRA_RELEASE:
            self->ext.GS_Props.grabedAscending = 0;
            SetStep(GAIBON_FLY_TOWARDS_PLAYER);
        }
        break;
    case GAIBON_NEAR_DEATH:
        switch (self->step_s) {
        case GAIBON_NEAR_DEATH_SETUP:
            self->animCurFrame = 9;
            self->velocityX = 0;
            self->velocityY = 0;
            self->ext.GS_Props.nearDeath = 1;
            self->step_s++;
            /* fallthrough */
        case GAIBON_NEAR_DEATH_FLOOR_HIT_WAIT:
            if (UnkCollisionFunc3(sensors) & 1) {
                SetSubStep(GAIBON_NEAR_DEATH_FLOOR_LANDING);
            }
            break;
        case GAIBON_NEAR_DEATH_FLOOR_LANDING:
            if (AnimateEntity(anim8, self) == 0) {
                self->ext.GS_Props.flag = 0;
                SetSubStep(GAIBON_NEAR_DEATH_TRANSFORM);
            }
            break;
        case GAIBON_NEAR_DEATH_TRANSFORM:
            if (AnimateEntity(anim9, self) == 0) {
                self->ext.GS_Props.flag++;
                self->palette = g_EInitGaibonNP3[3] + self->ext.GS_Props.flag;
                if (self->ext.GS_Props.flag == 6) {
                    self->flags &= ~0xF;
                    slograGaibonRetreat = 1;
                    SetStep(SLOGRA_GAIBON_RETREAT);
                }
            }
            break;
        }
        break;
    case SLOGRA_GAIBON_RETREAT:
        switch (self->step_s) {
        case 0:
            other = &SLOGRA;
            xVar = other->posX.i.hi - self->posX.i.hi;
            if (xVar > 0) {
                self->facingLeft = 1;
            } else {
                self->facingLeft = 0;
            }
            self->ext.GS_Props.speed = 0;
            g_CastleFlags[SLO_GAI_RETREATED] |= 1;
            self->step_s++;
            /* fallthrough */
        case 1:
            other = &SLOGRA;
            xVar = other->posX.i.hi - self->posX.i.hi;
            yVar = other->posY.i.hi - (self->posY.i.hi + 28);
            angle = ratan2(yVar, xVar);
            self->ext.GS_Props.speed += FIX(0.5);
            if (self->ext.GS_Props.speed >= FIX(3.5)) {
                self->ext.GS_Props.speed = FIX(3.5);
            }
            speed = self->ext.GS_Props.speed;
            self->velocityX = (speed * rcos(angle)) >> 0xC;
            self->velocityY = (speed * rsin(angle)) >> 0xC;
            MoveEntity();
            if (abs(xVar) < 8 && abs(yVar) < 8) {
                self->velocityX = 0;
                self->velocityY = 0;
                self->step_s++;
            }
            break;
        case 2:
            AnimateEntity(anim4, self);
            MoveEntity();
            self->velocityY -= FIX(5.0 / 128);
            if (self->velocityY < FIX(-2)) {
                self->velocityY = FIX(-2);
            }
            other = &SLOGRA;
            other->posX.i.hi = self->posX.i.hi;
            other->posY.i.hi = self->posY.i.hi + 28;
            break;
        }
        break;
    // Because we are in the initial Entrance encounter, it is not possible to
    // reach this step. The fact that it is here anyway seems like strong
    // evidence that this whole function was copy-pasted, and then tweaked to
    // suit the needs in Entrance.
    case GAIBON_DYING:
        switch (self->step_s) {
        case GAIBON_DYING_REACT:
            if (AnimateEntity(anim10, self) == 0) {
                self->ext.GS_Props.timer = 96;
                self->animCurFrame = 0x1F;
                self->flags &= ~0xF;
                self->palette = g_EInitGaibonNP3[3];
                self->step_s++;
            }
            break;
        case GAIBON_DYING_TURN_INTO_BONES:
            if (!(self->ext.GS_Props.timer & 7)) {
                other = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (other != NULL) {
                    CreateEntityFromEntity(E_EXPLOSION, self, other);
                    other->posY.i.hi += 28;
                    // Scatter bones randomly between +- 32
                    other->posX.i.hi += ((Random() & 63) - 32);
                    other->zPriority = self->zPriority + 1;
                    other->params = 2;
                }
            }
            if (!--self->ext.GS_Props.timer) {
                DestroyEntity(self);
                return;
            }
            break;
        }
        break;
    case 0xFF:
#include "../pad2_anim_debug.h"
    }
    hitboxPtr = &gaibonHitboxes[0][0];
    hitboxPtr += gaibonHitboxIdx[self->animCurFrame] * 4;
    self->hitboxOffX = *hitboxPtr++;
    self->hitboxOffY = *hitboxPtr++;
    self->hitboxWidth = *hitboxPtr++;
    self->hitboxHeight = *hitboxPtr++;
}


void EntityGaibonLeg(Entity *self)
{
  Entity *parent;
  if (self->step == 0)
  {
    InitializeEntity(&g_EInitGaibon);
    self->hitboxState = 0;
  }
  self->facingLeft = (self - 1)->facingLeft;
  parent = self - 1;
  self->palette = (self - 1)->palette;
  self->animCurFrame = 0;
  self->posX.i.hi = (self - 1)->posX.i.hi;
  self->posY.i.hi = parent->posY.i.hi;
  if (((u32) (parent->animCurFrame - 0x20)) < 3)
  {
    self->animCurFrame = 0x26;
  }
  else
    if (parent->animCurFrame == 0x23)
  {
    self->animCurFrame = 0x27;
  }
  else
    if (((u32) (parent->animCurFrame - 0x24)) < 2)
  {
    self->animCurFrame = 0x28;
  }
  if (parent->entityId != 0x19)
  {
    DestroyEntity(self);
  }
}

extern EInit g_EInitGaibonProjectile;

extern u8 g_AnimSmallGaibonProjectile[];

void EntitySmallGaibonProjectile(Entity* self) {
    if (self->flags & FLAG_DEAD) {
        self->drawFlags = ENTITY_DEFAULT;
        self->step = 0;
        self->pfnUpdate = EntityExplosion;
        self->entityId = 2;
        self->params = 0;
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitGaibonProjectile);
        self->animSet = ANIMSET_DRA(2);
        self->animCurFrame = 1;
        self->drawFlags = ENTITY_SCALEX | ENTITY_ROTATE;
        self->scaleX = 0xC0;
        self->velocityX = (rcos(self->rotate) * FIX(2.5)) >> 0xC;
        self->velocityY = (rsin(self->rotate) * FIX(2.5)) >> 0xC;
        self->rotate -= 0x400;
        self->palette = PAL_FLAG(PAL_UNK_1B6);
        // fallthrough

    case 1:
        MoveEntity();
        AnimateEntity(g_AnimSmallGaibonProjectile, self);
        break;
    }
}

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntityLargeGaibonProjectile);
