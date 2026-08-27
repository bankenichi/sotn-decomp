// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

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

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", Entity3DBackgroundHouse);
