// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Was a private copy of `Random` plus INCLUDE_ASM stubs for `Update` and
// `UpdateStageEntities`. src/st/st_update.h defines all three and 28 stages
// already shim it.
//
// rno0 needed THREE segments before this could work, and only the first was
// obvious:
//   .data, st_update at 0x1048  - the header's `unused` and UNK_Invincibility0
//   .bss,  st_update at 0x54B4C - 0x40 of uninitialised storage, previously
//                                 extracted as D_us_801D4B4C
//   c,     st_update at 0x37324 - already present
//
// The bss one is the trap. Without it the storage is still emitted, just
// appended after every other bss object, which silently pushed g_Statues (and
// the whole overlay) 0x40 higher.
#include "../st_update.h"
