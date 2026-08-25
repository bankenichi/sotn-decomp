/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RLIB:EntityHarpyKick
   source : upstream/master:src/st/e_harpy.h
   target : src/st/rlib/unk_2DBE8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rlib.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801ADBE8);

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

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AE414);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AE4B4);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AE534);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AED4C);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AEFE0);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801D8D44_from_no4);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AF11C);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AF3C8);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AF448);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AF9E8);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AFC88);
