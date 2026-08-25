/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:EntityParanthropusSkull
   source : upstream/master:src/st/e_paranthropus.h
   target : src/st/rno1/unk_34074.c
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
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

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

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusThrownBone);

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusBoneHitbox);

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
        self->posX.i.hi = (self - 2)->posX.i.hi - skull_positions[i].x;
    } else {
        self->posX.i.hi = (self - 2)->posX.i.hi + skull_positions[i].x;
    }
    self->posY.i.hi = (self - 2)->posY.i.hi + skull_positions[i].y;

     
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
