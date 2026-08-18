/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_801C7654
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/e_subweapon_container.c
   verdict: BUILD FAILED:
102:src/st/rno0/e_subweapon_container.c:36: invalid operands to binary +
103:src/st/rno0/e_subweapon_container.c:36: incompatible type for argument 1 of indirect function call
104:src/st/rno0/e_subweapon_container.c:37: structure has no member named `unk0'
105-[101/245] psx cc src/st/rno3/gen/e_laydef.c
106-[102/245] psx cc src/st/rno3/gen/e_layout.c

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
extern void (*g_api_CheckCollision)(s32 x, s32 y, Collider* res, s32 unk);
extern void DestroyEntity(Entity* entity);
extern void InitializeEntity(u16 arg0[]);
extern void AnimateEntity(void* arg0, Entity* arg1);
extern void MoveEntity(void);
extern s32 rcos(s32 angle);
extern s32 rsin(s32 angle);
extern u16 RNO0_EInitParticle[];
extern u8 D_us_80183294[];

void func_801C7654(Entity* self) {
    Collider collider;
    s32 temp;

    switch (self->step) {
    case 0:
        InitializeEntity(RNO0_EInitParticle);
        self->animSet = 2;
        self->palette = 0x816D;
        self->blendMode = 0x70;
        self->velocityX = rcos(self->rotate) * 16;
        self->velocityY = rsin(self->rotate) * 16;
        break;

    case 1:
        AnimateEntity(D_us_80183294, self);
        MoveEntity();
        self->velocityY += 0x2000;
        g_api_CheckCollision(self->posX, self->posY + 8, &collider, 0);
        if (collider.unk0 & 1) {
            self->drawFlags = 2;
            self->scaleY = 0x100;
            self->velocityY = 0x4000;
            self->velocityX *= 8;
            self->step++;
        }
        break;

    case 2:
        MoveEntity();
        self->scaleY -= 8;
        if (self->scaleY == 0) {
            DestroyEntity(self);
        }
        break;
    }
}