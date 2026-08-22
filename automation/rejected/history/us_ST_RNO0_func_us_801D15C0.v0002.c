/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801D15C0
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   verdict: BUILD FAILED:
92:src/st/rno0/unk_4F968.c:122: structure has no member named `unkAB'
93:src/st/rno0/unk_4F968.c:143: `D_us_80183310' undeclared (first use this function)
94:src/st/rno0/unk_4F968.c:143: (Each undeclared identifier is reported only once
95:src/st/rno0/unk_4F968.c:143: for each function it appears in.)
96:src/st/rno0/unk_4F968.c:145: structure has no member named `unkA4'
97:src/st/rno0/unk_4F968.c:154: `g_Entities_160' undeclared (first use this function)
98:src/st/rno0/unk_4F968.c:166: structure has no member named `unkA4'
99:src/st/rno0/unk_4F968.c:167: structure has no member named `unkA4'
100:src/st/rno0/unk_4F968.c:177: `D_us_80183320' undeclared (first use this function)
101:src/st/rno0/unk_4F968.c:205: `D_us_8018332C' undeclared (first use this function)
102:src/st/rno0/unk_4F968.c:208: structure has no member named `unkAB'
103:src/st/rno0/unk_4F968.c:227: structure has no member named `unkAB'
104:src/st/rno0/unk_4F968.c:245: structure has no member named `unkAB'
105:src/st/rno0/unk_4F968.c:246: structure has no member named `unkAB'
106-[91/361] psx cc src/st/rno3/stage_data.c
107-[92/361] psx cc src/st/rnz0/gen/e_laydef.c

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
extern Point16 D_us_80183310[];
extern s16 D_us_8018332C[];

