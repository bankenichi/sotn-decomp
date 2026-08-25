/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:ST/RNO4:EntityBgColumnsParallax_from_no4
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/no4/first_c_file.c
   target : src/st/rno4/unk_44B0C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void EntityFloatingIcePlatform(Entity* self);
void DestroyEntity(Entity*);
int FntPrint(const char* fmt, ...);
extern int rand(void);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
long ratan2(long y, long x);
void MoveEntity();
void EntitySkeletonApe(Entity* self);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
extern int func_pspeu_0923D4A0();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakable);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C123C_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C12B0_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C15F8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5364);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitParticle;
extern EInit g_EInitCommon;
extern unkGraphicsStruct g_unkGraphicsStruct;

void EntityBgColumnsParallax_from_no4(Entity* self) {
    s32 primIndex;
    s32 scrollY;
    s32 scrollX;
    s32 flipXY;
    s16* ptr;
    s32 posYBottom;
    s32 posY;
    s32 posX;
    Primitive* prim;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 10);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            prim->tpage = 0xE;
            prim->clut = 0x84;
            prim->u0 = prim->u2 = 0xE9;
            prim->u1 = prim->u3 = 0xFD;
            prim->v0 = prim->v1 = 1;
            prim->v2 = prim->v3 = 0x7F;
            prim->priority = 0x1C;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    ptr = (s16*)bg_columns_parallax_props;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollX /= 2;
    scrollX &= 0xFF;
    scrollY = g_Tilemap.scrollY.i.hi;
    if (scrollY < 0xB0) {
        scrollY /= 2;
#ifdef FIX_UB
         
         
        for (int i = 0; i < LEN(bg_columns_parallax_props); i++) {
#else
        while (1) {
#endif
            posX = *ptr++;
            posY = *ptr++;
            flipXY = *ptr++;
            posX -= scrollX;
            posY -= scrollY;
            posYBottom = posY + 0x7E;
            if (posX < -20) {
                continue;
            }
            if (posX >= STAGE_WIDTH) {
                break;
            }
            if (posYBottom >= 0 && posY < 0xE0) {
                if (flipXY & 1) {
                    prim->x0 = prim->x2 = posX + 0x14;
                    prim->x1 = prim->x3 = posX;
                } else {
                    prim->x0 = prim->x2 = posX;
                    prim->x1 = prim->x3 = posX + 0x14;
                }
                if (flipXY & 2) {
                    prim->y0 = prim->y1 = posY;
                    prim->y2 = prim->y3 = posYBottom;
                } else {
                    prim->y0 = prim->y1 = posYBottom;
                    prim->y2 = prim->y3 = posY;
                }
                prim->drawMode = DRAW_DEFAULT;
                prim = prim->next;
            }
        }
    }
    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

s16 D_us_80181514[] = {
    0x010, 0x032, 0x070, 0x09E, 0x0DF, 0x110,
    0x132, 0x170, 0x19E, 0x1DF, 0x210, 0x000,
};

void func_us_801C1EE4(Entity* self) {
    s32 scrollX;
    s32 clut;
    s32 yOffset;
    s32 var_s5;
    s32 var_s4;
    s32 scrollY;
    s32 var_s2;
    s32 var_s1;
    Primitive* prim;

    s32 primIndex;
    s16* ptr;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 16);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->ext.et_801C12B0.clut = 0;
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            prim->tpage = 0xE;
            prim->u0 = prim->u2 = 0xFC;
            prim->u1 = prim->u3 = 0xFE;
            prim->priority = 0x1A;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    ptr = D_us_80181514;
    self->ext.et_801C12B0.clut++;
    if (self->ext.et_801C12B0.clut >= 0xE) {
        self->ext.et_801C12B0.clut = 0;
    }
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollX *= 3;
    scrollX /= 8;
    scrollX &= 0xFF;
    scrollY = g_Tilemap.scrollY.i.hi;
    yOffset = 0x50 - scrollY;
    if (yOffset < 0) {
        yOffset = 0;
    }
    var_s5 = 0xB0 - scrollY;
    if (var_s5 >= 0) {
        scrollY *= 3;
        scrollY /= 8;
        scrollY += yOffset;
        scrollY %= 0x20;

        var_s5 -= yOffset;
        if (scrollY + var_s5 > 0x60) {
            var_s2 = 0x60 - scrollY;
        } else {
            var_s2 = var_s5;
        }

        var_s4 = var_s5 - var_s2;
        var_s5 = var_s2;
        var_s2 += yOffset;
        clut = self->ext.et_801C12B0.clut + 0x90;

        while (true) {
            var_s1 = *ptr++;
            var_s1 -= scrollX;
            if (var_s1 < -2) {
                continue;
            }

            if (var_s1 >= 0x100) {
                break;
            }

            prim->clut = clut;
            prim->v0 = prim->v1 = scrollY + 0x84;
            prim->v2 = prim->v3 = prim->v0 + var_s5;
            prim->x0 = prim->x2 = var_s1;
            prim->x1 = prim->x3 = var_s1 + 2;
            prim->y0 = prim->y1 = yOffset;
            prim->y2 = prim->y3 = var_s2;
            prim->drawMode =
                DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE | DRAW_TRANSP;
            prim = prim->next;
            if (var_s4 != 0) {
                prim->clut = clut;
                prim->v0 = prim->v1 = 0x84;
                prim->v2 = prim->v3 = var_s4 + 0x84;
                prim->x0 = prim->x2 = var_s1;
                prim->x1 = prim->x3 = var_s1 + 2;
                prim->y0 = prim->y1 = var_s2;
                prim->y2 = prim->y3 = var_s2 + var_s4;
                prim->drawMode =
                    DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE | DRAW_TRANSP;
                prim = prim->next;
            }
        }
    }

    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

 
void func_us_801C21AC(Entity* self) {
    s32 primIndex;
    s32 var_s7;
    s32 var_s6;
    s32 scrollY;
    s32 clut;
    u16 params;
    s32 posX;
    s32 posY;
    Primitive* prim;

    s16* ptr;

    params = self->params;
    if (!self->step) {
        InitializeEntity(g_EInitParticle);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 2);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA |
                       FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA | FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            if (params) {
                prim->tpage = 0xF;
                prim->u0 = prim->u2 = 0x82;
                prim->u1 = prim->u3 = 0x9D;
            } else {
                prim->tpage = 0xE;
                prim->u0 = prim->u2 = 0xE9;
                prim->u1 = prim->u3 = 0xF7;
            }

            prim->priority = 0x62;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
     
     
    ptr = D_us_80181514;
    self->ext.et_801C12B0.clut++;
    if (self->ext.et_801C12B0.clut >= 0xE) {
        self->ext.et_801C12B0.clut = 0;
    }

    posY = self->posY.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;

    if (posY >= 0) {
        scrollY %= 0x20;

         
        if (params) {
            clut = 0x90;
        } else {
            clut = 0xB0;
        }
        clut = 0xB0;

        clut += self->ext.et_801C12B0.clut;
        if (scrollY + posY > 0x60) {
            var_s7 = 0x60 - scrollY;
        } else {
            var_s7 = posY;
        }

        var_s6 = posY - var_s7;
        posY = var_s7;
        prim->clut = clut;

        if (params) {
            posX = self->posX.i.hi - 0xD;
            prim->v0 = prim->v1 = scrollY + 4;
            prim->x1 = prim->x3 = posX + 0x1B;
            prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                             DRAW_UNK02 | DRAW_TRANSP;
        } else {
            posX = self->posX.i.hi - 7;
            prim->v0 = prim->v1 = scrollY + 0x84;
            prim->x1 = prim->x3 = posX + 0xE;
            prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                             DRAW_UNK02 | DRAW_TRANSP;
        }

        prim->v2 = prim->v3 = prim->v0 + posY;
        prim->x0 = prim->x2 = posX;
        prim->y0 = prim->y1 = 0;
        prim->y2 = prim->y3 = posY;
        prim = prim->next;

        if (var_s6 != 0) {
            prim->clut = clut;
            if (params) {
                prim->v0 = prim->v1 = 4;
                prim->v2 = prim->v3 = var_s6 + 4;
                prim->x0 = prim->x2 = posX;
                prim->x1 = prim->x3 = posX + 0x1B;
                prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                                 DRAW_UNK02 | DRAW_TRANSP;
            } else {
                prim->v0 = prim->v1 = 0x84;
                prim->v2 = prim->v3 = var_s6 + 0x84;
                prim->x0 = prim->x2 = posX;
                prim->x1 = prim->x3 = posX + 0xE;
                prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                                 DRAW_UNK02 | DRAW_TRANSP;
            }

            prim->y0 = prim->y1 = posY;
            prim->y2 = prim->y3 = posY + var_s6;
            prim = prim->next;
        }
    }

    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

 
void func_us_801C2474(Entity* self) {
    Primitive* prim;
    s32 volume;
    s32 pan;
    s32 i;
    s32 var_s4;
    s32 scrollX;
    s32 scrollY;
    s32 clut;
    s32 primIndex;

    Entity* player;

    player = &PLAYER;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    volume = (scrollY / 24) + 0x4D;
    if (volume > 0x7F) {
        volume = 0x7F;
    }
    pan = (scrollX + player->posX.i.hi) - 0xD8;
    if (pan > 0) {
        if (pan < 0x20) {
            pan = 0;
        } else {
            pan = (pan - 0x20) / -24;
        }
        if (pan < -8) {
            pan = -8;
        }
    } else {
        if (pan > -0x20) {
            pan = 0;
        } else {
            pan = (pan + 0x20) / -0x10;
        }
        if (pan > 8) {
            pan = 8;
        }
    }
#ifdef VERSION_US
    FntPrint("vol ; %x\n", volume);
    FntPrint("pan : %d\n", pan);
#endif

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 4);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->ext.et_801C12B0.clut = 0;
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;

        while (prim != NULL) {
            prim->priority = 0x9C;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    g_api.SetVolumeCommand22_23(volume, pan);
    self->ext.et_801C12B0.clut++;
    if (self->ext.et_801C12B0.clut >= 0xE) {
        self->ext.et_801C12B0.clut = 0;
    }
    clut = self->ext.et_801C12B0.clut + 0xA0;

    prim = self->ext.et_801C12B0.prim;
    pan = 0xB0;
    i = 0x5B0;
    pan -= scrollY;
    i -= scrollY;
    if (pan < 0) {
        pan = 0;
    }
    if (i > 0xF0) {
        i = 0xF0;
    }

    i -= pan;
    do {
        volume = (pan + scrollY) - 0xB0;
        if (volume < 0xFE) {
            prim->tpage = 0xE;
            prim->u0 = prim->u2 = 0x87;
            prim->u1 = prim->u3 = 0xE7;
            prim->v0 = prim->v1 = volume + 1;
            var_s4 = volume + i;
            if (var_s4 > 0xFE) {
                prim->v2 = prim->v3 = 0xFF;
                volume = 0xFE - volume;
            } else {
                prim->v2 = prim->v3 = var_s4 + 1;
                volume = i;
            }
            prim->x0 = prim->x2 = 0xC0 - scrollX;
            prim->x1 = prim->x3 = 0x120 - scrollX;
        } else {
            prim->tpage = 0xF;
            volume -= 0xFE;
            volume %= 126;
            prim->u0 = prim->u2 = 0xCC;
            prim->u1 = prim->u3 = 0xFD;
            prim->v0 = prim->v1 = volume + 1;
            var_s4 = volume + i;
            if (var_s4 > 0x7E) {
                prim->v2 = prim->v3 = 0x7F;
                volume = 0x7E - volume;
            } else {
                prim->v2 = prim->v3 = (var_s4 + 1);
                volume = i;
            }
            prim->x0 = prim->x2 = 0xC0 - scrollX;
            prim->x1 = prim->x3 = 0xF1 - scrollX;
        }
        prim->y0 = prim->y1 = pan;
        pan += volume;
        prim->y2 = prim->y3 = pan;
        i -= volume;
        prim->clut = clut;
        prim->drawMode = DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;
        prim = prim->next;

        if (i == 0) {
            break;
        }
    } while (true);

    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

void func_us_801C2850(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 scrollX;
    s32 scrollY;
    s32 var_s4;
    s32 var_s3;
    s32 var_s2;
    s32 var_s1;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_G4, 3);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;

        while (prim != NULL) {
            prim->priority = 0x9E;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    if (scrollY > 0x300) {
        var_s4 = 0x3E0;
        var_s3 = 0x5E0;
        var_s4 -= scrollY;
        var_s3 -= scrollY;
        var_s1 = scrollY & 7;
        if (var_s4 < -0x10) {
            var_s4 = -0x10 - var_s1;
        }
        if (var_s3 > 0xF0) {
            var_s3 = (-var_s1 & 7) + 0xF0;
        }
        var_s1 = (var_s4 + scrollY) - 0x3E0;
        var_s2 = (var_s3 + scrollY) - 0x3E0;
        if (self->ext.et_801C12B0.unk80 & 1) {
            var_s1 *= 0x13;
            var_s1 /= 40;
            var_s2 *= 0x13;
            var_s2 /= 40;
        } else {
            var_s1 *= 0x12;
            var_s1 /= 40;
            var_s2 *= 0x12;
            var_s2 /= 40;
        }

         
        prim->r0 = prim->r1 = prim->b0 = prim->b1 = prim->g0 = prim->g1 =
            var_s1;
        prim->r2 = prim->r3 = prim->b2 = prim->b3 = prim->g2 = prim->g3 =
            var_s2;
        prim->x0 = prim->x2 = 0x80 - scrollX;
        prim->x1 = prim->x3 = 0x120 - scrollX;
        prim->y0 = prim->y1 = var_s4;
        prim->y2 = prim->y3 = var_s3;
        prim->drawMode = DRAW_DITHERING | DRAW_TPAGE2 | DRAW_TPAGE |
                         DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        prim = prim->next;

         
        prim->r0 = prim->r2 = prim->b0 = prim->b2 = prim->g0 = prim->g2 = 0;
        prim->r1 = prim->b1 = prim->g1 = var_s1;
        prim->r3 = prim->b3 = prim->g3 = var_s2;
        prim->x0 = prim->x2 = 0x20 - scrollX;
        prim->x1 = prim->x3 = 0x80 - scrollX;
        prim->y0 = prim->y1 = var_s4;
        prim->y2 = prim->y3 = var_s3;
        prim->drawMode = DRAW_DITHERING | DRAW_TPAGE2 | DRAW_TPAGE |
                         DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        prim = prim->next;

         
        prim->r0 = prim->b0 = prim->g0 = var_s1;
        prim->r2 = prim->b2 = prim->g2 = var_s2;
        prim->r1 = prim->b1 = prim->g1 = prim->r3 = prim->b3 = prim->g3 = 0;
        prim->x0 = prim->x2 = 0x120 - scrollX;
        prim->x1 = prim->x3 = 0x180 - scrollX;
        prim->y0 = prim->y1 = var_s4;
        prim->y2 = prim->y3 = var_s3;
        prim->drawMode = DRAW_DITHERING | DRAW_TPAGE2 | DRAW_TPAGE |
                         DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        prim = prim->next;
    }

    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

void func_us_801C2B78(Entity* self) {
    Primitive* prim;
    s32 i;
    s32 var_s2;
    s32 var_s3;
    s32 scrollX;
    s32 primIndex;
    s32 scrollY;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_TILE, 128);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            prim->priority = 0x6C;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    if (scrollY > 0x4D0) {
        var_s3 = 0x5B0;
        var_s3 -= scrollY;
        for (i = 0; i < 4; i++) {
            while (prim != NULL) {
                if (prim->drawMode == DRAW_HIDE) {
                    prim->r0 = prim->b0 = prim->g0 = 0x80;
                    prim->x0 = ((((rand() % 11) * 4) + 0xBF) - scrollX) + i;
                    prim->y0 = var_s3 - 4 + (rand() & 7);
                    prim->x1 = 0;
                    LOH(prim->r1) = 0;
                    prim->u0 = prim->v0 = 2;
                    LOW(prim->r2) = FIX(4);
                    LOW(prim->u1) = 0;
                    LOW(prim->x3) = (0x4000 - (rand() & 0xFF0));
                    LOW(prim->r3) = ((rand() & 0x1F00) - 0xF80);
                    prim->clut = 0x20;
                    prim->drawMode = DRAW_UNK02;
                    break;
                }

                prim = prim->next;
            }
        }
    }

     
    prim = self->ext.et_801C12B0.prim;
    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            LOH(prim->b1) = prim->x0;
            prim->y1 = prim->y0;
            LOW(prim->x1) += LOW(prim->r2);
            LOW(prim->r1) += LOW(prim->u1);
            prim->x0 = LOH(prim->b1);
            prim->y0 = prim->y1;

            var_s2 = 0;
            if (LOW(prim->r2) < 0) {

            } else {
                var_s2 = 1;
            }
            LOW(prim->r2) -= LOW(prim->x3);
            LOW(prim->u1) -= LOW(prim->r3);

            if (!--prim->clut) {
                prim->drawMode = DRAW_HIDE;
            }
        }
        prim = prim->next;
    }
}

static u16 D_us_8018152C[] = {0, 10, 4, 8, 1, 12, 5, 9, 2, 6, 11, 3, 7};

void func_us_801C2E60(Entity* self) {
    s32 var_s5;
#ifdef VERSION_PSP
    u32 scrollX;
#else
    s32 scrollX;
#endif
    s32 scrollY;
    s32 var_s2;
    s32 primIndex;
    Primitive* prim;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 32);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            prim->clut = PAL_CC_STONE_EFFECT;
            prim->tpage = 0x1A;
            prim->u0 = prim->u2 = 0;
            prim->u1 = prim->u3 = 0x1E;
            prim->v0 = prim->v1 = 0x60;
            prim->v2 = prim->v3 = 0x7C;
            prim->priority = 0x9D;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    if (self->ext.et_801C12B0.unk80 >= LEN(D_us_8018152C)) {
        self->ext.et_801C12B0.unk80 = 0;
    }
    if (scrollY > 0x480) {
        var_s2 = 0x5B0;
        var_s2 -= scrollY;

        while (prim != NULL) {
            if (prim->drawMode == DRAW_HIDE) {
                prim->y0 = prim->y1 = prim->y2 = prim->y3 = var_s2;
#ifdef VERSION_PSP
                var_s5 = (D_us_8018152C[self->ext.et_801C12B0.unk80] * 4) +
                         0xBB - scrollX - 9;
                prim->x2 = prim->x0 = var_s5 + (rand() & 3);
#else
                var_s5 = (rand() & 3) - 9;
                prim->x2 = prim->x0 =
                    (D_us_8018152C[self->ext.et_801C12B0.unk80] * 4) + 0xBB -
                    scrollX + var_s5;
#endif
                prim->x3 = prim->x1 = prim->x0 + 0x12;
                PGREY(prim, 0) = PGREY(prim, 1) = 0xFF;
                PGREY(prim, 2) = PGREY(prim, 3) = 0x80;
                prim->p1 = 0;
                prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                                 DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
                break;
            }

            prim = prim->next;
        }
    }
    prim = self->ext.et_801C12B0.prim;
    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            prim->y0--;
            if (rand() & 7) {
                prim->y0--;
            }
            prim->y1 = prim->y0;
            prim->p1++;
            prim->b1 -= 0x10;
            PGREY(prim, 0) = PGREY(prim, 1);
            prim->b3 -= 8;
            PGREY(prim, 2) = PGREY(prim, 3);
            if (prim->r0 < 0x11) {
                prim->drawMode = DRAW_HIDE;
            }
        }

        prim = prim->next;
    }
}

