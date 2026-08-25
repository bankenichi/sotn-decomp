/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityAlucardWaterEffect
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/water_effects.h
   target : src/st/rnz1/unk_37BF8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

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

extern s16 D_us_80181060[];
extern s16 D_us_80181E68[8];

static u16 func_pspeu_0924B480(s16 arg0, s16 arg1, s16 arg2, s16* arg3) {
    s16 temp_s2;
    s16 temp;
    s16* ptr;

    ptr = &D_us_80181060[arg0 * 8];
    arg1 -= (g_Tilemap.width - *ptr++);
    temp_s2 = *ptr++;
    arg1 += temp_s2;
    if (arg1 < 0) {
        return 0;
    }
    *arg3++ = arg1;

    temp = temp_s2 - arg1;
    if (temp <= 0) {
        return 0;
    }
    temp_s2 = temp;
    *arg3 = temp;

    temp = D_us_80181E68[*ptr++];
    if (temp) {
        temp = temp_s2 / temp;
    } else {
        temp = 0;
    }

    temp = temp + (g_Tilemap.height - *ptr++);
    if (temp < arg2) {
        return 0;
    }
    if (arg2 <= (g_Tilemap.height - *ptr++)) {
        return 0;
    }
    return ((temp + 0x7FFF) + 1) - arg2;
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
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

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySplashWater);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_37BF8", EntitySurfacingWater);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCommon;

extern EInit g_EInitCommon;
extern u16 D_us_8018105C[];
extern s32 D_us_80181EB4[16];
extern s16 D_us_80181EF4[8];

void EntitySideWaterSplash(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 velY;
    u16 params;
    s16 angle;
    s32 velX;
    s16 y;
    s16 x;
    s32* speedPtr;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        while (prim != NULL) {
            prim->u0 = prim->u2 = 0xF0;
            prim->u1 = prim->u3 = 0xFF;
            prim->v0 = prim->v1 = 0;
            prim->v2 = prim->v3 = 0xF;
            prim->clut = PAL_CC_STONE_EFFECT;
            prim->tpage = 0x1A;
            PGREY(prim, 0) = PGREY(prim, 1) = 128;
            PGREY(prim, 2) = PGREY(prim, 3) = 128;

            prim->p1 = 0;
            prim->priority = self->zPriority + 2;
            prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS |
                             DRAW_UNK02 | DRAW_TRANSP;
            prim = prim->next;
        }
        params = self->params;
        if (!(params & 0xF)) {
            g_api_PlaySfx(D_us_8018105C[0]);
        }
        angle = D_us_80181EF4[(params >> 4) & 0xF];
         
        speedPtr = &D_us_80181EB4[(params & 0xF) * 2];
        velX = rcos(angle) * *speedPtr;
        velY = rsin(angle + 0x800) * *speedPtr++;  
         
        velX += rsin(angle) * *speedPtr;
        velY += rcos(angle) * *speedPtr;
        velX += (s16)(params & 0xFF00) * 4;
        self->velocityX = -velX;
        self->velocityY = -velY;
        self->ext.waterEffects.accelY = FIX(22.0 / 128);
        break;

    case 1:
        MoveEntity(self);
        self->velocityY -= self->ext.waterEffects.accelY;
        break;
    }

    x = self->posX.i.hi;
    y = self->posY.i.hi;

    prim = &g_PrimBuf[self->primIndex];
    while (prim != NULL) {
        prim->x0 = prim->x2 = x - (prim->p1 / 2) - 4;
        prim->x1 = prim->x3 = x + (prim->p1 / 2) + 4;
        prim->y0 = prim->y1 = y - (prim->p1 / 2) - 4;
        prim->y2 = prim->y3 = y + (prim->p1 / 2) + 4;
        if (prim->b1 >= 3) {
            prim->b1 -= 3;
        } else {
            DestroyEntity(self);
            return;
        }
        PGREY(prim, 0) = PGREY(prim, 1);
        if (prim->b3 >= 4) {
            prim->b3 -= 4;
        }
        PGREY(prim, 2) = PGREY(prim, 3);
        prim->p1++;
        prim = prim->next;
    }
}

extern EInit g_EInitCommon;
extern s32 D_us_80181F04[8];

