/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:BOSS/BO5:BO5_RicSetDeadPrologue
   score  : 15
   receipt: nonmatchings/.adapt-scores/20260824-233341-62298-525042/BO5_RicSetDeadPrologue/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/boss/bo5/unk_25F88.c
   asm    : asm/us/boss/bo5/nonmatchings/unk_25F88/BO5_RicSetDeadPrologue.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A5F88);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A62B4);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A666C);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A66B0);

void func_801B1D68(Entity* self) { func_us_801A66B0(self, 0); }

void BO6_RicSetStep(s32 step);

void BO5_RicSetDeadPrologue(void) {
    BO6_RicSetStep(0x17);
}
