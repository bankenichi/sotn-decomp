// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo0.h"

// A proximity check with the same shape as EntityIsNearPlayer in
// src/st/e_red_door.h, but a wider box: 24 horizontal instead of 16. bo0
// already shims e_red_door.h in src/boss/bo0/e_red_door.c, so this is a
// genuinely separate function and must NOT be folded into that header. The
// same is true of its rno0 relative func_us_801B9A8C, which uses 16.
//
// The four separate locals are load-bearing. Written as one reassigned local
// (`dx = a - b; if (dx < 0) dx = -dx;`) GCC keeps the raw difference
// un-extended and sign-extends only at the comparison, emitting sll/sra once
// where the original emits it twice. Assigning the extended difference to
// `diffX` and the negation to `distanceX` makes each assignment truncate.
//
// The symbol keeps its address-derived name because func_us_801BB08C below is
// still assembly and calls it by that name.
bool func_us_801BB014(Entity* self) {
    s16 distanceX;
    s16 diffX;
    s16 distanceY;
    s16 diffY;

    diffX = PLAYER.posX.i.hi - self->posX.i.hi;
    distanceX = abs(diffX);
    if (distanceX > 24) {
        return false;
    }

    diffY = PLAYER.posY.i.hi - self->posY.i.hi;
    distanceY = abs(diffY);
    if (distanceY > 32) {
        return false;
    }

    return true;
}

INCLUDE_ASM("boss/bo0/nonmatchings/3B014", func_us_801BB08C);
