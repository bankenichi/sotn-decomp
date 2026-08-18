/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RCEN:func_us_8019CDF8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_shaft.c
   verdict: quality reject: `Entity` has no member `unk80`; 0x80 falls inside `ext` (0x7C)

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
extern u32 PrizeDrops;
extern int rand(void);
extern Tilemap g_Tilemap;
extern void DestroyEntity(Entity* entity);
extern void InitializeEntity(u16*);
extern void SetStep(u8);
extern void MoveEntity(void);
extern void PlaySfxPositional(s16);
extern s32 rcos(s16 angle);
extern s32 rsin(s16 angle);
extern s16 ratan2(s32 x, s32 y);
extern s16 func_us_8019A98C(s16, s16, s16);
extern s32 Random(void);
extern Entity* AllocEntity(Entity*, Entity*);
extern void CreateEntityFromEntity(s16, Entity*, Entity*);
extern u16 D_us_8018057C[];
extern Entity g_Entities_96;

/* Shaft's heart floating enemy behavior */
void func_us_8019CDF8(Entity *entity) {
    Entity *newEntity;
    s16 angle;
    s16 targetAngle;
    s16 parentXHi;
    s16 parentYHi;
    s32 parentX;
    s32 parentY;
    u16 step;
    u16 step_s;

    if ((PrizeDrops & 4) && (entity->step != 4)) {
        SetStep(4);
    }

    step = entity->step;
    if (step < 5) {
        switch (step) {
        case 0:
            InitializeEntity(D_us_8018057C);
            entity->hitboxState = 0;
            /* unk80 at ext+0x04 */
            entity->unk80 = ((Random() & 0x1F) * 4) + 0x10;
            /* fall through to case 1 */
        case 1:
            /* unk80 at ext+0x04 */
            entity->unk80--;
            if (entity->unk80 == 0) {
                SetStep(2);
            }
            break;
        case 2:
            step_s = entity->step_s;
            switch (step_s) {
            case 0:
                entity->velocityY = 0xFFFA0000 - (rand() * 0x10);
                entity->animCurFrame = 0x2B;
                PlaySfxPositional(0x670);
                entity->step_s++;
                /* fall through to case 1 */
            case 1:
                MoveEntity();
                if (entity->posY.i.hi < 0xC0) {
                    /* unk80 at ext+0x04 */
                    entity->unk80 = 0x60;
                    entity->step_s++;
                }
                break;
            case 2:
                MoveEntity();
                entity->velocityY -= (entity->velocityY >> 4);
                /* unk80 at ext+0x04 */
                entity->unk80--;
                if (entity->unk80 == 0) {
                    entity->hitboxState = 2;
                    SetStep(3);
                }
                break;
            }
            break;
        case 3:
            if (entity->step_s == 0) {
                /* unk84 at ext+0x08 */
                entity->unk84 = rand() & 0xFFF;
                /* unk82 at ext+0x06 */
                entity->unk82 = rand() & 0xFFF;
                entity->animCurFrame = 0x2B;
                entity->step_s++;
            }
            /* unk9C at ext+0x20, pointer to parent entity */
            newEntity = entity->unk9C;
            parentXHi = newEntity->posX.i.hi;
            parentYHi = newEntity->posY.i.hi;
            parentYHi -= 4;
            /* unk84 at ext+0x08 */
            angle = entity->unk84;
            parentXHi += ((rcos(angle) * 48) >> 12);
            targetAngle = ratan2(parentYHi - entity->posY.i.hi, parentXHi - entity->posX.i.hi);
            targetAngle = func_us_8019A98C(0x40, entity->unk82, targetAngle);
            entity->velocityX = (rcos(targetAngle) * 40);
            entity->velocityY = (rsin(targetAngle) * 40);
            /* unk82 at ext+0x06 */
            entity->unk82 = targetAngle;
            MoveEntity();
            /* unk84 at ext+0x08 */
            entity->unk84 += 0x20;
            break;
        case 4:
            step_s = entity->step_s;
            switch (step_s) {
            case 0:
                entity->hitboxState = 0;
                entity->animCurFrame = 0x2B;
                entity->velocityX = 0;
                entity->velocityY = 0;
                entity->step_s++;
                /* fall through to case 1 */
            case 1:
                parentXHi = entity->posX.i.hi + g_Tilemap.scrollX.i.hi;
                parentYHi = entity->posY.i.hi + g_Tilemap.scrollY.i.hi;
                if (parentYHi >= 0x1D9 || (u32)(parentXHi - 0x114) >= 0xD7) {
                    entity->step_s = 2;
                    entity->flags |= 0x80000000;
                } else {
                    entity->step_s = 3;
                }
                break;
            case 2:
                MoveEntity();
                entity->velocityY += 0x4000;
                break;
            case 3:
                MoveEntity();
                entity->velocityY += 0x4000;
                parentYHi = entity->posY.i.hi + g_Tilemap.scrollY.i.hi;
                if (parentYHi >= 0x1D9) {
                    entity->posY.i.hi = 0x1D8 - g_Tilemap.scrollY.i.hi;
                    /* unk80 at ext+0x04 */
                    entity->unk80 = 0x40;
                    entity->step_s++;
                }
                break;
            case 4:
                /* unk80 at ext+0x04 */
                if (!(entity->unk80 & 3)) {
                    newEntity = AllocEntity(&g_Entities_96, &g_Entities_96 + 0x7580);
                    if (newEntity != NULL) {
                        CreateEntityFromEntity(0x20, entity, newEntity);
                        newEntity->params = 1;
                        newEntity->zPriority = entity->zPriority + 1;
                    }
                }
                /* unk80 at ext+0x04 */
                entity->unk80--;
                if (entity->unk80 == 0) {
                    DestroyEntity(entity);
                    return;
                }
                break;
            }
            /* Check flag before destruction */
            if (PrizeDrops & 8) {
                DestroyEntity(entity);
            }
            break;
        }
    }
}