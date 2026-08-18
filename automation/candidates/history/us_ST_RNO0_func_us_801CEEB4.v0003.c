/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_us_801CEEB4
   attempt: 4/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/st/rno0/e_gorgon.c
   asm    : asm/us/st/rno0/nonmatchings/e_gorgon/func_us_801CEEB4.s

   IMPORT VIA THE SUPERVISOR, NOT DIRECTLY:
       permuter_supervisor.py --import-seeds

   This banner used to say `import.py <this file> <asm>`,
   and that ADVICE CANNOT WORK. The seed is the whole
   source file, so it starts with quoted includes like
   #include "bo0.h" -- and cpp resolves a quoted include
   relative to the DIRECTORY OF THE FILE. From
   automation/candidates/ there is no bo0.h, so the import
   dies with `fatal error: bo0.h: No such file or
   directory` before it ever looks at the C.

   The supervisor gets this right: it writes the body back
   into `origin` above, imports from there so the includes
   resolve, and restores the file afterwards (journalled,
   so a kill cannot leave the edit behind).

   Six BOSS/BO0 records were deferred as `seed-bug` with a
   note blaming a missing `extern func_us_801B171C`. That
   diagnosis was wrong; the seeds were fine and the import
   command in this banner was not. Verified 2026-08-10 by
   running the import and reading the actual error.

   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
int abs(int x);

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_801CD78C_801CEB40();
extern int func_us_801D2424_from_are();

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_801CD78C_801CEB40);

INCLUDE_ASM("st/rno0/nonmatchings/e_gorgon", func_us_801D2424_from_are);

void func_us_801CEEB4(Entity* self, Entity* target, u16* spawnData, Entity* entityList) {
        u16 temp_s0;
        u16 temp_s0_2;
        s16 temp_s0_3;
        Entity *temp_s2;
        Entity *temp_s2_2;
    s16 sp20;
    s16 sp22;
    s16 sp28;
    s16 sp2A;
    s16 sp30[4];
    s16 sp38[4];

    temp_s0 = *spawnData;
    spawnData--;
    func_801CD78C_801CEB40((s16*)-0xE, (s16)temp_s0, sp30);
    sp20 = 6;
    sp22 = 6;
    sp28 = 0xA;
    sp2A = 8;
    entityList->entityRoomIndex = 2;
    func_us_801D2424_from_are(sp30, (s16)temp_s0, &sp20, self, (s32)(s16)temp_s0, &sp28, entityList);
    temp_s2_2 = entityList->nextPart;
    func_801CD78C_801CEB40(sp30, 3, (s16*)temp_s0, sp30);
    temp_s0_2 = *spawnData;
    spawnData--;
    func_801CD78C_801CEB40(sp30, -0xC, (s16*)temp_s0_2, sp38);
    sp20 = 6;
    sp22 = 6;
    sp28 = 6;
    sp2A = 6;
    func_us_801D2424_from_are(sp38, (s16)temp_s0_2, &sp20, sp30, (s32)(s16)temp_s0_2, &sp28, temp_s2_2);
    temp_s2_2->entityRoomIndex = 2;
    temp_s2 = temp_s2_2->nextPart;
    func_801CD78C_801CEB40(sp38, -4, (s16*)temp_s0_2, sp38);
    temp_s0_3 = *spawnData;
    func_801CD78C_801CEB40(sp38, 5, (s16*)temp_s0_3, sp38);
    func_801CD78C_801CEB40(sp38, -0x16, (s16*)temp_s0_3, target);
    sp20 = 8;
    sp22 = 8;
    sp28 = 0xA;
    sp2A = 0xA;
    func_us_801D2424_from_are(target, temp_s0_3, &sp20, sp38, (s32)temp_s0_3, &sp28, temp_s2);
    temp_s2->entityRoomIndex = 2;
}

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
