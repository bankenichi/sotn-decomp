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

// BO6_CheckHighJumpInput's two RIC_ scalars must be declared BEFORE this
// point. RIC_velocityY is declared further down at its other use site, which is
// after this function, so it is repeated here rather than moved: moving it
// would reorder declarations that other functions already depend on.
//
// Both are FLAT externs, not RIC.step / RIC.velocityY, and the assembly says
// so: BO6_CheckHighJumpInput.s builds its own lui/%lo pair for each
// (`lui $a0, %hi(RIC_step)` / `lhu $a0, %lo(RIC_step)($a0)`), which is the
// signature this file already documents at the RicStepStandInAir comment as
// marking a plain scalar global rather than a struct member. lhu is a 16-bit
// unsigned load, hence u16.
extern u16 RIC_step;
extern s32 RIC_velocityY;

/* BO6: when the player is in a step that allows a high jump (steps 1/3/4, or
   step 5 while falling faster than 1.0 px/frame) and the jump button was just
   tapped, hand off to func_us_801BA050 to perform the high jump. */
// Takes NO argument. The jal's delay slot is a bare nop and nothing
// sets up $a0; the register merely still holds RIC_step from the test
// at the top of the function. Declaring a parameter and passing
// RIC_step made GCC re-emit the lui/lhu pair to load it, which is
// exactly the 8 bytes (2 instructions) the overlay came out long by.
extern void func_us_801BA050(void);

void BO6_CheckHighJumpInput(void) {
    /* Step gates: 3, 1, 4 always qualify; step 5 only qualifies when falling
       fast (0x10000 = 1.0 in fixed point, so > 1.0 px/frame downward). */
    if (RIC_step == 3 || RIC_step == 1 ||
        (RIC_step == 5 && RIC_velocityY > 0x10000) ||
        RIC_step == 4)
    {
        /* unk46: a lock flag that must be clear so the jump cannot re-fire;
           padTapped bit 1 (0x2) is the jump-button tap. */
        if (g_Ric.unk46 == 0 && (g_Ric.padTapped & 2)) {
            func_us_801BA050();
        }
    }
}


INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicMain);

extern s32 D_us_801CF3C8;
extern s32 D_us_801CF3CC;

void func_us_801B5A14(s32 arg0) {
    D_us_801CF3C8 = arg0;
    D_us_801CF3CC = 0;
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", RichterThinking);

// TRIED AND REVERTED 2026-08-16. Upstream has a C body for this
// (src/boss/bo6/richter.c) and it links here, but it does not match: the
// build comes out ONE INSTRUCTION LONG at +21, a load-delay nop the original
// does not have, and every later instruction is shifted by that one word.
//
// So this is a codegen difference inside case 10/case 11, not a naming or
// symbol problem -- the two `(g_CastleFlags[SHAFT_ORB_DEFEATED] == 0) &&
// (g_DemoMode == Demo_None)` tests are the only candidates, and getting the
// scheduler to drop that nop is permuter work, not transcription. Left as a
// stub deliberately rather than committed as a near-miss.
//
// The reverted body is in the upstream file if it is wanted as a permuter
// seed; nothing else here depends on it.
INCLUDE_ASM("boss/bo6/nonmatchings/richter", func_us_801B6998);

extern EInit D_us_80180400;
extern s32 D_us_801CF3E0;
extern s32 D_us_801CF3E4;

// HARVESTED from upstream/master src/boss/bo6/richter.c.
//
// TWO RENAMES, both the same BO6_ prefix divergence between this fork and
// upstream, and both confirmed against config/symbols.us.bobo6.txt rather
// than guessed:
//   upstream RicMain()            -> BO6_RicMain           (INCLUDE_ASM above)
//   upstream DisableAfterImage()  -> BO6_DisableAfterImage (= 0x801B9B78)
// Everything else is upstream's verbatim, including the entity sweep from
// STAGE_ENTITY_START + 4 up to 144, which clears the room before the duel.
void EntityRichter(Entity* self) {
    Entity* entity;
    s32 i;

    g_Ric.unk6A = RIC.hitPoints;
    if (self->step == 0) {
        InitializeEntity(D_us_80180400);
        func_us_801B4BD0();
        entity = &g_Entities[STAGE_ENTITY_START + 4];
        for (i = STAGE_ENTITY_START + 4; i < 144; i++, entity++) {
            DestroyEntity(entity);
        }
        g_Ric.unk6E = g_Ric.unk6A = g_Ric.unk6C = RIC.hitPoints;
        D_us_801CF3E4 = g_Ric.unk6E / 2;
        D_us_801CF3E0 = 0;
        g_Ric.unk70 = RIC.hitboxState;
        func_us_801B5A14(18);
        BO6_DisableAfterImage(1, 48);
    } else {
        RichterThinking();
        BO6_RicMain(); // equivalent to EntityDoppleganger{10,40}
        func_us_801BBBD0();
        func_us_801B6998();
    }
    g_Ric.unk6C = g_Ric.unk6A;
}

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

/* BO6_RicStepEnableFlameWhip: BO6 (Richter) flame-whip entry step.
 * When the anim frame hits the flame-swing pose (0xB5) with poseTimer at 1,
 * spawn the whip entity and play its unleash SFX. Once the pose timer goes
 * negative (abort / animation end), drop back to the standing pose and kick
 * the dash-recovery timer. */
extern s16 RIC_animCurFrame; /* 0x8007632E -- flame-step swing frame */

void BO6_RicStepEnableFlameWhip(void) {
    /* Both comparisons branch to the shared end on failure, so && is exact. */
    if (RIC_animCurFrame == 0xB5 && RIC_poseTimer == 1) {
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x23, 0); /* whip entity */
        g_api_PlaySfx(0x62F);
    }

    /* poseTimer < 0 -> leave the flame step and reset its state. */
    if (RIC_poseTimer < 0) {
        BO6_RicSetStand(0);
        g_Ric.unk46 = 0;                 /* g_Ric + 0x396: step state latch */
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x450021, 0);
        g_Ric.timers[0] = 0x800;         /* g_Ric + 0x330: dash-timer reload */
    }
}

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

