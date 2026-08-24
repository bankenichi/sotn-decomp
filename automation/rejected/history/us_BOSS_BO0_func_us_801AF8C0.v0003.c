/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801AF8C0
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
107:src/boss/bo0/2D26C.c:35: structure has no member named `unkA4'
108:src/boss/bo0/2D26C.c:42: `g_EInitOlroxAfterImage' undeclared (first use this function)
109:src/boss/bo0/2D26C.c:42: (Each undeclared identifier is reported only once
110:src/boss/bo0/2D26C.c:42: for each function it appears in.)
111:src/boss/bo0/2D26C.c:52: `D_us_80180D7C' undeclared (first use this function)
112:

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
extern EInit g_EInitOlroxAfterImage;

/* Mechanical symbol repair from escalation_triage.py. */
extern s32 D_us_80180D7C[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/BA8.data.s, size 0x18 */

void func_us_801AF8C0(Entity* entity) {
    Entity* child;
    s16 scale;
    u16 palette;

    if (entity->ext.afterImage.unkA4->flags & 0x100) {
        entity->step = 3;
        entity->flags |= 0x100;
    }

    switch (entity->step) {
    case 0:
        InitializeEntity(&g_EInitOlroxAfterImage);
        entity->animCurFrame = 0x54;
        entity->scaleY = 0;
        entity->scaleX = 0;
        entity->hitboxState = 0;
        entity->drawFlags |= 3;
        entity->zPriority -= 1;
        break;

    case 1:
        AnimateEntity(D_us_80180D7C, entity);
        if (entity->scaleX < 0x100) {
            scale = entity->scaleY + 8;
            entity->scaleY = scale;
            entity->scaleX = scale;
            return;
        }
        entity->scaleY = 0x100;
        entity->scaleX = 0x100;
        entity->step += 1;
        break;

    case 2:
        AnimateEntity(D_us_80180D7C, entity);
        if (g_Timer == (g_Timer / 12) * 12) {
            child = AllocEntity((Entity*)g_Entities_160, (Entity*)(g_Entities_160 + 0x5E0));
            if (child != NULL) {
                CreateEntityFromEntity(0x2F, entity, child);
                child->ext.afterImage.unkA4 = (u32)entity;
                PlaySfxPositional(0x691);
            }
        }
        palette = 0x8213;
        if (g_Timer == (g_Timer / 5) * 5) {
            palette = 0x8215;
        }
        entity->palette = palette;
        if (entity->ext.afterImage.unkA4->ext.afterImage.disableFlag != 0) {
            entity->step += 1;
        }
        break;

    case 3:
        AnimateEntity(D_us_80180D7C, entity);
        scale = entity->scaleY - 8;
        entity->scaleY = scale;
        entity->scaleX = scale;
        if (scale < 0) {
            DestroyEntity(entity);
        }
        break;
    }
}