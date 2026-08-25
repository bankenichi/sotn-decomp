/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801B8B64
   attempt: 4/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/boss/bo0/nonmatchings/2D26C/func_us_801B8B64.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo0.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
s32 Random();
void UnkPolyFunc0(Primitive* prim);
void UnkPrimHelper(Primitive* prim);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_us_801B163C();
extern int func_us_801B171C();
/* End permuter-seed writer declarations. */



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

s32 func_us_801B1E5C(void *arg0)
{
  void *entity = arg0;
  s32 result1;
  s32 result2;
  void *child = *((void **) (((char *) entity) + 0x18));
  func_us_801B163C(&g_CurrentEntity->ext.venusWeed.pad_90, 0, 0xC);
  result1 = func_us_801B171C(entity, -0x40, 0x40, 0x60);
 do { result2 = func_us_801B171C(child, -0x200, 0x280, 0x50); return (result1 + result2) == 2; } while (0);
}

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

void func_us_801B8B64(void* arg0) {
    Entity* entity = *(Entity**)arg0;
    s32 temp;
    s16 temp16;
    u32 temp_u32;
    s32 i;

    switch (entity->zPriority) {
    case 0:
        *(u8*)((s32)&entity->posY + 3) = 3; // unk07 inside posY
        entity->entityId = 0xAE;
        entity->entityRoomIndex = 2;
        *(u8*)((s32)&entity->pfnUpdate + 3) |= 0x30; // unk2B inside pfnUpdate
        temp = Random() & 0xF;
        temp = -((temp << 14) + 0x2000);
        entity->hitboxOffX = temp;
        *(u8*)((s32)&entity->pfnUpdate + 2) = 0; // unk2A inside pfnUpdate
        entity->scaleY = (Random() & 7) + 6;
        entity->rotate = (Random() & 7) + 6;
        entity->rotPivotX = 0x1000;
        entity->rotPivotY = 0x1000;
        entity->scaleX = 0;
        entity->step = 0;
        entity->step_s = 0;
        entity->zPriority = 1;
        break;

    case 1:
        entity->hitboxOffX -= 0x4000;
        temp = (Random() & 3) + 2;
        temp <<= 6;
        entity->step_s += temp;
        entity->step += 0x40;
        entity->scaleX += 0x40;
        entity->rotPivotX -= 0x40;
        entity->rotPivotY = entity->rotPivotX;
        temp16 = (entity->rotPivotX << 16) >> 20;
        temp16 = (temp16 + (temp16 >> 15)) >> 1;
        *(u8*)((s32)&entity->pfnUpdate + 2) = temp16; // unk2A inside pfnUpdate
        if ((s16)entity->rotPivotX < 0x100) {
            UnkPolyFunc0(arg0);
            return;
        }
        break;

    default:
        break;
    }

    UnkPrimHelper(arg0);
    i = arg0 + 0x1C;
    temp_u32 = *(u8*)i >> 1;
    i = arg0 + 0x1D;
    temp_u32 = *(u8*)i >> 1;
    i = arg0 + 0x1E;
    temp_u32 = *(u8*)i >> 1;
    // These assignments store to specific byte offsets of arg0 (unk10, unk04, unk11, unk05, unk12, unk06)
    *(s8*)(arg0 + 0x10) = (s8)((*(u8*)(arg0 + 0x1C)) >> 1);
    *(s8*)(arg0 + 0x04) = (s8)((*(u8*)(arg0 + 0x1C)) >> 1);
    *(s8*)(arg0 + 0x11) = (s8)((*(u8*)(arg0 + 0x1D)) >> 1);
    *(s8*)(arg0 + 0x05) = (s8)((*(u8*)(arg0 + 0x1D)) >> 1);
    *(s8*)(arg0 + 0x12) = (s8)((*(u8*)(arg0 + 0x1E)) >> 1);
    *(s8*)(arg0 + 0x06) = (s8)((*(u8*)(arg0 + 0x1E)) >> 1);
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8D8C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B9BEC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA030);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA128);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA4AC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA724);
