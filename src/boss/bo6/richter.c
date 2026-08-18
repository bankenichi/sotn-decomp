// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo6.h"

extern AnimationFrame D_us_80182008[];
extern s32 D_us_801D11C8[];
extern s32 D_us_801D1248[];

// HARVESTED from upstream/master src/boss/bo6/richter.c.
// One rename: RicSetStand -> BO6_RicSetStand.
//
// The g_Ric clear is a hand-rolled word loop rather than memset, and that is
// upstream's shape, not an oversight: the original emits the loop inline.
void func_us_801B4BD0(void) {
    s32 i;
    Entity* var_s1;
    Entity* e;
    PlayerState* var_a0;
    Primitive* prim;
    s32* memset_ptr;
    s32 memset_len;
    s16 temp_v0;
    s16 primIndex;
    s32 radius;
    s32 intensity;
    s32 temp_v1;
    s32 var_s2;
    s32 var_s2_2;
    s32 var_s2_3;
    s32* var_s0;
    s32* var_s3;

    RIC.animSet = ANIMSET_OVL(1);
    RIC.zPriority = g_unkGraphicsStruct.g_zEntityCenter + 8;
    RIC.flags = FLAG_UNK_10000000 | FLAG_POS_CAMERA_LOCKED |
                FLAG_SUPPRESS_STUN | FLAG_UNK_2000;
    RIC.facingLeft = 0;
    RIC.unk5A = 8;
    RIC.palette = 0x8220;
    RIC.scaleX = RIC.scaleY = 0x100;
    RIC.rotPivotY = 0x18;
    RIC.blendMode = BLEND_NO;

    g_PlayerDraw[8].r0 = g_PlayerDraw[8].r1 = g_PlayerDraw[8].r2 =
        g_PlayerDraw[8].r3 = g_PlayerDraw[8].g0 = g_PlayerDraw[8].g1 =
            g_PlayerDraw[8].g2 = g_PlayerDraw[8].g3 = g_PlayerDraw[8].b0 =
                g_PlayerDraw[8].b1 = g_PlayerDraw[8].b2 = g_PlayerDraw[8].b3 =
                    0x80;

    g_PlayerDraw[8].enableColorBlend = 0;

    memset_len = sizeof(PlayerState) / sizeof(s32);
    memset_ptr = (s32*)&g_Ric;
    for (i = 0; i < memset_len; i++) {
        *memset_ptr++ = 0;
    }

    g_Ric.vram_flag = g_Ric.unk04 = 1;

    BO6_RicSetStand(0);
    RIC.anim = D_us_80182008;

    for (i = 0; i < 32; i++) {
        radius = (rand() & 0x3FF) + FLT(1.0 / 16.0);
        intensity = (rand() & 0xFF) + FLT(1.0 / 16.0);
        D_us_801D11C8[i] = ((rcos(radius) << 4) * intensity) >> 8;
        D_us_801D1248[i] = -(((rsin(radius) << 4) * intensity) >> 7);
    }

    for (e = &g_Entities[STAGE_ENTITY_START + 1], i = 0; i < 3; i++, e++) {
        DestroyEntity(e);
        e->animSet = ANIMSET_OVL(1);
        e->unk5A = i + 9;
        e->palette = PAL_FLAG(0x220);
        e->flags = FLAG_POS_CAMERA_LOCKED;
    }

    primIndex = g_api.AllocPrimitives(PRIM_TILE, 6);
    prim = &g_PrimBuf[primIndex];
    g_Entities[65].primIndex = primIndex;
    g_Entities[65].flags |= FLAG_HAS_PRIMS;
    while (prim != NULL) {
        prim->drawMode = DRAW_UNK_100 | DRAW_HIDE | DRAW_UNK02;
        prim = prim->next;
    }
    g_api.TimeAttackController(
        TIMEATTACK_EVENT_SAVE_RICHTER, TIMEATTACK_SET_VISITED);
}

// HARVESTED from upstream/master src/boss/bo6/richter.c, verbatim.
// No renames: it calls nothing. The four hard bounds are the arena's extent
// during the Richter fight, which is why this overlay clamps position itself
// instead of going through the ordinary collision path.
void func_us_801B4EAC(void) {
    g_Ric.unk04 = g_Ric.vram_flag;
    g_Ric.vram_flag = 0;
    RIC.posY.val += RIC.velocityY;
    RIC.posX.val += RIC.velocityX;

    if (RIC.posY.val >= 0xB30000) {
        RIC.posY.val = 0xB30000;
        g_Ric.vram_flag |= TOUCHING_GROUND;
    }
    if (RIC.posY.val <= 0x280000) {
        RIC.posY.val = 0x280000;
        g_Ric.vram_flag |= TOUCHING_CEILING;
    }
    if (RIC.posX.val >= 0xF80000) {
        RIC.posX.val = 0xF80000;
        g_Ric.vram_flag |= TOUCHING_R_WALL;
    }
    if (RIC.posX.val <= 0x80000) {
        RIC.posX.val = 0x80000;
        g_Ric.vram_flag |= TOUCHING_L_WALL;
    }
}

static void BO6_CheckBladeDashInput() {
    u16 step = RIC.step;

    if ((step == 1 || step == 2 || RIC.step == 3 || step == 4 || step == 5) &&
        (g_Ric.unk46 == 0) && (g_Ric.padTapped & 8)) {
        func_us_801BA9D0();
    }
}

// BO6_CheckHighJumpInput's two RIC_ scalars must be declared BEFORE this
// point. RIC_velocityY is declared further down at its other use site, which is
// after this function, so it is repeated here rather than moved: moving it
// would reorder declarations that other functions already depend on.
//
// Both are FLAT externs, not RIC.step / RIC.velocityY, and the assembly says
// so: BO6_CheckHighJumpInput.s builds its own lui/%lo pair for each
// (`lui $a0, %hi(RIC_step)` / `lhu $a0, %lo(RIC_step)($a0)`), which is the
// signature this file already documents at the RicStepStandInAir comment as
// marking a plain scalar global rather than a struct member. lhu is a 16-bit
// unsigned load, hence u16.
extern u16 RIC_step;
extern s32 RIC_velocityY;

