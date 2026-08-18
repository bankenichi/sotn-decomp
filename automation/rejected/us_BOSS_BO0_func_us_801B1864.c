/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B1864
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
105:src/boss/bo0/2D26C.c:70: structure has no member named `unk90'
106:src/boss/bo0/2D26C.c:72: structure has no member named `unk90'
107:src/boss/bo0/2D26C.c:79: structure has no member named `unk90'
108:src/boss/bo0/2D26C.c:81: structure has no member named `unk90'
109-[104/297] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/dra.map -T build/us/dra.ld -T config/und

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
void func_us_801B1864(Entity* arg0) {
    s16 temp_v0;
    s16 temp_v0_2;
    u8 temp_v1;

    temp_v1 = arg0->step;
    switch (temp_v1) {
    case 0:
        if (func_us_801B171C(arg0, -0x40, 0x40, 0x1C) != 0) {
            arg0->step = (u8) (arg0->step + 1);
        }
        temp_v0 = (s16) g_CurrentEntity->unk90; // Entity offset 0x90
        if (temp_v0 >= -0xFF) {
            g_CurrentEntity->unk90 = temp_v0 - 0xC; // Entity offset 0x90
        }
        return;
    case 1:
        if (func_us_801B171C(arg0, -0x100, 0x300, 0x18) != 0) {
            arg0->step = (u8) (arg0->step + 1);
        }
        temp_v0_2 = (s16) g_CurrentEntity->unk90; // Entity offset 0x90
        if (temp_v0_2 < 0x100) {
            g_CurrentEntity->unk90 = temp_v0_2 + 8; // Entity offset 0x90
        }
        break;
    }
}