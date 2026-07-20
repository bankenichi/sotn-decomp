// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", func_us_801CCAAC_from_no0);

// Opens/closes the two birdcage doors based on the clock's minute reading
void UpdateBirdcages(Entity* self, u32 timerMinutes) {
    // self + 7 is birdcage door 1
    self += 7;
    if (timerMinutes >= 10 && timerMinutes < 30) {
        self->ext.birdcage.state = true;
    } else {
        self->ext.birdcage.state = false;
    }

    // self + 8 is birdcage door 2
    self += 1;
    if (timerMinutes >= 30 && timerMinutes < 50) {
        self->ext.birdcage.state = true;
    } else {
        self->ext.birdcage.state = false;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", UpdateClockHands);

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", EntityClockRoomController);

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", EntityClockHands);

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", EntityBirdcageDoor);

// Paints the tilemap foreground tiles for a statue's clock-face segments
void UpdateStatueTiles(s32 tilePos, u16 tile) {
    u32 i;

    for (i = 0; i < 6; i++) {
        g_Tilemap.fg[tilePos] = tile;
        tilePos++;
        g_Tilemap.fg[tilePos] = tile;
        tilePos += 15;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", EntityStatue);

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", EntityStatueGear);

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", UpdateStoneDoorTiles);

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", EntityStoneDoor);

void RNO0_Unused801C2338(void) {}
