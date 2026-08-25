/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO0:EntityNovaSkeleton
   score  : 10
   receipt: nonmatchings/.adapt-scores/20260824-235350-62298-341400/EntityNovaSkeleton-2/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno0/unk_48100.c
   asm    : asm/us/st/rno0/nonmatchings/unk_48100/EntityNovaSkeleton.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
void DestroyEntity(Entity*);
s32 GetSideToPlayer(void);
s16 GetDistanceToPlayerX();
void PlaySfxPositional(s32 arg0);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 PrimDecreaseBrightness(Primitive* prim, u8 arg1);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int UnkPolyFunc2();
extern int UnkCollisionFunc3();
extern int AnimateEntity();
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

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBones);

extern EInit D_us_80180B40;

extern u16 D_us_80181F00[];

void EntityJackOBonesDeathParts(Entity* self) {
    if (self->step) {
        if (--self->ext.jackoBones.deathPartLife) {
            self->rotate += D_us_80181F00[self->params];
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
    InitializeEntity(D_us_80180B40);
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitNovaSkeleton;

#define E_NOVA_DEATH_PARTS 42
#define NOVA_1 1
#define NOVA_5 5
#define NOVA_DEAD 8
#define NOVA_IDLE 2
#define NOVA_INIT 0
#define NOVA_SHOOT 7
#define NOVA_WALK_BACK 4
#define NOVA_WALK_FWD 3
extern EInit g_EInitNovaSkeleton;
extern s16 D_us_80181F9C[8];
extern u8 D_us_80181FB4[13];
extern u8 D_us_80181FC4[13];
extern u8 D_us_80181FEC[11];
extern u8 D_us_80181FF8[66];
extern u8 D_us_8018203C[48];
extern u8 D_us_8018207C[8];
extern s32 D_us_80182084[8];
extern s32 D_us_801820A4[8];
extern s16 D_us_801820C4[8];
extern s16 D_us_801820D4[8];
extern u8 D_us_801820E4[8];
void DrawLaserRing(void);

void EntityNovaSkeleton(Entity* self) {
    s32 var_s4;
    Entity* other;
    Primitive* prim;
    s32 primIndex;
    s32 i;

    if (self->flags & FLAG_DEAD) {
        SetStep(NOVA_DEAD);
    }
    switch (self->step) {
    case NOVA_INIT:
        InitializeEntity(g_EInitNovaSkeleton);
        self->ext.nova.cooldown = 0x50;
 
#if defined(VERSION_PSP)
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 2);
#else
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 1);
#endif
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.nova.prim = prim;
        UnkPolyFunc2(prim);
        prim->tpage = 0x12;
        prim->clut = 0x216;
        prim->u0 = prim->u2 = 0xC0;
        prim->u1 = prim->u3 = 0xFF;
        prim->v0 = prim->v1 = 0;
        prim->v2 = prim->v3 = 0x40;
        prim->priority = self->zPriority + 1;
        prim->drawMode = DRAW_HIDE;
        break;
    case NOVA_1:
        if (UnkCollisionFunc3(D_us_80181F9C) == 0) {
            break;
        }
        SetStep(NOVA_IDLE);
        break;
    case NOVA_IDLE:
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        AnimateEntity(&D_us_80181FEC, self);
        if (GetDistanceToPlayerX() < 0x70) {
            SetStep(NOVA_WALK_BACK);
        }
        break;
    case NOVA_WALK_FWD:
        if (AnimateEntity(&D_us_80181FB4, self) == 0) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        }
        self->ext.nova.movingLeft = self->facingLeft;
        if (self->ext.nova.movingLeft) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        if (GetDistanceToPlayerX() < 0x4C) {
            self->step = NOVA_WALK_BACK;
        }
        TryShoot();
        break;
    case NOVA_WALK_BACK:
        if (AnimateEntity(&D_us_80181FC4, self) == 0) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        }
        self->ext.nova.movingLeft = self->facingLeft ^ 1;
        if (self->ext.nova.movingLeft) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        if (GetDistanceToPlayerX() > 0x5C) {
            self->step = NOVA_WALK_FWD;
        }
        TryShoot();
        break;
     
    case NOVA_5:
        break;
    case NOVA_CHARGE:
        if (AnimateEntity(&D_us_80181FF8, self) == 0) {
            self->ext.nova.ringState = 0;
            SetStep(NOVA_SHOOT);
        }
        if ((!self->poseTimer) && (self->pose == 2)) {
            PlaySfxPositional(SFX_ELECTRICITY);
        }
        break;
    case NOVA_SHOOT:
        switch (self->step_s) {
        case 0:
            other = self + 1;
            CreateEntityFromEntity(E_NOVA_LASER, self, other);
            if (self->facingLeft) {
                other->posX.i.hi += 0xA;
            } else {
                other->posX.i.hi -= 0xA;
            }
            other->posY.i.hi -= 4;
            other->facingLeft = self->facingLeft;
            self->step_s++;
            break;
        case 1:
            prim = self->ext.nova.prim;
            PrimDecreaseBrightness(prim, 5);
            break;
        }
        DrawLaserRing();
        if (!AnimateEntity(&D_us_8018203C, self)) {
            prim = self->ext.nova.prim;
            prim->drawMode = DRAW_HIDE;
            var_s4 = ++self->ext.nova.laserTimerIndex & 7;
            self->ext.nova.cooldown = D_us_801820E4[var_s4];
            SetStep(NOVA_WALK_BACK);
        }
        break;
    case NOVA_DEAD:
        for (i = 0; i < 6; i++) {
            other = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (other == NULL) {
                break;
            }
            CreateEntityFromCurrentEntity(E_NOVA_DEATH_PARTS, other);
            other->facingLeft = self->facingLeft;
            other->params = i;
            other->ext.nova.deathPartLife = D_us_8018207C[i];
            if (self->facingLeft) {
                other->posX.i.hi -= D_us_801820C4[i];
            } else {
                other->posX.i.hi += D_us_801820C4[i];
            }
            other->posY.i.hi += D_us_801820D4[i];
            other->velocityX = D_us_80182084[i];
            other->velocityY = D_us_801820A4[i];
        }
        PlaySfxPositional(SFX_SKELETON_DEATH_B);
        DestroyEntity(self);
        break;
    }
}

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
