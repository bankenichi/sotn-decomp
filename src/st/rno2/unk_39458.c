// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define false 0
#define true 1

static bool func_us_801B9458(Entity* self) {
    s16 distanceX;
    s16 diffX;
    s16 distanceY;
    s16 diffY;

    diffX = PLAYER.posX.i.hi - self->posX.i.hi;
    distanceX = abs(diffX);
    if (distanceX > 16) {
        return false;
    }

    diffY = PLAYER.posY.i.hi - self->posY.i.hi;
    distanceY = abs(diffY);
    if (distanceY > 32) {
        return false;
    }

    return true;
}



INCLUDE_ASM("st/rno2/nonmatchings/unk_39458", EntityRedDoor);
