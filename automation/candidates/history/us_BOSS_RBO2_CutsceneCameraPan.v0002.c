/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:BOSS/RBO2:CutsceneCameraPan
   score  : 10
   receipt: nonmatchings/.adapt-scores/20260825-003200-88457-595095/CutsceneCameraPan/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/boss/rbo2/e_cutscene_actors.c
   asm    : asm/us/boss/rbo2/nonmatchings/e_cutscene_actors/CutsceneCameraPan.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo2.h"

void CutsceneCameraPan(s16 arg0) {
    s16 delta = arg0 - g_Tilemap.height;

    if (delta > 1) {
        g_Tilemap.height++;
    } else if (delta < -1) {
        g_Tilemap.height--;
    } else {
        g_Tilemap.height = arg0;
    }

#ifdef VERSION_PSP
    g_Tilemap.x = 0;
    g_Tilemap.width = 0x300;
#endif
}

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
