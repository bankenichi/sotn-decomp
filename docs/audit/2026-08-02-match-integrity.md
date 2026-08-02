# Match integrity audit — 2026-08-02

Independent, adversarial, read-only. No file in the tree was modified, no build
was run. Working ref: `38b833c44`, upstream baseline `upstream/master` =
`f6bfa3791`.

**Bottom line: the matches are real. The accounting around them is inflated.**

I found no fabricated match, no tampered oracle, and no function credited as
matched that is still `INCLUDE_ASM`. I did find that a little over half of the
C this fork defines is verbatim upstream code, and that three of the reasons
the ROADMAP gives for keeping those copies are contradicted by the tree itself.

---

## 1. What I verified as sound

### 1.1 The oracle is untampered and it passes 81/81

```
git diff --quiet upstream/master -- config/check.us.sha   -> IDENTICAL
sha1sum -c config/check.us.sha                            -> 81 OK, 0 FAILED
```

`config/check.us.sha` is byte-identical to `upstream/master`. It was not edited
to accommodate a bad build. Hashing the on-disk artifacts in `build/us/`
against it passes all 81 lines.

This matters more than any doc claim: an overlay hash is a whole-binary
assertion. If `build/us/RNO0.BIN` matches the original, every byte of rno0 —
including all the C this fork wrote — is correct.

### 1.2 The build is not stale relative to sources

```
find src/ -name "*.c" -newer build/us/RNO0.BIN   -> (empty)
build/us/RNO0.BIN   2026-08-02 10:24:36
src/st/rno0/st_common.c  2026-08-01 09:40:21
```

No source file postdates the build output, so the 81/81 above reflects the
current tree and not an older one. (ROADMAP records that stale artifacts have
burned this project before — that guard is warranted and it is currently
clean.)

### 1.3 No "matched" record is still assembly

The obvious way to fake a match under a whole-overlay oracle is to mark a
function matched while leaving it as `INCLUDE_ASM` — the overlay hashes fine
because the original assembly is still being assembled in. I tested for exactly
this across the 33 matched records in `work/queue.jsonl`:

```
matched records whose function is STILL INCLUDE_ASM: 0
```

Four records (`Random`, `EntityMedusaHeadYellow`, `UnkPolyFunc0`,
`FindFirstUnkPrim`) have no C definition in their overlay directory either —
those are the private copies that were deleted when a shared header was shimmed
in, which is the documented and correct outcome, not a gap.

### 1.4 The `D_us_XXXXXXXX` externs are legitimate

I extracted every raw-address extern from the changed files and resolved each
address against **all** of `config/symbols.us.*.txt`:

```
D_us_ externs scanned:            34
with a real name available:        0
```

The one apparent hit — `D_us_80180490` at `src/boss/bo6/us_3E79C.c:531`
resolving to `gfxBanks` — is a false positive of my own check.
`gfxBanks = 0x80180490` is in `config/symbols.us.strare.txt`, i.e. the RARE
overlay. Overlays alias the same 0x8018xxxx VRAM window, so a bare address
match across symbol files means nothing. In BO6 that address is a genuinely
unnamed `EInit`.

`src/st/rno0/e_collect.c:8-61` is the densest cluster (16 externs) and every
one carries a comment saying what the data is and why it has no name
("Storage lives in an undecompiled data blob"). Line 48-51 documents a raw
address that was *removed* in favour of the real `g_ItemIconSlots`. This is the
opposite of hiding structure.

Other named externs spot-checked and confirmed real: `PrizeDrops`
(`config/symbols.pspeu.*` × 9), `D_us_80180594` (unnamed in every symbol file).

### 1.5 No `ILLEGAL` ext usage

`grep ILLEGAL` across all 29 changed files: zero hits.

### 1.6 Symbol and shared-header edits are disciplined

`config/symbols.us.strno0.txt` gains 15 names. Every one is justified in a
comment that cites the `%hi`/`%lo` relocation in a specific
`asm/us/st/rno0/nonmatchings/*.s` file it was read off, plus an explicit
ALL-OR-NOTHING warning about the `INCLUDE_ASM` fallback breaking. That is
derivation, not guessing.

