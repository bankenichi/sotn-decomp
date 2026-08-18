/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO0:EntityJackOBones
   score  : 20
   receipt: nonmatchings/.adapt-scores/20260818-193651-71274-127578/EntityJackOBones/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno0/unk_48100.c
   asm    : asm/us/st/rno0/nonmatchings/unk_48100/EntityJackOBones.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
s16 GetDistanceToPlayerX();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
s32 Random();
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int GetSideToPlayer();
extern int UnkCollisionFunc3();
extern int AnimateEntity();
extern int SetStep();
extern int PlaySfxPositional();
extern int CheckFieldCollision();
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", TryThrow);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitJackOBones;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

#define E_JACKO_DEATH_PARTS 37
#define E_JACKO_JACK 38
#define JACKO_1 1
#define JACKO_DEAD 6
#define JACKO_INIT 0
#define JACKO_JUMP 5
#define JACKO_JUMP_LANDING 2
#define JACKO_JUMP_MIDAIR 1
#define JACKO_JUMP_WINDUP 0
#define JACKO_THROW 4
#define JACKO_WALK_BACK 3
#define JACKO_WALK_FWD 2
extern EInit g_EInitJackOBones;
extern u8 D_us_80181EB0[];
extern u8 D_us_80181EC0[];
extern u8 D_us_80181ED0[];
extern u8 D_us_80181EE8[];
extern u8 D_us_80181EF4[];
extern u8 D_us_80181F10[];
extern s32 D_us_80181F18[];
extern s32 D_us_80181F34[];
extern s16 D_us_80181F50[];
extern s16 D_us_80181F60[];
extern u8 D_us_80181F70[][4];
extern s16 D_us_80181F78[];
extern s16 D_us_80181F90[];
void TryThrow(void);

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
        if (UnkCollisionFunc3(D_us_80181F78) == 0) {
            break;
        }
        self->step++;
        break;
    case JACKO_WALK_FWD:
        if (AnimateEntity(D_us_80181EB0, self) == 0) {
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
        if (AnimateEntity(D_us_80181EC0, self) == 0) {
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
        var_s2 = AnimateEntity(D_us_80181ED0, self);
         
        if (self->params) {
            i = 11;
        } else {
            i = 10;
        }
         
        if (!var_s2) {
            SetStep(JACKO_WALK_BACK);
            var_s2 = ++self->ext.jackoBones.throwTimerIndex & 3;
            self->ext.jackoBones.throwTimer =
                D_us_80181F70[self->params & 1][var_s2];
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
            if (!(AnimateEntity(D_us_80181EE8, self) & 1)) {
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
            if (UnkCollisionFunc3(D_us_80181F78)) {
                self->step_s++;
            }
            CheckFieldCollision(D_us_80181F90, 2);
            break;
        case JACKO_JUMP_LANDING:
            if (AnimateEntity(D_us_80181EF4, self) == 0) {
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
            other->ext.jackoBones.deathPartLife = D_us_80181F10[i];
            if (self->facingLeft) {
                other->posX.i.hi -= D_us_80181F50[i];
            } else {
                other->posX.i.hi += D_us_80181F50[i];
            }
            other->posY.i.hi += D_us_80181F60[i];
            other->velocityX = D_us_80181F18[i];
            other->velocityY = D_us_80181F34[i];
        }
        DestroyEntity(self);
        break;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesJack);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", TryShoot);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", DrawLaserRing);

INCLUDE_RODATA("st/rno0/nonmatchings/unk_48100", D_us_801B5D8C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaSkeleton);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityBladeSoldierDeathParts);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaLaser);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaLaserPulse);
