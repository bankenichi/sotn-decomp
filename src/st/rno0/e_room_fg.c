// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// rno0 exports the common descriptor under an OVL_EXPORT name, the same idiom
// e_clock_room.c and e_red_door.c use in this directory.
#define g_EInitCommon OVL_EXPORT(EInitCommon)

#include "../e_room_fg.h"
