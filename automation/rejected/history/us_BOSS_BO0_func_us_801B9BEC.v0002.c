/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B9BEC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/3053C.c
   verdict: BUILD FAILED:
78:src/boss/bo0/3053C.c:586: `D_us_8018072C' undeclared (first use this function)
79:src/boss/bo0/3053C.c:586: (Each undeclared identifier is reported only once
80:src/boss/bo0/3053C.c:586: for each function it appears in.)
81:src/boss/bo0/3053C.c:593: union has no member named `unkA4'
82:src/boss/bo0/3053C.c:602: `D_us_801812F8' undeclared (first use this function)
83:src/boss/bo0/3053C.c:602: union has no member named `unkAD'
84:src/boss/bo0/3053C.c:638: `D_us_801812E4' undeclared (first use this function)
85-[77/356] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/borbo5.map -T build/us/borbo5.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.borbo5.txt -T build/us/config/undefined_syms_auto.us.borbo5.txt -o build/us/borbo5.elf
86-[78/356] psx cc src/st/cat/gfx_data.c

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
extern s32 D_us_8018072C[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/0.data.s, size 0xc */
extern s16 D_us_801812F8[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/BA8.data.s, size 0x8 */
extern s32 D_us_801812E4[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/BA8.data.s, size 0x14 */

void func_us_801B9BEC(Entity* arg0) {
    Entity* newEntity;
    Primitive* prim;
    Primitive* primNext;
    s16 angle;
    s16 parentAngle;
    s32 velocity;
    u16 step;
    s32 primIndex;
    s32 tileX;
    s32 tileY;

    if (arg0->flags & 0x100) {
        newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[0x1780 / sizeof(Entity)]);
        if (newEntity != NULL) {
            CreateEntityFromEntity(2, arg0, newEntity);
            newEntity->params = 0;
        }
        DestroyEntity(arg0);
        return;
    }

    step = arg0->step;
    switch (step) {
    case 0:
        InitializeEntity(&D_us_8018072C);
        arg0->animSet = 9;
        arg0->animCurFrame = 1;
        arg0->hitboxWidth = 5;
        arg0->hitboxHeight = 5;
        arg0->scaleX = 0x140;
        arg0->drawFlags |= 5;
        parentAngle = ((Entity*)arg0->ext.unkA4)->rotate - 0x100;
        arg0->rotate = parentAngle;
        if (arg0->facingLeft != 0) {
            angle = parentAngle;
        } else {
            angle = 0x800 - parentAngle;
        }
        arg0->posX.i.hi += (rcos(angle) * 16) >> 12;
        arg0->posY.i.hi += -(rsin(angle) * 16) >> 12;
        velocity = D_us_801812F8[arg0->ext.unkAD];
        arg0->velocityX = (s16)velocity * rcos(angle);
        arg0->velocityY = -(s16)velocity * rsin(angle);
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 2);
        if (primIndex == -1) {
            DestroyEntity(arg0);
            return;
        }
        prim = &g_PrimBuf[primIndex];
        arg0->primIndex = primIndex;
        arg0->ext.prim = prim;
        arg0->flags |= 0x800000;
        UnkPolyFunc2(prim, primIndex);
        prim->tpage = 0x1A;
        prim->clut = 0x16D;
        prim->u1 = 0xE0;
        prim->u0 = 0xE0;
        prim->u3 = 0xC0;
        prim->u2 = 0xC0;
        prim->v2 = 0x80;
        prim->v0 = 0x80;
        prim->v3 = 0x90;
        prim->v1 = 0x90;
        primNext = prim->next;
        primNext->p2 = 0x34;
        primNext->p3 = 0x16;
        primNext->tpage = (u16)(-angle);
        primNext->b3 = 0x60;
        primNext->x1 = arg0->posX.i.hi;
        primNext->y0 = arg0->posY.i.hi;
        prim->drawMode = 0x37;
        prim->priority = arg0->zPriority + 1;
        g_api_PlaySfx(0x652);
        return;
    case 1:
        MoveEntity();
        AnimateEntity(&D_us_801812E4, arg0);
        prim = arg0->ext.prim;
        primNext = prim->next;
        primNext->x1 = arg0->posX.i.hi;
        primNext->y0 = arg0->posY.i.hi;
        if (arg0->facingLeft != 0) {
            angle = arg0->rotate;
        } else {
            angle = 0x800 - arg0->rotate;
        }
        primNext->x1 -= (rcos(angle) * 24) >> 12;
        primNext->y0 -= -(rsin(angle) * 24) >> 12;
        UnkPrimHelper(prim, primNext);
        prim->v3++;
        prim->v1 = prim->v3;
        prim->v2++;
        prim->v0 = prim->v2;
        if (prim->v1 == 0xB0) {
            prim->v2 = 0x80;
            prim->v0 = 0x80;
            prim->v3 = 0x90;
            prim->v1 = 0x90;
        }
        prim->r0 = 0;
        prim->g0 = 0;
        prim->b0 = 0;
        prim->r2 = 0;
        prim->g2 = 0;
        prim->b2 = 0;
        tileX = (g_Tilemap.scrollX.i.hi + arg0->posX.i.hi) - 0x30;
        tileY = (g_Tilemap.scrollY.i.hi + arg0->posY.i.hi) - 0x50;
        if ((u16)tileX >= 0x1A1 || (u16)tileY >= 0x181) {
            arg0->flags |= 0x100;
        }
        return;
    }
}