void func_us_801C3160(Entity* self) {
    s32 scrollY;
    s32 primIndex;
    u16 iterations;
    u16 params;
    s32 scrollX;
    s32 i;
    s32 yOffset;
    s32 randVal;
    Primitive* prim;

    params = self->params;
    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        if (!params) {
            primIndex = g_api.AllocPrimitives(PRIM_TILE, 0x80);
        } else {
            primIndex = g_api.AllocPrimitives(PRIM_TILE, 8);
        }
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = (s32)primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            prim->priority = 0x6C;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

     
    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    if (scrollY < 0xF0) {
        if (!params) {
            iterations = 4;
            yOffset = 0xB0 - scrollY;
        } else {
            iterations = 1;
            yOffset = 0xD6 - scrollY;
        }

        for (i = 0; i < iterations; i++) {
            while (prim != NULL) {
                if (prim->drawMode == DRAW_HIDE) {
                    if (!params) {
                        randVal = rand() & 0x1F;
                        prim->y0 = yOffset + randVal;
                        prim->x0 =
                            ((0x100 - (rand() % 40)) - scrollX) - randVal;
                        LOW(prim->u1) = 0xFFFE0000;
                        prim->u0 = prim->v0 = 2;
                        LOW(prim->r2) = 0;
                        prim->clut = 0x10;
                    } else {
                        prim->y0 = yOffset + (rand() & 3);
                        prim->x0 = (0x70E - scrollX) + (rand() & 3);
                        LOW(prim->u1) = 0x14000;
                        LOW(prim->r2) = ((rand() & 0x1F) << 0xB);
                        prim->u0 = prim->v0 = 1;
                        prim->clut = 8;
                    }
                    prim->r0 = prim->b0 = prim->g0 = 0x80;
                    prim->x1 = 0;
                    LOH(prim->r1) = 0;
                    LOW(prim->x3) = 0x4000;
                    LOW(prim->r3) = 0;
                    prim->drawMode = DRAW_UNK02;
                    break;
                }

                prim = prim->next;
            }
        }
    }

     
    prim = self->ext.et_801C12B0.prim;
    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            LOH(prim->b1) = prim->x0;
            prim->y1 = prim->y0;
            LOW(prim->x1) = LOW(prim->x1) + LOW(prim->r2);
            LOW(prim->r1) = LOW(prim->r1) + LOW(prim->u1);
            prim->x0 = LOH(prim->b1);
            prim->y0 = prim->y1;
            LOW(prim->r2) = LOW(prim->r2) + LOW(prim->x3);
            prim->r0 = prim->b0 = prim->g0 -= 8;
            if (!--prim->clut) {
                prim->drawMode = DRAW_HIDE;
            }
        }
        prim = prim->next;
    }
}

