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

## P1 — Reseed the queue against the post-merge set  *(staged, needs a connector restart)*

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

## P3 — Segment rno0's `.data` and `.bss` in the splat config

**Why:** this single change unblocks five of the seven remaining private
implementations. It is the highest-leverage item on the list and also the
riskiest, which is why it sits behind P1 and P2.

The blocker is placement, not code. rno0 keeps `.data` in unnamed blobs (0x2C,
0xE20) and `.bss` in one blob (0x53EB8), while every stage that shims
successfully has them segmented per file. Addresses recovered from the binary:

| segment | address | size |
|---|---|---|
| `create_entity` bss | 0x53EB8 | 16 bytes |
| `giantbro_helpers` bss | 0x54AC8 | 124 bytes |
| overlay bss end | 0x54B8C | |

`st_common`'s bss is a `short[256]`, 512 bytes, address not yet recovered. The
region between 0x53EC8 and 0x54AC8 is unattributed and must be identified before
writing any config.

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

- **Shimming `e_blade` or `e_gurkha`.** No stage shims them, so there is no
  shared implementation to defer to. Converting them would be wrong, not merely
  unhelpful. The index flags both.
- **"Fixing" upstream's 55 private implementations.** rno3/water_effects,
  mad/collision and the rest are upstream's own architecture. They were briefly
  counted as our defects; they are not.
- **Preparing a pull request.** Stated above, repeated here because the framing
  has drifted before.
