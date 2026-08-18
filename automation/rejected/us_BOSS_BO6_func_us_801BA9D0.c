/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BA9D0
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: BUILD FAILED:
48:src/boss/bo6/us_39144.c:468: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
49:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
50-[48/292] psx cc src/st/are/gfx_data.c
51-[49/292] psx cc src/st/cat/gfx_data.c

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
extern AnimationFrame D_us_80182360;

/* Initiates Ric's subweapon throw animation and spawns the projectile entity */
void func_us_801BA9D0(void) {
    BO6_RicSetStep(0x19);
    BO6_RicSetAnimation(&D_us_80182360);
    g_CurrentEntity->velocityY = 0;
    BO6_RicSetSpeedX(0x58000);
    g_Ric.unk46 = 5;
    g_Ric.timers[0xC] = 4;
    BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x1A, 0);
    func_us_801B9C14();
    g_api_PlaySfx(0x834);
    g_api_PlaySfx(0x707);
}