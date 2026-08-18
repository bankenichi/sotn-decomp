/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801BA128
   attempt: 4/4
   model  : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: quality reject: `Entity` has no member `unkA4`; 0xA4 falls inside `ext` (0x7C)

   This is NOT a permuter seed and must never be treated as
   one: it has never compiled. automation/candidates/ is for
   code that builds and merely misses on bytes.

   Why it is kept: the escalation path used to record only
   the compiler's message, so a record like `g_EInitCommon
   undeclared` described code nobody could look at any more.
   Twelve such records were assumed to be one extern away
   from building, and turned out to need a full re-attempt
   because the candidate had been discarded.

   Do NOT apply this to the tree. Read it, fix what the
   verdict names, and re-attempt. */
