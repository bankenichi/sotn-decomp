/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:BOSS/BO7:EntityBreakableWall
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/chi/en_breakable_wall.c
   target : src/boss/bo7/e_breakable_wall.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
Entity* AllocEntity(Entity* start, Entity* end);
s32 Random();
void CreateEntityFromCurrentEntity(u16, Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/bo7/nonmatchings/e_breakable_wall", EntityBreakableWallDebris);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern u8 g_CastleFlags[];
extern Tilemap g_Tilemap;
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

