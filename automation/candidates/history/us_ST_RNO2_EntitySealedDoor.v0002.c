/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:EntitySealedDoor
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_sealed_door.h
   target : src/st/rno2/unk_3459C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
s32 GetSideToPlayer(void);
Entity* AllocEntity(Entity* start, Entity* end);
void* GetLang(void* en, void* fr, void* sp, void* ge, void* it);
void CreateEntityFromCurrentEntity(u16, Entity*);
int rcos(int a);
int rsin(int a);
int abs(int x);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SealedDoorIsNearPlayer();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AB9EC_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B5FB8_from_no2);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AC54C_from_bo0);

static void func_us_801AC73C_from_bo0(Primitive* prim) {
    s32 x, y;

    if (!prim->g3) {
        prim->u0 = 1;
        prim->v0 = 1;
        prim->r0 = 0x80;
        prim->g0 = 0x80;
        prim->b0 = 0xC0;
        prim->drawMode = DRAW_UNK02;
        prim->x0 = g_CurrentEntity->posX.i.hi;
        prim->y0 = g_CurrentEntity->posY.i.hi + 8;
        prim->x1 = 0;
        prim->y1 = 0;
        LOW(prim->x2) = 0x7000 - ((Random() & 7) << 0xD);
        LOW(prim->x3) = 0x7000 - ((Random() & 7) << 0xD);
        prim->g3 = 1;
        prim->r3 = 0x20;
    }
#ifdef VERSION_US
    x = (prim->x0 << 0x10) + (u16)prim->x1;
#else
    x = (prim->x0 << 0x10) + prim->x1;
#endif
    x += LOW(prim->x2);
    prim->x0 = HIHU(x);
    prim->x1 = LOHU(x);
#ifdef VERSION_US
    y = (prim->y0 << 0x10) + (u16)prim->y1;
#else
    y = (prim->y0 << 0x10) + prim->y1;
#endif
    y += LOW(prim->x3);
    prim->y0 = HIH(y);
    prim->y1 = LOH(y);
    LOW(prim->x3) += 0x2000;
    prim->r3 -= 1;
    if (!prim->r3) {
        prim->g3 = 0;
        prim->drawMode = DRAW_HIDE;
        prim->p3 = 0;
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B68EC_from_no2);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", EntityPrisoner);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B5EE4);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCommon;
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern PlayerState g_Player;
extern s32 g_PlayableCharacter;
extern PlayerStatus g_Status;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern Tilemap g_Tilemap;

void EntitySealedDoor(Entity* self) {
    s32 palette;
    Entity* messageBox;
    Primitive* prim;
    s32 i;
    s16 angle;
    u8* uv;
    s16 x, y;
    u8 params;
    s16 endX;
    s16 scrollX, scrollY;
    s32 tileIdx;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        self->animSet = 0;
        self->animCurFrame = 1;
        self->zPriority = PLAYER.zPriority - 0x20;
        self->palette = SEALED_DOOR_PALETTE;
        self->facingLeft = 0;
        self->posY.i.hi += 0x1F;

        if (self->params & 0x100) {
            self->ext.sealedDoor.unk86 = -4;
        } else {
            self->ext.sealedDoor.unk86 = 4;
        }
        self->posX.i.hi += self->ext.sealedDoor.unk86;
        self->primIndex = g_api.AllocPrimitives(PRIM_GT4, 4);
        if (self->primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        uv = g_eBlueDoorUV[0];
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0, y = self->posY.i.hi - 0x1F; prim->next != NULL; i++,
            uv += 8, prim = prim->next) {
            prim->u0 = uv[0];
            prim->u1 = uv[1];
            prim->u2 = uv[2];
            prim->u3 = uv[3];
            prim->v0 = uv[4];
            prim->v1 = uv[5];
            prim->v2 = uv[6];
            prim->v3 = uv[7];
            prim->tpage = 0x15;
            prim->clut = SEALED_DOOR_CLUT;
            prim->priority = PLAYER.zPriority - 0x20;
            prim->y0 = prim->y1 = y;
            prim->y2 = prim->y3 = y + 0x3E;
            if (i == 0) {
                prim->y0 = prim->y1 = y;
                prim->y2 = prim->y3 = y + 0x3E;
            }
            prim->drawMode = DRAW_COLORS | DRAW_UNK02;
            prim->r0 = prim->b0 = prim->g0 = 0x7F;
            LOW(prim->r1) = LOW(prim->r0);
            LOW(prim->r2) = LOW(prim->r0);
            LOW(prim->r3) = LOW(prim->r0);
            if (i == 2 && (self->params & 0x100) == 0) {
                prim->drawMode |= DRAW_HIDE;
            }
            if (i == 1 && (self->params & 0x100)) {
                prim->drawMode |= DRAW_HIDE;
            }
        }
        prim->tpage = 0x15;
        prim->clut = self->palette;
        prim->u0 = prim->u2 = 0x40;
        prim->u1 = prim->u3 = 0x50;
        prim->v0 = prim->v1 = 0;
        prim->v2 = prim->v3 = 0x48;
        prim->x0 = prim->x2 = self->posX.i.hi - 8;
        prim->x1 = prim->x3 = self->posX.i.hi + 8;
        prim->y0 = prim->y1 = self->posY.i.hi - 0x24;
        prim->y2 = prim->y3 = self->posY.i.hi + 0x24;
        prim->priority = 0xAA;
        prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;
        if (SealedDoorIsNearPlayer(self)) {
            if ((self->params & 0x100) == 0) {
                self->ext.sealedDoor.angle = 0x1000;
            }
            if ((self->params & 0x100) != 0) {
                self->ext.sealedDoor.angle = 0x800;
            }
            PLAYER.velocityY = 0;
            g_Player.padSim = 0;
            g_Player.demo_timer = 24;
            self->animCurFrame = 0;
            self->step = 4;
            break;
        }
    case 1:
        GetPlayerCollisionWith(self, 8, 32, 5);
        self->ext.sealedDoor.angle = 0xC00;
        for (prim = &g_PrimBuf[self->primIndex], i = 0; prim->next != NULL; i++,
            prim = prim->next) {
            if (i != 0) {
                prim->drawMode |= DRAW_HIDE;
            } else {
                prim->drawMode = DRAW_COLORS | DRAW_UNK02;
            }
        }
        prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;

        if (!(((PLAYER.facingLeft != GetSideToPlayer()) & 1) ^ 1) &&
            ((PLAYER.step == 25 && g_PlayableCharacter != PLAYER_ALUCARD) ||
             PLAYER.step == 1) &&
            SealedDoorIsNearPlayer(self)) {
             
            if (!(g_Status.relics[RELIC_JEWEL_OF_OPEN] & RELIC_FLAG_ACTIVE)) {
                if (self->ext.sealedDoor.showedMessage) {
                    break;
                }
                messageBox = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (messageBox == NULL) {
                    break;
                }

#ifdef VERSION_PSP
                sealed_door_label =
                    GetLang(sealed_door_ENG, sealed_door_FR, sealed_door_ES,
                            sealed_door_DE, sealed_door_IT);
#endif

                self->ext.sealedDoor.showedMessage = 1;
                CreateEntityFromCurrentEntity(E_MESSAGE_BOX, messageBox);
                messageBox->posX.i.hi = 0x80;
                messageBox->posY.i.hi = 0xB0;
                messageBox->ext.messageBox.label = sealed_door_label;
                break;
            }
            prim = &g_PrimBuf[self->primIndex];
            for (i = 0; prim != NULL; i++, prim = prim->next) {
                if (i == 1 && (self->params & 0x100) == 0) {
                    prim->drawMode &= ~DRAW_HIDE;
                }
                if (i == 2 && (self->params & 0x100) != 0) {
                    prim->drawMode &= ~DRAW_HIDE;
                }
                if (i == 0) {
                    prim->drawMode &= ~DRAW_HIDE;
                }
            }
            self->animCurFrame = 0;
            g_Player.padSim = 0;
            g_Player.demo_timer = 2;
            self->ext.sealedDoor.sideToPlayer = (GetSideToPlayer() & 1) ^ 1;
            g_api.PlaySfx(SFX_DOOR_OPEN);
            self->step++;
        }
        break;

    case 2:
        g_Player.padSim = 0;
        g_Player.demo_timer = 24;
        if ((self->params & 0x100) == 0) {
            self->ext.sealedDoor.angle += 0x20;
            if (self->ext.sealedDoor.angle >= ROT(360)) {
                self->ext.sealedDoor.angle = ROT(360);
            }
            if (self->ext.sealedDoor.angle == ROT(360)) {
                self->step++;
            }
        } else {
            self->ext.sealedDoor.angle -= 0x20;
            if (self->ext.sealedDoor.angle <= ROT(180)) {
                self->ext.sealedDoor.angle = ROT(180);
            }
            if (self->ext.sealedDoor.angle == ROT(180)) {
                self->step++;
            }
        }
        break;

    case 3:
        if (g_Player.demo_timer >= 4) {
            return;
        }
        if (self->ext.sealedDoor.sideToPlayer) {
            g_Player.padSim = PAD_LEFT;
        } else {
            g_Player.padSim = PAD_RIGHT;
        }
        g_Player.demo_timer = 3;
        self->step++;
        break;

    case 4:
        if (self->ext.sealedDoor.sideToPlayer) {
            g_Player.padSim = PAD_LEFT;
        } else {
            g_Player.padSim = PAD_RIGHT;
        }
        g_Player.demo_timer = 4;
        if (!SealedDoorIsNearPlayer(self)) {
            g_api.PlaySfx(SFX_DOOR_OPEN);
            self->step++;
            g_Player.demo_timer = 0;
        }
        break;

    case 5:
        g_Player.padSim = 0;
        g_Player.demo_timer = 4;
        if ((self->params & 0x100) == 0) {
            self->ext.sealedDoor.angle -= 0x20;
            if (self->ext.sealedDoor.angle <= ROT(270)) {
                self->ext.sealedDoor.angle = ROT(270);
            }
        } else {
            self->ext.sealedDoor.angle += 0x20;
            if (self->ext.sealedDoor.angle >= ROT(270)) {
                self->ext.sealedDoor.angle = ROT(270);
            }
        }
        if (self->ext.sealedDoor.angle == ROT(270)) {
            prim = &g_PrimBuf[self->primIndex];
            for (i = 0; prim != NULL; i++, prim = prim->next) {
                if ((self->params & 0x1000) == 0 || i != 0) {
                    prim->drawMode |= DRAW_HIDE;
                }
            }
            self->animCurFrame = 1;
            self->step = 1;
        }
        break;
    }

    if (self->step != 1) {
        g_api.func_8010E168(1, 0x20);
        g_api.func_8010DFF0(1, 1);
    }

    x = self->posX.i.hi - self->ext.sealedDoor.unk86;
    if (self->params & 0x100) {
        x--;
    } else {
        x++;
    }

    i = 0;
    angle = self->ext.sealedDoor.angle;
    prim = &g_PrimBuf[self->primIndex];
    for (; prim->next != NULL; i++, prim = prim->next) {
        if (prim->drawMode & DRAW_HIDE) {
            continue;
        }
        if ((self->params & 0x100) == 0) {
            if (i == 0) {
                endX = prim->x0 = prim->x2 = x + ((rcos(angle) >> 8) * 32 >> 4);
                prim->x1 = prim->x3 = prim->x0 - ((rsin(angle) >> 4) * 6 >> 8);
                if (angle > ROT(348.75)) {
                    prim->x1 = prim->x3 = prim->x0 + 1;
                }
                if (angle > ROT(315)) {
                    prim->u0 = prim->u2 = 4;
                    prim->u1 = prim->u3 = 12;
                }
                if (angle <= ROT(315)) {
                    prim->u0 = prim->u2 = 3;
                    prim->u1 = prim->u3 = 13;
                }
                if (angle == ROT(360)) {
                    prim->r1 = prim->b1 = prim->g1 = 63;
                    prim->r3 = prim->b3 = prim->g3 = 63;
                } else {
                    prim->r1 = prim->b1 = prim->g1 =
                        0x7F - ((angle & 0x3FF) >> 4);
                    prim->r3 = prim->b3 = prim->g3 =
                        0x7F - ((angle & 0x3FF) >> 4);
                }
            } else {
                prim->x0 = prim->x2 = x;
                prim->x1 = prim->x3 = endX;
                if (angle == ROT(360)) {
                    prim->r0 = prim->b0 = prim->g0 = 63;
                    prim->r2 = prim->b2 = prim->g2 = 63;
                } else {
                    prim->r0 = prim->b0 = prim->g0 = (angle & 0x3FF) >> 4;
                    prim->r2 = prim->b2 = prim->g2 = (angle & 0x3FF) >> 4;
                }
            }
        } else {
            if (i == 0) {
                endX = prim->x1 = prim->x3 = x + ((rcos(angle) >> 8) * 32 >> 4);
                prim->x0 = prim->x2 = prim->x1 + ((rsin(angle) >> 4) * 6 >> 8);
                if (angle < ROT(191.25)) {
                    prim->x0 = prim->x2 = prim->x1 - 1;
                }
                if (angle < ROT(225)) {
                    prim->u0 = prim->u2 = 4;
                    prim->u1 = prim->u3 = 12;
                }
                if (angle > ROT(225)) {
                    prim->u0 = prim->u2 = 3;
                    prim->u1 = prim->u3 = 13;
                }
                if (angle == ROT(180)) {
                    prim->r0 = prim->b0 = prim->g0 = 127;
                    prim->r2 = prim->b2 = prim->g2 = 127;
                } else {
                    prim->r0 = prim->b0 = prim->g0 =
                        63 + ((angle & 0x3FF) >> 4);
                    prim->r2 = prim->b2 = prim->g2 =
                        63 + ((angle & 0x3FF) >> 4);
                }
            } else {
                prim->x0 = prim->x2 = endX - 1;
                prim->x1 = prim->x3 = x;
                if (angle == ROT(180)) {
                    prim->r1 = prim->b1 = prim->g1 = 63;
                    prim->r3 = prim->b3 = prim->g3 = 63;
                } else {
                    prim->r1 = prim->b1 = prim->g1 =
                        63 - ((angle & 0x3FF) >> 4);
                    prim->r3 = prim->b3 = prim->g3 =
                        63 - ((angle & 0x3FF) >> 4);
                }
            }
        }
    }

    if (self->animCurFrame) {
        prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;
    } else {
        prim->drawMode = DRAW_HIDE | DRAW_UNK02;
    }
    prim->clut = self->palette;
    self->ext.sealedDoor.unk82 += 0x20;
    if (self->ext.sealedDoor.unk82 > 0x380) {
        self->ext.sealedDoor.unk82 = -self->ext.sealedDoor.unk82;
    }

    palette = abs(self->ext.sealedDoor.unk82) >> 8;
    self->palette = palette + SEALED_DOOR_PALETTE;

    params = self->params & 0xFF;
    if (self->animCurFrame) {
        for (i = 0; i < 4; i++) {
            x = self->posX.i.hi;
            y = self->posY.i.hi - 24 + i * 0x10;
            scrollX = x + g_Tilemap.scrollX.i.hi;
            scrollY = y + g_Tilemap.scrollY.i.hi;
            tileIdx = (scrollX >> 4) + (scrollY >> 4) * g_Tilemap.hSize * 0x10;
            g_Tilemap.fg[tileIdx] = g_eBlueDoorTiles[params][i];
        }
    } else {
        for (i = 0; i < 4; i++) {
            x = self->posX.i.hi;
            y = self->posY.i.hi - 24 + i * 0x10;
            scrollX = x + g_Tilemap.scrollX.i.hi;
            scrollY = y + g_Tilemap.scrollY.i.hi;
            tileIdx = (scrollX >> 4) + (scrollY >> 4) * g_Tilemap.hSize * 0x10;
            g_Tilemap.fg[tileIdx] = g_eBlueDoorTiles[params][i + 4];
        }
    }
}
