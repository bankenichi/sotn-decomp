/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BC2F0
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: BUILD FAILED:
46:src/boss/bo6/us_39144.c:454: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
47:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
48-src/boss/bo6/us_39144.c: In function `func_us_801BC2F0':
49:src/boss/bo6/us_39144.c:482: `RIC_posX_i_hi' undeclared (first use this function)
50:src/boss/bo6/us_39144.c:482: (Each undeclared identifier

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
void func_us_801BC2F0(Entity* arg0) {
    if (RIC_step == 0x18) {
        arg0->posX.i.hi = RIC_posX_i_hi;
        arg0->posY.i.hi = RIC_posY_i_hi;
        arg0->facingLeft = RIC_facingLeft;
        if (arg0->step == 0) {
            InitializeEntity(&D_us_8018043C);
            arg0->flags = 0x18000000;
            arg0->hitboxOffX = 0x14;
            arg0->hitboxOffY = 0xC;
            arg0->hitboxHeight = 9;
            arg0->hitboxWidth = 9;
            arg0->step = 1;
            arg0->ext.reboundStone.stoneAngle = arg0->hitboxState;
        }
        arg0->hitboxState = arg0->ext.reboundStone.stoneAngle;
        if (RIC_pose < 2) {
            arg0->hitboxState = 0;
        }
        if (RIC_pose >= 8) {
            DestroyEntity(arg0);
        }
    } else {
        DestroyEntity(arg0);
    }
}