/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO6:func_us_801C488C
   attempt: 4/4
   model  : opencode/deepseek-v4-flash-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:

   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
/* func_us_801C488C - BO6 boss warning shot: allocates a warning-beacon primitive,
   drifts it downward, and destroys the entity when the primitive is gone. */
s32 func_us_801BB5BC(Primitive *primitive, s16 x, s16 y); /* extern */

void func_us_801C488C(Entity *entity) {
    Primitive *prim;
    s32 idx;

    if (entity->step == 0) {
        /* Allocate one GT4 primitive for the shot's glow flare. */
        idx = g_api_AllocPrimitives(PRIM_GT4, 1);
        entity->primIndex = (s32) idx;
        if (idx != -1) {
            entity->flags = 0x08800000;          /* ENT_DROPS | high range flag */
            entity->velocityY = 0x8000;          /* fixed-point Y drift 0.5 */
            /* Random jitter around the spawn point, upper 16 bits of the float are
             * an integer coordinate (m2c's posX.i.hi is offset +0x2). */
            entity->posX.i.hi = entity->posX.i.hi - 8 + (rand() & 0xF);
            entity->posY.i.hi = entity->posY.i.hi - 4 + (rand() & 0xF);

            prim = &g_PrimBuf[entity->primIndex];
            prim->clut = 0x1B0;
            prim->tpage = 0x1A;
            prim->b0 = 0;
            prim->b1 = 0;
            prim->drawMode = 0x31;              /* DRAWMODE blend start? */
            prim->priority = entity->zPriority + 4;
            func_us_801BB5BC(prim, (s16) entity->posX.i.hi, (s16) entity->posY.i.hi);
            entity->step++;
            return;
        }
        DestroyEntity(entity);
        return;
    }

    /* Apply the constant Y drift, then keep the flare glued to the camera palm. */
    entity->posY.val += entity->velocityY;
    if (func_us_801BB5BC(&g_PrimBuf[entity->primIndex],
                         (s16) entity->posX.i.hi, (s16) entity->posY.i.hi) != 0) {
        DestroyEntity(entity);
    }
}