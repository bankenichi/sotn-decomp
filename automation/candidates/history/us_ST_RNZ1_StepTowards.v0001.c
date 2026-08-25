/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:StepTowards
   source : upstream/master:src/st/step_towards.h
   target : src/st/rnz1/e_cloaked_knight.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int abs(int x);
/* End permuter-seed writer declarations. */

bool StepTowards(s16* val, s32 target, s32 step) {
#else
bool StepTowards(s16* val, s32 target, s32 step) {
#endif
    if (abs(*val - target) < step) {
        *val = target;
        return true;
    }

    if (*val > target) {
        *val -= step;
    }

    if (*val < target) {
        *val += step;
    }

    return false;
}


INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnight);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightCloak);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightAura);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightSword);
