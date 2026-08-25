/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:BOSS/BO7:EntityDemonSwitchWall
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/chi/en_demon_switch_wall.c
   target : src/boss/bo7/e_demon_switch_wall.c
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
void MoveEntity();
extern Primitive* FindFirstUnkPrim(Primitive* prim);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* End permuter-seed writer declarations. */

s32 Random(void);

void UpdateFallingPebble(Primitive* prim) {
    const int FallSpeed = 2;
    const int MaxScrolledY = 160;

    s32 newYScrolled;
    u32 rand;

    switch (prim->p3) {
    case 1:  
        rand = (Random() & 1);
        prim->u0 = rand + 1;
        prim->v0 = rand + 1;
        prim->r0 = 0x60;
        prim->g0 = 0x80;
        prim->b0 = 0x30;
        prim->priority = 0xA0;
        prim->drawMode = DRAW_UNK02;
        prim->p2 = (Random() & 0x1F) + 0x10;
        prim->p3 = 2;
         
    case 2:  
        prim->y0 += FallSpeed;
        newYScrolled = g_Tilemap.scrollY.i.hi + prim->y0;
        if (!--prim->p2 || newYScrolled > MaxScrolledY) {
            prim->drawMode = DRAW_HIDE;
            prim->p3 = 0;  
        }
        return;
    }
}

INCLUDE_ASM("boss/bo7/nonmatchings/e_demon_switch_wall", EntityDemonSwitch);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern u8 g_CastleFlags[];
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern Pad g_pads[];

void EntityDemonSwitchWall(Entity* self) {
    typedef enum Step {
        INIT = 0,
        IDLE_CLOSED = 1,
        PREP_TO_OPEN = 2,
        OPENING = 3,
        IDLE_OPEN = 16,  
    };

    s32 tileIdx;
    s16* pSrcTile;
    s32 iRow;
    s32 iCol;
    s32 primIdx;
    Primitive* prim;
    Entity* newEntity;
    s32 remainingColumnCount;
    s32 xPos;
    s32 yPos;

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitSecret);

        self->animCurFrame = 1;  

         
        pSrcTile = WallTiles;
        if (g_CastleFlags[CHI_DEMON_SWITCH]) {
            pSrcTile += 0xC;  
        }

         
        tileIdx = 0x6D;
        for (iCol = 0; iCol < 3; tileIdx++, iCol++) {
            for (iRow = 0; iRow < 4; iRow++, pSrcTile++) {
                *(&g_Tilemap.fg[tileIdx] + iRow * 16) = *pSrcTile;
            }
        }

         
        if (g_CastleFlags[CHI_DEMON_SWITCH]) {
            self->animCurFrame = 0;
            self->step = IDLE_OPEN;
            break;
        }
         
    case IDLE_CLOSED:  
        if (g_CastleFlags[CHI_DEMON_SWITCH]) {
            self->step++;  
        }
        break;
    case PREP_TO_OPEN:  
        primIdx = g_api.AllocPrimitives(PRIM_TILE, 16);
        if (primIdx != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIdx;
            prim = &g_PrimBuf[primIdx];
            self->ext.demonSwitchWall.prim = prim;

            while (prim != NULL) {
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
            }
        } else {
            DestroyEntity(self);
            return;
        }
        self->step++;  
        return;
    case OPENING:  
         
        self->ext.demonSwitchWall.unk80++;
        if (self->ext.demonSwitchWall.unk80 & 1) {
            self->posY.i.hi++;
        } else {
            self->posY.i.hi--;
        }

        if (!(self->ext.demonSwitchWall.unk80 % 8)) {
            g_api.PlaySfx(SFX_WALL_DEBRIS_B);
        }
        MoveEntity();

        if (self->velocityX < FIX(0.25)) {
            self->velocityX += FIX(0.0078125);
        }

         
        prim = self->ext.demonSwitchWall.prim;
        prim = FindFirstUnkPrim(prim);
        if (prim != NULL) {
            prim->p3 = 1;

            xPos = self->posX.i.hi + (Random() & 63) + -24;
            if (xPos > 0x100) {
                xPos -= 0x10;
            }

            yPos = self->posY.i.hi - 0x20;
            prim->x0 = xPos;
            prim->y0 = yPos;
        }

         
        prim = self->ext.demonSwitchWall.prim;
        while (prim != NULL) {
            if (prim->p3) {
                UpdateFallingPebble(prim);
            }
            prim = prim->next;
        }

         
        xPos = self->posX.i.hi - 0x18;
        yPos = self->posY.i.hi + 0x20;
        newEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (newEntity != NULL) {
            CreateEntityFromCurrentEntity(E_ID(GREY_PUFF), newEntity);
            newEntity->posX.i.hi = xPos + (Random() & 0x1F);
            newEntity->posY.i.hi = yPos;
            newEntity->params = Random() & 3;
            newEntity->zPriority = 0xA0;
        }

         
        remainingColumnCount = 0;
        remainingColumnCount = self->posX.i.hi - 0xE8;
        remainingColumnCount >>= 4;
        if (remainingColumnCount > 3) {
            remainingColumnCount = 3;
        }

         
        pSrcTile = WallTiles;
        pSrcTile += 0xC;
        tileIdx = 0x6D;
        for (iCol = 0; iCol < remainingColumnCount; tileIdx++, iCol++) {
            for (iRow = 0; iRow < 4; iRow++, pSrcTile++) {
                *((&g_Tilemap.fg[tileIdx]) + iRow * 16) = *pSrcTile;
            }
        }

         
        if (self->posX.i.hi > 0x128) {
            DestroyEntity(self);
        }
        break;
    case IDLE_OPEN:
        if (g_pads[1].pressed & PAD_SQUARE) {
            if (self->params) {
                break;
            }
            self->animCurFrame++;
            self->params |= 1;  
        } else {
            self->params = 0;
        }

        if (g_pads[1].pressed & PAD_CIRCLE) {
            if (self->step_s) {
                break;
            }
            self->animCurFrame--;
            self->step_s |= 1;  
        } else {
            self->step_s = 0;
        }
        break;
    }
}
