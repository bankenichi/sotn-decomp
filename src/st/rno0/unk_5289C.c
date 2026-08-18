// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

bool func_us_801D289C(Entity* self) {
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

INCLUDE_ASM("st/rno0/nonmatchings/unk_5289C", EntitySealedDoor);
