# Harvesting from upstream

**What this is.** Upstream (`Xeeynamo/sotn-decomp`) has decompiled functions
this fork still has as `INCLUDE_ASM` stubs. Copying one in, adapting it to this
fork, and verifying it against the oracle is a *harvest*. As of 2026-08-16, 25
functions have landed this way.

**What it is not.** A harvest is not this fork's automation producing a match.
The body was already written, by someone else, somewhere else. That distinction
is load-bearing for the whole project: the point of the fork is measuring what
an AI harness can do, and a harvested function measures nothing about that. It
is worth doing because it clears the queue of work that does not need a model,
leaving the genuinely hard records for the fleet.

This is why `upstream-harvest` outranks every other source in
`match_provenance.py`'s `_PRECEDENCE` — see [Provenance](#provenance) below.

---

## The loop

```
upstream_harvest.py                 what does upstream have that we do not
  -> git_diff  config/splat.us.<ovl>.yaml   upstream/master   SEGMENT CHECK FIRST
  -> git_show_file --start --count          just the function, not the file
  -> edit, rename call sites to this fork's convention
  -> job_start make_build ; verify_build    THE ORACLE DECIDES
  -> fn_diff --overlay X --function Y       if it missed, why
  -> git_add (explicit paths) ; git_commit
  -> queue_report status=matched proof="all expected artifacts OK"  notes=METHOD=UPSTREAM-HARVEST
```

