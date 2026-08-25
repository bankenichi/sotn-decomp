/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO1:EntityIsNearPlayer
   score  : 5
   receipt: nonmatchings/.adapt-scores/20260825-003430-88457-422691/EntityIsNearPlayer/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno1/e_red_door.c
   asm    : asm/us/st/rno1/nonmatchings/e_red_door/EntityIsNearPlayer.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

int abs(int x);

bool EntityIsNearPlayer(Entity* self) {
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

INCLUDE_ASM("st/rno1/nonmatchings/e_red_door", EntityRedDoor);
