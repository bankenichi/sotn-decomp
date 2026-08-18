/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BD47C
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: BUILD FAILED:
51:src/boss/bo6/us_39144.c:454: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
52:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
53-[51/243] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/stcen.map -T build/us/stcen.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.stcen.txt -T build/us/

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
s32 func_us_801BD47C(Entity* arg0) {
    s32 i;
    Entity* entity;
    u16 entityId;
    u16 params;

    entityId = arg0->entityId;
    params = arg0->params;
    for (i = 0x50, entity = &g_Entities[0x50]; i < 0x90; i++, entity++) {
        if (entity->entityId != entityId) {
            continue;
        }
        if (entity->params != params) {
            continue;
        }
        if (entity == arg0) {
            continue;
        }
        return 1;
    }
    return 0;
}