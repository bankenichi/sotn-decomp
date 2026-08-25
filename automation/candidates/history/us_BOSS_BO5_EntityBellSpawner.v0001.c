/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO5:EntityBellSpawner
   source : upstream/master:src/st/dai/e_bell.c
   target : src/boss/bo5/e_bell_spawner.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;

void EntityBellSpawner(Entity* self) {
    Entity* bell;
    s32 count;
    s16* ptr = *bell_spawner_params;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        for (bell = self + 1, count = 0; count < 2; count++, bell++) {
            CreateEntityFromCurrentEntity(E_ID(BELL), bell);
            bell->posX.i.hi = *ptr++ - g_Tilemap.scrollX.i.hi;
            bell->posY.i.hi = *ptr++ - g_Tilemap.scrollY.i.hi;
            bell->params = *ptr++;
        }
    }
}
