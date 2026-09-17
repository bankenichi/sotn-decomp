/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO4:EntityNovaSkeleton
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rno4/unk_58A30.c
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
void FallEntity(void);
void MoveEntity();
void InitializeEntity(u16 arg0[]);
s16 GetDistanceToPlayerX();
u8 GetSideToPlayer();
void DestroyEntity(Entity*);
void UnkPolyFunc2(Primitive* prim);
s32 UnkCollisionFunc3(s16* sensors);
u8 AnimateEntity(u8 frames[], Entity* entity);
void PlaySfxPositional(s32 arg0);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 PrimDecreaseBrightness(Primitive* prim, u8 arg1);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
int abs(int x);
extern void (*g_api_PlaySfx)(s32 sfxId);
s32 Random();
int rcos(int a);
int rsin(int a);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int DrawLaserRing();
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



INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityJackOBones);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitNovaSkeleton;
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityNovaSkeleton(Entity* self) {
    extern u8 g_NovaSkeletonSensors[];
    extern u8 g_NovaSkeletonAnimWalkLeft[];
    extern u8 g_NovaSkeletonAnimWalkRight[];
    extern u8 g_NovaSkeletonAnimIdle[];
    extern u8 g_NovaSkeletonAnimAttack[];
    extern u8 g_NovaSkeletonAnimAttackEnd[];
    extern u8 g_NovaSkeletonDeathPartLifetimes[];
    extern s32 g_NovaSkeletonDeathPartVelocityX[];
    extern s32 g_NovaSkeletonDeathPartVelocityY[];
    extern s16 g_NovaSkeletonDeathPartOffsetX[];
    extern s16 g_NovaSkeletonDeathPartOffsetY[];
    extern u8 g_NovaSkeletonCooldowns[];
    s32 var_s4;
    Entity* other;
    Primitive* prim;
    s32 primIndex;
    s32 i;

    if (self->flags & FLAG_DEAD) {
        SetStep(8);
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitNovaSkeleton);
        self->ext.nova.cooldown = 0x50;



        primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);

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

    case 1:
        if (UnkCollisionFunc3(g_NovaSkeletonSensors) == 0) {
            break;
        }
        SetStep(2);
        break;

    case 2:
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        AnimateEntity(g_NovaSkeletonAnimIdle, self);
        if (GetDistanceToPlayerX() < 0x70) {
            SetStep(4);
        }
        break;

    case 3:
        if (AnimateEntity(g_NovaSkeletonAnimWalkLeft, self) == 0) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        }
        self->ext.nova.movingLeft = self->facingLeft;
        if (self->ext.nova.movingLeft) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        if (GetDistanceToPlayerX() < 0x4C) {
            self->step = 4;
        }
        TryShoot();
        break;

    case 4:
        if (AnimateEntity(g_NovaSkeletonAnimWalkRight, self) == 0) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        }
        self->ext.nova.movingLeft = self->facingLeft ^ 1;
        if (self->ext.nova.movingLeft) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        if (GetDistanceToPlayerX() > 0x5C) {
            self->step = 3;
        }
        TryShoot();
        break;

    case 5:
        break;

    case 6:
        if (AnimateEntity(g_NovaSkeletonAnimAttack, self) == 0) {
            self->ext.nova.ringState = 0;
            SetStep(7);
        }
        if ((!self->poseTimer) && (self->pose == 2)) {
            PlaySfxPositional(SFX_ELECTRICITY);
        }
        break;

    case 7:
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
        if (AnimateEntity(g_NovaSkeletonAnimAttackEnd, self) == 0) {
            prim = self->ext.nova.prim;
            prim->drawMode = DRAW_HIDE;
            var_s4 = ++self->ext.nova.laserTimerIndex & 7;
            self->ext.nova.cooldown = g_NovaSkeletonCooldowns[var_s4];
            SetStep(4);
        }
        break;

    case 8:
        for (i = 0; i < 6; i++) {
            other = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (other == NULL) {
                break;
            }
            CreateEntityFromCurrentEntity(E_BLADE_SOLDIER_DEATH_PARTS, other);
            other->facingLeft = self->facingLeft;
            other->params = i;
            other->ext.nova.deathPartLife = g_NovaSkeletonDeathPartLifetimes[i];
            if (self->facingLeft) {
                other->posX.i.hi -= g_NovaSkeletonDeathPartOffsetX[i];
            } else {
                other->posX.i.hi += g_NovaSkeletonDeathPartOffsetX[i];
            }
            other->posY.i.hi += g_NovaSkeletonDeathPartOffsetY[i];
            other->velocityX = g_NovaSkeletonDeathPartVelocityX[i];
            other->velocityY = g_NovaSkeletonDeathPartVelocityY[i];
        }
        PlaySfxPositional(SFX_SKELETON_DEATH_B);
        DestroyEntity(self);
        break;
    }
}


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
extern EInit g_EInitImpSmoke;
extern u8 anim_imp_smoke[];

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern unkGraphicsStruct g_unkGraphicsStruct;

void EntityImpSmoke(Entity* self) {
    Entity* player;

    if (!self->step) {
        InitializeEntity(g_EInitImpSmoke);
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
    if (AnimateEntity(anim_imp_smoke, self) == 0) {
        DestroyEntity(self);
    }
}



INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityRdaiUnk33);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitImpDeathParticle;
extern u8 g_ImpDeathParticleAnim[];

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
        InitializeEntity(g_EInitImpDeathParticle);
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
        AnimateEntity(g_ImpDeathParticleAnim, self);
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
