/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:BOSS/BO5:EntityStainedGlass
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
void gte_SetRotMatrix(MATRIX* m);
void gte_ldv0(SVECTOR* v);
void gte_rtps(void);
void gte_stsxy(long* sxy);
MATRIX* RotMatrixY(long r, MATRIX* m);
MATRIX* RotMatrixZ(long r, MATRIX* m);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int gte_SetTransVector();
extern int StainedGlassRecurseDepth();
extern int gte_ldv3();
extern int gte_rtpt();
extern int gte_stsxy3_gt3();
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;
extern GameApi g_api;
extern Primitive g_PrimBuf[];

void EntityStainedGlass(Entity* self) {
    s16 midpointX, midpointY;
    s32 primIndex;
    SVECTOR rotVector;
    VECTOR transVector;
    MATRIX mtx;
    u8 transparent;
    s32 iterations;
    s16* yValsPtr;
    VECTOR* paramsPtr;
    CVECTOR* colorPtr;
    s32 count;
    Primitive* glassPrim;
    Primitive* lightPrim;
    Primitive* tempPrim;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 60);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            glassPrim = &g_PrimBuf[primIndex];
            self->ext.stainedGlass.glassPrim = glassPrim;
            for (count = 0; count < 12; count++) {
                glassPrim->tpage = 15;
                glassPrim->clut = PAL_STAINED_GLASS;
                glassPrim->u0 = glassPrim->u2 = 4;
                glassPrim->u1 = glassPrim->u3 = 28;
                glassPrim->v0 = glassPrim->v1 = 1;
                glassPrim->v2 = glassPrim->v3 = 174;
                PGREY(glassPrim, 0) = 96;
                LOW(glassPrim->r1) = LOW(glassPrim->r0);
                LOW(glassPrim->r2) = LOW(glassPrim->r0);
                LOW(glassPrim->r3) = LOW(glassPrim->r0);
                glassPrim->priority = 86;
                glassPrim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_TRANSP;
                glassPrim = glassPrim->next;
            }
            for (self->ext.stainedGlass.lightPrim = glassPrim;
                 glassPrim != NULL; glassPrim = glassPrim->next) {
                glassPrim->drawMode = DRAW_HIDE;
            }
            return;
        }
        DestroyEntity(self);
        return;
    case 1:
        SetGeomScreen(1024);
        SetGeomOffset(128, 160);
        glassPrim = self->ext.stainedGlass.glassPrim;
        lightPrim = self->ext.stainedGlass.lightPrim;
        paramsPtr = params;
        yValsPtr = y_vals;
        colorPtr = colors;
        for (count = 0; count < 12; count++) {
            rotVector.vx = 0;
            rotVector.vy = *yValsPtr;
            rotVector.vz = 0;
            RotMatrix(&rotVector, &mtx);
            transVector = *paramsPtr;
            if (transVector.vx > 0) {
                transparent = true;
                glassPrim->drawMode =
                    DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
            } else {
                transparent = false;
                glassPrim->drawMode = DRAW_COLORS;
            }
            iterations = paramsPtr->pad;
            transVector.vx += self->posX.i.hi - 128;
            transVector.vy += self->posY.i.hi - 160;
            transVector.vz += FLT(0.25);



            gte_SetRotMatrix(&mtx);

            gte_SetTransVector(&transVector);
            CVEC(glassPrim->r0) = *colorPtr;
            LOW(glassPrim->r1) = LOW(glassPrim->r0);
            LOW(glassPrim->r2) = LOW(glassPrim->r0);
            LOW(glassPrim->r3) = LOW(glassPrim->r0);
            glassPrim->type = PRIM_GT4;
            if (iterations) {
                lightPrim = StainedGlassRecurseDepth(
                    &glass_points_0, &glass_points_1, &glass_points_2,
                    &glass_points_3, glassPrim, iterations, lightPrim,
                    (u8*)SP(0));
                glassPrim->drawMode = DRAW_HIDE;
            }
            gte_ldv3(&glass_points_0, &glass_points_1, &glass_points_2);
            gte_rtpt();
            gte_stsxy3_gt3(glassPrim);
            gte_ldv0(&glass_points_3);
            gte_rtps();
            gte_stsxy((long*)&glassPrim->x3);

            if (transparent) {
                tempPrim = lightPrim->next;
                *lightPrim = *glassPrim;
                lightPrim->next = tempPrim;

                lightPrim->clut = PAL_FILL_WHITE;
                lightPrim->priority = glassPrim->priority - 1;
                lightPrim->drawMode = DRAW_COLORS;
                lightPrim->r0 = lightPrim->g0 = lightPrim->b0 = colorPtr->cd;
                LOW(lightPrim->r1) = LOW(lightPrim->r0);
                lightPrim->r2 = lightPrim->g2 = lightPrim->b2 =
                    colorPtr->cd / 2;
                LOW(lightPrim->r3) = LOW(lightPrim->r2);

                lightPrim = lightPrim->next;
                tempPrim = lightPrim->next;
                *lightPrim = *glassPrim;
                lightPrim->next = tempPrim;

                rotVector.vx = 0;
                rotVector.vy = *yValsPtr;
                rotVector.vz = -1024;
                RotMatrix(&light_rot_vector, &mtx);
                RotMatrixY(rotVector.vy, &mtx);
                RotMatrixZ(rotVector.vz, &mtx);
                transVector = *paramsPtr;
                transVector.vx = 96;
                transVector.vy = 256;
                transVector.vx += self->posX.i.hi - 128;
                transVector.vy += self->posY.i.hi - 160;
                transVector.vz += 1024;



                gte_SetRotMatrix(&mtx);

                gte_SetTransVector(&transVector);
                CVEC(lightPrim->r0) = *colorPtr;
                LOW(lightPrim->r1) = LOW(lightPrim->r0);
                LOW(lightPrim->r2) = LOW(lightPrim->r0);
                LOW(lightPrim->r3) = LOW(lightPrim->r0);
                lightPrim->type = PRIM_GT4;
                gte_ldv3(&light_points_0, &light_points_1, &light_points_2);
                gte_rtpt();
                gte_stsxy3_gt3(lightPrim);
                gte_ldv0(&light_points_3);
                gte_rtps();
                gte_stsxy((long*)&lightPrim->x3);
                lightPrim->clut = PAL_STAINED_GLASS_LIGHT;
                lightPrim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                                      DRAW_COLORS | DRAW_TRANSP;
                midpointX = (lightPrim->x0 + lightPrim->x2) / 2;
                midpointY = (lightPrim->y0 + lightPrim->y1) / 2;
                lightPrim = lightPrim->next;
                tempPrim = lightPrim->next;
                *lightPrim = *glassPrim;
                lightPrim->next = tempPrim;
                lightPrim->clut = PAL_FILL_WHITE;
                lightPrim->priority = glassPrim->priority + 1;
                lightPrim->drawMode =
                    DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
                lightPrim->r0 = 24;
                lightPrim->g0 = 8;
                lightPrim->b0 = 32;
                LOW(lightPrim->r1) = LOW(lightPrim->r0);
                lightPrim->r2 = 8;
                lightPrim->g2 = 24;
                lightPrim->b2 = 8;
                lightPrim->r3 = lightPrim->g3 = lightPrim->b3 = 0;
                LOW(lightPrim->x0) = LOW(glassPrim->x1);
                LOW(lightPrim->x1) = LOW(glassPrim->x0);
                LOW(lightPrim->x2) = LOW(glassPrim->x3);
                lightPrim->x3 = midpointX;
                lightPrim->y3 = midpointY;
                lightPrim = lightPrim->next;
            }
            colorPtr++;
            yValsPtr++;
            paramsPtr++;
            glassPrim = glassPrim->next;
        }
        for (count = 0; lightPrim; lightPrim = lightPrim->next) {
            count++;
            lightPrim->drawMode = DRAW_HIDE;
        }
    }
}


INCLUDE_ASM("boss/bo5/nonmatchings/e_stained_glass", EntityStainedGlassBackground);
