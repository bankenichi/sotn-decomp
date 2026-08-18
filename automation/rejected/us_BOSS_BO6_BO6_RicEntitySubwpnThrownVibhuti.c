/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntitySubwpnThrownVibhuti
   attempt: 4/4
   model  : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
r was expected
81:src/boss/bo6/us_3E79C.c:936: structure has no member named `velocityX'
82:src/boss/bo6/us_3E79C.c:939: structure has no member named `velocityY'
83:src/boss/bo6/us_3E79C.c:939: structure has no member named `velocityY'
84:src/boss/bo6/us_3E79C.c:940: structure has no member named `velocityY'
85:src/boss/bo6/us_3E79C.c:941: structure has no member named `velocityY'
8

   This is NOT a permuter seed and must never be treated as
   one: it has never compiled. automation/candidates/ is for
   code that builds and merely misses on bytes.

   Why it is kept: the escalation path used to record only
   the compiler's message, so a record like `g_EInitCommon
   undeclared` described code nobody could look at any more.
   Twelve such records were assumed to be one extern away
   from building, and turned out to need a full re-attempt
   because the candidate had been discarded.

   Do NOT apply this to the tree. Read it, fix what the
   verdict names, and re-attempt. */
void BO6_RicEntitySubwpnThrownVibhuti(Entity* self) {
    Collider sp10;
    Primitive* prim;
    s16 var_s1;
    s32 temp_s0;
    s32 temp_s1;
    s32 temp_v1;
    s32 var_s0;
    u16 temp_s5;
    u16 temp_s6;
    u16 temp_v0;
    u16 var_v0;

    switch (self->step) {
    case 0:
        temp_v0 = g_api_func_800EDB58(0x11, 0xD);
        self->primIndex = (s32)temp_v0;
        if (temp_v0 != -1) {
            self->flags = 0x08800000;
            self->hitboxHeight = 4;
            self->hitboxWidth = 4;
            self->ext.vibhuti.unk7C = 0x80;
            self->posY.i.hi -= 0xF;
            prim = &g_PrimBuf[self->primIndex];
            if (RIC_facingLeft != 0) {
                var_v0 = self->posX.i.hi - 0xD;
            } else {
                var_v0 = self->posX.i.hi + 0xD;
            }
            self->posX.i.hi = var_v0;
            temp_s6 = self->posX.i.hi;
            temp_s5 = self->posY.i.hi;
            prim->drawMode = 2;
        loop_9:
            prim->priority = RIC_zPriority - 1;
            if (prim->next != NULL) {
                prim->x1 = temp_s6;
                prim->y1 = (s16)temp_s5;
                prim->x0 = 0;
                prim->y0 = 0;
                temp_s0 = (rand() & 0xFF) + 0x100;
                temp_s1 = (rand() & 0xFF) + 0x80;
                prim->velocityX = (s32)(((s32)(rcos(temp_s0) * 0x10 * temp_s1) >> 9) + 0x8000);
                temp_v1 = rsin(temp_s0) * 0x10 * temp_s1;
                prim->velocityX = (s32)(prim->velocityX * 3) >> 1;
                prim->velocityY = (s32)-(temp_v1 >> 9);
                if (self->facingLeft != 0) {
                    prim->velocityX = (s32)-prim->velocityX;
                }
                prim->unk24 = 1;
                prim->y1 = (u16)prim->y1 - 4;
                prim->r0 = 0xFF;
                prim->g0 = 0xFF;
                prim->b0 = 0xFF;
                prim->u0 = 2;
                prim->v0 = 2;
                prim->x0 = (s16)prim->x1;
                prim->y0 = (s16)(u16)prim->y1;
                prim = prim->next;
                prim->drawMode = 2;
                goto loop_9;
            }
            prim->u0 = 0;
            prim->x0 = 0;
            prim->y0 = 0;
            prim->drawMode &= 0xFFF7;
            g_api_PlaySfx(0x60C);
            self->step += 1;
            return;
        }
    block_17:
        DestroyEntity(self);
        return;
    case 1:
        var_s1 = 2;
        if (self->facingLeft != 0) {
            var_s1 = -2;
        }
        temp_v0 = self->ext.vibhuti.unk7C - 1;
        self->ext.vibhuti.unk7C = temp_v0;
        var_s0 = 0;
        if ((temp_v0 << 0x10) == 0) {
            goto block_17;
        }
        prim = &g_PrimBuf[self->primIndex];
    loop_20:
        if (prim->next != NULL) {
            prim->x1 = (u16)prim->x0;
            prim->y1 = (s16)(u16)prim->y0;
            if (prim->unk24 != 0) {
                temp_v1 = prim->velocityX;
                if (temp_v1 != 0) {
                    prim->x0 = (s32)(prim->x0 + temp_v1);
                    g_api_CheckCollision((s16)prim->x1 + var_s1, (s32)prim->y1, &sp10, 0);
                    if ((s32)sp10 & 2) {
                        prim->velocityX = 0;
                    }
                }
                prim->velocityY = prim->velocityY + 0x1800;
                prim->y0 = (s32)(prim->y0 + prim->velocityY);
                if (prim->velocityY > 0x40000) {
                    prim->velocityY = 0x40000;
                }
                if (prim->velocityY > 0) {
                    g_api_CheckCollision((s32)(s16)prim->x1, (s32)prim->y1, &sp10, 0);
                    if ((s32)sp10 & 1) {
                        prim->unk24 = 0;
                        prim->v0 = 3;
                        prim->u0 = 3;
                        prim->y1 = (((u16)prim->y1 + (u16)sp10.unk18) - 1) - (var_s0 % 3);
                    }
                }
            }
            if ((self->ext.vibhuti.unk7C & 7) == var_s0) {
                self->posX.i.hi = prim->x1;
                self->posY.i.hi = (u16)prim->y1;
                if (prim->drawMode & 8) {
                    self->hitboxHeight = 0;
                    self->hitboxWidth = 0;
                } else {
                    self->hitboxHeight = 4;
                    self->hitboxWidth = 4;
                }
                if (prim->unk24 != 0) {
                    self->hitboxOffY = 0;
                } else {
                    self->hitboxOffY = -6;
                }
            }
            if ((self->hitFlags != 0) && ((((s16)self->ext.vibhuti.unk7C + 1) & 7) == var_s0)) {
                prim->drawMode = 8;
            }
            if (((s16)self->ext.vibhuti.unk7C - 1) == var_s0) {
                prim->drawMode = 8;
            }
            prim->x0 = (s16)prim->x1;
            prim->y0 = (s16)(u16)prim->y1;
            prim = prim->next;
            var_s0 += 1;
            goto loop_20;
        }
        prim->u0 = 0;
        prim->x0 = 0;
        prim->y0 = 0;
        prim->drawMode &= 0xFFF7;
        self->hitFlags = 0;
        return;
    }
}