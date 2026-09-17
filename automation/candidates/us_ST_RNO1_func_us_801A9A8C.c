/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO1:func_us_801A9A8C
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rno1/unk_29930.c
   target : src/st/rno1/unk_29930.c
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
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_801B9028_from_no1);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;

void func_us_801A9A8C(Entity* self) {
    Entity* child;
    s32 i;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        self->animCurFrame = 0;
        child = self + 1;
        i = 1;
        for (; i < 2; i++) {
            CreateEntityFromEntity(E_ID(UNK_2E), self, child);
            child->params = i + 0x100;
            child++;
            CreateEntityFromEntity(E_ID(UNK_2E), self, child);
            child->params = i;
            child++;
        }
    case 1:
    default:
        break;
    }
}


INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_80198A18_from_rbo4);

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_801A9BEC);
