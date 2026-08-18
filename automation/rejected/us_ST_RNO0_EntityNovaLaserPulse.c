/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RNO0:EntityNovaLaserPulse
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_48100.c
   verdict: quality reject: `Entity` has no member `unk94`; 0x94 falls inside `ext` (0x7C)

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
extern void InitializeEntity(u16 arg0[]);
extern void MoveEntity(void);
extern void DestroyEntity(Entity* entity);
extern u16 D_us_80180B64;

/* Nova laser pulse entity: expands outward, then shrinks and destroys itself */
void EntityNovaLaserPulse(Entity* self) {
    s32 absVelX;
    s32 temp;
    s16 scale;

    switch (self->step) {
    case 0:
        InitializeEntity(&D_us_80180B64);
        self->animCurFrame = 0x24;
        self->scaleY = 0x10;
        self->scaleX = 0x10;
        self->hitboxState = 0;
        self->drawFlags |= 3;
        if (self->facingLeft) {
            self->velocityX = 0x80000;
        } else {
            self->velocityX = -0x80000;
        }
        /* fall through */
    case 1:
        MoveEntity();
        absVelX = self->velocityX;
        if (absVelX < 0) {
            absVelX = -absVelX;
        }
        /* unk94: ext+0x18, accumulates absolute velocity */
        self->unk94 += absVelX;
        scale = self->scaleY + 0x40;
        self->scaleY = scale;
        self->scaleX = scale;
        if (scale >= 0x100) {
            self->step++;
        }
        break;

    case 2:
        MoveEntity();
        absVelX = self->velocityX;
        if (absVelX < 0) {
            absVelX = -absVelX;
        }
        /* unk94: ext+0x18, accumulates absolute velocity */
        temp = absVelX + self->unk94;
        self->unk94 = temp;
        /* unk90: ext+0x14, used as a size/lifetime counter */
        if (((self->unk90 + 0x20) << 16) - temp < 0) {
            DestroyEntity(self);
        }
        break;
    }
}