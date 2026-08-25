/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO2:EntityBossTorch
   source : upstream/master:src/boss/rbo0/e_boss_torch.c
   target : src/boss/bo2/unk_224DC.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo2.h"

extern u8* g_eBreakableAnimations[];
extern u8 g_eBreakableHitboxes[];
extern u8 g_eBreakableExplosionTypes[];
extern u16 g_eBreakableanimSets[];
extern u8 blend_modes[];

#include "../../st/e_breakable.h"

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", func_us_801A2610);

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", func_us_801A269C);

#include "e_minotaur.h"

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", func_us_801A3E04);

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", func_us_801A460C);

// Shared body vendored with the overlay so this source remains self-contained.
#include "e_unk_29.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;

void EntityBossTorch(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
#ifdef INVERTED_STAGE
        self->zPriority = 0x6A;
#endif
        self->drawFlags = ENTITY_SCALEY | ENTITY_SCALEX;
        self->scaleX = self->scaleY = scale[self->params];
         
    case 1:
#ifdef VERSION_PSP
        AnimateEntity(frames, self);
#else
        AnimateEntity(PrizeDrops, self);
#endif
        if (g_Timer & 4) {
            self->palette = (self->params * 2) + PAL_FLAG(PAL_TORCH_A);
        } else {
            self->palette = (self->params * 2) + PAL_FLAG(PAL_TORCH_B);
        }
        break;
    case 0xFF:
#include "../../st/pad2_anim_debug.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
/* End permuter-seed writer declarations. */
    }
}

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", EntityBossDoors);
