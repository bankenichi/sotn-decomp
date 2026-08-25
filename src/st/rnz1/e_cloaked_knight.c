// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

#define STEP_TOWARDS_EXTERNAL
#include "../step_towards.h"
#undef STEP_TOWARDS_EXTERNAL



INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnight);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern AnimateEntityFrame D_us_80181F24[5];
extern EInit g_EInitCloakedknight;

void EntityCloakedKnightCloak(Entity* self) {
    Entity* prev;
    s32 velocityX;
    s32 velocityY;
    s16 temp_s0_3;
    s32 distance;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCloakedknight);
        self->hitboxState = 0;
        self->flags |= FLAG_UNK_00200000 | FLAG_UNK_2000;
        self->drawFlags = ENTITY_ROTATE;


    case 1:
        AnimateEntity(D_us_80181F24, self);
        prev = self - 1;
        self->posX.i.hi = prev->posX.i.hi;
        self->posY.i.hi = prev->posY.i.hi;
        velocityX = prev->velocityX;
        velocityY = prev->velocityY;
        temp_s0_3 = ratan2(velocityX, -velocityY);
        temp_s0_3 = temp_s0_3 - self->rotate;
        velocityX = FIX_TO_I(velocityX);
        velocityY = FIX_TO_I(velocityY);
        distance = SquareRoot0(SQ(velocityX) + SQ(velocityY));
        temp_s0_3 = (temp_s0_3 * distance) >> 4;
        self->rotate += temp_s0_3;
        StepTowards(&self->rotate, 0, 0x20);
        if (prev->entityId != E_CLOAKED_KNIGHT) {
            DestroyEntity(self);
        }
        break;
    }
}



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitCloakedKnightAura;

void EntityCloakedKnightAura(Entity* self) {
    Entity* parent;

    if (!self->step) {
        InitializeEntity(g_EInitCloakedKnightAura);
        self->hitboxState = 0;
        self->flags |= FLAG_UNK_00200000 | FLAG_UNK_2000;
        self->animCurFrame = 1;
        self->palette += 1;
        self->drawFlags |= ENTITY_OPACITY | ENTITY_SCALEY | ENTITY_SCALEX;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        self->scaleX = self->scaleY = 0x100;
        self->opacity = 0x80;
    }

    parent = self->ext.cloakedKnightAura.parent;
    self->posX.val = parent->posX.val;
    self->posY.val = parent->posY.val;
    self->scaleX = self->scaleY += 6;
    if (parent->ext.cloakedKnight.unk86) {
        self->scaleX = self->scaleY += 6;
    }
    self->opacity -= 4;
    if (self->opacity < 32
#ifndef VERSION_PSP
        || parent->entityId != E_CLOAKED_KNIGHT
#endif
    ) {
        DestroyEntity(self);
    }
}



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit D_us_80180BE8;

void EntityCloakedKnightSword(Entity* self) {
    Entity* entity;
    s32 scale;
    s16 rotate;
    s32 offsetX;
    s32 offsetY;
    Pos* pos;
    s32 scale1;

    if (!self->params) {
        entity = self - 2;
        if ((entity->flags & FLAG_DEAD) != 0 ||
            entity->entityId != E_CLOAKED_KNIGHT) {
            if (self->step != 4) {
                self->hitboxState = 0;
                SetStep(4);
            }
        }
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180BE8);
        self->animCurFrame = 7;
        self->drawFlags = ENTITY_ROTATE;
        if (!self->params) {
            entity = self + 1;
            CreateEntityFromCurrentEntity(E_CLOAKED_KNIGHT_SWORD, entity);
            entity->params = 1;
        } else {
            self->flags |= FLAG_UNK_2000;
            self->animCurFrame = 0;
            self->step = 8;
        }
        break;

    case 1:
        if (entity->step > 2) {
            self->step++;
        }
        entity = self - 2;
        if (entity->entityId != E_CLOAKED_KNIGHT) {
            DestroyEntity(self);
        }
        break;

    case 2:
        MoveEntity();
        pos = &self->ext.cloakedKnightSword.targetPos;
        offsetX = pos->x.i.hi - self->posX.i.hi;
        offsetY = pos->y.i.hi - self->posY.i.hi;
        scale1 = SQ(offsetX) + SQ(offsetY);
        scale1 = SquareRoot0(scale1);
        scale = scale1;
        if (scale > 0x38) {
            scale = 0x38;
        }
        if (scale < 4) {
            SetStep(3);
        }
        rotate = ratan2(offsetY, offsetX);
        self->velocityX = scale * rcos(rotate);
        self->velocityY = scale * rsin(rotate);
        break;

    case 3:
        pos = &self->ext.cloakedKnightSword.targetPos;
        self->posX.i.hi = pos->x.i.hi;
        self->posY.i.hi = pos->y.i.hi;
        break;

    case 4:
        self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA |
                       FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA;
        MoveEntity();
        self->velocityY += FIX(0.125);
        self->rotate += ROT(11.25);
        break;

    case 8:
        entity = self - 1;
        self->hitboxState = entity->hitboxState;
        self->posX.i.hi = entity->posX.i.hi;
        self->posY.i.hi = entity->posY.i.hi;
        rotate = entity->rotate + ROT(90.0);
        self->hitboxOffX = (rcos(rotate) * 3 * 8) >> 12;
        self->hitboxOffY = (rsin(rotate) * 3 * 8) >> 12;
        if (entity->entityId != E_CLOAKED_KNIGHT_SWORD) {
            DestroyEntity(self);
        }
        break;
    }
}