/* BO6: when the player is in a step that allows a high jump (steps 1/3/4, or
   step 5 while falling faster than 1.0 px/frame) and the jump button was just
   tapped, hand off to func_us_801BA050 to perform the high jump. */
// Takes NO argument. The jal's delay slot is a bare nop and nothing
// sets up $a0; the register merely still holds RIC_step from the test
// at the top of the function. Declaring a parameter and passing
// RIC_step made GCC re-emit the lui/lhu pair to load it, which is
// exactly the 8 bytes (2 instructions) the overlay came out long by.
extern void func_us_801BA050(void);

void BO6_CheckHighJumpInput(void) {
    /* Step gates: 3, 1, 4 always qualify; step 5 only qualifies when falling
       fast (0x10000 = 1.0 in fixed point, so > 1.0 px/frame downward). */
    if (RIC_step == 3 || RIC_step == 1 ||
        (RIC_step == 5 && RIC_velocityY > 0x10000) ||
        RIC_step == 4)
    {
        /* unk46: a lock flag that must be clear so the jump cannot re-fire;
           padTapped bit 1 (0x2) is the jump-button tap. */
        if (g_Ric.unk46 == 0 && (g_Ric.padTapped & 2)) {
            func_us_801BA050();
        }
    }
}


INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicMain);

extern s32 D_us_801CF3C8;
extern s32 D_us_801CF3CC;

void func_us_801B5A14(s32 arg0) {
    D_us_801CF3C8 = arg0;
    D_us_801CF3CC = 0;
}

extern s32 D_us_80181278;
extern s32 D_us_801CF3D0;
extern s32 D_us_801CF3D8;
extern s32 D_us_801CF3E0;
extern s32 D_us_801CF3E4;
extern s32 g_CutsceneFlags;
extern s32 D_us_801D169C;

typedef enum { THINK_STEP_INIT } ThinkStep;