static s16 D_us_80181548[][5] = {
    {0x0058, 0x0068, 0x00B0, 0x0030, 0xFFFE},
    {0x06A0, 0x0060, 0x00C8, 0x0020, 0x0001},
};

void func_us_801C34EC(Entity* self) {
    s32 scrollX;
    s16 xOffset;
    s16 randX;
    s16 randY;
    s16 tpage;
    s32 yOffset;
    s32 scrollY;
    s32 primIndex;
    s16* ptr;
    Primitive* prim;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_TILE, 0x40);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            prim->priority = 0x9B;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    ptr = D_us_80181548[self->params];
    xOffset = *ptr++;
    randX = *ptr++;
    yOffset = *ptr++;
    randY = *ptr++;
    tpage = *ptr;
    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    if (scrollY < 0xF0) {
        yOffset -= scrollY;

        while (prim != NULL) {
            if (prim->drawMode == DRAW_HIDE) {
                prim->r0 = prim->b0 = prim->g0 = 0x80;
                prim->y0 = yOffset + (rand() % randY);
                prim->x0 = (xOffset - scrollX) + (rand() % randX);
                prim->x1 = 0;
                LOH(prim->r1) = 0;
                prim->u0 = prim->v0 = 2;
                LOW(prim->u1) = 0;
                prim->tpage = tpage;
                prim->drawMode = DRAW_UNK02;
                break;
            }

            prim = prim->next;
        }
    }

     
    prim = self->ext.et_801C12B0.prim;
    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            LOH(prim->b1) = prim->x0;
            LOW(prim->r1) += LOW(prim->u1);
            prim->x0 = LOH(prim->b1);
            prim->r0 -= 8;
            prim->b0 = prim->g0 = prim->r0;
            if (prim->r0 < 8) {
                prim->drawMode = DRAW_HIDE;
            }
        }
        prim = prim->next;
    }
}

void func_us_801C37C8(Entity* self) {
    Primitive* prim;
    s32 scrollX;
    s32 scrollY;
    s32 xOffset;
    s32 primIndex;
    s32 clut;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->ext.et_801C12B0.clut = 0;
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        prim->tpage = 0xF;
        prim->v0 = prim->v1 = 1;
        prim->v2 = prim->v3 = 0x7F;
        prim->priority = 0x9C;
        prim->drawMode = DRAW_HIDE;
    }

    scrollX = (rand() & 0x1F) - 0x10;
    D_us_80181150[35] = scrollX + 0x1D0;
    D_us_80181150[36] = 0x4C - scrollX;
    D_us_80181150[41] = scrollX + 0x180;
    D_us_80181150[20] = scrollX + 0x540;
    D_us_80181150[21] = 0x2B0 - scrollX;
    D_us_80181150[26] = scrollX + 0x70;
    self->ext.et_801C12B0.clut++;
    if (self->ext.et_801C12B0.clut >= 0xE) {
        self->ext.et_801C12B0.clut = 0;
    }

    clut = self->ext.et_801C12B0.clut + 0xA0;
    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;

    if (scrollX < 0x288) {
        xOffset = 0x218 - scrollX;
        if (xOffset < 0x100) {
            prim->u0 = prim->u2 = 0x11;
            prim->u1 = prim->u3 = 0x80;
        } else {
            prim->drawMode = DRAW_HIDE;
            return;
        }
    } else if (scrollX < 0x4D8) {
        xOffset = 0x468 - scrollX;
        if (xOffset < 0x100) {
            prim->u0 = prim->u2 = 0x80;
            prim->u1 = prim->u3 = 0x11;
        } else {
            prim->drawMode = DRAW_HIDE;
            return;
        }
    } else {
        prim->drawMode = DRAW_HIDE;
        return;
    }

    prim->clut = clut;
    prim->x0 = prim->x2 = xOffset;
    prim->x1 = prim->x3 = xOffset + 0x6F;
    prim->y0 = prim->y1 = 0xB0 - scrollY;
    prim->y2 = prim->y3 = prim->y0 + 0x7F;
    prim->drawMode = DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;
}

