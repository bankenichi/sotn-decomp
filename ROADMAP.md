# Roadmap

State as of 2026-08-01. Companion to `ORCHESTRATOR.md` (how to dispatch) and
`MATCHING-LESSONS.md` (what has already gone wrong and why).

This fork is not preparing a pull request. Upstream has been offered the fork to
take what it wants. Success here means the harness produces work that is correct
and structurally idiomatic, and that the database makes the same mistake
impossible twice.

---

## Where things actually stand

| | |
|---|---|
| Oracle | **81/81** (was 77/77 before the upstream merge added RCHI and RDAI) |
| Baseline | merged to `upstream/master` @ `f6bfa379`, 2026-08-01 |
| Queue | 134 matched, 34 escalated, 27 deferred, 243 todo |
| Index sees | 370 unmatched US functions, data symbols excluded |
| Our private impls in rno0 | 9 found, 2 resolved, 7 blocked on splat config |
| Manual review | all 142 defined functions read, 2026-08-01; 15 defects fixed |
| Provenance | 124 authored; 79 (64%) are copies, 74 shimmable, 4 should become shared headers |
| Twins | 174 of 335 unmatched stubs have a candidate already in the tree; 145 by name |
| Twin audit | 30321 matched pairs cross-checked; 10 of ours are private copies of shared code |

The queue and the index disagree (304 vs 370) because upstream's merge added 32
unmatched functions in RCHI and RDAI that the queue has never seen. Reconciling
that is P1 below.

### Where the remaining work is

```
ST/RNO0  115    BOSS/BO6  98    BOSS/BO0  66    MAIN  36
ST/RCEN   19    ST/RDAI   18    ST/RCHI   14    ST/MAD  3
```

Three overlays hold 75% of it. RNO0 is also where every one of our private
implementations lives, so it carries both the most functions and the most
structural debt.

---

## P0 — Do not regress

These are cheap, and skipping them is how a good tree quietly becomes a bad one.

1. **Verify 81/81 before and after every session.** `verify_build` hashes what is
   on disk, so always build immediately before verifying. A 77/77 result now
   means a stale tree, not a healthy one.
2. **Rebuild the index after every upstream merge**, and re-point `UPSTREAM_REF`
   at `upstream/master`. Never at our `HEAD` — see `MATCHING-LESSONS.md` §12.
3. **Consult `shim_viable()` before hand-writing any shared-implementation
   file.** It is free and it has already been right six times out of six.

## P1 — (resolved 2026-08-02) Queue reseeded; the two totals differ BY DESIGN

**Reseed: done.** Re-running `queue_init` on 2026-08-02 reported `added 0
records`, and it is additive with id-skipping, so every seed id is already in
`/home/kenichi/sotn-work/queue.jsonl`. RCHI (14) and RDAI (18) are present. The
"needs a connector restart" note in the old heading is stale: `queue_init` is in
the live allowlist and the connector has been restarted since.

**Reconciling the totals: the premise was wrong.** This entry asked to make
`queue_stats` and the index agree. They cannot and should not:

- `codebase_index.py` indexes from **`upstream/master`**, deliberately (see P0
  item 2 and MATCHING-LESSONS §12). Its `unmatched` counts what UPSTREAM has
  not matched: 334 after a rebuild on 2026-08-02.
- `queue_stats` counts OUR work: 470 records, of which 155 are matched by us.

So the numbers measure different populations and equality would be a bug, not a
goal. What matters is the blind-spot check the entry actually cared about, and
that one passes: every seeded function has a record.

The index rebuild also surfaced a shim candidate this file had not recorded:
`rno0/st_common` is blocked on a missing `.bss, st_common` segment. It carries
no `INCLUDE_ASM` stubs today, so shimming it would delete a duplicated copy
rather than match anything new.

### Original entry

`automation/seed.us.txt` is written and a `queue_init` action is added to the
connector. It cannot be called until the connector is restarted, because the
reseed MUST run in WSL: `SOTN_QUEUE` defaults to `~/sotn-work/queue.jsonl`, so
a different `HOME` resolves to a different file. The sandbox copy reports 33
matched where the real one has 134, and seeding the wrong one would fork the
harness state while appearing to succeed.

