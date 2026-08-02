# Harness code audit — 2026-08-02

Adversarial, read-only review of the generate/apply/build/verify/route harness.

Scope:

- `automation/win/worker_direct.py`
- `automation/scheduler.py`
- `automation/mcp/commands_client.py`
- `automation/mcp/sotn_cmd_mcp.py`
- `automation/mcp/jobs.py`

Nothing was built, modified or committed. Line numbers are as of this date.
Supporting files were read where a claim depended on them (`tools/m2ctx.py`,
`tools/sotn-assets/build.go`, `tools/sotn-assets/check.go`, `Makefile`,
`.gitignore`, `automation/asm_twin_finder.py`).

Findings are ordered by severity. Comments that contradict the code they
describe are called out inline and collected in the last section.

---

## Summary

| # | Severity | Area | One line |
|---|---|---|---|
| F1 | critical | state | A **matched** function is reverted to its stub by the journal replay |
| F2 | critical | concurrency | Journal replay clobbers other **live** workers' in-flight edits |
| F3 | critical | concurrency | Connector build/git actions ignore the BuildLock entirely |
| F4 | high | oracle | An empty or partly-corrupt `check.<v>.sha` makes the oracle pass vacuously |
| F5 | high | routing | A compiler **warning** turns a permuter candidate into `escalated` |
| F6 | high | routing | Any WSL/build-timeout failure is filed as `escalated`, score 0 |
| F7 | high | input | ASM truncation makes the size gate unreachable on `cli` and feeds partial asm |
| F8 | high | concurrency | `ctx.c` is one shared file written by every worker outside the lock |
| F9 | high | routing | A verified match is deleted and refiled `escalated` if the report is refused |
| F10 | high | concurrency | Stale-lock takeover is TOCTOU; two workers can hold the BuildLock |
| F11 | high | silent failure | `report --id <unknown>` is a no-op that exits 0 |
| F12 | high | state | No claim fencing: a late worker can overwrite a verified match |
| F13 | med-high | state | `sched()` drops the claim before the scheduler call succeeds |
| F14 | med-high | concurrency | Job exclusivity covers the wrong resource and fails open |
| F15 | medium | silent failure | A finished job can be reported `ok: False` (empty `.done` race) |
| F16 | medium | state | Job ids collide; a poller is silently retargeted |
| F17 | medium | resources | `run()` timeout orphans ninja; the tree keeps mutating |
| F18 | medium | resources | `opencode` stderr is never drained → deadlock, phantom timeouts, zombies |
| F19 | medium | silent failure | `shim_gate`'s blocker reason is computed and thrown away |
| F20 | medium | routing | Quality-gated records are escalated as though they failed to build |
| F21 | medium | routing | Unbounded requeue loop; `iterations` is never incremented by anyone |
| F22 | medium | routing | Deferred pool leaks: routing ignores `claimed_from` |
| F23 | medium | concurrency | `fleet_stop` deletes a lock and reclaims claims it does not own |
| F24 | medium | trust | "Read-only" analysis scripts write; arg filter allows escaping the repo |
| F25 | medium | trust | `_inrepo` uses a string-prefix containment test |
| F26 | medium | oracle | `config/check.*.sha` and `scheduler.py` are writable via the connector |
| F27 | low-med | state | `_migrate_legacy_queue` can silently roll the queue back to an old snapshot |
| F28 | low-med | concurrency | The queue lock silently vanishes off POSIX |
| F29 | low | dead check | `audit_artifact_mapping()` has zero call sites |
| F30 | low | targeting | `find_source` ignores the record's overlay when there is one candidate |
| F31 | low | input | `prepare()` does not fail on a missing `.s` file |
| F32 | low | shell | `cd` is unquoted in `wsl()` |
| F33 | low | hygiene | `.build.lock` and `automation/candidates/` are not gitignored |
| F34 | low | concurrency | SIGTERM while holding the BuildLock leaves it held for an hour |

---

## Critical

### F1 — A matched function is reverted to its INCLUDE_ASM stub by journal replay

**Where:** `worker_direct.py:2514` (`journal_write` inside `apply_code`),
`worker_direct.py:2520-2524` (`restore` → `journal_clear`),
`worker_direct.py:2871-2879` (the matched path),
`worker_direct.py:3025` and `:3037` (`replay_pending_journals`).

**What goes wrong.** `journal_clear()` has exactly one call site: inside
`restore()`. `restore()` is called on every failure path. It is deliberately
**not** called when the build matches — the edit must stay in the tree. So on
success the journal file `automation/logs/pending/<WORKER_NAME>.json`, which
holds the **pre-edit stub text**, survives with no owner and no expiry.

`replay_pending_journals()` writes that stored text back over the source and
deletes the journal. It runs at every worker startup (`:3037`), in the SIGTERM
handler (`:3025`), and on Ctrl-C (`:3077`).

**Trigger.**

1. Worker `fleet-oc-1` matches `BO6_RicSetSlide`. `sched report --status matched`
   succeeds; the queue now records `matched` with `proof` and `verified_at`.
2. Worker returns `True`, loops, claims the next record.
3. Anything sends SIGTERM — `fleet_stop`, a watchdog recycle, a machine
   shutdown. The handler calls `replay_pending_journals()`.
4. The journal is replayed. `src/boss/bo6/…c` is rewritten with the
   `INCLUDE_ASM(...)` stub.

The function is gone. The queue still says `matched`, with machine proof, and
the STRUCTURAL TRUST INVARIANT in `scheduler.py:359-363` — the thing that lets
the orchestrator read the queue without re-verifying — is now false. The next
`make build` fails on that overlay and takes every later report down with it
(see F9).

Step 3 is not even required: the *next* startup of *any* worker replays it
(F2).

**Severity:** critical. Silent, total loss of the harness's only product, with
the queue asserting the opposite.

**Fix.** Call `journal_clear()` immediately after the successful
`sched(... --status matched ...)` at `:2875`, inside the BuildLock, before
`matched = True`. Better: make the journal own its lifetime — write it in
`apply_code`, clear it in a `finally` around the whole critical section, and
have the matched path clear it explicitly.

---

### F2 — Journal replay clobbers other live workers' in-flight edits