void func_us_801C3A04(Entity* self) {
    Primitive* prim;
    s32 i;
    s32 var_s2;
    s32 yOffset;
    s32 posX;
    s32 primIndex;
    s32 scrollY;

    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_TILE, 0x40);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;

        while (prim != NULL) {
            prim->priority = 0x6C;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    posX = self->posX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    yOffset = 0x120;
    yOffset -= scrollY;

     
    for (i = 0; i < 2; i++) {
        while (prim != NULL) {
            if (prim->drawMode == DRAW_HIDE) {
                prim->r0 = prim->b0 = prim->g0 = 0x80;
                prim->x0 = ((rand() % 0x10) * 2) + i + posX;
                prim->y0 = yOffset - 4 + (rand() & 7);
                prim->x1 = 0;
                LOH(prim->r1) = 0;
                prim->u0 = prim->v0 = 2;
                LOW(prim->r2) = 0x40000;
                LOW(prim->u1) = 0;
                LOW(prim->x3) = 0x4000 - (rand() & 0xFF0);
                LOW(prim->r3) = (rand() & 0x1F00) - 0xF80;
                prim->clut = 0x20;
                prim->drawMode = DRAW_UNK02;
                break;
            }

            prim = prim->next;
        }
    }

     
    prim = self->ext.et_801C12B0.prim;
    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            LOH(prim->b1) = prim->x0;
            prim->y1 = prim->y0;
            LOW(prim->x1) += LOW(prim->r2);
            LOW(prim->r1) += LOW(prim->u1);
            prim->x0 = LOH(prim->b1);
            prim->y0 = prim->y1;

            var_s2 = 0;
            if (LOW(prim->r2) >= 0) {
                var_s2 = 1;
            }
            LOW(prim->r2) -= LOW(prim->x3);
            LOW(prim->u1) -= LOW(prim->r3);
            if (!--prim->clut) {
                prim->drawMode = DRAW_HIDE;
            }
        }
        prim = prim->next;
    }
}

static u16 D_us_8018155C[] = {0, 4, 8, 1, 5, 2, 6, 3, 7, 0};

void func_us_801C3CC4(Entity* self) {
    s32 var_s5;
    s32 posX;
    s32 scrollY;
    s32 var_s2;
    s32 primIndex;
    Primitive* prim;

    if (!self->step) {
        InitializeEntity(g_EInitParticle);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 0x20);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            prim->clut = PAL_CC_STONE_EFFECT;
            prim->tpage = 0x1A;
            prim->u0 = prim->u2 = 0;
            prim->u1 = prim->u3 = 0x1E;
            prim->v0 = prim->v1 = 0x60;
            prim->v2 = prim->v3 = 0x7C;
            prim->priority = 0x9D;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    posX = self->posX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    if (self->ext.et_801C12B0.unk80 >= 9) {
        self->ext.et_801C12B0.unk80 = 0;
    }
    var_s2 = 0x120;
    var_s2 -= scrollY;

    while (prim != NULL) {
        if (prim->drawMode == DRAW_HIDE) {
            prim->y0 = prim->y1 = prim->y2 = prim->y3 = var_s2;
#ifdef VERSION_PSP
            var_s5 = D_us_8018155C[self->ext.et_801C12B0.unk80] * 4;
            prim->x2 = prim->x0 = var_s5 + (rand() & 3) - 0x19 + posX;
#else
            var_s5 = rand() & 3;
            prim->x2 = prim->x0 =
                (D_us_8018155C[self->ext.et_801C12B0.unk80] * 4) + var_s5 -
                0x19 + posX;
#endif
            prim->x3 = prim->x1 = prim->x0 + 0x12;
            PGREY(prim, 0) = PGREY(prim, 1) = 0xFF;
            PGREY(prim, 2) = PGREY(prim, 3) = 0x80;
            prim->p1 = 0;
            prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                             DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
            break;
        }

        prim = prim->next;
    }

    prim = self->ext.et_801C12B0.prim;

    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            prim->y0--;
            if (rand() & 3) {
                prim->y0--;
            }
            prim->y1 = prim->y0;
            prim->p1++;
            prim->b1 -= 0x10;
            PGREY(prim, 0) = PGREY(prim, 1);
            prim->b3 -= 8;
            PGREY(prim, 2) = PGREY(prim, 3);
            if (prim->r0 < 0x11) {
                prim->drawMode = DRAW_HIDE;
            }
        }

        prim = prim->next;
    }
}

static s16 D_us_80181570[] = {
    0x0100, 0x0000, 0x0240, 0x0018, 0x02E0, 0x000C,
    0x0300, 0x0000, 0x0320, 0x0010, 0x7FFF, 0x0000,
};

