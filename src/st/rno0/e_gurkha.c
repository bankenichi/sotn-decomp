// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Gurkha entity 15: sync rotation to parent's rotation + offset (0x300 = approx. 270 degrees)
void func_801CF778(void) {
    Entity* currEnt15;
    Entity* ent15Parent;
    currEnt15 = g_CurrentEntity + 15;
    ent15Parent = currEnt15->ext.GH_Props.parent;
    currEnt15->ext.GH_Props.rotate = ent15Parent->ext.GH_Props.rotate + 0x300;  // 0x300 angle offset
}

static s32 func_801CF7A0(Entity* self) {
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
        func_801CE1E8(10);
        return;
    }

    if (g_CurrentEntity->ext.GH_Props.unk84 == 1) {
        otherEnt = g_CurrentEntity + 10;
    } else {
        otherEnt = g_CurrentEntity + 13;
    }

    step = func_801CE120(otherEnt, g_CurrentEntity->facingLeft);
    if (step != 0) {
        func_801CE1E8(7);
        return;
    }

    step = 5;

    if (dx < 48) {
        step = 7;
    }

    if (dx < 80) {
        step = 5;
    }

    if (dx > 128) {
        step = 8;
    }

    if (!g_CurrentEntity->ext.GH_Props.unk8E) {
        if (dx < 160) {
            g_CurrentEntity->ext.GH_Props.unk8E = 3;
            step = 6;
            g_CurrentEntity->ext.GH_Props.unk8C = 1;
        }
        if (dx < 64) {
            g_CurrentEntity->ext.GH_Props.unk8C = 0;
        }
    }

    if (step != g_CurrentEntity->step) {
        func_801CE1E8(step);
    }

    if (g_CurrentEntity->step == 7 && step == 5) {
        g_CurrentEntity->ext.GH_Props.unkB0[0] = 1;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/e_gurkha", EntityGurkha);

INCLUDE_ASM("st/rno0/nonmatchings/e_gurkha", EntityGurkhaWeapon);
