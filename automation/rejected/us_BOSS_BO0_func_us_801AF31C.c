/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO0:func_us_801AF31C
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: quality reject: `Entity` has no member `unkAA`; 0xAA falls inside `ext` (0x7C)

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
extern void InitializeEntity(u16* stateEventList);
extern void MoveEntity(void);
extern void PlaySfxPositional(s16 sfxId, ...);

void func_us_801AF31C(Entity* arg0) {
    Primitive* prim;
    s16 x;
    s16 y;
    u16 abs_x;
    s16 primIndex;
    s16 hitWidth;
    s16 unkAA_abs;

    switch (arg0->step) {
    case 0:
        InitializeEntity(&D_us_801806FC);
        if (arg0->facingLeft != 0) {
            x = arg0->posX.i.hi + 0x1C;
        } else {
            x = arg0->posX.i.hi - 0x1C;
        }
        arg0->posX.i.hi = x;
        arg0->posY.i.hi -= 0xC;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 1);
        if (primIndex != -1) {
            prim = &g_PrimBuf[primIndex];
            arg0->primIndex = primIndex;
            arg0->ext.prim = prim;
            arg0->flags |= 0x800000;
            prim->tpage = 0x12;
            prim->clut = 0x212;
            prim->u3 = 0xD0;
            prim->u1 = 0xD0;
            prim->v2 = 0xA0;
            prim->v0 = 0xA0;
            prim->b0 = 0;
            prim->b1 = 0;
            prim->b2 = 0;
            prim->v1 = 0x10;
            prim->v3 = 0x10;
            prim->x0 = arg0->posX.i.hi;
            prim->x1 = arg0->posX.i.hi;
            prim->x2 = arg0->posX.i.hi;
            prim->x3 = arg0->posX.i.hi;
            prim->y0 = arg0->posY.i.hi;
            prim->y1 = arg0->posY.i.hi;
            prim->y2 = arg0->posY.i.hi;
            prim->y3 = arg0->posY.i.hi;
            prim->r1 = 0xA0;
            prim->g1 = 0xA0;
            prim->unk1C = prim->r0;
            prim->unk28 = prim->r2;
            prim->drawMode = 0x37;
            prim->priority = arg0->zPriority + 4;
            arg0->velocityY = 0;
            if (arg0->facingLeft != 0) {
                arg0->velocityX = -0x8000;
                arg0->unkAA = -0x30; // Entity ext offset 0x2E
            } else {
                arg0->velocityX = 0x8000;
                arg0->unkAA = 0x30; // Entity ext offset 0x2E
            }
            arg0->hitboxWidth = 0;
            arg0->hitboxHeight = 5;
            PlaySfxPositional(0x7D1, prim);
        }
        break;
    case 1:
        MoveEntity();
        if (arg0->facingLeft != 0) {
            arg0->velocityX -= 0x2000;
            arg0->unkA8 = arg0->unkA8 + 0xFFFB0000; // Entity ext offset 0x2C
        } else {
            arg0->velocityX += 0x2000;
            arg0->unkA8 = arg0->unkA8 + 0x50000; // Entity ext offset 0x2C
        }
        prim = arg0->ext.prim;
        prim->x1 = arg0->posX.i.hi + arg0->unkAA;
        prim->x3 = arg0->posX.i.hi + arg0->unkAA;
        prim->x0 = arg0->posX.i.hi;
        prim->x2 = arg0->posX.i.hi;
        y = arg0->posY.i.hi;
        prim->y0 = y - 8;
        prim->y1 = y - 8;
        prim->y2 = y + 8;
        prim->y3 = y + 8;
        unkAA_abs = arg0->unkAA;
        if (unkAA_abs < 0) {
            unkAA_abs = -unkAA_abs;
        }
        if (unkAA_abs < 0) {
            unkAA_abs += 3;
        }
        arg0->hitboxWidth = unkAA_abs >> 2;
        unkAA_abs = arg0->unkAA;
        if (unkAA_abs < 0) {
            unkAA_abs = -unkAA_abs;
        }
        arg0->hitboxOffX = unkAA_abs - arg0->hitboxWidth - 4;
        break;
    }

    abs_x = arg0->posX.i.hi;
    if (abs_x < 0) {
        abs_x = -abs_x;
    }
    if (abs_x >= 0x281) {
        DestroyEntity(arg0);
    }
}