// HARVESTED from upstream/master src/boss/bo6/richter.c.
//
// The boss AI: it drives Richter by SYNTHESISING PAD INPUT into g_Ric.padSim
// rather than by setting steps directly, which is why the same step machine
// serves both the player and the boss. D_us_801CF3C8 is the think step and
// D_us_801CF3CC its sub-step; func_us_801B5A14 sets the pair.
//
// The case labels jump (0-19, then 30-32, 40-41, 50). Those gaps are
// upstream's and are real: the 30s are the item-crash sequence, the 40s the
// death cutscene, and 50 the post-death hold. Nothing writes the values in
// between.
//
// Renames to this fork's BO6_ exports, both confirmed against
// config/symbols.us.bobo6.txt:
//     RicSetInvincibilityFrames     -> BO6_RicSetInvincibilityFrames
//     RicCreateEntFactoryFromEntity -> BO6_RicCreateEntFactoryFromEntity
void RichterThinking(void) {
    s32 globalPosX;
    s32 playerDistanceX;
    bool facingLeft;

    if (D_us_801CF3D8) {
        D_us_801CF3D8--;
    }

    globalPosX = g_Tilemap.scrollX.i.hi + RIC.posX.i.hi;
    g_Ric.demo_timer = 2;
    g_Ric.padSim = 0;

    facingLeft = false;
    if ((RIC.posX.i.hi - PLAYER.posX.i.hi) >= 0) {
        facingLeft = true;
    }

    playerDistanceX = abs(RIC.posX.i.hi - PLAYER.posX.i.hi);

    if (D_us_801CF3E4 < g_Ric.unk6C && D_us_801CF3E4 >= g_Ric.unk6A) {
        D_us_801CF3C8 = 0x1E;
    }

    if (D_us_801D169C != 0) {
        func_us_801B5A14(0x28);
    }

    if (g_Player.status & PLAYER_STATUS_DEAD) {
        D_us_801CF3C8 = 0x32;
    }

    if (D_us_801CF3C8 < 0x12) {
        if (g_Ric.status & PLAYER_STATUS_UNK10000) {
            func_us_801B5A14(0);
        } else if (g_Player.timers[ALU_T_USE_SPELL] && D_us_801CF3C8 != 0xE) {
            func_us_801B5A14(0xE);
        }
    }

    FntPrint("think_step:%02x\n", D_us_801CF3C8);

    switch (D_us_801CF3C8) { /* switch 1 */
    // following item crash at start of fight
    case THINK_STEP_INIT: /* switch 1 */
        if (!(g_Ric.status & PLAYER_STATUS_UNK10000)) {
            if (g_Player.timers[ALU_T_USE_SUBWPN]) {
                if (rand() & 1) {
                    func_us_801B5A14(7);
                } else {
                    func_us_801B5A14(5);
                }
            } else if (abs(RIC.posY.i.hi - PLAYER.posY.i.hi) > 0x20) {
                func_us_801B5A14(7);
            } else {
                if (playerDistanceX > 0x58) {
                    if (facingLeft) {
                        g_Ric.padSim = 0x8000;
                    } else {
                        g_Ric.padSim = 0x2000;
                    }
                } else {
                    func_us_801B5A14(1);
                }
            }
        }
        break;
    // decicing on attack?
    case 1: /* switch 1 */
        if (RIC.facingLeft != facingLeft) {
            if (facingLeft) {
                g_Ric.padSim = 0x8000;
            } else {
                g_Ric.padSim = 0x2000;
            }
        }

        if (D_us_801CF3CC == 0) {
            D_us_801CF3D0 = 8;
            D_us_801CF3CC = 1;
            return;
        }

        if (playerDistanceX > 0x58) {
            func_us_801B5A14(0);
        } else {
            if (((globalPosX < 0x10) && (RIC.facingLeft == 0)) ||
                ((globalPosX > 0xF0) && (RIC.facingLeft))) {
                func_us_801B5A14(4);
                if (D_us_801CF3E0 != 0) {
                    func_us_801B5A14(0xD);
                    return;
                }
            } else if (g_Player.status & PLAYER_STATUS_CROUCH) {
                if (rand() & 1) {
                    func_us_801B5A14(6);
                } else {
                    func_us_801B5A14(5);
                }
            } else {
                if (g_Player.timers[ALU_T_9]) {
                    switch (rand() & 7) { /* switch 2 */
                    case 0:               /* switch 2 */
                    case 6:               /* switch 2 */
                        func_us_801B5A14(6);
                        break;
                    case 7: /* switch 2 */
                        func_us_801B5A14(7);
                        break;
                    case 1: /* switch 2 */
                        func_us_801B5A14(5);
                        break;
                    case 2: /* switch 2 */
                    case 3: /* switch 2 */
                    case 4: /* switch 2 */
                    case 5: /* switch 2 */
                    default:
                        func_us_801B5A14(2);
                        break;
                    }
                } else {
                    if (g_Player.timers[ALU_T_USE_SUBWPN]) {
                        if (rand() & 1) {
                            func_us_801B5A14(7);
                        } else {
                            func_us_801B5A14(5);
                        }
                    } else if (D_us_801CF3D0) {
                        D_us_801CF3D0--;
                    } else if (playerDistanceX < 0x40) {
                        if ((RIC.posY.i.hi - PLAYER.posY.i.hi) < 0x18) {
                            func_us_801B5A14(3);
                        } else {
                            func_us_801B5A14(8);
                        }
                    } else {
                        func_us_801B5A14(8);
                    }
                }
            }
        }
        break;
    case 2:                      /* switch 1 */
        switch (D_us_801CF3CC) { /* switch 3; irregular */
        case 0:                  /* switch 3 */
            if (RIC.step == 5) {
                D_us_801CF3CC = 1;
            } else if (g_Timer & 1) {
                g_Ric.padSim = 0x40;
            }
            break;
        case 1: /* switch 3 */
            if (g_Ric.unk44 & 8) {
                D_us_801CF3CC = 2;
            } else {
                if (g_Timer & 1) {
                    g_Ric.padSim = 0x40;
                }
                if (g_Ric.vram_flag & TOUCHING_GROUND) {
                    func_us_801B5A14(0);
                }
            }
            break;
        case 2:
        default: /* switch 3 */
            if (D_us_801CF3E0 == 0) {
                func_us_801B5A14(9);
            }
            if (g_Ric.vram_flag & TOUCHING_GROUND) {
                if (D_us_801CF3E0 != 0) {
                    func_us_801B5A14(0xC);
                } else {
                    func_us_801B5A14(0);
                }
            }
            break;
        }
        break;
    // whip attack
    case 3: /* switch 1 */
        if (D_us_801CF3CC == 0) {
            if (!g_Ric.unk46) {
                if (g_Timer & 1) {
                    g_Ric.padSim = 0x80;
                }
                D_us_801CF3CC = 1;
            }
        } else {
            if (!g_Ric.unk46) {
                func_us_801B5A14(0);
            }
        }
        break;
    // dash
    case 4: /* switch 1 */
        if (D_us_801CF3CC == 0) {
            if (g_Timer & 1) {
                g_Ric.padSim = PAD_R1;
            }
            if (RIC.step == 0x19) {
                D_us_801CF3C8 = 1;
            }
        } else if (RIC.step != 0x19) {
            func_us_801B5A14(0);
        }
        break;
    case 5: /* switch 1 */
        g_Ric.padSim = 0x4000;
        switch (D_us_801CF3CC) {
        case 0:
            if (RIC.facingLeft != facingLeft) {
                if (facingLeft) {
                    g_Ric.padSim |= 0x8000;
                } else {
                    g_Ric.padSim |= 0x2000;
                }
            }
            if (RIC.step == 3) {
                D_us_801CF3CC = 1;
                D_us_801CF3D0 = 8;
            }
            break;
        case 1:
        default:
            if (!--D_us_801CF3D0) {
                func_us_801B5A14(17);
            } else if (playerDistanceX < 0x40) {
                func_us_801B5A14(10);
            }
            break;
        }
        break;
    case 6: /* switch 1 */
        if (D_us_801CF3CC == 0) {
            if (RIC.step == 5) {
                D_us_801CF3CC = 1;
            } else if (g_Timer & 1) {
                g_Ric.padSim = 0x40;
            }
        } else if (g_Ric.vram_flag & TOUCHING_GROUND) {
            func_us_801B5A14(0);
        } else if (RIC.velocityY > 0x4000) {
            func_us_801B5A14(9);
        }
        break;
    case 7: /* switch 1 */
        if (RIC.facingLeft) {
            g_Ric.padSim = PAD_LEFT;
        } else {
            g_Ric.padSim = PAD_RIGHT;
        }
        if (D_us_801CF3CC == 0) {
            if (RIC.step == 5) {
                D_us_801CF3CC = 1;
            } else if (g_Timer & 1) {
                g_Ric.padSim |= PAD_CROSS;
            }
        } else if (g_Ric.vram_flag & TOUCHING_GROUND) {
            func_us_801B5A14(0);
        } else if (RIC.velocityY > 0x4000) {
            if (rand() & 1) {
                func_us_801B5A14(0xB);
            } else {
                func_us_801B5A14(9);
            }
        }
        break;
    // subweapon attack?
    case 8: /* switch 1 */
        if (D_us_801CF3CC == 0) {
            if (!g_Ric.unk46) {
                if (g_Timer & 1) {
                    g_Ric.padSim = PAD_UP | PAD_SQUARE;
                }
                D_us_801CF3CC = 1;
            }
        } else if (!g_Ric.unk46) {
            func_us_801B5A14(0);
        }
        break;
    case 9: /* switch 1 */
        if (g_Ric.vram_flag & TOUCHING_GROUND) {
            func_us_801B5A14(0);
        } else if (D_us_801CF3CC == 0) {
            if (!g_Ric.unk46) {
                if (g_Timer & 1) {
                    g_Ric.padSim = PAD_UP | PAD_SQUARE;
                }
                D_us_801CF3CC = 1;
            }
        } else if (!g_Ric.unk46) {
            func_us_801B5A14(0);
        }
        break;
    case 10: /* switch 1 */
        g_Ric.padSim = PAD_DOWN;
        if (D_us_801CF3CC == 0) {
            if (!g_Ric.unk46) {
                if (g_Timer & 1) {
                    g_Ric.padSim |= PAD_SQUARE;
                }
                D_us_801CF3CC = 1;
            }
        } else if (!g_Ric.unk46) {
            func_us_801B5A14(0);
        }
        break;
    case 11: /* switch 1 */
        if (g_Ric.vram_flag & TOUCHING_GROUND) {
            func_us_801B5A14(0);
        } else if (D_us_801CF3CC == 0) {
            if (!g_Ric.unk46) {
                if (g_Timer & 1) {
                    g_Ric.padSim = 0x80;
                }
                D_us_801CF3CC = 1;
            }
        } else if (!g_Ric.unk46) {
            func_us_801B5A14(0);
        }
        break;
    case 12: /* switch 1 */
        if (D_us_801CF3CC == 0) {
            if (RIC.step == 0x1C) {
                D_us_801CF3CC = 1;
            } else if (g_Timer & 1) {
                g_Ric.padSim = 0x110;
            }
        } else if (RIC.step != 0x1C) {
            func_us_801B5A14(0x11);
            return;
        }
        break;
    case 13: /* switch 1 */
        // STEP: cutscene
        if (D_us_801CF3CC == 0) {
            if (RIC.step == 0x1C) {
                D_us_801CF3CC = 1;
            } else if (g_Timer & 1) {
                g_Ric.padSim = 0x810;
            }
        } else if (RIC.step != 0x1C) {
            func_us_801B5A14(0);
        }
        break;

    case 14: /* switch 1 */
        if (D_us_801CF3CC == 0) {
            if (RIC.step == 0x13) {
                D_us_801CF3CC = 1;
            } else if (g_Timer & 1) {
                g_Ric.padSim = 0x14;
            }
        } else if (RIC.step != 0x13) {
            func_us_801B5A14(0);
        }
        break;

    case 15: /* switch 1 */
        if (D_us_801CF3CC == 0) {
            if (RIC.step == 0x15) {
                D_us_801CF3CC = 1;
            } else if (g_Timer & 1) {
                g_Ric.padSim = 0x11;
            }
        } else if (RIC.step != 0x15) {
            func_us_801B5A14(0);
        }
        break;
    case 16: /* switch 1 */
        if (D_us_801CF3CC == 0) {
            if (RIC.step == 0x13) {
                D_us_801CF3CC = 1;
            } else if (g_Timer & 1) {
                g_Ric.padSim = 0x10;
            }
        } else if (RIC.step != 0x13) {
            func_us_801B5A14(0);
        }
        break;
    case 17:                     /* switch 1 */
        switch (D_us_801CF3CC) { /* switch 4; irregular */
        case 0:                  /* switch 4 */
            g_Ric.padSim = 0x4000;
            if (RIC.step == 3) {
                D_us_801CF3CC = 1;
            }
            break;
        case 1: /* switch 4 */
            if (RIC.step == 0x18) {
                D_us_801CF3CC = 4;
                if (D_us_801CF3E0 != 0) {
                    if (RIC.facingLeft && RIC.posX.i.hi > 0x80) {
                        D_us_801CF3CC = 2;
                    }
                    if (!RIC.facingLeft && RIC.posX.i.hi < 0x80) {
                        D_us_801CF3CC = 2;
                    }
                }
            } else {
                g_Ric.padSim = 0x4000;
                if (g_Timer & 1) {
                    g_Ric.padSim |= PAD_CROSS;
                }
            }
            break;
        case 2: /* switch 4 */
            if (RIC.step == 0x1B) {
                D_us_801CF3CC = 3;
            } else {
                g_Ric.padSim = 0x4000;
                if (g_Timer & 1) {
                    g_Ric.padSim |= 0x40;
                }
            }
            break;
        case 3: /* switch 4 */
            g_Ric.padSim = 0x80;
            if (RIC.step != 0x1B) {
                func_us_801B5A14(0);
            }
            // fallthrough

        default:
            func_us_801B5A14(0);
            break;
        }
        break;
    case 18: /* switch 1 */
        BO6_RicSetInvincibilityFrames(1, 4);
        if (RIC.step == 1) {
            func_us_801B5A14(0x13);
        }
        break;

    case 19: /* switch 1 */
        BO6_RicSetInvincibilityFrames(1, 4);
        if (D_us_801CF3CC == 0) {
            D_us_801CF3D0 = 0x40;
            D_us_801CF3CC = 1;
        } else {
            if ((g_CutsceneFlags & 2) || (g_CastleFlags[SHAFT_ORB_DEFEATED]) ||
                (g_DemoMode != Demo_None)) {
                if (!--D_us_801CF3D0) {
                    BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x48, 0);
                    func_us_801B5A14(0x10);
                }
            }
        }
        break;
    case 30: /* switch 1 */
        g_Player.timers[ALU_T_INVINCIBLE_CONSUMABLES] = 3;
        BO6_RicSetInvincibilityFrames(1, 8);
        g_Ric.padSim = 0x1000;
        if (RIC.step == 1 && RIC.step_s == 1) {
            RIC.step = 0x50;
            RIC.step_s = 0;
            D_us_801CF3C8 = 0x1F;
        }
        break;
    case 31: /* switch 1 */
        g_Player.timers[ALU_T_INVINCIBLE_CONSUMABLES] = 3;
        BO6_RicSetInvincibilityFrames(1, 8);
        if (RIC.step != 0x50) {
            D_us_801CF3E0 = 1;
            func_us_801B5A14(0x20);
        }
        break;
    case 32: /* switch 1 */
        g_Player.timers[ALU_T_INVINCIBLE_CONSUMABLES] = 3;
        BO6_RicSetInvincibilityFrames(1, 8);
        if (D_us_801CF3CC == 0) {
            D_us_801CF3D0 = 0x10;
            D_us_801CF3CC = 1;
        } else {
            if (D_us_801CF3D0 != 0) {
                D_us_801CF3D0--;
            }
            func_us_801B5A14(0xF);
        }
        break;

    case 40: /* switch 1 */
        g_Player.timers[ALU_T_INVINCIBLE_CONSUMABLES] = 3;
        D_us_80181278 = 0x32;
        D_us_801CF3C8++;
        break;

    case 41: /* switch 1 */
        g_Player.timers[ALU_T_INVINCIBLE_CONSUMABLES] = 3;
        break;

    case 50: /* switch 1 */
        if (!(g_Player.status & PLAYER_STATUS_DEAD)) {
            func_us_801B5A14(0);
        }
        g_Ric.padSim = 0x1000;
        break;
    }
}

