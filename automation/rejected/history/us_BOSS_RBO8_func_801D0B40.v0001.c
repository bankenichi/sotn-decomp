/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/RBO8:func_801D0B40
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/rbo8/unk_15868.c
   verdict: quality reject: `Entity` has no member `unk5C4`; 0x5C4 falls inside `unkB8` (0xB8)

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
void func_801D0B40(void) {
    Entity* self = g_CurrentEntity;
    Entity* entity1 = self->unk5C4; // Entity at ext+0x548
    Entity* entity2 = self->unk8B4; // Entity at ext+0x838
    s16 angle1 = entity1->unk9C + 0x100; // ext+0x20
    s16 angle2 = entity2->unk9C + 0x180; // ext+0x20
    self->unk5C0 = angle1; // Entity at ext+0x544
    self->unk8B0 = angle2; // Entity at ext+0x834
}