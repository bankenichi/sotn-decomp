// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo6.h"

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9144);

// Empty stub
void func_us_801B9338(void) {}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9340);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B94CC);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B96F4);

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

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_DisableAfterImage);

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

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicSetCrouch);

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
extern void BO6_RicCreateEntFactoryFromEntity(Entity*, u32, s32);

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
void func_us_801B9DE4(void) {
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

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9E70);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicSetFall);

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

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicDoSubweapon);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicDoAttack);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicDoCrash);

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

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BB314);

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

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityHitByHoly);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityHitByDark);

// Empty stub
void func_us_801BBBC0(void) {}

// Empty stub
void func_us_801BBBC8(void) {}

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BBBD0);

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

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityFactory);

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

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BD0B8);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BD384);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BD47C);

INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", BO6_RicEntityPlayerBlinkWhite);
