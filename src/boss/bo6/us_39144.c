// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo6.h"

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9144);

// Empty stub
void func_us_801B9338(void) {}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9340);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B94CC);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B96F4);

extern u16 RIC_step;
extern u16 D_80076306;

// Richter (BO6): set state machine step and clear related flag
void BO6_RicSetStep(s32 step) {
    RIC_step = step;
    D_80076306 = 0;
}

// Richter (BO6): set animation and clear pose state
void BO6_RicSetAnimation(AnimationFrame *animFrame) {
    g_CurrentEntity->anim = animFrame;
    g_CurrentEntity->poseTimer = 0;
    g_CurrentEntity->pose = 0;
}

// Richter (BO6): reduce X velocity toward zero by deceleration amount, clamping at 0
void DecelerateX(s32 deceleration) {
    s32 velocityX;
    s32 newVelocityX;
    s32 newVelocityX_2;

    velocityX = g_CurrentEntity->velocityX;
    if (velocityX < 0) {
        newVelocityX = deceleration + velocityX;  // moving left, add deceleration
        g_CurrentEntity->velocityX = newVelocityX;
        if (newVelocityX > 0) {  // overshot to positive
            g_CurrentEntity->velocityX = 0;
        }
    } else {
        newVelocityX_2 = velocityX - deceleration;  // moving right, subtract deceleration
        g_CurrentEntity->velocityX = newVelocityX_2;
        if (newVelocityX_2 < 0) {  // overshot to negative
            g_CurrentEntity->velocityX = 0;
        }
    }
}

// Richter (BO6): reduce Y velocity toward zero by deceleration amount, clamping at 0
void DecelerateY(s32 deceleration) {
    s32 velocityY;
    s32 newVelocityY;
    s32 newVelocityY_2;

    velocityY = g_CurrentEntity->velocityY;
    if (velocityY < 0) {
        newVelocityY = deceleration + velocityY;  // moving up, add deceleration
        g_CurrentEntity->velocityY = newVelocityY;
        if (newVelocityY > 0) {  // overshot to positive
            g_CurrentEntity->velocityY = 0;
        }
    } else {
        newVelocityY_2 = velocityY - deceleration;  // moving down, subtract deceleration
        g_CurrentEntity->velocityY = newVelocityY_2;
        if (newVelocityY_2 < 0) {  // overshot to negative
            g_CurrentEntity->velocityY = 0;
        }
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicCheckFacing);

// Richter (BO6): set X velocity with facing direction applied
void BO6_RicSetSpeedX(s32 speed) {
    s32 signedSpeed;

    signedSpeed = speed;
    if (g_CurrentEntity->facingLeft == 1) {
        signedSpeed = -signedSpeed;  // negate if facing left
    }
    g_CurrentEntity->velocityX = signedSpeed;
}

extern u16 D_8007630A;
extern s32 RIC_velocityX;

// Richter (BO6): set global RIC_velocityX with facing direction applied
void func_us_801B9ACC(s32 speed) {
    s32 signedSpeed;

    signedSpeed = speed;
    if (D_8007630A == 1) {  // facing left flag
        signedSpeed = -signedSpeed;  // negate if facing left
    }
    RIC_velocityX = signedSpeed;
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicSetInvincibilityFrames);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_DisableAfterImage);

extern s8 D_80076410;
extern s8 D_80076411;
extern s8 D_80076412;
extern s8 D_80076413;

// Richter (BO6): clear animation control fields (likely afterimage/special effect data)
void func_us_801B9C14(void) {
    D_80076413 = 0;
    D_80076412 = 0;
    D_80076411 = 0;
    D_80076410 = 0;
}

void BO6_RicSetStep(s32);

// Richter (BO6): set step to 0xF0 (possibly a special state)
void func_us_801B9C3C(void) {
    BO6_RicSetStep(0xF0);
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicSetCrouch);

extern s32 RIC_velocityY;
extern AnimationFrame ric_anim_stand[];

// Richter (BO6): transition to the standing state - zero velocity, clear
// unk44 (crouch/step-related flag), set step 1 and the standing animation
void BO6_RicSetStand(s32 velocityX) {
    RIC_velocityX = velocityX;
    RIC_velocityY = 0;
    g_Ric.unk44 = 0;
    BO6_RicSetStep(1);
    BO6_RicSetAnimation(ric_anim_stand);
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9D74);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9DE4);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9E70);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicSetFall);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BA050);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicCheckSubwpnChainLimit);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicDoSubweapon);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicDoAttack);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicDoCrash);

// Richter (BO6): set step to 0x17 (death prologue/dying state)
void BO6_RicSetDeadPrologue(void) {
    BO6_RicSetStep(0x17);
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicSetSlide);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicSetSlideKick);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BA9D0);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicCheckInput);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicGetFreeEntity);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicGetFreeEntityReverse);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BB314);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BB370);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicCheckSubweapon);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BB5BC);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityHitByHoly);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityHitByDark);

// Empty stub
void func_us_801BBBC0(void) {}

// Empty stub
void func_us_801BBBC8(void) {}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BBBD0);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicCreateEntFactoryFromEntity);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityFactory);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC2F0);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC3E0);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC4F8);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC5C8);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC678);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityHitByCutBlood);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BD0B8);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BD384);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BD47C);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityPlayerBlinkWhite);
