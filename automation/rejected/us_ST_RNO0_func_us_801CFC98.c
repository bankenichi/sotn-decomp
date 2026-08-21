/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801CFC98
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   verdict: BUILD FAILED:
233:src/st/rno0/unk_4F968.c:38: structure has no member named `hit'
234:src/st/rno0/unk_4F968.c:42: structure has no member named `hit'
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
s32 func_us_801CFC98(Entity* entity, s32 facingLeft) {
    Collider sp10;
    s32 xPos;
    s32 yPos;
    s32 flags;
    s32 i;

    // Read upper 16 bits of posX (integer part of fixed-point)
    xPos = ((s16*)&entity->posX)[1];
    if (facingLeft != g_CurrentEntity->facingLeft) {
        xPos += 0x38;
    } else {
        xPos -= 0x38;
    }
    flags = 0;
    // Read upper 16 bits of posY (integer part of fixed-point) + 4
    yPos = ((s16*)&entity->posY)[1] + 4;
    for (i = 0; i < 2; i++, yPos += 4) {
        g_api_CheckCollision(xPos, yPos, &sp10, 0);
        if (i == 0) {
            if (sp10.hit & 1) {
                flags |= 1;
            }
        } else {
            if (!(sp10.hit & 1)) {
                flags |= 2;
            }
        }
    }
    return flags;
}