extern s32 D_us_801D07F8;

// BO6 Richter throw daggers step: manages a countdown timer while
// throwing, and allows cancellation via pad input.
void BO6_RicStepThrowDaggers(void) {
    s32 temp_v0;

    if (g_Entities[64].step_s == 0) {
        D_us_801D07F8 = 0x200;
        g_Entities[64].step_s += 1;
    } else {
        BO6_RicCheckFacing();
        temp_v0 = D_us_801D07F8 - 1;
        D_us_801D07F8 = temp_v0;
        if (temp_v0 == 0) {
            /* unk46 is an s16 field in PlayerState (not Entity hitboxWidth) */
            g_Ric.unk46 = 0;
            BO6_RicSetStand(0);
            /* unk4E is an s16 field in PlayerState */
            g_Ric.unk4E = 1;
        }
    }
    /* padTapped is a s32 field in PlayerState at offset 0x31C */
    if (g_Ric.padTapped & 0x40) {
        func_us_801B9E70();
        g_Ric.unk46 = 0;
        g_Ric.unk4E = 1;
        D_us_801D07F8 = 0;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepSlide);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepSlideKick);

#include "bo6.h"

/*
 * BO6 version of Ric's dashing idle-step: the overlay's twin of RicStepBladeDash.
 * Keeps welding Ric to the sabre dash, decays the forward velocity, and every
 * 4 ticks while in the 0x20018 costume it spawns a slide-dust burst.
 */
void BO6_RicStepBladeDash(void) {
    DecelerateX(0x1C00); /* drag the dash velocity down so the squeal skid stops */

    if (RIC_poseTimer < 0) {                /* idle pose expired -> stand back up */
        g_Ric.unk46 = 0;                    /* offset 0x396: clear the dash-hold flag */
        BO6_RicSetStand(0);
        return;
    }
    /* if we are no longer in the dash pose range and are not flagged airborne */
    if ((u16)RIC_pose >= 0x12U && !(g_Ric.vram_flag & 1)) {
        g_Ric.unk46 = 0;                    /* offset 0x396 */
        BO6_RicSetFall();
        return;
    }
    /* while the dash pose is active, seed a smoke entity every 4 game ticks */
    if ((g_GameTimer & 3) == 0 && (u16)RIC_pose < 0x12U && (g_Ric.vram_flag & 1)) {
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x20018, 0);
    }
    /* final slash end: read pose as a word so entity factory id 0 fires exactly
     * once when the pose counter has been pushed into the 0x10012 delta */
    if (*(s32 *)&RIC_pose == 0x10012 && (g_Ric.vram_flag & 1)) {
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", func_us_801B8E80);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepHighJump);
