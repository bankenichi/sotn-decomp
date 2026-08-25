/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:ST/RNO2:SpikesApplyDamage
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_spikes.h
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
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesDust);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesParts);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", SpikesBreak);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;
extern Entity* g_CurrentEntity;

void SpikesApplyDamage(u32 tileIdx) {
    Entity* spikesDamage;
    s16 tilePosX, tilePosY;

    tilePosX = ((tileIdx % SPIKES_TILE_WIDTH) * 16) + 8;
    tilePosY = ((tileIdx / SPIKES_TILE_WIDTH) * 16) + 8;
    tilePosX -= g_Tilemap.scrollX.i.hi;
    tilePosY -= g_Tilemap.scrollY.i.hi;

#ifdef HAS_ORIENTATIONS
    spikesDamage = &g_CurrentEntity[1];
#ifdef DAMAGE_ENT_ON_HIT
    spikesDamage->posX.i.hi = tilePosX;
    spikesDamage->posY.i.hi = tilePosY;
#endif
#endif

#ifdef DAMAGE_ENT_ON_HIT
     
    spikesDamage = AllocEntity(&DAMAGE_ENT_START, &DAMAGE_ENT_END);
    if (spikesDamage != NULL) {
        CreateEntityFromCurrentEntity(E_ID(SPIKES_DAMAGE), spikesDamage);
        spikesDamage->posX.i.hi = tilePosX;
        spikesDamage->posY.i.hi = tilePosY;
    }
#else
     
    spikesDamage->posX.i.hi = tilePosX;
    spikesDamage->posY.i.hi = tilePosY;
#endif
}

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikes);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesDamage);

INCLUDE_RODATA("st/rno2/nonmatchings/e_spikes", D_us_801B1C4C);
