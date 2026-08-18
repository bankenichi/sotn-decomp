/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO6:BO6_RicStepStand
   attempt: 2026-08-18 Luna effort benchmark shadow run
   model  : gpt-5.6-luna, xhigh
   body   : exact Stage A candidate recovered from the Codex task transcript
   decls  : evidence-backed declarations supplied by the root agent
   origin : src/boss/bo6/richter.c
   asm    : asm/us/boss/bo6/nonmatchings/richter/BO6_RicStepStand.s
   verdict: make_build completed; verify_build returned 80/81 with only
            build/us/BO6.BIN different. overlay_size_check.py reported
            BO6_RicStepStand is -0x4 bytes wrong.

   The model form below calls func_us_801B9DE4 with no argument. The root also
   tested an old-style declaration plus func_us_801B9DE4(0) at both call sites.
   That variant compiled but remained -0x4, so the hypothesis is exhausted.

   Do not apply this as a match. It is preserved as a compiling starting point
   for asm-differ and the permuter. */
extern void BO6_DisableAfterImage(s32, s32);
extern void BO6_RicSetAnimation(AnimationFrame*);
extern void func_us_801B9DE4(void);
extern AnimationFrame D_us_80181F1C[];
extern AnimationFrame D_us_80182130[];
extern AnimationFrame D_us_801822B8[];
extern AnimationFrame* RIC_anim;
extern s16 RIC_pose;
extern s16 RIC_poseTimer;

void BO6_RicStepStand(void) {
    if (BO6_RicCheckInput(0x4305C) == 0) {
        DecelerateX(0x2000);

        switch (RIC.step_s) {
        case 0:
            if (BO6_RicCheckFacing()) {
                func_us_801B9DE4();
            } else if (g_Ric.padPressed & PAD_UP) {
                BO6_RicSetAnimation(D_us_80181F1C);
                RIC.step_s = 1;
            }
            break;

        case 1:
            if (BO6_RicCheckFacing()) {
                func_us_801B9DE4();
            } else if (!(g_Ric.padPressed & PAD_UP)) {
                BO6_RicSetStand(0);
            }
            break;

        case 0x40:
            BO6_DisableAfterImage(1, 1);

            if ((u16)RIC_pose < 3) {
                BO6_RicCheckFacing();

                if (g_Ric.padPressed & PAD_DOWN) {
                    RIC_step = PL_S_CROUCH;
                    RIC_anim = D_us_80182130;
                    return;
                }
            }

            if (RIC_poseTimer < 0) {
                if (g_Ric.padPressed & PAD_SQUARE) {
                    g_Ric.unk46 = 2;
                    RIC.step_s++;
                    BO6_RicSetAnimation(D_us_801822B8);
                    BO6_RicCreateEntFactoryFromEntity(
                        g_CurrentEntity, BP_ARM_BRANDISH_WHIP, 0);
                } else {
                    g_Ric.unk46 = 0;
                    BO6_RicSetStand(0);
                }
            }
            break;

        case 0x41:
            BO6_DisableAfterImage(1, 1);

            if (!(g_Ric.padPressed & PAD_SQUARE)) {
                g_Ric.unk46 = 0;
                BO6_RicSetStand(0);
            }
            break;

        case 0x42:
            BO6_DisableAfterImage(1, 1);

            if ((u16)RIC_pose < 3) {
                BO6_RicCheckFacing();
            }

            if (RIC_poseTimer < 0) {
                g_Ric.unk46 = 0;
                BO6_RicSetStand(0);
            }
            break;
        }
    }
}
