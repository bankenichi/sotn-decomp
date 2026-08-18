/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO0:EntityNovaSkeleton
   score  : 10
   receipt: nonmatchings/.adapt-scores/20260818-193644-71274-141799/EntityNovaSkeleton/adapt-score.json
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

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
void DestroyEntity(Entity*);
int GetDistanceToPlayerX();
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
extern int GetSideToPlayer();
extern int AnimateEntity();
extern int PlaySfxPositional();

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", TryThrow);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBones);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesJack);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", TryShoot);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", DrawLaserRing);

INCLUDE_RODATA("st/rno0/nonmatchings/unk_48100", D_us_801B5D8C);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitNovaSkeleton;
extern Primitive g_PrimBuf[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

#define E_NOVA_DEATH_PARTS 42
#define NOVA_1 1
#define NOVA_5 5
#define NOVA_CHARGE 6
#define NOVA_DEAD 8
#define NOVA_IDLE 2
#define NOVA_INIT 0
#define NOVA_SHOOT 7
#define NOVA_WALK_BACK 4
#define NOVA_WALK_FWD 3
extern EInit g_EInitNovaSkeleton;
extern s16 D_us_80181F9C[];
extern u8 D_us_80181FB4[];
extern u8 D_us_80181FC4[];
extern u8 D_us_80181FEC[];
extern u8 D_us_80181FF8[];
extern u8 D_us_8018203C[];
extern u8 D_us_8018207C[];
extern s32 D_us_80182084[];
extern s32 D_us_801820A4[];
extern s16 D_us_801820C4[];
extern s16 D_us_801820D4[];
extern u8 D_us_801820E4[];
void TryShoot(void);
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

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaLaserPulse);
