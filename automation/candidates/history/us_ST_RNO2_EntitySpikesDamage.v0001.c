/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:EntitySpikesDamage
   source : upstream/master:src/st/e_spikes.h
   target : src/st/rno2/e_spikes.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesDust);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesParts);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", SpikesBreak);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", SpikesApplyDamage);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikes);

void EntitySpikesDamage(Entity* self) {
    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->attackElement = SPIKES_ELEMENT;
        self->attack = 15;
        self->hitboxState = 1;
        self->hitboxWidth = 4;
        self->hitboxHeight = 4;
        self->poseTimer = 4;
#ifdef DAMAGE_ENT_ON_HIT
    } else {
        DestroyEntity(self);
#endif
    }
}

INCLUDE_RODATA("st/rno2/nonmatchings/e_spikes", D_us_801B1C4C);
