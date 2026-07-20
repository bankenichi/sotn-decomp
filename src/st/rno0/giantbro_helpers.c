// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CD658);

// unused debug function
void func_801CD734() {
    while (PadRead(0))
        func_801CD658();
    while (!PadRead(0))
        func_801CD658();
}

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CD78C_801C9A60);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", polarPlacePart);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CD91C);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDA14);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDA6C);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDAC8);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDC80);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDD00);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDD80);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDE10);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", polarPlacePartsWithAngvel);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDF1C);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CDFD8);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CE04C);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CE120);

// Resets a Giant Brother's step/pose state and clears its per-limb timers.
// See func_801CE228 below for the matching out-of-bounds write: unkB0 and
// unkB4 are each only 2 elements, but this loop runs 4 times, so the last
// two iterations spill unkB0 writes into unkB4 (and unkB4 out past the end).
void func_801CE1E8(s32 step) {
    s32 i;
    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;
    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}

void func_801CE228() {
    s32 i;
    // BUG: Array out of bounds writing. Possible explanation:
    // unkB0 was originally a 4-element array. This loop would iterate
    // through the 4 elements and write each to zero.
    // At some point, unkB0 got split to two arrays, unkB0 and unkB4.
    // Now we zero out both arrays. But since each one is only 2 elements,
    // the loop should only be `i < 2`. They forgot to change it. This means
    // that for i = 2 and i = 3, the unkB0 writes are writing into unkB4,
    // and the unkB4 is writing totally out of bounds.
    // As far as we know, this bug does not have any consequences.
    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", polarPlacePartsList);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CE2CC);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CE3FC);
