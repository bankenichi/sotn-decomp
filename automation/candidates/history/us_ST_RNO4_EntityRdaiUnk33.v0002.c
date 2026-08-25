/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntityRdaiUnk33
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_rdai_unk33.h
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
void PlaySfxPositional(s32 arg0);
void InitializeEntity(u16 arg0[]);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
int FntPrint(const char* fmt, ...);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BBE58_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BC650_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCA5C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCB9C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCD80_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCE4C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCFC8_from_rnz1);

#define JACKO_JUMP 5
#define JACKO_THROW 4
extern u16 D_us_801829DC[];
extern s16 D_us_801829E4[];

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180BFC;

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180C20;

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180C38;

extern EInit D_us_80180C38;
extern u8 D_us_80182B90[];

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitRdaiUnk33;
extern u8 g_RdaiUnk33Anim2[];
extern u8 g_RdaiUnk33Anim3[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern u8 g_RdaiUnk33Anim4[];
extern u8 g_RdaiUnk33Anim5[];
extern char g_RdaiUnk33DebugText[];

void EntityRdaiUnk33(Entity* self) {
    Entity* entity;
    s32 i;

    if ((self->flags & FLAG_DEAD) && !RDAI_UNK33_DEATH_STARTED(self)) {
        PlaySfxPositional(SFX_EXPLODE_B);
        if (self->params) {
            SetStep(5);
        } else {
            SetStep(3);
        }
        RDAI_UNK33_DEATH_STARTED(self) = 1;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitRdaiUnk33);
        if (self->params) {
            SetStep(4);
            break;
        }
        self->hitboxOffY = -4;
        SetStep(2);
        break;

    case 2:
        AnimateEntity(g_RdaiUnk33Anim2, self);
        break;

    case 3:
        if (!AnimateEntity(g_RdaiUnk33Anim3, self)) {
            for (i = 0; i < 16; i++) {
                entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (entity != NULL) {
                    CreateEntityFromEntity(E_UNK_34, self, entity);
                }
            }
            DestroyEntity(self);
        }
        break;

    case 4:
        AnimateEntity(g_RdaiUnk33Anim4, self);
        break;

    case 5:
        if (!AnimateEntity(g_RdaiUnk33Anim5, self)) {
            for (i = 0; i < 16; i++) {
                entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (entity != NULL) {
                    CreateEntityFromEntity(E_UNK_34, self, entity);
                }
            }
            DestroyEntity(self);
        }
        break;

    case 0xFF:
#if defined(VERSION_PSP)
        FntPrint(g_RdaiUnk33DebugText, self->animCurFrame);
#else
        FntPrint("charal %x\n", self->animCurFrame);
#endif
        if (RDAI_UNK33_PAD_PRESSED & PAD_SQUARE) {
            if (self->params) {
                break;
            }
            self->animCurFrame++;
            self->params |= 1;
        } else {
            self->params = 0;
        }
        if (RDAI_UNK33_PAD_PRESSED & PAD_CIRCLE) {
            if (self->step_s) {
                break;
            }
            self->animCurFrame--;
            self->step_s |= 1;
        } else {
            self->step_s = 0;
        }
        break;
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180C50;

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
