/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801D0CFC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   verdict: BUILD FAILED:
113:src/st/rno0/unk_4F968.c:67: `D_us_801832E4' undeclared (first use this function)
114:src/st/rno0/unk_4F968.c:67: (Each undeclared identifier is reported only once
115:src/st/rno0/unk_4F968.c:67: for each function it appears in.)
116:src/st/rno0/unk_4F968.c:86: structure has no member named `ext'
117:src/st/rno0/unk_4F968.c:87: structure has no member named `ext'
118:src/st/rno0/u

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
extern u8 D_us_801832E4[]; /* retained ST/RNO0 data asm/us/st/rno0/data/32B4.data.s, size 0x20 */

void func_us_801D0CFC(Entity* self) {
    Collider collider;
    s16 sp40;
    s16 sp42;
    Entity* child;
    Entity* child2;
    Primitive* prim;
    s32 i;
    s16 var_v0;
    u16 step;
    u16 step_s;

    step = self->step;
    self->animCurFrame = 0xD;

    switch (step) {
    case 0:
        InitializeEntity(g_EInitGorgon);
        self->animCurFrame = 0xD;
        self->drawFlags = 4;
        self->zPriority = 0x73;
        CreateEntityFromEntity(0x41, self, self + 0xBC);
        self->ext.venusWeedSpike.flower = self + 0x178;
        self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = 0x10;
        CreateEntityFromEntity(0x41, self, self + 0x178);
        self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = 0x11;

        prim = g_api_AllocPrimitives(PRIM_GT4, 4);
        if (prim == -1) {
            DestroyEntity(self);
            return;
        }

        self->primIndex = prim;
        self->ext.venusWeedSpike.firstPart = (Entity*)g_PrimBuf;
        self->flags |= 0x800000;

        if (self->ext.venusWeedSpike.firstPart != NULL) {
            u8* data = (u8*)&D_us_801832E4;
            prim = (Primitive*)self->ext.venusWeedSpike.firstPart;
            while (prim != NULL) {
                prim->tpage = 0x13;
                prim->clut = 0x232;
                prim->u0 = data[0];
                prim->v0 = data[1];
                prim->u1 = data[2];
                prim->v1 = data[3];
                prim->u2 = data[4];
                prim->v2 = data[5];
                prim->u3 = data[6];
                prim->v3 = data[7];
                prim->drawMode = 8;
                data += 8;
                prim = prim->next;
            }
        }

        self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.clutOffset = 0x40;
        self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 = 0;
        self->step = 0x15;
        break;

    case 16:
    case 17:
    case 18:
        if (self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 == 0) {
            child = self + 0xBC;
            child2 = self + 0x178;
        } else {
            child = self + 0x178;
            child2 = self + 0xBC;
        }

        step_s = self->step;
        switch (step_s) {
        case 17:
            sp40 = 0xA;
            sp42 = 0x40;
            func_us_801CF7D0(child, child2, &sp40);
            break;
        case 16:
            sp40 = 8;
            sp42 = 0x20;
            func_us_801CF7D0(child, child2, &sp40);
            break;
        case 18:
            func_us_801CFB20(child, child2);
            break;
        }

        func_us_801CF24C(self, child2, func_us_801CF380(self, child, (Primitive*)self->ext.venusWeedSpike.firstPart));
        func_us_801CFD70(2);

        if (func_us_801CF7D0 != 0) {
            self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 ^= 1;
        }

        self->rotate = (s16)((s16)self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 / 2);
        break;

    case 20:
    case 21:
        self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 = 0;
        if (self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 == 0) {
            child = self + 0xBC;
            child2 = self + 0x178;
        } else {
            child = self + 0x178;
            child2 = self + 0xBC;
        }

        prim = (Primitive*)self->ext.venusWeedSpike.firstPart;
        if (self->step == 0x15) {
            func_us_801CF24C(self, child2, func_us_801CF24C(self, child, prim));
        } else {
            func_us_801CF380(self, child2, func_us_801CF380(self, child, prim));
        }

        func_us_801CFD70(2);
        break;

    case 19:
        if (self->step_s == 0) {
            self->step_s++;
        } else {
            prim = (Primitive*)self->ext.venusWeedSpike.firstPart;
            self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 = 1;
            self->animCurFrame = 0;
            while (prim != NULL) {
                prim->drawMode |= 8;
                prim = prim->next;
            }
        }
        break;

    case 22:
        step_s = self->step_s;
        switch (step_s) {
        case 0:
            child = self + 0xBC;
            prim = (Primitive*)self->ext.venusWeedSpike.firstPart;
            for (i = 0; i < 2; i++) {
                if ((s16)child->ext.venusWeedSpike.firstPart != 0) {
                    prim = func_us_801CF380(self, child, prim);
                } else {
                    prim = func_us_801CF24C(self, child, prim);
                }
                child = self + 0x178;
            }
            func_us_801CFD70(2);
            g_api_CheckCollision(self->posX.i.hi, self->posY.i.hi + 0x18, &collider, 0);
            if (collider.unk0 & 1) {
                PlaySfxPositional(0x653);
                self->step_s++;
            }
            break;

        case 1:
            if (self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 != 0) {
                self->step_s++;
            }
            break;

        case 2:
            self->animCurFrame = 0;
            child = AllocEntity(&g_Entities_224[0], &g_Entities_224[0] + 0x1780);
            if (child != NULL) {
                CreateEntityFromEntity(2, self, child);
                child->params = 3;
                child->zPriority = self->zPriority;
            }
            self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 = 1;
            self->step_s++;
            break;

        case 3:
            prim = (Primitive*)self->ext.venusWeedSpike.firstPart;
            while (prim != NULL) {
                if (!(prim->drawMode & 8)) {
                    child = AllocEntity(&g_Entities_224[0], &g_Entities_224[0] + 0x1780);
                    if (child != NULL) {
                        CreateEntityFromCurrentEntity(2, child);
                        child->posX.i.hi = prim->x0;
                        child->posY.i.hi = prim->y0;
                        child->params = 1;
                    }
                    prim->drawMode = 8;
                }
                prim = prim->next;
            }
            DestroyEntity(self);
            return;
        }
        break;
    }

    self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = self->facingLeft;
    self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = self->facingLeft;
    self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = self->facingLeft;

    if (self->ext.venusWeedSpike.firstPart->ext.venusWeedFlower.unk93 == 0) {
        self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = self->posX.i.hi;
        self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = self->posY.i.hi;
        self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = self->posX.i.hi;
        self->ext.venusWeedSpike.flower->ext.venusWeedFlower.unk93 = self->posY.i.hi - 0xD;
    }
}