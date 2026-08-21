/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RCEN:func_801904B8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_elevator.c
   verdict: BUILD FAILED:
233:src/st/rcen/e_elevator.c:24: aggregate value used where an integer was expected
234:src/st/rcen/e_elevator.c:37: aggregate value used where an integer was expected
235-[232/356] psx cc src/st/rno3/stage_data.c
236-[233/356] psx cc src/st/rnz0/sprite_banks.c

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
s16 func_801904B8(Entity* arg0, s16 arg1) {
    s16 temp_a1;
    s16 temp_v0;
    s16 temp_v1;
    s16 var_a2;

    arg0->zPriority = 0x50;
    // unk0C: no named field, writing to low byte of velocityY is not possible without raw byte pointer.
    arg0->step = 0x60;
    // unk18: no named field, writing to low byte of blendMode is not possible without raw byte pointer.
    arg0->entityRoomIndex = 2;
    temp_v0 = (u16) g_CurrentEntity->posX - 8;
    arg0->rotPivotX = temp_v0;
    // unk08: no named field, writing to low byte of velocityX is not possible without raw byte pointer.
    temp_a1 = arg1 + 0x20;
    arg0->step_s = arg1;
    arg0->rotPivotY = arg1;
    var_a2 = temp_a1;
    // unk31: no named field, writing to high byte of params is not possible without raw byte pointer.
    // unk25: no named field, writing to high byte of zPriority is not possible without raw byte pointer.
    arg0->drawFlags = 6;
    // unk0D: no named field, writing to high byte of velocityY is not possible without raw byte pointer.
    arg0->palette = var_a2;
    // unk0A: no named field, writing to high byte of velocityX is not possible without raw byte pointer.
    temp_v1 = (u16) g_CurrentEntity->posX + 8;
    arg0->step = temp_v1;
    arg0->facingLeft = temp_v1;
    if (temp_a1 >= 0x101) {
        var_a2 = 0;
    }
    return var_a2;
}