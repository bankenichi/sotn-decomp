// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo6.h"

// The next three are HARVESTED from upstream/master src/boss/bo6/us_39144.c.
// Upstream calls the helpers by their bare RIC names; this fork exports them
// with a BO6_ prefix, so each call site is rewritten. The mapping is only
// ever taken from a definition that already exists in this file or from
// config/symbols.us.bobo6.txt, never guessed:
//     RicSetAnimation             -> BO6_RicSetAnimation
//     RicCreateEntFactoryFromEntity -> BO6_RicCreateEntFactoryFromEntity
//     RicSetStand                 -> BO6_RicSetStand
//     RicResetPose                -> BO6_RicResetPose  (richter.c)
//     RicCheckInput               -> BO6_RicCheckInput
// func_us_801B9ACC and DecelerateX keep their names: this fork already
// defines both under exactly those spellings, further down.

extern s32 D_us_80181278;
extern AnimationFrame D_us_80181F1C[];
extern AnimationFrame D_us_801823C8[];

// ending 2 function
void func_us_801B9144(void) {
    Entity* entity;
    switch (RIC.step_s) {
    case 0:
        BO6_RicSetAnimation(D_us_80181F1C);
        g_api.PlaySfx(SFX_BOSS_RIC_LAUGH);
        if (RIC.posX.i.hi < 0x80) {
            RIC.facingLeft = 0;
        } else {
            RIC.facingLeft = 1;
        }
        RIC.step_s++;
        // fallthrough

    case 1:
        D_us_80181278 = 0x14;
        entity = &g_Entities[200];
        CreateEntityFromCurrentEntity(E_ID_17, entity);
        entity->params = 1;
        RIC.step_s++;
        // fallthrough

    case 2:
        if (D_us_80181278 == 0x1E) {
            BO6_RicSetAnimation(D_us_801823C8);
            BO6_RicCreateEntFactoryFromEntity(
                g_CurrentEntity, FACTORY(E_ID_24, 0x1), 0);
            RIC.step_s++;
        }
        break;
    case 3:
        if (RIC.animCurFrame == 0xB5) {
            if (RIC.poseTimer == 1) {
                BO6_RicCreateEntFactoryFromEntity(
                    g_CurrentEntity, FACTORY(E_ID_23, 0), 0);
                g_api.PlaySfx(SFX_WEAPON_APPEAR);
            }
        }
        if (RIC.poseTimer < 0) {
            D_us_80181278 = 0x28;
            BO6_RicSetStand(0);
            BO6_RicCreateEntFactoryFromEntity(
                g_CurrentEntity, FACTORY(E_ID_21, 0x45), 0);
            g_Ric.timers[ALU_T_POISON] = 0x800;
        }
        break;
    }
}

// Empty stub
void func_us_801B9338(void) {}

extern s16 D_us_8018221C[];

void func_us_801B9340(void) {
    switch (RIC.step_s) {
    case 0:
        BO6_RicResetPose();
        RIC.velocityY = FIX(-5);
        func_us_801B9ACC(0xFFFF1000);
        RIC.anim = D_us_8018221C;
        g_api.PlaySfx(SFX_BOSS_RIC_DEATH);
        g_Ric.damagePalette = 0x8166;
        g_Ric.timers[2] = 8;
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 0x58), 0);
        RIC.step_s += 1;
        return;
    case 1:
        if ((g_Ric.vram_flag & TOUCHING_CEILING) && (FIX(-1) > RIC.velocityY)) {
            RIC.velocityY = FIX(-1);
        }
        if (BO6_RicCheckInput(0x20280) != 0) {
            RIC.step = 0x70;
            RIC.step_s = 2;
            return;
        }
        return;
    case 2:
        DecelerateX(FIX(0.125));
        if ((PLAYER.posX.i.hi - RIC.posX.i.hi) > 0) {
            RIC.facingLeft = 0;
            return;
        }
        RIC.facingLeft = 1;
        break;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B94CC);

extern u8 D_us_80181298[];
extern u8 D_us_801812A8[];

// The after-image fade. No renames were needed here at all: it only touches
// g_Entities, g_PrimBuf and g_PlayerDraw, none of which the fork re-exports.
void func_us_801B96F4(void) {
    byte pad[0x28];
    Primitive* prim;
    PlayerDraw* draw;
    s32 i;
    u8 var_s3;
    u8 var_s5;
    u8 resetAnim;

    resetAnim = g_Entities[65].ext.afterImage.resetFlag;
    prim = &g_PrimBuf[g_Entities[65].primIndex];
    i = 0;
    draw = &g_PlayerDraw[9];
    var_s5 = D_us_80181298[g_Entities[65].ext.afterImage.index];
    var_s3 = D_us_801812A8[g_Entities[65].ext.afterImage.index];
    while (prim != NULL) {
        if (prim->r0 > var_s3) {
            prim->r0 -= var_s5;
        }
        if (prim->r0 < 112 && prim->b0 < 240) {
            prim->b0 += 6;
        }
        if (prim->r0 < 88) {
            prim->y1 = 16;
        } else {
            prim->y1 = 0;
        }
        if (prim->r0 <= var_s3) {
            prim->x1 = 0;
        }
        if ((i ^ g_Timer) & 1) {
            g_Entities[i / 2 + 65].posX.i.hi = prim->x0;
            g_Entities[i / 2 + 65].posY.i.hi = prim->y0;
            g_Entities[i / 2 + 65].animCurFrame = prim->x1;
            g_Entities[i / 2 + 65].blendMode = prim->y1;
            g_Entities[i / 2 + 65].facingLeft = prim->x2;
            g_Entities[i / 2 + 65].palette = prim->y2;
            g_Entities[i / 2 + 65].zPriority = RIC.zPriority - 2;
            if (resetAnim) {
                g_Entities[i / 2 + 65].animCurFrame = 0;
                prim->x1 = 0;
            }

            draw->r0 = draw->r1 = draw->r2 = draw->r3 = draw->g0 = draw->g1 =
                draw->g2 = draw->g3 = prim->r0;
            draw->b0 = draw->b1 = draw->b2 = draw->b3 = prim->b0;
            draw->enableColorBlend = true;
            draw++;
        }
        i++;
        prim = prim->next;
    }
}

extern u16 RIC_step;

// Richter (BO6): set state machine step and clear the sub-step counter.
void BO6_RicSetStep(s32 step) {
    RIC_step = step;
    RIC.step_s = 0;
}

// Richter (BO6): set animation and clear pose state
void BO6_RicSetAnimation(AnimationFrame *animFrame) {
    g_CurrentEntity->anim = animFrame;
    g_CurrentEntity->poseTimer = 0;
    g_CurrentEntity->pose = 0;
}

// Richter (BO6): reduce X velocity toward zero by deceleration amount, clamping at 0
void DecelerateX(s32 deceleration) {
    s32 velocityX;
    s32 newVelocityX;
    s32 newVelocityX_2;

    velocityX = g_CurrentEntity->velocityX;
    if (velocityX < 0) {
        newVelocityX = deceleration + velocityX;  // moving left, add deceleration
        g_CurrentEntity->velocityX = newVelocityX;
        if (newVelocityX > 0) {  // overshot to positive
            g_CurrentEntity->velocityX = 0;
        }
    } else {
        newVelocityX_2 = velocityX - deceleration;  // moving right, subtract deceleration
        g_CurrentEntity->velocityX = newVelocityX_2;
        if (newVelocityX_2 < 0) {  // overshot to negative
            g_CurrentEntity->velocityX = 0;
        }
    }
}