`src/st/clock_room_entities.h` is a **shared header with 3 consumers**
(`st/no0`, `st/rno0`, `boss/mar`). It was parameterised with five `#ifndef`
defaults so no0 and mar stay byte-identical. The 81/81 result confirms NO0.BIN
and MAR.BIN did not move. Correct technique for a change with blast radius.

### 1.7 `review_checks.py` works; its zero is just narrow

Its `--self-test` passes 6/6 testable cases. Its "0 findings over 29 changed
files" is a genuine result — see M4 for why that must not be read as "clean".

---

## 2. Findings by severity

### CRITICAL — none

No evidence of a fabricated, misrepresented, or unverifiable match.

---

### HIGH

#### H1. `ROADMAP.md:486` states something the tree contradicts, and it excuses 6 duplicate functions

> `e_blade`, `e_gurkha` and `e_hammer` have no shared implementation at all.

This is false. All three shared headers exist and are already shimmed by two
stages each:

| header | consumers |
|---|---|
| `src/st/e_blade.h` | `src/st/no2/blade.c:4`, `src/st/np3/blade.c:4` |
| `src/st/e_gurkha.h` | `src/st/no2/gurkha.c:4`, `src/st/np3/gurkha.c:4` |
| `src/st/e_hammer.h` | `src/st/no2/hammer.c:3`, `src/st/np3/hammer.c:3` |

And `automation/provenance_check.py` scores rno0's copies at **1.000** against
those very headers:

```
src/st/rno0/e_blade.c:func_801D0A00   <- src/st/e_blade.h:func_801D0A00
src/st/rno0/e_blade.c:func_801D0B40   <- src/st/e_blade.h:func_801D0B40
src/st/rno0/e_blade.c:func_801D0B78   <- src/st/e_blade.h:func_801D0B78
src/st/rno0/e_gurkha.c:func_801CF778  <- src/st/e_gurkha.h:func_801CF778
src/st/rno0/e_gurkha.c:func_801CF7A0  <- src/st/e_gurkha.h:func_801CF7A0
src/st/rno0/e_hammer.c:func_801CE4CC  <- src/st/e_hammer.h:func_801CE4CC
```

The project's own tool disagrees with the project's own roadmap. **Action:**
correct ROADMAP.md:486, then evaluate these three stems as shim candidates on
their merits. Note `func_801CF778` is one of the records marked *matched* (see
H3).

#### H2. `ROADMAP.md:77` gives a blocker for `rno0/st_common` that three independent sources contradict

> `rno0/st_common` is blocked on a missing `.bss, st_common` segment.

Against this:

1. `ROADMAP.md:235`, in the same file: *"`st_common` has no bss here"*. The
   document contradicts itself.
2. `src/st/st_common.h` declares **zero** file-scope storage — I parsed it for
   non-function file-scope declarations and got none. There is no bss for a
   segment to hold.
3. **No** `config/splat.us.*.yaml` in the repo declares a `.bss, st_common`
   segment. No stage needs one.

What this excuses is the single largest block of duplicated code in the fork.
`src/st/rno0/st_common.c` is **713 lines / 34 function definitions**. I diffed
its bodies against `src/st/st_common.h` (whitespace-normalised, comments
stripped) myself rather than trusting the audit tool:

```
BYTE-IDENTICAL bodies: 22
  AdjustValueWithinThreshold, AllocEntity, DestroyEntitiesFromIndex,
  EntityExplosionSpawn, GetAngleBetweenEntitiesShifted, GetAnglePointToEntity,
  GetAnglePointToEntityShifted, GetDistanceToPlayerX, GetDistanceToPlayerY,
  GetPlayerCollisionWith, GetSideToPlayer, InitializeEntity, LimitAngleChange,
  MoveEntity, PreventEntityFromRespawning, ReplaceBreakableWithItemDrop,
  SetEntityVelocityFromAngle, SetSubStep, UnkAnimFunc, UnkCollisionFunc2,
  UnkCollisionFunc3, UnkEntityFunc0
plus AnimateEntity and DestroyEntity, identical to src/st/animate_entity.h
and src/destroy_entity.h, which st_common.h includes           = 24 total
```

