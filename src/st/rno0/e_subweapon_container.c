// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/e_subweapon_container", EntitySubWeaponContainer);

INCLUDE_ASM("st/rno0/nonmatchings/e_subweapon_container", EntitySubWpnContGlass);

INCLUDE_ASM("st/rno0/nonmatchings/e_subweapon_container", func_801C7654);

INCLUDE_ASM("st/rno0/nonmatchings/e_subweapon_container", func_801C77B8);

// InitializeEntity descriptor for obtainable pickups. Defined WITHOUT
// OVL_EXPORT at src/st/rno0/e_init.c:169, so the plain name is correct here;
// the asm does lui/addiu on `g_EInitObtainable` itself.
extern EInit g_EInitObtainable;

// Per-item animation script pointers, indexed by params. Storage is in an
// undecompiled data blob; e_collect.c:42 declares it the same way.
extern u8* D_us_80181830[];

// The subweapon/prize entity is always allocated as container+1 (see
// EntitySubWeaponContainer), so self[-1] is its container. The asm reads it as
// a raw -0x90 off self, which is not a negative-offset hack: Entity is 0xBC and
// step sits at 0x2C, so self - 0xBC + 0x2C = self - 0x90 exactly. An earlier
// attempt copied that as `*(u16*)((u8*)self - 0x90)` and got the arithmetic
// right but the meaning wrong. src/st/nz0/e_subweapon_container.c contains a
// function of this same name that writes it as self[-1] and matches this
// disassembly instruction for instruction.
void func_801C7884(Entity* self) {
    Entity* tempEntity;
    s32 params;

    params = self->params;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitObtainable);
        self->hitboxState = 0;
        /* fallthrough: the asm has no branch between the init block and the
           shared body, so step 0 runs the body too on its first frame. */
    case 1:
        MoveEntity();
        AnimateEntity(D_us_80181830[params], self);
        self->velocityY = rsin(self->rotate) * 2;
        self->rotate += 0x20;

        tempEntity = &self[-1];
        if (tempEntity->step != 1) {
            self->entityId = E_PRIZE_DROP;
            self->pfnUpdate = EntityPrizeDrop;
            self->poseTimer = 0;
            self->pose = 0;
            self->step = 0;
            self->hitboxState = 1;
        }
        break;
    }
}
