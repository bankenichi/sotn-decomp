/* PRESERVED NEAR CANDIDATE
 * record: us:BOSS/BO6:BO6_RicStepHighJump
 * source: src/ric/pl_steps.c:RicStepHighJump
 * isolated score: 170
 * build proof: 80/81, only build/us/BO6.BIN failed
 *
 * The body aligns through its stack restoration. The sole structural delta is
 * the compiler's required jr $ra at 0x801B9134. That instruction and its delay
 * slot were split into the first empty function in src/boss/bo6/unused.c.
 * Preserve this candidate while the source boundary is corrected.
 */
extern AnimationFrame D_us_801820BC[];

void BO6_RicStepHighJump(void) {
    bool loadAnim;

    loadAnim = false;
    g_Ric.high_jump_timer++;
    switch (RIC.step_s) {
    case 0:
        if (g_Ric.padPressed & (PAD_LEFT | PAD_RIGHT)) {
            if (RIC.facingLeft) {
                if (!(g_Ric.padPressed & PAD_LEFT)) {
                    DecelerateX(FIX(0.0625));
                }
            } else {
                if (!(g_Ric.padPressed & PAD_RIGHT)) {
                    DecelerateX(FIX(0.0625));
                }
            }
        } else {
            DecelerateX(FIX(0.0625));
        }

        if (g_Ric.vram_flag & TOUCHING_CEILING) {
            func_us_801B8E80(3);
            g_Ric.high_jump_timer = 0;
            RIC.step_s = 2;
        } else if (g_Ric.high_jump_timer > 0x1C) {
            RIC.step_s = 1;
            RIC.velocityY = -0x60000;
        }
        break;
    case 1:
        if (g_Ric.vram_flag & TOUCHING_CEILING) {
            RIC.step_s = 2;
            func_us_801B8E80(3);
            g_Ric.high_jump_timer = 0;
        } else {
            RIC.velocityY += 0x6000;
            if (RIC.velocityY > 0x8000) {
                loadAnim = true;
            }
        }
        break;
    case 2:
        if (g_Ric.high_jump_timer > 4) {
            loadAnim = true;
        }
        break;
    }

    if (loadAnim) {
        BO6_RicSetAnimation(D_us_801820BC);
        BO6_RicSetStep(PL_S_JUMP);
    }
}
