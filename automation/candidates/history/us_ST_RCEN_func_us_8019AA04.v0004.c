/* PERMUTER SEED -- legacy compiling body reconstructed as a whole file.
   record : us:ST/RCEN:func_us_8019AA04
   migration: ROADMAP #163; original bytes are immutable history
   content: WHOLE FILE (legacy body reconstructed)
   origin : src/st/rcen/e_shaft.c
   asm    : st/rcen/nonmatchings/e_shaft
   verdict: migration only; the original generation retains the
            measured compiler and checksum evidence

   Import through permuter_supervisor.py so quoted includes resolve at
   the recorded source depth. Do not apply this seed as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rcen.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
int abs(int x);
extern s32 (*g_api_PlaySfxVolPan)(s32 sfxId, s32 sfxVol, s32 sfxPan);
void InitializeEntity(u16 arg0[]);
s32 DestroyEntity();

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

void func_us_8019AA04(s32 arg0) {
        s32 dist_x;
        s32 dy_raw;
        s32 dy_abs;
        s32 dy_adj;
        s32 dist;
        s32 vol_raw;
        s32 vol;
    Entity* entity = g_CurrentEntity;

    // Horizontal distance from screen center (0x80) in fixed-point integer pixels
    s32 dx_raw = entity->posX.i.hi - 0x80;
    s32 dx_abs = dx_raw >= 0 ? dx_raw : -dx_raw;

    // Pan: (|dx| - 0x20) / 32, clamped to [-8, 8], sign follows dx_raw
    s32 pan = (dx_abs - 0x20) >> 5;            // arithmetic shift = divide by 32
    if (pan > 8) pan = 8;
    else if (pan < 0) pan = 0;
    if (dx_raw < 0) pan = -pan;

    // Volume distance components
    dist_x = dx_abs - 0x60;
    dy_raw = entity->posY.i.hi - 0x80;
    dy_abs = dy_raw >= 0 ? dy_raw : -dy_raw;
    dy_adj = dy_abs - 0x70;

    // Total distance: horizontal + positive vertical excess
    dist = dist_x;
    if (dy_adj > 0) dist += dy_adj;

    // Volume raw: (dist >> 1) if dist >= 0 (as s16), else 0
    // Assembly checks bit 15 of dist via sll 16 / bgez, so 16-bit sign matters.
    // Dist fits in 16 bits here, so 32-bit compare is equivalent.
    vol_raw = (dist >= 0) ? (dist >> 1) : 0;

    // Final volume: 0x40 - vol_raw, play only if > 0
    vol = 0x40 - vol_raw;
    if (vol > 0) {
        // API takes s32 args; low 16 bits of arg0/pan are sign-extended in asm
        g_api_PlaySfxVolPan((s16)arg0, vol, (s16)pan);
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
