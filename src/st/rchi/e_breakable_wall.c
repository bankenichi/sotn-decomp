// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/*
 * The reverse-stage wall mirrors velocity, tile traversal, positions, and map
 * coordinates throughout both functions; it is not a constants-only CHI port.
 */
// EntityBreakableWallDebris's candidate failed to build on this name alone.
// Declared in the shared src/st/e_fire_warg.h:11. An unused extern emits no
// code; this only removes the wall the retry would hit again.
extern EInit g_EInitCommon;

INCLUDE_ASM("st/rchi/nonmatchings/e_breakable_wall", EntityBreakableWallDebris);

INCLUDE_ASM("st/rchi/nonmatchings/e_breakable_wall", EntityBreakableWall);
