// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/e_elevator", func_us_8019FD4C_from_rcen);

// TWIN PORT from this fork's own src/st/no0/e_elevator.c:37, which is already
// matched. Not an upstream harvest: the donor is in-tree.
//
// A STRAIGHT COPY OF THE DONOR DOES NOT MATCH, and this is the
// CONSTANT_DIVERGENT class asm_twin_finder warns about by name. RNO0's
// elevator shaft sits elsewhere on screen, so every geometry constant differs
// and the branch is inverted. Derived instruction by instruction from
// asm/us/st/rno0/nonmatchings/e_elevator/func_us_801C2044_from_no0.s:
//
//   donor (NO0)                  here (RNO0)          evidence
//   dy -= 0x20                   dy += 0x20           addiu $v0, $a1, 0x20
//   if (dy < 0x44) complex       if (dy >= 0xC0) ..   slti 0xC0 + bnez to the
//                                                     SIMPLE path, so the
//                                                     sense is reversed
//   dy = 0x44 - dy               dy -= 0xC0           addiu $a1, $a1, -0xA0 on
//                                                     the ORIGINAL dy, and
//                                                     -0xA0 == +0x20 - 0xC0
//   y0 = 0x44                    y0 = 0xC0            ori $v0, 0xC0
//   next y0 = 0x2C               next y0 = 0xBC       ori $v0, 0xBC
//   next y2 = 0x3C               next y2 = 0xCC       ori $v0, 0xCC
//   next x1 = posX + dy          next x1 = posX - dy  subu $v0, $v0, $a1
//
// NOT static, though the donor is. Its only caller,
// func_us_801C2184_from_no0, is still INCLUDE_ASM just below, so the assembly
// references this by name and needs external linkage; a static with no visible
// call site is also something the compiler may discard. Binding is the only
// difference and the emitted instructions are identical. Make it static at the
// moment func_us_801C2184_from_no0 is ported too.
s16 func_us_801C2044_from_no0(Primitive* prim, s16 dy) {
    prim->drawMode = DRAW_UNK02;
    prim->u0 = prim->u2 = 0x50;
    prim->u1 = prim->u3 = 0x60;
    prim->x0 = prim->x2 = g_CurrentEntity->posX.i.hi - 8;
    prim->x1 = prim->x3 = g_CurrentEntity->posX.i.hi + 8;
    prim->v2 = prim->v3 = 0x26;
    prim->y2 = prim->y3 = dy;
    dy += 0x20;

    if (dy >= 0xC0) {
        dy -= 0xC0;
        prim->v0 = prim->v1 = dy + 6;
        prim->y0 = prim->y1 = 0xC0;

        prim = prim->next;
        // NOT the chained `prim->v0 = prim->v1 = 0x50` the donor uses, and the
        // split is the whole remaining difference. With the chained form the
        // compiler evaluates `0x22 - dy` three slots earlier and the register
        // allocation moves with it: the copy of dy lands in $v0 instead of $a0,
        // dy+6 in $v1 instead of $v0, and 0x22-dy in $a0 instead of $v1. Eight
        // instructions differ and every one of them is only a register number.
        // Splitting v1 out and storing v0 after the y pair puts the
        // subtraction back where the original has it, at index 39.
        prim->v1 = 0x50;
        prim->y0 = prim->y1 = 0xBC;
        prim->v0 = 0x50;
        prim->v2 = prim->v3 = 0x60;
        prim->u0 = prim->u2 = 0x22 - dy;
        prim->u1 = prim->u3 = 0x22;
        prim->drawMode = DRAW_UNK02;
        prim->y2 = prim->y3 = 0xCC;
        prim->x0 = prim->x2 = g_CurrentEntity->posX.i.hi;
        prim->x1 = prim->x3 = g_CurrentEntity->posX.i.hi - dy;
    } else {
        prim->v0 = prim->v1 = 6;
        prim->y0 = prim->y1 = dy;
    }
    return dy;
}

INCLUDE_ASM("st/rno0/nonmatchings/e_elevator", func_us_801C2184_from_no0);

INCLUDE_ASM("st/rno0/nonmatchings/e_elevator", EntityUnkId1B);
