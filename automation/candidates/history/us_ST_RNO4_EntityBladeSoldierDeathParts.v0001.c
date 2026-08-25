/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntityBladeSoldierDeathParts
   source : upstream/master:src/st/are/e_blade_soldier.c
   target : src/st/rno4/unk_58A30.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void FallEntity(void);
void MoveEntity();
void InitializeEntity(u16 arg0[]);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BBE58_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BC650_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCA5C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCB9C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCD80_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCE4C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCFC8_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", TryThrow);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityJackOBones);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityJackOBonesJack);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", TryShoot);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", DrawLaserRing);

INCLUDE_RODATA("st/rno4/nonmatchings/unk_58A30", D_us_801C4800);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityNovaSkeleton);

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

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityNovaLaser);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityNovaLaserPulse);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityImp);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityImpSmoke);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityRdaiUnk33);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityImpDeathParticle);