After restart: `queue_init` (additive, skips existing ids), then `queue_stats`
should total 370 rather than 438-minus-matched.

**Why first:** the fleet is currently working from a list that predates the
merge, so it cannot see RCHI or RDAI at all, and 66 functions are invisible to
it. Everything downstream inherits that blind spot.

- Reseed from the index's `unmatched` (370), not from the old seed file.
- Rank by `automation/decl_coverage.py`, which scores how much of a function's
  symbol usage is already declared. High coverage means a model has what it
  needs; low coverage means it will guess a type and miss.
- Reconcile the two totals so `queue_stats` and the index stop disagreeing. They
  count different things today (all-version `INCLUDE_ASM` vs US code functions),
  and that ambiguity has already caused one bogus "1277 remaining" figure.

**Done when:** `queue_stats` totals match the index, and RCHI/RDAI functions
appear in `queue_list`.

## P2 — Run the permuter against the 34 escalated

**Why:** the permuter is free, it has never been run against this pool, and
escalated records are by definition the ones that got close. Spending model
quota on them before exhausting a free search is the exact waste the tiering
exists to prevent.

Sequencing matters and is easy to get wrong: the permuter searches for a
byte-exact variant of an **already-compiling** function. It cannot fix a wrong
parameter type or a missing shared implementation, because neither is a search
problem. Exhaust the structural and type causes first, then permute the residue.

**Done when:** every escalated record has either matched, or carries a note
saying the permuter was run and what it exhausted.

## P2b — Port BO6's 65 named twins from `src/ric`  *(open, no blockers)*

`automation/asm_twin_finder.py` found that 65 of BO6's unmatched stubs have a
same-named function in `src/ric`. Four have been ported by hand and all four
matched, two of them on the first build.

These are NOT shimmable and must not be treated as such. RIC's copies read
`g_Player` and `PLAYER`; BO6's read `g_Ric` and `RIC`, which are different
objects at different addresses. The port is mechanical but not blind:

1. `python3 automation/asm_twin_finder.py --symbol <SYM>` for the twin.
2. Read the twin's C, then read the stub's assembly and resolve every global
   BY ADDRESS, not by name affinity. `RIC_facingLeft` is `g_Entities[64] +
   0x14`, which is `RIC.facingLeft`; writing the struct access matched.
3. Diff the twin against the assembly before copying. Of the four done,
   `BO6_RicCreateEntFactoryFromEntity` differed from RIC's by a slot window
   AND a missing flag propagation. Copying it verbatim would have failed.

The same finder reports 64 named twins in rno0, but almost all of those point
at `src/st/<name>.h` shared implementations, so they are P3's work rather than
this section's. rchi's 15 point at sibling stage overlays; `e_bat` and
`e_breakable` there were already investigated and rejected upstream, and the
rejection notes are in `src/st/rchi_psp/`.

**Done when:** every BO6 stub with a `src/ric` twin has either matched or
carries a note saying what the twin could not explain.

## P3 — (resolved 2026-08-01) rno0's `.bss` is segmented; four files shimmed

The bss is fully attributed and segmented, and the mechanism is proven on real
code four times over. `create_entity.c`, `giantbro_helpers.c` and
`e_clock_room.c` are now shims, and `unk_4A320.c` was split out to match the
upstream file boundary. Roughly 630 lines of private copy deleted, 81/81
throughout.

```yaml
      - [0x53EB8, .bss, create_entity]      # 0x10
      - [0x53EC8, .bss, bss]                # 0xC00 anonymous pad
      - [0x54AC8, .bss, giantbro_helpers]   # 0x7C
      - [0x54B44, bss]                      # 0x48, e_clock_room's, left as asm
```

The trailing 0x48 is e_clock_room's: `g_Statues` is at 0x801D4B48, confirmed by
the shim resolving against it. Naming that segment would require
`e_clock_room.c` to *define* all three symbols in C, two of which have no known
purpose, for no gain. It is left as extracted assembly deliberately.

`.data` is still unsegmented and does NOT need to be for any shim done so far:
only `header`, `e_init` and `e_room_bg` contribute `.data`, and all three
already have named segments. It blocks exactly one known case, tracked
separately.