// Richter (BO6): reduce Y velocity toward zero by deceleration amount, clamping at 0
void DecelerateY(s32 deceleration) {
    s32 velocityY;
    s32 newVelocityY;
    s32 newVelocityY_2;

    velocityY = g_CurrentEntity->velocityY;
    if (velocityY < 0) {
        newVelocityY = deceleration + velocityY;  // moving up, add deceleration
        g_CurrentEntity->velocityY = newVelocityY;
        if (newVelocityY > 0) {  // overshot to positive
            g_CurrentEntity->velocityY = 0;
        }
    } else {
        newVelocityY_2 = velocityY - deceleration;  // moving down, subtract deceleration
        g_CurrentEntity->velocityY = newVelocityY_2;
        if (newVelocityY_2 < 0) {  // overshot to negative
            g_CurrentEntity->velocityY = 0;
        }
    }
}

// Richter (BO6): turn to follow the pad, and report which way the player is
// pushing. Returns -1 when the facing changed this frame, 1 when the pad is
// already pushing the way Richter faces, 0 otherwise.
//
// This is BO6's copy of RicCheckFacing in src/ric/pl_utils.c. Not shareable:
// RIC's version reads g_Player and PLAYER, BO6's reads g_Ric and RIC, and
// those are different objects in the same address space.
//
// Symbol resolution, all confirmed by address rather than by name affinity:
//   g_Ric + 0x394 -> PlayerState.unk44      (game.h:1976)
//   g_Ric + 0x318 -> PlayerState.padPressed (game.h:1946)
//   g_Ric + 0x39C -> PlayerState.unk4C      (game.h:1984)
//   0x800762EC    -> g_Entities[64] + 0x14, which is RIC.facingLeft; the
//                    splat symbol RIC_facingLeft in symbols.us.bobo6.txt
//                    names the same address.
// Verbatim copy of CheckMoveDirection in src/boss/rbo5/unk_44954.c.
// Kept in sync by hand: this file cannot include that header.
s32 BO6_RicCheckFacing(void) {
    if (g_Ric.unk44 & 2) {
        return 0;
    }

    if (RIC.facingLeft == 1) {
        if (g_Ric.padPressed & PAD_RIGHT) {
            RIC.facingLeft = 0;
            g_Ric.unk4C = 1;
            return -1;
        } else if (g_Ric.padPressed & PAD_LEFT) {
            return 1;
        }
    } else {
        if (g_Ric.padPressed & PAD_RIGHT) {
            return 1;
        }
        if (g_Ric.padPressed & PAD_LEFT) {
            RIC.facingLeft = 1;
            g_Ric.unk4C = 1;
            return -1;
        }
    }
    return 0;
}

// Richter (BO6): set X velocity with facing direction applied
void BO6_RicSetSpeedX(s32 speed) {
    s32 signedSpeed;

    signedSpeed = speed;
    if (g_CurrentEntity->facingLeft == 1) {
        signedSpeed = -signedSpeed;  // negate if facing left
    }
    g_CurrentEntity->velocityX = signedSpeed;
}

extern s32 RIC_velocityX;

// Richter (BO6): set RIC_velocityX with the facing direction applied. The side
// flag is Richter's entityRoomIndex (RIC + 0x32), which func_us_801B77D8 in
// richter.c sets from the player's position; the original reuses that field
// rather than the entity's own facingLeft at +0x14.
void func_us_801B9ACC(s32 speed) {
    s32 signedSpeed;

    signedSpeed = speed;
    if (RIC.entityRoomIndex == 1) {
        signedSpeed = -signedSpeed;  // negate when the player is to the left
    }
    RIC_velocityX = signedSpeed;
}

// Richter (BO6): raise an invincibility timer to at least
// `invincibilityFrames`, never lower it. kind == 0 uses the scene timer and
// also spawns the crash-dagger blueprint; anything else uses the ordinary
// invincibility timer. Twin of RicSetInvincibilityFrames in src/ric/pl_utils.c,
// semantically identical.
//
// Timer indices resolved by address: g_Ric + 0x34A and + 0x34C, with
// PlayerState.timers at +0x330, give (0x34A-0x330)/2 = 13 and 14.
//
// The comparison direction is the easy thing to get backwards. The asm does
// `slt $v0, $v0, $v1` on (frames < timer) and BRANCHES OVER the store, so the
// store happens when timer <= frames.
void BO6_RicSetInvincibilityFrames(s32 kind, s16 invincibilityFrames) {
    if (!kind) {
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(BP_CRASH_DAGGER, 0x15), 0);
        if (g_Ric.timers[PL_T_INVINCIBLE_SCENE] <= invincibilityFrames) {
            g_Ric.timers[PL_T_INVINCIBLE_SCENE] = invincibilityFrames;
        }
    } else if (g_Ric.timers[PL_T_INVINCIBLE] <= invincibilityFrames) {
        g_Ric.timers[PL_T_INVINCIBLE] = invincibilityFrames;
    }
}

/**
 * Disables Richter's stage-owned afterimage entities. This is the same shape
 * as DisableAfterImage in src/ric/pl_utils.c, except BO6 keeps the player and
 * its three afterimages in entity slots 0x40 through 0x43. The target addresses
 * identify slots E_ID_41 through E_ID_43, and g_Ric + 0x34E identifies timer
 * PL_T_AFTERIMAGE_DISABLE. RIC's US-only debug print is absent from this copy.
 */
void BO6_DisableAfterImage(s32 resetAnims, s32 arg1) {
    Primitive* prim;

    if (resetAnims) {
        g_Entities[E_ID_41].ext.disableAfterImage.resetFlag = 1;
        g_Entities[E_ID_41].animCurFrame =
            g_Entities[E_ID_42].animCurFrame =
                g_Entities[E_ID_43].animCurFrame = 0;
        prim = &g_PrimBuf[g_Entities[E_ID_41].primIndex];
        while (prim) {
            prim->x1 = 0;
            prim = prim->next;
        }
    }
    g_Entities[E_ID_41].ext.disableAfterImage.disableFlag = 1;
    g_Entities[E_ID_41].ext.disableAfterImage.index = MaxAfterImageIndex;
    if (arg1) {
        g_Ric.timers[PL_T_AFTERIMAGE_DISABLE] = 4;
    }
}

// Richter (BO6): reset the afterimage effect state.
// Same idiom as src/boss/bo4/unk_45354.c and src/boss/rbo5/unk_44954.c.
void func_us_801B9C14(void) {
    g_Entities[STAGE_ENTITY_START + E_AFTERIMAGE_1].ext.afterImage.timer = 0;
    g_Entities[STAGE_ENTITY_START + E_AFTERIMAGE_1].ext.afterImage.index = 0;
    g_Entities[STAGE_ENTITY_START + E_AFTERIMAGE_1].ext.afterImage.resetFlag = 0;
    g_Entities[STAGE_ENTITY_START + E_AFTERIMAGE_1].ext.afterImage.disableFlag = 0;
}

void BO6_RicSetStep(s32);

// Richter (BO6): enter the debug step. RIC's equivalent is explicit:
// src/ric/pl_setstep.c RicSetDebug() { RicSetStep(PL_S_DEBUG); }
void func_us_801B9C3C(void) {
    BO6_RicSetStep(PL_S_DEBUG);
}

