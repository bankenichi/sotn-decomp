/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO7:EntityCtulhuDeath
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo7/unk_138A0.c
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
u8 AnimateEntity(u8 frames[], Entity* entity);
void DestroyEntity(Entity*);
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
extern s32 D_us_8018076C[]; /* retained BOSS/RBO7 data asm/us/boss/rbo7/data/568.data.s, size 0x1c */

void EntityCtulhuDeath(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->animSet = 14;
        self->unk5A = 121;
        self->drawFlags = ENTITY_OPACITY;
        if (self->params) {
            self->palette = 0x2EE;
            self->opacity = 8;
            self->blendMode = BLEND_TRANSP | BLEND_SUB;
            self->flags &= ~FLAG_POS_CAMERA_LOCKED;
        } else {
            self->palette = 0x2E4;
            self->zPriority += 2;
            self->opacity = 0x14;
            self->blendMode = BLEND_TRANSP | BLEND_ADD;
        }
        /* fall through */
    case 1:
        self->posY.val -= FIX(1);
        if (!AnimateEntity(D_us_8018076C, self)) {
            DestroyEntity(self);
        }
        break;
    }
}
