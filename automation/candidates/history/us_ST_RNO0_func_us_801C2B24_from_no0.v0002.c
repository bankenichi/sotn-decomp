/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_us_801C2B24_from_no0
   attempt: 3/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/rno0/nonmatchings/e_background_clock_pendulum/func_us_801C2B24_from_no0.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
extern void (*g_api_PlaySfx)(s32 sfxId);
extern s32 (*g_api_PlaySfxVolPan)(s32 sfxId, s32 sfxVol, s32 sfxPan);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int InitializeEntity();
extern int rsin();

#define g_EInitCommon OVL_EXPORT(EInitCommon)
extern EInit RNO0_EInitCommon;

void func_us_801C2A34_from_no0(Entity* self) {
    s16 angle;

    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(2);
        self->animCurFrame = 33;
        self->zPriority = 0x50;
        self->unk5A = 0;
        self->palette = 0;
        self->drawFlags = ENTITY_ROTATE | ENTITY_OPACITY;
        self->opacity = 0x60;
    }
    angle = rsin((((g_Timer % 120) << 0xC) + 60) / 120);
    if (!angle) {
        g_api.PlaySfx(SFX_LOW_CLOCK_TICK);
    }
    self->rotate = (angle >> 6) + (angle >> 7);
}

extern EInit RNO0_EInitSpawner;
extern u32 g_Timer;
extern void (*g_api_PlaySfx)(s32 sfxId);
extern Tilemap g_Tilemap;
extern s32 (*g_api_PlaySfxVolPan)(s32 sfxId, s32 sfxVol, s32 sfxPan);
extern s16 PLAYER_posX_i_hi;

void func_us_801C2B24_from_no0(Entity* self) {
    s16 panning;

    if (self->step == 0) {
        InitializeEntity(&RNO0_EInitSpawner);
    }

    if (g_Timer == (g_Timer / 30) * 60) {
        switch (self->step_s) {
        case 0:
            g_api_PlaySfx(0x6B7);
            break;
        case 1:
            panning = ((0x140 - (g_Tilemap.scrollX.i.hi + PLAYER_posX_i_hi)) * 2) / 5;
            if (panning < 0) {
                panning = 0;
            } else if (panning >= 0x80) {
                panning = 0x7F;
            }
            g_api_PlaySfxVolPan(0x6B7, panning & 0xFF, -8);
            break;
        case 2:
            panning = ((PLAYER_posX_i_hi + 0x40) * 2) / 5;
            if (panning < 0) {
                panning = 0;
            } else if (panning >= 0x80) {
                panning = 0x7F;
            }
            g_api_PlaySfxVolPan(0x6B7, panning & 0xFF, 8);
            break;
        }
    }
}

void RNO0_Unused801B70FC(void) {}
