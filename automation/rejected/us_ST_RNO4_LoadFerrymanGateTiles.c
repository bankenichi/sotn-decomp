/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO4:LoadFerrymanGateTiles
   attempt: 1/4
   from   : deterministic transplant
   origin : src/st/rno4/unk_44B0C.c
   verdict: BUILD FAILED:
282:src/st/rno4/unk_44B0C.c:335: `tiles' undeclared (first use this function)
283:src/st/rno4/unk_44B0C.c:335: (Each undeclared identifier is reported only once
284:src/st/rno4/unk_44B0C.c:335: for each function it appears in.)
285-[281/507] psx cc src/st/top/palette_def.c
286-[282/507] psx cc src/st/top/layers.c

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
void LoadFerrymanGateTiles(void) {
    u16* tileLayoutPtr;
    Tilemap* tileMap;
    s32 i;
    s16 offset;

    tileMap = &g_Tilemap;
    offset = 0x595;
    tileLayoutPtr = *tiles;

    for (i = 0; i < LEN(tiles); i++) {
        tileMap->fg[offset] = *tileLayoutPtr++;
        offset++;
        tileMap->fg[offset] = *tileLayoutPtr++;
        offset += 0xCF;
    }
}