void func_us_801C3FB0(Entity* self) {
    s32 primIndex;
    s32 scrollX;
    s32 scrollY;
    s16* ptr;
    s32 clut;
    s32 var_s4;
    s32 var_s3;
    s32 var_s2;
    s32 var_s1;
    Primitive* prim;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 0x10);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->ext.et_801C12B0.clut = 0;
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;

        while (prim != NULL) {
            prim->tpage = 0xF;
            prim->u0 = prim->u2 = 0x82;
            prim->u1 = prim->u3 = 0x9D;
            prim->priority = 0xC0;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    ptr = D_us_80181570;
    self->ext.et_801C12B0.clut++;
    if (self->ext.et_801C12B0.clut >= 0xE) {
        self->ext.et_801C12B0.clut = 0;
    }
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollX *= 5;
    scrollX /= 4;

    scrollY = g_Tilemap.scrollY.i.hi;
    scrollY *= 5;
    scrollY /= 4;
    scrollY %= 0x20;

    clut = self->ext.et_801C12B0.clut + 0x90;

    while (prim != NULL) {
        var_s3 = *ptr++;
        var_s3 -= scrollX;
        if (var_s3 < -0x1B) {
            continue;
        }

        if (var_s3 >= 0x100) {
            break;
        }

        var_s4 = scrollY + *ptr++;
        var_s2 = 0x60 - var_s4;
        var_s1 = 0;

        while (prim != NULL) {
            prim->clut = clut;
            prim->v0 = prim->v1 = var_s4 + 4;
            prim->v2 = prim->v3 = prim->v0 + var_s2;
            prim->x0 = prim->x2 = var_s3;
            prim->x1 = prim->x3 = var_s3 + 0x1B;
            prim->y0 = prim->y1 = var_s1;
            var_s1 += var_s2;
            prim->y2 = prim->y3 = var_s1;
            prim->drawMode =
                DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE | DRAW_TRANSP;
            prim = prim->next;

            if (var_s1 >= 0xE8) {
                break;
            }

            var_s4 = 0;
            if (var_s1 > 0x88) {
                var_s2 = 0xE8 - var_s1;
            } else {
                var_s2 = 0x60;
            }
        }
    }

    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

void func_us_801C4228(Entity* self) {
    s32 scrollY;
    s32 scrollX;
    s32 primIndex;
    s32 yOffset;
    s32 yMax;
    s32 xOffset;
    Primitive* prim;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_G4, 4);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;

        while (prim != NULL) {
            prim->priority = 0xC0;
            prim->r0 = prim->r2 = prim->g0 = prim->g2 = prim->r1 = prim->r3 =
                prim->g1 = prim->g3 = 0x10;
            prim->b0 = prim->b2 = prim->b1 = prim->b3 = 0;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    if (scrollX > 0x90) {
        xOffset = PLAYER.posX.i.hi + 0x10;
    } else {
        xOffset = 0x120 - scrollX;
    }
    yOffset = 0x550 - scrollY;
    yMax = yOffset + 0x80;
    if (yMax > 0 && xOffset < 0x110) {
         
        prim->x0 = prim->x2 = xOffset;
        prim->x1 = prim->x3 = xOffset + 0x30;
        prim->y0 = prim->y1 = yOffset;
        prim->y2 = prim->y3 = yMax;
        prim->r1 = prim->r3 = prim->g1 = prim->g3 = prim->b1 = prim->b3 = 0xFF;
        prim->r0 = prim->r2 = prim->g0 = prim->g2 = prim->b0 = prim->b2 = 0;
        prim->drawMode =
            DRAW_UNK_40 | DRAW_TPAGE | DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        prim = prim->next;

         
#ifdef VERSION_PSP
        prim->x0 = prim->x2 = xOffset;
        prim->x1 = prim->x3 = xOffset + 1;
#else
        prim->x0 = prim->x2 = xOffset + 1;
        xOffset += 3;
        prim->x1 = prim->x3 = xOffset;
#endif
        prim->y0 = prim->y1 = yOffset;
        prim->y2 = prim->y3 = yMax;
#ifdef VERSION_PSP
        prim->r0 = prim->r2 = prim->g0 = prim->g2 = prim->r1 = prim->r3 =
            prim->g1 = prim->g3 = 8;
        prim->b0 = prim->b2 = prim->b1 = prim->b3 = 0;
        prim->drawMode =
            DRAW_UNK_40 | DRAW_TPAGE | DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
#else
        prim->r0 = prim->r2 = prim->g0 = prim->g2 = 7;
        prim->b0 = prim->b2 = prim->b1 = prim->b3 = 0;
        prim->r1 = prim->r3 = prim->g1 = prim->g3 = 8;
        prim->drawMode =
            DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
#endif
        prim->priority = 0xC1;
        prim = prim->next;

         
        prim->x0 = prim->x2 = xOffset;
#ifdef VERSION_PSP
        xOffset += 0x30;
#else
        xOffset += 0x2D;
#endif
        prim->x1 = prim->x3 = xOffset;
        prim->y0 = prim->y1 = yOffset;
        prim->y2 = prim->y3 = yMax;

        prim->r0 = prim->r2 = prim->g0 = prim->g2 = prim->r1 = prim->r3 =
            prim->g1 = prim->g3 = 0x10;
        prim->b0 = prim->b2 = prim->b1 = prim->b3 = 0;
        prim->drawMode =
            DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        prim->priority = 0xC1;
        prim = prim->next;

         
        if (xOffset < 0x110) {
            prim->x0 = prim->x2 = xOffset;
            prim->x1 = prim->x3 = 0x110;
            prim->y0 = prim->y1 = yOffset;
            prim->y2 = prim->y3 = yMax;
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        }
    }

    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

 
 
void EntityWaterBox(Entity* self) {
    Entity* player;
    u16 collision;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = 6;
        if (g_CastleFlags[NO4_WATER_BLOCKED]) {
            self->posX.i.hi = 0x720 - g_Tilemap.scrollX.i.hi;
        } else {
            self->posX.i.hi = 0x760 - g_Tilemap.scrollX.i.hi;
        }
    }

    player = &PLAYER;
    collision = GetPlayerCollisionWith(self, 16, 17, 5);

    if (collision & 1 && g_Player.vram_flag & TOUCHING_GROUND) {
        if (self->posX.i.hi > player->posX.i.hi) {
            if (g_pads[0].pressed & PAD_RIGHT && PLAYER.step == Player_Walk) {
                if (self->ext.timer.t) {
                    self->ext.timer.t--;
                    return;
                }
                if (self->posX.i.hi + g_Tilemap.scrollX.i.hi < 0x7A0) {
                    self->posX.i.hi++;
                    player->posX.i.hi++;
                }
                self->ext.timer.t = 3;
            }
        } else {
            if (g_pads[0].pressed & PAD_LEFT && PLAYER.step == Player_Walk) {
                if (self->ext.timer.t) {
                    self->ext.timer.t--;
                    return;
                }
                if (self->posX.i.hi + g_Tilemap.scrollX.i.hi > 0x720) {
                    self->posX.i.hi--;
                    player->posX.i.hi--;
                    if (self->posX.i.hi + g_Tilemap.scrollX.i.hi == 0x720) {
                        g_CastleFlags[NO4_WATER_BLOCKED] = 1;
                    }
                }
                self->ext.timer.t = 3;
            }
        }
    }
}

 
static u8 D_us_80181588[] = {1, 7, 1, 8, 1, 9, 0, 0};

 
void EntityWaterSpray(Entity* self) {
    Entity* newEnt;
    s16* var_s2;
    s16* var_s1;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = ANIMSET_OVL(1);
        self->palette = 0x44;
        self->drawFlags = ENTITY_MASK_R;
        self->posX.i.hi = 0x711 - g_Tilemap.scrollX.i.hi;
        if (g_CastleFlags[NO4_WATER_BLOCKED]) {
            self->ext.et_waterAlcove.waterHeight = 0x40;
        } else {
            newEnt = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (newEnt != NULL) {
                CreateEntityFromCurrentEntity(E_ID(ID_27), newEnt);
                newEnt->params = 1;
            }
            self->ext.et_waterAlcove.entity7E = newEnt;

            newEnt = AllocEntity(newEnt, &g_Entities[256]);
            if (newEnt != NULL) {
                CreateEntityFromCurrentEntity(E_ID(ID_26), newEnt);
                newEnt->params = 1;
            }
            self->ext.et_waterAlcove.entity82 = newEnt;
            self->ext.et_waterAlcove.waterHeight = 0;
        }
    }

     
    AnimateEntity(D_us_80181588, self);

    if (g_CastleFlags[NO4_WATER_BLOCKED]) {
        if (self->ext.et_waterAlcove.waterHeight < 0x40) {
            if (!(self->ext.et_waterAlcove.unk8E & 0x7)) {
                if (!self->ext.et_waterAlcove.waterHeight) {
                    g_api.PlaySfx(SFX_WATER_BUBBLE);
                }
                self->ext.et_waterAlcove.waterHeight++;
                if (self->ext.et_waterAlcove.waterHeight == 0x14) {
                    g_CastleFlags[NO4_WATER_BLOCKED]++;
                }
                if (self->ext.et_waterAlcove.waterHeight == 0x34) {
                    g_CastleFlags[NO4_WATER_BLOCKED]++;
                }
            }
            self->ext.et_waterAlcove.unk8E++;
        }

        if (self->ext.et_waterAlcove.entity7E) {
            DestroyEntity(self->ext.et_waterAlcove.entity7E);
            self->ext.et_waterAlcove.entity7E = NULL;
        }

        if (self->ext.et_waterAlcove.entity82) {
            DestroyEntity(self->ext.et_waterAlcove.entity82);
            self->ext.et_waterAlcove.entity82 = NULL;
        }
        self->animCurFrame = 0;
    }

    var_s2 = D_us_8018124C;
    var_s1 = D_us_80181150;
    var_s2 += 0x36;
    var_s1 += 0x43;

    *var_s2 = 0xB1 - self->ext.et_waterAlcove.waterHeight;
    *var_s1 = 0xB0 - self->ext.et_waterAlcove.waterHeight;

    if (self->ext.et_waterAlcove.waterHeight >= 0x40) {
        DestroyEntity(self);
    }
}

static u16 D_us_80181590[] = {0x30, 0x0F, 0x28, 0x0F, 0x18, 0x0F};

void EntityFloatingIcePlatform(Entity* self) {
    u16* hitboxPtr;
    u16 collision;
    Entity* player;
    s16 prevPosY;
    s16 dx, dy;
    u16 hitboxIndex;

    player = &PLAYER;
    hitboxIndex = self->params;

    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = hitboxIndex + 25;
        self->drawFlags = ENTITY_ROTATE;
        self->ext.et_801C4980.posY = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
    }

    hitboxPtr = &D_us_80181590[hitboxIndex * 2];

    prevPosY = self->posY.i.hi;
    self->posY.i.hi = self->ext.et_801C4980.posY - g_Tilemap.scrollY.i.hi +
                      self->ext.et_801C4980.timer;
#ifdef VERSION_PSP
    collision = GetPlayerCollisionWith(self, hitboxPtr[0], hitboxPtr[1], 4);
#else
    collision = GetPlayerCollisionWith(self, *hitboxPtr++, *hitboxPtr, 4);
#endif
    self->posY.i.hi = prevPosY;
    self->ext.et_801C4980.prevTimer = self->ext.et_801C4980.timer;

    dx = self->posX.i.hi - player->posX.i.hi;

    if (collision) {
        if (self->ext.et_801C4980.timer < 4) {
            self->ext.et_801C4980.timer++;
        }
    } else {
        if (self->ext.et_801C4980.timer) {
            self->ext.et_801C4980.timer--;
        }
    }

    dy = self->ext.et_801C4980.timer;
    if (dx < 0) {
        prevPosY = (dx * dy * -0x100) / 56;
    } else {
        prevPosY = (dx * dy * 0x100) / 56;
    }

    self->posY.i.hi = (self->ext.et_801C4980.posY - g_Tilemap.scrollY.i.hi) +
                      (dy - prevPosY / 256);

    if (collision) {
        dy = dy - self->ext.et_801C4980.prevTimer;
        player->posY.i.hi += dy;
        g_unkGraphicsStruct.shoveX.i.hi += dy;
    }

    prevPosY = -prevPosY;
    if (collision || dy) {
        if (dx < 0) {
            self->rotate = ratan2(prevPosY, -0x3800);
            self->rotate = (self->rotate - 0x800) & 0xFFF;
            return;
        }
        self->rotate = ratan2(prevPosY, 0x3800);
    } else {
        self->rotate = 0;
    }
}