**Where:** `worker_direct.py:2164-2189`, called from `:3025`, `:3037`, `:3077`.

**What goes wrong.** `replay_pending_journals()` iterates **every** `*.json` in
`automation/logs/pending/` regardless of which worker wrote it, whether that
worker is still alive, and whether the BuildLock is held. It restores the file
and unlinks the journal.

**Trigger (new worker joins a running fleet).**

1. Worker A holds the BuildLock, has applied its candidate to
   `src/st/no0/clock_room.c`, and is 200 s into `make build`.
2. Worker B is started (fleet scale-up, a manual `worker_direct.py once`, a
   watchdog restart). `main()` calls `replay_pending_journals()` at `:3037`.
3. B rewrites `clock_room.c` with A's stub text and deletes A's journal.
4. A's build finishes against the stub → "does not match" → A files the record
   `near` or `escalated` for a candidate that was never actually compiled.
5. A's own `restore()` then writes its `original` back — same content, so the
   damage is invisible afterwards. A now has no journal, so a subsequent SIGKILL
   leaves its edit in the tree permanently.

**Trigger (fleet_stop).** `fleet_stop` SIGTERMs all four workers. Each handler
replays **all four** journals, including any left by a *matched* record (F1).

**Severity:** critical. Combines silent misclassification with the destruction
of the crash-recovery mechanism it is supposed to be.

**Fix.** Replay only journals whose recorded `worker` is this process, or whose
recorded pid is provably dead; record the pid in `journal_write` (it already
records `worker` and `at`). Hold the BuildLock across replay.

---

### F3 — Connector build and git actions do not respect the BuildLock

**Where:** `commands_client.py:169-252` (`REGISTRY`), `:270` (`run`), `:343`
(`start_job`), `jobs.py:144` (`start`). The only reference to
`automation/.build.lock` outside the worker is `commands_client.py:771`, which
**deletes** it.

**What goes wrong.** `BuildLock` (`worker_direct.py:2049-2064`) is described as
the thing that serialises "apply → build → verify → restore" so that "worker A's
edit would be present in the tree while worker B builds" cannot happen. The
connector is a fifth participant in that tree and takes no part in the protocol:

- `make_build`, `make_clean`, `make_extract`, `make_expected`,
  `make_force_symbols` — all write `build/`, `build.ninja` and
  `build.ninja.version` with no lock.
- `asm_diff` defaults to `make_first=True` (`sotn_cmd_mcp.py:130`), so the
  read-only-sounding diff tool starts a build too.
- `git_add_all` / `git_commit` — stage and commit the whole worktree.
- `git_restore <path>` — discards working-tree edits to one path.
- `verify_build` (`commands_client.py:454`) reads `build/` with no lock.

**Concrete sequences.**

*False verdict:* worker A holds the lock and has `clock_room.c` applied. The
orchestrator calls `verify_build()`. It returns `all_ok: true, 77/77` — a true
statement about the artifacts and a false one about which sources produced them,
because A's unverified candidate is in the tree. If the orchestrator is running
its own function at the same time, it may then legitimately call
`queue_report(status="matched", proof=<that verdict>)` for a record whose code is
not what was measured. **This is a path from a non-matching change to a recorded
`matched`.**

*Corrupt build dir:* the orchestrator calls `job_start('make_clean')` while four
workers build. `jobs` refuses only same-action concurrency (F14), so this runs.
`build/` is deleted underneath four in-flight ninja invocations.

*Committing garbage:* `git_add_all` + `git_commit` while any worker is between
`apply_code` and `restore` commits a temporary candidate that the harness is
about to throw away. `automation/.build.lock` and `automation/candidates/` are
not gitignored (F33), so the commit also captures a live lock file.

*Destroying an edit:* `git_restore("src/st/no0/clock_room.c")` while A holds the
lock reverts A's applied candidate mid-build.

**Severity:** critical. This is the largest structural hole: two independent
subsystems mutate one tree and only one of them locks.

**Fix.** Lift `BuildLock` into a module both sides import (it is 55 lines and
has no worker dependencies). Acquire it in `commands_client.run()` and
`start_job()` for every action in `LONG_ACTIONS` plus `asm_diff`, `git_add_all`,
`git_commit`, `git_restore`, and in `verify_build()`. Make `fleet_stop` break the
lock only after confirming no live pid holds it.

---

## High

### F4 — The scheduler oracle passes vacuously on an empty or corrupt check file

**Where:** `scheduler.py:307-352` (`_verify_artifacts`), called from `:373`.

**What goes wrong.** The function counts `expected` only for lines it can parse.
Lines that fail `line.split(None, 1)` are `continue`d silently (`:327-329`). If
the file exists but yields zero parseable lines, `missing` and `bad` are both
empty and the function returns `(True, "0/0 artifacts byte-exact")`. The caller
at `:374` treats that as proof and records `matched`.

The same shape holds partially: if half the file is corrupted, the oracle
verifies the surviving half and reports `"38/38 artifacts byte-exact"` —
a number that looks like success and is not comparable to anything.

The only guard is `if not check.exists()` at `:318`. A zero-byte or truncated
file is not a missing file.

**Trigger.** A crashed `git checkout`, an interrupted sync, or a `write_file`
through the connector (F26) leaves `config/check.us.sha` empty. The next
`report --status matched` is accepted with no verification whatsoever, and the
proof string is decorated `[scheduler-verified: 0/0 artifacts byte-exact]`.

**Severity:** high. This is the oracle's own fail-open.

**Fix.**

```python
if expected == 0:
    return False, f"oracle file {check} has no usable entries"
```

plus a count of unparsable lines in the detail, and ideally a floor
(`expected >= 70` for `us`) so a shrunken oracle is loud.

---

### F5 — A compiler warning misclassifies a permuter candidate as BUILD FAILED

**Where:** `worker_direct.py:2537-2566` (`build_failed_to_compile`), the grep at
`:2610-2617`, the routing at `:2881` and `:2912-2948`.

**What goes wrong.** The classifier is:

```python
if rc == 0: return False
if any(m in out for m in _COMPILE_FAIL_MARKS) or _DIAG_RX.search(out):
    return True
return "checksum check failed" not in out
```

