// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void ParanthropusSetStep(u16 step) {
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;
    g_CurrentEntity->ext.paranthropus.unk7C = 0;
    g_CurrentEntity->ext.paranthropus.unk7E = false;
    g_CurrentEntity->step = step;
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropus);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitParanthropusThrownBone;
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
void MoveEntity(void);

void EntityParanthropusThrownBone(Entity* self) {
    if (self->flags & FLAG_DEAD) {
        DestroyEntity(self);
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParanthropusThrownBone);
        self->drawFlags |= ENTITY_ROTATE;
        if (self->facingLeft) {
            self->velocityX = FIX(2.0);
        } else {
            self->velocityX = FIX(-2.0);
        }
        self->velocityY = FIX(-6.0);
        break;
    case 1:
        MoveEntity();
        self->rotate -= ROT(22.5);
        self->velocityY += FIX(0.25);
        break;
    }
}



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitParanthropusBoneHitbox;
extern Point16 D_us_80181A70[33];
extern Size16 D_us_80181AF4[33];

void EntityParanthropusBoneHitbox(Entity* self) {
    Entity* paranthropus;
    u8 paranthropusAnimCurFrame;

    if (!self->step) {
        InitializeEntity(g_EInitParanthropusBoneHitbox);
    }

    paranthropus = self - 1;

    paranthropusAnimCurFrame = paranthropus->animCurFrame;
    if (paranthropusAnimCurFrame > 0x1D) {
        paranthropusAnimCurFrame = 0;
    }

    self->hitboxOffX = D_us_80181A70[paranthropusAnimCurFrame].x;
    self->hitboxOffY = D_us_80181A70[paranthropusAnimCurFrame].y;
    self->hitboxWidth =
        D_us_80181AF4[paranthropusAnimCurFrame].width / 2;
    self->hitboxHeight =
        D_us_80181AF4[paranthropusAnimCurFrame].height / 2;
    self->facingLeft = paranthropus->facingLeft;
    self->hitboxState = paranthropus->hitboxState;
    self->posX.i.hi = paranthropus->posX.i.hi;
    self->posY.i.hi = paranthropus->posY.i.hi;

    if (paranthropus->entityId != E_PARANTHROPUS) {
        DestroyEntity(self);
    }
}



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define DEATH 7
extern EInit g_EInitInteractable;
extern Point16 D_us_80181B78[34];

void EntityParanthropusSkull(Entity* self) {
    u8 i;
    Entity* entity;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->attack = 0;
        self->attackElement = ELEMENT_NONE;
    }


    entity = self - 2;
    i = entity->animCurFrame;
    if (i >= 0x21) {
        i = 0;
    }

    if (entity->facingLeft) {
        self->posX.i.hi = (self - 2)->posX.i.hi - D_us_80181B78[i].x;
    } else {
        self->posX.i.hi = (self - 2)->posX.i.hi + D_us_80181B78[i].x;
    }
    self->posY.i.hi = (self - 2)->posY.i.hi + D_us_80181B78[i].y;


#ifdef VERSION_US
    i = 0;
#endif
    if (entity->step < DEATH) {
        i = GetPlayerCollisionWith(self, 8, 10, 4);
    }

    entity = &PLAYER;
    if (i) {
        entity->posY.val += FIX(2.0);
    }

    if ((self - 2)->entityId != E_PARANTHROPUS) {
        DestroyEntity(self);
    }
}


