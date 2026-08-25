/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO1:EntityBreakable
   source : upstream/master:src/boss/bo1/e_breakable.c
   target : src/boss/rbo1/unk_12274.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
void ReplaceBreakableWithItemDrop(Entity*);
void InitializeEntity(u16 arg0[]);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitBreakable;

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

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801923A8);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80192C5C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80192F84);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801936FC);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80193C2C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80193E24);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80194108);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_8019ED80_from_rbo2);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", polarPlacePartsWithAngvel);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CDD00);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CDD80);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CDF1C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CE1E8);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CE228);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", polarPlacePartsList);

// decompiled in src/boss/bo1/e_explosion_flame.c
INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_8019D260_from_rcen);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801947E4);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80194C50);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", EntityBossRoomBlock);
