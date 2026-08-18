/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RCEN:EntityUnkId1B
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_elevator.c
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
extern s32 D_us_801805A0;

void EntityUnkId1B(Entity* self) {
    Entity* parent;
    s32 step;
    u16 params;
    s16 collisionResult;

    params = self->params;
    step = self->step;

    // Calculate parent entity index: params * 0xBC (size of Entity struct)
    parent = (Entity*)((s32)self + (params * 0xBC));

    switch (step) {
    case 0:
        InitializeEntity(&D_us_801805A0);
        params = self->params;
        if (params & 0x10) {
            // Lower 4 bits of params used as animation frame index
            self->animCurFrame = params & 0xF;
            self->zPriority = 0x6A;
            self->step = 2;
        } else {
            self->animCurFrame = 0;
        }
        break;

    case 1:
        // unk02 is inside posX (offset 0x00, f32), reading upper 16 bits
        self->unk02 = parent->unk02;
        if (params == step) {
            // unk06 is inside posY (offset 0x04, f32), reading upper 16 bits
            collisionResult = parent->unk06 + 0x1B;
            collisionResult = GetPlayerCollisionWith(self, 0xC, 8, 4);
        } else {
            // unk06 is inside posY (offset 0x04, f32), reading upper 16 bits
            collisionResult = parent->unk06 - 0x20;
            collisionResult = GetPlayerCollisionWith(self, 0xC, 8, 6);
        }
        self->unk06 = collisionResult;
        self->ext.reboundStone.stoneAngle = collisionResult;
        break;
    }
}