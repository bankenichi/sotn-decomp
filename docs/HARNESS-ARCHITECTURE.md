# Harness architecture

How the automated matching-decompilation harness in `automation/` fits together,
what each piece is responsible for, and the constraints that shaped it.

Read this before changing anything under `automation/`. Most of the surprising
decisions here are scar tissue from a specific failure, and the failure is named
in each case so you can tell a deliberate choice from an accident.

---

## 1. The oracle

One thing decides whether work is correct: the 81 SHA-1 hashes in
`config/check.us.sha`. A function is matched when the overlay binary containing
it is byte-identical to the original. Not "looks right", not "compiles", not a
percentage from a diff tool.

`verify_build` is the only tool that answers this. **`make build` returning 0
does not mean the build matches** — see section 5.

Everything else in this document exists to feed that oracle more candidates per
hour, or to stop bad candidates reaching it.

---

## 2. Component map

```
              ~/sotn-work/queue.jsonl         <- single source of truth
                (NOT work/queue.jsonl; that path is legacy)
                          |                      (scheduler.py is its ONLY writer)
        +-----------------+------------------+
        |                                    |
   scheduler.py                        worker_direct.py  x N
   (claim / report / stats)            (generate -> gate -> apply -> build -> verify)
        |                                    |
        |                             automation/candidates/   <- permuter seeds
        |                             automation/logs/gen/     <- every attempt (disposable)
        |                                    |
   commands_client.py  <---- allowlist ----  sotn_cmd_mcp.py   <- the MCP connector
        |                                            |
   jobs.py (detached long commands)          Claude / Cowork
```

Supporting analysis, all read-only, all runnable via `run_analysis`:

| Script | Answers |
|---|---|
| `asm_twin_finder.py` | does this stub have a twin elsewhere in the tree? |
| `codebase_index.py` | symbol/struct index used by the worker's prompt and gates |
| `quality_audit.py` | ILLEGAL variants, invented symbols, magic numbers, duplicates |
| `review_checks.py` | the nine reviewer-perspective checks (see section 4) |
| `provenance_check.py` | is this match actually ours, and honestly described? |
| `decl_coverage.py` | which unmatched functions have resolvable declarations |
| `overlay_size_check.py` | map vs symbol addresses; catches TEXT size bugs |
| `opencode_size_bisect.py` | model/prompt-size diagnosis for the cli backend |

Self-tests: `test_twin_wiring.py`, `test_build_classifier.py`,
`test_review_gate.py`. Each is allowlisted and each pins a bug that actually
happened.

---

## 3. The worker loop

`automation/win/worker_direct.py`, one function per iteration:

1. **Claim** a `todo` record from the queue.
2. **Prepare** context: the `.s` file verbatim, an m2c first draft, resolved
   declarations, and a twin section if `twins.us.json` has one.
3. **Generate** C from the model.
4. **Gate** the candidate, before any build:
   - `quality_gate()` — invented externs, raw pointer casts, magic numbers.
   - `review_gate()` — the reviewer checks (section 4).
   A defect costs one attempt and becomes the retry feedback, which is the
   point: the next attempt is *better*, not merely different.
5. **Apply, build, verify** under `BuildLock`.
6. **Route** by failure kind (section 5) and **restore** the file.

### Prompts go on stdin, never argv

`opencode` is a Windows `.exe` invoked from WSL, so the command line is capped
at 32767 characters by `CreateProcess`. Past that the process never starts:
`rc=1`, `opencode.exe: Invalid argument`, in 0.0 seconds.

This looks *identical* to a model returning an empty body, and it cost four
separate investigations (quota, auth, agent resolution, stdout routing) before
anyone measured it. 59% of the remaining functions produce prompts over that
limit, so on argv most of the remaining work was unreachable by any model.

Do not move the prompt back onto argv. `automation/opencode_size_bisect.py`
reproduces the whole thing on demand.

### Model choice is not cosmetic

