// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// rno0 exports these two descriptors under OVL_EXPORT names. Bridging them with
// a shim-local #define is the established idiom here: e_clock_room.c,
// e_red_door.c and e_medusa_head.c in this same directory all do it, and it
// keeps the rename out of the shared header.
#define g_EInitParticle OVL_EXPORT(EInitParticle)

// NOT OVL_EXPORT(EInitUnkId13), despite the name lining up perfectly.
//
// EntityUnkId13.s references RNO0_EInitDamageNum at 0x80180A98. The
// similarly-named RNO0_EInitUnkId13 sits at 0x80180A74, and the difference is
// 0x24, which is 3 * sizeof(EInit). Binding it to the name-matching descriptor
// left exactly one relocation-shaped difference with that delta, which
// automation/relocation_check.py reported as such and is how this was found.
//
// This is the second time an OVL_EXPORT name has pointed at the wrong
// descriptor in this overlay: g_EInitLockCamera had the identical failure, also
// at -0x24. In rno0, the name is not evidence. Read the address out of the
// assembly.
#define g_EInitUnkId13 OVL_EXPORT(EInitDamageNum)

// rno0 is in the g_QuadIndices2 exclusion list in the shared header, alongside
// cat and lib, which is what makes its .data slot 0xB4 rather than the 0xB8
// majority. See config/splat.us.strno0.yaml and e_misc.h:790.
#include "../e_misc.h"