extern s32 D_us_801D11C0;

// BO6: the post-fight cutscene driver, called from EntityRichter on every
// frame the boss is not initialising. D_us_80181278 is the cutscene step;
// RichterThinking's case 40 slams it to 0x32, which is the last slot of this
// function's 51-entry jump table and therefore a deliberate no-op parking
// value. Only four of the 51 steps do anything.
//
// DERIVED BY HAND from asm/us/boss/bo6/nonmatchings/richter/func_us_801B6998.s
// after upstream's body was tried and reverted on 2026-08-16 for coming out
// one instruction long. The extra word was a nop in the branch delay slot at
// +21, where the original carries `ori $v0, $zero, 0x1`. That slot is filled
// only when the first instruction of the fall-through path is a single
// register-immediate the scheduler is allowed to hoist over the branch. Any
// store to a global expands to a two-instruction lui/%lo macro, which the
// scheduler cannot split and therefore cannot hoist, so the store must not be
// written first: `g_unkGraphicsStruct.pauseEnemies = true;` before
// `D_us_801D11C0 = 0;` is what puts the constant materialisation at the front
// of the block and lets it fall into the delay slot. Swapping those two lines
// is what costs the word.
void func_us_801B6998(void) {
    switch (D_us_80181278) {
    // Cases 0 and 50 are empty and are NOT invented padding: they are what
    // makes this a jump table instead of a compare chain. The dispatch is
    // `sltiu $v0, $v1, 0x33` straight into jtbl_us_801A69F8 with no minimum
    // subtracted first, so the compiler saw a case range of exactly 0..50, and
    // it only emits a table once the case count clears its threshold. Written
    // with just the four live steps, this function compiles to
    // `li v0,0xb / beq / slti / beq ...` and comes out 0xB4 short. Step 50 is
    // the value RichterThinking's case 40 parks here; step 0 is the initial
    // value. Both do nothing, which is why their table slots point at the
    // shared return.
    case 0:
        break;
    case 10:
        // Freeze the room for the death cutscene, but only on a real playthrough
        // that has not already beaten Shaft's orb.
        if (!g_CastleFlags[SHAFT_ORB_DEFEATED] && g_DemoMode == Demo_None) {
            g_unkGraphicsStruct.pauseEnemies = true;
            D_us_801D11C0 = 0;
        }
        D_us_80181278++;
        break;
    case 11:
        // Hold for two frames with the room frozen, then start the white-out.
        // slti (signed) against 2, so this is >= and not a bit test.
        if (++D_us_801D11C0 >= 2) {
            if (!g_CastleFlags[SHAFT_ORB_DEFEATED] && g_DemoMode == Demo_None) {
                g_unkGraphicsStruct.unk20 = 0xFF;
            }
            D_us_80181278++;
        }
        break;
    case 20:
        // Wait for the cutscene player to acknowledge, then jump to step 30.
        if (g_CutsceneFlags & 4) {
            D_us_80181278 = 30;
        }
        break;
    case 40:
        g_CutsceneFlags |= 8;
        break;
    case 50:
        break;
    }
}

