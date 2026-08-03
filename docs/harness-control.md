# Harness control: supervisor, commands, dashboard

Three pieces, added 2026-08-03. They exist because every long-running process
in this harness was previously driven by hand, and the hand made mistakes that
cost hours: single-threaded permuter runs, jobs reported stopped while still
running, scores read wrong off a log tail, and work dirs permuted for functions
that had already been matched.

---

## 1. Quick start

```bash
export PATH="$PWD/automation/bin:$PATH"    # once, or add to ~/.bashrc

run-permuter plan          # what would run, and why the rest would not
run-permuter start         # supervised, self-terminating
run-permuter status
run-permuter stop

runfleet-cli start 2       # OpenCode CLI workers
runfleet-llama start 2     # local llama workers
runfleet-cli stop          # stops ALL workers and reclaims their queue records

sotn-dash start            # http://127.0.0.1:8777
sotn-dash stop
```

`plan` and `status` never start or stop anything and are always safe to run.

All four commands are symlinks to `automation/bin/sotn-run`, which dispatches on
`$0`. Adding a command means adding a symlink and a `case` arm, not another copy
of the argument handling.

---

## 2. The permuter supervisor

`automation/permuter_supervisor.py`

### The cycle it automates

```
pick candidates from the queue
  -> drop phantoms (function already defined in src/ with no INCLUDE_ASM)
  -> rank by best known score, unscored last
  -> run N concurrently
       on improvement-then-stall : promote the seed, restart, count a cycle
       on stall with nothing to promote : retire, say "re-derive from the asm"
       on score 0 : promote, bank the output, free the slot
  -> exit when nothing is left
```

### Why each default is what it is

| Setting | Default | Reason |
|---|---|---|
| `--slots` | 3 | Four concurrent jobs at 4 threads saturated the machine while a build also wanted cores. `make_build` is exclusive and must not be starved. |
| `--threads` | 4 | decomp-permuter's `-j` **defaults to 1**. Every run before 2026-08-03 was single-threaded, including one that held a core for 170,002 iterations. |
| `--stall` | 2500 | Past the latest last-improvement observed in any run (6,810, in a run that had been improving steadily up to that point). |
| `--cycles` | 4 | `func_us_801C488C` needed two promotions to reach zero. Nothing has needed four. |

### What it deliberately does not do

It never applies a match to the tree and never builds. A permuter zero means
the function matches **compiled in isolation** against its own `target.o`, which
is necessary but not sufficient. `func_us_801BC3E0` scored 0 and then failed the
real build at 80/81 because a `volatile int pad` made the frame 0x20 where the
target was 0x18. Landing a match stays a human decision, and the build is the
only thing that settles it.

### Candidate selection

Draws from queue status `near` by default. Those records compiled and produced
wrong bytes, which is exactly the precondition the permuter needs. `todo`
records have no compiling C at all and are not permuter work.

Then every candidate is checked against the tree via
`permuter_stall.workdir_state`. When this was written, **four of nine work dirs
were phantoms**: functions already defined in `src/` with no `INCLUDE_ASM`
anywhere. One reported score 10 and looked like the most promising seed in the
set while being long since matched and shipped. A score alone cannot distinguish
"nearly matched" from "matched a while ago", which is why the check reads the
tree instead.

---

## 3. Supporting tools

| Tool | Does |
|---|---|
| `permuter_stall.py --all` | True minimum, when it was reached, verdict (MATCH / STALLED / UNPERTURBABLE / PHANTOM / searching) |
| `permuter_promote.py --dir X` | Promote best output to `base.c`, keeping `base.c.orig`; `--revert` undoes |
| `permuter_supervisor.py` | Drives both of the above in a loop |

`permuter_promote.py` exists because **permuter.py only ever reads `base.c`**
(`src/main.py:322`) and never its own `output-*` directories. Restarting a work
dir therefore discards everything the previous run found. This is the tool's
intended workflow, not a trick: `randomizer.py:2059` describes `perm_remove_ast`
as cleaning up "unnecessary changes from an improved base.c".

Measured effect, `func_us_801C488C`:

| Run | Start | Iterations | Result |
|---|---|---|---|
| Unpromoted, 1 thread | base | 170,002 | never below 220 |
| Promoted once, 4 threads | 220 | ~6,700 | reached 70 |
| Promoted twice, 6 threads | 70 | **31** | **matched** |

---

## 4. The dashboard

