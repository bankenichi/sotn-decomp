/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801AE858
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
32:src/boss/bo0/2D26C.c:67: `D_us_801806F0' undeclared (first use this function)
33:src/boss/bo0/2D26C.c:67: (Each undeclared identifier is reported only once
34:src/boss/bo0/2D26C.c:67: for each function it appears in.)
35:src/boss/bo0/2D26C.c:153: `D_us_80180BF8' undeclared (first use this function)
36:src/boss/bo0/2D26C.c:157: `D_us_80180D48' undeclared (first use this function)
37:src/boss/bo0/2D26C.c:167: `D_us_80180D50' undeclared (first use this function)
38:src/boss/bo0/2D26C.c:178: `D_us_80180BA8' undeclared (first use this function)
39:src/boss/bo0/2D26C.c:236: structure has no member named `unk96'
40:src/boss/bo0/2D26C.c:237: structure has no member named `unk98'
41:src/boss/bo0/2D26C.c:238: structure has no member named `unk9A'
42:src/boss/bo0/2D26C.c:239: structure has no member named `unk9C'
43:src/boss/bo0/2D26C.c:240: structure has no member named `unk9E'
44:src/boss/bo0/2D26C.c:241: structure has no member named `unkA0'
45:src/boss/bo0/2D26C.c:248: structure has no member named `unk96'
46:src/boss/bo0/2D26C.c:250: parse error before `['
47:src/boss/bo0/2D26C.c:266: structure has no member named `unk96'
48-[31/358] psx cc src/st/no2/stage_data.c
49-[32/358] psx cc src/st/no2/tilemaps.c

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
extern s32 D_us_80180BA8;

