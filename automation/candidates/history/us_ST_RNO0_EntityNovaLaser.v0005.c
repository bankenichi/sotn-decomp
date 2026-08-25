/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO0:EntityNovaLaser
   score  : 10
   receipt: nonmatchings/.adapt-scores/20260824-235343-62298-047826/EntityNovaLaser-2/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno0/unk_48100.c
   asm    : asm/us/st/rno0/nonmatchings/unk_48100/EntityNovaLaser.s
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
void FallEntity(void);
void MoveEntity();
void InitializeEntity(u16 arg0[]);
s16 GetDistanceToPlayerX();
s32 GetSideToPlayer(void);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
void DestroyEntity(Entity*);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void PlaySfxPositional(s32 arg0);
s32 Random();
int abs(int x);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int UnkCollisionFunc2();
extern int UnkCollisionFunc();
extern int SetStep();
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

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaSkeleton);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityBladeSoldierDeathParts);

#define E_NOVA_PULSE 41
#define LASER_1 1
#define LASER_2 2
#define LASER_3 3
#define LASER_4 4
#define LASER_INIT 0
extern EInit D_us_80180B64;
extern u8 D_us_80182118[12];

void EntityNovaLaser(Entity* self) {
    s32 centerX;
    s32 primIndex;
    s32 centerY;
    Entity* other;
    s32 primX;
    s32 var_s2;
    u8* var_s1;
    Primitive* prim;

    switch (self->step) {
    case LASER_INIT:
        InitializeEntity(D_us_80180B64);
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 3);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.nova.prim = prim;
        var_s1 = &D_us_80182118[0];
        for (var_s2 = 0; var_s2 < 3; prim = prim->next, var_s2++) {
            prim->tpage = 0x12;
            prim->clut = 0x216;
            prim->u0 = prim->u2 = *var_s1++ + 0x80;
            prim->u1 = prim->u3 = *var_s1++ + 0x80;
            prim->v0 = prim->v1 = 0x40;
            prim->v2 = prim->v3 = 0x5F;
            prim->r0 = prim->g0 = prim->b0 = *var_s1++;
            LOW(prim->r2) = LOW(prim->r0);
            prim->r1 = prim->g1 = prim->b1 = *var_s1++;
            LOW(prim->r3) = LOW(prim->r1);
            prim->priority = self->zPriority + 2;
            prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS |
                             DRAW_UNK02 | DRAW_TRANSP;
        }
        self->ext.nova.laserTimer = 0x60;
        self->ext.nova.laserLength = 0;
    case LASER_1:
        self->ext.nova.laserFadeTimer = 0x10;
        if (self->ext.nova.laserLength < 0x80) {
            self->ext.nova.laserLength += 0x10;
        } else {
            self->ext.nova.laserLength = 0x80;
            self->hitboxState = 1;
            self->step++;
        }
    case LASER_2:
        if (!(self->ext.nova.laserTimer & 3)) {
            other = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (other != NULL) {
                CreateEntityFromEntity(E_NOVA_PULSE, self, other);
                other->zPriority = self->zPriority - 1;
                other->ext.nova.laserLength = self->ext.nova.laserLength;
                other->facingLeft = self->facingLeft;
            }
        }
        if (!(self->ext.nova.laserTimer & 0xF)) {
            PlaySfxPositional(SFX_BAT_ECHO_A);
        }
        if (self->ext.nova.laserTimer < 0x10) {
            PlaySfxPositional(SFX_BAT_ECHO_D);
            self->step++;
        }
    case LASER_3:
        if (Random() & 1) {
            if (self->ext.nova.laserLength < 0x88) {
                self->ext.nova.laserLength++;
            } else if (self->ext.nova.laserLength > 0x78) {
                self->ext.nova.laserLength--;
            }
        }
        self->hitboxWidth = self->ext.nova.laserLength / 2 + 0x10;
        self->hitboxOffX = -self->ext.nova.laserLength / 2 - 0x10;
        self->hitboxHeight = 8;
        other = self - 1;
        if (other->entityId != E_NOVA_SKELETON) {
            self->ext.nova.laserTimer = 1;
        }
        if (!--self->ext.nova.laserTimer) {
            self->hitboxState = 0;
            self->step++;
        }
        break;
    case LASER_4:
        self->ext.nova.laserFadeTimer--;
        if (!self->ext.nova.laserFadeTimer) {
            DestroyEntity(self);
            return;
        }
        break;
    }
    centerX = self->posX.i.hi;
    centerY = self->posY.i.hi;
    prim = self->ext.nova.prim;
    for (var_s2 = 0; var_s2 < 3; prim = prim->next, var_s2++) {
        prim->y0 = prim->y1 = centerY - self->ext.nova.laserFadeTimer;
        prim->y2 = prim->y3 = centerY + self->ext.nova.laserFadeTimer;
        if (g_Timer & 1) {
            prim->clut = 0x216;
        } else {
            prim->clut = 0x217;
        }
    }
    prim = self->ext.nova.prim;
    primX = centerX;
    if (self->facingLeft) {
        primX -= 0x10;
    } else {
        primX += 0x10;
    }

    prim->x1 = prim->x3 = primX;
    if (self->facingLeft) {
        primX += 0x20;
    } else {
        primX -= 0x20;
    }

    prim->x0 = prim->x2 = primX;
    prim = prim->next;
    prim->x1 = prim->x3 = primX;
    if (self->facingLeft) {
        primX += self->ext.nova.laserLength;
    } else {
        primX -= self->ext.nova.laserLength;
    }

    prim->x0 = prim->x2 = primX;
    prim = prim->next;
    prim->x1 = prim->x3 = primX;
    if (self->facingLeft) {
        primX += 0x20;
    } else {
        primX -= 0x20;
    }
    prim->x0 = prim->x2 = primX;
    prim = prim->next;
}

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
