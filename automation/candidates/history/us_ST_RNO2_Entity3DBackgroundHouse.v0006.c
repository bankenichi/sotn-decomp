/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO2:Entity3DBackgroundHouse
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_background_house.h
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
long NormalClip(long sxy0, long sxy1, long sxy2);
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
void SetGeomScreen(long h);
void SetGeomOffset(long ofx, long ofy);
MATRIX* RotMatrix(SVECTOR* r, MATRIX* m);
MATRIX* TransMatrix(MATRIX* m, VECTOR* v);
void SetRotMatrix(MATRIX* m);
void SetTransMatrix(MATRIX* m);
long RotTransPers3(SVECTOR* v0, SVECTOR* v1, SVECTOR* v2, long* sxy0,
                   long* sxy1, long* sxy2, long* p, long* flag);
long RotTransPers(SVECTOR*, long*, long*, long*);
/* End permuter-seed writer declarations. */

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define LOW(x) (*(s32*)&(x))
#define SPAD(x) ((s32*)SP((x) * sizeof(s32)))
#define SP(x) (SCRATCH_PAD + (x))
#define SCRATCH_PAD 0x1F800000

static Primitive* DrawFacade(Primitive* prim, u8* indices, u16* arg2) {
    s32 p0;
    s32 p1;
    s32 p2;
    s32 p3;
    s32 p4;
    s32 clip;

    p0 = *SPAD(indices[0]);
    p1 = *SPAD(indices[1]);
    p2 = *SPAD(indices[2]);
    clip = NormalClip(p0, p1, p2);
    if (clip <= 0) {
        return prim;
    }
    p3 = *SPAD(indices[3]);
    p4 = *SPAD(indices[4]);

    prim->tpage = 0xF;
    prim->clut = arg2[0];
    prim->u0 = prim->u2 = 4;
    prim->u1 = prim->u3 = 0x7C;
    prim->v0 = prim->v1 = 3;
    prim->v2 = prim->v3 = 0x9E;
    LOW(prim->x0) = p0;
    LOW(prim->x1) = p1;
    LOW(prim->x2) = p2;
    LOW(prim->x3) = p3;
    prim->drawMode = DRAW_UNK02;
    prim->drawMode |= DRAW_COLORS;
    prim->r0 = prim->g0 = prim->b0 = arg2[1];
    LOW(prim->r1) = LOW(prim->r0);
    LOW(prim->r2) = LOW(prim->r0);
    LOW(prim->r3) = LOW(prim->r0);
    prim = prim->next;

    prim->tpage = 0xF;
    prim->clut = arg2[0];
    prim->u0 = 0xFE;
    prim->u1 = 0xC2;
    prim->u2 = 0xC2;
    prim->u3 = 0xFE;
    prim->v0 = 0xAC;
    prim->v1 = 0x6C;
    prim->v2 = 0xAC;
    prim->v3 = 0xAC;
    LOW(prim->x0) = p0;
    LOW(prim->x3) = p1;
    LOW(prim->x1) = p4;

    prim->x2 = (prim->x0 + prim->x3) / 2;
    prim->y2 = (prim->y0 + prim->y3) / 2;

    prim->drawMode = DRAW_UNK02;
    prim->drawMode |= DRAW_COLORS;
    prim->r0 = prim->g0 = prim->b0 = arg2[1];
    LOW(prim->r1) = LOW(prim->r0);
    LOW(prim->r2) = LOW(prim->r0);
    LOW(prim->r3) = LOW(prim->r0);
    prim = prim->next;
    return prim;
}


/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define HIH(x) (((s16*)&(x))[1])
#define LOH(x) (*(s16*)&(x))
#define LOW(x) (*(s32*)&(x))
#define SPAD(x) ((s32*)SP((x) * sizeof(s32)))
#define SP(x) (SCRATCH_PAD + (x))
#define SCRATCH_PAD 0x1F800000

