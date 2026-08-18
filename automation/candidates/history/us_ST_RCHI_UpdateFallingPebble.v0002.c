/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCHI:UpdateFallingPebble
   attempt: 4/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/rchi/nonmatchings/e_demon_switch_wall/UpdateFallingPebble.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int Random();

/*
 * RCHI differs throughout these CHI-derived functions (branch layout,
 * constants, and wall control flow), so the CHI source is not byte-identical.
 */
void UpdateFallingPebble(Entity* self) {
    u8 step = ((u8*)&self->pfnUpdate)[3]; // unk2B: byte inside pfnUpdate
    u8 temp_v1_2;
    s16 temp_v0_2;

    switch (step) {
    case 1:
        temp_v1_2 = (Random() & 1) + 1;
        ((u8*)&self->velocityY)[0] = temp_v1_2; // unk0C: byte inside velocityY
        ((u8*)&self->velocityY)[1] = temp_v1_2; // unk0D: byte inside velocityY
        ((u8*)&self->posY)[0] = 0x60; // unk04: byte inside posY
        ((u8*)&self->posY)[1] = 0x80; // unk05: byte inside posY
        ((u8*)&self->posY)[2] = 0x30; // unk06: byte inside posY
        self->entityId = 0xA0; // unk26
        self->entityRoomIndex = 2; // unk32
        ((u8*)&self->rotate)[1] = (Random() & 0x1F) + 0x10; // unk1F: byte inside rotate
        ((u8*)&self->pfnUpdate)[3] = 2; // unk2B: byte inside pfnUpdate
        // fall through
    case 2:
        temp_v0_2 = ((u16*)&self->velocityX)[0] + 2; // unk0A: half inside velocityX
        temp_v1_2 = ((u8*)&self->rotate)[1] - 1; // unk1F: byte inside rotate
        ((u16*)&self->velocityX)[0] = temp_v0_2; // unk0A: half inside velocityX
        ((u8*)&self->rotate)[1] = temp_v1_2; // unk1F: byte inside rotate
        if (!(temp_v1_2 & 0xFF) || ((g_Tilemap.scrollY.i.hi + (s16)temp_v0_2) >= 0xA1)) {
            self->entityRoomIndex = 8; // unk32
            ((u8*)&self->pfnUpdate)[3] = 0; // unk2B: byte inside pfnUpdate
        }
        return;
    }
}

INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", EntityDemonSwitch);

INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", EntityDemonSwitchWall);
