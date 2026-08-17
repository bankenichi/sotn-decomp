// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/e_elevator", func_us_8019FD4C_from_rcen);

// TWIN PORT from this fork's own src/st/no0/e_elevator.c:37, which is already
// matched. Not an upstream harvest: the donor is in-tree.
//
// A STRAIGHT COPY OF THE DONOR DOES NOT MATCH, and this is the
// CONSTANT_DIVERGENT class asm_twin_finder warns about by name. RNO0's
// elevator shaft sits elsewhere on screen, so every geometry constant differs
// and the branch is inverted. Derived instruction by instruction from
// asm/us/st/rno0/nonmatchings/e_elevator/func_us_801C2044_from_no0.s:
//
//   donor (NO0)                  here (RNO0)          evidence
//   dy -= 0x20                   dy += 0x20           addiu $v0, $a1, 0x20
//   if (dy < 0x44) complex       if (dy >= 0xC0) ..   slti 0xC0 + bnez to the
//                                                     SIMPLE path, so the
//                                                     sense is reversed
//   dy = 0x44 - dy               dy -= 0xC0           addiu $a1, $a1, -0xA0 on
//                                                     the ORIGINAL dy, and
//                                                     -0xA0 == +0x20 - 0xC0
//   y0 = 0x44                    y0 = 0xC0            ori $v0, 0xC0
//   next y0 = 0x2C               next y0 = 0xBC       ori $v0, 0xBC
//   next y2 = 0x3C               next y2 = 0xCC       ori $v0, 0xCC
//   next x1 = posX + dy          next x1 = posX - dy  subu $v0, $v0, $a1
//
// STATIC as of 2026-08-17, matching the donor. It could not be until now: its
// only caller, func_us_801C2184_from_no0, was INCLUDE_ASM just below, so the
// assembly referenced this by name and it needed external linkage. That caller
// is C in this same translation unit now, which is exactly the condition the
// note here used to be waiting on.
static s16 func_us_801C2044_from_no0(Primitive* prim, s16 dy) {
    prim->drawMode = DRAW_UNK02;
    prim->u0 = prim->u2 = 0x50;
    prim->u1 = prim->u3 = 0x60;
    prim->x0 = prim->x2 = g_CurrentEntity->posX.i.hi - 8;
    prim->x1 = prim->x3 = g_CurrentEntity->posX.i.hi + 8;
    prim->v2 = prim->v3 = 0x26;
    prim->y2 = prim->y3 = dy;
    dy += 0x20;

    if (dy >= 0xC0) {
        dy -= 0xC0;
        prim->v0 = prim->v1 = dy + 6;
        prim->y0 = prim->y1 = 0xC0;

        prim = prim->next;
        // NOT the chained `prim->v0 = prim->v1 = 0x50` the donor uses, and the
        // split is the whole remaining difference. With the chained form the
        // compiler evaluates `0x22 - dy` three slots earlier and the register
        // allocation moves with it: the copy of dy lands in $v0 instead of $a0,
        // dy+6 in $v1 instead of $v0, and 0x22-dy in $a0 instead of $v1. Eight
        // instructions differ and every one of them is only a register number.
        // Splitting v1 out and storing v0 after the y pair puts the
        // subtraction back where the original has it, at index 39.
        prim->v1 = 0x50;
        prim->y0 = prim->y1 = 0xBC;
        prim->v0 = 0x50;
        prim->v2 = prim->v3 = 0x60;
        prim->u0 = prim->u2 = 0x22 - dy;
        prim->u1 = prim->u3 = 0x22;
        prim->drawMode = DRAW_UNK02;
        prim->y2 = prim->y3 = 0xCC;
        prim->x0 = prim->x2 = g_CurrentEntity->posX.i.hi;
        prim->x1 = prim->x3 = g_CurrentEntity->posX.i.hi - dy;
    } else {
        prim->v0 = prim->v1 = 6;
        prim->y0 = prim->y1 = dy;
    }
    return dy;
}

// The two elevator animation scripts. NO0 declares them static in
// src/st/no0/e_elevator.c as anim0 and anim1; RNO0's copies are still inside
// the undecompiled data blob that runs from 0xED0, so this overlay reaches them
// by their splat symbols. The addresses are read from the disassembly, not
// guessed: the two AnimateEntity calls in the function below do lui/addiu on
// D_us_80180FAC and D_us_80180FC4 directly. Declaring them this way is also why
// no [0xFAC, .data, e_elevator] segment is needed -- splat keeps emitting the
// blob and the compiled file does not duplicate it.
extern u8 D_us_80180FAC[];
extern u8 D_us_80180FC4[];

