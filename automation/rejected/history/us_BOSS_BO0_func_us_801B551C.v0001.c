/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B551C
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/3053C.c
   verdict: BUILD FAILED:
n_unkA8'
101:src/boss/bo0/3053C.c:694: structure has no member named `unkAD'
102:src/boss/bo0/3053C.c:695: structure has no member named `_align_unkA8'
103:src/boss/bo0/3053C.c:696: structure has no member named `_align_unkA8'
104:src/boss/bo0/3053C.c:701: structure has no member named `unkAD'
105:src/boss/bo0/3053C.c:701: structure has no member named `unkAD'
106:src/boss/bo0/3053C.c:705: structure has no member named `unkA9'
107:src/boss/bo0/3053C.c:711: structure has no member named `unkA9'
108:src/boss/bo0/3053C.c:714: structure has no member named `unkA9'
109:src/boss/bo0/3053C.c:717: structure has no member named `unkA9'
110:src/boss/bo0/3053C.c:720: structure has no member named `unkA9'
111:src/boss/bo0/3053C.c:746: called object is not a function
112:src/boss/bo0/3053C.c:756: structure has no member named `unkA9'
113:src/boss/bo0/3053C.c:763: structure has no member named `unkA9'
114:src/boss/bo0/3053C.c:767: called object is not a function
115-[79/391] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/bobo4.map -T build/us/bobo4.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.bobo4.txt -T build/us/config/undefined_syms_auto.us.bobo4.txt -o build/us/bobo4.elf
116-[80/391] psx cc src/st/cat/gfx_data.c

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
extern u16 PLAYER_posX_i_hi;
extern u16 PLAYER_posY_i_hi;
extern s32 g_api_func_800EB758;

