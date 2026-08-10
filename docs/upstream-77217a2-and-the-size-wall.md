# Upstream 77217a2, and what it means for the 11 too-large records

Task #100. Fetched `upstream/master` at `77217a234`, "rno2: decompile azaghal
(us + pspeu) (#3526)".

## 1. What the commit actually does

Not function splitting. It splits a **block of functions** out of an
oversized translation unit and satisfies the new TU from a **shared header**
extracted from a donor overlay.

```
 config/splat.pspeu.strno2.yaml |    8 +-      new segment
 config/splat.us.strno2.yaml    |    6 +
 config/symbols.us.strno2.txt   |    9 -       names now resolved
 src/st/e_azaghal.h             | 1160 ++++++   NEW shared header
 src/st/rare/e_azaghal.c        | 1151 -------   donor emptied into it
 src/st/rno2/e_azaghal.c        |    4 +        the new TU, in full
 src/st/rno2/unk_47A9C.c        |   18 -        azaghal stubs removed
 src/st/rno2/unk_4AB8C.c        |    4 +        tail function left as asm
 src/st/rno2_psp/unk_3EF8.c     |   16 -
```

The entire new translation unit is four lines:

```c
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

#include "../e_azaghal.h"
```

Their own description, which is the clearest statement of the technique:

> Splits the azaghal block out of `unk_47A9C` into its own TU: eight
> functions (six static helpers plus `EntityAzaghal` and
> `EntityAzaghalSwordHitbox`) mirroring the structure of the `rare` donor
> [...] validated standalone on current master with fresh splat extraction:
> us + hd + pspeu checksums all green

So the moving parts are: remove N `INCLUDE_ASM` stubs from a large TU, add a
new TU that includes a shared header, extract that header from an overlay
where the code is already decompiled, and add a splat segment so the new TU
gets its own object.

## 2. This is a technique we already have

It is what this fork calls **shimming**, and it has been used at least seven
times: `st_update.h`, `collision.h`, `e_particles.h`, `e_medusa_head.h`,
`e_red_door.h`, `entity_lock_camera.h`, and the giant-bro trio. See
`docs/shared-header-parameterisation.md` and tasks #41, #50, #51, #58, #60,
#67, #70.

Upstream is doing the same thing we are. The one detail worth copying is the
**splat segment split**: they add a segment so the extracted block becomes
its own object file, which is what lets the tail function
(`func_us_801CAB8C`) stay as assembly in a separate `unk_4AB8C` TU rather
than blocking the whole file. We have done segment work for `.data` and
`.bss` (#41, #56, #58) but not routinely for splitting `.text` blocks.

## 3. It does NOT solve the size problem as posed

A shared header does not make one function smaller. The 11 deferred records
are single functions of 20165 to 68865 characters of assembly, and
`e_azaghal.h` would not shrink any of them.

**But the size problem was posed wrong.** Size is only a barrier when the
function has to be DERIVED from assembly. If the same function is already
decompiled somewhere in the tree, the work is a transplant, and the size of
the assembly is irrelevant, because nobody is reading it.

## 4. The actual finding: most of the 11 already exist

Verified by search, four of the eleven:

| record | asm chars | already decompiled at |
|---|---|---|
| `us:ST/RNO0:EntityRelicOrb` | 43582 | `src/st/e_collect.h:989` (a SHARED header) |
| `us:ST/RCHI:EntityGaibon` | 67724 | `src/st/np3/gaibon.c:111`, `src/st/nz0/gaibon.c:113` |
| `us:BOSS/BO6:BO6_RicEntitySubwpnBible` | 20682 | `src/ric/319C4.c:2038` |
| `us:BOSS/BO6:BO6_RicEntityAguneaLightning` | 24940 | `src/ric/319C4.c:1213` |

`EntityRelicOrb` is the strongest case and the most embarrassing: the
implementation is in a shared header that RNO0 could include, and
`src/st/rno0/e_collect.c:761` still carries `INCLUDE_ASM(..., EntityRelicOrb)`
with a comment right above it explaining that its support tables live in
undecompiled data blobs. So the code was never the blocker; the DATA was.
That is a `.data` segment problem of exactly the kind #41/#56/#58 already
solved three times.

`BO6_RicEntitySubwpnBible` sits in a file that already contains
`OVL_EXPORT(RicEntitySubwpnBibleTrail)` decompiled from the same `src/ric/`
donor, twenty lines above the stub. The porting pattern is established in
that very file.

Checked and NOT found anywhere in `src/`: `BO6_RicEntitySubwpnAgunea`,
`BO6_RicEntitySubwpnReboundStone`, `BO6_RicEntityAguneaHitEnemy`. I had
guessed all three would be on the same `src/ric/319C4.c` donor as their
siblings; they are not. BO6 is the only place they exist, so they are
genuine derivations and belong with the remaining seven.

`RicEntityAguneaCircle` (`319C4.c:1351`) and the static helpers
`GetAguneaLightningAngle` / `AguneaShuffleParams` DO exist there, which is
what made the guess plausible. Two of those are already matched in BO6
(`BO6_AguneaShuffleParams`, `BO6_GetAguneaLightningAngle` is escalated), so
the donor relationship is real but does not extend to all of the family.

## 5. What to do

The tooling for this already exists and was never pointed at these records:
`asm_twin_finder.py`, `transplant.py --list`, `shim_sweep.py`,
`codebase_index.py:shim_viable`.

1. Run the twin finders against the 11 specifically. Cheap, no model calls,
   and by the evidence above it should resolve most of them.
2. For each hit, decide transplant (copy the body) versus shim (include a
   shared header). `EntityRelicOrb` wants a shim plus a `.data` segment;
   `BO6_RicEntitySubwpnBible` wants a transplant with `Ric` to `BO6_Ric`
   renaming, which the file already demonstrates.
3. Only what survives that is genuinely too large to derive, and only THOSE
   need the piecewise-decompilation mechanism #97 was originally about.
4. Adopt the splat `.text` segment split from 77217a2 when a block has to be
   separated from a TU that is otherwise blocked.

Every record stays in scope. Nothing here descopes anything; it reclassifies
work from "cannot be attempted" to "can be attempted without model calls".

## 6. Honest limits of this finding

- Four twins verified by search, and my inference about the other three
  BO6 subweapons was WRONG: `SubwpnAgunea`, `SubwpnReboundStone` and
  `AguneaHitEnemy` exist nowhere but BO6. Reasoning "its siblings came from
  `src/ric/`, so this one will too" produced three false positives out of
  four guesses. Run the twin finder rather than pattern-matching on names.
- So the split is 4 transplantable, 7 genuinely needing derivation. That is
  a smaller win than section 4 first suggested, and it means #97 still needs
  a real mechanism for the remainder.
- A twin existing does not mean the transplant matches. The overlays differ
  in constants and layout, which is why `transplant.py` builds and reverts
  rather than trusting the copy. `func_us_801BB014` in the queue is a
  standing example: an `EntityIsNearPlayer` relative with a 24-wide box, not
  16, deliberately NOT folded with its near-identical sibling.
- `EntityRelicOrb`'s blocker is data, not code, and data segment work has
  been the slowest part of every shim so far.
