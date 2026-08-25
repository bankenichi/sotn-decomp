/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:BOSS/RBO8:func_801D0B40
   score  : 30
   receipt: nonmatchings/.adapt-scores/20260825-003213-88457-171608/func_801D0B40/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/boss/rbo8/unk_15868.c
   asm    : asm/us/boss/rbo8/nonmatchings/unk_15868/func_801D0B40.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo8.h"

void func_801CE3FC(s16* offsets) {
    Entity* entity;
    s32 i;

    for (i = 0; i < 4; i++) {
        entity = g_CurrentEntity + offsets[i];
        polarPlacePart(entity);
    }
    offsets += 4;

    while (*offsets) {
        if (*offsets != 0xFF) {
            entity = g_CurrentEntity + *offsets;
            polarPlacePart(entity);
        }
        offsets++;
    }
}

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80195938);

void func_801D0B40(void) {
    Entity* ent;
    s16* unk88;

    ent = g_CurrentEntity + 15;
    unk88 = ent->ext.et_801D0B40.unk88;
    ent->ext.et_801D0B40.unk84 = unk88[0x4E] - 0x600;

    ent = g_CurrentEntity + 16;
    unk88 = ent->ext.et_801D0B40.unk88;
    ent->ext.et_801D0B40.unk84 = unk88[0x4E] - 0x600;
}

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80195AD8);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80195D80);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80197B1C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801980E4);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80198210);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801983EC);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80198964);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019C7B8_from_rcen);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801991D4);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019921C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", EntityMinotaurSpitLiquid);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019943C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019953C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801BA164_from_cat);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80199A58);
