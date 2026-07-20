// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_801CD78C_801CEB40);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801D2424_from_are);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CEEB4);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CF08C);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CF24C);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801CF380);

// EntitySpectralSword primarily uses this as a method to smoothly rotate, but
// also to retract it's outer ring after an attack by decreasing the radius.
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
