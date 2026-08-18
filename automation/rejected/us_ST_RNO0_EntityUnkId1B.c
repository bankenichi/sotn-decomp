/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RNO0:EntityUnkId1B
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/e_elevator.c
   verdict: quality reject: `Entity` has no member `unk02`; 0x02 falls inside `posX` (0x00)

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
void EntityUnkId1B(Entity* self) {
    Entity* parent;
    s16 collisionType;
    u16 params;
    u16 step;

    params = self->params;
    step = self->step;
    parent = self + params * 0xBC;

    switch (step) {
    case 0:
        InitializeEntity(&D_us_80180BF4);
        params = self->params;
        if (params & 0x10) {
            self->animCurFrame = params & 0xF;
            self->zPriority = 0x6A;
            self->step = 2;
            return;
        }
        self->animCurFrame = 0;
        return;

    case 1:
        /* unk02 is inside posX (f32 at 0x00), reading low 16 bits */
        self->unk02 = parent->unk02;
        if (params == step) {
            collisionType = 4;
            /* unk06 is inside posY (f32 at 0x04), reading low 16 bits */
            self->unk06 = parent->unk06 + 0x1B;
        } else {
            collisionType = 6;
            /* unk06 is inside posY (f32 at 0x04), reading low 16 bits */
            self->unk06 = parent->unk06 - 0x20;
        }
        self->ext.reboundStone.stoneAngle = GetPlayerCollisionWith(self, 0xC, 8, collisionType);
        return;
    }
}