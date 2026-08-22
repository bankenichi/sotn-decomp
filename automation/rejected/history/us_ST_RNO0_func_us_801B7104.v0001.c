/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801B7104
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/func_us_801b7104.c
   verdict: BUILD FAILED:
5:src/st/rno0/func_us_801b7104.c:25: `RNO0_EInitCommon' undeclared (first use this function)
6:src/st/rno0/func_us_801b7104.c:25: (Each undeclared identifier is reported only once
7:src/st/rno0/func_us_801b7104.c:25: for each function it appears in.)
8:src/st/rno0/func_us_801b7104.c:36: `D_us_80180FDC' undeclared (first use this function)
9:src/st/rno0/func_us_801b7104.c:53: `D_us_80180FE8' undeclared (first use this function)
10-[4/159] psx cc src/weapon/w_019.c
11-[5/159] psx cc src/weapon/w_014.c

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
void func_us_801B7104(Entity* self) {
    Primitive* prim;
    u8* dataPtr;
    s16* coordData;
    s16 primIndex;
    s16 step;
    s16 params;
    s16 posX;
    s16 posY;
    s16 i;

    step = self->step;
    params = self->params;

    if (step == 0) {
        InitializeEntity(RNO0_EInitCommon);
        self->animCurFrame = 0;
        self->zPriority = 0x9E;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 3);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->primIndex = primIndex;
        self->flags |= 0x800000;
        prim = &g_PrimBuf[primIndex];
        dataPtr = (u8*)D_us_80180FDC;
        while (prim != NULL) {
            prim->tpage = 0xF;
            prim->clut = 0x3E;
            prim->u0 = prim->u2 = dataPtr[0];
            prim->u1 = prim->u3 = dataPtr[1];
            prim->v0 = prim->v1 = dataPtr[2];
            prim->v2 = prim->v3 = dataPtr[3];
            prim->drawMode = 2;
            prim->priority = self->zPriority + 1;
            prim = prim->next;
            dataPtr += 4;
        }
        self->step = 3;
    }

    if (step != 2) {
        coordData = (s16*)((u8*)D_us_80180FE8 + (((params * 2) + 1) * 0x18));
        prim = &g_PrimBuf[self->primIndex];
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;
        while (prim != NULL) {
            prim->x0 = prim->x2 = posX + coordData[0];
            prim->x1 = prim->x3 = posX + coordData[2];
            prim->y0 = prim->y1 = posY + coordData[4];
            prim->y2 = prim->y3 = posY + coordData[6];
            prim = prim->next;
            coordData += 8;
        }
    }
}