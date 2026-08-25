/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:BOSS/RBO4:func_us_80192B38_from_rbo3
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/boss/rbo3/rbo3.c
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
void InitializeEntity(u16 arg0[]);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", EntityBreakable);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_80197938);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_8019818C);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_8019846C);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;
extern Tilemap g_Tilemap;
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void func_us_80192B38_from_rbo3(Entity* self) {
    Entity* entity;
    s32 x;
    s32 y;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);

    case 1:
        entity = &PLAYER;
        x = entity->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (x > 128 && x < 384) {
            D_us_8018072C = 1;
            D_us_80180728 = 1;
            g_api.TimeAttackController(
                TIMEATTACK_EVENT_MEDUSA_DEFEAT, TIMEATTACK_SET_VISITED);
            stopMusicFlag = true;
            currentMusicId = MU_ENCHANTED_BANQUET;
            self->step++;
        }
        break;
    case 2:
        if (g_api.func_80131F68() == false) {
            stopMusicFlag = false;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
        break;

    case 3:
        if (D_us_80180728 & 2) {
            g_api.TimeAttackController(
                TIMEATTACK_EVENT_MEDUSA_DEFEAT, TIMEATTACK_SET_RECORD);
            g_api.PlaySfx(SET_UNK_90);
            currentMusicId = MU_LOST_PAINTING;
            self->step++;
        }
        break;

    case 4:
        if (D_us_80180728 & 4) {
            self->step++;
        }
        break;

    case 5:
        x = 256 - g_Tilemap.scrollX.i.hi;
        y = 128 - g_Tilemap.scrollY.i.hi;
        entity = AllocEntity(&g_Entities[0xA0], &g_Entities[0xC0]);
        if (entity == NULL) {
            break;
        }




        CreateEntityFromEntity(UNK_ENTITY_30, self, entity);

        entity->posX.i.hi = x;
        entity->posY.i.hi = y;
        entity->params = 0x11;
        D_us_8018072C = 0;
        stopMusicFlag = true;
        currentMusicId = MU_LOST_PAINTING;
        self->step++;
        break;

    case 6:
        if (g_api.func_80131F68() == false) {
            stopMusicFlag = false;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
        break;
    }
}


INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_80198A18);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_801C0B9C_from_no1);
