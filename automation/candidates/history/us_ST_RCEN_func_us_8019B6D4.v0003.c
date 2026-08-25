/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RCEN:func_us_8019B6D4
   score  : 2240
   receipt: nonmatchings/.adapt-scores/20260824-195218-1906-507437/func_us_8019B6D4/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rcen/e_shaft.c
   asm    : asm/us/st/rcen/nonmatchings/e_shaft/func_us_8019B6D4.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rcen.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int abs(int x);
void InitializeEntity(u16 arg0[]);
u8 AnimateEntity(u8 frames[], Entity* entity);
void SetStep(u8 step);
void MoveEntity();
long ratan2(long y, long x);
int rcos(int a);
int rsin(int a);
long SquareRoot0(long a);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */



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

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019AA04);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", EntityShaft);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B5A4);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180570;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

extern u32 PrizeDrops;
extern EInit D_us_80180570;
extern s32 D_us_80180844[];

void func_us_8019B6D4(Entity* self) {
    s16 angle;
    s32 dx;
    s32 dy;
    s32 dist;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180570);
        self->blendMode = 0x30;
        self->drawFlags = 8;
        self->opacity = 0x60;
        self->animCurFrame = 0x23;
        break;

    case 1:
        if (PrizeDrops & 1) {
            self->step++;
        }
        break;

    case 2:
        if (AnimateEntity(D_us_80180844, self) == 0) {
            SetStep(3);
        }
        break;

    case 3:
        MoveEntity();
        dx = g_Entities[0].posX.i.hi - self->posX.i.hi;
        dy = g_Entities[0].posY.i.hi - self->posY.i.hi;
        angle = ratan2(dy, dx);
        self->velocityX = rcos(angle) << 4;
        self->velocityY = rsin(angle) << 4;
        dist = SquareRoot0(dx * dx + dy * dy);
        if (dist < 2) {
            self->posX.i.hi = g_Entities[0].posX.i.hi;
            self->posY.i.hi = g_Entities[0].posY.i.hi;
            self->step++;
        }
        break;

    case 4:
        self->opacity -= 8;
        if (self->opacity < 0) {
            PrizeDrops |= 2;
            DestroyEntity(self);
        }
        break;
    }
}

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