### What made the shims tractable, and is now tooling

- `automation/overlay_size_check.py` compares every function's map address
  against `config/symbols.us.<ovl>.txt`. The first divergence names the
  function AFTER the oversized one, and the delta is how many bytes wrong it
  is. This replaced repeated 15k-token asm diffs with a one-second answer.
  `<ovl>_BSS_START` equals `TEXT_END`, so a shifted bss with internally correct
  symbols is a TEXT bug, not a segmentation one.
- The worker prompt now recognises an inverted-castle overlay whose twin is a
  first-castle file and lists the mirrorings to expect: sign-flipped position
  offsets, swapped `posX` `++`/`--`, different tilemap indices, a different
  `ANIMSET_OVL` bank, and `CEN_OPEN` -> `RCEN_OPEN` (+228 = 0xE4, so a
  relocation differing by exactly 0xE4 is that, not a wrong symbol).

## P3b — (resolved 2026-08-02) rno0 shims `e_red_door.h`

**Done.** `EntityRedDoor` matched, the duplicated `EntityIsNearPlayer`
(`func_us_801B9A8C`) deleted, 81/81 verified, 0 shifted symbols across 43
overlays. Commit `7c6ad016c`. Full working plan in
`docs/P3b-rno0-red-door-plan.md`.

It was far smaller than this entry assumed. rno0's `unk_39A8C` segment **already
was** `e_red_door.c`, merely misnamed: its text span `0x39A8C..0x3A73C` is
`0xCB0`, byte-identical to rcen's `e_red_door` segment. So the work was one
`.data` split plus two renames, not the segmentation surgery `.bss` needed.

What actually had to be discovered, none of it guessable:

- `g_eRedDoorUV` at `0x1454`, found by searching `RNO0_BIN` for the
  initialiser's 24-byte signature. The method was validated first against
  `RCEN.BIN`, where it reproduces the `0xE78` rcen's config already declares.
  `EntityRedDoor.s` independently references `D_us_80181454`.
- `g_RedDoorTiles = 0x80180E20`, confirmed by USE: the assembly does
  `sll $v0, $a0, 4` (params * 16) added to that base and stores into
  `g_Tilemap + 0xA`, which is the header's
  `g_Tilemap.fg[tileIdx] = g_RedDoorTiles[params][i]`.
- `D_us_80181134` had to be named explicitly. splat emits no glabel for it in
  rno0 because it falls mid-object inside the unnamed `0xE20` blob, so the
  header's `extern` would not have linked.
- `g_EInitCommon` needed the same `OVL_EXPORT` define that `e_clock_room.c`
  already uses; rno0 exports it as `RNO0_EInitCommon`.

**Lesson worth reusing:** before trusting a byte-signature search to locate a
`static` array, run it against an overlay whose answer is already in a config
file. A technique that reproduces a known boundary can be believed on an
unknown one.

### Original entry, kept for context

**Why:** this single change unblocks five of the seven remaining private
implementations. It is the highest-leverage item on the list and also the
riskiest, which is why it sits behind P1 and P2.

The blocker is placement, not code. rno0 keeps `.data` in unnamed blobs (0x2C,
0xE20) and `.bss` in one blob (0x53EB8), while every stage that shims
successfully has them segmented per file. `.text` and `.rodata` are ALREADY
per-file segmented, so that single bss line is the entire obstacle.

### The bss is now fully attributed (2026-08-01)

Earlier notes guessed at this and were wrong twice: `st_common` has no bss here,
and the "unattributed 3 KB" is not a gap. Recovered from
`build/us/strno0.map` plus each shared header's own declared section sizes:

| address | size | owner | evidence |
|---|---|---|---|
| 0x53EB8 | 0x10 | `create_entity` | `src/st/create_entity.h` states `BSS 0x10`, and its 6 declarations sum to exactly 16 |
| 0x53EC8 | 0xC00 | anonymous pad | the tree's own idiom: `np3/bss.c` and `nz0/bss.c` are `STATIC_PAD_BSS(0xC00)` and nothing else |
| 0x54AC8 | 0xC4 | `giantbro_helpers` | 8 `D_us_801D4*` symbols summing to 196; `giantbro_helpers.h` carries `STATIC_PAD_BSS(104)` |
| 0x54B8C | | overlay bss end | |

