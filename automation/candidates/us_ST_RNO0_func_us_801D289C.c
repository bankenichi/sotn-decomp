/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_us_801D289C
   attempt: 4/4
   model  : opencode/mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/rno0/nonmatchings/unk_5289C/func_us_801D289C.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Checks if player is within a horizontal range of 25 units and vertical range of 33 units
 * from this entity, using the high 16 bits of fixed-point positions. */
extern u16 PLAYER_posX_i_hi;
extern u16 PLAYER_posY_i_hi;

s32 func_us_801D289C(Entity* entity) {
    s32 diffX;
    s32 diffY;
    u16 playerXHi = PLAYER_posX_i_hi;
    u16 playerYHi = PLAYER_posY_i_hi;
    
    /* Calculate horizontal distance between player and entity using high 16 bits.
     * The cast to s16 treats the subtraction as signed. */
    diffX = (s16)(playerXHi - entity->posX.i.hi);
    if (diffX < 0) {
        diffX = -diffX;
    }
    
    if (diffX < 0x19) {
        /* Within horizontal range - check vertical distance */
        diffY = (s16)(playerYHi - entity->posY.i.hi);
        if (diffY < 0) {
            diffY = -diffY;
        }
        return diffY < 0x21;
    }
    
    return 0;
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_5289C", EntitySealedDoor);
