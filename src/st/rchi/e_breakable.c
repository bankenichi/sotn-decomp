// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/*
 * RCHI's breakable entity is stage-specific and roughly twice the size of the
 * shared candle implementation (0x270 versus 0x134 bytes).
 */
// EntityBreakableDebris's candidate failed to build on this name alone.
// Declared in the shared src/st/e_breakable.h:9.
extern EInit g_EInitBreakable;

INCLUDE_ASM("st/rchi/nonmatchings/e_breakable", EntityBreakable);

INCLUDE_ASM("st/rchi/nonmatchings/e_breakable", EntityBreakableDebris);
