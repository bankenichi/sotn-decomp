/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:TryShoot
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_48100.c
   verdict: BUILD FAILED:
96:src/st/rno0/unk_48100.c:29: union has no member named `unkA4'
97:src/st/rno0/unk_48100.c:37: union has no member named `unkA4'
98-[95/243] psx cc src/st/rno3/layers.c
99-[96/243] psx cc src/st/rno3/graphics_banks.c

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
extern Entity* g_CurrentEntity;
extern s32 UnkCollisionFunc2(s32*);
extern s32 GetDistanceToPlayerX(void);
extern s32 GetSideToPlayer(void);
extern void SetStep(s32);
extern s32 D_us_80181FAC;

/* Boss shooting logic: if close enough and facing player, start attack step;
   otherwise decrement a cooldown timer stored in ext.unkA4 */
void TryShoot(void) {
    UnkCollisionFunc2(&D_us_80181FAC);
    if (g_CurrentEntity->ext.unkA4 == 0) {
        if (GetDistanceToPlayerX() < 0x80) {
            u16 facing = g_CurrentEntity->facingLeft;
            if (facing != (GetSideToPlayer() & 1)) {
                SetStep(6);
            }
        }
    } else {
        g_CurrentEntity->ext.unkA4 -= 1;
    }
}