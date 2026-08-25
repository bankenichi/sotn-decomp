/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:ST/RLIB:func_us_801AE8E8_from_lib
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/lib/first_c_file.c
   target : src/st/rlib/unk_20AE8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rlib.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
void PlaySfxPositional(s32 arg0);
void SetGeomScreen(long h);
MATRIX* RotMatrix(SVECTOR* r, MATRIX* m);
MATRIX* TransMatrix(MATRIX* m, VECTOR* v);
void SetRotMatrix(MATRIX* m);
void SetTransMatrix(MATRIX* m);
void SetBackColor(long rbk, long gbk, long bbk);
void SetLightMatrix(MATRIX* m);
void SetColorMatrix(MATRIX* m);
void SetFarColor(long rfc, long gfc, long bfc);
void SetFogNear(long a, long h);
void SetGeomOffset(long ofx, long ofy);
long RotTransPers(SVECTOR*, long*, long*, long*);
long NormalClip(long sxy0, long sxy1, long sxy2);
int abs(int x);
int rcos(int a);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int labs();
extern int VectorNormalS();
extern int NormalColorDpq();
extern int UnkRecursivePrimFunc2();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", EntityBreakable);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AE7AC_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AE84C_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AF280_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AF538_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AF7B8_from_lib);

INCLUDE_ASM("st/rlib/nonmatchings/unk_20AE8", func_us_801AFA80_from_lib);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern unkGraphicsStruct g_unkGraphicsStruct;
extern PlayerState g_Player;
extern u8 g_CastleFlags[];
extern u32 g_Timer;

