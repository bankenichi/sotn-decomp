/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCHI:EntityBreakable
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rchi/e_rchi_breakable.h
   target : src/st/rchi/e_breakable.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
u8 AnimateEntity(u8 frames[], Entity* entity);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
void DestroyEntity(Entity*);
void ReplaceBreakableWithItemDrop(Entity*);
/* End permuter-seed writer declarations. */

/*
 * RCHI's breakable entity is stage-specific and roughly twice the size of the
 * shared candle implementation (0x270 versus 0x134 bytes).
 */
// EntityBreakableDebris's candidate failed to build on this name alone.
// Declared in the shared src/st/e_breakable.h:9.
extern EInit g_EInitBreakable;

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityBreakable(Entity* self) {
    u16 breakableType = self->params >> 12;
    Entity* entity;
    s32 i;
    s16* debrisOffsets;

    if (!self->step) {
        InitializeEntity(g_EInitBreakable);
        self->zPriority = 0x70;
        self->blendMode = g_RchiBreakableBlendModes[breakableType];
        self->hitboxHeight = g_RchiBreakableHitboxHeights[breakableType];
        self->animSet = g_RchiBreakableAnimSets[breakableType];
        entity = self + 1;
        CreateEntityFromEntity(E_ID(BACKGROUND_BLOCK), self, entity);
        if (breakableType) {
            entity->posY.i.hi += 0x20;
        } else {
            entity->posY.i.hi += 0x10;
        }
        entity->params = 1;
    }

    AnimateEntity(g_RchiBreakableAnimations[breakableType], self);
    if (self->hitParams) {
        g_api.PlaySfx(SFX_FIRE_SHOT);
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromCurrentEntity(E_EXPLOSION, entity);
            entity->params = g_RchiBreakableExplosionTypes[breakableType];
            entity->params |= 0x10;
        }

        debrisOffsets = g_RchiBreakableDebrisOffsets;
        for (i = 0; i < 4; i++) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_ID(BREAKABLE_DEBRIS), self, entity);
                entity->posX.i.hi -= *debrisOffsets++;
                entity->posY.i.hi -= *debrisOffsets++;
                if (breakableType) {
                    entity->posY.i.hi += 0x14;
                }
                entity->params = i;
            }
        }
        if (breakableType) {
            for (i = 0; i < 3; i++) {
                entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (entity != NULL) {
                    CreateEntityFromEntity(
                        E_ID(BREAKABLE_DEBRIS), self, entity);
                    entity->posX.i.hi -= *debrisOffsets++;
                    entity->posY.i.hi -= *debrisOffsets++;
                    entity->params = i + 4;
                }
            }
        }
        entity = self + 1;
        DestroyEntity(entity);
        ReplaceBreakableWithItemDrop(self);
    }
}


INCLUDE_ASM("st/rchi/nonmatchings/e_breakable", EntityBreakableDebris);
