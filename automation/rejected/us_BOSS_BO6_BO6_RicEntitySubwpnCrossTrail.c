/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntitySubwpnCrossTrail
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
3] psx cc src/dra/sound.c
36-[34/293] psx cc src/dra/d_2FE48.c
--
50:src/boss/bo6/us_3E79C.c:588: union has no member named `castleTrail'
51:src/boss/bo6/us_3E79C.c:588: union has no member named `castleTrail'
52:src/boss/bo6/us_3E79C.c:592: `D_us_80182994' undeclared (first use this function)
53:src/boss/bo6/us_3E79C.c:592: (Each undeclared identifier is reported only once
54:src/bo

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
void BO6_RicEntitySubwpnCrossTrail(Entity* self) {
    u16 step;
    u16 temp;
    s32* posData;

    step = self->step;
    switch (step) {
    case 0:
        self->flags = 0x18000000;
        self->animSet = -0x7FFC;
        self->ext.castleTrail.posData = self->ext.castleTrail.parentCross->ext.castleTrail.posData;
        self->unk5A = 0x44;
        self->palette = 0x81B0;
        self->blendMode = 0x10;
        self->animCurFrame = D_us_80182994[self->params];
        self->facingLeft = RIC_facingLeft;
        self->drawFlags = 4;
        self->rotate = 0xC00;
        self->step += 1;
        self->zPriority = RIC_zPriority;
        /* fall through */
    default:
block_11:
        posData = &self->ext.castleTrail.posData[self->ext.castleTrail.posIndex * 2];
        self->posX.i.hi = posData[0] - g_Tilemap.scrollX.i.hi;
        self->ext.castleTrail.posIndex = (self->ext.castleTrail.posIndex + 1) & 0x3F;
        self->posY.i.hi = posData[1] - g_Tilemap.scrollY.i.hi;
        return;
    case 1:
        self->rotate -= 0x80;
        if ((u32)(self->ext.castleTrail.parentCross->step - 6) < 2U) {
            self->step += 1;
            self->ext.castleTrail.timer = (self->params + 1) * 4;
        }
        goto block_11;
    case 2:
        temp = self->ext.castleTrail.timer - 1;
        self->ext.castleTrail.timer = temp;
        self->rotate -= 0x80;
        if ((temp << 0x10) == 0) {
            DestroyEntity(self);
            return;
        }
        goto block_11;
    }
}