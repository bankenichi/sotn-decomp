/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntityHitByLightning
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
73:src/boss/bo6/us_3E79C.c:88: `D_us_80181E74' undeclared (first use this function)
74:src/boss/bo6/us_3E79C.c:88: (Each undeclared identifier is reported only once
75:src/boss/bo6/us_3E79C.c:88: for each function it appears in.)
76:src/boss/bo6/us_3E79C.c:122: `D_800762DC' undeclared (first use this function)
77-[72/243] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/u

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
extern u16 RIC_step;
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
extern int rand(void);
extern Primitive g_PrimBuf[];
extern s32 RIC_velocityY;
extern void (*g_api_PlaySfx)(s32 sfxId);
extern PlayerState g_Ric;
extern void DestroyEntity(Entity* entity);
extern u16 RIC_zPriority;
extern s32 g_Entities_64;

void BO6_RicEntityHitByLightning(Entity* self) {
    s32 shouldDestroy;
    s32 primIndex;
    Primitive* prim;
    Primitive* nextPrim;
    s16 angle;
    s16 sinVal;
    s16 cosVal;
    s32 offsetX;
    s32 offsetY;
    s32 temp;
    s32 randVal;
    s32 randVal2;
    s32 i;
    s16 baseX;
    s16 baseY;
    s16 amplitude;
    s16 angleOffset;
    s16 primCount;
    s16 stepVal;
    s16 paramsHigh;
    s16 unk90Val;
    s16 unk94Val;

    shouldDestroy = 0;
    paramsHigh = self->params & 0xFF00;

    if (paramsHigh == 0x100) {
        self->ext.hitbylightning.unk9C++;
        if ((self->ext.hitbylightning.unk9C << 16) > 0xA80000) {
            shouldDestroy = 1;
        }
    } else if (paramsHigh == 0x200) {
        self->ext.hitbylightning.unk9C++;
        if ((s16)self->ext.hitbylightning.unk9C >= 0x91) {
            shouldDestroy = 1;
        }
    } else if (RIC_step != 0xB) {
        shouldDestroy = 1;
    }

    stepVal = self->step;
    switch (stepVal) {
    case 0:
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 6);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags = 0x08800000;
        self->ext.hitbylightning.unk7C = ((self->params & 0xF) << 9) + (rand() & 0x3F);
        self->ext.hitbylightning.unk80 = rand();
        self->ext.hitbylightning.unk82 = (rand() & 0x1FF) + 0x100;
        prim = &g_PrimBuf[self->primIndex];
        if (prim != NULL) {
            do {
                prim->x0 = self->posX.i.hi;
                prim->x1 = self->posX.i.hi;
                prim->x2 = self->posX.i.hi;
                prim->x3 = self->posX.i.hi;
                prim->y0 = self->posY.i.hi;
                prim->y1 = self->posY.i.hi;
                prim->y2 = self->posY.i.hi;
                prim->y3 = self->posY.i.hi;
                prim->tpage = 0x1A;
                prim->clut = D_us_80181E74[rand() & 1];
                prim->r0 = 0x80;
                prim->g0 = 0x80;
                prim->b0 = 0x80;
                prim->r1 = 0x80;
                prim->g1 = 0x80;
                prim->b1 = 0x80;
                prim->r2 = 0x80;
                prim->g2 = 0x80;
                prim->b2 = 0x80;
                prim->r3 = 0x80;
                prim->g3 = 0x80;
                prim->b3 = 0x80;
                prim->drawMode = 0x133;
                prim->priority = RIC_zPriority - 2;
                prim = prim->next;
            } while (prim != NULL);
        }
        if ((RIC_velocityY != 0) && (RIC_step != 0x11)) {
            self->ext.hitbylightning.unk92 = 1;
        }
        self->ext.hitbylightning.unk94 = 0x10;
        g_api_PlaySfx(0x6E4);
        self->step++;
        /* fall through to common drawing code */
    case 1:
        if (self->step == 1) {
            self->ext.hitbylightning.unk7C = ((self->params & 0xF) << 9) + (rand() & 0x1FF);
            sinVal = rsin(self->ext.hitbylightning.unk80);
            self->ext.hitbylightning.unk80 += self->ext.hitbylightning.unk82;
            cosVal = rcos(self->ext.hitbylightning.unk7C);
            offsetX = ((cosVal * sinVal) >> 7) * 12;
            offsetY = ((rsin(self->ext.hitbylightning.unk7C) * sinVal) >> 7) * -14;
            self->posX.val = offsetX + g_Entities_64;
            self->posY.val = offsetY + D_800762DC;
            if ((self->ext.hitbylightning.unk92 != 0) && (g_Ric.vram_flag & 0xE)) {
                shouldDestroy = 1;
            }
            if (shouldDestroy) {
                self->ext.hitbylightning.unk90 = (rand() & 0xF) + 0x10;
                self->step++;
            }
        }
        /* fall through to common drawing code */
    case 2:
        if (self->step == 2) {
            unk90Val = self->ext.hitbylightning.unk90 - 1;
            self->ext.hitbylightning.unk90 = unk90Val;
            if ((unk90Val << 16) == 0) {
                DestroyEntity(self);
                return;
            }
            unk94Val = self->ext.hitbylightning.unk94;
            if (unk94Val > 0) {
                self->ext.hitbylightning.unk94 = unk94Val - 1;
            }
            self->ext.hitbylightning.unk7C = ((self->params & 0xF) << 9) + (rand() & 0xFF);
            sinVal = rsin(self->ext.hitbylightning.unk80);
            self->ext.hitbylightning.unk80 += self->ext.hitbylightning.unk82;
            cosVal = rcos(self->ext.hitbylightning.unk7C);
            randVal = rand();
            temp = randVal;
            if (randVal < 0) {
                temp = randVal + 7;
            }
            angleOffset = (randVal - ((temp >> 3) * 8)) + 8;
            sinVal = rsin(self->ext.hitbylightning.unk7C);
            randVal2 = rand();
            temp = randVal2;
            if (randVal2 < 0) {
                temp = randVal2 + 7;
            }
            angleOffset = (randVal2 - ((temp >> 3) * 8)) + 10;
            self->posX.val = (((cosVal * sinVal) >> 7) * angleOffset) + g_Entities_64;
            self->ext.hitbylightning.unk98 -= 0x8000;
            self->posY.val = (-((rsin(self->ext.hitbylightning.unk7C) * sinVal) >> 7) * angleOffset) + self->ext.hitbylightning.unk98 + D_800762DC;
        }
        /* common drawing code for steps 1 and 2 */
        primCount = 0;
        baseX = (self->posX.i.hi + (rand() & 7)) - 4;
        unk94Val = self->ext.hitbylightning.unk94;
        baseY = (self->posY.i.hi + (rand() & 0x1F)) - 0x18;
        prim = &g_PrimBuf[self->primIndex];
        amplitude = (unk94Val * rsin(self->ext.hitbylightning.unk80)) >> 12;
        do {
            nextPrim = prim->next;
            /* copy primitive data from next to current */
            prim->next = nextPrim->next;
            prim->r0 = nextPrim->r0;
            prim->g0 = nextPrim->g0;
            prim->b0 = nextPrim->b0;
            prim->x0 = nextPrim->x0;
            prim->r1 = nextPrim->r1;
            prim->g1 = nextPrim->g1;
            prim->b1 = nextPrim->b1;
            prim->x1 = nextPrim->x1;
            prim->r2 = nextPrim->r2;
            prim->g2 = nextPrim->g2;
            prim->b2 = nextPrim->b2;
            prim->x2 = nextPrim->x2;
            prim->r3 = nextPrim->r3;
            prim->g3 = nextPrim->g3;
            prim->b3 = nextPrim->b3;
            prim->x3 = nextPrim->x3;
            prim->y0 = nextPrim->y0;
            prim->y1 = nextPrim->y1;
            prim->y2 = nextPrim->y2;
            prim->y3 = nextPrim->y3;
            prim->u0 = (primCount * 0x10) - 0x70;
            prim->u2 = (primCount * 0x10) - 0x70;
            prim->u1 = ((primCount + 1) * 0x10) - 0x70;
            prim->u3 = ((primCount + 1) * 0x10) - 0x70;
            primCount++;
            prim->v0 = 0xC0;
            prim->v1 = 0xC0;
            prim->v2 = 0xCF;
            prim->v3 = 0xCF;
            prim->next = nextPrim;
        } while (primCount < 5);

        /* update last primitive's positions */
        prim->x0 = prim->x1;
        prim->y0 = prim->y1;
        prim->x2 = prim->x3;
        prim->y2 = prim->y3;

        angleOffset = self->ext.hitbylightning.unk7C + 0x400;
        prim->x1 = baseX + ((rcos(angleOffset) >> 4) * amplitude >> 8);
        prim->y1 = baseY - ((rsin(angleOffset) >> 4) * amplitude >> 8);

        angleOffset = self->ext.hitbylightning.unk7C - 0x400;
        prim->x3 = baseX + ((rcos(angleOffset) >> 4) * amplitude >> 8);
        prim->y3 = baseY - ((rsin(angleOffset) >> 4) * amplitude >> 8);

        temp = self->ext.hitbylightning.unk80 & 0xFFF;
        if (temp >= 0x400 && temp < 0xC00) {
            prim->priority = RIC_zPriority - 2;
        } else {
            prim->priority = RIC_zPriority + 2;
        }

        prim->u0 = (primCount * 0x10) - 0x70;
        prim->u2 = (primCount * 0x10) - 0x70;
        prim->u1 = ((primCount + 1) * 0x10) - 0x70;
        prim->u3 = ((primCount + 1) * 0x10) - 0x70;
        prim->v0 = 0xC0;
        prim->v1 = 0xC0;
        prim->v2 = 0xCF;
        prim->v3 = 0xCF;
        break;
    }
}