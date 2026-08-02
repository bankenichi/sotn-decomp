// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// rno0 defines neither STAGE_FLAG nor STAGE_NAME_BOX_MARGIN, and both defaults
// are correct here. EntityStageNamePopup.s reads and writes g_CastleFlags + 0x2,
// and NULL_STAGE_FLAG is 2 (include/castle_flags.h), so the header's fallback
// produces exactly this addressing. rcen, rchi and rdai shim it the same way.
// rno0 exports the interactable descriptor as RNO0_EInitInteractable rather
// than under the shared name. See the STAGE_NAME_EINIT note in the header.
#define STAGE_NAME_EINIT OVL_EXPORT(EInitInteractable)

#ifdef VERSION_US
#include "../e_stage_name_us.h"
#endif

#ifdef VERSION_PSP
#include "../e_stage_name_jp.h"
#endif