extern EInit D_us_80180400;
extern s32 D_us_801CF3E0;
extern s32 D_us_801CF3E4;

// HARVESTED from upstream/master src/boss/bo6/richter.c.
//
// TWO RENAMES, both the same BO6_ prefix divergence between this fork and
// upstream, and both confirmed against config/symbols.us.bobo6.txt rather
// than guessed:
//   upstream RicMain()            -> BO6_RicMain           (INCLUDE_ASM above)
//   upstream DisableAfterImage()  -> BO6_DisableAfterImage (= 0x801B9B78)
// Everything else is upstream's verbatim, including the entity sweep from
// STAGE_ENTITY_START + 4 up to 144, which clears the room before the duel.
void EntityRichter(Entity* self) {
    Entity* entity;
    s32 i;

    g_Ric.unk6A = RIC.hitPoints;
    if (self->step == 0) {
        InitializeEntity(D_us_80180400);
        func_us_801B4BD0();
        entity = &g_Entities[STAGE_ENTITY_START + 4];
        for (i = STAGE_ENTITY_START + 4; i < 144; i++, entity++) {
            DestroyEntity(entity);
        }
        g_Ric.unk6E = g_Ric.unk6A = g_Ric.unk6C = RIC.hitPoints;
        D_us_801CF3E4 = g_Ric.unk6E / 2;
        D_us_801CF3E0 = 0;
        g_Ric.unk70 = RIC.hitboxState;
        func_us_801B5A14(18);
        BO6_DisableAfterImage(1, 48);
    } else {
        RichterThinking();
        BO6_RicMain(); // equivalent to EntityDoppleganger{10,40}
        func_us_801BBBD0();
        func_us_801B6998();
    }
    g_Ric.unk6C = g_Ric.unk6A;
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepStand);