/* Mechanical symbol repair from escalation_triage.py. */
extern s32 D_us_801806F0[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/0.data.s, size 0xc */
extern s16 D_us_80180BF8[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/BA8.data.s, size 0x8 */
extern s32 D_us_80180D48[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/BA8.data.s, size 0x8 */
extern s32 D_us_80180D50[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/BA8.data.s, size 0x18 */

void func_us_801AE858(Entity* self) {
        s16 sp70;
        s32 spA8;
        s32 spC8;
        s32 spCC;
        s32 spD0;
        s32 spD4;
        s32 spD8;
        s32 spDC;
    DRAWENV drawEnv;
    DRAWENV* drawEnvPtr;
    Primitive* prim;
    Primitive* prim2;
    s32 primIndex;
    s32 i;
    s32 j;
    s32 temp;
    s32 angle;
    s32 cosVal;
    s16 posX;
    s16 posY;
    s16 timer;
    s16 wiggle;
    s16 primCount;
    s16 primIndex2;
    s16* fp;
    s16* fp2;
    u16 tpage;
    u16 step;
    u16 params;
    u16* extPtr;
    s32 sp10[19];

    step = self->step;
    extPtr = (u16*)self->ext.venusWeedSpike.flower;

    switch (step) {
    case 0:
        InitializeEntity(D_us_801806F0);
        self->hitboxWidth = 0x10;
        self->scaleX = 0x100;
        self->hitboxHeight = 0;
        self->scaleY = 0;
        self->drawFlags |= 3;
        self->zPriority += 0xC;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 0x18);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        prim = &g_PrimBuf[primIndex];
        self->primIndex = primIndex;
        self->ext.venusWeedSpike.firstPart = prim;
        self->flags |= 0x800000;

        // First loop: 2 prims
        for (i = 0; i < 2; i++) {
            prim->tpage = 0x13;
            prim->clut = 0x214;
            prim->u0 = prim->u2 = i * 0x18;
            prim->u1 = prim->u3 = i * 0x18 + 0x17;
            prim->v0 = prim->v1 = 0x40;
            prim->v2 = prim->v3 = 0x5E;
            prim->drawMode = 0x33;
            prim->priority = self->zPriority + 0xA;
            prim = prim->next;
        }

        // Second loop: 8 prims
        for (i = 0; i < 8; i++) {
            temp = (i % 2) * 0x18;
            prim->tpage = 0x12;
            prim->clut = 0x214;
            prim->u0 = prim->u2 = temp - 0x30;
            prim->u1 = prim->u3 = temp - 0x19;
            prim->v0 = prim->v1 = (i / 2) * 0x1F - 0x80;
            if (i < 2) {
                prim->v0 = (i / 2) * 0x1F - 0x7F;
                prim->v1 += 1;
            }
            prim->v2 = prim->v3 = prim->v0 + 0x1F;
            prim->drawMode = 0x33;
            prim->priority = self->zPriority + 0xA;
            prim = prim->next;
        }

        // Third loop: 2 prims
        for (i = 0; i < 2; i++) {
            prim->tpage = 0x13;
            prim->clut = 0x214;
            prim->u0 = prim->u2 = i * 0x18;
            prim->u1 = prim->u3 = i * 0x18 + 0x17;
            prim->v0 = prim->v1 = 0x5E;
            prim->v2 = prim->v3 = 0x40;
            prim->drawMode = 0x33;
            prim->priority = self->zPriority + 0xA;
            prim = prim->next;
        }

        // Swap UVs loop: 6 prims
        prim = self->ext.venusWeedSpike.firstPart;
        for (i = 0; i < 6; i++) {
            prim2 = prim->next;
            temp = prim2->u0;
            prim2->u0 = prim2->u1;
            prim2->u1 = temp;
            temp = prim2->u2;
            prim2->u2 = prim2->u3;
            prim2->u3 = temp;
            prim = prim2->next;
        }

        // Remaining prims
        self->ext.venusWeedSpike.flower = (Entity*)prim;
        if (prim != NULL) {
            do {
                prim->drawMode = 8;
                prim->priority = self->zPriority + 8;
                prim = prim->next;
            } while (prim != NULL);
        }

        self->ext.venusWeed.timer = 0x18;
        self->ext.venusWeed.wiggleT = 0;
        self->ext.venusWeed.stemPrim = D_us_80180BF8[self->params];
        break;

    case 1:
        if (AnimateEntity(D_us_80180D48, self) == 0) {
            SetStep(2);
            self->pose = Random() & 7;
        }
        if (self->scaleY < 0x100) {
            self->scaleY += 0x10;
        }
        break;

    case 2:
        AnimateEntity(D_us_80180D50, self);
        if (extPtr[0x86 / 2] != 0) {
            if (self->ext.venusWeed.stemPrim != 0) {
                self->ext.venusWeed.stemPrim--;
                return;
            }
            self->step += 1;
        }
        if (self->scaleY < 0x100) {
            self->scaleY += 0x10;
        }
        if (D_us_80180BA8[0] != 0) {
            DestroyEntity(self);
        }
        break;

    case 3:
        drawEnvPtr = &g_CurrentBuffer->draw;
        for (i = 0; i < 19; i++) {
            sp10[i] = ((s32*)drawEnvPtr)[i];
        }
        tpage = 0x100;
        if (sp10[6] != 0) {
            tpage = 0x104;
        }

        posY = self->posY.i.hi;
        prim = self->ext.venusWeedSpike.flower;
        posX = self->posX.i.hi;
        timer = posY;
        if (posY >= 0xF1) {
            timer = 0xF0;
        }

        wiggle = self->ext.venusWeed.timer;
        if (wiggle != 0) {
            self->ext.venusWeed.timer--;
            self->ext.venusWeed.wiggleT += 2;
        }

        // Left prim
        prim->tpage = tpage;
        prim->u0 = prim->u2 = posX - 0x18;
        prim->u1 = prim->u3 = posX;
        prim->v0 = prim->v1 = 0;
        prim->v2 = prim->v3 = timer;
        prim->x0 = prim->x2 = posX - self->ext.venusWeed.timer;
        prim->x1 = prim->x3 = posX - self->ext.venusWeed.timer;
        prim->y0 = prim->y1 = -self->ext.venusWeed.wiggleT;
        prim->y2 = prim->y3 = -self->ext.venusWeed.wiggleT;
        prim->drawMode = 2;

        // Right prim
        prim = prim->next;
        prim->tpage = tpage;
        prim->u0 = prim->u2 = posX;
        prim->u1 = prim->u3 = posX + 0x18;
        prim->v0 = prim->v1 = 0;
        prim->v2 = prim->v3 = timer;
        prim->x0 = prim->x2 = posX;
        prim->x1 = prim->x3 = posX;
        prim->y0 = prim->y1 = -self->ext.venusWeed.wiggleT;
        prim->y2 = prim->y3 = -self->ext.venusWeed.wiggleT;
        prim->drawMode = 2;

        if (self->ext.venusWeed.timer == 0) {
            g_api_PlaySfx(0x7CA);
            self->ext.venusWeedFlower.clutOffset = -0x20;
            self->ext.venusWeedFlower.unk93 = -0x40;
            self->ext.venusWeedFlower.unk96 = -0x60;
            self->ext.venusWeedFlower.unk98 = -0x80;
            self->ext.venusWeedFlower.unk9A = -0xA0;
            self->ext.venusWeedFlower.unk9C = -0xC0;
            self->ext.venusWeedFlower.unk9E = 0;
            self->ext.venusWeedFlower.unkA0 = -0xC0;
            self->step += 1;
        }
        break;

    case 4:
        AnimateEntity(D_us_80180D50, self);
        fp = &self->ext.venusWeedFlower.unk96;
        for (i = 0; i < 7; i++) {
            fp[i] += (s16[]){8, 7, 6, 5, 4, 3, 2}[i];
            if (fp[i] > 0x280) {
                fp[i] = 0x280;
            }
        }

        drawEnvPtr = &g_CurrentBuffer->draw;
        for (i = 0; i < 19; i++) {
            sp10[i] = ((s32*)drawEnvPtr)[i];
        }
        tpage = 0x100;
        if (sp10[6] != 0) {
            tpage = 0x104;
        }

        prim = self->ext.venusWeedSpike.firstPart;
        fp2 = &self->ext.venusWeedFlower.unk96;
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;

        for (i = 0; i < 7; i++) {
            s16 leftX = fp2[0];
            s16 rightX = fp2[1];
            s16 clampedLeft = leftX;
            s16 clampedRight = rightX;

            if (posY < leftX) {
                clampedLeft = posY;
            }
            if (posY < rightX) {
                clampedRight = posY;
            }

            sp70 = fp2[1];

            // Left prim
            prim->y0 = prim->y1 = clampedLeft;
            prim->y2 = prim->y3 = clampedRight;
            prim->x0 = prim->x2 = posX - 0x18;
            prim->x1 = prim->x3 = posX;

            angle = (leftX * 24) + (i * 2048);
            cosVal = rcos(angle);
            if (cosVal < 0) {
                cosVal += 0x3FF;
            }
            prim->x0 = prim->x2 = (posY - 0x18) + (cosVal >> 10);

            angle = (sp70 * 24) + (i * 2048);
            cosVal = rcos(angle);
            if (cosVal < 0) {
                cosVal += 0x3FF;
            }
            prim->x1 = prim->x3 = (posY - 0x18) + (cosVal >> 10);

            // Right prim
            prim2 = prim->next;
            prim2->tpage = tpage;
            prim2->u0 = prim2->u2 = posY - 0x18;
            prim2->u1 = prim2->u3 = posY;
            prim2->v0 = prim2->v1 = clampedLeft;
            prim2->v2 = prim2->v3 = clampedRight;
            prim2->x0 = prim2->x2 = prim->x0;
            prim2->x1 = prim2->x3 = prim->x1;
            prim2->y0 = prim2->y1 = prim->y0;
            prim2->y2 = prim2->y3 = prim->y2;
            prim2->drawMode = tpage;

            if (clampedLeft < 0) {
                prim2->drawMode = 0;
                prim2->y0 = prim2->y1 = 0;
            }

            prim = prim2->next;
            fp2 += 2;
        }
        break;
    }
}