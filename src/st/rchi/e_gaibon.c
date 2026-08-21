// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

// Defined in this overlay at src/st/rchi/e_init.c:96. EntityGaibonLeg needs
// it and the permuter cannot add a declaration, so its score-0 result sat in
// `deferred` reading as PERMUTER_EXHAUSTED until this line existed.
//
// Deliberately NOT taken from src/st/nz0/nz0.h:152, which is the only other
// place the name appears. EInit objects are overlay-local data; borrowing
// NZ0's would name a different object.
extern EInit g_EInitGaibon;
// EntitySmallGaibonProjectile's candidate failed to build on this name alone.
// Declared in the shared src/st/e_armor_lord.h:2.
extern EInit g_EInitInteractable;

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntityGaibon);

void EntityGaibonLeg(Entity *self)
{
  Entity *parent;
  if (self->step == 0)
  {
    InitializeEntity(&g_EInitGaibon);
    self->hitboxState = 0;
  }
  self->facingLeft = (self - 1)->facingLeft;
  parent = self - 1;
  self->palette = (self - 1)->palette;
  self->animCurFrame = 0;
  self->posX.i.hi = (self - 1)->posX.i.hi;
  self->posY.i.hi = parent->posY.i.hi;
  if (((u32) (parent->animCurFrame - 0x20)) < 3)
  {
    self->animCurFrame = 0x26;
  }
  else
    if (parent->animCurFrame == 0x23)
  {
    self->animCurFrame = 0x27;
  }
  else
    if (((u32) (parent->animCurFrame - 0x24)) < 2)
  {
    self->animCurFrame = 0x28;
  }
  if (parent->entityId != 0x19)
  {
    DestroyEntity(self);
  }
}

extern EInit D_us_80180624;

extern u8 D_us_80181748[];

void EntitySmallGaibonProjectile(Entity* self) {
    if (self->flags & FLAG_DEAD) {
        self->drawFlags = ENTITY_DEFAULT;
        self->step = 0;
        self->pfnUpdate = EntityExplosion;
        self->entityId = 2;
        self->params = 0;
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180624);
        self->animSet = ANIMSET_DRA(2);
        self->animCurFrame = 1;
        self->drawFlags = ENTITY_SCALEX | ENTITY_ROTATE;
        self->scaleX = 0xC0;
        self->velocityX = (rcos(self->rotate) * FIX(2.5)) >> 0xC;
        self->velocityY = (rsin(self->rotate) * FIX(2.5)) >> 0xC;
        self->rotate -= 0x400;
        self->palette = PAL_FLAG(PAL_UNK_1B6);
        // fallthrough

    case 1:
        MoveEntity();
        AnimateEntity(D_us_80181748, self);
        break;
    }
}

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntityLargeGaibonProjectile);
