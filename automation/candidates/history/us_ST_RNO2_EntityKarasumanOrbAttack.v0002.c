/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:EntityKarasumanOrbAttack
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/nz1/e_karasuman.c
   target : src/st/rno2/unk_439A4.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
int rcos(int a);
int rsin(int a);
void MoveEntity();
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
extern int GetAngleBetweenEntities();
extern int LimitAngleChange();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C39A4);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4960);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4C0C);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4EA8);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasuman);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanFeatherAttack);

void EntityKarasumanOrbAttack(Entity* self) {
    Entity* entity;
    s16 angle;
    s16 angleBetweenEntities;

#ifndef VERSION_PSP
    if (D_us_80181138 & 2) {
        DestroyEntity(self);
        return;
    }
#endif

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitKarasumanOrbAttack);
        self->drawFlags = ENTITY_SCALEY | ENTITY_SCALEX;
        self->scaleX = self->scaleY = 0;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
         

    case 1:
        self->scaleX = self->scaleY += 6;
        if (self->scaleX > 0xA0) {
            self->step++;
        }
         

    case 2:
        AnimateEntity(D_us_80181200, self);
        entity = self->ext.karasuman.parent;
        if (entity->ext.karasuman.flag1) {
            self->step++;
        }
        break;

    case 3:
        angle = (self->params << 9) + ROT(22.5);
        self->velocityX = rcos(angle) << 6;
        self->velocityY = rsin(angle) << 6;
        self->ext.karasuman.angle = angle;
        self->ext.karasuman.timer = 128;
        self->step++;
         

    case 4:
        entity = &PLAYER;
        angle = GetAngleBetweenEntities(self, entity);
        angle = LimitAngleChange(24, self->ext.karasuman.angle, angle);
        self->velocityX = 64 * rcos(angle);
        self->velocityY = 64 * rsin(angle);
        self->ext.karasuman.angle = angle;
        if (self->hitFlags & 0x80) {
            self->ext.karasuman.timer = 16;
            self->step = 6;
        }

        if (!--self->ext.karasuman.timer) {
            self->step++;
        }
         

    case 5:
        self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA;
        AnimateEntity(D_us_80181200, self);
        MoveEntity();
        break;

    case 6:
        AnimateEntity(D_us_80181200, self);
        entity = &PLAYER;
        self->posX.i.hi = entity->posX.i.hi;
        self->posY.i.hi = entity->posY.i.hi;
        if (!--self->ext.karasuman.timer) {
            self->step = 5;
        }
        break;
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanRavenAttack);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_8018094C;

extern EInit D_us_8018094C;

void EntityKarasumanFeather(Entity* self) {
    s16 angle;
    s32 scale;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_8018094C);
        self->animCurFrame = 63;
        self->drawFlags = ENTITY_ROTATE;
        self->facingLeft = Random() & 1;
        scale = (Random() & 0x1F) + 0x10;
        angle = (Random() * 6) + FLT(9.0 / 16.0);

        self->velocityX = scale * rcos(angle);
        self->velocityY = scale * rsin(angle);
        self->posX.val += 16 * self->velocityX;
        self->posY.val += 16 * self->velocityY;

        self->rotate = angle;
        self->ext.karasuman.timer = 64;
         

    case 1:
        MoveEntity();
        self->velocityX -= self->velocityX / 16;
        self->velocityY -= self->velocityY / 16;

        self->rotate += 64;
        if (!--self->ext.karasuman.timer) {
            self->velocityX = 0;
            self->step++;
        }
        break;

    case 2:
        MoveEntity();
        self->rotate += 32;
        if (self->velocityY < FIX(1.5)) {
            self->velocityY += FIX(1.0 / 32.0);
        }
        break;
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180940;

extern u8 D_us_80181D8C[16];
extern EInit D_us_80180940;

void EntityKarasumanRavenAbsorb(Entity* self) {
    s16 angle;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180940);
        self->blendMode = BLEND_TRANSP;
        self->drawFlags = ENTITY_ROTATE;
        self->hitboxState = 0;

        self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA | FLAG_UNK_2000;
        if (self->params) {
            self->animCurFrame = 0;
            self->step = 4;
            break;
        }
        angle = ROT(-22.5) - ((Random() & 0x3F) * 16);
        self->rotate = -angle;
        if (!self->facingLeft) {
            angle = FLT(0.5) - angle;
        }
        self->velocityX = 56 * rcos(angle);
        self->velocityY = 56 * rsin(angle);
         

    case 1:
        MoveEntity();
        AnimateEntity(D_us_80181D8C, self);
        break;

    case 4:
        switch (self->step_s) {
        case 0:
            self->ext.karasuman.timer = 96;
            self->step_s++;
             

        case 1:
            if (self->ext.karasuman.timer & 1) {
                self->animCurFrame = 61;
            } else {
                self->animCurFrame = 0;
            }

            if (!--self->ext.karasuman.timer) {
                DestroyEntity(self);
            }
            break;
        }
        break;
    }
}
