/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B619C
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/3053C.c
   verdict: quality reject: 5 raw byte-pointer cast(s) like `*(u16*)((u8*)p + N)`; use the real struct and named members instead

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
extern s32 D_us_801CE5B0;
extern s32 D_us_80180708[];
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
extern GAME_IMPORT Primitive g_PrimBuf[MAX_PRIM_COUNT];
extern s32 D_us_801812D0[];
extern s32 D_us_80181288[];
extern u8 D_us_80181298[];
extern u8 D_us_801812A8[];
extern AnimationFrame* D_us_801812B8[];
void InitializeEntity(u16 arg0[]);
s32 func_us_801B5D6C(void*, s32, s32);
s32 func_us_801B5E08(void*, void*, s32);
void func_us_801B5E8C(void);

void func_us_801B619C(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 temp;
    s16* unk88Ptr;
    s32 i;
    u8 unk80Val;

    self->facingLeft = *(u16*)((u8*)self - 0x2DC);
    self->palette = *(u16*)((u8*)self - 0x2DA);

    if (D_us_801CE5B0 == 0) {
        self->posX.val = *(s32*)((u8*)self - 0x2F0);
        self->posY.val = *(s32*)((u8*)self - 0x2EC);
        if (self->facingLeft == 0) {
            self->posX.i.lo += 4;
        } else {
            self->posX.i.lo -= 4;
        }
    }

    if (self->flags & 0x100) {
        self->hitboxState = 0;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180708);
        self->hitboxState = 0;
        self->animCurFrame = 0;
        self->flags |= 0x08000000;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 8);
        if (primIndex == -1) {
            self->step = 0;
            break;
        }
        self->primIndex = primIndex;
        self->ext.unk80 = (s32)(&g_PrimBuf[primIndex]);
        self->flags |= 0x800000;
        prim = &g_PrimBuf[primIndex];
        for (i = 0; i < 8; i++) {
            prim->u0 = -0x80;
            prim->u2 = -0x80;
            prim->tpage = 0x14;
            prim->clut = 0x20B;
            prim->u1 = -0x75;
            prim->u3 = -0x75;
            prim->v0 = 0x50;
            prim->v1 = 0x50;
            prim->v2 = 0x60;
            prim->v3 = 0x60;
            prim->priority = 0xA1;
            prim->drawMode = 2;
            prim = prim->next;
        }
        unk88Ptr = (s16*)&self->ext.unk80 + 2;
        for (i = 0; i < 8; i++) {
            unk88Ptr[0] = -0x180;
            unk88Ptr += 2;
        }
        self->ext.unk84 = 0;
        /* fallthrough */
    case 1:
        if (D_us_801CE5B0 == 0) {
            self->step++;
        }
        break;
    case 2:
        temp = self->ext.unk84;
        if (temp < 0x1000) {
            self->ext.unk84 = temp + 0x200;
        } else {
            self->ext.unk84 = 0x1000;
            self->step++;
        }
        break;
    case 3:
        unk80Val = self->ext.unk80;
        temp = func_us_801B5E08(&self->ext.unk80 + 2, (void*)D_us_801812D0[unk80Val], 0x20);
        if (temp & 0xFF) {
            self->ext.unk80 ^= 1;
        }
        break;
    case 4:
        func_us_801B5E08(&self->ext.unk80 + 2, D_us_80181288, 0x20);
        break;
    case 5:
        break;
    case 6:
        func_us_801B5E08(&self->ext.unk80 + 2, D_us_80181298, 0x60);
        break;
    case 7:
        func_us_801B5E08(&self->ext.unk80 + 2, D_us_801812A8, 0x80);
        break;
    case 8:
        func_us_801B5E08(&self->ext.unk80 + 2, D_us_801812B8, 0x60);
        break;
    case 9:
        unk80Val = self->ext.unk80;
        temp = func_us_801B5D6C(&self->ext.unk80 + 2, (void*)D_us_801812D0[unk80Val], 0x40);
        if (temp & 0xFF) {
            self->ext.unk80 ^= 1;
        }
        break;
    }

    func_us_801B5E8C();

    if (self->palette & 0x8000) {
        prim = (Primitive*)self->ext.unk80;
        if (prim != NULL) {
            do {
                prim->clut = self->palette & 0xFFF;
                prim = prim->next;
            } while (prim != NULL);
        }
    }

    if (*(u8*)((u8*)self - 0x255) != 0) {
        prim = (Primitive*)self->ext.unk80;
        if (prim != NULL) {
            do {
                prim->tpage = 0x15;
                prim->clut = 0x219;
                prim = prim->next;
            } while (prim != NULL);
        }
    }
}