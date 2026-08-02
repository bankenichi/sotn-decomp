// SPDX-License-Identifier: AGPL-3.0-or-later
#include <common.h>

// 0xC00 of anonymous bss sitting between create_entity's 0x10 and the
// giantbro_helpers block at 0x54AC8. Nothing in the overlay names it, so there
// is no symbol to decompile; it exists to hold the address space so the
// segments either side land where the linker script expects.
//
// Same idiom and same size as src/st/np3/bss.c and src/st/nz0/bss.c.
STATIC_PAD_BSS(0xC00);
