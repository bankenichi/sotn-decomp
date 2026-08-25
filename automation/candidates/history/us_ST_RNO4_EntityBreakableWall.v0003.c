/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:ST/RNO4:EntityBreakableWall
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/chi/en_breakable_wall.c
   target : src/st/rno4/unk_44B0C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void DestroyEntity(Entity*);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
Entity* AllocEntity(Entity* start, Entity* end);
s32 Random();
void CreateEntityFromCurrentEntity(u16, Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakable);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C123C_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C12B0_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C15F8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5364);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBgColumnsParallax_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C1EE4_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5C78);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5EE4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2850_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2B78_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2E60_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3160_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C34EC_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C37C8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3A04_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3CC4_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3FB0_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C4228_from_no4);

#define PLAYER g_Entities[PLAYER_CHARACTER]
#define PLAYER_CHARACTER 0
#define NO4_WATER_BLOCKED 193
#define PAD_LEFT 32768
#define PAD_RIGHT 8192
#define Player_Walk 1
#define TOUCHING_GROUND 1
extern EInit g_EInitInteractable;
extern struct Entity;
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
void InitializeEntity(u16 arg0[]);

void EntityWaterBox(Entity* self) {
    Entity* player;
    u16 collision;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = 6;
        if (g_CastleFlags[NO4_WATER_BLOCKED]) {
            self->posX.i.hi = 0x720 - g_Tilemap.scrollX.i.hi;
        } else {
            self->posX.i.hi = 0x760 - g_Tilemap.scrollX.i.hi;
        }
    }

    player = &PLAYER;
    collision = GetPlayerCollisionWith(self, 16, 17, 5);

    if (collision & 1 && g_Player.vram_flag & TOUCHING_GROUND) {
        if (self->posX.i.hi > player->posX.i.hi) {
            if (g_pads[0].pressed & PAD_RIGHT && PLAYER.step == Player_Walk) {
                if (self->ext.timer.t) {
                    self->ext.timer.t--;
                    return;
                }
                if (self->posX.i.hi + g_Tilemap.scrollX.i.hi < 0x7A0) {
                    self->posX.i.hi++;
                    player->posX.i.hi++;
                }
                self->ext.timer.t = 3;
            }
        } else {
            if (g_pads[0].pressed & PAD_LEFT && PLAYER.step == Player_Walk) {
                if (self->ext.timer.t) {
                    self->ext.timer.t--;
                    return;
                }
                if (self->posX.i.hi + g_Tilemap.scrollX.i.hi > 0x720) {
                    self->posX.i.hi--;
                    player->posX.i.hi--;
                    if (self->posX.i.hi + g_Tilemap.scrollX.i.hi == 0x720) {
                        g_CastleFlags[NO4_WATER_BLOCKED] = 1;
                    }
                }
                self->ext.timer.t = 3;
            }
        }
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C81C8);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityFloatingIcePlatform);

#define PLAYER g_Entities[PLAYER_CHARACTER]
#define PLAYER_CHARACTER 0
#define SET_UNK_A6 0xA6
#define SFX_WATERFALL_LOOP 1943
#define false 0
#define true 1
extern bool D_us_8018104C;
extern s16 D_us_801814E8[16];
extern EInit g_EInitInteractable;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void func_us_801C4BD8_from_no4(Entity* self) {
    Entity* player;
    s16* dataPtr;
    s32 volume;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
    }

    player = &PLAYER;
    dataPtr = &D_us_801814E8[self->params * 4];

    volume = player->posX.i.hi + g_Tilemap.scrollX.i.hi - *dataPtr++;
    volume = (volume * *dataPtr++) / 0x1000;
    volume += *dataPtr++;

    if (volume < 0) {
        volume = 0;
    } else if (volume > 0x7F) {
        volume = 0x7F;
    }

    if (!volume) {
        if (D_us_8018104C) {
            D_us_8018104C = false;
            g_api_PlaySfx(SET_UNK_A6);
            return;
        }
    }
    if (D_us_8018104C) {
        g_api_SetVolumeCommand22_23(volume, *dataPtr++);
        return;
    }

    g_api_PlaySfxVolPan(SFX_WATERFALL_LOOP, volume, *dataPtr++);
    D_us_8018104C = true;
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8668);

