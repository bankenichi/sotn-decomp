// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180B40;

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180B64;

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
