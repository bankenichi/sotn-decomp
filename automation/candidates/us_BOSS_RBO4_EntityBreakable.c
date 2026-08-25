/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:BOSS/RBO4:EntityBreakable
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/boss/bo1/e_breakable.c
   target : src/boss/rbo4/unk_17804.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
u8 AnimateEntity(u8 frames[], Entity* entity);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
void ReplaceBreakableWithItemDrop(Entity*);
void InitializeEntity(u16 arg0[]);
/* End permuter-seed writer declarations. */


/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern EInit g_EInitBreakable;
extern unkGraphicsStruct g_unkGraphicsStruct;

void EntityBreakable(Entity* self) {
    u16 breakableType = self->params >> 12;
    if (self->step) {
        AnimateEntity(g_eBreakableAnimations[breakableType], self);
        if (self->hitParams) {
            Entity* entityDropItem;
            g_api.PlaySfx(SFX_CANDLE_HIT);
            entityDropItem = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entityDropItem != NULL) {
                CreateEntityFromCurrentEntity(E_EXPLOSION, entityDropItem);
                entityDropItem->params =
                    g_eBreakableExplosionTypes[breakableType];
            }
            ReplaceBreakableWithItemDrop(self);
        }
    } else {
        InitializeEntity(g_EInitBreakable);
        self->zPriority = g_unkGraphicsStruct.g_zEntityCenter - 20;
        self->zPriority = g_eBreakableZPriority[breakableType];
        self->blendMode = blend_modes[breakableType];
        self->hitboxHeight = g_eBreakableHitboxes[breakableType];
        self->animSet = g_eBreakableanimSets[breakableType];
    }
}


INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_80197938);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_8019818C);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_8019846C);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_80192B38_from_rbo3);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_80198A18);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_801C0B9C_from_no1);
