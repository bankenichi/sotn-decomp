/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:EntityParanthropusThrownBone
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
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
void MoveEntity();
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitParanthropusThrownBone;

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

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusBoneHitbox);

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusSkull);
