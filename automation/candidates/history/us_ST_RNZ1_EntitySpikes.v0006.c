/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNZ1:EntitySpikes
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_spikes.h
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
void InitializeEntity(u16 arg0[]);
u8 GetAngleBetweenEntitiesShifted(Entity* a, Entity* b);
void SetEntityVelocityFromAngle(u8 arg0, s16 arg1);
void MoveEntity();
u8 AnimateEntity(u8 frames[], Entity* entity);
void DestroyEntity(Entity*);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SpikesBreak();
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


/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitSpawner;
extern GAME_IMPORT GpuBuffer g_GpuBuffers[2];
extern GameApi g_api;

void EntitySpikes(Entity* self) {
#ifdef HAS_ORIENTATIONS
    Entity* entity;
#else
    u32 newTileType;
#endif
    Entity* playerPtr;
    u32 tileIdx;
    u32 tileType;
    u8 collisionType;
    s32 count;
    s16 posX, posY;
    s16 scrollX, scrollY;

    playerPtr = &PLAYER;
    switch (self->step) {
    case SPIKES_INIT:
        InitializeEntity(g_EInitSpawner);
#ifdef DAMAGE_ENT_ON_SPAWN
        entity = self + 1;
        CreateEntityFromCurrentEntity(E_ID(SPIKES_DAMAGE), entity);
#endif
#ifdef HAS_ORIENTATIONS
        break;
    case SPIKES_INTERACT:
        entity = self + 1;
        entity->posX.i.hi = -16;
        entity->posY.i.hi = -16;
#else
        g_GpuBuffers[0].draw.r0 = 0x10;
        g_GpuBuffers[0].draw.g0 = 0x10;
        g_GpuBuffers[0].draw.b0 = 0x10;
        g_GpuBuffers[1].draw.r0 = 0x10;
        g_GpuBuffers[1].draw.g0 = 0x10;
        g_GpuBuffers[1].draw.b0 = 0x10;
    /* fallthrough */
    case SPIKES_INTERACT:
#endif
        posX = playerPtr->posX.i.hi;
        posY = playerPtr->posY.i.hi;
        scrollX = posX + g_Tilemap.scrollX.i.hi;
        scrollY = posY + g_Tilemap.scrollY.i.hi;
        tileIdx = (scrollX >> 4) + (scrollY >> 4) * g_Tilemap.hSize * 16;
        tileIdx -= SPIKES_TILE_WIDTH;
        for (count = 0; count < 3; tileIdx += SPIKES_TILE_WIDTH, count++) {
            tileType = g_Tilemap.fg[tileIdx];
            collisionType = g_Tilemap.tileDef->collision[tileType];
            if (collisionType > 243 && collisionType < 248) {
                if (g_api.CheckEquipmentItemCount(
                        ITEM_SPIKE_BREAKER, EQUIP_ARMOR)) {
#if defined(STAGE_IS_NZ1) || defined(STAGE_IS_RNZ1)
                    g_Tilemap.fg[tileIdx] = 0x58B;
#elif defined(HAS_ORIENTATIONS)
                    g_Tilemap.fg[tileIdx] = 0;
#else
                    switch (tileType) {
                    case 0x6AE:
                        newTileType = 0x6B1;
                        break;

                    case 0x6AF:
                        newTileType = 0x6B2;
                        break;

                    case 0x6B0:
                        newTileType = 0x6B3;
                        break;
                    }
                    g_Tilemap.fg[tileIdx] = newTileType;
#endif
                    SpikesBreak(tileIdx);
                    g_api.PlaySfx(SFX_EXPLODE_FAST_A);
                } else {
                    SpikesApplyDamage(tileIdx);
                }
            }
        }
        break;
    }
}


INCLUDE_ASM("st/rnz1/nonmatchings/e_spikes", EntitySpikesDamage);
