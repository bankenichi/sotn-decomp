/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_801CD78C_801CEB40
   attempt: 2/4
   model  : opencode/ling-3.0-flash-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/rno0/nonmatchings/e_gorgon/func_801CD78C_801CEB40.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

void func_801CD78C_801CEB40(void *arg0, s32 arg1, s16 arg2, void *arg3) {
    s16 var_s0;

    var_s0 = arg2;
    if (g_CurrentEntity->facingLeft != 0) {
        var_s0 = -arg2;
    }
    *(s32 *)arg3 = *(s32 *)arg0;
    *((s32 *)arg3 + 1) = *((s32 *)arg0 + 1);
    *(s32 *)arg3 = *(s32 *)arg3 - (arg1 * rsin((s32)var_s0) * 0x10);
    *((s32 *)arg3 + 1) = *((s32 *)arg3 + 1) + (arg1 * rcos((s32)var_s0) * 0x10);
}

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801D2424_from_are);

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
