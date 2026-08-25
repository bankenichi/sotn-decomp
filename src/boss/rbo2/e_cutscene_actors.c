// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo2.h"

INCLUDE_ASM("boss/rbo2/nonmatchings/e_cutscene_actors", CutsceneCameraPan);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern PlayerState g_Player;
extern u32 g_Timer;

bool func_us_801A8FC0_from_bo6(void) {
    if (g_Player.status & PLAYER_STATUS_TRANSFORM) {
        g_Player.padSim = PAD_NONE;
        if (g_Timer & 1) {
            if (g_Player.status & PLAYER_STATUS_BAT_FORM) {
                g_Player.padSim = PAD_R1;
            } else if (g_Player.status & PLAYER_STATUS_MIST_FORM) {
                g_Player.padSim = PAD_L1;
            } else if (g_Player.status & PLAYER_STATUS_WOLF_FORM) {
                g_Player.padSim = PAD_R2;
            }
        }
        return true;
    }
    return false;
}


