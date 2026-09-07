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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;
extern Entity* g_CurrentEntity;

void SpikesApplyDamage(u32 tileIdx) {
    Entity* spikesDamage;
    s16 tilePosX, tilePosY;
    tilePosX = ((tileIdx % 16) * 16) + 8;
    tilePosY = ((tileIdx / 16) * 16) + 8;
    tilePosX -= g_Tilemap.scrollX.i.hi;
    tilePosY -= g_Tilemap.scrollY.i.hi;
    spikesDamage = &g_CurrentEntity[1];
    spikesDamage->posX.i.hi = tilePosX;
    spikesDamage->posY.i.hi = tilePosY;
}


INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikes);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesDamage);
