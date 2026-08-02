// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Was a stub for EntitySoulStealOrb plus a private copy of EntityEnemyBlood.
// src/st/e_particles.h defines exactly those two and 27 stages already shim it;
// rno0 could not until its .data was segmented, because the header's own
// file-scope data would otherwise be emitted a second time by the unnamed blob.
//
// Unlike st_update.h this header declares NO uninitialised storage, so it needs
// a .data segment only. That was checked before building, not after.
#include "../e_particles.h"