extern s32 BO6_RicCheckInput(s32);
extern void DecelerateX(s32);
extern s32 BO6_RicCheckFacing(void);
extern void BO6_RicSetStand(s32);
extern void BO6_RicSetSpeedX(s32);

/* Ric's walking step in BOSS/BO6: when no directional input is held,
 * decelerate and either stand still or resume walk speed while the
 * sub-step counter is still zero. */
void BO6_RicStepWalk(void) {
    /* 0x305C is a capability mask, NOT pad state. BO6_RicCheckInput never
       reads the pad itself; it ANDs this argument against fixed bits to
       decide which transitions (crouch, jump, attack, dash) the current
       state is allowed to take. Every caller passes a different constant:
       BO6_RicStepStand 0x4305C, BO6_RicStepCrouch 0x4105C, BO6_RicStepJump
       0x11009. The same idiom appears in src/boss/bo4/unk_45354.c. */
    if (BO6_RicCheckInput(0x305C) == 0) {
        DecelerateX(0x2000);
        if (BO6_RicCheckFacing() == 0) {
            BO6_RicSetStand(0);
        } else if (RIC.step_s == 0) {
            BO6_RicSetSpeedX(0x14000);
        }
    }
}

extern AnimationFrame D_us_80181F24[];

// Richter (BO6) run step. This is RicStepRun without RIC's US-only unk7A
// early exit; the target begins directly with the two timer reloads.
void BO6_RicStepRun(void) {
    g_Ric.timers[PL_T_8] = 8;
    g_Ric.timers[PL_T_CURSE] = 8;
    if (!BO6_RicCheckInput(0x305C)) {
        DecelerateX(FIX(0.125));
        if (BO6_RicCheckFacing() == 0) {
            BO6_RicSetStand(0);
            if (g_Ric.timers[PL_T_RUN] == 0) {
                if (!(g_Ric.vram_flag &
                      (TOUCHING_L_WALL | TOUCHING_R_WALL))) {
                    BO6_RicSetAnimation(D_us_80181F24);
                    BO6_RicCreateEntFactoryFromEntity(
                        g_CurrentEntity, BP_SKID_SMOKE, 0);
                }
            } else {
                RIC.velocityX = 0;
            }
            return;
        }
        if (RIC.step_s == 0) {
            BO6_RicSetSpeedX(FIX(2.25));
        }
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepJump);

extern void func_us_801B9E70(void);

// Richter (BO6): the falling step. Twin of RicStepFall in src/ric/pl_steps.c,
// with no divergence beyond the g_Player -> g_Ric / PLAYER -> RIC swap.
//
// 0x9009 is the same capability mask RIC passes:
// CHECK_GROUND(1) | CHECK_FACING(8) | CHECK_ATTACK(0x1000) |
// CHECK_GRAVITY_FALL(0x8000). Spelled numerically because bo6.h pulls in
// ric_shared.h but not src/ric/ric.h, where the CHECK_* enum lives.
void BO6_RicStepFall(void) {
    if (BO6_RicCheckInput(0x9009)) {
        return;
    }
    DecelerateX(FIX(1. / 16));
    switch (RIC.step_s) {
    case 0:
        if (g_Ric.timers[PL_T_5] && (g_Ric.padTapped & PAD_CROSS)) {
            func_us_801B9E70();
        } else if (BO6_RicCheckFacing()) {
            BO6_RicSetSpeedX(FIX(0.75));
        }
        break;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepCrouch);

extern u8 RIC_drawFlags;
extern s16 RIC_poseTimer;
extern s16 RIC_pose;

void BO6_RicResetPose(void) {
    RIC_drawFlags &= ~ENTITY_ROTATE;
    RIC_poseTimer = 0;
    RIC_pose = 0;
    g_Ric.unk44 = 0;
    g_Ric.unk46 = 0;
}

// Richter (BO6): record which side the player is on. The original reuses
// Richter's entityRoomIndex as this flag rather than the entity's own
// facingLeft (which lives at +0x14, RIC_facingLeft); the address here is
// RIC + 0x32, which the Entity layout names entityRoomIndex.
void func_us_801B77D8(void) {
    if (RIC.posX.i.hi - PLAYER.posX.i.hi <= 0) {
        RIC.entityRoomIndex = 0;
    } else {
        RIC.entityRoomIndex = 1;  // player is to Richter's left
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepHit);

INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepDead);

extern s32 RIC_velocityY;
extern AnimationFrame D_us_801820B0[];
extern void BO6_RicSetStep(s32);
extern void BO6_RicSetAnimation(AnimationFrame*);

// Richter (BO6): the "hang in the air" step. Twin of RicStepStandInAir in
// src/ric/pl_steps.c, MINUS its trailing `if (g_Player.unk72) PLAYER.velocityY
// = 0;` clamp. All three exits jump straight to the epilogue at 0x385CC and
// nothing in the function loads g_Ric + 0x3C2, so adding that block would be
// inventing behaviour.
//
// RIC_velocityY is used as a flat extern rather than RIC.velocityY because the
// assembly builds a fresh lui/%lo pair for each of the three accesses, while
// step_s gets its address hoisted into $v1 once. That asymmetry is the
// signature of a plain scalar global against a struct member.
void BO6_RicStepStandInAir(void) {
    if (RIC.step_s == 0) {
        RIC_velocityY += 0x3800;
        if (RIC_velocityY > 0) {
            RIC_velocityY = 0;
            RIC.step_s = 1;
        }
    } else if (g_Ric.unk4E) {
        g_Ric.unk46 = 0;
        BO6_RicSetStep(PL_S_JUMP);
        BO6_RicSetAnimation(D_us_801820B0);
        g_Ric.unk44 = 0;
    }
}

/* BO6_RicStepEnableFlameWhip: BO6 (Richter) flame-whip entry step.
 * When the anim frame hits the flame-swing pose (0xB5) with poseTimer at 1,
 * spawn the whip entity and play its unleash SFX. Once the pose timer goes
 * negative (abort / animation end), drop back to the standing pose and kick
 * the dash-recovery timer. */
extern s16 RIC_animCurFrame; /* 0x8007632E -- flame-step swing frame */

void BO6_RicStepEnableFlameWhip(void) {
    /* Both comparisons branch to the shared end on failure, so && is exact. */
    if (RIC_animCurFrame == 0xB5 && RIC_poseTimer == 1) {
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x23, 0); /* whip entity */
        g_api_PlaySfx(0x62F);
    }

    /* poseTimer < 0 -> leave the flame step and reset its state. */
    if (RIC_poseTimer < 0) {
        BO6_RicSetStand(0);
        g_Ric.unk46 = 0;                 /* g_Ric + 0x396: step state latch */
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x450021, 0);
        g_Ric.timers[0] = 0x800;         /* g_Ric + 0x330: dash-timer reload */
    }
}

