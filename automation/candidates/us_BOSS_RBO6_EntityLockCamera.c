/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:BOSS/RBO6:EntityLockCamera
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_lock_camera.h
   target : src/boss/rbo6/e_lock_camera.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
u8 GetSideToPlayer();
/* End permuter-seed writer declarations. */


/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
int abs(int x);

bool PlayerIsWithinHitbox(Entity* self) {
    s16 posXAbs;
    s16 posXDiff;
    s16 posYAbs;
    s16 posYDiff;

    posXDiff = PLAYER.posX.i.hi - self->posX.i.hi;
    posXAbs = abs(posXDiff);
    if (posXAbs > self->hitboxWidth) {
        return false;
    }

    posYDiff = PLAYER.posY.i.hi - self->posY.i.hi;
    posYAbs = abs(posYDiff);
    if (posYAbs > self->hitboxHeight) {
        return false;
    }
    return true;
}



/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;
extern EInit g_EInitLockCamera;

void EntityLockCamera(Entity* self) {
    Tilemap* tilemap = &g_Tilemap;
    u16* dataPtr;

    u16 var_s2;
    u16 params;
    s16 var_s4;















    params = self->params;
    if (!self->step) {
        InitializeEntity(g_EInitLockCamera);
        self->hitboxState = 1;
        var_s2 = self->ext.lockCamera.unk7C = entityLockCameraData[params];
        if (var_s2) {
            self->hitboxWidth = entityLockCameraHitbox[params];
            self->hitboxHeight = 0x14;
        } else {
            self->hitboxWidth = 0x14;
            self->hitboxHeight = entityLockCameraHitbox[params];
        }
        self->ext.lockCamera.unk88 = 2;
    }

    switch (params) {
    default:
        break;
    }

    if (PlayerIsWithinHitbox(self)) {
        var_s2 = GetSideToPlayer();
        if (self->ext.lockCamera.unk7C) {
            var_s2 &= 2;
            var_s2 *= 2;
        } else {
            var_s2 &= 1;
            var_s2 *= 4;
        }
        if (var_s2 != self->ext.lockCamera.unk88) {
            self->ext.lockCamera.unk88 = var_s2;
            params = (params << 3) + var_s2;
            dataPtr = &entityLockCameraTilemapProps[params];
            self->ext.lockCamera.unk7E = 0;
            self->ext.lockCamera.unk8A = 0x10;
            params = tilemap->scrollX.i.hi;
            if (params != *dataPtr && self->ext.lockCamera.unk7C) {
                self->ext.lockCamera.unk7E = 1;
                tilemap->x = params;
            } else {
                tilemap->x = *dataPtr;
            }
            self->ext.lockCamera.unk80 = *dataPtr++;
            var_s2 = tilemap->scrollY.i.hi - 4;
            if (var_s2 != *dataPtr && !self->ext.lockCamera.unk7C) {
                self->ext.lockCamera.unk7E |= 2;
                tilemap->y = var_s2;
            } else {
                tilemap->y = *dataPtr;
            }
            self->ext.lockCamera.unk82 = *dataPtr++;
            params += 0x100;
            if (params != *dataPtr && self->ext.lockCamera.unk7C) {
                self->ext.lockCamera.unk7E |= 4;
                tilemap->width = params;
            } else {
                tilemap->width = *dataPtr;
            }
            self->ext.lockCamera.unk84 = *dataPtr++;
            var_s2 += 0x100;
            if (var_s2 != *dataPtr && !self->ext.lockCamera.unk7C) {
                self->ext.lockCamera.unk7E |= 8;
                tilemap->height = var_s2;
            } else {
                tilemap->height = *dataPtr;
            }
            self->ext.lockCamera.unk86 = *dataPtr;
        }
    } else {
        self->ext.lockCamera.unk88 = 2;
    }

    switch (self->params) {
    case 4:



        break;
    }

    if (self->ext.lockCamera.unk7E) {
        if (!--self->ext.lockCamera.unk8A) {
            tilemap->x = self->ext.lockCamera.unk80;
            tilemap->y = self->ext.lockCamera.unk82;
            tilemap->width = self->ext.lockCamera.unk84;
            tilemap->height = self->ext.lockCamera.unk86;
            self->ext.lockCamera.unk7E = 0;
        } else {
            var_s4 = (self->ext.lockCamera.unk80 - tilemap->x) / 2;
            if (var_s4) {
                if (var_s4 > 0) {
                    tilemap->x += 2;
                } else {
                    tilemap->x -= 2;
                }
            } else {
                tilemap->x = self->ext.lockCamera.unk80;
                self->ext.lockCamera.unk7E &= ~1;
            }
            var_s4 = (self->ext.lockCamera.unk82 - tilemap->y) / 2;
            if (var_s4) {
                if (var_s4 > 0) {
                    tilemap->y += 2;
                } else {
                    tilemap->y -= 2;
                }
            } else {
                tilemap->y = self->ext.lockCamera.unk82;
                self->ext.lockCamera.unk7E &= ~2;
            }
            var_s4 = (self->ext.lockCamera.unk84 - tilemap->width) / 2;
            if (var_s4) {
                if (var_s4 > 0) {
                    tilemap->width += 2;
                } else {
                    tilemap->width -= 2;
                }
            } else {
                tilemap->width = self->ext.lockCamera.unk84;
                self->ext.lockCamera.unk7E &= ~4;
            }
            var_s4 = (self->ext.lockCamera.unk86 - tilemap->height) / 2;
            if (var_s4) {
                if (var_s4 > 0) {
                    tilemap->height += 2;
                } else {
                    tilemap->height -= 2;
                }
            } else {
                tilemap->height = self->ext.lockCamera.unk86;
                self->ext.lockCamera.unk7E &= ~8;
            }
        }
    }




}

