/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO5:EntityStainedGlassBackground
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/dai/e_stained_glass.c
   target : src/boss/bo5/e_stained_glass.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

#include "../../st/e_stained_glass_blend.h"

extern s16 indices[];

#include "../../st/e_stained_glass_recurse.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
void SetGeomScreen(long h);
void SetGeomOffset(long ofx, long ofy);
MATRIX* RotMatrix(SVECTOR* r, MATRIX* m);
void gte_ldv0(SVECTOR* v);
void gte_rtps(void);
void gte_stsxy(long* sxy);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int StainedGlassBlendPalette();
extern int gte_SetTransVector();
extern int gte_ldv3();
extern int gte_rtpt();
extern int gte_stsxy3();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/bo5/nonmatchings/e_stained_glass", EntityStainedGlass);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GAME_IMPORT GpuBuffer g_GpuBuffers[2];
extern EInit g_EInitInteractable;
extern GameApi g_api;
extern Primitive g_PrimBuf[];

void EntityStainedGlassBackground(Entity* self) {
 
#ifdef VERSION_PSP
    RECT rect2, rect1;
#endif

    VECTOR transVector;
    MATRIX mtx;
    RECT rect;
    CVECTOR color;

 
#ifndef VERSION_PSP
     
    RECT rect1, rect2;
    s32 tempRect2w, tempRect2x;
    s32 tempRect1w, tempRect1x;
#endif

    s32 primIndex;
    VECTOR* transVectorPtr;
    s32 midindex1, midindex2;
    s32 idx;
    Primitive* prim;
    s16 tempY, tempX;

    g_GpuBuffers[0].draw.r0 = 24;
    g_GpuBuffers[0].draw.g0 = 24;
    g_GpuBuffers[0].draw.b0 = 24;
    g_GpuBuffers[1].draw.r0 = 24;
    g_GpuBuffers[1].draw.g0 = 24;
    g_GpuBuffers[1].draw.b0 = 24;
    switch (self->step) {
    case 0:  
        InitializeEntity(g_EInitInteractable);
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 19);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            for (self->ext.stainedGlass.glassPrim = prim; prim != NULL;
                 prim = prim->next) {
                prim->tpage = 15;
                prim->clut = PAL_STAINED_GLASS_BG;
                prim->u0 = prim->u2 = 35;
                prim->u1 = prim->u3 = 92;
                prim->v0 = prim->v1 = 1;
                prim->v2 = prim->v3 = 62;
                PGREY(prim, 0) = 128;
                LOW(prim->r1) = LOW(prim->r0);
                LOW(prim->r2) = LOW(prim->r0);
                LOW(prim->r3) = LOW(prim->r0);
                prim->priority = 84;
                prim->drawMode = DRAW_DEFAULT;
            }
            for (prim = self->ext.stainedGlass.glassPrim, idx = 0; idx < 4;
                 prim = prim->next, idx++) {
                prim->clut = 5;
                prim->u0 = prim->u2 = 129;
                prim->u1 = prim->u3 = 174;
                prim->v0 = prim->v1 = 1;
                prim->v2 = prim->v3 = 126;
                prim->priority = 80;
            }
            prim = self->ext.stainedGlass.glassPrim;
            PGREY(prim, 0) = 32;
            PGREY(prim, 1) = 48;
            PGREY(prim, 2) = 64;
            PGREY(prim, 3) = 48;
            prim = prim->next;
            prim->clut = PAL_FILL_WHITE;
            PGREY(prim, 0) = 24;
            PGREY(prim, 1) = 24;
            PGREY(prim, 2) = 24;
            PGREY(prim, 3) = 24;
            prim->priority = 81;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
            PGREY(prim, 0) = 80;
            PGREY(prim, 1) = 48;
            PGREY(prim, 2) = 160;
            PGREY(prim, 3) = 48;
            prim = prim->next;
            prim->clut = PAL_FILL_WHITE;
            prim->r0 = 24;
            prim->g0 = 24;
            prim->b0 = 24;
            prim->r2 = 24;
            prim->g2 = 24;
            prim->b2 = 24;
            PGREY(prim, 1) = 24;
            PGREY(prim, 3) = 24;
            prim->priority = 81;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
            prim->type = PRIM_G4;
            prim->r0 = 64;
            prim->g0 = 24;
            prim->b0 = 72;
            LOW(prim->r1) = LOW(prim->r0);
            prim->r2 = 200;
            prim->g2 = 24;
            prim->b2 = 104;
            LOW(prim->r2) = LOW(prim->r3);
            prim->priority = 82;
            prim->drawMode = DRAW_COLORS | DRAW_UNK02;
        } else {
            DestroyEntity(self);
            return;
        }
        rect.x = 0;
        rect.y = 256;
        rect.w = 16;
        rect.h = 1;
        color.r = 24;
        color.g = 24;
        color.b = 24;
        StainedGlassBlendPalette(
            &rect, PAL_STAINED_GLASS_BG, PAL_STAINED_GLASS_BG_LIGHT,
            COLORS_PER_PAL, &color);
        break;
    case 1:  
        SetGeomScreen(1024);
        SetGeomOffset(128, 160);
        prim = self->ext.stainedGlass.glassPrim;
        for (transVectorPtr = trans_vectors, idx = 0; idx < 8; idx++,
            transVectorPtr++) {
            RotMatrix(&bg_rot_vector, &mtx);
            transVector = *transVectorPtr;
            transVector.vx += self->posX.i.hi - 128;
            transVector.vy += self->posY.i.hi - 160;
            transVector.vz += 1024;
            SETROTMATRIX(&mtx);
            gte_SetTransVector(&transVector);
            if (idx == 0) {
                gte_ldv0(&bg_pos_vector);
                gte_rtps();
#ifdef VERSION_PSP
                gte_stsxy((long*)&rect2.w);
                tempX = (u16)LOW(rect2.w);
                tempY = LOW(rect2.w) >> 16;
#else
                gte_stsxy((long*)&rect1.x);
                prim->drawMode = DRAW_COLORS;
                tempX = rect1.x;
                tempY = LOW(rect1.x) >> 16;
#endif

                prim->x0 = prim->x2 = tempX - 45;
                prim->x1 = prim->x3 = tempX;
                prim->y0 = prim->y1 = tempY - 62;
                prim->y2 = prim->y3 = tempY + 62;
#ifdef VERSION_PSP
                prim->drawMode = DRAW_COLORS;
#endif
                prim = prim->next;
                prim->x0 = prim->x2 = tempX - 45;
                prim->x1 = prim->x3 = tempX;
                prim->y0 = prim->y1 = tempY - 62;
                prim->y2 = prim->y3 = tempY + 62;
                prim->drawMode = DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
                prim = prim->next;
                prim->x0 = prim->x2 = tempX + 45;
                prim->x1 = prim->x3 = tempX;
                prim->y0 = prim->y1 = tempY - 62;
                prim->y2 = prim->y3 = tempY + 62;
                prim->drawMode = DRAW_COLORS;
                prim = prim->next;
                prim->x0 = prim->x2 = tempX + 45;
                prim->x1 = prim->x3 = tempX;
                prim->y0 = prim->y1 = tempY - 62;
                prim->y2 = prim->y3 = tempY + 62;
                prim->drawMode = DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
                prim = prim->next;
                prim->x0 = tempX - 8;
                prim->x1 = tempX + 8;
                prim->x2 = self->posX.i.hi - 24;
                prim->x3 = self->posX.i.hi + 24;
                prim->y0 = prim->y1 = tempY + 56;
                prim->y2 = prim->y3 = self->posY.i.hi + 194;
                prim->drawMode = DRAW_COLORS;
                prim = prim->next;
            } else {
                gte_ldv3(&bg_points_0, &bg_points_1, &bg_points_2);
                gte_rtpt();
#ifdef VERSION_PSP
                gte_stsxy3(&rect2.w, &rect2.x, &rect1.w);
                if (rect1.h >= 0) {
#else
                gte_stsxy3(&rect1.x, &rect1.w, &rect2.x);
                if (rect2.y >= 0) {
#endif
                    gte_ldv0(&bg_points_3);
                    gte_rtps();

 
 
#ifdef VERSION_PSP
                    gte_stsxy((long*)&rect1.x);
                    midindex1 =
                        ((LOW(rect2.w) + LOW(rect2.x)) / 2) & 0xFFFF0000;
                    midindex1 |= (rect2.w + rect2.x) >> 1;
                    midindex2 =
                        (((LOW(rect1.w) + LOW(rect1.x)) / 2) & 0xFFFF0000);
                    midindex2 |= ((rect1.w + rect1.x) >> 1);
                    prim->clut = ((idx * 2) + PAL_STAINED_GLASS_BG_LIGHT);
                    LOW(prim->x0) = LOW(rect2.w);
                    LOW(prim->x1) = midindex1;
                    LOW(prim->x2) = LOW(rect1.w);
                    LOW(prim->x3) = midindex2;
                    prim->drawMode = DRAW_DEFAULT;
                    prim = prim->next;
                    prim->clut = ((idx * 2) + PAL_STAINED_GLASS_BG_LIGHT);
                    LOW(prim->x0) = LOW(rect2.x);
                    LOW(prim->x1) = midindex1;
                    LOW(prim->x2) = LOW(rect1.x);
                    LOW(prim->x3) = midindex2;
                    prim->drawMode = DRAW_DEFAULT;
                    prim = prim->next;
#else
                    gte_stsxy((long*)&rect2.w);
                    tempRect1x = LOW(rect1.x);
                    tempRect1w = LOW(rect1.w);
                    prim->clut = ((idx * 2) + PAL_STAINED_GLASS_BG_LIGHT);
                    prim->drawMode = DRAW_DEFAULT;
                    tempRect2x = LOW(rect2.x);
                    tempRect2w = LOW(rect2.w);
                    midindex1 = ((tempRect1x + tempRect1w) / 2) & 0xFFFF0000;
                    midindex1 |= (rect1.x + rect1.w) >> 1;
                    midindex2 = (((tempRect2x + tempRect2w) / 2) & 0xFFFF0000);
                    midindex2 |= ((rect2.x + rect2.w) >> 1);
                    LOW(prim->x0) = tempRect1x;
                    LOW(prim->x1) = midindex1;
                    LOW(prim->x2) = tempRect2x;
                    LOW(prim->x3) = midindex2;
                    prim = prim->next;
                    prim->clut = ((idx * 2) + PAL_STAINED_GLASS_BG_LIGHT);
                    LOW(prim->x0) = tempRect1w;
                    LOW(prim->x1) = midindex1;
                    LOW(prim->x2) = tempRect2w;
                    LOW(prim->x3) = midindex2;
                    prim->drawMode = DRAW_DEFAULT;
                    prim = prim->next;
#endif
                }
            }
        }
        for (; prim != NULL; prim = prim->next) {
            prim->drawMode = DRAW_HIDE;
        }
        break;
    }
}