static s16 D_us_8018159C[] = {
    0, -2048, 77, -8, 0, -2048, 127, -8, 256, 2048, 77, 8, 256, 2048, 127, 8,
};

void func_us_801C4BD8(Entity* self) {
    Entity* player;
    s16* dataPtr;
    s32 volume;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
    }

    player = &PLAYER;
    dataPtr = &D_us_8018159C[self->params * 4];

    volume = player->posX.i.hi + g_Tilemap.scrollX.i.hi - *dataPtr++;
    volume = (volume * *dataPtr++) / 0x1000;
    volume += *dataPtr++;

    if (volume < 0) {
        volume = 0;
    } else if (volume > 0x7F) {
        volume = 0x7F;
    }

    if (!volume) {
        if (D_us_80181108) {
            D_us_80181108 = false;
            g_api.PlaySfx(SET_UNK_A6);
            return;
        }
    }
    if (D_us_80181108) {
        g_api.SetVolumeCommand22_23(volume, *dataPtr++);
        return;
    }

    g_api.PlaySfxVolPan(SFX_WATERFALL_LOOP, volume, *dataPtr++);
    D_us_80181108 = true;
}

void func_us_801C4D2C(Entity* self) {
    s16 minX, maxX;
    s16 x, y;
    u16 playerInRange;
    u16* tilePtr;
    Entity* newEntity;
    Tilemap* tilemap;
    Entity* player;
    u16 tile;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
    }

    player = &PLAYER;
    tilemap = &g_Tilemap;

     
    if (g_pads[1].tapped & PAD_TRIANGLE) {
        g_api.PlaySfx(SFX_WOODEN_BRIDGE_EXPLODE);
    }

    playerInRange = false;
    if (!(g_Player.status &
          (PLAYER_STATUS_BAT_FORM | PLAYER_STATUS_MIST_FORM))) {
        y = player->posY.i.hi + tilemap->scrollY.i.hi;
        if (g_Player.status & PLAYER_STATUS_WOLF_FORM) {
            if (y > 0x97 && y < 0xAB) {
                playerInRange = true;
                minX = player->posX.i.hi + tilemap->scrollX.i.hi - 12;
                maxX = minX + 24;
            }
        } else {
            if (y > 0x97 && y < 0xC7) {
                playerInRange = true;
                minX = player->posX.i.hi + tilemap->scrollX.i.hi - 8;
                maxX = minX + 16;
            }
        }
    }

    if (!playerInRange) {
        return;
    }
    for (x = minX; x <= maxX; x += 8) {
        playerInRange = false;
        if ((x >= 0xA40 && x < 0xAE0) || (x >= 0xB80 && x < 0xBE0)) {
            playerInRange = true;
        }

        if (!playerInRange) {
            continue;
        }
        tilePtr = &tilemap->fg[x / 16] + 0x8F0;
        tile = *tilePtr;

        if (tile == 0x701 || tile == 0x705) {
            newEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (newEntity) {
                CreateEntityFromCurrentEntity(E_ID(ID_54), newEntity);
                newEntity->posX.i.hi =
                    ((x & 0xFFF0) + 8) - tilemap->scrollX.i.hi;
                newEntity->posY.i.hi = 0xB2 - tilemap->scrollY.i.hi;
                if (player->posX.i.hi > newEntity->posX.i.hi) {
                    newEntity->params = 1;
                }
            }
            *tilePtr = 0xAC7;
        } else if (tile == 0x70C) {
            newEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (newEntity) {
                CreateEntityFromCurrentEntity(E_ID(ID_54), newEntity);
                newEntity->posX.i.hi =
                    ((x & 0xFFF0) + 8) - tilemap->scrollX.i.hi;
                newEntity->posY.i.hi = 0xB2 - tilemap->scrollY.i.hi;
                if (player->posX.i.hi > newEntity->posX.i.hi) {
                    newEntity->params = 1;
                }
            }
            *tilePtr = 0x59D;
        }
    }
}

void func_us_801C5020(Entity* self) {
    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = 12;
        self->drawFlags = ENTITY_OPACITY | ENTITY_ROTATE;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        self->opacity = 0x80;
        self->rotate = 0;
        self->zPriority = 0x9F;
        PlaySfxPositional(SFX_UNK_NO4_7BE);
    }

    if (self->params) {
        self->rotate += 0x20;
    } else {
        self->rotate -= 0x20;
    }

    self->posY.val += FIX(0.5);
    self->opacity -= 4;

    if (self->opacity < 8) {
        DestroyEntity(self);
    }
}

static void RemoveBridgeTiles(void) {
    u16* tile;
    s16 i;

    tile = &g_Tilemap.fg[691];

    for (i = 0; i < 10; i++) {
        *tile++ = 0;
    }
}

static s16 D_us_801815BC[] = {-72, -32, 32, 72, -72, -32, 32, 72};
static s16 D_us_801815CC[] = {7, 4, 4, 7, 7, 4, 4, 7};

void func_us_801C5134(void) {
    Entity* newEntity;
    s16 offsetX;
    s32 i;

    PlaySfxPositional(SFX_WOODEN_BRIDGE_EXPLODE);

    for (i = 1; i < 4; i++) {
        newEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (newEntity == NULL) {
            break;
        }
        CreateEntityFromCurrentEntity(E_ID(ID_5C), newEntity);
        newEntity->posX.i.hi += D_us_801815BC[i];
        newEntity->posY.i.hi += D_us_801815CC[i];
        newEntity->params = i;
    }

    offsetX = -72;
    for (i = 0; i < 10; i++) {
        newEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (newEntity == NULL) {
            break;
        }
        CreateEntityFromCurrentEntity(E_EXPLOSION, newEntity);
        newEntity->params = 17;
        newEntity->posX.i.hi += ((rand() & 7) * 2) + offsetX - 7;
        newEntity->posY.i.hi += ((rand() & 7) * 4) - 7;
        offsetX += 16;
    }
}

 
void func_us_801C5268(Entity* self) {
    Entity* entity;
    s16 offsetX;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = ANIMSET_OVL(0);
        self->posX.i.hi = 0x380 - g_Tilemap.scrollX.i.hi;
        if (g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE] > 1) {
            RemoveBridgeTiles();
            DestroyEntity(self);
            return;
        }
    }
    if (g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE] == 1) {
        if (!self->step_s) {
            entity = &g_Entities[88];
            if (entity->entityId == E_ID(SKELETON_APE)) {
                entity = entity->ext.et_801C5268.unk80;
                if (entity) {
                    self->ext.et_801C5268.unk7C = entity;
                    self->step_s++;
                }
            }
        } else {
            entity = self->ext.et_801C5268.unk7C;
            if (entity->entityId != E_ID(SKELETON_APE_BARREL)) {
                self->step_s = 0;
            } else if (entity->step == 4 &&
                       entity->posY.i.hi + g_Tilemap.scrollY.i.hi > 128) {
                offsetX = entity->posX.i.hi + g_Tilemap.scrollX.i.hi;
                if (offsetX > 0x328 && offsetX < 0x3D8) {
                    g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE] = 2;
                }
            }
        }
    }
    if (g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE] == 2 ||
        g_pads[1].tapped & PAD_TRIANGLE) {
        PlaySfxPositional(SFX_WOODEN_BRIDGE_EXPLODE);
        g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE]++;
        RemoveBridgeTiles();
        func_us_801C5134();
    }
}

static u16 D_us_801815DC[] = {11, 10, 10, 11, 11, 10, 10, 11};
static u16 D_us_801815EC[] = {0, 0, 1, 1, 0, 0, 1, 1};
static s16 D_us_801815FC[] = {
    -0x100, -0x40, -0x28, -0x120, -0x100, -0x40, -0x28, -0x120,
};
static s32 D_us_8018160C[] = {
    FIX(-3), FIX(-2.5), FIX(-3.125), FIX(-2.25),
    FIX(-3), FIX(-2.5), FIX(-3.125), FIX(-2.25),
};

void func_us_801C542C(Entity* self) {
    u16 params = self->params;
    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = D_us_801815DC[params];
        self->facingLeft = D_us_801815EC[params];
        self->velocityY = D_us_8018160C[params];
        self->drawFlags = ENTITY_ROTATE;
        self->rotate = false;
    }
    if (F(self->velocityY).i.hi < 8) {
        self->velocityY += FIX(0.25);
    }
    MoveEntity();
    self->rotate += D_us_801815FC[params];
}

