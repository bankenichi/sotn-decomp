# Audit: 77 escalated, 43 deferred

> **CORRECTIONS, 2026-08-10.** Three claims below were wrong. They were
> written from reading queue notes rather than reading code, and that shows.
> Read this box before acting on section 4 or 6.
>
> 1. **"Cross-overlay guard is only applied to raw `D_us_` names" (section 5,
>    item 3) is FALSE.** It has always been applied to every symbol. The real
>    defect was that nothing looked for a DEFINITION in the record's own
>    overlay before giving up, which is what hid `g_EInitGaibon` at
>    `src/st/rchi/e_init.c:96`. Fixed in `5b4f67d2d`; it resolved zero
>    additional live records.
>
> 2. **"A1 missing declaration: the candidate code is already written and
>    fails only because an `extern` is absent" (sections 2b and 4) is FALSE,
>    and it invalidates the Stage 2 plan as written.** The escalation path in
>    `worker_direct` reports only the NOTE:
>
>        sched("report", "--id", rec["id"], "--status", "escalated",
>              "--notes", (best_build or best)[:250])
>
>    The failing candidate C is never persisted. `save_candidate` runs only
>    for compiling-but-differing candidates (permuter seeds). So for all 12
>    A1 records the function is still an `INCLUDE_ASM` stub and **there is
>    nothing to write-build-revert**. Stage 2 cannot be "apply the existing
>    candidate"; see the corrected plan in task #96.
>
> 3. **The `26 records, zero model calls` headline in section 4 is
>    overstated.** 14 of them (the 13 stale `ILLEGAL` rejects and the false
>    escalation) were genuinely free and have been requeued. `EntityGaibonLeg`
>    was genuinely free and is matched. The 12 A1 records are NOT free: they
>    need a re-attempt, which costs model calls. The honest figure is
>    **15 free, 12 unblocked-but-not-free**.
>
> What survives unchanged: the class analysis, the counts, the too-large
> measurements, and gap 5 (nothing validated candidate text before writing it
> to `src/`), which turned out to be the most valuable finding in the
> document.


Date: 2026-08-10. Queue: 470 records (149 todo, 0 claimed, 0 near, 201 matched,
77 escalated, 43 deferred).

Reproduce with:

```
run_analysis escalation_triage.py
run_analysis deferred_triage.py
```

The question this answers: of the 120 records the fleet has given up on, how
many are blocked by something a program can fix, and what is the plan for the
rest.

Answer up front: **at least 26 of 120 need no model call at all.** One of them
is a finished match.

---

## 1. Free match available now

`us:ST/RCHI:EntityGaibonLeg` is deferred with:

> PERMUTER_EXHAUSTED: scored 0 but does not compile in its real file; needs
> declarations the permuter cannot add. COMPILE ERROR: `g_EInitGaibon`
> undeclared at src/st/rchi/e_gaibon.c:12

**The permuter already scored zero.** The only thing between that and a match
is one line, and the symbol is defined in the same overlay:

```
src/st/rchi/e_init.c:96:  EInit g_EInitGaibon = {ANIMSET_OVL(4), 0, 76, 515, 0x0FE};
```

So `extern EInit g_EInitGaibon;` in `e_gaibon.c`, build, verify. This is the
highest value/effort ratio in the entire backlog and it has been sitting in
`deferred` behind a note that reads like a failure.

Caution that cost me a wrong answer while writing this: grepping for
`extern[^;]*g_EInitGaibon` finds only `src/st/nz0/nz0.h:152`, a DIFFERENT
overlay, which would be the wrong object. The right symbol is a
**definition**, not a declaration, and only turns up by searching the
overlay's own `e_init.c`. Any automation for this class must search for both
forms and must reject cross-overlay hits.

---

## 2. Escalated: 77

`escalation_triage.py` reports harness 2, symbol 43, real 13, unknown 19.
The `symbol` and `unknown` buckets both decompose further, and that is where
the automatable work is.

### 2a. `unknown` (19) is not unknown: it is every quality reject

The triage tool has no class for quality rejects, so all 19 land in "read it".
They are:

