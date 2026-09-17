/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNZ1:func_us_801BD184
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rnz1/e_crusher.c
   target : src/st/rnz1/unk_3BE58.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
s32 Random();
int rcos(int a);
int rsin(int a);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BBE58);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BC650);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCA5C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCB9C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCD80);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCE4C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCFC8);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BD0EC);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void func_us_801BD184(Primitive* prim) {
    u32 x;
    u32 y;
    s32 length;
    s16 angle;

    switch (prim->p1) {
    case 0:
        prim->r0 = 0x80;
        prim->g0 = 0x80;
        prim->b0 = 0xC0;
        prim->drawMode = DRAW_UNK02;
        prim->x1 = 0;
        prim->y1 = 0;
        prim->y0 = g_CurrentEntity->posY.i.hi + 0xC;
        length = (Random() & 0x1F) + 0x20;
        angle = (Random() * 6) + 0x900;
        LOW(prim->x2) = length * rcos(angle);
        LOW(prim->x3) = length * rsin(angle);
        prim->p1 = 1;
        prim->r3 = 0x10;
        /* fallthrough */
    case 1:

        x = (prim->x0 << 0x10) + (u16)prim->x1;



        x += LOW(prim->x2);
        prim->x0 = HIHU(x);
        prim->x1 = LOHU(x);

        y = (prim->y0 << 0x10) + (u16)prim->y1;



        y += LOW(prim->x3);
        prim->y0 = HIH(y);
        prim->y1 = LOH(y);
        LOW(prim->x3) += 0x2000;
        prim->r0 -= 5;
        prim->g0 -= 5;
        prim->b0 -= 9;
        prim->r3 -= 1;
        if (!prim->r3) {
            prim->drawMode = DRAW_HIDE;
            prim->p3 = 0;
        }
    }
}


// Grindy crushy platform things.
// params 0 = one-wide, params 1 = three-wide
INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BD324);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BD398);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BDA24);