`_DIAG_RX` is `[^\s]+\.(?:c|h):\d+:` (`:2534`) — it matches
`src/st/no0/clock_room.c:88: warning: …` exactly as well as an error, because
GCC 2.7 has no `error:` keyword to distinguish them (which is the stated reason
the regex is shaped this way). The build grep at `:2612-2614` uses the same
pattern, so warnings are guaranteed to be in `out` whenever they exist.

`make build` exits non-zero on a pure checksum mismatch
(`tools/sotn-assets/check.go:92` → `build.go:42`), so `rc != 0` is the normal
outcome for a *good* candidate. The evidence that the build was fine
("checksum check failed") is only consulted on line `:2566`, **after** the
diagnostic test has already returned `True`.

**Trigger.** Model produces C that compiles with one warning and misses on bytes.
`out` contains the warning line → `really_broken = True` → `detail` starts with
`"BUILD FAILED:"` → `compiled_once` stays `False` at `:2881` → no permuter seed
is saved (`:2890`) → the record is routed to `escalated` with `--score 0`
(`:2943`) instead of `near`/`--score 50` with a seed.

**Severity:** high. It reproduces exactly the failure the 30-line docstring at
`:2537-2558` says it fixed, and it starves the permuter of the seeds that
`save_candidate`'s docstring (`:756-774`) says were already lost once.

**Fix.** Reorder and tighten:

```python
if any(m in out for m in _COMPILE_FAIL_MARKS):
    return True
if "checksum check failed" in out:
    return False
if _DIAG_RX.search(out) and not re.search(r":\d+:\s*warning:", out):
    return True
return True
```

and exclude `warning:` lines from the grep fed to the model as feedback.

---

### F6 — Infrastructure failures are filed as escalated build failures

**Where:** `worker_direct.py:520-540` (`wsl`), `:2610-2623`, `:2940-2948`.

**What goes wrong.** `wsl()` never raises. A timeout returns
`(124, "timeout after 900s")` and any other exception returns
`(1, "wsl invocation failed: …")`. Both land in `build_and_check` as `rc != 0`
with output containing no diagnostics *and* no `"checksum check failed"`, so
`build_failed_to_compile` returns `True` at `:2566`, `detail` becomes
`"BUILD FAILED: timeout after 900s"`, and the record is escalated with score 0.

So "the machine was busy", "WSL was restarting" and "the build exceeded
`BUILD_TIMEOUT`" are all recorded as *the model wrote non-compiling C*. Compare
`:2924-2939`, which goes to considerable trouble to requeue a record when the
**model** failed for infrastructure reasons — the same reasoning is not applied
to the build.

**Secondary, worse:** on a `make build` timeout, `subprocess.run` kills
`wsl.exe`/`bash` only. `ninja` and the compilers keep running inside WSL,
writing `build/`. The worker then restores the source **underneath a live
build**, releases the BuildLock, and the next worker applies its own candidate
and starts a second ninja into the same directory. The artifacts that result
verify against nothing.

**Severity:** high (misclassification) plus high (orphan build corrupting the
shared build dir).

**Fix.** Have `wsl()` distinguish infra failure from build failure — return a
sentinel for rc 124/`wsl invocation failed` and route those to `todo` with a
note, not `escalated`. Launch the build with `start_new_session=True` and
`os.killpg(...)` on timeout so nothing survives it.

---

### F7 — ASM truncation makes the size gate unreachable on `cli` and silently feeds partial assembly

**Where:** `worker_direct.py:396` (`MAX_ASM_CHARS = 12000`), `:862`
(`read()[:MAX_ASM_CHARS]`), `:419-420` (`MAX_FUNC_CHARS` = 20000 for `cli`),
`:2693` (the gate).

**What goes wrong.** The gate compares the **already truncated** length:

```python
asm_text = open(p, errors="ignore").read()[:MAX_ASM_CHARS]   # <= 12000
...
if len(ctx["asm"]) > MAX_FUNC_CHARS:                          # cli: > 20000
```

12000 can never exceed 20000. Two consequences:

1. A `cli` worker **can never defer for size**. The `TIER_HANDOFF_TOO_LARGE`
   mechanism is one-directional by construction, which is fine, but it also
   means the cli tier has no "too large for me" escape at all.
2. Every function whose assembly exceeds 12000 characters is handed to the model
   with the tail silently removed. It is asked to produce a complete function
   from a partial one. It cannot match. The record is then filed `near` (if the
   truncated version happens to compile) or `escalated` — for a reason that has
   nothing to do with the model or the function.

The comments at `:411-418` state that the cli tier "exists precisely to pick up
what llama defers" and that hosted models "take much more context". The code
truncates that context to 12000 chars before the model ever sees it.

On the `http` backend the gate works (6000 < 12000), but a >12000-char function
is reported as `asm 12000 chars > 6000`, understating the real size in the
handoff note the next tier reads.

**Severity:** high. Silent input corruption on the majority of remaining work —
the same comment block at `:276-278` says 59% of remaining functions produce
prompts over 32767 chars.

**Fix.** Measure before truncating:

```python
raw_asm = open(p, errors="ignore").read()
ctx["asm_full_len"] = len(raw_asm)
asm_text = raw_asm[:MAX_ASM_CHARS]
```

gate on `asm_full_len`, and refuse to generate (defer) whenever
`asm_full_len > MAX_ASM_CHARS`.

---

### F8 — `ctx.c` is a single shared file written by every worker outside the lock

**Where:** `worker_direct.py:864-871` (`prepare`), `tools/m2ctx.py:83`
(`open(os.path.join(root_dir, "ctx.c"), "w")`), and the sequencing at `:2692`
(prepare runs before the BuildLock is taken at `:2861`).

**What goes wrong.** `prepare()` runs

```
python3 tools/m2ctx.py <src_rel>      -> writes <repo>/ctx.c
python3 tools/m2c/m2c.py --context ctx.c -f <fn> <asm>
```

`ctx.c` is at the repo root and its name is fixed. Four workers run `prepare()`
concurrently — deliberately, because this phase is documented as safe to
overlap: `BuildLock`'s docstring at `:2052-2057` says "Generation (the slow
part…) is safe to overlap **because it only reads**", and `:2755` repeats
"generation: safe to run concurrently with other workers".

