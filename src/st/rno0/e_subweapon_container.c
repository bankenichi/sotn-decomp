// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Shimmed 2026-08-17. The body is the shared implementation in
// src/st/e_subweapon_container.h, adopted verbatim from upstream; see the note
// there. It supplies FIVE functions, not the two the harvest scan could name:
// EntitySubWeaponContainer, EntitySubWpnContGlass, EntityFallingLiquid
// (this fork's func_801C7654), EntityBubbles (func_801C77B8) and
// EntitySubwpnInContainer (func_801C7884). The last of those was already
// matched here by hand; that body is superseded by upstream's, which is the
// same function under its real name.
//
// The matching .data slot is declared as
// [0x3228, .data, e_subweapon_container] in config/splat.us.strno0.yaml.

// RNO0 keeps its particle descriptor under OVL_EXPORT while the shared headers
// ask for the common name. Same one-line bridge src/st/rno0/e_misc.c:8 already
// uses, for the same reason: renaming the definition would touch every
// OVL_EXPORT reference in the overlay to gain nothing.
#define g_EInitParticle OVL_EXPORT(EInitParticle)

// The per-item animation script table. Its storage is inside the undecompiled
// data blob at 0x166C, so this overlay has it only as the splat symbol; upstream
// gets the real name because it compiles e_collect's .data from C and this fork
// does not. src/st/rno0/e_collect.c:42 declares the same array the same way.
//
// g_MariaSubweaponAnimPrizeDrop needs no bridge: the header references it only
// under VERSION_PSP, and an extern declaration that nothing uses emits neither
// a relocation nor an undefined symbol.
#define g_SubweaponAnimPrizeDrop D_us_80181830

#include "../e_subweapon_container.h"
