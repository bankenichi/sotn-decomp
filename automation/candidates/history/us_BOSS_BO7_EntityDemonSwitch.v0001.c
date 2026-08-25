/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO7:EntityDemonSwitch
   source : upstream/master:src/st/chi/en_demon_switch_wall.c
   target : src/boss/bo7/e_demon_switch_wall.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/bo7/nonmatchings/e_demon_switch_wall", UpdateFallingPebble);

void EntityDemonSwitch(Entity* self) {
    typedef enum Step {
        INIT = 0,
        PRESS = 1,
    };

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitSecret);

        self->animCurFrame = 3;
        self->hitPoints = 32767;
        self->hitboxState = 3;
        self->hitboxWidth = 6;
        self->hitboxHeight = 8;

        if (g_CastleFlags[CHI_DEMON_SWITCH]) {
            self->animCurFrame = 4;
        }
         
    case PRESS:
        if (self->hitParams == 7) {
            g_api.PlaySfx(SFX_ANIME_SWORD_B);
            g_CastleFlags[CHI_DEMON_SWITCH] = 1;
             
             
             
            g_api.RevealSecretPassageAtPlayerPositionOnMap(CHI_DEMON_SWITCH);
            self->animCurFrame = 4;
            self->step++;  
        }
        break;
    }
}

INCLUDE_ASM("boss/bo7/nonmatchings/e_demon_switch_wall", EntityDemonSwitchWall);
