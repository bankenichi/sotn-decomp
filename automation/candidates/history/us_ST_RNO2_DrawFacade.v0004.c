/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO2:DrawFacade
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
long NormalClip(long sxy0, long sxy1, long sxy2);
/* End permuter-seed writer declarations. */

Primitive* DrawFacade(Primitive* prim, u8* indices, u16* arg2) {
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


INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawSides);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawRoof);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", Entity3DHouseSpawner);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", Entity3DBackgroundHouse);