It does not only read. Worker B's `m2ctx` overwrites `ctx.c` between worker A's
`m2ctx` and worker A's `m2c`, so A's first draft is typed against B's
translation unit. `ctx_ok` at `:867` only checks that the file **exists**, so
there is no error, no warning, and no way to tell afterwards. The output is a
draft with wrong or missing struct types — precisely the class of defect the
whole DECLARATIONS/ENTITY LAYOUT apparatus exists to prevent.

**Trigger.** Any two workers whose `prepare()` calls overlap. With four workers
and m2ctx taking seconds, this is the common case, not the rare one.

**Severity:** high. Silent, systematic degradation of every prompt, invisible in
logs.

**Fix.** Give m2ctx an output path (`--out ctx.<WORKER_NAME>.c`) or run
`prepare()` in a per-worker temp cwd; pass that path to `m2c --context`. Add
`ctx.*.c` to `.gitignore` alongside the existing `ctx.c`.

---

### F9 — A verified match is deleted and refiled `escalated` when the scheduler refuses the report

**Where:** `worker_direct.py:2860-2877` (the matched path), `:594`
(`sched` raises on rc != 0), `:2964-2969` (the generic handler),
`scheduler.py:364-379` (whole-tree re-verification).

**What goes wrong.** Inside the BuildLock the worker proves its own artifact and
calls `sched("report", ..., "--status", "matched", ...)`. The scheduler
re-verifies **all 77 artifacts** (`_verify_artifacts`, `scheduler.py:307`). If
any unrelated artifact is dirty, it `sys.exit`s with a message, `sched` raises
`RuntimeError`, the exception escapes the `with BuildLock`, and the generic
handler runs:

```python
except Exception as e:
    if original is not None:
        try: restore(ctx, original)      # original IS not None here
        except Exception: pass
    sched("report", ..., "--status", "escalated",
          "--notes", f"worker error: {type(e).__name__}: {e}"[:250])
```

The byte-exact code is **deleted from the tree** and the record is filed
`escalated` with a note that reads like a worker crash.

**Trigger — several, none involving a racing worker:**

- a previously matched function is in the tree but its overlay has not been
  rebuilt since (the tree is legitimately dirty relative to `build/`);
- a human left an uncommitted experiment in another overlay;
- an orphaned build from F6 was still writing `build/` when this build ran;
- the connector ran `make_clean` or `make_build` out of band (F3);
- `expected/build/<v>` copying (`build.go:41-46`) or any partial build left one
  artifact stale.

