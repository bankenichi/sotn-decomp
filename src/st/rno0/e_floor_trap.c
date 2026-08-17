// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Shimmed 2026-08-16. The body is the shared implementation in
// src/st/e_floor_trap.h, adopted from upstream; see the note there. The
// matching .data slot is declared as [0x1DC4, .data, e_floor_trap] in
// config/splat.us.strno0.yaml.
#include "../e_floor_trap.h"