`automation/dashboard.py`, served by `sotn-dash start`.

Single HTML file, stdlib `http.server`, no npm and no build step.

### Panels

- **Header** live queue counts by status, straight from the scheduler queue
- **Permuter** one column per running job: best score, iteration count,
  rejection count, stalled/improving, and the last 20 log lines
- **Fleet** one column per worker log, last 20 lines, with the alive count

Polls `/api/status` every 3 seconds.

The progress bar shows how far a job is into its **stall window**, not progress
toward a match. There is no such number: the search is unbounded, and any bar
claiming otherwise would be inventing one.

### Endpoints

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/` | none | the page, token substituted in |
| GET | `/api/status` | none | `{queue, permuter[], supervisor, fleet[]}` |
| POST | `/api/action/<name>` | `X-Token` | `{ok, out}` |

Actions: `permuter_start`, `permuter_stop`, `permuter_plan`,
`fleet_cli_start`, `fleet_llama_start`, `fleet_stop`.

### Safeguards

This process can start and stop jobs, so it is deliberately hard to reach and
cannot be talked into running anything arbitrary.

1. **Binds `127.0.0.1` only.** Never `0.0.0.0`. Not reachable off the machine.
2. **Actions are a fixed dict of zero-argument callables.** No command string,
   no argv, no shell anywhere in the request path, so a crafted request has
   nothing to inject into. Adding an action means editing the file.
3. **Mutation requires POST plus the token.** A GET can never change state, so a
   browser prefetch or a pasted link cannot stop your fleet.
4. **Token is random per process** and invalidated by a restart.
5. **Stop paths are idempotent** and always pass `hold=True`, because a killed
   worker cannot release its own queue claim and those records would otherwise
   sit `claimed` forever, invisible to every later run.
6. **Log text is escaped** before it reaches the DOM.
7. **Buttons disable in flight** and destructive ones confirm, so a double click
   cannot start two fleets.

### Verified

`automation/dashboard.py --self-test` covers the safety invariants, log tail
cleaning, queue counting and page structure. A live end-to-end test additionally
confirmed: page serves with the token substituted, `/api/status` returns real
queue counts, unknown paths 404, and POST is refused three ways (no token,
wrong token, unknown action name).

---

## 5. Testing criteria

Any change to these files must keep all of the following true.

**Supervisor** (`permuter_supervisor.py --self-test`, 20 checks)

- `workdir_for("fn_c")` finds `fn_c-2`; `workdir_for("fn_")` matches nothing
- candidates exclude `todo` and `matched` records
- ranking is by best score with unscored dirs last
- a record with no work dir is reported with a reason, never silently dropped
- a missing, empty, or partly malformed queue does not raise

**Dashboard** (`dashboard.py --self-test`, 19 checks)

- `HOST == "127.0.0.1"`
- every `ACTIONS` value is callable and takes no arguments
- no `shell=True`, `os.system` or `eval` before `def self_test`
- POST checks `X-Token`; GET does not
- backspace padding and blank lines are stripped from tails
- queue counting flags malformed lines rather than dropping them

**Promotion** (`permuter_promote.py --self-test`, 16 checks)

- lowest-scoring output wins; an output dir without `source.c` is ignored
- `base.c.orig` is written once and still holds the hand-derived seed after a
  second, better promotion
- a second promotion at the same score is refused
- `--revert` restores and clears the score stamp
- `--dry-run` changes nothing

**Stall detection** (`permuter_stall.py --self-test`, 21 checks)

- parses the true minimum and the iteration it was reached at
- STALLED advises re-deriving and never advises waiting
- UNPERTURBABLE is distinct from STALLED
- phantom detection runs against the real `src/` tree, not fixtures, and
  suppresses the score verdict

---

## 6. Known gaps

- The supervisor cannot create a work dir. A `near` record whose seed has never
  been imported is listed as blocked with `permuter_import` named as the fix,
  rather than being imported automatically.
- `preserve_macros` in `config/permuter_settings.toml` only takes effect on
  **import**. Re-importing an existing work dir would reset its promoted seed,
  so it is not done automatically. Current seeds use none of the nine preserved
  macros, so nothing is lost today.
- The dashboard's fleet panel lists worker logs and a total alive count, but
  does not map an individual log to an individual PID.
- `--status-filter` accepts any queue status. Pointing it at `todo` will queue
  functions with no compiling C, which the permuter cannot use.
