// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

void func_us_801CCAAC_from_no0(Entity* self) {
    Entity* tempEntity;
    s16 angle;

    if ((self->ext.clockRoom.unk88 & 0x1F) == 0) {
        g_api.PlaySfxVolPan(SFX_STONE_MOVE_A, 0x40, 0);
    }
    self->ext.clockRoom.unk88++;

     
    tempEntity = self + 5;
    angle =
        tempEntity->ext.clockRoom.unk80 +
        (LOW(tempEntity->ext.clockRoom.bellTimer) * self->ext.clockRoom.unk88) /
            512;
    angle %= (60 * 60);
    tempEntity->ext.clockRoom.hand = angle;

     
    tempEntity++;
    angle =
        tempEntity->ext.clockRoom.unk80 -
        (LOW(tempEntity->ext.clockRoom.bellTimer) * self->ext.clockRoom.unk88) /
            512;
    angle %= (60 * 60);
    tempEntity->ext.clockRoom.hand = angle;
}

// Opens/closes the two birdcage doors based on the clock's minute reading
// Verbatim copy of UpdateBirdcages in src/st/no0/clock_room.c.
// Kept in sync by hand: this file cannot include that header.
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

// Updates the minute and hour hand rotation angles from the room timer
// Verbatim copy of UpdateClockHands in src/st/no0/clock_room.c.
// Kept in sync by hand: this file cannot include that header.
void UpdateClockHands(Entity* self, PlayerStatus* status) {
    // self + 5 is the minute hand
    self += 5;
    self->ext.clockRoom.hand = status->timerMinutes * 60;

    // self + 6 is the hour hand
    self += 1;
    self->ext.clockRoom.hand =
        (status->timerHours * 300) + (status->timerMinutes * 5);
}

INCLUDE_ASM("st/rno0/nonmatchings/e_clock_room", EntityClockRoomController);

// Shared clock-room entity set; see src/st/clock_room_entities.h. Same
// structure as src/st/no0/clock_room.c: the per-overlay controller and its
// helpers stay here, header included at the END.
//
// UpdateBirdcages and UpdateClockHands above deliberately do NOT move into the
// header: no0 and mar define them themselves ahead of their own include.
//
// The header's data tables are bound by naming them in
// config/symbols.us.strno0.txt rather than re-authored here. g_Statues is used
// by the header without a declaration of its own.
extern u16 g_Statues[];

// no0 and mar name the shared init struct g_EInitCommon; rno0 exports it as
// OVL_EXPORT(EInitCommon) = RNO0_EInitCommon at 0x80180AB0. Without this the
// header's reference resolves to zero and every InitializeEntity passes NULL.
extern EInit OVL_EXPORT(EInitCommon);
#define g_EInitCommon OVL_EXPORT(EInitCommon)

// rno0's clock-room sprites are in overlay animset bank 2, not bank 1, and its
// clock face sits elsewhere in the tilemap.
#define CLOCK_ROOM_ANIMSET ANIMSET_OVL(2)
#define STATUE_TILE_POS_1 0xAC
#define STATUE_TILE_POS_0 0xA2
#define STONE_DOOR_TILE_POS 0x24
#define CLOCK_ROOM_DOOR_FLAG RCEN_OPEN

// Same entity slot 0x20 as no0's E_CLOCK_ROOM_SHADOW, but rno0.h names it
// E_DUMMY_20 because this overlay points that slot at EntityDummy. Map it here
// rather than renaming the enum entry, which e_init.c's table also feeds.
#define E_CLOCK_ROOM_SHADOW E_DUMMY_20

// rno0 exports the trailing stub under its overlay-prefixed name, which
// e_init.c references as OVL_EXPORT(Unused801C2338).
#define EntityClockRoomUnused RNO0_Unused801C2338
#include "../clock_room_entities.h"
