/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RDAI:func_us_801C6040
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/bo4/unk_45354.c
   target : src/st/rdai/func_46040.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rdai.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
s32 CheckMoveDirection(void);
void func_8010E570(s32);
void func_8010FAF4(void);
void func_8010E470(s32, s32);
Entity* CreateEntFactoryFromEntity(Entity* entity, u32, s32);
void func_8010E6AC(bool forceAnim13);
int abs(int x);
void func_us_801C59DC(void);
s32 func_us_801C5CF8(void);
void func_us_801C58E4(void);
void func_us_801C5990(void);
void func_us_801C5FDC(void);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern PlayerState g_Dop;
extern GameApi g_api;
extern Entity* g_CurrentEntity;

bool func_us_801C6040(s32 arg0) {
    s32 velocityX;
    s32 velocityY;
    u8 _pad[40]; // n.b.! needs to be 33-40 bytes (inclusive)

    if (arg0 & 8) {
        if (g_Dop.unk46 == 0) {
            CheckMoveDirection();
        }
    }

    if (arg0 & 0x8000) {
        DOPPLEGANGER.velocityY += FIX(11.0 / 64.0);
        if (DOPPLEGANGER.velocityY > FIX(7.0)) {
            DOPPLEGANGER.velocityY = FIX(7.0);
        }
    }
    if (arg0 & 0x10000) {
        if (DOPPLEGANGER.velocityY < FIX(3.0 / 8.0) &&
            DOPPLEGANGER.velocityY > -FIX(1.0 / 8.0) && !(g_Dop.unk44 & 0x20) &&
            (g_Dop.padPressed & 0x40)) {
            DOPPLEGANGER.velocityY += FIX(563.0 / 16384.0);
        } else {

            DOPPLEGANGER.velocityY += FIX(11.0 / 64.0);
            if (DOPPLEGANGER.velocityY > FIX(7.0)) {
                DOPPLEGANGER.velocityY = FIX(7.0);
            }
        }
    }

    if (arg0 & 0x80) {
        if (g_Dop.vram_flag & TOUCHING_CEILING) {
            if (DOPPLEGANGER.velocityY < FIX(-1)) {
                DOPPLEGANGER.velocityY = FIX(-1);
            }
        }
    }
    if (arg0 & 0x200) {
        if (DOPPLEGANGER.velocityY < FIX(3.0 / 8.0) &&
            DOPPLEGANGER.velocityY > -FIX(1.0 / 8.0)) {
            DOPPLEGANGER.velocityY += FIX(11.0 / 128.0);
        } else {
            DOPPLEGANGER.velocityY += FIX(11.0 / 64.0);
            if (DOPPLEGANGER.velocityY > FIX(7)) {
                DOPPLEGANGER.velocityY = FIX(7);
            }
        }
    }

    if (DOPPLEGANGER.velocityY >= 0) {
        if ((arg0 & 1) && (g_Dop.vram_flag & TOUCHING_GROUND)) {
            if (g_Dop.unk46) {
                if ((g_Dop.unk46 & 0x7FFF) == 0xFF) {
                    func_8010E570(0);
                    func_8010FAF4();
                    g_api.PlaySfx(SFX_STOMP_SOFT_B);
                    return true;
                }
                if (DOPPLEGANGER.velocityY > FIX(6.875)) {
                    func_8010E470(1, 0U);
                    g_api.PlaySfx(SFX_STOMP_HARD_B);
                    CreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
                } else {
                    if (g_Dop.unk44 & 0x10) {
                        func_8010E6AC(1);
                    } else {
                        func_8010E570(0);
                    }
                    g_api.PlaySfx(SFX_STOMP_SOFT_B);
                }
                func_8010FAF4();
                return true;
            }
            if (DOPPLEGANGER.velocityY > FIX(6.875)) {
                if (DOPPLEGANGER.step_s == 0x70 ||
                    DOPPLEGANGER.step == Dop_Jump) {
                    func_8010E470(3, DOPPLEGANGER.velocityX / 2);
                } else {
                    func_8010E470(1, 0);
                }
                g_api.PlaySfx(SFX_STOMP_HARD_B);
                CreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
            } else if (g_Dop.unk44 & 0x10) {
                func_8010E6AC(1);
                g_api.PlaySfx(SFX_STOMP_SOFT_B);
            } else if (abs(DOPPLEGANGER.velocityX) > FIX(2)) {
                g_api.PlaySfx(SFX_STOMP_HARD_B);
                CreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
                func_8010E570(DOPPLEGANGER.velocityX);
            } else {
                g_api.PlaySfx(SFX_STOMP_SOFT_B);
                func_8010E570(0);
            }
            return true;
        }

        if ((arg0 & 0x20000) && (g_Dop.vram_flag & TOUCHING_GROUND)) {
            func_8010E470(3, DOPPLEGANGER.velocityX);
            g_api.PlaySfx(SFX_STOMP_HARD_B);
            CreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
            return true;
        }
    }

    if ((arg0 & 4) && !(g_Dop.vram_flag & TOUCHING_GROUND)) {
        func_us_801C59DC();
        return true;
    }

    if ((arg0 & 0x1000) && (g_Dop.padTapped & 0xA0) && func_us_801C5CF8()) {
        return true;
    }

    if (!(g_Dop.unk46 & 0x8000)) {
        if ((arg0 & 0x10) && (g_Dop.padTapped & 0x40)) {
            func_us_801C58E4();
            return true;
        }

        if ((arg0 & 0x20) && (g_Dop.padTapped & 0x40) && !(g_Dop.unk44 & 1)) {
            func_us_801C5990();
            return true;
        }

        if ((arg0 & 0x2000) && (g_Dop.padPressed & 0x4000)) {
            func_8010E470(2, 0U);
            return true;
        }

        if ((arg0 & 0x40000) && (g_Dop.padTapped & 0x10) &&
            DOPPLEGANGER.ext.player.anim != 0xDB) {
            func_us_801C5FDC();
            return true;
        }
    }

    return false;
}
