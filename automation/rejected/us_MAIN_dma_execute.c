/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:MAIN:dma_execute
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/main/psxsdk/libcd/c_011.c
   verdict: BUILD FAILED:
10:src/main/psxsdk/libcd/c_011.c:235: conflicting types for `libcd_CDRegister0'
11:src/main/psxsdk/libcd/registers.h:4: previous declaration of `libcd_CDRegister0'
12-[10/296] psx cc src/st/rcat/gen/us/sprites.c
13-[11/296] psx cc src/st/rno3/gen/us/rooms.c
--
211:FAILED: build/us/main.elf
212-mipsel-linux-gnu-ld -nostdlib --no-check-sections  -Map build/us/main.map -T build/us/main.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_syms_auto.us.main.txt -o build/us/main.elf
213-mipsel-linux-gnu-ld: build/us/src/main/psxsdk/libcd/c_011.c.o: in function `LM201':
214:src/main/psxsdk/libcd/c_011.c:(.text+0xa1c): undefined reference to `D_800109E8'
215:mipsel-linux-gnu-ld: src/main/psxsdk/libcd/c_011.c:(.text+0xa20): undefined reference to `D_800109E8'
216-[209/296] psx cc src/weapon/w_037.c
217-[210/296] psx cc src/weapon/w_038.c

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
extern s32 D_80032E84[];
extern u8 D_800109E8[];
int printf(char*, ...);
extern s32 D_80032E80[];
extern s32 libcd_CDRegister0;

void dma_execute(s32 channel, s32 addr, s32 size, s32 mode, s32 dir, u8 enable) {
    s32 i;
    s32 status;
    s32 mask;
    s32 dmaReg;
    s32* dmaBase;
    u8* reg0;

    i = 0;
    status = D_80032E84[channel * 4 + 0x1F801088 / 4] & 0x01000000;
    if (status != 0) {
        while (i != 0x10000) {
            i++;
            status = D_80032E84[channel * 4 + 0x1F801088 / 4] & 0x01000000;
            if (status == 0) {
                break;
            }
        }
        if (i == 0x10000) {
            printf(D_800109E8, D_80032E84[channel * 4 + 0x1F801088 / 4]);
        }
    }

    mask = 1 << channel;
    if (enable == 1) {
        ((u8*)D_80032E84)[2] = ((u8*)D_80032E84)[2] | mask;
    } else {
        ((u8*)D_80032E84)[2] = ((u8*)D_80032E84)[2] & ~mask;
    }

    dmaBase = (s32*)(channel * 0x10 + 0x1F801080);
    dmaReg = 1 << (channel * 4 + 3);
    *D_80032E80 = *D_80032E80 | dmaReg;

    dmaBase[0] = addr;
    dmaBase[1] = (size << 16) | mode;

    reg0 = (u8*)&libcd_CDRegister0;
    while ((*reg0 & 0x40) == 0) {
        // wait for DMA ready
    }

    dmaBase[2] = dir;
}