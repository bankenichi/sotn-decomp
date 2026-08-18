/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/MAD:func_8018DC28
   attempt: 1/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/mad/nonmatchings/D8C8/func_8018DC28.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "mad.h"
#include "sfx.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
void func_8018E1D4();
extern int rand(void);

void func_8018D8C8(u16* tilemap);
INCLUDE_ASM("asm/us/st/mad/nonmatchings/D8C8", func_8018D8C8);

void func_8018DC28(u16* tilemap);
void func_8018DC28(u16* tilemap) {
        s16 tileType;
        u16 *rowAPtr;
        u16 *rowBPtr;
    s32 yPositions[15];
    s32 i, j, count;
    s32 lo, mid, hi, neg;
    s32 rowA, rowB;

    // Phase 1: Zero out array
    for (i = 0; i < 15; i++) {
        yPositions[i] = 0;
    }

    // Phase 2: Random placement of 20 y-coordinates
    count = 0;
    while (count < 20) {
        i = rand() % 13 + 1; // pick slot 1-13
        if (yPositions[i] >= yPositions[i - 1] + 2) continue;
        if (yPositions[i] >= yPositions[i + 1] + 2) continue;
        yPositions[i] += 2;
        count++;
    }

    // Phase 3: Assign tile types to rows 5,4,3,2 (columns 1-14)
    lo = 0; // t1 = t0*2
    mid = 2; // t5
    hi = 4;  // t6
    neg = -2; // t7

    for (i = 0; i < 4; i++) {
        u16* basePtr = (u16*)((u8*)tilemap + ((5 - i) * 32));
        j = 0;
        do {
            tileType = 3;

            if (yPositions[j] == lo) {
                if (yPositions[j + 1] == lo + 2) {
                    tileType = 0xB;
                }
            }

            if (yPositions[j] == mid) {
                if (yPositions[j + 1] == lo) {
                    tileType = 8;
                }
            }

            if (yPositions[j] < mid && yPositions[j + 1] < mid) {
                tileType = 0;
            }

            if (yPositions[j] >= hi || yPositions[j + 1] >= hi) {
                tileType = 0;
            }

            if (neg >= yPositions[j] && yPositions[j + 1] == mid) {
                tileType = 0xB;
            }

            if (yPositions[j] == mid) {
                if (neg >= yPositions[j + 1]) {
                    tileType = 8;
                }
            }

            basePtr[j + 1] = tileType;
            j++;
        } while (j < 14);

        lo += 2;
        hi += 2;
        mid += 2;
        neg += 2;
    }

    // Phase 4: Adjust tile types based on neighbors
    for (i = 0; i < 4; i++) {
        rowA = (5 - i) * 16;
        rowB = (4 - i) * 16;
        rowAPtr = tilemap + rowA;
        rowBPtr = tilemap + rowB;

        for (j = 0; j < 14; j++) {
            u16 left = rowAPtr[j];
            u16 center = rowAPtr[j + 1];
            u16 right = rowAPtr[j + 2];
            u16 below = rowBPtr[j + 1];
            u16 newLeft = left;
            u16 newCenter = center;
            u16 newRight = right;
            u16 newBelow = below;

            if (center == 8) {
                if (right == 3) {
                    newRight = 2;
                }
                if (below == 3) {
                    newBelow = 9;
                }
            } else if (center == 0xB) {
                if (left == 3) {
                    newLeft = 2;
                }
                if (below == 3) {
                    newBelow = 0xA;
                }
            }

            rowAPtr[j] = newLeft;
            rowAPtr[j + 1] = newCenter;
            rowAPtr[j + 2] = newRight;
            rowBPtr[j + 1] = newBelow;
        }
    }
}

void func_8018DF0C(u16* tilemap, s32 arg1) {
    const int RoomWidth = 32;
    s32 y, x;
    s16 tile;

    for (y = 0; y < 16; y++) {
        for (x = 0; x < 32; x++) {
            if (y < 2 || y > 13) {
                tile = 3;
            } else {
                tile = 0;
            }
            if (x < 2 || x > 29) {
                tile = 3;
            }
            *(tilemap + x + y * RoomWidth) = tile;
        }
    }
    if (arg1 & 4) {
        for (y = 6; y < 10; y++) {
            for (x = 0; x < 2; x++) {
                *(tilemap + x + y * RoomWidth) = 0;
            }
        }
    }
    if (arg1 & 8) {
        for (y = 6; y < 10; y++) {
            for (x = 30; x < 32; x++) {
                *(tilemap + x + y * RoomWidth) = 0;
            }
        }
    }
    if (arg1 & 1) {
        for (y = 0; y < 2; y++) {
            for (x = 6; x < 10; x++) {
                u8 variant = !(arg1 & 8) * RoomWidth;
                *((u16*)((u8*)&tilemap[x] + variant) + y * RoomWidth) = 0;
            }
        }
    }
    if (arg1 & 2) {
        for (y = 14; y < 16; y++) {
            for (x = 6; x < 10; x++) {
                u8 variant = !(arg1 & 8) * RoomWidth;
                *((u16*)((u8*)&tilemap[x] + variant) + y * RoomWidth) = 0;
            }
        }
    }
}

void func_8018E090(u16* tilemap) {
    const int RoomWidth = 32;
    s32 x, y;
    s32 varY;
    s32 varX;

randomize_pos:
    varX = (rand() & 0xF) + 8;
    varY = (rand() & 7) + 4;
    for (y = -2; y < 3; y++) {
        for (x = -1; x < 2; x++) {
            if (*(&tilemap[varX + x] + (varY + y) * RoomWidth)) {
                goto randomize_pos;
            }
        }
    }
    *(tilemap + varX + varY * RoomWidth) = 3;
}

void func_8018E13C(u16* tilemap) {
    const int RoomWidth = 16;
    s32 x, y;

    for (y = 10; y < 16; y++) {
        for (x = 0; x < RoomWidth; x++) {
            if (rand() & 1) {
                *(tilemap + x + y * RoomWidth) = 3;
            }
        }
    }
}

void func_8018E1D4(void);
INCLUDE_ASM("asm/us/st/mad/nonmatchings/D8C8", func_8018E1D4);
