/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO2:Entity3DBackgroundHouse
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_background_house.h
   target : src/st/rno2/e_background_house.c
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
void SetGeomScreen(long h);
void SetGeomOffset(long ofx, long ofy);
MATRIX* RotMatrix(SVECTOR* r, MATRIX* m);
MATRIX* TransMatrix(MATRIX* m, VECTOR* v);
void SetRotMatrix(MATRIX* m);
void SetTransMatrix(MATRIX* m);
long RotTransPers(SVECTOR*, long*, long*, long*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int DrawFacade();
extern int DrawRoof();
extern int DrawSides();
extern int RotTransPers3();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawFacade);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawSides);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawRoof);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", Entity3DHouseSpawner);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;
extern GameApi g_api;
extern Primitive g_PrimBuf[];

void Entity3DBackgroundHouse(Entity* self) {
    long p, flag;
    SVECTOR rot;
    VECTOR trans;
    MATRIX m;
    Primitive* prim;
    s32 primIndex;
    s16* modelData;
    s32 i;
    SVECTOR** vPtr;
    s32* scratchpad;
    u8* iPtr;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 16);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.bghouse.prim = prim;
            while (prim != NULL) {
                prim->tpage = 0xF;
                prim->priority = 0x58 - self->params;
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
            }
        } else {
            DestroyEntity(self);
            return;
        }

        self->ext.bghouse.unk80 = 0x80;
        self->ext.bghouse.unk82 = 0x80;
        self->ext.bghouse.unk84 = 0x80;
        break;

    case 1:
        if (self->posX.i.hi > 0x200 || self->posX.i.hi < -0x200) {
            prim = self->ext.bghouse.prim;
            while (prim != NULL) {
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
            }
            return;
        }
        prim = self->ext.bghouse.prim;
        SetGeomScreen(0x400);
        SetGeomOffset(128, 192);

        modelData = D_us_80180CD8;

        modelData += self->params * 7;
        rot.vx = 0;
        rot.vy = *modelData++;
        rot.vz = 0;
        RotMatrix(&rot, &m);
        trans.vx = self->posX.i.hi - 0x80;
        trans.vy = self->posY.i.hi - 0xC0;
        trans.vz = *modelData++ + 0x400;
        TransMatrix(&m, &trans);
        SetRotMatrix(&m);
        SetTransMatrix(&m);
        vPtr = vertices;
        scratchpad = SPAD(0);
        for (i = 0; i < 6; i++) {
            RotTransPers3(vPtr[0], vPtr[1], vPtr[2], &scratchpad[0],
                          &scratchpad[1], &scratchpad[2], &p, &flag);
            vPtr += 3;
            scratchpad += 3;
        }
        RotTransPers(vPtr[0], (long*)scratchpad, &p, &flag);
        prim = self->ext.bghouse.prim;
        iPtr = facadeIndices;
        for (i = 0; i < 2; i++) {
            prim = DrawFacade(prim, iPtr, (u16*)modelData);
            iPtr += 5;
        }
        iPtr = sideIndices;
        for (i = 0; i < 2; i++) {
            prim = DrawSides(prim, iPtr, (u16*)modelData);
            iPtr += 4;
        }
        modelData += 3;
        iPtr = roofIndices;
        for (i = 0; i < 2; i++) {
            prim = DrawRoof(prim, iPtr, (u16*)modelData);
            iPtr += 20;
        }
        while (prim != NULL) {
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
        break;
    }
}

