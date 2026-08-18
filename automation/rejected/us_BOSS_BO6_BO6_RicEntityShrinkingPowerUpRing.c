/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntityShrinkingPowerUpRing
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: quality reject: 5 raw byte-pointer cast(s) like `*(u16*)((u8*)p + N)`; use the real struct and named members instead

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
void BO6_RicEntityShrinkingPowerUpRing(Entity *self) {
        s16 radius;
        s16 baseAngle;
        s32 temp;
        s16 tableOffset;
        u16 unk8A;
        u16 unk7E;
        u16 primCount;
        u16 primIndexCalc;
        s32 divResult;
    Primitive *prim;
    Primitive *prim2;
    s16 i;
    u16 angle;
    s16 primIndex;
    s16 step;
    s16 offsetX, offsetY;
    s16 scaleX, scaleY;
    u16 unk80, unk82, unk84, unk86, unk88;
    s16 xScale, yScale;
    s16 r, g, b;

    /* Access table of parameters: 12 bytes per entry, index from self->params */
    tableOffset = ((self->params & 0x7F00) >> 8) * 12;
    unk8A = *(u16*)((char*)D_us_80181CAC + tableOffset + 10);
    offsetX = *(u16*)((char*)D_us_80181CAC + tableOffset + 4);
    scaleY = *(u16*)((char*)D_us_80181CAC + tableOffset + 6);
    xScale = *(u16*)((char*)D_us_80181CAC + tableOffset);
    yScale = *(u16*)((char*)D_us_80181CAC + tableOffset + 2);

    self->posX.i.hi = RIC_posX_i_hi;
    self->posY.i.hi = RIC_posY_i_hi;
    step = self->step;
    if (step == 1) {
        goto case_1;
    } else if (step < 2) {
        if (step == 0) {
            goto case_0;
        }
        goto cleanup;
    } else {
        if (step == 2) {
            goto case_2;
        } else if (step == 3) {
            goto case_3;
        } else {
            goto cleanup;
        }
    }

case_0:
    primCount = g_api_AllocPrimitives(PRIM_GT4, 0x20);
    self->primIndex = primCount;
    if (primCount == -1) {
        goto cleanup;
    }
    self->flags = 0x18800000;
    prim = &g_PrimBuf[self->primIndex];
    prim2 = prim;
    i = 0xF;
    do {
        prim = prim->next;
        i--;
    } while (i >= 0);

    i = 0;
    angle = 0;
    do {
        prim2->u0 = (rcos(angle) * 2 >> 8) + 0x20;
        i++;
        angle = i << 8;
        prim2->v0 = -(rsin(angle) * 2 >> 8) - 0x21;
        prim2->u1 = (rcos(i << 8) * 2 >> 8) + 0x20;
        prim2->v1 = -(rsin(i << 8) * 2 >> 8) - 0x21;
        prim->u3 = 0x20;
        prim->u2 = 0x20;
        prim->v3 = 0xDF;
        prim->v2 = 0xDF;
        /* Average UVs between the two primitives */
        prim->u0 = (prim2->u0 + prim->u2) >> 1;
        prim2->u2 = prim->u0;
        prim->v0 = (prim2->v0 + prim->v2) >> 1;
        prim2->v2 = prim->v0;
        prim->u1 = (prim2->u1 + prim->u3) >> 1;
        prim2->u3 = prim->u1;
        prim->v1 = (prim2->v1 + prim->v3) >> 1;
        prim2->v3 = prim->v1;
        prim2->tpage = 0x1A;
        prim->tpage = 0x1A;
        prim2->clut = 0x15F;
        prim->clut = 0x15F;
        prim2->priority = RIC_zPriority + 2;
        prim->priority = RIC_zPriority + 2;
        prim2->drawMode = 0x37;
        prim->drawMode = 0x37;
        prim2 = prim2->next;
        prim = prim->next;
    } while (i < 0x10);

    self->unk82 = 0x280;
    self->unk80 = 0x280;
    self->unk86 = 0x240;
    self->unk84 = 0x240;
    self->unk88 = 0xC0;
    self->unk8A = unk8A;
    self->step++;
    /* fall through to rendering code */

cleanup:
    prim2 = &g_PrimBuf[self->primIndex];
    prim = prim2;
    i = 0xF;
    do {
        prim = prim->next;
        i--;
    } while (i >= 0);
    i = 0;
    do {
        /* Scale and position the ring */
        prim->x0 = self->posX.i.hi + ((prim->u0 - 0x20) * self->unk80 / 256);
        prim->y0 = self->posY.i.hi + ((prim->v0 - 0xE0) * self->unk82 / 256);
        prim->x1 = self->posX.i.hi + ((prim->u1 - 0x20) * self->unk80 / 256);
        prim->y1 = self->posY.i.hi + ((prim->v1 - 0xE0) * self->unk82 / 256);
        /* Calculate next two points using rotation */
        prim2->x2 = self->posX.i.hi + (rcos((i + 1) << 8) * 2 / 256 * self->unk84);
        prim2->y2 = self->posY.i.hi - (rsin((i + 1) << 8) * 2 / 256 * self->unk86);
        prim2->x3 = self->posX.i.hi + (rcos((i + 2) << 8) * 2 / 256 * self->unk84);
        prim2->y3 = self->posY.i.hi - (rsin((i + 2) << 8) * 2 / 256 * self->unk86);
        /* Average positions between pairs of primitives */
        prim->x0 = (prim->x0 + prim2->x2) / 2;
        prim2->x0 = prim->x0;
        prim->y0 = (prim->y0 + prim2->y2) / 2;
        prim2->y0 = prim->y0;
        prim->x1 = (prim->x1 + prim2->x3) / 2;
        prim2->x1 = prim->x1;
        prim->y1 = (prim->y1 + prim2->y3) / 2;
        prim2->y1 = prim->y1;
        /* Calculate RGB based on sine wave */
        angle = i * scaleY;
        unk7E = self->unk7E;
        /* R component */
        temp = ((rsin(angle + unk7E) + 0x1000) >> 7) * self->unk88;
        divResult = temp / offsetX;
        prim->r2 = divResult;
        prim2->r0 = divResult;
        /* G component */
        temp = ((rsin(angle + (scaleY + unk7E)) + 0x1000) >> 7) * self->unk88;
        divResult = temp / xScale;
        prim->g2 = divResult;
        prim2->g0 = divResult;
        /* B component */
        temp = ((rsin(angle + (yScale + unk7E)) + 0x1000) >> 7) * self->unk88;
        divResult = temp / scaleY;
        prim->b2 = divResult;
        prim2->b0 = divResult;
        /* Next color components */
        temp = ((rsin(angle + (scaleY + unk7E)) + 0x1000) >> 7) * self->unk88;
        divResult = temp / offsetX;
        prim->r3 = divResult;
        prim2->r1 = divResult;
        temp = ((rsin(angle + (scaleY + (xScale + unk7E))) + 0x1000) >> 7) * self->unk88;
        divResult = temp / xScale;
        prim->g3 = divResult;
        prim2->g1 = divResult;
        temp = ((rsin(angle + (scaleY + (yScale + unk7E))) + 0x1000) >> 7) * self->unk88;
        divResult = temp / scaleY;
        prim->b3 = divResult;
        prim2->b1 = divResult;
        /* Zero out first set of RGB */
        prim->r0 = 0;
        prim->g0 = 0;
        prim->b0 = 0;
        prim->r1 = 0;
        prim->g1 = 0;
        prim->b1 = 0;
        prim2->r2 = 0;
        prim2->g2 = 0;
        prim2->b2 = 0;
        prim2->r3 = 0;
        prim2->g3 = 0;
        prim2->b3 = 0;
        prim2 = prim2->next;
        prim = prim->next;
    } while (i++ < 0x10);
    return;

case_1:
    unk86 = self->unk86 - 0xA;
    self->unk86 = unk86;
    unk7E = self->unk7E + 0x40;
    self->unk7E = unk7E;
    if ((unk86 & 0x8000) != 0) {
        self->unk86 = 0;
        self->unk7C = 0x20;
        self->step++;
    }
    self->unk84 = self->unk86;
    self->unk80 -= 5;
    self->unk82 -= 5;
    goto cleanup;

case_2:
    self->unk7E += 0x40;
    self->unk82 -= 3;
    self->unk80 -= 6;
    self->unk7C -= 1;
    if (self->unk7C == 0) {
        self->step++;
    }
    goto cleanup;

case_3:
    self->unk7E += 0x40;
    self->unk82 -= 3;
    self->unk80 -= 6;
    self->unk88 -= 0xC;
    if (self->unk88 & 0x8000) {
        DestroyEntity(self);
        return;
    }
    goto cleanup;
}