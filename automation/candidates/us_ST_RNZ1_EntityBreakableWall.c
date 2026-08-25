/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNZ1:EntityBreakableWall
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/chi/en_breakable_wall.c
   target : src/st/rnz1/unk_276A8.c
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
void PlaySfxPositional(s32 arg0);
long ratan2(long y, long x);
int rcos(int a);
int rsin(int a);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
u8 AnimateEntity(u8 frames[], Entity* entity);
void DestroyEntity(Entity*);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
Entity* AllocEntity(Entity* start, Entity* end);
s32 Random();
void CreateEntityFromCurrentEntity(u16, Entity*);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitEnvironment;

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern PlayerState g_Player;
extern GAME_IMPORT Point32 D_8006C38C;
extern unkGraphicsStruct g_unkGraphicsStruct;

void EntityGearSidewaysLarge(Entity* self) {
    Entity* player;
    s16 angle;
    s32 offsetX;
    s32 offsetY;
    s32 collision;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->zPriority = 0x6C;
        self->hitboxState = 1;
        self->hitboxWidth = 8;
        self->hitboxHeight = 3;
        self->animCurFrame = 3;
        self->drawFlags = ENTITY_ROTATE;
        self->ext.gearPuzzle.cooldownTimer = 0x80;


    case 1:
        self->rotate += 8;
        if (!--self->ext.gearPuzzle.cooldownTimer) {
            self->ext.gearPuzzle.cooldownTimer = 0x80;
            PlaySfxPositional(SFX_CLOCK_TOWER_GEAR);
        }

        player = &PLAYER;
        offsetX = player->posX.i.hi;
        offsetY = player->posY.i.hi + 26;
        offsetX -= self->posX.i.hi;
        offsetY -= self->posY.i.hi;
        angle = ratan2(offsetY, offsetX);
        if (angle <= 0) {
            offsetX = rcos(angle) * 54 * 16;
            offsetY = rsin(angle) * 54 * 16;
            self->hitboxOffX = offsetX >> 16;
            self->hitboxOffY = (offsetY >> 16) - 1;

            if (g_Player.status &
                (PLAYER_STATUS_MIST_FORM | PLAYER_STATUS_BAT_FORM)) {
                collision = 0;
            } else {
                collision = GetPlayerCollisionWith(self, 8, 3, 4);
            }

            if (collision & 4) {
                angle += 8;
                offsetX = (rcos(angle) * 54 * 16) - offsetX;
                offsetY = (rsin(angle) * 54 * 16) - offsetY;
                D_8006C38C.x = offsetY;

                player = &PLAYER;
                if (!(g_Player.vram_flag & TOUCHING_R_WALL)) {

                    player->posX.val += offsetX;
                    g_unkGraphicsStruct.shoveX.val += offsetX;
                }
                player->posY.val += offsetY + FIX(3);
                g_unkGraphicsStruct.shoveY.val += offsetY + FIX(3);
                self->ext.gearPuzzle.offsetX = angle;
            }
            self->ext.gearPuzzle.collision = collision;
        }
        break;
    }
}



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern u8 D_us_80180F54[8];

void EntityGearHorizontal(Entity* self) {
    Entity* player;
    s32 collision;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->zPriority = 0x6C;


    case 1:
        AnimateEntity(D_us_80180F54, self);
        collision = GetPlayerCollisionWith(self, 0x20, 8, 4);
        if (collision != 0) {
            player = &PLAYER;
            if (!self->params) {
                if (!(g_Player.vram_flag & TOUCHING_R_WALL)) {
                    player->posX.val += FIX(0.25);
                    g_unkGraphicsStruct.shoveX.val += FIX(0.25);
                }
            } else {
                if (!(g_Player.vram_flag & TOUCHING_L_WALL)) {
                    player->posX.val -= FIX(0.25);
                    g_unkGraphicsStruct.shoveX.val -= FIX(0.25);
                }
            }
        }
        break;
    }
}



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern AnimationFrame D_us_80180F5C[2];

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

void EntityGearVertical(Entity* self) {
    Entity* player;
    s32 collision;
    s32 posY;
    s32 offsetY;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->zPriority = 0x6C;
        self->drawFlags = ENTITY_ROTATE;
        self->rotate = 0x400;


    case 1:
        AnimateEntity(D_us_80180F5C, self);
#ifdef VERSION_PSP
        collision = GetPlayerCollisionWith(self, 8, 0x20, 5);
#else
        if (g_Player.vram_flag & (TOUCHING_L_WALL | TOUCHING_R_WALL)) {
            collision = 4;
        } else {
            collision = 5;
        }
        collision = GetPlayerCollisionWith(self, 8, 0x20, collision | 0x8);
#endif
        self->ext.gearPuzzle.cooldownTimer = 0x20;
        if (collision & 4) {
            self->step++;
        }
        break;

    case 2:
        AnimateEntity(&D_us_80180F5C, self);
#ifndef VERSION_PSP
        collision = 0;
#endif
        self->ext.gearPuzzle.cooldownTimer--;
        if (!self->ext.gearPuzzle.cooldownTimer) {
            self->ext.gearPuzzle.timer2 = 0x20;
            self->step = 3;
        } else {
            player = &PLAYER;
            if (self->ext.gearPuzzle.collision & 4) {
                posY = self->posY.i.hi + g_Tilemap.scrollY.i.hi -
                       self->ext.gearPuzzle.cooldownTimer;
                offsetY = posY - self->ext.gearPuzzle.offsetY;
                player->posY.i.hi += offsetY;
                g_unkGraphicsStruct.shoveY.val += offsetY;
            }
#ifdef VERSION_PSP
            collision = GetPlayerCollisionWith(
                self, 8, self->ext.gearPuzzle.cooldownTimer, 5);
#else
            if (g_Player.vram_flag & (TOUCHING_L_WALL | TOUCHING_R_WALL)) {
                collision = 4;
            } else {
                collision = 5;
            }
            collision = GetPlayerCollisionWith(
                self, 8, self->ext.gearPuzzle.cooldownTimer, collision | 0x8);
#endif
            if (!(collision & 4)) {
                self->ext.gearPuzzle.timer2 = 0x10;
                self->step = 3;
            }
        }
        break;

    case 3:
        AnimateEntity(&D_us_80180F5C, self);
        collision = 0;

        if (!--self->ext.gearPuzzle.timer2) {
            self->step = 1;
        }
        break;
    }
    self->ext.gearPuzzle.collision = collision;
    self->ext.gearPuzzle.offsetY = self->posY.i.hi + g_Tilemap.scrollY.i.hi -
                                   self->ext.gearPuzzle.cooldownTimer;
}



INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern u8 g_CastleFlags[];
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

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


INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitInteractable;
extern s16 D_us_80181024[7][4];

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Primitive g_PrimBuf[];

void EntityWaterForeground(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s16* ptr;
    s32 x, y;
    s32 params;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        primIndex = g_api_AllocPrimitives(PRIM_TILE, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.prim = prim;
        prim->r0 = 0x48;
        prim->g0 = 0x40;
        prim->b0 = 0xC0;
        params = self->params;
        ptr = (s16*)D_us_80181024[params];
        x = ptr[0] - g_Tilemap.scrollX.i.hi;
        y = ptr[1] - g_Tilemap.scrollY.i.hi;
        prim->x0 = x;
        prim->y0 = y;
        prim->u0 = ptr[2];
        prim->v0 = ptr[3];
        prim->priority = 0x9A;
        prim->drawMode = DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;
        break;
    case 1:
        break;
    }
}