// BO6 animation tables corresponding, in order, to RIC's crouch-from-stand2,
// crouch, land-from-air-run, and crouch-from-stand tables.
extern AnimationFrame D_us_80182038[];
extern AnimationFrame D_us_80182048[];
extern AnimationFrame D_us_80182050[];
extern AnimationFrame D_us_80182058[];

// Richter (BO6): enter crouch using the same state variants as RicSetCrouch.
void BO6_RicSetCrouch(s32 kind, s32 velocityX) {
    BO6_RicSetStep(PL_S_CROUCH);
    BO6_RicSetAnimation(D_us_80182048);
    RIC.velocityX = velocityX;
    RIC.velocityY = 0;
    if (kind == 1) {
        RIC.anim = D_us_80182038;
        RIC.step_s = 4;
    }
    if (kind == 2) {
        RIC.anim = D_us_80182058;
        RIC.step_s = 1;
    }
    if (kind == 3) {
        RIC.anim = D_us_80182050;
        RIC.step_s = 4;
    }
}

extern s32 RIC_velocityY;
extern AnimationFrame ric_anim_stand[];

// Richter (BO6): transition to the standing state - zero velocity, clear
// unk44 (crouch/step-related flag), set step 1 and the standing animation
void BO6_RicSetStand(s32 velocityX) {
    RIC_velocityX = velocityX;
    RIC_velocityY = 0;
    g_Ric.unk44 = 0;
    BO6_RicSetStep(1);
    BO6_RicSetAnimation(ric_anim_stand);
}

extern PlayerState g_Ric;
extern void BO6_RicSetStep(s32);
extern void BO6_RicSetAnimation(AnimationFrame*);
extern void BO6_RicSetSpeedX(s32);
extern Entity* g_CurrentEntity;
extern s32 RIC_velocityY;
extern AnimationFrame D_us_801821F8;
extern Entity* BO6_RicCreateEntFactoryFromEntity(Entity*, u32, s32);

// Sets up Richter's initial state for the BO6 boss fight intro:
// resets hitParams, sets step 0x1A, plays intro animation,
// sets walk speed, resets vertical velocity, and spawns entity factory.
void func_us_801B9D74(void) {
    g_Ric.unk44 = 0;
    BO6_RicSetStep(0x1A);
    BO6_RicSetAnimation(&D_us_801821F8);
    BO6_RicSetSpeedX(0x24000);
    g_Ric.timers[0xB] = 0x28;
    RIC_velocityY = 0;
    BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x50001U, 0);
}

extern AnimationFrame D_us_80182010[];
void func_us_801B9D74(void);

// Richter (BO6): if the dash timer is still running, defer to the dash handler;
// otherwise begin the dash - arm timers[1] and timers[8], clear unk44, and set
// step 2 with the dash animation and speed.
void func_us_801B9DE4(s32 unused) {
    if (g_Ric.timers[8] != 0) {
        func_us_801B9D74();
        return;
    }
    // The redundant store to timers[1] is present in the original asm at
    // 0x39E18 and 0x39E28; it is not a transcription error.
    g_Ric.timers[1] = 8;
    g_Ric.timers[8] = 0xC;
    g_Ric.timers[1] = 0xC;
    g_Ric.unk44 = 0;
    BO6_RicSetStep(2);
    BO6_RicSetAnimation(D_us_80182010);
    BO6_RicSetSpeedX(0x14000);
    RIC_velocityY = 0;
}

extern s16 D_us_80182078[];
extern s16 D_us_80182094[];

// HARVESTED from upstream/master src/boss/bo6/us_39144.c. Same BO6_ call-site
// mapping as the three at the top of this file.
void func_us_801B9E70(void) {
    if ((BO6_RicCheckFacing() != 0) || (RIC.step == 0x18)) {
        BO6_RicSetAnimation(D_us_80182094);
        if (RIC.step == 0x1A) {
            BO6_RicSetSpeedX(FIX(2.25));
            g_Ric.unk44 = 0x10;
        } else {
            BO6_RicSetSpeedX(0x14000);
            g_Ric.unk44 = 0;
        }
    } else {
        BO6_RicSetAnimation(D_us_80182078);
        RIC.velocityX = 0;
        g_Ric.unk44 = 4;
    }
    BO6_RicSetStep(5);
    RIC.velocityY = FIX(-4.6875);
}

extern AnimationFrame D_us_801820BC[];

// Richter (BO6): enter the falling step. BO6's RicSteps values are one above
// the playable RIC values, and the target comparisons match the BO6 enum.
void BO6_RicSetFall(void) {
    if (g_Ric.prev_step != PL_S_RUN && g_Ric.prev_step != PL_S_SLIDE) {
        RIC.velocityX = 0;
    }
    if (g_Ric.prev_step != PL_S_WALK && g_Ric.prev_step != PL_S_RUN) {
        BO6_RicSetAnimation(D_us_801820BC);
    }
    if (g_Ric.prev_step == PL_S_RUN) {
        g_Ric.unk44 = 0x10;
    }
    BO6_RicSetStep(PL_S_FALL);
    RIC.velocityY = FIX(2);
    g_Ric.timers[PL_T_5] = 8;
    g_Ric.timers[PL_T_6] = 8;
    g_Ric.timers[PL_T_CURSE] = 0;
    g_Ric.timers[PL_T_8] = 0;
    if (g_Ric.prev_step == PL_S_SLIDE) {
        g_Ric.timers[PL_T_5] = g_Ric.timers[PL_T_6] = 0;
        RIC.pose = 2;
        RIC.poseTimer = 0x10;
        RIC.velocityX /= 2;
    }
}

extern AnimationFrame D_us_80182324;

void func_us_801BA050(void) {
    BO6_RicSetStep(9);
    RIC_velocityX = 0;
    BO6_RicSetSpeedX(0x14000);
    RIC_velocityY = -0x78000;
    g_Ric.high_jump_timer = 0;
    BO6_RicSetAnimation(&D_us_80182324);
    func_us_801B9C14();
    BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x2D, 0);
    g_api_PlaySfx(0x82D);
    g_Ric.timers[0xC] = 4;
}

// Richter (BO6): refuse to spawn another subweapon if `limit` of the same id
// are already live, or if there is no free slot at all.
//
// Twin of RicCheckSubwpnChainLimit in src/ric/pl_setstep.c, where it is
// static. It must NOT be static here: assembly still stubbing the rest of this
// overlay calls it across translation units.
//
// Real difference from RIC: the scanned window. RIC walks g_Entities[32..47],
// 16 slots. BO6 walks g_Entities[96..127], 32 slots. The base came out of the
// induction variable: the loop loads at D_80077B08 with member offset 0xB0, so
// the entity base is 0x80077B08 - 0xB0 = 0x80077A58, which is g_Entities + 96
// exactly. The count is the literal in `slti $a3, 0x20`.
s32 BO6_RicCheckSubwpnChainLimit(s16 subwpnId, s16 limit) {
    Entity* entity;
    s32 i;
    s32 nFound;
    s32 nEmpty;

    entity = &g_Entities[STAGE_ENTITY_START + 32];
    for (i = 0, nFound = 0, nEmpty = 0; i < 32; i++, entity++) {
        if (!entity->entityId) {
            nEmpty++;
        }
        if (entity->ext.subweapon.subweaponId &&
            entity->ext.subweapon.subweaponId == subwpnId) {
            nFound++;
        }
        if (nFound >= limit) {
            return -1;
        }
    }
    if (nEmpty) {
        return 0;
    }
    return -1;
}