void RNO4_Unused801C8704(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C870C);

void RNO4_Unused801C8768(void) {}

void RNO4_Unused801C8770(void) {}

#define DRAW_HIDE 8
#define DRAW_UNK02 2
#define FLAG_HAS_PRIMS 8388608
#define PRIM_GT4 4
extern u16 D_us_80181508[16];
extern u8 D_us_80181528[2][4];
extern s16 D_us_80181530[12];
extern s16 D_us_80181548[60];
extern EInit g_EInitInteractable;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void EntityBoatElevatorChains(Entity* self) {
    u32 primIndex;
    u32 scrollX;

    u32 scrollY;
    s16 cos;
    u8* ptr;
    s32 i;
    s16* ptrTwo;
    s16 sin;
    s16 xOffset;
    s16 yOffset;
    Primitive* prim;

    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 13);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];

            i = 0;
            while (prim != NULL) {
                prim->tpage = 0xF;
                prim->clut = 0x5F;
                ptr = *D_us_80181528;
                ptr += D_us_80181508[i] * 4;
                prim->u0 = prim->u2 = *ptr++;
                prim->u1 = prim->u3 = *ptr++;
                prim->v0 = prim->v1 = *ptr++;
                prim->v2 = prim->v3 = *ptr;
                prim->priority = 0x80;
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
                i++;
            }
            self->rotate = 0x200;
        } else {
            self->step = 0;
            return;
        }
    }

    if (self->ext.boatElevator_child.unk7C) {
        if (self->ext.boatElevator_child.unk7C < 0) {
            self->ext.boatElevator_child.unk7E++;
            self->rotate += 0x10;
        } else {
            self->ext.boatElevator_child.unk7E--;
            self->rotate -= 0x10;
        }
    }
    self->ext.boatElevator_child.unk7E &= 0xF;
    prim = &g_PrimBuf[self->primIndex];
    i = 0;
    while (prim != NULL) {
        if (i < 3) {
            ptrTwo = &D_us_80181530[(self->params * 6) + (i * 2)];
            xOffset = *ptrTwo++ - scrollX;
            yOffset = *ptrTwo - scrollY;
            if (self->params) {
                sin = (rsin(-self->rotate) * 0x1A) >> 0xC;
                cos = (rcos(-self->rotate) * 0x1A) >> 0xC;
            } else {
                sin = (rsin(self->rotate) * 0x1A) >> 0xC;
                cos = (rcos(self->rotate) * 0x1A) >> 0xC;
            }

            prim->x0 = xOffset - cos;
            prim->x1 = xOffset + sin;
            prim->x2 = xOffset - sin;
            prim->x3 = xOffset + cos;
            prim->y0 = yOffset - sin;
            prim->y1 = yOffset - cos;
            prim->y2 = yOffset + cos;
            prim->y3 = yOffset + sin;
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        } else {
            ptrTwo = &D_us_80181548[(self->params * 3) * 10 + ((i - 3) * 3)];
            sin = *ptrTwo++;
            xOffset = *ptrTwo++ - scrollX;
            yOffset = *ptrTwo - scrollY;
            switch (sin) {
            case 0:
                prim->x0 = prim->x2 = xOffset - 4;
                prim->x1 = prim->x3 = xOffset + 4;
                yOffset += self->ext.boatElevator_child.unk7E;
                prim->y0 = prim->y1 = yOffset;
                prim->y2 = prim->y3 = yOffset + 0x60;
                break;
            case 1:
                prim->x0 = prim->x2 = xOffset - 4;
                prim->x1 = prim->x3 = xOffset + 4;
                yOffset -= self->ext.boatElevator_child.unk7E;
                prim->y0 = prim->y1 = yOffset;
                prim->y2 = prim->y3 = yOffset + 0x60;
                break;
            case 2:
                xOffset -= self->ext.boatElevator_child.unk7E;
                prim->x0 = prim->x1 = xOffset;
                prim->x2 = prim->x3 = xOffset + 0x60;
                prim->y1 = prim->y3 = yOffset - 4;
                prim->y0 = prim->y2 = yOffset + 4;
                break;
            case 3:
                xOffset += self->ext.boatElevator_child.unk7E;
                prim->x0 = prim->x1 = xOffset;
                prim->x2 = prim->x3 = xOffset + 0x60;
                prim->y1 = prim->y3 = yOffset - 4;
                prim->y0 = prim->y2 = yOffset + 4;
                break;
            }
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        }
        i++;
    }
}

