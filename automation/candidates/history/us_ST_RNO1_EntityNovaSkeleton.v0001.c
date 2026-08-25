/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:EntityNovaSkeleton
   source : upstream/master:src/st/e_nova_skeleton.h
   target : src/st/rno1/unk_35378.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
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
extern int DrawLaserRing();
extern int TryShoot();
extern int SetStep();
extern int UnkPolyFunc2();
extern int UnkCollisionFunc3();
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", TryThrow);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBones);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBonesJack);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", TryShoot);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", DrawLaserRing);

INCLUDE_RODATA("st/rno1/nonmatchings/unk_35378", D_us_801A5DDC);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitNovaSkeleton;
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

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
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 2);
#else
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
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
        if (UnkCollisionFunc3(sensors1) == 0) {
            break;
        }
        SetStep(NOVA_IDLE);
        break;
    case NOVA_IDLE:
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        AnimateEntity(&anim_idle, self);
        if (GetDistanceToPlayerX() < 0x70) {
            SetStep(NOVA_WALK_BACK);
        }
        break;
    case NOVA_WALK_FWD:
        if (AnimateEntity(&anim_walk_fwd, self) == 0) {
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
        if (AnimateEntity(&anim_walk_back, self) == 0) {
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
        if (AnimateEntity(&anim_laser_charge, self) == 0) {
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
        if (!AnimateEntity(&anim_laser_blast, self)) {
            prim = self->ext.nova.prim;
            prim->drawMode = DRAW_HIDE;
            var_s4 = ++self->ext.nova.laserTimerIndex & 7;
            self->ext.nova.cooldown = laser_cooldowns[var_s4];
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
            other->ext.nova.deathPartLife = death_parts_lifetimes[i];
            if (self->facingLeft) {
                other->posX.i.hi -= death_parts_xPos[i];
            } else {
                other->posX.i.hi += death_parts_xPos[i];
            }
            other->posY.i.hi += death_parts_yPos[i];
            other->velocityX = death_parts_xVels[i];
            other->velocityY = death_parts_yVels[i];
        }
        PlaySfxPositional(SFX_SKELETON_DEATH_B);
        DestroyEntity(self);
        break;
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityBladeSoldierDeathParts);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaLaser);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaLaserPulse);
