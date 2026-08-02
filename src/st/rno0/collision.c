// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Was stubs for HitDetection and EntityDamageDisplay. One include covers both:
// src/st/collision.h defines HitDetection and, at its end, includes
// entity_damage_display.h. 22 stages already shim it this way, which is why
// none of them has a separate entity_damage_display file or segment.
//
// The header's own data (g_testCollEnemyLookup, g_testCollLuckCutoff) is
// selected by VERSION, not by stage, so it is identical across every us stage.
// That is why the .data address at 0x1094 calibrated cleanly against three
// peers. The header declares no uninitialised storage, so unlike st_update
// this needs no .bss segment.
#include "../collision.h"
