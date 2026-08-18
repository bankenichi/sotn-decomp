/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntityCrashHydroStorm
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
/bo6/us_3E79C.c:182: structure has no member named `unk24'
80:src/boss/bo6/us_3E79C.c:183: structure has no member named `unk30'
81:src/boss/bo6/us_3E79C.c:183: structure has no member named `unk30'
82:src/boss/bo6/us_3E79C.c:185: structure has no member named `unk0C'
83:src/boss/bo6/us_3E79C.c:188: structure has no member named `unk2A'
84:src/boss/bo6/us_3E79C.c:190: structure has n

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
void BO6_RicEntityCrashHydroStorm(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s16 var_v1;
    u16 step;
    s32 temp;
    s16 temp_s16;
    u16 temp_u16;
    s32 temp_s32;

    step = self->step;
    if (step < 0x18) {
        var_v1 = 0x20;
    } else {
        var_v1 = 0x21 - ((step - 0x20) * 2);
    }

    switch (self->step) {
    case 0:
        primIndex = g_api_AllocPrimitives(PRIM_LINE_G2, var_v1);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        InitializeEntity(&D_us_80180484);
        self->ext.unkB0 = 0x10;
        self->posX.i.hi = 0x80;
        self->posY.i.hi = 0x70;
        self->hitboxWidth = 0x78;
        self->hitboxHeight = 0x78;
        self->facingLeft = 0;
        prim = &g_PrimBuf[self->primIndex];
        self->flags |= 0x10800000;
        if (prim != NULL) {
            do {
                prim->r0 = 0x1F;
                prim->g0 = 0x1F;
                prim->b0 = 0x30;
                prim->r1 = 0x3F;
                prim->g1 = 0x50;
                prim->b1 = 0x7F;
                temp_s16 = rand() & 0x1FF;
                prim->x0 = temp_s16;
                prim->x1 = temp_s16;
                temp_s16 = -(rand() & 0xF);
                prim->y1 = temp_s16;
                prim->y0 = temp_s16;
                prim->unk2A = (u16)prim->x1;
                prim->y3 = (s16)(u16)prim->y1;
                prim->unk18 = (s32)(rcos(0xB80) * 0x30 * 4);
                prim->unk1C = (s32)(rsin(0xB80) * -0x30 * 4);
                prim->unk30 = 0;
                prim->unk24 = (s16)((rand() & 0xF) + 0xC);
                if (rand() & 1) {
                    temp_u16 = RIC_zPriority + 2;
                } else {
                    temp_u16 = RIC_zPriority - 2;
                }
                prim->priority = temp_u16;
                prim->drawMode = 0x31;
                prim = prim->next;
            } while (prim != NULL);
        }
        if (self->params == 1) {
            g_api_SetFadeMode(3);
        }
        self->ext.unk7C = 0x160;
        if ((u16)self->params < 0x10) {
            if (!(self->params & 3)) {
                g_api_PlaySfx(0x830);
            }
        }
        self->step = 1;
        /* fallthrough */
    default:
        g_Ric.timers[3] = 0x10;
        return;
    case 1:
        prim = &g_PrimBuf[self->primIndex];
        if (prim != NULL) {
            do {
                if (prim->unk30 == 0) {
                    prim->y3 = (s16)(u16)prim->y1;
                    prim->unk2A = (u16)prim->x1;
                    prim->unk2C = (s32)(prim->unk2C + prim->unk1C);
                    temp_u16 = (u16)prim->y3;
                    prim->unk28 = (s32)(prim->unk28 + prim->unk18);
                    prim->y1 = (s16)temp_u16;
                    prim->x1 = (s16)prim->unk2A;
                    if (prim->unk24 < (s16)temp_u16) {
                        prim->unk30 = (s16)((u16)prim->unk30 + 1);
                        prim->clut = (u16)prim->y0 - (u16)prim->y1;
                        prim->unk0C = (u16)((u16)prim->x0 - (u16)prim->x1);
                    }
                } else {
                    prim->unk2A = (u16)prim->x1;
                    prim->y3 = (s16)(u16)prim->y1;
                    prim->unk28 = (s32)(prim->unk28 + prim->unk18);
                    prim->unk2C = (s32)(prim->unk2C + prim->unk1C);
                    temp_u16 = (u16)prim->y3;
                    prim->y1 = (s16)temp_u16;
                    prim->x1 = (s16)prim->unk2A;
                    prim->y0 = temp_u16 + prim->clut;
                    prim->x0 = (u16)prim->x1 + prim->unk0C;
                    if (prim->y0 >= 0xD8) {
                        self->step = 2;
                    }
                }
                prim = prim->next;
            } while (prim != NULL);
        }
        self->ext.unk7C += 1;
        g_Ric.timers[3] = 0x10;
        return;
    case 2:
        if (self->params == 0x18) {
            g_Ric.unk4E = 1;
        }
        DestroyEntity(self);
        g_Ric.timers[3] = 0x10;
        return;
    }
}