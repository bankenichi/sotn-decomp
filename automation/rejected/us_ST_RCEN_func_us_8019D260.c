/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RCEN:func_us_8019D260
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/unk_1D260.c
   verdict: quality reject: `Entity` has no member `unk89`; 0x89 falls inside `ext` (0x7C)

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
void func_us_8019D260(void) {
    Entity* entity;
    s32 i;
    u16 var_s3;
    u8 var_s4;

    var_s4 = Random() & 3;
    var_s3 = ((Random() & 0xF) << 8) - 0x800;
    for (i = 0; i < 6; i++) {
        entity = AllocEntity(g_Entities_224, &g_Entities_224[240]);
        if (entity != NULL) {
            CreateEntityFromEntity(0x20, g_CurrentEntity, entity);
            /* Entity offset 0x89 (ext.unk89) */
            entity->unk89 = 6 - i;
            /* Entity offset 0x88 (ext.unk88) */
            entity->unk88 = var_s4;
            entity->params = 2;
            /* Entity offset 0x84 (ext.unk84) */
            entity->unk84 = var_s3;
            entity->zPriority = g_CurrentEntity->zPriority + 1;
        }
    }
}