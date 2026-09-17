/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO2:SpikesBreak
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_spikes.h
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
u8 GetAngleBetweenEntitiesShifted(Entity* a, Entity* b);
void SetEntityVelocityFromAngle(u8 arg0, s16 arg1);
void MoveEntity();
u8 AnimateEntity(u8 frames[], Entity* entity);
void DestroyEntity(Entity*);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* End permuter-seed writer declarations. */

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define PAL_SPIKES_DUST 353
extern EInit g_EInitParticle;
extern AnimateEntityFrame anim_dust[7];

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
    if (!AnimateEntity(anim_dust, self)) {
        DestroyEntity(self);
    }
}


INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesParts);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

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
        // params & 0xF0 to EntityIntenseExplosion uses the dust cloud palette
        entity->params = 16;
    }
    entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
    if (entity != NULL) {
        CreateEntityFromCurrentEntity(E_ID(SPIKES_DUST), entity);
        entity->posX.i.hi = tilePosX;
        entity->posY.i.hi = tilePosY;
    }
}


INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", SpikesApplyDamage);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikes);

INCLUDE_ASM("st/rno2/nonmatchings/e_spikes", EntitySpikesDamage);

INCLUDE_RODATA("st/rno2/nonmatchings/e_spikes", D_us_801B1C4C);
