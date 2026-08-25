/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RCEN:func_us_8019D260
   score  : 10
   receipt: nonmatchings/.adapt-scores/20260824-235225-62298-253681/func_us_8019D260/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rcen/unk_1D260.c
   asm    : asm/us/st/rcen/nonmatchings/unk_1D260/func_us_8019D260.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rcen.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
s32 Random();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* End permuter-seed writer declarations. */

// This function does not appear to have a corresponding func on PSP - likely
// unused and stripped
#define E_EXPLOSION_FLAME 34

void func_us_8019D260(void) {
    s16 temp_s3;
    s32 i;
    s8 temp_s4;
    Entity* entity;

    temp_s4 = Random() & 3;
    temp_s3 = ((Random() & 0xF) << 8) - 0x800;
    for (i = 0; i < 6; i++) {
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(
                E_ID(EXPLOSION_FLAME), g_CurrentEntity, entity);
            entity->ext.et_801A518C.unk89 = 6 - i;
            entity->ext.et_801A518C.unk88 = temp_s4;
            entity->params = 2;
            entity->ext.et_801A518C.unk84 = temp_s3;
            entity->zPriority = g_CurrentEntity->zPriority + 1;
        }
    }
}

INCLUDE_ASM("st/rcen/nonmatchings/unk_1D260", func_us_8019D330);
