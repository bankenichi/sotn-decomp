/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntityCrashVibhuti
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
ure has no member named `unk10'
100:src/boss/bo6/us_3E79C.c:1008: structure has no member named `unk10'
101:src/boss/bo6/us_3E79C.c:1008: structure has no member named `unk18'
102:src/boss/bo6/us_3E79C.c:1009: structure has no member named `unk14'
103:src/boss/bo6/us_3E79C.c:1009: structure has no member named `unk14'
104:src/boss/bo6/us_3E79C.c:1009: structure has no member named `u

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
void BO6_RicEntityCrashVibhuti(Entity* self) {
    Primitive* prim;
    Primitive* prim2;
    Primitive* prim3;
    s32 i;
    s16 angle;
    s32 radius;
    s16 timer;
    s16 counter0x7C;
    s16 counter0x7E;
    s16 counter0x80;

    switch (self->step) {
    case 0:
        if (g_api_AllocPrimitives(PRIM_TILE, 9) == -1) {
            DestroyEntity(self);
            g_Ric.unk4E = 1;
            return;
        }
        self->primIndex = g_api_AllocPrimitives(PRIM_TILE, 9);
        self->flags = 0x10800000;
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; i < 9; i++) {
            prim->r0 = 0xFF;
            prim->g0 = 0xFF;
            prim->b0 = 0xFF;
            prim->u0 = 1;
            prim->v0 = 1;
            prim->drawMode = 0xA;
            prim->priority = RIC_zPriority + 8;
            prim = prim->next;
        }
        self->step += 1;
        return;
    case 1:
        self->ext.unk7E += 1;
        if (!(self->ext.unk7E & 1)) {
            counter0x7C = self->ext.unk7C;
            if (counter0x7C < 8) {
                self->ext.unk7C = counter0x7C + 1;
                counter0x80 = self->ext.unk80 + 1;
                self->ext.unk80 = counter0x80;
                if ((s16)counter0x80 >= 0x30) {
                    self->step += 1;
                }
                prim2 = &g_PrimBuf[self->primIndex];
                i = 0;
                while (i < 9) {
                    if (!(prim2->drawMode & 8)) {
                        break;
                    }
                    prim2 = prim2->next;
                    i += 1;
                }
                if (i == 9) {
                    return;
                }
                /* Set initial position to player's position + offset */
                prim2->unk10 = (s32)g_Entities_64;
                prim2->unk14 = (s32)(D_800762DC - 0x180000);
                /* Random angle (0-511) and radius */
                angle = rand();
                if (angle < 0) {
                    angle += 0x1FF;
                }
                angle = (angle % 512);
                radius = (rand() % 24) + 0x20;
                /* Velocity based on angle and radius */
                prim2->unk18 = (s32)(rcos(angle) * radius);
                prim2->unk1C = (s32)(-(rsin(angle) * radius));
                /* Timer and clear bit 3 of drawMode */
                prim2->unk24 = 0x10;
                prim2->drawMode &= ~8;
            }
        }
        /* Fall through to case 2 */
    case 2:
        prim3 = &g_PrimBuf[self->primIndex];
        for (i = 0; i < 9; i++) {
            if (!(prim3->drawMode & 8)) {
                timer = prim3->unk24 - 1;
                prim3->unk24 = timer;
                if (timer == 0) {
                    prim3->drawMode |= 8;
                    self->ext.unk7C -= 1;
                    /* Copy primitive position to entity ext for factory */
                    self->ext.unk84 = prim3->unk10;
                    self->ext.unk88 = prim3->unk14;
                    self->ext.unk8C = prim3->unk18 < 1;
                    BO6_RicCreateEntFactoryFromEntity(self, 0x37, 0);
                } else {
                    /* Update position and velocity */
                    prim3->unk10 = prim3->unk10 + prim3->unk18;
                    prim3->unk14 = prim3->unk14 + prim3->unk1C;
                    prim3->unk1C = prim3->unk1C + 0x4000;
                    /* Restore initial position for drawing */
                    prim3->x0 = (s16)prim3->unk12;
                    prim3->y0 = (s16)(u16)prim3->unk16;
                }
            }
            prim3 = prim3->next;
        }
        if (self->step == 2 && (s16)self->ext.unk7C == 0) {
            self->step += 1;
        }
        return;
    case 3:
        g_Ric.unk4E = 1;
        DestroyEntity(self);
        break;
    }
}