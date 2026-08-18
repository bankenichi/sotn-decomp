/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BC5C8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: BUILD FAILED:
52:src/boss/bo6/us_39144.c:454: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
53:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
54-[52/292] psx cc src/st/are/gfx_data.c
55-[53/292] psx cc src/st/cat/gfx_data.c

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
void func_us_801BC5C8(Entity* entity) {
    if (RIC_step != 9) {
        DestroyEntity(entity);
        return;
    }

    entity->posX.i.hi = RIC_posX_i_hi;
    entity->posY.i.hi = RIC_posY_i_hi;
    entity->facingLeft = RIC_facingLeft;

    if (entity->step == 0) {
        InitializeEntity(&D_us_80180430);
        entity->flags = 0x18000000;
        entity->hitboxOffX = 12;
        entity->hitboxOffY = -26;
        entity->hitboxWidth = 12;
        entity->hitboxHeight = 12;
        entity->step = 1;
    }
}