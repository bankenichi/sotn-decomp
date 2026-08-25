/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO1:func_801CDD00
   source : upstream/master:src/boss/rbo8_psp/unk_DEB8.c
   target : src/boss/rbo1/unk_12274.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo1.h"

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", EntityBreakable);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801923A8);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80192C5C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80192F84);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801936FC);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80193C2C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80193E24);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80194108);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_8019ED80_from_rbo2);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", polarPlacePartsWithAngvel);

void func_801CDD00(Entity* entity, s16 arg1, s16 arg2) {
    s16 temp_t0 = arg1 - entity->ext.GH_Props.rotate;

    if (temp_t0 > 0x800) {
        temp_t0 = temp_t0 - 0x1000;
    }

    if (temp_t0 < -0x800) {
        temp_t0 = temp_t0 + 0x1000;
    }

    temp_t0 = temp_t0 / arg2;
    entity->ext.GH_Props.rotVel = temp_t0;
    entity->ext.GH_Props.unkA4 = arg1;
}

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CDD80);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CDF1C);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CE1E8);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_801CE228);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", polarPlacePartsList);

// decompiled in src/boss/bo1/e_explosion_flame.c
INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_8019D260_from_rcen);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_801947E4);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", func_us_80194C50);

INCLUDE_ASM("boss/rbo1/nonmatchings/unk_12274", EntityBossRoomBlock);