extern AnimationFrame D_us_80182170[];
extern AnimationFrame D_us_801821C0[];
extern AnimationFrame D_us_80182110[];
extern AnimationFrame D_us_80182130[];
extern AnimationFrame D_us_80182150[];
extern s32 BO6_RicCheckSubweapon(SubweaponDef*, s32, s32);

// Richter (BO6): create the selected subweapon and move Richter into the
// matching throw animation. Unlike playable RIC, this target performs one
// selection lookup and relies on its result directly.
s32 BO6_RicDoSubweapon(void) {
    SubweaponDef subweapon;
    s16 subweaponId;
    s16 chainLimit;
    s16 unused; // Retained from the twin; the compiler removes the assignment.

    unused = 0;
    if (!(g_Ric.padPressed & PAD_UP)) {
        return 1;
    }

    subweaponId = BO6_RicCheckSubweapon(&subweapon, false, false);
    chainLimit = subweapon.chainLimit;
    if (BO6_RicCheckSubwpnChainLimit(subweaponId, chainLimit) < 0) {
        return 2;
    }

    BO6_RicCreateEntFactoryFromEntity(
        g_CurrentEntity, subweapon.blueprintNum, 0);
    g_Ric.timers[PL_T_10] = 4;
    switch (RIC.step) {
    case PL_S_RUN:
        RIC.step = PL_S_STAND;
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, BP_SKID_SMOKE, 0);
        BO6_RicSetAnimation(D_us_80182170);
        break;
    case PL_S_STAND:
    case PL_S_WALK:
    case PL_S_CROUCH:
        RIC.step = PL_S_STAND;
        BO6_RicSetAnimation(D_us_80182170);
        break;
    case PL_S_FALL:
    case PL_S_JUMP:
        RIC.step = PL_S_JUMP;
        BO6_RicSetAnimation(D_us_801821C0);
        break;
    }
    g_Ric.unk46 = 3;
    RIC.step_s = 0x42;
    g_Ric.timers[PL_T_10] = 4;
    return 0;
}

// Richter (BO6): start a whip attack or hand control to the subweapon path.
// The RIC twin supplies the control flow; BO6 uses its boss voice bank,
// animations, entity window and factory table.
bool BO6_RicDoAttack(void) {
    s32 i;
    s16 poisoned;
    s16 sfxGrunt;

    sfxGrunt = rand() % 6;
    if (BO6_RicDoSubweapon() == 0) {
        if (sfxGrunt == 0) {
            g_api_PlaySfx(SFX_BOSS_RIC_ATTACK_A);
        }
        if (sfxGrunt == 1) {
            g_api_PlaySfx(SFX_BOSS_RIC_ATTACK_B);
        }
        if (sfxGrunt == 2) {
            g_api_PlaySfx(SFX_BOSS_RIC_ATTACK_C);
        }
        if (sfxGrunt == 3) {
            g_api_PlaySfx(SFX_BOSS_RIC_ATTACK_D);
        }
        return true;
    }
    if (g_Ric.timers[PL_T_POISON]) {
        poisoned = true;
    } else {
        poisoned = false;
    }
    for (i = STAGE_ENTITY_START + 16; i < STAGE_ENTITY_START + 31; i++) {
        DestroyEntity(&g_Entities[i]);
    }
    if (BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(BP_WHIP, poisoned), 0)) {
        if (poisoned) {
            g_api_PlaySfx(SFX_RIC_FLAME_WHIP);
        } else {
            g_api_PlaySfx(SFX_BOSS_RIC_WHIP_ATTACK);
        }
        if (sfxGrunt == 0) {
            g_api_PlaySfx(SFX_BOSS_RIC_ATTACK_A);
        }
        if (sfxGrunt == 1) {
            g_api_PlaySfx(SFX_BOSS_RIC_ATTACK_B);
        }
        if (sfxGrunt == 2) {
            g_api_PlaySfx(SFX_BOSS_RIC_ATTACK_C);
        }
        if (sfxGrunt == 3) {
            g_api_PlaySfx(SFX_BOSS_RIC_ATTACK_D);
        }
        switch (RIC.step) {
        case PL_S_STAND:
        case PL_S_WALK:
            RIC.step = PL_S_STAND;
            BO6_RicSetAnimation(D_us_80182110);
            g_CurrentEntity->velocityX = 0;
            break;
        case PL_S_RUN:
            RIC.step = PL_S_STAND;
            BO6_RicSetAnimation(D_us_80182110);
            BO6_RicCreateEntFactoryFromEntity(
                g_CurrentEntity, BP_SKID_SMOKE, 0);
            break;
        case PL_S_CROUCH:
            BO6_RicSetAnimation(D_us_80182130);
            g_CurrentEntity->velocityX = 0;
            break;
        case PL_S_FALL:
        case PL_S_JUMP:
            RIC.step = PL_S_JUMP;
            BO6_RicSetAnimation(D_us_80182150);
            break;
        default:
            return false;
        }
        g_Ric.unk46 = 1;
        RIC.step_s = 0x40;
        g_Ric.timers[PL_T_ATTACK] = 4;
        return true;
    }
    return false;
}

extern AnimationFrame D_us_80182190[];
extern AnimationFrame D_us_801821E0[];
extern AnimationFrame D_us_80182334[];
extern AnimationFrame D_us_8018246C[];

// Richter (BO6): start the AI-selected subweapon crash. This follows the RIC
// twin's factory and state transitions, but BO6 performs one selector call,
// does not spend hearts, and uses the boss animation and voice banks.
bool BO6_RicDoCrash(void) {
    SubweaponDef subWpn;
    Entity* subWpnEnt;
    s16 subWpnID;

    subWpnID = BO6_RicCheckSubweapon(&subWpn, true, false);
    if (subWpnID == SUBWPN_HOLYWATER && g_Ric.timers[PL_T_3]) {
        return false;
    }

    if (subWpn.blueprintNum) {
        if (subWpnID == SUBWPN_DAGGER) {
            subWpnEnt = BO6_RicCreateEntFactoryFromEntity(
                g_CurrentEntity, FACTORY(subWpn.blueprintNum, 1), 0);
        } else {
            subWpnEnt = BO6_RicCreateEntFactoryFromEntity(
                g_CurrentEntity, FACTORY(subWpn.blueprintNum, 0), 0);
        }
    }
    // The target tests the register even when blueprintNum is zero. Preserve
    // the original uninitialized local rather than inventing a default value.
    if (subWpnEnt == NULL) {
        return false;
    }

    g_Ric.unk46 = 4;
    g_Ric.unk4E = 0;
    RIC.velocityX = RIC.velocityY = 0;
    switch (subWpnID) {
    case SUBWPN_NONE:
        BO6_RicSetStep(PL_S_FLAME_WHIP);
        BO6_RicSetAnimation(D_us_801823C8);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_24, 1), 0);
        break;

    case SUBWPN_DAGGER:
        BO6_RicSetStep(PL_S_THROW_DAGGERS);
        BO6_RicSetAnimation(D_us_80182190);
        g_api_PlaySfx(SFX_BOSS_RIC_ITEM_CRASH_ATTACK);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 2), 0);
        break;

    case SUBWPN_AXE:
        BO6_RicSetStep(PL_S_STAND_IN_AIR);
        BO6_RicSetAnimation(D_us_801821E0);
        RIC.velocityY = FIX(-4.6875);
        func_us_801B9C14();
        g_api_PlaySfx(SFX_BOSS_RIC_ITEM_CRASH_ATTACK);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 2), 0);
        break;

    case SUBWPN_HOLYWATER:
        BO6_RicSetStep(PL_S_HYDROSTORM);
        BO6_RicSetAnimation(D_us_80182334);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 0x40), 0);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 0x47), 0);
        g_api_PlaySfx(SFX_BOSS_RIC_HYDRO_STORM);
        break;

    case SUBWPN_REBNDSTONE:
    case SUBWPN_VIBHUTI:
    case SUBWPN_AGUNEA:
        BO6_RicSetStep(PL_S_SUBWPN_CRASH);
        BO6_RicSetAnimation(D_us_80182334);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 0x40), 0);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 0x47), 0);
        g_api_PlaySfx(SFX_BOSS_RIC_ITEM_CRASH_ATTACK);
        break;

    case SUBWPN_BIBLE:
    case SUBWPN_STOPWATCH:
        BO6_RicSetStep(PL_S_SUBWPN_CRASH);
        BO6_RicSetAnimation(D_us_8018246C);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 0x40), 0);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 0x47), 0);
        g_api_PlaySfx(SFX_BOSS_RIC_ITEM_CRASH_ATTACK);
        break;

    case SUBWPN_CROSS:
        BO6_RicSetStep(PL_S_STAND_IN_AIR);
        BO6_RicSetAnimation(D_us_801821E0);
        RIC.velocityY = FIX(-4.6875);
        func_us_801B9C14();
        g_api_PlaySfx(SFX_BOSS_RIC_HOLY_CROSS);
        BO6_RicCreateEntFactoryFromEntity(
            g_CurrentEntity, FACTORY(E_ID_21, 2), 0);
        break;
    }

    g_Ric.timers[PL_T_12] = 4;
    return true;
}