void RNO4_Unused801C8BD4(void) {}

void RNO4_Unused801C8BDC(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", LoadFerrymanGateTiles);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8C54);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A071C_from_bo3);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A07CC_from_bo3);

#define PLAYER g_Entities[PLAYER_CHARACTER]
#define PLAYER_CHARACTER 0
extern s16 D_us_801815F8[12];
extern EInit g_EInitInteractable;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void func_us_801C5518_from_no4(Entity* self) {
    Entity* player;
    u16 diff;
    s16* dataPtr;

    player = &PLAYER;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
    }

    dataPtr = &D_us_801815F8[self->params * 4];

    diff = player->posX.i.hi + g_Tilemap.scrollX.i.hi - *dataPtr++;
    if (diff > *dataPtr++) {
        return;
    }
    diff = player->posY.i.hi + g_Tilemap.scrollY.i.hi - *dataPtr++;
    if (diff > *dataPtr++) {
        return;
    }
    if (player->velocityY < 0) {
        player->velocityY *= 7;
        player->velocityY /= 8;
    } else if (player->velocityY > 0) {
        player->nFramesInvincibility = 1;
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C9048);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C909C);

extern s32 D_us_80181698[6];
extern u8 D_us_801816B0[4];
extern u16 D_us_801816B4[4];

void EntityExplosionVariants(Entity* self) {
    if (!self->step) {
        self->velocityY = D_us_80181698[self->ext.destructAnim.index];
        self->flags =
            FLAG_UNK_2000 | FLAG_KEEP_ALIVE_OFFCAMERA | FLAG_POS_CAMERA_LOCKED;
        self->palette = PAL_FLAG(PAL_UNK_195);
        self->animSet = ANIMSET_DRA(2);
        self->animCurFrame = D_us_801816B0[self->params];
        self->blendMode = BLEND_TRANSP;
        self->step++;
    } else {
        self->posY.val -= self->velocityY;
        ++self->poseTimer;
        if ((self->poseTimer % 2) == 0) {
            self->animCurFrame++;
        }

        if (self->poseTimer > D_us_801816B4[self->params]) {
            DestroyEntity(self);
        }
    }
}

extern s16 D_us_80181670[8];
extern s32 D_us_80181680[6];

