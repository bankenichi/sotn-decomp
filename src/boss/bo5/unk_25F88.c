// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A5F88);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A62B4);

void func_us_801A666C(Entity* self, s32 arg1) {
    s16 rotPivotX;
    u16 step;
    u16 palette;
    u16 step_s;

    rotPivotX = self->rotPivotX - arg1;
    step = self->step + arg1;
    palette = self->palette - arg1;
    step_s = self->step_s + arg1;
    self->rotPivotX = rotPivotX;
    LOH(self->velocityX) = rotPivotX;
    self->step = step;
    self->facingLeft = step;
    self->palette = palette;
    HIH(self->velocityX) = palette;
    self->step_s = step_s;
    self->rotPivotY = step_s;
}


INCLUDE_ASM("boss/bo5/nonmatchings/unk_25F88", func_us_801A66B0);

void func_801B1D68(Entity* self) { func_us_801A66B0(self, 0); }

void BO5_RicSetDeadPrologue(Entity* self) {
    func_us_801A66B0(self, 1);
}
