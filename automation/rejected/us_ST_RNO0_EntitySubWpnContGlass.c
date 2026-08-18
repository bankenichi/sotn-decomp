/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:EntitySubWpnContGlass
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/e_subweapon_container.c
   verdict: BUILD FAILED:
145:src/st/rno0/e_subweapon_container.c:12: conflicting types for `D_us_80180BC4'
146:src/st/rno0/e_subweapon_container.c:10: previous declaration of `D_us_80180BC4'
147:src/st/rno0/e_subweapon_container.c:15: conflicting types for `Random'
148:include/stage.h:208: previous declaration of `Random'
149-[145/295] psx cc src/weapon/w_020.c
150-[146/295] psx cc src/weapon/w_021.c
--- bui

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
extern u16 D_us_80180BC4;
extern void InitializeEntity(u16*);
extern void MoveEntity(void);
extern u32 Random(void);

void EntitySubWpnContGlass(Entity* self) {
    s32 var_v0;

    switch (self->step) {
    case 0:
        InitializeEntity(&D_us_80180BC4);
        self->drawFlags = 4;
        self->animCurFrame = self->params;
        self->palette += self->ext.subwpnContGlass.palette;
        self->velocityX = self->ext.subwpnContGlass.velX << 12;
        self->velocityX = (self->velocityX + 0x8000) - (Random() << 8);
        self->velocityY = self->velocityY - ((Random() & 0x1F) << 12);
        break;

    case 1:
        MoveEntity();
        self->velocityY += 0x2000;
        if (self->velocityX != 0) {
            if (self->facingLeft == 0) {
                var_v0 = self->rotate - 0x10;
            } else {
                var_v0 = self->rotate + 0x10;
            }
        } else {
            if (self->facingLeft != 0) {
                var_v0 = self->rotate - 0x10;
            } else {
                var_v0 = self->rotate + 0x10;
            }
        }
        self->rotate = var_v0;
        break;
    }
}