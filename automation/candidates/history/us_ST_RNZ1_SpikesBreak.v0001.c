/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:SpikesBreak
   source : upstream/master:src/st/e_spikes.h
   target : src/st/rnz1/e_spikes.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesDust);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesParts);

void SpikesBreak(u32 tileIdx) {
    Entity* entity;
    s16 tilePosX, tilePosY;
    s32 count;
#ifdef HAS_ORIENTATIONS
    s32 tileIdxOffset;
    u32 tileType;
    u8 collisionType;
    u8 params;
#endif

    tilePosX = ((tileIdx % SPIKES_TILE_WIDTH) * 16) + 8;
    tilePosY = ((tileIdx / SPIKES_TILE_WIDTH) * 16) + 8;
#ifdef HAS_ORIENTATIONS
    params = 0;
    tileIdx -= SPIKES_TILE_WIDTH + 1;
    for (count = 0; count < 3; tileIdx += SPIKES_TILE_WIDTH, count++) {
        for (tileIdxOffset = 0; tileIdxOffset < 3; tileIdxOffset++) {
            tileType = (&g_Tilemap.fg[tileIdx])[tileIdxOffset];
            collisionType = g_Tilemap.tileDef->collision[tileType];
            if (collisionType == 3) {
                params |= parts_params[count][tileIdxOffset];
            }
        }
    }
#endif
    tilePosX -= g_Tilemap.scrollX.i.hi;
    tilePosY -= g_Tilemap.scrollY.i.hi;
    for (count = START_COUNT; count < 3; count++) {
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromCurrentEntity(E_ID(SPIKES_PARTS), entity);
            entity->posX.i.hi = tilePosX;
            entity->posY.i.hi = tilePosY;
#ifdef HAS_ORIENTATIONS
            entity->params = params + (count << 8);
#else
            entity->params = count;
#endif
        }
    }
    entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
    if (entity != NULL) {
        CreateEntityFromCurrentEntity(E_INTENSE_EXPLOSION, entity);
        entity->posX.i.hi = tilePosX;
        entity->posY.i.hi = tilePosY;
         
        entity->params = 16;
    }
    entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
    if (entity != NULL) {
        CreateEntityFromCurrentEntity(E_ID(SPIKES_DUST), entity);
        entity->posX.i.hi = tilePosX;
        entity->posY.i.hi = tilePosY;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", SpikesApplyDamage);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikes);

INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesDamage);
