/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityBossDoorTrigger
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/nz1/e_boss_doors.c
   target : src/st/rnz1/unk_29914.c
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
void DestroyEntity(Entity*);
void CreateEntityFromCurrentEntity(u16, Entity*);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* End permuter-seed writer declarations. */

int abs(int x);

bool func_801CDC80(s16* value, s16 target, s16 step) {
    if (abs(*value - target) < step) {
        *value = target;
        return true;
    }

    if (*value > target) {
        *value -= step;
    }

    if (*value < target) {
        *value += step;
    }

    return false;
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801A9994);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801A9DB8);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityFrozenShadeCrystal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AAF00);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB04C);

void func_801B2CF8(Primitive* prim) {
    s32 i;

    s32* ptr = (s32*)prim;
    s32 size = sizeof(Primitive) / sizeof(ptr);

    for (i = 0; i < size; i++) {
        *ptr++ = 0;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB16C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB198);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB380);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB768);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABA38);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABB58);

void RNZ1_Unused801ABDC0(void) {}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABDC8);

INCLUDE_RODATA("st/rnz1/nonmatchings/unk_29914", D_us_801A6050);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABDE4);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern Tilemap g_Tilemap;
extern PlayerState g_Player;
extern s32 D_us_80181134;

void EntityBossDoorTrigger(Entity* self) {
    Entity* entity;
    s32 timeAttackResult;
    s32 scrollX;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        timeAttackResult = g_api.TimeAttackController(
            TIMEATTACK_EVENT_KARASUMAN_DEFEAT, TIMEATTACK_GET_RECORD);
        if (timeAttackResult) {
            DestroyEntity(self);
            return;
        }
        entity = &g_Entities[80];
        CreateEntityFromCurrentEntity(E_ID(KARASUMAN), entity);
        entity->posX.i.hi = 128 - g_Tilemap.scrollX.i.hi;
        entity->posY.i.hi = 176 - g_Tilemap.scrollY.i.hi;
         

    case 1:
        entity = &PLAYER;
        scrollX = entity->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (!g_Player.demo_timer) {
            D_us_80181138 |= 1;
            g_api.TimeAttackController(
                TIMEATTACK_EVENT_KARASUMAN_DEFEAT, TIMEATTACK_SET_VISITED);
            self->step++;
        }
        break;

    case 2:
        entity = self + 1;
        CreateEntityFromCurrentEntity(E_ID(BOSS_DOORS), entity);
        entity->posX.i.hi = -8 - g_Tilemap.scrollX.i.hi;
        entity->posY.i.hi = 128 - g_Tilemap.scrollY.i.hi;
        entity->params = 0;
        entity = self + 2;
        CreateEntityFromCurrentEntity(E_ID(BOSS_DOORS), entity);
        entity->posX.i.hi = 264 - g_Tilemap.scrollX.i.hi;
        entity->posY.i.hi = 128 - g_Tilemap.scrollY.i.hi;
        entity->params = 1;
        D_us_80181134 = 1;
        self->step++;
         

    case 3:
        if (g_api.func_80131F68() != false) {
            g_api.PlaySfx(SET_UNK_90);
        }
        stopMusicFlag = true;
        currentMusicId = MU_FESTIVAL_OF_SERVANTS;
        self->step++;
        break;

    case 4:
        if (g_api.func_80131F68() == false) {
            stopMusicFlag = false;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
         
    case 5:
        if (D_us_80181138 & 2) {
            g_api.TimeAttackController(
                TIMEATTACK_EVENT_KARASUMAN_DEFEAT, TIMEATTACK_SET_RECORD);
            if (g_api.func_80131F68() != false) {
                g_api.PlaySfx(SET_UNK_90);
            }
            currentMusicId = MU_THE_TRAGIC_PRINCE;
            self->step++;
        }
        break;
    case 6:
        if (D_us_80181138 & 4) {
            entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_ID(LIFE_UP_SPAWN), self, entity);
                entity->posX.i.hi = 128;
                entity->posY.i.hi = 128;
                entity->params = 7;
                D_us_80181134 = 0;
                stopMusicFlag = true;
                currentMusicId = MU_THE_TRAGIC_PRINCE;
                self->step++;
            }
        }
        break;
    case 7:
        if (g_api.func_80131F68() == false) {
            stopMusicFlag = 0;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
        break;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityBossDoors);
