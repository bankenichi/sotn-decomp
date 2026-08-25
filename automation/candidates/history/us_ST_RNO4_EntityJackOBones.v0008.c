/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO4:EntityJackOBones
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_jack_o_bones.h
   target : src/st/rno4/unk_58A30.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

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
extern void (*g_api_PlaySfx)(s32 sfxId);
int rcos(int a);
int rsin(int a);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BBE58_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BC650_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCA5C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCB9C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCD80_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCE4C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCFC8_from_rnz1);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define JACKO_JUMP 5
#define JACKO_THROW 4
extern u16 D_us_801829DC[];
extern s16 D_us_801829E4[];

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

static void TryThrow(void) {
    s32 temp_s1;
    u16 temp_s0;

    temp_s1 = UnkCollisionFunc2(D_us_801829DC);
    temp_s0 = UnkCollisionFunc(D_us_801829E4, 3);
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

        self->ext.jackoBones.throwTimer = 0x50;


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

        if (self->params) {
            i = 11;
        } else {
            i = 10;
        }

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


/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit D_us_80180BFC;
extern u16 D_us_80182954[];

void EntityJackOBonesDeathParts(Entity* self) {
    if (self->step) {
        if (--self->ext.jackoBones.deathPartLife) {
            self->rotate += D_us_80182954[self->params];
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
    InitializeEntity(D_us_80180BFC);
    self->animCurFrame = (self->params & 0xFF) + 15;
    if (self->params & 0x100) {
        self->palette += 1;
    }
    self->drawFlags = ENTITY_ROTATE;
    if (self->facingLeft) {
        self->velocityX = -self->velocityX;
    }
}



INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityJackOBonesJack);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define NOVA_CHARGE 6
extern s16 D_us_80182A00[];

static void TryShoot(void) {

    s32 unused = UnkCollisionFunc2(&D_us_80182A00);

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



INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", DrawLaserRing);

INCLUDE_RODATA("st/rno4/nonmatchings/unk_58A30", D_us_801C4800);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityNovaSkeleton);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityBladeSoldierDeathParts);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityNovaLaser);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit D_us_80180C20;

void EntityNovaLaserPulse(Entity* self) {
    s32 temp_s0;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180C20);
        self->hitboxState = 0;
        self->animCurFrame = 0x24;
        self->drawFlags |= ENTITY_SCALEY | ENTITY_SCALEX;
        self->scaleX = self->scaleY = 0x10;
        if (self->facingLeft) {
            self->velocityX = FIX(8.0);
        } else {
            self->velocityX = FIX(-8.0);
        }


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



INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityImp);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit D_us_80180C38;
extern u8 D_us_80182B90[];

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern unkGraphicsStruct g_unkGraphicsStruct;

void EntityImpSmoke(Entity* self) {
    Entity* player;

    if (!self->step) {
        InitializeEntity(D_us_80180C38);
        self->zPriority = g_unkGraphicsStruct.g_zEntityCenter + 4;
        player = &PLAYER;
        self->posX.i.hi = player->posX.i.hi;
        self->posY.i.hi = player->posY.i.hi - 0x18;
        if (player->facingLeft) {
            self->posX.i.hi -= 6;
        } else {
            self->posX.i.hi += 6;
        }
        g_api_PlaySfx(SFX_BONE_THROW);
    }
    self->posY.val -= FIX(0.5);
    if (AnimateEntity(D_us_80182B90, self) == 0) {
        DestroyEntity(self);
    }
}



INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityRdaiUnk33);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit D_us_80180C50;
extern u8 D_us_80182BF4[];

void EntityImpDeathParticle(Entity* self) {
    s32 speed;
    s16 angle;

    if (self->flags & FLAG_DEAD) {
        PlaySfxPositional(SFX_SMALL_FLAME_IGNITE);
        self->pfnUpdate = EntityExplosion;
        self->step = 0;
        self->params = 0;
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180C50);
        self->facingLeft = Random() & 1;
        speed = (Random() & 0x1F) + 0x10;
        angle = Random() * 6 + 0x900;
        self->velocityX = speed * rcos(angle);
        self->velocityY = speed * rsin(angle);
        self->posX.val += self->velocityX * 4;
        self->posY.val += self->velocityY * 4;
        self->ext.imp.timer = (Random() & 0x1F) + 0x10;
        self->rotate = angle;

    case 1:
        AnimateEntity(D_us_80182BF4, self);
        MoveEntity();
        self->velocityX -= self->velocityX / 16;
        self->velocityY -= self->velocityY / 16;
        if (!--self->ext.imp.timer) {
            self->velocityX = 0;
            self->step++;
        }
        break;

    case 2:
        MoveEntity();
        if (self->velocityY < FIX(0.5)) {
            self->velocityY += FIX(0.03125);
        }
#if defined(VERSION_PSP)
        angle = self->rotate += 0x80;
        self->velocityX = (rcos(angle) << 15) >> 12;
#else
        self->rotate += 0x80;
        self->velocityX = (rcos(self->rotate) << 15) >> 12;
#endif
        break;
    }
}


