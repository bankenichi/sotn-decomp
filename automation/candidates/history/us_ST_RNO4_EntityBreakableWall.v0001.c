/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntityBreakableWall
   source : upstream/master:src/st/chi/en_breakable_wall.c
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
void InitializeEntity(u16 arg0[]);
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

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityWaterBox);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C81C8);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityFloatingIcePlatform);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C4BD8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8668);

void RNO4_Unused801C8704(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C870C);

void RNO4_Unused801C8768(void) {}

void RNO4_Unused801C8770(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBoatElevatorChains);

void RNO4_Unused801C8BD4(void) {}

void RNO4_Unused801C8BDC(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", LoadFerrymanGateTiles);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8C54);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A071C_from_bo3);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A07CC_from_bo3);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5518_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C9048);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C909C);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityExplosionVariants);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityGreyPuff);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityIntenseExplosion);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", PlaySfxPositional);

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
