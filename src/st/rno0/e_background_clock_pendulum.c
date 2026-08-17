// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

#define g_EInitCommon OVL_EXPORT(EInitCommon)
extern EInit RNO0_EInitCommon;

/* TRANSPLANTED from NO0's copy by automation/transplant.py --auto, no model
 * call. Verified by the oracle. */
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

// TWIN PORT from src/st/no0/42A34.c:38, matched there. Plays the clock tick,
// panned and attenuated by how far the player is from the clock.
//
// CONSTANT_DIVERGENT, and every divergence is the inverted castle. Derived
// from asm/us/st/rno0/nonmatchings/e_background_clock_pendulum/
// func_us_801C2B24_from_no0.s:
//
//   donor (NO0)                            here (RNO0)
//   InitializeEntity(D_us_80180A88)        RNO0_EInitSpawner, which is the
//                                          same descriptor under the name this
//                                          overlay gives it (e_background_
//                                          pillars.c:4 already bridges it)
//   case 1: (scrollX + playerX - 0x1C0)    (0x140 - (scrollX + playerX))
//   case 1: pan +8                         pan -8
//   case 2: (0x140 - playerX)              (playerX + 0x40)
//   case 2: pan -8                         pan +8
//
// The two pans SWAP, which is the tell that this is a mirror and not a set of
// unrelated constants: the clock is on the other side of the room, so the
// stereo field flips with it. Each distance expression mirrors about the same
// axis. Read off the assembly instruction by instruction, not assumed:
// case 1 is `ori 0x140; subu` on the sum, case 2 is `addiu 0x40` on the player
// alone, and the pan is `addiu $a2, -0x8` in the first arm and `ori $a2, 0x8`
// in the second.
void func_us_801C2B24_from_no0(Entity* self) {
    Tilemap* tilemap = &g_Tilemap;
    Entity* player = &PLAYER;
    u8 volume;
    s16 distance;

    if (!self->step) {
        InitializeEntity(RNO0_EInitSpawner);
    }
    if ((g_Timer % 60) == 0) {
        switch (self->params) {
        case 0:
            g_api.PlaySfx(SFX_LOW_CLOCK_TICK);
            break;

        case 1:
            distance =
                ((0x140 - (tilemap->scrollX.i.hi + player->posX.i.hi)) * 2) / 5;
            if (distance < 0) {
                volume = 0;
            } else if (distance >= 0x80) {
                volume = 0x7F;
            } else {
                volume = distance;
            }
            g_api.PlaySfxVolPan(SFX_LOW_CLOCK_TICK, volume, -8);
            break;

        case 2:
            distance = ((player->posX.i.hi + 0x40) * 2) / 5;
            if (distance < 0) {
                volume = 0;
            } else if (distance >= 0x80) {
                volume = 0x7F;
            } else {
                volume = distance;
            }
            g_api.PlaySfxVolPan(SFX_LOW_CLOCK_TICK, volume, 8);
            break;
        }
    }
}

void RNO0_Unused801B70FC(void) {}
