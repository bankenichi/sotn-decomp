// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/e_blade", func_801D0A00);

static void func_801D0B40(void) {
    Entity* ent;
    s16* unk88;

    ent = g_CurrentEntity + 15;
    unk88 = ent->ext.et_801D0B40.unk88;
    ent->ext.et_801D0B40.unk84 = unk88[0x4E] - 0x600;

    ent = g_CurrentEntity + 16;
    unk88 = ent->ext.et_801D0B40.unk88;
    ent->ext.et_801D0B40.unk84 = unk88[0x4E] - 0x600;
}

INCLUDE_ASM("st/rno0/nonmatchings/e_blade", func_801D0B78);

INCLUDE_ASM("st/rno0/nonmatchings/e_blade", EntityBlade);

INCLUDE_ASM("st/rno0/nonmatchings/e_blade", EntityBladeWeapon);
