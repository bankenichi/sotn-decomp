/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_801CE2CC
   attempt: 1/4
   model  : opencode/ling-3.0-flash-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/rno0/nonmatchings/unk_4A320/func_801CE2CC.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Split out of giantbro_helpers.c to match the upstream file boundary.
// src/st/giantbro_helpers.h ends at func_801CDFD8; src/st/no2/4966C.c and
// src/st/np3/4E04C.c both BEGIN here, at func_801CE04C, with exactly this set
// of functions. rno0 had the two groups merged into one file, which is why
// giantbro_helpers.c could not be reduced to a shim: e_blade.c and e_gurkha.c
// call polarPlacePartsList and func_801CE1E8 across TU boundaries, and the
// shared header does not define them.
//
// The 0x801CExxx in these symbol names is no2/np3's address, NOT rno0's.
// rno0's func_801CE04C sits at file offset 0x4A320, vram 0x801CA320, which is
// where the splat `c` segment for this file starts.

INCLUDE_ASM("st/rno0/nonmatchings/unk_4A320", func_801CE04C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4A320", func_801CE120);

// Resets a Giant Brother's step/pose state and clears its per-limb timers.
// See func_801CE228 below for the matching out-of-bounds write: unkB0 and
// unkB4 are each only 2 elements, but this loop runs 4 times, so the last
// two iterations spill unkB0 writes into unkB4 (and unkB4 out past the end).
// Verbatim copy of func_801CE1E8 in src/st/no2/4966C.c.
// Kept in sync by hand: this file cannot include that header.
void func_801CE1E8(s32 step) {
    s32 i;
    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;
    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}

// Verbatim copy of func_801CE228 in src/st/no2/4966C.c.
// Kept in sync by hand: this file cannot include that header.
void func_801CE228() {
    s32 i;
    // BUG: Array out of bounds writing. Possible explanation:
    // unkB0 was originally a 4-element array. This loop would iterate
    // through the 4 elements and write each to zero.
    // At some point, unkB0 got split to two arrays, unkB0 and unkB4.
    // Now we zero out both arrays. But since each one is only 2 elements,
    // the loop should only be `i < 2`. They forgot to change it. This means
    // that for i = 2 and i = 3, the unkB0 writes are writing into unkB4,
    // and the unkB4 is writing totally out of bounds.
    // As far as we know, this bug does not have any consequences.
    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}

// Polar Knight parts placement: iterates through a sentinel-terminated list
// of sub-entity indices and calls polarPlacePart for any part that has not
// already been placed this frame. unkA8 is the "placed" flag polarPlacePart
// sets on its way out; see the shared ../giantbro_helpers.h, which reaches the
// same byte as self->ext.GH_Props.unkA8 (ext base 0x7C + 0x2C = 0xA8).
void polarPlacePartsList(s16* partsList) {
    s16* iter = partsList;
    s16 index;
    Entity* entity;

    while (*iter != 0) {
        index = *iter;
        entity = &g_CurrentEntity[index];
        iter++;
        if (entity->ext.GH_Props.unkA8 == 0) {
            polarPlacePart(entity);
        }
    }
}

// Places entities in polar coordinates relative to g_CurrentEntity using indices
// from a parameter block. Offsets 0/2 use func_801CD91C; offsets 4/6 and the
// variable-length tail (terminated by 0) use polarPlacePart. Value 0xFF skips.
void func_801CE2CC(u16 *arg0) {
    func_801CD91C(&g_CurrentEntity[arg0[1]]);
    func_801CD91C(&g_CurrentEntity[arg0[0]]);
    polarPlacePart(&g_CurrentEntity[arg0[2]]);
    polarPlacePart(&g_CurrentEntity[arg0[3]]);
    arg0 += 4;
    while (*arg0 != 0) {
        s16 value = (s16)*arg0;
        arg0++;
        if (value != 0xFF) {
            polarPlacePart(&g_CurrentEntity[value]);
        }
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_4A320", func_801CE3FC);
