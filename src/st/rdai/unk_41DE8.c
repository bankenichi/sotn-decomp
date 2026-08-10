// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rdai.h"

// func_us_801C1DE8's candidate failed to build on this name alone. Defined by
// THIS overlay at src/st/rdai/e_init.c:132.
extern EInit g_EInitShield;

INCLUDE_ASM("st/rdai/nonmatchings/unk_41DE8", func_us_801C1DE8);

INCLUDE_ASM("st/rdai/nonmatchings/unk_41DE8", func_us_801C21E4);

INCLUDE_ASM("st/rdai/nonmatchings/unk_41DE8", func_us_801C2418);

INCLUDE_ASM("st/rdai/nonmatchings/unk_41DE8", func_us_801C3580);
