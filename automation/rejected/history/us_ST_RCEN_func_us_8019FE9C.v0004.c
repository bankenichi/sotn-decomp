/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RCEN:func_us_8019FE9C
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_elevator.c
   verdict: BUILD FAILED:
15:src/st/rcen/e_elevator.c:32: `g_eBreakableAnimations' undeclared (first use this function)
16:src/st/rcen/e_elevator.c:32: (Each undeclared identifier is reported only once
17:src/st/rcen/e_elevator.c:32: for each function it appears in.)
18:src/st/rcen/e_elevator.c:34: `PLAYER_zPriority' undeclared (first use this function)
19:src/st/rcen/e_elevator.c:69: `D_80073510' undeclared (first use this function)
20:src/st/rcen/e_elevator.c:79: `PLAYER_posX_i_hi' undeclared (first use this function)
21:src/st/rcen/e_elevator.c:87: `PLAYER_velocityX' undeclared (first use this function)
22:src/st/rcen/e_elevator.c:88: `PLAYER_velocityY' undeclared (first use this function)
23:src/st/rcen/e_elevator.c:109: `D_us_80180A54' undeclared (first use this function)
24:src/st/rcen/e_elevator.c:128: `D_us_80180A3C' undeclared (first use this function)
25:src/st/rcen/e_elevator.c:139: `PLAYER_posY_i_hi' undeclared (first use this function)
26-[14/157] psx cc src/weapon/w_009.c
27-[15/157] psx cc src/weapon/w_010.c

   This is NOT a permuter seed and must never be treated as
   one: it has never built. automation/candidates/ is for
   code that builds and merely misses on bytes.

   Why it is kept: the escalation path used to record only
   the compiler's message, so a record like `g_EInitCommon
   undeclared` described code nobody could look at any more.
   Twelve such records were assumed to be one extern away
   from building, and turned out to need a full re-attempt
   because the candidate had been discarded.

   Do NOT apply this to the tree. Read it, fix what the
   verdict names, and re-attempt. */
/* Mechanical symbol repair from escalation_triage.py. */
extern s32 D_us_80180A54[]; /* retained ST/RCEN data asm/us/st/rcen/data/A3C.data.s, size 0x18 */
extern s32 D_us_80180A3C[]; /* retained ST/RCEN data asm/us/st/rcen/data/A3C.data.s, size 0x18 */

void func_us_8019FE9C(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s16 temp;
    u16 step;
    u16 step_s;
    Entity* child;
    s32 flags;

    step = self->step;
    switch (step) {
    case 0:
        InitializeEntity(g_eBreakableAnimations);
        self->animCurFrame = 3;
        self->zPriority = PLAYER_zPriority + 0xC;
        CreateEntityFromCurrentEntity(0x25, self - 0xBC);
        (self - 0x178)->pose = 1;
        CreateEntityFromCurrentEntity(0x25, self - 0x178);
        (self - 0x148)->pose = 2;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 0xC);
        if (primIndex != -1) {
            prim = &g_PrimBuf[primIndex];
            self->primIndex = primIndex;
            self->ext.prim = prim;
            self->flags |= 0x800000;
            prim->tpage = 0x12;
            prim->clut = 0x240;
            prim->u3 = 0x38;
            prim->u1 = 0x38;
            prim->v3 = 0x38;
            prim->v2 = 0x38;
            prim->priority = 0x6B;
            prim->u2 = 0x28;
            prim->u0 = 0x28;
            prim->v1 = 0x28;
            prim->v0 = 0x28;
            prim->drawMode = 8;
            prim = prim->next;
            while (prim != NULL) {
                prim->tpage = 0x12;
                prim->clut = 0x240;
                prim->priority = 0x6A;
                prim->drawMode = 8;
                prim = prim->next;
            }
            if (g_Entities[0].posY.i.hi >= 0xC1) {
                self->posY.i.hi = g_Entities[0].posY.i.hi;
                g_Entities[0].posX.i.hi = self->posX.i.hi;
                self->animCurFrame = 0xA;
                D_80073510 = 1;
                SetStep(2);
            }
        } else {
            DestroyEntity(self);
            return;
        }
        break;
    case 1:
        if ((self->ext.player.pad != 0) && (g_pads->pressed & 0x4000)) {
            temp = self->posX.i.hi - PLAYER_posX_i_hi;
            if (temp < 0) {
                temp = -temp;
            }
            if (temp < 8) {
                D_80073510 = 1;
                g_Player.demo_timer = 2;
                g_Player.padSim = 0;
                PLAYER_velocityX = 0;
                PLAYER_velocityY = 0;
                self->step = 3;
            }
        }
        break;
    case 2:
        g_Player.demo_timer = 2;
        g_Player.padSim = 0;
        step_s = self->step_s;
        switch (step_s) {
        case 0:
            self->posY.val -= 0x8000;
            if ((s16)(g_Tilemap.scrollY.i.hi + self->posY.i.hi) < 0x18D) {
                self->posY.i.hi = 0x18C - g_Tilemap.scrollY.i.hi;
                self->step_s += 1;
            }
            if (!(g_Timer & 0xF)) {
                PlaySfxPositional(0x60D);
            }
            break;
        case 1:
            if (AnimateEntity(D_us_80180A54, self) == 0) {
                self->pose = 0;
                self->poseTimer = 0;
                D_80073510 = 0;
                self->step_s = 0;
                self->step = 1;
            }
            if (self->pose == 4) {
                g_api_PlaySfx(0x675);
            }
            break;
        }
        break;
    case 3:
        g_Player.demo_timer = 2;
        g_Player.padSim = 0;
        step_s = self->step_s;
        switch (step_s) {
        case 0:
            if (AnimateEntity(D_us_80180A3C, self) == 0) {
                self->pose = 0;
                self->poseTimer = 0;
                self->step_s += 1;
            }
            if (self->pose == 4) {
                g_api_PlaySfx(0x675);
            }
            break;
        case 1:
            self->posY.val += 0x8000;
            PLAYER_posY_i_hi += 1;
            if (!(g_Timer & 0xF)) {
                PlaySfxPositional(0x60D);
            }
            break;
        }
        break;
    }

    prim = self->ext.prim;
    temp = self->posX.i.hi - 8;
    prim->x2 = temp;
    prim->x0 = temp;
    temp = self->posX.i.hi + 8;
    prim->x3 = temp;
    prim->x1 = temp;
    temp = self->posY.i.hi;
    prim->drawMode = 2;
    prim->y3 = temp + 0x1F;
    prim->y2 = temp + 0x1F;
    prim->y1 = temp + 0x2F;
    prim->y0 = temp + 0x2F;
    prim = prim->next;
    temp = self->posY.i.hi + 0x28;
    while (prim != NULL) {
        temp = func_801904B8(prim, temp);
        prim = prim->next;
        if (temp < 0x20) {
            break;
        }
    }
    while (prim != NULL) {
        prim->drawMode = 8;
        prim = prim->next;
    }
}