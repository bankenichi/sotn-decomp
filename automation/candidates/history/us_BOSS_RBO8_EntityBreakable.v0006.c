/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO8:EntityBreakable
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo8/unk_1546C.c
   target : src/boss/rbo8/unk_1546C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo8.h"

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
void polarPlacePart(Entity* self);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern s32 D_us_80180BBC[]; /* retained BOSS/RBO8 data asm/us/boss/rbo8/data/B74.data.s, size 0x20 */
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern u8 D_us_80180BE4[]; /* retained BOSS/RBO8 data asm/us/boss/rbo8/data/B74.data.s, size 0x8 */
extern EInit g_EInitBreakable;
extern unkGraphicsStruct g_unkGraphicsStruct;
extern u8 D_us_80180BFC[]; /* retained BOSS/RBO8 data asm/us/boss/rbo8/data/B74.data.s, size 0x10 */
extern u8 D_us_80180BDC[]; /* retained BOSS/RBO8 data asm/us/boss/rbo8/data/B74.data.s, size 0x8 */

void EntityBreakable(Entity* self) {
    Entity* entity;
    u16 breakableType;

    breakableType = self->params >> 12;
    if (self->step) {
        AnimateEntity(D_us_80180BBC[breakableType], self);
        if (self->hitParams) {
            g_api.PlaySfx(SFX_CANDLE_HIT);
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromCurrentEntity(E_EXPLOSION, entity);
                entity->params = D_us_80180BE4[breakableType];
            }
            ReplaceBreakableWithItemDrop(self);
        }
    } else {
        InitializeEntity(g_EInitBreakable);
        self->zPriority = g_unkGraphicsStruct.g_zEntityCenter - 20;
        self->blendMode = D_us_80180BFC[breakableType];
        self->hitboxHeight = D_us_80180BDC[breakableType];
        self->animSet = D_us_80180BEC[breakableType];
    }
}


INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_us_801955A0);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_1546C", func_us_801955F8);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void func_801CE1E8(s32 step) {
    s32 i;

    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;

    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}



void func_801CE228() {
    s32 i;









    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}



void polarPlacePartsList(s16* offsets) {
    Entity* entity;

    while (*offsets) {
        entity = g_CurrentEntity + *offsets;
        if (!entity->ext.GH_Props.unkA8) {
            polarPlacePart(entity);
        }
        offsets++;
    }
}
