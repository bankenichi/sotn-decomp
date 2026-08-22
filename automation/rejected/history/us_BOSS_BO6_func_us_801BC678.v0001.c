/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BC678
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: BUILD FAILED:
30:src/boss/bo6/us_39144.c:1543: conflicting types for `D_us_801818A8'
31:src/boss/bo6/us_39144.c:1450: previous declaration of `D_us_801818A8'
32-[30/156] psx cc src/weapon/w_010.c
33-[31/156] psx cc src/weapon/w_024.c

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
extern u8 D_us_801818A8[10];
extern u16 D_us_80181878[];
extern PlayerState g_Ric;
extern s32 D_us_80181884[];
extern s32 D_us_8018189C[];
extern void BO6_RicSetSpeedX(s32);
extern u16 D_us_8018189E[];
void DestroyEntity(Entity*);
extern u16 RIC_zPriority;

/* Richter's whip trail / slash effect entity update */
void func_us_801BC678(Entity* self) {
    s32 step;
    u16 paramsHi;
    u16 paramsLo;
    s16 posXOffset;
    s32 index;
    s32 temp;

    paramsLo = self->params & 0xFF;
    paramsHi = self->params >> 8;
    step = self->step;

    if (step == 0) {
        self->animSet = 5;
        self->anim = D_us_801818A8;
        self->flags = 0x28000000;
        self->blendMode = 0x30;
        self->drawFlags = 0xB;
        self->opacity = 0x60;
        self->zPriority = RIC_zPriority + 2;

        posXOffset = D_us_80181878[paramsLo];
        if (paramsHi == 0) {
            posXOffset += 6;
        }
        if (paramsHi == 1) {
            posXOffset -= 8;
        }
        if (paramsHi == 2) {
            posXOffset -= 6;
        }
        if (paramsHi == 5) {
            posXOffset = -6;
        }
        if (paramsHi == 3) {
            self->posY.i.hi -= 8;
        }
        if (paramsHi != 4) {
            if (paramsHi == 1 && (g_Ric.vram_flag & 0x8000)) {
                /* Halve the offset (round toward zero) */
                posXOffset = (posXOffset + (posXOffset >> 31)) >> 1;
            }
            if (self->facingLeft) {
                posXOffset = -posXOffset;
            }
            self->posY.i.hi += 0x18;
            self->posX.i.hi += posXOffset;
            index = paramsLo * 2;
            self->scaleX = D_us_8018189C[paramsLo] + 0x40;
            self->velocityY = D_us_80181884[paramsLo];
            if (paramsHi == 1) {
                self->velocityY = -0x4000;
                BO6_RicSetSpeedX(-0x3000);
                self->scaleX = D_us_8018189E[0] + 0x40;
            }
            if (paramsHi == 5) {
                /* (4 - index) as array index into D_us_80181884 */
                self->velocityY = D_us_80181884[4 - index];
            }
            if (paramsHi == 2) {
                self->velocityY = -0x8000;
                BO6_RicSetSpeedX(-0x3000);
                self->scaleX = D_us_8018189E[0] + 0x40;
            }
            self->scaleY = self->scaleX;
            self->step++;
            return;
        }
        DestroyEntity(self);
        return;
    } else if (step == 1) {
        self->opacity += 0xFE;
        self->posY.val += self->velocityY;
        self->posX.val += self->velocityX;
        if (self->poseTimer < 0) {
            DestroyEntity(self);
        }
    }
}