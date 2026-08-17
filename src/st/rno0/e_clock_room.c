// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Which end of the room each statue is. Every overlay with a clock room
// declares this for itself -- src/st/no0/clock_room.c:4 and src/boss/mar/mar.h:40
// both do -- because src/st/clock_room_entities.h does not provide it.
typedef enum Statues {
    /* 0 */ RIGHT_STATUE,
    /* 1 */ LEFT_STATUE,
} Statues;

// The shared clock-room entity set is included at the END of this file, the
// same shape src/st/no0/clock_room.c uses: the per-overlay controller and its
// helpers live here, the header goes last. But the controller REFERENCES the
// bindings below, so they have to be declared before it rather than beside the
// include. That ordering is the only thing that made EntityClockRoomController
// fail to compile when it was first written.
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

/* TRANSPLANTED from NO0's copy by automation/transplant.py --auto, no model
 * call. The `_from_no0` suffix is the tree's convention for a body ported
 * across overlays and is what identifies it as such. Verified by the oracle.
 */
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

// NOT a twin port, despite sharing most of its shape with
// src/st/no0/clock_room.c:106. Six divergences are ordinary inverted-castle
// constants; the seventh is different LOGIC, which is why this one waited while
// the rest of the clock room shimmed months ago. Every line is read off
// asm/us/st/rno0/nonmatchings/e_clock_room/EntityClockRoomController.s:
//
//   donor (NO0)                        here (RNO0)      evidence
//   if (posY > 128) RIGHT = false      if (posY < 0x90) slti 0x90 + beqz-skip
//   the same again for LEFT            same inversion
//   case 0: if (posY < 64)             if (posY > 0xC0) slti 0xC1 + bnez-skip
//   ... posX < 64  -> LEFT  = true     -> RIGHT = true  stores to g_Statues+0
//   ... posX > 0xC0 -> RIGHT = true    -> LEFT  = true  stores to g_Statues+2
//   ANIMSET_OVL(1)                     CLOCK_ROOM_ANIMSET, ANIMSET_OVL(2)
//   g_CastleFlags[CEN_OPEN]            CLOCK_ROOM_DOOR_FLAG, g_CastleFlags+0xE4
//   posX >= 48 && posX < 209           >= 0x60 && < 0xA1  addiu -0x60, sltiu 0x41
//
// THE SEVENTH. The donor opens the stone floor when the player wears a gold
// ring and a silver ring in the two accessory slots. This overlay instead walks
// five bytes of g_Status and opens only if every one has bit 0 set. Those bytes
// are relics[0x19]..relics[0x1D]: PlayerStatus begins with `u8 relics[30]` at
// offset 0, and RELIC_DEMON_CARD's own comment in game.h pins 0x80097979, which
// is g_Status + 0x15 = relic 21, so 0x19 is RELIC_HEART_OF_VLAD and the run
// ends at RELIC_EYE_OF_VLAD. Bit 0 is RELIC_FLAG_FOUND. The inverted castle's
// clock room wants Vlad's five relics -- the same set the true ending needs --
// which is why no amount of constant substitution would have reached it.
//
// It must be spelled g_Status.relics[i] and NOT status->relics[i]: the assembly
// re-materialises %hi(g_Status) inside the loop while holding &g_Status in $s3
// for the timer fields, and the pointer form reuses $s3.
//
// Two more structural differences, both in step 2. The player's X is SNAPPED to
// 0x60 or 0xA0 on entry rather than merely read, and sub-steps 0 through 3 are
// bare increments where the donor drives the player around with padSim and
// transform checks. Each of those is its own block in the assembly
// (.Lus_801C1414 / 1420 / 142C), so they are written as separate cases: a
// merged `case 1: case 2: case 3:` would emit one shared block and not match.
void EntityClockRoomController(Entity* self) {
    PlayerStatus* status = &g_Status;
    Primitive* prim;
    Entity* entity;
    s32 primIndex;
    u16 i;
    // SIGNED, and the assembly is explicit about it: the emptiness test is
    // `sll $v0, $v1, 16` followed by bnez, which is how this compiler checks a
    // 16-bit SIGNED value against zero. A u16 counter emits `andi 0xffff`
    // instead and is the one thing that kept this function from matching.
    s16 relicsMissing;
    s16 posX;

    // Plays the clock bell
    if (self->ext.clockRoom.bellTimer) {
        if (!self->ext.clockRoom.bellDuration) {
            g_api.PlaySfx(SFX_CLOCK_ROOM_BELL);
            if (--self->ext.clockRoom.bellTimer) {
                self->ext.clockRoom.bellDuration = 64;
            }
        } else {
            self->ext.clockRoom.bellDuration--;
        }
    }

    // Controls the statues
    entity = &PLAYER;
    if (g_unkGraphicsStruct.D_800973FC == 0) {
        if (entity->posY.i.hi < 0x90) {
            g_Statues[RIGHT_STATUE] = false;
        }
    } else if (!self->ext.clockRoom.unk8A) {
        g_Statues[RIGHT_STATUE] = true;
    }

    self->ext.clockRoom.unk8A = g_unkGraphicsStruct.D_800973FC;

    // Every other minute the top left statue opens
    if (status->timerMinutes & 1) {
        if (entity->posY.i.hi < 0x90) {
            g_Statues[LEFT_STATUE] = false;
        }
    } else {
        g_Statues[LEFT_STATUE] = true;
    }

    switch (self->step) {
    case 0:
        if ((g_Timer % 60) == 0) {
            g_api.PlaySfx(SFX_CLOCK_ROOM_TICK);
        }

        primIndex = g_api.AllocPrimitives(PRIM_G4, 1);
        if (primIndex == -1) {
            return;
        }
        InitializeEntity(g_EInitCommon);
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        prim->x0 = prim->x2 = prim->y0 = prim->y1 = 0;
        prim->x1 = prim->x3 = prim->y2 = prim->y3 = 256;
        prim->r0 = prim->g0 = prim->b0 = 0;
        LOW(prim->r1) = LOW(prim->r0);
        LOW(prim->r2) = LOW(prim->r0);
        LOW(prim->r3) = LOW(prim->r0);
        prim->priority = 0x1F0;
        prim->drawMode = DRAW_HIDE;

        g_api.PlaySfx(SET_STOP_MUSIC);
        stopMusicFlag = true;
        currentMusicId = 0;
        entity = &PLAYER;
        g_Statues[RIGHT_STATUE] = false;

        if (entity->posY.i.hi > 0xC0) {
            posX = entity->posX.i.hi;
            if (posX < 0x40) {
                g_Statues[RIGHT_STATUE] = true;
            } else if (posX > 0xC0) {
                g_Statues[LEFT_STATUE] = true;
            }
        }

        self->animSet = CLOCK_ROOM_ANIMSET;
        self->animCurFrame = 23;
        self->zPriority = 0x40;

        // Create clock hands
        entity = self + 5;
        for (i = 0; i < 2; i++, entity++) {
            CreateEntityFromCurrentEntity(E_CLOCK_HANDS, entity);
            entity->params = i;
        }
        UpdateClockHands(self, status);

        // Create Birdcage doors
        entity = self + 7;
        for (i = 0; i < 2; i++, entity++) {
            CreateEntityFromCurrentEntity(E_BIRDCAGE_DOOR, entity);
            entity->params = i;
        }
        UpdateBirdcages(self, status->timerMinutes);

        // Shadow for the Bighorn sheep head on the center
        entity = self + 9;
        CreateEntityFromCurrentEntity(E_CLOCK_ROOM_SHADOW, entity);
        entity->animSet = CLOCK_ROOM_ANIMSET;
        entity->animCurFrame = 23;
        entity->zPriority = 0x40;
        entity->palette = PAL_FLAG(0x4B);
        entity->drawFlags = ENTITY_OPACITY;
        entity->blendMode = BLEND_TRANSP;
        entity->posY.i.hi += 4;

        // Create path blocking statues
        entity = self + 1;
        for (i = 0; i < 2; i++, entity++) {
            CreateEntityFromCurrentEntity(E_STATUE, entity);
            entity->params = i;
        }

        // Create the gears that drive the statues
        entity = self + 12;
        for (i = 0; i < 2; i++, entity++) {
            CreateEntityFromCurrentEntity(E_STATUE_GEAR, entity);
            entity->params = i;
        }

        // Create the stones on the floor
        entity = self + 14;
        for (i = 0; i < 2; i++, entity++) {
            CreateEntityFromCurrentEntity(E_STONE_DOOR, entity);
            entity->params = i;
        }
        break;

    case 1:
        if (!status->timerFrames) {
            g_api.PlaySfx(SFX_CLOCK_ROOM_TICK);
        }

        UpdateClockHands(self, status);
        if (status->timerSeconds == 0 && status->timerFrames == 0) {
            if (status->timerMinutes == 0) {
                self->ext.clockRoom.bellTimer =
                    ((status->timerHours + 11) % 12) + 1;
                if (!self->ext.clockRoom.bellTimer) {
                    self->ext.clockRoom.bellTimer = 12;
                }
            }
        }

        UpdateBirdcages(self, status->timerMinutes);

        if (!g_CastleFlags[CLOCK_ROOM_DOOR_FLAG]) {
            entity = &PLAYER;
            if (entity->posX.i.hi >= 0x60 && entity->posX.i.hi < 0xA1) {
                // Vlad's five relics, every one of them found
                relicsMissing = 0;
                for (i = RELIC_HEART_OF_VLAD; i < NUM_RELICS; i++) {
                    if (!(g_Status.relics[i] & RELIC_FLAG_FOUND)) {
                        relicsMissing++;
                    }
                }
                if (!relicsMissing) {
                    SetStep(2);
                }
            }
        }
        break;

    case 2:
        g_Statues[RIGHT_STATUE] = false;
        g_Statues[LEFT_STATUE] = false;
        g_Player.padSim = 0;
        g_Player.demo_timer = 1;
        entity = &PLAYER;
        if (entity->posX.i.hi < 0x81) {
            entity->posX.i.hi = 0x60;
        } else {
            entity->posX.i.hi = 0xA0;
        }
        switch (self->step_s) {
        case 0:
            self->ext.clockRoom.unk88 = 0;
            self->step_s++;
            break;

        case 1:
            self->step_s++;
            break;

        case 2:
            self->step_s++;
            break;

        case 3:
            self->step_s++;
            break;

        case 4:
            prim = &g_PrimBuf[self->primIndex];
            prim->r0 = prim->g0 = prim->b0 += 16;
            LOW(prim->r1) = LOW(prim->r0);
            LOW(prim->r2) = LOW(prim->r0);
            LOW(prim->r3) = LOW(prim->r0);
            prim->drawMode = DRAW_TRANSP | DRAW_TPAGE | DRAW_TPAGE2;
            if (prim->r0 > 192) {
                self->step_s++;
            }
            break;

        case 5:
            prim = &g_PrimBuf[self->primIndex];
            prim->r0 = prim->g0 = prim->b0 -= 4;
            LOW(prim->r1) = LOW(prim->r0);
            LOW(prim->r2) = LOW(prim->r0);
            LOW(prim->r3) = LOW(prim->r0);
            if (prim->r0 < 8) {
                prim->drawMode = DRAW_HIDE;
                self->step_s++;
            }
            break;

        case 6:
            entity = self + 7;
            LOH(entity->ext.clockRoom.unk80) = 1;

            entity++;
            LOH(entity->ext.clockRoom.unk80) = 1;

            self->ext.clockRoom.unk88 = 1;
            self->step_s++;
            break;

        case 7:
            if (!--self->ext.clockRoom.unk88) {
                // Minute hand
                entity = self + 5;
                posX = LOW(entity->ext.clockRoom.unk80) =
                    entity->ext.clockRoom.hand;
                posX %= (60 * 60);
                LOW(entity->ext.clockRoom.bellTimer) = 5400 - posX;

                // Hour hand
                entity++;
                posX = LOW(entity->ext.clockRoom.unk80) =
                    entity->ext.clockRoom.hand;
                posX %= (60 * 60);
                LOW(entity->ext.clockRoom.bellTimer) = posX + 1800;

                self->ext.clockRoom.unk88 = 0;
                self->step_s++;
            }
            break;

        case 8:
            func_us_801CCAAC_from_no0(self);
            if (self->ext.clockRoom.unk88 >= 0x200) {
                self->step_s++;
                self->ext.clockRoom.bellTimer = 13;
                self->ext.clockRoom.unk88 = 0x380;
            }
            break;

        case 9:
            if (!--self->ext.clockRoom.unk88) {
                g_CastleFlags[CLOCK_ROOM_DOOR_FLAG] = 1;
                g_api.RevealSecretPassageAtPlayerPositionOnMap(
                    CLOCK_ROOM_DOOR_FLAG);
                SetStep(3);
                self->ext.clockRoom.unk88 = 0x140;
            }
        }
        break;

    case 3:
        g_Statues[RIGHT_STATUE] = false;
        g_Statues[LEFT_STATUE] = false;
        switch (self->step_s) {
        case 0:
            if (!--self->ext.clockRoom.unk88) {
                // Minute hand
                entity = self + 5;
                LOW(entity->ext.clockRoom.unk80) = entity->ext.clockRoom.hand;
                posX = status->timerMinutes * 60;
                LOW(entity->ext.clockRoom.bellTimer) = posX + 1800;

                // Hour hand
                entity++;
                LOW(entity->ext.clockRoom.unk80) = entity->ext.clockRoom.hand;
                posX = (status->timerHours * 300) + (status->timerMinutes * 5);
                LOW(entity->ext.clockRoom.bellTimer) = 5400 - posX;

                self->ext.clockRoom.unk88 = 0;
                self->step_s++;
            }
            break;

        case 1:
            func_us_801CCAAC_from_no0(self);
            if (self->ext.clockRoom.unk88 >= 0x200) {
                SetStep(1);
            }
        }
        break;
    }
}

// UpdateBirdcages and UpdateClockHands above deliberately do NOT move into the
// header: no0 and mar define them themselves ahead of their own include. The
// bindings the header needs are declared at the top of this file, above
// EntityClockRoomController, which also uses them.
#include "../clock_room_entities.h"
