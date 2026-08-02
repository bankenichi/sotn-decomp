// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Was a stub for EntityLockCamera. The shared implementation is
// src/st/entity_lock_camera.h -- note the name. 20 stages shim it from a file
// called e_lock_camera.c while including that differently-named header, which
// is exactly what an index rule matching shims by FILENAME could not see. It
// reported "shimmed by no stage", and that was written into the docs as
// unshimmable. Their c segments are 0x1BC, byte-identical to rno0's.
//
// rno0's tilemap table is its own: 18 of its 56 u16 differ from the header's
// default, spread across the whole table rather than confined to the leading
// row the header's STAGE_IS_* branches cover. So this uses the header's own
// escape hatch, ENTITY_LOCK_CAMERA_DATA_DEFINED, the same way rchi does for
// PSP. Values read directly out of disks/us/ST/RNO0/RNO0.BIN at 0xE50.
//
// The hitbox and the zeroed data block are IDENTICAL to the header's defaults
// (verified: the build matched at 0xE50 and 0xE58 and first differed at 0xE60),
// but the guard covers all three, so all three are restated here.
static u8 entityLockCameraHitbox[] = {
    0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x50, 0x20,
};

static u8 entityLockCameraData[8] = {0};

static u16 entityLockCameraTilemapProps[] = {
    0x0000, 0x01FC, 0x0600, 0x02FC, 0x0000, 0x00FC, 0x0600, 0x02FC,
    0x0000, 0x00FC, 0x0600, 0x01FC, 0x0000, 0x0000, 0x0600, 0x01FC,
    0x0000, 0x00FC, 0x0600, 0x01FC, 0x0000, 0x00FC, 0x0600, 0x0300,
    0x0500, 0x0100, 0x0600, 0x02FC, 0x0000, 0x00FC, 0x0600, 0x01FC,
    0x0000, 0x0000, 0x0600, 0x0100, 0x0000, 0x0000, 0x0600, 0x0100,
    0x0000, 0x01FC, 0x0500, 0x02FC, 0x0000, 0x01FC, 0x0500, 0x02FC,
    0x00F0, 0x01FC, 0x0310, 0x02FC, 0x00F0, 0x01FC, 0x0310, 0x02FC,
};

#define ENTITY_LOCK_CAMERA_DATA_DEFINED

// NO OVL_EXPORT bridge here, deliberately. rno0 has an
// OVL_EXPORT(EInitLockCamera) at 0x80180A80, and it is the WRONG object: the
// descriptor this entity actually uses is at 0x80180AA4, now named
// g_EInitLockCamera in e_init.c. Bridging to the plausible-looking name left
// one relocation-shaped difference of -0x24, which is 3 * sizeof(EInit).
#include "../entity_lock_camera.h"