void func_us_801D15C0(Entity* self) {
    Collider collider;
    s32 sp50;
    s32 sp54;
    s32 sp58;
    s16 sp20;
    s16 sp22;
    s32 stepResult;
    s32 stepResult2;
    Entity* entity;
    Primitive* prim;
    s16 angle;
    u16 palette;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180BDC);
        self->animCurFrame = 0xB;
        self->zPriority = 0x70;
        self->hitboxWidth = 7;
        self->hitboxHeight = 7;
        self->hitboxOffX = -3;
        self->drawFlags |= 4;
        prim = g_api_AllocPrimitives(PRIM_GT4, 1);
        if (prim != (Primitive*)-1) {
            self->primIndex = (s32)prim;
            self->ext.prim = prim;
            self->flags |= 0x800000;
            prim->tpage = 0x13;
            prim->clut = 0x232;
            prim->u3 = 0x60;
            prim->u2 = 0x60;
            prim->v2 = 0x68;
            prim->v0 = 0x68;
            prim->priority = 0x6F;
            prim->drawMode = 2;
            prim->u1 = 0x80;
            prim->u0 = 0x80;
            prim->v3 = 0x80;
            prim->v1 = 0x80;
            self->ext.reboundStone.stoneAngle = 0x400;
        } else {
            DestroyEntity(self);
            return;
        }
        break;

    case 19:
        if (self->step_s != 0) {
            prim = self->ext.prim;
            self->ext.reboundStone.unkAB = 1;
            self->animCurFrame = 0;
            prim->drawMode |= 8;
        } else {
            self->step_s += 1;
        }
        break;

    case 20:
        switch (self->step_s) {
        case 0:
            stepResult = StepTowards(&self->ext.reboundStone.stoneAngle, 0x600, 0x10);
            stepResult += StepTowards(&self->rotate, 0x300, 0x20);
            if (stepResult == 2) {
                self->step_s += 1;
            }
            break;

        case 1:
            stepResult = StepTowards(&self->ext.reboundStone.stoneAngle, 0x500, 0x18);
            stepResult += StepTowards(&self->rotate, 0x100, 0x30);
            if (AnimateEntity(D_us_80183310, self) == 0) {
                if (stepResult == 2) {
                    self->ext.reboundStone.unkA4 = 0x40;
                    PlaySfxPositional(0x77B);
                    self->step_s += 1;
                }
            }
            break;

        case 2:
            if (!(g_Timer & 3)) {
                entity = AllocEntity(&g_Entities_160[0], &g_Entities_160[0] + 0x1780);
                if (entity != NULL) {
                    CreateEntityFromEntity(0x45, self, entity);
                    entity->facingLeft = self->facingLeft;
                    if (self->facingLeft != 0) {
                        entity->posX.i.hi += 0xC;
                    } else {
                        entity->posX.i.hi -= 0xC;
                    }
                    entity->posY.i.hi += 2;
                }
            }
            self->ext.reboundStone.unkA4 -= 1;
            if (self->ext.reboundStone.unkA4 == 0) {
                self->pose = 0;
                self->poseTimer = 0;
                self->step_s += 1;
            }
            break;

        case 3:
            stepResult = StepTowards(&self->ext.reboundStone.stoneAngle, 0x400, 0x10);
            stepResult += StepTowards(&self->rotate, 0, 0x20);
            if (AnimateEntity(D_us_80183320, self) == 0) {
                if (stepResult == 2) {
                    self->step = 0x15;
                }
            }
            break;
        }
        break;

    case 16:
    case 17:
    case 18:
        if (self->step_s == 0) {
            if (StepTowards(&self->ext.reboundStone.stoneAngle, 0x500, 8) != 0) {
                self->step_s += 1;
            }
        } else {
            if (StepTowards(&self->ext.reboundStone.stoneAngle, 0x400, 8) != 0) {
                self->step_s = 0;
            }
        }
        break;

    case 22:
        switch (self->step_s) {
        case 0:
            StepTowards(&self->ext.reboundStone.stoneAngle, 0x400, 8);
            StepTowards(&self->rotate, 0x200, 0x10);
            AnimateEntity(D_us_8018332C, self);
            g_api_CheckCollision(self->posX.i.hi, self->posY.i.hi + 8, &collider, 0);
            if (collider.effects & 1) {
                self->ext.reboundStone.unkAB = 1;
                PlaySfxPositional(0x653);
                self->step_s += 1;
            }
            break;

        case 1:
            entity = AllocEntity(&g_Entities_224[0], &g_Entities_224[0] + 0x1780);
            if (entity != NULL) {
                CreateEntityFromEntity(2, self, entity);
                entity->params = 3;
            }
            DestroyEntity(self);
            return;
        }
        break;
    }

    /* Common post-switch logic: update facing, draw primitive, spawn water drops */
    self->ext.reboundStone.unkAB = 0;
    self->animCurFrame = 0xB;
    if (!(g_Timer & 0x7F)) {
        entity = AllocEntity(&g_Entities_224[0], &g_Entities_224[0] + 0x1780);
        if (entity != NULL) {
            PlaySfxPositional(0x77A);
            CreateEntityFromEntity(0x46, self, entity);
            entity->facingLeft = self->facingLeft;
            if (self->facingLeft != 0) {
                entity->posX.i.hi += 0x14;
            } else {
                entity->posX.i.hi -= 0x14;
            }
            entity->posY.i.hi += 0x14;
        }
    }

    /* Update facing and draw the stone primitive */
    self->facingLeft = self->ext.reboundStone.unkAB;
    if (self->ext.reboundStone.unkAB == 0) {
        sp50 = self->posX.val;
        sp54 = self->posY.val;
        if (self->facingLeft != 0) {
            sp54 += 0x10;
        } else {
            sp54 -= 0x10;
        }
        angle = self->ext.reboundStone.stoneAngle;
        func_801CD78C_801CEB40(&sp50, -0xC, angle, &sp50);
        func_801CD78C_801CEB40(&sp50, 0x18, angle, &sp58);
        sp20 = 0xC;
        sp22 = 0xC;
        prim = self->ext.prim;
        func_us_801D2424_from_are(&sp50, angle, &sp20, &sp58, angle, &sp20, prim);
        palette = self->palette;
        if (palette & 0x8000) {
            prim->clut = palette & 0xFFF;
        } else {
            prim->clut = 0x232;
        }
        prim->drawMode = 2;
        func_801CD78C_801CEB40(&sp50, 0x16, (s16)(angle - 0x100), &self->posX.val);
    }
}