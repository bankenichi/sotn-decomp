# AGENTS.md

Read this first. It is the entry point for any agent working in this repository,
whichever client you are running under.

---

## 1. What this project actually is

This is a fork of the Castlevania: Symphony of the Night decompilation, and the
decompilation is **not the point**. It is an AI proof of concept that happens to
be pointed at a matching decompilation, chosen because the oracle is binary and
cannot be argued with: every configured SHA-1 checksum either matches or it does not. There is
no partial credit, no reviewer to persuade, and no way to fake progress.

Two consequences follow, and both override ordinary instincts:

- **No pull request will ever be opened.** Do not prepare one, do not format
  work as one, do not optimise for upstream's review preferences.
- **The deliverable is the harness and the knowledge base**, not the matched
  functions. A function that matches but teaches nothing is worth less than a
  failure that is understood and written down.

The owner is an AI enthusiast, not a decompilation engineer. Explanations should
carry the reasoning, not just the conclusion.

## 2. Standing constraints

These are absolute. Each exists because breaking it cost real work.

1. **Never run git for this repo in a sandbox shell.** All git goes through the
   `sotn-cmd` connector. A 45-second sandbox cap killed a rebase mid-flight and
   left a `.git/index.lock` that corrupted the tree.
2. **Do not use the sandbox for this project at all.** It times out, and its
   results describe a different machine than the one that builds.
3. **Stage explicit paths.** `git_add` one file or one coherent directory at a
   time. A directory is explicit only when every change beneath it belongs to
   the same task. `git_add_all` sweeps harness scratch into commits. It is
   permitted only by an explicit, batch-specific owner instruction, and that
   permission expires with that batch. Never carry it into a later follow-up.
4. **Push to `origin` only.**
5. **Never rewrite a document wholesale without being asked.** The markdown files
   in this repository have no backup. Revise in place, surgically.
6. **No record is ever removed from scope.** Queue records and roadmap tasks get
   re-scoped, superseded or marked void. They do not get deleted.
7. **Subagents never build.** Builds take an exclusive BuildLock; a subagent
   build corrupts the lock state for the session that owns it.
8. **No em dashes and no emojis**, in code, comments, commits or documents.
9. **Verify before claiming.** A match is `verify_build` returning every expected checksum and
   nothing else.
10. **Archive before replacement.** Superseded plans, prompts and records move
    under `docs/archive/`; they are evidence and are not silently deleted.
11. **Vendor intentional dependency divergence when practical.** This fork does
    not prepare pull requests for submodules. External repositories are
    reference corpora and dependency sources, not contribution targets.
12. **Long actions are jobs.** Use `job_start` and poll `job_status`. Never
    call a known long action synchronously or retry it blindly after a transport
    timeout. First determine whether the original process is still running.
13. **Every push gets a fresh, exact pre-push gate.** After the final commit or
    amend: require a clean `git_state`; audit the exact commit paths without
    relying on truncated output; run `make_build -> verify_build`; start
    `git_push` through `job_start`; poll it to completion; and confirm the
    branch is no longer ahead. Prior proof is not a substitute.
14. **A push audit includes generated evidence.** Inspect top-level paths and
    each touched generated store. Explicitly reject build output, `ctx*`,
    `*.m2c`, caches, debug objects, local agent state, and work directories.
15. **Do not multiply validation without a state change.** Run the focused
    regression after an edit and each required consolidated suite once before
    landing. Do not repeat full analysis, builds or checksum-oracle calls when
    the source or build inputs they validate have not changed. A clean,
    just-completed post-push oracle remains the baseline for later
    automation-only work; do not re-run it at that work's start. The sole
    no-state-change exception is the mandatory fresh pre-push build and oracle
    immediately before an actual push.
16. **Interpret overrides narrowly.** A command-specific or batch-specific
    instruction changes only that operation unless the owner explicitly states
    a new general policy. Never turn an exception into a standing workflow.
17. **Persist process failures as controls.** When the owner identifies an agent
    failure, record the violated rule here or beside the affected tool and add
    an automated refusal or regression test where practical. Do not answer with
    agreement or reassurance in place of a durable correction.
18. **Do not interrupt active subagents for progress.** A missed checkpoint or
    absence of file writes during reasoning is not evidence of a stall. Interrupt
    only when concrete evidence shows repeated looping, inactivity beyond the
    expected duration of the active operation, scope violation, or unsafe action.
    Prefer non-interrupting messages and waiting for completion.
19. **Report collaboration state from evidence only.** Collaboration mailbox
    delivery state is not proof that a subagent did or did not reply or reach a
    response boundary. Never infer or report UI-visible worker state from an
    absent mailbox event. State only what the collaboration tool actually
    returned. If the owner reports a visible reply that the root agent cannot
    see, retract unsupported claims and request redelivery.
20. **The lead owns planning and orchestration.** Do not delegate document
    updates, planning, orchestration, coordination, or lead review to subagents.
    Subagents are reserved for substantive implementation work that the owner
    explicitly authorizes for delegation.
21. **Generated commit evidence never consumes unrelated dirty state.** The
    commit-time living-document sync runs only when the worktree holds no
    unrelated unstaged tracked or nonignored untracked paths; otherwise it
    defers and stages nothing, and generated output from a raced generator
    pass is never swept into a caller's commit. The lead owns living-document
    edits, including any deferred generator output.

## 3. Where everything is

