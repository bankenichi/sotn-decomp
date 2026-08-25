/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO6:PlayerIsWithinHitbox
   source : upstream/master:src/st/player_is_within_hitbox.h
   target : src/boss/rbo6/e_lock_camera.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int abs(int x);
/* End permuter-seed writer declarations. */

bool PlayerIsWithinHitbox(Entity* self) {
    s16 posXAbs;
    s16 posXDiff;
    s16 posYAbs;
    s16 posYDiff;

    posXDiff = PLAYER.posX.i.hi - self->posX.i.hi;
    posXAbs = abs(posXDiff);
    if (posXAbs > self->hitboxWidth) {
        return false;
    }

    posYDiff = PLAYER.posY.i.hi - self->posY.i.hi;
    posYAbs = abs(posYDiff);
    if (posYAbs > self->hitboxHeight) {
        return false;
    }
    return true;
}

INCLUDE_ASM("boss/rbo6/nonmatchings/e_lock_camera", EntityLockCamera);
