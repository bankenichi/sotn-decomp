/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B19FC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
90:src/boss/bo0/2D26C.c:74: structure has no member named `unk90'
91:src/boss/bo0/2D26C.c:76: structure has no member named `unk90'
92:src/boss/bo0/2D26C.c:88: structure has no member named `unk90'
93:src/boss/bo0/2D26C.c:90: structure has no member named `unk90'
94-[89/297] psx cc src/st/dai/gfx_data.c
95-[90/297] psx cc src/st/dai/tilemaps.c

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
void func_us_801B19FC(Entity* self) {
    s32 temp_v0;
    s32 temp_v0_2;
    u8 temp_v1;

    temp_v1 = self->step;
    switch (temp_v1) {
    case 0:
        if (func_us_801B171C(self, -0x80, 0x80, 0x1C) != 0) {
            self->step = self->step + 1;
        }
        temp_v0 = (s16) g_CurrentEntity->unk90;
        if (temp_v0 >= -0xFF) {
            g_CurrentEntity->unk90 = temp_v0 - 0x10;
        }
        return;
    case 1:
        if (func_us_801B171C(self, -0x100, 0, 0x18) != 0) {
            self->step = self->step + 1;
        }
        return;
    case 2:
        if (func_us_801B171C(self, -0x280, -0xC0, 0x14) != 0) {
            self->step = self->step + 1;
        }
        temp_v0_2 = (s16) g_CurrentEntity->unk90;
        if (temp_v0_2 < 0x100) {
            g_CurrentEntity->unk90 = temp_v0_2 + 0x10;
        }
        break;
    }
}