// Richter (BO6): set step to 0x17 (death prologue/dying state)
void BO6_RicSetDeadPrologue(void) {
    BO6_RicSetStep(0x17);
}

extern AnimationFrame D_us_801822D8[];
void func_us_801B9C14(void);

// Richter (BO6): enter the slide - face the target, set step 0x18 and the slide
// animation, kill vertical velocity, set slide speed, clear the afterimage
// fields, spawn the slide effect, play the slide sfx and arm timers[0xC].
void BO6_RicSetSlide(void) {
    BO6_RicCheckFacing();
    BO6_RicSetStep(0x18);
    BO6_RicSetAnimation(D_us_801822D8);
    g_CurrentEntity->velocityY = 0;
    BO6_RicSetSpeedX(0x58000);
    func_us_801B9C14();
    BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x19, 0);
    g_api_PlaySfx(0x826);
    g_Ric.timers[0xC] = 4;
}

extern AnimationFrame D_us_80182304[];

// Richter (BO6): enter the slide kick. Twin of RicSetSlideKick in
// src/ric/pl_setstep.c.
//
// One real divergence: the sfx. RIC plays SFX_VO_RIC_ATTACK_B (0x6FA); BO6
// plays 0x82C from the boss-Richter voice bank (`ori $a0, $zero, 0x82C` at
// 0x3A99C). RIC also calls through the g_api struct where BO6 loads the
// standalone g_api_PlaySfx pointer, matching BO6_RicSetSlide above.
void BO6_RicSetSlideKick(void) {
    g_Ric.unk44 = 0;
    BO6_RicSetStep(PL_S_SLIDE_KICK);
    BO6_RicSetAnimation(D_us_80182304);
    g_CurrentEntity->velocityY = FIX(-2);
    BO6_RicSetSpeedX(FIX(5.5));
    func_us_801B9C14();
    BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, BP_25, 0);
    g_api_PlaySfx(0x82C);
    g_Ric.timers[PL_T_12] = 4;
    BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, BP_31, 0);
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BA9D0);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicCheckInput);

// Richter (BO6): first unused entity slot in [start, end), or NULL.
// Straight port of RicGetFreeEntity in src/ric/pl_blueprints.c, where it is
// static. It cannot be static here: the assembly still stubbing the rest of
// this overlay calls it across translation units, and a C grep cannot see
// those call sites.
Entity* BO6_RicGetFreeEntity(s16 start, s16 end) {
    Entity* entity = &g_Entities[start];
    s16 i;

    for (i = start; i < end; i++, entity++) {
        if (entity->entityId == E_NONE) {
            return entity;
        }
    }
    return NULL;
}

// Richter (BO6): as above, but searching downward from the top of the range.
// Port of RicGetFreeEntityReverse in src/ric/pl_blueprints.c.
//
// The assembly's base symbol is D_8007331C, which is g_Entities - 0xBC, one
// Entity below the array. That is not a separate object: it is what GCC folds
// `&g_Entities[end - 1]` into, hoisting the -1 into the base address so the
// index scales cleanly. Declaring D_8007331C as a global would have invented
// a symbol for an address that already has a meaning.
Entity* BO6_RicGetFreeEntityReverse(s16 start, s16 end) {
    Entity* entity = &g_Entities[end - 1];
    s16 i;

    for (i = end - 1; i >= start; i--, entity--) {
        if (entity->entityId == E_NONE) {
            return entity;
        }
    }
    return NULL;
}

extern AnimationFrame* D_us_801812B8[];
extern u8 D_us_801D07FC;
extern u8 D_us_801812B9[];
extern u8 D_us_801D0800;
extern u8 D_us_801812BA[];
extern u8 D_us_801D0804;
extern u8 D_us_801812BB[];
extern u8 D_us_801D0808;

// Copies boss animation frame data into working variables for the current frame index
void func_us_801BB314(s32 arg0) {
    s32 index;

    // arg0 is the frame index; multiply by 4 to get byte offset into pointer arrays
    index = arg0 * 4;

    // D_us_801812B8 is AnimationFrame*[], so D_us_801812B8[arg0] loads the pointer value
    // The asm treats it as a byte load from the pointer array entry (low byte of pointer)
    D_us_801D07FC = (u8)(s32)D_us_801812B8[arg0];

    // D_us_801812B9/BA/BB are u8 arrays indexed by the same scaled index
    D_us_801D0800 = D_us_801812B9[index];
    D_us_801D0804 = D_us_801812BA[index];
    D_us_801D0808 = D_us_801812BB[index];
}

extern SubweaponDef subweapons_def[];

// Load a subweapon entity's combat attributes from the subweapon table, indexed
// by the entity's own subweaponId. Every offset the original uses lines up with
// SubweaponDef (size 0x14, which is the stride the index is multiplied by), so
// there is nothing here that needs a raw cast.
//
// While Richter's invincibility timer is running the base attack is doubled.
// The original reads `attack` as SIGNED on that path and UNSIGNED on the other,
// which is why the two branches are not written as one expression.
void func_us_801BB370(Entity* entity) {
    SubweaponDef* subwpn = &subweapons_def[entity->ext.subweapon.subweaponId];

    if (g_Ric.timers[ALU_T_INVINCIBLE] != 0) {
        entity->attack = subwpn->attack * 2;
    } else {
        entity->attack = (u16)subwpn->attack;
    }

    entity->attackElement = subwpn->attackElement;
    entity->hitboxState = subwpn->hitboxState;
    entity->nFramesInvincibility = subwpn->nFramesInvincibility;
    entity->stunFrames = subwpn->stunFrames;
    entity->hitEffect = subwpn->hitEffect;
    entity->entityRoomIndex = subwpn->entityRoomIndex;
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicCheckSubweapon);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BB5BC);

extern Point16 D_us_801D080C[16];
extern s32 func_us_801BB5BC(Primitive*, s16, s16);

