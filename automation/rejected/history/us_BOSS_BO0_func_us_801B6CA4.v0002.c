/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B6CA4
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
108:src/boss/bo0/2D26C.c:165: `D_us_80180708' undeclared (first use this function)
109:src/boss/bo0/2D26C.c:165: (Each undeclared identifier is reported only once
110:src/boss/bo0/2D26C.c:165: for each function it appears in.)
111:src/boss/bo0/2D26C.c:196: union has no member named `unk1B8'
112:src/boss/bo0/2D26C.c:196: structure has no member named `unk89E'
113:src/boss/bo0/2D26C.c:

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
extern s32 D_us_80180708[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/0.data.s, size 0xc */

void func_us_801B6CA4(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 temp;
    s32 var_a0;
    s32 var_a1;
    s32 var_a2;
    s32 var_a3;
    s16 var_v0;
    s16 var_v1;
    s16 var_v1_2;
    s8 temp_v0;
    u16 temp_v1;
    u16 temp_v1_2;
    u16 temp_v1_4;
    u16 var_v0_3;

    // unk02 and unk06 are inside posX/posY (f32), reading part of that word.
    self->facingLeft = *(u16*)((s8*)self + 0x14); // unk14 -> facingLeft
    self->palette = *(u16*)((s8*)self + 0x16); // unk16 -> palette
    if (*(u8*)((s8*)self + 0x489) == 0) { // unk-489
        *(u8*)((s8*)self + 0x9A) = 0; // unk9A
        if (*(u32*)((s8*)self + 0xF0) & 0x100) { // unkF0
            *(u8*)((s8*)self + 0x9A) = 2;
        }
        if (*(u32*)((s8*)self + 0x1AC) & 0x100) { // unk1AC
            *(u8*)((s8*)self + 0x9A) = *(u8*)((s8*)self + 0x9A) | 1;
        }
        if ((*(u8*)((s8*)self + 0x9A) != 0) && (self->step != 0xA)) {
            self->step = 9;
        }
    }
    if (self->flags & 0x100) {
        self->hitboxState = 0;
    }
    temp_v1 = self->step;
    switch (temp_v1) {
    case 0:
        InitializeEntity(&D_us_80180708);
        self->hitboxWidth = 0xC;
        self->hitboxHeight = 8;
        self->hitboxOffX = 0;
        self->hitboxOffY = 8;
        self->animCurFrame = 0;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 6);
        if (primIndex == -1) {
            self->step = 0;
        } else {
            prim = &g_PrimBuf[primIndex];
            self->primIndex = primIndex;
            self->ext.prim = prim;
            self->flags |= 0x800000;
            if (prim != NULL) {
                do {
                    prim->drawMode = 8;
                    prim = prim->next;
                } while (prim != NULL);
            }
            *(s16*)((s8*)self + 0x88) = 0x180; // unk88
            *(s16*)((s8*)self + 0x8C) = -0x180; // unk8C
            *(s16*)((s8*)self + 0x80) = 0x100; // unk80
            *(s16*)((s8*)self + 0x84) = -0x80; // unk84
            *(u8*)((s8*)self + 0x91) = 0x1D; // unk91
            *(u8*)((s8*)self + 0x90) = 0x21; // unk90
            *(u8*)((s8*)self + 0x94) = 0; // unk94
        }
        // fall through
    case 1:
        self->step_s = 0;
        self->ext.unk1B8 = g_api_enemyDefs->unk89E; // unk1B8
        break;
    case 2:
        temp_v1_2 = self->step_s;
        *(u8*)((s8*)self + 0x94) = 0; // unk94
        switch (temp_v1_2) {
        case 0:
            *(u8*)((s8*)self + 0x91) = 0x1D; // unk91
            *(u8*)((s8*)self + 0x90) = 0x21; // unk90
            if (func_us_801B6520(0x100100, 0x10FD00, 0x10FFC0, 0x10FE00, -0x40, 0x10, -0x200, 0x10, 0x100, 0x10, -0x300, 0x10) != 0) {
                self->step_s = 1;
            }
            break;
        case 1:
            if (func_us_801B6520(0x100000, 0x10FD80, 0x100080, 0x10FD00, 0x80, 0x10, -0x300, 0x10, 0, 0x10, -0x280, 0x10) != 0) {
                self->step_s = 0;
            }
            break;
        }
        break;
    case 3:
        var_a0 = 0x100100;
        var_a1 = 0x10FD80;
        var_a2 = 0x100100;
        var_a3 = 0x10FD00;
        *(u8*)((s8*)self + 0x91) = 0x1F; // unk91
        var_v1 = 0x10;
        *(u8*)((s8*)self + 0x90) = 0x20; // unk90
        *(u8*)((s8*)self + 0x94) = 0; // unk94
        var_v0 = -0x280;
        goto block_63;
    case 4:
        *(u8*)((s8*)self + 0x91) = 0x1F; // unk91
        *(u8*)((s8*)self + 0x90) = 0x20; // unk90
        *(u8*)((s8*)self + 0x94) = 0; // unk94
        temp = func_us_801B6520(0x600200, 0x60FD00, 0x60FDC0, 0x60FDC0, -0x240, 0x60, -0x240, 0x60, 0x200, 0x60, -0x300, 0x60);
        if (*(s16*)((s8*)self + 0x88) < 0x80) { // unk88
            *(u8*)((s8*)self + 0x49B) = 0; // unk-49B
        }
        if (*(s16*)((s8*)self + 0x88) < -0x80) { // unk88
            *(u8*)((s8*)self + 0x49B) = 3; // unk-49B
        }
        self->ext.unk1B8 = g_api_enemyDefs->unk8EE; // unk1B8
        if (temp != 0) {
            temp_v0 = *(u8*)((s8*)self + 0x93); // unk93
            if (temp_v0 < 0x60) {
                *(u8*)((s8*)self + 0x93) = temp_v0 + 0x10; // unk93
            } else {
                self->step = 5;
                self->ext.unk1B8 = g_api_enemyDefs->unk89E; // unk1B8
                PlaySfxPositional(0x7C8);
            }
        }
        break;
    case 5:
        temp_v0 = *(u8*)((s8*)self + 0x93); // unk93
        *(u8*)((s8*)self + 0x94) = 0; // unk94
        if (temp_v0 > 0) {
            *(u8*)((s8*)self + 0x93) = temp_v0 - 0xC; // unk93
        } else {
            *(u8*)((s8*)self + 0x93) = 0; // unk93
            self->step = 1;
        }
        break;
    case 11:
        var_a0 = 0x20FE00;
        var_a1 = 0x20FC00;
        var_a2 = 0x180280;
        var_a3 = 0x18FE00;
        *(u8*)((s8*)self + 0x94) = 1; // unk94
        *(u8*)((s8*)self + 0x91) = 0x1F; // unk91
        *(u8*)((s8*)self + 0x90) = 0x20; // unk90
        var_v1 = 0x20;
        var_v0 = -0x400;
        goto block_63;
    case 12:
        temp_v0 = *(u8*)((s8*)self + 0x93); // unk93
        *(u8*)((s8*)self + 0x94) = 1; // unk94
        *(u8*)((s8*)self + 0x91) = 0x1D; // unk91
        *(u8*)((s8*)self + 0x90) = 0x21; // unk90
        if (temp_v0 < 0x40) {
            *(u8*)((s8*)self + 0x93) = temp_v0 + 8; // unk93
        }
        var_v0 = func_us_801B6520(0x400180, 0x40FE00, 0x60FB00, 0x78F880, -0x500, 0x60, -0x780, 0x78, 0x180, 0x40, -0x200, 0x40);
        self->ext.unk1B8 = g_api_enemyDefs->unk916; // unk1B8
        goto block_64;
    case 13:
        *(u8*)((s8*)self + 0x94) = 1; // unk94
        temp_v0 = *(u8*)((s8*)self + 0x93) - 0xC; // unk93
        *(u8*)((s8*)self + 0x93) = temp_v0; // unk93
        var_a0 = 0x400000;
        if (temp_v0 & 0x80) {
            *(u8*)((s8*)self + 0x93) = 0; // unk93
        }
        var_a1 = 0x40FF80;
        var_a2 = 0x400100;
        var_a3 = 0x50FE00;
        *(u8*)((s8*)self + 0x91) = 0x1F; // unk91
        *(u8*)((s8*)self + 0x90) = 0x21; // unk90
        var_v1 = 0x40;
        var_v0 = -0x80;
        goto block_63;
    case 14:
        *(u8*)((s8*)self + 0x94) = 1; // unk94
        *(u8*)((s8*)self + 0x91) = 0x1F; // unk91
        *(u8*)((s8*)self + 0x90) = 0x20; // unk90
        temp_v0 = *(u8*)((s8*)self + 0x93) - 0xC; // unk93
        *(u8*)((s8*)self + 0x93) = temp_v0; // unk93
        if (temp_v0 & 0x80) {
            *(u8*)((s8*)self + 0x93) = 0; // unk93
        }
        var_a0 = 0x200100;
        var_a1 = 0x20FD00;
        var_a2 = 0x20FF80;
        var_a3 = 0x20FE00;
        var_v1 = 0x20;
        var_v0 = -0x300;
        goto block_63;
    case 6:
        var_a0 = 0x200000;
        var_a1 = 0x20FC80;
        var_a2 = 0x200080;
        var_a3 = 0x20FD80;
        *(u8*)((s8*)self + 0x91) = 0x1F; // unk91
        *(u8*)((s8*)self + 0x90) = 0x20; // unk90
        var_v1 = 0x20;
        *(u8*)((s8*)self + 0x94) = 0; // unk94
        var_v0 = -0x380;
        goto block_63;
    case 7:
        var_a0 = 0x100000;
        var_a1 = 0x10FE00;
        var_a2 = 0x100100;
        var_a3 = 0x10FF00;
        *(u8*)((s8*)self + 0x94) = 1; // unk94
        *(u8*)((s8*)self + 0x91) = 0x1D; // unk91
        *(u8*)((s8*)self + 0x90) = 0x20; // unk90
        var_v1 = 0x10;
        var_v0 = -0x200;
        goto block_63;
    case 8:
        var_a0 = 0x200000;
        var_a1 = 0x20FEC0;
        var_a2 = 0x200180;
        var_a3 = 0x20FF00;
        *(u8*)((s8*)self + 0x94) = 1; // unk94
        *(u8*)((s8*)self + 0x91) = 0x1F; // unk91
        *(u8*)((s8*)self + 0x90) = 0x21; // unk90
        var_v1 = 0x20;
        var_v0 = -0x140;
        goto block_63;
    case 9:
        *(u8*)((s8*)self + 0x94) = 1; // unk94
        *(u8*)((s8*)self + 0x90) = 0x20; // unk90
        if (*(u8*)((s8*)self + 0x9A) == 2) { // unk9A
            var_v1_2 = 0x18;
        } else {
            var_v1_2 = 0x10;
        }
        *(u8*)((s8*)self + 0x91) = 0x1D; // unk91
        if (*(u8*)((s8*)self + 0x9A) == 1) { // unk9A
            var_v1_2 = 0x18;
        } else {
            var_v1_2 = 0x10;
        }
        func_us_801B6520(
            *(s32*)((s8*)self + 0x10) | (*(s32*)((s8*)self + 0x10) << 0x10),
            *(s32*)((s8*)self + 0x18) | (*(s32*)((s8*)self + 0x18) << 0x10),
            *(s32*)((s8*)self + 0x20) | (*(s32*)((s8*)self + 0x20) << 0x10),
            *(s32*)((s8*)self + 0x28) | (*(s32*)((s8*)self + 0x28) << 0x10),
            var_v1_2, -0x100, var_v1_2);
        if (*(u8*)((s8*)self + 0x9A) == 0) { // unk9A
            self->step = 1;
        }
        break;
    case 15:
        var_a0 = 0x200000;
        var_a1 = 0x20FE00;
        var_a2 = 0x200080;
        var_a3 = 0x20FF00;
        *(u8*)((s8*)self + 0x94) = 1; // unk94
        *(u8*)((s8*)self + 0x91) = 0x1D; // unk91
        *(u8*)((s8*)self + 0x90) = 0x20; // unk90
        var_v1 = 0x20;
        var_v0 = -0x200;
        goto block_63;
    case 10:
        temp_v1_4 = self->step_s;
        switch (temp_v1_4) {
        case 0:
            if (*(u8*)((s8*)self + 0x489) == 2) { // unk-489
                var_v0_3 = self->step_s + 1;
                self->step_s = var_v0_3;
            }
            break;
        case 1:
            *(u8*)((s8*)self + 0x94) = 1; // unk94
            *(u8*)((s8*)self + 0x91) = 0x1D; // unk91
            *(u8*)((s8*)self + 0x90) = 0x21; // unk90
            if (func_us_801B6520(0x10FF00, 0x10FC00, 0x10FE00, 0x10FD00, -0x200, 0x10, -0x300, 0x10, -0x100, 0x10, -0x400, 0x10) != 0) {
                self->step_s = self->step_s + 1;
            }
            if (*(u8*)((s8*)self + 0x489) == 3) { // unk-489
                self->step_s = 3;
            }
            break;
        case 2:
            *(u8*)((s8*)self + 0x94) = 1; // unk94
            *(u8*)((s8*)self + 0x91) = 0x1D; // unk91
            *(u8*)((s8*)self + 0x90) = 0x21; // unk90
            func_us_801B6520(0xA0100, 0xAFE00, 0x60000, 0x6FF00, 0, 6, -0x100, 6, 0x100, 0xA, -0x200, 0xA);
            if (*(u8*)((s8*)self + 0x489) == 3) { // unk-489
                self->step_s = 3;
            }
            break;
        }
        break;
    }

block_63:
    var_v0 = func_us_801B6520(var_a0, var_a1, var_a2, var_a3, var_v1, var_v0, var_v1);

block_64:
    if (var_v0 != 0) {
block_65:
        self->step = 1;
    }

    func_us_801B65C0(
        *(s32*)((s8*)self + 0x10) | (*(s32*)((s8*)self + 0x10) << 0x10),
        self->ext.prim,
        func_us_801B65C0(
            *(s32*)((s8*)self + 0x10) | (*(s32*)((s8*)self + 0x10) << 0x10),
            self->ext.prim,
            1,
            *(u16*)((s8*)self + 0x02), // unk02 (inside posX)
            *(u16*)((s8*)self + 0x06)), // unk06 (inside posY)
        0,
        *(u16*)((s8*)self + 0x02), // unk02 (inside posX)
        *(u16*)((s8*)self + 0x06)); // unk06 (inside posY)

    if (self->palette & 0x8000) {
        prim = self->ext.prim;
        if (prim != NULL) {
            do {
                prim->clut = self->palette & 0xFFF;
                prim = prim->next;
            } while (prim != NULL);
        }
    }
    if (*(u8*)((s8*)self + 0x489) != 0) { // unk-489
        prim = self->ext.prim;
        if (prim != NULL) {
            do {
                prim->tpage = 0x15;
                prim->clut = 0x219;
                prim = prim->next;
            } while (prim != NULL);
        }
    }
}