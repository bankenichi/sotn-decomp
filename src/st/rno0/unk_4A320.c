// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Shimmed 2026-08-17. The body is the shared implementation in
// src/st/giantbro_helpers_2.h, adopted verbatim from upstream.
//
// This file was split out of giantbro_helpers.c earlier to match the upstream
// file boundary: src/st/giantbro_helpers.h ends at func_801CDFD8, and
// src/st/no2/4966C.c and src/st/np3/4E04C.c both BEGIN at func_801CE04C with
// exactly this set of functions. The split was the prerequisite; the header is
// what it was for.
//
// The header supplies all SEVEN functions this file holds, which is more than
// the two the name-based harvest scan reported: func_801CE04C, func_801CE120
// and func_801CE3FC were INCLUDE_ASM stubs, and func_801CE1E8, func_801CE228,
// polarPlacePartsList and func_801CE2CC were hand-written copies kept in sync
// by hand, with a comment on each saying so. That duplication is now gone.
//
// STILL NAMED unk_4A320.c, which upstream calls giantbro_helpers_2.c. The
// segment in config/splat.us.strno0.yaml has to match the filename, so
// renaming means deleting a tracked file, and nothing in the connector can
// delete one. Renaming both together is worth doing and is recorded as debt;
// the name is the only thing left that is wrong here.
//
// The 0x801CExxx in these symbol names is no2/np3's address, NOT rno0's.
// rno0's func_801CE04C sits at file offset 0x4A320, vram 0x801CA320, which is
// where the splat `c` segment for this file starts.
#include "../giantbro_helpers_2.h"
