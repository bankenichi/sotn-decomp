/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNZ1:EntitySpikesDamage
   score  : 5
   receipt: nonmatchings/.adapt-scores/20260824-235118-62298-103387/EntitySpikesDamage/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rnz1/e_spikes.c
   asm    : asm/us/st/rnz1/nonmatchings/e_spikes/EntitySpikesDamage.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesDust);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesParts);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", SpikesBreak);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", SpikesApplyDamage);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikes);

#define SPIKES_ELEMENT ELEMENT_CUT | ELEMENT_UNK_10
extern EInit g_EInitInteractable;

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
