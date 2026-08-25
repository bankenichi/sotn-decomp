/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:func_us_801B41A4_from_bo0
   source : upstream/master:src/st/no2_bg.h
   target : src/st/rno2/unk_322E4.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", EntityBreakable);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", EntityBreakableDebris);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B3D8C_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B3F30_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B4148_from_bo0);

void func_us_801B41A4_from_bo0(Entity* self) {
    if (g_CurrentEntity->step == 0) {
        g_CurrentEntity->step++;
    }
    g_GpuBuffers[0].draw.r0 = 0x20;
    g_GpuBuffers[0].draw.g0 = 0x18;
    g_GpuBuffers[0].draw.b0 = 0x28;
    g_GpuBuffers[1].draw.r0 = 0x20;
    g_GpuBuffers[1].draw.g0 = 0x18;
    g_GpuBuffers[1].draw.b0 = 0x28;
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B4210_from_bo0);
