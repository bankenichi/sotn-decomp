/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityMedusaHeadYellow
   source : upstream/master:src/st/e_medusa_head.h
   target : src/st/rnz1/e_medusa_head.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void EntityMedusaHeadBlue(Entity* self);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadSpawner);

void EntityMedusaHeadYellow(Entity* self) {
    self->params = 1;
    EntityMedusaHeadBlue(self);
}

INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadBlue);
