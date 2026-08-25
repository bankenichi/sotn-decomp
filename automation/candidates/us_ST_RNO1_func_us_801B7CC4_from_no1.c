/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:func_us_801B7CC4_from_no1
   source : upstream/master:src/st/no1/unk_36490.c
   target : src/st/rno1/unk_26178.c
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
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakable);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakableDebris);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugShowWaitInfo);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugInputWait);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A68AC);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A700C);

void func_us_801B7CC4_from_no1(Entity* self) {
    if (self->step == 0) {
        g_api.PlaySfx(SET_RELEASE_RATE_HIGH_20_21);
        self->step++;
    }
    DestroyEntity(self);
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801B8F50_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BE880_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BEB54_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BEE00_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BF074_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A86A8);
