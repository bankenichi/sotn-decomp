/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCHI:EntityDemonSwitch
   attempt: 2/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/rchi/nonmatchings/e_demon_switch_wall/EntityDemonSwitch.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/*
 * RCHI differs throughout these CHI-derived functions (branch layout,
 * constants, and wall control flow), so the CHI source is not byte-identical.
 */
INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", UpdateFallingPebble);

#include "game.h"

extern u8 g_CastleFlags[];
extern void (*g_api_PlaySfx)(s32 sfxId);
extern void (*g_api_RevealSecretPassageAtPlayerPositionOnMap)(s32 arg0);
extern u16 g_EInitCommon[];

/* EntityDemonSwitch - Handles the demon switch in Inverted Castle (RCHI) overlay */
void EntityDemonSwitch(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        self->hitPoints = 0x7FFF;
        self->hitboxWidth = 6;
        self->animCurFrame = 3;
        self->hitboxState = 3;
        self->hitboxHeight = 8;
        /* If the switch was already pressed in Normal Castle, show pressed frame */
        if (g_CastleFlags[0x58] != 0) {
            self->animCurFrame = 4;
        }
        /* fall through to handle hitParams check */
    case 1:
        if (self->hitParams == 7) {
            g_api_PlaySfx(0x640);
            /* Set the flag in Inverted Castle (offset 0x58) */
            g_CastleFlags[0x58] = 1;
            g_api_RevealSecretPassageAtPlayerPositionOnMap(0x58);
            self->animCurFrame = 4;
            self->step++;
        }
        break;
    }
}

INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", EntityDemonSwitchWall);
