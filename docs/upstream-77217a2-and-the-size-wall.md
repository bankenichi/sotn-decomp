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

Then `transplant.py --list` found a fifth that I had just finished writing off:

| record | asm chars | donor |
|---|---|---|
| `us:ST/RNO0:func_us_801D1388_from_are` | 20165 | `src/st/e_armor_lord.h` |

Checked and genuinely absent from `src/`: `BO6_RicEntitySubwpnAgunea`,
`BO6_RicEntitySubwpnReboundStone`, `BO6_RicEntityAguneaHitEnemy`,
`func_us_801C9DE8`, `func_us_8019C7B8` (transplant: "no usable twin in this
tree"), `func_us_801C2418`.

**Final: 5 transplantable, 6 needing derivation.**

I had guessed the three BO6 subweapons would be on the same `src/ric/319C4.c`
donor as their siblings. They are not. `RicEntityAguneaCircle` and the static
helpers `GetAguneaLightningAngle` / `AguneaShuffleParams` DO live there, which
is what made the guess plausible, but the donor relationship does not extend
to the whole family.

## 4b. The size ceiling is a MODEL limit, and m2c does not have one

The more useful finding, and it needs no new mechanism at all.

`worker_direct` runs `prepare()` BEFORE the size gate. `prepare()` shells out
to `tools/m2ctx.py` and `tools/m2c/m2c.py` to build a typed C draft. Only
afterwards does this run:

```python
_asm_size = ctx.get("asm_full") or len(ctx["asm"])
if _asm_size > MAX_FUNC_CHARS and not dry:
    ... status deferred, TIER_HANDOFF_TOO_LARGE ...
```

So for all 11 records **the m2c draft was already computed and then thrown
away**. `MAX_FUNC_CHARS` exists because a 68865-char function does not fit in
a model's context window. m2c is a static translator with no context window;
it does not care how big the function is.

That gives a path for the 6 that need derivation, with zero model calls:

1. m2c draft (already produced today, just discarded)
2. run it through the existing draft cleaning
3. build it
4. if it compiles, it is a permuter seed by definition ("compiles, bytes
   differ"), and `save_candidate` already handles exactly that outcome
5. hand it to the permuter

m2c output usually compiles and rarely matches, which is precisely the input
the permuter wants. The 20000-char ceiling should gate the MODEL step, not the
whole record.

## 4c. Can a single function be split? Not into multiple functions

Worth stating plainly because it is the intuitive idea and it does not work.

Splitting one function into two C functions cannot match. Each function gets
its own prologue and epilogue, registers are allocated per function, and the
call between them is instructions that are not in the target. The oracle is
byte equality; two functions are not one function.

What can be split is the WORK, not the output:

- **Chunked drafting, whole-function verification.** Feed the model one basic
  block at a time, assemble the pieces into a single function body, build
  once. The prompt is bounded; the output is still one function. Needs the
  control-flow graph up front, which is compact even for a 68k function.
- **Diff-driven iteration.** Draft once, build, and feed back only the first
  divergence. The prompt stays bounded no matter how large the function is.
  `local_summarize_diff` and `asm_delta.py` already exist for this.
- **m2c first**, as in 4b, which removes the context problem from the draft
  step entirely.

`static inline` helpers and macros are NOT a safe way to split: whether GCC
2.7 inlines is a codegen decision, so it can change the bytes. Macros are safe
only when the expansion is identical, which makes them a readability tool
rather than a size tool. This repo already uses them that way (`SELF_BB`,
`ANIMSET_OVL`, `GIANTBRO_ZPRIORITY_ADJUST`).

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
