/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RCEN:func_us_8019C4EC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_shaft.c
   verdict: quality reject: `Entity` has no member `unk82`; 0x82 falls inside `ext` (0x7C)

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
void func_us_8019C4EC(Entity* self) {
    s32 angle;
    s32 velocity;
    Entity* parent;

    if (!(PrizeDrops & 4)) {
        if (self->step == 0) {
            InitializeEntity(D_us_80180588);
            self->palette = 0x2E7;
            self->drawFlags = 4;
            self->velocityX = 0;
            self->blendMode = 0x30;
            /* unk82 is ext+0x06, no named field */
            self->rotate = self->unk82 + 0x400;
        }
        /* unk9C is ext+0x20, no named field */
        parent = self->unk9C;
        angle = self->unk82;
        self->velocityX += 0x10000;
        self->posX.i.hi = parent->posX.i.hi;
        self->posY.i.hi = parent->posY.i.hi;
        velocity = self->velocityX >> 12;
        self->posX.val += velocity * rcos(angle);
        self->posY.val += velocity * rsin(angle);
        if (AnimateEntity(D_us_80180890, self) == 0) {
            DestroyEntity(self);
        }
    } else {
        DestroyEntity(self);
    }
}