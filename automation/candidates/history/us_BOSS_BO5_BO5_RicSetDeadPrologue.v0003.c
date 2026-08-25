/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:BOSS/BO5:BO5_RicSetDeadPrologue
   score  : 0
   receipt: nonmatchings/.adapt-scores/20260825-162432-33165-183850/BO5_RicSetDeadPrologue/adapt-score.json
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

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_us_801A66B0();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A5F88);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A62B4);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A666C);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A66B0);

void func_801B1D68(Entity* self) { func_us_801A66B0(self, 0); }

void BO5_RicSetDeadPrologue(Entity* self) {
    func_us_801A66B0(self, 1);
}
