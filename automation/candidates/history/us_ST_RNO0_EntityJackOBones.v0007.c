/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO0:EntityJackOBones
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_jack_o_bones.h
   target : src/st/rno0/unk_48100.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
s32 UnkCollisionFunc2(s16* posX);
s32 UnkCollisionFunc(s16* hitSensors, s16 sensorCount);
void SetStep(u8 step);
void InitializeEntity(u16 arg0[]);
u8 GetSideToPlayer();
s32 UnkCollisionFunc3(s16* sensors);
u8 AnimateEntity(u8 frames[], Entity* entity);
s16 GetDistanceToPlayerX();
Entity* AllocEntity(Entity* start, Entity* end);
void PlaySfxPositional(s32 arg0);
void CreateEntityFromCurrentEntity(u16, Entity*);
s32 Random();
void CheckFieldCollision(s16* hitSensors, s16 sensorCount);
void DestroyEntity(Entity*);
void FallEntity(void);
void MoveEntity();
int abs(int x);
/* End permuter-seed writer declarations. */

#define JACKO_JUMP 5
#define JACKO_THROW 4
extern u16 D_us_80181F88[];
extern s16 D_us_80181F90[];

static void TryThrow(void) {
    s32 temp_s1;
    u16 temp_s0;

    temp_s1 = UnkCollisionFunc2(D_us_80181F88);
    temp_s0 = UnkCollisionFunc(D_us_80181F90, 3);
    if ((temp_s1 == 0x80) || (temp_s0 & 2)) {
        SetStep(JACKO_JUMP);
        return;
    }
    if (!g_CurrentEntity->ext.jackoBones.throwTimer) {
        SetStep(JACKO_THROW);
        return;
    }
    g_CurrentEntity->ext.jackoBones.throwTimer--;
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitJackOBones;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityJackOBones(Entity* self) {
    s32 xShift;
    u8 var_s2;
    s32 i;
    Entity* other;

    if (self->flags & FLAG_DEAD) {
        self->step = JACKO_DEAD;
    }
    switch (self->step) {
    case JACKO_INIT:
        InitializeEntity(g_EInitJackOBones);
        if (self->params) {
            self->palette++;
        }
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        // Cooldown for throwing jacks
        self->ext.jackoBones.throwTimer = 0x50;
        // When walking forward, this tells us if facing left. When walking
        // back, this is the inverse of whether we are facing left.
        self->ext.jackoBones.movingLeft = 0;
        self->ext.jackoBones.throwTimerIndex = 0;
        break;
    case JACKO_1:
        if (UnkCollisionFunc3(sensors1) == 0) {
            break;
        }
        self->step++;
        break;
    case JACKO_WALK_FWD:
        if (AnimateEntity(anim_walk_fwd, self) == 0) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        }
        self->ext.jackoBones.movingLeft = self->facingLeft;
        if (self->ext.jackoBones.movingLeft) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        if (GetDistanceToPlayerX() < 76) {
            self->step = JACKO_WALK_BACK;
        }
        TryThrow();
        break;
    case JACKO_WALK_BACK:
        if (AnimateEntity(anim_walk_back, self) == 0) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        }
        self->ext.jackoBones.movingLeft = self->facingLeft ^ 1;
        if (self->ext.jackoBones.movingLeft) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        if (GetDistanceToPlayerX() > 92) {
            self->step = JACKO_WALK_FWD;
        }
        TryThrow();
        break;
    case JACKO_THROW:
        var_s2 = AnimateEntity(anim_throw, self);
        // We set a value here but it is never used.
        if (self->params) {
            i = 11;
        } else {
            i = 10;
        }
        // Animation done. walk backward and set the timer for next throw.
        if (!var_s2) {
            SetStep(JACKO_WALK_BACK);
            var_s2 = ++self->ext.jackoBones.throwTimerIndex & 3;
            self->ext.jackoBones.throwTimer =
                throw_timers[self->params & 1][var_s2];
            break;
        }
        if ((var_s2 & 0x80) && (self->animCurFrame == 0xB)) {
            other = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (other != NULL) {
                PlaySfxPositional(SFX_BONE_THROW);
                CreateEntityFromCurrentEntity(E_JACKO_JACK, other);
                if (self->params) {
                    xShift = -16;
                } else {
                    xShift = 8;
                }
                if (self->facingLeft) {
                    other->posX.i.hi -= xShift;
                } else {
                    other->posX.i.hi += xShift;
                }
                other->posY.i.hi -= 16;
                other->params = self->params;
                other->facingLeft = self->facingLeft;
            }
        }
        break;
    case JACKO_JUMP:
        switch (self->step_s) {
        case JACKO_JUMP_WINDUP:
            if (!(AnimateEntity(anim_jump_windup, self) & 1)) {
                var_s2 = self->ext.jackoBones.movingLeft;
                if (!(Random() & 3)) {
                    var_s2 ^= 1;
                }
                if (var_s2) {
                    self->velocityX = FIX(2);
                } else {
                    self->velocityX = FIX(-2);
                }
                self->velocityY = FIX(-3);
                self->pose = 0;
                self->poseTimer = 0;
                self->step_s++;
            }
            break;
        case JACKO_JUMP_MIDAIR:
            if (UnkCollisionFunc3(sensors1)) {
                self->step_s++;
            }
            CheckFieldCollision(sensors3, 2);
            break;
        case JACKO_JUMP_LANDING:
            if (AnimateEntity(anim_jump_landing, self) == 0) {
                SetStep(JACKO_WALK_BACK);
            }
        }
        break;
    case JACKO_DEAD:
        PlaySfxPositional(SFX_SKELETON_DEATH_B);
        for (i = 0; i < 6; i++) {
            other = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (other == NULL) {
                break;
            }
            CreateEntityFromCurrentEntity(E_JACKO_DEATH_PARTS, other);
            other->facingLeft = self->facingLeft;
            other->params = i;
            other->params |= (self->params << 8);
            other->ext.jackoBones.deathPartLife = death_parts_lifetimes[i];
            if (self->facingLeft) {
                other->posX.i.hi -= death_parts_xPos[i];
            } else {
                other->posX.i.hi += death_parts_xPos[i];
            }
            other->posY.i.hi += death_parts_yPos[i];
            other->velocityX = death_parts_xVels[i];
            other->velocityY = death_parts_yVels[i];
        }
        DestroyEntity(self);
        break;
    }
}


