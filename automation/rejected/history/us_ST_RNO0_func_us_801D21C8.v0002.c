/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801D21C8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   verdict: BUILD FAILED:
115:src/st/rno0/unk_4F968.c:46: `D_us_8018333C' undeclared (first use this function)
116:src/st/rno0/unk_4F968.c:46: (Each undeclared identifier is reported only once
117:src/st/rno0/unk_4F968.c:46: for each function it appears in.)
118-[114/243] psx cc src/st/rno3/stage_data.c
119-[115/243] psx cc src/st/rnz0/gen/us/sprites.c

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
/* Mechanical symbol repair from escalation_triage.py. */
extern s16 D_us_8018333C[];

void func_us_801D21C8(Entity* entity) {
    u16 step;
    s32 animResult;

    step = entity->step;
    switch (step) {
    case 0:
        InitializeEntity(g_EInitGorgon);
        entity->zPriority = 0x72;
        entity->palette = 0x8235;
        entity->velocityY = -0xC000;
        break;
    case 1:
        MoveEntity();
        animResult = AnimateEntity(D_us_8018333C, entity);
        if (animResult == 0) {
            DestroyEntity(entity);
        }
        break;
    default:
        break;
    }
}