// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rdai.h"

#include "../e_spear_guard_collision.h"

#include "../approach_s16.h"

// Both candidates below failed to build on these names alone.
//
// g_EInitRdaiUnk1F IS reachable via ../e_rdai_unk1f.h, but that include sits
// BELOW this point, so a body substituted into the func_us_801BF830 stub
// cannot see it. Position is the whole problem here; declaring it above the
// stub is what makes the retry viable.
//
// D_us_80180884 is defined by THIS overlay at src/st/rdai/e_init.c:127.
extern EInit g_EInitRdaiUnk1F;
extern EInit D_us_80180884;

INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801BF830);

// Child parts share one implementation; only the fixed EInit address is local.
#include "../e_rdai_unk1f.h"

// These functions do not match from portable C under the PSX compiler.
INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801BFE6C);

INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801C0240);

INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801C0528);

INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801C0898);
