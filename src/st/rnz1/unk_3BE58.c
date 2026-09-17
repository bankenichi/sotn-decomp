// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BBE58);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BC650);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCA5C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCB9C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCD80);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCE4C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCFC8);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BD0EC);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define HIH(x) (((s16*)&(x))[1])
#define HIHU(x) (((u16*)&(x))[1])
#define LOH(x) (*(s16*)&(x))
#define LOHU(x) (*(u16*)&(x))
#define LOW(x) (*(s32*)&(x))

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
