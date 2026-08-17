// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Shimmed 2026-08-17. The body is the shared implementation in
// src/st/e_armor_lord.h, adopted verbatim from upstream; see the note there.
//
// GUARDIAN SELECTS THE VARIANT, and it is why this file could not be shimmed
// before. The Armor Lord and the Guardian are nearly the same enemy, and the
// header carries both behind #ifdef GUARDIAN: it changes attackTimers, the
// fireball charge animation, whether the overhead slice and flametrail
// animations end or loop, the wake distance (0xC0 rather than 0xA0), the
// turn-around distance (0x40 rather than 0x50), and adds a shield reaction to
// the player casting. The version this fork previously carried had none of
// those branches, so no amount of parameterisation here would have reached
// RNO0's behaviour. Upstream's src/st/rno0/e_guardian.c defines GUARDIAN for
// the same reason.
#define GUARDIAN

// RNO0 keeps this descriptor under OVL_EXPORT deliberately -- see the note at
// its definition in e_init.c -- while the shared headers ask for the common
// name. Same one-line bridge src/st/rno0/e_misc.c:8 uses.
#define g_EInitInteractable OVL_EXPORT(EInitInteractable)

// The header supplies NINE functions, more than the two the harvest scan could
// name. Four were INCLUDE_ASM stubs here:
//
//   EntityArmorLordFireWave      (a stub, and on the scan's list)
//   EntityArmorLord              (a stub, and on the scan's list)
//   EntityArmorLordSwordShadow   (the stub func_us_801D348C_from_are)
//   FadeArmorLordDeath           (the stub func_us_801D1DAC_from_are; static
//                                 in the header, so its symbol goes away)
//
// and five were already matched here by hand, transplanted from ST/ARE:
//
//   FireWavePrimHelper1          was func_us_801D1184_from_are
//   FireWavePrimHelper2          was func_us_801D1388_from_are
//   ArmorLordShieldHelper        was func_us_801D1A9C_from_are
//   EntityArmorLordUnused        was OVL_EXPORT(Unused801C2C50)
//   EntityArmorLordUnk2          was func_us_801D3700_from_are
//
// The `_from_are` suffix recorded where each transplant came from, which was
// honest while they were copies. They are shared code now, and the header
// names each function after what it does.
//
// PAL_ARMOR_LORD_UNK stays in rno0.h. It is per-overlay -- ARE says 0x21A, NO1
// says 0x220, RNO0's 0x20A was read out of this overlay's own assembly -- and
// the header expects the including stage to supply it.
//
// The matching .data slot is declared as
// [0x1B00, .data, e_armor_lord_guardian] in config/splat.us.strno0.yaml.
#include "../e_armor_lord.h"
