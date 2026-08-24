// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

#include "../../st/pfn_entity_update.h"
#define GOLD_COLLECT_TEXT                                                      \
    _S("$1"), _S("$25"), _S("$50"), _S("$100"), _S("$250"), _S("$400"),        \
        _S("$700"), _S("$1000"), _S("$2000"), _S("$5000"),
#define HEART_DROP_CASTLE_FLAG 0
#define EntityHeartDrop EntityPersistentItemDrop
#include "../../st/e_collect.h"

asm(".globl D_us_80181144\n"
    ".set D_us_80181144, g_bigRedFireballAnim");
