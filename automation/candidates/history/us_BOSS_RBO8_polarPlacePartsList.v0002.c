/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO8:polarPlacePartsList
   source : upstream/master:src/st/giantbro_helpers_2.h
   target : src/boss/rbo8/unk_1546C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo8.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void polarPlacePart(Entity* self);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", EntityBreakable);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_us_801955A0);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_us_801955F8);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_801CE1E8);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_801CE228);

void polarPlacePartsList(s16* offsets) {
    Entity* entity;

    while (*offsets) {
        entity = g_CurrentEntity + *offsets;
        if (!entity->ext.GH_Props.unkA8) {
            polarPlacePart(entity);
        }
        offsets++;
    }
}
