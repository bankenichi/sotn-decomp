/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO1:func_us_801B9028_from_no1
   attempt: 1/4
   from   : deterministic transplant
   origin : src/st/rno1/unk_29930.c
   verdict: BUILD FAILED:
226:src/st/rno1/unk_29930.c:15: `D_us_80180D44' undeclared (first use this function)
227:src/st/rno1/unk_29930.c:15: (Each undeclared identifier is reported only once
228:src/st/rno1/unk_29930.c:15: for each function it appears in.)
229:src/st/rno1/unk_29930.c:17: `D_us_80180D58' undeclared (first use this function)
230-[225/507] psx cc src/st/rno3/layers.c
231-[226/507] psx cc src/st/rno3/graphics_banks.c

   This is NOT a permuter seed and must never be treated as
   one: it has never built. automation/candidates/ is for
   code that builds and merely misses on bytes.

   Why it is kept: the escalation path used to record only
   the compiler's message, so a record like `g_EInitCommon
   undeclared` described code nobody could look at any more.
   Twelve such records were assumed to be one extern away
   from building, and turned out to need a full re-attempt
   because the candidate had been discarded.

   Do NOT apply this to the tree. Read it, fix what the
   verdict names, and re-attempt. */
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