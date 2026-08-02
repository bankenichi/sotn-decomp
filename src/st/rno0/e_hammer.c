// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// rno0's giant-bro entities sit 8 z-levels forward of every other stage's.
// That single difference -- three instructions, 0xC -- is why this file could
// not be a shim. Found 2026-08-02 by aligning rno0's assembly against no2's
// compiled bytes with automation/fn_diff.py.
#define GIANTBRO_ZPRIORITY_ADJUST 8

// no2.h and np3.h declare these; rno0.h does not. Without them GCC 2.7 treats
// the identifier as an implicit int and passes its VALUE instead of its
// address, so InitializeEntity was called with 0. That cost 2 instructions per
// call site and was invisible except as a size delta, because an implicit
// declaration is only a WARNING.
extern EInit g_EInitHammer;
extern EInit g_EInitHammerWeapon;
extern EInit g_EInitGurkha;
extern EInit g_EInitBlade;

#include "../e_hammer.h"
