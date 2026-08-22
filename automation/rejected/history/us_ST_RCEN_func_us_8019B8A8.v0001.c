/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RCEN:func_us_8019B8A8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_shaft.c
   verdict: quality reject: candidate is not usable C: unbalanced braces: 1 unclosed `{`

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
extern s32 D_us_8018057C[];
void InitializeEntity(u16 arg0[]);
void MoveEntity();
extern s32 D_us_8018074C[];
extern u8 D_us_80180718[];
int rcos(int a);
long ratan2(long y, long x);
int rsin(int a);
extern u8 D_us_80180690[];
extern s32 D_us_801806E0[];
extern void (*g_api_PlaySfx)(s32 sfxId);
extern GAME_IMPORT u32 g_Timer;
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
extern GAME_IMPORT Tilemap g_Tilemap;
extern Entity g_Entities[];
extern s32 D_us_801806A8[];
extern s16 PLAYER_posX_i_hi;
extern s16 PLAYER_posY_i_hi;

void func_us_8019B8A8(Entity* self) {
    Entity* other;
    s32 temp_s0;
    s32 temp_s2;
    s32 var_a2;
    s32 var_s0;
    s32 var_s2;
    s32 var_v0;
    s32 var_v0_2;
    s32 var_v0_3;
    s32 var_v0_4;
    s32 var_v0_5;
    s32 var_v0_6;
    s32 var_v0_7;
    s32 var_v0_8;
    s32 var_v1;
    s16 angle;
    s16 temp_v0;
    u16 temp_v1;
    u16 temp_v1_2;
    u16 temp_v1_3;
    u16 temp_v1_4;
    u16 temp_v1_5;
    u16 temp_v1_6