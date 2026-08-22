/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RCEN:func_us_8019B5A4
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_shaft.c
   verdict: BUILD FAILED:
44:src/st/rcen/e_shaft.c:44: conflicting types for `D_us_80180570'
45:src/st/rcen/e_shaft.c:40: previous declaration of `D_us_80180570'
46-[44/156] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/weapon/w0_022.map -T weapon0.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.weapon.txt -T build/us/config/undefined_syms_auto.us.weapon.txt -o build/us/weapon/w0_022.elf
47-[45/156] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/weapon/w0_031.map -T weapon0.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.weapon.txt -T build/us/config/undefined_syms_auto.us.weapon.txt -o build/us/weapon/w0_031.elf

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
extern u32 PrizeDrops;
extern s32 D_us_80180570[];
extern s32 D_us_801807D0[];
extern GAME_IMPORT u32 g_Timer;
extern s32 D_us_80180800[];
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
void AnimateEntity(s32* arg0, Entity* arg1);
void SetStep(u16 step);
void PlaySfxPositional(s32 sfxId);
void func_us_8019AA04(s32 arg0);

/* Shaft entity update in RCEN: handles initialization, animation, and destruction */
void func_us_8019B5A4(Entity* self) {
    if (PrizeDrops & 4) {
        if (self->step != 2) {
            SetStep(2);
        }
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180570);
        self->blendMode = 0x30;
        /* fall through */
    case 1:
        AnimateEntity(D_us_801807D0, self);
        self->posX.i.hi = self->ext.timer.t;
        self->posY.i.hi = self->ext.timer.t >> 16;
        if (!(g_Timer & 0x7F)) {
            func_us_8019AA04(0x6E6);
        }
        break;

    case 2:
        AnimateEntity(D_us_80180800, self);
        if (self->pose == 0xA) {
            PlaySfxPositional(0x84D);
        }
        self->posX.i.hi = self->ext.timer.t;
        self->posY.i.hi = self->ext.timer.t >> 16;
        if (PrizeDrops & 8) {
            DestroyEntity(self);
        }
        break;
    }
}