/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801BA030
   attempt: 3/4
   model  : opencode/mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/boss/bo0/nonmatchings/2D26C/func_us_801BA030.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo0.h"

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD26C);

// Checks whether the tile at (x, y) is solid ground.
s32 func_us_801AD2F0(s16 x, s16 y) {
    Collider col;

    g_api.CheckCollision(x, y, &col, 0);
    return col.effects & EFFECT_SOLID;
}

INCLUDE_RODATA("boss/bo0/nonmatchings/2D26C", D_us_801A9344);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD338);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AE858);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF31C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF604);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF8C0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AFAF4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", EntityOlroxAfterImage);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B001C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B053C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B088C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B0930);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B13A8);

void func_us_801B1590(u8 step) {
    ET_B0_Unk* temp = (ET_B0_Unk*)g_CurrentEntity->ext.b0Unk.unk80;

    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;

    temp->childPalette = 0;
    temp = (ET_B0_Unk*)temp->parent;
    temp->childPalette = 0;
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B15BC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B163C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B171C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B17BC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1864);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1950);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B19FC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1B30);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1C60);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1CE0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1DDC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1E5C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1EDC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1F5C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2044);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B20F4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2178);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B21F0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B24CC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2690);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B30AC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B365C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5470);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B551C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5D6C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5E08);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5E8C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B619C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B6520);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B65C0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B6CA4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B76E4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7BAC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7C44);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7CC8);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8794);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B888C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8970);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8B64);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8D8C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B9BEC);

// Plays a sound effect with volume/pan based on entity's distance from center of room
void func_us_801BA030(s16 arg0) {
    Entity* entity = g_CurrentEntity;
    s16 posX = entity->posX.i.hi;
    s32 posXDiff = posX - 0x80;
    s32 absPosXDiff;
    s32 pan;
    s32 posYDiff;
    s32 absPosYDiff;
    s32 volumeX;
    s32 volumeY;
    s32 volume;
    s32 adjustedVolume;

    // Calculate panning from horizontal distance
    absPosXDiff = posXDiff;
    if (posXDiff < 0) {
        absPosXDiff = -absPosXDiff;
    }
    
    pan = (absPosXDiff - 0x20) >> 5;
    
    // Clamp pan to 0-8 range
    if ((s16)pan >= 9) {
        pan = 8;
    } else if ((s16)pan < 0) {
        pan = 0;
    }
    
    // Negate pan if entity is to the left of center
    if (posXDiff < 0) {
        pan = -pan;
    }
    
    // Calculate volume from distances
    // Reuse posXDiff absolute value
    absPosXDiff = posXDiff;
    if (posXDiff < 0) {
        absPosXDiff = -absPosXDiff;
    }
    
    volumeX = absPosXDiff - 0x60;
    
    // Get vertical distance from room center
    posYDiff = entity->posY.i.hi - 0x80;
    absPosYDiff = posYDiff;
    if (posYDiff < 0) {
        absPosYDiff = -absPosYDiff;
    }
    
    volumeY = absPosYDiff - 0x70;
    
    // Combine X and Y distances, only adding Y if positive
    volume = volumeX;
    if (volumeY > 0) {
        volume += volumeY;
    }
    
    // Scale volume down by half and subtract from max volume
    adjustedVolume = (volume << 16) >> 17;  // Arithmetic shift divides by 2
    volume = 0x58 - adjustedVolume;
    
    // Play sound if volume is positive
    if (volume > 0) {
        g_api_PlaySfxVolPan(arg0, volume, pan);
    }
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA128);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA4AC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA724);
