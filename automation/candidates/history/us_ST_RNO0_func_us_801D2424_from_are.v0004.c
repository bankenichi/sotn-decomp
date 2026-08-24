// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int rcos(int a);
int rsin(int a);
int abs(int x);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_801CD78C_801CEB40);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void func_us_801D2424_from_are(Pos* arg0, s16 arg1, Point16* arg2, Pos* arg3,
                             s16 arg4, Point16* arg5, Primitive* prim) {
    prim->x0 = prim->x1 = arg0->x.i.hi;
    prim->y0 = prim->y1 = arg0->y.i.hi;
    prim->x2 = prim->x3 = arg3->x.i.hi;
    prim->y2 = prim->y3 = arg3->y.i.hi;
    if (g_CurrentEntity->facingLeft) {
        prim->x0 += FLT_TO_I(arg2->x * rcos(arg1));
        prim->x1 -= FLT_TO_I(arg2->y * rcos(arg1));
        prim->x2 += FLT_TO_I(arg5->x * rcos(arg4));
        prim->x3 -= FLT_TO_I(arg5->y * rcos(arg4));
    } else {
        prim->x0 -= FLT_TO_I(arg2->x * rcos(arg1));
        prim->x1 += FLT_TO_I(arg2->y * rcos(arg1));
        prim->x2 -= FLT_TO_I(arg5->x * rcos(arg4));
        prim->x3 += FLT_TO_I(arg5->y * rcos(arg4));
    }
    prim->y0 -= FLT_TO_I(arg2->x * rsin(arg1));
    prim->y1 += FLT_TO_I(arg2->y * rsin(arg1));
    prim->y2 -= FLT_TO_I(arg5->x * rsin(arg4));
    prim->y3 += FLT_TO_I(arg5->y * rsin(arg4));
}

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CEEB4);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CF08C);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CF24C);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CF380);

// EntitySpectralSword primarily uses this as a method to smoothly rotate, but
// also to retract it's outer ring after an attack by decreasing the radius.
// NOT static, despite the shared src/st/step_towards.h defaulting to static.
// src/st/rno0/unk_4F968.c still holds INCLUDE_ASM stubs that `jal StepTowards`
// across the translation-unit boundary, so this needs external linkage until
// those are decompiled. A source-level grep does not show this: the callers
// are assembly, not C.
// Verbatim copy of func_801CDC80 in src/st/approach_s16.h.
// Kept in sync by hand: this file cannot include that header.
bool StepTowards(s16* val, s32 target, s32 step) {
    if (abs(*val - target) < step) {
        *val = target;
        return true;
    }

    if (*val > target) {
        *val -= step;
    }

    if (*val < target) {
        *val += step;
    }

    return false;
}

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CF64C);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CF7D0);
