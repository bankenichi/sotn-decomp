/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RCHI:EntityLargeGaibonProjectile
   score  : 10
   receipt: nonmatchings/.adapt-scores/20260818-195012-74049-818394/EntityLargeGaibonProjectile/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rchi/e_gaibon.c
   asm    : asm/us/st/rchi/nonmatchings/e_gaibon/EntityLargeGaibonProjectile.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
int rcos(int a);
int rsin(int a);
void MoveEntity();
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();

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
  unsigned long parentAnimFrame;
  if (self->step == 0)
  {
    InitializeEntity(&g_EInitGaibon);
    self->hitboxState = 0;
  }
  self->facingLeft = (self - 1)->facingLeft;
  parent = self - 1;
  self->palette = (self - 1)->palette;
  ;
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

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntitySmallGaibonProjectile);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180630;
extern u32 g_Timer;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

#define BLEND_ADD 32
#define BLEND_TRANSP 16
#define ENTITY_DEFAULT 0
#define ENTITY_OPACITY 8
#define ENTITY_ROTATE 4
#define ENTITY_SCALEX 1
#define E_GAIBON_BIG_FIREBALL 84
#define FLAG_DEAD 256
#define FLAG_UNK_2000 8192
#define PAL_UNK_1B6 438
#define PAL_UNK_1F3 499
extern u8 D_us_80181754[14];
extern u8 D_us_80181764[28];
extern EInit D_us_80180630;
extern struct Entity;
Entity* AllocEntity(Entity* start, Entity* end);

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
        InitializeEntity(D_us_80180630);
        if (!self->params) {
            self->animSet = ANIMSET_DRA(2);
            self->drawFlags = ENTITY_ROTATE;
            self->velocityX = (rcos(self->rotate) * FIX(3.5)) >> 0xC;
            self->velocityY = (rsin(self->rotate) * FIX(3.5)) >> 0xC;
            self->rotate -= 0x400;
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
        AnimateEntity(D_us_80181754, self);
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
        if (AnimateEntity(D_us_80181764, self) == 0) {
            DestroyEntity(self);
        }
        break;
    }
}
