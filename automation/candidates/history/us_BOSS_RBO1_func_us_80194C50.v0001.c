/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO1:func_us_80194C50
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo1/e_boss_room.c
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
void InitializeEntity(u16 arg0[]);
void CreateEntityFromCurrentEntity(u16, Entity*);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_us_8019ED80_from_rbo2();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", EntityBreakable);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801923A8);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80192C5C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80192F84);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801936FC);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80193C2C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80193E24);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80194108);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_8019ED80_from_rbo2);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", polarPlacePartsWithAngvel);

void func_801CDD00(Entity* entity, s16 arg1, s16 arg2) {
    s16 temp_t0 = arg1 - entity->ext.GH_Props.rotate;

    if (temp_t0 > 0x800) {
        temp_t0 = temp_t0 - 0x1000;
    }

    if (temp_t0 < -0x800) {
        temp_t0 = temp_t0 + 0x1000;
    }

    temp_t0 = temp_t0 / arg2;
    entity->ext.GH_Props.rotVel = temp_t0;
    entity->ext.GH_Props.unkA4 = arg1;
}



/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void func_801CDD80(s16* entOffsets, unkStr_801CDD80* arg1) {
    Entity* var_s1;
    s16* ptr = arg1->unk4;

    while (*entOffsets) {
        if (*entOffsets != 0xFF) {
            var_s1 = g_CurrentEntity + *entOffsets;
            func_801CDD00(var_s1, *ptr, arg1->unk0);
        }
        ptr++;
        entOffsets++;
    }
}



void func_801CDF1C(s16 entIndices[], unkStr_801CDD80* arg1, s32 arg2) {

    arg1 += (u16)g_CurrentEntity->ext.GH_Props.unkB0[arg2];

    if (!g_CurrentEntity->ext.GH_Props.unkB4[arg2]) {
        func_801CDD80(entIndices, arg1);
        g_CurrentEntity->ext.GH_Props.unkB4[arg2] = arg1->unk0;
    }
    if (!--g_CurrentEntity->ext.GH_Props.unkB4[arg2]) {
        arg1++;
        if (!arg1->unk0) {
            g_CurrentEntity->ext.GH_Props.unkB0[arg2] = 0;
        } else {
            ++g_CurrentEntity->ext.GH_Props.unkB0[arg2];
        }
    }
}



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
            func_us_8019ED80_from_rbo2(entity);
        }
        offsets++;
    }
}


// decompiled in src/boss/bo1/e_explosion_flame.c
INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_8019D260_from_rcen);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801947E4);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;
extern Tilemap g_Tilemap;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern GameApi g_api;

void func_us_80194C50(Entity* self) {
    Entity* entity;
    Rbo1TilePlacement* placement;
    s32 offsetX;
    s32 offsetY;
    s32 i;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        entity = &self[1];
        placement = tile_placements;
        i = 0;
        while (i < LEN(tile_placements)) {
            CreateEntityFromCurrentEntity(E_ID(BOSS_ROOM_BLOCK), entity);
            entity->params = placement->params;
            entity->posX.i.hi = placement->x - g_Tilemap.scrollX.i.hi;
            entity->posY.i.hi = placement->y - g_Tilemap.scrollY.i.hi;
            i++;
            entity++;
            placement++;
        }
        entity = &g_Entities[80];
        CreateEntityFromCurrentEntity(E_ID(UNK_16), entity);
        entity->posX.i.hi = 0x240 - g_Tilemap.scrollX.i.hi;
        entity->posY.i.hi = 0xD8 - g_Tilemap.scrollY.i.hi;
        // fallthrough

    case 1:
        offsetX = PLAYER.posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (offsetX > 0x18 && offsetX < 0x3D8) {
            bossFlags |= RBO1_BOSS_FLAG_DOORS_CLOSE;
            g_api.PlaySfx(SET_UNK_90);
            self->step++;
        }
        break;

    case 2:
        offsetX = PLAYER.posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (offsetX > 0x140 && offsetX < 0x320) {
            bossFlags |= RBO1_BOSS_FLAG_FIGHT_STARTED;
            g_api.TimeAttackController(
                TIMEATTACK_EVENT_BEELZEBUB_DEFEAT, TIMEATTACK_SET_VISITED);
            self->step++;
        }
        break;

    case 3:
        if (g_api.func_80131F68() == false) {
            stopMusicFlag = false;
            currentMusicId = MU_DEATH_BALLAD;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
        // fallthrough

    case 4:
        if (bossFlags & RBO1_BOSS_FLAG_DEFEATED) {
            g_api.TimeAttackController(
                TIMEATTACK_EVENT_BEELZEBUB_DEFEAT, TIMEATTACK_SET_RECORD);
            g_api.PlaySfx(SET_UNK_90);
            currentMusicId = MU_FINAL_TOCATTA;
            self->step++;
        }
        break;

    case 5:
        if (bossFlags & RBO1_BOSS_FLAG_REWARD_READY) {
            self->step++;
        }
        break;

    case 6:
        offsetX = 0x80;
        offsetY = 0x180 - g_Tilemap.scrollY.i.hi;
        entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_ID(LIFE_UP_SPAWN), self, entity);
            entity->posX.i.hi = offsetX;
            entity->posY.i.hi = offsetY;
            entity->params = 5;
            stopMusicFlag = true;
            currentMusicId = MU_FINAL_TOCATTA;
            bossFlags |= RBO1_BOSS_FLAG_DOORS_OPEN;
            self->step++;
        }
        break;

    case 7:
        if (g_api.func_80131F68() == false) {
            stopMusicFlag = false;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
        break;
    }
}


INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", EntityBossRoomBlock);