**0x10 + 0xC00 + 0xC4 = 0xCD4, which is exactly the bss size the map reports.**
The attribution closes with no gap and no overlap, so the proposed segmentation
is arithmetically complete rather than a best guess:

```yaml
      - [0x53EB8, .bss, create_entity]
      - [0x53EC8, .bss, bss]
      - [0x54AC8, .bss, giantbro_helpers]
  - [0x54B8C]
```

Two things worth knowing before editing. Every rno0 `.c` object contributes
ZERO bss; all 0xCD4 comes from one extracted object,
`asm/us/st/rno0/data/53EB8.bss.s.o`. And splat's label
`g_LayoutObjPosVertical` currently appears to span 3076 bytes when it owns 4,
because splat sizes a symbol by distance to the next label and the 0xC00 pad
carries no label at all. Do not trust that number.

The conflict a shim hits is now concrete: `src/st/create_entity.h:15` DEFINES
`g_LayoutObjPosHorizontal` and friends as `static`, while
`src/st/rno0/create_entity.c:12` declares them `extern` and takes them from the
asm blob. Including the header emits those statics into the TU's own bss, which
cannot land at the right address while the overlay's bss is one anonymous
segment.

**Risk, and treat this as the main constraint:** splat config changes drive
re-extraction, which can overwrite source files. Back up `src/st/rno0/` and dry
run before committing anything. This is the one item on the roadmap that can
damage the tree rather than merely fail.

**Done when:** `shim_viable` reports VIABLE for the five, each is shimmed one at
a time, and 81/81 holds after each.

## P3b — (resolved 2026-08-01) The 9 non-shimmable copies, classified

Two subagents read all nine against their claimed source AND against this
overlay's own ground-truth asm. **None is functionally wrong.** The split:

**Four should become shared headers.** This is the outcome upstream would most
want, and it converts a copy into infrastructure rather than deleting it:

| ours | destination | consumers |
|---|---|---|
| `e_clock_room.c:UpdateBirdcages` | `src/st/clock_room_entities.h` | no0, rno0, rno0_psp |
| `e_clock_room.c:UpdateClockHands` | `src/st/clock_room_entities.h` | no0, rno0, rno0_psp |
| `giantbro_helpers.c:func_801CE1E8` | `src/st/giantbro_helpers.h` | no2, np3, rno0, rno0_psp |
| `giantbro_helpers.c:func_801CE228` | `src/st/giantbro_helpers.h` | no2, np3, rno0, rno0_psp |

Each was verified instruction-by-instruction against 2 or 3 overlays' asm with
zero divergence. `UpdateClockHands` needs its `#ifdef VERSION_PSP` split
preserved; `clock_room_entities.h` already uses that idiom.

Why the clock-room pair sat outside the header while its neighbour
`UpdateStatueTiles` sat inside it: the header groups the *entity update*
functions, and these two are utilities called from `EntityClockRoomController`,
which is not shared because it is full of per-overlay room-state logic. The
boundary was drawn at "everything after the controller", not at "everything
reusable". No functional reason blocks the move.

**Two are covered by P3 after all** and were only listed here because the
scanner named the wrong source: `st_common.c:DestroyEntity` (real twin
`src/destroy_entity.h`, which `src/st/st_common.h` already includes) and
`st_common.c:SetSubStep` (real twin `src/st/st_common.h`). 27 of 28 stage
overlays get both free from a 4-line shim; rno0 is the sole outlier.

**Three are legitimate per-overlay implementations.** `BO6_RicSetAnimation` is
an idiom duplicated 5+ times across the tree. `func_us_801B9C14` zeroes four
fields where the cited match zeroes two. `RicEntitySubwpnCross` adds an entire
"knocked out of the air while spinning" state RIC does not have, including a
double store of `timer` that the byte-matched asm confirms is in the original.

### What this cost the tool, and what it bought

Three of the nine were MISATTRIBUTIONS by `provenance_check.py`, and finding
that was worth more than the classifications. Two defects, both now fixed and
both regression-tested against these nine cases:

1. **Generic shapes.** Erasing identifiers is what lets the metric see through
   a rename; it is also what makes every "load pointer, store three fields"
   setter identical. Now gated on ambiguity, not on length: if more than 3
   distinct upstream functions tie at the top score, no attribution is made.
   Gating on flatness instead was tried first and wrongly suppressed
   `UpdateClockHands`, a real copy.
2. **Set similarity cannot count.** `a=0;b=0;c=0;d=0;` and `a=0;b=0;` erase to
   the same shingle SET, so Jaccard returned 1.000 for bodies of different
   size. Scores are now scaled by length agreement.

Corrected distribution: 79 of 124 are copies (was 83), 3 unattributable.

## P4 — (resolved 2026-08-02) Review checks now gate the worker

**Done.** `review_gate()` in `worker_direct.py` runs `review_checks.py`'s
functions as a PRE-BUILD gate, reusing them rather than reimplementing so the
two callers cannot drift. Wired: `linkage`, `ext`, `static`, `signature`,
`stub`. Pinned by `automation/test_review_gate.py` (19 checks), which proves the
end-to-end rejection against real cross-TU callers rather than a fixture.

`virtual_apply()` reproduces `apply_code`'s substitution in memory, because the
checks need whole-file context. The test asserts the candidate really lands in
the inspected text: if that regex ever drifts, the gate would silently inspect
the unmodified file and pass everything, which is the dangerous failure because
it looks like success.

Left manual as this entry already specified: `angle` and `argn`. Also left to
review time: `comment` and `block`, which compare against a previous C version
that does not exist before apply.

Architecture is now written up in `docs/HARNESS-ARCHITECTURE.md`.

### Original entry

## P4 — Wire the review checks into the worker

`automation/review_checks.py` (9 checks) and `automation/provenance_check.py` currently inform a human. It should gate the
worker the same way `quality_gate()` does, so a generated function cannot be
accepted while it names the wrong union variant or narrows a symbol's linkage
below what the assembly requires. The linkage check in particular belongs
*before* the build, since it predicts a link error the build would otherwise
surface minutes later.

Two classes were reviewed and deliberately left manual, with the measurement
recorded in `MATCHING-LESSONS.md` section 20: "same as X except Y" comments
that understate real differences, and descriptive parameter names replaced by
`argN`. Both need a reader.

## P5 — (closed 2026-08-01) The named quality classes are clear

Both items that stood here are done, and the method each used is worth keeping
because it generalises:

- **`ext.ILLEGAL` is gone from the tree.** Resolve these from evidence, never
  affinity. `polarPlacePartsList` fell to the shared header (ext is at 0x7C, so
  `ILLEGAL.u8[0x2C]` is `GH_Props.unkA8`). `func_us_801C8590` fell to the
  dispatch table: its slot in BO6's `D_us_8018158C` matches
  `RicEntityCrashReboundStoneParticles` in RIC's table, which uses
  `ext.subweapon.timer`. See `MATCHING-LESSONS.md` §18 for the procedure.
- **`func_us_801BB370` no longer casts.** `SubweaponDef` covered every offset it
  was using, and its size 0x14 was the stride the index was multiplied by. The
  two loose addresses resolved to `ext.subweapon.subweaponId` and
  `timers[ALU_T_INVINCIBLE]`.

Remaining audit output is 67 duplicates, all blocked on P3, and nothing else.

## P6 — (partly resolved 2026-08-02) The shim gate runs before the model

**Done:** `shim_gate()` in `worker_direct.py` asks `shim_viable()` before any
model call and defers records whose correct fix is a shim, with marker
`SHIM_INSTEAD_OF_GENERATE`. Pinned by `automation/test_shim_gate.py` (21
checks).

Measured over the 417 `INCLUDE_ASM` stubs in `src/st`: 288 have no shared
implementation (generating is correct), 121 have one but are blocked, and 8 are
shimmable now. **Only the 8 are deferred.** This entry said a record targeting a
shared-implementation file "should not reach a model at all until the blocker is
cleared"; applied literally that defers all 129 and stalls 29% of the queue
behind structural work with no automated consumer. The test asserts both edges,
because the failure modes are opposite: too eager starves the fleet, too lax
brings the duplicates back.