Every other reverse stage does this in three or four lines:

```
src/st/rno3/st_common.c   4 lines   #include "../st_common.h"
src/st/rnz0/st_common.c   4 lines
src/st/rcat/st_common.c   4 lines
src/st/rchi/st_common.c   3 lines
src/st/rdai/st_common.c   4 lines
src/st/rcen/st_common.c   4 lines
src/st/rare/st_common.c   4 lines
src/st/rtop/st_common.c   3 lines
src/st/rwrp/st_common.c   4 lines
```

ROADMAP.md:309 already concedes the shape of this — *"27 of 28 stage overlays
get both free from a 4-line shim; rno0 is the sole outlier"* — but the stated
blocker at line 77 is what keeps it unfixed.

**I cannot prove the shim would build** (building is out of scope for this
audit). The finding is that the *reason given* is unsupported, not that the
shim is known to work. **Action:** a human should attempt
`#include "../st_common.h"` in `src/st/rno0/st_common.c` and record the actual
failure mode, or correct ROADMAP.md:77 to state the real one.

#### H3. Verbatim shared-header code is recorded as harness matches with no provenance note

Cross-referencing the byte-identical set from H2 against the matched records:

```
us:ST/RNO0:SetSubStep           claimed_by fleet-2  iterations 0
us:ST/RNO0:MoveEntity           claimed_by fleet-1  iterations 0
us:ST/RNO0:GetDistanceToPlayerY claimed_by fleet-1  iterations 0
us:ST/RNO0:GetDistanceToPlayerX claimed_by fleet-1  iterations 0
us:ST/RNO0:GetSideToPlayer      claimed_by fleet-2  iterations 0
```

Five of the 33 matched records in the visible queue (15%) are functions whose
text already existed verbatim at `src/st/st_common.h`. All five have
`iterations: 0`. Their `notes`/`proof` fields cite only the overlay SHA-1 —
correct as a *matching* proof, but silent on the fact that the code was not
authored here.

Tree-wide, `automation/provenance_check.py` puts this at **53 of 104 functions
(51.0%) verbatim**, plus 4 adapted and 7 derived. Only 33 (31.7%) are original.

To be clear about what is and is not wrong: the binaries are genuine and the
oracle proof is valid. What is misleading is the framing. "155 matched
functions" reads as 155 functions decompiled by this project; roughly half of
the fork's C is a re-typed copy of code already in the tree. **Action:** the
queue schema should carry a `provenance` field, and any headline count should
be stated as e.g. "155 matched, of which N are shared-header copies". Credit
`provenance_check.py` — the project already built the tool that surfaces this;
it just is not wired into the reported number.

---

### MEDIUM

#### M1. `automation/quality_audit.py` — the comment guard is in the wrong place; the audit's only FAKE SYMBOL finding is a false positive

`check_file()` runs the `fake_symbol` scan at lines 297-303, and the
comment-skip guard sits *below* it at lines 305-311, immediately above the
`ext.ILLEGAL` check at line 313:

```python
        # 1. invented externs that alias a real entity field
        for m in re.finditer(r"\bD_(?:us_)?[0-9A-Fa-f]{8}\b", line):
            ...
        # A line that is only a comment cannot contain a defect...
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue
        # 2. ext.ILLEGAL where named variants exist
```

So check #1 scans comment prose. The consequence, and the *entire* FAKE SYMBOL
section of the report:

```
src/boss/bo6/us_39144.c:240  [func_us_801B9DE4]
    D_80077B08 is g_Entities[96].ext (+0x34)
```

Line 240 is:

```c
// induction variable: the loop loads at D_80077B08 with member offset 0xB0, so
```

It is a comment explaining how the entity base was *derived from the assembly*.
The actual code, at line 243, uses the correct named form:

```c
entity = &g_Entities[STAGE_ENTITY_START + 32];
```

`D_80077B08` is never declared in that file — `grep` finds it only on line 240.
This is a clean piece of work being penalised for documenting itself, which is
the precise failure mode the guard's own comment says it was added to prevent.