extern EInit g_EInitJackOBones2;

extern u16 death_parts_rotspeeds[];

void EntityJackOBonesDeathParts(Entity* self) {
    if (self->step) {
        if (--self->ext.jackoBones.deathPartLife) {
            self->rotate += death_parts_rotspeeds[self->params];
            FallEntity();
            MoveEntity();
            return;
        }
        self->entityId = E_EXPLOSION;
        self->pfnUpdate = EntityExplosion;
        self->params = 0;
        self->step = 0;
        return;
    }
    InitializeEntity(g_EInitJackOBones2);
    self->animCurFrame = (self->params & 0xFF) + 15;
    if (self->params & 0x100) {
        self->palette += 1;
    }
    self->drawFlags = ENTITY_ROTATE;
    if (self->facingLeft) {
        self->velocityX = -self->velocityX;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesJack);

#define NOVA_CHARGE 6
extern s16 D_us_80181FAC[];

static void TryShoot(void) {

    s32 unused = UnkCollisionFunc2(&D_us_80181FAC);

    if (!g_CurrentEntity->ext.nova.cooldown) {
        if (GetDistanceToPlayerX() >= 0x80) {
            return;
        }
        if ((g_CurrentEntity->facingLeft) ^ (GetSideToPlayer() & 1)) {
            SetStep(NOVA_CHARGE);
        }
    } else {
        g_CurrentEntity->ext.nova.cooldown--;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", DrawLaserRing);

INCLUDE_RODATA("st/rno0/nonmatchings/unk_48100", D_us_801B5D8C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaSkeleton);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityBladeSoldierDeathParts);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaLaser);

extern EInit D_us_80180B64;

void EntityNovaLaserPulse(Entity* self) {
    s32 temp_s0;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180B64);
        self->hitboxState = 0;
        self->animCurFrame = 0x24;
        self->drawFlags |= ENTITY_SCALEY | ENTITY_SCALEX;
        self->scaleX = self->scaleY = 0x10;
        if (self->facingLeft) {
            self->velocityX = FIX(8.0);
        } else {
            self->velocityX = FIX(-8.0);
        }
        // fallthrough

    case 1:
        MoveEntity();
        self->ext.nova.laserPulseDist += abs(self->velocityX);
        self->scaleX = self->scaleY += 0x40;
        if (self->scaleX < 0x100) {
            return;
        }
        self->step++;
        return;
    case 2:
        MoveEntity();
        self->ext.nova.laserPulseDist += abs(self->velocityX);
        temp_s0 = (self->ext.nova.laserLength + 0x20) << 0x10;
        temp_s0 -= self->ext.nova.laserPulseDist;
        if (temp_s0 < 0) {
            DestroyEntity(self);
            return;
        }

        temp_s0 >>= 0x10;
        temp_s0 <<= 3;
        if (temp_s0 > 0x100) {
            temp_s0 = 0x100;
        }
        break;
    }
}
