/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO1:func_us_801B9028_from_no1
   attempt: 1/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (calls declared)
   origin : src/st/rno1/unk_29930.c
   asm    : asm/us/st/rno1/nonmatchings/unk_29930/func_us_801B9028_from_no1.s

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
#include "rno1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_8018076C;

void func_us_801B9028_from_no1(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(D_us_8018076C);
        self->animCurFrame = self->params + 1;
        self->zPriority = D_us_80180D44[self->params];
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = D_us_80180D58[self->params];
        break;

    case 1:
        break;

    case 2:
#include "../pad2_anim_debug.h"
    }
}


INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_801A9A8C);

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_80198A18_from_rbo4);

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_801A9BEC);