| sub-pattern | n | records |
|---|---|---|
| uses `ext.ILLEGAL` | 13 | `8019D260`, `801B1864`, `801CFD70`, `801B19FC`, `801CFB20`, `801D2038`, `801CF7D0`, `801B24CC`, `801CEEB4`, `801BE79C`, `801B21F0`, `801BA128`, `BO6_RicEntitySubwpnThrownVibhuti` |
| `unkNN` inside `ext` | 3 | `801CE04C`, `801CF968`, `801C4C4C` |
| raw byte-pointer casts | 2 | `801C0898`, `801D136C` |
| unnamed constant | 1 | `EntitySlogra` (`0x20` should be `ENTITY_MASK_G`) |

**The 13 `ext.ILLEGAL` rejects are stale.** Task #82 removed `ILLEGAL` from
the SYSTEM rule, the entity layout and the per-offset hint, and made the
offset table pointer-type aware. Every one of these was rejected by a gate
whose cause has since been fixed upstream of the model. They are the exact
analogue of `deferred_triage`'s `stale-tier` class: deferred for a reason that
no longer holds.

Requeue all 13 as `todo`. Zero analysis, zero model calls to decide.

### 2b. `symbol` with a machine-resolved mapping (25)

`escalation_triage` already prints the resolution. Three sub-patterns, and
some records appear in two:

**A1 — missing declaration, symbol exists and is reachable (12 records).**
The candidate code is already written and fails only because an `extern` is
absent. Mechanical, no model call:

| symbol | source | records |
|---|---|---|
| `g_EInitCommon` | `src/st/e_fire_warg.h:11` (shared) | `8019F9C0`, `EntityBreakableWallDebris`, `EntityDemonSwitchWall` |
| `g_EInitInteractable` | `src/st/e_armor_lord.h:2` (shared) | `8019F5F0`, `EntitySmallGaibonProjectile` |
| `g_EInitGorgon` | `src/st/rno0/e_init.c:229` (same overlay) | `801D1BF0` |
| `g_EInitBreakable` | `src/st/e_breakable.h:9` (shared) | `EntityBreakableDebris` |
| `g_EInitShield` | `src/st/rdai/e_init.c:132` (same overlay) | `801C1DE8` |
| `g_EInitRdaiUnk1F` | `src/st/e_rdai_unk1f.h:3` (shared) | `801BF830` |
| `D_us_80180600` | `src/st/rchi/e_init.c:94` (same overlay) | `EntitySlograSpear` |
| `D_us_80180884` | `src/st/rdai/e_init.c:127` (same overlay) | `801C0528` |
| `g_Entities_224` | `src/st/e_imp.h:9` (shared) | `EntitySlograSpearProjectile` |