static Primitive* DrawSides(Primitive* prim, u8* indices, u16* arg2) {
    s32 p0;
    s32 p1;
    s32 p2;
    s32 p3;
    s32 clip;
    s16 avg1;
    s16 avg2;
    s16 avg3;
    s16 avg4;

    p0 = *SPAD(indices[0]);
    p1 = *SPAD(indices[1]);
    p2 = *SPAD(indices[2]);
    clip = NormalClip(p0, p1, p2);
    if (clip <= 0) {
        return prim;
    }
    p3 = *SPAD(indices[3]);

    prim->tpage = 0xF;
    prim->clut = arg2[0];
    prim->u0 = prim->u2 = 4;
    prim->u1 = prim->u3 = 0x7C;
    prim->v0 = prim->v1 = 3;
    prim->v2 = prim->v3 = 0x9E;
    LOW(prim->x0) = p0;
    LOW(prim->x2) = p2;
    avg1 = (LOH(p0) + LOH(p1)) / 2;
    prim->x1 = avg1;
    avg2 = (LOH(p2) + LOH(p3)) / 2;
    prim->x3 = avg2;
    avg3 = (HIH(p0) + HIH(p1)) / 2;
    prim->y1 = avg3;
    avg4 = (HIH(p2) + HIH(p3)) / 2;
    prim->y3 = avg4;
    prim->drawMode = DRAW_UNK02;
    prim->drawMode |= DRAW_COLORS;
    prim->r0 = prim->g0 = prim->b0 = arg2[2];
    LOW(prim->r1) = LOW(prim->r0);
    LOW(prim->r2) = LOW(prim->r0);
    LOW(prim->r3) = LOW(prim->r0);
    prim = prim->next;

    prim->tpage = 0xF;
    prim->clut = arg2[0];
    prim->u0 = prim->u2 = 4;
    prim->u1 = prim->u3 = 0x7C;
    prim->v0 = prim->v1 = 3;
    prim->v2 = prim->v3 = 0x9E;
    LOW(prim->x1) = p1;
    LOW(prim->x3) = p3;
    prim->x0 = avg1;
    prim->x2 = avg2;
    prim->y0 = avg3;
    prim->y2 = avg4;
    prim->drawMode = DRAW_UNK02;
    prim->drawMode |= DRAW_COLORS;
    prim->r0 = prim->g0 = prim->b0 = arg2[2];
    LOW(prim->r1) = LOW(prim->r0);
    LOW(prim->r2) = LOW(prim->r0);
    LOW(prim->r3) = LOW(prim->r0);
    prim = prim->next;
    return prim;
}


/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define LOW(x) (*(s32*)&(x))
#define SPAD(x) ((s32*)SP((x) * sizeof(s32)))
#define SP(x) (SCRATCH_PAD + (x))
#define SCRATCH_PAD 0x1F800000

static Primitive* DrawRoof(Primitive* prim, u8* indices, u16* arg2) {
    s32 p0;
    s32 p1;
    s32 p2;
    s32 clip;
    s32 i;

    p0 = *SPAD(indices[0]);
    p1 = *SPAD(indices[1]);
    p2 = *SPAD(indices[2]);
    clip = NormalClip(p0, p1, p2);
    if (clip <= 0) {
        return prim;
    }
    indices += 4;
    for (i = 0; i < 4; i++) {
        prim->tpage = 0xF;
        prim->clut = arg2[0];
        prim->u0 = prim->u2 = 0x82;
        prim->u1 = prim->u3 = 0xBE;
        prim->v0 = prim->v1 = 0x6C;
        prim->v2 = prim->v3 = 0xA4;
        LOW(prim->x0) = *SPAD(indices[0]);
        LOW(prim->x1) = *SPAD(indices[1]);
        LOW(prim->x2) = *SPAD(indices[2]);
        LOW(prim->x3) = *SPAD(indices[3]);
        indices += 4;
        prim->drawMode = DRAW_UNK02;
        prim->drawMode |= DRAW_COLORS;
        prim->r0 = prim->g0 = prim->b0 = arg2[1];
        LOW(prim->r1) = LOW(prim->r0);
        LOW(prim->r2) = LOW(prim->r0);
        LOW(prim->r3) = LOW(prim->r0);
        prim = prim->next;
    }
    return prim;
}


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
        // These seem to be unused?
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
        SetGeomOffset(0x80, BG_HOUSE_GEOM_Y);
        // this is a 7-by-X array, so params picks a set of 7 values
        modelData = backgroundHouseModelData;
        // Params is 0 or 1. 0 if house is straight, 1 if rotated 90 degree.
        modelData += self->params * 7;
        rot.vx = 0;
        rot.vy = *modelData++;
        rot.vz = BG_HOUSE_ROT_Z;
        RotMatrix(&rot, &m);
        trans.vx = self->posX.i.hi - 0x80;
        trans.vy = self->posY.i.hi - BG_HOUSE_GEOM_Y;
        trans.vz = *modelData++ + 0x400;
        TransMatrix(&m, &trans);
        SetRotMatrix(&m);
        SetTransMatrix(&m);
        vPtr = backgroundHouseVertices;
        scratchpad = SPAD(0);
        for (i = 0; i < 6; i++) {
            RotTransPers3(vPtr[0], vPtr[1], vPtr[2], &scratchpad[0],
                          &scratchpad[1], &scratchpad[2], &p, &flag);
            vPtr += 3;
            scratchpad += 3;
        }
        RotTransPers(vPtr[0], (long*)scratchpad, &p, &flag);
        prim = self->ext.bghouse.prim;
        iPtr = backgroundHouseFacadeIndices;
        for (i = 0; i < 2; i++) {
            prim = DrawFacade(prim, iPtr, (u16*)modelData);
            iPtr += 5;
        }
        iPtr = backgroundHouseSideIndices;
        for (i = 0; i < 2; i++) {
            prim = DrawSides(prim, iPtr, (u16*)modelData);
            iPtr += 4;
        }
        modelData += 3;
        iPtr = backgroundHouseRoofIndices;
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
