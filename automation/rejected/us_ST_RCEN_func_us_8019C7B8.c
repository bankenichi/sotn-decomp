/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RCEN:func_us_8019C7B8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_shaft.c
   verdict: BUILD FAILED:
ed `unk8C'
115:src/st/rcen/e_shaft.c:199: union has no member named `unk8C'
116:src/st/rcen/e_shaft.c:201: union has no member named `unk8C'
117:src/st/rcen/e_shaft.c:213: union has no member named `unk86'
118:src/st/rcen/e_shaft.c:215: union has no member named `unk86'
119:src/st/rcen/e_shaft.c:219: union has no member named `unk86'
120:src/st/rcen/e_shaft.c:223: union has no member

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
/* func_us_8019C7B8: Spawns interactive particles that follow the player and create secondary entities. */
void func_us_8019C7B8(Entity* entity) {
        s16 angle;
        s16 speed;
        s32 step;
        s32 i;
        s32 randVal;
    Primitive* prim;
    Primitive* prim2;
    Entity* parent;
    Entity* target;
    Entity* newEntity;
    s32 primIndex;
    s16 dx, dy;
    s16 absDx, absDy;

    if (PrizeDrops & 4) {
        DestroyEntity(entity);
        return;
    }

    parent = entity->ext.unk9C; /* entity->ext.unk9C is the parent entity */
    entity->posX.i.hi = parent->posX.i.hi;
    entity->posY.i.hi = parent->posY.i.hi;

    if (parent->entityId == 0x1A && parent->step == 4) {
        step = entity->step;
        switch (step) {
        case 0:
            InitializeEntity(&g_EInitInteractable);
            primIndex = g_api_AllocPrimitives(PRIM_GT4, 0x14);
            if (primIndex == -1) {
                DestroyEntity(entity);
                return;
            }
            entity->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            entity->ext.unk80 = (u32)prim;
            entity->flags |= 0x800000;
            if (prim != NULL) {
                i = 0;
                do {
                    /* Set primitive UVs and colors */
                    prim->r0 = 0x50;
                    prim->g0 = 0x50;
                    prim->b0 = 0x50;
                    prim->u0 = (i * 0x10) - 0x70;
                    prim->u1 = (i * 0x10) - 0x70;
                    prim->u2 = (i * 0x10) - 0x60;
                    prim->u3 = (i * 0x10) - 0x60;
                    prim->v0 = 0xD0;
                    prim->v1 = 0xC0;
                    prim->v2 = 0xD0;
                    prim->v3 = 0xC0;
                    prim->tpage = 0x1A;
                    prim->clut = 0x194;
                    prim->drawMode = 8;
                    prim->priority = entity->zPriority;
                    /* Copy color to other vertices? Assembly copies unk4 to unk10, unk1C, unk28 */
                    /* These are likely r1,g1,b1 etc. We'll set them the same */
                    prim->r1 = prim->r0;
                    prim->g1 = prim->g0;
                    prim->b1 = prim->b0;
                    prim->r2 = prim->r0;
                    prim->g2 = prim->g0;
                    prim->b2 = prim->b0;
                    prim->r3 = prim->r0;
                    prim->g3 = prim->g0;
                    prim->b3 = prim->b0;
                    prim = prim->next;
                    i++;
                    if (i >= 6) i = 0;
                } while (prim != NULL);
            }
            entity->step = 1;
            break;
        case 1:
            prim = entity->ext.unk80;
            /* Set initial positions */
            prim->x0 = entity->posX.i.hi;
            prim->y0 = entity->posY.i.hi;
            prim->x1 = prim->x0;
            prim->y1 = prim->y0 - 0x10;
            prim->x2 = entity->posX.i.hi;
            prim->y2 = entity->posY.i.hi;
            prim->x3 = prim->x2;
            prim->y3 = prim->y2 - 0x10;
            entity->ext.unk80 = (u32)prim;
            /* Compute initial angle based on relative position of parent and target */
            target = entity->ext.unkA0;
            if (target->posX.i.hi - parent->posX.i.hi > 0) {
                speed = (rand() & 0x7FF) - 0x400;
            } else {
                speed = (rand() & 0x7FF) + 0x400;
            }
            entity->ext.unk84 = speed;
            /* Initialize all primitives */
            if (prim != NULL) {
                do {
                    prim->r0 = 0x50;
                    prim->g0 = 0x50;
                    prim->b0 = 0x50;
                    prim->drawMode = 8;
                    prim->r1 = prim->r0;
                    prim->g1 = prim->g0;
                    prim->b1 = prim->b0;
                    prim->r2 = prim->r0;
                    prim->g2 = prim->g0;
                    prim->b2 = prim->b0;
                    prim->r3 = prim->r0;
                    prim->g3 = prim->g0;
                    prim->b3 = prim->b0;
                    prim = prim->next;
                } while (prim != NULL);
            }
            entity->ext.unk8C = 0;
            entity->step = 2;
            break;
        case 2:
            /* Loop over primitives, update positions and create secondary entities */
            prim = entity->ext.unk80;
            target = entity->ext.unkA0;
            angle = entity->ext.unk84;
            /* Compute distance to target */
            dx = target->posX.i.hi - prim->x2;
            dy = target->posY.i.hi - prim->y2;
            absDx = dx;
            if (dx < 0) absDx = -dx;
            absDy = dy;
            if (dy < 0) absDy = -absDy;
            speed = 0;
            if (absDx < 0x10) {
                if (absDy < 0x10) {
                    /* Very close, skip distance check */
                } else {
                    goto mediumDistance;
                }
            } else {
            mediumDistance:
                if (absDx < 0x20) {
                    if (absDy < 0x20) {
                        speed = 1;
                    }
                }
                if (entity->ext.unk8C == 0) {
                    entity->ext.unk8C = 4;
                    if (speed != 0) {
                        entity->ext.unk8C = 2;
                    }
                    angle = ratan2(-dy, dx) - angle;
                    if (angle >= 0x801) {
                        angle -= 0x1000;
                    }
                    if (angle < -0x800) {
                        angle += 0x1000;
                    }
                    if (speed == 0) {
                        /* Far away: divide by 4 */
                        if (angle >= 0) {
                            entity->ext.unk86 = angle >> 2;
                        } else {
                            entity->ext.unk86 = (angle + 3) >> 2;
                        }
                    } else {
                        /* Medium distance: divide by 2 */
                        entity->ext.unk86 = (angle + (angle >> 31)) >> 1;
                    }
                }
                /* Update angle */
                angle = entity->ext.unk84 + entity->ext.unk86;
                if (speed == 0) {
                    /* Add random offset */
                    randVal = Random();
                    angle = (angle + 0x60) - ((randVal & 3) << 6);
                }
                entity->ext.unk84 = angle & 0xFFF;
                /* Move primitive to next in chain */
                prim2 = prim->next;
                if (prim2 != NULL) {
                    prim2->x0 = prim->x2;
                    prim2->y0 = prim->y2;
                    prim2->x1 = prim->x2;
                    prim2->y1 = prim->y2;
                    prim2->x2 = prim->x2;
                    prim2->y2 = prim->y2;
                    prim2->x3 = prim->x2;
                    prim2->y3 = prim->y2;
                    /* Update positions using trig */
                    dx = rcos(angle & 0xFFF);
                    dx = (dx * 12) >> 12;
                    dy = rsin(angle & 0xFFF);
                    dy = (dy * 12) >> 12;
                    prim2->x2 = (prim->x2 + dx) & 0xFFFF;
                    prim2->y2 = (prim->y2 - dy) & 0xFFFF;
                    /* Update second set of coordinates */
                    dx = rcos((angle - 0x400) & 0xFFF);
                    dx = (dx * 16) >> 12;
                    dy = rsin((angle - 0x400) & 0xFFF);
                    dy = (dy * 16) >> 12;
                    prim2->x3 = (prim2->x2 + dx) & 0xFFFF;
                    prim2->y3 = (prim2->y2 - dy) & 0xFFFF;
                    /* Check if near player */
                    dx = prim2->x3 - PLAYER_posX_i_hi;
                    if (dx < 0) dx = -dx;
                    dy = prim2->y3 - PLAYER_posY_i_hi;
                    if (dy < 0) dy = -dy;
                    if (dx < 0xC && dy < 0xC) {
                        /* Create secondary entity */
                        newEntity = AllocEntity(&g_Entities[0xA0], &g_Entities_192);
                        if (newEntity != NULL) {
                            CreateEntityFromCurrentEntity(0x1E, newEntity);
                            newEntity->posX.i.hi = prim2->x3;
                            newEntity->posY.i.hi = prim2->y3;
                        }
                    }
                    prim2->entityRoomIndex = 0x37;
                    entity->ext.unk8C--;
                    prim = prim2;
                    goto loop2;
                }
            }
            entity->step = 1;
            break;
        case 3:
            prim = entity->ext.unk80;
            if (prim != NULL) {
                do {
                    prim->drawMode = 8;
                    prim = prim->next;
                } while (prim != NULL);
            }
            entity->step = 1;
            break;
        }
    } else {
        DestroyEntity(entity);
    }
}