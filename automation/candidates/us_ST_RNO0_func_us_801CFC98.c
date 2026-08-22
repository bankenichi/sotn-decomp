/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_us_801CFC98
   attempt: 1/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/st/rno0/unk_4F968.c
   asm    : asm/us/st/rno0/nonmatchings/unk_4F968/func_us_801CFC98.s

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
extern void (*g_api_CheckCollision)(s32 x, s32 y, Collider* res, s32 unk);
/* End permuter-seed writer declarations. */

// func_us_801D1BF0's candidate failed to build on this name alone. Defined by
// THIS overlay at src/st/rno0/e_init.c:229, not borrowed from another one.
extern EInit g_EInitGorgon;

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CF968);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFB20);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

s32 func_us_801CFC98(Entity* arg0, s32 arg1) {
    Collider sp10;
    s32 result;
    s32 i;
    s32 checkX;
    s32 checkY;

    checkX = arg0->posX.i.hi;
    if (arg1 != g_CurrentEntity->facingLeft) {
        checkX += 0x38;
    } else {
        checkX -= 0x38;
    }

    result = 0;
    checkY = arg0->posY.i.hi + 4;

    for (i = 0; i < 2; i++) {
        g_api_CheckCollision(checkX, checkY, &sp10, 0);
        if (i == 0) {
            if (sp10.effects & 1) {
                result |= 1;
            }
        } else {
            if (!(sp10.effects & 1)) {
                result |= 2;
            }
        }
        checkY += 4;
    }

    return result;
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFD70);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFE6C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFEA0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D068C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D0CFC);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D136C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D15C0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D1BF0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D2038);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D21C8);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D2264);
