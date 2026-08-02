# P6 item 2: Tier 2/3 consumers for `escalated`

ROADMAP P6 leaves one item open: "`escalated` still has no automated rung above
Tier 0. Records accumulate until an orchestrator picks them up by hand."
ORCHESTRATOR 7.1 says the same thing and has said it since 2026-07-19.

This is the design for closing it. The central claim, and the reason the obvious
design is wrong:

**`escalated` means "never compiled". The permuter mutates an already-compiling
function. So almost nothing in `escalated` is permuter material, and a tier
ladder that assumes otherwise will spend tokens and CPU on records whose failure
it cannot address.**

That distinction only became true on 2026-08-02, when `build_failed_to_compile()`
stopped collapsing "never compiled" into "compiled, bytes differ". Anything
written before that date about what `escalated` contains describes the old,
mixed pool. ROADMAP P2 ("Run the permuter against the 34 escalated", "escalated
records are by definition the ones that got close") is one of those things. See
section 5.

## What I verified and what I did not

Verified by reading the code and the tree:

- every note string that can reach `escalated`, and the exact code path for each;
- that the thirteen functions solved by the 2026-08-02 shim work
  (`Update`, `UpdateStageEntities`, `HitDetection`, `EntityDamageDisplay`,
  `EntitySoulStealOrb`, `EntityMedusaHeadSpawner`, `EntityMedusaHeadBlue`,
  `EntityRedDoor`, `Random`, `EntityEnemyBlood`, `EntityMedusaHeadYellow`,
  `EntityIsNearPlayer`, `func_us_801B9A8C`) now have **zero** `INCLUDE_ASM`
  stubs anywhere in us-buildable `src/`. Any queue record still naming one of
  them lands on `find_source() -> None`, which reports exactly
  `INCLUDE_ASM stub not found`. The stale class is real and its cause is proven;
- that `iterations` is always 0, because nothing anywhere passes
  `--add-iters` to `scheduler.py report`. There is currently no retry counter;
- that `cmd_reclaim` returns any stale `claimed` record to **`todo`**,
  unconditionally, with no memory of what it was claimed from.

Not verified, because `queue_list` is a connector tool this environment cannot
call: the exact per-note counts. The proportions below are the orchestrator's
reading of 22 escalated records, and they are provisional. Section 4 includes an
acceptance criterion whose only purpose is to make those proportions measurable
instead of remembered.

---

## 1. What actually lands in `escalated`

Five distinct producers, only three of which are about the function at all.

| Kind | Note shape | Share of the 22 | Produced by |
|---|---|---|---|
| A. never compiled | `BUILD FAILED: <diagnostic>` | majority, roughly 16-17 | end of `process_one`, `produced_code and not compiled_once` |
| B. evidence lost | `attempt 4 failed: RuntimeError`, `attempt 4 timed out` | a handful, roughly 3-4 | same branch, note clobbered |
| C. stale record | `INCLUDE_ASM stub not found` | 2 | `find_source()` returned None |
| D. harness fault | `worker error: <Exc>: <msg>` | 0 today, 3 in the 2026-07-20 snapshot | the outer `except` in `process_one` |
| E. merge rollback | reason from `merge_verified.py` | not seen | ORCHESTRATOR 4.8 |

### A. Never compiled

The model produced C, it was applied, and the build emitted a compiler
diagnostic, a ninja `FAILED:` block, or a link error. `build_failed_to_compile()`
is deliberately conservative, so this is also where **unexplained** non-zero
exits land, and that matters: `wsl()` converts a build timeout into
`(124, "timeout after 900s")`, which has no diagnostic and no
`checksum check failed`, so a 900-second build timeout is currently recorded as
`BUILD FAILED` and escalated as if the model had written broken C.

So kind A is not one thing. It needs splitting before any consumer can be built:

- **A1 link error** (`undefined reference to X`). The linker names the missing
  symbol *and* the file that wants it. ROADMAP's own shim notes call this "the
  best failure to get here" for exactly that reason: `g_ItemIconSlots` and
  `g_EInitDamageNum` were both found in one build each.
- **A2 compile diagnostic** (`structure has no member named 'unk32'`,
  `parse error`, implicit declaration). A type or declaration failure. The
  worker already fed this back for up to four attempts.
- **A3 build infrastructure** (`timeout after 900s`, `wsl invocation failed`).
  Says nothing about the function.

Nothing on the record distinguishes these today. Notes are truncated at 250
characters (`best[:250]`), the full build log is deleted by the build command
itself (`rm -f $blog`), and the model's non-compiling C survives only in
`automation/logs/gen/`, which is gitignored and periodically archived. That is
the same trap that left all four `near` records with zero permuter seeds on
2026-08-02.

### B. Evidence lost, not a separate failure

This one is worth reading the code for. `best` is overwritten by every attempt,
including a failed one:

```python
best = f"attempt {attempt} failed: {type(e).__name__}"   # generation error
best = f"attempt {attempt} timed out"                    # generation timeout
```

and the routing is:

```python
if compiled_once:              -> near
elif not produced_code:        -> todo (requeue; not the model's fault)
else:                          -> escalated, --notes best[:250]
```

A record reaching `escalated` with a generation-error note therefore had
`produced_code == True`: an **earlier** attempt did produce C, and that C failed
to build. Then attempt 4 died in generation and its message overwrote the build
verdict.

These are kind A records wearing the wrong label. They do not need a generation
consumer, they need the worker to stop discarding the build verdict.

Uncertainty worth naming: I inferred this from the control flow, not from the
records. If a note of this shape ever appears on a record where no attempt
reached the build, the inference is wrong and the requeue branch has a hole.

### C. Stale record

`find_source()` walks `src/`, skips `_psp`, `/psp/`, and `saturn` paths, and
indexes `INCLUDE_ASM("...", NAME)`. It returns None only when **no** us-buildable
`.c` mentions that function. That happens when the function stopped being a stub,
which is what "solved" looks like: either it was written in C and matched, or the
file now `#include`s a shared implementation from `src/st/<stem>.h` and the stub
was deleted.

Verified above for all thirteen functions the 2026-08-02 shim work resolved. The
record is not a failure. It is a queue entry that the tree moved past.

### D. Harness fault

The outer `except` escalates on any exception, including
`subprocess.TimeoutExpired` from a build and a `RuntimeError` from `apply_code`
("INCLUDE_ASM stub for X not found in Y", which is kind C arriving through a
different door: the file was found but the stub was edited away in the interval).
The three escalations in the 2026-07-20 legacy snapshot are all of this shape
(`worker error: TimeoutError: timed out`).

This contradicts the deliberate policy forty lines below it, which requeues a
record when the failure was the model or the infrastructure rather than the
function. Escalating a harness fault is the 2026-07-21 escalation spike in
miniature: a broken free model burned about 40 functions, escalating each one
after four generations nobody evaluated.

### What each kind actually needs

| Kind | Needs |
|---|---|
| A1 link | the missing symbol resolved against the tree, or a statement that it is an unnamed address |
| A2 compile | a stronger model, but only if `decl_coverage` says the declarations exist |
| A3 build infra | a retry. Nothing else. |
| B | the worker to keep the build verdict |
| C | the record retired, not retried |
| D | a retry, and to stop being escalated in the first place |

---

## 2. The consumer for each kind

Ordered by value, and the order is also the build order: each one depends on
the evidence the previous one produces.

### C1. Make the failure legible (prerequisite, no model involved)

Nothing above Tier 0 can route a record that carries 250 truncated characters
and no artifact. Three changes in `worker_direct.py`:

1. **Keep the build verdict.** Track `best_build` separately from `best`, and
   prefer it when reporting. A late generation error must never overwrite the
   reason the function actually failed. This alone converts kind B into kind A.
2. **Prefix the note with a greppable class token**: `FAIL=LINK`, `FAIL=COMPILE`,
   `FAIL=INFRA`, `FAIL=STALE`. `queue_list` prints notes, so this is
   immediately filterable with no schema change. Precedent:
   `SHIM_INSTEAD_OF_GENERATE` and `TIER_HANDOFF_TOO_LARGE` already work this way.
   Do not add a queue field or a status for this (section 5).
3. **`save_failed_candidate()`**, mirroring `save_candidate()` into
   `automation/candidates/failed/<slug>.c`, with the diagnostic in the header
   comment. Same reasoning as the permuter seed, same trap avoided: the copy in
   `automation/logs/gen/` is gitignored and archived, so today the C that failed
   to compile is gone by the time anyone looks.

The classification itself belongs next to `build_failed_to_compile()` and should
reuse its constants (`_COMPILE_FAIL_MARKS`, `_DIAG_RX`), so the two cannot drift.
`FAIL=INFRA` must cover `rc == 124` and the `wsl invocation failed` string.

### C2. Self-heal the stale class (fully automated, free)

Detection is read-only and lives in `codebase_index.py` as
`stub_state(function, overlay)` returning one of:

- `STUB_PRESENT` (an `INCLUDE_ASM` exists in a us-buildable `.c`),
- `IMPLEMENTED_IN_C` (a definition of the symbol exists in the overlay's source),
- `COVERED_BY_SHIM` (the overlay's `.c` includes `src/st/<stem>.h` and that
  header defines the symbol),
- `NO_US_TARGET` (no stub, no definition, and no `asm/us/**/nonmatchings/<fn>.s`).

Two callers, one implementation, because the `review_gate` precedent applies:
reusing `review_checks.py` rather than reimplementing it is what stops the two
callers disagreeing.

- **The worker**, at the `find_source() is None` branch, so the cause is fixed
  and not just the records. Invariant 6 says exactly this: the `near`/`escalated`
  misrouting was hand-patched at the record level once and came straight back.
- **A scheduler subcommand**, `scheduler.py triage --stale`, to clean the
  records that already exist, since nothing ever revisits an `escalated` record.

Disposition, and this is the part to get right:

| state | report | notes |
|---|---|---|
| `IMPLEMENTED_IN_C`, `COVERED_BY_SHIM` | `deferred` | `STALE_STUB_RESOLVED: <mechanism>, <evidence>` |
| `NO_US_TARGET` | leave alone, list for a human | prune candidate |
| `STUB_PRESENT` | leave alone | detector is wrong, or the record is fine |

`deferred`, not `matched`. The tree is at 81/81 and the function is genuinely
matched, so `matched` would be factually defensible and is still the wrong
answer: this harness did not produce that match, `provenance_check.py` exists to
catch precisely that kind of credit, and it would inflate the one number the
project reports honestly. `deferred` with a marker is also inert by construction,
because `next --include-deferred` only ever reclaims `TIER_HANDOFF_TOO_LARGE`.

Writer discipline, from the `annotate` docstring: this must run inside the same
process family as every other writer and print the resolved `SOTN_QUEUE` path.
`SOTN_QUEUE` resolves per `HOME`, and a helper run from the Cowork sandbox saw
33 matched where the live queue had 134. A sandbox-side writer would fork the
harness state and print success. Dry run by default with `--apply`, like `prune`
and `annotate`.

### C3. A Tier 2 consumer for `FAIL=LINK` only

This is the one class with an automated answer that is not "spend more tokens".
The linker hands over the missing symbol and the requesting file. The consumer:

1. look the symbol up in `codebase_index.py`;
2. if it exists in the tree under another name or resolves to a known address,
   that is a mechanical edit: Tier 2 (haiku-class, ORCHESTRATOR 4.3), capped, one
   pass, report with `--tier 2`;
3. if it resolves to an unnamed `D_` address, stop. That is structural
   (MATCHING-LESSONS 1a) and no model fixes it. Annotate the record with the
   symbol and leave it escalated with `--tier 2` so it is never re-attempted at
   the same rung.

**Build this only after C1 has run for one fleet cycle.** I could not measure how
many of the 22 are link errors, because the notes are truncated and the logs are
gone. Building a consumer for a class whose size is unknown is how the "8 free
shims" retraction happened.

### FAIL=COMPILE: a stronger model, gated, not a loop

The honest consumer is a bigger model, and it is the only class where spending
tokens is defensible. Two conditions, both cheap to check, both mandatory:

- `automation/priority.us.json` must not mark the function `blocked`. A blocked
  function's failure is unnamed data, and a larger context window does not name
  data. This is the same reasoning `cmd_next` already applies when ordering.
- one pass, then `--tier 2` or `--tier 3` on the record. Never a loop.

Until C1 lands there is no way to select this class, so it stays an explicit
orchestrator dispatch, exactly as ORCHESTRATOR 7.1 instructs.

### FAIL=INFRA and kind D: requeue, never escalate

Fully automatable and free. A build timeout or a WSL fault carries no information
about the function, so `escalated` is the wrong shelf. Requeue to `todo`, with a
bound so a permanently broken environment cannot spin the queue.

The bound needs a counter and there is not one: `iterations` is incremented by
`--add-iters`, which nothing passes, so it is 0 on every record. Either start
passing it from the worker or carry the count in the marker
(`FAIL=INFRA requeue=2`). Passing `--add-iters` is better, since the field
already exists and `report` already handles it.

### C4. Claim safety, required by any consumer above Tier 0

`scheduler.py next` only ever claims `todo` (plus the size-handoff deferrals), so
a Tier 2/3 consumer cannot claim at all today. It can only `queue_list` and
`queue_report`, which means two orchestrator sessions can work the same record.

Two changes, and the second is a live bug regardless of this design:

1. `next --pool escalated --max-tier 1`, so a record can be claimed once per
   rung and a record already at tier 2 is never handed back to tier 2.
2. Record `claimed_from` at claim time and have `cmd_reclaim` restore **it**
   rather than hard-coding `todo`. Today, a Tier 2 consumer that dies leaves a
   `claimed` record that `reclaim --older-than-min 60` silently converts into
   `todo`, where a Tier 0 worker regenerates it from scratch. That is the exact
   token waste the tiering exists to prevent, and `release_claim_if_held()` has
   the same hard-coded `todo`.

---

## 3. Stale records: detection and self-heal, concretely

Restating C2 as the implementable unit, since this is the part ROADMAP asked for
specifically.

**Detect** (`codebase_index.stub_state`, read-only, never raises, degrades to
"no opinion" when the index is missing, per `shim_gate`'s precedent):

1. Is there an `INCLUDE_ASM("...", <fn>)` in any `.c` under `src/` that is not
   `_psp`, `/psp/`, or `saturn`? If yes, `STUB_PRESENT`. Reuse `RX_INC` and the
   same path exclusions as `find_source()`, or the two will disagree about
   `UpdateClockHands` again, the function that resolved to
   `src/st/rno0_psp/unk_1028.c` and was handed to a model with "asm: 0 chars".
2. Does the overlay's source define the symbol in C? `IMPLEMENTED_IN_C`.
3. Does the overlay's `.c` include a `src/st/<stem>.h` that defines it?
   `COVERED_BY_SHIM`. Name the header in the reason string.
4. Otherwise, is there an `asm/us/**/nonmatchings/<fn>.s`? If not,
   `NO_US_TARGET`: the record was probably never a us function. Do not guess
   further, and do not delete it.

**Heal**, in two places, sharing one implementation:

- `worker_direct.process_one`, replacing the current
  `escalated / "INCLUDE_ASM stub not found"` report with
  `deferred / "STALE_STUB_RESOLVED: <state>, <evidence>"` when the state is
  `IMPLEMENTED_IN_C` or `COVERED_BY_SHIM`. Keep `escalated` for `NO_US_TARGET`,
  because that is a seeding defect and should stay visible.
- `scheduler.py triage --stale [--apply]`, dry run by default, printing the
  resolved queue path, scanning `escalated` records only, and reporting through
  the same transaction machinery as every other subcommand. Idempotent: a record
  that already carries the marker is skipped and counted, and "nothing matched"
  must never print the same message as "nothing left to do", which is the bug
  `annotate` fixed by shouting.

The `apply_code` path (`RuntimeError: INCLUDE_ASM stub for X not found in Y`)
should call the same detector before the outer handler escalates, so a record
that goes stale between claim and apply gets the same disposition.

---

## 4. Acceptance criteria

House style: one self-test, allowlisted in `ANALYSIS_SCRIPTS` (which needs a
connector restart before `run_analysis` will accept it), each check pinning a
failure that actually happened. Proposed file: `automation/test_escalation_triage.py`.

**Classifier (C1)**

- `classify("timeout after 900s", rc=124)` is `INFRA`, not `COMPILE`.
  Pins: `wsl()` returns `(124, "timeout after 900s")`, and
  `build_failed_to_compile` correctly calls that a build failure, so a 900s
  build timeout currently escalates as if the model wrote broken C.
- `classify("undefined reference to `polarPlacePartsList'")` is `LINK`.
  Pins: link errors are the one class with a mechanical consumer and are
  currently indistinguishable from parse errors on the record.
- `classify("src/boss/bo0/2D26C.c:133: structure has no member named `unk32'")`
  is `COMPILE`. Pins: GCC 2.7 emits no `error:` keyword, the bug
  `test_build_classifier.py` already covers from the other side.
- A note of the form `attempt N failed: <Exc>` classifies as
  `EVIDENCE_LOST`, never `INFRA`. Pins: reaching `escalated` with that note
  proves an earlier attempt built and failed, so treating it as an
  infrastructure fault would requeue a genuine compile failure forever.
- Source contract, grep style, as in `test_build_classifier.py`: the worker
  reports a build verdict when one exists, that is,
  `best_build` (or equivalent) is read at the escalation report and a
  generation-error assignment cannot be the last writer.
- Source contract: `save_failed_candidate` writes under
  `automation/candidates/`, and the string `automation/logs` does not appear in
  its path construction. Pins: all four `near` records had zero surviving seeds
  because `logs/` is gitignored and archived.

**Stale detection (C2/C3)**

- For each of `Update`, `UpdateStageEntities`, `HitDetection`,
  `EntityDamageDisplay`, `EntitySoulStealOrb`, `EntityMedusaHeadSpawner`,
  `EntityMedusaHeadBlue`, `EntityRedDoor`, `Random`, `EntityEnemyBlood`,
  `EntityMedusaHeadYellow`, `EntityIsNearPlayer`, `func_us_801B9A8C`:
  `stub_state` is not `STUB_PRESENT`, and the reason names either the shim
  header or the defining `.c`. Pins: two records escalated as "INCLUDE_ASM stub
  not found" after their function was solved on 2026-08-02.
- For a function with a live stub (read one out of `src/st/rno0/` at test time
  rather than hard-coding a name that may get matched tomorrow):
  `stub_state` is `STUB_PRESENT`. Pins the opposite failure, a detector that
  retires live work.
- A function whose only stub is in a `_psp` or `_saturn` file is `NO_US_TARGET`,
  not `IMPLEMENTED_IN_C`. Pins: `UpdateClockHands` resolving to
  `src/st/rno0_psp/unk_1028.c` with an empty assembly section.
- `stub_state` with `WIN_REPO` pointed at a nonexistent path returns a
  no-opinion answer and does not raise. Pins: the same degradation
  `test_shim_gate.py` asserts for `shim_gate`.
- Source contract: the triage path never reports `matched`. Pins: a stale
  record is not this harness's match and `provenance_check.py` exists to say so.
- Idempotence: running the planner twice plans zero changes the second time,
  and the "nothing matched" and "nothing to do" messages are distinct strings.
  Pins: `annotate`'s first version printed "already annotated" after matching
  zero records, which is how a total no-op passes for success.
- Dry run by default: `--apply` is required to write. Pins: `prune`, the only
  other destructive-ish queue operation, and for the same reason.
- Scope: the planner considers only `escalated` records. A `todo`, `near`,
  `matched`, or `deferred` record is never in the plan, whatever its notes say.

**Claim safety (C4)**

- A record claimed from `escalated` and then reclaimed by
  `reclaim --older-than-min` returns to `escalated`, not `todo`. Pins: today's
  `cmd_reclaim` hard-codes `todo`, so a dead Tier 2 consumer feeds its record
  back to Tier 0.
- `next --pool escalated --max-tier 1` never returns a record with
  `tier_reached >= 2`. Pins: an unbounded ladder re-spending the same tier.
- `next` with no `--pool` still returns only `todo` and size-handoff deferrals.
  Pins: the Tier 0 fleet must not start pulling escalated work by accident.

**Measurement, which is itself an acceptance criterion**

- After one fleet cycle with C1 live, `queue_list --status escalated` shows a
  `FAIL=` token on every escalated record written since. The proportions in
  section 1 are then replaced with measured ones, and section 2's "build C3
  only after measuring" gate is satisfied or refuted.

---

## 5. What not to build

- **A permuter consumer for `escalated`.** The permuter searches codegen space
  around a function that already compiles. An escalated record never compiled.
  The permuter's population is `near` plus whatever `automation/candidates/`
  holds, which is one file today.
- **Therefore, ROADMAP P2 as written.** "Run the permuter against the 34
  escalated" and "escalated records are by definition the ones that got close"
  were true when `escalated` and `near` were the same pool, that is, before the
  `build_failed_to_compile` fix. P2 should be re-scoped to `near` and to saved
  seeds. This is a docs fix, not a code fix, and it is not this document's to
  make, but leaving it unsaid would let the next reader build the wrong thing.
- **A new queue status.** `VALID_STATUS` is read by `report`, and `cmd_stats`
  and the connector both print a hard-coded list of six. A seventh status would
  be accepted by `report` and then be invisible in `queue_stats`, which is worse
  than no feature. Use `deferred` plus a greppable marker, as
  `SHIM_INSTEAD_OF_GENERATE` and `TIER_HANDOFF_TOO_LARGE` already do.
- **A same-tier retry of `escalated`.** The worker already spent
  `MAX_ATTEMPTS=4` with asm-differ feedback and quality-gate feedback on each
  one. A fifth attempt at the same rung is resampling, and on 2026-07-21 two
  unrelated models produced identical, semantically correct C that still missed.
- **A scheduled or looping escalation ladder.** Every rung must be one-shot,
  marked with `--tier`, and refuse records already at or above its own tier.
  Without that, a permanently unmatchable function costs a model call per cycle
  forever.
- **Auto-pruning stale records.** `queue_prune` deletes, and deliberately
  refuses anything that is not `todo`, so that matched, near and escalated work
  is never at risk from a mistyped pattern. Retiring a stale record to
  `deferred` keeps the history and the totals; deleting it loses the evidence
  that the function was solved elsewhere.
- **A sandbox-side queue writer.** `SOTN_QUEUE` resolves per `HOME`. A helper
  run in the Cowork sandbox writes a different file and reports success.
- **A Tier 2 consumer for `FAIL=COMPILE` that ignores `priority.us.json`.**
  A function blocked on unnamed data is not made solvable by a larger model,
  and that is where the quota goes if the gate is skipped.
- **Anything at all before C1.** Every consumer above Tier 0 needs to know why
  a record failed. Right now the record says at most 250 characters, sometimes
  about the wrong attempt, and the failing C is in a gitignored directory. Fix
  the evidence first, measure, then build one consumer for the largest class.
