// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

INCLUDE_ASM("st/rno4/nonmatchings/e_killer_fish", EntityKillerFish);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define BLEND_ADD 32
#define BLEND_TRANSP 16
#define ENTITY_OPACITY 8
extern u8 D_us_8018176C[28];
extern EInit g_EInitParticle;
extern struct Entity;
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);

void EntityKillerFishDeathPuff(Entity* self) {
    if (!self->step) {
        InitializeEntity(g_EInitParticle);
        self->pose = 0;
        self->poseTimer = 0;
        self->animSet = 0xE;
        self->unk5A = 0x79;
        self->palette = 0x2E8;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = 0x60;
        if (self->params & 0xFF00) {
            self->zPriority = (self->params & 0xFF00) >> 8;
        }
        self->velocityY += -0x8000 - 0x8000;
        return;
    }

    self->posY.val += self->velocityY;
    if (!AnimateEntity(D_us_8018176C, self)) {
        DestroyEntity(self);
    }
}


