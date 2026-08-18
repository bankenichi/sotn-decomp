/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RCHI:EntityDemonSwitch
   score  : 15
   receipt: nonmatchings/.adapt-scores/20260818-195136-74174-824869/EntityDemonSwitch-2/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rchi/e_demon_switch_wall.c
   asm    : asm/us/st/rchi/nonmatchings/e_demon_switch_wall/EntityDemonSwitch.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
extern void (*g_api_PlaySfx)(s32 sfxId);
extern void (*g_api_RevealSecretPassageAtPlayerPositionOnMap)(s32 arg0);

/*
 * RCHI differs throughout these CHI-derived functions (branch layout,
 * constants, and wall control flow), so the CHI source is not byte-identical.
 */
// EntityDemonSwitchWall's candidate failed to build on this name alone.
// Declared in the shared src/st/e_fire_warg.h:11.
extern EInit g_EInitCommon;

INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", UpdateFallingPebble);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180648;
extern u8 g_CastleFlags[];

#define CHI_DEMON_SWITCH 80
#define SFX_ANIME_SWORD_B 1600
extern EInit D_us_80180648;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void EntityDemonSwitch(Entity* self) {
    typedef enum Step {
        INIT = 0,
        PRESS = 1,
    };

    switch (self->step) {
    case INIT:
        InitializeEntity(D_us_80180648);

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
            g_api_PlaySfx(SFX_ANIME_SWORD_B);
            g_CastleFlags[CHI_DEMON_SWITCH] = 1;
             
             
             
            g_api_RevealSecretPassageAtPlayerPositionOnMap(CHI_DEMON_SWITCH);
            self->animCurFrame = 4;
            self->step++;  
        }
        break;
    }
}

INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", EntityDemonSwitchWall);
