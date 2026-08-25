/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:func_us_801B9028_from_no1
   source : upstream/master:src/st/no1/unk_39028.c
   target : src/st/rno1/unk_29930.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

void func_us_801B9028_from_no1(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180A4C);
        self->animCurFrame = self->params + 1;
        self->zPriority = D_us_8018142C[self->params];
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = D_us_80181440[self->params];
        break;

    case 1:
        break;

    case 2:
#include "../pad2_anim_debug.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
/* End permuter-seed writer declarations. */
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_801A9A8C);

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_80198A18_from_rbo4);

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_801A9BEC);
