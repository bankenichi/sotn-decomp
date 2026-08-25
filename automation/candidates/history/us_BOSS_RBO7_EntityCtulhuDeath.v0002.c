/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO7:EntityCtulhuDeath
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_ctulhu.h
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
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityBreakable);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801BAB18_from_bo0);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80192B38_from_rbo3);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801940B4);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801957C0);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityHarpyKick);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80195A8C);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80195D04);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;

void EntityCtulhuDeath(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->animSet = 14;
        self->unk5A = 121;
        self->palette = PAL_FLAG(PAL_CTULHU_DEATH);
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = 16;
        if (self->params) {
            self->opacity = 16;
            self->blendMode = BLEND_TRANSP | BLEND_SUB;
            self->flags &= ~FLAG_POS_CAMERA_LOCKED;
        } else {
            self->zPriority += 2;
            self->blendMode = BLEND_TRANSP | BLEND_ADD;
        }
         
    case 1:
        self->posY.val -= FIX(1);
        if (!AnimateEntity(anim_death, self)) {
            DestroyEntity(self);
        }
        break;
    }
}
