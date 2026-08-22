/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BE79C
   attempt: 4/4
   model  : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
72:src/boss/bo6/us_3E79C.c:16: `RIC_posX_i_hi' undeclared (first use this function)
73:src/boss/bo6/us_3E79C.c:16: (Each undeclared identifier is reported only once
74:src/boss/bo6/us_3E79C.c:16: for each function it appears in.)
75:src/boss/bo6/us_3E79C.c:18: `RIC_posY_i_hi' undeclared (first use this function)
76:src/boss/bo6/us_3E79C.c:50: `RIC_zPriority' undeclared (first use thi

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
// Boss entity that tracks player position, draws an expanding/fading quad, then self-destructs.
/* Mechanical symbol repair from escalation_triage.py. */
extern s16 RIC_posX_i_hi;

/* Mechanical symbol repair from escalation_triage.py. */
extern s16 RIC_posY_i_hi;

void func_us_801BE79C(Entity* entity) {
    u16 step;
    Primitive* prim;
    s16 primIndex;
    u8 alpha;
    u16 halfWidth;
    u16 halfHeight;

    // Entity offsets 0x7C and 0x7E (ext union, no named variant provided)
    struct { u16 unk7C; u16 unk7E; } *extData = (void*)&entity->ext;

    entity->posX.i.hi = RIC_posX_i_hi;
    step = entity->step;
    entity->posY.i.hi = RIC_posY_i_hi - 8;
    switch (step) {
    case 0:
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 1);
        entity->primIndex = primIndex;
        if (primIndex != -1) {
            extData->unk7C = 0x10;
            extData->unk7E = 0xC;
            prim = &g_PrimBuf[primIndex];
            prim->u2 = 0x40;
            prim->u0 = 0x40;
            prim->v1 = 0xC0;
            prim->v0 = 0xC0;
            prim->u3 = 0x7F;
            prim->u1 = 0x7F;
            prim->v3 = 0xFF;
            prim->v2 = 0xFF;
            prim->b3 = 0x80;
            prim->g3 = 0x80;
            prim->r3 = 0x80;
            prim->b2 = 0x80;
            prim->g2 = 0x80;
            prim->r2 = 0x80;
            prim->b1 = 0x80;
            prim->g1 = 0x80;
            prim->r1 = 0x80;
            prim->b0 = 0x80;
            prim->g0 = 0x80;
            prim->r0 = 0x80;
            prim->tpage = 0x1A;
            prim->clut = 0x160;
            prim->drawMode = 0x35;
            prim->priority = RIC_zPriority + 8;
            entity->flags = 0x18800000;
            entity->step += 1;
        } else {
            DestroyEntity(entity);
            return;
        }
        break;
    case 1:
        extData->unk7C += 2;
        extData->unk7E += 2;
        if ((s16)extData->unk7C >= 0x39) {
            DestroyEntity(entity);
            return;
        }
        break;
    }

    // Update primitive vertices and fade alpha
    prim = &g_PrimBuf[entity->primIndex];
    halfWidth = extData->unk7C;
    halfHeight = extData->unk7E;
    prim->x0 = (u16)entity->posX.i.hi - halfWidth;
    prim->y0 = (u16)entity->posY.i.hi - halfHeight;
    prim->x1 = (u16)entity->posX.i.hi + halfWidth;
    prim->y1 = (u16)entity->posY.i.hi - halfHeight;
    prim->x2 = (u16)entity->posX.i.hi - halfWidth;
    prim->y2 = (u16)entity->posY.i.hi + halfHeight;
    prim->x3 = (u16)entity->posX.i.hi + halfWidth;
    prim->y3 = (u16)entity->posY.i.hi + halfHeight;
    if ((u8)prim->b3 >= 0xC) {
        // Fade alpha by -12 (0xF4 as signed 8-bit)
        alpha = prim->b3 + 0xF4;
    } else {
        alpha = prim->b3;
    }
    prim->g3 = alpha;
    prim->r3 = alpha;
    prim->b2 = alpha;
    prim->g2 = alpha;
    prim->r2 = alpha;
    prim->b1 = alpha;
    prim->g1 = alpha;
    prim->r1 = alpha;
    prim->b0 = alpha;
    prim->g0 = alpha;
    prim->r0 = alpha;
}