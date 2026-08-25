/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntityAlucardWaterEffect
   source : upstream/master:src/st/water_effects.h
   target : src/st/rno4/unk_52ED0.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void InitializeEntity(u16 arg0[]);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_801C4144();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_pspeu_0924B480);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;
extern PlayerState g_Player;
extern s16 g_WaterXTbl[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern unkGraphicsStruct g_unkGraphicsStruct;
extern EInit g_EInitSpawner;

void EntityAlucardWaterEffect(Entity* self) {
    s16 sp10[2];
    s16 posX, posY;
    u16 sp28;
    Entity* tempEntity;
    s16 var_s1;
    s16 var_s3;
    s16 i;
    u16 sp30;
    u16 var_s6;
    u32 var_s7;
    u16 sp4A;
    s32 status;
    Tilemap* tilemap = &g_Tilemap;
    Entity* player = &PLAYER;

    posX = player->posX.i.hi + tilemap->scrollX.i.hi;
    status = g_Player.status;
    if (status & (PLAYER_STATUS_CROUCH | PLAYER_STATUS_TRANSFORM)) {
        if (status & PLAYER_STATUS_CROUCH) {
            sp4A = 0x14;
            var_s6 = 0x19;
            if (status & PLAYER_STATUS_WOLF_FORM) {
                sp4A = 0xA;
            }
        } else if (
            status & (PLAYER_STATUS_MIST_FORM | PLAYER_STATUS_BAT_FORM)) {
            sp4A = 0xC;
            var_s6 = 5;
        } else if (status & PLAYER_STATUS_WOLF_FORM) {
            sp4A = 0x14;
            var_s6 = 0x19;
        }
    } else {
        sp4A = 0x28;
        var_s6 = 0x19;
    }
    posY = var_s6 + (player->posY.i.hi + tilemap->scrollY.i.hi);
    var_s3 = var_s1 = self->params;
    var_s3 &= 0xFF;
    var_s1 = var_s1 >> 8;
    for (i = 0; i < var_s1; i++, var_s3++) {
        sp28 = func_801C4144(var_s3, posX, posY, sp10);
        if (sp28) {
            sp30 = var_s3 * 8;
            break;
        }
    }
    var_s3 = sp28 & 0x7FFF;
    if (self->step) {
        if (F(player->velocityY).i.hi &&
            (status & (PLAYER_STATUS_MIST_FORM | PLAYER_STATUS_BAT_FORM)) ==
                0) {
            if (F(player->velocityY).i.hi < 0) {
                if (!sp28) {
                    var_s1 = self->ext.aluwater.unk7C;
                    if (var_s1 && (var_s1 & 0x7FFF) < 17) {
                        var_s1 = self->ext.aluwater.unk88;
                        if (self->ext.aluwater.unk8C < 14) {
                            var_s7 = ((14 - self->ext.aluwater.unk8C) << 11) +
                                     (g_WaterXTbl[var_s1 + 2] << 8) +
                                     (g_WaterXTbl[var_s1 + 5] << 5);
                        } else {
                            if (self->ext.aluwater.unk8E < 14) {
                                var_s7 =
                                    ((self->ext.aluwater.unk8E + 14) << 11) +
                                    (g_WaterXTbl[var_s1 + 2] << 8) +
                                    (g_WaterXTbl[var_s1 + 6] << 5);
                            } else {
                                var_s7 = g_WaterXTbl[var_s1 + 2] << 8;
                            }
                        }
                        var_s1 = (var_s7 >> 8) & 7;
                        if (!var_s1 || var_s1 == 7) {
                            var_s1 = (var_s7 >> 5) & 7;
                            if (!var_s1 || var_s1 == 7) {
                                var_s1 = 0;
                            }
                        }
                        if (var_s1) {
                            for (i = 0; i < 8; i++) {
                                tempEntity = AllocEntity(
                                    &g_Entities[224], &g_Entities[256]);
                                if (tempEntity == NULL) {
                                    break;
                                }
                                CreateEntityFromEntity(
                                    E_SIDE_WATER_SPLASH, player, tempEntity);
                                tempEntity->params =
                                    (u16)g_WaterXTbl[self->ext.aluwater.unk88 +
                                                     7] +
                                    (var_s1 << 4) + i;
                                tempEntity->posY.i.hi += var_s6 - var_s3;
                                tempEntity->zPriority = player->zPriority;
                            }
                        } else {
                            tempEntity =
                                AllocEntity(&g_Entities[224], &g_Entities[256]);
                            if (tempEntity != NULL) {
                                CreateEntityFromEntity(
                                    E_SPLASH_WATER, player, tempEntity);
                                tempEntity->posX.i.hi =
                                    self->ext.aluwater.unk80 -
                                    tilemap->scrollX.i.hi;
                                tempEntity->posY.i.hi =
                                    self->ext.aluwater.unk82 -
                                    (self->ext.aluwater.unk7C & 0x7FFF) -
                                    tilemap->scrollY.i.hi;
                                tempEntity->zPriority = player->zPriority;
                                if (player->velocityY > FIX(-4)) {
                                    tempEntity->params = var_s7 + 1;
                                } else {
                                    tempEntity->params = var_s7;
                                }
                            }
                        }
                    }
                }
            } else if (sp28 && (var_s3 < 9) && !self->ext.aluwater.unk7C) {
                if (sp10[0] < 14) {
                    var_s7 =
                        ((14 - sp10[0]) << 11) + (g_WaterXTbl[sp30 + 2] << 8) +
                        (g_WaterXTbl[sp30 + 5] << 5);
                } else if (sp10[1] < 14) {
                    var_s7 =
                        ((sp10[1] + 14) << 11) + (g_WaterXTbl[sp30 + 2] << 8) +
                        (g_WaterXTbl[sp30 + 6] << 5);
                } else {
                    var_s7 = g_WaterXTbl[sp30 + 2] << 8;
                }
                var_s1 = (var_s7 >> 8) & 7;
                if (!var_s1 || var_s1 == 7) {
                    var_s1 = (var_s7 >> 5) & 7;
                    if (!var_s1 || var_s1 == 7) {
                        var_s1 = 0;
                    }
                }
                if (var_s1) {
                    for (i = 0; i < 8; i++) {
                        tempEntity =
                            AllocEntity(&g_Entities[224], &g_Entities[256]);
                        if (tempEntity == NULL) {
                            break;
                        }
                        CreateEntityFromEntity(
                            E_SIDE_WATER_SPLASH, player, tempEntity);
                        tempEntity->params =
                            (u16)g_WaterXTbl[sp30 + 7] + (var_s1 << 4) + i;
                        tempEntity->posY.i.hi += var_s6 - var_s3;
                        tempEntity->zPriority = player->zPriority;
                    }
                } else {
                    tempEntity =
                        AllocEntity(&g_Entities[224], &g_Entities[256]);
                    if (tempEntity != NULL) {
                        CreateEntityFromEntity(
                            E_SPLASH_WATER, player, tempEntity);
                        if (player->velocityY > FIX(4)) {
                            tempEntity->params = var_s7 + 1;
                        } else {
                            tempEntity->params = var_s7 + 2;
                        }
                        tempEntity->params =
                            var_s7;  
                        tempEntity->posY.i.hi += var_s6 - var_s3;
                        tempEntity->zPriority = player->zPriority;
                    }
                }
            }
        } else if ((status & PLAYER_STATUS_MIST_FORM) == 0) {
            if (sp28 && !self->ext.aluwater.unk7E) {
                var_s1 = g_WaterXTbl[sp30 + 7];
                if (posX != self->ext.aluwater.unk80) {
                    if (var_s3 <= sp4A && sp10[0] >= 6 && sp10[1] >= 6) {
                        tempEntity =
                            AllocEntity(&g_Entities[224], &g_Entities[256]);
                        if (tempEntity != NULL) {
                            CreateEntityFromEntity(
                                E_SURFACING_WATER, player, tempEntity);
                            tempEntity->posY.i.hi += var_s6 - var_s3;
                            if (player->velocityX != 0) {
                                tempEntity->params = (sp4A - var_s3) >> 3;
                                if (tempEntity->params == 5) {
                                    tempEntity->params = 4;
                                }
                            } else {
                                tempEntity->params = 0;
                            }
                            tempEntity->params |= g_WaterXTbl[sp30 + 2] << 8;
                            tempEntity->ext.aluwater.unk88 = sp30;
                            tempEntity->ext.aluwater.unk8A = var_s1;
                            tempEntity->zPriority = player->zPriority;
                            self->ext.aluwater.unk7E = 8;
                        }
                    }
                } else if (
                    var_s1 && var_s3 <= sp4A && sp10[0] >= 6 && sp10[1] >= 6) {
                    tempEntity =
                        AllocEntity(&g_Entities[224], &g_Entities[256]);
                    if (tempEntity != NULL) {
                        CreateEntityFromEntity(
                            E_SURFACING_WATER, player, tempEntity);
                        tempEntity->posY.i.hi += var_s6 - var_s3;
                        tempEntity->params = g_WaterXTbl[sp30 + 2] << 8;
                        tempEntity->ext.aluwater.unk88 = sp30;
                        tempEntity->ext.aluwater.unk8A = var_s1;
                        tempEntity->zPriority = player->zPriority;
                        self->ext.aluwater.unk7E = 8;
                    }
                }
            }
            if (sp28) {
                var_s1 = g_WaterXTbl[sp30 + 7];
                if (var_s1 > 0x1000 || var_s1 < -0x1000) {
                    if (var_s3 >= sp4A) {
                        if (status & PLAYER_STATUS_BAT_FORM) {
                            var_s1 = var_s1 * 3 / 4;
                        } else {
                            var_s1 /= 2;
                        }
                    } else {
                        var_s1 = (var_s1 * var_s3) / 0x50;
                    }
                    if ((var_s1 < 0 &&
                         !(g_Player.vram_flag & TOUCHING_L_WALL)) ||
                        (var_s1 > 0 &&
                         !(g_Player.vram_flag & TOUCHING_R_WALL))) {
                        player->posX.val += var_s1 << 4;
                    }
                }
            }
        }
        if (self->ext.aluwater.unk7E) {
            self->ext.aluwater.unk7E--;
        }
        g_unkGraphicsStruct.D_80097448 = var_s3;
        if (status & (PLAYER_STATUS_CROUCH | PLAYER_STATUS_TRANSFORM)) {
            if (status & PLAYER_STATUS_CROUCH) {
                if (status & PLAYER_STATUS_WOLF_FORM) {
                    if (var_s3 > 4) {
                        g_unkGraphicsStruct.D_8009744C = var_s3 - 4;
                    } else {
                        g_unkGraphicsStruct.D_8009744C = 0;
                    }
                    if (var_s3 > 12) {
                        g_unkGraphicsStruct.D_80097450 = var_s3 - 12;
                    } else {
                        g_unkGraphicsStruct.D_80097450 = 0;
                    }
                } else {
                    if (var_s3 > 8) {
                        g_unkGraphicsStruct.D_8009744C = var_s3 - 8;
                    } else {
                        g_unkGraphicsStruct.D_8009744C = 0;
                    }
                    if (var_s3 > 0x18) {
                        g_unkGraphicsStruct.D_80097450 = var_s3 - 0x18;
                    } else {
                        g_unkGraphicsStruct.D_80097450 = 0;
                    }
                }
            } else if (
                status & (PLAYER_STATUS_MIST_FORM | PLAYER_STATUS_BAT_FORM)) {
                if (var_s3 > 6) {
                    g_unkGraphicsStruct.D_8009744C = var_s3 - 6;
                } else {
                    g_unkGraphicsStruct.D_8009744C = 0;
                }
                if (var_s3 > 0x10) {
                    g_unkGraphicsStruct.D_80097450 = var_s3 - 0x10;
                } else {
                    g_unkGraphicsStruct.D_80097450 = 0;
                }
            } else if (status & PLAYER_STATUS_WOLF_FORM) {
                if (var_s3 > 8) {
                    g_unkGraphicsStruct.D_8009744C = var_s3 - 8;
                } else {
                    g_unkGraphicsStruct.D_8009744C = 0;
                }
                if (var_s3 > 0x18) {
                    g_unkGraphicsStruct.D_80097450 = var_s3 - 0x18;
                } else {
                    g_unkGraphicsStruct.D_80097450 = 0;
                }
            }
        } else {
            if (var_s3 > 0x10) {
                g_unkGraphicsStruct.D_8009744C = var_s3 - 0x10;
            } else {
                g_unkGraphicsStruct.D_8009744C = 0;
            }
            if (var_s3 > 0x30) {
                g_unkGraphicsStruct.D_80097450 = var_s3 - 0x30;
            } else {
                g_unkGraphicsStruct.D_80097450 = 0;
            }
        }
    } else {
        InitializeEntity(g_EInitSpawner);
    }
    self->ext.aluwater.unk7C = sp28;
    self->ext.aluwater.unk80 = posX;
    self->ext.aluwater.unk82 = posY;
    self->ext.aluwater.unk88 = sp30;
    self->ext.aluwater.unk8C = sp10[0];
    self->ext.aluwater.unk8E = sp10[1];
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntitySplashWater);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntitySurfacingWater);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntitySideWaterSplash);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntitySmallWaterDrop);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", EntityWaterDrop);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D511C);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D58FC);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D5BA4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", StepTowards);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D5DC8);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D5E90);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D68E0);

INCLUDE_ASM("st/rno4/nonmatchings/unk_52ED0", func_us_801D6B8C);
