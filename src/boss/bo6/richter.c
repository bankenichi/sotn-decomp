// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo6.h"

INCLUDE_ASM("boss/bo6/nonmatchings/richter", func_us_801B4BD0);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", func_us_801B4EAC);

static void BO6_CheckBladeDashInput() {
    u16 step = RIC.step;

    if ((step == 1 || step == 2 || RIC.step == 3 || step == 4 || step == 5) &&
        (g_Ric.unk46 == 0) && (g_Ric.padTapped & 8)) {
        func_us_801BA9D0();
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_CheckHighJumpInput);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicMain);

extern s32 D_us_801CF3C8;
extern s32 D_us_801CF3CC;

void func_us_801B5A14(s32 arg0) {
    D_us_801CF3C8 = arg0;
    D_us_801CF3CC = 0;
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", RichterThinking);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", func_us_801B6998);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", EntityRichter);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepStand);

extern s32 BO6_RicCheckInput(s32);
extern void DecelerateX(s32);
extern s32 BO6_RicCheckFacing(void);
extern void BO6_RicSetStand(s32);
extern void BO6_RicSetSpeedX(s32);

/* Ric's walking step in BOSS/BO6: when no directional input is held,
 * decelerate and either stand still or resume walk speed while the
 * sub-step counter is still zero. */
void BO6_RicStepWalk(void) {
    /* 0x305C is the directional-pad bitmask checked for any held input */
    if (BO6_RicCheckInput(0x305C) == 0) {
        DecelerateX(0x2000);
        if (BO6_RicCheckFacing() == 0) {
            BO6_RicSetStand(0);
        } else if (RIC.step_s == 0) {
            BO6_RicSetSpeedX(0x14000);
        }
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepRun);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepJump);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepFall);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepCrouch);

extern u8 RIC_drawFlags;
extern s16 RIC_poseTimer;
extern s16 RIC_pose;

void BO6_RicResetPose(void) {
    RIC_drawFlags &= ~ENTITY_ROTATE;
    RIC_poseTimer = 0;
    RIC_pose = 0;
    g_Ric.unk44 = 0;
    g_Ric.unk46 = 0;
}

// Richter (BO6): record which side the player is on. The original reuses
// Richter's entityRoomIndex as this flag rather than the entity's own
// facingLeft (which lives at +0x14, RIC_facingLeft); the address here is
// RIC + 0x32, which the Entity layout names entityRoomIndex.
void func_us_801B77D8(void) {
    if (RIC.posX.i.hi - PLAYER.posX.i.hi <= 0) {
        RIC.entityRoomIndex = 0;
    } else {
        RIC.entityRoomIndex = 1;  // player is to Richter's left
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepHit);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepDead);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepStandInAir);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepEnableFlameWhip);

extern void BO6_RicSetStand(s32);
extern s16 RIC_poseTimer;

void BO6_RicStepHydrostorm(void) {
    if (RIC_poseTimer < 0) {
        BO6_RicSetStand(0);
        g_Ric.unk46 = 0;
    }
}

void BO6_RicStepGenericSubwpnCrash(void) {
    if (g_Ric.unk4E != 0) {
        BO6_RicSetStand(0);
        g_Ric.unk46 = 0;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepThrowDaggers);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepSlide);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepSlideKick);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepBladeDash);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", func_us_801B8E80);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepHighJump);