Free Zen models split cleanly into ones that answer and ones that return an
empty body. Use `deepseek-v4-flash-free`, `nemotron-3-ultra-free`,
`mimo-v2.5-free`. Do not use `big-pickle`, `north-mini-code-free`,
`ling-3.0-flash-free`, `laguna-s-2.1-free`. Evidence and the measurement method
are in `automation/opencode/ZEN-FREE-MODELS.md`.

---

## 4. The two gates

Both run **before** the build, so a defect costs one retry instead of a build
cycle or a review cycle.

`quality_gate(code, asm)` is defined in the worker and covers defects the model
produces despite the prompt forbidding them. Prompt rules are not enforcement.

`review_gate(ctx, fn, code)` reuses `review_checks.py` rather than
reimplementing it, so the two callers cannot drift. It builds the file as it
*would* look after `apply_code` (`virtual_apply`) and runs the checks on that,
because the checks need whole-file context.

Wired: `linkage`, `ext`, `static`, `signature`, `stub`.

Deliberately NOT wired, per ROADMAP P4 and `MATCHING-LESSONS.md` section 20:

- `angle`, `argn` — "same as X except Y" comments that understate a real
  difference, and descriptive parameter names replaced by `argN`. Both need a
  human reader; as automatic gates they would reject good code.
- `comment`, `block` — they compare against a *previous C version*. Before
  apply, the file still holds the `INCLUDE_ASM` stub, so there is nothing to
  have lost. They remain meaningful at review time.

The `linkage` check earns its place: adding `static` to a function whose callers
are `INCLUDE_ASM` stubs in a sibling `.c` breaks the link, and a C-source grep
cannot see those callers. It predicts a link error minutes before the build
would surface it.

Findings about *other* functions in the file are dropped. The file can carry
pre-existing findings in code this worker did not write, and failing on those
would make the record permanently unmatchable.

---

## 4a. The shim gate (before the model, not after)

`shim_gate()` asks `codebase_index.shim_viable()` whether the record's target
file should defer to a shared implementation in `src/st/<stem>.h`. If it should,
the record is deferred with marker `SHIM_INSTEAD_OF_GENERATE` and **no model
call is made**. Writing a private copy of code the tree already has is wrong
work: the quality audit flags it as a duplicate and a reviewer rejects it.

Measured over the 417 `INCLUDE_ASM` stubs in `src/st`:

| Group | Count | Behaviour |
|---|---|---|
| no shared implementation | 288 | generate, correct as-is |
| shared impl exists, blocked | 121 | **annotate only** |
| shimmable now, no blocker | 8 → **0** | **defer** |

**There are currently no free shims.** All 8 the gate first reported were false
positives. That is the finding, not a bug: the gate stays live and fires the
moment a stage gains the segment it is missing.

### shim_viable has a blind spot: it never asks if it is the same code

`shim_viable()` checks *placement* — segments, `.data`, `.bss`. It does not
compare implementations. Of the 8 it first reported, 7 were false positives:

| | own text | peer median | ratio | verdict |
|---|---|---|---|---|
| rchi/e_breakable | 0x674 | 0x134 | 5.36x | different code |
| rno0/e_lock_camera | 0x1bc | 0x4cc | 0.36x | different code |
| rno0/e_breakable | 0x170 | 0x134 | 1.19x | plausible |

`rchi/e_breakable.c` had a comment saying so all along: "stage-specific and
roughly twice the size of the shared candle implementation (0x270 versus 0x134
bytes)" — a rejection upstream had already investigated.

`shim_size_divergence()` compares a stage's `c` segment size against the median
of the stages that already shim that header, and blocks outside 0.75x–1.25x.
**Both directions matter**: rno0's lock camera is a third of its peers', which
is no more shimmable than rchi's being five times larger. Too-small is the case
a naive check misses.

`_psp` and `_saturn` paths are also out of scope: `shim_viable` reasons from
`config/splat.us.*`, and the us oracle cannot verify a change to another build
target, so any verdict about them is unfounded.

