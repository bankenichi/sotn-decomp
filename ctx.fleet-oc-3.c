#define SET_UNK_80 0x80
#define SET_UNK_82 0x82
#define EvSpNEW 0x2000
#define EvSpINT 0x0002
#define POLYGT4_CODE 0x3C
#define GEN_VERSION(file) CPP_STR(PATH_JOIN(gen, PATH_JOIN(VERSION_TOKEN, file)))
#define ENTITY_H 
#define CdlModeSpeedDouble 1
#define CdlDataEnd 0x04
#define HwCARD_0 (DescHW | 0x12)
#define HwCARD_1 (DescHW | 0x13)
#define FWLOCK 0x0020
#define SPU_VOICE_ADSR_DR (0x01 << 12)
#define SAVE_FLAG_REPLAY (2)
#define gte_stsxy(r0) 
#define KERNEL_H 
#define RCntMdFR 0x0000
#define ICON_SLOT_NUM 32
#define LAYER_SEMI_TRANS 0x80
#define SS_IMEDIATE 0
#define PAL_TERMINATE() ((u_long*)-1)
#define VERSION_US 
#define setlen(p,_len) (((P_TAG*)(p))->len = (u_char)(_len))
#define MaxAfterImages 6
#define RIC_PRG_PTR 0x8013C000
#define EvSpACK 0x0010
#define CdlSync 0x00
#define SS_TICK120 3
#define CdlReset 0x0A
#define CD_SOUND_COMMAND_7 7
#define CD_SOUND_COMMAND_8 8
#define getaddr(p) (u_long)(((P_TAG*)(p))->addr)
#define CdlGetTN 0x13
#define UNGREEN_MASK (BLUE_MASK | RED_MASK | ALPHA_MASK)
#define FIX(x) ((s32)((x) * 65536.0))
#define HEART_VESSEL_INCREASE 5
#define POLYG4_CODE 0x38
#define BO6_H 
#define INT16_MAX (0x7FFF)
#define OTSIZE 0x200
#define EvStACTIVE 0x2000
#define LIBAPI_H 
#define PRIMITIVE_H 
#define UNUSED 
#define EvSpERROR 0x8000
#define WEAPON_0_END (WEAPON_1_START - 1)
#define POSE_END {-1, 0}
#define SYNC_FIELD(struct1,struct2,field) 
#define SPU_VOICE_ADSR_RR (0x01 << 14)
#define STAGE_PRG_PTR 0x80180000
#define SPU_VOICE_ADSR_AMODE (0x01 << 8)
#define MAX_LINE_G2_COUNT 0x100
#define RCntMdSC 0x0001
#define RCntMdSP 0x0000
#define PAD_FIELD(size) const CRITICAL_PAD_FIELD(size)
#define COLOR_LEN ((COLOR_BPP) / 8)
#define SPU_COMMON_MVOLMODEL (0x01 << 2)
#define SS_TICKMODE_MAX 6
#define COMMON_H 
#define CD_SOUND_COMMAND_16 16
#define SPU_VOICE_SAMPLE_NOTE (0x01 << 6)
#define PAL_BULK_(dst,src,len) (u_long*)(dst), (u_long*)(len), (u_long*)(src)
#define SPRT_CODE 0x64
#define CdlReadN 0x06
#define CdlReadS 0x1B
#define MaxEntityCount 32
#define FONT_SPACE 4
#define CdlNop 0x01
#define ALIGNED4 
#define HwCPU (DescHW | 0x10)
#define getcode(p) (u_char)(((P_TAG*)(p))->code)
#define FIX_FRAC(x) (*(s16*)&(x))
#define gte_ldv0(r0) 
#define gte_ldv3(r0,r1,r2) 
#define WIDTH_OF_MAP_ROW_IN_PIXELS (256)
#define DISP_ALL_H 240
#define EvSpPERROR 0x8001
#define SET_RELEASE_RATE_LOW_20_21 0xA3
#define EvMdNOINTR 0x2000
#define MEMCPY memcpy
#define OT_TYPE u_long
#define DEMO_MAX_LEN 0x2000
#define LIBGS_H 
#define getTPage(tp,abr,x,y) ((GetGraphType() == 1 || GetGraphType() == 2) ? ((((tp) & 0x3) << 9) | (((abr) & 0x3) << 7) | (((y) & 0x300) >> 3) | (((x) & 0x3ff) >> 6)) : ((((tp) & 0x3) << 7) | (((abr) & 0x3) << 5) | (((y) & 0x100) >> 4) | (((x) & 0x3ff) >> 6) | (((y) & 0x200) << 2)))
#define __asm__(...) 
#define SET_UNK_81 0x81
#define SQUARE 0xEA
#define USE_MICRO_OPTIMIZATIONS 0
#define PAL_UNK_OP3 3
#define CdlSeekL 0x15
#define CdlSeekP 0x16
#define SPU_REV_MODE_CLEAR_WA 0x100
#define DISP_TITLE_H DISP_ALL_H
#define LAYER_TPAGE_ALT 0x100
#define setLineG4(p) setlen(p, 9), setcode(p, 0x5c), (p)->pad = 0x55555555
#define SET_SOUNDMODE_MONO 5
#define setSprt8(p) setlen(p, 3), setcode(p, 0x74)
#define TILE_SIZE 16
#define STRINGIFY_(x) #x
#define PORT_COUNT (2)
#define STAGE_INVERTEDCASTLE_FLAG 0x20
#define WIDTH_OF_MAP_TILE_IN_PIXELS (4)
#define SS_SOFF 0
#define FLT(x) ((s32)((x) * 4096.0))
#define EvSpUNKNOWN 0x0200
#define GAMEBUTTONS (~(PAD_START | PAD_SELECT))
#define SS_REV 1
#define PATH_JOIN(a,b) a/b
#define E_ID(name) E_ ##name
#define RELIC_FLAG_DISABLE 0
#define setXY0(p,_x0,_y0) (p)->x0 = (_x0), (p)->y0 = (_y0)
#define setXY2(p,_x0,_y0,_x1,_y1) (p)->x0 = (_x0), (p)->y0 = (_y0), (p)->x1 = (_x1), (p)->y1 = (_y1)
#define setXY4(p,_x0,_y0,_x1,_y1,_x2,_y2,_x3,_y3) (p)->x0 = (_x0), (p)->y0 = (_y0), (p)->x1 = (_x1), (p)->y1 = (_y1), (p)->x2 = (_x2), (p)->y2 = (_y2), (p)->x3 = (_x3), (p)->y3 = (_y3)
#define ASM_RODATA __asm__(".section .rodata")
#define EvSpCZ 0x0001
#define SPU_REV_MODE_SPACE 6
#define BITS_PER_BYTE (8)
#define SS_TICKVSYNC 5
#define SPU_VOICE_ADSR_ADSR2 (0x01 << 18)
#define setPolyFT3(p) setlen(p, 7), setcode(p, 0x24)
#define setPolyFT4(p) setlen(p, 9), setcode(p, 0x2c)
#define PAL_GLOW_DATA(data) (u_long*)(data)
#define LIBGTE_H 
#define MAX_SPRT_COUNT 0x200
#define STAGE_WIDTH 256
#define FLT_TO_FIX(x) ((s32)(x) << 4)
#define CdlModeSize0 0x10
#define NUM_AVAIL_RELICS (NUM_RELICS - 2)
#define SS_SEQ_TABSIZ 176
#define DescEV 0xf1000000
#define EvStUNUSED 0x0000
#define setSprt16(p) setlen(p, 3), setcode(p, SPRT16_CODE)
#define STATIC_PAD_DATA(size) STATIC_PAD_BSS(size) = {0}
#define CdlModeAP 0x02
#define DescHW 0xf0000000
#define HIHU(x) (((u16*)&(x))[1])
#define SAVE_FLAG_CLEAR (1)
#define CdlDataReady 0x01
#define ANIMSET_OVL_FLAG 0x8000
#define GET_BLUE(x) (((x) >> 10) & 0x1F)
#define _ROMIO_H 
#define SPU_COMMON_RVOLL (0x01 << 4)
#define SPU_COMMON_RVOLR (0x01 << 5)
#define WIDTH_OF_MAP_ROW_IN_BYTES (WIDTH_OF_MAP_ROW_IN_PIXELS / PIXELS_PER_BYTE)
#define SPRT16_CODE 0x7C
#define FTRUNC 0x0400
#define LEN(x) ((s32)(sizeof(x) / sizeof(*(x))))
#define SPU_VOICE_ADSR_AR (0x01 << 11)
#define CD_SOUND_COMMAND_10 10
#define LIFE_VESSEL_INCREASE 5
#define CdlStatSeekError 0x04
#define CdlGetlocP 0x11
#define SET_XA_PLAYBACK 0x11
#define PLAYER g_Entities[PLAYER_CHARACTER]
#define PAL_UNK_OP3_INFO(dst,n) (u_long*)(dst), (u_long*)(n)
#define RELIC_FLAG_FOUND 1
#define EvSpCLOSE 0x0008
#define CdlSetfilter 0x0D
#define CdlGetlocL 0x10
#define TcbStUNUSED 0x1000
#define DISP_MENU_W 384
#define GFX_ENTRY(x,y,w,h,data) (u_long*)((x) | ((y) << 16)), (u_long*)((h) | ((w) << 16)), (u_long*)data
#define DescRC 0xf2000000
#define FNBLOCK 0x0004
#define setaddr(p,_addr) (((P_TAG*)(p))->addr = (u_long)(_addr))
#define COLOR_BIT_DEPTH (4)
#define POSE_JUMP(anim) {-2, anim}
#define DescTH DescMask
#define SPU_REV_MODE_HALL 5
#define setWH(p,_w,_h) (p)->w = _w, (p)->h = _h
#define SPU_OFF 0
#define LIBSPU_H 
#define SCRIPT(...) {}
#define PACKED 
#define gte_SetTransMatrix(r0) 
#define CdlModeRT 0x40
#define CdlMAXDIR 128
#define LOHU(x) (*(u16*)&(x))
#define USE_CD_SPEED_DOUBLE 0
#define SET_RELEASE_RATE_HIGH_20_21 0xA1
#define PAL_COPY 1
#define SEEK_CUR 1
#define OVL_EXPORT(x) BO6_ ##x
#define addPrim(ot,p) setaddr(p, getaddr(ot)), setaddr(ot, p)
#define __SPU_IRQCALLBACK_PROC 
#define GET_RED(x) (((x) >> 0) & 0x1F)
#define ANIMSET_DRA(x) (x)
#define SS_TICK240 2
#define SET_SOUNDMODE_STEREO 6
#define GAME_IMPORT 
#define PBLU(p) p->b0 = p->b1 = p->b2 = p->b3
#define setPolyF3(p) setlen(p, 4), setcode(p, 0x20)
#define setPolyF4(p) setlen(p, 5), setcode(p, 0x28)
#define FRCOM 0x2000
#define MAX_PRIM_COUNT 0x500
#define SET_PAUSE_SFX_SCRIPTS 0xE
#define setPolyG3(p) setlen(p, 6), setcode(p, 0x30)
#define setPolyG4(p) setlen(p, 8), setcode(p, POLYG4_CODE)
#define CdlModeDA 0x01
#define RIC g_Entities[STAGE_ENTITY_START]
#define DescMask 0xff000000
#define DISP_STAGE_H DISP_ALL_H
#define DISP_STAGE_W 256
#define POSE_LOOP(index) {0, index}
#define SPU_REV_MODE_PIPE 9
#define GREEN_MASK 0x3E0
#define STRINGIFY(x) STRINGIFY_(x)
#define isendprim(p) ((((P_TAG*)(p))->addr) == 0xffffff)
#define CLAMP(x,min,max) x < min ? min : (x > max ? max : x)
#define TOTAL_ENTITY_COUNT 256
#define SPU_COMMON_CDMIX (0x01 << 9)
#define SPU_COMMON_EXTVOLR (0x01 << 11)
#define setUV3(p,_u0,_v0,_u1,_v1,_u2,_v2) (p)->u0 = (_u0), (p)->v0 = (_v0), (p)->u1 = (_u1), (p)->v1 = (_v1), (p)->u2 = (_u2), (p)->v2 = (_v2)
#define setUV4(p,_u0,_v0,_u1,_v1,_u2,_v2,_u3,_v3) (p)->u0 = (_u0), (p)->v0 = (_v0), (p)->u1 = (_u1), (p)->v1 = (_v1), (p)->u2 = (_u2), (p)->v2 = (_v2), (p)->u3 = (_u3), (p)->v3 = (_v3)
#define CdlNoIntr 0x00
#define CdlSetloc 0x02
#define LOWU(x) (*(u32*)&(x))
#define PLAYER_MARIA 2
#define CdlPause 0x09
#define UNKNOWN_CRITICAL_PAD_TYPE(type,size) CRITICAL_PAD_TYPE_FIELD(type, size)
#define SPRITESHEET_PTR 0x8013C020
#define ANIM_FRAME_LOAD 0x8000
#define SS_TICK50 4
#define SET_UNK_A6 0xA6
#define SS_TICK60 1
#define BTN_MIST PAD_L1
#define HwRTC0 (DescHW | 0x05)
#define HwRTC1 (DescHW | 0x06)
#define HwRTC2 (DescHW | 0x07)
#define ANIMSET_OVL(x) ((x) | ANIMSET_OVL_FLAG)
#define FRLOCK 0x0010
#define PLAYER_RICHTER 1
#define MAX_POLY_GT3_COUNT 0x30
#define ZERO_LEN 0
#define SS_REV_TYPE_DELAY 8
#define F3DEX_GBI_2 1
#define COLOR_BPP (16)
#define CdlModeSF 0x08
#define COLOR16(r,g,b,a) (r) + ((g) << 5) + ((b) << 10) + ((a) << 15)
#define POSE_UNKNOWN(anim) {-3, anim}
#define STAGE_ENTITY_START 64
#define SS_REV_TYPE_STUDIO_A 2
#define SS_REV_TYPE_STUDIO_C 4
#define LAYOUT_RECT_PARAMS_UNKNOWN_20 0x20
#define SS_WAIT_COMPLETED 1
#define PAL_COPY_DATA_(dst,data,len) (u_long*)(dst), (u_long*)(len), (u_long*)(data)
#define LAYOUT_RECT_PARAMS_UNKNOWN_40 0x40
#define CdlPlay 0x03
#define SET_KEY_ON_20_21 0xA4
#define M2CTX 1
#define TEST_BITS(x,y) (((x) & (y)) == (y))
#define CRITICAL_PAD_FIELD(size) CRITICAL_PAD_TYPE_FIELD(uint8_t, size)
#define SPU_REV_MODE_STUDIO_A 2
#define SPU_REV_MODE_STUDIO_B 3
#define SPU_REV_MODE_STUDIO_C 4
#define termPrim(p) setaddr(p, 0xffffffff)
#define SET_STOP_MUSIC 0xA
#define FIX_TO_I(x) ((s32)((x) >> 16))
#define S32_MAX INT32_MAX
#define SPU_REV_MODE (0x01 << 0)
#define CIRCLE 0xE8
#define MAX_PRIM_ALLOC_COUNT 0x400
#define O_NOBUF FNBUF
#define WEAPON_0_START 0xE0
#define DIAG_EOL 0xFF
#define MAX_POLY_G4_COUNT 0x100
#define STAGE_INVERTEDCASTLE_MASK 0x1F
#define SAVE_DATA_PTR 0x801EA000
#define SET_UNK_92 0x92
#define SPU_VOICE_ADSR_SL (0x01 << 15)
#define DISP_TITLE_W 512
#define EvSpERANGE 0x0302
#define SPU_VOICE_ADSR_SR (0x01 << 13)
#define setXY3(p,_x0,_y0,_x1,_y1,_x2,_y2) (p)->x0 = (_x0), (p)->y0 = (_y0), (p)->x1 = (_x1), (p)->y1 = (_y1), (p)->x2 = (_x2), (p)->y2 = (_y2)
#define HwDMAC (DescHW | 0x04)
#define GAME_H 
#define PIXELS_PER_BYTE (BITS_PER_BYTE / COLOR_BIT_DEPTH)
#define SS_REV_TYPE_ECHO 7
#define CdlMAXLEVEL 8
#define CLAMP_MAX(v,max) ((v) > (max) ? (max) : (v))
#define DISP_MENU_H DISP_ALL_H
#define HEIGHT_OF_MAP_TILE_IN_PIXELS (4)
#define SPU_VOICE_ADSR_SMODE (0x01 << 9)
#define LAYER_SHOW 1
#define PCOL(p) PRED(p) = PGRN(p) = PBLU(p)
#define SET_SOUND_WAIT 0xD
#define SET_VOLUME_22_23 1
#define gte_SetRotMatrix(r0) 
#define SIM_PTR 0x80280000
#define PAL_UNK_OP3_DATA(data) (u_long*)(data)
#define STATIC_ASSERT(x,...) 
#define setPolyGT3(p) setlen(p, 9), setcode(p, POLYGT3_CODE)
#define setPolyGT4(p) setlen(p, 12), setcode(p, POLYGT4_CODE)
#define INCLUDE_ASM_H 
#define EvSpEDOM 0x0301
#define CD_SOUND_COMMAND_6 6
#define PLAYER_ALUCARD 0
#define RCntCNT1 (DescRC | 0x01)
#define RCntCNT2 (DescRC | 0x02)
#define RCntCNT3 (DescRC | 0x03)
#define SET_E_ID(name) E_ID(name) = E_ ##name
#define SIZEOF_MENUCONTEXT (0x1E)
#define HwGPU (DescHW | 0x02)
#define SPU_VOICE_VOLL (0x01 << 0)
#define SS_SON 1
#define SPU_VOICE_VOLR (0x01 << 1)
#define SPU_COMMON_CDVOLL (0x01 << 6)
#define SPU_COMMON_CDVOLR (0x01 << 7)
#define MAX_GOLD 999999
#define FLT_TO_I(x) ((s32)(x) >> 12)
#define OFF(type,field) ((size_t)(&((type*)0)->field))
#define NUM_HORIZONTAL_SENSORS 4
#define CdlBackward 0x05
#define SS_REV_TYPE_HALL 5
#define STAGE 0xCC
#define COLORS_PER_PAL (16)
#define O_RDWR FREAD | FWRITE
#define setTile(p) setlen(p, 3), setcode(p, TILE_CODE)
#define SPU_COMMON_EXTMIX (0x01 << 13)
#define CdlAcknowledge 0x03
#define CdlStatIdError 0x08
#define SwMATH (DescSW | 0x02)
#define BLOCK_PER_CARD (15)
#define gte_SetGeomScreen(r0) 
#define VERSION_TOKEN us
#define gte_stszotz(r0) 
#define setShadeTex(p,tge) ((tge) ? setcode(p, getcode(p) | 0x01) : setcode(p, getcode(p) & ~0x01))
#define CD_SOUND_COMMAND_12 12
#define PAL_COPY_DATA(dst,data) (u_long*)(dst), (u_long*)LEN(data), (u_long*)(data)
#define DISP_STAGE_NEXT_X DISP_STAGE_W
#define INT32_MAX (0x7FFFFFFF)
#define CLUT_INDEX_SERVANT_OVERWRITE 0x430
#define RCntMdINTR 0x1000
#define MaxAfterImageIndex 10
#define SPU_COMMON_MVOLMODER (0x01 << 3)
#define NUM_VERTICAL_SENSORS 7
#define getlen(p) (u_char)(((P_TAG*)(p))->len)
#define GET_PAL_OP_FREQ(x) (HIH(x))
#define BTN_WOLF PAD_R2
#define PAL_FLAG(x) ((x) | PAL_UNK_FLAG)
#define SS_REV_TYPE_SPACE 6
#define LINEG2_CODE 0x50
#define EvSpDE 0x0080
#define LIBGPU_H 
#define O_RDONLY FREAD
#define PAL_BULK_COPY 5
#define SS_REV_TYPE_PIPE 9
#define PAD_SHOULDERS (PAD_L1 | PAD_R1 | PAD_L2 | PAD_R2)
#define PGRN(p) p->g0 = p->g1 = p->g2 = p->g3
#define ROT(x) ((s32)(FLT(x) / 360))
#define nextPrim(p) (void*)((u_long)(((P_TAG*)(p))->addr) | 0x80000000)
#define FWRITE 0x0002
#define SS_REV_TYPE_OFF 0
#define SPU_REV_MODE_ROOM 1
#define setUV0(p,_u0,_v0) (p)->u0 = (_u0), (p)->v0 = (_v0)
#define HIH(x) (((s16*)&(x))[1])
#define SPU_COMMON_EXTREV (0x01 << 12)
#define SS_NOTICK0 0
#define CdlStatStandby 0x02
#define LIBCD_H 
#define GET_GREEN(x) (((x) >> 5) & 0x1F)
#define SPU_COMMON_MVOLL (0x01 << 0)
#define SPU_COMMON_MVOLR (0x01 << 1)
#define MAX_TILE_COUNT 0x100
#define setSprt(p) setlen(p, 4), setcode(p, SPRT_CODE)
#define setLineF2(p) setlen(p, 3), setcode(p, 0x40)
#define setLineF3(p) setlen(p, 5), setcode(p, 0x48), (p)->pad = 0x55555555
#define setLineF4(p) setlen(p, 6), setcode(p, 0x4c), (p)->pad = 0x55555555
#define EvSpTRAP 0x1000
#define WIDTH_OF_MAP_TILE_IN_BYTES (WIDTH_OF_MAP_TILE_IN_PIXELS / PIXELS_PER_BYTE)
#define setLineG2(p) setlen(p, 4), setcode(p, LINEG2_CODE)
#define setLineG3(p) setlen(p, 7), setcode(p, 0x58), (p)->pad = 0x55555555
#define SEEK_SET 0
#define SS_SERIAL_A 0
#define SS_SERIAL_B 1
#define gte_rtps() 
#define gte_rtpt() 
#define N_VERTI_TILES 16
#define FSCAN 0x1000
#define gte_stsxy2(r0) 
#define gte_stsxy3(r0,r1,r2) 
#define CdlDiskError 0x05
#define SET_UNPAUSE_SFX_SCRIPTS 0xF
#define SET_UNK_10 0x10
#define setTile16(p) setlen(p, 2), setcode(p, 0x78)
#define EvSpTIMOUT 0x0100
#define OBJECTS_H 
#define PLAYER_CHARACTER 0
#define O_CREAT FCREAT
#define SPELL_FLAG_KNOWN 0x80
#define PAL_BULK(dst,src) (u_long*)(dst), (u_long*)LEN(src), (u_long*)(src)
#define UNBLUE_MASK (GREEN_MASK | RED_MASK | ALPHA_MASK)
#define FNBUF 0x4000
#define __INDIRECT_CRITICAL_PAD_TYPE_FIELD(type,size,line,counter) type __pad__ ##size ##__ ##line ##__ ##counter[size]
#define NULL (0)
#define LAYER_TPAGE_ID (0x20 | 0x40)
#define RIC_SHARED_H 
#define CD_SOUND_COMMAND_FADE_OUT_1 3
#define CD_SOUND_COMMAND_FADE_OUT_2 2
#define CdlSetmode 0x0E
#define setUVWH(p,_u0,_v0,_w,_h) (p)->u0 = (_u0), (p)->v0 = (_v0), (p)->u1 = (_u0) + (_w), (p)->v1 = (_v0), (p)->u2 = (_u0), (p)->v2 = (_v0) + (_h), (p)->u3 = (_u0) + (_w), (p)->v3 = (_v0) + (_h)
#define CdlStatRead 0x20
#define MAKE_PAL_OP(kind,freq) (u_long*)((kind) | ((freq) << 0x10))
#define CASTLE_MAP_PTR 0x801E0000
#define SPU_VOICE_LSAX (0x01 << 16)
#define SET_KEY_ON_22_23 0xA8
#define __attribute__(...) 
#define EvSpIOE 0x0004
#define CdlStop 0x08
#define SPU_VOICE_NOTE (0x01 << 5)
#define INCLUDE_RODATA(FOLDER,NAME) __asm__(".pushsection .rodata\n" ".include \"asm/" VERSION "/" FOLDER "/" #NAME ".s\"\n" ".popsection")
#define TcbStACTIVE 0x4000
#define CdlStandby 0x07
#define SPU_VOICE_ADSR_RMODE (0x01 << 10)
#define CdlMAXFILE 64
#define PAL_GLOW_INFO(dst,n) (u_long*)(dst), (u_long*)(n)
#define ITEMS_H 
#define MAX_BG_LAYER_COUNT 16
#define gte_nclip() 
#define SPU_VOICE_VOLMODEL (0x01 << 2)
#define SPU_VOICE_VOLMODER (0x01 << 3)
#define PGREY_ALT(p,n,v) p->r ##n = v; p->g ##n = v; p->b ##n = v;
#define PRED(p) p->r0 = p->r1 = p->r2 = p->r3
#define WEAPON1_PTR 0x8017D000
#define CdlStatSeek 0x40
#define CdlModeStream2 0x120
#define ASSERT(x) 
#define setClut(p,x,y) ((p)->clut = getClut(x, y))
#define SS_REV_TYPE_ROOM 1
#define SPU_VOICE_ADSR_ADSR1 (0x01 << 17)
#define LOH(x) (*(s16*)&(x))
#define HwCdRom (DescHW | 0x03)
#define DRA_PRG_PTR 0x800A0000
#define RELIC_FLAG_ACTIVE 2
#define SPU_REV_MODE_OFF 0
#define MAX_ENV_COUNT 0x10
#define O_NBLOCK FNBLOCK
#define TILE_CODE 0x60
#define SPU_REV_MODE_ECHO 7
#define MAX_DRAW_MODES 0x400
#define PGREY(p,n) p->r ##n = p->g ##n = p->b ##n
#define SET_STOP_SEQ 7
#define MEMCARD_ID "BASLUS-00067DRAX00"
#define SPU_VOICE_NUM 24
#define N_HORIZ_TILES 17
#define RCntMdNOINTR 0x2000
#define HwVBLANK (DescHW | 0x01)
#define CdlModeStream 0x100
#define HwSIO (DescHW | 0x0b)
#define gte_stopz(r0) 
#define CdlModeRept 0x04
#define HwPIO (DescHW | 0x0a)
#define SPU_REV_FEEDBACK (0x01 << 4)
#define PAL_UNK_OP2_INFO(dst,n) (u_long*)(dst), (u_long*)(n)
#define EvStWAIT 0x1000
#define EvSpCOMP 0x0020
#define POSE(duration,frameNo,hitboxNo) {(duration), (((frameNo) & 0x1FF) | (((hitboxNo) & 0x7F) << 9))}
#define PRIM_DR_ENV(prim) ((DR_ENV*)LOW((prim)->r1))
#define O_NOWAIT FASYNC
#define UNRED_MASK (BLUE_MASK | GREEN_MASK | ALPHA_MASK)
#define SPU_REV_MODE_DELAY 8
#define PSP_RANDMASK 0xFFFFFFFF
#define WEAPON0_PTR 0x8017A000
#define SPU_COMMON_CDREV (0x01 << 8)
#define HwSPU (DescHW | 0x09)
#define SPU_COMMON_EXTVOLL (0x01 << 10)
#define TYPES_H 
#define FCREAT 0x0200
#define setSemiTrans(p,abe) ((abe) ? setcode(p, getcode(p) | 0x02) : setcode(p, getcode(p) & ~0x02))
#define SS_IMMEDIATE 0
#define DescUEV 0xf3000000
#define CdlGetparam 0x0F
#define DEMO_KEY_LEN 3
#define FONT_H 8
#define SET_UNK_0C 0xC
#define FONT_W 8
#define CdlForward 0x04
#define I_TO_FIX(x) ((s32)((x) << 16))
#define LIBETC_H 
#define CH(x) ((x) - 0x20)
#define FONT_GAP FONT_W
#define TcbMdPRI 0x2000
#define __CPP_STR(x) #x
#define I_TO_FLT(x) ((s32)(x) << 12)
#define POS(x) (*(Pos*)&(x))
#define PALETTE_LEN ((COLORS_PER_PAL) * ((COLOR_BPP) / 8))
#define FREAD 0x0001
#define EvStALREADY 0x4000
#define setRGB0(p,_r0,_g0,_b0) (p)->r0 = _r0, (p)->g0 = _g0, (p)->b0 = _b0
#define setRGB1(p,_r1,_g1,_b1) (p)->r1 = _r1, (p)->g1 = _g1, (p)->b1 = _b1
#define HwCNTL (DescHW | 0x08)
#define SEEK_END 2
#define RCntCNT0 (DescRC | 0x00)
#define CdlMute 0x0B
#define catPrim(p0,p1) setaddr(p0, p1)
#define setRGB2(p,_r2,_g2,_b2) (p)->r2 = _r2, (p)->g2 = _g2, (p)->b2 = _b2
#define SS_MIX 0
#define CdlModeSize1 0x20
#define STATIC_PAD_RODATA(size) const STATIC_PAD_BSS(size) = {0}
#define CdlStatError 0x01
#define ALPHA_MASK 0x8000
#define setRGB3(p,_r3,_g3,_b3) (p)->r3 = _r3, (p)->g3 = _g3, (p)->b3 = _b3
#define TILE_MASK 0x0F
#define O_WRONLY FWRITE
#define PAL_GLOW_ANIM 4
#define SET_RELEASE_RATE_LOW_22_23 0xA7
#define PAL_COPY_INFO() MAKE_PAL_OP(PAL_COPY, 0)
#define STATIC_PAD_BSS(size) static CRITICAL_PAD_FIELD(size)
#define SPU_REV_MODE_MAX 10
#define CARD_BLOCK_SIZE (8192)
#define HEART_VESSEL_RICHTER 30
#define FACTORY(id,param) ((id) + (param << 16))
#define CROSS 0xE9
#define CdlStatShellOpen 0x10
#define SPU_REV_DELAYTIME (0x01 << 3)
#define addPrims(ot,p0,p1) setaddr(p1, getaddr(ot)), setaddr(ot, p0)
#define WOLF_CHARGE_ATK_BTN (PAD_SQUARE)
#define CdlStatPlay 0x80
#define SPU_ON 1
#define SS_NOTICK 0x1000
#define SET_UNK_90 0x90
#define SPU_VOICE_WDSA (0x01 << 7)
#define PAL_UNK_OP2_DATA(data) (u_long*)(data)
#define EvSpSYSCALL 0x4000
#define FAMILIAR_PTR 0x80170000
#define LAYER_CLUT_ALT 0x200
#define SQ(x) ((x) * (x))
#define STAGE_H 
#define LIBC_H 
#define MAX_POLY_GT4_COUNT 0x300
#define HwCARD (DescHW | 0x11)
#define UV(x) (*(uvPair*)&(x))
#define CdlModeSpeedNormal 0
#define RCntMdGATE 0x0010
#define SAVE_FLAG_NORMAL (0)
#define setTile1(p) setlen(p, 2), setcode(p, 0x68)
#define setTile8(p) setlen(p, 2), setcode(p, 0x70)
#define __CRITICAL_PAD_TYPE_FIELD(type,size,line,counter) __INDIRECT_CRITICAL_PAD_TYPE_FIELD(type, size, line, counter)
#define CdlDemute 0x0C
#define setBlockFill(p) setlen(p, 3), setcode(p, 0x02)
#define EvSpIOER 0x0400
#define EvSpIOEW 0x0800
#define DIAG_EOS 0x00
#define POLYGT3_CODE 0x34
#define SFX_H 
#define CLAMP_MIN(v,min) ((v) < (min) ? (min) : (v))
#define LIBSND_H 
#define PAL_UNK_OP2 2
#define O_TAG u_long tag
#define GET_PAL_OP_KIND(x) (LOHU(x))
#define CPP_STR(x) __CPP_STR(x)
#define LAYER_WRAP_BG 0x1000
#define _LANGUAGE_C 1
#define _S(x) (x)
#define FAPPEND 0x0100
#define WEAPON_1_START 0xF0
#define CLUT_INDEX_SERVANT 0x400
#define DescSW 0xf4000000
#define SIM_CHR0 0x80280000
#define SIM_CHR1 0x80284000
#define CdlGetTD 0x14
#define S16_MAX INT16_MAX
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define getClut(x,y) ((y << 6) | ((x >> 4) & 0x3f))
#define PAL_BULK_COPY_INFO(dst,n) (u_long*)(dst), (u_long*)(n)
#define _SE(x) (x)
#define RED_MASK 0x1F
#define SwCARD (DescSW | 0x01)
#define FASYNC 0x8000
#define F(x) (*(f32*)&(x))
#define SPU_VOICE_PITCH (0x01 << 4)
#define DEMO_KEY_PTR 0x801E8000
#define setTPage(p,tp,abr,x,y) ((p)->tpage = getTPage(tp, abr, x, y))
#define UNKNOWN_CRITICAL_PAD_FIELD(size) CRITICAL_PAD_FIELD(size)
#define _MIPS_SZLONG 32
#define TRIANGLE 0xEB
#define CdlComplete 0x02
#define SET_UNK_12 0x12
#define CdlModeSpeed 0x80
#define LAYOUT_RECT_PARAMS_HIDEONMAP 0x10
#define CD_SOUND_COMMAND_START_XA 4
#define SPU_REV_DEPTHL (0x01 << 1)
#define SPU_REV_DEPTHR (0x01 << 2)
#define EvMdINTR 0x1000
#define VERSION CPP_STR(VERSION_TOKEN)
#define EvSpDR 0x0040
#define MIN(a,b) ((a) > (b) ? (b) : (a))
#define MAXSPRT16 0x280
#define INCLUDE_ASM(FOLDER,NAME) __asm__(".pushsection .text\n" "\t.align\t2\n" "\t.globl\t" #NAME ".NON_MATCHING\n" "\t.ent\t" #NAME "\n" #NAME ":\n" "\t.type\t" #NAME ".NON_MATCHING, @object\n" "\t" #NAME ".NON_MATCHING:\n" ".include \"asm/" VERSION "/" FOLDER "/" #NAME ".s\"\n" "\t.set reorder\n" "\t.set at\n" "\t.end\t" #NAME "\n" ".popsection")
#define SET_UNK_0B 0xB
#define CD_SOUND_START_XA_PLAYBACK 14
#define SET_UNK_13 0x13
#define CRITICAL_PAD_TYPE_FIELD(type,size) __CRITICAL_PAD_TYPE_FIELD(type, size, __LINE__, __COUNTER__)
#define VERSION_H 
#define setXYWH(p,_x0,_y0,_w,_h) (p)->x0 = (_x0), (p)->y0 = (_y0), (p)->x1 = (_x0) + (_w), (p)->y1 = (_y0), (p)->x2 = (_x0), (p)->y2 = (_y0) + (_h), (p)->x3 = (_x0) + (_w), (p)->y3 = (_y0) + (_h)
#define SPU_REV_MODE_CHECK (-1)
#define BLUE_MASK 0x7C00
#define PAL_UNK_FLAG 0x8000
#define TcbMdRT 0x1000
#define GFX_TERMINATE() ((u_long*)-1)
#define CVEC(x) (*(CVECTOR*)&(x))
#define PAD_SHAPES (PAD_SQUARE | PAD_CROSS | PAD_CIRCLE | PAD_TRIANGLE)
#define LOBU(x) (*(u8*)&(x))
#define SS_REV_TYPE_STUDIO_B 3
#define setcode(p,_code) (((P_TAG*)(p))->code = (u_char)(_code))
#define LOW(x) (*(s32*)&(x))
typedef char int8_t;
typedef short int16_t;
typedef int int32_t;
typedef long long int64_t;
typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;
typedef unsigned long long uint64_t;
typedef unsigned char u_char;
typedef unsigned short u_short;
typedef unsigned long u_long;
typedef unsigned int size_t;
typedef signed char s8;
typedef signed short s16;
typedef signed int s32;
typedef signed long long s64;
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef signed char byte;
typedef unsigned short ushort;
typedef unsigned int uint;
enum { false, true };
typedef signed int bool;
typedef union {
    s32 val;
    struct {
        s16 lo;
        s16 hi;
    } i;
} f32;
typedef union {
    s16 val;
    struct {
        u8 lo;
        u8 hi;
    } i;
} f16;
typedef struct {
              s16 x;
              s16 y;
} Point16;
typedef struct {
              s32 x;
              s32 y;
} Point32;
typedef struct {
    u16 width;
    u16 height;
} Size16;
typedef struct {
    u8 u;
    u8 v;
} uvPair;
typedef struct {
    f32 x;
    f32 y;
} Pos;
extern u8 g_CastleFlags[0x300];
typedef enum {
              CEN_OPEN = 0,
              NO4_OPEN = 1,
              NULL_STAGE_FLAG = 2,
              NO0_STAGE_FLAG = 2,
              RARE_STAGE_FLAG = 2,
               NO1_ELEVATOR_ACTIVATED = 16,
               NO1_UNKNOWN_FLAG = 17,
               NO1_SECRET_WALL_BROKEN = 18,
               NO1_WEATHER = 19,
               NO1_BIRD_CYCLE = 20,
               NO1_STAGE_FLAG = 21,
               RNO1_SECRET_WALL_BROKEN = 24,
               NO2_SECRET_WALL_OPEN = 32,
               NO2_SECRET_CEILING_OPEN = 33,
               NO2_STAGE_FLAG = 34,
               RNO2_SECRET_WALL_OPEN = 40,
               RNO2_SECRET_FLOOR_OPEN = 41,
               NO4_TO_NP3_SHORTCUT = 48,
               NO0_TO_NP3_SHORTCUT = 49,
               WRP_TO_NP3_SHORTCUT = 50,
               JEWEL_SWORD_ROOM_STEPS = 51,
               PROLOGUE_COMPLETE = 52,
               IVE_BEEN_ROBBED = 53,
               NO3_STAGE_FLAG = 54,
               NP3_STAGE_FLAG = 54,
               MAD_STAGE_FLAG = 54,
               CASTLE_TURNED_ON = 55,
               DEATH_STAIRWAY_BROKEN = 56,
               SLO_GAI_RETREATED = 57,
               JEWEL_SWORD_ROOM_OPEN = 58,
               JEWEL_ROOM_STEPS = 59,
               INV_DEATH_STAIRWAY_BROKEN = 60,
               JEWEL_ROOM_OPEN = 61,
               CAT_LEFT_SECRET_WALL_OPEN = 64,
               CAT_RIGHT_SECRET_WALL_OPEN = 65,
               CAT_SPIKE_ROOM_LIT = 66,
               CAT_STAGE_FLAG = 67,
               SPIKE_BREAKER_SECRET = 68,
               RCAT_RIGHT_SECRET_WALL_OPEN = 72,
               RCAT_SECRET_WALL_BROKEN = 73,
               RCAT_SPIKE_ROOM_LIT = 74,
               RCAT_LEFT_SECRET_WALL_OPEN = 75,
               CHI_DEMON_SWITCH = 80,
               CHI_SECRET_WALL_OPEN = 81,
               CHI_LARGE_STEPS_FALLEN = 82,
               CHI_TINY_STEPS_FALLEN = 83,
               CHI_STAGE_FLAG = 84,
               RCHI_DEMON_SWITCH = 88,
               RCHI_SECRET_WALL_OPEN = 89,
               NO2_TO_DAI_SHORTCUT = 96,
               DAI_STAGE_FLAG = 97,
               MET_MARIA_AFTER_HIPPOGRYPH = 98,
               MET_MARIA_IN_DAI = 99,
               LIB_BOOKSHELF_SECRET = 112,
               LIB_STAGE_FLAG = 113,
               MET_LIBRARIAN = 114,
               BOUGHT_CASTLE_MAP = 115,
               LIBRARIAN_DROPS = 116,
               NZ0_STAGE_FLAG = 128,
               NZ0_SECRET_WALL_OPEN = 129,
               NZ0_SECRET_FLOOR_OPEN = 130,
               NZ0_CANNON_WALL_SHORTCUT = 131,
               SLO_GAI_DEFEATED = 132,
               MET_MARIA_IN_NZ0 = 133,
               RNZ0_SECRET_WALL_OPEN = 136,
               RNZ0_SECRET_CEILING_OPEN = 137,
               TOP_STAGE_FLAG = 144,
               TOP_SECRET_WALL_1_BROKEN =
        145,
               TOP_SECRET_WALL_2_BROKEN =
        146,
               TOP_LION_LIGHTS = 147,
               TOP_SECRET_STAIRS = 148,
               SHAFT_ORB_DEFEATED = 149,
               INVERTED_CASTLE_UNLOCKED = 150,
               RTOP_SECRET_WALL_1_BROKEN = 152,
               RTOP_SECRET_WALL_2_BROKEN = 153,
               RTOP_SECRET_STAIRS = 155,
               NZ1_STAGE_FLAG = 160,
               NZ1_LOWER_WALL_OPEN = 161,
               NZ1_UPPER_WALL_OPEN = 162,
               NZ1_STATUE_ROOM_BREAKABLE_WALLS = 163,
               RNZ1_UPPER_WALL_OPEN = 169,
               RNZ1_LOWER_WALL_OPEN = 170,
               RNZ1_STATUE_ROOM_BREAKABLE_WALLS = 171,
               ARE_STAGE_FLAG = 176,
               ARE_TO_DAI_SHORTCUT = 177,
               ARE_ELEVATOR_ACTIVATED = 178,
               ARE_SECRET_CEILING_OPEN = 179,
               RICHTER_CS_AFTER_M_AND_W = 180,
               RARE_SECRET_FLOOR_OPEN = 184,
               RARE_ELEVATOR_ACTIVATED = 185,
               NO4_STAGE_FLAG = 192,
               NO4_WATER_BLOCKED = 193,
               FERRYMAN_GATE_OPEN = 194,
               SCYLLA_DEFEATED = 195,
               NO4_SECRET_FLOOR_OPEN = 196,
               SCYLLA_WYRM_DEFEATED = 197,
               NO4_SECRET_WALL_OPEN = 198,
               NO4_SKELETON_APE_AND_BRIDGE = 199,
               MET_FERRYMAN_2 = 200,
               MET_FERRYMAN_1 = 201,
               RNO4_SECRET_CEILING_OPEN = 202,
               RNO4_SECRET_WALL_OPEN = 203,
               WRP_UNLOCKS = 208,
               RWRP_UNLOCKS = 209,
               SUCCUBUS_CS = 212,
               DRE_STAGE_FLAG = 213,
               MET_MARIA_IN_CEN = 216,
               DEATH_FIGHT_CS = 220,
               SHAFT_FIGHT_CS_UNK1 = 224,
               SHAFT_FIGHT_CS_UNK2 = 227,
               RCEN_OPEN = 228,
                CASTLE_COLLECTIBLES_100 = 256,
                CASTLE_COLLECTIBLES_101 = 257,
                CASTLE_COLLECTIBLES_102 = 258,
                CASTLE_COLLECTIBLES_104 = 260,
                CASTLE_COLLECTIBLES_105 = 261,
                CASTLE_COLLECTIBLES_106 = 262,
                CASTLE_COLLECTIBLES_107 = 263,
                CASTLE_COLLECTIBLES_108 = 264,
                CASTLE_COLLECTIBLES_109 = 265,
                CASTLE_COLLECTIBLES_10A = 266,
                CASTLE_COLLECTIBLES_10B = 267,
                CASTLE_COLLECTIBLES_10C = 268,
                CASTLE_COLLECTIBLES_10E = 270,
                CASTLE_COLLECTIBLES_10F = 271,
                CASTLE_COLLECTIBLES_110 = 272,
                CASTLE_COLLECTIBLES_111 = 273,
                CASTLE_COLLECTIBLES_112 = 274,
                CASTLE_COLLECTIBLES_113 = 275,
                CASTLE_COLLECTIBLES_114 = 276,
                CASTLE_COLLECTIBLES_116 = 278,
                CASTLE_COLLECTIBLES_117 = 279,
                CASTLE_COLLECTIBLES_11A = 282,
                CASTLE_COLLECTIBLES_11C = 284,
                CASTLE_COLLECTIBLES_11D = 285,
                CASTLE_COLLECTIBLES_11E = 286,
                CASTLE_COLLECTIBLES_11F = 287,
                MAD_COLLISION_FLAGS_START = 288,
                CASTLE_COLLECTIBLES_120 = 288,
                CASTLE_COLLECTIBLES_121 = 289,
                CASTLE_COLLECTIBLES_122 = 290,
                CASTLE_COLLECTIBLES_127 = 295,
                CASTLE_COLLECTIBLES_128 = 296,
                CASTLE_COLLECTIBLES_12B = 299,
                CASTLE_COLLECTIBLES_12F = 303,
                CASTLE_COLLECTIBLES_130 = 304,
                CASTLE_COLLECTIBLES_133 = 307,
                CASTLE_COLLECTIBLES_134 = 308,
                CASTLE_COLLECTIBLES_137 = 311,
                CASTLE_COLLECTIBLES_138 = 312,
                CASTLE_COLLECTIBLES_139 = 313,
                CASTLE_COLLECTIBLES_13A = 314,
                CASTLE_COLLECTIBLES_13B = 315,
                CASTLE_COLLECTIBLES_13C = 316,
                CASTLE_COLLECTIBLES_13F = 319,
                MAD_RAREDROP_FLAGS_START = 320,
                CASTLE_COLLECTIBLES_140 = 320,
                CASTLE_COLLECTIBLES_141 = 321,
                CASTLE_COLLECTIBLES_143 = 323,
                CASTLE_COLLECTIBLES_144 = 324,
                CASTLE_COLLECTIBLES_145 = 325,
                CASTLE_COLLECTIBLES_147 = 327,
                CASTLE_COLLECTIBLES_14F = 335,
                CASTLE_COLLECTIBLES_153 = 339,
                CASTLE_COLLECTIBLES_154 = 340,
                CASTLE_COLLECTIBLES_155 = 341,
                CASTLE_COLLECTIBLES_156 = 342,
                CASTLE_COLLECTIBLES_157 = 343,
                CASTLE_COLLECTIBLES_158 = 344,
                CASTLE_COLLECTIBLES_15B = 347,
                CASTLE_COLLECTIBLES_15C = 348,
                ENEMY_TACTICS_180 = 384,
                ENEMY_TACTICS_181 = 385,
                ENEMY_TACTICS_182 = 386,
                ENEMY_TACTICS_183 = 387,
                ENEMY_LIST_190 = 400,
                ENEMY_LIST_191 = 401,
                ENEMY_LIST_192 = 402,
                ENEMY_LIST_193 = 403,
                ENEMY_LIST_194 = 404,
                ENEMY_LIST_195 = 405,
                ENEMY_LIST_196 = 406,
                ENEMY_LIST_197 = 407,
                ENEMY_LIST_198 = 408,
                ENEMY_LIST_199 = 409,
                ENEMY_LIST_19A = 410,
                ENEMY_LIST_19B = 411,
                ENEMY_LIST_19C = 412,
                ENEMY_LIST_19D = 413,
                ENEMY_LIST_19E = 414,
                ENEMY_LIST_19F = 415,
                ENEMY_LIST_1A0 = 416,
                ENEMY_LIST_1A1 = 417,
                ENEMY_LIST_1A2 = 418,
                ENEMY_LIST_RAREDROP_1B0 = 432,
                ENEMY_LIST_RAREDROP_1B1 = 433,
                ENEMY_LIST_RAREDROP_1B2 = 434,
                ENEMY_LIST_RAREDROP_1B3 = 435,
                ENEMY_LIST_RAREDROP_1B4 = 436,
                ENEMY_LIST_RAREDROP_1B5 = 437,
                ENEMY_LIST_RAREDROP_1B6 = 438,
                ENEMY_LIST_RAREDROP_1B7 = 439,
                ENEMY_LIST_RAREDROP_1B8 = 440,
                ENEMY_LIST_RAREDROP_1B9 = 441,
                ENEMY_LIST_RAREDROP_1BA = 442,
                ENEMY_LIST_RAREDROP_1BB = 443,
                ENEMY_LIST_RAREDROP_1BC = 444,
                ENEMY_LIST_RAREDROP_1BD = 445,
                ENEMY_LIST_RAREDROP_1BE = 446,
                ENEMY_LIST_RAREDROP_1BF = 447,
                ENEMY_LIST_RAREDROP_1C0 = 448,
                ENEMY_LIST_RAREDROP_1C1 = 449,
                ENEMY_LIST_RAREDROP_1C2 = 450,
                SWORD_FAMILIAR = 464,
                RWRP_STAGE_FLAG = 480
} CastleFlagOffsets;
typedef enum {
    Player_Stand,
    Player_Walk,
    Player_Crouch,
    Player_Fall,
    Player_Jump,
    Player_MorphBat,
    Player_AlucardStuck,
    Player_MorphMist,
    Player_HighJump,
    Player_UnmorphBat,
    Player_Hit,
    Player_StatusStone,
    Player_BossGrab,
    Player_KillWater,
    Player_UnmorphMist,
    Player_SwordWarp,
    Player_Kill,
    Player_Unk17,
    Player_Teleport,
    Player_FlameWhip,
    Player_Unk20,
    Player_ThousandBlades,
    Player_RichterFourHolyBeasts,
    Player_Slide,
    Player_MorphWolf,
    Player_UnmorphWolf,
    Player_SlideKick,
    Player_Unk27,
    Player_SpellDarkMetamorphosis = 32,
    Player_SpellSummonSpirit,
    Player_SpellHellfire,
    Player_SpellTetraSpirit,
    Player_Spell36,
    Player_SpellSoulSteal,
    Player_Unk38,
    Player_SpellSwordBrothers,
    Player_AxearmorStand,
    Player_AxearmorWalk,
    Player_AxearmorJump,
    Player_AxearmorHit,
    Player_Unk48 = 48,
    Player_Unk49,
    Player_Unk50
} PlayerSteps;
typedef enum {
    Player_Stand_0,
    Player_Stand_PressUp,
    Player_Stand_2,
    Player_Stand_3,
    Player_Stand_ChairSit
} PlayerStandSteps;
struct DIRENTRY {
               char name[20];
               long attr;
               long size;
               struct DIRENTRY* next;
               long head;
               char system[4];
};
void EnterCriticalSection(void);
void ExitCriticalSection(void);
long _card_info(long chan);
long _card_clear(long chan);
long _card_load(long chan);
void InitCARD(long val);
long StartCARD(void);
struct EXEC {
    unsigned long pc0;
    unsigned long gp0;
    unsigned long t_addr;
    unsigned long t_size;
    unsigned long d_addr;
    unsigned long d_size;
    unsigned long b_addr;
    unsigned long b_size;
    unsigned long s_addr;
    unsigned long s_size;
    unsigned long sp, fp, gp, ret, base;
};
extern void InitHeap(void*, unsigned long);
extern long Load(char*, struct EXEC*);
extern long Exec(struct EXEC*, long, char**);
extern void _bu_init(void);
extern int open(const char* devname,
                 int flag
);
extern long lseek(long, long, long);
extern long read(long fd,
                 void* buf,
                 long n
);
extern long write(long, void*, long);
extern int close(int fd
);
extern long format(char* fs
);
extern struct DIRENTRY* firstfile(char*, struct DIRENTRY*);
extern struct DIRENTRY* nextfile(struct DIRENTRY*);
extern long erase(char*);
extern void ChangeClearPAD(long);
extern void StopPAD(void);
int PAD_init(s32 , s32* );
extern void FlushCache(void);
extern void DeliverEvent(unsigned long, unsigned long);
extern long TestEvent(unsigned long event
);
extern long OpenEvent(unsigned long, long, long, long (*func)());
extern long EnableEvent(long);
extern void _96_remove(void);
extern long SetRCnt(unsigned long, unsigned short, long);
extern long StartRCnt(unsigned long);
extern long GetRCnt(unsigned long);
extern long StopRCnt(unsigned long);
extern long ResetRCnt(unsigned long);
extern void exit();
extern void puts(char*);
extern char* strcat(char*, char*);
extern int strcmp(const char*, const char*);
extern int strncmp(const char*, const char*);
extern char* strcpy(const char*, const char*);
extern int strlen(const char*);
extern void* memcpy(void*, const void*, size_t);
extern void* memset(unsigned char*, unsigned char, int);
extern int rand(void);
extern void srand(unsigned int);
extern void* malloc(size_t
);
extern void free(void*);
int printf(char*, ...);
int abs(int x);
typedef struct {
    u_char minute;
    u_char second;
    u_char sector;
    u_char track;
} CdlLOC;
typedef struct {
    u_char val0;
    u_char val1;
    u_char val2;
    u_char val3;
} CdlATV;
typedef struct {
    u_short id;
    u_short type;
    u_short secCount;
    u_short nSectors;
    u_long frameCount;
    u_long frameSize;
    u_short width;
    u_short height;
    u_long dummy1;
    u_long dummy2;
    CdlLOC loc;
} StHEADER;
typedef struct {
    CdlLOC pos;
    u_long size;
    char name[16];
} CdlFILE;
typedef void (*CdlCB)(u_char, u_char*);
int CdInit(void);
char CdStatus(void);
int CdMode(void);
int CdLastCom(void);
int CdReset(int mode);
void CdFlush(void);
int CdSetDebug(int level);
char* CdComstr(u_char com);
char* CdIntstr(u_char intr);
int CdSync(int mode, u_char* result);
int CdReady(int mode, u_char* result);
CdlCB CdSyncCallback(CdlCB func);
CdlCB CdReadyCallback(CdlCB func);
int CdControl(u_char com, u_char* param, u_char* result);
int CdControlB(u_char com, u_char* param, u_char* result);
int CdControlF(u_char com, u_char* param);
int CdMix(CdlATV* vol
);
int CdGetSector(void* madr, int size);
long CdDataCallback(void (*func)());
CdlLOC* CdIntToPos(int i, CdlLOC* p);
int CdPosToInt(CdlLOC* p);
CdlFILE* CdSearchFile(CdlFILE* fp, char* name);
int CdRead(int sectors, u_long* buf, int mode);
int CdReadSync(int mode, u_char* result);
CdlCB CdReadCallback(CdlCB func);
int CdRead2(long mode);
void StClearRing(void);
void StSetStream(u_long mode, u_long start_frame, u_long end_frame,
                 void (*func1)(), void (*func2)());
void StSetMask(u_long mask, u_long start, u_long end);
u_long StGetNext(u_long** addr, u_long** header);
u_long StFreeRing(u_long* base);
int StGetBackloc(CdlLOC* loc);
void StSetRing(u_long* ring_addr, u_long ring_size1);
void StUnSetRing(void);
typedef void (*Callback)();
struct Callbacks {
    const char* rcsid;
    Callback (*DMACallback)(int dma, Callback f);
    Callback (*InterruptCallback)(int irq, Callback f);
    void* (*ResetCallback)(void);
    void* (*StopCallback)(void);
    Callback (*VSyncCallbacks)(int ch, Callback f);
    void* (*RestartCallback)(void);
    void* intrEnv;
};
extern struct Callbacks* D_8002D340;
int VSync(int mode);
void VSyncCallback(Callback f);
Callback VSyncCallbacks(int ch, Callback f);
Callback DMACallback(int dma, Callback f);
void* ResetCallback(void);
void StopCallback(void);
long RestartCallback(void);
int CheckCallback(void);
long SetVideoMode(long mode);
void PadInit(int mode);
u_long PadRead(int id);
void PadStop(void);
typedef struct {
              short x;
              short y;
              short w;
              short h;
} RECT;
typedef struct {
    u_long addr : 24;
    u_long len : 8;
    u_char r0, g0, b0, code;
} P_TAG;
typedef struct {
    u_char r0, g0, b0, code;
} P_CODE;
typedef struct {
    u_long tag;
              u_long code[15];
} DR_ENV;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    short x1, y1;
    short x2, y2;
} POLY_F3;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    short x1, y1;
    short x2, y2;
    short x3, y3;
} POLY_F4;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    u_char u0, v0;
    u_short clut;
    short x1, y1;
    u_char u1, v1;
    u_short tpage;
    short x2, y2;
    u_char u2, v2;
    u_short pad1;
} POLY_FT3;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    u_char u0, v0;
    u_short clut;
    short x1, y1;
    u_char u1, v1;
    u_short tpage;
    short x2, y2;
    u_char u2, v2;
    u_short pad1;
    short x3, y3;
    u_char u3, v3;
    u_short pad2;
} POLY_FT4;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    u_char r1, g1, b1, pad1;
    short x1, y1;
    u_char r2, g2, b2, pad2;
    short x2, y2;
} POLY_G3;
typedef struct {
               u_long tag;
               u_char r0;
               u_char g0;
               u_char b0;
               u_char code;
               short x0;
               short y0;
               u_char u0;
               u_char v0;
               u_short clut;
               u_char r1;
               u_char g1;
               u_char b1;
               u_char p1;
               short x1;
               short y1;
               u_char u1;
               u_char v1;
               u_short tpage;
               u_char r2;
               u_char g2;
               u_char b2;
               u_char p2;
               short x2;
               short y2;
               u_char u2;
               u_char v2;
               u_short pad2;
} POLY_GT3;
typedef struct {
               u_long tag;
               u_char r0;
               u_char g0;
               u_char b0;
               u_char code;
               short x0;
               short y0;
               u_char r1;
               u_char g1;
               u_char b1;
               u_char pad1;
               short x1;
               short y1;
               u_char r2;
               u_char g2;
               u_char b2;
               u_char pad2;
               short x2;
               short y2;
               u_char r3;
               u_char g3;
               u_char b3;
               u_char pad3;
               short x3;
               short y3;
} POLY_G4;
typedef struct {
               u_long tag;
               u_char r0;
               u_char g0;
               u_char b0;
               u_char code;
               short x0;
               short y0;
               u_char u0;
               u_char v0;
               u_short clut;
               u_char r1;
               u_char g1;
               u_char b1;
               u_char p1;
               short x1;
               short y1;
               u_char u1;
               u_char v1;
               u_short tpage;
               u_char r2;
               u_char g2;
               u_char b2;
               u_char p2;
               short x2;
               short y2;
               u_char u2;
               u_char v2;
               u_short pad2;
               u_char r3;
               u_char g3;
               u_char b3;
               u_char p3;
               short x3;
               short y3;
               u_char u3;
               u_char v3;
               u_short pad3;
} POLY_GT4;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    short x1, y1;
} LINE_F2;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    u_char r1, g1, b1, p1;
    short x1, y1;
} LINE_G2;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    short x1, y1;
    short x2, y2;
    u_long pad;
} LINE_F3;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    u_char r1, g1, b1, p1;
    short x1, y1;
    u_char r2, g2, b2, p2;
    short x2, y2;
    u_long pad;
} LINE_G3;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    short x1, y1;
    short x2, y2;
    short x3, y3;
    u_long pad;
} LINE_F4;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    u_char r1, g1, b1, p1;
    short x1, y1;
    u_char r2, g2, b2, p2;
    short x2, y2;
    u_char r3, g3, b3, p3;
    short x3, y3;
    u_long pad;
} LINE_G4;
typedef struct {
               u_long tag;
               u_char r0;
               u_char g0;
               u_char b0;
               u_char code;
               short x0;
               short y0;
               u_char u0;
               u_char v0;
               u_short clut;
               short w;
               short h;
} SPRT;
typedef struct {
               u_long tag;
               u_char r0;
               u_char g0;
               u_char b0;
               u_char code;
               short x0;
               short y0;
               u_char u0;
               u_char v0;
               u_short clut;
} SPRT_16;
typedef struct {
               u_long tag;
               u_char r0;
               u_char g0;
               u_char b0;
               u_char code;
               short x0;
               short y0;
               u_char u0;
               u_char v0;
               u_short clut;
} SPRT_8;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    short w, h;
} TILE;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
} TILE_16;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
} TILE_8;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
} TILE_1;
typedef struct {
    u_long tag;
    u_char r0, g0, b0, code;
    short x0, y0;
    short w, h;
} BLK_FILL;
typedef struct {
               RECT clip;
               short ofs[2];
               RECT tw;
               u_short tpage;
               u_char dtd;
               u_char dfe;
               u_char isbg;
               u_char r0, g0, b0;
               DR_ENV dr_env;
} DRAWENV;
typedef struct {
               RECT disp;
               RECT screen;
               u_char isinter;
               u_char isrgb24;
               u_char pad0;
               u_char pad1;
} DISPENV;
typedef struct {
    u_long tag;
    u_long code[2];
} DR_MODE;
typedef struct {
    u_long tag;
    u_long code[2];
} DR_TWIN;
typedef struct {
    u_long tag;
    u_long code[2];
} DR_AREA;
typedef struct {
    u_long tag;
    u_long code[2];
} DR_OFFSET;
typedef struct {
    u_long tag;
    u32 code[2];
} DR_PRIO;
typedef struct PixPattern {
    u8 w;
    u8 h;
    u8 x;
    u8 y;
} PixPattern;
extern u_short LoadTPage(
    u_long* pix,
    int tp,
    int abr,
    int x, int y,
    int w, int h
);
extern u_short LoadClut(u_long* clut, int x, int y);
u_short GetClut(int x,
                int y
);
u_short GetTPage(int tp, int abr, int x, int y);
void DumpTPage(u_short tpage);
void DumpClut(u_short clut);
extern void AddPrim(void* ot, void* p);
extern void SetShadeTex(void* p, int tge);
extern void SetLineG2(LINE_G2* p);
extern void SetPolyGT3(POLY_GT3* p);
extern void SetPolyG4(POLY_G4* p);
extern void SetPolyGT4(POLY_GT4* p);
extern void SetSemiTrans(void* p, int abe);
extern void SetSprt(SPRT* p);
extern void SetSprt16(SPRT_16* p);
extern void SetSprt8(SPRT_8* p);
extern void SetTile(TILE* p);
extern int ResetGraph(int mode);
int SetGraphDebug(int level);
extern int SetGraphReverse(int mode);
extern int SetGraphQueue(int mode);
extern u_long DrawSyncCallback(void (*func)());
extern void FntLoad(int tx, int ty);
int FntPrint(const char* fmt, ...);
extern void SetDispMask(int mask);
extern void SetDrawMode(DR_MODE* p, int dfe, int dtd, int tpage, RECT* tw);
extern void SetDumpFnt(int id);
extern int ClearImage(RECT* rect, u_char r, u_char g, u_char b);
extern int DrawSync(int mode);
extern int FntOpen(int x, int y, int w, int h, int isbg, int n);
extern u_long* FntFlush(int id);
extern int LoadImage(RECT* rect, u_long* p);
extern int StoreImage(RECT* rect, u_long* p);
extern int MoveImage(RECT* rect, int x, int y);
extern u_long* ClearOTag(u_long* ot, int n);
extern u_long* ClearOTagR(u_long* ot, int n);
extern void DrawOTag(u_long* p);
extern DRAWENV* PutDrawEnv(DRAWENV* env);
extern DISPENV* PutDispEnv(DISPENV* env);
extern DISPENV* SetDefDispEnv(DISPENV* env, int x, int y, int w, int h);
extern DRAWENV* SetDefDrawEnv(DRAWENV* env, int x, int y, int w, int h);
extern void SetDrawEnv(DR_ENV* dr_env, DRAWENV* env);
void GsClearVcount(void);
long GsGetVcount();
void GsInitVcount();
void InitGeom();
typedef struct {
    short m[3][3];
    long t[3];
} MATRIX;
typedef struct {
    long vx, vy, vz;
    long pad;
} VECTOR;
typedef struct {
    short vx, vy, vz;
    short pad;
} SVECTOR;
typedef struct {
    u_char r, g, b;
    u_char cd;
} CVECTOR;
MATRIX* CompMatrix(MATRIX* m0, MATRIX* m1, MATRIX* m2);
MATRIX* RotMatrix(SVECTOR* r, MATRIX* m);
void SetGeomOffset(long ofx, long ofy);
void RotTrans(SVECTOR* v0, VECTOR* v1, long* flag);
long RotTransPers(SVECTOR*, long*, long*, long*);
void SetGeomScreen(long h);
void SetRotMatrix(MATRIX* m);
MATRIX* RotMatrixX(long r, MATRIX* m);
MATRIX* RotMatrixY(long r, MATRIX* m);
MATRIX* RotMatrixZ(long r, MATRIX* m);
MATRIX* TransMatrix(MATRIX* m, VECTOR* v);
MATRIX* ScaleMatrix(MATRIX* m, VECTOR* v);
void SetTransMatrix(MATRIX* m);
long RotTransPers4(
    SVECTOR* v0, SVECTOR* v1, SVECTOR* v2,
    SVECTOR* v3,
    long* v10, long* v11, long* v12,
    long* v13,
    long* p,
    long* flag
);
long RotAverage4(SVECTOR* v0, SVECTOR* v1, SVECTOR* v2, SVECTOR* v3, long* sxy0,
                 long* sxy1, long* sxy2, long* sxy3, long* p, long* flag);
long RotAverageNclip4(
    SVECTOR* v0, SVECTOR* v1, SVECTOR* v2,
    SVECTOR* v3,
    long* sxy0, long* sxy1, long* sxy2,
    long* sxy3,
    long* p,
    long* otz,
    long* flag
);
long NormalClip(long sxy0, long sxy1, long sxy2);
void NormalColorCol(SVECTOR* v0,
                    CVECTOR* v1,
                    CVECTOR* v2
);
MATRIX* RotMatrixY(long r,
                   MATRIX* m
);
void SetBackColor(long rbk, long gbk, long bbk);
void SetColorMatrix(MATRIX* m);
void SetLightMatrix(MATRIX* m);
void SetTransMatrix(MATRIX* m);
void SetFarColor(long rfc, long gfc, long bfc);
void SetFogNear(long a, long h);
MATRIX* MulMatrix(MATRIX* m0, MATRIX* m1);
long SquareRoot0(long a);
long SquareRoot12(long a);
int rcos(int a);
int rsin(int a);
long ratan2(long y, long x);
typedef void (*SpuIRQCallbackProc)(void);
typedef struct {
    unsigned short left;
    unsigned short right;
} SpuVolume;
typedef struct {
               unsigned long voice;
               unsigned long mask;
               SpuVolume volume;
               SpuVolume volmode;
               SpuVolume volumex;
               unsigned short pitch;
               unsigned short note;
               unsigned short sample_note;
               short envx;
               unsigned long addr;
               unsigned long loop_addr;
               long a_mode;
               long s_mode;
               long r_mode;
               unsigned short ar;
               unsigned short dr;
               unsigned short sr;
               unsigned short rr;
               unsigned short sl;
               unsigned short adsr1;
               unsigned short adsr2;
} SpuVoiceAttr;
typedef struct {
    unsigned long mask;
    long mode;
    SpuVolume depth;
    long delay;
    long feedback;
} SpuReverbAttr;
typedef struct {
    SpuVolume volume;
    long reverb;
    long mix;
} SpuExtAttr;
typedef struct {
    unsigned long mask;
    SpuVolume mvol;
    SpuVolume mvolmode;
    SpuVolume mvolx;
    SpuExtAttr cd;
    SpuExtAttr ext;
} SpuCommonAttr;
extern long SpuSetTransferMode(long mode);
extern unsigned long SpuWrite(unsigned char* addr, unsigned long size);
extern long SpuSetReverbModeParam(SpuReverbAttr* attr);
extern void SpuSetVoiceAttr(SpuVoiceAttr* arg);
extern void SpuSetKey(long on_off, unsigned long voice_bit);
extern long SpuMallocWithStartAddr(unsigned long addr, long size);
extern SpuIRQCallbackProc SpuSetIRQCallback(SpuIRQCallbackProc);
extern void SsSeqClose(short seq_access_num);
extern void SsSetMVol(short voll, short volr);
extern void SsSetSerialAttr(char s_num, char attr, char mode);
extern void SsSetSerialVol(short s_num, short voll, short volr);
extern long SpuClearReverbWorkArea(long rev_mode
);
void SsInitHot(void);
char SsSetReservedVoice(char voices
);
void SsSetTickMode(long tick_mode
);
void SsStart(void);
short SsUtKeyOnV(
    short voice,
    short vabId,
    short prog,
    short tone,
    short note,
    short fine,
    short voll,
    short volr
);
short SsUtSetVVol(short vc,
                  short voll,
                  short volr
);
void SpuGetAllKeysStatus(s8* status);
void SsSetTableSize(
    char* table,
    short s_max,
    short t_max
);
void SsSeqStop(short seq_access_num
);
void SsSetMono(void);
void SsSetStereo(void);
s32 SsVabOpenHeadSticky(
    u_char* addr,
    u_long vabid,
    u_long sbaddr
);
s32 SsVabTransBodyPartly(
    u_char* addr,
    u_long bufsize,
    u_long vabid
);
s32 SsVabTransCompleted(
    short immediateFlag
);
void SsUtSetReverbType(short type);
void SsUtReverbOn(void);
void SsUtSetReverbDepth(
    short ldepth,
    short rdepth
);
void SsUtSetReverbDelay(short delay);
typedef long Event;
typedef struct Vertex {
              u8 r;
              u8 g;
              u8 b;
              u8 p;
              s16 x;
              s16 y;
              u8 u;
              u8 v;
              u16 param;
} Vertex;
typedef struct {
               SVECTOR* v0;
               SVECTOR* v1;
               SVECTOR* v2;
               SVECTOR* v3;
} SVEC4;
typedef struct {
    s16 x;
    s16 y;
    u8 u;
    u8 v;
    u16 param;
    u8 r;
    u8 g;
    u8 b;
    u8 p;
} VertexFake;
typedef struct Prim {
    struct Prim* next;
    struct Vertex v[4];
} Prim;
typedef enum {
    PRIORITY_DIALOGUE = 0x1FE,
} PrimitivePriority;
typedef enum {
    PRIM_NONE,
    PRIM_TILE,
    PRIM_LINE_G2,
    PRIM_G4,
    PRIM_GT4,
    PRIM_GT3,
    PRIM_SPRT,
    PRIM_ENV,
    PRIM_TILE_ALT = PRIM_TILE | 0x10,
    PRIM_LINE_G2_ALT = PRIM_LINE_G2 | 0x10,
    PRIM_G4_ALT = PRIM_G4 | 0x10
} PrimitiveType;
typedef struct Primitive {
               struct Primitive* next;
               u8 r0;
               u8 g0;
               u8 b0;
               u8 type;
               s16 x0;
               s16 y0;
               u8 u0;
               u8 v0;
               u16 clut;
               u8 r1;
               u8 g1;
               u8 b1;
               u8 p1;
               s16 x1;
               s16 y1;
               u8 u1;
               u8 v1;
               u16 tpage;
               u8 r2;
               u8 g2;
               u8 b2;
               u8 p2;
               s16 x2;
               s16 y2;
               u8 u2;
               u8 v2;
               u16 priority;
               u8 r3;
               u8 g3;
               u8 b3;
               u8 p3;
               s16 x3;
               s16 y3;
               u8 u3;
               u8 v3;
               u16 drawMode;
} Primitive;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
typedef struct FakePrim {
    struct FakePrim* next;
               u8 r0;
               u8 g0;
               u8 b0;
               u8 type;
               s16 x0;
               s16 y0;
               u8 w;
               u8 h;
               u16 clut;
               f32 posX;
               f32 posY;
               f32 velocityX;
               f32 velocityY;
               s16 x2;
               s16 y2;
               s16 delay;
               u16 priority;
               f32 accelerationX;
               f32 accelerationY;
               s16 timer;
               u16 drawMode;
} FakePrim;
typedef struct PrimLineG2 {
    struct PrimLineG2* next;
               u8 r0;
               u8 g0;
               u8 b0;
               u8 type;
               s16 x0;
               s16 y0;
               s16 xLength;
               s16 yLength;
               u8 r1;
               u8 g1;
               u8 b1;
               u8 p1;
               s16 x1;
               s16 y1;
               f32 velocityX;
               f32 velocityY;
               s32 angle;
               s16 delay;
               u16 priority;
               f32 preciseX;
               f32 preciseY;
               s16 timer;
               u16 drawMode;
} PrimLineG2;
typedef struct AxePrim {
    struct AxePrim* next;
               u8 r0;
               u8 g0;
               u8 b0;
               u8 type;
               s16 x0;
               s16 y0;
               s32 unk0C;
               s32 unk10;
               s16 x1;
               s16 y1;
               u8 u1;
               u8 v1;
               u16 tpage;
               s16 unk1C;
               s16 unk1E;
               s16 x2;
               s16 y2;
               u8 step;
               u16 priority;
               s32 pad;
               s16 timer;
               s16 unk2E;
               u8 u3;
               u8 v3;
               u16 drawMode;
} AxePrim;
typedef struct EntranceCascadePrim {
               struct EntranceCascadePrim* next;
               s32 : 32;
               s16 x0;
               s16 y0;
               s32 unk10;
               s32 unk14;
               s16 x1;
               s16 y1;
               s16 : 16;
               s16 unk1E;
               s16 x2;
               s16 y2;
               f32 velocityY;
               u8 step;
               u8 unk25;
               u16 priority;
               u8 r3;
               u8 g3;
               u8 b3;
               u8 p3;
               f32 velocityX;
               s16 : 16;
               u16 drawMode;
} EntranceCascadePrim;
typedef struct FrozenShadePrim {
               struct FrozenShadePrim* next;
               u8 r0;
               u8 g0;
               u8 b0;
               u8 type;
               s16 x0;
               s16 y0;
               f32 posX;
               u8 r1;
               u8 g1;
               u8 b1;
               u8 p1;
               s16 x1;
               s16 y1;
               f32 posY;
               u8 r2;
               u8 g2;
               u8 b2;
               u8 p2;
               s16 x2;
               s16 y2;
               u8 u2;
               u8 v2;
               u16 priority;
               u8 r3;
               u8 g3;
               u8 b3;
               u8 p3;
               s16 x3;
               s16 y3;
               u8 u3;
               u8 v3;
               u16 drawMode;
} FrozenShadePrim;
typedef struct NumericPrim {
               struct NumericPrim* next;
               u8 r0;
               u8 g0;
               u8 b0;
               u8 type;
               s16 x0;
               s16 y0;
               u8 u0;
               u8 v0;
               u16 clut;
               s16 _xOffset;
               s16 _yOffset;
               s16 x1;
               s16 y1;
               u8 u1;
               u8 v1;
               u16 tpage;
               u16 _width;
               u16 _height;
               s16 x2;
               s16 y2;
               u8 u2;
               u8 v2;
               u16 priority;
               u32 unused28;
               s16 x3;
               s16 y3;
               u8 u3;
               u8 v3;
               u16 drawMode;
} NumericPrim;
typedef struct {
    Primitive* prim;
    float y0;
} UnkPrimStruct;
struct SubPrim {
    u8 col[3];
    u8 type;
    s16 x0;
    s16 y0;
    u8 u0;
    u8 v0;
    u16 clut;
};
typedef struct Primitive2 {
    struct Primitive2* next;
    struct SubPrim prim[4];
} Primitive2;
typedef struct ProloguePrimitive {
    u8 u0;
    u8 v0;
    u8 u1;
    u8 v1;
    s16 x;
    s16 y;
    u16 tpage;
} ProloguePrimitive;
typedef struct {
               s32 x0;
               s32 y0;
               s32 x1;
               s32 y1;
               s32 x2;
               s32 y2;
               s16 u0;
               s16 v0;
               s16 u1;
               s16 v1;
               s16 u2;
               s16 v2;
               u8 pad[8];
} PrimWeapon017;
;
;
;
;
;
;
;
typedef enum {
    DRAW_DEFAULT = 0x00,
    DRAW_TRANSP = 0x01,
    DRAW_UNK02 = 0x02,
    DRAW_COLORS = 0x04,
    DRAW_HIDE = 0x08,
    DRAW_TPAGE = 0x10,
    DRAW_TPAGE2 = 0x20,
    DRAW_UNK_40 = 0x40,
    DRAW_MENU = 0x80,
    DRAW_UNK_100 = 0x100,
    DRAW_UNK_200 = 0x200,
    DRAW_DITHERING = 0x400,
    DRAW_UNK_800 = 0x800,
    DRAW_UNK_1000 = 0x1000,
    DRAW_ABSPOS = 0x2000,
} DrawMode;
typedef enum {
    BLEND_NO = 0x00,
    BLEND_TRANSP = 0x10,
    BLEND_ADD = 0x20,
    BLEND_SUB = 0x40,
    BLEND_QUARTER = 0x60,
} BlendModes;
struct Entity;
typedef void (*PfnEntityUpdate)(struct Entity*);
typedef union {
    u8 u8[0x3C];
    s8 s8[0x3C];
    u16 u16[0x1E];
    s16 s16[0x1E];
    u32 u32[0xF];
    s32 s32[0xF];
} ET_Placeholder;
typedef struct {
               u16 timer;
               s16 : 16;
               u8 aliveTimer;
               s8 : 8;
               s16 : 16;
               s32 fallSpeed;
               s16 gravity;
               s16 sparkleTimer;
               u16 iconSlot;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s32 castleFlag;
} ET_EquipItemDrop;
typedef struct {
               u32 unk[14];
               u16 unkB4;
               s16 unkB6;
} ET_HeartDrop;
typedef struct {
               u16 timer;
               u16 size;
               u32 speed;
} ET_BloodDroplets;
typedef struct {
               u16 nPrims;
               u16 nDigits;
               u8 digits[4];
               u16 timer;
               s16 unk86;
               u16 unk88;
               s16 unk8A;
} ET_NumericDamage;
typedef struct {
    u16 unk7C;
    u16 unk7E;
    u16 sparkleCycle;
    u16 sparkleAnim;
    u32 unk84;
    u32 unk88;
    u16 iconSlot;
    u16 unk8E;
    u16 floatTimer;
    u16 unk92;
    u32 yFloatSpeed;
} ET_RelicOrb;
typedef struct {
               u32 unused7C;
               s16 unused80;
               s16 : 16;
               s16 angle;
               s16 xOffset;
               s16 isBackgroundDoor;
} ET_RedDoor;
typedef struct {
               u32 unused7C;
               s16 unused80;
               s16 unk82;
               s16 angle;
               s16 unk86;
               u8 sideToPlayer;
               u8 showedMessage;
} ET_SealedDoor;
typedef struct {
               struct Primitive* firstTextPrim;
               s32 timer;
               struct Primitive* boxPrim;
               struct Primitive* firstOutlinePrim;
               struct Primitive* firstDissolvePrim;
               s16 textOutlineBrightness;
               s16 textFillBrightness;
} ET_StagePopup;
typedef struct {
               struct Primitive* firstTextPrim;
               s16 timer;
               struct Primitive* boxPrim;
               struct Primitive* firstStarPrim;
               u8 unk8C;
               s32 : 32;
               s32 depth;
               s32 pad[3];
               struct Primitive* firstRollingTextPrim;
               s16 rotationSlices[5];
} ET_StagePopupJP;
typedef struct {
               char* label;
               u16 width;
               u16 height;
               s16 unk84;
               u16 duration;
} ET_MessageBox;
typedef struct {
               s16 lifetime;
               s16 unk7E;
               struct Entity* unk80;
    u8 pad[16];
               struct Entity* parent;
    u8 pad2[8];
               s8 childPalette;
} ET_B0_Unk;
typedef struct {
               s16 lifetime;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               struct Entity* some_ent;
               s16 childPalette;
               s16 unk8A;
               struct Entity* parent;
               s16 unk90;
               s16 unk92;
               s16 unk94;
               s16 unk96;
               s16 unk98;
               s16 unk9A;
               s32 accelerationX;
               s32 accelerationY;
               s16 unkA4;
               s16 vol;
               s32 unkA8;
               u8 anim;
               u8 unkAD;
               s16 equipId;
} ET_Weapon;
typedef struct {
    s16 unk7C;
    s16 lifetime;
    s16 velocityZ;
    s16 unk82;
    s32 accelerationX;
    s32 accelerationY;
    byte pad[32];
    u8 anim;
} ET_WeaponUnk006;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s32 unk88;
               struct Entity* parent;
               s32 unk90;
               struct Entity* other;
               s32 unk98;
               s32 unk9C;
               s32 unkA0;
               s16 unkA4;
               s16 unkA6;
               s32 unkA8;
               u8 anim;
               u8 unkAD;
} ET_WeaponUnk030;
typedef struct {
    s32 unk7C;
    s32 unk80;
    s32 unk84;
    s32 : 32;
    s32 : 32;
    s32 unk90;
    s32 unk94;
    s32 unk98;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
    u8 anim;
} ET_WeaponUnk046;
typedef struct {
    s32 unk7C;
    s32 : 32;
    s32 unk84;
    s32 unk88;
    byte pad[32];
    u8 anim;
} ET_WeaponUnk047;
typedef struct {
    s16 timer;
    s16 unk7E;
    s32 unk80;
    s16 unk84;
    s16 unk86;
    s16 unk88;
    s16 unk8A;
    s32 unk8C;
    s16 unk90;
    s16 unk92;
    s16 unk94;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
    u8 anim;
} ET_KarmaCoin;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 : 16;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    byte pad[16];
    s32 vol;
    s32 unk9C;
               s32 : 32;
               s32 : 32;
               s32 : 32;
    u8 anim;
} ET_WeaponUnk012;
typedef struct {
    s16 unk7C;
    s16 : 16;
    byte pad[28];
    s16 unk9C;
               s32 : 32;
               s32 : 32;
               s32 : 32;
    u8 anim;
} ET_WeaponUnk014;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s32 unk80;
    s16 unk84;
    s16 unk86;
    s16 unk88;
    s16 unk8A;
    struct Entity* parent;
    s32 unk90;
    s32 unk94;
    s32 unk98;
    s32 accelerationX;
    s32 accelerationY;
    s32 unkA4;
    s32 unkA8;
    u8 anim;
} ET_WeaponUnk016;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    s16 unk88;
    s16 unk8A;
    struct Entity* parent;
    s16 unk90;
    s16 unk92;
    s16 unk94;
    s16 unk96;
    s16 unk98;
    s16 unk9A;
    s16 unk9C;
    s16 unk9E;
    s16 unkA0;
    s16 unkA2;
    s32 unkA4;
    s32 unkA8;
    u8 anim;
    u8 unkAD;
} ET_Sword;
typedef struct {
    s16 angle;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    s16 xPos;
    s16 unk8A;
    struct Entity* parent;
    s32 unk90;
    s32 unk94;
    s32 unk98;
    s32 accelerationX;
    s32 accelerationY;
    s32 unkA4;
    s32 unkA8;
    u8 anim;
    u8 unkAD;
} ET_HeavenSword;
typedef struct {
    s16 angle;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s32 unk84;
    s16 xPos;
    s16 unk8A;
    struct Entity* parent;
    s32 unk90;
    s32 unk94;
    s32 unk98;
    s32 accelerationX;
    s32 accelerationY;
    s32 unkA4;
    s32 unkA8;
    u8 anim;
    u8 unkAD;
} ET_HeavenSword2;
typedef struct {
               u8 unk7C;
               u8 unk7D;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s16 childPalette;
               s16 unk8A;
               struct Entity* parent;
               s16 unk90;
               s16 unk92;
               s16 unk94;
               s16 unk96;
               s16 unk98;
               s16 unk9A;
               s16 unk9C;
               s16 unk9E;
               s16 unkA0;
               byte pad[10];
               u8 anim;
               u8 padAD;
               s16 unkAE;
} ET_Shield;
typedef struct {
               u8 unk7C;
               u8 unk7D;
               s16 unk7E;
               u16 unk80;
               s16 pal;
               s16* palettePtr;
               u16 childPalette;
               s16 unk8A;
               struct Entity* parent;
               s16 unk90;
               s16 unk92;
               s16 unk94;
               s16 unk96;
               s16 unk98;
               s16 unk9A;
               s16 unk9C;
               byte pad[14];
               u8 anim;
               u8 padAD;
               s16 unkAE;
} ET_DarkShield;
typedef struct {
               u8 unk7C;
               u8 unk7D;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s16 childPalette;
               s16 unk8A;
               struct Entity* parent;
               struct Entity* target;
               s16 unk94;
               s16 unk96;
               s32 unk98;
               s16 unk9C;
               s16 unk9E;
               s16 unkA0;
               s16 unkA2;
               s16 unkA4;
               u16 : 16;
               u32 : 32;
               u8 anim;
               u8 unkAD;
               s16 unkAE;
} ET_MedusaShieldLaser;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s16 childPalette;
               s16 unk8A;
               struct Entity* parent;
               s16 unk90;
               s16 unk92;
               s16 unk94;
               s16 unk96;
               s16 unk98;
               s16 unk9A;
               s16 unk9C;
               s16 unk9E;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u8 anim;
} ET_ShamanShieldStar;
typedef struct {
               u8 unk7C;
               u8 unk7D;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s16 childPalette;
               s16 unk8A;
               struct Entity* parent;
               s16 unk90;
               s16 unk92;
               s16 unk94;
               s16 unk96;
               s16 unk98;
               s16 unk9A;
               u8 unk9C;
               u8 pad[15];
               u8 anim;
               s16 unkAE;
} ET_HeraldShieldSwirlEffect;
typedef struct {
    s16 timer;
    s16 unk7E;
    s32 unk80;
    s16 pad[21];
    s16 foodId;
} ET_Food;
typedef struct {
               char pad_7C[0x4];
               s16 timer;
               char pad_82[0x2];
               u8 attackMode;
               u8 flag;
               u8 nearDeath;
               s32 speed;
               s16 angle;
               char pad_8E[0xE];
               u8 pickupFlag;
               u8 grabedAscending;
} ET_GaibonSlogra;
typedef struct {
               u16 angle;
               u16 unk7E;
               u16 unk80;
               s16 unk82;
} ET_SoulStealOrb;
typedef struct {
               Primitive* primBg;
               s32 unused80;
               Primitive* primFade;
               s32 unk88;
} ET_WarpRoom;
typedef struct {
               char pad_0[0x8];
               u8 timer;
               u8 : 8;
               u8 timer2;
               u8 : 8;
               s32 : 32;
               u16 palette;
               char pad_8E[0x12];
               u8 isUnderwater;
               u8 ignoreCol;
} ET_Merman;
typedef struct {
               struct Primitive* prim;
               char pad_0[0x6];
               u8 timer;
               char pad_87[0x5];
               s16 rotation;
               char pad_8E[0x12];
               u8 isUnderwater;
               u8 ignoreCol;
} ET_Merman_2;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s16 previouslyInitialized;
               s16 batIndex;
               s16 randomMovementAngle;
               s16 targetAngle;
               s16 randomMovementScaler;
               s16 angleStep;
               s16 frameCounter;
               s16 doUpdateCloseAnimation;
               s32 unk90;
               s32 unk94;
               s32 unk98;
               s16 unk9C;
               s16 unk9E;
               s32 unkA0;
               struct Entity* attackTarget;
               s16 hasShotFireball;
               s16 unkAA;
               s16 cameraX;
               s16 cameraY;
               s16 lastPlayerPosX;
               s16 lastPlayerPosY;
               struct Entity* follow;
} ET_Bat;
typedef struct {
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               struct Entity* parent;
} ET_BatFamBlueTrail;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    struct Primitive* unk84;
    s16 unk88;
    s16 unk8A;
} ET_BatEcho;
typedef struct {
               s16 pad7C;
               s16 unk7E;
               s16 bobCounterY;
               s16 targetAngle;
               s16 maxAngle;
               s16 frameCounter;
               s16 opacity;
               s16 opacityAdjustmentAmount;
               s16 confusedSubStep;
               s32 pad8E;
               struct Entity* attackEntity;
               struct Entity* confusedEntity;
               byte pad_1C[0x6];
               struct Entity* attackTarget;
} ET_Ghost;
typedef struct {
               struct Entity* parent;
} ET_FaerieWings;
typedef struct {
               s16 lifeAppleTimer;
               s16 drawMode;
               s16 primX;
               s16 primY;
               s16 opacity;
               s16 effectOpacity;
} ET_FaerieLifeApple;
typedef struct {
               s16 : 16;
               s16 unk7E;
               s16 unkAccumulator;
               s16 unkFlag;
} ET_FaerieItem;
typedef struct {
              s16 flag;
              s16 animIndex;
              s16 sfxId;
} ServantSfxEventDesc;
typedef struct {
               s16 : 16;
               s16 abilityId;
               s16 animationFlag;
               s16 : 16;
               s16 randomMovementAngle;
               s16 targetAngle;
               s16 defaultDistToTargetLoc;
               s16 maxAngle;
               s16 frameCounter;
               s16 unk8E;
               s16 requireUncurseLuckCheck;
               s16 requireAntivenomLuckCheck;
               s16 requirePotionLuckCheck;
               s16 timer;
               u32 tileMapX;
               u32 tileMapY;
               s16 idleFrameCounter;
               s16 : 16;
               ServantSfxEventDesc* currentSfxEvent;
               s16 sfxEventFlag;
               s16 padAA[5];
               s16 unkB4;
} ET_Faerie;
typedef struct {
               s16 frameCounter;
               s16 abilityId;
               s16 : 16;
               s16 : 16;
               s16 randomMovementAngle;
               s16 targetAngle;
               s16 defaultDistToTargetLoc;
               s16 angleStep;
               s16 abilityTimer;
               s16 : 16;
               s16 : 16;
               s16 attackEndCounter;
               s16 switchPressVelocityOffset;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 unkCounter;
               struct Entity* target;
} ET_Demon;
typedef struct {
               s16 unk7c;
               s16 : 16;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s16 unk88;
               s16 currentX;
               s16 unk8c;
               s16 targetX;
               u32 posX;
               u32 posY;
               s16 unk98;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               struct Entity* follow;
} ET_SwordFamiliar;
typedef struct ET_Dracula {
               char pad_7C[4];
               struct Primitive* unk80;
               struct Primitive* unk84;
               char pad_88[4];
               s16 unk8C;
               char pad_8E[0x2];
               u8 unk90;
               char pad91;
               u8 unk92;
               char pad93;
               u8 unk94;
               char pad_95[0x3];
               s16 unk98;
               char pad_9A[0x2];
               s16 unk9C;
               char pad_9E[0x2];
               u8 unkA0;
               u8 unkA1;
               u8 unkA2;
               char pad_A3[0x9];
               struct Primitive* prim;
} ET_Dracula;
typedef struct {
               struct Primitive* prim;
               s32 unk80;
               s32 unk84;
               s16 unk88;
               char pad_8A[0x2];
               s16 unk8C;
               s16 unk8E;
} ET_StageTitleCard;
typedef struct ET_Succubus {
               char pad_7C[0x4];
               s16 timer;
               char pad_82[0x2];
               u8 facingLeft;
               u8 unk85;
               u8 nextAttack;
               u8 unk87;
               u16 nextStep;
               char pad_8A[0x4];
               s16 yOffset;
               char pad_90[0xC];
               struct Entity* real;
               s16 clonePosX;
               s16 unkA2;
} ET_Succubus;
typedef struct {
               u16 timer;
               char pad_7E[2];
               s32 unk80;
} ET_RoomTransition2;
typedef struct {
               char pad_7C[0x4];
               u8* anim;
               char pad_84[0x8];
               s32 accelY;
} ET_80192998;
typedef struct {
               s32 : 32;
               u8* anim;
               s16 angle;
               s16 : 16;
               u8 puffStyle;
               u8 speed;
               u16 : 16;
               s32 unk8C;
} ET_ExplosionPuffOpaque;
typedef struct ET_CastleDoor {
               struct Primitive* prim;
               s16 timer;
               char pad_82[0x2];
               s16 rotate;
} ET_CastleDoor;
typedef struct {
               struct Primitive* prim;
               s16 unk80;
               s16 unk82;
               s16 timer;
} ET_ShuttingWindow;
typedef struct {
               struct Primitive* prim;
               s32 : 32;
               s16 unk84;
} ET_DeathSkySwirl;
typedef struct {
               struct Primitive* prim;
               s32 yPos;
               s32 elevatorTarget;
} ET_Elevator;
typedef struct {
               s32 pad[8];
               s16 unk84;
               s16 unk86;
               s16* unk88;
} ET_801D0B40;
typedef struct {
               char pad_0[0xC];
               u16 unk88;
} ET_801D0B78;
typedef struct {
               u32 accelY;
               s16 : 16;
               s16 unk82;
               f32 topY;
               u16 unk88;
               s16 unk8A;
} ET_WaterEffects;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               s16 : 16;
               u8 unk84;
               s32 : 24;
               u16 unk88;
               s16 : 16;
               u8 unk8C;
               u8 unk8D;
               u8 unk8E;
               u8 : 8;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 rotate;
               s16 length;
               struct Entity* parent;
               s16 unkA4;
               s16 rotVel;
               u8 unkA8;
               u8 : 8;
               u16 : 16;
               s32 : 32;
               u16 unkB0[2];
               u16 unkB4[2];
} ET_GurkhaHammer;
typedef struct {
               struct Primitive* prim;
               s16 unk80;
} ET_TransparentWater;
typedef struct {
               struct Primitive* prim;
               s32 timer;
} ET_HeartRoomGoldDoor;
typedef struct {
               struct Primitive* prim;
               char pad_80[0x4];
               u8 unk84;
               u8 unk85;
               s8 unk86;
} ET_MermanWaterSplash;
typedef struct {
               u32 playerVelocity;
} ET_CastleDoorTransition;
typedef struct {
               u8 disableAfterImageFlag;
    s32 : 24;
               u32 unk80;
} ET_AlucardController;
typedef struct {
               u16 unk7C;
               u16 unk7E;
               s16 unk80;
} ET_FadeToWhite;
typedef struct {
               u16 unk7C;
               s16 : 16;
               s16 posX;
               s16 posY;
               u16 moveTimer;
               u16 moveDirection;
} ET_Death;
typedef struct {
               u8 unk7C;
               u8 : 8;
               s16 : 16;
               s16 unk80;
               s16 unk82;
               struct Entity* unk84;
} ET_SpittleBone;
typedef struct {
    Primitive* prim;
    char pad[0x24];
    s16 unkA4;
    s16 unkA6;
    void* unkA8;
    u8 anim;
} ET_Player;
typedef struct {
    u8 disableFlag;
    u8 resetFlag;
    u8 index;
    u8 timer;
} ET_AfterImage;
typedef struct {
    char pad[0x32];
    s16 unkAE;
} ET_EntitySlot16;
typedef struct {
    u8 fiveFrameCounter;
    struct Entity* parent;
    char pad[8];
    u16 parentId;
} ET_Entity13;
typedef struct {
    s16 t;
} ET_TimerOnly;
typedef struct {
    u16 t;
} ET_UTimerOnly;
typedef struct {
               s8 unk7C;
               u8 unk7D;
               s16 : 16;
               s16 unk80;
               s16 unk82;
               struct Primitive* prim;
               u8 unk88;
} ET_AxeKnight;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s16 unk88;
               s16 unk8A;
               struct Entity* parent;
               s16 newEntityId;
               s16 unk92;
               s16 amount;
               s16 nPerCycle;
               s16 tCycle;
               s16 delay;
               s16 kind;
               s16 isNonCritical;
               s16 paramsBase;
               s16 incParamsKind;
               s16 origin;
               s16 spawnIndex;
               s16 entityIdMod;
               s16 unkAA;
               s16 unkAC;
               s16 unkAE;
               s16 unkB0;
               s16 unkB2;
} ET_EntFactory;
typedef struct {
    char pad[8];
    s32 unk8;
} unk_sub_8011E4BC;
typedef struct {
    s16 unk7C;
    byte pad[14];
               struct Entity* parent;
} ET_8011E4BC;
typedef struct {
    s16 beamwidth;
    s16 beamheight;
    s16 timer;
} ET_HellfireHandler;
typedef struct {
    s16 stoneAngle;
    s16 lifeTimer;
    s16 unk80;
    s16 unk82;
    s16 unk84;
               s16 : 16;
               s32 : 32;
               struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 subweaponId;
} ET_ReboundStone;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
               s32 : 32;
               struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 subweaponId;
} ET_ReboundStoneCrashExplosion;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 subweaponId;
} ET_GiantSpinningCross;
typedef struct {
    s16 unk7C;
    s16 unk7E;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               struct Entity* parent;
} ET_8017091C;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s32 unk84;
    s32 unk88;
               struct Entity* parent;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s16 subweaponId;
} ET_Agunea;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s32 : 32;
    s32 : 32;
               struct Entity* parent;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s16 subweaponId;
} ET_AguneaCrash;
typedef struct {
    s16 timer;
    s16 size;
    s32 : 32;
    s32 : 32;
    s32 : 32;
               struct Entity* parent;
} ET_stopwatchCircle;
typedef struct {
    s16 t;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    f32 unk84;
    s32 unk88;
               struct Entity* parent;
    s16 unk90;
    s16 unk92;
    s16 crashIndex;
    s16 unk96;
    struct Entity* unk98;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s16 subweaponId;
} ET_RICStopWatch;
typedef struct {
    s16 timer;
    s16 index;
} ET_StopwatchCrash;
typedef struct {
    s16 t;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    f32 unk84;
    f32 unk88;
    s16 unk8C;
    s16 unk8E;
} ET_DRAStopWatch;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    struct Primitive* unk88;
    s16 unk8C;
    s16 unk8E;
    s16 unk90;
    s16 unk92;
    s16 unk94;
} ET_stopwatchSparkle;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    s32 unk88;
               struct Entity* parent;
    s16 unk90;
    s16 unk92;
    s16 unk94;
    s16 unk96;
    struct Entity* unk98;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s16 subweaponId;
} ET_BibleSubwpn;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
               s32 : 32;
               s32 : 32;
               struct Entity* parent;
} ET_80162870;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    s32 unk88;
    struct Entity* parent;
} ET_8016E9E4;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    s16 unk88;
    s16 unk8A;
    struct Entity* parent;
} ET_RichterPowerUpRing;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    s16 unk88;
    s16 unk8A;
} ET_TransparentWhiteCircle;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s32 : 32;
    s32 : 32;
    struct Entity* parent;
} ET_HitByIce;
typedef struct {
    s16 unk7C;
    s16 pad7E;
    s16 unk80;
    s16 unk82;
    s32 : 32;
    s32 : 32;
    struct Entity* parent;
    s16 unk90;
    s16 unk92;
    s16 unk94;
    s16 : 16;
    s32 unk98;
    s16 unk9C;
} ET_HitByLightning;
typedef struct {
    s32 width;
    s32 height;
    s32 timer;
    s32 colorIntensity;
    struct Entity* parent;
    s32 unk90;
} ET_Teleport;
typedef struct {
               s16 timer;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 subweaponId;
               s16 unkB2;
} ET_Subweapon;
typedef struct {
    s16 timer;
    s16 angle;
    s16 unk80;
    s16 unk82;
    s16 hitboxState;
               s16 : 16;
               s32 : 32;
               struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 subweaponId;
               s16 unkB2;
} ET_HolyWater;
typedef struct {
    s16 unk7C;
    f16 unk7E;
    u8 unk80;
    byte pad81;
    u8 unk82;
    byte pad83;
    s32 unk84;
    s32 : 32;
    struct Entity* parent;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s16 subweaponId;
} ET_CrashCross;
typedef struct {
               s16 timer;
               s16 unk7E;
               u16 unk80;
               u16 pad82;
               Point16* unk84;
               s32 : 32;
               struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 subweaponId;
} ET_CrossBoomerang;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    s16 unk88;
    s16 unk8A;
    u8 unk8C[4];
    u8 unk90[4];
    u8 unk94[4];
    s32 unk98;
    s32 velocity;
    s16 angle;
    s16 unkA2;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    s16 subweaponId;
} ET_SubwpnAxe;
typedef struct {
    s16 timer;
    s16 unk7E;
    s16 unk80;
    s16 pad82;
    s32 x;
    s32 y;
    s16 facing;
} ET_VibhutiCrash;
typedef struct {
    s16 unk7C;
    s16 : 16;
    s32 : 32;
    s32 : 32;
    s32 : 32;
    struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 subweaponId;
} ET_VibhutiCrashCloud;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 : 16;
    s32 : 32;
               s32 : 32;
    struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
    s16 subweaponId;
} ET_BibleBeam;
typedef struct {
    s32 prevX;
    s32 prevY;
    s16 unk84;
    s16 unk86;
    s32 unk88;
    s16 unk8C;
    s16 unk8E;
    s32 unk90;
    s32 unk94;
    s32 curX;
    s32 curY;
    s32 unkA0;
    s16 unkA4;
    s16 unkA6;
    s32 unkA8;
    s32 unkAC;
    s16 subweaponId;
    s32 unkB4;
} ET_Whip;
typedef struct {
               struct Primitive* prim1;
               struct Primitive* prim2;
               s16 unk84;
               s16 unk86;
               s16 unk88;
               struct Entity* parent;
    s16 unk90;
} ET_801291C4;
typedef struct {
    PrimLineG2* lines[4];
    s16 unk8C;
    s16 unk8E;
    s16 unk90;
} ET_8016D9C4;
typedef struct {
    struct Primitive* prim1;
    struct Primitive* prim2;
    struct Primitive* prim3;
    struct Primitive* prim4;
    s16 unk8C;
    s16 unk8E;
    u8 unk90;
} ET_801AF774;
typedef struct {
    s32 unk7C;
    s16 timer;
    s16 unk82;
    s16 unk84;
} ET_DracFinal;
typedef struct {
               byte pad[4];
               s16 angle;
               byte pad2[2];
               u8 switch_control;
               u8 speed;
} ET_BigRedFireball;
typedef struct {
    s16 timer;
    s16 spawnTimer;
} ET_SummonSpirit;
typedef struct {
    struct Primitive* prim;
    s16 unk80;
    s16 unk82;
    s16 unk84;
} ET_3DBackgroundhouse;
typedef struct {
    struct Primitive* prim1;
    struct Primitive* prim2;
    s16 unk84;
    s16 unk86;
    s16 unk88;
} ET_LifeUpSpawn;
typedef struct {
    struct Primitive* unk7C;
    u16 unk80;
    u16 unk82;
    s16 unk84;
    s16 : 16;
    s16 unk88;
    s16 : 16;
    u8 unk8C;
} ET_Owl;
typedef struct {
    u16 unk7C;
    s16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    u16 unk88;
    s16 unk8A;
    s16 unk8C;
    s16 unk8E;
} ET_AlucardWaterEffect;
typedef struct {
    u32 unk24[10];
    u8 unk28;
    u8 unk29;
} ET_80123B40;
typedef struct {
    struct Entity* ent;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
} ET_80129864;
typedef struct {
    s16 timer;
    s16 pad;
    s16 xCurrent;
    s16 yCurrent;
    s16 xTarget;
    s16 yTarget;
} ET_Mist;
typedef struct {
    s32 unk7C;
    s16 unk80;
    s16 unk82;
    s32 un84;
    s16 unk88;
    s16 unk8A;
    struct Entity* parent;
    s16 unk90;
    s16 unk92;
    s32 unk94;
    s16 unk98;
    s16 unk9A;
    s16 unk9C;
} ET_PlayerBlink;
typedef struct {
    struct Primitive* prim;
    s16 unk80;
    s16 pad82;
    s32 pad84;
    s32 pad88;
    struct Primitive* prim2;
    struct Primitive* prim3;
} ET_BloodSplatter;
typedef struct {
    s32 pad7c;
    s16 timer;
    s16 pad82;
    s32 pad84;
    s32 pad88;
    s32 pad8C;
    s16 brightness;
} ET_PlayerOutline;
typedef struct {
    u8 digits[4];
    s16 number;
    s16 type;
    s16 nDigits;
    u16 unk86;
    u16 unk88;
    u16 unk8A;
    s16 unk8C;
    s16 unk8E;
    s16 unk90;
    s16 unk92;
    s16 angleToMeter;
    s16 distToMeter;
    s16 unk98;
} ET_HPNumberMove;
typedef struct {
    s16 timer;
    s16 pad1;
    s16 halfWidth;
    s16 halfHeight;
    s32 pad2;
    s16 angle;
    s16 pad3;
    s32 pad4;
    s32 str_x;
    s32 str_y;
    s32 unk98;
} ET_GuardText;
typedef struct {
    s16 unk7C;
    s16 unk7E;
    s16 unk80;
} ET_Dissolve;
typedef struct {
    u16 unk7C;
    u16 unk7E;
    s16 unk80;
    s16 unk82;
    s16 unk84;
    s16 unk86;
    u16 unk88;
    u16 unk8A;
} ET_LockCamera;
typedef struct {
    s32 : 32;
    s16 unk80;
    s16 unk82;
} ET_Maria092BEAB0;
typedef struct {
    s16 : 16;
    s16 : 16;
    s16 crashId;
    s16 timer;
} ET_MariaCrashSummon;
typedef struct {
               struct Primitive* prim;
               s32 jiggler;
               s8 collision;
               f32 xCoord;
               f32 yCoord;
} ET_CavernDoor;
typedef struct {
               struct Primitive* prim;
               f32 unk80;
               s32 : 32;
               u16 unk88;
               s16 : 16;
               s32 unk8C;
} ET_UnkSelEnts;
typedef struct {
               s32 : 32;
               s16 spawnDelay;
               s16 : 16;
               s32 : 32;
               s32 spawnSide;
} ET_ZombieSpawner;
typedef struct {
               u8 attackTimer;
               s32 : 24;
               u8 facingLeft;
               s32 : 24;
               u8 attackTimerIndex;
               s32 : 24;
               u8 explosionTimer;
               u8 : 8;
               u8 explosionTimer2;
               s8 : 8;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 initialX;
} ET_Skeleton;
typedef struct {
               struct Primitive* prim;
               s32 unk80;
               s32 unk84;
               u8 unk88;
} ET_NZ0_311C0;
typedef struct {
               s16 unk7C;
               s16 unk7E;
} ET_FireWargDeathBeams;
typedef struct {
               u8 unk7C;
               s32 : 24;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
} ET_FireWarg;
typedef struct {
               bool unk7C;
} ET_FireWargHelper;
typedef struct {
               s32 hand;
               s32 unk80;
               u16 bellTimer;
               u16 bellDuration;
               u16 unk88;
               u16 unk8A;
} ET_ClockRoom;
typedef struct {
               u16 timer;
               u16 prevState;
               u16 state;
} ET_Birdcage;
typedef struct {
               u16 timer;
               u16 step;
} ET_Statue;
typedef struct {
               s32 flag;
               u16 unk80;
} ET_StoneDoor;
typedef struct {
               u8 disableFlag;
               u8 resetFlag;
               u8 index;
} ET_DisableAfterImage;
typedef struct {
               struct Primitive* prim;
               s32 : 32;
               u8 unk84;
} ET_EntityMermanFireSpit;
typedef struct {
               s32 : 32;
               u32 resetTimer;
               u32 breakCount;
} ET_Breakable;
typedef struct {
               struct Primitive* prim;
               s16 angle;
               s16 : 16;
               s16 breakCount;
               s16 pad[7];
               s16 resetTimer;
               s16 pad2[3];
               s16 rotSpeed;
} ET_BreakableDebris;
typedef struct {
               struct Primitive* unk7C;
               s16 unk80;
               s16 : 16;
               struct Primitive* unk84;
               u8 unk88;
} ET_BreakableNO2;
typedef struct {
               struct Primitive* prim;
               s16 hitPoints;
               s16 damageTaken;
               u8 pieceBroken;
} ET_SegmentedBreakableWall;
typedef struct {
               char pad_7C[0x4];
               s32 unk80;
} ET_DemonSwitchWall;
typedef struct {
               Primitive* prim;
               s16 timer;
} ET_DebugCerberusGate;
typedef struct {
               char pad_7C[0x4];
               s32 primBatchCount;
               s16 rotateAccel;
               char pad_86[0x2];
               Primitive* prim;
} ET_FallingStairs;
typedef struct {
               char pad_7C[0x4];
               s16 timer;
               s16 idleCircleTimer;
               u8 thinksPlayerIsEngaging;
               u8 willCurseNextAttack;
               char pad_86[1];
               u8 isDriftDirectionUp;
               char pad_88[4];
               s32 targetYPos;
} ET_SalemWitch;
typedef struct {
               char pad_7C[0x4];
               s16 timer;
} ET_SalemWitchTribolt;
typedef struct {
               char pad_7C[0x4];
               s16 timer;
} ET_Gremlin;
typedef struct {
               char pad_7C[0x4];
               s16 timer;
} ET_GremlinFire;
typedef struct {
               char pad_7C[0x4];
               s16 timer;
               char pad_82[0x4];
               u8 isCorpseweedSpawned;
} ET_Thornweed;
typedef struct {
               char pad_7C[0x4];
               s16 timer;
               char pad_82[0x2];
               u8 leavesDoneGrowing;
               u8 stalkDoneGrowing;
               char pad_86[0x2];
               s16 bobbingLeavesXT;
               s16 bobbingLeavesYT;
               s16 bobbingStalkXT;
               s16 bobbingStalkYT;
               s16 bobbingTimer;
               s16 bobbingAngle;
} ET_Corpseweed;
typedef struct {
               char pad_7C[0x4];
               Primitive* stemPrim;
               s16 leavesWidth;
               s16 leavesHeight;
               s16 stemWidth;
               s16 stemHeight;
               s16 timer;
               s16 wiggleT;
               char pad_90[0x1];
               u8 triggerAttack;
} ET_VenusWeed;
typedef struct {
               char pad_7C[0x10];
               s16 triggerAttack;
               char pad_8E[0x3];
               u8 clutOffset;
               u8 nextAttackIsDarts;
               u8 unk93;
               char pad_94[0x10];
               struct Entity* entity;
} ET_VenusWeedFlower;
typedef struct {
               char pad_7C[0x10];
               s16 timer;
               char pad_8E[0x2];
               u8 spikeStartTimeOffsetIndex;
               char pad_91[0x2];
               u8 unk93;
               s16 targetX;
               char pad_96[0xE];
               struct Entity* entity;
} ET_VenusWeedTendril;
typedef struct {
               char pad_7C[0x10];
               s16 clutIndex;
               char pad_8E[0x6];
               s16 nextPosDeltaX;
               s16 nextPosDeltaY;
               s32 speed;
               s32 accel;
} ET_VenusWeedDart;
typedef struct {
               Primitive* firstPart;
               char pad_80[0x24];
               struct Entity* flower;
} ET_VenusWeedSpike;
typedef struct {
               s16 timer;
               u16 unk7E;
} ET_EntityExplosion3;
typedef struct {
    s32 : 32;
    s16 timer;
    s16 : 16;
    u8 unk84;
} ET_BackgroundLightning;
typedef struct {
               s32 : 32;
               s32 : 32;
               u8 unk84;
} ET_SecretStairs;
typedef struct {
               s32 : 32;
               s16 unk80;
               s16 : 16;
               u8 unk84;
               u8 unk85;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               u8 index;
} ET_DestructAnimation;
typedef struct {
               struct Primitive* unk7C;
               s32 : 32;
               s16 velX;
               s16 palette;
} ET_SubwpnContainerGlass;
typedef struct {
               struct Primitive* prim;
               s16 unk80;
               s16 : 16;
               u8 unk84;
} ET_BloodyZombie;
typedef struct {
               s32 : 32;
               s32 : 32;
               s16 unk84;
} ET_MermanRock;
typedef struct {
               u8 movingBackward;
               s8 : 8;
               s8 : 8;
               s8 : 8;
               s16 timer;
               s16 decisionDelay;
               u16 anchorX;
               s16 attackTimer;
               u16 deathPosX;
               u16 deathPosY;
} ET_Warg;
typedef struct {
               u16 extStep;
               s32 : 32;
               u16 timer;
} ET_DeathScythe;
typedef struct {
               u8 animframe;
               s32 : 24;
               u8 velIndex;
} ET_Unused_MAD_ST0;
typedef struct {
               struct Primitive* prim;
               u8 playerCollision;
} ET_CEN_Elevator;
typedef struct {
               u8 playerCollision;
               u8 : 8;
               u8 movingUp;
               u8 unk7F;
               s16 unk80;
               s16 unk82;
               Point16 mapPos;
               s16 unk88;
               s16 unk8A;
               s32 unk8C;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               struct Primitive* prim;
} ET_TOP_Elevator;
typedef struct {
               struct Primitive* prim;
               s16 unk80;
               s16 : 16;
               s32 elevatorPosition;
} ET_ARE_Elevator;
typedef struct {
               s32 : 32;
               s16 timer;
} ET_BloodSkeleton;
typedef struct {
               s16 swayAngle;
               s16 swaySpeed;
               s16 timer;
} ET_SmallRisingHeart;
typedef struct {
               u8 currentAngle;
               u8 targetAngle;
} ET_801CC9B4;
typedef struct {
    u8 r, g, b;
} ET_EntranceUnk16;
typedef struct {
    s16 width;
    s16 height;
} ET_ExpandingCircle;
typedef struct {
    s16 size;
    s16 timer;
} ET_RicMariaPower;
typedef struct {
    s16 timer;
    s16 boolDidSound;
} ET_RicMaria;
typedef struct {
               u8 digits[4];
               s16 value;
               s16 kind;
               s16 nDigits;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 width;
               s16 height;
               s16 timer;
               s16 x;
               s16 direction;
               s16 distance;
               s16 angle;
} ET_Maria092BEB40;
typedef struct {
               s16 timer;
               s16 unk7E;
               s16 velocityX;
               s16 angle;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unkB0;
} ET_MariaOwl;
typedef struct {
               s16 timer;
               s16 : 16;
               s16 : 16;
               s16 hitboxState;
               s16 rotation;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unkB0;
} ET_MariaTurtleVortex;
typedef struct {
               s16 timer;
               s16 : 16;
               s16 timer2;
               s16 : 16;
               s16 timer3;
} ET_MariaTurtleCrash;
typedef struct {
               s16 timer;
               s16 x;
} ET_MariaTurtleAttack;
typedef struct {
               s16 timer;
               s16 : 16;
               s16 defaultTargetX;
               s16 defaultTargetY;
               s16 angle;
               s16 velocityX;
               Point16 pos1;
               Point16 pos2;
               Point16 pos3;
               Point16 pos4;
               struct Entity* target;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unkB0;
} ET_MariaCardinalCrash;
typedef struct {
               s16 timer;
               s16 : 16;
               s16 opacity;
               s16 nSpawn;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unkB0;
} ET_MariaCardinal;
typedef struct {
               s16 timer;
               s16 y;
               s16 opacity;
               s16 velocity;
               struct Entity* target;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unkB0;
} ET_MariaDragon;
typedef struct {
               s16 timer;
               s16 nBounce;
               s16 : 16;
               s16 unk46;
               s16 opacity;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unkB0;
} ET_MariaCat;
typedef struct {
               s16 timer;
               s16 : 16;
               s16 opacity;
               s16 : 16;
               s16 scale;
               s16 ttl;
               s32 : 32;
               struct Entity* parent;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unkB0;
} ET_MariaDoll;
typedef struct {
               u32 accelY;
               s32 yProximity;
               s32 xProximity;
               s32 unk88;
} ET_BatEnemy;
typedef struct {
               struct Primitive* prim1;
               struct Primitive* unk80;
               s16 unk84[4];
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unk9C;
               s16 unk9E;
               u32 unkA0;
               s16 unkA4;
               s16 unkA6;
} ET_801BC5C0;
typedef struct {
               struct Primitive* prim;
               s16 rotationTimer;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               s16 cameraDistance;
} ET_CutscenePhotograph;
typedef struct {
               struct Primitive* prim;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unk9C;
               s16 unk9E;
               s16 unkA0;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               s16 : 16;
               s16 unkAE;
} ET_ClockTower;
typedef struct {
               struct Primitive* prim;
               s16 unk80;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unk9C;
               s16 unk9E;
               s16 unkA0;
               s16 : 16;
               s16 unkA4;
               s16 unkA6;
               s16 unkA8;
               s16 unkAA;
               s16 : 16;
               s16 unkAE;
} ET_BackgroundVortex;
typedef struct {
               s32 : 32;
               s16 timer;
               s16 : 16;
               s32 spawned;
               struct Entity* parent;
               s16 : 16;
               s16 unk8E;
               s32 isThrown;
} ET_OuijaTable;
typedef struct {
               s16 unk7C;
} ET_FleaMan;
typedef struct {
               s32 : 32;
               s16 timer;
               s16 : 16;
               u8 hopCount;
               u8 tripleFireballCount;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 y;
               struct Primitive* shockwavePrim;
               struct Primitive* deathExplosionPrim;
} ET_Ctulhu;
typedef struct {
               s32 : 32;
               s16 timer;
} ET_GhostEnemySpawner;
typedef struct {
               s32 : 32;
               s16 angle;
               s16 : 16;
               u32 speed;
} ET_GhostEnemy;
typedef struct {
               struct Entity* next;
               s16 timer;
               s16 : 16;
               s16 offsets[26];
} ET_MedusaUnk1A;
typedef struct {
               s16 segmentAngle;
               s16 wavePhase;
               s16 swayIndex;
               s16 waveAmplitude;
               s16 seedTimer;
               s16 timer;
               s16 waveBase;
               s16 hasBeenHit;
               struct Entity* parent;
               s16 recoilAngle;
               s16 : 16;
               s16 blastRadius;
} ET_StoneRose;
typedef struct {
               s32 : 32;
               u8 angle;
               u8 : 8;
               u16 : 16;
               s16 unk84;
} ET_Skelerang;
typedef struct {
               struct Entity* torso;
               struct Entity* foot0;
               struct Entity* foot1;
               struct Entity* foot2;
               struct Entity* foot3;
               s32 : 32;
               s32 : 32;
               s32 unk98;
               u8 unk9C;
               u8 unk9D;
               u8 unk9E;
               u8 unk9F;
               struct Entity* tail;
               struct Entity* activeFoot;
               s32 : 32;
               u8 hitParams;
               u8 hitParams2;
} ET_Diplocephalus;
typedef struct {
               struct Entity* diplo;
               s32 : 32;
               s16 : 16;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               struct Entity* unk90;
               s32 : 32;
               s32 velocityY;
               u8 : 8;
               u8 unk9D;
               u8 unk9E;
               u8 unk9F;
               s32 : 32;
               s32 unkA4;
               s32 unkA8;
               s32 unkAC;
} ET_DiplocephalusBody;
typedef struct {
               struct Entity* diplo;
               struct Entity* tip;
               s16 angle;
               s16 : 16;
               s32 : 32;
               struct Entity* prevPart;
               struct Entity* nextPart;
               s32 velocityX;
               s32 velocityY;
               u8 unk9C;
               u8 unk9D;
               u8 : 8;
               u8 unk9F;
} ET_DiplocephalusTail;
typedef struct {
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 speed;
               s16 angle;
               s16 : 16;
               struct Primitive* unk90;
               s32 : 32;
               s32 : 32;
               u8 unk9C;
} ET_DiplocephalusFireball;
typedef struct {
               struct Entity* unk0;
               s16 unk4;
               s16 unk6;
               Pos unk8;
               RECT* unk10;
} unk_PlatelordStruct;
typedef struct {
               s16 : 16;
               s16 : 16;
               s16 unk80;
               s16 unk82;
               u8 unk84;
               u8 unk85;
               u8 unk86;
               u8 unk87;
               unk_PlatelordStruct unk88;
               unk_PlatelordStruct unk9C;
               s16 unkB0;
} ET_PlateLord;
typedef struct {
               s16 : 16;
               s16 : 16;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s16 unk88;
               s16 unk8A;
               s16 unk8C;
               s16 unk8E;
               s16 unk90;
               s16 : 16;
               s16 unk94;
               s16 unk96;
               s16 unk98;
               s16 : 16;
               u8 unk9C;
               u8 unk9D;
               s16 : 16;
               struct Primitive* unkA0;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 unkAC;
               s16 : 16;
               s16 unkB0;
} ET_PlatelordUnknown;
typedef struct {
               u8 unk7C;
               u8 : 8;
               u16 : 16;
               s16 unk80;
               u16 : 16;
               u16 posX;
               u16 posY;
               u16 unk88;
               s16 unk8A;
} ET_801CE2E0;
typedef struct {
               struct Primitive* prim;
               s16 unk80;
               s16 : 16;
               u8 unk84;
               u8 unk85;
               u8 unk86;
               u8 : 8;
               s16 unk88;
               s16 unk8A;
               u8 unk8C;
               u8 unk8D;
               u8 unk8E;
               u8 unk8F;
               struct Primitive* unk90;
} ET_ArmorLord;
typedef struct {
               struct Primitive* unk7C;
               s16 unk80;
               s16 unk82;
               struct Primitive* unk84;
               struct Primitive* unk88;
               struct Primitive* unk8C;
               struct Primitive* unk90;
               struct Primitive* unk94;
               struct Primitive* unk98;
               s32 unk9C;
               s16 : 16;
               s16 : 16;
               u8 unkA4;
               s8 : 8;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               struct Primitive* unkAC;
} ET_801BA290;
typedef struct {
               u8 unk7C;
               u8 unk7D;
               u8 unk7E;
               u8 unk7F;
               u8 unk80;
} ET_Wereskeleton;
typedef struct {
               u8 timer;
               u8 delay;
               u8 unk7E;
               u8 : 8;
               u32 unk80;
               u8 unk84;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               struct Primitive* prim;
} ET_SwordLord;
typedef struct {
               struct Primitive* unk7C;
               s16 : 16;
               s16 : 16;
               s32 unk84;
               struct Entity* unk88;
               u8 unk8C;
               u8 unk8D;
} ET_801CEB28;
typedef struct {
               u16 timer;
               s16 : 16;
               s16 accelY;
} ET_MedusaHead;
typedef struct {
               struct Primitive* unk7C;
               s16 unk80;
               s16 : 16;
               struct Primitive* unk84;
               s16 unk88;
} ET_801B9304;
typedef struct {
               s32 : 32;
               struct Primitive* unk80;
} ET_801B7188;
typedef struct {
               struct Primitive* unk7C;
               s32 : 32;
               u8 unk84;
               u8 unk85;
               u8 unk86;
               u8 unk87;
               s16 unk88;
               s16 : 16;
               s16 unk8C;
               s16 : 16;
               struct Primitive* unk90;
               u8 unk94;
               u8 unk95;
} ET_801BBD90;
typedef struct {
               s16 unk7C;
               s16 : 16;
               struct Entity* unkEntity;
               u32 unk84;
} ET_SkeletonApe;
typedef struct {
               s16 unk7C;
               s32 unk80;
} ET_SkeletonApeBarrel;
typedef struct {
               s32 : 32;
               s32 : 32;
               s16 unk84;
               s16 unk86;
               s16 unk88;
               s16 : 16;
               u8 unk8C;
               u8 : 8;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 unk94;
               s16 unk96;
} ET_BoneArcher;
typedef struct {
               struct Primitive* unk7C;
               s32 unk80;
} ET_801C10F4;
typedef struct {
               struct Primitive* unk7C;
               SVECTOR unk80;
} ET_801BFB40;
typedef struct {
               u8 unk7C;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u8 unk80;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u8 unk84;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u8 unk88;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u8 unk8C;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u32 unk90;
} ET_SpearGuard;
typedef struct {
               struct Entity* spearGuard;
} ET_ThrownSpear;
typedef struct {
               struct Primitive* unk7C;
               s32 unk80;
               u8 unk84;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               s32 unk88;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unk9C;
} ET_801BDA0C;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s16 unk80;
} ET_801B84E4;
typedef struct {
               u8 unk7C;
               u8 unk7D;
               u8 unk7E;
               u8 unk7F;
               u8 unk80;
               u8 unk81;
} ET_801B87E8;
typedef struct {
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 unk88;
} ET_801BF3F4;
typedef struct {
               struct Primitive* unk7C;
               struct Primitive* unk80;
               u8 unk84;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               s16 unk88[8];
               s32 : 32;
               s32 : 32;
               s16 unkA0;
} ET_801BE2C8;
typedef struct {
               s16 : 16;
               s16 : 16;
               s16 unk80;
} ET_801B9BE4;
typedef struct {
    s16 unk0;
    s16 pad[7];
    struct Entity* unkEntity;
} ET_Chair;
typedef struct {
               struct Primitive* prim;
               u16 timer;
               u16 : 16;
               u8 unk84;
               u8 unk85;
               u8 : 8;
               u8 unk87;
               struct Entity* unk88;
               u16 unk8C;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 unkAC;
               u16 : 16;
               s16 unkB0;
               u16 unkB2;
} ET_LesserDemon;
typedef struct {
               u8 unk7C;
               u8 unk7D;
               u8 : 8;
               u8 : 8;
               u16 unk80;
               u16 unk82;
               s16 unk84;
               s16 unk86;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u8 unkAC;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               s16 unkB0;
} ET_801D4558;
typedef struct {
               s16 timer;
               s16 unk7E;
} ET_801B7D34;
typedef struct {
               s16 pad[3];
               s16 timer;
} ET_Fish;
typedef struct {
               s16 timer;
} ET_Bird;
typedef struct {
               struct Primitive* unk7C;
               u8* unk80;
               s16 unk84;
} ET_Marionette;
typedef struct {
               u16 unk7C;
               u16 unk7E;
               u16 unk80;
               u16 unk82;
               u16 unk84;
               u16 unk86;
               u16 unk88;
} ET_801B6F30;
typedef struct {
               u16 unk7C;
               u16 unk7E;
               u16 unk80;
               u16 unk82;
               u16 unk84;
               u16 unk86;
               u8 unk88[1];
} ET_801B15C0;
typedef struct {
    u16 debugAnimID;
    u16 timer;
    u16 totalHits;
    u16 consecutiveHits;
} ET_LibrarianChair;
typedef struct {
               struct Primitive* unk7C;
               u8 unk80;
               u8 unk81;
               u8 : 8;
               u8 : 8;
               u16 unk84;
               u16 : 16;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               struct Entity* unk9C;
} ET_Mudman;
typedef struct {
               struct Primitive* unk7C;
               s16 unk80;
               s16 unk82;
               s16 unk84;
               s16 unk86;
               s16 unk88;
               s16 unk8A;
               s16 unk8C;
               s16 unk8E;
               u32 unk90;
               u8 unk94;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               s16 : 16;
               s16 : 16;
               SVECTOR unk9C;
               SVECTOR unkA4;
} ET_SpellbookMagicTome;
typedef struct {
               Primitive* prim;
               Primitive* lastPrim;
} ET_LibraryShadow;
typedef struct {
               struct Primitive* unk7C;
               struct Primitive* unk80;
               s16 unk84;
               s16 unk86;
               u8 unk88;
               u8 unk89;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               struct Entity* unk9C;
} ET_Dhuron;
typedef struct {
               u16 unk7C;
               u16 unk7E;
               u8 unk80;
               u8 unk81;
} ET_FlyingZombie;
typedef struct {
               struct Primitive* unk7C;
               s16 unk80;
               s16 unk82;
               s32 unk84;
               s32 unk88;
               s16 unk8C;
               s16 : 16;
               s16 unk90;
               s16 : 16;
               struct Primitive* unk94;
               struct Primitive* unk98;
} ET_801AE8E8;
typedef struct {
               u8 counter;
               u8 counter2;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u8 flag;
} ET_FleaArmor;
typedef struct {
               u16 : 16;
               u16 : 16;
               u16 : 16;
               u16 unk82;
               s16 unk84;
} ET_801B56E4;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               s32 unk84;
               s32 unk88;
               struct Entity* unk8C;
               s16 unk90;
               s16 unk92;
               s16 unk94;
               s16 unk96;
} ET_Ectoplasm;
typedef struct {
               s32 : 32;
               s32 : 32;
               u8 unk84;
} ET_801BB200;
typedef struct {
               Primitive* prim;
               s32 : 32;
               f32 unk84;
               s32 unk88;
               s32 unk8C;
               s32 unk90;
               s32 unk94;
               s32 unk98;
               f32 unk9C;
               f32 unkA0;
} ET_Clouds;
typedef struct {
               Primitive* prim;
               s16 unk80;
} ET_801B8D30;
typedef struct {
               s32 : 32;
               s32 : 32;
               u8 unk84;
} ET_801C0B9C;
typedef struct {
               u32 : 32;
               u32 : 32;
               u8 unk84;
               u32 : 24;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               s16 unk9C;
} ET_unkDoor;
typedef struct {
               u16 unk7C;
               u16 unk7E;
               u8 unk80;
               u8 unk81;
               u8 unk82;
               u8 unk83;
               s16 unk84;
               u16 unk86;
               u16 unk88;
               u16 unk8A;
               u32 unk8C;
               struct Primitive* unk90;
               struct Primitive* unk94;
               s16 unk98;
               s16 : 16;
               u16 unk9C;
               u16 unk9E;
               s16 unkA0;
               s16 unkA2;
               s16 unkA4;
               s16 : 16;
               u8 unkA8[8];
} ET_FrozenShade;
typedef struct {
               u16 unk7C;
               u16 unk7E;
               u16 unk80;
               u16 unk82;
               u16 unk84;
               u16 angle;
               u8 r;
               u8 g;
               u8 b;
               u8 : 8;
               struct Entity* unk8C;
               s16 posX;
               s16 posY;
} ET_FrozenShadeIcicle;
typedef struct {
               u32 : 32;
               Primitive* prim;
               u8 unk84;
} ET_DopplegangerBGLight;
typedef struct {
               s32 : 32;
               s16 lickTimer;
               s16 jumpTimer;
               u8 jumpStep;
               u8 jumpCount;
               s16 : 16;
               struct Entity* tongueEntity;
} ET_FrogToad;
typedef struct {
               struct Primitive* prim;
               s16 attackTimer;
               s16 palette;
               u8 attackTimerIndex;
               u8 playerIsClose;
               u8 isBottomHead;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               struct Entity* fishheadEntity;
} ET_Fishhead;
typedef struct {
               u32 swimTimer;
               u32 swimCount;
} ET_KillerFish;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               u16 unk80;
               s16 : 16;
               s16 : 16;
               s16 : 16;
               s16 origPosX;
               s16 origPosY;
               u16 unk8C;
               s16 : 16;
               s32 unk90;
               s32 unk94;
               s16 newPosX;
               s16 newPosY;
} ET_SurfacingWater;
typedef struct {
               s32 playerInBoat;
               s32 unk80;
               s32 accelerationX;
               s32 : 32;
               s16 : 16;
               u16 splashTimer;
               s32 flags;
               s32 unk94;
} ET_FerrymanBoat;
typedef struct {
               u16 unk7C;
               u16 unk7E;
               u16 unk80;
               s16 unk82;
               s32 unk84;
               s32 unk88;
               s32 unk8C;
               s32 unk90;
               u16 unk94;
               u16 : 16;
               u16 collisionDetected;
               u16 unk9A;
} ET_BoatElevator;
typedef struct {
               s16 unk7C;
               u16 unk7E;
               s32 : 32;
               s16 : 16;
               s16 unk86;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 unk94;
               s16 unk98;
               s16 unk9A;
} ET_BoatElevator_Child;
typedef struct {
               u16 waterHeight;
               struct Entity* entity7E;
               struct Entity* entity82;
               s32 : 32;
               s32 : 32;
               u16 unk8E;
} ET_WaterAlcove;
typedef struct {
               Primitive* prim;
               s16 unk80;
               s16 unk82;
               s32 clut;
} ET_801C12B0;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               s16 : 16;
               u8 attackIntervalIdx;
               u8 bottomDead;
               u8 isBouncing;
               struct Entity* linkEntity;
               s16 pad[19];
               s16 unkB2;
} ET_BonePillar;
typedef struct {
               s16 unk7C;
} ET_801C4520;
typedef struct {
               struct Primitive* prim;
               s16 hoverTimer;
               s16 : 16;
               s32 referenceY;
} ET_Crow;
typedef struct {
               u16 timer;
               s16 posY;
               u16 prevTimer;
} ET_801C4980;
typedef struct {
               struct Entity* unk7C;
               struct Entity* unk80;
} ET_801C5268;
typedef struct {
               s32 : 32;
               s16 unk80;
               s16 : 16;
               s16 unk84;
} ET_ValhallaKnight;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               s16 weaponCount;
               u16 hasWeapons;
               s16 : 16;
               Pos weaponPos;
               s16 angle;
               s16 : 16;
               s16 moveTimer;
               u8 weaponIndex;
               s8 : 8;
               s16 rotX;
               s16 rotY;
               s16 rotateTarget;
               s16 rotate;
               s16 : 16;
               s16 radius;
               s32 pad[2];
               struct Entity* poltergeist;
               u8 unkB0;
} ET_SpectralSword;
typedef struct {
               s32 : 32;
               struct Entity* unk80;
} ET_801CEB08;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s16 unk80;
} ET_801B3F30;
typedef struct {
               s16 unk7C;
} ET_801B4210;
typedef struct {
               s32 : 32;
               u8 unk80;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               s16 unk84;
} ET_Prisoner;
typedef struct {
               s32 : 32;
               u8* animData;
} ET_801B72E8;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               struct Entity* entity;
               u8 unk84;
               u8 unk85;
               u16 : 16;
               s16 unk88;
} ET_FleaRider;
typedef struct {
               u32 : 32;
               s16 timer;
} ET_Tombstone;
typedef struct {
               s32 : 32;
               s32 : 32;
               s32 unk84;
               s32 : 32;
               s16 timer;
} ET_Yorick;
typedef struct {
               s32 : 32;
               s32 : 32;
               s32 unk84;
               u8 unk88;
               u8 unk89;
               u16 : 16;
               s32 : 32;
               s32 : 32;
               u8 unk94;
} ET_YorickSkull;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               s16 unk82;
               s16 unk84;
               s16 : 16;
               s32 : 32;
               u8 unk8C;
               s32 : 24;
               s16 unk90;
} ET_SkullLord;
typedef struct {
               struct Primitive* prim;
               u32 step;
               s32 swingDistance;
               s32 swingVelocity;
               s32 maxSwing;
               s32 pad[3];
               u32 ringTimer;
} ET_Bell;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               s16 : 16;
               s16 numBlades;
               s16 curtainShake;
               s16 activateChime;
} ET_ConfessionalGhost;
typedef struct {
    struct Primitive* prim;
    s16 attackTimer;
    s16 sinePhase;
    u8 brightness;
    u8 attackPatternIdx;
    u8 attacking;
    u8 random;
    s32 : 32;
    s16 nextStep;
    s16 cycleTimer;
    s16 scrollY;
    struct Primitive* spiritPrim;
    struct Primitive* attackPrim;
    u16 attackStep;
    u16 frames;
    s16 rotate;
    s32 attack;
} ET_HuntingGirl;
typedef struct {
               struct Primitive* prim;
               s16 attackInterval;
               s16 : 16;
               u8 prevPlayerOnLeft;
               u8 facingLeft;
} ET_CornerGuard;
typedef struct {
               u8 timer;
               u8 pad0[3];
               u8 facingLeft;
               u8 pad1[3];
               u8 attackIntervalIdx;
               u8 pad2[3];
               u8 partLifespan;
               u8 pad3[3];
               s16 lungeTimer;
} ET_BoneHalberd;
typedef struct {
               struct Primitive* glassPrim;
               struct Primitive* lightPrim;
} ET_StainedGlass;
typedef struct {
               struct Primitive* prim;
               s16 rotate;
               s16 : 16;
               s32 : 32;
               s16 echoCooldown;
} ET_Spikes;
typedef struct {
               struct Primitive* prim;
               struct Primitive* unk80;
               struct Primitive* unk84;
               u8 unk88;
               u8 unk89;
               u8 unk8A;
               u8 unk8B;
               s16 unk8C;
               s16 : 16;
               s16 unk90;
               s16 unk92;
               s16 deathTimer;
               s16 palette;
               s32 : 32;
               u8 unk9C;
               u8 largeSlimePaletteCycle;
               u8 facingLeft;
               u8 dying;
               u8 deathColorCycle;
               u8 largeSlimeDying;
} ET_Slime;
typedef struct {
               struct Primitive* prim;
               u8 thrownDisc;
               u8 angle;
               s16 unk82;
               u32 unk84;
               u32 unk88;
               s16 unk8C;
               s16 unk8E;
               struct Primitive* lastPrim;
               s16 unk94;
               s16 unk96;
               u32 unk98;
               s16 unk9C;
               s16 unk9E;
               struct Primitive* unkA0;
               struct Entity* entity;
               s32 unkA8;
               s32 unkAC;
} ET_DiscusLord;
typedef struct {
               s32 : 32;
               s16 walkTimer;
               s16 unk82;
               u8 kickHitPlayer;
               u8 resetColliderEffects;
} ET_GraveKeeper;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               u16 : 16;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               struct Entity* unk9C;
               struct Primitive* unkA0;
               s16 unkA4;
               u16 : 16;
               struct Entity* lossothEntity;
} ET_Lossoth;
typedef struct {
               struct Primitive* prim;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               struct Primitive* unk9C;
               f32 unkA0;
               u8 paletteOffset;
               u8 unkA5;
} ET_LossothNapalmFlare;
typedef struct {
               struct Primitive* prim;
               struct Primitive* primTwo;
               s16 timer;
               s16 deathPartsRotate;
               u8 attackChoice;
               u8 : 8;
               u16 : 16;
               struct Entity* attackEntity;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               struct Primitive* primThree;
} ET_HellfireBeast;
typedef struct {
               struct Primitive* prim;
               struct Entity* entity;
               s16 castTimer;
               s16 unk86;
               s16 unk88;
               s16 unk8A;
               s32 unk8C;
               s32 unk90;
               u8 unk94;
               u8 : 8;
               u16 : 16;
               u32 : 32;
} ET_HellfireBeastThorsHammer;
typedef struct {
               struct Primitive* prim;
               s16 unk80;
               s16 : 16;
               s16 castTimer;
} ET_HellfireBeastFlamePillar;
typedef struct {
               s16 skeletonPosX;
               s16 skeletonPosY;
               s16 unk80;
               s16 unk82;
               struct Primitive* prim;
               f32 unk88;
               f32 unk8C;
               u8 unk90;
               u8 crouching;
               u8 skeletonDied;
               u8 headDying;
               s16 unk94;
               s16 : 16;
               s32 projectileVelocity;
               struct Entity* entity;
               u8 walkingRight;
} ET_BoneArk;
typedef struct {
               u32 : 32;
               s16 unk80;
               s16 angle;
               u8 unk84;
               u8 : 8;
               s16 unk86;
               s16 unk88;
               s16 timer;
               s32 unk8C;
               s16 unk90;
               s16 unk92;
} ET_Harpy;
typedef struct {
               Primitive* prim;
               s16 timer;
               s16 : 16;
               u16 unk84;
               u8 unk86;
               u8 : 8;
               Pos pos;
               s32 : 32;
               s16 unk94;
               s16 : 16;
               s32 : 32;
               s16 targetDistance;
               s16 unk9E;
               s16 : 16;
               s16 unkA2;
} ET_CloakedKnight;
typedef struct {
               s32 : 32;
               struct Entity* parent;
} ET_CloakedKnightAura;
typedef struct {
               s32 : 32;
               s32 : 32;
               s32 : 32;
               Pos targetPos;
} ET_CloakedKnightSword;
typedef struct {
               Primitive* prim;
               f16 timer;
               s16 collisionHeight;
               s16 unk84;
               s16 unk86;
               s16 unk88;
} ET_SpikeRoomSwitch;
typedef struct {
               Primitive* prim;
               s16 unk80;
               s16 : 16;
               u8 unk84;
} ET_801BA164;
typedef struct {
               s32 : 32;
               u8 playerOnLeft;
} ET_Coffin;
typedef struct {
               Primitive* prim;
               s16 : 16;
               s16 : 16;
               u16 unk84;
               s16 : 16;
               u8 : 8;
               u8 unk89;
               s16 : 16;
               s16 clut;
               s16 : 16;
               Primitive* emberPrim;
} ET_Lava;
typedef struct {
               s32 : 32;
               s16 deathTimer;
               s16 playerStepTowards;
               u8 walkCounter;
               u8 slashInProgress;
} ET_BladeMaster;
typedef struct {
               u8 attackTimer;
               u8 : 8;
               u16 : 16;
               u8 walkDirection;
               u8 : 8;
               u16 : 16;
               u8 attackCount;
               u8 : 8;
               u16 : 16;
               u8 deathPartFallDuration;
               u8 : 8;
               u16 : 16;
               s16 chargeDuration;
               u16 : 16;
               u8* animPtr;
} ET_BladeSoldier;
typedef struct {
               u8 unk7C;
               u8 lastFacingDirection;
               u8 unk7E;
               u8 deathVortexColor;
               Primitive* deathVortexPrim;
               u8 unk84;
               u8 nextAttack;
} ET_Paranthropus;
typedef struct {
               u32 : 32;
               s16 cooldownTimer;
               s16 timer2;
               u8 collision;
               u32 : 24;
               u32 : 32;
               s16 offsetX;
               s16 offsetY;
} ET_GearPuzzle;
typedef struct {
               u32 : 32;
               u32 : 32;
               u8 collision;
               u32 : 24;
               u32 : 32;
               s16 offsetX;
               s16 offsetY;
               u32 : 32;
               s16 chainAngle;
               s16 weightAngle;
} ET_Pendulum;
typedef struct {
               u32 : 32;
               s16 timer;
} ET_ARE_BossDoor;
typedef struct {
               u32 : 32;
               u32 : 32;
               s32 startingPosY;
} ET_StoneSkull;
typedef struct {
               struct Entity* entity;
               u8 unk80;
               u8 unk81;
               u8 angle;
               u8 unk83;
               s16 unk84;
               s16 unk86;
               s32 unk88;
               f32 posX;
               f32 posY;
               s16 attackTimer;
               s16 unk96;
               u8 unk98;
               u8 unk99;
               s16 unk9A;
               u8 unk9C;
               u8 unk9D;
               u8 unk9E;
               u8 unk9F;
               s32 unkA0;
               u8 unkA4;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               struct Primitive* prim;
} ET_WhiteDragon;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               s16 moveTimer;
               u8 moveAway;
               u8 : 8;
               u8 : 8;
               u8 : 8;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               s16 unk9C;
} ET_Werewolf;
typedef struct {
               u32 : 32;
               s16 timer;
               s16 moveTimer;
               s32 deathPuffPosX;
               u32 : 32;
               u8 moveAway;
               u8 : 8;
               u8 : 8;
               u8 : 8;
} ET_Minotaur;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               s16 bodyGlowPhase;
               s32 : 32;
               s32 : 32;
               u8 bodyGlowIntensity;
               u8 attackCounter;
               u8 animIndex;
               u8 : 8;
               struct Primitive* primTwo;
               struct Primitive* primThree;
               s32 lerpT;
               SVECTOR pos;
               SVECTOR offset;
               SVECTOR base;
} ET_Azaghal;
typedef struct {
               s32 : 32;
               s16 timer;
               s16 : 16;
               u8 flag0;
               u8 flag1;
               u8 flag2;
               u8 : 8;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               struct Entity* parent;
               s16 angle;
} ET_Karasuman;
typedef struct {
               s16 playerAngle;
               u16 : 16;
               s32 velocity;
               u8 targetIsLeft;
               u8 timer;
               u16 : 16;
               s16 acceleration;
} ET_PhantomSkull;
typedef struct {
               u8 timer;
               u8 facingLeft;
} ET_FlailGuard;
typedef struct {
               s16 unk7C;
               s16 unk7E;
               s16 unk80;
               s16 : 16;
               struct Primitive* prim;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               s32 prevAttack;
} ET_FlailGuardFlail;
typedef struct {
               s16 : 16;
               s16 unk7E;
               f32 unk80;
               s16 unk84;
               s16 unk86;
} ET_ClockTowerClouds;
typedef struct {
               u32 : 32;
               s16 timer;
               u16 : 16;
               u16 : 16;
               u8 flag;
               u8 : 8;
               u32 : 32;
               u32 : 32;
               s16 angle;
               s16 timer2;
               u32 : 32;
               u32 : 32;
               Primitive* prim;
} ET_VandalSword;
typedef struct {
               s16 : 16;
               s16 unk7E;
               s16 unk80;
               s16 unk82;
               Primitive* unk84;
               s16 unk88;
               s16 unk8A;
               s16 : 16;
               s16 unk8E;
} ET_801BACF4;
typedef struct {
               u32 : 32;
               u16 : 16;
               s16 bobPhase;
               u8 moveLeft;
               u8 thrownObject;
               u8 playerWithinProximity;
               u8 shieldActivated;
               s16 attackTimer;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u32 : 32;
               u8 touchedGround;
               u8 unk9D;
               u8 isDeathCat;
} ET_Salome;
typedef struct {
             s32 : 32;
             s16 timer;
             s16 : 16;
             s16 unk84;
             s16 unk86;
             s16 unk88;
             s16 : 16;
             s32 paletteTimer;
             s16 unk90;
             s16 : 16;
             s32 : 32;
             s32 : 32;
             struct Entity* wheelParent;
} ET_FloorTrap;
typedef struct {
             u32 : 32;
             struct Primitive* prim80;
             struct Primitive* prim84;
             s16 timer;
             u8 palOffMin;
             u8 : 8;
             u32 accelerationY;
             u8 palDirection;
             u8 palTimer;
             u8 pal_offset;
             u8 palOffMax;
             s16 angle;
             u16 zPriority;
             s16 unk98;
             u16 : 16;
    union {
        s16 xVars[2];
        struct Entity* otherEnt;
    } unk9C;
             u8 unkA0;
             struct Primitive* primA4;
} ET_FireDemon;
typedef struct {
    s32 : 32;
    s16 deathTimer;
    s16 angle;
} ET_Bitterfly;
typedef struct {
             s32 : 32;
             s16 timer;
             s16 : 16;
             u32 prevDirsPressed;
             s16 playerJamTimer;
             s16 angle;
             s16 jamOffsetX;
             s16 jamOffsetY;
} ET_Imp;
typedef struct {
               s32 : 32;
               s16 timer;
} ET_801806B0;
typedef struct {
               s32 : 32;
               s16 timer;
               s16 unk82;
               s16 unk84;
               s16 : 16;
               s16 unk88;
               s16 unk8A;
               s32 unk8C;
} ET_BossCoffin;
typedef struct {
               s32 : 32;
               s16 timer;
               s16 : 16;
               s32 : 32;
               s32 : 32;
               s32 unk8C;
} ET_FakeGrant;
typedef struct {
               s32 : 32;
               s16 timer;
               s16 : 16;
               u16 itemEntityId;
               s16 : 16;
               s32 : 32;
               s32 unk8C;
} ET_FakeRalph;
typedef struct {
               s32 : 32;
               s16 timer;
               s16 angle;
               s16 red;
               s16 green;
               s16 blue;
               s16 : 16;
               s32 unk8C;
} ET_FakeSypha;
typedef struct {
               s32 : 32;
               struct AnimateEntityFrame* frames;
               s16 angle;
               s16 : 16;
               u8 unk88;
               u8 unk89;
               s16 : 16;
               u32 unk8C;
} ET_DeathFlames;
typedef struct {
               struct Primitive* prim;
               s16 timer;
               s16 angle;
               u8 moveAwayFromPlayer;
               u8 castBlizzard;
               u8 iciclePositionIdx;
               u8 moveUpwards;
               struct Entity* entity;
               s32 deathPrimCount;
} ET_FrozenHalf;
typedef struct {
               u16 unk7C;
} ET_PlatformUnk;
typedef struct {
               u8 throwTimer;
               s16 : 16;
               u8 movingLeft;
               s16 : 16;
               u8 throwTimerIndex;
               s16 : 16;
               u8 deathPartLife;
               s16 : 16;
               s16 bouncesDone;
} ET_JackOBones;
typedef struct {
               struct Primitive* prim;
               u8 movingLeft;
               u8 cooldown;
               u8 laserTimerIndex;
               u8 deathPartLife;
               s16 : 16;
               s16 laserTimer;
               u8 ringState;
               s16 : 16;
               s16 ringSize;
               s16 ringRot;
               s16 laserLength;
               s16 laserFadeTimer;
               u32 laserPulseDist;
} ET_NovaSkeleton;
typedef struct {
               struct Entity* parent;
               s16 stepTimer;
               s16 : 16;
               u8 movingLeft;
               u8 unk9;
               u8 riderDead;
               u32 gravity;
               s32 : 32;
               s16 targetTimer;
               s16 vel_angle;
               s16 rest_time;
               s16 : 16;
               s16 targetX;
               s16 targetY;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s32 : 32;
               s16 : 16;
               s16 unused_zero;
} ET_Orobourous;
typedef struct {
               s32 : 32;
               s16 timer;
               s16 : 16;
               s16 doubleSpeed;
} ET_Dodo;
typedef union {
    struct Primitive* prim;
    ET_Placeholder ILLEGAL;
    ET_TimerOnly timer;
    ET_UTimerOnly utimer;
    ET_EntFactory factory;
    ET_AfterImage afterImage;
    ET_EntitySlot16 entSlot16;
    ET_Entity13 ent13;
    ET_8011E4BC et_8011E4BC;
    ET_801CC9B4 et_801CC9B4;
    ET_HellfireHandler hellfireHandler;
    ET_8016D9C4 et_8016D9C4;
    ET_ReboundStoneCrashExplosion reboundStoneCrashExplosion;
    ET_CrossBoomerang crossBoomerang;
    ET_Subweapon subweapon;
    ET_HolyWater holywater;
    ET_CrashCross crashcross;
    ET_SubwpnAxe subwpnAxe;
    ET_VibhutiCrash vibhutiCrash;
    ET_VibhutiCrashCloud vibCrashCloud;
    ET_GiantSpinningCross giantcross;
    ET_ReboundStone reboundStone;
    ET_BibleBeam bibleBeam;
    ET_BibleSubwpn et_BibleSubwpn;
    ET_EquipItemDrop equipItemDrop;
    ET_HeartDrop heartDrop;
    ET_BloodDroplets bloodDroplets;
    ET_BloodSplatter bloodSplatter;
    ET_NumericDamage ndmg;
    ET_RelicOrb relicOrb;
    ET_RedDoor redDoor;
    ET_SealedDoor sealedDoor;
    ET_StagePopup stpopup;
    ET_StagePopupJP stpopupj;
    ET_MessageBox messageBox;
    ET_Weapon weapon;
    ET_WeaponUnk006 weapon_006;
    ET_WeaponUnk012 weapon_012;
    ET_WeaponUnk014 weapon_014;
    ET_WeaponUnk016 weapon_016;
    ET_WeaponUnk030 weapon_030;
    ET_WeaponUnk046 weapon_046;
    ET_WeaponUnk047 weapon_047;
    ET_Shield shield;
    ET_DarkShield darkShield;
    ET_KarmaCoin karmacoin;
    ET_Sword sword;
    ET_HeavenSword heavenSword;
    ET_HeavenSword2 heavenSword2;
    ET_MedusaShieldLaser medshieldlaser;
    ET_ShamanShieldStar shamanshieldstar;
    ET_HeraldShieldSwirlEffect heraldSwirl;
    ET_Food food;
    ET_HitByIce hitbyice;
    ET_HitByLightning hitbylightning;
    ET_PlayerBlink playerBlink;
    ET_Mist mist;
    ET_Bat bat;
    ET_BatFamBlueTrail batFamBlueTrail;
    ET_BatEcho batEcho;
    ET_Ghost ghost;
    ET_Faerie faerie;
    ET_FaerieWings faerieWings;
    ET_FaerieItem faerieItem;
    ET_FaerieLifeApple faerieLifeApple;
    ET_Demon demon;
    ET_SwordFamiliar swordFamiliar;
    ET_SoulStealOrb soulStealOrb;
    ET_GaibonSlogra GS_Props;
    ET_WarpRoom warpRoom;
    ET_Teleport teleport;
    ET_Merman merman;
    ET_Merman_2 merman2;
    ET_MermanWaterSplash mermanWaterSplash;
    ET_Agunea agunea;
    ET_801291C4 et_801291C4;
    ET_8017091C et_8017091C;
    ET_AguneaCrash aguneaCrash;
    ET_RICStopWatch ricStopWatch;
    ET_StopwatchCrash stopwatchCrash;
    ET_DRAStopWatch stopwatch;
    ET_stopwatchCircle et_stopwatchCircle;
    ET_stopwatchSparkle et_stopWatchSparkle;
    ET_80162870 et_80162870;
    ET_Whip whip;
    ET_RichterPowerUpRing ricPowerRing;
    ET_TransparentWhiteCircle whiteCircle;
    ET_8016E9E4 et_8016E9E4;
    ET_Dracula dracula;
    ET_DracFinal dracFinalForm;
    ET_Succubus succubus;
    ET_StageTitleCard stageTitleCard;
    ET_RoomTransition2 roomTransition2;
    ET_80192998 e_80192998;
    ET_ExplosionPuffOpaque opaquePuff;
    ET_FireWarg fireWarg;
    ET_FireWargHelper fireWargHelper;
    ET_ShuttingWindow shuttingWindow;
    ET_CastleDoor castleDoor;
    ET_DeathSkySwirl deathSkySwirl;
    ET_Elevator elevator;
    ET_801D0B40 et_801D0B40;
    ET_801D0B78 et_801D0B78;
    ET_WaterEffects waterEffects;
    ET_GurkhaHammer GH_Props;
    ET_TransparentWater transparentWater;
    ET_HeartRoomGoldDoor heartRoomGoldDoor;
    ET_CastleDoorTransition castleDoorTransition;
    ET_AlucardController alucardController;
    ET_FadeToWhite fadeToWhite;
    ET_Death death;
    ET_SpittleBone spittleBone;
    ET_Player player;
    ET_801AF774 et_801AF774;
    ET_BigRedFireball bigredfireball;
    ET_SummonSpirit summonspirit;
    ET_3DBackgroundhouse bghouse;
    ET_LifeUpSpawn lifeUpSpawn;
    ET_AxeKnight axeknight;
    ET_Owl owl;
    ET_AlucardWaterEffect aluwater;
    ET_80123B40 et_80123B40;
    ET_80129864 et_80129864;
    ET_PlayerOutline playerOutline;
    ET_HPNumberMove hpNumMove;
    ET_GuardText guardText;
    ET_Dissolve dissolve;
    ET_LockCamera lockCamera;
    ET_Maria092BEAB0 maria092BEAB0;
    ET_MariaCrashSummon mariaCrashSummon;
    ET_CavernDoor cavernDoor;
    ET_UnkSelEnts unkSelEnts;
    ET_ZombieSpawner zombieSpawner;
    ET_Skeleton skeleton;
    ET_NZ0_311C0 nz0311c0;
    ET_FireWargDeathBeams fireWargDeathBeams;
    ET_ClockRoom clockRoom;
    ET_Birdcage birdcage;
    ET_Statue statue;
    ET_StoneDoor stoneDoor;
    ET_DisableAfterImage disableAfterImage;
    ET_EntityMermanFireSpit EntityMermanFireSpit;
    ET_EntityExplosion3 entityExplosion3;
    ET_BackgroundLightning backgroundLightning;
    ET_DestructAnimation destructAnim;
    ET_SecretStairs secretStairs;
    ET_SubwpnContainerGlass subwpnContGlass;
    ET_BloodyZombie bloodyZombie;
    ET_MermanRock mermanRock;
    ET_Warg warg;
    ET_DeathScythe deathScythe;
    ET_Unused_MAD_ST0 unusedMadST0;
    ET_CEN_Elevator cenElevator;
    ET_TOP_Elevator topElevator;
    ET_ARE_Elevator areElevator;
    ET_BloodSkeleton bloodSkeleton;
    ET_SmallRisingHeart smallRisingHeart;
    ET_EntranceUnk16 entrance16;
    ET_Breakable breakable;
    ET_BreakableDebris breakableDebris;
    ET_BreakableNO2 breakableNo2;
    ET_SegmentedBreakableWall segmentedBreakableWall;
    ET_DemonSwitchWall demonSwitchWall;
    ET_DebugCerberusGate debugCerberusGate;
    ET_FallingStairs fallingStairs;
    ET_SalemWitch salemWitch;
    ET_SalemWitchTribolt salemWitchTribolt;
    ET_Gremlin gremlin;
    ET_GremlinFire gremlinFire;
    ET_Thornweed thornweed;
    ET_Corpseweed corpseweed;
    ET_VenusWeed venusWeed;
    ET_VenusWeedFlower venusWeedFlower;
    ET_VenusWeedTendril venusWeedTendril;
    ET_VenusWeedDart venusWeedDart;
    ET_VenusWeedSpike venusWeedSpike;
    ET_ExpandingCircle circleExpand;
    ET_RicMariaPower ricMariaPower;
    ET_RicMaria ricMaria;
    ET_Maria092BEB40 maria092BEB40;
    ET_MariaOwl mariaOwl;
    ET_MariaTurtleVortex mariaTurtleVortex;
    ET_MariaTurtleCrash mariaTurtleCrash;
    ET_MariaTurtleAttack mariaTurtleAttack;
    ET_MariaCardinalCrash mariaCardinalCrash;
    ET_MariaCardinal mariaCardinal;
    ET_MariaDragon mariaDragon;
    ET_MariaCat mariaCat;
    ET_MariaDoll mariaDoll;
    ET_BatEnemy batEnemy;
    ET_801BC5C0 et_801BC5C0;
    ET_CutscenePhotograph cutscenePhoto;
    ET_ClockTower clockTower;
    ET_BackgroundVortex bgVortex;
    ET_MedusaUnk1A medusaUnk1A;
    ET_OuijaTable ouijaTable;
    ET_FleaMan fleaMan;
    ET_Ctulhu ctulhu;
    ET_StoneRose stoneRose;
    ET_GhostEnemy ghostEnemy;
    ET_GhostEnemySpawner ghostEnemySpawner;
    ET_Skelerang skelerang;
    ET_Diplocephalus diplo;
    ET_DiplocephalusBody diploBody;
    ET_DiplocephalusTail diploTail;
    ET_DiplocephalusFireball diploFireball;
    ET_PlateLord plateLord;
    ET_PlatelordUnknown plateLordUnknown;
    ET_SkeletonApe skeletonApe;
    ET_SkeletonApeBarrel skeletonApeBarrel;
    ET_801CE2E0 et_801CE2E0;
    ET_ArmorLord armorLord;
    ET_801BA290 et_801BA290;
    ET_Wereskeleton wereskeleton;
    ET_SwordLord swordLord;
    ET_801CEB28 et_801CEB28;
    ET_MedusaHead medusaHead;
    ET_801B9304 et_801B9304;
    ET_801B7188 et_801B7188;
    ET_801BBD90 et_801BBD90;
    ET_BoneArcher boneArcher;
    ET_801C10F4 et_801C10F4;
    ET_SpearGuard spearGuard;
    ET_ThrownSpear thrownSpear;
    ET_801B84E4 et_801B84E4;
    ET_801BF3F4 et_801BF3F4;
    ET_801BFB40 et_801BFB40;
    ET_801BDA0C et_801BDA0C;
    ET_801BE2C8 et_801BE2C8;
    ET_801B9BE4 et_801B9BE4;
    ET_Chair chair;
    ET_LesserDemon lesserDemon;
    ET_801D4558 et_801D4558;
    ET_801B7D34 et_801B7D34;
    ET_Fish fish;
    ET_Bird bird;
    ET_Marionette marionette;
    ET_801B6F30 et_801B6F30;
    ET_801B15C0 et_801B15C0;
    ET_Mudman mudman;
    ET_SpellbookMagicTome spellbookMagicTome;
    ET_LibrarianChair libraryChair;
    ET_LibraryShadow libraryShadow;
    ET_Dhuron dhuron;
    ET_FlyingZombie flyingZombie;
    ET_801AE8E8 et_801AE8E8;
    ET_FleaArmor fleaArmor;
    ET_801B56E4 et_801B56E4;
    ET_Ectoplasm ectoplasm;
    ET_801BB200 et_801BB200;
    ET_801B8D30 et_801B8D30;
    ET_Clouds clouds;
    ET_801C0B9C et_801C0B9C;
    ET_unkDoor unkDoor;
    ET_FrozenShade frozenShade;
    ET_FrozenShadeIcicle frozenShadeIcicle;
    ET_DopplegangerBGLight dopBGLight;
    ET_FrogToad frogToad;
    ET_Fishhead fishhead;
    ET_KillerFish killerFish;
    ET_SurfacingWater et_surfacingWater;
    ET_WaterAlcove et_waterAlcove;
    ET_801C12B0 et_801C12B0;
    ET_BonePillar bonePillar;
    ET_801C4520 et_801C4520;
    ET_801C4980 et_801C4980;
    ET_801C5268 et_801C5268;
    ET_Crow crow;
    ET_FerrymanBoat ferrymanBoat;
    ET_BoatElevator boatElevator;
    ET_BoatElevator_Child boatElevator_child;
    ET_ValhallaKnight valhallaKnight;
    ET_SpectralSword spectralSword;
    ET_801CEB08 et_801CEB08;
    ET_801B3F30 et_801B3F30;
    ET_801B4210 et_801B4210;
    ET_Prisoner prisoner;
    ET_801B87E8 et_801B87E8;
    ET_801B72E8 et_801B72E8;
    ET_FleaRider fleaRider;
    ET_Tombstone tombstone;
    ET_Yorick yorick;
    ET_YorickSkull yorickSkull;
    ET_SkullLord skullLord;
    ET_Bell bell;
    ET_ConfessionalGhost confessionalGhost;
    ET_CornerGuard cornerGuard;
    ET_BoneHalberd boneHalberd;
    ET_Spikes spikes;
    ET_HuntingGirl huntingGirl;
    ET_Slime slime;
    ET_StainedGlass stainedGlass;
    ET_DiscusLord discusLord;
    ET_GraveKeeper graveKeeper;
    ET_Lossoth lossoth;
    ET_LossothNapalmFlare lossothNapalm;
    ET_HellfireBeast hellfireBeast;
    ET_HellfireBeastThorsHammer hellfireBeastThorsHammer;
    ET_HellfireBeastFlamePillar hellfireBeastFlamePillar;
    ET_BoneArk boneArk;
    ET_Harpy harpy;
    ET_CloakedKnight cloakedKnight;
    ET_CloakedKnightAura cloakedKnightAura;
    ET_CloakedKnightSword cloakedKnightSword;
    ET_SpikeRoomSwitch spikeRoomSwitch;
    ET_801BA164 et_801BA164;
    ET_Coffin coffin;
    ET_Lava lava;
    ET_BladeMaster bladeMaster;
    ET_BladeSoldier bladeSoldier;
    ET_Paranthropus paranthropus;
    ET_GearPuzzle gearPuzzle;
    ET_Pendulum pendulum;
    ET_ARE_BossDoor areBossDoor;
    ET_StoneSkull stoneSkull;
    ET_WhiteDragon whiteDragon;
    ET_Werewolf werewolf;
    ET_Minotaur minotaur;
    ET_Azaghal azaghal;
    ET_Karasuman karasuman;
    ET_PhantomSkull phantom_skull;
    ET_FlailGuard flailGuard;
    ET_FlailGuardFlail flailGuardFlail;
    ET_ClockTowerClouds clockTowerClouds;
    ET_VandalSword vandalSword;
    ET_801BACF4 et_801BACF4;
    ET_Salome salome;
    ET_FloorTrap floorTrap;
    ET_FireDemon fireDemon;
    ET_Bitterfly bitterfly;
    ET_Imp imp;
    ET_801806B0 et_801806B0;
    ET_BossCoffin bossCoffin;
    ET_FakeRalph ralph;
    ET_FakeGrant grant;
    ET_FakeSypha sypha;
    ET_DeathFlames deathFlames;
    ET_FrozenHalf frozenHalf;
    ET_PlatformUnk platformUnk;
    ET_JackOBones jackoBones;
    ET_NovaSkeleton nova;
    ET_Orobourous orob;
    ET_Dodo dodo;
    ET_B0_Unk b0Unk;
} Ext;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
;
typedef enum {
    PAD_COUNT = 2,
    PAD_NONE = 0x0000,
    BUTTON_COUNT = 8,
    PAD_L2 = 0x0001,
    PAD_R2 = 0x0002,
    PAD_L1 = 0x0004,
    PAD_R1 = 0x0008,
    PAD_TRIANGLE = 0x0010,
    PAD_CIRCLE = 0x0020,
    PAD_CROSS = 0x0040,
    PAD_SQUARE = 0x0080,
    PAD_SELECT = 0x0100,
    PAD_L3 = 0x0200,
    PAD_R3 = 0x0400,
    PAD_START = 0x0800,
    PAD_UP = 0x1000,
    PAD_RIGHT = 0x2000,
    PAD_DOWN = 0x4000,
    PAD_LEFT = 0x8000,
    PAD_BAT = PAD_R1,
    PAD_MIST = PAD_L1,
    PAD_WOLF = PAD_R2,
    PAD_SIM_UNK10000 = 0x10000,
    PAD_SIM_UNK20000 = 0x20000,
    PAD_DIRECTION_MASK = PAD_UP | PAD_RIGHT | PAD_DOWN | PAD_LEFT,
} PlayerPad;
typedef enum Elements {
    ELEMENT_NONE = 0,
    ELEMENT_UNK_1 = 0x1,
    ELEMENT_UNK_2 = 0x2,
    ELEMENT_UNK_4 = 0x4,
    ELEMENT_UNK_8 = 0x8,
    ELEMENT_UNK_10 = 0x10,
    ELEMENT_HIT = 0x20,
    ELEMENT_CUT = 0x40,
    ELEMENT_POISON = 0x80,
    ELEMENT_CURSE = 0x100,
    ELEMENT_STONE = 0x200,
    ELEMENT_WATER = 0x400,
    ELEMENT_DARK = 0x800,
    ELEMENT_HOLY = 0x1000,
    ELEMENT_ICE = 0x2000,
    ELEMENT_THUNDER = 0x4000,
    ELEMENT_FIRE = 0x8000,
    ELEMENT_ALL = ELEMENT_FIRE | ELEMENT_THUNDER | ELEMENT_ICE | ELEMENT_HOLY |
                  ELEMENT_DARK | ELEMENT_WATER | ELEMENT_STONE | ELEMENT_CURSE |
                  ELEMENT_POISON | ELEMENT_CUT | ELEMENT_HIT,
    ELEMENT_UNK_10000 = 0x10000,
} Elements;
typedef enum {
    SBT_DEF,
    SBT_ATK,
    SBT_LCK,
    SBT_INT,
    SBT_STR,
    SBT_RESISTFIRE,
    SBT_RESISTICE,
    SBT_RESISTTHUNDER,
    SBT_RESISTCURSE,
    SBT_RESISTHOLY,
    SBT_RESISTSTONE,
    SBT_RESISTDARK,
} StatBuffTimers;
typedef enum {
    ENTITY_DEFAULT = 0x00,
    ENTITY_SCALEX = 0x01,
    ENTITY_SCALEY = 0x02,
    ENTITY_ROTATE = 0x04,
    ENTITY_OPACITY = 0x08,
    ENTITY_MASK_R = 0x10,
    ENTITY_MASK_G = 0x20,
    ENTITY_MASK_B = 0x40,
    ENTITY_BLINK = 0x80,
} EntityDrawFlags;
typedef enum {
    FLAG_UNK_10 = 0x10,
    FLAG_UNK_20 = 0x20,
    FLAG_UNK_40 = 0x40,
    FLAG_UNK_80 = 0x80,
    FLAG_DEAD = 0x100,
    FLAG_UNK_200 = 0x200,
    FLAG_UNK_400 = 0x400,
    FLAG_UNK_800 = 0x800,
    FLAG_UNK_1000 = 0x1000,
    FLAG_UNK_2000 = 0x2000,
    FLAG_UNK_4000 = 0x4000,
    FLAG_UNK_8000 = 0x8000,
    FLAG_UNK_10000 = 0x10000,
    FLAG_UNK_20000 = 0x20000,
    FLAG_POS_PLAYER_LOCKED = 0x40000,
    FLAG_UNK_80000 = 0x80000,
    FLAG_UNK_100000 = 0x100000,
    FLAG_UNK_00200000 = 0x00200000,
    FLAG_SUPPRESS_STUN = 0x400000,
    FLAG_HAS_PRIMS = 0x800000,
    FLAG_NOT_AN_ENEMY = 0x01000000,
    FLAG_UNK_02000000 = 0x02000000,
    FLAG_KEEP_ALIVE_OFFCAMERA = 0x04000000,
    FLAG_POS_CAMERA_LOCKED = 0x08000000,
    FLAG_UNK_10000000 = 0x10000000,
    FLAG_UNK_20000000 = 0x20000000,
    FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA = 0x40000000,
    FLAG_DESTROY_IF_OUT_OF_CAMERA = 0x80000000,
} EntityFlag;
typedef enum {
    PLAYER_STATUS_BAT_FORM = 0x1,
    PLAYER_STATUS_MIST_FORM = 0x2,
    PLAYER_STATUS_WOLF_FORM = 0x4,
    PLAYER_STATUS_TRANSFORM =
        (PLAYER_STATUS_BAT_FORM | PLAYER_STATUS_MIST_FORM |
         PLAYER_STATUS_WOLF_FORM),
    PLAYER_STATUS_UNK8 = 0x8,
    PLAYER_STATUS_UNK10 = 0x10,
    PLAYER_STATUS_CROUCH = 0x20,
    PLAYER_STATUS_UNK40 = 0x40,
    PLAYER_STATUS_STONE = 0x80,
    PLAYER_STATUS_INVINCIBLE = 0x100,
    PLAYER_STATUS_UNK200 = 0x200,
    PLAYER_STATUS_UNK400 = 0x400,
    PLAYER_STATUS_SUBWPN = 0x800,
    PLAYER_STATUS_SPELLCAST = 0x1000,
    PLAYER_STATUS_UNK2000 = 0x2000,
    PLAYER_STATUS_POISON = 0x4000,
    PLAYER_STATUS_CURSE = 0x8000,
    PLAYER_STATUS_UNK10000 = 0x10000,
    PLAYER_STATUS_UNK20000 = 0x20000,
    PLAYER_STATUS_DEAD = 0x40000,
    PLAYER_STATUS_UNK80000 = 0x80000,
    PLAYER_STATUS_UNK100000 = 0x100000,
    PLAYER_STATUS_UNK200000 = 0x200000,
    PLAYER_STATUS_UNK400000 = 0x400000,
    PLAYER_STATUS_UNK800000 = 0x800000,
    PLAYER_STATUS_AXEARMOR = 0x1000000,
    PLAYER_STATUS_ABSORB_BLOOD = 0x2000000,
    PLAYER_STATUS_UNK4000000 = 0x4000000,
    NO_AFTERIMAGE = 0x8000000,
    PLAYER_STATUS_UNK10000000 = 0x10000000,
    PLAYER_STATUS_UNK20000000 = 0x20000000,
    PLAYER_STATUS_UNK40000000 = 0x40000000,
    PLAYER_STATUS_UNK80000000 = 0x80000000,
} PlayerStateStatus;
typedef enum {
    TOUCHING_GROUND = 1 << 0,
    TOUCHING_CEILING = 1 << 1,
    TOUCHING_R_WALL = 1 << 2,
    TOUCHING_L_WALL = 1 << 3,
    VRAM_FLAG_UNK10 = 1 << 4,
    IN_AIR_OR_EDGE = 1 << 5,
    VRAM_FLAG_UNK40 = 1 << 6,
    VRAM_FLAG_UNK80 = 1 << 7,
    VRAM_FLAG_UNK100 = 1 << 8,
    VRAM_FLAG_UNK200 = 1 << 9,
    VRAM_FLAG_UNK400 = 1 << 10,
    TOUCHING_CEILING_SLOPE = 1 << 11,
    TOUCHING_SLIGHT_SLOPE = 1 << 12,
    VRAM_FLAG_UNK2000 = 1 << 13,
    TOUCHING_RAISING_SLOPE = 1 << 14,
    TOUCHING_ANY_SLOPE = 1 << 15
} PlayerVramFlag;
typedef struct {
                struct DIRENTRY entries[(15)];
                u32 unk258;
                u32 unk25C;
                u32 nBlockUsed;
                s32 nFreeBlock;
                u8 blocks[(15)];
} MemcardInfo;
typedef enum {
    Game_Init,
    Game_Title,
    Game_Play,
    Game_GameOver,
    Game_NowLoading,
    Game_VideoPlayback,
    Game_Unk6,
    Game_PrologueEnd,
    Game_MainMenu,
    Game_Ending,
    Game_Boot,
    Game_99 = 99,
} GameState;
typedef enum {
    Engine_Init,
    Engine_Normal,
    Engine_Menu,
    Engine_3,
    Engine_5 = 5,
    Engine_10 = 10,
    Engine_Map = 20,
    Engine_0x70 = 0x70
} GameEngineStep;
typedef enum {
    WALL_NONE,
    WALL_TOP,
    WALL_LEFT,
    WALL_BOTTOM,
    WALL_RIGHT,
} WallSide;
typedef enum {
    STAGE_NO0 = 0x00,
    STAGE_NO1 = 0x01,
    STAGE_LIB = 0x02,
    STAGE_CAT = 0x03,
    STAGE_NO2 = 0x04,
    STAGE_CHI = 0x05,
    STAGE_DAI = 0x06,
    STAGE_NP3 = 0x07,
    STAGE_CEN = 0x08,
    STAGE_NO4 = 0x09,
    STAGE_ARE = 0x0A,
    STAGE_TOP = 0x0B,
    STAGE_NZ0 = 0x0C,
    STAGE_NZ1 = 0x0D,
    STAGE_WRP = 0x0E,
    STAGE_NO1_ALT = 0x0F,
    STAGE_NO0_ALT = 0x10,
    STAGE_DRE = 0x12,
    STAGE_NZ0_DEMO = 0x13,
    STAGE_NZ1_DEMO = 0x14,
    STAGE_LIB_DEMO = 0x15,
    STAGE_BO7 = 0x16,
    STAGE_MAR = 0x17,
    STAGE_BO6 = 0x18,
    STAGE_BO5 = 0x19,
    STAGE_BO4 = 0x1A,
    STAGE_BO3 = 0x1B,
    STAGE_BO2 = 0x1C,
    STAGE_BO1 = 0x1D,
    STAGE_BO0 = 0x1E,
    STAGE_ST0 = 0x1F,
    STAGE_RNO0 = STAGE_NO0 | 0x20,
    STAGE_RNO1 = STAGE_NO1 | 0x20,
    STAGE_RLIB = STAGE_LIB | 0x20,
    STAGE_RCAT = STAGE_CAT | 0x20,
    STAGE_RNO2 = STAGE_NO2 | 0x20,
    STAGE_RCHI = STAGE_CHI | 0x20,
    STAGE_RDAI = STAGE_DAI | 0x20,
    STAGE_RNO3 = STAGE_NP3 | 0x20,
    STAGE_RCEN = STAGE_CEN | 0x20,
    STAGE_RNO4 = STAGE_NO4 | 0x20,
    STAGE_RARE = STAGE_ARE | 0x20,
    STAGE_RTOP = STAGE_TOP | 0x20,
    STAGE_RNZ0 = STAGE_NZ0 | 0x20,
    STAGE_RNZ1 = STAGE_NZ1 | 0x20,
    STAGE_RWRP = STAGE_WRP | 0x20,
    STAGE_RNZ1_DEMO = 0x35,
    STAGE_RBO8 = 0x36,
    STAGE_RBO7 = 0x37,
    STAGE_RBO6 = 0x38,
    STAGE_RBO5 = 0x39,
    STAGE_RBO4 = 0x3A,
    STAGE_RBO3 = 0x3B,
    STAGE_RBO2 = 0x3C,
    STAGE_RBO1 = 0x3D,
    STAGE_RBO0 = 0x3E,
    STAGE_MAD = 0x40,
    STAGE_NO3 = 0x41,
    STAGE_IWA_LOAD = 0x42,
    STAGE_IGA_LOAD = 0x43,
    STAGE_HAGI_LOAD = 0x44,
    STAGE_SEL = 0x45,
    STAGE_TE1 = 0x46,
    STAGE_TE2 = 0x47,
    STAGE_TE3 = 0x48,
    STAGE_TE4 = 0x49,
    STAGE_TE5 = 0x4A,
    STAGE_TOP_ALT = 0x4B,
    STAGE_EU_WARNING = 0x70,
    STAGE_ENDING = 0xFE,
    STAGE_MEMORYCARD = 0xFF,
} Stages;
typedef enum {
    Play_Reset = 0,
    Play_Init,
    Play_PrepareDemo,
    Play_Default,
    Play_PrepareNextStage,
    Play_LoadStageChr,
    Play_WaitStageChr,
    Play_LoadStageSfx,
    Play_WaitStageSfx,
    Play_LoadStagePrg,
    Play_WaitStagePrg,
    Play_Unk11,
    Play_Unk12,
    Play_Unk13,
    Play_Unk14,
    Play_Unk15,
    Play_16,
    Gameover_Init = 0,
    Gameover_AllocResources,
    Gameover_2,
    Gameover_3,
    Gameover_4,
    Gameover_5,
    Gameover_6,
    Gameover_7,
    Gameover_8,
    Gameover_9,
    Gameover_10,
    Gameover_11,
    Gameover_Alt = 99,
    Gameover_Init_Alt,
    Gameover_AllocResources_Alt,
    Gameover_2_Alt,
    Gameover_3_Alt,
    Gameover_11_Alt = 111,
    NowLoading_2 = 2,
} GameSteps;
typedef enum {
    Demo_None,
    Demo_PlaybackInit,
    Demo_Recording,
    Demo_End,
    Demo_Playback,
} DemoMode;
typedef enum {
    TIMEATTACK_INVALID = -1,
    TIMEATTACK_GET_RECORD,
    TIMEATTACK_SET_RECORD,
    TIMEATTACK_SET_VISITED,
} TimeAttackActions;
typedef enum {
    TIMEATTACK_EVENT_DRACULA_DEFEAT,
    TIMEATTACK_EVENT_OLROX_DEFEAT,
    TIMEATTACK_EVENT_DOPPLEGANGER_10_DEFEAT,
    TIMEATTACK_EVENT_GRANFALOON_DEFEAT,
    TIMEATTACK_EVENT_MINOTAUR_WEREWOLF_DEFEAT,
    TIMEATTACK_EVENT_SCYLLA_DEFEAT,
    TIMEATTACK_EVENT_SLOGRA_GAIBON_DEFEAT,
    TIMEATTACK_EVENT_HYPPOGRYPH_DEFEAT,
    TIMEATTACK_EVENT_BEELZEBUB_DEFEAT,
    TIMEATTACK_EVENT_SUCCUBUS_DEFEAT,
    TIMEATTACK_EVENT_KARASUMAN_DEFEAT,
    TIMEATTACK_EVENT_RALPH_GRANT_SYPHA_DEFEAT,
    TIMEATTACK_EVENT_DEATH_DEFEAT,
    TIMEATTACK_EVENT_CERBERUS_DEFEAT,
    TIMEATTACK_EVENT_SAVE_RICHTER,
    TIMEATTACK_EVENT_MEDUSA_DEFEAT,
    TIMEATTACK_EVENT_THE_CREATURE_DEFEAT,
    TIMEATTACK_EVENT_LESSER_DEMON_DEFEAT,
    TIMEATTACK_EVENT_DOPPLEGANGER_40_DEFEAT,
    TIMEATTACK_EVENT_AKMODAN_II_DEFEAT,
    TIMEATTACK_EVENT_DARKWING_BAT_DEFEAT,
    TIMEATTACK_EVENT_GALAMOTH_DEFEAT,
    TIMEATTACK_EVENT_FINAL_SAVEPOINT,
    TIMEATTACK_EVENT_MEET_DEATH,
    TIMEATTACK_EVENT_GET_HOLYGLASSES,
    TIMEATTACK_EVENT_MEET_MASTER_LIBRARIAN,
    TIMEATTACK_EVENT_FIRST_MARIA_MEET,
    NUM_TIMEATTACK_EVENTS,
    TIMEATTACK_EVENT_UNUSED_28,
    TIMEATTACK_EVENT_UNUSED_29,
    TIMEATTACK_EVENT_UNUSED_30,
    TIMEATTACK_EVENT_UNUSED_31,
    TIMEATTACK_EVENT_END,
    TIMEATTACK_EVENT_INVALID = 0xFF,
} TimeAttackEvents;
struct Entity;
typedef struct {
    f32 posX;
    f32 posY;
} Camera;
typedef struct {
    unsigned char width;
    unsigned char height;
    unsigned short unk2;
    unsigned char data[0];
} ImgSrc;
typedef struct {
               u32 gfxOff;
               u32 ovlOff;
               u32 ovlLen;
               u32 vhOff;
               u32 vhLen;
               u32 vbLen;
               u32 musicId;
               const char* gfxName;
               const char* ovlName;
               char* name;
               u8 unk28;
               s8 seqIdx;
} Lba;
typedef struct {
               s16 cursorX;
               s16 cursorY;
               s16 cursorW;
               s16 cursorH;
               RECT unk1;
               s16 w;
               s16 h;
               s16 unk14;
               s16 unk16;
               s16 otIdx;
               s16 unk1A;
               u8 unk1C;
               u8 unk1D;
} MenuContext;
typedef struct {
              u8 tileLayoutId;
              u8 tilesetId;
              u8 objGfxId;
              u8 objLayoutId;
} RoomLoadDef;
typedef struct {
              u8 left;
              u8 top;
              u8 right;
              u8 bottom;
              RoomLoadDef load;
} RoomHeader;
typedef struct {
              u16 x;
              u16 y;
              u16 roomId;
              u16 unk6;
              u16 stageId;
} RoomTeleport;
typedef struct {
               s32 x;
               s32 y;
               Stages stageId;
               TimeAttackEvents eventId;
               s32 unk10;
} RoomBossTeleport;
typedef struct {
              u16 pressed;
              u16 previous;
              u16 tapped;
              u16 repeat;
} Pad;
typedef struct {
    u16 duration;
    u16 pose;
} AnimationFrame;
typedef struct {
    s8 unk0;
    s8 unk2;
    s8 hitboxWidth;
    s8 hitboxHeight;
} FrameProperty;
typedef struct Entity {
               f32 posX;
               f32 posY;
               s32 velocityX;
               s32 velocityY;
               s16 hitboxOffX;
               s16 hitboxOffY;
               u16 facingLeft;
               u16 palette;
               u8 blendMode;
               u8 drawFlags;
               s16 scaleX;
               s16 scaleY;
               s16 rotate;
               s16 rotPivotX;
               s16 rotPivotY;
               u16 zPriority;
               u16 entityId;
               PfnEntityUpdate pfnUpdate;
               u16 step;
               u16 step_s;
               u16 params;
               u16 entityRoomIndex;
               s32 flags;
               s16 : 16;
               u16 enemyId;
               u16 hitboxState;
               s16 hitPoints;
               s16 attack;
               u16 attackElement;
               u16 hitParams;
               u8 hitboxWidth;
               u8 hitboxHeight;
               u8 hitFlags;
               u8 nFramesInvincibility;
               s16 unk4A;
               AnimationFrame* anim;
               u16 pose;
               s16 poseTimer;
               s16 animSet;
               s16 animCurFrame;
               s16 stunFrames;
               u16 unk5A;
               struct Entity* parent;
               struct Entity* nextPart;
               s32 primIndex;
               u16 unk68;
               u16 hitEffect;
               u8 opacity;
               u8 unk6D[11];
               s32 unk78;
               Ext ext;
               struct Entity* unkB8;
} Entity;
typedef struct {
               u16 animSet;
               u16 zPriority;
               u16 unk5A;
               u16 palette;
               u16 drawFlags;
               u16 blendMode;
               u32 flags;
               u8* animFrames;
} ObjInit;
typedef struct {
               u16 animSet;
               u16 zPriority;
               u8 facingLeft;
               u8 unk5A;
               u16 palette;
               u16 drawFlags;
               u16 blendMode;
               u32 flags;
               u8* animFrames;
} ObjInit2;
typedef struct GpuBuffer {
                  struct GpuBuffer* next;
                  DRAWENV draw;
                  DISPENV disp;
                  DR_ENV env[0x10];
                  u_long ot[0x200];
                  DR_MODE drawModes[0x400];
                  POLY_GT4 polyGT4[0x300];
                  POLY_G4 polyG4[0x100];
                  POLY_GT3 polyGT3[0x30];
                  LINE_G2 lineG2[0x100];
                  SPRT_16 sprite16[0x280];
                  TILE tiles[0x100];
                  SPRT sprite[0x200];
} GpuBuffer;
typedef struct {
               u32 drawModes;
               u32 gt4;
               u32 g4;
               u32 gt3;
               u32 line;
               u32 sp16;
               u32 tile;
               u32 sp;
               u32 env;
} GpuUsage;
typedef enum {
    GFX_BANK_NONE,
    GFX_BANK_4BPP,
    GFX_BANK_8BPP,
    GFX_BANK_16BPP,
    GFX_BANK_COMPRESSED,
} GfxBankKind;
typedef struct {
               u_long* xy;
               u_long* wh;
               u_long* data;
} GfxEntry;
typedef struct {
    GfxBankKind kind;
    GfxEntry entries[0];
} GfxBank;
typedef struct {
              GfxEntry* next;
              u16 kind;
              s16 unk6;
              s16 unk8;
              s16 unkA;
} GfxLoad;
typedef enum EquipKind {
    EQUIP_HAND,
    EQUIP_HEAD,
    EQUIP_ARMOR,
    EQUIP_CAPE,
    EQUIP_ACCESSORY,
    NUM_EQUIP_KINDS,
} EquipKind;
typedef enum {
    DROP_ZIRCON = 360,
    DROP_AQUAMARINE = 361,
    DROP_TURQUOISE = 362,
    DROP_ONYX = 363,
    DROP_GARNET = 364,
    DROP_OPAL = 365,
    DROP_DIAMOND = 366,
} DroppedItem;
typedef enum {
    ITEM_S_SWORD,
    ITEM_SWORD,
    ITEM_THROW_1,
    ITEM_FIST,
    ITEM_CLUB,
    ITEM_TWOHAND,
    ITEM_FOOD,
    ITEM_BOMB,
    ITEM_THROW_2,
    ITEM_SHIELD,
    ITEM_MEDICINE,
    ITEM_END,
} ItemCategory;
typedef enum {
    SUBWPN_NONE,
    SUBWPN_DAGGER,
    SUBWPN_AXE,
    SUBWPN_HOLYWATER,
    SUBWPN_CROSS,
    SUBWPN_BIBLE,
    SUBWPN_STOPWATCH,
    SUBWPN_REBNDSTONE,
    SUBWPN_VIBHUTI,
    SUBWPN_AGUNEA
} SubWpnID;
typedef enum { STAT_STR, STAT_CON, STAT_INT, STAT_LCK } Stats;
typedef struct {
    s32 level;
    s32 exp;
    s32 unk8;
} FamiliarStats;
typedef enum {
    RELIC_SOUL_OF_BAT,
    RELIC_FIRE_OF_BAT,
    RELIC_ECHO_OF_BAT,
    RELIC_FORCE_OF_ECHO,
    RELIC_SOUL_OF_WOLF,
    RELIC_POWER_OF_WOLF,
    RELIC_SKILL_OF_WOLF,
    RELIC_FORM_OF_MIST,
    RELIC_POWER_OF_MIST,
    RELIC_GAS_CLOUD,
    RELIC_CUBE_OF_ZOE,
    RELIC_SPIRIT_ORB,
    RELIC_GRAVITY_BOOTS,
    RELIC_LEAP_STONE,
    RELIC_HOLY_SYMBOL,
    RELIC_FAERIE_SCROLL,
    RELIC_JEWEL_OF_OPEN,
    RELIC_MERMAN_STATUE,
    RELIC_BAT_CARD,
    RELIC_GHOST_CARD,
    RELIC_FAERIE_CARD,
    RELIC_DEMON_CARD,
    RELIC_SWORD_CARD,
    RELIC_JP_0,
    RELIC_JP_1,
    RELIC_HEART_OF_VLAD,
    RELIC_TOOTH_OF_VLAD,
    RELIC_RIB_OF_VLAD,
    RELIC_RING_OF_VLAD,
    RELIC_EYE_OF_VLAD,
    NUM_RELICS,
} RelicIds;
typedef enum {
    SPELL_DARK_METAMORPHOSIS,
    SPELL_SUMMON_SPIRIT,
    SPELL_HELLFIRE,
    SPELL_TETRA_SPIRIT,
    SPELL_WOLF_CHARGE,
    SPELL_SOUL_STEAL,
    SPELL_WING_SMASH,
    SPELL_SWORD_BROTHERS,
    NUM_SPELLS,
} SpellIds;
typedef enum {
    FAM_ABILITY_BAT_ATTACK = 15,
    FAM_ABILITY_GHOST_ATTACK = 17,
    FAM_ABILITY_GHOST_ATTACK_SOULSTEAL,
    FAM_ABILITY_SWORD_UNK19,
    FAM_ABILITY_SWORD_UNK20,
    FAM_ABILITY_DEMON_UNK21,
    FAM_ABILITY_DEMON_UNK22,
    FAM_ABILITY_DEMON_UNK24 = 24,
    FAM_ABILITY_DEMON_UNK25,
    FAM_ABILITY_DEMON_UNK26,
} FamiliarAbilityIds;
typedef enum {
    FAM_STATS_BAT,
    FAM_STATS_GHOST,
    FAM_STATS_FAERIE,
    FAM_STATS_DEMON,
    FAM_STATS_SWORD,
    FAM_STATS_YOUSEI,
    FAM_STATS_NOSE_DEMON,
    NUM_FAMILIARS
} FamiliarStatsIds;
typedef enum {
    FAM_ACTIVE_NONE,
    FAM_ACTIVE_BAT = FAM_STATS_BAT + 1,
    FAM_ACTIVE_GHOST = FAM_STATS_GHOST + 1,
    FAM_ACTIVE_FAERIE = FAM_STATS_FAERIE + 1,
    FAM_ACTIVE_DEMON = FAM_STATS_DEMON + 1,
    FAM_ACTIVE_SWORD = FAM_STATS_SWORD + 1,
    FAM_ACTIVE_YOUSEI = FAM_STATS_YOUSEI + 1,
    FAM_ACTIVE_NOSE_DEMON = FAM_STATS_NOSE_DEMON + 1,
} FamiliarActiveIds;
typedef struct {
                   u8 relics[30];
                   u8 spells[NUM_SPELLS];
                   u8 equipHandCount[169];
                   u8 equipBodyCount[90];
                   u8 equipHandOrder[169];
                   u8 equipBodyOrder[90];
                   char saveName[12];
                   u32 spellsLearnt;
                   s32 hp;
                   s32 hpMax;
                   s32 hearts;
                   s32 heartsMax;
                   s32 mp;
                   s32 mpMax;
                   s32 statsBase[4];
                   s32 statsEquip[4];
                   s32 statsTotal[4];
                   s32 level;
                   u32 exp;
                   s32 gold;
                   s32 killCount;
                   u32 D_80097BF8;
                   u32 subWeapon;
                   u32 equipment[2];
                   u32 wornEquipment[5];
                   u32 attackHands[2];
                   s32 defenseEquip;
                   u16 elementsWeakTo;
                   u16 elementsResist;
                   u16 elementsImmune;
                   u16 elementsAbsorb;
                   s32 timerHours;
                   s32 timerMinutes;
                   s32 timerSeconds;
                   s32 timerFrames;
                   u32 D_80097C40;
                   FamiliarStats statsFamiliars[NUM_FAMILIARS];
} PlayerStatus;
typedef enum {
    FADE_NONE,
    FADE_TO_BLACK,
    FADE_FROM_BLACK,
    FADE_BLUE_TINT,
    FADE_TO_BLACK_FAST,
    FADE_TO_BLACK_SLOW,
    FADE_SHOW_MAP,
    FADE_HIDE_MAP,
} FadeModes;
typedef struct {
                         s32 cursorMain;
                         s32 cursorRelic;
                         s32 cursorEquip;
                         s32 cursorHandEquipType;
                         s32 cursorEquipType[NUM_EQUIP_KINDS - 1];
                         s32 scrollEquipType[NUM_EQUIP_KINDS];
                         s32 cursorSpells;
                         s32 cursorSettings;
                         s32 cursorCloak;
                         s32 cursorButtons;
                         s32 cursorWindowColors;
                         s32 cursorTimeAttack;
} MenuNavigation;
typedef struct {
                            s32 buttonConfig[BUTTON_COUNT];
                            u16 buttonMask[BUTTON_COUNT];
                            s32 timeAttackRecords[TIMEATTACK_EVENT_END];
                            s32 cloakColors[6];
                            s32 windowColors[3];
                            s32 equipOrderTypes[ITEM_END];
                            s32 isCloakLiningReversed;
                            s32 isSoundMono;
                            s32 D_8003CB00;
                            s32 D_8003CB04;
} GameSettings;
typedef struct {
               u8 Magic[2];
               u8 Type;
               u8 BlockEntry;
               char Title[64];
               u8 reserve[28];
               u8 Clut[32];
               u8 Icon[3 * 128];
} MemcardHeader;
typedef struct {
               char name[12];
               s32 level;
               s32 gold;
               s32 playHours;
               s32 playMinutes;
               s32 playSeconds;
               s32 cardIcon;
               u32 endGameFlags;
               s16 stage;
               u16 nRoomsExplored;
               u16 roomX;
               u16 roomY;
               s32 character;
               s32 saveSize;
} SaveInfo;
typedef struct {
                MemcardHeader header;
                SaveInfo info;
                PlayerStatus status;
                MenuNavigation menuNavigation;
                GameSettings settings;
                u8 castleFlags[0x300];
                u8 castleMap[0x800];
                 s32 rng;
} SaveData;
typedef struct {
                   s32 icon[(15)];
                   u32 slot[(15)];
                   u32 stage[(15)];
                   u32 roomX[(15)];
                   u32 roomY[(15)];
                   u32 level[(15)];
                   u32 gold[(15)];
                   u32 nRoomsExplored[(15)];
                   u32 playHours[(15)];
                   u32 playSeconds[(15)];
                   u32 playMinutes[(15)];
                   u32 kind[(15)];
                   u32 character[(15)];
                   char name[(15)][10];
    s32 padding;
} SaveSummary;
typedef struct {
    u_long* vlcbuf[2];
    int vlcid;
    u_short* imgbuf[2];
    int imgid;
    RECT rect[2];
    int rectid;
    RECT slice;
    int isdone;
} DECENV;
typedef struct {
    DECENV dec;
    DISPENV disp;
    DRAWENV draw;
    RECT rect;
    s32 unkFC;
} StreamEnv;
typedef struct {
               u8* gfxPage;
               u8* gfxIndex;
               u8* clut;
               u8* collision;
} TileDefinition;
typedef struct {
               u32 left : 6;
               u32 top : 6;
               u32 right : 6;
               u32 bottom : 6;
               u8 params : 8;
} LayoutRect;
typedef struct {
               u16* layout;
               TileDefinition* tileDef;
               LayoutRect rect;
               u16 zPriority;
               u16 flags;
} LayerDef;
typedef struct {
    LayerDef* fg;
    LayerDef* bg;
} RoomDef;
typedef struct {
               s16 flags;
               s16 offsetx;
               s16 offsety;
               s16 width;
               s16 height;
               s16 clut;
               s16 tileset;
               s16 left;
               s16 top;
               s16 right;
               s16 bottom;
} SpritePart;
typedef struct {
               u16 count;
               SpritePart parts[0];
} SpriteParts;
typedef struct {
               u16 frame;
               s16 pivotX;
               s16 pivotY;
               u16 clut;
} AluFrame;
typedef struct {
                   void (*Update)(void);
                   void (*HitDetection)(void);
                   void (*UpdateRoomPosition)(void);
                   void (*InitRoomEntities)(s32 layoutId);
                   RoomHeader* rooms;
                   SpriteParts** spriteBanks;
                   u_long** cluts;
                   void* objLayoutHorizontal;
                   RoomDef* tileLayers;
                   GfxBank** gfxBanks;
                   void (*UpdateStageEntities)(void);
                   u8** unk2C;
                   u8** unk30;
                   s32* unk34;
                   s32* unk38;
                   void (*StageEndCutScene)(void);
} Overlay;
typedef struct {
                   void (*Update)(void);
                   void (*HitDetection)(void);
                   void (*UpdateRoomPosition)(void);
                   void (*InitRoomEntities)(s32 layoutId);
                   RoomHeader* rooms;
                   SpriteParts** spriteBanks;
                   u_long** cluts;
                   void* objLayoutHorizontal;
                   RoomDef* tileLayers;
                   GfxBank** gfxBanks;
                   void (*UpdateStageEntities)(void);
} AbbreviatedOverlay;
typedef struct {
                   void (*Update)(void);
                   void (*HitDetection)(void);
                   void (*UpdateRoomPosition)(void);
                   void (*InitRoomEntities)(s32 layoutId);
                   RoomHeader* rooms;
                   SpriteParts** spriteBanks;
                   u_long** cluts;
                   void* objLayoutHorizontal;
                   RoomDef* tileLayers;
                   GfxBank** gfxBanks;
                   void (*UpdateStageEntities)(void);
                   u8** unk2C;
                   u8** unk30;
} AbbreviatedOverlay2;
typedef enum {
    EFFECT_NONE = 0,
    EFFECT_SOLID = 1 << 0,
    EFFECT_UNK_0002 = 1 << 1,
    EFFECT_QUICKSAND = 1 << 2,
    EFFECT_WATER = 1 << 3,
    EFFECT_MIST_ONLY = 1 << 4,
    EFFECT_UNK_0020 = 1 << 5,
    EFFECT_SOLID_FROM_ABOVE = 1 << 6,
    EFFECT_SOLID_FROM_BELOW = 1 << 7,
    EFFECT_UNK_0100 = 1 << 8,
    EFFECT_UNK_0200 = 1 << 9,
    EFFECT_UNK_0400 = 1 << 10,
    EFFECT_UNK_0800 = 1 << 11,
    EFFECT_UNK_1000 = 1 << 12,
    EFFECT_UNK_2000 = 1 << 13,
    EFFECT_UNK_4000 = 1 << 14,
    EFFECT_UNK_8000 = 1 << 15,
    EFFECT_NOTHROUGH = EFFECT_SOLID | EFFECT_QUICKSAND,
    EFFECT_NOTHROUGH_PLUS = EFFECT_SOLID | EFFECT_UNK_0002 | EFFECT_QUICKSAND,
    EFFECT_UNK_C000 = EFFECT_UNK_8000 | EFFECT_UNK_4000
} ColliderEffectFlags;
typedef struct Collider {
               u32 effects;
               s32 unk4;
               s32 unk8;
               s32 unkC;
               s32 unk10;
               s32 unk14;
               s32 unk18;
               s32 unk1C;
               s32 unk20;
} Collider;
typedef struct XaMusicConfig {
    u32 cd_addr;
    s32 unk228;
    u8 filter_file;
    u8 filter_channel_id;
    u8 volume;
    u8 unk22f;
    u32 unk230;
} XaMusicConfig;
typedef struct {
               u8 vabid;
               u8 prog;
               u8 note;
               s8 volume;
               u8 mode;
               u8 tone;
               u8 unk6;
} Unkstruct_800BF554;
typedef struct {
               const char* name;
               s16 hitPoints;
               s16 attack;
               u16 attackElement;
               s16 defense;
               u16 hitboxState;
               u16 weaknesses;
               u16 strengths;
               u16 immunes;
               u16 absorbs;
               u16 level;
               u16 exp;
               u16 rareItemId;
               u16 uncommonItemId;
               u16 rareItemDropRate;
               u16 uncommonItemDropRate;
               u8 hitboxWidth;
               u8 hitboxHeight;
               s32 flags;
} EnemyDef;
typedef struct {
               s16 attack;
               s16 heartCost;
               u16 attackElement;
               u8 chainLimit;
               u8 nFramesInvincibility;
               u16 stunFrames;
               u8 anim;
               u8 blueprintNum;
               u16 hitboxState;
               u16 hitEffect;
               u8 crashId;
               u8 unk11;
               u16 entityRoomIndex;
} SubweaponDef;
typedef struct {
               const char* name;
               const char* description;
               s16 attack;
               s16 defense;
               u16 element;
               u8 itemCategory;
               u8 weaponId;
               u8 palette;
               u8 unk11;
               u8 playerAnim;
               u8 unk13;
               u8 unk14;
               u8 lockDuration;
               u8 chainLimit;
               u8 unk17;
               u8 specialMove;
               u8 isConsumable;
               u8 enemyInvincibilityFrames;
               u8 unk1B;
               u32 comboSub;
               u32 comboMain;
               u16 mpUsage;
               u16 stunFrames;
               u16 hitType;
               u16 hitEffect;
               u16 icon;
               u16 iconPalette;
               u16 criticalRate;
} Equipment;
typedef struct {
               const char* name;
               const char* description;
               s16 attBonus;
               s16 defBonus;
               u8 statsBonus[4];
               u16 weakToElements;
               u16 resistElements;
               u16 immuneElements;
               u16 absorbElements;
               u16 icon;
               u16 iconPalette;
               u16 equipType;
} Accessory;
typedef struct {
               const char* name;
               const char* combo;
               char* description;
               u8 mpUsage;
               u8 nFramesInvincibility;
               u16 stunFrames;
               u16 hitboxState;
               u16 hitEffect;
               u16 entityRoomIndex;
               u16 attackElement;
               s16 attack;
} SpellDef;
typedef struct {
               const char* name;
               char* desc;
               u16 icon;
               u16 iconPalette;
               s32 unk0C;
} RelicDesc;
typedef enum {
    DAMAGEKIND_0,
    DAMAGEKIND_1,
    DAMAGEKIND_2,
    DAMAGEKIND_3,
    DAMAGEKIND_4,
    DAMAGEKIND_5,
    DAMAGEKIND_6,
    DAMAGEKIND_7,
    DAMAGEKIND_8,
    DAMAGEKIND_9,
    DAMAGEKIND_10,
    DAMAGEKIND_11,
    DAMAGEKIND_12,
    DAMAGEKIND_13,
    DAMAGEKIND_14,
    DAMAGEKIND_15,
    DAMAGEKIND_16,
    DAMAGEKIND_17,
    DAMAGEKIND_18,
} DamageKind;
typedef struct {
    u32 effects;
    u32 damageKind;
    s32 damageTaken;
    u32 unkC;
} DamageParam;
typedef struct {
                   Overlay o;
                   void (*FreePrimitives)(s32);
                   s16 (*AllocPrimitives)(PrimitiveType type, s32 count);
                   void (*CheckCollision)(s32 x, s32 y, Collider* res, s32 unk);
                   void (*func_80102CD8)(s32 arg0);
                   u32 (*UpdateAnim)(
        FrameProperty* frameProps, AnimationFrame** anims);
                   void (*SetSpeedX)(s32 value);
                   Entity* (*GetFreeEntity)(s16 start, s16 end);
                   void (*GetEquipProperties)(
        s32 handId, Equipment* res, s32 equipId);
                   s32 (*func_800EA5E4)(u32);
                   void (*LoadGfxAsync)(s32 gfxId);
                   void (*PlaySfx)(s32 sfxId);
                   s16 (*func_800EDB58)(u8, s32);
                   void (*func_800EA538)(s32 arg0);
                   void (*func_800EA5AC)(u32 a, u32 r, u32 g, u32 b);
                   void (*SetFadeMode)(FadeModes fadeMode);
                   void (*func_800EB758)(
        s16 pivotX, s16 pivotY, Entity* e, u16 flags, POLY_GT4* p, u16 flipX);
                   Entity* (*CreateEntFactoryFromEntity)(
        Entity* self, u32 flags, s32 arg2);
                   bool (*func_80131F68)(void);
                   DR_ENV* (*func_800EDB08)(POLY_GT4* poly);
                   u16* (*func_80106A28)(u32 arg0, u16 kind);
                   void (*func_80118894)(Entity*);
                   EnemyDef* enemyDefs;
                   Entity* (*func_80118970)(void);
                   s16 (*func_80118B18)(
        Entity* ent1, Entity* ent2, s32 facingLeft);
                   s32 (*UpdateUnarmedAnim)(s8* frameProps, u16** frames);
                   void (*PlayAnimation)(s8*, AnimationFrame** frames);
                   void (*func_80118C28)(s32 arg0);
                   void (*func_8010E168)(s32 arg0, s16 arg1);
                   void (*func_8010DFF0)(s32 arg0, s32 arg1);
                   u16 (*DealDamage)(
        Entity* enemyEntity, Entity* attackerEntity);
                   void (*LoadEquipIcon)(s32 equipIcon, s32 palette, s32 index);
                   Equipment* equipDefs;
                   Accessory* accessoryDefs;
                   void (*AddHearts)(s32 value);
                   bool (*LoadMonsterLibrarianPreview)(s32 monsterId);
                   s32 (*TimeAttackController)(
        TimeAttackEvents eventId, TimeAttackActions action);
                   void (*ForceAfterImageOn)(void);
                   s32 (*func_800FE044)(s32, s32);
                   void (*AddToInventory)(u32 id, EquipKind kind);
                   RelicDesc* relicDefs;
                   void (*InitStatsAndGear)(bool debugMode);
                   s32 (*PlaySfxVolPan)(s32 sfxId, s32 sfxVol, s32 sfxPan);
                   s32 (*SetVolumeCommand22_23)(s32 vol, s32 distance);
                   void (*MakeAll)(void);
                   u32 (*CheckEquipmentItemCount)(u32 itemId, u32 equipType);
                   void (*GetPlayerSensor)(Collider* col);
                   void (*RevealSecretPassageAtPlayerPositionOnMap)(s32 arg0);
                   void (*func_800F2288)(s32 arg0);
                   void (*GetServantStats)(
        Entity* entity, s32 spellId, s32 arg2, FamiliarStats* out);
                   s32 (*func_800FF460)(s32 arg0);
                   s32 (*func_800FF494)(EnemyDef* arg0);
                   bool (*CdSoundCommandQueueEmpty)(void);
                   bool (*func_80133950)(void);
                   bool (*func_800F27F4)(s32 arg0);
                   s32 (*GetStatBuffTimer)(s32 arg0);
                   s32 (*func_800FD664)(s32 arg0);
                   bool (*CalcPlayerDamage)(DamageParam* damageParam);
                   void (*LearnSpell)(s32 spellId);
                   void (*DebugInputWait)(const char* str);
                   int (*CalcDealDamageMaria)(s32 baseAttack);
                   bool (*CalcPlayerDamageMaria)(DamageParam* damageParam);
                   u16* (*func_psp_0913FA28)(u32 ch, u16 kind);
                   u16 (*func_psp_0913F960)(char*, u8* ch);
                   void* unused13C;
} GameApi;
typedef struct {
    u8 childId;
    u8 unk1;
    u8 unk2;
    u8 unk3;
    u8 unk4;
    u8 unk5;
} FactoryBlueprint;
typedef struct {
               u8 count;
               u8 r;
               u8 g;
               u8 b;
               u8 w;
               u8 h;
               s16 priority;
               s16 drawMode;
               s16 unkA;
               u32 flags;
} unkStr_8011E4BC;
typedef struct {
    void (*D_8013C000)(void);
    void (*D_8013C004)(u16 params);
    void (*D_8013C008)(void);
    void (*GetPlayerSensor)(Collider* col);
    u8** sprites0;
    u8** sprites1;
    u8** sprites2;
    u8** sprites3;
} PlayerOvl;
extern PlayerOvl g_PlOvl;
extern u8** g_PlOvlAluBatSpritesheet[1];
extern u8* g_PlOvlSpritesheet[];
extern void (*g_api_FreePrimitives)(s32);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
extern void (*g_api_CheckCollision)(s32 x, s32 y, Collider* res, s32 unk);
extern void (*g_api_func_80102CD8)(s32 arg0);
extern void (*g_api_UpdateAnim)(
    FrameProperty* frameProps, AnimationFrame** anims);
extern void (*g_api_SetSpeedX)(s32 value);
extern Entity* (*g_api_GetFreeEntity)(s16 start, s16 end);
extern void (*g_api_GetEquipProperties)(
    s32 handId, Equipment* res, s32 equipId);
extern s32 (*g_api_func_800EA5E4)(u32);
extern void (*g_api_LoadGfxAsync)(s32 gfxId);
extern void (*g_api_PlaySfx)(s32 sfxId);
extern s16 (*g_api_func_800EDB58)(s32, s32);
extern void (*g_api_func_800EA538)(s32 arg0);
extern void (*g_api_func_800EA5AC)(u32 a, u32 r, u32 g, u32 b);
extern Entity* (*g_api_CreateEntFactoryFromEntity)(
    Entity* self, u32 flags, s32 arg2);
extern bool (*g_api_func_80131F68)(void);
extern DR_ENV* (*g_api_func_800EDB08)(POLY_GT4* poly);
extern u16* (*g_api_func_80106A28)(u32 arg0, u16 kind);
extern void (*g_api_func_80118894)(Entity*);
extern EnemyDef* g_api_enemyDefs;
extern s32 (*g_api_UpdateUnarmedAnim)(s8* frameProps, u16** frames);
extern void (*g_api_PlayAnimation)(s8*, AnimationFrame** frames);
extern void (*g_api_func_8010E168)(s32 arg0, s16 arg1);
extern void (*g_api_func_8010DFF0)(s32 arg0, s32 arg1);
extern u16 (*g_api_DealDamage)(Entity* enemyEntity, Entity* attackerEntity);
extern void (*g_api_LoadEquipIcon)(s32 equipIcon, s32 palette, s32 index);
extern Equipment* g_api_equipDefs;
extern Accessory* g_api_accessoryDefs;
extern void (*g_api_AddHearts)(s32 value);
extern s32 (*g_api_TimeAttackController)(
    TimeAttackEvents eventId, TimeAttackActions action);
extern void (*g_api_ForceAfterImageOn)(void);
extern s32 (*g_api_func_800FE044)(s32, s32);
extern void (*g_api_AddToInventory)(u32 id, EquipKind kind);
extern RelicDesc* g_api_relicDefs;
extern s32 (*g_api_PlaySfxVolPan)(s32 sfxId, s32 sfxVol, s32 sfxPan);
extern s32 (*g_api_SetVolumeCommand22_23)(s32 vol, s32 distance);
extern void (*g_api_MakeAll)(void);
extern u32 (*g_api_CheckEquipmentItemCount)(u32 itemId, u32 equipType);
extern void (*g_api_GetPlayerSensor)(Collider* col);
extern void (*g_api_RevealSecretPassageAtPlayerPositionOnMap)(s32 arg0);
extern void (*g_api_func_800F2288)(s32 arg0);
extern void (*g_api_GetServantStats)(
    Entity* entity, s32 spellId, s32 arg2, FamiliarStats* out);
extern s32 (*g_api_func_800FF460)(s32 arg0);
extern s32 (*g_api_func_800FF494)(EnemyDef* arg0);
extern bool (*g_api_CdSoundCommandQueueEmpty)(void);
extern bool (*g_api_func_80133950)(void);
extern bool (*g_api_func_800F27F4)(s32 arg0);
extern s32 (*g_api_GetStatBuffTimer)(s32 arg0);
extern s32 (*g_api_func_800FD664)(s32 arg0);
extern bool (*g_api_CalcPlayerDamage)(DamageParam* damageParam);
extern void (*g_api_LearnSpell)(s32 spellId);
extern void (*g_api_DebugInputWait)(const char* str);
typedef struct {
               u16** frames;
               s8* frameProps;
               u16 palette;
               u16 soundId;
               u8 frameStart;
               u8 soundFrame;
               s16 unused;
} WeaponAnimation;
typedef struct {
                        u16* layout;
                        TileDefinition* tileDef;
                        f32 scrollX;
                        f32 scrollY;
                        u32 unused10;
                        u32 unused14;
                        u32 order;
                        u32 flags;
                        u32 w;
                        u32 h;
                        u32 hideTimer;
                        u32 scrollKind;
} BgLayer;
typedef struct {
                   u16* fg;
                   TileDefinition* tileDef;
                   f32 scrollX;
                   f32 scrollY;
                   s32 unused10;
                   s32 unused14;
                   s32 order;
                   u32 flags;
                   u32 hSize;
                   u32 vSize;
                   u32 hideTimer;
                   s32 left;
                   s32 top;
                   s32 right;
                   s32 bottom;
                   s32 x;
                   s32 y;
                   s32 width;
                   s32 height;
                   s32 unk30;
                   s32 D_800730D4;
} Tilemap;
typedef struct {
                     u16 flags;
                     u16 unk2;
                     u16 unk4;
                     s16 zPriority;
} FgLayer;
typedef struct {
                     u32 flags;
                     u32 zPriority;
} FgLayer32;
enum AluTimers {
    ALU_T_POISON,
    ALU_T_CURSE,
    ALU_T_HITEFFECT,
    ALU_T_3,
    ALU_T_4,
    ALU_T_5,
    ALU_T_6,
    ALU_T_7,
    ALU_T_8,
    ALU_T_9,
    ALU_T_USE_SUBWPN,
    ALU_T_DARKMETAMORPH,
    ALU_T_USE_SPELL,
    ALU_T_INVINCIBLE,
    ALU_T_INVINCIBLE_CONSUMABLES,
    ALU_T_15,
};
typedef struct {
                       Collider colFloor[4];
                        Collider colCeiling[4];
                         Collider colWall[7 * 2];
                         u32 padPressed;
                         u32 padTapped;
                         u32 padHeld;
                         u32 padSim;
                         u32 D_80072EF8;
                         s32 demo_timer;
                         s16 timers[16];
                         s32 vram_flag;
                         s32 unk04;
                         s32 unk08;
                         PlayerStateStatus status;
                         s32 unk10;
                         u32 unk14;
                         s32 unk18;
                         s32 warp_flag;
                         s32 unk20;
                         u32 unk24;
                         PfnEntityUpdate unk28;
                         s32 unk2C;
                         s32 unk30;
                         s32 unk34;
                         s32 unk38;
                         s32 unk3C;
                         u16 damagePalette;
                         u16 high_jump_timer;
                         u16 unk44;
                         u16 unk46;
                         u16 unk48;
                         s16 unk4A;
                         u16 unk4C;
                         u16 unk4E;
                         u16 prev_step;
                         u16 prev_step_s;
                         u16 unk54;
                         u16 unk56;
                         u16 unk58;
                         u16 damageTaken;
                         u16
        unk5C;
                         u16 unk5E;
                         u16 unk60;
                         u16 unk62;
                         u16 unk64;
                         u16 unk66;
                         u16 unk68;
                         u16 unk6A;
                         u16 unk6C;
                         u16 unk6E;
                         u16 unk70;
                         u16 unk72;
                         u32 unk74;
                         u16 unk78;
                         u16 unk7A;
                         u16 unk7C;
                         u16 unk7E;
} PlayerState;
typedef struct {
               RECT rect0;
               RECT rect1;
               RECT rect2;
               u8 r0;
               u8 b0;
               u8 g0;
               u8 enableColorBlend;
               u8 r1;
               u8 b1;
               u8 g1;
               u8 tpage;
               u8 r2;
               u8 b2;
               u8 g2;
               u8 flipX;
               u8 r3;
               u8 b3;
               u8 g3;
               u8 unk27;
} PlayerDraw;
typedef struct {
    s16 buttonsCorrect;
    s16 timer;
} ButtonComboState;
typedef struct {
    s16 curFrame;
    s16 drawFlags;
    u16 palette;
    s16 enabled;
} DebugInfo;
typedef struct {
                     s32 primIndex;
                     s32 D_800973FC;
                     bool pauseEnemies;
                     s32 unk4;
                     s32 g_zEntityCenter;
                     s32 unkC;
                     s32 BottomCornerTextTimer;
                     s32 BottomCornerTextPrims;
                     s32 unk18;
                     s32 unk1C;
                     s32 unk20;
                     s32 unk24;
                     s32 D_80097428[8];
                     s32 D_80097448;
                     s32 D_8009744C;
                     s32 D_80097450;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     s32 : 32;
                     f32 shoveX;
                     f32 shoveY;
} unkGraphicsStruct;
typedef struct {
    RECT D_800ACD80;
    RECT D_800ACD88;
    RECT D_800ACD90;
    RECT D_800ACD98;
    RECT D_800ACDA0;
    RECT D_800ACDA8;
    RECT D_800ACDB0;
    RECT D_800ACDB8;
    RECT D_800ACDC0;
    RECT D_800ACDC8;
    RECT D_800ACDD0;
    RECT D_800ACDD8;
    RECT D_800ACDE0;
    RECT D_800ACDE8;
    RECT D_800ACDF0;
} Vram;
typedef struct {
               u_long* desc;
               u_long* data;
               u16 unk8;
               u16 index;
               u16 unkC;
               u16 unkE;
               u8 unkArray[0x30];
} Unkstruct_8006C3C4;
extern s32 D_8003925C;
extern s32 g_GameClearFlag;
extern s32 D_8003C0EC[4];
extern s32 D_8003C100;
extern u16 g_ClutIds[];
extern s32 g_CutsceneHasControl;
extern FgLayer D_8003C708;
extern s16 D_8003C710;
extern s16 D_8003C712;
extern s32 D_8003C728;
extern s32 D_8003C730;
extern GameState g_GameState;
extern s32 D_8003C738;
extern s32 D_8003C73C;
extern u32 D_8003C744;
extern u32 g_RoomCount;
extern Vram g_Vram;
extern GameApi g_api;
extern bool g_PauseAllowed;
extern u32 g_GameTimer;
extern bool D_8003C908;
extern s32 g_EquippedWeaponIds[2];
extern u32 g_Timer;
extern s16* D_92641C8[];
extern s32 g_MapCursorTimer;
                 extern s32 g_PlayableCharacter;
                 extern u32 g_GameEngineStep;
                 extern MenuNavigation g_MenuNavigation;
                 extern GameSettings g_Settings;
extern GpuBuffer g_GpuBuffers[2];
extern s16 g_GpuBuffers_1_buf_draw_clip_y;
extern const char g_MemcardSavePath[];
extern const char aBaslus00067dra[19];
extern const char g_strMemcardRootPath[];
extern s32 g_LoadFile;
extern s32 D_8006BB00;
extern u8 g_CastleMap[0x800];
extern s32 D_8006C374;
extern s32 D_8006C378;
extern GpuBuffer* g_CurrentBuffer;
extern Point32 D_8006C384;
extern Point32 D_8006C38C;
extern u32 g_CdStep;
extern s32 D_8006C3AC;
extern s32 g_backbufferX;
extern s32 g_backbufferY;
extern s32 g_IsUsingCd;
extern Entity* g_CurrentEntity;
extern Unkstruct_8006C3C4 D_8006C3C4[32];
extern s32 g_Servant;
extern u16 g_Clut[3][0x1000];
extern PlayerState g_Player;
extern GfxLoad g_GfxLoad[0x10];
extern u32 g_GameStep;
extern s32 g_ServantLoaded;
extern Event g_EvSwCardEnd;
extern Event g_EvSwCardErr;
extern Event g_EvSwCardTmo;
extern s32 g_PrevScrollX;
extern Event g_EvSwCardNew;
extern s32 g_PrevScrollY;
extern s32 D_80073080;
extern Tilemap g_Tilemap;
extern BgLayer g_BgLayers[16];
typedef enum {
    E_AFTERIMAGE_1 = 1,
    E_AFTERIMAGE_2,
    E_AFTERIMAGE_3,
    UNK_ENTITY_4,
    UNK_ENTITY_5,
    UNK_ENTITY_6,
    UNK_ENTITY_7,
    UNK_ENTITY_8,
    E_WEAPON = 0x10,
    UNK_ENTITY_11 = 0x11,
    UNK_ENTITY_12 = 0x12,
    UNK_ENTITY_13 = 0x13,
    UNK_ENTITY_20 = 0x20,
    E_BOSS_WEAPON = 0x50,
    UNK_ENTITY_51 = 0x51,
    UNK_ENTITY_100 = 0x100
} EntityTypes;
extern Entity g_Entities[256];
extern Event g_EvHwCardEnd;
extern Event g_EvHwCardErr;
extern Event g_EvHwCardTmo;
extern Event g_EvHwCardNew;
extern u8 g_Pix[4][128 * 128 / 2];
extern Primitive g_PrimBuf[0x500];
extern s32 g_PlayerX;
extern s32 g_PlayerY;
extern u32 g_randomNext;
extern s32 D_80096ED8[];
extern s32 D_800973EC;
extern unkGraphicsStruct g_unkGraphicsStruct;
extern Pad g_pads[PAD_COUNT];
extern Stages g_StageId;
extern s32 D_800974A4;
extern DR_ENV D_800974AC[16];
extern s32 g_UseDisk;
extern s32 D_800978B4;
extern s32 D_800978C4;
extern u32 g_MenuStep;
extern s32 D_80097904;
extern s32 g_ScrollDeltaX;
extern s32 g_ScrollDeltaY;
extern s32 currentMusicId;
extern DemoMode g_DemoMode;
extern s32 g_LoadOvlIdx;
extern Point32 D_8009791C;
extern s32 D_80097924;
extern s32 stopMusicFlag;
extern GpuUsage g_GpuUsage;
extern PlayerStatus g_Status;
extern u32 D_80097C98;
extern s32 subWeapon;
extern s32 D_80097C40[];
extern PlayerDraw g_PlayerDraw[0x10];
extern bool g_InvincibleFlag;
extern s32 D_800987B4;
extern StHEADER* D_800987C8;
extern s32 g_DebugPlayer;
extern s32 D_80098894;
typedef enum {
    LANG_JP,
    LANG_EN,
    LANG_FR,
    LANG_SP,
    LANG_GE,
    LANG_IT,
} Language;
extern s32 D_psp_08B42044;
extern u32 g_ConfirmButton;
extern u32 g_CancelButton;
extern s32 g_UserLanguage;
extern char* D_psp_08B42060;
extern s32 g_VoiceLanguage;
extern bool D_psp_08C62AA4;
extern bool g_InfiniteHearts;
extern bool g_UnlockAllTactics;
extern s32 D_psp_08C630D4;
extern s32 D_psp_08C630D8;
extern s32 D_psp_08C630DC;
extern u8 D_psp_08D39D3C[];
extern u_long D_psp_08D6DC40;
void func_psp_0891CEB8(s32, s32);
void func_psp_0892667C(s32 paletteID, u16* palette);
float func_psp_089260AC(float);
float func_psp_089260D0(float);
u8* GetLangAt(s32 idx, u8* en, u8* fr, u8* sp, u8* ge, u8* it);
typedef enum {
    PAL_NULL = 0x0,
    PAL_ALUCARD = 0x100,
    PAL_ALUCARD_RED_OUTLINE,
    PAL_ALUCARD_BLUE_OUTLINE_MASK,
    PAL_ALUCARD_GRAY_OUTLINE_MASK,
    PAL_ALUCARD_WOLF,
    PAL_PLAYER_HIDDEN = 0x10D,
    PAL_UNK_110 = 0x110,
    PAL_UNK_111 = 0x111,
    PAL_UNK_117 = 0x117,
    PAL_RICHTER = 0x120,
    PAL_UNK_128 = 0x128,
    PAL_UNK_12F = 0x12F,
    PAL_UNK_138 = 0x138,
    PAL_UNK_13C = 0x13C,
    PAL_UNK_13D = 0x13D,
    PAL_SERVANT = 0x140,
    PAL_RIC_WHIP = 0x140,
    PAL_UNK_143 = 0x143,
    PAL_UNK_148 = 0x148,
    PAL_UNK_149 = 0x149,
    PAL_UNK_14E = 0x14E,
                PAL_FILL_YELLOW = 0x158,
                PAL_FILL_ORANGE,
                PAL_FILL_PURPLE,
                PAL_FILL_BLUE,
                PAL_FILL_GREEN,
                PAL_FILL_RED,
                PAL_FILL_BLACK,
                PAL_FILL_WHITE,
                PAL_CC_FIRE_EFFECT,
                PAL_CC_STONE_EFFECT,
                PAL_CC_MAGIC_HUD_EFFECT,
                PAL_CC_CRITICAL_EFFECT,
                PAL_CC_DARK_EFFECT,
                PAL_CC_CURSE_EFFECT,
                PAL_CC_RED_EFFECT_A,
                PAL_CC_YELLOW_EFFECT,
                PAL_CC_GREEN_EFFECT_A,
                PAL_CC_BLUE_EFFECT_A,
                PAL_CC_PURPLE_EFFECT_A,
                PAL_CC_TURQUOISE_EFFECT,
                PAL_CC_PURPLE_EFFECT_B,
                PAL_CC_RED_EFFECT_B,
                PAL_CC_GREEN_EFFECT_B,
                PAL_CC_BLUE_EFFECT_B,
    PAL_UNK_170 = 0x170,
    PAL_UNK_190 = 0x190,
    PAL_UNK_191 = 0x191,
    PAL_UNK_194 = 0x194,
    PAL_UNK_195 = 0x195,
    PAL_UNK_196 = 0x196,
    PAL_UNK_197 = 0x197,
    PAL_UNK_198 = 0x198,
    PAL_UNK_199 = 0x199,
    PAL_UNK_19C = 0x19C,
    PAL_UNK_19D = 0x19D,
    PAL_UNK_19E = 0x19E,
    PAL_UNK_19F = 0x19F,
    PAL_UNK_1B0 = 0x1B0,
    PAL_UNK_1B1 = 0x1B1,
    PAL_UNK_1B2 = 0x1B2,
    PAL_UNK_1B3 = 0x1B3,
    PAL_UNK_1B4 = 0x1B4,
    PAL_UNK_1B5 = 0x1B5,
    PAL_UNK_1B6 = 0x1B6,
    PAL_UNK_1B7 = 0x1B7,
    PAL_UNK_1B8 = 0x1B8,
    PAL_UNK_1BA = 0x1BA,
    PAL_UNK_1A1 = 0x1A1,
    PAL_UNK_1AB = 0x1AB,
    PAL_UNK_1AE = 0x1AE,
    PAL_UNK_1AF = 0x1AF,
    PAL_UNK_1CF = 0x1CF,
    PAL_UNK_1F3 = 0x1F3,
} PaletteIndices;
typedef enum ItemSlots {
    LEFT_HAND_SLOT,
    RIGHT_HAND_SLOT,
    HEAD_SLOT,
    ARMOR_SLOT,
    CAPE_SLOT,
    ACCESSORY_1_SLOT,
    ACCESSORY_2_SLOT,
    NUM_ITEM_SLOTS,
} ItemSlots;
typedef enum HandItems {
                ITEM_EMPTY_HAND,
                ITEM_MONSTER_VIAL_1,
                ITEM_MONSTER_VIAL_2,
                ITEM_MONSTER_VIAL_3,
                ITEM_SHIELD_ROD,
                ITEM_LEATHER_SHIELD,
                ITEM_KNIGHT_SHIELD,
                ITEM_IRON_SHIELD,
                ITEM_AXELORD_SHIELD,
                ITEM_HERALD_SHIELD,
                ITEM_DARK_SHIELD,
                ITEM_GODDESS_SHIELD,
                ITEM_SHAMAN_SHIELD,
                ITEM_MEDUSA_SHIELD,
                ITEM_SKULL_SHIELD,
                ITEM_FIRE_SHIELD,
                ITEM_ALUCARD_SHIELD,
                ITEM_SWORD_OF_DAWN,
                ITEM_BASILARD,
                ITEM_SHORT_SWORD,
                ITEM_COMBAT_KNIFE,
                ITEM_NUNCHAKU,
                ITEM_WERE_BANE,
                ITEM_RAPIER,
                ITEM_KARMA_COIN,
                ITEM_MAGIC_MISSILE,
                ITEM_RED_RUST,
                ITEM_TAKEMITSU,
                ITEM_SHOTEL,
                ITEM_ORANGE,
                ITEM_APPLE,
                ITEM_BANANA,
                ITEM_GRAPES,
                ITEM_STRAWBERRY,
                ITEM_PINEAPPLE,
                ITEM_PEANUTS,
                ITEM_TOADSTOOL,
                ITEM_SHIITAKE,
                ITEM_CHEESECAKE,
                ITEM_SHORTCAKE,
                ITEM_TART,
                ITEM_PARFAIT,
                ITEM_PUDDING,
                ITEM_ICE_CREAM,
                ITEM_FRANKFURTER,
                ITEM_HAMBURGER,
                ITEM_PIZZA,
                ITEM_CHEESE,
                ITEM_HAM_AND_EGGS,
                ITEM_OMELETTE,
                ITEM_MORNING_SET,
                ITEM_LUNCH_A,
                ITEM_LUNCH_B,
                ITEM_CURRY_RICE,
                ITEM_GYROS_PLATE,
                ITEM_SPAGHETTI,
                ITEM_GRAPE_JUICE,
                ITEM_BARLEY_TEA,
                ITEM_GREEN_TEA,
                ITEM_NATOU,
                ITEM_RAMEN,
                ITEM_MISO_SOUP,
                ITEM_SUSHI,
                ITEM_PORK_BUN,
                ITEM_RED_BEAN_BUN,
                ITEM_CHINESE_BUN,
                ITEM_DIM_SUM_SET,
                ITEM_POT_ROAST,
                ITEM_SIRLOIN,
                ITEM_TURKEY,
                ITEM_MEAL_TICKET,
                ITEM_NEUTRON_BOMB,
                ITEM_POWER_OF_SIRE,
                ITEM_PENTAGRAM,
                ITEM_BAT_PENTAGRAM,
                ITEM_SHURIKEN,
                ITEM_CROSS_SHURIKEN,
                ITEM_BUFFALO_STAR,
                ITEM_FLAME_STAR,
                ITEM_TNT,
                ITEM_BWAKA_KNIFE,
                ITEM_BOOMERANG,
                ITEM_JAVELIN,
                ITEM_TYRFING,
                ITEM_NAMAKURA,
                ITEM_KNUCKLE_DUSTER,
                ITEM_GLADIUS,
                ITEM_SCIMITAR,
                ITEM_CUTLASS,
                ITEM_SABER,
                ITEM_FALCHION,
                ITEM_BROADSWORD,
                ITEM_BEKATOWA,
                ITEM_DAMASCUS_SWORD,
                ITEM_HUNTER_SWORD,
                ITEM_ESTOC,
                ITEM_BASTARD_SWORD,
                ITEM_JEWEL_KNUCKLES,
                ITEM_CLAYMORE,
                ITEM_TALWAR,
                ITEM_KATANA,
                ITEM_FLAMBERGE,
                ITEM_IRON_FIST,
                ITEM_ZWEIHANDER,
                ITEM_SWORD_OF_HADOR,
                ITEM_LUMINUS,
                ITEM_HARPER,
                ITEM_OBSIDIAN_SWORD,
                ITEM_GRAM,
                ITEM_JEWEL_SWORD,
                ITEM_MORMEGIL,
                ITEM_FIREBRAND,
                ITEM_THUNDERBRAND,
                ITEM_ICEBRAND,
                ITEM_STONE_SWORD,
                ITEM_HOLY_SWORD,
                ITEM_TERMINUS_EST,
                ITEM_MARSIL,
                ITEM_DARK_BLADE,
                ITEM_HEAVEN_SWORD,
                ITEM_FIST_OF_TULKAS,
                ITEM_GURTHANG,
                ITEM_MOURNEBLADE,
                ITEM_ALUCARD_SWORD,
                ITEM_MABLUNG_SWORD,
                ITEM_BADELAIRE,
                ITEM_SWORD_FAMILIAR,
                ITEM_GREAT_SWORD,
                ITEM_MACE,
                ITEM_MORNINGSTAR,
                ITEM_HOLY_ROD,
                ITEM_STAR_FLAIL,
                ITEM_MOON_ROD,
                ITEM_CHAKRAM,
                ITEM_FIRE_BOOMERANG,
                ITEM_IRON_BALL,
                ITEM_HOLBEIN_DAGGER,
                ITEM_BLUE_KNUCKLES,
                ITEM_DYNAMITE,
                ITEM_OSAFUNE_KATANA,
                ITEM_MASAMUNE,
                ITEM_MURAMASA,
                ITEM_HEART_REFRESH,
                ITEM_RUNESWORD,
                ITEM_ANTIVENOM,
                ITEM_UNCURSE,
                ITEM_LIFE_APPLE,
                ITEM_HAMMER,
                ITEM_STR_POTION,
                ITEM_LUCK_POTION,
                ITEM_SMART_POTION,
                ITEM_ATTACK_POTION,
                ITEM_SHIELD_POTION,
                ITEM_RESIST_FIRE,
                ITEM_RESIST_THUNDER,
                ITEM_RESIST_ICE,
                ITEM_RESIST_STONE,
                ITEM_RESIST_HOLY,
                ITEM_RESIST_DARK,
                ITEM_POTION,
                ITEM_HIGH_POTION,
                ITEM_ELIXIR,
                ITEM_MANNA_PRISM,
                ITEM_VORPAL_BLADE,
                ITEM_CRISSAEGRIM,
                ITEM_YASUTSUNA,
                ITEM_LIBRARY_CARD,
                ITEM_ALUCART_SHIELD,
                ITEM_ALUCART_SWORD,
                NUM_HAND_ITEMS,
} HandItems;
typedef enum BodyItems {
               ITEM_NO_ARMOR,
               ITEM_CLOTH_TUNIC,
               ITEM_HIDE_CUIRASS,
               ITEM_BRONZE_CUIRASS,
               ITEM_IRON_CUIRASS,
               ITEM_STEEL_CUIRASS,
               ITEM_SILVER_PLATE,
               ITEM_GOLD_PLATE,
               ITEM_PLATINUM_MAIL,
               ITEM_DIAMOND_PLATE,
               ITEM_FIRE_MAIL,
               ITEM_LIGHTNING_MAIL,
               ITEM_ICE_MAIL,
               ITEM_MIRROR_CUIRASS,
               ITEM_SPIKE_BREAKER,
               ITEM_ALUCARD_MAIL,
               ITEM_DARK_ARMOR,
               ITEM_HEALING_MAIL,
               ITEM_HOLY_MAIL,
               ITEM_WALK_ARMOR,
               ITEM_BRILLIANT_MAIL,
               ITEM_MOJO_MAIL,
               ITEM_FURY_PLATE,
               ITEM_DRACULA_TUNIC,
               ITEM_GODS_GARB,
               ITEM_AXE_LORD_ARMOR,
               ITEM_EMPTY_HEAD,
               ITEM_SUNGLASSES,
               ITEM_BALLROOM_MASK,
               ITEM_BANDANNA,
               ITEM_FELT_HAT,
               ITEM_VELVET_HAT,
               ITEM_GOGGLES,
               ITEM_LEATHER_HAT,
               ITEM_HOLY_GLASSES,
               ITEM_STEEL_HELM,
               ITEM_STONE_MASK,
               ITEM_CIRCLET,
               ITEM_GOLD_CIRCLET,
               ITEM_RUBY_CIRCLET,
               ITEM_OPAL_CIRCLET,
               ITEM_TOPAZ_CIRCLET,
               ITEM_BERYL_CIRCLET,
               ITEM_CAT_EYE_CIRCLET,
               ITEM_CORAL_CIRCLET,
               ITEM_DRAGON_HELM,
               ITEM_SILVER_CROWN,
               ITEM_WIZARD_HAT,
               ITEM_NO_CAPE,
               ITEM_CLOTH_CAPE,
               ITEM_REVERSE_CLOAK,
               ITEM_ELVEN_CLOAK,
               ITEM_CRYSTAL_CLOAK,
               ITEM_ROYAL_CLOAK,
               ITEM_BLOOD_CLOAK,
               ITEM_JOSEPHS_CLOAK,
               ITEM_TWILIGHT_CLOAK,
               ITEM_NO_ACCESSORY,
               ITEM_MOONSTONE,
               ITEM_SUNSTONE,
               ITEM_BLOODSTONE,
               ITEM_STAUROLITE,
               ITEM_RING_OF_PALES,
               ITEM_ZIRCON,
               ITEM_AQUAMARINE,
               ITEM_TURQUOISE,
               ITEM_ONYX,
               ITEM_GARNET,
               ITEM_OPAL,
               ITEM_DIAMOND,
               ITEM_LAPIS_LAZULI,
               ITEM_RING_OF_ARES,
               ITEM_GOLD_RING,
               ITEM_SILVER_RING,
               ITEM_RING_OF_VARDA,
               ITEM_RING_OF_ARCANA,
               ITEM_MYSTIC_PENDANT,
               ITEM_HEART_BROACH,
               ITEM_NECKLACE_OF_J,
               ITEM_GAUNTLET,
               ITEM_ANKH_OF_LIFE,
               ITEM_RING_OF_FEANOR,
               ITEM_MEDAL,
               ITEM_TALISMAN,
               ITEM_DUPLICATOR,
               ITEM_KINGS_STONE,
               ITEM_COVENANT_STONE,
               ITEM_NAUGLAMIR,
               ITEM_SECRET_BOOTS,
               ITEM_ALUCART_MAIL,
               NUM_BODY_ITEMS,
} BodyItems;
typedef enum ItemDrops {
               ITEMDROP_SMALL_HEART,
               ITEMDROP_LARGE_HEART,
               ITEMDROP_GOLD_1,
               ITEMDROP_GOLD_2,
               ITEMDROP_GOLD_3,
               ITEMDROP_GOLD_4,
               ITEMDROP_GOLD_5,
               ITEMDROP_GOLD_6,
               ITEMDROP_GOLD_7,
               ITEMDROP_GOLD_8,
               ITEMDROP_GOLD_9,
               ITEMDROP_GOLD_10,
               ITEMDROP_HEART_VESSEL,
               ITEMDROP_DUMMY,
               ITEMDROP_SUBWEAPON_1,
               ITEMDROP_SUBWEAPON_2,
               ITEMDROP_SUBWEAPON_3,
               ITEMDROP_SUBWEAPON_4,
               ITEMDROP_SUBWEAPON_5,
               ITEMDROP_SUBWEAPON_6,
               ITEMDROP_SUBWEAPON_7,
               ITEMDROP_SUBWEAPON_8,
               ITEMDROP_SUBWEAPON_9,
               ITEMDROP_LIFE_VESSEL,
               ITEMDROP_EMPTY_HAND = 0x80,
               ITEMDROP_MONSTER_VIAL_1,
               ITEMDROP_MONSTER_VIAL_2,
               ITEMDROP_MONSTER_VIAL_3,
               ITEMDROP_SHIELD_ROD,
               ITEMDROP_LEATHER_SHIELD,
               ITEMDROP_KNIGHT_SHIELD,
               ITEMDROP_IRON_SHIELD,
               ITEMDROP_AXELORD_SHIELD,
               ITEMDROP_HERALD_SHIELD,
               ITEMDROP_DARK_SHIELD,
               ITEMDROP_GODDESS_SHIELD,
               ITEMDROP_SHAMAN_SHIELD,
               ITEMDROP_MEDUSA_SHIELD,
               ITEMDROP_SKULL_SHIELD,
               ITEMDROP_FIRE_SHIELD,
               ITEMDROP_ALUCARD_SHIELD,
               ITEMDROP_SWORD_OF_DAWN,
               ITEMDROP_BASILARD,
               ITEMDROP_SHORT_SWORD,
               ITEMDROP_COMBAT_KNIFE,
               ITEMDROP_NUNCHAKU,
               ITEMDROP_WERE_BANE,
               ITEMDROP_RAPIER,
               ITEMDROP_KARMA_COIN,
               ITEMDROP_MAGIC_MISSILE,
               ITEMDROP_RED_RUST,
               ITEMDROP_TAKEMITSU,
               ITEMDROP_SHOTEL,
               ITEMDROP_ORANGE,
               ITEMDROP_APPLE,
               ITEMDROP_BANANA,
               ITEMDROP_GRAPES,
               ITEMDROP_STRAWBERRY,
               ITEMDROP_PINEAPPLE,
               ITEMDROP_PEANUTS,
               ITEMDROP_TOADSTOOL,
               ITEMDROP_SHIITAKE,
               ITEMDROP_CHEESECAKE,
               ITEMDROP_SHORTCAKE,
               ITEMDROP_TART,
               ITEMDROP_PARFAIT,
               ITEMDROP_PUDDING,
               ITEMDROP_ICE_CREAM,
               ITEMDROP_FRANKFURTER,
               ITEMDROP_HAMBURGER,
               ITEMDROP_PIZZA,
               ITEMDROP_CHEESE,
               ITEMDROP_HAM_AND_EGGS,
               ITEMDROP_OMELETTE,
               ITEMDROP_MORNING_SET,
               ITEMDROP_LUNCH_A,
               ITEMDROP_LUNCH_B,
               ITEMDROP_CURRY_RICE,
               ITEMDROP_GYROS_PLATE,
               ITEMDROP_SPAGHETTI,
               ITEMDROP_GRAPE_JUICE,
               ITEMDROP_BARLEY_TEA,
               ITEMDROP_GREEN_TEA,
               ITEMDROP_NATOU,
               ITEMDROP_RAMEN,
               ITEMDROP_MISO_SOUP,
               ITEMDROP_SUSHI,
               ITEMDROP_PORK_BUN,
               ITEMDROP_RED_BEAN_BUN,
               ITEMDROP_CHINESE_BUN,
               ITEMDROP_DIM_SUM_SET,
               ITEMDROP_POT_ROAST,
               ITEMDROP_SIRLOIN,
               ITEMDROP_TURKEY,
               ITEMDROP_MEAL_TICKET,
               ITEMDROP_NEUTRON_BOMB,
               ITEMDROP_POWER_OF_SIRE,
               ITEMDROP_PENTAGRAM,
               ITEMDROP_BAT_PENTAGRAM,
               ITEMDROP_SHURIKEN,
               ITEMDROP_CROSS_SHURIKEN,
               ITEMDROP_BUFFALO_STAR,
               ITEMDROP_FLAME_STAR,
               ITEMDROP_TNT,
               ITEMDROP_BWAKA_KNIFE,
               ITEMDROP_BOOMERANG,
               ITEMDROP_JAVELIN,
               ITEMDROP_TYRFING,
               ITEMDROP_NAMAKURA,
               ITEMDROP_KNUCKLE_DUSTER,
               ITEMDROP_GLADIUS,
               ITEMDROP_SCIMITAR,
               ITEMDROP_CUTLASS,
               ITEMDROP_SABER,
               ITEMDROP_FALCHION,
               ITEMDROP_BROADSWORD,
               ITEMDROP_BEKATOWA,
               ITEMDROP_DAMASCUS_SWORD,
               ITEMDROP_HUNTER_SWORD,
               ITEMDROP_ESTOC,
               ITEMDROP_BASTARD_SWORD,
               ITEMDROP_JEWEL_KNUCKLES,
               ITEMDROP_CLAYMORE,
               ITEMDROP_TALWAR,
               ITEMDROP_KATANA,
               ITEMDROP_FLAMBERGE,
               ITEMDROP_IRON_FIST,
               ITEMDROP_ZWEIHANDER,
               ITEMDROP_SWORD_OF_HADOR,
               ITEMDROP_LUMINUS,
               ITEMDROP_HARPER,
               ITEMDROP_OBSIDIAN_SWORD,
               ITEMDROP_GRAM,
               ITEMDROP_JEWEL_SWORD,
               ITEMDROP_MORMEGIL,
               ITEMDROP_FIREBRAND,
               ITEMDROP_THUNDERBRAND,
               ITEMDROP_ICEBRAND,
               ITEMDROP_STONE_SWORD,
               ITEMDROP_HOLY_SWORD,
               ITEMDROP_TERMINUS_EST,
               ITEMDROP_MARSIL,
               ITEMDROP_DARK_BLADE,
               ITEMDROP_HEAVEN_SWORD,
               ITEMDROP_FIST_OF_TULKAS,
               ITEMDROP_GURTHANG,
               ITEMDROP_MOURNEBLADE,
               ITEMDROP_ALUCARD_SWORD,
               ITEMDROP_MABLUNG_SWORD,
               ITEMDROP_BADELAIRE,
               ITEMDROP_SWORD_FAMILIAR,
               ITEMDROP_GREAT_SWORD,
                ITEMDROP_MACE,
                ITEMDROP_MORNINGSTAR,
                ITEMDROP_HOLY_ROD,
                ITEMDROP_STAR_FLAIL,
                ITEMDROP_MOON_ROD,
                ITEMDROP_CHAKRAM,
                ITEMDROP_FIRE_BOOMERANG,
                ITEMDROP_IRON_BALL,
                ITEMDROP_HOLBEIN_DAGGER,
                ITEMDROP_BLUE_KNUCKLES,
                ITEMDROP_DYNAMITE,
                ITEMDROP_OSAFUNE_KATANA,
                ITEMDROP_MASAMUNE,
                ITEMDROP_MURAMASA,
                ITEMDROP_HEART_REFRESH,
                ITEMDROP_RUNESWORD,
                ITEMDROP_ANTIVENOM,
                ITEMDROP_UNCURSE,
                ITEMDROP_LIFE_APPLE,
                ITEMDROP_HAMMER,
                ITEMDROP_STR_POTION,
                ITEMDROP_LUCK_POTION,
                ITEMDROP_SMART_POTION,
                ITEMDROP_ATTACK_POTION,
                ITEMDROP_SHIELD_POTION,
                ITEMDROP_RESIST_FIRE,
                ITEMDROP_RESIST_THUNDER,
                ITEMDROP_RESIST_ICE,
                ITEMDROP_RESIST_STONE,
                ITEMDROP_RESIST_HOLY,
                ITEMDROP_RESIST_DARK,
                ITEMDROP_POTION,
                ITEMDROP_HIGH_POTION,
                ITEMDROP_ELIXIR,
                ITEMDROP_MANNA_PRISM,
                ITEMDROP_VORPAL_BLADE,
                ITEMDROP_CRISSAEGRIM,
                ITEMDROP_YASUTSUNA,
                ITEMDROP_LIBRARY_CARD,
                ITEMDROP_ALUCART_SHIELD,
                ITEMDROP_ALUCART_SWORD,
                ITEMDROP_NO_ARMOR,
                ITEMDROP_CLOTH_TUNIC,
                ITEMDROP_HIDE_CUIRASS,
                ITEMDROP_BRONZE_CUIRASS,
                ITEMDROP_IRON_CUIRASS,
                ITEMDROP_STEEL_CUIRASS,
                ITEMDROP_SILVER_PLATE,
                ITEMDROP_GOLD_PLATE,
                ITEMDROP_PLATINUM_MAIL,
                ITEMDROP_DIAMOND_PLATE,
                ITEMDROP_FIRE_MAIL,
                ITEMDROP_LIGHTNING_MAIL,
                ITEMDROP_ICE_MAIL,
                ITEMDROP_MIRROR_CUIRASS,
                ITEMDROP_SPIKE_BREAKER,
                ITEMDROP_ALUCARD_MAIL,
                ITEMDROP_DARK_ARMOR,
                ITEMDROP_HEALING_MAIL,
                ITEMDROP_HOLY_MAIL,
                ITEMDROP_WALK_ARMOR,
                ITEMDROP_BRILLIANT_MAIL,
                ITEMDROP_MOJO_MAIL,
                ITEMDROP_FURY_PLATE,
                ITEMDROP_DRACULA_TUNIC,
                ITEMDROP_GODS_GARB,
                ITEMDROP_AXE_LORD_ARMOR,
                ITEMDROP_EMPTY_HEAD,
                ITEMDROP_SUNGLASSES,
                ITEMDROP_BALLROOM_MASK,
                ITEMDROP_BANDANNA,
                ITEMDROP_FELT_HAT,
                ITEMDROP_VELVET_HAT,
                ITEMDROP_GOGGLES,
                ITEMDROP_LEATHER_HAT,
                ITEMDROP_HOLY_GLASSES,
                ITEMDROP_STEEL_HELM,
                ITEMDROP_STONE_MASK,
                ITEMDROP_CIRCLET,
                ITEMDROP_GOLD_CIRCLET,
                ITEMDROP_RUBY_CIRCLET,
                ITEMDROP_OPAL_CIRCLET,
                ITEMDROP_TOPAZ_CIRCLET,
                ITEMDROP_BERYL_CIRCLET,
                ITEMDROP_CAT_EYE_CIRCLET,
                ITEMDROP_CORAL_CIRCLET,
                ITEMDROP_DRAGON_HELM,
                ITEMDROP_SILVER_CROWN,
                ITEMDROP_WIZARD_HAT,
                ITEMDROP_NO_CAPE,
                ITEMDROP_CLOTH_CAPE,
                ITEMDROP_REVERSE_CLOAK,
                ITEMDROP_ELVEN_CLOAK,
                ITEMDROP_CRYSTAL_CLOAK,
                ITEMDROP_ROYAL_CLOAK,
                ITEMDROP_BLOOD_CLOAK,
                ITEMDROP_JOSEPHS_CLOAK,
                ITEMDROP_TWILIGHT_CLOAK,
                ITEMDROP_NO_ACCESSORY,
                ITEMDROP_MOONSTONE,
                ITEMDROP_SUNSTONE,
                ITEMDROP_BLOODSTONE,
                ITEMDROP_STAUROLITE,
                ITEMDROP_RING_OF_PALES,
                ITEMDROP_ZIRCON,
                ITEMDROP_AQUAMARINE,
                ITEMDROP_TURQUOISE,
                ITEMDROP_ONYX,
                ITEMDROP_GARNET,
                ITEMDROP_OPAL,
                ITEMDROP_DIAMOND,
                ITEMDROP_LAPIS_LAZULI,
                ITEMDROP_RING_OF_ARES,
                ITEMDROP_GOLD_RING,
                ITEMDROP_SILVER_RING,
                ITEMDROP_RING_OF_VARDA,
                ITEMDROP_RING_OF_ARCANA,
                ITEMDROP_MYSTIC_PENDANT,
                ITEMDROP_HEART_BROACH,
                ITEMDROP_NECKLACE_OF_J,
                ITEMDROP_GAUNTLET,
                ITEMDROP_ANKH_OF_LIFE,
                ITEMDROP_RING_OF_FEANOR,
                ITEMDROP_MEDAL,
                ITEMDROP_TALISMAN,
                ITEMDROP_DUPLICATOR,
                ITEMDROP_KINGS_STONE,
                ITEMDROP_COVENANT_STONE,
                ITEMDROP_NAUGLAMIR,
                ITEMDROP_SECRET_BOOTS,
                ITEMDROP_ALUCART_MAIL,
} ItemDrops;
void EntityBreakable(Entity*);
void EntityExplosion(Entity*);
void EntityPrizeDrop(Entity*);
void EntityDamageDisplay(Entity*);
void EntityIntenseExplosion(Entity*);
void EntitySoulStealOrb(Entity*);
void EntityRoomForeground(Entity*);
void EntityStageNamePopup(Entity*);
void EntityEquipItemDrop(Entity*);
void EntityRelicOrb(Entity*);
void EntityHeartDrop(Entity*);
void EntityEnemyBlood(Entity*);
void EntityMessageBox(Entity*);
void EntityDummy(Entity*);
typedef enum { MONO_SOUND, STEREO_SOUND } soundMode;
enum SfxModes {
    SFX_MODE_CHANNELS_12_19,
    SFX_MODE_CHANNELS_22_23,
    SFX_MODE_RELEASE_22_23,
    SFX_MODE_CHANNELS_20_21,
    SFX_MODE_SCRIPT_NO_PAUSE = 5
};
enum {
                   SD_SEQ_LIBRARY = 0x203,
                             MU_NO_AUDIO = 0x2FF,
                             MU_LOST_PAINTING = 0x301,
                             MU_LOST_PAINTING_LOOP_POINT,
                             MU_CURSE_ZONE,
                             MU_CURSE_ZONE_LOOP_POINT,
                             MU_REQUIEM_FOR_THE_GODS,
                             MU_REQUIEM_FOR_THE_GODS_LOOP_POINT,
                             MU_RAINBOW_CEMETERY,
                             MU_RAINBOW_CEMETERY_LOOP_POINT,
                             MU_WOOD_CARVING_PARTITA,
                             MU_BLANK_30A,
                             MU_CRYSTAL_TEARDROPS,
                             MU_CRYSTAL_TEARDROPS_LOOP_POINT,
                             MU_MARBLE_GALLERY,
                             MU_MARBLE_GALLERY_LOOP_POINT,
                             MU_DRACULAS_CASTLE,
                             MU_DRACULAS_CASTLE_LOOP_POINT,
                             MU_THE_TRAGIC_PRINCE,
                             MU_THE_TRAGIC_PRINCE_LOOP_POINT,
                             MU_TOWER_OF_MIST,
                             MU_TOWER_OF_MIST_LOOP_POINT,
                             MU_DOOR_OF_HOLY_SPIRITS,
                             MU_DOOR_OF_HOLY_SPIRITS_LOOP_POINT,
                             MU_DANCE_OF_PALES,
                             MU_DANCE_OF_PALES_LOOP_POINT,
                             MU_ABANDONED_PIT,
                             MU_ABANDONED_PIT_LOOP_POINT,
                             MU_HEAVENLY_DOORWAY,
                             MU_BLANK_31C,
                             MU_FESTIVAL_OF_SERVANTS,
                             MU_FESTIVAL_OF_SERVANTS_LOOP_POINT,
                             MU_DANCE_OF_ILLUSIONS,
                             MU_DANCE_OF_ILLUSIONS_LOOP_POINT,
                             MU_PROLOGUE,
                             MU_PROLOGUE_LOOP_POINT,
                             MU_WANDERING_GHOSTS,
                             MU_WANDERING_GHOSTS_LOOP_POINT,
                             MU_THE_DOOR_TO_THE_ABYSS,
                             MU_THE_DOOR_TO_THE_ABYSS_LOOP_POINT,
                             MU_METAMORPHOSIS,
                             MU_METAMORPHOSIS_II,
                             MU_METAMORPHOSIS_III,
                             SE_INTRO_WIND,
                             SE_INTRO_WIND_LOOP_POINT,
                             SE_INTRO_WIND_QUIET,
                             SE_INTRO_WIND_QUIET_LOOP_POINT,
                             MU_DANCE_OF_GOLD,
                             MU_DANCE_OF_GOLD_LOOP_POINT,
                             MU_ENCHANTED_BANQUET,
                             MU_ENCHANTED_BANQUET_LOOP_POINT,
                             MU_PRAYER,
                             MU_PRAYER_LOOP_POINT,
                             MU_DEATH_BALLAD,
                             MU_DEATH_BALLAD_LOOP_POINT,
                             MU_BLOOD_RELATIONS,
                             MU_BLOOD_RELATIONS_LOOP_POINT,
                             MU_FINAL_TOCATTA,
                             MU_FINAL_TOCATTA_LOOP_POINT,
                             MU_BLACK_BANQUET,
                             MU_BLACK_BANQUET_LOOP_POINT,
                             MU_STAFF_CREDITS,
                             MU_SILENCE,
                             MU_LAND_OF_BENEDICTION,
                             MU_NOCTURNE,
                             MU_MOONLIGHT_NOCTURNE,
                             JP_VO_NARRATOR_KATSUTE,
                             JP_VO_NARRATOR_SOSHITE,
                             JP_VO_NARRATOR_AKUMAJO,
                             JP_VO_FUKAMI_RIKA_MESSAGE,
                             JP_VO_SHIINA_HEKIRU_MESSAGE,
                             JP_VO_YANADA_KIYOYUKI_MESSAGE,
                             JP_VO_OKIAYU_RYOUTAROU_MESSAGE,
                             JP_VO_SATOU_MASAHARU_MESSAGE,
                             JP_VO_WAKAMOTO_NORIO_MESSAGE,
                             JP_VO_YOKOYAMA_CHISA_MESSAGE,
                             JP_VO_YANAMI_JYOUJI_MESSAGE,
                             JP_VO_KONAMI_1,
                             JP_VO_KONAMI_2,
                             JP_VO_KONAMI_3,
                             JP_VO_KONAMI_4,
                             JP_VO_KONAMI_5,
                             JP_VO_KONAMI_6,
                             JP_VO_KONAMI_7,
                             JP_VO_KONAMI_8,
                             JP_VO_KONAMI_9,
                             JP_VO_KONAMI_10,
                             JP_VO_KONAMI_11,
                             JP_VO_KONAMI_12,
                             NA_VO_RI_DIE_MONSTER,
                             NA_VO_DR_IT_WAS_NOT,
                             NA_VO_RI_TRIBUTE,
                             UNK_390 = 0x390,
                             NA_VO_AL_DEATH_DREAM_WORLD,
                             UNK_3A8 = 0x3A8,
                             NA_VO_AL_INTERESTED,
                             UNK_3AA,
                             UNK_3AB,
                             UNK_3AC,
                             NA_VO_ML_THANKS,
                             UNK_3AE,
                             UNK_3AF,
                             UNK_3B0,
                             UNK_3B1,
                             NA_VO_ML_FAREWELL,
                             UNK_3CD = 0x3CD,
                             NA_VO_MA_IF_YOU_WEAR,
                             UNK_3D9 = 0x3D9,
                             NA_VO_RI_IMPRESSIVE_WHIP,
                             NA_VO_RI_IMPRESSIVE_ESCAPE,
                             NA_VO_RI_ONLY_THE_COUNT,
                             UNK_471 = 0x471,
                             FAERIE_INTRO_LIFE,
                             FAERIE_INTRO_COMMAND,
                             UNK_474,
                             UNK_475,
                             FAERIE_LETS_GO,
                             UNK_477,
                             UNK_478,
                             FAERIE_FOLLOW,
                             FAERIE_WALL_HINT,
                             UNK_47B,
                             UNK_47C,
                             UNK_47D,
                             UNK_47E,
                             UNK_47F,
                             UNK_480,
                             UNK_481,
                             UNK_482,
                             UNK_483,
                             UNK_484,
                             UNK_485,
                             UNK_486,
                             UNK_487,
                             UNK_488,
                             UNK_489,
                             FAERIE_SUSPICIOUS_HINT,
                             UNK_48B,
                             UNK_48C,
                             UNK_48D,
                             FAERIE_MIST_HINT,
                             UNK_48F,
                             UNK_490,
                             UNK_491,
                             FAERIE_DARKNESS_HINT,
                             UNK_4E6 = 0x4E6,
                             UNK_4E7,
                             DEMON_INTRO_COMMAND,
                             UNK_4E9,
                             UNK_4EA,
                             UNK_4EB,
                             UNK_4EC,
                             DEMON_INTRO_READY,
                             DEMON_SWITCH_1,
                             DEMON_SWITCH_2,
                             UNK_52D = 0x52D,
                             JP_VO_SH_GROAN,
                             JP_VO_SH_SCREAM,
                             JP_VO_SH_SONO_TEIDO,
};
enum Sfx {
    MU_SEQ_LIBRARIAN = 0x202,
    MU_SEQ_CONFESSIONAL_BELLS = 0x204,
    MU_SEQ_LIBRARIAN_PSP = 0x302,
    MU_SEQ_CONFESSIONAL_BELLS_PSP = 0x304,
                SFX_HARPY_WING_FLAP = 0x601,
                SFX_RIC_WHIP_RATTLE_A,
                SFX_RIC_WHIP_RATTLE_B,
                SFX_RIC_WHIP_RATTLE_C,
                SFX_RIC_WHIP_RATTLE_D,
                SFX_RIC_WHIP_RATTLE_E,
                SFX_STONE_MOVE_A,
                SFX_STONE_MOVE_B,
                SFX_STONE_MOVE_C,
                SFX_WEAPON_SWISH_A,
                SFX_WEAPON_SWISH_B,
                SFX_WEAPON_SWISH_C,
                SFX_METAL_CLANG_A,
                SFX_METAL_CLANG_B,
                SFX_METAL_CLANG_C,
                SFX_METAL_CLANG_D,
                SFX_METAL_CLANG_E,
                SFX_METAL_CLANG_F,
                SFX_UNK_CROW,
                SFX_ELECTRICITY,
                SFX_SCRAPE_A,
                SFX_SCRAPE_B,
                SFX_SCRAPE_C,
                SFX_UNK_618,
                SFX_GLASS_BREAK_A,
                SFX_GLASS_BREAK_B,
                SFX_GLASS_BREAK_C,
                SFX_GLASS_BREAK_D,
                SFX_GLASS_BREAK_E,
                SFX_BAT_ECHO_A,
                SFX_BAT_ECHO_B,
                SFX_BAT_ECHO_C,
                SFX_BAT_ECHO_D,
                SFX_SKULL_BONK,
                SFX_RIC_RSTONE_TINK,
                SFX_SALEM_WITCH_CURSE_ATTACK,
                SFX_ARROW_SHOT_A,
                SFX_ARROW_SHOT_B,
                SFX_ARROW_SHOT_C,
                SFX_ARROW_SHOT_D,
                SFX_SKELETON_DEATH_A,
                SFX_SKELETON_DEATH_B,
                SFX_SKELETON_DEATH_C,
                SFX_FIRE_SHOT,
                SFX_WEAPON_STAB_A,
                SFX_WEAPON_STAB_B,
                SFX_WEAPON_APPEAR,
                SFX_UNK_BETA_630,
                SFX_DEATH_AMBIENCE,
                SFX_SUBWEAPON_CONTAINER_BREAK,
                SFX_UI_CONFIRM,
                SFX_CANDLE_HIT,
                SFX_TELEPORT_BANG_A,
                SFX_TELEPORT_BANG_B,
                SFX_SUC_APPEAR,
                SFX_UNUSED_SCRAPE_A,
                SFX_UNUSED_SCRAPE_B,
                SFX_UNUSED_SCRAPE_C,
                SFX_UNUSED_UI_SELECT,
                SFX_START_SLAM_A,
                SFX_START_SLAM_B,
                SFX_UNUSED_START_SLAM_C,
                SFX_ANIME_SWORD_A,
                SFX_ANIME_SWORD_B,
                SFX_ANIME_SWORD_C,
                SFX_DOOR_OPEN,
                SFX_WALL_DEBRIS_A,
                SFX_WALL_DEBRIS_B,
                SFX_WALL_DEBRIS_C,
                SFX_STOMP_HARD_A,
                SFX_STOMP_HARD_B,
                SFX_STOMP_HARD_C,
                SFX_STOMP_HARD_D,
                SFX_STOMP_HARD_E,
                SFX_STOMP_SOFT_A,
                SFX_STOMP_SOFT_B,
                SFX_SAVE_HEARTBEAT,
                SFX_BAT_SCREECH,
                SFX_DOOR_CLOSE_A,
                SFX_DOOR_CLOSE_B,
                SFX_UNK_UI_ERROR,
                SFX_EXPLODE_FAST_A,
                SFX_EXPLODE_FAST_B,
                SFX_EXPLODE_A,
                SFX_EXPLODE_B,
                SFX_UNUSED_EXPLODE_C,
                SFX_EXPLODE_D,
                SFX_EXPLODE_E,
                SFX_EXPLODE_F,
                SFX_FM_EXPLODE_A,
                SFX_FM_EXPLODE_B,
                SFX_UNUSED_FM_EXPLODE_C,
                SFX_FM_EXPLODE_D,
                SFX_EXPLODE_SMALL,
                SFX_PSP_MARIA_CARDINAL_CRASH,
                SFX_FIREBALL_SHOT_A,
                SFX_FIREBALL_SHOT_B,
                SFX_FIREBALL_SHOT_C,
                SFX_SALEM_WITCH_CURSE_PROJ,
                SFX_THUNDER_A,
                SFX_THUNDER_B,
                SFX_UNUSED_THUNDER_C,
                SFX_UNK_TE3_LOW_UI,
                SFX_TRANSFORM,
                SFX_MAGIC_WEAPON_APPEAR_A,
                SFX_MAGIC_WEAPON_APPEAR_B,
                SFX_AXE_KNIGHT_WEAPON_BREAK,
                SFX_BONE_SWORD_SWISH_A,
                SFX_BONE_SWORD_SWISH_B,
                SFX_BONE_SWORD_SWISH_C,
                SFX_UNK_TELEPORT_BANG_SHORT_A,
                SFX_TELEPORT_BANG_SHORT_B,
                SFX_UNUSED_TELEPORT_BANG_SHORT_C,
                SFX_NOISE_SWEEP_DOWN_A,
                SFX_NOISE_SWEEP_DOWN_B,
                SFX_FROG_TOAD_TONGUE,
                SFX_LEVER_METAL_BANG,
                SFX_SWITCH_CLICK,
                SFX_RUNESWORD_ATTACK,
                SFX_WEAPON_HIT_A,
                SFX_UNK_TE3_WEAPON_HIT_B,
                SFX_HEART_PICKUP,
                SFX_UI_MOVE,
                SFX_ITEM_PICKUP,
                SFX_UI_MP_FULL,
                SFX_CANDLE_HIT_WHOOSH_A,
                SFX_CANDLE_HIT_WHOOSH_B,
                SFX_QUICK_STUTTER_EXPLODE_A,
                SFX_WHITE_DRAGON_HIT,
                SFX_KARMA_COIN_JINGLE,
                SFX_QUICK_STUTTER_EXPLODE_B,
                SFX_FM_THUNDER_EXPLODE,
                SFX_BONE_MUSKET_SHOT,
                SFX_UI_ERROR,
                SFX_LEVEL_UP,
                SFX_DEBUG_SELECT,
                SFX_WEAPON_SCRAPE_ECHO,
                SFX_RIC_HOLY_WATER_ATTACK,
                SFX_DRA_GLASS_BREAK,
                SFX_WING_FLAP_A,
                SFX_WING_FLAP_B,
                SFX_HEALTH_PICKUP,
                SFX_OUIJA_TABLE_DEATH,
                SFX_FM_EXPLODE_SWISHES,
                SFX_SMALL_FLAME_IGNITE,
                SFX_UNK_TE1_TRANSFORM,
                SFX_STUTTER_EXPLODE_LOW,
                SFX_FM_STUTTER_EXPLODE,
                SFX_FAST_STUTTER_EXPLODE,
                SFX_SWORD_LORD_EXPLODE,
                SFX_STUTTER_EXPLODE_A,
                SFX_STUTTER_EXPLODE_B,
                SFX_STUTTER_EXPLODE_C,
                SFX_ALU_HOLY_WATER_ATTACK,
                SFX_BAT_WING_SWISHES,
                SFX_BAT_SCREECH_SWISH,
                SFX_MAGIC_SWITCH,
                SFX_THROW_WEAPON_SWISHES,
                SFX_RIC_CRASH_CROSS,
                SFX_TRANSFORM_LOW,
                SFX_STOPWATCH_TICK,
                SFX_DEATH_SWISH,
                SFX_RAPID_SCRAPE_3X,
                SFX_UI_SUBWEAPON_TINK,
                SFX_SKULL_KNOCK_A,
                SFX_SKULL_KNOCK_B,
                SFX_UNUSED_SKULL_KNOCK_C,
                SFX_ALUCARD_SWORD_SWISH,
                SFX_GOLD_PICKUP,
                SFX_MARIONETTE_RATTLE,
                SFX_SEED_SPIT,
                SFX_CANNON_EXPLODE,
                SFX_UI_ALERT_TINK,
                SFX_TINK_JINGLE,
                SFX_GUARD_TINK,
                SFX_GLASS_SHARDS,
                SFX_TRANSFORM_3X,
                SFX_BIBLE_SCRAPE,
                SFX_UNK_TE1_TICK,
                SFX_UNK_TE2_RATTLE,
                SFX_RIC_FLAME_WHIP,
                SFX_UNK_TE2_FIRE_BURST,
                SFX_LOW_CLOCK_TICK,
                SFX_UNK_TE3_LOW_CLOCK_TICK,
                SFX_UNUSED_METAL_TING,
                SFX_FAST_SWORD_SWISHES,
                SFX_BONE_MUSKET_RELOAD,
                SFX_SKELERANG_CATCH,
                SFX_QUIET_STEPS,
                SFX_BLIPS_A,
                SFX_UNUSED_BLIPS_B,
                SFX_BLIPS_C,
                SFX_BLIPS_D,
                SFX_DISCUS_LORD_EXPLODE,
                SFX_HIPPOGRYPH_FIRE_ATTACK,
                SFX_SALOME_MAGIC_ATTACK,
                SFX_MAGIC_NOISE_SWEEP,
                SFX_BOSS_WING_FLAP,
                SFX_WHIP_TWIRL_SWISH,
                SFX_BONE_THROW,
                SFX_BONE_CREAK,
                SFX_FLEA_ARMOR_EXPLODE,
                SFX_RED_SKEL_COLLAPSE,
                SFX_RED_SKEL_REBUILD,
                SFX_BLADE_SOLDIER_CHARGE_STAB,
                SFX_CORNER_GUARD_DEATH,
                SFX_TOMBSTONE_MOVE,
                SFX_FLEA_RIDER_EXPLODE,
                SFX_STONE_ROSE_SEED,
                SFX_VENUS_WEED_CHARGE_ATTACK,
                SFX_RNO4_MAGIC_GLASS_BREAK,
                SFX_PSWORD_TWIRL_ATTACK,
                SFX_PSWORD_TWIRL,
                SFX_CROW_DEATH,
                SFX_CROW_CAW,
                SFX_UNUSED_CLONE_DISAPPEAR,
                SFX_BOSS_CLONE_DISAPPEAR,
                SFX_METAL_RATTLE_A,
                SFX_METAL_RATTLE_B,
                SFX_METAL_RATTLE_C,
                SFX_RAPID_SYNTH_BUBBLE,
                SFX_RAPID_SYNTH_BUBBLE_SHORT,
                SFX_CRASH_CROSS,
                SFX_SAVE_COFFIN_SWISH,
                SFX_RCEN_GLASS_BREAKS,
                SFX_RIC_SUC_REVIVE,
                SFX_SCYLLA_BUBBLE_BURST,
                SFX_PENTAGRAM_ATTACK,
                SFX_UNUSED_ANIME_EXPLODE,
                SFX_LOW_SYNTH_BUBBLES,
                SFX_VO_ALU_PAIN_A,
                SFX_VO_ALU_PAIN_B,
                SFX_VO_ALU_PAIN_C,
                SFX_VO_ALU_PAIN_D,
                SFX_VO_ALU_PAIN_E,
                SFX_VO_ALU_SILENCE,
                SFX_VO_ALU_YELL,
                SFX_VO_ALU_ATTACK_A,
                SFX_VO_ALU_ATTACK_B,
                SFX_VO_ALU_ATTACK_C,
                SFX_VO_ALU_ATTACK_D,
                SFX_VO_ALU_WHAT,
                SFX_VO_ALU_DARK_META,
                SFX_VO_ALU_SOUL_STEAL,
                SFX_UNUSED_6F5,
                SFX_VO_ALU_DEATH,
                SFX_ALU_WOLF_BARK,
                SFX_UNUSED_VO_ALU_WHOA,
                SFX_VO_RIC_ATTACK_A,
                SFX_VO_RIC_ATTACK_B,
                SFX_VO_RIC_ATTACK_C,
                SFX_VO_RIC_ATTACK_YELL,
                SFX_UNUSED_6FD,
                SFX_UNUSED_6FE,
                SFX_VO_RIC_DEATH,
                SFX_VO_RIC_HYDRO_STORM,
                SFX_VO_RIC_PAIN_A,
                SFX_VO_RIC_PAIN_B,
                SFX_VO_RIC_PAIN_C,
                SFX_VO_RIC_PAIN_D,
                SFX_RIC_WHIP_HIT,
                SFX_RIC_WHIP_ATTACK,
                SFX_RIC_SLIDE_SKID,
                SFX_RIC_HYDRO_STORM_ATTACK,
                SFX_SLOGRA_ROAR,
                SFX_SLOGRA_ROAR_DEFEAT,
                SFX_SLOGRA_PAIN_A,
                SFX_SLOGRA_PAIN_B,
                SFX_CORPSEWEED_ATTACK,
                SFX_LESSER_DEMON_POISON,
                SFX_VENUS_WEED_HURT,
                SFX_VENUS_WEED_DEATH,
                SFX_UNK_RNZ0_711,
                SFX_UNUSED_712,
                SFX_UNUSED_713,
                SFX_FLYING_ZOMBIE_PAIN,
                SFX_FLYING_ZOMBIE_DEATH,
                SFX_FLYING_ZOMBIE_BODY_RIP,
                SFX_UNK_RDAI_717,
                SFX_VALHALLA_KNIGHT_NEIGH,
                SFX_VALHALLA_KNIGHT_GALLOP,
                SFX_TOAD_CROAK,
                SFX_FROG_CROAK,
                SFX_UNUSED_71C,
                SFX_MERMAN_DEATH,
                SFX_CLOAKED_KNIGHT_ATTACK,
                SFX_UNK_CLOAKED_KNIGHT_71F,
                SFX_CLOAKED_KNIGHT_DEATH,
                SFX_UNK_NZ1_721,
                SFX_UNK_NZ1_722,
                SFX_UNK_NZ1_723,
                SFX_RNO2_ANIME_SWORD,
                SFX_MARIONETTE_LAUGH,
                SFX_MARIONETTE_YELL,
                SFX_UNUSED_727,
                SFX_GREMLIN_HURT,
                SFX_GREMLIN_DEATH,
                SFX_HUNTING_GIRL_ATTACK,
                SFX_HUNTING_GIRL_PAIN,
                SFX_HUNTING_GIRL_DEATH,
                SFX_VANDAL_SWORD_ATTACK,
                SFX_VANDAL_SWORD_PAIN,
                SFX_VANDAL_SWORD_DEATH,
                SFX_STONE_ROSE_PAIN,
                SFX_STONE_ROSE_DEATH,
                SFX_UNK_RLIB_732,
                SFX_FROZEN_SHADE_SCREAM,
                SFX_LOSSOTH_NAPALM_GRUNT,
                SFX_LOSSOTH_DEATH,
                SFX_SALEM_WITCH_ATTACK,
                SFX_SALEM_WITCH_HURT,
                SFX_SALEM_WITCH_DEATH,
                SFX_GHOST_ENEMY_HOWL,
                SFX_ECTOPLASM_BOING,
                SFX_ECTOPLASM_DEATH,
                SFX_SPITTLEBONE_ACID_SPLAT,
                SFX_UNK_RLIB_73D,
                SFX_UNUSED_73E,
                SFX_SKULL_LORD_DEATH,
                SFX_GURKHA_ATTACK,
                SFX_GURKHA_PAIN,
                SFX_GURKHA_DEATH,
                SFX_HAMMER_ATTACK,
                SFX_HAMMER_PAIN,
                SFX_HAMMER_DEATH,
                SFX_BLOODY_ZOMBIE_PAIN,
                SFX_BLOODY_ZOMBIE_DEATH,
                SFX_BLOODY_ZOMBIE_BODY_HIT,
                SFX_BLOODY_ZOMBIE_SPLATTER,
                SFX_SALOME_ATTACK,
                SFX_SALOME_PAIN,
                SFX_SALOME_MEOW_SHORT,
                SFX_SALOME_MEOW,
                SFX_BLADE_ENEMY_ATTACK,
                SFX_BLADE_ENEMY_PAIN,
                SFX_BLADE_ENEMY_DEATH,
                SFX_ARMOR_LORD_ATTACK,
                SFX_ARMOR_LORD_FIRE_ATTACK,
                SFX_ARMOR_LORD_DEATH,
                SFX_GRAVE_KEEPER_GRAAH,
                SFX_GRAVE_KEEPER_HIYAH,
                SFX_GRAVE_KEEPER_DEATH,
                SFX_CTULHU_DEATH,
                SFX_CTULHU_LAUGH,
                SFX_CTULHU_ROAR,
                SFX_ROCK_KNIGHT_ATTACK,
                SFX_ROCK_KNIGHT_PAIN,
                SFX_UNK_RNO4_75C,
                SFX_ROCK_KNIGHT_DEATH,
                SFX_PLATE_LORD_ATTACK,
                SFX_PLATE_LORD_PAIN,
                SFX_PLATE_LORD_DEATH,
                SFX_PLATE_LORD_BALL_IMPACT,
                SFX_BONE_ARK_CHARGE_ATTACK,
                SFX_DISCUS_LORD_ATTACK,
                SFX_DISCUS_LORD_DEATH,
                SFX_DISCUS_BUZZ,
                SFX_AXE_KNIGHT_ATTACK,
                SFX_AXE_KNIGHT_DEATH,
                SFX_HIPPOGRYPH_WING_FLAP,
                SFX_HIPPOGRYPH_SQUAWK,
                SFX_UNK_RDAI_76A,
                SFX_FROZEN_HALF_DEATH,
                SFX_FROZEN_HALF_ATTACK,
                SFX_FROZEN_HALF_MAXIMUM_POWER,
                SFX_FROZEN_HALF_BLIZZARD,
                SFX_UNUSED_76F,
                SFX_SPEAR_GUARD_ATTACK,
                SFX_SPEAR_GUARD_DEATH,
                SFX_SPEAR_GUARD_UNUSED_MOVE,
                SFX_SPEAR_GUARD_MOVE,
                SFX_UNUSED_774,
                SFX_HELLFIRE_BEAST_DEATH,
                SFX_DIPLOCEPHALUS_ATTACK,
                SFX_DIPLOCEPHALUS_PAIN,
                SFX_DIPLOCEPHALUS_DEATH,
                SFX_DIPLOCEPHALUS_STOMP,
                SFX_GORGON_SNORT,
                SFX_GORGON_ATTACK,
                SFX_FLEA_RIDER_DEATH,
                SFX_SWORD_LORD_SWIPE_ATTACK,
                SFX_SWORD_LORD_STAB_ATTACK,
                SFX_SWORD_LORD_DEATH,
                SFX_WARG_DEATH_HOWL,
                SFX_WARG_PAIN,
                SFX_WARG_ATTACK,
                SFX_WARG_GROWL,
                SFX_UNK_RNO4_784,
                SFX_WEREWOLF_SPIN_ATTACK,
                SFX_MINOTAUR_ATTACK,
                SFX_MINOTAURUS_JUMP_ATTACK,
                SFX_MINOTAUR_BREATH_ATTACK,
                SFX_UNK_BO2_789,
                SFX_HARPY_ATTACK,
                SFX_HARPY_DEATH,
                SFX_MUDMAN_ATTACK,
                SFX_SPELLBOOK_DEATH,
                SFX_MAGIC_TOME_ATTACK,
                SFX_LESSER_DEMON_SWIPE_ATTACK,
                SFX_MALACHI_ROLLING_ORB,
                SFX_FIRE_DEMON_ATTACK_CHARGE,
                SFX_OWL_KNIGHT_TAUNT,
                SFX_OWL_KNIGHT_ATTACK,
                SFX_OWL_KNIGHT_REACT,
                SFX_OWL_KNIGHT_DEATH,
                SFX_OWL_DEATH,
                SFX_WATERFALL_LOOP,
                SFX_UNK_TE4_798,
                SFX_UNK_TE4_799,
                SFX_UNK_TE4_79A,
                SFX_UNK_TE4_79B,
                SFX_UNUSED_79C,
                SFX_SHUTTING_WINDOW,
                SFX_UNUSED_79E,
                SFX_UNK_TE3_79F,
                SFX_DEATH_TAKES_ITEMS,
                SFX_DEATH_LAUGH,
                SFX_ITEM_YOINK,
                SFX_UNUSED_7A3,
                SFX_TREE_BRANCH_SNAP,
                SFX_CASTLE_GATE_RISE,
                SFX_CLOCK_ROOM_BELL,
                SFX_UNUSED_7A7,
                SFX_UNUSED_7A8,
                SFX_CLOCK_ROOM_TICK,
                SFX_ELEVATOR_GEARS_LOOP,
                SFX_UNK_TE2_7AB,
                SFX_TELESCOPE_SHUTTER_CLICK,
                SFX_ALU_ZZZ_SNORE,
                SFX_DOP_DOOR_OPEN,
                SFX_RAIN_LOOP,
                SFX_UNK_TE5_7B0,
                SFX_ELEVATOR_DOOR,
                SFX_UNK_TE4_7B2,
                SFX_ELEVATOR_SLAM,
                SFX_UNK_TE4_7B4,
                SFX_ELEVATOR_START,
                SFX_BAD_LUCK_JINGLE,
                SFX_NO1_BIRD_CYCLE,
                SFX_UNK_TE2_7B8,
                SFX_UNK_TE2_7B9,
                SFX_UNK_TE2_7BA,
                SFX_CONFESS_GHOST_CURTAIN_PULL,
                SFX_CHAPEL_BELL,
                SFX_WOODEN_BRIDGE_EXPLODE,
                SFX_UNK_NO4_7BE,
                SFX_OAR_ROW,
                SFX_DUNGEON_PRISONER_RATTLE,
                SFX_CLOCK_TOWER_GEAR,
                SFX_WATER_SPLASH_JUMP,
                SFX_WATER_SPLASH_MOVE,
                SFX_WATER_BUBBLE,
                SFX_BOSS_LARGE_FLAMES,
                SFX_B07_STOMP,
                SFX_BO1_UNK_7C7,
                SFX_MEDUSA_WEAPON_SWING,
                SFX_UNUSED_7C9,
                SFX_BO0_UNK_7CA,
                SFX_DOPPLEGANGER_DOOR_OPEN,
                SFX_DOPPLEGANGER_APPEAR,
                SFX_GRANFALOON_APPEAR,
                SFX_SHAFT_DEATH,
                SFX_SHAFT_FIRE_ATTACK,
                SFX_UNUSED_7D0,
                SFX_SCIFI_BLAST,
                SFX_BOSS_DEFEATED,
                SFX_DRACULA_FLY_IN,
                SFX_UNK_TE1_7D4,
                SFX_BEELZEBUB_FLY_BUZZ,
                SFX_UNUSED_7D6,
                SFX_VO_DOP_PAIN_A,
                SFX_VO_DOP_PAIN_B,
                SFX_VO_DOP_PAIN_C,
                SFX_VO_DOP_PAIN_D,
                SFX_VO_DOP_PAIN_E,
                SFX_VO_DOP_PAIN_F,
                SFX_VO_DOP_YELL,
                SFX_VO_DOP_ATTACK_A,
                SFX_VO_DOP_ATTACK_B,
                SFX_VO_DOP_ATTACK_C,
                SFX_VO_DOP_ATTACK_D,
                SFX_UNUSED_VO_DOP_WHAT,
                SFX_UNUSED_7E3,
                SFX_UNUSED_7E4,
                SFX_UNUSED_7E5,
                SFX_VO_DOP_DEATH,
                SFX_UNUSED_7E7,
                SFX_DOP_SUBWEAPON_TINK,
                SFX_UNUSED_7E9,
                SFX_THE_CREATURE_HAMMER,
                SFX_THE_CREATURE_ATTACK,
                SFX_THE_CREATURE_DEATH,
                SFX_UNUSED_7ED,
                SFX_UNUSED_7EE,
                SFX_DEATH_PAIN_A,
                SFX_DEATH_ATTACK,
                SFX_DEATH_SCYTHE_ATTACK,
                SFX_DEATH_BALL_ATTACK,
                SFX_DEATH_YOURE_STRONG_INDEED,
                SFX_DEATH_BUT_NOW_YOU_WILL_DIE,
                SFX_UNUSED_7F5,
                SFX_UNUSED_7F6,
                SFX_DEATH_PAIN_B,
                SFX_DEATH_PAIN_C,
                SFX_UNK_TE2_7F9,
                SFX_DEATH_SCYTHE_SWISH,
                SFX_MEDUSA_STONE,
                SFX_UNUSED_MEDUSA_OOH_WHOA,
                SFX_MEDUSA_VENOM,
                SFX_MEDUSA_ATTACK_A,
                SFX_MEDUSA_ATTACK_B,
                SFX_UNUSED_MEDUSA_ATTACK_C,
                SFX_MEDUSA_PAIN_A,
                SFX_MEDUSA_PAIN_B,
                SFX_UNUSED_MEDUSA_OH_NO,
                SFX_MEDUSA_DEATH,
                SFX_SCYLLA_ATTACK_YELL,
                SFX_SCYLLA_ATTACK_DIE,
                SFX_SCYLLA_PAIN,
                SFX_SCYLLA_DEATH,
                SFX_SCYLLA_WYRM_ATTACK,
                SFX_SCYLLA_WYRM_WALL_DEBRIS,
                SFX_GRANFALOON_LASER_ATTACK,
                SFX_UNUSED_GRANFALOON_SCREAM_A,
                SFX_UNUSED_GRANFALOON_SCREAM_B,
                SFX_GRANFALOON_BODIES_FALL,
                SFX_GALAMOTH_ELECTRICITY,
                SFX_UNUSED_GALAMOTH_810,
                SFX_UNUSED_GALAMOTH_811,
                SFX_FAKE_SYPHA_ATTACK,
                SFX_FAKE_SYPHA_PAIN,
                SFX_FAKE_SYPHA_DEATH,
                SFX_FAKE_TREVOR_BLOOD_CROSS,
                SFX_OLROX_BAT_ATTACK,
                SFX_OLROX_TRANSFORM,
                SFX_OLROX_ATTACK,
                SFX_OLROX_MONSTER_PAIN,
                SFX_OLROX_LASER_ATTACK,
                SFX_AKMODAN_II_PAIN,
                SFX_AKMODAN_II_DEATH,
                SFX_AKMODAN_II_ARM_STRETCH,
                SFX_AKMODAN_II_MOVE,
                SFX_AKMODAN_II_DISSOLVE,
                SFX_UNK_RNZ1_DEBRIS_820,
                SFX_UNK_RNZ1_EXPLODE_821,
                SFX_UNK_RNZ1_EXPLODE_822,
                SFX_UNK_RNZ1_SWISH_823,
                SFX_UNK_RNZ1_WIND_824,
                SFX_BOSS_RIC_WHIP_ATTACK,
                SFX_BOSS_RIC_SLIDE_SKID,
                SFX_BOSS_RIC_ITEM_CRASH_ATTACK,
                SFX_BOSS_RIC_HYDRO_STORM,
                SFX_BOSS_RIC_HOLY_CROSS,
                SFX_UNUSED_BOSS_RIC_EVIL_LAUGH,
                SFX_BOSS_RIC_LAUGH,
                SFX_BOSS_RIC_ATTACK_A,
                SFX_BOSS_RIC_ATTACK_B,
                SFX_BOSS_RIC_ATTACK_C,
                SFX_BOSS_RIC_ATTACK_D,
                SFX_BOSS_RIC_HYDRO_STORM_RAIN,
                SFX_UNUSED_831,
                SFX_UNUSED_832,
                SFX_UNUSED_833,
                SFX_BOSS_RIC_DASH_ATTACK,
                SFX_UNUSED_835,
                SFX_BOSS_RIC_PAIN_A,
                SFX_BOSS_RIC_PAIN_B,
                SFX_BOSS_RIC_PAIN_C,
                SFX_BOSS_RIC_PAIN_D,
                SFX_BOSS_RIC_PAIN_E,
                SFX_BOSS_RIC_PAIN_F,
                SFX_UNUSED_BOSS_RIC_CURSES,
                SFX_UNUSED_BOSS_RIC_INSOLENT_PUP,
                SFX_BOSS_RIC_DEATH,
                SFX_UNUSED_83F,
                SFX_SHAFT_ATTACK_A,
                SFX_UNUSED_SHAFT_ATTACK_B,
                SFX_UNUSED_SHAFT_ATTACK_C,
                SFX_UNUSED_SHAFT_ATTACK_D,
                SFX_UNUSED_SHAFT_ATTACK_E,
                SFX_SHAFT_ATTACK_DEMONIC_BLESSING,
                SFX_UNUSED_SHAFT_LAUGH_A,
                SFX_UNUSED_SHAFT_DISINTEGRATE,
                SFX_UNUSED_SHAFT_PAIN_A,
                SFX_UNUSED_SHAFT_PAIN_B,
                SFX_UNUSED_SHAFT_PAIN_C,
                SFX_UNUSED_SHAFT_DEATH,
                SFX_SHAFT_ORB_BOUNCE,
                SFX_SHAFT_ORB_BREAK,
                SFX_UNUSED_SHAFT_LAUGH_B,
                SFX_DRACULA_LAUGH_A,
                SFX_DRACULA_LAUGH_B,
                SFX_UNUSED_DRACULA_ATTACK_A,
                SFX_UNUSED_DRACULA_ATTACK_B,
                SFX_DRACULA_FIREBALL_ATTACK,
                SFX_DRACULA_SQUISH_GRUNT,
                SFX_DRACULA_HERE_IS_TRUE_POWER,
                SFX_UNK_ST0_856,
                SFX_DRACULA_GRANT_ME_POWER,
                SFX_DRACULA_PLAYTIME_IS_OVER,
                SFX_DRACULA_MONSTER_MAGIC_ATTACK,
                SFX_PSP_DRACULA_FIREBALL_ATTACK,
                SFX_DRACULA_PAIN_A,
                SFX_DRACULA_PAIN_B,
                SFX_DRACULA_PAIN_C,
                SFX_UNUSED_DRACULA_PAIN_A,
                SFX_UNUSED_DRACULA_PAIN_B,
                SFX_UNUSED_DRACULA_PAIN_C,
                SFX_UNUSED_DRACULA_PAIN_D,
                SFX_UNUSED_862,
                SFX_UNUSED_863,
                SFX_UNUSED_864,
                SFX_UNUSED_865,
                SFX_DRACULA_MONSTER_ROAR,
                SFX_UNUSED_867,
                SFX_DRACULA_KARASUMAN_SQUISH,
                SFX_DRACULA_ELECTRICITY,
                SFX_UNUSED_86A,
                SFX_DRACULA_BEHOLD_MY_TRUE_FORM,
                SFX_UNUSED_86C,
                SFX_UNUSED_86D,
                SFX_SUCCUBUS_LAUGH,
                SFX_UNK_SUCCUBUS_86F,
                SFX_SUCCUBUS_DUPLICATES,
                SFX_UNUSED_SUCCUBUS_ATTACK_A,
                SFX_SUCCUBUS_HOMING_ORB_ATTACK,
                SFX_UNUSED_SUCCUBUS_ATTACK_B,
                SFX_SUCCUBUS_WING_ATTACK,
                SFX_UNUSED_SUCCUBUS_AH,
                SFX_SUCCUBUS_ILL_SUCK_YOU_DRY,
                SFX_UNUSED_SUCCUBUS_OH_A,
                SFX_UNUSED_SUCCUBUS_OH_B,
                SFX_SUCCUBUS_PAIN_A,
                SFX_SUCCUBUS_PAIN_B,
                SFX_SUCCUBUS_DEFEAT,
                SFX_SUCCUBUS_HOMING_ORB,
                SFX_MARIA_RICHTER,
                SFX_MARIA_GRANT_HIM_YOUR_STRENGTH,
                SFX_UNUSED_MARIA_AIM_FOR_HIS_HEAD,
                SFX_DRACULA_MONSTER_SILHOUETTE_APPEAR,
                SFX_MARIA_ANIMALS_APPEAR,
                SFX_MARIA_FOOTSTEPS_A,
                SFX_MARIA_FOOTSTEPS_B,
                SFX_UNUSED_884,
                SFX_FAERIE_HEALING,
                SFX_FAERIE_POTION,
                SFX_FAERIE_REGENERATION,
                SFX_FAERIE_NO_MEDICINE,
                SFX_FAERIE_HAMMER_A,
                SFX_FAERIE_HAMMER_B,
                SFX_FAERIE_HAMMER_C,
                SFX_FAERIE_HAMMER_D,
                SFX_FAERIE_FALL_OFF_A,
                SFX_FAERIE_FALL_OFF_B,
                SFX_FAERIE_FALL_OFF_C,
                SFX_FAERIE_FALL_OFF_D,
                SFX_FAERIE_OH_NO,
                SFX_FAERIE_ARE_YOU_OK,
                SFX_YOUSEI_POTION,
                SFX_YOUSEI_UNK_A,
                SFX_YOUSEI_REGENERATION,
                SFX_YOUSEI_UNK_C,
                SFX_YOUSEI_HAMMER_A,
                SFX_YOUSEI_HAMMER_B,
                SFX_YOUSEI_FALL_OFF_A,
                SFX_YOUSEI_FALL_OFF_B,
                SFX_YOUSEI_FALL_OFF_C,
                SFX_YOUSEI_FALL_OFF_D,
                SFX_YOUSEI_YELL,
                SFX_DEMON_GRUNT_1,
                SFX_DEMON_GRUNT_2,
                SFX_DEMON_GRUNT_3,
                SFX_DEMON_TAKE_THAT,
                SFX_DEMON_DIE,
                SFX_DEMON_FIRE_SPEAR,
                SFX_DEMON_ICE_SPEAR,
                SFX_DEMON_THUNDER_SPEAR,
                SFX_DEMON_LIGHTNING_SPEAR,
                SFX_UNUSED_DEMON_EAT,
                SFX_NOSE_DEMON_UNK_A,
                SFX_NOSE_DEMON_UNK_B,
                SFX_NOSE_DEMON_UNK_C,
                SFX_NOSE_DEMON_UNK_D,
                SFX_NOSE_DEMON_UNK_E,
                SFX_NOSE_DEMON_UNK_F,
                SFX_NOSE_DEMON_UNK_G,
                SFX_NOSE_DEMON_UNK_H,
                SFX_NOSE_DEMON_UNK_I,
                SFX_NOSE_DEMON_UNK_J,
                SFX_SWORD_SERVANT_SLASH,
                SFX_SWORD_SERVANT_SLICE,
                SFX_SWORD_SERVANT_TEAR,
                SFX_SWORD_SERVANT_DARK_EDGE,
                SFX_SWORD_SERVANT_BROS_SPELL,
                SFX_SWORD_SERVANT_GRUNT_A,
                SFX_SWORD_SERVANT_GRUNT_B,
                SFX_THE_CREATURE_HEAD_FALL,
                SFX_TELEPORT_SYNTH_UP,
                SFX_TELEPORT_SYNTH_DOWN,
                SFX_UNUSED_TELEPORT_SYNTH_UP,
                SFX_UNUSED_TELEPORT_SYNTH_DOWN,
                SFX_BURNING_PHOTOGRAPH,
                SFX_DRACULA_TRIANGLE_ATTACK,
                SFX_GRANFALOON_SCREAMS_A,
                SFX_GRANFALOON_SCREAMS_B,
                SFX_BEELZEBUB_PAIN,
                SFX_BIBLE_SUBWPN_SWISH,
                SFX_UI_NAME_ENTRY = 0x8CD,
                SFX_UNUSED_UI_NAME_ENTRY,
                SFX_UNUSED_ANIME_SWORD,
                SFX_UNUSED_8D0,
                SFX_SUCCUBUS_DELICIOUS,
                SFX_VO_MAR_8E6 = 0x8E6,
                SFX_VO_MAR_ATTACK_C,
                SFX_VO_MAR_8E8,
                SFX_VO_MAR_8E9,
                SFX_VO_MAR_8EA,
                SFX_VO_MAR_8EB,
                SFX_VO_MAR_8EC,
                SFX_VO_MAR_8ED,
                SFX_VO_MAR_8EE,
                SFX_VO_MAR_8EF,
                SFX_VO_MAR_8F0,
                SFX_VO_MAR_8F1,
                SFX_VO_MAR_PAIN_B,
                SFX_VO_MAR_PAIN_C,
                SFX_VO_MAR_PAIN_D,
                SFX_VO_MAR_DEATH,
};
typedef struct {
               s16 sndId;
               u16 sndVol;
               s16 sndPan;
} SfxRingBufferItem;
typedef enum {
    EXPLOSION_SMALL,
    EXPLOSION_FIREBALL,
    EXPLOSION_SMALL_MULTIPLE,
    EXPLOSION_BIG,
    EXPLOSION_UNK_4,
    EXPLOSION_UNK_17 = 0x11,
    EXPLOSION_UNK_19 = 0x13
} ExplosionTypes;
typedef u16 EInit[5];
extern EInit g_EInitSpawner;
typedef struct AnimateEntityFrame {
    u8 duration;
    u8 pose;
} AnimateEntityFrame;
typedef struct {
              u16 posX;
              u16 posY;
              u16 entityId;
              u16 entityRoomIndex;
              u16 params;
} LayoutEntity;
typedef struct {
    u8* unkPtr;
    s16 unk4;
    u16 priority;
} cloudData;
typedef struct {
               s32 unk0;
               s32 unk4;
               s32 unk8;
               s32 unkC;
} cloudStructUnk;
typedef struct {
    u16 u0, u1, u2, u3;
} MedusaCloudsUVal;
typedef struct {
    u8 u0, v0, u1, v1, u2, v2;
    u16 clut;
} ClockTowerData;
typedef struct {
    u8 u, v, w, h;
    u16 clut;
} ClockTowerData2;
typedef struct {
    s16 unk0;
    s16* unk4;
} unkStr_801CDD80;
typedef struct {
    s16 eArrayOffset;
    s16 eArrayParentOffset;
    u16 length;
    u16 params;
    u16 zOffset;
} giantBroBodyPartsInit;
typedef struct {
    u16 animSet;
    u16 unk5A;
    u16 palette;
    u16 blendMode;
    u8* animData;
} EntityConfig;
typedef struct {
    s16 top;
    s16 bottom;
    s16 left;
    s16 right;
} TileCollision;
typedef struct {
    s32 velocityX;
    s32 velocityY;
    s16 rotate;
    s16 unkA;
} dhuronUnkStruct;
typedef struct {
    EInit* unk0;
    s16 unk4;
    s16 unk6;
    s16 unk8;
    s16 unkA;
    u8 unkC;
} unkBookStruct;
typedef struct {
    s32 animSet;
    AnimationFrame* anim;
    s32 count;
    CVECTOR color;
} AnimParam;
typedef struct {
    u32 velocityX;
    u32 velocityY;
    s16 rotate;
} unkStr_80182100;
typedef struct {
    SVECTOR points[4];
    Point16 sxy[4];
    long p;
    long flag;
    CVECTOR primaryColor;
    CVECTOR color;
    MATRIX mat;
} NO4_SCRATCHPAD;
typedef struct {
    MATRIX m[2];
    SVECTOR vec[1];
    SVECTOR sp4c[2];
    s32 var_s3[18];
    s32 sp5c[9];
    CVECTOR sp50;
    u8 var_s5[1];
} ST0_SCRATCHPAD;
extern u16 g_ItemIconSlots[32];
void InitRoomEntities(s32 objLayoutId);
void UpdateRoomPosition();
void Update(void);
void UpdateStageEntities();
void HitDetection(void);
s32 Random();
void DestroyEntity(Entity*);
void DestroyEntitiesFromIndex(s16 index);
void FallEntity(void);
Entity* AllocEntity(Entity* start, Entity* end);
void InitializeEntity(u16 arg0[]);
typedef enum EntityID {
               E_NONE,
               E_FACTORY,
               E_EXPLOSION,
               E_PRIZE_DROP,
               E_NUMERIC_DAMAGE,
               E_RED_DOOR,
               E_INTENSE_EXPLOSION,
               E_SOUL_STEAL_ORB,
               E_ROOM_FOREGROUND,
               E_STAGE_NAME_POPUP,
               E_EQUIP_ITEM_DROP,
               E_RELIC_ORB,
               E_HEART_DROP,
               E_ENEMY_BLOOD,
               E_MESSAGE_BOX,
               E_ID_13,
               E_EXPLOSION_VARIANTS = 0x14,
               E_GREY_PUFF,
               E_ID_17 = 0x17,
               E_ID_21 = 0x21,
               E_ID_23 = 0x23,
               E_ID_24 = 0x24,
               E_RICHTER = 64,
               E_ID_41,
               E_ID_42,
               E_ID_43,
               E_ID_44,
               E_ID_90 = 0x90,
} EntityID;
typedef enum RicSteps {
               PL_S_STAND = 1,
               PL_S_WALK,
               PL_S_CROUCH,
               PL_S_FALL,
               PL_S_JUMP,
               PL_S_5,
               PL_S_6,
               PL_S_7,
               PL_S_HIGHJUMP,
               PL_S_9,
               PL_S_HIT,
               PL_S_11,
               PL_S_BOSS_GRAB,
               PL_S_13,
               PL_S_14,
               PL_S_15,
               PL_S_DEAD,
               PL_S_17,
               PL_S_STAND_IN_AIR,
               PL_S_FLAME_WHIP,
               PL_S_HYDROSTORM,
               PL_S_THROW_DAGGERS,
               PL_S_DEAD_PROLOGUE,
               PL_S_SLIDE,
               PL_S_BLADEDASH,
               PL_S_RUN,
               PL_S_SLIDE_KICK,
               PL_S_SUBWPN_CRASH,
               PL_S_28,
               PL_S_29,
               PL_S_30,
               PL_S_31,
               PL_S_INIT,
               PL_S_ENDING_1 = 0x40,
               PL_S_ENDING2 = 0x50,
               PL_S_ENDING_3 = 0x60,
               PL_S_ENDING_4 = 0x70,
               PL_S_DEBUG = 0xF0,
} BO6_RicSteps;
enum RicTimers {
    PL_T_POISON,
    PL_T_CURSE,
    PL_T_2,
    PL_T_3,
    PL_T_4,
    PL_T_5,
    PL_T_6,
    PL_T_7,
    PL_T_8,
    PL_T_ATTACK,
    PL_T_10,
    PL_T_RUN,
    PL_T_12,
    PL_T_INVINCIBLE_SCENE,
    PL_T_INVINCIBLE,
    PL_T_AFTERIMAGE_DISABLE,
};
enum RicBlueprints {
    BP_SKID_SMOKE,
    BP_SMOKE_PUFF,
    BP_SUBWPN_CROSS,
    BP_SUBWPN_CROSS_PARTICLES,
    BP_EMBERS,
    BP_5,
    BP_SUBWPN_HOLYWATER,
    BP_HOLYWATER_FIRE,
    BP_HIT_BY_FIRE,
    BP_HOLYWATER_FLAMES,
    BP_WHIP,
    BP_MULTIPLE_EMBERS,
    BP_HYDROSTORM,
    BP_CRASH_CROSS,
    BP_CRASH_CROSSES_ONLY,
    BP_NOT_IMPLEMENTED_1,
    BP_NOT_IMPLEMENTED_2,
    BP_ARM_BRANDISH_WHIP,
    BP_18,
    BP_AXE,
    BP_20,
    BP_NOT_IMPLEMENTED_3,
    BP_REVIVAL_COLUMN,
    BP_MARIA_POWERS_APPLIED,
    BP_SLIDE,
    BP_25,
    BP_BLADE_DASH,
    BP_BLUE_CIRCLE,
    BP_BLUE_SPHERE,
    BP_MARIA,
    BP_MARIA_POWERS_INVOKED,
    BP_31,
    BP_NOT_IMPLEMENTED_4,
    BP_RIC_BLINK,
    BP_CRASH_CROSS_PARTICLES,
    BP_35,
    BP_36,
    BP_37,
    BP_38,
    BP_39,
    BP_HOLYWATER_GLASS,
    BP_CRASH_AXE,
    BP_42,
    BP_SUBWPN_DAGGER,
    BP_CRASH_DAGGER,
    BP_HIGH_JUMP,
    BP_HIT_BY_CUT,
    BP_HIT_BY_ICE,
    BP_HIT_BY_THUNDER,
    BP_VIBHUTI,
    BP_REBOUND_STONE,
    BP_AGUNEA,
    BP_AGUNEA_HIT_ENEMY,
    BP_DEATH_BY_FIRE,
    BP_CRASH_VITHUBI,
    BP_VITHUBI_CRASH_CLOUD,
    BP_CRASH_REBOUND_STONE,
    BP_57,
    BP_CRASH_REBOUND_STONE_EXPLOSION,
    BP_CRASH_BIBLE,
    BP_CRASH_BIBLE_BEAM,
    BP_BIBLE,
    BP_BIBLE_TRAIL,
    BP_SUBWPN_STOPWATCH,
    BP_STOPWATCH_CIRCLE,
    BP_CRASH_STOPWATCH,
    BP_66,
    BP_CRASH_AGUNEA,
    BP_CRASH_AGUNEA_THUNDER,
    BP_CRASH_REBOUND_STONE_PARTICLES,
    BP_HIT_BY_DARK,
    BP_HIT_BY_HOLY,
    BP_AGUNEA_THUNDER,
    BP_CRASH_STOPWATCH_LIGHTNING,
    BP_SMOKE_PUFF_2,
    BP_SKID_SMOKE_2,
    BP_SKID_SMOKE_3,
    BP_TELEPORT,
    NUM_BLUEPRINTS,
};
enum RicSubweapons {
    PL_W_NONE,
    PL_W_DAGGER,
    PL_W_AXE,
    PL_W_HOLYWATER,
    PL_W_CROSS,
    PL_W_BIBLE,
    PL_W_STOPWATCH,
    PL_W_REBNDSTONE,
    PL_W_VIBHUTI,
    PL_W_AGUNEA,
    PL_W_10,
    PL_W_HOLYWATER_FLAMES,
    PL_W_CRASH_CROSS,
    PL_W_CRASH_CROSS_BEAM,
    PL_W_WHIP,
    PL_W_15,
    PL_W_HYDROSTORM,
    PL_W_BIBLE_BEAM,
    PL_W_KICK,
    PL_W_19,
    PL_W_20,
    PL_W_21,
    PL_W_HIGHJUMP,
    PL_W_23,
    PL_W_CRASH_VIBHUTI,
    PL_W_CRASH_REBOUND_STONE,
    PL_W_CRASH_AGUNEA,
    PL_W_27,
    PL_W_28,
    PL_W_CRASH_REBOUND_EXPLOSION,
    PL_W_30,
    NUM_WEAPONS,
};
extern PlayerState g_Ric;
;
;
;
;
;
;
;
extern AnimationFrame D_us_80181EDC[];
void func_us_801C13A8(Entity* self) {
    s16 params = self->params & 0x7F00;
    switch (self->step) {
    case 0:
        self->flags = FLAG_UNK_20000000 | FLAG_POS_CAMERA_LOCKED;
        self->unk5A = 0x79;
        self->animSet = (14);
        self->zPriority = g_Entities[64].zPriority + 6;
        self->palette = ((0x25E) | 0x8000);
        self->blendMode = BLEND_TRANSP | BLEND_QUARTER;
        self->drawFlags = ENTITY_SCALEY | ENTITY_SCALEX;
        self->scaleX = self->scaleY = 0xC0;
        self->anim = D_us_80181EDC;
        if (params) {
            self->scaleX = self->scaleY = 0x80;
            self->anim = D_us_80181EDC;
        }
        self->velocityY = -((s32)((0.25) * 65536.0));
        self->step++;
        break;
    case 1:
        self->posY.val += self->velocityY;
        if (self->poseTimer < 0) {
            DestroyEntity(self);
        }
        break;
    }
}
;
;
extern s16 D_us_80182870[];
void func_us_801C2688(Entity* entity) {
    if (g_Ric.unk46 == 0) {
        DestroyEntity(entity);
        return;
    }
    if (entity->step == 0) {
        entity->flags = FLAG_UNK_10000000 | FLAG_POS_CAMERA_LOCKED;
    }
    if (!(entity->params & 0xFF00)) {
        g_Entities[D_us_80182870[entity->poseTimer]].palette = ((0x240) | 0x8000);
    }
    g_Entities[D_us_80182870[entity->poseTimer]].ext.player.unkA4 = 4;
    entity->poseTimer++;
    if (entity->poseTimer == 15) {
        DestroyEntity(entity);
    }
}
void func_us_801C277C(void) {}
void func_us_801C2784(void) {}
;
;
;
extern void BO6_DebugShowWaitInfo(const char* msg);
void BO6_DebugInputWait(const char* msg) {
    while (PadRead(0)) {
        BO6_DebugShowWaitInfo(msg);
    }
    while (PadRead(0) == 0) {
        BO6_DebugShowWaitInfo(msg);
    }
}
static s32 BO6_RicCheckHolyWaterCollision(s16 baseY, s16 baseX) {
    Collider collider;
    Collider collider2;
    s16 maskedEffects;
    s16 maskedEffects2;
    s16 posX;
    s16 posY;
    s16 newPosY;
    if ((g_CurrentEntity->posX.val + baseX) < 0 ||
        (g_CurrentEntity->posX.i.hi + baseX) > 256) {
        if ((g_CurrentEntity->posY.i.hi + baseY) >= 212) {
            g_CurrentEntity->posY.i.hi = 212 - baseY;
            return EFFECT_SOLID;
        }
        return EFFECT_NONE;
    }
    posX = g_CurrentEntity->posX.i.hi + baseX;
    posY = g_CurrentEntity->posY.i.hi + baseY;
    g_api.CheckCollision(posX, posY, &collider, 0);
    maskedEffects = collider.effects &
                    (EFFECT_UNK_8000 | EFFECT_UNK_4000 | EFFECT_UNK_2000 |
                     EFFECT_UNK_1000 | EFFECT_UNK_0800 | EFFECT_SOLID);
    posY = posY - 1 + collider.unk18;
    g_api.CheckCollision(posX, posY, &collider2, 0);
    newPosY = baseY + (g_CurrentEntity->posY.i.hi + collider.unk18);
    if ((maskedEffects & (EFFECT_UNK_8000 | EFFECT_UNK_0800 | EFFECT_SOLID)) ==
            EFFECT_SOLID ||
        (maskedEffects & (EFFECT_UNK_8000 | EFFECT_UNK_0800 | EFFECT_SOLID)) ==
            (EFFECT_UNK_0800 | EFFECT_SOLID)) {
        maskedEffects = collider2.effects &
                        (EFFECT_UNK_8000 | EFFECT_UNK_4000 | EFFECT_UNK_2000 |
                         EFFECT_UNK_1000 | EFFECT_SOLID);
        if (!(maskedEffects & EFFECT_SOLID)) {
            g_CurrentEntity->posY.i.hi = newPosY;
            return EFFECT_SOLID;
        }
        if (((s32)collider2.effects & (EFFECT_UNK_8000 | EFFECT_SOLID)) ==
            (EFFECT_UNK_8000 | EFFECT_SOLID)) {
            g_CurrentEntity->posY.i.hi = newPosY - 1 + collider2.unk18;
            return maskedEffects;
        }
        return EFFECT_NONE;
    }
    if ((maskedEffects & (EFFECT_UNK_8000 | EFFECT_SOLID)) ==
        (EFFECT_UNK_8000 | EFFECT_SOLID)) {
        g_CurrentEntity->posY.i.hi = newPosY;
        return maskedEffects &
               (EFFECT_UNK_8000 | EFFECT_UNK_4000 | EFFECT_UNK_2000 |
                EFFECT_UNK_1000 | EFFECT_SOLID);
    }
    return EFFECT_NONE;
}
static int func_8016840C() { return EFFECT_NONE; }
extern EInit D_us_80180460;
void BO6_RicEntitySubwpnHolyWater(Entity* self) {
    s16 xMod;
    s32 colRes;
    if (self->step > 2) {
        self->posY.i.hi += 5;
    }
    switch (self->step) {
    case 0:
        self->ext.holywater.subweaponId = PL_W_HOLYWATER;
        InitializeEntity(D_us_80180460);
        self->flags = FLAG_POS_CAMERA_LOCKED;
        self->animSet = ((3) | 0x8000);
        self->animCurFrame = 0x23;
        self->zPriority = g_Entities[64].zPriority + 2;
        self->unk5A = 0x24;
        self->palette = ((0x22F) | 0x8000);
        xMod = 0;
        if (self->facingLeft) {
            xMod = -xMod;
        }
        self->posX.i.hi += xMod;
        self->posY.i.hi += -16;
        self->ext.holywater.angle = (rand() & 0x7F) + ((s32)(((s32)((309.375) * 4096.0)) / 360));
        if (g_Entities[64].facingLeft == true) {
            self->ext.holywater.angle = (rand() & 0x7F) + ((s32)(((s32)((219.375) * 4096.0)) / 360));
        }
        self->velocityX =
            (((s32)(rcos(self->ext.holywater.angle)) << 4) * ((s32)((3.0 / 128.0) * 65536.0))) >>
            8;
        self->velocityY =
            -(((s32)(rsin(self->ext.holywater.angle)) << 4) * ((s32)((3.0 / 128.0) * 65536.0))) >>
            8;
        self->hitboxWidth = 4;
        self->hitboxHeight = 4;
        self->ext.holywater.unk80 = 0x200;
        self->step = 1;
        break;
    case 1:
        self->posY.val += self->velocityY;
        colRes = BO6_RicCheckHolyWaterCollision(0, 0);
        self->posX.val += self->velocityX;
        if ((colRes & EFFECT_SOLID) || (self->hitFlags != 0)) {
            BO6_RicCreateEntFactoryFromEntity(self, 0x28, 0);
            g_api.PlaySfx(SFX_RIC_HOLY_WATER_ATTACK);
            self->ext.holywater.timer = 80;
            self->animSet = 0;
            self->step = 3;
            self->velocityX >>= 2;
        } else if (self->flags & FLAG_DEAD) {
            BO6_RicCreateEntFactoryFromEntity(self, 0x28, 0);
            g_api.PlaySfx(SFX_RIC_HOLY_WATER_ATTACK);
            self->ext.holywater.timer = 80;
            self->animSet = 0;
            self->step = 3;
            self->velocityX = -((s32)self->velocityX >> 2);
        }
        break;
    case 2:
        if (self->flags & FLAG_DEAD) {
            DestroyEntity(self);
            return;
        }
        if (--self->ext.holywater.timer == 0) {
            self->velocityX >>= 2;
            self->ext.holywater.timer = 80;
            self->step++;
        }
        break;
    case 3:
        if (self->flags & FLAG_DEAD) {
            self->velocityX = 0;
        }
        if (!(self->ext.holywater.timer & 3)) {
            BO6_RicCreateEntFactoryFromEntity(
                self, ((BP_HOLYWATER_FIRE) + (self->ext.holywater.unk82 << 16)), 0);
            self->ext.holywater.unk82 += 1;
            self->velocityX -= (self->velocityX / 32);
        }
        self->posX.val += self->velocityX;
        colRes = BO6_RicCheckHolyWaterCollision(6, 0);
        if (!(colRes & EFFECT_SOLID)) {
            self->velocityX >>= 1;
            self->step++;
        }
        break;
    case 4:
        if (self->flags & FLAG_DEAD) {
            self->velocityX = 0;
        }
        if (!(self->ext.holywater.timer & 3)) {
            BO6_RicCreateEntFactoryFromEntity(
                self, ((BP_HOLYWATER_FIRE) + (self->ext.holywater.unk82 << 16)), 0);
            self->ext.holywater.unk82 += 1;
        }
        self->velocityY += ((s32)((12.0 / 128) * 65536.0));
        if (self->velocityY > ((s32)((4) * 65536.0))) {
            self->velocityY = ((s32)((4) * 65536.0));
        }
        self->posY.val += self->velocityY;
        colRes = BO6_RicCheckHolyWaterCollision(0, 0);
        self->posX.val += self->velocityX;
        xMod = 4;
        if (self->velocityX < 0) {
            xMod = -xMod;
        }
        colRes |= func_8016840C(-7, xMod);
        if (colRes & EFFECT_SOLID) {
            self->velocityX <<= 1;
            self->step--;
        }
        break;
    case 5:
        break;
    }
    if (self->step > 2) {
        if (--self->ext.holywater.timer < 0) {
            DestroyEntity(self);
            return;
        }
        if (self->ext.holywater.timer == 2) {
            self->step = 5;
        }
        self->posY.i.hi -= 5;
        self->animCurFrame = 0;
    }
    g_Ric.timers[PL_T_3] = 2;
    self->hitFlags = 0;
    self->flags &= ~FLAG_DEAD;
    FntPrint("judge:%02x\n", self->hitboxState);
}
;
;
extern EInit D_us_80180454;
extern s16 D_us_801D10C8;
extern AnimationFrame anim_cross_boomerang[];
extern Point16 D_us_801D08C4[4][128];
extern s32 D_us_801D10C4;
void BO6_RicEntitySubwpnCross(Entity* self) {
    s16 playerHitboxX;
    s16 playerHitboxY;
    s16 rotate;
    s16* psp_s1;
    s32 xAccel;
    rotate = self->rotate;
    switch (self->step) {
    case 0:
        self->ext.crossBoomerang.subweaponId = PL_W_CROSS;
        InitializeEntity(D_us_80180454);
        self->flags =
            FLAG_UNK_20000000 | FLAG_UNK_10000000 | FLAG_POS_CAMERA_LOCKED;
        D_us_801D10C8 = self->hitboxState;
        self->ext.crossBoomerang.unk84 = D_us_801D08C4[D_us_801D10C4];
        D_us_801D10C4++;
        D_us_801D10C4 &= 3;
        BO6_RicCreateEntFactoryFromEntity(self, BP_5, 0);
        self->animSet = ((4) | 0x8000);
        self->unk5A = 0x44;
        self->anim = anim_cross_boomerang;
        self->facingLeft = g_Entities[64].facingLeft;
        self->zPriority = g_Entities[64].zPriority;
        BO6_RicSetSpeedX(((s32)((3.5625) * 65536.0)));
        self->drawFlags = ENTITY_ROTATE;
        self->rotate = ((s32)(((s32)((270) * 4096.0)) / 360));
        self->hitboxWidth = 8;
        self->hitboxHeight = 8;
        self->posY.i.hi -= 8;
        g_api.PlaySfx(SFX_RIC_CRASH_CROSS);
        self->step = 1;
        break;
    case 1:
        if (g_Entities[64].pose == 1) {
            self->step++;
        }
    case 2:
        self->rotate -= ((s32)(((s32)((11.25) * 4096.0)) / 360));
        self->posX.val += self->velocityX;
        if (self->facingLeft) {
            xAccel = ((s32)((-1.0 / 16) * 65536.0));
        } else {
            xAccel = ((s32)((1.0 / 16) * 65536.0));
        }
        self->velocityX -= xAccel;
        if (abs(self->velocityX) < ((s32)((0.75) * 65536.0))) {
            self->step = 3;
        }
        if ((self->hitFlags == 2) || (self->flags & FLAG_DEAD)) {
            if (self->velocityX < 0) {
                self->velocityX = ((s32)((-0.03125) * 65536.0));
            } else {
                self->velocityX = ((s32)((0.03125) * 65536.0));
            }
            self->ext.crossBoomerang.timer = 30;
            self->step = 3;
            self->ext.crossBoomerang.timer = 16;
            self->hitboxState = 0;
        }
        break;
    case 3:
        self->rotate -= ((s32)(((s32)((22.50) * 4096.0)) / 360));
        self->posX.val += self->velocityX;
        if (self->facingLeft) {
            xAccel = ((s32)((-1.0 / 16) * 65536.0));
        } else {
            xAccel = ((s32)((1.0 / 16) * 65536.0));
        }
        if (self->hitFlags == 2 || (self->flags & FLAG_DEAD)) {
            if (self->facingLeft) {
                xAccel = ((s32)((-1.0 / 16) * 65536.0));
            } else {
                xAccel = ((s32)((1.0 / 16) * 65536.0));
            }
        }
        self->velocityX -= xAccel;
        if (abs(self->velocityX) > ((s32)((0.75) * 65536.0))) {
            self->step++;
        }
        break;
    case 4:
        if (self->facingLeft) {
            xAccel = ((s32)((-1.0 / 16) * 65536.0));
        } else {
            xAccel = ((s32)((1.0 / 16) * 65536.0));
        }
        self->velocityX -= xAccel;
        if (abs(self->velocityX) > ((s32)((2.5) * 65536.0))) {
            self->hitboxState = D_us_801D10C8;
            self->step++;
        }
    case 5:
        if (--self->ext.crossBoomerang.timer < 0 &&
            ((self->hitFlags == 2) || (self->flags & FLAG_DEAD))) {
            self->velocityY = ((s32)((-3.0) * 65536.0));
            self->ext.crossBoomerang.timer = 50;
            self->hitboxState = 0;
            self->step = 6;
            self->velocityX = -((s32)self->velocityX / 2);
        }
        playerHitboxX = (g_Entities[64].posX.i.hi + g_Entities[64].hitboxOffX);
        playerHitboxY = (g_Entities[64].posY.i.hi + g_Entities[64].hitboxOffY);
        if (abs(self->posX.i.hi - playerHitboxX) <
                g_Entities[64].hitboxWidth + self->hitboxWidth &&
            abs(self->posY.i.hi - playerHitboxY) <
                g_Entities[64].hitboxHeight + self->hitboxHeight) {
            self->step = 7;
            self->ext.crossBoomerang.timer = 32;
            return;
        }
        if ((self->facingLeft == 0 && self->posX.i.hi < -32) ||
            (self->facingLeft && self->posX.i.hi > 0x120)) {
            self->step = 7;
            self->ext.crossBoomerang.timer = 32;
            return;
        }
        self->rotate -= ((s32)(((s32)((11.25) * 4096.0)) / 360));
        self->posX.val += self->velocityX;
        break;
    case 6:
        if (--self->ext.crossBoomerang.timer == 0) {
            DestroyEntity(self);
            return;
        }
        self->velocityY += ((s32)((0.15625) * 65536.0));
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        self->rotate += ((s32)(((s32)((33.75) * 4096.0)) / 360));
        break;
    case 7:
        if (--self->ext.crossBoomerang.timer == 0) {
            DestroyEntity(self);
            return;
        }
        self->hitboxState = 0;
        self->animSet = 0;
        self->posX.val += self->velocityX;
        break;
    }
    self->ext.crossBoomerang.unk7E++;
    if (1 < self->step && self->step < 6) {
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 1) {
            BO6_RicCreateEntFactoryFromEntity
            (self, BP_SUBWPN_CROSS_PARTICLES, 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 4) {
            BO6_RicCreateEntFactoryFromEntity
            (self, ((BP_EMBERS) + (6 << 16)), 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 6) {
            BO6_RicCreateEntFactoryFromEntity
            (self, BP_SUBWPN_CROSS_PARTICLES, 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 8) {
            BO6_RicCreateEntFactoryFromEntity
            (self, ((BP_EMBERS) + (6 << 16)), 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 12) {
            BO6_RicCreateEntFactoryFromEntity
            (self, ((BP_EMBERS) + (6 << 16)), 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 11) {
            BO6_RicCreateEntFactoryFromEntity
            (self, BP_SUBWPN_CROSS_PARTICLES, 0);
        }
    }
    if ((g_GameTimer >> 1) & 1) {
        self->palette = ((0x1B0) | 0x8000);
    } else {
        self->palette = ((0x1B1) | 0x8000);
    }
    psp_s1 = (s16*)self->ext.crossBoomerang.unk84;
    psp_s1 = &psp_s1[self->ext.crossBoomerang.unk80 * 2];
    *psp_s1 = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
    psp_s1++;
    *psp_s1 = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
    self->ext.crossBoomerang.unk80++;
    self->ext.crossBoomerang.unk80 &= 0x3F;
    rotate ^= self->rotate;
    g_Ric.timers[PL_T_3] = 2;
    self->hitFlags = 0;
    self->flags &= ~FLAG_DEAD;
}
;
;
;
;
extern EInit D_us_80180490;
extern u8 D_us_8018299C[];
void BO6_RicEntityCrashAxe(Entity* self) {
    Primitive* primFirst;
    Primitive* prim;
    s16 angle1;
    s16 angle2;
    s16 angle3;
    s16 angle4;
    s32 mod;
    s32 i;
    u8 r;
    u8 g;
    u8 b;
    s16 angleMod;
    s16 x;
    s16 y;
    s16 angle;
    s32 pose;
    s32 velocity;
    s32 colorRef;
    mod = 21;
    switch (self->step) {
    case 0:
        self->ext.subwpnAxe.subweaponId = 2;
        InitializeEntity(D_us_80180490);
        self->primIndex = g_api.AllocPrimitives(PRIM_GT4, 5);
        if (self->primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags =
            FLAG_UNK_10000000 | FLAG_POS_CAMERA_LOCKED | FLAG_HAS_PRIMS;
        self->facingLeft = 0;
        self->ext.subwpnAxe.unk7C = ((self->params & 0xFF) << 9) + ((s32)(((s32)((270) * 4096.0)) / 360));
        self->posY.i.hi -= 12;
        prim = &g_PrimBuf[self->primIndex];
        i = 0;
        while (prim) {
            prim->tpage = 0x1C;
            prim->u0 = prim->v0 = prim->v1 = prim->u2 = 0;
            prim->u1 = prim->u3 = 0x18;
            prim->v2 = prim->v3 = 0x28;
            prim->priority = g_Entities[64].zPriority + 4;
            if (i != 0) {
                prim->drawMode = DRAW_UNK_100 | DRAW_TPAGE2 | DRAW_TPAGE |
                                 DRAW_HIDE | DRAW_COLORS | DRAW_TRANSP;
                self->ext.subwpnAxe.unk8C[i - 1] = 0;
                self->ext.subwpnAxe.unk90[i - 1] = 0;
                self->ext.subwpnAxe.unk94[i - 1] = 0;
            } else {
                prim->drawMode = DRAW_UNK_100 | DRAW_HIDE;
            }
            i++;
            prim = prim->next;
        }
        self->hitboxHeight = self->hitboxWidth = 12;
        self->ext.subwpnAxe.angle = (self->params & 0xFF) << 9;
        self->ext.subwpnAxe.velocity = 16;
        self->step = 1;
        break;
    case 1:
        velocity = self->ext.subwpnAxe.velocity;
        self->ext.subwpnAxe.velocity++;
        if (self->ext.subwpnAxe.velocity > 0x28) {
            self->ext.subwpnAxe.unkA2 = 16;
            self->step++;
        }
        angle = self->ext.subwpnAxe.angle;
        self->ext.subwpnAxe.angle += 0xC0;
        self->ext.subwpnAxe.unk7C += 0x80;
        self->velocityX = velocity * rcos(angle);
        self->velocityY = velocity * -rsin(angle);
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        break;
    case 2:
        if (--self->ext.subwpnAxe.unkA2 == 0) {
            self->ext.subwpnAxe.unkA2 = 8;
            self->step++;
        }
        velocity = self->ext.subwpnAxe.velocity;
        angle = self->ext.subwpnAxe.angle;
        self->ext.subwpnAxe.angle += 0xC0;
        self->ext.subwpnAxe.unk7C += 0x80;
        self->velocityX = rcos(angle) * velocity;
        self->velocityY = -rsin(angle) * velocity;
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        break;
    case 3:
        if (--self->ext.subwpnAxe.unkA2 == 0) {
            g_Ric.unk4E = 1;
            self->flags &= ~FLAG_UNK_10000000;
        }
        velocity = self->ext.subwpnAxe.velocity;
        self->ext.subwpnAxe.velocity += 2;
        angle = self->ext.subwpnAxe.angle;
        self->ext.subwpnAxe.angle += 0x28;
        self->ext.subwpnAxe.unk7C += 0x80;
        self->velocityX = rcos(angle) * velocity;
        self->velocityY = -rsin(angle) * velocity;
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        if (self->poseTimer == 0) {
            pose = self->pose;
            self->ext.subwpnAxe.unk8C[pose] = 0;
            self->ext.subwpnAxe.unk90[pose] = 1;
            self->ext.subwpnAxe.unk94[pose] = 1;
            pose++;
            pose &= 3;
            self->pose = pose;
            self->poseTimer = 2;
        } else {
            self->poseTimer--;
        }
        if ((self->hitFlags == 2) || (self->flags & FLAG_DEAD)) {
            self->velocityY = ((s32)((-3.0) * 65536.0));
            self->hitboxState = 0;
            self->step = 4;
            self->velocityX = -((s32)self->velocityX / 2);
        }
        break;
    case 4:
        if (self->facingLeft) {
            angleMod = 0xC0;
        } else {
            angleMod = -0xC0;
        }
        self->ext.subwpnAxe.unk7C += angleMod;
        self->velocityY += 0x2400;
        if (self->velocityY > ((s32)((8.0) * 65536.0))) {
            self->velocityY = ((s32)((8.0) * 65536.0));
        }
        self->posY.val += self->velocityY;
        self->posX.val += self->velocityX;
        if (self->posY.i.hi > 256) {
            DestroyEntity(self);
            return;
        }
        break;
    }
    prim = &g_PrimBuf[self->primIndex];
    primFirst = prim;
    pose = ((g_GameTimer >> 1) & 1) + 0x1AB;
    i = 0;
    while (prim != (0)) {
        prim->clut = pose;
        if (i == 0) {
            if (self->facingLeft) {
                angle1 = 0x800 - 0x2A0;
                angle2 = 0x2A0;
                angle3 = 0x800 + 0x2A0;
                angle4 = 0x800 + 0x800 - 0x2A0;
            } else {
                angle2 = 0x800 - 0x2A0;
                angle1 = 0x2A0;
                angle4 = 0x800 + 0x2A0;
                angle3 = 0x800 + 0x800 - 0x2A0;
            }
            x = self->posX.i.hi;
            y = self->posY.i.hi;
            angleMod = self->ext.subwpnAxe.unk7C;
            angle1 += angleMod;
            angle2 += angleMod;
            angle3 += angleMod;
            angle4 += angleMod;
            prim->x0 = x + +(((rcos(angle1) << 4) * mod) >> 0x10);
            prim->y0 = y + -(((rsin(angle1) << 4) * mod) >> 0x10);
            prim->x1 = x + +(((rcos(angle2) << 4) * mod) >> 0x10);
            prim->y1 = y + -(((rsin(angle2) << 4) * mod) >> 0x10);
            prim->x2 = x + +(((rcos(angle3) << 4) * mod) >> 0x10);
            prim->y2 = y + -(((rsin(angle3) << 4) * mod) >> 0x10);
            prim->x3 = x + +(((rcos(angle4) << 4) * mod) >> 0x10);
            prim->y3 = y + -(((rsin(angle4) << 4) * mod) >> 0x10);
            prim->drawMode &= ~DRAW_HIDE;
        } else if (self->ext.subwpnAxe.unk90[i - 1]) {
            if (self->ext.subwpnAxe.unk94[i - 1]) {
                self->ext.subwpnAxe.unk94[i - 1] = 0;
                prim->x0 = primFirst->x0;
                prim->y0 = primFirst->y0;
                prim->x1 = primFirst->x1;
                prim->y1 = primFirst->y1;
                prim->x2 = primFirst->x2;
                prim->y2 = primFirst->y2;
                prim->x3 = primFirst->x3;
                prim->y3 = primFirst->y3;
            }
            colorRef = (self->ext.subwpnAxe.unk8C[i - 1]++);
            if (colorRef < 10) {
                r = D_us_8018299C[colorRef * 4 + 0];
                g = D_us_8018299C[colorRef * 4 + 1];
                b = D_us_8018299C[colorRef * 4 + 2];
                prim->r0 = r;
                prim->g0 = g;
                prim->b0 = b;
                prim->r1 = r;
                prim->g1 = g;
                prim->b1 = b;
                prim->r2 = r;
                prim->g2 = g;
                prim->b2 = b;
                prim->r3 = r;
                prim->g3 = g;
                prim->b3 = b;
                prim->drawMode &= ~DRAW_HIDE;
            } else {
                self->ext.subwpnAxe.unk90[i - 1] = 0;
                prim->drawMode |= DRAW_HIDE;
            }
        }
        i++;
        prim = prim->next;
    }
}
;
void BO6_ReboundStoneBounce1(s32 arg0) {
    g_CurrentEntity->ext.reboundStone.stoneAngle =
        ((s32)(arg0 << 16) >> 15) -
        g_CurrentEntity->ext.reboundStone.stoneAngle;
    if (g_CurrentEntity->ext.reboundStone.unk82 == 0) {
        g_CurrentEntity->ext.reboundStone.unk80 += 1;
        g_CurrentEntity->ext.reboundStone.unk82 += 1;
    }
}
void BO6_ReboundStoneBounce2(s32 arg0) {
    Entity* entity = g_CurrentEntity;
    if (entity->ext.reboundStone.unk82 != 0)
        return;
    entity->ext.reboundStone.stoneAngle =
        ((s32)(arg0 << 16) >> 15) - entity->ext.reboundStone.stoneAngle;
    entity->ext.reboundStone.unk80++;
    entity->ext.reboundStone.unk82++;
}
;
;
u8 BO6_PrimDecreaseBrightness(Primitive2* prim, u8 amount) {
    s32 i, j;
    u8 isEnd = 0;
    struct SubPrim* subprim = &prim->prim[0];
    u8* pColor;
    for (i = 0; i < 4; i++) {
        for (j = 0; j < 3; j++) {
            pColor = &subprim->col[j];
            *pColor -= amount;
            if (*pColor < 16) {
                *pColor = 16;
            } else {
                isEnd |= 1;
            }
        }
        subprim++;
    }
    return isEnd;
}
;
;
extern AnimationFrame D_us_801829D4[];
void BO6_RicEntityVibhutiCrashCloud(Entity* self) {
    s32 angle;
    switch (self->step) {
    case 0:
        self->primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
        if (self->primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags = FLAG_POS_CAMERA_LOCKED | FLAG_HAS_PRIMS;
        self->posX.val = self->ext.vibCrashCloud.parent->ext.vibhutiCrash.x;
        self->posY.val = self->ext.vibCrashCloud.parent->ext.vibhutiCrash.y;
        self->facingLeft =
            self->ext.vibCrashCloud.parent->ext.vibhutiCrash.facing;
        self->flags |= FLAG_UNK_20000000;
        self->unk5A = 0x64;
        self->animSet = 0xE;
        self->palette = ((0x19E) | 0x8000);
        self->anim = D_us_801829D4;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = 0x60;
        self->hitboxWidth = 8;
        self->hitboxHeight = 8;
        angle = (rand() % 512) + 0x300;
        self->velocityX = rcos(angle) << 5;
        self->velocityY = -(rsin(angle) << 5);
        self->step++;
        break;
    case 1:
        self->ext.vibCrashCloud.unk7C++;
        if (self->ext.vibCrashCloud.unk7C > 38) {
            DestroyEntity(self);
        } else {
            self->posX.val += self->velocityX;
            self->posY.val += self->velocityY;
        }
        break;
    }
}
;
void func_us_801C8590(Entity *arg0)
{
    u16 step;
    step = arg0->step;
    switch (step) {
    case 0:
        arg0->flags = FLAG_UNK_10000000;
        arg0->hitboxWidth = 4;
        arg0->hitboxHeight = 4;
        arg0->step++;
        return;
    case 1:
        arg0->ext.subweapon.timer++;
        if (arg0->ext.subweapon.timer >= 4) {
            DestroyEntity(arg0);
        }
        return;
    default:
        return;
    }
}
extern s32 D_us_80182A0C[];
void func_us_801C8618(Entity* self) {
    PrimLineG2* prim;
    Primitive* prim2;
    s32 i;
    long angle;
    s32 var_s6;
    s32 var_s5;
    s32 var_s7;
    s32 brightness;
    switch (self->step) {
    case 0:
        self->primIndex = g_api.AllocPrimitives(PRIM_LINE_G2, 20);
        if (self->primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags = FLAG_UNK_10000000 | FLAG_HAS_PRIMS;
        prim = (PrimLineG2*)&g_PrimBuf[self->primIndex];
        for (i = 0; i < 4; i++) {
            prim->preciseX.val = g_Entities[64].posX.val;
            prim->preciseY.val = g_Entities[64].posY.val - ((s32)((40) * 65536.0));
            prim->priority = 194;
            prim->drawMode = DRAW_HIDE;
            prim->x0 = prim->x1 = g_Entities[64].posX.i.hi;
            prim->y0 = prim->y1 = g_Entities[64].posY.i.hi - 0x1C;
            prim->r0 = prim->g0 = prim->b0 = 0x80;
            prim->r1 = prim->g1 = prim->b1 = 0x70;
            prim->angle = D_us_80182A0C[i];
            prim->delay = 1;
            prim = (PrimLineG2*)prim->next;
        }
        for (brightness = 0x80; i < 20; i++) {
            if (!(i % 4)) {
                brightness -= 0x10;
                switch (i / 4) {
                case 1:
                    self->ext.et_8016D9C4.lines[0] = prim;
                    break;
                case 2:
                    self->ext.et_8016D9C4.lines[1] = prim;
                    break;
                case 3:
                    self->ext.et_8016D9C4.lines[2] = prim;
                    break;
                case 4:
                    self->ext.et_8016D9C4.lines[3] = prim;
                    break;
                }
            }
            prim->priority = 0xC2;
            prim->drawMode = DRAW_HIDE;
            prim->x0 = prim->x1 = g_Entities[64].posX.i.hi;
            prim->y0 = prim->y1 = g_Entities[64].posY.i.hi - 0x1C;
            prim->r0 = prim->g0 = prim->b0 = brightness;
            prim->r1 = prim->g1 = prim->b1 = brightness - 0x10;
            prim = (PrimLineG2*)prim->next;
        }
        self->ext.et_8016D9C4.unk90 = 4;
        self->ext.et_8016D9C4.unk8C = self->ext.et_8016D9C4.unk8E = 0;
        self->step++;
        break;
    case 1:
        self->ext.et_8016D9C4.unk8E = 1;
        switch (self->ext.et_8016D9C4.unk8C) {
        case 0:
            prim = (PrimLineG2*)&g_PrimBuf[self->primIndex];
            break;
        case 1:
            prim = self->ext.et_8016D9C4.lines[0];
            break;
        case 2:
            prim = self->ext.et_8016D9C4.lines[1];
            break;
        case 3:
            prim = self->ext.et_8016D9C4.lines[2];
            break;
        case 4:
            prim = self->ext.et_8016D9C4.lines[3];
            break;
        }
        for (i = 0; i < 4; i++) {
            prim->drawMode &= ~DRAW_HIDE;
            prim = (PrimLineG2*)prim->next;
        }
        self->ext.et_8016D9C4.unk8C++;
        if (self->ext.et_8016D9C4.unk8C > 4) {
            self->step++;
        }
        break;
    case 2:
        if (!self->ext.et_8016D9C4.unk90) {
            self->step++;
            break;
        }
        break;
    case 3:
        self->ext.et_8016D9C4.unk90++;
        if (self->ext.et_8016D9C4.unk90 > 4) {
            DestroyEntity(self);
            return;
        }
        break;
    }
    if (!self->ext.et_8016D9C4.unk8E) {
        return;
    }
    prim = (PrimLineG2*)&g_PrimBuf[self->primIndex];
    for (i = 0; i < 4; i++) {
        if (prim->delay) {
            prim->x1 = prim->x0;
            prim->y1 = prim->y0;
            prim->x0 = prim->preciseX.i.hi;
            prim->y0 = prim->preciseY.i.hi;
            var_s7 = ratan2(prim->preciseY.val, ((s32)((128) * 65536.0)) - prim->preciseX.val) &
                     0xFFF;
            angle = prim->angle - var_s7;
            if (labs(angle) > 0x800) {
                if (angle < 0) {
                    angle += 0x1000;
                } else {
                    angle -= 0x1000;
                }
            }
            if (angle >= 0) {
                if (angle > 0x80) {
                    var_s6 = 0x80;
                } else {
                    var_s6 = angle;
                }
                angle = var_s6;
            } else {
                if (angle < -0x80) {
                    var_s5 = -0x80;
                } else {
                    var_s5 = angle;
                }
                angle = var_s5;
            }
            prim->angle = prim->angle - angle;
            prim->angle &= 0xFFF;
            prim->velocityX.val = (rcos(prim->angle) << 4 << 4);
            prim->velocityY.val = -(rsin(prim->angle) << 4 << 4);
            prim->preciseX.val += prim->velocityX.val;
            prim->preciseY.val += prim->velocityY.val;
            self->posX.i.hi = prim->preciseX.i.hi;
            self->posY.i.hi = prim->preciseY.i.hi;
            BO6_RicCreateEntFactoryFromEntity
            (self, BP_CRASH_REBOUND_STONE_PARTICLES, 0);
            if (prim->preciseY.val < 0) {
                prim->delay = 0;
                prim->drawMode |= DRAW_HIDE;
                self->ext.et_8016D9C4.unk90--;
            }
        }
        prim = (PrimLineG2*)prim->next;
    }
    prim = self->ext.et_8016D9C4.lines[0];
    prim2 = &g_PrimBuf[self->primIndex];
    for (i = 0; i < 16; i++) {
        prim->x1 = prim->x0;
        prim->y1 = prim->y0;
        prim->x0 = prim2->x1;
        prim->y0 = prim2->y1;
        prim = (PrimLineG2*)prim->next;
        prim2 = prim2->next;
    }
}
;
;
;
;
;
void func_us_801CA340(Entity* self) {
    BO6_RicCreateEntFactoryFromEntity(self, ((0x3F) + (1 << 16)), 0);
    DestroyEntity(self);
}
;
;
;
;
;
;
void BO6_RicEntitySubwpnBibleTrail(Entity* entity) {
    Primitive* prim;
    switch (entity->step) {
    case 0:
        entity->primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
        if (entity->primIndex == -1) {
            DestroyEntity(entity);
            return;
        }
        entity->flags = FLAG_UNK_10000000 | FLAG_HAS_PRIMS;
        prim = &g_PrimBuf[entity->primIndex];
        prim->tpage = 0x1C;
        prim->clut = 0x19D;
        prim->u0 = prim->u2 = 0x20;
        prim->v0 = prim->v1 = 0;
        prim->u1 = prim->u3 = 0x30;
        prim->v2 = prim->v3 = 0x10;
        prim->x0 = prim->x2 = entity->posX.i.hi - 8;
        prim->x1 = prim->x3 = entity->posX.i.hi + 8;
        prim->y0 = prim->y1 = entity->posY.i.hi - 8;
        prim->y2 = prim->y3 = entity->posY.i.hi + 8;
        prim->priority = entity->zPriority;
        prim->drawMode = DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
        entity->ext.et_BibleSubwpn.unk7E = 0x60;
        entity->step++;
        break;
    case 1:
        entity->ext.et_BibleSubwpn.unk7C++;
        if (entity->ext.et_BibleSubwpn.unk7C > 5) {
            entity->step++;
        }
        entity->ext.et_BibleSubwpn.unk7E -= 8;
        break;
    case 2:
        DestroyEntity(entity);
        return;
    }
    prim = &g_PrimBuf[entity->primIndex];
    prim->r0 = prim->r1 = prim->r2 = prim->r3 = prim->g0 = prim->g1 = prim->g2 = prim->g3 = prim->b0 = prim->b1 = prim->b2 = prim->b3 = entity->ext.et_BibleSubwpn.unk7E;
}
;
;
;
;
