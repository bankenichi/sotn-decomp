/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801B94CC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: BUILD FAILED:
38:src/boss/bo6/us_39144.c:121: `RIC_velocityY' undeclared (first use this function)
39:src/boss/bo6/us_39144.c:121: (Each undeclared identifier is reported only once
40:src/boss/bo6/us_39144.c:121: for each function it appears in.)
41:src/boss/bo6/us_39144.c:127: `D_us_80181284' undeclared (first use this function)
42-src/boss/bo6/us_39144.c: At top level:
43:src/boss/bo6/us_39144.c:455: `RIC_velocityY' used prior to declaration
44-[37/159] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/weapon/w0_014.map -T weapon0.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.weapon.txt -T build/us/config/undefined_syms_auto.us.weapon.txt -o build/us/weapon/w0_014.elf
45-[38/159] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/weapon/w0_018.map -T weapon0.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.weapon.txt -T build/us/config/undefined_syms_auto.us.weapon.txt -o build/us/weapon/w0_018.elf

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
/* Mechanical symbol repair from escalation_triage.py. */
extern s32 RIC_velocityY;

void func_us_801B94CC(void) {
    Entity* self = &g_Entities[65];
    Primitive* prim;
    s32 i;
    u8 temp_v0;
    u8* extBytes = (u8*)&self->ext;

    if (extBytes[0] == 0) {
        if ((g_Ric.padTapped & ~0x900) ||
            ((g_Ric.padHeld ^ g_Ric.padPressed) & g_Ric.padHeld & ~0x900) ||
            (RIC_velocityY > 0x8000)) {
            extBytes[2] = 0;
            extBytes[3] = 0;
        } else {
            if (extBytes[2] < 0xA) {
                if (extBytes[3] == 0) {
                    extBytes[3] = D_us_80181284[extBytes[2]];
                }
                temp_v0 = extBytes[3] - 1;
                extBytes[3] = temp_v0;
                if ((temp_v0 & 0xFF) == 0) {
                    extBytes[2] += 1;
                    extBytes[3] = D_us_80181284[extBytes[2]];
                }
            }
        }
    }

    if (self->pose != 0) {
        self->pose = self->pose - 1;
        return;
    }

    prim = &g_PrimBuf[self->primIndex];
    i = 0;
    if (prim != NULL) {
        do {
            if (i == self->entityId) {
                prim->r0 = 0x80;
                prim->g0 = 0x80;
                prim->b0 = 0x80;
                prim->x0 = self->posX.val;
                prim->y0 = self->posY.val;
                prim->y1 = 0;
                prim->x1 = self->velocityX;
                prim->x2 = self->hitboxOffX;
                prim->y2 = self->hitboxOffY;
            }
            prim = prim->next;
            i += 1;
        } while (prim != NULL);
    }

    self->entityId = self->entityId + 1;
    self->pose = 2;
    if (self->entityId >= 6) {
        self->entityId = 0;
    }
}