Secondary: the finding is attributed to `func_us_801B9DE4` (defined at line
208) when the enclosing function is `BO6_RicCheckSubwpnChainLimit` (line 243).
`cur_fn` lags because the comment block precedes the definition.

**Action:** move the comment guard above check #1. Expected effect: FAKE SYMBOL
drops to 0 and the audit's headline goes from 48 findings to 47.

#### M2. `src/st/rcen/unk_1F0D8.c:31` — magic literal where the same file uses the named constant

```c
void func_us_801B4148_from_bo0(Entity* self) {      // line 16
        self->animSet = ANIMSET_OVL(1);             // line 19  <- named
...
void func_us_801C123C_from_no4(Entity* self) {      // line 27
        self->animSet = -0x7FFF;                    // line 31  <- magic
```

`include/game.h:486-488`:

```c
#define ANIMSET_OVL_FLAG 0x8000
#define ANIMSET_OVL(x) ((x) | ANIMSET_OVL_FLAG)
```

`1 | 0x8000` = `0x8001` = `-0x7FFF` as `s16`. The two lines are the same value,
twelve lines apart, in the same file, added in the same change. Both functions
are fork-authored (the upstream diff shows both were `INCLUDE_ASM` before).

`quality_audit.py` does not catch this: its magic-number check fires only when
the variable name identifies a flag family, and `animSet` is not a flag group.

**Action:** `self->animSet = ANIMSET_OVL(1);`. Also worth teaching the audit
about `animSet` specifically, since `ANIMSET_OVL`/`ANIMSET_DRA` cover it
exhaustively.

*Not a finding:* the `_from_bo0` / `_from_no4` suffixes look like invented
placeholder names, and I initially flagged them. They are upstream's — the diff
shows `INCLUDE_ASM("st/rcen/nonmatchings/unk_1F0D8", func_us_801B4148_from_bo0)`
in `upstream/master`. The fork only supplied bodies under existing names.

#### M3. The "155 matched" figure cannot be verified from this repository

`ROADMAP.md:70` sources it from `queue_stats` over
`/home/kenichi/sotn-work/queue.jsonl` — outside the tree, outside my access.
The in-repo copy is 13 days stale:

```
work/queue.jsonl   438 records, 33 matched
                   newest updated_at 2026-07-20T06:41:15Z
```

