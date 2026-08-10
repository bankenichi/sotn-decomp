// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

#define g_EInitCommon OVL_EXPORT(EInitCommon)
extern EInit RNO0_EInitCommon;

void func_us_801C2A34_from_no0(Entity* self) {
    s16 angle;

    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(2);
        self->animCurFrame = 33;
        self->zPriority = 0x50;
        self->unk5A = 0;
        self->palette = 0;
        self->drawFlags = ENTITY_ROTATE | ENTITY_OPACITY;
        self->opacity = 0x60;
    }
    angle = rsin((((g_Timer % 120) << 0xC) + 60) / 120);
    if (!angle) {
        g_api.PlaySfx(SFX_LOW_CLOCK_TICK);
    }
    self->rotate = (angle >> 6) + (angle >> 7);
}

INCLUDE_ASM("st/rno0/nonmatchings/e_background_clock_pendulum", func_us_801C2B24_from_no0);

void RNO0_Unused801B70FC(void) {}
