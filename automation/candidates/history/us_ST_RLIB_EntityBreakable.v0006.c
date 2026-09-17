/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RLIB:EntityBreakable
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rlib/unk_20AE8.c
   target : src/st/rlib/unk_20AE8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rlib.h"

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
void PlaySfxPositional(s32 arg0);
void PreventEntityFromRespawning(Entity* entity);
void DestroyEntity(Entity*);
void ReplaceBreakableWithItemDrop(Entity*);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitBreakable;
extern unkGraphicsStruct g_unkGraphicsStruct;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern GameApi g_api;

void EntityBreakable(Entity* self) {
    Entity* entity;
    u16 breakableType;

    breakableType = self->params >> 12;
    if (!self->step) {
        InitializeEntity(g_EInitBreakable);
        self->zPriority = g_unkGraphicsStruct.g_zEntityCenter - 20;
        if (breakableType < 5) {
            entity = self + 1;
            CreateEntityFromEntity(E_ID(UNK_1B), self, entity);
            entity->params = breakableType;
            entity->zPriority = self->zPriority;
        }
        self->blendMode = g_RlibBreakableBlendModes[breakableType];
        self->hitboxHeight = g_RlibBreakableHitboxHeights[breakableType];
        self->animSet = g_RlibBreakableAnimSets[breakableType];
        self->unk5A = g_RlibBreakableUnk5A[breakableType];
        self->palette = g_RlibBreakablePalettes[breakableType];
        self->hitboxOffY = g_RlibBreakableHitboxOffsetsY[breakableType];
    }
    AnimateEntity(g_RlibBreakableAnimations[breakableType], self);
    if (self->hitParams) {
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromCurrentEntity(E_EXPLOSION, entity);
            entity->params = g_RlibBreakableExplosionTypes[breakableType];
        }
        switch (breakableType) {
        case 2:
        case 3:
            PlaySfxPositional(SFX_GLASS_BREAK_E);
            break;
        case 9:
            entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (entity != NULL) {
                CreateEntityFromCurrentEntity(E_ID(UNK_28), entity);
                entity->params = 0x100;
            }
            g_api.PlaySfx(SFX_GLASS_BREAK_E);
            entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_PERSISTENT_ITEM_DROP, self, entity);
                entity->params = self->params & 0x1FF;
            }
            PreventEntityFromRespawning(self);
            DestroyEntity(self);
            return;
        case 7:
            g_api.PlaySfx(SFX_GLASS_BREAK_E);
            entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_PERSISTENT_ITEM_DROP, self, entity);
                entity->params = self->params & 0x1FF;
            }
            PreventEntityFromRespawning(self);
            DestroyEntity(self);
            return;
        case 8:
            g_api.PlaySfx(SFX_GLASS_BREAK_E);
            entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_PERSISTENT_ITEM_DROP, self, entity);
                entity->params = 3;
            }
            PreventEntityFromRespawning(self);
            DestroyEntity(self);
            return;
        default:
            g_api.PlaySfx(SFX_GLASS_BREAK_C);
            break;
        }
        ReplaceBreakableWithItemDrop(self);
    }
}


INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AE7AC_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AE84C_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AF280_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AF538_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AF7B8_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AFA80_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AE8E8_from_lib);