I checked every source: all 12 are either a **shared** `src/st/*.h` header or
the **same overlay** as the failing record. None is a cross-overlay borrow.
The triage tool already refuses cross-overlay for raw `D_us_` addresses (it
correctly flagged `D_us_8018206C` and `D_us_80180B3C` as "NOT the same
object"), and that guard must be extended to named symbols before this is
automated, because `g_EInitGaibon` above is exactly the case it would get
wrong.

**A2 — flat name to dotted member (4 records).** `PLAYER_posX_i_hi` to
`PLAYER.posX.i.hi`, `RIC_zPriority` to `RIC.zPriority`. Records: `8019F148`,
`801B1C34`, `801BFE6C`, `BO6_RicEntitySubwpnCrashCrossParticles`. The tool
marks these UNVERIFIED, correctly: it is inferring structure from a name. The
build is the verifier, so this is automatable as write-build-revert.

**A3 — `unkNN` offset to real member (9 records).** Splits again:

- Offset resolves to a real `Entity` field: `unk6C`->`opacity`,
  `unk28`->`pfnUpdate`, `unk8`->`velocityX`, `unk4`->`posY`. Mechanical rename.
- Offset falls INSIDE `ext` (0x7C): `801B8D8C` (0x84/0x88/0x98), `801BFE6C`
  (0x80), `801C0240` (0x9C), `801C17E8` (0x90/0x94), `801C21E4` (0x9A). These
  need the per-entity `ext` variant, which is the same problem as 2a. Not
  mechanical; they need the entity type, which #82's pointer-aware offset
  table now supplies to the model.

### 2c. `symbol` unresolvable (18) and `real` (13)

Genuinely hard. Notable within them:

- `us:ST/RNO0:func_us_8019FD4C_from_rcen` has **`<tool_call>` XML in the
  source**: `earch_text<arg_key>pattern</arg_key><arg_value>func_us_8019FD4C`.
  Raw model tool-call markup was written into a `.c` file. That is a harness
  defect, not a decompilation failure, and it means the output path has no
  sanity check on what it writes.
- `us:BOSS/BO0:func_us_801AD26C`: `ninja: build stopped: interrupted by user`.
  A **false escalation** from an interrupted build. Requeue.
- `us:ST/RNO0:func_us_801CF24C`: `undefined reference to 'sw'`. The model
  emitted a MIPS instruction as a C call.
- `us:BOSS/BO6:BO6_RicStepSlide`: `stray '\' in program` at richter.c:232.
  Escaping damage in the emitted C.

The last three are all **output-integrity** failures rather than reasoning
failures, and they share a fix: validate the candidate before writing it.

### 2d. `harness` (2)

`func_801CD78C_801C9A60` and `EntityClockHands`: "INCLUDE_ASM stub not found".
Bookkeeping; the triage tool already says fix the harness then requeue.

---

## 3. Deferred: 43

| class | n |
|---|---|
| PERMUTER_EXHAUSTED | 30 |
| TIER_HANDOFF_TOO_LARGE | 11 |
| no note | 1 (`EntityBreakable`) |
| specific human note | 1 (`801CFE6C`) |

Of the 30 exhausted:

- **1 is a finished match** (`EntityGaibonLeg`, section 1).
- **1 is a new seed bug**: `us:ST/RDAI:func_us_801C5AA0` reports
  `UNDECLARED SYMBOL: the seed calls GetSideToPlayer without declaring it`.
  `GetSideToPlayer` has no prototype anywhere in `src/`. This is the same
  class fixed in commit `08f1465c7`, but that fix only declares **same-file
  `INCLUDE_ASM` stub siblings**, and this symbol is not one. The gap is real:
  undeclared symbols that are not same-file stubs still reach the permuter.
- **28 are genuine exhaustions.**

### The 11 too-large records are NOT stale

`deferred_triage` measures the real `.s` size rather than trusting the note
(the notes all say "12000 chars", which is the prompt builder's truncation
point, not a measurement). Real sizes: 20165, 20575, 20682, 21175, 23161,
23208, 24940, 26134, 33232, 43582, 67724, 68865. Every one exceeds the hosted
20000 ceiling. There is no requeue available; this class needs a different
mechanism, not a retry.

### Result of the seed-declaration fix (16 records re-searched)

The 16 records requeued in `57012e43e` have now been re-searched with fixed
seeds. Best score before (accumulated) versus after (single fresh search):

| function | before | after | |
|---|---|---|---|
| `801B1F5C` | 2050 | 1420 | -31% |
| `801B171C` | 1950 | 1480 | -24% |
| `801B2044` | 2070 | 1620 | -22% |
| `801B1950` | 2080 | 1655 | -20% |
| `801B1B30` | 420 | 330 | -21% |
| `801B5D6C` | 360 | 225 | -38% |
| `801B1DDC` | 205 | 105 | -49% |
| `801B163C` | 1770 | 1550 | -12% |
| `801B15BC` | 515 | 445 | -14% |
| `801B1CE0` | 435 | 415 | -5% |
| `801B1EDC` | 100 | 100 | 0 |
| `801B6520` | 410 | 430 | +5% |
| `801B5E08` | 30 | 40 | +33% |
| `801B8B64` | 2215 | 2660 | +20% |
| `801BA724` | 275 | 765 | +178% |
| `801B5E8C` | 3640 | 3875 | +6% |

10 improved, 1 unchanged, 5 regressed. **None reached zero**, so the
declaration fix improved the search without cracking anything.

The 5 regressions are very likely an artefact, not a loss: the "before"
figures accumulated across multiple prior sessions with promoted bases, while
"after" is one fresh search from the seed. The old bases still exist, because
the re-import **renamed** the stale work dirs rather than deleting them
(`nonmatchings/<fn>.stale-20260810-*`). Recovering them is a
`permuter_promote.py` run against the stale dir, not new work.

---

## 4. Programmatically addressable, ranked

| # | class | n | model calls | effort |
|---|---|---|---|---|
| 1 | `EntityGaibonLeg`: add one extern, build | 1 | 0 | minutes |
| 2 | Stale `ext.ILLEGAL` rejects: requeue as todo | 13 | 0 to decide | minutes |
| 3 | A1 missing declaration: insert extern, build, revert on red | 12 | 0 | hours |
| 4 | False escalations (`801AD26C` interrupted build) | 1+ | 0 | minutes |
| 5 | A2 flat-name rewrite, build-verified | 4 | 0 | hours |
| 6 | A3 `unkNN` to real field (non-ext half) | ~4 | 0 | hours |

**26 records, zero model calls to decide, and one of them is already a
match.** That is 22% of the escalated+deferred backlog.

Not addressable without reasoning: A3's ext half (~5), unresolvable symbols
(18), `real` (13), genuine exhaustions (28), too-large (11).

---

## 5. Tooling gaps this audit exposed

1. **`escalation_triage.py` has no `quality` class.** 19 of 77 records, every
   one a quality reject, land in "unknown: read it". It should classify them
   and, like `deferred_triage`, recognise a reject whose *cause* was later
   fixed (the 13 `ILLEGAL` ones) as stale and requeueable.
2. **`escalation_triage.py` cannot requeue.** `deferred_triage` gained
   `--requeue --apply` in `57012e43e`; the escalated side still only prints
   advice. Printing advice nobody executes is how the `scheduler.py set`
   invocation stayed wrong for months.
3. **Cross-overlay guard is only applied to raw `D_us_` names.** Named symbols
   like `g_EInitGaibon` can resolve to another overlay's header and would be
   wrong to copy. Extend the guard before automating A1.
4. **The seed writer only declares same-file `INCLUDE_ASM` siblings.**
   `func_us_801C5AA0` shows undeclared non-stub symbols still reaching the
   permuter and burning part of the search.
5. **Nothing validates candidate text before writing it.** A `.c` file in the
   tree contains `<tool_call>` XML. Stray backslashes and a bare `sw` call
   reached builds too. A cheap pre-write check (balanced braces, no markup, no
   bare MIPS mnemonics) would convert three "real" escalations into retries.

---

## 6. Orchestration plan for the remainder

Ordered so that everything cheap and certain happens before anything
expensive or uncertain, and so that each stage's output improves the next.

**Stage 0 — harvest the free work (no model calls).**
Land `EntityGaibonLeg`. Requeue the 13 stale `ILLEGAL` rejects and the
interrupted-build false escalation. Run `permuter_promote.py` against the 5
`.stale-*` dirs to recover the better bases. Verify 81/81 after each landing,
not at the end.

**Stage 1 — close the tooling gaps (items 1 to 5).**
These are prerequisites, not side quests: stage 2 automates A1, and doing that
without gap 3 fixed will copy a cross-overlay symbol and produce a wrong
build. Item 5 pays for itself immediately by preventing the class rather than
triaging it.

**Stage 2 — automated declaration repair (A1, 12 records).**
Write-build-revert per record, under `BuildLock`, journalled. Model calls
zero. Expect a high hit rate: these already compiled apart from one missing
name. Same harness as `transplant.py --auto`, which already does
write-build-revert unsupervised.

**Stage 3 — mechanical rewrites (A2 and A3-non-ext, ~8 records).**
Same machinery, lower confidence, so build-verified individually and reverted
on red. The A2 mappings are explicitly UNVERIFIED inferences from a name; the
build is the only thing that makes them safe.

**Stage 4 — re-attempt the requeued quality rejects (13).**
These go back through the normal fleet with the #82 prompt. This is the first
stage that spends model calls, and it is deliberately after the free work so
the fleet is not competing with mechanical repairs for the build lock.

**Stage 5 — the too-large 11.**
Needs a mechanism, not a retry. Options, in order of expected value: a
backend with a larger context window; splitting the asm at basic-block
boundaries and decompiling piecewise; or treating them as
human/strong-model-only and removing them from fleet scope so they stop
appearing as actionable. Pick one deliberately rather than letting them cycle.

**Stage 6 — genuine exhaustions (28) and unresolvable symbols (18).**
These are the real remaining decompilation work. The permuter cannot help:
it mutates expressions, and an exhausted record means the *structure* is
wrong. They need re-derivation from the asm by a strong model or a human.
Sequence them by `best_score`, lowest first, since a low score means the
structure is nearly right and a small edit may finish it.

**Sequencing constraint that applies throughout:** builds are exclusive
(`BuildLock`), so stages 2, 3 and 4 must not run concurrently with each other
or with a fleet. Stage 0's promotions and stage 1's tooling work are the only
things safe to overlap with a running fleet, and only because they do not
build.