extern void BO6_RicSetStand(s32);
extern s16 RIC_poseTimer;

void BO6_RicStepHydrostorm(void) {
    if (RIC_poseTimer < 0) {
        BO6_RicSetStand(0);
        g_Ric.unk46 = 0;
    }
}

void BO6_RicStepGenericSubwpnCrash(void) {
    if (g_Ric.unk4E != 0) {
        BO6_RicSetStand(0);
        g_Ric.unk46 = 0;
    }
}

extern s32 D_us_801D07F8;

// BO6 Richter throw daggers step: manages a countdown timer while
// throwing, and allows cancellation via pad input.
void BO6_RicStepThrowDaggers(void) {
    s32 temp_v0;

    if (g_Entities[64].step_s == 0) {
        D_us_801D07F8 = 0x200;
        g_Entities[64].step_s += 1;
    } else {
        BO6_RicCheckFacing();
        temp_v0 = D_us_801D07F8 - 1;
        D_us_801D07F8 = temp_v0;
        if (temp_v0 == 0) {
            /* unk46 is an s16 field in PlayerState (not Entity hitboxWidth) */
            g_Ric.unk46 = 0;
            BO6_RicSetStand(0);
            /* unk4E is an s16 field in PlayerState */
            g_Ric.unk4E = 1;
        }
    }
    /* padTapped is a s32 field in PlayerState at offset 0x31C */
    if (g_Ric.padTapped & 0x40) {
        func_us_801B9E70();
        g_Ric.unk46 = 0;
        g_Ric.unk4E = 1;
        D_us_801D07F8 = 0;
    }
}

void BO6_RicStepSlide(void) {
    s32 isTouchingGround = 0;
    // CODEGEN: Preserve the original 0x40-byte stack frame. The live body
    // otherwise compiles instruction-for-instruction with a 0x18-byte frame.
    volatile s32 stackPadding[10];

    if (!RIC.facingLeft && (g_Ric.vram_flag & TOUCHING_R_WALL)) {
        isTouchingGround = 1;
    }
    if (RIC.facingLeft && (g_Ric.vram_flag & TOUCHING_L_WALL)) {
        isTouchingGround = 1;
    }
    if ((RIC.posX.i.hi >= STAGE_WIDTH - 4) && !RIC.facingLeft) {
        isTouchingGround = 1;
    }
    if ((RIC.posX.i.hi <= 4) && RIC.facingLeft) {
        isTouchingGround = 1;
    }
    if ((!RIC.facingLeft &&
         (g_Player.colFloor[2].effects & EFFECT_UNK_8000)) ||
        (RIC.facingLeft &&
         (g_Player.colFloor[3].effects & EFFECT_UNK_8000))) {
        isTouchingGround = 1;
    }
    if (isTouchingGround && RIC.pose < 6) {
        RIC.pose = 6;
        if (RIC.velocityX > FIX(1)) {
            RIC.velocityX = FIX(2);
        }
        if (RIC.velocityX < FIX(-1)) {
            RIC.velocityX = FIX(-2);
        }
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
    }
    if (RIC.pose < 5) {
        // BO6 input capability mask: fall or crash.
        if (BO6_RicCheckInput(0x44)) {
            return;
        }
        if (g_Ric.padTapped & PAD_CROSS) {
            RIC.posY.i.hi -= 4;
            BO6_RicSetSlideKick();
            return;
        }
    } else if (RIC.pose < 7) {
        // BO6 input capability mask: fall, crash, or slide.
        if (BO6_RicCheckInput(0x40044)) {
            return;
        }
    } else {
        // BO6 input capability mask: fall, facing, crash, or slide.
        if (BO6_RicCheckInput(0x4004C)) {
            return;
        }
    }

    DecelerateX(FIX(0.125));
    switch (RIC.step_s) {
    case 0:
        if (!(g_GameTimer & 3) && RIC.pose < 6 && RIC.pose > 2) {
            BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x20018, 0);
        }
        if (RIC.pose == 6 && RIC.poseTimer == 1) {
            BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
        }
        if (RIC.poseTimer < 0) {
            BO6_RicSetCrouch(0, RIC.velocityX);
        }
        break;
    }
}

