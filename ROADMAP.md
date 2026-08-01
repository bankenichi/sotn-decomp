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
| Provenance | 124 functions authored; 83 (67%) are copies of upstream, 74 of them shimmable |

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

## P1 — Reseed the queue against the post-merge set

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

## P3b — The 9 copies that shimming will NOT fix

**Why separate from P3:** `provenance_check.py` grades every function we
authored against upstream. 83 of 124 are copies, which substantiates upstream's
"just copies of functions we already have" exactly. But 74 of those come from a
shared `src/st/*.h` and vanish the moment P3 lands. Nine do not:

| ours | copied from |
|---|---|
| `us_39144.c:BO6_RicSetAnimation` | `boss/dop_anim.h:func_8010DA2C` |
| `us_39144.c:func_us_801B9C14` | `boss/bo4/unk_45354.c:EnableAfterImage` |
| `us_3E79C.c:RicEntitySubwpnCross` | `ric/pl_subweapon_cross.c` (0.809) |
| `e_clock_room.c:UpdateBirdcages` | `st/no0/clock_room.c` |
| `e_clock_room.c:UpdateClockHands` | `st/no0/clock_room.c` |
| `giantbro_helpers.c:func_801CE1E8` | `st/no2/4966C.c` |
| `giantbro_helpers.c:func_801CE228` | `st/no2/4966C.c` |
| `st_common.c:DestroyEntity` | `destroy_entity.h` |
| `st_common.c:SetSubStep` | `boss/dop_anim.h:func_8010DA2C` |

For each, the question is which of three it is, and the answer differs per row:

1. the body genuinely recurs per overlay and a private copy is correct
   (upstream ships 55 of these itself, so this is a real category);
2. it should become a shared header the way `destroy_entity.h` and
   `dop_anim.h` already are, which is the strongest outcome and the one
   upstream would most want;
3. it is a copy that was never checked against this overlay's own asm and may
   be wrong in a way the byte match cannot show, since two overlays' versions
   can differ in constants while sharing a shape.

Do not batch these. Each needs its own asm comparison.

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
