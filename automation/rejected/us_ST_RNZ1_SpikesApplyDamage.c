/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNZ1:SpikesApplyDamage
   attempt: 1/4
   from   : deterministic transplant
   origin : src/st/rnz1/e_spikes.c
   verdict: BUILD FAILED:
256:src/st/rnz1/e_spikes.c:21: `SPIKES_TILE_WIDTH' undeclared (first use this function)
257:src/st/rnz1/e_spikes.c:21: (Each undeclared identifier is reported only once
258:src/st/rnz1/e_spikes.c:21: for each function it appears in.)
259-[255/505] psx cc src/st/rtop/stage_data.c
260-[256/505] psx cc src/st/rtop/tilemaps.c

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
static void SpikesApplyDamage(u32 tileIdx) {
    Entity* spikesDamage;
    s16 tilePosX, tilePosY;

    tilePosX = ((tileIdx % SPIKES_TILE_WIDTH) * 16) + 8;
    tilePosY = ((tileIdx / SPIKES_TILE_WIDTH) * 16) + 8;
    tilePosX -= g_Tilemap.scrollX.i.hi;
    tilePosY -= g_Tilemap.scrollY.i.hi;

#ifdef HAS_ORIENTATIONS
    spikesDamage = &g_CurrentEntity[1];
#ifdef DAMAGE_ENT_ON_HIT
    spikesDamage->posX.i.hi = tilePosX;
    spikesDamage->posY.i.hi = tilePosY;
#endif
#endif

#ifdef DAMAGE_ENT_ON_HIT
     
    spikesDamage = AllocEntity(&DAMAGE_ENT_START, &DAMAGE_ENT_END);
    if (spikesDamage != NULL) {
        CreateEntityFromCurrentEntity(E_ID(SPIKES_DAMAGE), spikesDamage);
        spikesDamage->posX.i.hi = tilePosX;
        spikesDamage->posY.i.hi = tilePosY;
    }
#else
     
    spikesDamage->posX.i.hi = tilePosX;
    spikesDamage->posY.i.hi = tilePosY;
#endif
}