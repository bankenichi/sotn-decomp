// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rcen.h"

INCLUDE_ASM("st/rcen/nonmatchings/unk_1F0D8", func_8018F8EC);

INCLUDE_ASM("st/rcen/nonmatchings/unk_1F0D8", func_us_8019F148);

INCLUDE_ASM("st/rcen/nonmatchings/unk_1F0D8", func_us_8019F5F0);

INCLUDE_ASM("st/rcen/nonmatchings/unk_1F0D8", func_us_8019F9C0);

extern EInit g_EInitCommon;

// Initializes entity animation/priority on first step, mirroring func_us_801B4148 in bo0/no2_bg
void func_us_801B4148_from_bo0(Entity* self) {
    if (self->step == 0) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = 6;
        self->zPriority = 0x63;
    }
}

// Initializes entity animation/rotation state on first step, mirroring the NO4 idiom
void func_us_801C123C_from_no4(Entity* self) {
    if (self->step == 0) {
        InitializeEntity(g_EInitCommon);
        self->animSet = -0x7FFF;
        self->animCurFrame = 7;
        self->drawFlags = ENTITY_ROTATE;
        self->rotate = 0x800;
        self->zPriority = self->zPriority + 1;
    }
}
