// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
int abs(int x);

#include "../../st/player_is_within_hitbox.h"



INCLUDE_ASM("boss/rbo6/nonmatchings/e_lock_camera", EntityLockCamera);
