/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCHI:EntityLargeGaibonProjectile
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_gaibon_large_projectile.h
   target : src/st/rchi/e_gaibon.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
int rcos(int a);
int rsin(int a);
void MoveEntity();
u8 AnimateEntity(u8 frames[], Entity* entity);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* End permuter-seed writer declarations. */

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

extern EInit g_EInitGaibonProjectile;

extern u8 g_AnimSmallGaibonProjectile[];

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
        InitializeEntity(g_EInitGaibonProjectile);
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
        AnimateEntity(g_AnimSmallGaibonProjectile, self);
        break;
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern u32 g_Timer;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityLargeGaibonProjectile(Entity* self) {
    Entity* newEntity;

    if (self->flags & FLAG_DEAD) {
        self->drawFlags = ENTITY_DEFAULT;
        self->step = 0;
        self->pfnUpdate = EntityExplosion;
        self->entityId = 2;
        self->params = 1;
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitGaibonLargeProjectile);
        if (!self->params) {
            self->animSet = ANIMSET_DRA(2);
            self->drawFlags = ENTITY_ROTATE;
            self->velocityX = (rcos(self->rotate) * FIX(3.5)) >> 0xC;
            self->velocityY = (rsin(self->rotate) * FIX(3.5)) >> 0xC;
            self->rotate -= ROT(90);
            self->palette = PAL_FLAG(PAL_UNK_1B6);
        } else {
            self->animSet = ANIMSET_DRA(14);
            self->unk5A = 0x79;
            self->drawFlags = ENTITY_SCALEX | ENTITY_ROTATE | ENTITY_OPACITY;
            self->scaleX = 0x100;
            self->opacity = 0x80;
            self->palette = PAL_FLAG(PAL_UNK_1F3);
            self->blendMode = BLEND_TRANSP | BLEND_ADD;
            self->step = 2;
            self->hitboxState = 0;
            self->flags |= FLAG_UNK_2000;
        }
        break;

    case 1:
        MoveEntity();
        AnimateEntity(anim_large_fireball1, self);
        if (!(g_Timer & 3)) {
            newEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(
                    E_ID(GAIBON_BIG_FIREBALL), self, newEntity);
                newEntity->params = 1;
                newEntity->rotate = self->rotate;
                newEntity->zPriority = self->zPriority + 1;
            }
        }
        break;

    case 2:
        self->opacity -= 2;
        self->scaleX -= 4;
        if (AnimateEntity(anim_large_fireball2, self) == 0) {
            DestroyEntity(self);
        }
        break;
    }
}
