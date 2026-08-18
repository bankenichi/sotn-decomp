/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801C9DE8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
 union has no member named `unk00'
68:src/boss/bo6/us_3E79C.c:1189: union has no member named `unk00'
69:src/boss/bo6/us_3E79C.c:1205: union has no member named `unk00'
70:src/boss/bo6/us_3E79C.c:1245: structure has no member named `unk8'
71:src/boss/bo6/us_3E79C.c:1246: structure has no member named `unk20'
72:src/boss/bo6/us_3E79C.c:1247: structure has no member named `unkA'
73:src

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
void func_us_801C9DE8(Entity* self) {
        s16 temp;
        u16 tpage;
        s32 primIndex;
        s32 step;
        s32 extVal;
    Primitive* prim;
    s32 i;
    s16 angle;
    s16 radius;
    s16 x0, y0, x1, y1, x2, y2, x3, y3;
    s16 u0, v0, u1, v1, u2, v2, u3, v3;
    s16 sinVal, cosVal;

    step = self->step;
    switch (step) {
    case 0:
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 0x10);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            g_Ric.unk4E = 1;
            return;
        }
        self->flags = 0x10800000;
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; i < 0x10; i++) {
            prim->priority = 0xC2;
            prim->drawMode = 8;
            prim = prim->next;
        }
        self->step++;
        /* fallthrough */
    case 1:
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; i < 0x10; i++) {
            prim->drawMode &= 0xFFF7;
            prim = prim->next;
        }
        self->step++;
        /* fallthrough */
    case 2:
        extVal = self->ext.unk00;
        extVal++;
        self->ext.unk00 = extVal;
        if ((s16)extVal >= 0x18) {
            self->step++;
        }
        /* fallthrough */
    case 3:
        if (self->step == 3) {
            g_Ric.unk4E = 1;
            DestroyEntity(self);
            return;
        }
        break;
    default:
        return;
    }

    extVal = self->ext.unk00;
    if (extVal == 0) {
        return;
    }

    tpage = 0x100;
    if (g_CurrentBuffer == g_GpuBuffers) {
        tpage = 0x104;
    }

    prim = &g_PrimBuf[self->primIndex];
    for (i = 0; i < 0x10; i++) {
        angle = i * 0x100;
        sinVal = rsin(angle);
        cosVal = rcos(angle);
        radius = extVal * 8;
        temp = 0;
        if (extVal >= 4) {
            temp = (extVal - 4) * 8;
        }

        x0 = ((cosVal * radius) >> 12) + 0x80;
        y0 = ((cosVal * temp) >> 12) + 0x80;
        x2 = ((sinVal * temp) >> 12) + 0x78;
        y2 = ((sinVal * radius) >> 12) + 0x78;

        if (x0 < 0) x0 = 0;
        else if (x0 >= 0x100) x0 = 0xFF;
        if (y0 < 0) y0 = 0;
        else if (y0 >= 0x100) y0 = 0xFF;
        if (x2 < 0) x2 = 0;
        else if (x2 >= 0xF1) x2 = 0xF0;
        if (y2 < 0) y2 = 0;
        else if (y2 >= 0xF1) y2 = 0xF0;

        prim->x0 = x0;
        prim->x2 = y0;
        prim->y0 = x2;
        prim->y2 = y2;

        prim->u0 = ~(u8)prim->unk8;
        prim->u2 = ~(u8)prim->unk20;
        prim->v0 = -0x10 - (u8)prim->unkA;
        prim->v2 = -0x10 - (u8)prim->unk22;

        sinVal = rsin(tpage);
        cosVal = rcos(tpage);

        x1 = ((cosVal * radius) >> 12) + 0x80;
        y1 = ((cosVal * temp) >> 12) + 0x80;
        x3 = ((sinVal * temp) >> 12) + 0x78;
        y3 = ((sinVal * radius) >> 12) + 0x78;

        if (x1 < 0) x1 = 0;
        else if (x1 >= 0x100) x1 = 0xFF;
        if (y1 < 0) y1 = 0;
        else if (y1 >= 0x100) y1 = 0xFF;
        if (x3 < 0) x3 = 0;
        else if (x3 >= 0xF1) x3 = 0xF0;
        if (y3 < 0) y3 = 0;
        else if (y3 >= 0xF1) y3 = 0xF0;

        prim->x1 = x1;
        prim->x3 = y1;
        prim->y1 = x3;
        prim->y3 = y3;

        prim->tpage = tpage;
        prim->u1 = ~(u8)prim->unk14;
        prim->u3 = ~(u8)prim->unk2C;
        prim->v1 = -0x10 - (u8)prim->unk16;
        prim->v3 = -0x10 - (u8)prim->unk2E;

        prim = prim->next;
        tpage += 0x100;
    }
}