### And a second blind spot: headers that oblige the STAGE to supply data

`shim_viable`'s blocker 4 asks whether the *header* defines initialised
file-scope data. `src/st/e_breakable.h` defines none — and still reads
`g_eBreakableAnimations`, `g_eBreakableHitboxes`, `g_eBreakableExplosionTypes`,
`g_eBreakableanimSets` and `blend_modes`. Every stage that shims it declares
those `static` above the `#include`, so they are `.data` belonging to the stem
and the stage needs a `.data, <stem>` segment. rno0 has only a `c` segment.

`shim_needs_stage_data()` detects this from the **peers**, not from a guess: it
reads the `.c` of stages that already shim the header and checks whether they
must define static file-scope data. If they must, so must this stage.

Deferring the blocked 121 as well would follow ROADMAP P6 literally and stall
29% of the queue behind structural work that has no automated consumer. The
narrowing is deliberate and asserted in `test_shim_gate.py`, which fails both if
the gate becomes eager (the fleet would starve) and if it stops deferring
anything (duplicates return).

Deferred records are greppable by their marker and can be requeued as a batch
once the shim lands.

---

## 5. Failure taxonomy, and why it kept going wrong

Three outcomes, three different owners:

| Outcome | Status | Next step |
|---|---|---|
| never compiled | `escalated` | better model, or a human |
| compiled, bytes differ | `near` | the **permuter** — free, no tokens |
| bytes match | `matched` | verified by the oracle, committed |

**`make build` runs the `check` target itself**, so a clean compile whose bytes
differ still makes make exit non-zero. Treating `rc != 0` as "build failed"
collapsed the first two rows, and the consequences were invisible:

- records routed to `escalated` instead of `near`, starving the permuter of
  exactly the records it exists to solve;
- no permuter seed saved, since seeds are only written on the compiled path;
- retry feedback saying "build failed" when the build was fine.

Four `near` records had to be retriaged by hand on 2026-08-01 with notes reading
"misrouted... the tree BUILT and only the checksum differed". That fixed the
records and left the cause, so it recurred on 2026-08-02.

`build_failed_to_compile(rc, out)` now makes the distinction and is
**conservative**: any compiler diagnostic, ninja `FAILED:` block, link error, or
*unexplained* non-zero exit still counts as a real build failure. Only an
explicit `checksum check failed` with no diagnostic is reclassified, so broken C
can never be handed to the permuter. Pinned by `test_build_classifier.py`,
including the verbatim log tail that was misclassified.

### Permuter seeds

A candidate that compiles but misses is the most valuable artifact short of a
match, and it used to be discarded. `save_candidate()` writes it to
`automation/candidates/<record>.c` and the queue note names the file.

It must NOT live under `automation/logs/` — that directory is gitignored and
periodically archived, which is why all four `near` records had zero surviving
seeds when the permuter finally needed them.

Later compiling attempts overwrite earlier ones on purpose: retries carry
asm-differ feedback the first attempt never had.

---

## 6. Concurrency

`BuildLock` serialises everything that mutates the tree. This is not tidiness:

- Two concurrent builds share one build directory and produce artifacts
  matching nothing.
- Reporting a match must happen *inside* the lock, because `scheduler.py`
  re-verifies the **whole tree** before accepting `matched`. With the report
  outside the lock, another worker's edit made the scheduler see
  "80/81 OK, 1 MISMATCHED" for an overlay the function never touched, and two
  real matches were thrown away.

Consequences to respect:

- **Subagents must never build.**
- Connector builds (`make_build` via the MCP) do **not** take `BuildLock`.
  Anything that runs `make extract` or `make build` by hand requires the fleet
  to be stopped first. `make extract` regenerates `asm/` and the linker scripts,
  so running it under a live fleet is the worst case.

A worker killed mid-edit cannot restore its own file, so `journal_write()`
records the original contents *before* the write. The next worker start, or
`fleet_stop`, replays the journal.

---

## 7. The connector

