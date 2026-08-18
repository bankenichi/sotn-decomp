/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801D068C
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   verdict: BUILD FAILED:
4F968.c:99: structure has no member named `unkAA'
121:src/st/rno0/unk_4F968.c:101: structure has no member named `unkAA'
122:src/st/rno0/unk_4F968.c:112: structure has no member named `unkAB'
123:src/st/rno0/unk_4F968.c:113: structure has no member named `unkA8'
124:src/st/rno0/unk_4F968.c:141: structure has no member named `prim'
125:src/st/rno0/unk_4F968.c:144: structure has no mem

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
void func_us_801D068C(Entity* self) {
    Collider sp18;
    s16 sp48;
    s16 sp4A;
    s32 var_s5;
    Entity* var_s3;
    Entity* var_s4;
    u8* var_s0;
    u8* var_s1;
    Primitive* prim;
    s32 i;
    Entity* newEntity;
    u16 step_s;

    var_s5 = 0;
    self->animCurFrame = 9;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitGorgon);
        self->animCurFrame = 9;
        self->zPriority = 0x70;
        self->hitboxWidth = 8;
        self->hitboxHeight = 10;
        self->hitboxOffX = -8;
        self->hitboxOffY = 8;
        self->zPriority = (self->params * 4) + 0x70;
        CreateEntityFromEntity(0x41, self, self + 0xBC);
        self->ext.venusWeedTendril.timer = 0;
        CreateEntityFromEntity(0x41, self, self + 0x178);
        self->ext.venusWeedFlower.entity = 1;
        i = g_api_AllocPrimitives(PRIM_GT4, 6);
        if (i != -1) {
            prim = &g_PrimBuf[i];
            self->primIndex = i;
            self->ext.venusWeedTendril.prim = prim;
            self->flags |= 0x800000;
            for (i = 0; i < 6; i++) {
                prim->tpage = 0x13;
                prim->clut = 0x232;
                prim->priority = 0x72;
                prim->u0 = D_us_801832B4[i * 8 + 0];
                prim->v0 = D_us_801832B4[i * 8 + 1];
                prim->u1 = D_us_801832B4[i * 8 + 2];
                prim->v1 = D_us_801832B4[i * 8 + 3];
                prim->u2 = D_us_801832B4[i * 8 + 4];
                prim->v2 = D_us_801832B4[i * 8 + 5];
                prim->u3 = D_us_801832B4[i * 8 + 6];
                prim->v3 = D_us_801832B4[i * 8 + 7];
                prim = prim->next;
            }
            self->ext.venusWeedFlower.clutOffset = 0x100;
            self->ext.venusWeedFlower.unk92 = 0x100;
            self->ext.venusWeedTendril.spikeStartTimeOffsetIndex = 0x180;
            self->ext.venusWeedTendril.unk93 = -0x80;
            self->ext.venusWeedFlower.unk93 = 0x180;
            self->ext.venusWeedFlower.unk94 = -0x80;
            self->step = 0x15;
        }
        /* fallthrough */
    default:
        self->ext.venusWeedTendril.targetX = self->facingLeft;
        self->ext.venusWeedFlower.entity = self->facingLeft;
        self->ext.venusWeedFlower.unk94 = self->facingLeft;
        if (self->ext.venusWeedFlower.unkAB == 0) {
            s32 var_a2_2 = 0x330;
            if ((self->step - 0x10) < 2) {
                var_a2_2 = 0x360;
            }
            func_801CD78C_801CEB40(self, 0x22, var_a2_2, self + 0x234);
            self->ext.venusWeedFlower.unkAA = self->posX.i.hi;
            if (self->facingLeft) {
                self->ext.venusWeedFlower.unkAA = self->posX.i.hi - 1;
            } else {
                self->ext.venusWeedFlower.unkAA = self->posX.i.hi + 1;
            }
            (self + 0x524)->posY.i.hi = self->posY.i.hi + 6;
        }
        break;

    case 16:
    case 17:
    case 18:
    case 20:
    case 21:
        self->ext.venusWeedFlower.unkAB = 0;
        if (self->ext.venusWeedFlower.unkA8 == 0) {
            var_s3 = self + 0xBC;
            var_s0 = &self->ext.venusWeedTendril.spikeStartTimeOffsetIndex;
            var_s4 = self + 0x178;
            var_s1 = &self->ext.venusWeedFlower.unk93;
        } else {
            var_s3 = self + 0x178;
            var_s0 = &self->ext.venusWeedFlower.unk93;
            var_s4 = self + 0xBC;
            var_s1 = &self->ext.venusWeedTendril.spikeStartTimeOffsetIndex;
        }

        switch (self->step) {
        case 17:
            sp48 = 0xA;
            sp4A = 0x10;
            var_s5 = func_us_801CF64C(var_s3, var_s0, var_s4, var_s1, &sp48);
            break;
        case 16:
            sp48 = 8;
            sp4A = 8;
            var_s5 = func_us_801CF64C(var_s3, var_s0, var_s4, var_s1, &sp48);
            break;
        case 18:
            var_s5 = func_us_801CF968(var_s3, var_s0, var_s4, var_s1);
            break;
        }

        func_us_801CF08C(self, var_s4, var_s1, func_us_801CEEB4(var_s3, self, var_s0 + 4, self->ext.venusWeedTendril.prim));
        func_us_801CFD70(3);
        if (var_s5 != 0) {
            self->ext.venusWeedFlower.unkAE = 1;
            self->ext.venusWeedFlower.unkAA = 0;
            self->ext.venusWeedFlower.unkA8 ^= 1;
        } else {
            self->ext.venusWeedFlower.unkAE = 0;
        }
        break;

    case 19:
        if (self->step_s != 0) {
            prim = self->ext.venusWeedTendril.prim;
            self->ext.venusWeedFlower.unkAB = 1;
            self->animCurFrame = 0;
            while (prim != NULL) {
                prim->drawMode |= 8;
                prim = prim->next;
            }
        } else {
            self->step_s++;
        }
        break;

    case 22:
        if (self->ext.venusWeedFlower.unkA8 == 0) {
            var_s3 = self + 0xBC;
            var_s0 = &self->ext.venusWeedTendril.spikeStartTimeOffsetIndex;
            var_s4 = self + 0x178;
            var_s1 = &self->ext.venusWeedFlower.unk93;
        } else {
            var_s3 = self + 0x178;
            var_s0 = &self->ext.venusWeedFlower.unk93;
            var_s4 = self + 0xBC;
            var_s1 = &self->ext.venusWeedTendril.spikeStartTimeOffsetIndex;
        }

        step_s = self->step_s;
        switch (step_s) {
        case 0:
            self->ext.venusWeedFlower.unkAB = 0;
            StepTowards(var_s0 + 2, -0x600, 0x30);
            StepTowards(var_s0 + 4, -0x400, 0x30);
            StepTowards(var_s1, 0x400, 0x50);
            StepTowards(var_s1 + 2, -0x300, 0x38);
            StepTowards(var_s1 + 4, -0x500, 0x38);
            func_us_801CF08C(self, var_s4, var_s1, func_us_801CEEB4(var_s3, self, var_s0 + 4, self->ext.venusWeedTendril.prim));
            func_us_801CFD70(3);
            g_api_CheckCollision(self->posX.i.hi, self->posY.i.hi + 0x18, &sp18, 0);
            if (sp18.unk0 & 1) {
                g_api_func_80102CD8(1);
                PlaySfxPositional(0x654);
                self->step_s++;
            }
            break;
        case 1:
            if (self->ext.venusWeedFlower.unkAC != 0) {
                self->step_s++;
            }
            break;
        case 2:
            self->animCurFrame = 0;
            newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[23]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(2, self, newEntity);
                newEntity->params = 3;
                newEntity->zPriority = self->zPriority;
            }
            self->step_s++;
            break;
        case 3:
            prim = self->ext.venusWeedTendril.prim;
            if (prim != NULL) {
                while (prim != NULL) {
                    if (!(prim->drawMode & 8)) {
                        newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[23]);
                        if (newEntity != NULL) {
                            CreateEntityFromCurrentEntity(self, newEntity);
                            newEntity->posX.i.hi = prim->x0;
                            newEntity->posY.i.hi = prim->y0;
                            newEntity->params = 1;
                        }
                    }
                    prim->drawMode |= 8;
                    prim = prim->next;
                }
            }
            DestroyEntity(self);
            return;
        }
        break;
    }
}