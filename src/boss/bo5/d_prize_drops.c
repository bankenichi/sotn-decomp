// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

u16 PrizeDrops[] = {
    0x4000,
    ITEMDROP_SMALL_HEART,
};

asm(".globl D_us_80180B78\n"
    ".set D_us_80180B78, PrizeDrops");