The 18-line comment at `:2842-2859` asserts that moving the report inside the
lock fixed this class ("a REAL match was thrown away and marked escalated…
Confirmed on two records"). It fixed only the worker-versus-worker instance. The
scheduler still verifies global state from inside a local lock, and every other
cause of global dirtiness still discards the match.

**Severity:** high. Loses the most expensive artifact the harness produces, and
does so *more* often as the tree accumulates matches.

**Fix.** Handle a refused `matched` explicitly rather than letting it fall into
the generic handler:

```python
try:
    sched(..., "--status", "matched", ...)
    journal_clear()          # see F1
    matched = True
except RuntimeError as e:
    # Our artifact verified. The tree is dirty elsewhere. Keep the edit.
    sched(..., "--status", "near", "--score", "99",
          "--notes", f"artifact verified locally; scheduler refused: {e}"[:250])
    matched = True           # do NOT restore
```

Longer term: scope the scheduler's re-verification to the record's own artifact
plus a recorded whole-tree baseline, so "someone else's overlay is dirty" is not
the same event as "this function does not match".

---

### F10 — Stale-lock takeover is TOCTOU; two workers can hold the BuildLock

**Where:** `worker_direct.py:2071-2094` (`acquire`), `:2096-2106` (`release`).

**What goes wrong.**

```python
except FileExistsError:
    age = time.time() - os.path.getmtime(self.path)
    if age > self.stale_after:
        os.unlink(self.path)      # unconditional
        continue                  # retry the O_EXCL create
```

Two waiters can both observe `age > stale_after` before either acts:

1. B reads mtime → stale. C reads mtime → stale.
2. B unlinks, loops, `O_CREAT|O_EXCL` succeeds → **B holds the lock**.
3. C unlinks — **B's fresh lock** — loops, `O_CREAT|O_EXCL` succeeds → **C holds
   the lock**.

Both now apply candidates to the tree and build. Each `release()` then unlinks
`self.path` unconditionally, so whichever finishes first deletes the other's
lock and admits a third worker.

`stale_after` is 3600 s and nothing refreshes the lock's mtime while it is held,
so a legitimately long critical section (`BUILD_TIMEOUT` is configurable) also
becomes "stale" while genuinely in use.

**Severity:** high (low frequency, catastrophic effect: two simultaneous edits
to one tree, arbitrary cross-contamination of results).

**Fix.** Take over by rename, not by unlink:

```python
mine = f"{self.path}.take.{os.getpid()}"
os.close(os.open(mine, os.O_CREAT | os.O_EXCL | os.O_RDWR))
try:
    os.rename(mine, self.path)   # loser's rename is harmless only if …
```

or, since both the fleet and the connector run on Linux, use `fcntl.flock` on a
never-replaced lock file — which is exactly the correction `scheduler.py:117-123`
already documents for the queue. The lesson was learned in one file and not
applied in the other.

Also: refresh the mtime periodically while holding, and have `release()` verify
ownership (compare the pid written at `:2076`) before unlinking.

---

### F11 — `report --id <unknown>` is a silent no-op that exits 0

**Where:** `scheduler.py:383-401`.

```python
def fn(records):
    for r in records:
        if r["id"] == args.id: ...; return records, True
    return records, False

print("updated" if q.transaction(fn) else f"id not found: {args.id}")
```

The process exits 0 either way. `worker_direct.sched()` (`:592-595`) raises only
on `rc != 0`, and `commands_client.queue_report()` (`:499-502`) returns
`returncode: 0`. Every caller reads a successful report.

**Trigger.** A record pruned by `queue_prune` while a worker holds it; an id
mangled by the `wsl` command-line round trip; the orchestrator reporting against
an id from a stale `queue_list`. The outcome is recorded nowhere, the claim
leaks (status stays `claimed` until a `reclaim`), and the worker moves on
believing it filed a result.

**Severity:** high — this is the canonical "reports success when it did nothing".

**Fix.** `sys.exit(f"id not found: {args.id}")` on the false branch, and have
`commands_client.queue_report` surface a non-zero returncode as an error field.

---

### F12 — No claim fencing: a late worker can overwrite a verified match

**Where:** `scheduler.py:383-398` (`cmd_report` matches on `id` alone),
`scheduler.py:583-604` (`cmd_reclaim`), `commands_client.py:768-770`
(`fleet_stop` reclaims with `--older-than-min 0`).

**What goes wrong.** `report` updates whatever record has that id. It does not
check `claimed_by`, does not check the current status, and there is no claim
token. Meanwhile `reclaim` can return a record to `todo` while its worker is
still alive and working on it.

**Trigger.**

1. Worker A claims `us:BOSS/BO6:BO6_RicSetSlide` and stalls (a 30-minute
   `opencode` run plus retries; `FUNC_BUDGET` is 1800 s on `cli`).
2. A watchdog runs `reclaim --older-than-min 60`, or an operator runs
   `fleet_stop`, which reclaims **everything** at `--older-than-min 0`.
3. Worker B claims the same record, matches it, and the scheduler writes
   `status=matched`, `proof=…`, `verified_at=…`.
4. Worker A finishes and reports `escalated`.

The record now reads `status: escalated, score: 0` while still carrying `proof`
and `verified_at` from B. The match is invisible to `queue_stats`, the code is
in the tree with nothing pointing at it, and the record's own fields contradict
each other.

The reverse also happens: A reports `matched` for code that B has since
restored — the scheduler's re-verification catches that one, so it fails safe.
The `escalated`-over-`matched` direction does not.

**Severity:** high.

**Fix.** Have `cmd_next` mint a `claim_token` (uuid4) into the record and return
it; require `report --claim-token` and refuse a mismatch. Cheaper interim:
refuse any transition **out of** `matched` unless `--force` is passed, and make
`report` refuse when `claimed_by != --worker`.

---

## Medium-high

### F13 — `sched()` drops the claim before the scheduler call succeeds

**Where:** `worker_direct.py:585-596`.

```python
if args and args[0] == "report" and "--id" in args:
    _rid = args[args.index("--id") + 1]
    if _rid == _CURRENT_CLAIM:
        _CURRENT_CLAIM = None          # cleared BEFORE the command runs
rc, out = wsl("python3 automation/scheduler.py " + ...)
if rc != 0:
    raise RuntimeError(...)
```

If the scheduler fails — non-zero exit, or `wsl()` returning `(124, "timeout")`
at `:535` — the queue still says `claimed`, but `release_claim_if_held()`
(`:555-575`) now considers the claim released and does nothing. On SIGTERM or
Ctrl-C the record is stranded `claimed` until someone runs `reclaim`.

The mirror-image problem is in `claim_next()` (`:599-611`): if `wsl` times out
*after* the scheduler has written the claim but *before* its stdout is captured,
the record is `claimed` by a worker that never learned its id — unrecoverable by
any in-process mechanism.

**Fix.** Move the clear to after `rc == 0`. For `claim_next`, have the scheduler
write the claimed id to a per-worker file inside the transaction so a lost
stdout is recoverable.

---

### F14 — Job exclusivity covers the wrong resource and fails open

**Where:** `jobs.py:124-141` (`running_jobs`), `:144-192` (`start`),
`:106-122` (`_alive`).

Three separate defects in one mechanism whose docstring (`:148-151`) says
"Refusing is always better than racing":

1. **Wrong granularity.** `exclusive` refuses only another job of the *same
   action*. `make_build`, `make_clean`, `make_extract`, `make_expected` and
   `make_force_symbols` are five actions that all write `build/`,
   `build.ninja` and `build.ninja.version`. `job_start('make_clean')` during a
   running `make_build` is permitted and deletes the build directory under it.
   And no job of any kind is excluded against the fleet's own builds (F3).

2. **Fails open on a dead wrapper.** `running_jobs` requires *both* "no `.done`"
   **and** `_alive(pid)`. `pid` is the `/bin/sh` wrapper. If the wrapper is
   killed (OOM killer, a stray `kill`, a `killpg` that missed a child) while
   `make`/`ninja` survive as orphans, the job looks finished, the exclusivity
   check passes, and a second `make build` starts on top of the first — the exact
   outcome the docstring says is impossible.

3. **PID identity is never checked.** `_alive` only asks whether *a* process with
   that pid exists. A recycled pid pins an action as permanently "running" and
   blocks `job_start` for that action until someone deletes the meta file by
   hand. `commands_client._fleet_pids_alive` (`:688-728`) gets this right —
   it reads `/proc/<pid>/cmdline` and verifies — and `jobs.py` does not.

**Fix.** One `build` exclusion class covering every `make_*` action; store the
wrapper's pgid and its cmdline and verify both in `_alive`; and share the
BuildLock with the workers (F3).

---

## Medium

### F15 — A finished job can be reported as failed (empty `.done` race)

**Where:** `jobs.py:174-176` and `:232-241`.

```sh
<cmd> > log 2>&1; printf '%s' "$?" > done
```

The shell **creates** `done` on the redirection, then `printf` writes it. There
is a window in which `done_p.exists()` is true and its content is empty.
`status()` then computes

```python
rc = int((done_p.read_text(encoding="utf-8") or "1").strip() or 1)
```

→ `rc = 1` → `{"state": "done", "ok": False, "returncode": 1}` for a build that
in fact succeeded. The `or 1` fallback converts a transient empty read into a
confident wrong verdict rather than a retry.

**Fix.** `printf '%s' "$?" > done.tmp && mv done.tmp done`, and treat an empty
sentinel as "finishing" (loop again) rather than as rc 1.

### F16 — Job ids collide and silently retarget a poller

**Where:** `jobs.py:163-169`.

`job_id = f"{action}-{time.strftime('%H%M%S')}-{os.getpid()}"` has no date and
no counter. Two `make_build`s started by the same long-lived connector process at
the same wall-clock second on different days produce the same id; `start` then
unlinks the previous `.log`/`.done` and overwrites the `.json`. A caller still
polling the old id gets the new job's verdict with no indication anything
changed. Use `uuid4().hex[:8]` or an epoch timestamp.

### F17 — `run()` timeout orphans the build

**Where:** `commands_client.py:270-288`; also `:442` (`fs_search`) and `:467`
(`verify_build`).

`subprocess.run(argv, timeout=…)` kills only the direct child. `make` dies;
`ninja` and the compilers keep running and keep writing `build/`. The returned
dict is `{"timed_out": True, "timeout": N}` and nothing else — the caller cannot
distinguish "stopped" from "still mutating the tree". This is verbatim the
failure shape that `jobs.py`'s module docstring (`:11-17`) says is "the worst
possible failure shape", in the code path `jobs.py` exists to replace and which
is still exposed as `make_build` (`sotn_cmd_mcp.py:80`).

`fs_search` and `verify_build` do not catch `TimeoutExpired` at all; it escapes
as an unhandled exception.

**Fix.** `start_new_session=True` and `os.killpg(os.getpgid(p.pid), SIGKILL)` in
the timeout handler; catch `TimeoutExpired` in `fs_search`/`verify_build`.

### F18 — `opencode` stderr is never drained: deadlock, phantom timeouts, zombies, fd leak

**Where:** `worker_direct.py:283-353`.

`stderr=subprocess.PIPE` is set at `:285` and first read at `:335`, *after*
`proc.wait()`. A child that writes more than the pipe buffer (64 KiB on Linux)
to stderr blocks forever. `proc.wait(timeout=_to)` then fires and the attempt is
charged as a timeout at `:2773-2781` — even though the model answered correctly
and its output is sitting in `buf`.

The docstring at `:288-299` works this reasoning out precisely for **stdin**
("a prompt larger than the pipe buffer … blocks mid-write") and then leaves
stderr undrained. `opencode` is a Node CLI that logs to stderr; 64 KiB is not a
lot.

Two adjacent leaks:

- `:330-332` `proc.kill(); raise` with no `proc.wait()` → a zombie per timed-out
  attempt.
- `proc.stdout` and `proc.stderr` are never closed → two fds leaked per attempt.
  A `loop` worker running for hours will hit `EMFILE`.

**Fix.** `stderr=subprocess.STDOUT` (the pump thread already prints everything),
or a second drain thread; `proc.wait()` after `kill()`; wrap the Popen in `with`.

### F19 — `shim_gate`'s blocker reason is computed and thrown away

**Where:** `worker_direct.py:2704-2711`, `shim_gate` docstring `:2355-2359`.

The docstring states that the 121 "shared impl exists but blocked" records
"are annotated instead, so the blocker is visible on the record without blocking
the record." The code does this:

```python
if _why and not dry:
    print(f"  ~~ {_why}", flush=True)
```

`_why` goes to a gitignored worker log and nowhere else. Nothing is written to
the queue record. The annotation the design depends on does not exist —
a designed output, computed and discarded.

**Fix.** `sched("report", "--id", rec["id"], "--status", "todo", "--notes",
_why[:250])` before generating, or add a `scheduler annotate-note` verb so the
status is not touched.

### F20 — Quality-gated records are escalated as though they failed to build

**Where:** `worker_direct.py:2818` (`produced_code = True`), `:2826-2838` (the
gate `continue`s before any build), `:2940-2948`.

`produced_code` is set as soon as a candidate is longer than 20 characters —
before the quality gate, before `apply_code`, before any build. If all four
attempts are rejected by `quality_gate` / `review_gate`, then `compiled_once` is
False and `produced_code` is True, so the `else` branch fires with the comment
"A candidate WAS produced and it failed to build" and files `escalated`,
`--score 0`, with `best_build` empty and `best` reading `"quality reject: …"`.

Nothing reached the compiler. The record is routed toward "needs a stronger
model" when the real signal is "the gate rejects the same defect every time" —
possibly a false positive in the gate itself (`quality_gate` check 3 at `:1549`
flags `unsigned char` anywhere in the text, including inside a comment).

**Fix.** Track `built_at_least_once` separately from `produced_code`, and route
all-rejected records to `todo` with the defect in the notes, or to a distinct
status.

### F21 — Unbounded requeue; `iterations` is never incremented by anyone

**Where:** `worker_direct.py:2924-2939`; `scheduler.py:396`, `:631`.

The requeue path returns a record to `todo` with no attempt counter and no
backoff. `scheduler.cmd_report` maintains `r["iterations"] += args.add_iters`,
but `--add-iters` has **zero call sites in the repository** (verified across
`automation/`): neither `worker_direct.sched()` nor
`commands_client.queue_report()` passes it. `iterations` is therefore
permanently 0 and carries no information.

A record the fleet can never generate for — a model that always returns empty, a
prompt that always exceeds the transport, an asm file that does not exist (F31) —
is re-claimed forever. It burns account-wide OpenCode quota, occupies a worker,
and is indistinguishable in `queue_stats` from work nobody has attempted.

**Fix.** Pass `--add-iters 1` on every report, and refuse to requeue past a
threshold (route to `escalated` with the accumulated history instead).

### F22 — The deferred pool leaks: routing ignores `claimed_from`

**Where:** `worker_direct.py:2681` (records `_CURRENT_CLAIM_FROM`),
`:555-575` (`release_claim_if_held` honours it), `:2920`, `:2937`, `:2943` (the
three real routing calls, none of which do).

`scheduler.cmd_next` records `claimed_from` and `cmd_reclaim` restores to it, and
the comments at `:556-562` and `scheduler.py:286-293` explain at length why a
`deferred` handoff must not silently become `todo`. Only the *interrupt* path
respects this. The normal endings do not.

**Trigger.** A `cli` worker claims a `TIER_HANDOFF_TOO_LARGE` deferred record,
fails to generate (empty responses, quota), and the requeue path at `:2937`
reports `todo`. An `http` worker then claims it, hits its own 6000-char gate,
and defers it again — churning the record and rewriting its notes indefinitely.

**Fix.** Use `_CURRENT_CLAIM_FROM` in the requeue branch (`todo` → back to
`deferred` when that is where it came from), or better, have the scheduler
resolve `todo` to `claimed_from` on report the way `reclaim` already does.

### F23 — `fleet_stop` deletes a lock and reclaims claims it does not own

**Where:** `commands_client.py:751-796`, `_fleet_pids_alive` `:688-728`.

`_fleet_pids_alive` only sees pids from `automation/logs/fleet.pids` and
`automation/logs/worker-*.pid`, and requires `/proc`. A worker started by hand,
or by `automation/win/start_fleet.ps1` on the Windows side, is invisible to it.
`fleet_stop` then:

- unlinks `automation/.build.lock` (`:771-776`) while that worker holds it —
  after which a second process can enter the critical section, and the
  survivor's `release()` (`worker_direct.py:2103-2106`) deletes a third party's
  lock;
- runs `reclaim --older-than-min 0` (`:768`), resetting that worker's live claim
  so another worker takes the same record (see F12);
- returns `"note": "claims released, lock cleared"` unconditionally, including
  when `alive` was empty and it killed nothing.

**Fix.** Only break the lock if the pid recorded in it is dead. Scope the reclaim
to the workers actually stopped (`reclaim --worker <name>`), not to every claimed
record in the queue.

### F24 — "Read-only" analysis scripts write, and the arg filter allows escaping the repo

**Where:** `commands_client.py:80-127`, `sotn_cmd_mcp.py:397-413`.

The comment at `:88-90` states: "Every script listed is read-only by design
(they analyse and report; none edit sources or build), so exposing them costs
nothing in blast radius."

`automation/asm_twin_finder.py:741` writes `automation/twins.us.json` under
`--record`, and `:782`/`:819` write to an arbitrary `--json <path>`. Both flags
pass `_args()`: `_ARG_RX` (`:109`) accepts `--record`, and its first alternative
`^[A-Za-z0-9_][A-Za-z0-9_./=-]{0,120}$` accepts a path that merely *starts* with
an alphanumeric — so `--json a/../../../../tmp/out.json` is allowed and writes
outside the repo. `twins.us.json` is consumed by `scheduler annotate` and by the
worker's prompt builder (`worker_direct.py:1656-1672`), so rewriting it changes
what the fleet is told about every function.

**Fix.** Reject `..` in any argument token; validate path-shaped arguments with
`_inrepo`; drop `--record`/`--json` from the accepted flag set or split writing
scripts out of `ANALYSIS_SCRIPTS`. Also correct the comment.

Related, cosmetic: `sotn_cmd_mcp.py:407-409` documents 7 allowed scripts;
`ANALYSIS_SCRIPTS` contains 13.

### F25 — `_inrepo` uses a string-prefix containment test

**Where:** `commands_client.py:63-71`.

```python
rp = (REPO / p).resolve()
if not str(rp).startswith(str(REPO.resolve())):
```

`/home/u/SOTN-Decomp-old/x` starts with `/home/u/SOTN-Decomp`, so
`_inrepo("../SOTN-Decomp-old/x")` passes. `_resolve` (`:384-397`) does the same
job correctly with `rp != root and root not in rp.parents`. Two guards, two
different answers; `git_restore`, `permuter`, `permuter_import` and `queue_init`
all use the weak one. Make `_inrepo` delegate to `_resolve`.

### F26 — The oracle file and the queue writer are writable through the connector

**Where:** `commands_client.py:384-417` (`_resolve` / `fs_write`),
`sotn_cmd_mcp.py:450-454` (`write_file`).

`_resolve` blocks `.git` and nothing else. `write_file` can therefore overwrite:

- `config/check.us.sha` — the oracle. `scheduler.cmd_report` (`:364-379`)
  re-verifies against exactly this file, so anything that can call the connector
  can redefine what "matched" means. Combined with F4, writing an empty file is
  enough to make every subsequent `matched` report succeed unconditionally.
- `automation/scheduler.py` — the single queue writer, including the trust
  invariant itself.
- `automation/win/worker_direct.py`, `automation/mcp/commands_client.py`.

The whole design rests on "a model's claim is never sufficient"
(`scheduler.py:359-363`). That property is only as strong as the immutability of
the file it is checked against.

**Fix.** Extend `_resolve`'s deny list to `config/check.*.sha`, `automation/*.py`
and `automation/mcp/*.py`; or restrict `fs_write` to `src/`, `include/` and
`docs/`.

---

## Low-medium

### F27 — `_migrate_legacy_queue` can silently roll the queue back

**Where:** `scheduler.py:63-95`, executed unconditionally at import (`:95`).

The migration fires whenever the live queue is absent or zero-length, and copies
`<repo>/work/queue.jsonl` — a file the docstring says is "deliberately never
deleted… kept as a recovery point" and therefore arbitrarily stale — over the
live path. There is no timestamp comparison, no record-count comparison, and the
only notice is a single stderr line that `wsl()` folds into stdout and
`claim_next` discards.

It also runs **outside** the lock, at import time, so two scheduler processes can
race here before either enters a transaction.

**Trigger.** The live queue is lost (disk, a bad `SOTN_QUEUE`, a cleanup). The
next `report` resurrects a snapshot from whenever the legacy copy was taken, the
report is applied to *that*, and every `matched` recorded since is gone. The
harness continues, reporting success.

**Fix.** Refuse to migrate if the legacy file's newest `updated_at` is older than
some threshold without an explicit `--migrate` flag; print the record count and
newest timestamp of what is being restored; run it inside the lock.

### F28 — The queue lock silently vanishes off POSIX

**Where:** `scheduler.py:37-41`, `:150-162`.

```python
except ImportError:  # pragma: no cover - Windows fallback, no real locking
    _HAVE_FCNTL = False
```

`transaction()` then performs an unlocked read-modify-write with no warning, no
error, and no marker in the output. The comment acknowledges "no real locking"
and the surrounding design comments treat the lock as what makes the
single-writer property true. The repo ships a Windows worker
(`worker_direct.py`, `IS_WINDOWS` branches) and `automation/win/start_fleet.ps1`,
so a Windows-Python invocation is reachable.

**Fix.** Refuse to run any mutating subcommand when `_HAVE_FCNTL` is False, or
implement an `O_EXCL` lock-file fallback. A read-only `stats`/`list` may proceed
with a warning.

---

## Low

### F29 — `audit_artifact_mapping()` is dead code

`worker_direct.py:825-848`. Zero call sites anywhere in the repo. Its own
docstring: "A missing entry does not fail loudly at runtime, it just makes that
overlay permanently unmatchable, which is exactly the kind of defect that
hides." That defect still hides, because the detector never runs. The
`_ARTIFACT_OVERRIDES` table it validates (`:803-811`) is hand-maintained and
currently has one entry. Call it once at worker startup (it is cheap and
read-only) and log any results.

### F30 — `find_source` ignores the record's overlay when there is one candidate

`worker_direct.py:736`: `if overlay and len(cands) > 1:`. With exactly one
candidate the record's own overlay is never consulted, so a function stubbed only
in a different overlay is silently targeted there and the `us` oracle then judges
a change to the wrong file. Check the overlay whenever it is supplied; if no
candidate matches, report rather than guess.

### F31 — `prepare()` does not fail on a missing `.s` file

`worker_direct.py:860-862`: if the asm path does not exist, `asm_text` stays `""`
and generation proceeds with an empty `=== MIPS ASSEMBLY ===` section. The
docstring of `find_source` (`:700-709`) describes exactly this symptom
("handed the model an EMPTY assembly section while still asking it to
decompile") and fixes only the cause it found. The symptom is still unguarded,
so any new path to a missing `.s` — a renamed overlay, an unextracted build —
reproduces it silently and burns four attempts plus a quota. Add
`if not asm_text: report escalated("asm not found: …"); return`.

### F32 — `cd` is unquoted in `wsl()`

`worker_direct.py:528`: `full = f"cd {wsl_repo()} && {cmd}"`. Every other command
construction in this file is scrupulous about `shlex.quote` (see the note at
`:578-584`). A repo path containing a space breaks every WSL call with a
confusing error; metacharacters would be worse. `shlex.quote(wsl_repo())`.

### F33 — `.build.lock` and `automation/candidates/` are not gitignored

`.gitignore` ignores `automation/logs/` (so journals and generations are safe)
but not `automation/.build.lock` or `automation/candidates/`. A connector
`git_add_all` + `git_commit` during a fleet run commits a live lock file
containing a pid, and every permuter seed. A later checkout of that commit
recreates `.build.lock` and wedges the fleet for `stale_after` (3600 s) before
the takeover path (F10) fires.

### F34 — SIGTERM while holding the BuildLock leaves it held

`worker_direct.py:3021-3028`: `_on_sigterm` ends in `os._exit(143)`, which
releases nothing — not the BuildLock, and not the `atexit`-registered pid file
(`:3054-3062`). `fleet_stop` happens to delete the lock afterwards
(`commands_client.py:771`), so the fleet path is covered by accident; a plain
`kill <pid>` on one worker stalls every other worker for an hour. Release the
lock in the handler (track the active `BuildLock` in a module global).

---

## Comments that contradict the code

Listed separately because the comments in this repo are unusually detailed and
are being used as documentation.

| Location | Claim | Reality |
|---|---|---|
| `worker_direct.py:2052-2057`, `:2755` | "Generation… is safe to overlap **because it only reads**" | `prepare()` runs `m2ctx.py`, which writes the shared `<repo>/ctx.c` (F8) |
| `worker_direct.py:2537-2558` | The BUILD FAILED / checksum distinction is fixed; misrouting "was here" | Any compiler **warning** still routes a compiling candidate to `escalated` (F5) |
| `worker_direct.py:2842-2859` | Moving the report inside the lock stopped real matches being thrown away | Only fixes worker-vs-worker; any other dirty artifact still deletes the match (F9) |
| `worker_direct.py:2355-2359` (`shim_gate`) | Blocked records "are annotated instead, so the blocker is visible on the record" | `_why` is only printed to a gitignored log; nothing writes the record (F19) |
| `worker_direct.py:2133-2143` (`journal_write`) | "the damage is recoverable by anyone: the next worker start, or fleet_stop, replays it" | That replay is what destroys a matched function (F1) and clobbers live workers (F2) |
| `worker_direct.py:288-299` | Careful analysis of pipe-buffer deadlock — for stdin | `stderr` is a PIPE drained only after `wait()`; same deadlock (F18) |
| `worker_direct.py:411-420` | The `cli` tier "exists precisely to pick up what llama defers"; hosted models "take much more context" | ASM is truncated to 12000 chars before the gate, so `cli` never sees more (F7) |
| `commands_client.py:88-90` | "Every script listed is read-only by design… none edit sources" | `asm_twin_finder.py --record` / `--json` write, including outside the repo (F24) |
| `jobs.py:148-151` | "Two concurrent `make build`s… Refusing is always better than racing" | Different `make_*` actions are not mutually exclusive, and a dead wrapper fails the check open (F14) |
| `jobs.py:11-17` | The synchronous path's "worst possible failure shape" (tree mid-build, caller unaware) | `commands_client.run()` still exposes exactly that, and orphans ninja on timeout (F17) |
| `scheduler.py:307-315` | "A caller cannot talk its way past this" | An empty/corrupt `check.<v>.sha` returns `True, "0/0 artifacts byte-exact"` (F4), and that file is writable via the connector (F26) |
| `scheduler.py:117-123` | Correctly diagnoses why locking a replaced inode is unsound | `BuildLock` makes the equivalent mistake (unlink + recreate) and is not fixed (F10) |
| `scheduler.py:556-562` (`release_claim_if_held`) | `claimed_from` prevents a deferred record escaping the deferred pool | Only the interrupt path uses it; all three normal routing calls hard-code the status (F22) |

---

## Recommended order of work

1. **F1** — one line (`journal_clear()` on the matched path). Highest
   damage-per-character in the whole harness.
2. **F2** — filter `replay_pending_journals` to this worker / dead pids.
3. **F4** + **F26** — make the oracle non-vacuous and non-writable.
4. **F3** — share `BuildLock` between the worker and the connector.
5. **F5**, **F6**, **F9** — the three routing errors that discard real results.
6. **F7**, **F8** — the two silent input corruptions.
7. **F11**, **F12**, **F13** — queue-level truthfulness (report failures visible,
   claims fenced).
8. Everything else.
