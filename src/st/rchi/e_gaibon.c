// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

// Defined in this overlay at src/st/rchi/e_init.c:96. EntityGaibonLeg needs
// it and the permuter cannot add a declaration, so its score-0 result sat in
// `deferred` reading as PERMUTER_EXHAUSTED until this line existed.
//
// Deliberately NOT taken from src/st/nz0/nz0.h:152, which is the only other
// place the name appears. EInit objects are overlay-local data; borrowing
// NZ0's would name a different object.
extern EInit g_EInitGaibon;

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntityGaibon);

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntityGaibonLeg);

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntitySmallGaibonProjectile);

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntityLargeGaibonProjectile);
