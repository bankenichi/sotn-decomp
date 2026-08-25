// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", EntityBreakable);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", EntityBreakableDebris);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B3D8C_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B3F30_from_bo0);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitCommon;
void InitializeEntity(u16 arg0[]);

void func_us_801B4148_from_bo0(Entity* self) {
    if (self->step == 0) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(2);
        self->animCurFrame = 1;
        self->zPriority = 0xA0;
    }
}



INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B41A4_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B4210_from_bo0);
