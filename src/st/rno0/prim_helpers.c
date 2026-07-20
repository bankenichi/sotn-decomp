// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/prim_helpers", UnkPrimHelper);

s32 UpdateAnimation(u8* texAnimations, Primitive* prim) {
    u16 sp0;
    u16 tempUv;
    s32 retVal = 0;
    u8 index = prim->p1 * 5;
    u8* nextAnimation = &texAnimations[index];

    if (!prim->p2) {
        if (*nextAnimation) {
            if (*nextAnimation == 0xFF) {
                return 0;
            }
            prim->p2 = *nextAnimation++;
            tempUv = nextAnimation[0] + (nextAnimation[1] << 8);
            nextAnimation += 2;
            sp0 = nextAnimation[0] + (nextAnimation[1] << 8);
            LOH(prim->u0) = tempUv;
            LOH(prim->u1) = tempUv + *((u8*)(&sp0));
            LOH(prim->u2) = tempUv + (*((u8*)&sp0 + 1) << 8);
            LOH(prim->u3) = tempUv + sp0;
            prim->p1++;
            retVal = (retVal | 0x80) & 0xFFFF;
        } else {
            prim->p1 = 0;
            prim->p2 = 0;
            nextAnimation = &texAnimations[0];
            prim->p2 = *nextAnimation++;
            tempUv = nextAnimation[0] + (nextAnimation[1] << 8);
            nextAnimation += 2;
            sp0 = nextAnimation[0] + (nextAnimation[1] << 8);
            LOH(prim->u0) = tempUv;
            LOH(prim->u1) = tempUv + (*(u8*)&sp0);
            LOH(prim->u2) = tempUv + (*((u8*)&sp0 + 1) << 8);
            LOH(prim->u3) = tempUv + sp0;
            prim->p1++;
            return 0;
        }
    }

    prim->p2--;
#ifndef VERSION_PSP
    retVal |= 1;
#endif
    retVal = (retVal | 1) & 0xFFFF;
    return retVal & 0xFF;
}

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

// Similar to FindFirstUnkPrim, but returns the first prim with
// p3 == 0 if there is a prim with p3 == 0 at index positions after
Primitive* FindFirstUnkPrim2(Primitive* prim, u8 index) {
    int i;
    Primitive* primLocal = prim;

    while (primLocal != NULL) {
        if (!primLocal->p3) {
            prim = primLocal;
            for (i = 1; i < index; i++) {
                primLocal = primLocal->next;
                if (!primLocal) {
                    return NULL;
                }

                if (primLocal->p3) {
                    break;
                }
            }

            if (i == index) {
                return prim;
            }
        }
        primLocal = primLocal->next;
    }
    return NULL;
}

Primitive* PrimToggleVisibility(Primitive* prim, s32 count) {
    s32 i;
    u8 isVisible;

    if (prim->p3) {
        prim->p3 = false;
    } else {
        prim->p3 = true;
    }

    for (i = 0; i < count; i++) {
        if (prim->p3) {
            prim->drawMode &= ~DRAW_HIDE;
            isVisible = false;
        } else {
            prim->drawMode |= DRAW_HIDE;
            isVisible = true;
        }

        prim = prim->next;
        if (prim == NULL) {
            // Required for PSP match
            if (true) {
                return NULL;
            }
        }

        prim->p3 = isVisible;
    }

    return prim;
}

void PrimResetNext(Primitive* prim) {
    prim->p1 = 0;
    prim->p2 = 0;
    prim->p3 = 0;
    prim->next->x1 = 0;
    prim->next->y1 = 0;
    prim->next->y0 = 0;
    prim->next->x0 = 0;
    prim->next->clut = 0;
    LOHU(prim->next->u0) = 0;
    LOHU(prim->next->b1) = 0;
    LOHU(prim->next->r1) = 0;
    LOHU(prim->next->u1) = 0;
    prim->next->tpage = 0;
    LOHU(prim->next->r2) = 0;
    LOHU(prim->next->b2) = 0;
    prim->next->u2 = 0;
    prim->next->v2 = 0;
    prim->next->r3 = 0;
    prim->next->b3 = 0;
    prim->next->x2 = 0;
    prim->next->y2 = 0;
}

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

s32 PrimDecreaseBrightness(Primitive2* prim, u8 amount) {
    s32 isEnd;
    s32 i, j;
    struct SubPrim* subprim;
    u8* pColor;
    s32 col;

    isEnd = 0;
    subprim = &prim->prim[0];
    for (i = 0; i < 4; i++) {
        j = 0;
        for (; j < 3; j++) {
            pColor = &subprim->col[j];
            col = *pColor;
            col = col - amount;
            if (col < 0) {
                col = 0;
            } else {
                isEnd |= 1;
            }
            *pColor = col;
        }
        subprim++;
    }
    return isEnd;
}

INCLUDE_RODATA("st/rno0/nonmatchings/prim_helpers", D_us_801B6220);
