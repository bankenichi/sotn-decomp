// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitStoneSkull;
extern u16 g_pads_1_pressed;
extern Tilemap g_Tilemap;

extern EInit g_EInitStoneSkull;
extern u16 g_pads_1_pressed;
extern u8 D_us_80181E8C[];

void func_us_801C7F24(Entity* self) {
    s32 posY;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitStoneSkull);
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = 0xD0;
        self->ext.stoneSkull.startingPosY =
            g_Tilemap.scrollY.i.hi + self->posY.i.hi;
        self->velocityY = FIX(1.0);
         
    case 1:
        AnimateEntity(D_us_80181E8C, self);
        MoveEntity();
        posY = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
        posY = self->ext.stoneSkull.startingPosY - posY;
        if (self->velocityY > 0) {
            posY += self->params;
        } else {
            posY -= self->params;
        }

        if (posY < 0) {
            self->velocityY -= FIX(0.125);
            if (self->velocityY < FIX(-1.0)) {
                self->velocityY = FIX(-1.0);
            }
        } else {
            self->velocityY += FIX(0.125);
            if (self->velocityY > FIX(1.0)) {
                self->velocityY = FIX(1.0);
            }
        }
        break;

    case 0xFF:
        FntPrint("charal %x\n", self->animCurFrame);
        if (g_pads_1_pressed & 0x80) {
            if (self->params) {
                break;
            }
            self->animCurFrame++;
            self->params |= 1;
        } else {
            self->params = 0;
        }
        if (g_pads_1_pressed & 0x20) {
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
