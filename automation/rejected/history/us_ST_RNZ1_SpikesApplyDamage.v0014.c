/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RNZ1:SpikesApplyDamage
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rnz1/e_spikes.c
   verdict: quality reject: static_dropped: shared e_spikes.h declares it static in every version branch; our copy does not. FIX: restore static --

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
void SpikesApplyDamage(u32 arg0) {
    s32 tileX;
    s32 tileY;

    // Extract tile X from low nibble, scale to pixel offset, add 8 for center
    tileX = (arg0 & 0xF) * 16 + 8;
    // Extract tile Y from high nibble, scale to pixel offset, add 8 for center
    tileY = ((arg0 >> 4) & 0xF) * 16 + 8;

    // Subtract scroll position to get world-space coordinate
    g_CurrentEntity->ext.spikes.rotate = (s16)(tileX - g_Tilemap.scrollX.i.hi);
    g_CurrentEntity->ext.spikes.echoCooldown = (s16)(tileY - g_Tilemap.scrollY.i.hi);
}