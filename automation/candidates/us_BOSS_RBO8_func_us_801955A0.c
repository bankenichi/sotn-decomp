/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO8:func_us_801955A0
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo8/func_us_801955a0.h
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

void func_us_801955A0(Entity* self, Collider* collider) {
    s16 result;
    u16 hitFloor = false;

    result = g_Tilemap.scrollY.i.hi + self->posY.i.hi + collider->unk18;
    if (result >= 0x1C0) {
        result = 0x1C0 - result;
        hitFloor = true;
    } else {
        result = 0;
        hitFloor = false;
    }

    collider->unk18 = result;
    self->ext.et_8019921C.hitFloor = hitFloor;
}


INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_us_801955F8);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void func_801CE1E8(s32 step) {
    s32 i;

    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;

    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}



void func_801CE228() {
    s32 i;









    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}



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