**RETRACTED.** An earlier version of this entry called those 8 stubs "free
matches sitting behind a three-line shim each". Every one was a gate false
positive: 4 were different implementations (size divergence up to 5.36x), 2
were psp targets the us oracle cannot verify, and the rest need stage data
tables with no `.data, <stem>` segment to hold them. The gate was hardened and
now defers zero of them. See the size-divergence section below.

**Relocation detector: DONE.** `automation/relocation_check.py`, 9 self-test
cases. Diffs a built overlay against `disks/us/...` and reports whether every
differing word is relocation-shaped (same opcode, same registers, different
16-bit immediate) with one dominant delta. It refuses to name a constant unless
one covers 80% of the differences, because acting on the wrong constant is
worse than acting on nothing.

Two things it found immediately, both about the harness rather than the game:

- **Build artifacts go stale.** A worker that fails restores the SOURCE but
  leaves `build/us/<OVL>.BIN` behind. After the fleet stopped, `git status` was
  clean while the oracle read 80/81 on a reverted RCEN candidate. The tool now
  warns when `src`/`config` are newer than `build/us`, and a rebuild restored
  81/81.
- **`config/check.us.sha` is not uniformly lowercase.** CHI's line reads
  `4ea14c8B54B8526e...`. A case-sensitive hash compare reported CHI as failing
  while `shasum -c` and `verify_build` both passed it. Casefold both sides.

**Still open from this entry:** tier 2/3 consumers for `escalated` (item 2).

### 2026-08-02 result: four stems shimmed, 7 functions matched

`st_update`, `collision`, `e_particles` and `e_medusa_head` are all shimmed.
81/81, 0 shifted symbols across 43 overlays after each. Seven functions matched
(`Update`, `UpdateStageEntities`, `HitDetection`, `EntityDamageDisplay`,
`EntitySoulStealOrb`, `EntityMedusaHeadSpawner`, `EntityMedusaHeadBlue`) and
three private copies deleted (`Random`, `EntityEnemyBlood`,
`EntityMedusaHeadYellow`).

**The recipe, in the order that avoids wasted builds:**

1. Check whether the header declares UNINITIALISED file-scope storage. Only
   `st_update.h` did (`g_ItemIconSlots`), and it needs a `.bss, <stem>` segment
   or the storage is appended after all other bss and shifts the overlay.
2. Locate `.data` with `find_data_segment.py`, which calibrates against a peer
   before trusting a hit.
3. Expect to NAME symbols. Every one of the four needed it, and the linker says
   exactly which: `g_ItemIconSlots` (was `D_us_801D4B4C`, also used by
   `e_collect.c`), `g_EInitDamageNum` (was `D_us_80180ABC` in `e_init.c`), and
   three medusa-head `EInit`s bridged by `#define` because rno0 names them
   `g_EInitMedusaHead1/2` and `OVL_EXPORT(EInitSpawner)`.
4. Read mappings OFF THE ASSEMBLY. The blue/yellow `EInit` assignment was
   settled by the `bnez params` branch in `EntityMedusaHeadBlue.s`, not guessed.

**A link error is the best failure to get here.** Unlike a checksum mismatch it
names the missing symbol AND the file that wants it, which is how the
`e_collect`/`g_ItemIconSlots` overlap and `g_EInitDamageNum` were both found in
one build each.

`collision` was the one surprise: `src/st/collision.h` includes
`entity_damage_display.h` at its end, so a single shim covers both functions.
That is also why no stage has a separate entity_damage_display file.

### The remaining shim lever, measured 2026-08-02

A full sweep of all 130 shared implementations found 129 stubs in files a
shared header could in principle cover. Excluding `_psp` (a build target the us
oracle cannot verify), **seven rno0 stems are blocked on one single thing** — a
missing `.data, <stem>` splat segment:

```
e_misc 14   collision 2   st_update 2   e_medusa_head 2
e_collect 1   e_particles 1   e_room_fg 1        = 23 stubs
```

This is what P3b originally meant by "unblocks five of the seven remaining
private implementations". The `e_red_door` work resolved the first of them and,
more usefully, established the method: locate the `static` array by its
initialiser byte signature in the overlay binary, and validate the technique
against a peer overlay whose answer is already in a config file before trusting
it. See `docs/P3b-rno0-red-door-plan.md`.

