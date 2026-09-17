// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rcen.h"

s16 func_us_8019A98C(s16 arg0, s16 arg1, s16 arg2) {
    s16 v_s1;
    s16 v_s0;

    arg1 &= 0xFFF;

    v_s1 = arg2 - arg1;
    v_s0 = v_s1;

    if (v_s1 > ROT(180)) {
        v_s0 = v_s1 - ROT(360);
    }
    if (v_s1 < ROT(-180)) {
        v_s0 = v_s1 + ROT(360);
    }

    if (abs(v_s0) > arg0) {
        if (v_s1 < 0) {
            v_s0 = arg1 - arg0;
        } else {
            v_s0 = arg1 + arg0;
        }
        return v_s0;
    }

    return arg2;
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;
extern GameApi g_api;

void func_us_8019AA04(s16 sfxId) {
    s32 yOffset;
    s16 vol;
    s16 pan;
    s32 xOffset;

    xOffset = g_CurrentEntity->posX.i.hi - 128;
    pan = (abs(xOffset) - 0x20) >> 5;
    if (pan > 8) {
        pan = 8;
    } else if (pan < 0) {
        pan = 0;
    }
    if (xOffset < 0) {
        pan = -pan;
    }

    vol = abs(xOffset) - 0x60;
    yOffset = abs(g_CurrentEntity->posY.i.hi - 128) - 112;
    if (yOffset > 0) {
        vol += yOffset;
    }
    if (vol < 0) {
        vol = 0;
    }
    vol = 0x40 - (vol >> 1);
    if (vol > 0) {
        g_api.PlaySfxVolPan(sfxId, vol, pan);
    }
}


INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", EntityShaft);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B5A4);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B6D4);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B8A8);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019C4EC);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019C610);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019C7B8);

extern u32 PrizeDrops;
extern EInit D_us_80180594;

// Initializes shaft prize-drop entity if its drop flag is unset, otherwise destroys it
void func_us_8019CDA0(Entity* self) {
    if (!(PrizeDrops & 4)) {
        if (self->step == 0) {
            InitializeEntity(D_us_80180594);
            return;
        }
    }
    DestroyEntity(self);
}

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019CDF8);
