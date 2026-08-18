/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntityHitByIce
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
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
