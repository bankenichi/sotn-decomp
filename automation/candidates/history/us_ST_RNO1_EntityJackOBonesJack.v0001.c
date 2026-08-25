/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:EntityJackOBonesJack
   source : upstream/master:src/st/e_jack_o_bones.h
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
void MoveEntity();
void PlaySfxPositional(s32 arg0);
int abs(int x);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", TryThrow);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBones);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBonesDeathParts);

void EntityJackOBonesJack(Entity* self) {
    Collider sp10;
    s32 temp;
    s32 yVar;
    s32 xVar;

    if (!self->step) {
        InitializeEntity(g_EInitJackOBones3);
        if (self->params) {
            self->palette += 1;
        }
        self->animCurFrame = 0x15;
        self->drawFlags |= ENTITY_ROTATE;
        if (self->params) {
            yVar = FIX(4);
            xVar = FIX(1);
        } else {
            yVar = FIX(-1);
            xVar = FIX(2.5);
        }
        if (self->facingLeft) {
            self->velocityX = xVar;
        } else {
            self->velocityX = -xVar;
        }
        self->velocityY = yVar;
    }
    MoveEntity();
    self->velocityY += FIX(0.1875);
    self->rotate -= 0x40;
    xVar = self->posX.i.hi;
    yVar = self->posY.i.hi + 5;
    g_api.CheckCollision(xVar, yVar, &sp10, 0);
    if (sp10.effects & EFFECT_SOLID) {
        PlaySfxPositional(SFX_SKULL_KNOCK_A);
        self->ext.jackoBones.bouncesDone += 1;
        temp = sp10.unk18;
#if defined(VERSION_PSP)
        xVar = self->posX.i.hi;
        yVar = self->posY.i.hi - 3;
        g_api.CheckCollision(xVar, yVar, &sp10, 0);
        if (sp10.effects & EFFECT_SOLID) {
            self->velocityX = -self->velocityX;
        } else {
#else
        if (1) {
#endif
            self->posY.i.hi += temp;
#if defined(VERSION_PSP)
            self->velocityY = -self->velocityY;
#else
            self->velocityY =
                -((self->velocityY < 0) ? -self->velocityY : self->velocityY);
#endif
            if (self->params) {
                self->velocityY = FIX(-7) / self->ext.jackoBones.bouncesDone;
            } else {
                self->velocityY -= self->velocityY / 16;
            }
        }
        xVar = self->posX.i.hi + self->velocityX;
        yVar = self->posY.i.hi;
    }
#if defined(VERSION_PSP)
    if (self->params) {
#else
    if (1) {
#endif
        xVar = self->posX.i.hi;
        yVar = self->posY.i.hi - 5;
        g_api.CheckCollision(xVar, yVar, &sp10, 0);
        if (sp10.effects & EFFECT_SOLID) {
            self->posY.i.hi += sp10.unk20;
            self->velocityY = abs(self->velocityY);
        }
#if !defined(VERSION_PSP)
        xVar = self->posX.i.hi;
        yVar = self->posY.i.hi;
        if (self->velocityX > 0) {
            xVar += 5;
        } else {
            xVar -= 5;
        }
        g_api.CheckCollision(xVar, yVar, &sp10, 0);
        if (sp10.effects & EFFECT_SOLID) {
            self->velocityX = -self->velocityX;
        }
        if (self->params)
#endif
            if (self->ext.jackoBones.bouncesDone > 8) {
                self->flags |= FLAG_DEAD;
            }
    }

    if (self->flags & FLAG_DEAD) {
        self->drawFlags = ENTITY_DEFAULT;
        self->entityId = E_EXPLOSION;
        self->pfnUpdate = EntityExplosion;
        self->params = 0;
        self->step = 0;
    }
}


INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", TryShoot);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", DrawLaserRing);

INCLUDE_RODATA("st/rno1/nonmatchings/unk_35378", D_us_801A5DDC);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaSkeleton);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityBladeSoldierDeathParts);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaLaser);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaLaserPulse);
