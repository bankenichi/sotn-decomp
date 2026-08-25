/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:TryShoot
   source : upstream/master:src/st/e_nova_skeleton.h
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
s32 UnkCollisionFunc2(s16* posX);
s16 GetDistanceToPlayerX();
u8 GetSideToPlayer();
void SetStep(u8 step);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", TryThrow);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBones);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityJackOBonesJack);

void TryShoot(void) {
     
    s32 unused = UnkCollisionFunc2(&sensors2);
     
    if (!g_CurrentEntity->ext.nova.cooldown) {
        if (GetDistanceToPlayerX() >= 0x80) {
            return;
        }
        if ((g_CurrentEntity->facingLeft) ^ (GetSideToPlayer() & 1)) {
            SetStep(NOVA_CHARGE);
        }
    } else {
        g_CurrentEntity->ext.nova.cooldown--;
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", DrawLaserRing);

INCLUDE_RODATA("st/rno1/nonmatchings/unk_35378", D_us_801A5DDC);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaSkeleton);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityBladeSoldierDeathParts);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaLaser);

INCLUDE_ASM("st/rno1/nonmatchings/unk_35378", EntityNovaLaserPulse);
