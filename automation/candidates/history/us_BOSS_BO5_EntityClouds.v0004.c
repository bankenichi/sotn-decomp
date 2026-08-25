/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:BOSS/BO5:EntityClouds
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/boss/rbo3/e_clouds.c
   target : src/boss/bo5/e_clouds.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

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
void SetRotMatrix(MATRIX* m);
void gte_ldty(s16);
void gte_ldtz(s16);
void gte_ldtx(s16);
void gte_ldv0(SVECTOR* v);
void gte_rtps(void);
void gte_stsxy(long* sxy);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int gte_ldv3c();
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
extern GAME_IMPORT GpuBuffer g_GpuBuffers[2];

void EntityClouds(Entity* self) {
    Primitive* prim;
    Primitive* primTwo;
    MedusaCloudsUVal* uVals;
    u8* var_s4;
    u_long var_s3;
    s32 i;
    s32 j;
    s32 var_s8;
    SVECTOR* vector;

    s32 sp5C;
    s32 sp58;
    s32 priority;
    s32 primIndex;
    s32 posX;
    s32 sp48;
    long sp44;
    MATRIX* matrix;
    u8* sp3C;
    s16* sp38;
    cloudData* cloudData;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        primIndex = g_api.func_800EDB58(PRIM_GT4, 0x60);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.clouds.prim = prim;

        while (prim != NULL) {
            prim->tpage = 0xF;
            prim->clut = 0xC0;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    self->ext.clouds.unk84.val += FIX(1);
    self->ext.clouds.unk8C += FIX(2);
    self->ext.clouds.unk94 += 0;
    self->ext.clouds.unk88 += FIX(5);
    self->ext.clouds.unk90 += FIX(3);
    self->ext.clouds.unk98 += FIX(5);

    g_GpuBuffers[0].draw.r0 = 0x20;
    g_GpuBuffers[0].draw.g0 = 0x10;
    g_GpuBuffers[0].draw.b0 = 0x60;
    g_GpuBuffers[1].draw.r0 = 0x20;
    g_GpuBuffers[1].draw.g0 = 0x10;
    g_GpuBuffers[1].draw.b0 = 0x60;

    matrix = (MATRIX*)SP(0);
    uVals = cloudUVals;
    primTwo = (Primitive*)SP(0x20);

    for (i = 0; i < 7; primTwo++, uVals++, i++) {
        primTwo->tpage = 0xF;
        primTwo->clut = 0xC0;
        LOH(primTwo->u0) = uVals->u0;
        LOH(primTwo->u1) = uVals->u1;
        LOH(primTwo->u2) = uVals->u2;
        LOH(primTwo->u3) = uVals->u3;
    }

    vector = (SVECTOR*)SP(0x1E0);
    vector[0] = cloudVectorOne;
    vector[1] = cloudVectorTwo;
    vector[2] = cloudVectorThree;
    vector[3] = cloudVectorFour;

    var_s4 = (u8*)SP(0x2C0);
    var_s4[3] = 4;
    var_s4[7] = 4;

    SetGeomScreen(0x100);
    SetGeomOffset(0x80, 0x60);
    RotMatrix(&empty, matrix);
    SetRotMatrix(matrix);
    cloudData = data;
    sp38 = &self->ext.clouds.unk84.i.hi;
    prim = self->ext.clouds.prim;

    for (i = 0; i < 3; i++, cloudData++, sp38 += 4) {
        posX = self->posX.i.hi + *sp38;
        posX %= 0x800;
        priority = cloudData->priority;
        var_s3 = cloudData->unk4;
        gte_ldty(var_s3);
        for (sp5C = 0; sp5C < 8; sp5C++) {
            var_s3 = sp5C * 0x100 + 0x1C0;
            sp44 = (u16)sp38[2];
            var_s3 -= sp44 % 0x100;
            gte_ldtz(var_s3);
            sp44 = (sp5C + (sp44 / 0x100)) % 8;
            sp3C = (cloudData->unkPtr + sp44 * 8);
            var_s3 -= 0x1C0;

            var_s8 = FIX(8) - var_s3 * 0xA0;
            var_s4[0] = var_s8 >> 12;
            var_s4[4] = (var_s8 - 0x8000 - 0x2000) >> 12;

            var_s8 = FIX(8) - var_s3 * 0xB0;
            var_s4[1] = var_s8 >> 12;
            var_s4[5] = (var_s8 - 0x8000 - 0x3000) >> 12;

            var_s8 = FIX(8) - (var_s3 << 7);
            var_s4[2] = var_s8 >> 12;
            var_s4[6] = (var_s8 - 0x8000) >> 12;

            sp48 = posX;
            j = 0;
            sp58 = -1;
            while (1) {
                sp48 += sp58 << 8;
                j += sp58;
                j &= 7;
                var_s3 = sp3C[j];
                if (var_s3 == 0) {
                    continue;
                }

                gte_ldtx(sp48);
                gte_ldv0(&vector[3]);
                gte_rtps();
                primTwo = &((Primitive*)(SP(0x20)))[var_s3];
                primTwo->drawMode = DRAW_COLORS;
                gte_stsxy((long*)&primTwo->x3);
                gte_ldv3c(vector);
                gte_rtpt();
                if (primTwo->y3 < 0) {
                    primTwo->drawMode = DRAW_HIDE;
                    break;
                }
                if (primTwo->x3 < 0) {
                    primTwo->drawMode = DRAW_HIDE;
                    if (sp58 < 0) {
                        sp58 += 2;
                        sp48 = posX - 0x100;
                        j = 7;
                    }
                    continue;
                }

                LOW(primTwo->r0) = LOW(primTwo->r1) = LOW(var_s4[0]);
                LOW(primTwo->r2) = LOW(primTwo->r3) = LOW(var_s4[4]);
                primTwo->priority = priority;
                gte_stsxy3_gt3(primTwo);

                if (primTwo->x2 > 0x100) {
                    primTwo->drawMode = DRAW_HIDE;
                    if (sp58 > 0) {
                        break;
                    } else {
                        continue;
                    }
                } else {

                    var_s3 = (u_long)prim->next;
                    *prim = *primTwo;

                    prim->next = (Primitive*)var_s3;
                    prim = prim->next;
                    if (prim == NULL) {
                        return;
                    }
                }
            }
        }
    }

    for (j = 0; prim != NULL; j++, prim = prim->next) {
        prim->drawMode = DRAW_HIDE;
    }
}

