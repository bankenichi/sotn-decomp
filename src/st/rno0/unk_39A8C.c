// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// This is upstream's EntityIsNearPlayer from src/st/e_red_door.h, which 33
// other overlays already shim. rno0 cannot shim it yet: e_red_door.h also
// defines g_eRedDoorUV, and rno0 keeps .data in unnamed splat blobs (0x2C,
// 0xE20) rather than per-file segments, so including the header would emit
// that array at an address the linker script does not expect. See ROADMAP.md
// P3. Once rno0's .data and .bss are segmented, this whole file collapses to
// `#include "../e_red_door.h"` and this copy must be deleted.
//
// Keep the four separate locals. Writing it as one reassigned local
// (`dx = a - b; if (dx < 0) dx = -dx;`) compiles and reads identically but
// does NOT match: GCC then keeps the raw difference un-extended and only
// sign-extends at each use, emitting sll/sra once instead of twice. The
// original assigns the extended difference to `diffX` and the negation to
// `distanceX`, so each assignment truncates.
//
// The symbol stays func_us_801B9A8C rather than taking upstream's name
// because the EntityRedDoor assembly below still calls it by that name.
bool func_us_801B9A8C(Entity* self) {
    s16 distanceX;
    s16 diffX;
    s16 distanceY;
    s16 diffY;

    diffX = PLAYER.posX.i.hi - self->posX.i.hi;
    distanceX = abs(diffX);
    if (distanceX > 16) {
        return false;
    }

    diffY = PLAYER.posY.i.hi - self->posY.i.hi;
    distanceY = abs(diffY);
    if (distanceY > 32) {
        return false;
    }

    return true;
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_39A8C", EntityRedDoor);
