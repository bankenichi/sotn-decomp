/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO7:func_us_80192B38_from_rbo3
   source : upstream/master:src/boss/rbo3/rbo3.c
   target : src/boss/rbo7/unk_138A0.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo7.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityBreakable);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801BAB18_from_bo0);

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
#ifdef VERSION_PSP
         
        CreateEntityFromEntity(D_psp_09254D20, self, entity);
#else
        CreateEntityFromEntity(UNK_ENTITY_30, self, entity);
#endif
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

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801940B4);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801957C0);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityHarpyKick);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80195A8C);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80195D04);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityCtulhuDeath);