// BO6 twin of RicEntityHitByHoly. The boss overlay owns the primitives in
// camera space and uses Richter's hitbox, status, priority, and local points.
void BO6_RicEntityHitByHoly(Entity* entity) {
    Primitive* prim;
    s32 i;
    s32 temp;
    s16 hitboxX;
    s16 hitboxY;
    s16 temp_xRand;
    s16 temp_yRand;

    switch (entity->step) {
    case 0:
        entity->primIndex =
            (s16)g_api.AllocPrimitives(PRIM_GT4, LEN(D_us_801D080C));
        if (entity->primIndex == -1) {
            DestroyEntity(entity);
            return;
        }

        entity->flags = FLAG_HAS_PRIMS | FLAG_POS_CAMERA_LOCKED;
        hitboxX = RIC.posX.i.hi + RIC.hitboxOffX;
        hitboxY = RIC.posY.i.hi + RIC.hitboxOffY;
        prim = &g_PrimBuf[entity->primIndex];
        for (i = 0; i < LEN(D_us_801D080C); i++) {
            temp_xRand = hitboxX + rand() % 24 - 12;
            temp_yRand = hitboxY + rand() % 48 - 24;
            D_us_801D080C[i].x = temp_xRand;
            D_us_801D080C[i].y = temp_yRand;
            prim->clut = PAL_UNK_1B2;
            prim->tpage = 0x1A;
            prim->b0 = 0;
            prim->b1 = 0;
            prim->g0 = 0;
            prim->g1 = (rand() & 7) + 1;
            prim->g2 = 0;
            prim->priority = RIC.zPriority + 4;
            prim->drawMode = DRAW_UNK_100 | DRAW_TPAGE | DRAW_HIDE |
                             DRAW_UNK02 | DRAW_TRANSP;
            if (rand() & 1) {
                prim->drawMode =
                    DRAW_UNK_100 | DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                    DRAW_HIDE | DRAW_UNK02 | DRAW_TRANSP;
            }
            prim = prim->next;
        }
        entity->step++;
        break;

    case 1:
        if (!(g_Ric.status & PLAYER_STATUS_UNK10000)) {
            DestroyEntity(entity);
            return;
        }
        break;
    }

    prim = &g_PrimBuf[entity->primIndex];
    for (i = 0; i < LEN(D_us_801D080C); i++) {
        switch (prim->g0) {
        case 0:
            if (--prim->g1 == 0) {
                prim->g0++;
            }
            break;

        case 1:
            hitboxX = D_us_801D080C[i].x;
            hitboxY = D_us_801D080C[i].y;
            temp = func_us_801BB5BC(prim, hitboxX, hitboxY);
            D_us_801D080C[i].y--;
            if (temp < 0) {
                prim->drawMode |= DRAW_HIDE;
                prim->g0++;
            } else {
                prim->drawMode &= ~DRAW_HIDE;
            }
            break;
        }
        prim = prim->next;
    }
}

extern s32 D_us_801D084C;
extern AnimationFrame D_us_80181554[];

// BO6 twin of RicEntityHitByDark. This overlay uses the camera-locked effect
// flags, Richter's local z priority, animation data, and alternating counter.
void BO6_RicEntityHitByDark(Entity* entity) {
    switch (entity->step) {
    case 0:
        entity->flags = FLAG_UNK_20000000 | FLAG_POS_CAMERA_LOCKED;
        entity->unk5A = 0x79;
        entity->animSet = ANIMSET_DRA(14);
        entity->zPriority = RIC.zPriority + 2;
        entity->palette = PAL_FLAG(PAL_UNK_19F);
        if (D_us_801D084C & 1) {
            entity->blendMode = BLEND_TRANSP | BLEND_QUARTER;
        } else {
            entity->blendMode = BLEND_TRANSP;
        }
        D_us_801D084C++;
        entity->opacity = 0xFF;
        entity->drawFlags =
            ENTITY_SCALEX | ENTITY_SCALEY | ENTITY_MASK_R | ENTITY_MASK_G;
        entity->scaleX = entity->scaleY = 0x40;
        entity->anim = D_us_80181554;
        entity->posY.i.hi += (rand() % 35) - 15;
        entity->posX.i.hi += (rand() % 20) - 10;
        entity->velocityY = -0x6000 - (rand() & 0x3FFF);
        entity->step++;
        break;

    case 1:
        if (entity->opacity > 16) {
            entity->opacity -= 8;
        }
        entity->posY.val += entity->velocityY;
        entity->scaleX += 8;
        entity->scaleY += 8;
        if (entity->poseTimer < 0) {
            DestroyEntity(entity);
        }
        break;
    }
}

// Empty stub
void func_us_801BBBC0(void) {}

// Empty stub
void func_us_801BBBC8(void) {}

extern PfnEntityUpdate D_us_8018158C[];
// ARRAY, not a scalar. g_api.UpdateAnim's second parameter is
// AnimationFrame**, so this has to decay to its own address. Whatever
// declaration was in scope before made `D_us_801812B8` evaluate to 0, and the
// build passed a zero in $a1 where the original loads %hi/%lo of 0x801812B8 --
// one dropped instruction, and every branch target after it off by one.
extern AnimationFrame* D_us_801812B8[];
extern u8 D_us_801D0800;
extern u8 D_us_801D0804;
extern u8 D_us_801D0808;
extern u8 D_us_801D07FC;

// HARVESTED from upstream/master src/boss/bo6/us_39144.c, verbatim.
// No renames: it drives the entity table directly and calls nothing Ric*.
void func_us_801BBBD0(void) {
    Entity* entity;
    PfnEntityUpdate entityUpdate;
    s32 i;

    entity = g_CurrentEntity = &g_Entities[E_ID_44];

    for (i = E_ID_44; i < E_ID_90; i++, g_CurrentEntity++, entity++) {
        if (entity->entityId) {
            entityUpdate = D_us_8018158C[entity->entityId];
            entityUpdate(entity);
            entity = g_CurrentEntity;

            if (entity->entityId) {
                if (!(entity->flags & FLAG_UNK_10000000) &&
                    (entity->posX.i.hi > 288 || entity->posX.i.hi < -32 ||
                     entity->posY.i.hi > 256 || entity->posY.i.hi < -16)) {
                    DestroyEntity(entity);
                } else {
                    if (entity->flags & FLAG_UNK_20000000) {
                        g_api.UpdateAnim(NULL, D_us_801812B8);
                    }
                    entity->flags |= FLAG_NOT_AN_ENEMY;
                }
            }
        }
    }

    if (D_us_801D07FC) {
        D_us_801D07FC--;
        if (D_us_801D07FC & 1) {
            g_api.func_800EA5AC(1, D_us_801D0800, D_us_801D0804, D_us_801D0808);
        }
    }
    if ((RIC.step == 0x11) || (RIC.step == 0x60) || (RIC.step == 0x70)) {
        FntPrint("dead boss\n");
        entity = &g_Entities[E_ID_44];
        for (i = E_ID_44; i < E_ID_90; i++, entity++) {
            entity->hitboxState = 0;
        };
    }
}

