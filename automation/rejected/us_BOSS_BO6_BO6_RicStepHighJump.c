/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicStepHighJump
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/richter.c
   verdict: BUILD FAILED:
37:src/boss/bo6/richter.c:306: `D_80076306' undeclared (first use this function)
38:src/boss/bo6/richter.c:306: (Each undeclared identifier is reported only once
39:src/boss/bo6/richter.c:306: for each function it appears in.)
40:src/boss/bo6/richter.c:310: `RIC_facingLeft' undeclared (first use this function)
41:src/boss/bo6/richter.c:349: `D_us_801820BC' undeclared (first use this 

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
void BO6_RicStepHighJump(void) {
    s32 var_s1;
    s32 temp_v1;
    s32 var_v0;

    g_Ric.high_jump_timer += 1;
    var_s1 = 0;
    switch (D_80076306) {
    case 0:
        if (g_Ric.padPressed & 0xA000) {
            var_v0 = g_Ric.padPressed & 0x8000;
            if (RIC_facingLeft == 0) {
                var_v0 = g_Ric.padPressed & 0x2000;
            }
            if (var_v0 == 0) {
                goto block_10;
            }
        } else {
block_10:
            DecelerateX(0x1000);
        }
        if (g_Ric.vram_flag & 2) {
            func_us_801B8E80(3);
            g_Ric.high_jump_timer = 0;
            D_80076306 = 2;
        } else if ((u16)g_Ric.high_jump_timer >= 0x1D) {
            D_80076306 = 1;
            RIC_velocityY = -0x60000;
        }
        break;
    case 1:
        if (g_Ric.vram_flag & 2) {
            D_80076306 = 2;
            func_us_801B8E80(3);
            g_Ric.high_jump_timer = 0;
        } else {
            temp_v1 = RIC_velocityY + 0x6000;
            RIC_velocityY = temp_v1;
            if (temp_v1 > 0x8000) {
                var_s1 = 1;
            }
        }
        break;
    case 2:
        if ((u16)g_Ric.high_jump_timer >= 5) {
            var_s1 = 1;
        }
        break;
    }
    if (var_s1 != 0) {
        BO6_RicSetAnimation(&D_us_801820BC);
        BO6_RicSetStep(5);
    }
}