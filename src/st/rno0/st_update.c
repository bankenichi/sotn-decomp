// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

s32 Random(void) {
    u32 temp_v0;

    temp_v0 = (g_randomNext * 0x01010101) + 1;
    g_randomNext = temp_v0;
    return (s32) (temp_v0 >> 0x18);
}

INCLUDE_ASM("st/rno0/nonmatchings/st_update", Update);

INCLUDE_ASM("st/rno0/nonmatchings/st_update", UpdateStageEntities);
