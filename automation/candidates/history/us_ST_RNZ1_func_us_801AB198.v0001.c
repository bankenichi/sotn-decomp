/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNZ1:func_us_801AB198
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rnz1/e_dw_batwings.c
   target : src/st/rnz1/unk_29914.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
int abs(int x);

#include "../approach_s16.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int rcos(int a);
/* End permuter-seed writer declarations. */



INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801A9994);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801A9DB8);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityFrozenShadeCrystal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AAF00);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB04C);

void func_801B2CF8(Primitive* prim) {
    s32 i;
    // Clear the complete object one word at a time, starting at its real first
    // member. The target uses a word loop rather than individual fields.
    s32* ptr = (s32*)&prim->next;
    s32 size = sizeof(*prim) / sizeof(*ptr);

    for (i = 0; i < size; i++) {
        *ptr++ = 0;
    }
}



void func_us_801AB16C(s32* src, s32* dst, s32 count) {
    s32 i;

    // CODEGEN: The target overwrites incoming a2 with 13, then uses a register
    // slt. Keeping the bound in the third parameter preserves that exact shape.
    count = 13;

    for (i = 0; i < count; i++) {
        *dst++ = *src++;
    }
}


void func_us_801AB198(batWingStruct* arg0) {
    s32 var_s2;
    s32 var_s1;
    s32 var_s0;

    var_s2 = arg0->unk8 * 0x50 / 0x100;
    var_s1 = arg0->unk0;
    arg0->unk4 =
        (var_s2 * rcos(arg0->unkE) / 0x1000) +
        (((arg0->unk18 * rcos(arg0->unk28 / 0x100)) / 0x1000) * 0x3E) / 0x100;
    var_s0 = var_s1 - arg0->unk4;
    arg0->unk8 += var_s0;
    arg0->unk10 += arg0->unk8;
    var_s2 = (arg0->unk1C + arg0->unk8) * 0x90 / 0x100;
    var_s1 = arg0->unk14;
    arg0->unk18 = var_s2 * rcos(arg0->unk24) / 0x1000;
    var_s0 = var_s1 - arg0->unk18;
    arg0->unk1C += var_s0;
    arg0->unk28 += arg0->unk1C;
    if (arg0->unk10 > FIX(3.5)) {
        arg0->unk10 = FIX(3.5);
        arg0->unk8 = 0;
    }
    if (arg0->unk10 < FIX(-2.5)) {
        arg0->unk10 = FIX(-2.5);
        arg0->unk8 = 0;
    }
    if ((arg0->unk28 - arg0->unk10) > FIX(5)) {
        arg0->unk28 = (arg0->unk10 + FIX(5));
        arg0->unk1C = 0;
    }
    if ((arg0->unk28 - arg0->unk10) < FIX(-2.5)) {
        arg0->unk28 = (arg0->unk10 + FIX(-2.5));
        arg0->unk1C = 0;
    }
}


INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB380);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB768);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABA38);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABB58);

void RNZ1_Unused801ABDC0(void) {}

void func_us_801ABDC8(s32* values) {
    values[0] -= 0x400;
    values[5] -= 0x400;
}


INCLUDE_RODATA("st/rnz1/nonmatchings/unk_29914", D_us_801A6050);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABDE4);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityBossDoorTrigger);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityBossDoors);
