/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:DrawRoof
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

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawFacade);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawSides);

Primitive* DrawRoof(Primitive* prim, u8* indices, u16* arg2) {
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
