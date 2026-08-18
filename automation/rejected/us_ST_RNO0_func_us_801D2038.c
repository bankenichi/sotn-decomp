/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801D2038
   attempt: 4/4
   model  : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   verdict: BUILD FAILED:
139:src/st/rno0/unk_4F968.c:72: invalid operands to binary +
140:src/st/rno0/unk_4F968.c:72: union has no member named `pad'
141:src/st/rno0/unk_4F968.c:79: union has no member named `pad'
142:src/st/rno0/unk_4F968.c:79: invalid operands to binary +
143:src/st/rno0/unk_4F968.c:80: union has no member named `unkA4'
144:src/st/rno0/unk_4F968.c:80: invalid operands to binary +
145-[138/

   This is NOT a permuter seed and must never be treated as
   one: it has never compiled. automation/candidates/ is for
   code that builds and merely misses on bytes.

   Why it is kept: the escalation path used to record only
   the compiler's message, so a record like `g_EInitCommon
   undeclared` described code nobody could look at any more.
   Twelve such records were assumed to be one extern away
   from building, and turned out to need a full re-attempt
   because the candidate had been discarded.

   Do NOT apply this to the tree. Read it, fix what the
   verdict names, and re-attempt. */
extern u16 PLAYER_posY_i_hi;

void func_us_801D2038(Entity* self) {
    Collider collider;
    s32 diff;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitGorgon);
        self->animCurFrame = 0xC;
        self->zPriority = 0x73;
        break;

    case 19:
        if (self->step_s == 0) {
            self->step_s += 1;
        } else {
            self->animCurFrame = 0;
        }
        break;

    case 22:
        self->velocityY = 0x10000;
        MoveEntity();
        g_api_CheckCollision(
            self->posX.i.hi, self->posY.i.hi + 6, &collider, 0);
        if (collider.effects & 1) {
            DestroyEntity(self);
            return;
        }
        /* fall through */

    default:
        self->animCurFrame = 0xC;
        if (GetPlayerCollisionWith(self, 0x10, 0x8, 0x4) != 0) {
            diff = (g_Tilemap.scrollX + self->posX.val) - self->ext.pad;
            g_Entities[0].posX.val += diff;
            PLAYER_posY_i_hi += 1;
        }
        break;
    }

    self->ext.pad = g_Tilemap.scrollX + self->posX.val;
    self->ext.unkA4 = g_Tilemap.scrollY + self->posY.val;
}