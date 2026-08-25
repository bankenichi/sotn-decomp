/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO4:EntityBreakableWallDebris
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/cat/e_secrets.c
   target : src/st/rno4/e_breakable_wall.c
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
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int UnkPolyFunc2();
extern int UnkPrimHelper();
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitParticle;
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityBreakableWallDebris(Entity* self) {
    Collider collider;

    Primitive* prim;
    Primitive* prevPrim;
    Entity* newEntity;
    s32 primIndex;
    s16 posX;
    s16 posY;
    Primitive* nextPrim;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 3);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.segmentedBreakableWall.prim = prim;
            UnkPolyFunc2(prim);
            prim->tpage = 0xB;
            prim->clut = PAL_BREAKABLE_WALL_DEBRIS_MAIN;
            prim->u0 = prim->u2 = D_us_80181518[self->params][0];
            prim->u1 = prim->u3 = prim->u0 + 0xF;
            prim->v2 = prim->v3 = D_us_80181518[self->params][1];
            prim->v0 = prim->v1 = prim->v2 + 0xF;
            prim->next->x1 = self->posX.i.hi;
            prim->next->y0 = self->posY.i.hi;
            LOH(prim->next->r2) = 0x10;
            LOH(prim->next->b2) = 0x10;
            prim->next->b3 = 0x80;
            prim->priority = self->zPriority;
            prim->drawMode = DRAW_DEFAULT;
            prim = prim->next;
            prim = prim->next;

            prim->clut = PAL_BREAKABLE_WALL_DEBRIS_HIGHLIGHT;
            prim->drawMode = DRAW_TPAGE | DRAW_TRANSP;
        } else {
            DestroyEntity(self);
            return;
        }

        break;
    case 1:
        MoveEntity();
        self->velocityY += FIX(0.125);
        prim = self->ext.segmentedBreakableWall.prim;
        posX = prim->next->x1 = self->posX.i.hi;
        posY = prim->next->y0 = self->posY.i.hi;
        UnkPrimHelper(prim);
        prevPrim = prim;
        prim = prim->next;
        prim = prim->next;

        nextPrim = prim->next;
        *prim = *prevPrim;
        prim->next = nextPrim;

        prim->clut = PAL_BREAKABLE_WALL_DEBRIS_HIGHLIGHT;
        prim->y0 -= 2;
        prim->y1 -= 2;
        prim->y2 -= 2;
        prim->y3 -= 2;
        prim->priority -= 1;
        prim->drawMode = DRAW_TPAGE | DRAW_TRANSP;


        posY += 2;
        g_api.CheckCollision(posX, posY, &collider, 0);
        if (collider.effects) {
            self->velocityY = FIX(-1.75);
            self->step++;
        }
        break;
    case 2:
        MoveEntity();
        self->velocityY += FIX(0.125);
        prim = self->ext.segmentedBreakableWall.prim;
        posX = prim->next->x1 = self->posX.i.hi;
        posY = prim->next->y0 = self->posY.i.hi;
        UnkPrimHelper(prim);
        if (self->params > 1) {
            LOH(prim->next->tpage) += 0x10;
        } else {
            LOH(prim->next->tpage) -= 0x10;
        }
        posY += 2;

        prevPrim = prim;
        prim = prim->next;
        prim = prim->next;

        nextPrim = prim->next;
        *prim = *prevPrim;
        prim->next = nextPrim;

        prim->clut = PAL_BREAKABLE_WALL_DEBRIS_HIGHLIGHT;
        prim->y0 -= 2;
        prim->y1 -= 2;
        prim->y2 -= 2;
        prim->y3 -= 2;
        prim->priority -= 1;
        prim->drawMode = DRAW_TPAGE | DRAW_TRANSP;


        g_api.CheckCollision(posX, posY, &collider, 0);
        if (collider.effects) {
            newEntity =
                AllocEntity(&g_Entities[224], &g_Entities[TOTAL_ENTITY_COUNT]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, newEntity);
                newEntity->params = 0x10;
            }
            DestroyEntity(self);
        }
        break;
    }
}

