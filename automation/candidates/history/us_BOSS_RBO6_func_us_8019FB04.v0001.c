/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO6:func_us_8019FB04
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo6/unk_1D690.c
   target : src/boss/rbo6/unk_1D690.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
u8 AnimateEntity(u8 frames[], Entity* entity);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", EntityBreakable);

// decompiled in src/boss/bo1/e_explosion_flame.c
INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019D260_from_rcen);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019D330_from_rcen);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019DB9C);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019EADC);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019EE30);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019F1CC);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019FA78);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern s32 D_us_80180704[]; /* retained BOSS/RBO6 data asm/us/boss/rbo6/data/678.data.s, size 0x4 */
extern s32 D_us_801806E8[]; /* retained BOSS/RBO6 data asm/us/boss/rbo6/data/678.data.s, size 0x4 */
extern s32 D_us_801807F4[]; /* retained BOSS/RBO6 data asm/us/boss/rbo6/data/678.data.s, size 0x14 */
extern EInit D_us_80180540;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void func_us_8019FB04(Entity* self) {
    extern u16 D_us_80180704;
    extern s32 D_us_801806E8;
    extern u8* D_us_801807F4[];
    extern u16 D_us_80180540;
    extern void InitializeEntity(u16*);

    u16 value;

    self->palette = D_us_80180704;
    switch (self->step) {
    case 0:
        InitializeEntity(&D_us_80180540);
        /* fall through */
    case 1:
        AnimateEntity(D_us_801807F4[self->params], self);
        value = g_Entities[E_BOSS_WEAPON].posX.i.hi;
        self->posX.i.hi = value;
        value = g_Entities[E_BOSS_WEAPON].posY.i.hi;
        self->posY.i.hi = value;
        break;
    }

    if (D_us_801806E8 != 0) {
        self->animCurFrame = 0;
        self->hitboxState = 0;
    }
}


INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019FBC0);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019FCB4);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A01A4);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A0710);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A0860);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A0AB4);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A0DC0);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A1150);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A11DC);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A1B38);
