// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo7.h"

u16 PrizeDrops[] = {
    ITEMDROP_SMALL_HEART,
    ITEMDROP_SMALL_HEART,
};

asm(".globl D_us_80180564\n"
    ".set D_us_80180564, PrizeDrops");