void func_us_801B551C(Entity* self) {
    Entity* newEntity;
    Primitive* prim;
    s32 primIndex;
    s32 temp;
    s16 angle;
    s16 targetAngle;
    s16 temp_s0;
    s16 result;
    s16 var_a1;
    s16 var_a0;
    u16 step_s;
    u16 step;
    s32* dataPtr;
    s16* d16Ptr;

    *(u16*)&self->posX.i.lo = *(u16*)&self->posX.i.lo;
    *(u16*)&self->posY.i.lo = *(u16*)&self->posY.i.lo;
    if (self->flags & 0x100) {
        self->hitboxState = 0;
    }

    step = self->step;
    if (step >= 11) {
        goto post_switch;
    }

    switch (step) {
    case 0:
        InitializeEntity(D_us_80180714);
        self->hitboxWidth = 10;
        self->hitboxHeight = 10;
        self->animCurFrame = 1;
        self->drawFlags |= 4;
        self->rotate = -0x100;
        self->zPriority = D_us_801CE56C - 2;
        break;

    case 1:
        AnimateEntity(D_us_8018120C, self);
        func_us_801B15BC(&self->rotate, -0x80, 8);
        self->step_s = 0;
        break;

    case 7:
        AnimateEntity(D_us_80181220, self);
        func_us_801B15BC(&self->rotate, 0xC0, 8);
        if (self->poseTimer == 0 && !(self->pose & 3)) {
            g_api_PlaySfx(0x819);
            self->step_s = 0;
        } else {
            self->step_s = 0;
        }
        break;

    case 6:
        self->animCurFrame = 1;
        func_us_801B15BC(&self->rotate, -0x100, 0x20);
        break;

    case 5:
        if (func_us_801B15BC(&self->rotate, 0x180, 0x10)) {
            if (AnimateEntity(D_us_80181234, self) == 0) {
                self->ext.player.unkA9 = 0;
                self->step = 1;
            }
            if (self->pose == 2) {
                g_api_PlaySfx(0x819);
            }
            if (self->pose >= 3) {
                if (self->poseTimer & 2) {
                    *(u16*)&self->posX.i.lo = *(u16*)&self->posX.i.lo + 1;
                } else {
                    *(u16*)&self->posX.i.lo = *(u16*)&self->posX.i.lo - 1;
                }
            }
        } else {
            self->pose = 0;
            self->poseTimer = 0;
        }
        break;

    case 2:
        self->animCurFrame = 2;
        d16Ptr = &D_us_801811D0[self->ext.player.unkA8 * 4];
        if (func_us_801B15BC(&self->rotate, *d16Ptr, 0x10)) {
            self->ext.player.unkA9 = 1;
            self->step = 3;
            self->step_s = 0;
        }
        break;

    case 3:
        step_s = self->step_s;
        if (step_s == 0) {
            newEntity = AllocEntity(&g_Entities[64], &g_EvHwCardEnd);
            if (newEntity == NULL) {
                newEntity = self - 23;
                self->ext.player.unkA9 = 0;
                self->step_s++;
            }
            CreateEntityFromEntity(0x39, self, newEntity);
            newEntity->ext.player.unkA4 = (s32)self;
            newEntity->params = self->ext.player.unkA8 & 1;
            newEntity->facingLeft = self->facingLeft;
            self->ext.player.unkA9 = 1;
            self->animCurFrame = 3;
            self->step_s++;
        } else if (step_s == 1) {
            if (self->ext.player.unkA9 == 0) {
                self->ext.player.unkA9 = 0;
            }
        }
        break;

    case 4:
        step_s = self->step_s;
        if (step_s != 0) {
            if (step_s == 1) {
                goto case4_step1;
            }
        } else {
            self->animCurFrame = 4;
            temp_s0 = *(u16*)&self->posX.i.lo - PLAYER_posX_i_hi;
            var_a1 = temp_s0;
            if (self->facingLeft) {
                var_a1 = -temp_s0;
            }
            targetAngle = -ratan2(*(u16*)&self->posY.i.lo - PLAYER_posY_i_hi, var_a1) + 0x100;
            angle = targetAngle;
            if (targetAngle >= 0x381) {
                angle = 0x380;
            }
            if (angle < -0x180) {
                angle = 0x180;
            }
            self->ext.player.unkA8 = angle;
            self->step_s++;
        }
    case4_step1:
        temp_s0 = self->ext.player.unkA8;
        result = func_us_801B15BC(&self->rotate, temp_s0, 0x20);
        temp = func_us_801B163C(&self->hitboxOffX, -((temp_s0 + 0x180) / 2), 0x20);
        if (result + temp == 2) {
            self->ext.player.unkA8 = 1;
            self->step_s = 0;
            self->step = 9;
        }
        break;

    case 9:
        step_s = self->step_s;
        if (step_s == 0) {
            self->animCurFrame = 4;
            dataPtr = &D_us_801811EC[self->ext.player.unkAD * 2];
            self->ext.player.unkA8 = dataPtr[0];
            self->ext.player.unkA9 = 0;
            self->step_s++;
            self->ext.player._align_unkA8 = dataPtr[3];
        }
        if (self->step_s == 1) {
            self->ext.player._align_unkA8--;
            dataPtr = &D_us_801811EC[self->ext.player.unkAD * 2];
            if (self->ext.player._align_unkA8 == 0) {
                self->ext.player._align_unkA8 = dataPtr[3];
                newEntity = AllocEntity(&g_Entities[160], &g_Entities[160 + 0x1780]);
                if (newEntity != NULL) {
                    CreateEntityFromEntity(0x3A, self, newEntity);
                    newEntity->ext.player.unkA4 = (s32)self;
                    newEntity->ext.player.unkAD = self->ext.player.unkAD;
                    newEntity->facingLeft = self->facingLeft;
                }
            }
            if (self->ext.player.unkA9) {
                self->rotate += dataPtr[1];
            } else {
                self->rotate -= dataPtr[1];
            }
            if (self->rotate < (self->ext.player.unkA8 - dataPtr[0])) {
                self->ext.player.unkA9 = 1;
            }
            if ((self->ext.player.unkA8 + dataPtr[0]) < self->rotate) {
                self->ext.player.unkA9 = 0;
            }
            if (self->rotate < -0x180) {
                self->ext.player.unkA9 = 1;
            }
            if (self->rotate >= 0x381) {
                self->ext.player.unkA9 = 0;
            }
            self->hitboxOffX = -((self->rotate + 0x180) / 2);
            self->ext.player.unkA8--;
            if (self->ext.player.unkA8 == 0) {
                self->step_s = 0;
                self->step = 1;
                self->ext.player.unkA8 = 0;
            }
        }
        break;

    case 10:
        self->animCurFrame = 1;
        break;

    case 8:
        step_s = self->step_s;
        if (step_s == 0) {
            primIndex = g_api_AllocPrimitives(PRIM_GT4, 1);
            if (primIndex != -1) {
                prim = &g_PrimBuf[primIndex];
                self->primIndex = primIndex;
                self->ext.player.prim = prim;
                self->flags |= 0x800000;
                func_us_801B13A8(prim, primIndex);
                g_api_func_800EB758(*(u16*)&self->posX.i.lo, *(u16*)&self->posY.i.lo, self, self->drawFlags, prim, self->facingLeft);
                prim->tpage = 0x14;
                prim->clut = prim->clut + 0x20B;
                prim->drawMode = 2;
                prim->priority = self->zPriority;
            }
            self->step_s++;
        } else if (step_s == 1) {
            self->palette = 0x219;
            self->unk5A = 0x54;
            if (self->ext.player.unkA9) {
                self->ext.player.prim->drawMode = 8;
                self->step_s++;
            }
        } else if (step_s == 2) {
            self->palette = 0x8219;
            self->unk5A = 0x54;
            if (self->ext.player.unkA9 == 3) {
                prim = self->ext.player.prim;
                self->animCurFrame = 3;
                func_us_801B13A8(prim);
                g_api_func_800EB758(*(u16*)&self->posX.i.lo, *(u16*)&self->posY.i.lo, self, self->drawFlags, prim, self->facingLeft);
                prim->tpage = 0x15;
                prim->clut = 0x219;
                prim->drawMode = 2;
                prim->priority = self->zPriority;
            }
        }
        break;
    }

post_switch:
    self->hitboxOffX = -(rcos(self->rotate) * 0xC) >> 12;
    self->hitboxOffY = -(rsin(self->rotate) * 0xC) >> 12;

    if (D_us_801CE5B0 == 0 && self->step < 8 && !(Random() & 0x3F)) {
        newEntity = AllocEntity(&g_Entities[224], &g_Entities[224 + 0x1780]);
        if (newEntity != NULL) {
            CreateEntityFromEntity(0x3D, self, newEntity);
            newEntity->ext.player.unkA4 = (s32)self;
            newEntity->params = (Random() & 7) + 0x10;
        }
    }
}