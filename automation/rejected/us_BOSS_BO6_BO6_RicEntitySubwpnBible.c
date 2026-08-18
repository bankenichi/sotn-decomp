/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntitySubwpnBible
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
64:src/boss/bo6/us_3E79C.c:1281: `RIC_zPriority' undeclared (first use this function)
65:src/boss/bo6/us_3E79C.c:1281: (Each undeclared identifier is reported only once
66:src/boss/bo6/us_3E79C.c:1281: for each function it appears in.)
67:src/boss/bo6/us_3E79C.c:1352: `RIC_posX_i_hi' undeclared (first use this function)
68:src/boss/bo6/us_3E79C.c:1353: `RIC_posY_i_hi' undeclared (fir

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
void BO6_RicEntitySubwpnBible(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s16 angle1;
    s16 angle2;
    s32 sin1;
    s32 cos1;
    s32 sin2;
    s32 cos2;
    s32 radius;
    s32 x;
    s32 y;
    s32 temp;
    s16 unk86;
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s32 flags;
    s16 facing;
    s16 primX;
    s16 primY;

    switch (self->step) {
    case 0:
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 1);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags = 0x10800000;
        prim = &g_PrimBuf[self->primIndex];
        prim->tpage = 0x1E;
        prim->clut = 0x17F;
        prim->u0 = 0x98;
        prim->u2 = 0x98;
        prim->v0 = 0xD8;
        prim->v1 = 0xD8;
        prim->u1 = 0xA8;
        prim->u3 = 0xA8;
        prim->v2 = 0xF0;
        prim->v3 = 0xF0;
        prim->drawMode = 8;
        prim->priority = RIC_zPriority + 1;
        if (self->facingLeft) {
            self->ext.factory.unk84 = 0x20;
        } else {
            self->ext.factory.unk84 = -0x20;
        }
        self->hitboxWidth = 6;
        self->hitboxHeight = 6;
        self->step++;
        break;
    case 1:
        prim = &g_PrimBuf[self->primIndex];
        prim->drawMode &= 0xFFF7;
        self->ext.factory.unk86++;
        self->step++;
        /* fallthrough */
    case 2:
        self->ext.factory.unk7E++;
        self->ext.factory.unk7C++;
        if (self->ext.factory.unk7E >= 0x30) {
            self->step++;
        }
        break;
    case 3:
        self->ext.factory.unk7C++;
        if (self->ext.factory.unk7C >= 0x12C) {
            self->flags &= 0xEFFFFFFF;
            if (self->facingLeft) {
                self->velocityX = 0xFFF40000;
            } else {
                self->velocityX = 0xC0000;
            }
            self->velocityY = -0xC0000;
            self->ext.factory.unk86++;
            self->step++;
        }
        break;
    }

    unk86 = self->ext.factory.unk86;
    switch (unk86) {
    case 1:
        angle1 = self->ext.factory.unk80;
        sin1 = rsin(angle1);
        cos1 = rcos(angle1);
        radius = self->ext.factory.unk7E;
        x = (sin1 * radius) >> 12;
        y = (cos1 * radius) >> 12;
        temp = (cos1 * x) + (sin1 * y);
        x = (cos1 * x) - (sin1 * y);
        y = temp;
        angle2 = self->ext.factory.unk82;
        sin2 = rsin(angle2);
        cos2 = rcos(angle2);
        temp = (cos2 * x) + (sin2 * y);
        y = (cos2 * y) - (sin2 * x);
        x = temp;
        if (self->facingLeft) {
            self->ext.factory.unk80 = (self->ext.factory.unk80 + 0x80) & 0xFFF;
        } else {
            self->ext.factory.unk80 = (self->ext.factory.unk80 - 0x80) & 0xFFF;
        }
        self->ext.factory.unk82 += self->ext.factory.unk84;
        if (self->ext.factory.unk82 < 0) {
            temp = -self->ext.factory.unk82;
        } else {
            temp = self->ext.factory.unk82;
        }
        if (temp >= 0x200) {
            self->ext.factory.unk84 = -self->ext.factory.unk84;
        }
        self->posX.i.hi = RIC_posX_i_hi + (x >> 12);
        self->posY.i.hi = RIC_posY_i_hi + (y >> 12);
        if (y < 0) {
            self->zPriority = RIC_zPriority + 2;
        } else {
            self->zPriority = RIC_zPriority - 2;
        }
        break;
    case 2:
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        self->velocityY += 0xFFFE0000;
        break;
    }

    if (self->ext.factory.unk86 != 0) {
        prim = &g_PrimBuf[self->primIndex];
        primX = self->posX.i.hi;
        primY = self->posY.i.hi;
        prim->x0 = primX - 8;
        prim->x1 = primX + 8;
        prim->x2 = primX - 8;
        prim->x3 = primX + 8;
        prim->y0 = primY - 0xC;
        prim->y1 = primY - 0xC;
        prim->y2 = primY + 0xC;
        prim->y3 = primY + 0xC;
        prim->priority = self->zPriority;
        BO6_RicCreateEntFactoryFromEntity(self, 0x3E, 0, prim);
        if (g_GameTimer == ((g_GameTimer / 10) * 10)) {
            g_api_PlaySfx(0x60C);
        }
    }
}