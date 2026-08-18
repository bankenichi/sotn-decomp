/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B5470
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
36:src/boss/bo6/us_39144.c:454: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
37:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
38-[36/243] psx cc src/st/no3/stage_data.c
39-[37/243] psx cc src/st/no3/tilemaps.c
--
94:src/boss/bo0/2D26C.c:145: union has no member named `unk8C'
95-[91/243] mipsel-linux-gnu-ld -nostdlib --no-check-s

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

void func_us_801B5470(Entity* self) {
    Entity* parent;

    self->facingLeft = *(u16*)((s8*)self - 0xA8);
    if (self->flags & 0x100) {
        self->hitboxState = 0;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(&D_us_80180708);
        self->hitboxWidth = 0xC;
        self->hitboxHeight = 4;
        self->hitboxOffX = -0xC;
        self->animCurFrame = 0;
        break;

    case 1:
        parent = self->ext.unk8C;
        self->posX = parent->posX;
        self->posY = parent->posY;
        break;
    }
}