extern AnimationFrame D_us_801820E4[];
extern AnimationFrame D_us_80182310[];

// Richter (BO6): slide-kick collision and rebound. This is the RIC twin with
// two target-visible differences: the enemy bounce assigns -3.5 directly and
// there is no separate wall-contact block that zeros horizontal velocity.
void BO6_RicStepSlideKick(void) {
    if ((g_Ric.padPressed & PAD_SQUARE) && (g_Ric.unk44 & 0x80)) {
        RIC.step = PL_S_JUMP;
        BO6_RicSetAnimation(D_us_801820E4);
        BO6_RicSetSpeedX(FIX(-1.5));
        RIC.velocityY = FIX(-3.5);
        g_Ric.unk44 |= 10;
        g_Ric.unk44 &= ~4;
        RIC.step_s = 2;
        return;
    }

    DecelerateX(FIX(0.0625));
    RIC.velocityY += 0x1000;

    if (g_Ric.vram_flag & TOUCHING_GROUND) {
        g_CurrentEntity->velocityX /= 2;
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
        RIC.facingLeft++;
        RIC.facingLeft &= 1;
        BO6_RicSetCrouch(3, RIC.velocityX);
        g_api_PlaySfx(0x64B);
        return;
    }

    if (RIC.velocityX < 0) {
        if (g_Ric.padPressed & PAD_RIGHT) {
            DecelerateX(FIX(0.125));
        }
        if ((RIC.velocityX > FIX(-3)) ||
            (g_Ric.vram_flag & TOUCHING_L_WALL)) {
            RIC.facingLeft++;
            RIC.facingLeft &= 1;
            RIC.velocityX /= 2;
            BO6_RicSetAnimation(D_us_80182310);
            g_Ric.unk44 = 10;
            RIC.step_s = 2;
            RIC.step = PL_S_JUMP;
        }
    }

    if (RIC.velocityX > 0) {
        if (g_Ric.padPressed & PAD_LEFT) {
            DecelerateX(FIX(0.125));
        }
        if ((RIC.velocityX < FIX(3)) ||
            (g_Ric.vram_flag & TOUCHING_R_WALL)) {
            RIC.facingLeft++;
            RIC.facingLeft &= 1;
            RIC.velocityX /= 2;
            BO6_RicSetAnimation(D_us_80182310);
            g_Ric.unk44 = 10;
            RIC.step_s = 2;
            RIC.step = PL_S_JUMP;
        }
    }
}

#include "bo6.h"

/*
 * BO6 version of Ric's dashing idle-step: the overlay's twin of RicStepBladeDash.
 * Keeps welding Ric to the sabre dash, decays the forward velocity, and every
 * 4 ticks while in the 0x20018 costume it spawns a slide-dust burst.
 */
void BO6_RicStepBladeDash(void) {
    DecelerateX(0x1C00); /* drag the dash velocity down so the squeal skid stops */

    if (RIC_poseTimer < 0) {                /* idle pose expired -> stand back up */
        g_Ric.unk46 = 0;                    /* offset 0x396: clear the dash-hold flag */
        BO6_RicSetStand(0);
        return;
    }
    /* if we are no longer in the dash pose range and are not flagged airborne */
    if ((u16)RIC_pose >= 0x12U && !(g_Ric.vram_flag & 1)) {
        g_Ric.unk46 = 0;                    /* offset 0x396 */
        BO6_RicSetFall();
        return;
    }
    /* while the dash pose is active, seed a smoke entity every 4 game ticks */
    if ((g_GameTimer & 3) == 0 && (u16)RIC_pose < 0x12U && (g_Ric.vram_flag & 1)) {
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x20018, 0);
    }
    /* final slash end: read pose as a word so entity factory id 0 fires exactly
     * once when the pose counter has been pushed into the 0x10012 delta */
    if (*(s32 *)&RIC_pose == 0x10012 && (g_Ric.vram_flag & 1)) {
        BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0, 0);
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/richter", func_us_801B8E80);

extern AnimationFrame D_us_801820BC[];

// Richter (BO6): sustain the high jump, react to the ceiling, then transition
// to the ordinary jump step once upward momentum or the recovery timer ends.
void BO6_RicStepHighJump(void) {
    bool loadAnim;

    loadAnim = false;
    g_Ric.high_jump_timer++;
    switch (RIC.step_s) {
    case 0:
        if (g_Ric.padPressed & (PAD_LEFT | PAD_RIGHT)) {
            if (RIC.facingLeft) {
                if (!(g_Ric.padPressed & PAD_LEFT)) {
                    DecelerateX(FIX(0.0625));
                }
            } else {
                if (!(g_Ric.padPressed & PAD_RIGHT)) {
                    DecelerateX(FIX(0.0625));
                }
            }
        } else {
            DecelerateX(FIX(0.0625));
        }

        if (g_Ric.vram_flag & TOUCHING_CEILING) {
            func_us_801B8E80(3);
            g_Ric.high_jump_timer = 0;
            RIC.step_s = 2;
        } else if (g_Ric.high_jump_timer > 0x1C) {
            RIC.step_s = 1;
            RIC.velocityY = -0x60000;
        }
        break;
    case 1:
        if (g_Ric.vram_flag & TOUCHING_CEILING) {
            RIC.step_s = 2;
            func_us_801B8E80(3);
            g_Ric.high_jump_timer = 0;
        } else {
            RIC.velocityY += 0x6000;
            if (RIC.velocityY > 0x8000) {
                loadAnim = true;
            }
        }
        break;
    case 2:
        if (g_Ric.high_jump_timer > 4) {
            loadAnim = true;
        }
        break;
    }

    if (loadAnim) {
        BO6_RicSetAnimation(D_us_801820BC);
        BO6_RicSetStep(PL_S_JUMP);
    }
}