`ROADMAP.md:87` already flags that the sandbox copy diverges ("The sandbox copy
reports 33 matched where the real one has 134"). So the divergence is known,
but the effect is that the project's headline number has no in-repo evidence
and cannot be audited by anyone who does not have the author's WSL home
directory. Every conclusion I draw about match *counts* is therefore based on
the 33-record sample; conclusions about match *validity* rest on the 81/81
oracle and are unaffected.

**Action:** commit a periodic snapshot of the live queue (or its stats) into
the repo so the claim is falsifiable.

#### M4. `review_checks.py` reporting 0 findings is not evidence of cleanliness

It implements nine checks — `ext_variant_outlier`, `static_dropped`,
`signature_drift`, `param_argN`, `lost_comment_block`, `linkage_vs_asm`,
`angle_comment`, `entity_stub_signature`, `lost_comment`. **None** of them
covers duplicated code, fake symbols, `ext.ILLEGAL`, or magic numbers — the
four classes `quality_audit.py` exists for. The two tools are disjoint, and 0
from one alongside 48 from the other is consistent, not contradictory.

Three checks (`entity_stub_signature`, `linkage_vs_asm`, `lost_comment`) are
marked "exercised in the live run" and have no self-test coverage, so their 0
is unproven rather than verified.

**Action:** do not cite "review_checks: 0 findings" as a quality gate without
naming its scope.

---

### LOW

#### L1. `resolve_fake_symbol` is exposed to cross-overlay address aliasing

`automation/quality_audit.py:252` looks addresses up in a flat
`addr_to_name` map. As shown in §1.4, `0x80180490` is `gfxBanks` in RARE and an
unrelated `EInit` in BO6 — PS1 overlays share the 0x8018xxxx window. If the
index's `addr_to_name` ever ingests per-overlay symbol files, criterion (1)
will emit confident, wrong "the named symbol X" findings. It is not firing
today. **Action:** scope the lookup by overlay, or restrict criterion (1) to
main-RAM addresses (< 0x80180000).

#### L2. `e_collect` / `e_misc` duplicates — real, but honestly documented

`src/st/rno0/e_collect.c` (5 verbatim dupes) and `src/st/rno0/e_misc.c` (4)
remain private copies. Unlike H1/H2, these are properly justified in
`docs/P3b-rno0-remaining-data-segments.md`, which leads with *"RESULT
2026-08-02: none of them is shimmable. This is a dead end."* and gives measured
evidence — rno0's data slot is smaller than the shared header can emit
(`e_misc` short by 0x04, `e_room_fg` by 0x14), with the linker orphan symbols
that prove it. That document also retracts an earlier conclusion of its own.
This is the standard the rest of the ROADMAP should be held to. No action
beyond keeping them out of "our work" totals.

#### L3. Remaining duplicates with in-file justifications — acceptable

- `src/st/rno0/e_clock_room.c:43-45` — `UpdateBirdcages` / `UpdateClockHands`
  stay local because no0 and mar define them ahead of their own include.
  Stated in the file.
- `src/st/rno0/e_gorgon.c:19-23` — `StepTowards` duplicates
  `src/st/approach_s16.h:func_801CDC80` but needs external linkage for
  assembly callers in `unk_4F968.c`, and the header uses a different name.
  Stated in the file.
- `src/boss/bo6/us_39144.c` — `BO6_RicGetFreeEntity` /
  `BO6_RicGetFreeEntityReverse` duplicate `src/get_free_entity.h`. Overlay-
  prefixed exports; plausibly unavoidable, not separately justified in-file.

---

## 3. Things I could not verify

- **The 155 figure** (M3) — live queue is outside the repository.
- **Whether the H1/H2 shims would actually build.** Building was out of scope.
  Both findings are about the *stated reason* being contradicted by the tree,
  not proof that a shim succeeds.
- **`provenance_check.py`'s upstream corpus construction.** I used its output
  rather than re-deriving all 4266 upstream function bodies. I did
  independently re-derive the `rno0/st_common.c` ↔ `st_common.h` body equality
  with my own parser and got 22 identical bodies, agreeing with its 1.000
  scores — so its method checks out on the case that matters most.
- **Per-function assembly correspondence.** Under a whole-overlay SHA-1 oracle
  this is largely moot: an overlay that hashes correctly and contains no
  `INCLUDE_ASM` for a given function is proof that function's C is byte-exact.
  I confirmed both conditions (§1.1, §1.3) rather than diffing instruction
  streams by hand.

---

## 4. Verdict

The matching work is **genuine**. The oracle is upstream's, unmodified, and it
passes 81/81 against artifacts newer than every source file. Nothing is marked
matched while still being assembled from `INCLUDE_ASM`. There are no invented
symbols, no `ILLEGAL` ext usage, and the raw-address externs are all genuinely
unnamed data with in-file explanations of what they are.

The **honesty problem is in the accounting, not the binaries**. Roughly half
the C this fork defines is verbatim upstream code, and while
`provenance_check.py` measures that precisely, the headline "155 matched" does
not reflect it. Three specific ROADMAP statements (H1, H2) assert technical
blockers the tree contradicts, and those statements are what keep ~30 duplicate
functions in place.

The project's own tooling found most of this before I did. The gap is that its
conclusions have not been fed back into the documents that make the claims.

### Priority order

1. **H1** — correct `ROADMAP.md:486`; the three headers demonstrably exist.
2. **H2** — test the `st_common` shim or correct `ROADMAP.md:77`; 24 duplicate
   functions ride on it.
3. **H3** — add provenance to the queue schema; qualify the headline number.
4. **M1** — one-line fix; removes the audit's only false-positive class.
5. **M2** — one-line fix.
6. **M3** — snapshot the queue so the claim is falsifiable.