void EntityGreyPuff(Entity* self) {
    if (!self->step) {
        self->flags =
            FLAG_UNK_2000 | FLAG_KEEP_ALIVE_OFFCAMERA | FLAG_POS_CAMERA_LOCKED;
        self->palette = PAL_FLAG(PAL_UNK_195);
        self->animSet = ANIMSET_DRA(5);
        self->animCurFrame = 1;
        self->blendMode = BLEND_TRANSP;
        self->drawFlags = ENTITY_SCALEX | ENTITY_SCALEY;
        self->scaleX = D_us_80181670[self->params];
        self->scaleY = self->scaleX;
        self->velocityY = D_us_80181680[self->params];
        self->step++;
    } else {
        self->posY.val -= self->velocityY;
        self->poseTimer++;
        if ((self->poseTimer % 2) == 0) {
            self->animCurFrame++;
        }
        if (self->poseTimer > 36) {
            DestroyEntity(self);
        }
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityIntenseExplosion);

int abs(int x);

void PlaySfxPositional(s16 sfxId) {
    s32 posX, posY;
    s16 sfxPan;
    s16 sfxVol;

    posX = g_CurrentEntity->posX.i.hi - 128;
    sfxPan = (abs(posX) - 32) >> 5;
    if (sfxPan > 8) {
        sfxPan = 8;
    } else if (sfxPan < 0) {
        sfxPan = 0;
    }
    if (posX < 0) {
        sfxPan = -sfxPan;
    }
    sfxVol = abs(posX) - 96;
    posY = abs(g_CurrentEntity->posY.i.hi - 128) - 112;
    if (posY > 0) {
        sfxVol += posY;
    }
    if (sfxVol < 0) {
        sfxVol = 0;
    }
    sfxVol = 127 - (sfxVol >> 1);
    if (sfxVol > 0) {
        g_api.PlaySfxVolPan(sfxId, sfxVol, sfxPan);
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakableCrystalFloor);

void EntityBreakableWall(Entity* self) {
    const int WallWidthTiles = 3;
    const int WallHeightTiles = 4;
    const int WallTotalTiles = WallWidthTiles * WallHeightTiles;
    const int ResetTime = 20;
    const int RoomWidthTiles = 16;

    const int startTileIdx = 0x160;

    typedef enum Step {
        INIT = 0,
        IDLE = 1,
        BREAK_1 = 2,  
        BREAK_2 = 3,  
        BREAK_3 = 4,  
        WAIT_FOR_RESET = 8,
    };

    s32 xPos;        
    s32 yPos;        
    s32 newPrimIdx;  
    s32 b;           
    s32 c;           
    s32 tileIdx;     
    s16* pSrcTile;   
    Primitive* prim;
    Entity* entity;

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitSecret);
        self->animCurFrame = 2;
        self->animCurFrame = 0;
        self->hitPoints = 0x20;
        self->hitboxWidth = 24;
        self->hitboxHeight = 32;
        self->hitboxState = 2;

        self->flags |= FLAG_SUPPRESS_STUN;

         
        pSrcTile = BreakableWallTilesCollision;
        if (g_CastleFlags[CHI_SECRET_WALL_OPEN]) {
            pSrcTile += 0xC;  
        }

         
        tileIdx = 0x160;
        for (c = 0; c < WallWidthTiles; tileIdx++, c++) {
             
             
            for (b = 0; b < WallHeightTiles; b++, (s16*)pSrcTile++) {
                *(&g_Tilemap.fg[tileIdx] + b * RoomWidthTiles) = *pSrcTile;
            }
        }

        if (g_CastleFlags[CHI_SECRET_WALL_OPEN]) {
            DestroyEntity(self);
            return;
        }

        newPrimIdx = g_api.AllocPrimitives(PRIM_GT4, 2);
        if (newPrimIdx == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = newPrimIdx;
        prim = &g_PrimBuf[newPrimIdx];

        self->ext.breakableDebris.prim = prim;

         
        xPos = self->posX.i.hi - 23;
        yPos = self->posY.i.hi - 31;

         
        prim->tpage = 0xF;
        prim->clut = 7;
        prim->u0 = prim->u2 = 0x94;
        prim->u1 = prim->u3 = 0xB4;
        prim->v0 = prim->v1 = 0x84;
        prim->v2 = prim->v3 = 0xC4;
        prim->x0 = prim->x2 = xPos;
        xPos += 32;
        prim->x1 = prim->x3 = xPos;
        prim->y0 = prim->y1 = yPos;
        prim->y2 = prim->y3 = yPos + 64;
        prim->priority = 0x6A;
        prim->drawMode = DRAW_UNK02;

         
        prim = prim->next;
        prim->tpage = 0xF;
        prim->clut = 8;
        prim->u0 = prim->u2 = 0xBC;
        prim->u1 = prim->u3 = 0xCC;
        prim->v0 = prim->v1 = 0x84;
        prim->v2 = prim->v3 = 0xC4;
        prim->x0 = prim->x2 = xPos;
        prim->x1 = prim->x3 = xPos + 0x10;
        prim->y0 = prim->y1 = yPos;
        prim->y2 = prim->y3 = yPos + 0x40;
        prim->priority = 0x6A;
        prim->drawMode = DRAW_UNK02;

        pSrcTile = BreakableRoomEntityData;
        entity = self + 1;
         
         
        for (c = 0; c < 15; c++, (Entity*)entity++) {
            DestroyEntity(entity);
            CreateEntityFromEntity(E_ID(BREAKABLE_WALL_DEBRIS), self, entity);

            entity->params = *pSrcTile++;
            entity->posX.i.hi += *pSrcTile++;
            entity->posY.i.hi += *pSrcTile++;
            entity->rotate = *pSrcTile++;
        }
        break;

    case IDLE:
        if (!(self->flags & FLAG_DEAD)) {
            return;
        }
        g_api.PlaySfx(SFX_WALL_DEBRIS_B);

        self->ext.breakableDebris.breakCount++;

        self->flags &= ~FLAG_DEAD;
        self->hitPoints = 0x20;
        self->hitboxWidth -= 8;
        self->hitboxOffX -= 8;

         
        pSrcTile = BreakableWallTilesCollision;
        pSrcTile += 0x18 - self->ext.breakableDebris.breakCount * 4;
        tileIdx = 0x163 - self->ext.breakableDebris.breakCount;
        for (b = 0; b < WallHeightTiles; b++, pSrcTile++) {
            *(&g_Tilemap.fg[tileIdx] + b * RoomWidthTiles) = *pSrcTile;
        }

        entity = self + 1;
        entity += (self->ext.breakableDebris.breakCount - 1) * 5;
        for (c = 0; c < 5; c++, entity++) {
            entity->step++;
        }

         
        xPos = self->posX.i.hi + 0x20;
        yPos = self->posY.i.hi;
        xPos -= self->ext.breakableDebris.breakCount * 0xC;
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->posX.i.hi = xPos;
            entity->posY.i.hi = yPos + 0x10;
            entity->params = 0x13;
            entity->params |= 0xC000;
        }

         
        for (c = 0; c < 3; c++) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, entity);
                entity->posX.i.hi = xPos;
                entity->posY.i.hi = yPos + 0x20 - (Random() & 3) * 8;
                entity->params = 0x10;
                entity->params |= 0xC000;
            }
        }
         
        self->step += self->ext.breakableDebris.breakCount;
        break;

    case BREAK_1:  
        prim = self->ext.breakableDebris.prim;
        prim = prim->next;
        prim->drawMode = DRAW_HIDE;
        self->ext.breakableDebris.resetTimer = ResetTime;
        self->step = WAIT_FOR_RESET;
        break;

    case BREAK_2:  
        prim = self->ext.breakableDebris.prim;
        prim->u1 = prim->u3 -= 0x10;
        prim->x1 = prim->x3 -= 0x10;
        entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
        if (entity != NULL) {
            CreateEntityFromCurrentEntity(E_PERSISTENT_ITEM_DROP, entity);
            entity->posX.i.hi = 0x20 - g_Tilemap.scrollX.i.hi;
            entity->posY.i.hi = 0x188 - g_Tilemap.scrollY.i.hi;
            entity->params = 3;
        }
        self->ext.breakableDebris.resetTimer = ResetTime;
        self->step = WAIT_FOR_RESET;
        break;

    case BREAK_3:  
        prim = self->ext.breakableDebris.prim;
        prim->drawMode = DRAW_HIDE;
        self->hitboxState = 0;
        g_CastleFlags[CHI_SECRET_WALL_OPEN] = 1;
         
         
         
        g_api.RevealSecretPassageAtPlayerPositionOnMap(CHI_SECRET_WALL_OPEN);
        DestroyEntity(self);
        break;

    case WAIT_FOR_RESET:
        if (!--self->ext.breakableDebris.resetTimer) {
            self->step = IDLE;
        }
        break;
    }
}