void func_us_801AE8E8_from_lib(Entity* self) {
    s32 primIndex;
    long p, flag;
    SVECTOR rot;
    VECTOR trans;
    MATRIX m;
    MATRIX lightMatrix;
    CVECTOR sp68;
    SVECTOR sp70;
    s32 iterations;
    Primitive* prim;
    Primitive* prim2;
    SVECTOR** temp_a0_2;
    VECTOR** temp_a0_3;
    s16 temp_v1_2;
    s32 i;
    s16 posX;
    s16 dx;
    s32 clipper;

    Entity* player = &PLAYER;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->zPriority = 0x70;
        self->hitboxWidth = 0xC;
        self->hitboxHeight = 0x30;
        self->hitboxOffY = -0x30;
        self->ext.et_801AE8E8.unk80 = -0xC0;
        self->ext.et_801AE8E8.unk84 = 0;
        self->ext.et_801AE8E8.unk88 = 0;
        self->ext.et_801AE8E8.unk8C = 0x40;
        self->ext.et_801AE8E8.unk82 = 0x60;
        if (self->params) {
            self->ext.et_801AE8E8.unk80 = D_us_80180DA8[self->params];
            self->step = 4;
        }
        self->ext.et_801AE8E8.unk90 = D_us_80180DB0[self->params];
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 0x25);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.et_801AE8E8.unk7C = prim;
            for (i = 0; i < 2; i++) {
                prim->tpage = 0xF;
                prim->clut = 0x32;
                prim->u0 = prim->u2 = 4;
                prim->u1 = prim->u3 = 0x1C;
                prim->v0 = prim->v1 = 0x84;
                prim->v2 = prim->v3 = 0xE4;
                prim->r0 = prim->g0 = prim->b0 = 0x80;
                LOW(prim->r1) = LOW(prim->r0);
                LOW(prim->r2) = LOW(prim->r0);
                LOW(prim->r3) = LOW(prim->r0);
                prim->priority = self->zPriority - self->params;
                prim->drawMode = DRAW_DITHERING | DRAW_COLORS | DRAW_UNK02;
                prim = prim->next;
            }
            for (i = 0; i < 2; i++) {
                prim->tpage = 0xF;
                prim->clut = 0x33;
                prim->u0 = prim->u2 = 0x24;
                prim->u1 = prim->u3 = 0x64;
                prim->v0 = prim->v1 = 0x84;
                prim->v2 = prim->v3 = 0xE4;
                prim->r0 = prim->g0 = prim->b0 = 0x80;
                LOW(prim->r1) = LOW(prim->r0);
                LOW(prim->r2) = LOW(prim->r0);
                LOW(prim->r3) = LOW(prim->r0);
                prim->priority = self->zPriority - self->params;
                prim->drawMode = DRAW_DITHERING | DRAW_COLORS | DRAW_UNK02;
                prim = prim->next;
            }
            if (self->params) {
                prim->drawMode = DRAW_HIDE;
            } else {
                self->ext.et_801AE8E8.unk94 = prim;
                prim->type = PRIM_G4;
                prim->x0 = prim->x2 = self->posX.i.hi;
                prim->x1 = prim->x3 = 0x100;
                prim->y0 = self->posY.i.hi - 0x58;
                prim->y1 = self->posY.i.hi - 0x40;
                prim->y2 = prim->y3 = self->posY.i.hi;
                prim->priority = self->zPriority - 1;
                prim->drawMode =
                    DRAW_DITHERING | DRAW_UNK_40 | DRAW_TPAGE | DRAW_TRANSP;
            }
            prim = prim->next;
            self->ext.et_801AE8E8.unk98 = prim;
            while (prim != NULL) {
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
            }
        } else {
            DestroyEntity(self);
            return;
        }
        break;

    case 1:
        self->ext.et_801AE8E8.unk88 = 0;
        prim = NULL;
        temp_v1_2 = self->ext.et_801AE8E8.unk80 & 0xFFF;
        if (temp_v1_2 < 0x380 || temp_v1_2 > 0xC80) {
            prim = self->ext.et_801AE8E8.unk7C;
        }
        if (temp_v1_2 > 0x480 && temp_v1_2 < 0xB80) {
            prim = self->ext.et_801AE8E8.unk7C;
            prim = prim->next;
        }
        if (prim != NULL) {
            posX = player->posX.i.hi;
            if (prim->x0 > posX) {
                self->step_s = 0;
            } else {
                self->step_s = 1;
            }
            switch (self->step_s) {
            case 0:
                posX = prim->x0;
                dx = player->posX.i.hi + 10 - posX;
                if (dx >= 0) {
                    player->posX.i.hi -= dx;
                    g_unkGraphicsStruct.shoveX.i.hi -= dx;
                    g_Player.vram_flag |= VRAM_FLAG_UNK40 | TOUCHING_R_WALL;
                    if (!g_CastleFlags[LIB_BOOKSHELF_SECRET]) {
                        if (--self->ext.et_801AE8E8.unk82) {
                            break;
                        }
                        g_CastleFlags[LIB_BOOKSHELF_SECRET] = 1;
                    }
                    if (player->velocityX != 0) {
                        if ((g_Timer & 0xF) == 0) {
                            PlaySfxPositional(SFX_STONE_MOVE_B);
                        }
                        self->ext.et_801AE8E8.unk88 = -0x600;
                    }
                }
                break;
            case 1:
                posX = prim->x1;
                dx = player->posX.i.hi - 10 - posX;
                if (dx <= 0) {
                    player->posX.i.hi -= dx;
                    g_unkGraphicsStruct.shoveX.i.hi -= dx;
                    g_Player.vram_flag |= VRAM_FLAG_UNK40 | TOUCHING_L_WALL;
                    if (!g_CastleFlags[LIB_BOOKSHELF_SECRET]) {
                        if (--self->ext.et_801AE8E8.unk82) {
                            break;
                        }
                        g_CastleFlags[LIB_BOOKSHELF_SECRET] = 1;
                    }
                    if (player->velocityX != 0) {
                        if ((g_Timer & 0xF) == 0) {
                            PlaySfxPositional(SFX_STONE_MOVE_B);
                        }
                        self->ext.et_801AE8E8.unk88 = 0x600;
                    }
                }
                break;
            }
            if (labs(self->ext.et_801AE8E8.unk84) > 0x1000) {
                self->ext.et_801AE8E8.unk8C = 2;
            }
        }
        break;
    }

    self->ext.et_801AE8E8.unk84 += self->ext.et_801AE8E8.unk88;
    if (self->ext.et_801AE8E8.unk84 != 0) {
        self->ext.et_801AE8E8.unk84 -=
            (self->ext.et_801AE8E8.unk88 / self->ext.et_801AE8E8.unk84);
    }
    self->ext.et_801AE8E8.unk84 -=
        (self->ext.et_801AE8E8.unk84 * self->ext.et_801AE8E8.unk8C) / 0x100;
    self->ext.et_801AE8E8.unk80 += self->ext.et_801AE8E8.unk84 / 0x1000;
    prim = self->ext.et_801AE8E8.unk7C;
    SetGeomScreen(0x200);
    rot.vx = 0;
    rot.vy = self->ext.et_801AE8E8.unk80;
    rot.vz = 0;
    RotMatrix(&rot, &m);
    trans.vx = 0;
    trans.vy = 0;
    trans.vz = 0x228;
    if (self->params) {
        trans.vz += self->ext.et_801AE8E8.unk90;
    }
    TransMatrix(&m, &trans);
    SetRotMatrix(&m);
    SetTransMatrix(&m);
    sp68.r = 0x90;
    sp68.g = 0x90;
    sp68.b = 0x90;
    sp68.cd = prim->type;
    RotMatrix(&rot, &lightMatrix);
    SetBackColor(0x58, 0x58, 0x58);
    SetLightMatrix(&lightMatrix);
    SetColorMatrix(&D_us_80180D88);
    SetFarColor(0x40, 0x40, 0x40);
    SetFogNear(0x218, 0x200);
    SetGeomOffset(self->posX.i.hi, self->posY.i.hi);
    temp_a0_2 = D_us_80180C88;
    temp_a0_3 = D_us_80180D28;
    prim2 = self->ext.et_801AE8E8.unk98;
    for (i = 0; i < 8; i++) {
        RotTransPers(*temp_a0_2, &((long*)SPAD(0))[i], &p, &flag);
        VectorNormalS(*temp_a0_3, &sp70);
        NormalColorDpq(&sp70, &sp68, p, &((long*)SPAD(8))[i]);
        temp_a0_2++;
        temp_a0_3++;
    }
    if (!self->params) {
#ifdef VERSION_PSP
        iterations = 1;
#else
        iterations = 2;
#endif
    } else {
        iterations = 1;
    }
    prim = self->ext.et_801AE8E8.unk7C;
    for (i = 0; i < 4; i++) {
        LOW(prim->x0) = SPAD(0)[D_us_80180D48[i * 4 + 0]];
        LOW(prim->x1) = SPAD(0)[D_us_80180D48[i * 4 + 1]];
        LOW(prim->x2) = SPAD(0)[D_us_80180D48[i * 4 + 2]];
        LOW(prim->x3) = SPAD(0)[D_us_80180D48[i * 4 + 3]];
        LOW(prim->r0) = SPAD(8)[D_us_80180D48[i * 4 + 0]];
        LOW(prim->r1) = SPAD(8)[D_us_80180D48[i * 4 + 1]];
        LOW(prim->r2) = SPAD(8)[D_us_80180D48[i * 4 + 2]];
        LOW(prim->r3) = SPAD(8)[D_us_80180D48[i * 4 + 3]];
        clipper = NormalClip(LOW(prim->x0), LOW(prim->x1), LOW(prim->x2));
        prim->drawMode &= ~DRAW_HIDE;
        if (clipper <= 0) {
            prim->drawMode |= DRAW_HIDE;
        } else {
            prim2 = (Primitive*)UnkRecursivePrimFunc2(
                prim, iterations, prim2, (u8*)SPAD(16));
            prim->drawMode |= DRAW_HIDE;
        }
        prim = prim->next;
    }
    while (prim2 != NULL) {
        prim2->drawMode = DRAW_HIDE;
        prim2 = prim2->next;
    }
    if (!self->params) {
        prim = self->ext.et_801AE8E8.unk94;
        prim->r0 = abs(rcos(self->ext.et_801AE8E8.unk80)) * 0x28 / 0x1000;
        prim->g0 = prim->b0 = prim->r0;
        LOW(prim->r1) = LOW(prim->r0);
        LOW(prim->r2) = LOW(prim->r0);
        LOW(prim->r3) = LOW(prim->r0);
    }
}
