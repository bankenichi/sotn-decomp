/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:EntityBladeSoldierDeathParts
   source : upstream/master:src/st/are/e_blade_soldier.c
   target : src/st/rno1/unk_35378.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void FallEntity(void);
void MoveEntity();
void InitializeEntity(u16 arg0[]);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", TryThrow);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBones);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBonesJack);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", TryShoot);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", DrawLaserRing);

INCLUDE_RODATA("st/rno1/nonmatchings/unk_35378", D_us_801A5DDC);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaSkeleton);

void EntityBladeSoldierDeathParts(Entity* self) {
    if (self->step) {
        if (--self->ext.bladeSoldier.deathPartFallDuration) {
            self->rotate += death_parts_rotation[self->params];
            FallEntity();
            MoveEntity();
            return;
        }

        self->entityId = E_EXPLOSION;
        self->pfnUpdate = EntityExplosion;
        self->params = EXPLOSION_SMALL;
        self->step = 0;
        return;
    }

    InitializeEntity(g_EInitBladeSoldier);
    self->hitboxState = 0;
    self->flags |=
        FLAG_DESTROY_IF_OUT_OF_CAMERA | FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA |
        FLAG_UNK_00200000 | FLAG_UNK_2000;
    self->animCurFrame = self->params + 0x23;
    self->drawFlags = ENTITY_ROTATE;
    if (self->facingLeft) {
        self->velocityX = -self->velocityX;
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaLaser);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaLaserPulse);