static s16 D_us_8018162C[] = {
    0x260, 0x020, 0x0D0, 0x080, 0x470, 0x020,
    0x0D0, 0x080, 0x0C0, 0x02C, 0x0E0, 0x500,
};

void func_us_801C5518(Entity* self) {
    Entity* player;
    u16 diff;
    s16* dataPtr;

    player = &PLAYER;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
    }

    dataPtr = &D_us_8018162C[self->params * 4];

    diff = player->posX.i.hi + g_Tilemap.scrollX.i.hi - *dataPtr++;
    if (diff > *dataPtr++) {
        return;
    }
    diff = player->posY.i.hi + g_Tilemap.scrollY.i.hi - *dataPtr++;
    if (diff > *dataPtr++) {
        return;
    }
    if (player->velocityY < 0) {
        player->velocityY *= 7;
        player->velocityY /= 8;
    } else if (player->velocityY > 0) {
        player->nFramesInvincibility = 1;
    }
}

#ifdef VERSION_PSP
static char* D_us_80181644;

static char D_pspeu_0929D7F0[] =
    "\xB4\x24Something appeared\001by the wooden bridge.";
static char D_pspeu_0929D820[] =
    "\xB4\x24Hay algo junto al\001puente de madera.";
static char D_pspeu_0929D848[] =
    "\xB4\x24" _SE("È apparso qualcosa\001vicino al ponte.");
static char D_pspeu_0929D870[] =
    "\xB4\x24" _SE("Une chose est apparue\001près du pont en bois.");
static char D_pspeu_0929D8A0[] =
    "\xB4\x24" _SE("Etwas ist bei der\001Holzbrücke erschienen.");
#elif defined(VERSION_PC)  
static char D_us_80181644[] =
    "\xB8\x1ESomething appeared near\001to the wooden bridge\x81\x44";
#else
static char D_us_80181644[] =
    "\xB8\x1ESomething appeared near\001to the wooden bridge．";
#endif

 
void func_us_801C5628(Entity* self) {
    Entity* player;
    u16 collision;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = 40;
        if (!g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE]) {
            self->posX.i.hi = 52;
        } else {
            self->posX.i.hi = 44;
        }
    }

    player = &PLAYER;

    collision = GetPlayerCollisionWith(self, 8, 16, 5);

    if (collision & 1 && g_Player.vram_flag & TOUCHING_GROUND) {
        if (g_pads[0].pressed & PAD_LEFT && PLAYER.step == 1) {
            if (self->ext.et_801C4520.unk7C) {
                self->ext.et_801C4520.unk7C--;
            } else {
                if (self->posX.i.hi > 44) {
                    self->posX.i.hi--;
                    player->posX.i.hi--;
                    if (self->posX.i.hi == 44) {
                        g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE] = 1;
                        PlaySfxPositional(SFX_SWITCH_CLICK);
                        self->step++;
                    }
                }
                self->ext.et_801C4520.unk7C = 2;
            }
        }
    }

#ifdef VERSION_PSP
    D_us_80181644 = func_pspeu_0923D4A0(
        0, D_pspeu_0929D7F0, D_pspeu_0929D870, D_pspeu_0929D820,
        D_pspeu_0929D8A0, D_pspeu_0929D848);
#endif

    if (self->step == 2 && player->posX.i.hi > 0x80) {
        g_api.PlaySfxVolPan(SFX_WALL_DEBRIS_A, 0x7F, 8);
        player = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (player != NULL) {
            CreateEntityFromCurrentEntity(E_MESSAGE_BOX, player);
            player->posX.i.hi = 0x80;
            player->posY.i.hi = 0xB0;
            player->ext.messageBox.label = D_us_80181644;
            player->params = 0x100;
        }
        self->step++;
    }
}

void func_us_801C582C(Entity* self) {
    if (g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE]) {
        self->entityId = E_ID(SKELETON_APE);
        self->pfnUpdate = EntitySkeletonApe;
        EntitySkeletonApe(self);
    }
}

void func_us_801C5868(void) {
    u16* tile;
    s16 i;

    tile = &g_Tilemap.fg[163];

    for (i = 0; i < 10; i++) {
        *tile++ = 0;
    }
}

void func_us_801C58A0(Entity* self) {
    Entity* newEnt;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        if (g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE]) {
            func_us_801C5868();
            DestroyEntity(self);
        }
        break;

    case 1:
        if (g_CastleFlags[NO4_SKELETON_APE_AND_BRIDGE]) {
            newEnt = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (newEnt != NULL) {
                CreateEntityFromCurrentEntity(E_ID(SKELETON_APE), newEnt);
                newEnt->params = 2;
                newEnt->posY.i.hi -= 0x60;
                newEnt->posX.i.hi += 0x60;
                self->ext.et_801C5268.unk7C = newEnt + 2;
            }
            self->step++;
        }
        break;

    case 2:
        if (self->ext.et_801C5268.unk7C->step == 4) {
            func_us_801C5868();
            func_us_801C5134();
            DestroyEntity(self);
        }
        break;
    }
}


INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C1EE4_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5C78);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5EE4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2850_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2B78_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2E60_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3160_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C34EC_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C37C8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3A04_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3CC4_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3FB0_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C4228_from_no4);

#define PLAYER g_Entities[PLAYER_CHARACTER]
#define PLAYER_CHARACTER 0
#define NO4_WATER_BLOCKED 193
#define PAD_LEFT 32768
#define PAD_RIGHT 8192
#define Player_Walk 1
#define TOUCHING_GROUND 1
extern EInit g_EInitInteractable;
extern struct Entity;
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
void InitializeEntity(u16 arg0[]);

void EntityWaterBox(Entity* self) {
    Entity* player;
    u16 collision;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = 6;
        if (g_CastleFlags[NO4_WATER_BLOCKED]) {
            self->posX.i.hi = 0x720 - g_Tilemap.scrollX.i.hi;
        } else {
            self->posX.i.hi = 0x760 - g_Tilemap.scrollX.i.hi;
        }
    }

    player = &PLAYER;
    collision = GetPlayerCollisionWith(self, 16, 17, 5);

    if (collision & 1 && g_Player.vram_flag & TOUCHING_GROUND) {
        if (self->posX.i.hi > player->posX.i.hi) {
            if (g_pads[0].pressed & PAD_RIGHT && PLAYER.step == Player_Walk) {
                if (self->ext.timer.t) {
                    self->ext.timer.t--;
                    return;
                }
                if (self->posX.i.hi + g_Tilemap.scrollX.i.hi < 0x7A0) {
                    self->posX.i.hi++;
                    player->posX.i.hi++;
                }
                self->ext.timer.t = 3;
            }
        } else {
            if (g_pads[0].pressed & PAD_LEFT && PLAYER.step == Player_Walk) {
                if (self->ext.timer.t) {
                    self->ext.timer.t--;
                    return;
                }
                if (self->posX.i.hi + g_Tilemap.scrollX.i.hi > 0x720) {
                    self->posX.i.hi--;
                    player->posX.i.hi--;
                    if (self->posX.i.hi + g_Tilemap.scrollX.i.hi == 0x720) {
                        g_CastleFlags[NO4_WATER_BLOCKED] = 1;
                    }
                }
                self->ext.timer.t = 3;
            }
        }
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C81C8);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityFloatingIcePlatform);

#define PLAYER g_Entities[PLAYER_CHARACTER]
#define PLAYER_CHARACTER 0
#define SET_UNK_A6 0xA6
#define SFX_WATERFALL_LOOP 1943
#define false 0
#define true 1
extern bool D_us_8018104C;
extern s16 D_us_801814E8[16];
extern EInit g_EInitInteractable;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void func_us_801C4BD8_from_no4(Entity* self) {
    Entity* player;
    s16* dataPtr;
    s32 volume;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
    }

    player = &PLAYER;
    dataPtr = &D_us_801814E8[self->params * 4];

    volume = player->posX.i.hi + g_Tilemap.scrollX.i.hi - *dataPtr++;
    volume = (volume * *dataPtr++) / 0x1000;
    volume += *dataPtr++;

    if (volume < 0) {
        volume = 0;
    } else if (volume > 0x7F) {
        volume = 0x7F;
    }

    if (!volume) {
        if (D_us_8018104C) {
            D_us_8018104C = false;
            g_api_PlaySfx(SET_UNK_A6);
            return;
        }
    }
    if (D_us_8018104C) {
        g_api_SetVolumeCommand22_23(volume, *dataPtr++);
        return;
    }

    g_api_PlaySfxVolPan(SFX_WATERFALL_LOOP, volume, *dataPtr++);
    D_us_8018104C = true;
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8668);

