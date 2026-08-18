/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BD384
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: BUILD FAILED:
51:src/boss/bo6/us_39144.c:454: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
52:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
53-[51/240] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/stcen.map -T build/us/stcen.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.stcen.txt -T build/us/

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
/* Richter boss: falling whip particle that can spawn sub-entities */
extern AnimationFrame D_us_80181A40;
extern u16 RIC_zPriority;

void func_us_801BD384(Entity* arg0) {
    u16 step;

    step = arg0->step;
    switch (step) {
    case 0:
        arg0->animSet = 2;
        arg0->anim = &D_us_80181A40;
        arg0->flags = 0x28000000;
        arg0->zPriority = RIC_zPriority + 4;
        /* random downward velocity in fixed-point range */
        arg0->velocityY = (rand() & 0x3FFF) + 0xFFFF0000;
        arg0->step++;
        break;
    case 1:
        /* at pose frame 6, poseTimer 1, 50% chance to spawn a sub-entity */
        if ((arg0->pose == 6) && (arg0->poseTimer == step) && (rand() & 1)) {
            BO6_RicCreateEntFactoryFromEntity(arg0, 4, 0);
        }
        arg0->posY.val += arg0->velocityY;
        if (arg0->poseTimer < 0) {
            DestroyEntity(arg0);
        }
        break;
    }
}