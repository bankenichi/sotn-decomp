// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

typedef enum {
    HAMMER_STEP_0,
    HAMMER_STEP_1,
    HAMMER_STEP_2,
    HAMMER_STEP_3,
    HAMMER_STEP_5 = 5,
    HAMMER_STEP_6,
    HAMMER_STEP_7,
    HAMMER_STEP_8,
    HAMMER_STEP_10 = 10,
    HAMMER_STEP_12 = 12,
    HAMMER_DYING = 24
} HammerSteps;

// Hammer is a complex construction made of 16 entities.
// EntityHammer is the pelvis, and itself +1, +2, etc up to +14
// are the body parts. +15 is the hammer (the weapon).
// these are useful names for those body parts.
// The arms and legs are in 2 pairs. There is a bright blue foreground arm,
// and a dim grey background arm. Foreground is unprefixed, background is BACK_
typedef enum {
    PELVIS,
    HEAD,
    TORSO,
    SHOULDER,
    ARM_UPPER,
    ARM_LOWER,
    BACK_SHOULDER,
    BACK_ARM_UPPER,
    BACK_ARM_LOWER,
    LEG_UPPER,
    LEG_LOWER,
    FOOT,
    BACK_LEG_UPPER,
    BACK_LEG_LOWER,
    BACK_FOOT,
    HAMMER_WEAPON
} partEntOffsets;

static s32 func_801CE4CC(Entity* self) {
    Entity* otherEnt;
    s32 step;
    s32 dx;

    if (g_CurrentEntity->ext.GH_Props.unk8E) {
        g_CurrentEntity->ext.GH_Props.unk8E--;
    }

    otherEnt = &PLAYER;
    dx = self->posX.i.hi - otherEnt->posX.i.hi;
    if (g_CurrentEntity->facingLeft) {
        dx = -dx;
    }

    if (dx < -16) {
        func_801CE1E8(HAMMER_STEP_10);
        return;
    }

    if (g_CurrentEntity->ext.GH_Props.unk84 == 1) {
        otherEnt = g_CurrentEntity + LEG_LOWER;
    } else {
        otherEnt = g_CurrentEntity + BACK_LEG_LOWER;
    }

    step = func_801CE120(otherEnt, g_CurrentEntity->facingLeft);
    if (step != 0) {
        func_801CE1E8(HAMMER_STEP_7);
        return;
    }
    step = func_801CE120(otherEnt, g_CurrentEntity->facingLeft ^ 1);
    if (step != 0) {
        func_801CE1E8(HAMMER_STEP_5);
        return;
    }

    switch (g_CurrentEntity->step) {
    case 8:
        step = 8;
        if (dx < 80) {
            step = 5;
        }
        break;

    default:
        step = 5;
        if (dx < 80) {
            step = 7;
        }
        if (dx > 160) {
            step = 8;
        }
        break;
    }

    if (!g_CurrentEntity->ext.GH_Props.unk8E) {
        if (dx < 96) {
            g_CurrentEntity->ext.GH_Props.unk8E = 3;
            step = 6;
        }
    }

    if (step != g_CurrentEntity->step) {
        func_801CE1E8(step);
    }

    if (g_CurrentEntity->step == 7 && step == 5) {
        g_CurrentEntity->ext.GH_Props.unkB0[0] = 1;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/e_hammer", EntityHammer);

INCLUDE_ASM("st/rno0/nonmatchings/e_hammer", EntityGurkhaBodyParts);

INCLUDE_ASM("st/rno0/nonmatchings/e_hammer", EntityHammerWeapon);
