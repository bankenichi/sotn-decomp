// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

INCLUDE_ASM("st/rnz1/nonmatchings/e_valhalla_knight", EntityValhallaKnight);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit D_us_80180C24;
extern EInit D_us_80180C30;
extern s8 D_us_80182018[36];
extern u8 D_us_8018203C[20];
extern s8 D_us_80182050[20];
extern u8 D_us_80182064[20];

void func_us_801C8954_from_are(Entity* self) {
    Entity* tempEntity;
    s32 curFrame;
    s8* hitboxPtr;

    if (!self->step) {
        if (self->params) {
            InitializeEntity(D_us_80180C30);
        } else {
            InitializeEntity(D_us_80180C24);
            self->parent = self - 1;
            self->nextPart = self - 1;
        }
    }
    tempEntity = self - self->params - 1;
    if (tempEntity->entityId != E_VALHALLA_KNIGHT) {
        DestroyEntity(self);
        return;
    }
    curFrame = tempEntity->animCurFrame;
    self->facingLeft = tempEntity->facingLeft;
    self->posX.val = tempEntity->posX.val;
    self->posY.val = tempEntity->posY.val;
    if (self->params) {
        hitboxPtr = D_us_80182050;
        hitboxPtr += D_us_80182064[curFrame] * 4;
    } else {
        hitboxPtr = D_us_80182018;
        hitboxPtr += D_us_8018203C[curFrame] * 4;
    }
    self->hitboxOffX = *hitboxPtr++;
    self->hitboxOffY = *hitboxPtr++;
    self->hitboxWidth = *hitboxPtr++;
    self->hitboxHeight = *hitboxPtr++;
}



INCLUDE_ASM("st/rnz1/nonmatchings/e_valhalla_knight", func_us_801C8AAC_from_are);
