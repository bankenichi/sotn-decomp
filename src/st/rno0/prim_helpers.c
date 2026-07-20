// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/prim_helpers", UnkPrimHelper);

INCLUDE_ASM("st/rno0/nonmatchings/prim_helpers", UpdateAnimation);

// Traverse linked list of primitives and return the first one with p3 == 0
// (likely an unused/inactive primitive slot)
Primitive* FindFirstUnkPrim(Primitive* prim) {
    while (prim != NULL) {
        if (prim->p3 == 0) {
            return prim;
        }
        prim = prim->next;
    }

    return NULL;
}

INCLUDE_ASM("st/rno0/nonmatchings/prim_helpers", FindFirstUnkPrim2);

INCLUDE_ASM("st/rno0/nonmatchings/prim_helpers", PrimToggleVisibility);

INCLUDE_ASM("st/rno0/nonmatchings/prim_helpers", PrimResetNext);

// Reset a primitive's next sibling into a hidden 2-point gradient line
void UnkPolyFunc2(Primitive* prim) {
    PrimResetNext(prim);
    prim->p3 = 8;
    prim->next->p3 = 1;
    prim->next->type = PRIM_LINE_G2;
    prim->next->drawMode = DRAW_HIDE | DRAW_UNK02;
}

// Reset a primitive and its next sibling: disable rendering, set type and draw mode
void UnkPolyFunc0(Primitive* prim) {
    prim->p3 = 0;
    prim->drawMode = 8;
    prim->next->p3 = 0;
    prim->next->type = 4;  // specific primitive type
    prim->next->drawMode = 8;  // specific draw mode
}

INCLUDE_ASM("st/rno0/nonmatchings/prim_helpers", PrimDecreaseBrightness);

INCLUDE_RODATA("st/rno0/nonmatchings/prim_helpers", D_us_801B6220);
