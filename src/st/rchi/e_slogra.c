// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

// EntitySlograSpear and EntitySlograSpearProjectile each failed to build on
// one of these names. D_us_80180600 is defined by THIS overlay at
// src/st/rchi/e_init.c:94; g_Entities_224 is the shared src/st/e_imp.h:9.
extern EInit D_us_80180600;
extern Entity g_Entities_224[];

INCLUDE_ASM("st/rchi/nonmatchings/e_slogra", EntitySlogra);

INCLUDE_ASM("st/rchi/nonmatchings/e_slogra", EntitySlograSpear);

INCLUDE_ASM("st/rchi/nonmatchings/e_slogra", EntitySlograSpearProjectile);