| you want | read |
|---|---|
| the current plan, and every task ever opened | `ROADMAP.md` |
| which tool to call, and when not to | `docs/TOOLING.md` |
| how the connectors work and how to install them anywhere | `docs/CONNECTORS.md` |
| what has already gone wrong, and why | `MATCHING-LESSONS.md` |
| how the harness is built | `docs/HARNESS-ARCHITECTURE.md` |
| how to drive the harness day to day | `docs/harness-control.md`, `automation/README.md` |
| how to dispatch work | `ORCHESTRATOR.md` |
| naming and style rules for C in this tree | `docs/NAMING.md`, `docs/STYLE.md` |
| project status and framing | `README.md` |

`MATCHING-LESSONS.md` is long and it is worth it. Nearly every expensive mistake
in this project is a repeat of one recorded there.

## 4. The roadmap is not optional reading, and it is not read-only

`ROADMAP.md` is the single scope-of-record. It carries **every task, completed
and pending**, in a numbered ledger, plus the priority sections (P0 through P6)
that explain the current direction.

You are required to:

- **Read it before starting work.** The task you are about to do may already
  have a record, a prior attempt, and a recorded reason it was parked.
- **Update it when you finish anything.** Add the task if it is new. Change its
  status if it moved. Write one line of outcome, not one line of intent.
- **Retract wrong entries explicitly.** If a ledger line records a diagnosis that
  turned out to be false, mark it retracted and say what the real cause was.
  Silently correcting it destroys the evidence that the first diagnosis was
  plausible, which is the part worth keeping.
- **Never delete a line.** Supersede it. See constraint 6.

The same discipline applies to queue records: `queue_report` with
`keep_note=True` and a real `proof` string. Thirty-five matched records already
lost their method note to a build receipt overwriting the notes field, and that
is not recoverable.

## 5. How to work here

### Starting

```
list_allowed          what this connector can actually do
git_state             branch, HEAD, upstream, dirty summary
verify_build          is the complete baseline green before you touch anything
```

If `verify_build` is not completely green at the start, stop and find out why. Do not build
on a red tree.

### Landing a match

```
make_build  ->  verify_build          in that order, always
queue_report(..., proof=..., keep_note=True)
git_add <explicit path>  ->  git_commit  ->  git_push
```

`verify_build` hashes what is on disk, so build immediately before verifying.

### Making a checkpoint

```
queue_snapshot                        the queue is NOT in the repo
git_add automation/queue/snapshots/<the file it printed>
git_commit
git_checkout_branch("backup-<short hash>", create=True)  ->  git_push
git_checkout_branch("master")
```

A branch alone protects `src/` and the docs and **not** the queue, which lives
outside the repo on purpose. Skipping the snapshot gives you a checkpoint that
restores the code without the record of how it was produced.

Here, a checkpoint means a deliberate backup or recovery boundary, not every
ordinary commit. Take one queue snapshot for the whole recovery batch. Do not
take one after each `queue_report`, function match, source commit, or push. See
`automation/queue/snapshots/README.md` for the canonical frequency rule.

### The order to try things

Cheapest first. Every step below is free or nearly free compared to the one
after it:

1. **Is it already decompiled somewhere?** `upstream_harvest.py`,
   `asm_twin_finder.py`. Roughly half of what remains exists elsewhere.
2. **Can a shared header retire several stubs at once?** `shim_sweep.py`. One
   shim has landed a dozen functions for a few minutes of segment work.
3. **Can a twin body be moved in mechanically?** `transplant.py`.
4. **Derive it by hand from the assembly.** Slow, but it produces the lessons.
5. **Model fleet.** Roughly ten minutes of wall clock per attempt and nothing to
   show for it most of the time.
6. **Permuter.** Hours of CPU, and it only mutates expressions; it cannot find a
   structural error.

Reaching for step 5 or 6 before exhausting 1 through 4 is the most common way to
waste a session here.

### Writing C

Read `docs/STYLE.md` and `docs/NAMING.md`. Beyond those:

- **Named constants, never magic numbers**, when the name exists. The toolchain
  compiles an undeclared identifier as `0` at `-w` **with no diagnostic**, so a
  misspelled enum constant is silent until the checksum catches it.
- **Real struct members, never raw byte-pointer casts.** If an offset falls
  inside a union, find the variant that names it; `member_types.py` and
  `ext_demand.py` answer this.
- **Explain the reasoning in comments**, especially where the code looks odd.
  The odd shapes are usually load-bearing, and the next reader is an agent with
  no memory of this session.

## 6. Recording what you learn

A finding is worth more than a match. When something surprises you, write it
where the next agent will hit it:

- A compiler or toolchain behaviour goes in `MATCHING-LESSONS.md`.
- A harness or tooling behaviour goes in `docs/TOOLING.md` or
  `docs/CONNECTORS.md`, next to the tool it concerns.
- A task outcome goes in the `ROADMAP.md` ledger.
- A per-function derivation goes in the queue record's note.

Write down the wrong turn as well as the right one. "This looked like a
scheduling difference and was actually a dispatch-form difference" is more
useful than the fix alone, because the next reader will make the same first
guess.

## 7. Before you finish

```
python3 automation/test_connector_surfaces.py     # after touching automation/mcp/
python3 automation/run_selftests.py               # after touching automation/
make_build -> verify_build                        # always
```

Then update `ROADMAP.md`, commit with explicit paths, run the complete pre-push
gate in constraint 13, and push to `origin` only through the background job.