// Richter (BO6): spawn a factory entity that will build whatever the blueprint
// in factoryParams names, seeded from `source`'s position, facing and depth.
//
// RIC's twin is RicCreateEntFactoryFromEntity in src/ric/pl_blueprints.c. Two
// real differences, both visible in the assembly rather than assumed:
//   - the free-slot window is 0x44..0x50 here, not 8..16. Those are stage
//     entity slots 4..16, hence the STAGE_ENTITY_START arithmetic.
//   - RIC's trailing `if (source->flags & FLAG_UNK_10000)` block is absent.
//     BO6 does not propagate that flag; the assembly ends at the zPriority
//     store, so adding the block would be inventing behaviour.
//
// arg2 is genuinely unused. It is kept because the callers pass three
// arguments and because RIC's signature has it, but nothing reads $a2.
Entity* BO6_RicCreateEntFactoryFromEntity(
    Entity* source, u32 factoryParams, s32 arg2) {
    Entity* entity =
        BO6_RicGetFreeEntity(STAGE_ENTITY_START + 4, STAGE_ENTITY_START + 16);
    if (!entity) {
        return NULL;
    }
    DestroyEntity(entity);
    entity->entityId = E_FACTORY;
    entity->ext.factory.parent = source;
    entity->posX.val = source->posX.val;
    entity->posY.val = source->posY.val;
    entity->facingLeft = source->facingLeft;
    entity->zPriority = source->zPriority;
    entity->params = factoryParams & 0xFFF;
    entity->ext.factory.paramsBase = (factoryParams & 0xFF0000) >> 8;
    return entity;
}

extern FactoryBlueprint D_us_801816A0[];
extern u8 D_us_80181868[8][2];

enum BO6_BlueprintKind {
    BO6_B_DECORATION = 0,
    BO6_B_WHIP = 4,
    BO6_B_CUTSCENE_MARIA = 5,
};

enum BO6_BlueprintOrigin {
    BO6_B_ORIGIN_DEFAULT = 0,
    BO6_B_ORIGIN_FOLLOW_CAMERA = 1,
    BO6_B_ORIGIN_FOLLOW_PLAYER = 2,
    BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_HIT = 3,
    BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_RUNNING = 4,
    BO6_B_ORIGIN_UNUSED_5 = 5,
    BO6_B_ORIGIN_UNUSED_6 = 6,
    BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_NOT_HIT = 7,
    BO6_B_ORIGIN_FOLLOW_PARENT = 8,
    BO6_B_ORIGIN_CRASH_PARTICLE = 9,
};

// Richter (BO6): decode a six-byte factory blueprint, track its requested
// origin, and create the requested children in the BO6 entity ranges. This is
// the RicEntityFactory twin from src/ric/pl_blueprints.c, adapted to the boss
// overlay's local blueprint and range tables.
//
// Two absent operations matter. BO6 does not propagate FLAG_UNK_10000 to a
// child, and its running-origin setup does not set FLAG_UNK_20000. The latter
// still performs a load/store of flags in the target. `flags |= 0` preserves
// that instruction pair and the original fallthrough shape.
void BO6_RicEntityFactory(Entity* self) {
    Entity* newEntity;
    s16 nPerCycle;
    s16 i;
    s16 startIndex;
    s16 endIndex;
    u8* data;

    if (self->step == 0) {
        data = (u8*)&D_us_801816A0[self->params];
        self->ext.factory.newEntityId = *data++;
        self->ext.factory.amount = *data++;
        self->ext.factory.nPerCycle = *data & 0x3F;
        self->ext.factory.isNonCritical = (s16)(*data >> 7) & 1;
        self->ext.factory.incParamsKind = (s16)(*data++ >> 6) & 1;
        self->ext.factory.tCycle = *data++;
        self->ext.factory.kind = *data & 0x7;
        self->ext.factory.origin = (s16)(*data++ >> 3) & 0x1F;
        self->ext.factory.delay = *data;
        self->flags |= FLAG_UNK_10000000;
        self->step++;

        switch (self->ext.factory.origin) {
        case BO6_B_ORIGIN_DEFAULT:
            self->flags |= FLAG_POS_CAMERA_LOCKED;
            break;

        case BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_RUNNING:
            self->flags |= 0;
        case BO6_B_ORIGIN_FOLLOW_PLAYER:
        case BO6_B_ORIGIN_CRASH_PARTICLE:
            self->flags |= FLAG_POS_CAMERA_LOCKED;
        case BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_HIT:
        case BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_NOT_HIT:
            self->posX.val = RIC.posX.val;
            self->posY.val = RIC.posY.val;
            break;

        case BO6_B_ORIGIN_FOLLOW_PARENT:
            if (self->ext.factory.parent != NULL) {
                self->posX.val = self->ext.factory.parent->posX.val;
                self->posY.val = self->ext.factory.parent->posY.val;
            }
            self->flags |= FLAG_POS_CAMERA_LOCKED;
            break;
        }
    } else {
        switch (self->ext.factory.origin) {
        case BO6_B_ORIGIN_DEFAULT:
        case BO6_B_ORIGIN_FOLLOW_CAMERA:
        case BO6_B_ORIGIN_UNUSED_5:
        case BO6_B_ORIGIN_UNUSED_6:
            break;

        case BO6_B_ORIGIN_CRASH_PARTICLE:
            if (g_Ric.unk4E) {
                DestroyEntity(self);
                return;
            }
        case BO6_B_ORIGIN_FOLLOW_PLAYER:
            self->posX.val = RIC.posX.val;
            self->posY.val = RIC.posY.val;
            break;

        case BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_RUNNING:
            self->posX.val = RIC.posX.val;
            self->posY.val = RIC.posY.val;
            if (RIC.step != PL_S_RUN) {
                self->entityId = 0;
                return;
            }
            break;

        case BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_HIT:
            self->posX.val = RIC.posX.val;
            self->posY.val = RIC.posY.val;
            if (RIC.step == PL_S_HIT) {
                self->entityId = 0;
                return;
            }
            break;

        case BO6_B_ORIGIN_FOLLOW_PLAYER_WHILE_NOT_HIT:
            self->posX.val = RIC.posX.val;
            self->posY.val = RIC.posY.val;
            if (RIC.step != PL_S_HIT) {
                self->entityId = 0;
                return;
            }
            break;

        case BO6_B_ORIGIN_FOLLOW_PARENT:
            if (self->ext.factory.parent != NULL) {
                self->posX.val = self->ext.factory.parent->posX.val;
                self->posY.val = self->ext.factory.parent->posY.val;
            }
            break;
        }
    }

    if (self->ext.factory.delay) {
        if (--self->ext.factory.delay) {
            return;
        }
        self->ext.factory.delay = self->ext.factory.tCycle;
    }

    nPerCycle = self->ext.factory.nPerCycle;
    for (i = 0; i < nPerCycle; i++) {
        data = D_us_80181868[0];
        data += self->ext.factory.kind * 2;
        startIndex = *data++;
        endIndex = *data;

        if (self->ext.factory.kind == BO6_B_DECORATION) {
            newEntity =
                BO6_RicGetFreeEntityReverse(startIndex, endIndex + 1);
        } else if (self->ext.factory.kind == BO6_B_WHIP) {
            newEntity = &g_Entities[STAGE_ENTITY_START + 31];
        } else if (self->ext.factory.kind == BO6_B_CUTSCENE_MARIA) {
            newEntity = &g_Entities[STAGE_ENTITY_START + 48];
        } else {
            newEntity = BO6_RicGetFreeEntity(startIndex, endIndex + 1);
        }

        if (newEntity == NULL) {
            if (self->ext.factory.isNonCritical == 1) {
                self->entityId = 0;
            } else {
                self->ext.factory.delay = self->ext.factory.tCycle;
            }
            return;
        }

        DestroyEntity(newEntity);
        newEntity->entityId =
            self->ext.factory.newEntityId + self->ext.factory.entityIdMod;
        newEntity->params = self->ext.factory.paramsBase;
        newEntity->ext.factory.parent = self->ext.factory.parent;
        newEntity->posX.val = self->posX.val;
        newEntity->posY.val = self->posY.val;
        newEntity->facingLeft = self->facingLeft;
        newEntity->zPriority = self->zPriority;

        if (self->ext.factory.incParamsKind) {
            newEntity->params += self->ext.factory.spawnIndex;
        } else {
            newEntity->params += i;
        }
        self->ext.factory.spawnIndex++;
        if (self->ext.factory.spawnIndex == self->ext.factory.amount) {
            self->entityId = 0;
            return;
        }
    }
    self->ext.factory.delay = self->ext.factory.tCycle;
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC2F0);

