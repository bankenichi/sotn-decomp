/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO6:func_us_801A7DC0
   attempt: 2/4
   from   : m2c (no model call)
   origin : src/boss/bo6/cutscene.c
   verdict: quality reject: `Entity` has no member `unk30`; offset 0x30 is `params`

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
extern ? D_us_80180614;
extern ? D_us_80180618;
extern ? D_us_80180620;
extern ? D_us_80180624;
extern ? D_us_8018062C;
extern s8 D_us_8019A0C8;
extern s8 D_us_8019A0CC;
extern u8 D_us_8019A0D0;
extern u8 D_us_8019A2E1;
extern u8 D_us_8019A2FB;
extern ? PrizeDrops;
extern s32 g_IsCutsceneDone;

void func_us_801A7DC0(Entity *arg0) {
 s16 sp20;
 s16 sp22;
 s16 sp24;
 s16 sp26;
 Primitive *temp_s1_4;
 Primitive *temp_s1_5;
 Primitive *temp_s1_6;
 Primitive *temp_s1_7;
 Primitive *temp_s1_8;
 Primitive *var_s1;
 Primitive *var_s1_2;
 Primitive *var_s1_3;
 Primitive *var_s1_4;
 Primitive *var_s1_5;
 s16 temp_a0_2;
 s16 temp_a0_3;
 s16 temp_a1_3;
 s16 temp_a1_4;
 s16 temp_v0_10;
 s16 temp_v0_11;
 s16 temp_v0_12;
 s16 temp_v0_13;
 s16 temp_v0_14;
 s16 temp_v0_15;
 s16 temp_v0_16;
 s16 temp_v0_19;
 s16 temp_v0_20;
 s16 temp_v0_3;
 s16 temp_v0_6;
 s16 temp_v0_7;
 s16 temp_v0_9;
 s16 temp_v1_17;
 s16 temp_v1_18;
 s16 var_v1_4;
 s32 temp_v0_17;
 s32 temp_v0_5;
 s32 var_a0;
 s32 var_a0_2;
 s32 var_a0_3;
 s32 var_s0;
 s32 var_s0_2;
 s32 var_s0_3;
 s32 var_v0;
 s32 var_v0_3;
 s32 var_v1;
 s8 temp_v1_8;
 u16 temp_v1;
 u16 temp_v1_19;
 u16 temp_v1_21;
 u16 temp_v1_2;
 u16 temp_v1_3;
 u16 temp_v1_5;
 u32 temp_v1_4;
 u8 *temp_a1_2;
 u8 *temp_v0_2;
 u8 *temp_v0_4;
 u8 *temp_v1_10;
 u8 *temp_v1_11;
 u8 *temp_v1_12;
 u8 *temp_v1_14;
 u8 *temp_v1_15;
 u8 *temp_v1_16;
 u8 *temp_v1_6;
 u8 *temp_v1_7;
 u8 *var_v1_3;
 u8 temp_a0;
 u8 temp_a1;
 u8 temp_a2;
 u8 temp_s0;
 u8 temp_t2;
 u8 temp_v0;
 u8 temp_v0_18;
 u8 temp_v0_8;
 u8 temp_v1_13;
 u8 temp_v1_20;
 u8 var_v0_2;
 u8 var_v0_4;
 u8 var_v0_5;
 u8 var_v1_2;
 void *temp_s1;
 void *temp_s1_2;
 void *temp_s1_3;
 void *temp_v1_9;

 var_s0 = saved_reg_s0;
 if (arg0->step != 0) {
  if ((g_IsCutsceneDone != 0) && (g_SkipCutscene == 0)) {
   if (g_GameClearFlag == 0) {
    temp_v1 = arg0->params;
    switch (temp_v1) {  /* switch 1; irregular */
    default:  /* switch 1 */
     var_v1 = 0x20000;
     if (temp_v1 != 3) {

     } else {
block_13:
      var_v0 = g_Settings.D_8003CB04 & var_v1;
block_14:
      if (var_v0 != 0) {
       goto block_15;
      }
     }
     break;
    case 0:  /* switch 1 */
     var_v0 = g_Settings.D_8003CB04 & 0x8000;
     goto block_14;
    case 2:  /* switch 1 */
     var_v1 = 0x10000;
     goto block_13;
    }
   } else {
block_15:
    CutsceneSkip(arg0);
   }
  }
  if ((arg0->step != 0) && (g_Dialogue.hasEvents != 0)) {
   RunCutsceneEvents();
  }
 }
 temp_v1_2 = arg0->step;
 switch (temp_v1_2) {  /* switch 2 */
 case 0:  /* switch 2 */
  temp_v1_3 = arg0->params;
  if (temp_v1_3 != 1) {
   if ((s32) temp_v1_3 < 2) {
    if (temp_v1_3 != 0) {
     goto block_38;
    }
    if ((g_DemoMode == Demo_None) && (g_CastleFlags[0x95] == 0) && (g_PlayableCharacter == 0)) {
     temp_v0 = SetCutsceneScript(&D_us_8019A0D0);
     D_us_8019A0C8 = 0;
     var_s0 = temp_v0 & 0xFF;
     if (g_CastleFlags[0xD8] != 0) {
      D_us_8019A0C8 = 1;
     }
     D_us_8019A0CC = 0;
     if (g_api_CheckEquipmentItemCount(0x22U, 1U) != 0) {
      D_us_8019A0CC = 1;
     }
     goto block_38;
    }
    goto block_120;
   }
   if ((s32) temp_v1_3 < 4) {
    if ((g_DemoMode == Demo_None) && (g_CastleFlags[0x95] == 0)) {
     var_s0 = SetCutsceneScript(&D_us_8019A2FB) & 0xFF;
     D_us_8019A0CC = (u8) arg0->unk30 + 0xFE;
     goto block_38;
    }
block_120:
    DestroyEntity(arg0);
    return;
   }
   goto block_38;
  }
  var_s0 = SetCutsceneScript(&D_us_8019A2E1) & 0xFF;
block_38:
  if (var_s0 != 0) {
   g_CutsceneHasControl = 1;
   arg0->flags |= 0x802000;
   arg0->step += 1;
   g_CutsceneFlags = 0;
   g_IsCutsceneDone = 0;
   g_SkipCutscene = 0;
   arg0->primIndex = g_Dialogue.primIndex[2];
   arg0->flags |= 0x10000;
   return;
  }
 default:  /* switch 2 */
  return;
 case 1:  /* switch 2 */
 case 13:  /* switch 3 */
loop_41:
  if ((g_Dialogue.nextCharTimer == 0) || (g_SkipCutscene != 0)) {
   temp_v0_2 = g_Dialogue.scriptCur;
   g_Dialogue.scriptCur = temp_v0_2 + 1;
   temp_a2 = temp_v0_2->unk0;
   temp_v1_4 = temp_a2 & 0xFFFF;
   switch (temp_v1_4) {  /* switch 3 */
   case 0:  /* switch 3 */
    arg0->step = 7;
    return;
   case 1:  /* switch 3 */
    if (g_SkipCutscene == 0) {
     g_Dialogue.nextCharX = (s16) (&g_Dialogue.nextCharTimer)[-0xC].unk2;
     if (!((&g_Dialogue.nextCharTimer)[-0xC].unk8 & 1)) {
      (&g_Dialogue.nextCharTimer)[-0xC].unk-4 = (s16) ((&g_Dialogue.nextCharTimer)[-0xC].unk-4 + 0xC);
     }
     temp_v0_3 = (&g_Dialogue.nextCharTimer)[-0xC].unk4 + 1;
     (&g_Dialogue.nextCharTimer)[-0xC].unk4 = temp_v0_3;
     if (temp_v0_3 >= 5) {
      (&g_Dialogue.nextCharTimer)[-0xC].unk4 = 0;
     }
     CutsceneUnk4();
     temp_v1_5 = (&g_Dialogue.nextCharTimer)[-0xC].unk8;
     if (!(temp_v1_5 & 1)) {
      if ((&g_Dialogue.nextCharTimer)[-0xC].unk4 >= 4) {
       (&g_Dialogue.nextCharTimer)[-0xC].unk8 = (s16) (temp_v1_5 | 1);
       goto block_54;
      }
      goto loop_41;
     }
block_54:
     (&g_Dialogue.nextCharTimer)[-0xC].unk6 = 0;
     arg0->step_s = 0;
     arg0->step += 1;
     return;
    }
    goto loop_41;
   case 2:  /* switch 3 */
    temp_v0_4 = g_Dialogue.scriptCur;
    g_Dialogue.scriptCur = temp_v0_4 + 1;
    g_Dialogue.unk17 = temp_v0_4->unk0;
    goto loop_41;
   case 3:  /* switch 3 */
    temp_v1_6 = g_Dialogue.scriptCur;
    g_Dialogue.scriptCur = temp_v1_6 + 1;
    g_Dialogue.nextCharTimer = temp_v1_6->unk0;
    if (g_SkipCutscene == 0) {
     return;
    }
    goto loop_41;
   case 4:  /* switch 3 */
    if (g_SkipCutscene == 0) {
     var_s1 = g_Dialogue.prim[0];
     var_s0_2 = 1;
     do {
      var_s1->drawMode = 8;
      var_s1 = var_s1->next;
      var_s0_2 += 1;
     } while (var_s0_2 < 5);
     return;
    }
    goto loop_41;
   case 5:  /* switch 3 */
    if (g_SkipCutscene == 0) {
     temp_v1_7 = g_Dialogue.scriptCur;
     g_Dialogue.scriptCur = temp_v1_7 + 1;
     temp_s0 = temp_v1_7->unk0;
     g_Dialogue.scriptCur = temp_v1_7 + 2;
     temp_t2 = temp_v1_7->unk1;
     temp_s1 = (&g_Dialogue.nextCharTimer)[-0x16].unk2C;
     temp_v0_5 = temp_t2 & 1;
     temp_a0 = *(&PrizeDrops + temp_v0_5);
     temp_a1 = *(&D_us_80180614 + temp_v0_5);
     temp_s1->unk1A = 0x94;
     temp_s1->unkE = (u16) *(&D_us_80180618 + (temp_s0 * 2));
     if (temp_t2 & 0x80) {
      var_v1_2 = temp_a0;
      var_v0_2 = var_v1_2 + 0x2F;
     } else {
      var_v0_2 = temp_a0;
      var_v1_2 = var_v0_2 + 0x2F;
     }
     temp_s1->unk24 = var_v0_2;
     temp_s1->unkC = var_v0_2;
     temp_s1->unk30 = var_v1_2;
     temp_s1->unk18 = var_v1_2;
     temp_v1_8 = temp_a1 + 0x48;
     temp_s1->unk19 = temp_a1;
     temp_s1->unkD = temp_a1;
     temp_s1->unk31 = temp_v1_8;
     temp_s1->unk25 = temp_v1_8;
     temp_v0_6 = (u16) g_Dialogue.startX - 0x1E;
     temp_s1->unk2C = temp_v0_6;
     temp_s1->unk20 = temp_v0_6;
     temp_s1->unk14 = temp_v0_6;
     temp_s1->unk8 = temp_v0_6;
     temp_v0_7 = (&g_Dialogue.nextCharTimer)[-0x12].unk4 + 0x24;
     temp_s1->unk2E = temp_v0_7;
     temp_s1->unk22 = temp_v0_7;
     temp_s1->unk16 = temp_v0_7;
     temp_s1->unkA = temp_v0_7;
     (&g_Dialogue.nextCharTimer)[-0x12].unk10 = (u16) *(&D_us_80180624 + (temp_s0 * 2));
     CutsceneUnk1();
     CutsceneUnk4();
     temp_s1->unk26 = 0x1FE;
     temp_s1->unk32 = 0;
     DrawCutsceneActorName(temp_s0 & 0xFFFF, arg0);
     (&g_Dialogue.nextCharTimer)[-0x12].unkC = 6;
     arg0->step = 3;
     return;
    }
block_76:
    g_Dialogue.scriptCur += 2;
    goto loop_41;
   case 6:  /* switch 3 */
    if (g_SkipCutscene == 0) {
     var_s1_2 = g_Dialogue.prim[0];
     var_s0_3 = 1;
     do {
      var_s1_2->drawMode = 8;
      var_s1_2 = var_s1_2->next;
      var_s0_3 += 1;
     } while (var_s0_3 < 5);
     g_api_FreePrimitives(g_Dialogue.primIndex[1]);
     g_Dialogue.primIndex[1] = -1;
     g_Dialogue.portraitAnimTimer = 6;
     arg0->step = 4;
     return;
    }
    goto loop_41;
   case 7:  /* switch 3 */
    if (g_SkipCutscene == 0) {
     temp_v1_9 = (&g_Dialogue.nextCharTimer)[-0x12].unk-4;
     (&g_Dialogue.n