void EntitySmallWaterDrop(Entity* self) {
    u16 params = self->params;
    s16 upperParams = params & 0xFF00;
    Primitive *prim, *prim2;
    s32 primIndex;
    s32 xVel;
    s16 x, y;

    params &= 0xFF;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        primIndex = g_api_AllocPrimitives(PRIM_TILE, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];

        x = self->posX.i.hi;
        y = self->posY.i.hi;
        y -= Random() & 3;

        if (upperParams > 0) {
            x += Random() & 3;
        } else {
            x -= Random() & 3;
        }
        self->posX.i.hi = x;
        self->posY.i.hi = y;

        while (prim != NULL) {
            prim->u0 = 2;
            prim->v0 = 2;
            prim->x0 = x;
            prim->y0 = y;
            prim->r0 = 96;
            prim->g0 = 96;
            prim->b0 = 128;
            prim->priority = self->zPriority + 2;
            prim->drawMode =
                DRAW_TPAGE2 | DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;
            prim = prim->next;
        }
        xVel = D_us_80181F04[params * 2];
        if (upperParams > 0) {
            xVel = -xVel;
        }
        self->velocityX = xVel + (upperParams * 16);
        self->velocityY = D_us_80181F04[params * 2 + 1];
        self->ext.waterEffects.accelY = FIX(0.25);
        break;

    case 1:
        MoveEntity(self);
        self->velocityY -= self->ext.waterEffects.accelY;
        break;
    }

    x = self->posX.i.hi;
    y = self->posY.i.hi;

    prim = &g_PrimBuf[self->primIndex];
    prim->x0 = x;
    prim->y0 = y;
    if (prim->b0 >= 8) {
        prim->b0 -= 8;
        prim->r0 = prim->g0 -= 6;
    } else {
        DestroyEntity(self);
        return;
    }
}

extern EInit g_EInitCommon;

void EntityWaterDrop(Entity* self) {
    s16 x = self->posX.i.hi;
    s16 y = self->posY.i.hi;
    FakePrim* prim;
    s32 primIndex;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        primIndex = g_api_func_800EDB58(PRIM_TILE_ALT, 0x21);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        self->ext.timer.t = 0x2F;
        prim = (FakePrim*)&g_PrimBuf[primIndex];

        while (1) {
            prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                             DRAW_UNK02 | DRAW_TRANSP;
            prim->priority = self->zPriority + 2;

            if (prim->next == NULL) {
                prim->drawMode &= ~DRAW_HIDE;
                prim->y0 = prim->x0 = prim->w = 0;
                break;
            }

            prim->posX.i.lo = prim->posY.i.lo = 0;
            prim->velocityY.val = self->velocityY - (rand() & PSP_RANDMASK) * 8;
            prim->posY.i.hi = y + (rand() & 15);
            prim->posX.i.hi = x + (rand() & 31) - 16;
            prim->delay = (rand() & 15) + 32;
            prim->x0 = prim->posX.i.hi;
            prim->y0 = prim->posY.i.hi;
            prim->r0 = 255;
            prim->g0 = 255;
            prim->b0 = 255;
            prim->w = 2;
            prim->h = 2;
            prim = prim->next;
        }
        break;

    case 1:
        if (--self->ext.timer.t == 0) {
            DestroyEntity(self);
            return;
        }

        prim = (FakePrim*)&g_PrimBuf[self->primIndex];

        while (1) {
            if (prim->next == NULL) {
                prim->drawMode &= ~DRAW_HIDE;
                prim->y0 = prim->x0 = prim->w = 0;
                return;
            }
            prim->posX.i.hi = prim->x0;
            prim->posY.i.hi = prim->y0;
            if (!--prim->delay) {
                prim->drawMode |= DRAW_HIDE;
            }
            prim->posY.val += prim->velocityY.val;
            if (prim->velocityY.val < FIX(-0.5)) {
                prim->r0 -= 4;
                prim->g0 -= 4;
                prim->b0 -= 4;
            } else {
                prim->velocityY.val += FIX(-28.0 / 128);
            }
            prim->x0 = prim->posX.i.hi;
            prim->y0 = prim->posY.i.hi;
            prim = prim->next;
        }
        break;
    }
}