Not blocked on data placement, and NOT shimmable: `e_lock_camera` (0.36x its
peers' text) and `e_breakable` (obliges rno0 to supply stage data tables).
`e_blade`, `e_gurkha` and `e_hammer` have no shared implementation at all.

### Finding the .data addresses is now a tool

`automation/find_data_segment.py`. When a shared header defines its own data,
those bytes are identical in every stage that shims it, so a peer's bytes are
the search pattern. Every run **calibrates first**: it takes the pattern from
peer A, searches peer B, and requires the hit to equal the address B's splat
config already declares. If that fails it refuses to answer rather than
producing a number.

It re-derived `e_red_door` at `0x1454` — the address found by hand — from a
peer's bytes, which is the strongest evidence the method is sound. Results for
rno0:

```
st_update      0x1048  size 0x4C     collision   0x1094  size 0x3C0
e_particles    0x1CB8  size 0x80     e_medusa_head 0x3354 size 0x78
e_misc, e_collect, e_room_fg  -> REFUSED (bytes are stage-dependent)
```

An independent cross-check that cost nothing: `st_update 0x1048..0x1094`,
`collision 0x1094..0x1454` and the hand-found `e_red_door 0x1454` tile with no
gaps, in the same order as their `c` segments. splat emits a file's data in
text order, so five independent searches agreeing on a contiguous run is far
stronger than any one of them.

### But .data placement is NOT the last blocker (attempted 2026-08-02)

`st_update` was taken end to end: segment added at `0x1048`, file reduced to a
shim. It **compiled and linked**, every other overlay passed, and RNO0 came out
**0x40 bytes too large**.

`overlay_size_check.py` localised it immediately: `BSS_START == TEXT_END` and
`g_Statues` landed at `0x801D4B88` against an expected `0x801D4B48`, delta
`+0x40`. Per the map-address diagnostic that means **the fault is in TEXT**, not
in data or bss. Reverted; tree back to 81/81.

So the shared header compiles 0x40 larger under `rno0.h` than rno0's own code,
even though the declared `c` segment sizes are byte-identical (0x434 both, and
0x0 delta for all seven stems). The declared size describes the ORIGINAL binary;
it does not promise the header will compile to it here.

**RESOLVED 2026-08-02. `st_update` is shimmed; 81/81, 0 shifted symbols.**
`Update` and `UpdateStageEntities` matched, `Random`'s duplicate deleted. It
needed THREE segments, and only the first was obvious:

```
.data, st_update  0x1048   the header's `unused` + UNK_Invincibility0
.bss,  st_update  0x54B4C  g_ItemIconSlots, 0x40, was D_us_801D4B4C
c,     st_update  0x37324  already present
```

The bss one is the trap: without it the storage is still emitted, just appended
after every other bss object, silently pushing the whole overlay 0x40 higher.

`g_ItemIconSlots` had to be NAMED in `config/symbols.us.strno0.txt`, not left as
`D_us_801D4B4C`. `e_collect.c` declared `extern u16 D_us_801D4B4C[32]` against
the same storage, so once st_update.c owned the segment that auto-generated
label vanished and the link broke. Renaming both sides to the real name fixed it
and removed a raw address from e_collect.c as a bonus.

**Sequence of wrong turns, kept because each was cheap and each ruled something
out.** Inverted-castle divergence (refuted: nine inverted stages shim this
fine). The stage-header include (refuted: rebuilding without `#include "rno0.h"`
gave an identical delta). Placing the bss BEFORE `g_Statues` (refuted by the
linker, which named `e_collect.c` as another user of that exact address). The
linker error was the most informative signal of the three -- far better than a
checksum failure, because it names the symbol AND the file.

**ROOT CAUSE, for the record: it is `.bss`, not text and not data.**

Two hypotheses were tested and both refuted before the map gave the answer:

- *Inverted-castle divergence.* Refuted: nine inverted stages shim `st_update`
  successfully (rare, rcat, rcen, rchi, rdai, rno3, rnz0, rtop, rwrp). rno0 is
  the only us stage that does not.
- *The stage-header include.* Peer shims split two ways -- chi/no0/nz0 include
  only the shared header, are/cat/rcen/rno3 also include their stage header.
  Rebuilt with `#include "rno0.h"` removed: **identical +0x40**. Refuted.

The linker map settles it. Every `.data` object, every `.rodata` object and
every `c` segment lands at exactly its configured address. The growth is here:

```
bss 0x801d4ac8  0x7c  giantbro_helpers.c.o
bss 0x801d4b44  0x40  st_update.c.o      <- emitted, nothing reserved for it
bss 0x801d4b84  0x48  54B44.bss.s.o      <- g_Statues, pushed +0x40
```

`st_update.h` declares 0x40 of uninitialised static storage. rno0 has no
`.bss, st_update` segment, so it is appended after everything and shoves the
trailing bss along. **This overlay's own config predicted it**, in a comment
written during the earlier bss work: "The trailing 0x48 belongs to some other
file... np3 attributes the equivalent region to st_update." And np3 indeed has
`[0x533F4, .bss, st_update]` where rno0 has an unnamed `[0x54B44, bss]`.

**Correcting an error in the earlier diagnosis above:** `overlay_size_check`
reports "BSS_START equals TEXT_END, so the fault is in TEXT". That reasoning is
only valid when BSS_START itself is wrong. Here BSS_START was correct and the
growth was *inside* bss, so the message pointed at the wrong section. The check
should say so; see the follow-up task.

**Not a clean rename, which is why it is still open.** rno0's trailing region is
0x48 while the shim emits 0x40, and `g_Statues` sits at `0x801D4B48`, four bytes
into it. So st_update's storage cannot simply take that region; the 0x40 has to
be carved from the right place, most likely out of the `STATIC_PAD_BSS(0xC00)`
in `src/st/rno0/bss.c`. Establish where it belongs in the ORIGINAL before
moving anything.

The `.data` addresses found by `find_data_segment.py` are independently
cross-checked and were never the problem.

### Original entry

## P6 — Harness: make the four blockers unskippable

`shim_viable` currently informs a human. It should gate the worker: a record
whose target is a shared-implementation file should not reach a model at all
until the blocker is cleared. The same applies to the quality gate — the four
blockers belong in `quality_gate()` alongside the existing defect checks.

Also worth building, in rough value order:

1. A **relocation detector**. When an overlay fails, diff it against
   `disks/us/ST/<OVL>/<OVL>.BIN` and report whether the differences are all
   `%hi`/`%lo` pairs off by one constant. If they are, no C change will help and
   the harness should say so instead of burning attempts. This was worked out by
   hand twice; it should be a tool.
2. **Tier 2/3 consumers.** `escalated` still has no automated rung above Tier 0.
   Records accumulate until an orchestrator picks them up by hand.

---

## Deliberately not doing

- ~~**Shimming `e_blade` or `e_gurkha`.** No stage shims them...~~
  **RETRACTED 2026-08-02. This was false and it cost real work.** `e_blade.h`,
  `e_gurkha.h` and `e_hammer.h` all exist, and `no2` and `np3` each ship a
  four-line pure shim of them. `provenance_check.py` scores rno0's private
  copies at 1.000 against those headers.

  The claim came from `codebase_index.py` building `shimmed_by` with a
  FILENAME pattern, so a header shimmed from a differently-named file reported
  `shimmed_by == []`. The rule now matches on what a file INCLUDES, and both
  stems immediately reclassified from "no shared impl to use" to a real,
  fixable blocker: no `.data, <stem>` splat segment.

  This ring-fenced 7 rno0 stubs plus ~321 lines of duplicated copy as forbidden
  work. Same root cause hid `e_lock_camera`, which is now MATCHED.

  **Lesson: "X is impossible" is the most expensive kind of documentation
  error, because nobody re-tests it.** Any such claim in this repo should name
  the evidence and the date, so it can be re-checked rather than inherited.
- **"Fixing" upstream's 55 private implementations.** rno3/water_effects,
  mad/collision and the rest are upstream's own architecture. They were briefly
  counted as our defects; they are not.
- **Preparing a pull request.** Stated above, repeated here because the framing
  has drifted before.
