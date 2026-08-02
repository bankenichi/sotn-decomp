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
    /* 0x305C is a capability mask, NOT pad state. BO6_RicCheckInput never
       reads the pad itself; it ANDs this argument against fixed bits to
       decide which transitions (crouch, jump, attack, dash) the current
       state is allowed to take. Every caller passes a different constant:
       BO6_RicStepStand 0x4305C, BO6_RicStepCrouch 0x4105C, BO6_RicStepJump
       0x11009. The same idiom appears in src/boss/bo4/unk_45354.c. */
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

extern void func_us_801B9E70(void);

// Richter (BO6): the falling step. Twin of RicStepFall in src/ric/pl_steps.c,
// with no divergence beyond the g_Player -> g_Ric / PLAYER -> RIC swap.
//
// 0x9009 is the same capability mask RIC passes:
// CHECK_GROUND(1) | CHECK_FACING(8) | CHECK_ATTACK(0x1000) |
// CHECK_GRAVITY_FALL(0x8000). Spelled numerically because bo6.h pulls in
// ric_shared.h but not src/ric/ric.h, where the CHECK_* enum lives.
void BO6_RicStepFall(void) {
    if (BO6_RicCheckInput(0x9009)) {
        return;
    }
    DecelerateX(FIX(1. / 16));
    switch (RIC.step_s) {
    case 0:
        if (g_Ric.timers[PL_T_5] && (g_Ric.padTapped & PAD_CROSS)) {
            func_us_801B9E70();
        } else if (BO6_RicCheckFacing()) {
            BO6_RicSetSpeedX(FIX(0.75));
        }
        break;
    }
}

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

extern s32 RIC_velocityY;
extern AnimationFrame D_us_801820B0[];
extern void BO6_RicSetStep(s32);
extern void BO6_RicSetAnimation(AnimationFrame*);

// Richter (BO6): the "hang in the air" step. Twin of RicStepStandInAir in
// src/ric/pl_steps.c, MINUS its trailing `if (g_Player.unk72) PLAYER.velocityY
// = 0;` clamp. All three exits jump straight to the epilogue at 0x385CC and
// nothing in the function loads g_Ric + 0x3C2, so adding that block would be
// inventing behaviour.
//
// RIC_velocityY is used as a flat extern rather than RIC.velocityY because the
// assembly builds a fresh lui/%lo pair for each of the three accesses, while
// step_s gets its address hoisted into $v1 once. That asymmetry is the
// signature of a plain scalar global against a struct member.
void BO6_RicStepStandInAir(void) {
    if (RIC.step_s == 0) {
        RIC_velocityY += 0x3800;
        if (RIC_velocityY > 0) {
            RIC_velocityY = 0;
            RIC.step_s = 1;
        }
    } else if (g_Ric.unk4E) {
        g_Ric.unk46 = 0;
        BO6_RicSetStep(PL_S_JUMP);
        BO6_RicSetAnimation(D_us_801820B0);
        g_Ric.unk44 = 0;
    }
}

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
