/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCEN:func_801904B8
   attempt: 3/4
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

s16 func_801904B8(Entity* self, s16 arg1) {
    s16 posXHi;
    s16 posXHi2;
    s16 returnVal;

    ((u8*)&self->zPriority)[0] = 0x50;
    ((u8*)&self->velocityY)[0] = 0x50;
    ((u8*)&self->params)[0] = 0x60;
    self->blendMode = 0x60;

    posXHi = (u16)g_CurrentEntity->posX.i.hi - 8;

    self->entityRoomIndex = 2;
    self->rotPivotX = posXHi;
    ((s16*)&self->velocityX)[0] = posXHi;

    posXHi2 = (u16)g_CurrentEntity->posX.i.hi + 8;

    self->step_s = arg1;
    self->rotPivotY = arg1;
    returnVal = arg1 + 0x20;

    ((u8*)&self->params)[1] = 0x26;
    ((u8*)&self->zPriority)[1] = 0x26;

    self->drawFlags = 6;
    ((u8*)&self->velocityY)[1] = 6;

    self->palette = returnVal;
    ((s16*)&self->velocityX)[1] = returnVal;

    self->step = posXHi2;
    self->facingLeft = posXHi2;

    if ((s16)returnVal >= 0x101) {
        returnVal = 0;
    }

    return returnVal;
}

INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", func_us_8019FE9C);

INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", EntityUnkId1B);
