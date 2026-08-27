// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define PAL_SPIKES_DUST 353
extern EInit g_EInitParticle;
extern AnimateEntityFrame D_us_80181090[7];

void EntitySpikesDust(Entity* self) {
    s16 angle;

    if (!self->step) {
        InitializeEntity(g_EInitParticle);
        self->zPriority = 160;
        self->animSet = 8;
        self->animCurFrame = 1;
        self->palette = PAL_FLAG(PAL_SPIKES_DUST);
        angle = GetAngleBetweenEntitiesShifted(self, &PLAYER);
        SetEntityVelocityFromAngle(angle, 40);
        return;
    }
    MoveEntity();
    if (!AnimateEntity(D_us_80181090, self)) {
        DestroyEntity(self);
    }
}


INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesParts);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", SpikesBreak);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", SpikesApplyDamage);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikes);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesDamage);
