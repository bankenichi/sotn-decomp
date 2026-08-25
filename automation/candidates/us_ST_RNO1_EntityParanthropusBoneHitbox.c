/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:EntityParanthropusBoneHitbox
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitParanthropusBoneHitbox;

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

    self->hitboxOffX = bone_hitbox_offsets[paranthropusAnimCurFrame].x;
    self->hitboxOffY = bone_hitbox_offsets[paranthropusAnimCurFrame].y;
    self->hitboxWidth =
        bone_hitbox_dimensions[paranthropusAnimCurFrame].width / 2;
    self->hitboxHeight =
        bone_hitbox_dimensions[paranthropusAnimCurFrame].height / 2;
    self->facingLeft = paranthropus->facingLeft;
    self->hitboxState = paranthropus->hitboxState;
    self->posX.i.hi = paranthropus->posX.i.hi;
    self->posY.i.hi = paranthropus->posY.i.hi;

    if (paranthropus->entityId != E_PARANTHROPUS) {
        DestroyEntity(self);
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusSkull);