Every step has a tool. The two that did not exist before this work are
`git_show_file` (the connector could only ever show a *diff*, so "what does
upstream HAVE" was literally unanswerable) and `queue_coverage.py`.

---

## The seven rules, each paid for with a failed build

### 1. Diff the splat config BEFORE touching the source

If upstream declares a `.data, <stem>` segment where this fork has the range as
an unnamed blob, harvesting a body that owns file-scope arrays emits those
arrays a **second** time and shifts every symbol below them.

- ST/RCEN `unk_1F0D8`: `rooms` and 21 other symbols moved `+0x40`. Upstream had
  `[0x9FC, .data, unk_1F0D8]`; this fork had `[0x9FC, data]`.
- BOSS/BO0 `2B9EC`: same shape, pre-empted by checking first. The six statics
  total `0xFC` bytes, exactly the `0xA48..0xB44` blob.

```
git_diff(ref="upstream/master", path="config/splat.us.<overlay>.yaml")
```

### 2. A segment split can be load-bearing, not cosmetic

Upstream splits BO0's `2D26C` at `0x3053C`. Landing upstream's three bodies
inside this fork's *merged* translation unit put their jump table at `0x294A4`;
the original has it at `0x294A8`, because in upstream those functions compile to
their own object and a fresh `.rodata` section starts 8-aligned.

Same C, same compiler, wrong answer — decided entirely by which `.o` the rodata
landed in. I asserted the split was unnecessary and the oracle disagreed.

`make extract` does **not** re-split; it only does assets. A plain build does,
because ninja re-runs splat when the yaml changes.

### 3. `upstream_harvest.py` both undercounts and overcounts

- **Undercounts:** it matches by name. `e_secrets`' two static helpers are named
  for their ST/NO2 addresses upstream (`func_us_801B59C4`, `func_us_801B6794`)
  and are `func_us_801AB9EC` / `func_us_801AC73C` here, so it never saw them.
  Nine BO0 functions landed against a reported seven.
- **Overcounts:** it derives "unmatched" from the queue. A stale record makes an
  already-done function look harvestable. Closing the 11 stale ST/RNO0 records
  removed `func_801CD658`, `func_801CD91C` and `polarPlacePart` from its list.

Treat its output as a starting set, not a specification.

### 4. Not everything upstream has will match here

`func_us_801B6998` (BO6) compiles, links, and builds **one instruction long** —
an extra load-delay `nop` the original does not have, shifting everything after
it. That is permuter work, not transcription. It is recorded `near` with the
finding, not committed as a match and not silently dropped.

### 5. Report the queue at harvest time

The three ST/MAD functions sat `todo` for a full session after being committed
and building 81/81. `matched_audit.py` catches the opposite drift (a `matched`
record whose body vanished); nothing caught this direction until
`queue_coverage.py` existed.

### 6. Check the declaration, not just the body — now automated

`func_us_801BBBD0` was character-for-character upstream's and still missed,
because `D_us_801812B8` was declared such that the bare name evaluated to a
**value** (0) rather than decaying to its **address**. The build passed zero in
`$a1` where the original loads `%hi`/`%lo` of `0x801812B8`.

The fingerprint is mechanical: *the original materialises an address with a
`lui`/`addiu` pair and the build dropped the `addiu`*. One dropped word presents
as a dozen diff lines and reads like a codegen problem.

`fn_diff.py` now detects exactly this, reconstructs the address from the
instruction words, resolves it to a symbol name, and prints the fix:

```
WRONG EXTERN TYPE (likely): the original materialises the address 0x801812b8 ...
    symbol   D_us_801812B8
    fix      extern <type> D_us_801812B8[];
             Do NOT edit the body.
```

The last line is the important one. The body was already correct.

### 7. Ask the scheduler, never the queue file

`work/queue.jsonl` in the repo is a **stale legacy snapshot**. `scheduler.py`
names it `_LEGACY_QUEUE` and its line 5 says the live queue is
`~/sotn-work/queue.jsonl` via `SOTN_QUEUE`.

Grepping the repo copy on 2026-08-16 produced a confident, fully wrong claim
that ST/RDAI's 18 functions were invisible to the harness. They were never
missing. Use `queue_stats`, `queue_list`, or `queue_coverage.py`, all of which
go through the scheduler.

---

## Adapting upstream's code to this fork

The two trees have diverged in naming, and the divergence is not uniform.

**BOSS/BO6** is the worst case. This fork exports through `OVL_EXPORT(...)` and
`BO6_` prefixes where upstream uses bare `Ric*` names. Every call site in a
harvested body needs rewriting:

| upstream | this fork |
|---|---|
| `RicMain` | `BO6_RicMain` |
| `DisableAfterImage` | `BO6_DisableAfterImage` |
| `RicSetAnimation` | `BO6_RicSetAnimation` |
| `RicCreateEntFactoryFromEntity` | `BO6_RicCreateEntFactoryFromEntity` |
| `RicGetFreeEntity` | `BO6_RicGetFreeEntity` |
| `RicCheckInput` / `RicCheckFacing` | `BO6_RicCheckInput` / `BO6_RicCheckFacing` |

**Confirm every mapping against `config/symbols.us.<overlay>.txt` or an existing
definition in the same file. Do not infer it from the pattern.**

This fork is also *ahead* of upstream on roughly nine BO6 functions
(`BO6_AguneaShuffleParams`, `BO6_ReboundStoneBounce1`/`2`,
`BO6_PrimDecreaseBrightness`, `func_us_801C488C`, `func_us_801C8590` and others
are matched here and still `INCLUDE_ASM` upstream). A BO6 harvest is a **merge**,
not a copy. Never overwrite a function this fork has already matched.

**BOSS/BO0** needed only static renames, because upstream's `e_secrets.c` keeps
ST/NO2's names for functions and data. Every array name there was exactly `+0x300`
from its true BO0 address; the offset being uniform across all six is the
evidence the arithmetic was right rather than a guess.

### Entity ext variants

Three harvests needed an `ET_` variant restored to the `Ext` union in
`include/entity.h` that upstream has and this fork had dropped:

| variant | for | ends at |
|---|---|---|
| `ET_801B0930` | BO0 Olrox after-image | `0x92` |
| `ET_ShaftOrb` | BO6 Shaft's orb | `0x92` |

Adding a union member **cannot** move anything as long as it fits: `Ext` already
runs to `0xB7`, so a variant ending at `0x92` leaves the union's size unchanged
and every other entity untouched. That is why this is safe to do for a single
function, and why *widening* the union would not be.

Where upstream reaches through `ext.ILLEGAL.s16[]`, **keep it verbatim**. Those
slots land in the struct's anonymous padding; naming them would invent a layout
the assembly does not attest to. This is the one place the project's usual
objection to `ILLEGAL` is outweighed.

---

## Provenance

`match_provenance.py` ranks `upstream-harvest` **first** in `_PRECEDENCE`,
above even the shims. A harvested body was not generated here, not derived here,
and not searched for here. Crediting this fork's machinery for it would be the
largest overstatement available, and the honest answer to "what did the
automation produce" depends on these being subtracted first.

Every harvested record carries a note beginning `METHOD=UPSTREAM-HARVEST`,
naming the upstream file and any segment work it required. The detection regex
in `_PATTERNS` matches that marker plus `from upstream/master`.

`readme_status.py` regenerates the provenance table from these records. Its
`blurb` map must stay in step with `_PRECEDENCE` — a source with no entry
renders as a count beside an empty cell, which is what `upstream-harvest` did
the first time it was generated. There is now a self-test asserting the two
lists agree.

---

## Status

| overlay | harvested | state |
|---|---|---|
| ST/MAD | 3 | **complete** — zero stubs remain |
| ST/RCEN | 4 | 16 stubs left |
| BOSS/BO0 | 9 | **complete** for harvestable work |
| BOSS/BO6 | 9 | `us_39144.c` and `us_3E79C.c` complete; `richter.c` has 3 left |
| ST/RNO0 | 0 | **17 remain**, all via shared headers |

The ST/RNO0 group is the highest-risk remaining work: `e_armor_lord.h`,
`e_thornweed_corpseweed.h`, `e_floor_trap.h`, `e_subweapon_container.h`,
`giantbro_helpers*.h`, plus `no0/e_elevator.c`, `no0/42A34.c`, `no0/4C750.c` and
`mar/clock_room.c`. Shared headers mean rule 1 applies to nearly all of them.

Regenerate the live numbers with:

```
python3 automation/upstream_harvest.py     # what is left
python3 automation/queue_coverage.py       # queue vs tree, must be 0 BLIND / 0 stale
python3 automation/readme_status.py --write
```
