// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// no0 and mar name the shared init struct g_EInitCommon; rno0 exports it as
// OVL_EXPORT(EInitCommon) = RNO0_EInitCommon at 0x80180AB0. Without this the
// header's reference resolves to zero and every InitializeEntity passes NULL.
// Same treatment as e_clock_room.c.
extern EInit OVL_EXPORT(EInitCommon);
#define g_EInitCommon OVL_EXPORT(EInitCommon)

// This replaces src/st/rno0/unk_39A8C.c, which held a hand-written copy of
// EntityIsNearPlayer (as func_us_801B9A8C) plus an INCLUDE_ASM for
// EntityRedDoor. The copy was character-identical to the header's version,
// including the 16 and 32 constants and the four separate s16 locals.
//
// g_RedDoorTiles and D_us_80181134 are bound by naming them in
// config/symbols.us.strno0.txt rather than being re-declared here.
#include "../e_red_door.h"