`sotn_cmd_mcp.py` exposes tools; `commands_client.py` holds a hard allowlist.
There is no general shell.

**Two surfaces, and they can disagree.** `list_allowed` reports the
`REGISTRY` allowlist, but tools also exist as `@mcp.tool()` decorators. Checking
only the allowlist has produced wrong conclusions before; check the live tool
list when it matters.

Adding a script to `ANALYSIS_SCRIPTS` requires a connector restart before
`run_analysis` will accept it.

Argument filtering is deliberately narrow: no spaces, quotes, semicolons,
redirects — and **no commas**. Scripts meant to be driven through the connector
must accept list arguments some other way (`opencode_size_bisect.py` splits on
`+` and `-`, and takes `--top N` as two tokens).

### Long commands

The Cowork sandbox kills any call at 45 seconds and the MCP transport times out
well before a build finishes. Eight builds failed that way in one day *while the
build kept running*, leaving the tree mid-build with the caller unaware.

Use `job_start` / `job_status`. `job_status` blocks at most 30s by design,
because the caller polling it is itself capped at 45s.

Background jobs are impossible *inside* the sandbox: it runs under
`bwrap --die-with-parent --unshare-pid`, a fresh PID namespace per call. This
was tested, not assumed. That is why `jobs.py` runs on the WSL side.

---

## 8. Paths

Three views of the same repo, and mixing them up wastes a call:

| Context | Path |
|---|---|
| Windows / file tools | `C:\Users\kenic\Documents\SOTN-Decomp` |
| WSL / the fleet / connector | `/mnt/c/Users/kenic/Documents/SOTN-Decomp` |
| Cowork sandbox | `/sessions/<id>/mnt/SOTN-Decomp` |

The sandbox cannot reach WSL, cannot run `opencode`, and has no git credentials.
Git therefore runs through the connector, which is also why `git_push` takes no
arguments: this repo has two remotes and `upstream` is the project we forked
from, so a caller-chosen remote would be one typo from pushing at it. `origin`
is hard-coded and upstream's push URL is separately disabled.

---

## 9. Usage

```
# status
queue_stats()                      # todo / near / matched / escalated
fleet_status(tail=4)               # check the log tails, not just the count

# run the fleet (cli backend, known-good models only)
fleet_start(workers=4, backend="cli",
            opencode_model="opencode/deepseek-v4-flash-free,opencode/nemotron-3-ultra-free")
fleet_stop()                       # ALWAYS; a killed worker strands its claim

# analysis (read-only, safe while the fleet runs)
run_analysis(script="asm_twin_finder.py", args="--audit-matched")
run_analysis(script="opencode_size_bisect.py", args="--top 3 --big")

# self-tests
run_analysis(script="test_review_gate.py")
run_analysis(script="test_build_classifier.py")
run_analysis(script="test_twin_wiring.py")

# long commands
job_start("make_build", version="us"); job_status(job_id, wait_s=25)
verify_build(version="us")         # THE ORACLE
```

`fleet_stop(hold=True)` marks the stop as deliberate and makes `fleet_start`
refuse without `force=True`. Use it whenever a human asked for the stop; a
human may have stopped the fleet to reconfigure something.

---

## 10. Invariants

1. The tree is left clean and at 81/81 after every unit of work. On failure,
   revert and re-verify before doing anything else.
2. `scheduler.py` is the only writer of the queue, which lives at
   `~/sotn-work/queue.jsonl` (NOT `work/queue.jsonl`, which is the legacy path
   a sync daemon once emptied). Never hand-edit it. It is outside the repo, so
   the sandbox cannot read it; use `queue_stats` and `queue_list`.
3. `matched` requires machine proof — the verify verdict and the artifact hash.
4. Verify any untested script before running it. Bricking the repo costs far
   more than the check.
5. Never push to `upstream`. This fork ships no PRs.
6. Don't fix a symptom at the record level when the cause is in the code. The
   `near`/`escalated` misrouting was hand-patched once and came straight back.