extern s16 RIC_posX_i_hi;    /* 0x800762DA, symbols.us.bobo6.txt */
extern s16 RIC_posY_i_hi;    /* 0x800762DE */
extern u16 RIC_facingLeft;   /* 0x800762EC */
extern s16 RIC_animCurFrame; /* 0x8007632E */
extern EInit D_us_80180448;  /* src/boss/bo6/e_init.c:53 */

// Richter (BO6): the hitbox entity that tracks RIC during the flame-step
// swing. It mirrors RIC's position and facing every frame, and mirrors its own
// hit result back into g_Ric + 0x394 (PlayerState.unk44, game.h:1976) so the
// player state machine sees the hit.
//
// Flat RIC_* externs rather than RIC.<field>, per the rule recorded at
// src/boss/bo6/richter.c:133: each access here emits its own lui/%lo pair, so
// these are scalar externs, not members reached from a hoisted base.
//
// THE SHAPE HERE IS LOAD-BEARING. Two things look like noise and are not.
// Both were tested by removing them, and both removals break the match:
//
//   - `new_var` aliases `entity` for a subset of the stores. GCC 2.7 keeps the
//     alias in a second register; writing `entity` throughout re-loads it.
//   - `new_var2` reads entity->step BETWEEN the posX and posY stores. Moving
//     that read anywhere else, including one line up, changes the schedule.
//
// Measured: removing the aliasing and hoisting the step read to the top scores
// 780 against this function's target. Hoisting only the step read and keeping
// everything else scores in the 400s. Do not tidy this without re-checking:
//     python3 automation/permuter_promote.py --dir nonmatchings/func_us_801BC3E0
//
// The permuter's own 0-scoring output ALSO carried a `volatile int pad`, and
// that one is not kept here. It made the frame 0x20 where the target is 0x18.
// The permuter compiles this function alone and scored it 0 regardless, so its
// zero is necessary but not sufficient: the frame only revealed itself in a
// real overlay build. Every body instruction was already identical at that
// point, so asm_diff pointed straight at the eight bytes. Trust the build, not
// the permuter, for anything touching the frame.
void func_us_801BC3E0(Entity* entity) {
    u16 step;
    u16 new_var2;
    Entity* new_var;

    if (RIC_step != 0x1B) {
        DestroyEntity(entity);
        return;
    }
    entity->posX.i.hi = RIC_posX_i_hi;
    new_var2 = entity->step;
    // CODEGEN: This single-iteration wrapper is load-bearing. The isolated
    // exact body scores 0; replacing only the wrapper with a straight store
    // scores 405: 9 register differences, 1 reordering, 1 insertion, and
    // 2 deletions.
    do {
        entity->posY.i.hi = RIC_posY_i_hi;
    } while (0);
    step = new_var2;
    entity->facingLeft = RIC_facingLeft;
    new_var = entity;
    if (step == 0) {
        InitializeEntity(&D_us_80180448);
        new_var->flags = 0x18000000;
        entity->hitboxOffX = 0x14;
        entity->hitboxHeight = 9;
        new_var->hitboxWidth = 9;
        new_var->step = 1;
    }
    if (RIC_animCurFrame == 0x8C) {
        entity->hitboxOffY = 0;
    }
    if (RIC_animCurFrame == 0x8D) {
        entity->hitboxOffY = 0xC;
    }
    if (new_var->hitFlags != 0) {
        u16* ric_flag = (u16*)(((char*)(&g_Ric)) + 0x394);
        *ric_flag |= 0x80;
    } else {
        u16* ric_flag = (u16*)(((char*)(&g_Ric)) + 0x394);
        *ric_flag &= 0xFF7F;
    }
    entity->hitFlags = 0;
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC4F8);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC5C8);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BC678);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityHitByCutBlood);

extern AnimationFrame D_us_801818A8[];
extern AnimationFrame D_us_801819D0[];
extern AnimationFrame D_us_80181A0C[];

// HARVESTED from upstream/master src/boss/bo6/us_39144.c.
// One rename: RicCreateEntFactoryFromEntity -> BO6_RicCreateEntFactoryFromEntity.
// The three anim tables are declared as ARRAYS, which is the shape upstream
// uses and the shape the body needs -- see the note on D_us_801812B8 above.
void func_us_801BD0B8(Entity* self) {
    s16 paramsLo = self->params & 0xFF;
    s16 paramsHi = (self->params >> 8) & 0xFF;

    switch (self->step) {
    case 0:
        if (paramsHi == 1) {
            self->scaleX = 0xC0;
            self->scaleY = 0xC0;
            self->drawFlags = ENTITY_SCALEX | ENTITY_SCALEY;
            self->animSet = ANIMSET_DRA(2);
            self->anim = D_us_80181A0C;
        }

        if ((paramsHi == 0) || (paramsHi == 2)) {
            if (paramsLo & 3) {
                self->anim = D_us_801819D0;
                self->scaleX = 0x120;
                self->scaleY = 0x120;
                self->drawFlags = ENTITY_SCALEX | ENTITY_SCALEY;
                self->animSet = ANIMSET_DRA(2);
            } else {
                self->animSet = ANIMSET_DRA(5);
                self->anim = D_us_801818A8;
                self->palette = PAL_FLAG(0x170);
            }
        }
        self->flags = FLAG_UNK_20000000 | FLAG_POS_CAMERA_LOCKED;

        if (rand() & 3) {
            self->zPriority = RIC.zPriority + 2;
        } else {
            self->zPriority = RIC.zPriority - 2;
        }

        if (paramsHi == 2) {
            self->posX.i.hi = RIC.posX.i.hi + (rand() % 44) - 22;
        } else {
            self->posX.i.hi = RIC.posX.i.hi + (rand() & 15) - 8;
        }

        self->posY.i.hi = RIC.posY.i.hi + RIC.hitboxOffY + (rand() & 31) - 16;
        self->velocityY = FIX(-0.5);
        self->velocityX = RIC.velocityX >> 2;
        self->step++;
        break;

    case 1:
        self->scaleX -= 4;
        self->scaleY -= 4;
        self->posY.val += self->velocityY;
        self->posX.val += self->velocityX;
        if ((self->pose == 8) && (self->anim != D_us_801818A8)) {
            self->blendMode = BLEND_TRANSP;
            if (!(paramsLo & 1) && (self->poseTimer == 1)) {
                BO6_RicCreateEntFactoryFromEntity(self, FACTORY(4, 4), 0);
            }
        }

        if ((self->pose == 16) && (self->anim == D_us_801818A8)) {
            self->blendMode = BLEND_TRANSP;
        }

        if (self->poseTimer < 0) {
            DestroyEntity(self);
        }
        break;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BD384);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BD47C);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityPlayerBlinkWhite);
