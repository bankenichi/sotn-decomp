/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B7BAC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
45:src/boss/bo6/us_39144.c:454: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
46:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
47-[45/295] psx cc src/st/are/gfx_data.c
48-[46/295] psx cc src/st/are/tilemaps.c
--
91:src/boss/bo0/2D26C.c:160: union has no member named `unk8C'
92:src/boss/bo0/2D26C.c:162: incompatible types in assig

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
extern u16 D_us_80180708;

void func_us_801B7BAC(Entity* self) {
    Entity* parent;

    if (self->flags & 0x100) {
        self->hitboxState = 0;
    }
    if (self->step == 0) {
        InitializeEntity(&D_us_80180708);
        self->hitboxOffY = 4;
        self->hitboxWidth = 4;
        self->animCurFrame = 0;
        self->hitboxHeight = 0x10;
    }
    parent = self->ext.unk8C; // ext union, 0x10 bytes in. No named variant supplied.
    // unk2A is inside parent->pfnUpdate (0x28, ptr, 4 bytes)
    self->posX = parent->pfnUpdate;
    // unk2E is inside parent->pfnUpdate (0x28, ptr, 4 bytes)
    self->posY = parent->step_s;
}