// Still INCLUDE_ASM immediately above, so it needs a declaration before use.
s16 func_us_8019FD4C_from_rcen(Primitive* prim, s16 dx);

// The elevator's InitializeEntity descriptor, defined in src/st/rno0/e_init.c
// and not reachable through rno0.h. It is g_EInitElevator in upstream and in
// every sibling overlay, but it keeps the raw name here while EntityUnkId1B
// below is still INCLUDE_ASM: that stub references D_us_80180BF4 and `make
// extract` will not rewrite it, so renaming breaks the link. See the note at
// its definition, and the same warning in config/symbols.us.strno0.txt.
//
// Declaring it at all is not bookkeeping. At -w this toolchain compiles an
// undeclared identifier to 0 with no diagnostic, so leaving this out would
// have produced InitializeEntity(NULL) in a build that looked clean.
extern EInit D_us_80180BF4;

// TWIN PORT from src/st/no0/e_elevator.c:69, matched there. The elevator the
// player rides between the clock room and the caverns.
//
// CONSTANT_DIVERGENT, and heavily so: this is the inverted castle, so the
// elevator travels the other way and almost every constant that describes its
// motion flips. Derived instruction by instruction from
// asm/us/st/rno0/nonmatchings/e_elevator/func_us_801C2184_from_no0.s:
//
//   donor (NO0)                        here (RNO0)          evidence
//   clut 0x223                         0x240                ori $v0, 0x240
//   if (player posY > 0xC0)            < 0x50               slti 0x50 + beqz
//   SetStep(2)                         SetStep(3)           ori $a0, 3
//   (self - 1)->playerCollision        (self - 2)->..       lbu -0xF8($s1),
//                                                           and -0x178 + 0x80
//   padSim = PAD_DOWN                  0                    sw $zero, +0x324
//   self->step = 3                     2                    ori $v0, 2
//   posY.val += FIX(0.5)  (ride)       -= FIX(0.5)          addiu $v0, -0x8000
//   posY.val -= FIX(0.5)  (return)     += FIX(0.5)          ori $v1, 0x8000
//   if (dy == 0x94)                    == 0x6C              ori $v1, 0x6C
//   y2 = posY - 0x1F                   + 0x1F               addiu $v0, 0x1F
//   y0 = y2 - 0x10                     y2 + 0x10            addiu $v1, 0x2F
//   dy = posY - 0x28                   + 0x28               addiu $a1, 0x28
//   if (dy <= 0x20) break              < 0x20               slti 0x20
//   dx = posX + dy                     posX - dy            subu $v0, $v0, $a1
//
// THE TWO MOVING STEPS ARE ALSO SWAPPED. RNO0's case 2 holds what the donor
// puts in case 3 and vice versa, which follows from step 1 setting step = 2
// rather than 3. The bodies appear in numeric order in the assembly, so they
// are written in numeric order here.
//
// TWO STRUCTURAL DIFFERENCES, not constants:
//
//   `player->posY.i.hi++` sits in the ASCENDING step here (case 3, step_s 0)
//   where the donor has it in its descending one. The player is carried up
//   rather than down.
//
//   the final `if (abs(self->posY.i.hi) > 0x180) DestroyEntity(self);` has no
//   counterpart at all: the assembly's tail is the bare epilogue.
void func_us_801C2184_from_no0(Entity* self) {
    Entity* player = &PLAYER;
    Entity* parent;
    Primitive* prim;
    s32 primIndex;
    s16 dx, dy;
    u8 var_s6;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180BF4);
        self->animCurFrame = 3;
        self->zPriority = player->zPriority + 0xC;

        parent = (self - 1);
        CreateEntityFromCurrentEntity(E_UNK_ID1B, parent);
        parent->params = 1;

        parent = (self - 2);
        CreateEntityFromCurrentEntity(E_UNK_ID1B, parent);
        parent->params = 2;

        primIndex = g_api.AllocPrimitives(PRIM_GT4, 12);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.cenElevator.prim = prim;
            prim->tpage = 0x12;
            prim->clut = 0x240;
            prim->u0 = prim->u2 = 0x28;
            prim->u1 = prim->u3 = 0x38;
            prim->v0 = prim->v1 = 0x28;
            prim->v2 = prim->v3 = 0x38;
            prim->priority = 0x6B;
            prim->drawMode = DRAW_HIDE;

            prim = prim->next;
            while (prim != NULL) {
                prim->tpage = 0x12;
                prim->clut = 0x240;
                prim->priority = 0x6A;
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
            }
        } else {
            DestroyEntity(self);
            return;
        }

        if (player->posY.i.hi < 0x50) {
            self->posY.i.hi = player->posY.i.hi;
            player->posX.i.hi = self->posX.i.hi;
            self->animCurFrame = 10;
            g_Entities[E_AFTERIMAGE_1].ext.afterImage.disableFlag = 1;
            SetStep(3);
        }
        break;

    case 1:
        var_s6 = (self - 2)->ext.cenElevator.playerCollision;
        if (var_s6) {
            dx = self->posX.i.hi - player->posX.i.hi;
            // PAD_UP (0x1000), not the donor's PAD_DOWN (0x4000): `andi $v0,
            // $v0, 0x1000`. The inverted castle's elevator travels upward, so
            // the player summons it by pressing up.
            if (g_pads[0].pressed & PAD_UP && abs(dx) < 8) {
                g_Entities[E_AFTERIMAGE_1].ext.afterImage.disableFlag = 1;
                g_Player.demo_timer = 2;
                g_Player.padSim = 0;
                player->velocityX = 0;
                player->velocityY = 0;
                self->step = 2;
            }
        }
        break;

    case 2:
        g_Player.demo_timer = 2;
        g_Player.padSim = 0;
        switch (self->step_s) {
        case 0:
            if (!AnimateEntity(D_us_80180FAC, self)) {
                self->pose = 0;
                self->poseTimer = 0;
                self->step_s += 1;
            }
            if (!self->poseTimer && self->pose == 4) {
                g_api.PlaySfx(SFX_LEVER_METAL_BANG);
            }
            break;

        case 1:
            self->posY.val -= FIX(0.5);
            if ((g_Timer & 0xF) == 0) {
                PlaySfxPositional(SFX_METAL_CLANG_A);
            }
            break;
        }
        break;

    case 3:
        g_Player.demo_timer = 2;
        g_Player.padSim = 0;
        switch (self->step_s) {
        case 0:
            self->posY.val += FIX(0.5);
            player->posY.i.hi++;
            dy = g_Tilemap.scrollY.i.hi + self->posY.i.hi;
            if (dy == 0x6C) {
                self->step_s++;
            }
            if ((g_Timer & 0xF) == 0) {
                PlaySfxPositional(SFX_METAL_CLANG_A);
            }
            break;

        case 1:
            if (!AnimateEntity(D_us_80180FC4, self)) {
                self->pose = 0;
                self->poseTimer = 0;
                g_Entities[E_AFTERIMAGE_1].ext.afterImage.disableFlag = 0;
                self->step_s = 0;
                self->step = 1;
            }
            if (!self->poseTimer && self->pose == 4) {
                g_api.PlaySfx(SFX_LEVER_METAL_BANG);
            }
            break;
        }
        break;
    }

    prim = self->ext.cenElevator.prim;
    prim->x0 = prim->x2 = self->posX.i.hi - 8;
    prim->x1 = prim->x3 = self->posX.i.hi + 8;
    prim->y2 = prim->y3 = self->posY.i.hi + 0x1F;
    prim->y0 = prim->y1 = prim->y2 + 0x10;
    prim->drawMode = DRAW_UNK02;

    prim = prim->next;
    dy = self->posY.i.hi + 0x28;

    while (prim != NULL) {
        dy = func_us_801C2044_from_no0(prim, dy);
        prim = prim->next;

        if (dy < 0x20)
            break;
    }

    // GUARDED, where the donor writes a bare `prim = prim->next`. The assembly
    // tests $s0 at .Lus_801B6CE8 before the load, and it has to: this point is
    // reached both by the break above (prim may be live) and by the loop
    // running out (prim is NULL).
    if (prim != NULL) {
        prim = prim->next;
    }

    dx = self->posX.i.hi - dy;

    while (prim != NULL) {
        dx = func_us_8019FD4C_from_rcen(prim, dx);
        prim = prim->next;

        if (!dx)
            break;
    }

    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/e_elevator", EntityUnkId1B);
