/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B21F0
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
103:src/boss/bo0/2D26C.c:106: union has no member named `unk80'
104:src/boss/bo0/2D26C.c:107: union has no member named `unkBC'
105:src/boss/bo0/2D26C.c:108: union has no member named `unkC0'
106:src/boss/bo0/2D26C.c:110: union has no member named `unk84'
107:src/boss/bo0/2D26C.c:111: union has no member named `unk178'
108:src/boss/bo0/2D26C.c:112: union has no member named `unk17C'


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
void func_us_801B21F0(void) {
    Entity* entity = g_CurrentEntity;
    Entity* active;
    Entity* other;
    s32 angle;
    s32 cos_val;
    s32 sin_val;
    s32 posX;
    s32 posY;
    s32 temp;
    s32 temp2;

    active = entity->ext.unk80; // Entity offset 0x80
    active->pfnUpdate = entity->ext.unkBC; // Entity offset 0xBC
    active->step = entity->ext.unkC0; // Entity offset 0xC0

    other = entity->ext.unk84; // Entity offset 0x84
    other->pfnUpdate = entity->ext.unk178; // Entity offset 0x178
    other->step = entity->ext.unk17C; // Entity offset 0x17C

    if (entity->ext.unk88 == 0) { // Entity offset 0x88
        active = entity->ext.unk80;
    } else {
        active = entity->ext.unk84;
    }

    posX = active->pfnUpdate;
    posY = active->step;

    if (entity->facingLeft != 0) {
        angle = 0xC00 - active->hitboxOffX;
    } else {
        angle = active->hitboxOffX + 0xC00;
    }

    cos_val = rcos(angle);
    temp = cos_val * 4 + cos_val;
    temp = temp * 4 + cos_val;
    temp = temp * 32;
    posX -= temp;

    sin_val = rsin(angle);
    temp = sin_val * 4 + sin_val;
    temp = temp * 4 + sin_val;
    temp = temp * 32;
    posY += temp;

    active->rotPivotX = posX;
    active->rotPivotY = posY;

    if (entity->facingLeft != 0) {
        angle = 0xC00 - active->velocityY;
    } else {
        angle = active->velocityY + 0xC00;
    }

    cos_val = rcos(angle);
    temp = cos_val * 8 - cos_val;
    temp = temp * 64;
    temp2 = posX - temp;

    sin_val = rsin(angle);
    temp = sin_val * 8 - sin_val;
    temp = temp * 64;
    posY += temp;

    active->hitboxOffX = temp2 - posX;
    if (entity->facingLeft == 0) {
        active->hitboxOffX = -active->hitboxOffX;
    }

    entity->posX.val = temp2;
    entity->posY.val = posY + 0xFFFC0000;

    other = active->anim;
    if (entity->facingLeft != 0) {
        angle = 0xC00 - other->velocityY;
    } else {
        angle = other->velocityY + 0xC00;
    }

    cos_val = rcos(angle);
    temp = cos_val * 8 - cos_val;
    temp = temp * 64;
    posX = temp2 + temp;

    sin_val = rsin(angle);
    temp = sin_val * 8 - sin_val;
    temp = temp * 64;
    posY -= temp;

    other->rotPivotX = posX;
    other->rotPivotY = posY;

    if (entity->facingLeft != 0) {
        angle = 0xC00 - other->hitboxOffX;
    } else {
        angle = other->hitboxOffX + 0xC00;
    }

    cos_val = rcos(angle);
    temp = cos_val * 4 + cos_val;
    temp = temp * 4 + cos_val;
    temp = temp * 32;
    temp2 = posX + temp;

    sin_val = rsin(angle);
    temp = sin_val * 4 + sin_val;
    temp = temp * 4 + sin_val;
    temp = temp * 32;
    posY -= temp;

    temp = temp2 - posX;
    other->pfnUpdate = temp2;
    other->step = posY;
    other->hitboxOffX = temp;
    if (entity->facingLeft != 0) {
        other->hitboxOffX = -temp;
    }
}