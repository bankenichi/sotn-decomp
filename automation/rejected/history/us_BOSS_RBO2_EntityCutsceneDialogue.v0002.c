/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/RBO2:EntityCutsceneDialogue
   attempt: 2/4
   from   : m2c (no model call)
   origin : src/boss/rbo2/e_cutscene_dialogue.c
   verdict: quality reject: candidate is not usable C: unbalanced braces: 4 unclosed `{`

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
extern ? D_us_80180B60;
extern ? D_us_80180B64;
extern ? D_us_80180B68;
extern ? D_us_80180B6C;
extern ? D_us_80180B70;
extern ? D_us_80180B78;
extern u8 D_us_80181878;
extern s32 D_us_801AE850;
extern s16 D_us_801AE858;
extern u16 D_us_801AE85E;
extern s16 D_us_801AE862;
extern s16 D_us_801AE864;
extern ? D_us_801AE86A;
extern u8 D_us_801AE86B;
extern void *D_us_801AE86C;
extern void *D_us_801AE880;
extern ? D_us_801AE884;
extern s32 D_us_801AE888;
extern s32 D_us_801AE88C;
extern u16 D_us_801AE890;
extern s32 D_us_801AE904;
extern u16 g_pads_0_tapped;

void EntityCutsceneDialogue(Entity *arg0) {
 s16 sp20;
 s16 sp22;
 s16 sp24;
 s16 sp26;
 Primitive *var_s1_3;
 Primitive *var_s1_4;
 Primitive *var_s1_5;
 s16 temp_v0_10;
 s16 temp_v0_13;
 s16 temp_v0_14;
 s16 temp_v0_15;
 s16 temp_v0_18;
 s16 temp_v0_5;
 s16 temp_v0_6;
 s16 temp_v0_8;
 s16 var_v1_3;
 s32 temp_v0_16;
 s32 temp_v0_4;
 s32 var_a0;
 s32 var_a0_2;
 s32 var_a0_3;
 s32 var_s0;
 s32 var_s0_2;
 s32 var_v0_2;
 s8 temp_v1_6;
 u16 temp_a0_2;
 u16 temp_a0_3;
 u16 temp_a1_3;
 u16 temp_a1_4;
 u16 temp_v0_11;
 u16 temp_v0_12;
 u16 temp_v0_19;
 u16 temp_v0_2;
 u16 temp_v0_9;
 u16 temp_v1;
 u16 temp_v1_15;
 u16 temp_v1_16;
 u16 temp_v1_17;
 u16 temp_v1_3;
 u32 temp_v1_2;
 u8 *temp_a1_2;
 u8 *temp_v0;
 u8 *temp_v0_3;
 u8 *temp_v1_10;
 u8 *temp_v1_12;
 u8 *temp_v1_13;
 u8 *temp_v1_14;
 u8 *temp_v1_4;
 u8 *temp_v1_5;
 u8 *temp_v1_8;
 u8 *temp_v1_9;
 u8 *var_v1_2;
 u8 temp_a0;
 u8 temp_a1;
 u8 temp_a2;
 u8 temp_s0_2;
 u8 temp_t2;
 u8 temp_v0_17;
 u8 temp_v0_7;
 u8 temp_v1_11;
 u8 temp_v1_18;
 u8 var_v0;
 u8 var_v0_3;
 u8 var_v0_4;
 u8 var_v1;
 void *temp_s0;
 void *temp_s1;
 void *temp_s1_2;
 void *temp_s1_3;
 void *temp_s1_4;
 void *temp_s1_5;
 void *temp_s1_6;
 void *temp_s1_7;
 void *temp_s1_8;
 void *temp_s1_9;
 void *temp_s3;
 void *temp_v1_7;
 void *var_s1;
 void *var_s1_2;

 if (arg0->step != 0) {
  if ((D_us_801AE904 != 0) && (D_us_801AE850 == 0) && ((g_Settings.D_8003CB04 & 0x40000) || (g_GameClearFlag != 0)) && (g_pads_0_tapped & 0x800)) {
   D_us_801AE850 = 1;
   g_api_FreePrimitives(arg0->primIndex);
   arg0->flags ^= 0x800000;
   if (D_us_801AE888 != -1) {
    g_api_FreePrimitives(D_us_801AE888);
   }
   if (D_us_801AE884.unk0 != -1) {
    g_api_FreePrimitives(D_us_801AE884.unk0);
   }
   g_api_PlaySfx(0xA);
   arg0->step = 1;
   arg0->step_s = 0;
  }
  if ((arg0->step != 0) && (D_us_801AE890 != 0)) {
   RunCutsceneEvents();
  }
 }
 temp_v1 = arg0->step;
 switch (temp_v1) {  /* switch 1 */
 case 0:  /* switch 1 */
  if ((g_CastleFlags[0xDC] == 0) && (g_PlayableCharacter == 0) && (g_DemoMode == Demo_None)) {
   if (SetCutsceneScript(&D_us_80181878) & 0xFF) {
    g_CutsceneHasControl = 1;
    g_CutsceneFlags = 0;
    D_us_801AE904 = 0;
    D_us_801AE850 = 0;
    arg0->flags |= 0x802000;
    arg0->step += 1;
    arg0->primIndex = D_us_801AE88C;
    return;
   }
  default:  /* switch 1 */
   return;
  }
block_101:
  DestroyEntity(arg0);
  return;
 case 1:  /* switch 1 */
  temp_s1 = &D_us_801AE86A - 0x16;
  temp_s0 = &D_us_801AE86A - 0xC;
  temp_s3 = &D_us_801AE86A - 0x12;
 case 13:  /* switch 2 */
loop_22:
  if ((D_us_801AE86A.unk0 == 0) || (D_us_801AE850 != 0)) {
   temp_v0 = D_us_801AE86A.unk-16;
   D_us_801AE86A.unk-16 = (u8 *) (temp_v0 + 1);
   temp_a2 = temp_v0->unk0;
   temp_v1_2 = temp_a2 & 0xFFFF;
   switch (temp_v1_2) {  /* switch 2 */
   case 0:  /* switch 2 */
    arg0->step = 7;
    return;
   case 1:  /* switch 2 */
    if (D_us_801AE850 == 0) {
     D_us_801AE86A.unk-C = (u16) temp_s0->unk2;
     if (!(temp_s0->unk8 & 1)) {
      temp_s0->unk-4 = (u16) (temp_s0->unk-4 + 0xC);
     }
     temp_v0_2 = temp_s0->unk4 + 1;
     temp_s0->unk4 = temp_v0_2;
     if ((s16) temp_v0_2 >= 5) {
      temp_s0->unk4 = 0U;
     }
     CutsceneUnk4();
     temp_v1_3 = temp_s0->unk8;
     if (!(temp_v1_3 & 1)) {
      if ((s16) temp_s0->unk4 >= 4) {
       temp_s0->unk8 = (u16) (temp_v1_3 | 1);
       goto block_35;
      }
      goto loop_22;
     }
block_35:
     temp_s0->unk6 = 0;
     arg0->step_s = 0;
     arg0->step += 1;
     return;
    }
    goto loop_22;
   case 2:  /* switch 2 */
    temp_v0_3 = g_Dialogue.scriptCur;
    g_Dialogue.scriptCur = temp_v0_3 + 1;
    D_us_801AE86B = *temp_v0_3;
    goto loop_22;
   case 3:  /* switch 2 */
    temp_v1_4 = D_us_801AE86A.unk-16;
    D_us_801AE86A.unk-16 = (u8 *) (temp_v1_4 + 1);
    D_us_801AE86A.unk0 = (u8) temp_v1_4->unk0;
    if (D_us_801AE850 == 0) {
     return;
    }
    goto loop_22;
   case 4:  /* switch 2 */
    if (D_us_801AE850 == 0) {
     var_s1 = D_us_801AE86C;
     var_s0 = 1;
     do {
      var_s1->unk32 = 8;
      var_s1 = var_s1->unk0;
      var_s0 += 1;
     } while (var_s0 < 5);
     return;
    }
    goto loop_22;
   case 5:  /* switch 2 */
    if (D_us_801AE850 == 0) {
     temp_v1_5 = D_us_801AE86A.unk-16;
     D_us_801AE86A.unk-16 = (u8 *) (temp_v1_5 + 1);
     temp_s0_2 = temp_v1_5->unk0;
     D_us_801AE86A.unk-16 = (u8 *) (temp_v1_5 + 2);
     temp_t2 = temp_v1_5->unk1;
     temp_s1_2 = temp_s1->unk2C;
     temp_v0_4 = temp_t2 & 1;
     temp_a0 = *(&D_us_80180B60 + temp_v0_4);
     temp_a1 = *(&D_us_80180B64 + temp_v0_4);
     temp_s1_2->unk1A = 0x90;
     temp_s1_2->unkE = (u16) *(&D_us_80180B68 + (temp_s0_2 * 2));
     if (temp_t2 & 0x80) {
      var_v1 = temp_a0;
      var_v0 = var_v1 + 0x2F;
     } else {
      var_v0 = temp_a0;
      var_v1 = var_v0 + 0x2F;
     }
     temp_s1_2->unk24 = var_v0;
     temp_s1_2->unkC = var_v0;
     temp_s1_2->unk30 = var_v1;
     temp_s1_2->unk18 = var_v1;
     temp_v1_6 = temp_a1 + 0x48;
     temp_s1_2->unk19 = temp_a1;
     temp_s1_2->unkD = temp_a1;
     temp_s1_2->unk31 = temp_v1_6;
     temp_s1_2->unk25 = temp_v1_6;
     temp_v0_5 = D_us_801AE86A.unk-12 - 0x1E;
     temp_s1_2->unk2C = temp_v0_5;
     temp_s1_2->unk20 = temp_v0_5;
     temp_s1_2->unk14 = temp_v0_5;
     temp_s1_2->unk8 = temp_v0_5;
     temp_v0_6 = temp_s3->unk4 + 0x24;
     temp_s1_2->unk2E = temp_v0_6;
     temp_s1_2->unk22 = temp_v0_6;
     temp_s1_2->unk16 = temp_v0_6;
     temp_s1_2->unkA = temp_v0_6;
     temp_s3->unk10 = (u16) *(&D_us_80180B70 + (temp_s0_2 * 2));
     CutsceneUnk1();
     CutsceneUnk4();
     temp_s1_2->unk26 = 0x1FE;
     temp_s1_2->unk32 = 0;
     DrawCutsceneActorName(temp_s0_2 & 0xFFFF, arg0);
     temp_s3->unkC = 6;
     arg0->step = 3;
     return;
    }
block_57:
    D_us_801AE86A.unk-16 = (u8 *) (D_us_801AE86A.unk-16 + 2);
    goto loop_22;
   case 6:  /* switch 2 */
    if (D_us_801AE850 == 0) {
     var_s1_2 = D_us_801AE86C;
     var_s0_2 = 1;
     do {
      var_s1_2->unk32 = 8;
      var_s1_2 = var_s1_2->unk0;
      var_s0_2 += 1;
     } while (var_s0_2 < 5);
     g_api_FreePrimitives(D_us_801AE888);
     D_us_801AE888 = -1;
     D_us_801AE864 = 6;
     arg0->step = 4;
     return;
    }
    goto loop_22;
   case 7:  /* switch 2 */
    if (D_us_801AE850 == 0) {
     temp_v1_7 = temp_s3->unk-4;
     temp_s3->unk-4 = (void *) (temp_v1_7 + 1);
     temp_s3->unk-4 = (void *) (temp_v1_7 + 2);
     D_us_801AE86A.unk-12 = (u16) temp_v1_7->unk0;
     temp_v0_7 = temp_v1_7->unk1;
     temp_s3->unk4 = (u16) temp_v0_7;
     temp_s1_3 = *temp_s3->unk28;
     temp_s1_3->unk16 = (s16) temp_v0_7;
     temp_s1_3->unkA = (s16) temp_v0_7;
     temp_v0_8 = temp_s3->unk4 + 0x48;
     temp_s1_3->unk2E = temp_v0_8;
     temp_s1_3->unk22 = temp_v0_8;
     temp_s1_4 = temp_s1_3->unk0;
     temp_s1_4->unkA = (s16) (temp_s3->unk4 - 1);
     temp_s1_4->unkC = 0xF6;
     temp_s3->unkC = 0x18;
     arg0->step = 5;
     arg0->step_s = 0;
     return;
    }
    goto block_57;
   case 8:  /* switch 2 */
    if (D_us_801AE850 == 0) {
     D_us_801AE864 = 0x18;
     arg0->step = 6;
     return;
    }
    goto loop_22;
   case 9:  /* switch 2 */
    if (D_us_801AE850 != 0) {
     goto block_57;
    }
   case 20:  /* switch 2 */
    temp_v1_8 = D_us_801AE86A.unk-16;
    D_us_801AE86A.unk-16 = (u8 *) (temp_v1_8 + 1);
    D_us_801AE86A.unk-16 = (u8 *) (temp_v1_8 + 2);
    g_api_PlaySfx(temp_v1_8->unk1 | (temp_v
