/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B24CC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
109:src/boss/bo0/2D26C.c:111: union has no member named `unk80'
110:src/boss/bo0/2D26C.c:112: union has no member named `unk84'
111:src/boss/bo0/2D26C.c:114: union has no member named `unkBC'
112:src/boss/bo0/2D26C.c:115: union has no member named `unkC0'
113:src/boss/bo0/2D26C.c:117: union has no member named `unk178'
114:src/boss/bo0/2D26C.c:118: union has no member named `unk17C'


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
void func_us_801B24CC(void) {
    Entity* entity = g_CurrentEntity;
    Entity* child1;
    Entity* child2;
    s32 var_s5;
    s32 temp_s4;
    s32 temp_s3;
    s32 temp_s2;
    s32 temp_s3_2;
    s32 temp_s0;
    s32 temp_v1;
    s32 temp_s0_2;
    s16 var_v0;
    s16 var_v0_2;

    child1 = (Entity*)entity->ext.unk80; // ext union, 0x04 bytes in
    child2 = (Entity*)entity->ext.unk84; // ext union, 0x08 bytes in

    child1->scaleY = entity->ext.unkBC; // ext union, 0x40 bytes in
    child1->rotPivotX = entity->ext.unkC0; // ext union, 0x44 bytes in

    child2->scaleY = entity->ext.unk178; // ext union, 0xfc bytes in
    child2->rotPivotX = entity->ext.unk17C; // ext union, 0x100 bytes in

    var_s5 = 0;
    child1 = (Entity*)entity->ext.unk80; // ext union, 0x04 bytes in

    do {
        temp_s4 = entity->posX;
        temp_s3 = entity->posY;

        if (entity->facingLeft != 0) {
            var_v0 = 0xC00 - child1->hitboxOffX;
        } else {
            var_v0 = child1->hitboxOffX + 0xC00;
        }

        temp_s2 = temp_s4 + (rcos(var_v0) * 0x1C0);
        temp_s3_2 = temp_s3 - (rsin(var_v0) * 0x1C0);

        child1->pfnUpdate = (void (*)(Entity*))temp_s2;
        child1->step = (u16)temp_s3_2;

        if (entity->facingLeft != 0) {
            var_v0_2 = 0xC00 - child1->hitboxOffY;
        } else {
            var_v0_2 = child1->hitboxOffY + 0xC00;
        }

        temp_s0 = temp_s2 + (rcos(var_v0_2) * 0x2A0);
        temp_v1 = temp_s3_2 - (rsin(var_v0_2) * 0x2A0);

        child1->scaleY = (s16)temp_s0;
        temp_s0_2 = temp_s0 - temp_s4;
        child1->rotPivotX = (s16)temp_v1;
        child1->facingLeft = (u16)temp_s0_2;

        var_s5 += 1;

        if (entity->facingLeft != 0) {
            child1->facingLeft = (u16)(-temp_s0_2);
        }

        child1 = (Entity*)child1->blendMode;
    } while (var_s5 < 2);
}