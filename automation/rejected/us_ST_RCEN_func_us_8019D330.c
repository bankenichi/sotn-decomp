/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RCEN:func_us_8019D330
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/unk_1D260.c
   verdict: BUILD FAILED:
93:src/st/rcen/unk_1D260.c:26: `D_us_8018091C' undeclared (first use this function)
94:src/st/rcen/unk_1D260.c:26: (Each undeclared identifier is reported only once
95:src/st/rcen/unk_1D260.c:26: for each function it appears in.)
96:src/st/rcen/unk_1D260.c:32: union has no member named `unk80'
97:src/st/rcen/unk_1D260.c:47: union has no member named `unk80'
98:src/st/rcen/unk_1D260.c

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
void func_us_8019D330(Entity* self) {
    s32 angle;
    s32 velocityMultiplier;
    s32 animResult;
    u16 step_s;
    u16* entry;
    u16 temp;

    switch (self->step) {
    case 0:
        InitializeEntity(&g_EInitParticle);
        angle = self->params & 0xF;
        entry = (u16*)((u32)&D_us_8018091C + (angle * 12));
        self->palette = entry[2] + 0x2E0;
        self->blendMode = ((u8*)entry)[6];
        self->animSet = entry[0];
        self->unk5A = entry[1];
        self->step = angle + 1;
        self->ext.unk80 = entry[4]; // ext offset 0x04
        temp = self->params & 0xFF00;
        if (temp != 0) {
            self->zPriority = (u16)(temp >> 8);
        }
        if (self->params & 0xF0) {
            self->palette = 0x819F;
            self->blendMode = 0x10;
            self->facingLeft = 1;
            return;
        }
        return;
    case 1:
        MoveEntity();
        self->velocityY = -0x10000;
        animResult = AnimateEntity(self->ext.unk80, self); // ext offset 0x04
        if (animResult == 0) {
            DestroyEntity(self);
        }
        return;
    case 2:
        if (self->step_s == 0) {
            self->rotate = Random() - 0x80;
            self->drawFlags = 4;
            self->facingLeft = Random() & 1;
            angle = self->rotate;
            if (self->facingLeft != 0) {
                angle = -angle;
            }
            self->velocityX = rsin(angle) * 0x10;
            self->velocityY = -(rcos(angle) * 0x10);
            self->step_s += 1;
        }
        MoveEntity();
        self->velocityY = -0x10000;
        animResult = AnimateEntity(self->ext.unk80, self); // ext offset 0x04
        if (animResult == 0) {
            DestroyEntity(self);
        }
        return;
    case 3:
        if (self->step_s == 0) {
            self->drawFlags = 0xC;
            self->opacity = 0x80;
            self->facingLeft = Random() & 1;
            angle = rand() & 0xFFF;
            self->rotate = angle;
            if (self->facingLeft != 0) {
                angle = -angle;
            }
            self->velocityX = rsin(angle) * 0x28;
            self->velocityY = -(rcos(angle) * 0x28);
            self->ext.unk8C = (Random() * 0x10) + 0x1000; // ext offset 0x10
            self->step_s += 1;
        }
        MoveEntity();
        angle = self->rotate;
        self->opacity += 0xFF;
        if (self->facingLeft != 0) {
            angle = -angle;
        }
        self->velocityX += (rsin(angle) * self->ext.unk8C) >> 0xC; // ext offset 0x10
        self->velocityY += (-self->ext.unk8C * rcos(angle)) >> 0xC; // ext offset 0x10
        animResult = AnimateEntity(self->ext.unk80, self); // ext offset 0x04
        if (animResult == 0) {
            DestroyEntity(self);
        }
        return;
    case 4:
        if (self->step_s == 0) {
            self->drawFlags = 8;
            self->opacity = 0x80;
            self->facingLeft = Random() & 1;
            self->velocityX = (Random() << 9) + 0xFFFF0000;
            self->velocityY = -0x28000;
            self->ext.unk90 = -(Random() * 0x10) - 0x1000; // ext offset 0x14
            self->step_s += 1;
        }
        MoveEntity();
        self->velocityY += self->ext.unk90; // ext offset 0x14
        self->opacity += 0xFF;
        animResult = AnimateEntity(self->ext.unk80, self); // ext offset 0x04
        if (animResult == 0) {
            DestroyEntity(self);
        }
        return;
    }
}