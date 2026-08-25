/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:BOSS/RBO7:EntityHarpyKick
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_harpy.h
   target : src/boss/rbo7/unk_138A0.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo7.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityBreakable);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801BAB18_from_bo0);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80192B38_from_rbo3);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801940B4);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801957C0);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitHarpyKick;

void EntityHarpyKick(Entity* self) {
    s32 animFrame;
    s8* hitboxPtr;
    Entity* harpy;

    if (!self->step) {
        InitializeEntity(g_EInitHarpyKick);
    }
    harpy = self - 1;
    self->facingLeft = harpy->facingLeft;
    self->posX.val = harpy->posX.val;
    self->posY.val = harpy->posY.val;
    animFrame = harpy->animCurFrame;
    if (animFrame > 13) {
        animFrame = 0;
    }
    hitboxPtr = hitboxes[0];
    hitboxPtr += hitboxOffsets[animFrame] * 4;
    self->hitboxOffX = *hitboxPtr++;
    self->hitboxOffY = *hitboxPtr++;
    self->hitboxWidth = *hitboxPtr++;
    self->hitboxHeight = *hitboxPtr++;
    if (harpy->entityId != E_HARPY) {
        DestroyEntity(self);
    }
}

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80195A8C);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80195D04);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityCtulhuDeath);
