/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801C0FE8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
66:src/boss/bo6/us_3E79C.c:43: `D_us_80181E9C' undeclared (first use this function)
67:src/boss/bo6/us_3E79C.c:43: (Each undeclared identifier is reported only once
68:src/boss/bo6/us_3E79C.c:43: for each function it appears in.)
69:src/boss/bo6/us_3E79C.c:50: `RIC_zPriority' undeclared (first use this function)
70-[65/240] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build

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
void func_us_801C0FE8(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 angle;
    s32 temp;
    u16 step;
    u16 params;
    s32 offsetX;
    s32 offsetY;
    s32 randVal;
    Entity* newEntity;

    step = self->step;
    params = self->params;

    switch (step) {
    case 0:
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 1);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        prim = &g_PrimBuf[primIndex];
        prim->clut = 0x252;
        prim->tpage = 0x12;
        offsetX = D_us_80181E9C[params * 2] - 0x10;
        offsetY = D_us_80181E9C[params * 2 + 1] - 0x10;
        prim->u0 = prim->u2 = D_us_80181E9C[params * 2] - 2;
        prim->u1 = prim->u3 = D_us_80181E9C[params * 2] + 2;
        prim->v0 = prim->v1 = D_us_80181E9C[params * 2 + 1] - 2;
        prim->v2 = prim->v3 = D_us_80181E9C[params * 2 + 1] + 2;
        prim->drawMode = 2;
        prim->priority = RIC_zPriority + 4;
        self->posX.i.hi += offsetX;
        self->posY.i.hi += offsetY;
        angle = ratan2(-offsetY, offsetX);
        self->ext.factory.unk7E = angle - 0x40 + (rand() & 0x7F);
        self->ext.factory.unk7C = 8;
        self->flags = 0x10800000;
        self->step++;
        break;
    case 1:
        self->ext.factory.unk7C--;
        if (self->ext.factory.unk7C == 0) {
            self->ext.factory.unk7C = 0x10;
            temp = rcos(self->ext.factory.unk7E);
            self->velocityX = (temp << 5) + (rand() & 0xF);
            temp = rsin(self->ext.factory.unk7E);
            self->velocityY = -((temp << 5) + (rand() & 0xF));
            self->step++;
        }
        break;
    case 2:
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        self->ext.factory.unk7C--;
        if (self->ext.factory.unk7C == 0) {
            BO6_RicCreateEntFactoryFromEntity(self, 0x4A, 0);
            self->velocityY = (rand() & 0x7FFF) + 0xFFFF0000;
            self->ext.factory.unk7C = 1;
            self->velocityX >>= 2;
            self->step++;
        }
        break;
    case 3:
        if (!(self->ext.factory.unk7C & 3)) {
            newEntity = BO6_RicGetFreeEntity(0x50, 0x8F);
            if (newEntity != NULL) {
                DestroyEntity(newEntity);
                newEntity->entityId = 0x43;
                newEntity->params = 0x100;
                newEntity->ext.factory.parent = self->ext.factory.parent;
                newEntity->posX.val = self->posX.val;
                newEntity->posY.val = self->posY.val;
            }
        }
        self->ext.factory.unk7C++;
        self->velocityY += 0xC00;
        self->posY.val += self->velocityY;
        self->posX.val += self->velocityX;
        self->flags &= 0xEFFFFFFF;
        break;
    }

    prim = &g_PrimBuf[self->primIndex];
    prim->x0 = prim->x2 = self->posX.i.hi - 2;
    prim->x1 = prim->x3 = self->posX.i.hi + 2;
    prim->y0 = prim->y1 = self->posY.i.hi - 2;
    prim->y2 = prim->y3 = self->posY.i.hi + 2;
}