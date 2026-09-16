/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO5:func_us_801A1C14
   attempt: 4/4
   from   : muse-spark-1.3-contributor-free
   origin : src/boss/bo5/unk_2159C.c
   verdict: quality reject: `Entity` has no member `unk7E`; 0x7E falls inside `ext` (0x7C)

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
/* Hippogryph boss main update (BO5 overlay). Unsure on some velocities, kept as-is. */
extern GAME_IMPORT Entity g_Entities[TOTAL_ENTITY_COUNT];
void func_us_801A19CC(u8 step);
void DestroyEntity(Entity*);
extern void (*g_api_FreePrimitives)(s32);
void InitializeEntity(u16 arg0[]);
u8 GetSideToPlayer();
u8 AnimateEntity(u8 frames[], Entity* entity);
s16 GetDistanceToPlayerX();
extern s32 D_us_801806DC[];
extern s32 (*g_api_TimeAttackController)(TimeAttackEvents eventId, TimeAttackActions action);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
extern s32 D_us_80180804[];
extern s32 D_us_801808BC[];
void MoveEntity();
extern Tilemap g_Tilemap;
extern s32 D_us_801808D4[];
extern s32 D_us_80180830[];
void PlaySfxPositional(s32 arg0);
extern u16 PLAYER_posX_i_hi;
extern u16 PLAYER_posY_i_hi;
void func_us_801A1C14(Entity* self) {
    Entity* target;
    Entity* next;
    u16 step;
    s32 vel;
    u8 timer;

    if ((self->hitParams != 0) && (self->step & 1)) {
        /* knockback velocity, fixed-point 16.16 */
        if (self->facingLeft == 0) {
            vel = 0x10000;
        } else {
            vel = 0xFFFE0000;
        }
        self->velocityX = vel | 0x8000;
        self->velocityY = -0x40000;
        func_us_801A19CC(0x20);
    }
    if ((self->flags & 0x100) && ((u16)self->step < 0x22U)) {
        target = (Entity*)self->ext; /* placeholder use of ext root, actual 0x94 in ext union */
        self->hitboxState = 0;
        ((s16*)&self->velocityX)[1] = 0; /* entity offset 0x0A, hi of velocityX */
        ((s16*)&self->velocityY)[1] = 0;
        ((u8*)&self->ext)[0] = 0;
        self->animCurFrame = 0x6E;
        if (target != NULL) {
            DestroyEntity(target);
        }
        if (self->flags & 0x800000) {
            g_api_FreePrimitives(self->primIndex);
            self->flags &= 0xFF7FFFFF;
        }
        func_us_801A19CC(0x24);
    }
    step = self->step;
    switch (step) {
    case 0:
        InitializeEntity(&g_EInitHippogryph);
        self->unk7E = self->zPriority; /* entity offset 0x7E */
        self->zPriority = g_Entities->zPriority + 1;
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        self->unk7D = 1; /* entity offset 0x7D */
        break;
    case 1:
        self->hitboxState = 0;
        AnimateEntity(&g_EInitKarasuman, self);
        if ((self->unk7D != 0) && (GetDistanceToPlayerX() < 0x80)) { /* entity offset 0x7D */
            func_us_801A19CC(3);
            if (D_us_801806DC == 0) {
                g_api_TimeAttackController(TIMEATTACK_EVENT_HYPPOGRYPH_DEFEAT, TIMEATTACK_SET_VISITED);
            }
            next = self + 0xBC;
            self->hitboxState = 3;
            self->nextPart = next;
            D_us_801806DC |= 1;
            CreateEntityFromEntity(0x23, self, next);
        }
        break;
    case 3:
        if (AnimateEntity(D_us_80180804, self) == 0) {
            func_us_801A19CC(4);
        }
        break;
    case 4:
        MoveEntity();
        AnimateEntity(D_us_801808BC, self);
        break;
    case 6:
        MoveEntity();
        AnimateEntity(D_us_80180830, self);
        if ((s32)self->pose == 1) {
            PlaySfxPositional(0x768);
        }
        timer = ((u8*)&self->ext)[0];
        ((u8*)&self->ext)[0] = timer - 1;
        break;
    default:
        break;
    }
    timer = self->animCurFrame;
    if (((u8)(timer - 0xE) < 11U)) {
        self->hitboxWidth = 6;
        self->hitboxHeight = 0x14;
        self->hitboxOffX = 8;
    } else if (((u8)(timer - 0x3A) < 6U)) {
        self->hitboxWidth = 6;
        self->hitboxHeight = 0x14;
        self->hitboxOffX = 0;
    } else {
        self->hitboxWidth = 0x14;
        self->hitboxHeight = 8;
        self->hitboxOffX = 0;
    }
    self->hitboxOffY = timer;
}