void RNO4_Unused801C8704(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C870C);

void RNO4_Unused801C8768(void) {}

void RNO4_Unused801C8770(void) {}

#define DRAW_HIDE 8
#define DRAW_UNK02 2
#define FLAG_HAS_PRIMS 8388608
#define PRIM_GT4 4
extern u16 D_us_80181508[16];
extern u8 D_us_80181528[2][4];
extern s16 D_us_80181530[12];
extern s16 D_us_80181548[60];
extern EInit g_EInitInteractable;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void EntityBoatElevatorChains(Entity* self) {
    u32 primIndex;
    u32 scrollX;

    u32 scrollY;
    s16 cos;
    u8* ptr;
    s32 i;
    s16* ptrTwo;
    s16 sin;
    s16 xOffset;
    s16 yOffset;
    Primitive* prim;

    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 13);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];

            i = 0;
            while (prim != NULL) {
                prim->tpage = 0xF;
                prim->clut = 0x5F;
                ptr = *D_us_80181528;
                ptr += D_us_80181508[i] * 4;
                prim->u0 = prim->u2 = *ptr++;
                prim->u1 = prim->u3 = *ptr++;
                prim->v0 = prim->v1 = *ptr++;
                prim->v2 = prim->v3 = *ptr;
                prim->priority = 0x80;
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
                i++;
            }
            self->rotate = 0x200;
        } else {
            self->step = 0;
            return;
        }
    }

    if (self->ext.boatElevator_child.unk7C) {
        if (self->ext.boatElevator_child.unk7C < 0) {
            self->ext.boatElevator_child.unk7E++;
            self->rotate += 0x10;
        } else {
            self->ext.boatElevator_child.unk7E--;
            self->rotate -= 0x10;
        }
    }
    self->ext.boatElevator_child.unk7E &= 0xF;
    prim = &g_PrimBuf[self->primIndex];
    i = 0;
    while (prim != NULL) {
        if (i < 3) {
            ptrTwo = &D_us_80181530[(self->params * 6) + (i * 2)];
            xOffset = *ptrTwo++ - scrollX;
            yOffset = *ptrTwo - scrollY;
            if (self->params) {
                sin = (rsin(-self->rotate) * 0x1A) >> 0xC;
                cos = (rcos(-self->rotate) * 0x1A) >> 0xC;
            } else {
                sin = (rsin(self->rotate) * 0x1A) >> 0xC;
                cos = (rcos(self->rotate) * 0x1A) >> 0xC;
            }

            prim->x0 = xOffset - cos;
            prim->x1 = xOffset + sin;
            prim->x2 = xOffset - sin;
            prim->x3 = xOffset + cos;
            prim->y0 = yOffset - sin;
            prim->y1 = yOffset - cos;
            prim->y2 = yOffset + cos;
            prim->y3 = yOffset + sin;
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        } else {
            ptrTwo = &D_us_80181548[(self->params * 3) * 10 + ((i - 3) * 3)];
            sin = *ptrTwo++;
            xOffset = *ptrTwo++ - scrollX;
            yOffset = *ptrTwo - scrollY;
            switch (sin) {
            case 0:
                prim->x0 = prim->x2 = xOffset - 4;
                prim->x1 = prim->x3 = xOffset + 4;
                yOffset += self->ext.boatElevator_child.unk7E;
                prim->y0 = prim->y1 = yOffset;
                prim->y2 = prim->y3 = yOffset + 0x60;
                break;
            case 1:
                prim->x0 = prim->x2 = xOffset - 4;
                prim->x1 = prim->x3 = xOffset + 4;
                yOffset -= self->ext.boatElevator_child.unk7E;
                prim->y0 = prim->y1 = yOffset;
                prim->y2 = prim->y3 = yOffset + 0x60;
                break;
            case 2:
                xOffset -= self->ext.boatElevator_child.unk7E;
                prim->x0 = prim->x1 = xOffset;
                prim->x2 = prim->x3 = xOffset + 0x60;
                prim->y1 = prim->y3 = yOffset - 4;
                prim->y0 = prim->y2 = yOffset + 4;
                break;
            case 3:
                xOffset += self->ext.boatElevator_child.unk7E;
                prim->x0 = prim->x1 = xOffset;
                prim->x2 = prim->x3 = xOffset + 0x60;
                prim->y1 = prim->y3 = yOffset - 4;
                prim->y0 = prim->y2 = yOffset + 4;
                break;
            }
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        }
        i++;
    }
}

void RNO4_Unused801C8BD4(void) {}

void RNO4_Unused801C8BDC(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", LoadFerrymanGateTiles);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8C54);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A071C_from_bo3);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A07CC_from_bo3);

#define PLAYER g_Entities[PLAYER_CHARACTER]
#define PLAYER_CHARACTER 0
extern s16 D_us_801815F8[12];
extern EInit g_EInitInteractable;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void func_us_801C5518_from_no4(Entity* self) {
    Entity* player;
    u16 diff;
    s16* dataPtr;

    player = &PLAYER;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
    }

    dataPtr = &D_us_801815F8[self->params * 4];

    diff = player->posX.i.hi + g_Tilemap.scrollX.i.hi - *dataPtr++;
    if (diff > *dataPtr++) {
        return;
    }
    diff = player->posY.i.hi + g_Tilemap.scrollY.i.hi - *dataPtr++;
    if (diff > *dataPtr++) {
        return;
    }
    if (player->velocityY < 0) {
        player->velocityY *= 7;
        player->velocityY /= 8;
    } else if (player->velocityY > 0) {
        player->nFramesInvincibility = 1;
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C9048);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C909C);

extern s32 D_us_80181698[6];
extern u8 D_us_801816B0[4];
extern u16 D_us_801816B4[4];

void EntityExplosionVariants(Entity* self) {
    if (!self->step) {
        self->velocityY = D_us_80181698[self->ext.destructAnim.index];
        self->flags =
            FLAG_UNK_2000 | FLAG_KEEP_ALIVE_OFFCAMERA | FLAG_POS_CAMERA_LOCKED;
        self->palette = PAL_FLAG(PAL_UNK_195);
        self->animSet = ANIMSET_DRA(2);
        self->animCurFrame = D_us_801816B0[self->params];
        self->blendMode = BLEND_TRANSP;
        self->step++;
    } else {
        self->posY.val -= self->velocityY;
        ++self->poseTimer;
        if ((self->poseTimer % 2) == 0) {
            self->animCurFrame++;
        }

        if (self->poseTimer > D_us_801816B4[self->params]) {
            DestroyEntity(self);
        }
    }
}

extern s16 D_us_80181670[8];
extern s32 D_us_80181680[6];

void EntityGreyPuff(Entity* self) {
    if (!self->step) {
        self->flags =
            FLAG_UNK_2000 | FLAG_KEEP_ALIVE_OFFCAMERA | FLAG_POS_CAMERA_LOCKED;
        self->palette = PAL_FLAG(PAL_UNK_195);
        self->animSet = ANIMSET_DRA(5);
        self->animCurFrame = 1;
        self->blendMode = BLEND_TRANSP;
        self->drawFlags = ENTITY_SCALEX | ENTITY_SCALEY;
        self->scaleX = D_us_80181670[self->params];
        self->scaleY = self->scaleX;
        self->velocityY = D_us_80181680[self->params];
        self->step++;
    } else {
        self->posY.val -= self->velocityY;
        self->poseTimer++;
        if ((self->poseTimer % 2) == 0) {
            self->animCurFrame++;
        }
        if (self->poseTimer > 36) {
            DestroyEntity(self);
        }
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityIntenseExplosion);

int abs(int x);

void PlaySfxPositional(s16 sfxId) {
    s32 posX, posY;
    s16 sfxPan;
    s16 sfxVol;

    posX = g_CurrentEntity->posX.i.hi - 128;
    sfxPan = (abs(posX) - 32) >> 5;
    if (sfxPan > 8) {
        sfxPan = 8;
    } else if (sfxPan < 0) {
        sfxPan = 0;
    }
    if (posX < 0) {
        sfxPan = -sfxPan;
    }
    sfxVol = abs(posX) - 96;
    posY = abs(g_CurrentEntity->posY.i.hi - 128) - 112;
    if (posY > 0) {
        sfxVol += posY;
    }
    if (sfxVol < 0) {
        sfxVol = 0;
    }
    sfxVol = 127 - (sfxVol >> 1);
    if (sfxVol > 0) {
        g_api.PlaySfxVolPan(sfxId, sfxVol, sfxPan);
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakableCrystalFloor);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakableWall);
