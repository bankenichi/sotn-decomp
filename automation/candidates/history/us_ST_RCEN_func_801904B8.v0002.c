/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCEN:func_801904B8
   attempt: 2/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/st/rcen/e_elevator.c
   asm    : asm/us/st/rcen/nonmatchings/e_elevator/func_801904B8.s

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
#include "rcen.h"

// Unused on PSP, see UnusedPrimFunction in CEN
INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", func_us_8019FD4C);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

s16 func_801904B8(Entity* arg0, s16 arg1) {
    s16 posXHi;
    s16 posXHi2;
    s16 step_s_val;
    s16 rotPivot_val;
    s16 returnVal;
    u16 temp;

    ((u8*)&arg0->zPriority)[0] = 0x50;
    ((u8*)&arg0->velocityY)[0] = 0x50;
    ((u8*)&arg0->params)[0] = 0x60;
    arg0->blendMode = 0x60;

    temp = g_CurrentEntity->posX.i.hi;
    arg0->entityRoomIndex = 2;

    posXHi = (s16)(temp - 8);
    arg0->rotPivotX = posXHi;
    ((s16*)&arg0->velocityX)[0] = posXHi;

    posXHi2 = (s16)g_CurrentEntity->posX.i.hi;

    step_s_val = arg1;
    arg0->step_s = step_s_val;
    arg0->rotPivotY = step_s_val;

    rotPivot_val = arg1 + 0x20;
    arg0->params = 0x2600;
    arg0->zPriority = 0x2600;
    arg0->drawFlags = 6;
    ((u8*)&arg0->velocityY)[1] = 6;
    arg0->palette = rotPivot_val;
    ((s16*)&arg0->velocityX)[1] = rotPivot_val;

    posXHi2 = posXHi2 + 8;
    arg0->step = posXHi2;
    arg0->facingLeft = posXHi2;

    if ((s16)rotPivot_val < 0x101) {
        returnVal = rotPivot_val;
    } else {
        returnVal = 0;
    }

    return returnVal;
}

INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", func_us_8019FE9C);

INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", EntityUnkId1B);
