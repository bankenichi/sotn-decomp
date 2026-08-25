/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO5:EntityBell
   source : upstream/master:src/st/dai/e_bell.c
   target : src/boss/bo5/e_bell.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
extern void SetDrawEnv(DR_ENV* dr_env, DRAWENV* env);
int abs(int x);
int rsin(int a);
int rcos(int a);
void SetGeomScreen(long h);
void SetGeomOffset(long ofx, long ofy);
MATRIX* RotMatrix(SVECTOR* r, MATRIX* m);
MATRIX* TransMatrix(MATRIX* m, VECTOR* v);
void SetRotMatrix(MATRIX* m);
void SetTransMatrix(MATRIX* m);
long RotTransPers4(
    SVECTOR* v0, SVECTOR* v1, SVECTOR* v2,
    SVECTOR* v3, // Pointers to vectors (input)
    long* v10, long* v11, long* v12,
    long* v13, // Pointers to screen coordinates
    long* p,   // Pointer to interpolated value for depth cueing
    long* flag // Pointer to flag
);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;

void EntityBell(Entity* self) {
    s16 angle;
    bool sfxFlag;
    s32 primIndex;
    s32 gteFlag;
    s32 gteParams;
    s32 ropeLength;
    s32 priority;
     
     
    s32 tempPosX;
    s32 tempPosY;
    s32 tempX1;
    s32 tempY1;
    s32 tempX2;
    s32 tempY2;
    s32 tempX3;
    s32 tempY3;
    BellParams* bellParams;
    Entity* playerPtr;
    DRAWENV drawEnv;
    DR_ENV* drEnv;
    RECT clipRect;
    SVECTOR rotVector;
    s32 ropeSegments;
    s32 posY;
    SVEC4* pointsPtr;
    s32 posX;
    s32 segment;
    Primitive* prim;
     
    s32 dummy[4];
    MATRIX mtx;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->zPriority = g_unkGraphicsStruct.g_zEntityCenter + 8;
        self->ext.bell.ringTimer = 0;
        bellParams = &bell_params[self->params];
        ropeSegments = bellParams->ropeSegments;
        priority = bellParams->priority;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, ropeSegments + 6);
        if (primIndex == -1) {
            self->step = BELL_INIT;
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.bell.prim = prim;
        ropeLength = bellParams->ropeLength;
        prim->tpage = 15;
        prim->clut = PAL_BELL_ROPE;
        prim->u0 = prim->u2 = 96;
        prim->u1 = prim->u3 = 128;
        prim->v0 = prim->v1 = 0;
        prim->v2 = prim->v3 = 24;
        prim->x0 = prim->x2 = self->posX.i.hi - 16;
        prim->x1 = prim->x3 = prim->x0 + 32;
        prim->y0 = prim->y1 = self->posY.i.hi - 10;
        prim->y2 = prim->y3 = prim->y1 + 24;
        prim->priority = (priority - 1);
        prim->drawMode = DRAW_UNK02;
        prim = prim->next;
        for (segment = 0; segment < ropeSegments; segment++) {
            prim->tpage = 15;
            prim->clut = PAL_BELL_ROPE;
            prim->u0 = prim->u2 = 120;
            prim->u1 = prim->u3 = 128;
            prim->v0 = prim->v1 = 65;
            prim->v2 = prim->v3 = (ropeLength + 65);
            prim->priority = priority;
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        }
        prim->tpage = 15;
        prim->clut = PAL_BELL_ROPE;
        prim->u0 = prim->u2 = 96;
        prim->u1 = prim->u3 = 128;
        prim->v0 = prim->v1 = 36;
        prim->v2 = prim->v3 = 62;
        prim->priority = priority;
        prim->drawMode = DRAW_UNK02;
        prim = prim->next;
        for (segment = 0; segment < 2; segment++) {
            prim->tpage = 15;
            prim->clut = PAL_BELL;
            prim->u0 = prim->u2 = 177;
            prim->u1 = prim->u3 = 224;
            prim->v0 = prim->v1 = 1;
            prim->v2 = prim->v3 = 97;
            prim->priority = priority;
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        }
        drawEnv = g_CurrentBuffer->draw;

        drEnv = g_api.func_800EDB08((POLY_GT4*)prim);
        if (drEnv == NULL) {
            DestroyEntity(self);
            return;
        }
        prim->type = PRIM_ENV;
        drawEnv.isbg = 0;
        drawEnv.r0 = 0;
        drawEnv.g0 = 0;
        drawEnv.b0 = 0;
        drawEnv.dtd = 0;
        drawEnv.ofs[0] = 0;
        clipRect.x = 0;
        clipRect.w = 256;
        clipRect.y = 20;
        clipRect.h = 207;
        drawEnv.clip = clipRect;
        SetDrawEnv(drEnv, &drawEnv);
        prim->priority = (g_unkGraphicsStruct.g_zEntityCenter - 1);
        prim->drawMode = DRAW_UNK_1000 | DRAW_HIDE;
        prim = prim->next;
        drEnv = g_api.func_800EDB08((POLY_GT4*)prim);
        if (drEnv == NULL) {
            DestroyEntity(self);
            return;
        }
        prim->type = PRIM_ENV;
        prim->priority = (g_unkGraphicsStruct.g_zEntityCenter + 1);
        prim->drawMode = DRAW_UNK_800 | DRAW_HIDE;
        prim = prim->next;
    }
    self->ext.bell.swingDistance += self->ext.bell.swingVelocity;
    if (self->ext.bell.swingDistance > self->ext.bell.maxSwing) {
        self->ext.bell.swingVelocity -= FIX(0.25);
    }
    if (self->ext.bell.swingDistance < self->ext.bell.maxSwing) {
        self->ext.bell.swingVelocity += FIX(0.25);
    }
    self->ext.bell.swingVelocity -= self->ext.bell.swingVelocity / 8;
    if ((abs(self->ext.bell.swingVelocity) < FIX(0.375)) &&
        (abs(self->ext.bell.swingDistance - self->ext.bell.maxSwing) <
         FIX(0.375))) {
        self->ext.bell.swingVelocity = 0;
        self->ext.bell.swingDistance = self->ext.bell.maxSwing;
    }
    if (self->ext.bell.swingDistance > FIX(64.0)) {
        self->ext.bell.swingDistance = FIX(64.0);
    }
    if (self->ext.bell.swingDistance < FIX(-64.0)) {
        self->ext.bell.swingDistance = FIX(-64.0);
    }
    bellParams = &bell_params[self->params];
    priority = bellParams->priority;
    if (g_Player.status & PLAYER_STATUS_MIST_FORM) {
        priority = g_unkGraphicsStruct.g_zEntityCenter - 4 + (priority - 169);
    }

    posX = self->posX.i.hi;
    posY = self->posY.i.hi;
    ropeSegments = bellParams->ropeSegments;
    ropeLength = bellParams->ropeLength;
    angle = 0;
    prim = self->ext.bell.prim;
    prim->priority = (priority - 1);
    prim = prim->next;
    tempPosX = posX - 4;
    tempPosY = posY;
    tempX1 = posX + 4;
    tempY1 = posY;

    for (segment = 0; segment < ropeSegments; segment++) {
        posX -= (ropeLength * rsin(angle)) >> 12;
        posY += (ropeLength * rcos(angle)) >> 12;
        angle =
            ((self->ext.bell.swingDistance / ropeSegments) * segment) / FIX(1);
        tempX2 = posX - ((rsin(angle + 1024) * 4) >> 12);
        tempY2 = posY + ((rcos(angle + 1024) * 4) >> 12);
        tempX3 = posX - ((rsin(angle - 1024) * 4) >> 12);
        tempY3 = posY + ((rcos(angle - 1024) * 4) >> 12);
        prim->x0 = tempPosX;
        prim->y0 = tempPosY;
        prim->x1 = tempX1;
        prim->y1 = tempY1;
        prim->x2 = tempX2;
        prim->y2 = tempY2;
        prim->x3 = tempX3;
        prim->y3 = tempY3;
        prim->priority = priority;
        prim->drawMode = DRAW_UNK02;
        tempPosX = tempX2;
        tempPosY = tempY2;
        tempX1 = tempX3;
        tempY1 = tempY3;
        prim = prim->next;
    }
    SetGeomScreen(1024);
    SetGeomOffset(posX, posY);
    rotVector.vx = 0;
    rotVector.vy = 0;
    rotVector.vz = angle;
    RotMatrix(&rotVector, &mtx);
    TransMatrix(&mtx, &trans_vector);
    SetRotMatrix(&mtx);
    SetTransMatrix(&mtx);
    pointsPtr = points;
    for (segment = 0; segment < 3; segment++) {
        RotTransPers4(
            pointsPtr->v0, pointsPtr->v1, pointsPtr->v2, pointsPtr->v3,
            (long*)&prim->x0, (long*)&prim->x1, (long*)&prim->x2,
            (long*)&prim->x3, (long*)&gteFlag, (long*)&gteParams);
        pointsPtr++;
        prim->priority = priority;
        prim->drawMode = DRAW_UNK02;
        prim = prim->next;
    }
    tempPosX = posX;
    tempPosY = posY;
    playerPtr = &PLAYER;
    posX = playerPtr->posX.i.hi - tempPosX;
    posY = tempPosY + 124 - playerPtr->posY.i.hi;
    if ((u16)(posY) < 80 && (abs(posX) < 24)) {
        drEnv = PRIM_DR_ENV(prim);
        drawEnv = g_CurrentBuffer->draw;
        drawEnv.isbg = 0;
        drawEnv.ofs[0] = 0;
        clipRect.x = 0;
        clipRect.w = 256;
        clipRect.y = tempPosY + 120;
        clipRect.h = 227 - (tempPosY + 140);
        drawEnv.clip = clipRect;
        SetDrawEnv(drEnv, &drawEnv);
        prim->priority = (g_unkGraphicsStruct.g_zEntityCenter - 1);
        prim->drawMode = DRAW_UNK_1000;
        prim = prim->next;
        prim->drawMode = DRAW_UNK_800;
        prim = prim->next;
        g_api.func_8010DFF0(1, 1);
        g_api.func_8010E168(1, 32);
        g_Player.status |= PLAYER_STATUS_UNK100000 | PLAYER_STATUS_UNK8;
        if (!(g_Player.status &
              (PLAYER_STATUS_MIST_FORM | PLAYER_STATUS_BAT_FORM))) {
            g_Player.demo_timer = 2;
            g_Player.padSim = PAD_NONE;
        }
    } else {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
    self->hitboxWidth = 56;
    self->hitboxHeight = 128;
    self->hitboxHeight /= 2;
    self->hitboxOffY = (tempPosY - 8) - self->posY.i.hi;
    self->hitboxOffY += self->hitboxHeight;
    self->hitboxState = 1;
    sfxFlag = false;
    switch (self->ext.bell.step) {
    case BELL_NEUTRAL:
        self->ext.bell.maxSwing = 0;
        playerPtr = &PLAYER;
        posX = playerPtr->posX.i.hi - self->posX.i.hi;
        posY = playerPtr->posY.i.hi - (tempPosY - 8);
        if ((u16)(posY) < 128 && (abs(posX) < 56)) {
            if (g_Player.vram_flag & TOUCHING_GROUND) {
                sfxFlag = true;
                self->ext.bell.step = BELL_HIT_OUTSIDE;
                if (posX > 0) {
                    self->ext.bell.swingVelocity = FIX(10.0);
                } else {
                    self->ext.bell.swingVelocity = FIX(-10.0);
                }
            }
            if (g_Player.vram_flag & TOUCHING_CEILING) {
                sfxFlag = true;
                self->ext.bell.step = BELL_HIT_INSIDE;
                if (posX > 0) {
                    self->ext.bell.swingVelocity = FIX(-8.0);
                } else {
                    self->ext.bell.swingVelocity = FIX(8.0);
                }
            }
        }
        break;
    case BELL_HIT_OUTSIDE:
        playerPtr = &PLAYER;
        posX = playerPtr->posX.i.hi - self->posX.i.hi;
        if (!(g_Player.vram_flag & TOUCHING_GROUND)) {
            sfxFlag = true;
            self->ext.bell.step = BELL_NEUTRAL;
            if (posX > 0) {
                self->ext.bell.swingVelocity = FIX(10.0);
            } else {
                self->ext.bell.swingVelocity = FIX(-10.0);
            }
        } else if (posX > 0) {
            self->ext.bell.maxSwing = FIX(20.0);
        } else {
            self->ext.bell.maxSwing = FIX(-20.0);
        }
        break;
    case BELL_HIT_INSIDE:
        self->ext.bell.maxSwing = 0;
        if (!(g_Player.vram_flag & TOUCHING_CEILING)) {
            sfxFlag = true;
            self->ext.bell.step = BELL_NEUTRAL;
        }
        break;
    }
    if (self->ext.bell.ringTimer) {
        self->ext.bell.ringTimer--;
        return;
    }
    if (sfxFlag) {
        g_api.PlaySfx(SFX_CHAPEL_BELL);
        self->ext.bell.ringTimer = 64;
        return;
    }
}
