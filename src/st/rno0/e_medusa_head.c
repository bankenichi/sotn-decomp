// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Was stubs for EntityMedusaHeadSpawner and EntityMedusaHeadBlue plus a private
// copy of EntityMedusaHeadYellow. src/st/e_medusa_head.h defines all three.
//
// The header declares no uninitialised storage, so a .data segment alone is
// enough here; contrast st_update, which also needed .bss and silently grew the
// overlay 0x40 until it got one.
//
// rno0 names its three EInit descriptors differently from the shared header, so
// they are bridged rather than re-declared. The spawner follows the same
// OVL_EXPORT idiom as g_EInitCommon in e_clock_room.c.
extern EInit OVL_EXPORT(EInitSpawner);
#define g_EInitSpawner OVL_EXPORT(EInitSpawner)

// The blue/yellow mapping is READ OFF THE ASSEMBLY, not guessed.
// EntityMedusaHeadBlue.s does:
//     lhu  $v0, 0x30($s0)              # self->params
//     $a0 = g_EInitMedusaHead2
//     bnez $v0, .call                  # params != 0 keeps Head2
//     $a0 = g_EInitMedusaHead1         # params == 0 takes Head1
// and the header does `if (!params) Blue else Yellow`. So params==0 is Blue,
// which is Head1, and params!=0 is Yellow, which is Head2.
extern EInit g_EInitMedusaHead1;
extern EInit g_EInitMedusaHead2;
#define g_EInitMedusaHeadBlue g_EInitMedusaHead1
#define g_EInitMedusaHeadYellow g_EInitMedusaHead2

#include "../e_medusa_head.h"
