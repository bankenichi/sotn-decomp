// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Shimmed 2026-08-17. The body is the shared implementation in
// src/st/e_thornweed_corpseweed.h, adopted verbatim from upstream; see the note
// there. The three constants are RNO0's, taken from upstream's own
// src/st/rno0/e_thornweed_corpseweed.c, and the matching .data slot is declared
// as [0x1DD4, .data, e_thornweed_corpseweed] in config/splat.us.strno0.yaml.
#define CORPSEWEED_TPAGE 0x14
#define CORPSEWEED_PAL 0x219
#define CORPSEWEED_PROJ_PAL 0x21C
#include "../e_thornweed_corpseweed.h"
