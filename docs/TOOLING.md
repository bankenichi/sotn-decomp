# Tooling reference: what to call, and when

Every tool the `sotn-cmd` connector exposes, and every analysis script it can
run, with the thing that actually matters: **when to reach for it and when not
to.** For how the connectors are built and installed, read `docs/CONNECTORS.md`.
For the mechanisms that land matches, read `automation/README.md`.

`list_allowed` is the live answer to "what exists". This document is the live
answer to "which one do I want". If the two disagree, `list_allowed` wins and
this file is stale; `automation/test_connector_surfaces.py` fails when a tool
named here does not exist.

---

## The shape of a session

```
git_state                     where am I, is the tree clean
verify_build                  is the baseline still 81/81
  ... do the work ...
make_build  ->  verify_build   the oracle, in that order, always
queue_report                  record the outcome with proof
git_add (explicit paths)  ->  git_commit  ->  git_push
```

Four rules that are not negotiable, each because breaking them has cost a day:

1. **`verify_build` hashes what is on disk.** Always `make_build` immediately
   before verifying. A stale tree verifies green and tells you nothing.
2. **Stage explicit paths.** The harness writes constantly. `git_add_all` sweeps
   its scratch output into your commit.
3. **Never run git for this repo in a sandbox shell.** It goes through the
   connector only. A 45-second cap killed a rebase mid-flight once and left a
   `.git/index.lock` that corrupted the tree.
4. **Long actions go through `job_start`, not a bigger timeout.** A call that
   outlives its transport reports a stale result.

---

## 1. Build and the oracle

| tool | when to call it | when NOT to |
|---|---|---|
| `make_build` | after every source edit, before verifying | never from a subagent; builds are exclusive and take the BuildLock |
| `verify_build` | immediately after `make_build`, every time | not on its own to "check state"; it hashes disk, not source |
| `make_extract` | after changing a splat config | expecting it to refresh `nonmatchings/*.s`; **it does not rewrite existing stubs**, so renaming a symbol an asm stub references still breaks the link |
| `make_expected` | only when deliberately re-baselining | ever, casually. It redefines the oracle |
| `make_clean` | when artefacts are suspected stale | as a reflex; a full rebuild is minutes |
| `make_force_symbols` | after a green build, to harvest symbol names | on a red build; the names will be wrong |
| `make_function_finder` | surveying decomp status and call graphs | for per-function work; use the index |
| `make_reports` | duplicates report plus function finder in one pass | mid-session; it is slow |
| `make_duplicates_report` | hunting private copies of shared code | as evidence on its own; confirm with `asm_twin_finder.py` |

`verify_build` is **the** oracle: 81 SHA-1s in `config/check.us.sha`. Nothing
else in this repository is authoritative. A permuter score of 0, a clean
`asm_diff`, a confident model, a green compile: none of them are a match until
`verify_build` says 81/81.

## 2. Diagnosing a miss

Reach for these in this order. Each is cheaper than the one after it, and each
answers a different question.

| tool | the question it answers |
|---|---|
| `asm_diff` | *what* differs, instruction by instruction. Needs the overlay, not just the symbol |
| `permuter` with `debug=True` | how far off is the base, scored in seconds, no search |
| `permuter_import` | build a work dir from a seed so the permuter can search it |
| `permuter` | search the space. Hours. `-j` defaults to 1 |
| `run_analysis` | everything else; see section 6 |

**Read the side-by-side, not the score.** Permuter scores are inflated by symbol
naming alone: `PLAYER_posX_i_hi` against `g_Entities+2`, `g_api_PlaySfx` against
`g_api+0x68`, `jtbl_us_*` against `.rodata`. A function has scored 50 on naming
artefacts and still matched byte for byte. Conversely a score of 0 is an
isolated-compile result only, and `func_us_801CFD70` sits at 0 with the overlay
checksum still wrong.

**Before blaming the scheduler, check the dispatch form.** If a body links but
the overlay is short by roughly the size of a jump table, the switch compiled to
a compare chain. Empty cases at the ends of the case range restore the table,
and the table's own extent tells you where they go. `relocation_check.py` will
only say SIZE; `asm_diff` shows it immediately.

## 3. The queue

The live queue is `~/sotn-work/queue.jsonl`, resolved through `$HOME`, **outside
the repo**. `work/queue.jsonl` inside the repo is a stale legacy snapshot;
grepping it once produced a confident and completely false "18 functions are
invisible to the harness".

| tool | when to call it | notes |
|---|---|---|
| `queue_stats` | start of a session, to see the shape | counts by status |
| `queue_list` | find records; filter by `status` | output is long, filter it |
| `queue_report` | record an outcome | `proof` is **required** for `matched`. Pass `keep_note=True` or you overwrite the method note |
| `queue_annotate` | attach twin candidates from `automation/twins.us.json` | writes only the `twin` field, never status; re-running is a no-op |
| `queue_init` | seed a fresh queue from a seed file | destructive to ordering; not a routine action |
| `queue_prune` | drop records that are not real functions | **no record is ever removed from scope**; this is only for string labels and similar non-functions |

`queue_report` **replaces `notes` wholesale** unless you pass `keep_note`. That
is how 35 matched records lost the record of how they were solved and became
part of the 24% that `match_provenance.py` reports as unattributed. Not
recoverable for those records. Always pass the flag.

Status vocabulary: `todo`, `claimed`, `near` (compiles, bytes differ), `matched`,
`escalated` (a model produced something unusable), `deferred` (too large for the
tier, or the permuter exhausted itself).

## 4. Git

All of it goes through the connector. Push to `origin` only.

| tool | when to call it |
|---|---|
| `git_state` | first thing in a session: branch, HEAD, upstream, dirty summary in one call |
| `git_status` | the short listing |
| `git_add` | staging. **One explicit path per call.** This is the default |
| `git_add_all` | effectively never; it sweeps harness scratch into your commit |
| `git_commit` | landing work, with a message that explains the reasoning |
| `git_commit_amend` | fixing the message or adding a forgotten file to the tip |
| `git_push` | after verifying 81/81 |
| `git_fetch` | before comparing against upstream |
| `git_diff` | review before staging |
| `git_diff_stat` | scope of a change |
| `git_diff_stat_range` | what a range of commits touched |
| `git_log` | history |
| `git_log_range` | history between two revisions |
| `git_show` | one commit in full |
| `git_show_file` | a file's content at a revision |
| `git_ls_files` | what is tracked |
| `git_rev_parse` | resolve a revision to a hash |
| `git_branch_list` | list branches |
| `git_remote_list` | confirm you are about to push to `origin` |
| `git_config_get` | read a config value |
| `git_config_set` | set a config value |
| `git_checkout_branch` | switch branches |
| `git_checkout_path` | **adopt one path from a revision**, e.g. an upstream shared header. The harvest workhorse |
| `git_mv` | rename a tracked file. Refuses while a splat segment names the old stem |
| `git_rm` | delete a tracked file. Same guard |
| `git_rm_cached` | untrack without deleting, for scratch that got committed |
| `git_restore` | discard changes. Refuses on orphaned `src/` work |
| `git_restore_from_head` | restore a path from HEAD |
| `git_reset` | unstage, or move the branch |
| `git_clean` | remove untracked files. Read the dry run first |
| `git_stash_push` | park work |
| `git_stash_pop` | unpark it |
| `git_stash_list` | see what is parked |
| `git_merge_abort` | back out of a conflicted merge |
| `git_rebase_continue` | proceed through a rebase |
| `git_rebase_abort` | back out of a rebase |
| `git_cherry_pick_abort` | back out of a cherry-pick |

**On `git_checkout_path` and adoption:** a clean destination is recoverable but
not safe. Adopting `src/st/e_armor_lord.h` from upstream broke ARE's link on
contact, because the fork already carried an older copy that ARE and NO1 compile.
Check every consumer of a header before adopting it.

## 5. Long actions, the fleet, and jobs

| tool | when to call it |
|---|---|
| `job_start` | any action that might exceed a couple of minutes: builds, `permuter_supervisor`, big analyses |
| `job_status` | poll a job |
| `job_list` | see what is running |
| `job_cancel` | stop a job; it writes the exit sentinel so the job does not read as a crash |
| `fleet_start` | start N model workers. Backend defaults to `zen` |
| `fleet_status` | **read the log tails.** A stuck worker looks alive from the counters alone |
| `fleet_stop` | always, at the end. Releases claims, clears the lock, replays crash journals |
| `worker_once` | one worker iteration synchronously, for debugging the loop |
| `opencode_preflight` | before a fleet run, to fail a doomed configuration fast |

**Backend is `zen`, never `cli`.** The OpenCode CLI relays only `content`, and
the models worth running fill `reasoning_content` first, so through the CLI they
return empty roughly 94% of the time and worse on large contexts. Treating
`== "cli"` as a proxy for "big-context tier" is a recurring bug in this codebase.

`job_status.elapsed_s` **includes queue wait**. Jobs are exclusive. The same call
has measured 82s and 271s. It is not a runtime.

`permuter_supervisor.py`'s long modes must go through `job_start`. Run through
`run_analysis` its timeout kills it mid-lock, leaving a seed applied and a stale
build lock behind.

## 6. Analysis: `run_analysis`

`run_analysis` runs one read-only script from `commands_client.ANALYSIS_SCRIPTS`.
Pass a name that is not in the set and the error returns the full list, so **ask
by being wrong** rather than trusting any list, including this one. Every script
supports `--help` and most support `--self-test`.

### Finding work

| script | answers |
|---|---|
| `asm_twin_finder.py` | which unmatched stubs already exist elsewhere in the tree |
| `upstream_harvest.py` | what upstream has decompiled that we do not |
| `shim_sweep.py` | which shared headers could retire several stubs at once |
| `transplant.py` | move a twin body in mechanically |
| `codebase_index.py` | the searchable index of the whole tree |
| `queue_coverage.py` | does the queue cover what is actually in the tree |
| `decl_coverage.py` | are the declarations a candidate needs already reachable |
| `ext_demand.py` | which `Ext` union variants cover a set of offsets |
| `member_types.py` | is this struct member real, on **this** struct |
| `find_data_segment.py` | which splat `.data` address a symbol belongs to |

### Diagnosing

| script | answers |
|---|---|
| `asm_delta.py` | structured difference between two functions |
| `fn_diff.py` | one function against its twin |
| `relocation_check.py` | are the byte differences only a shifted relocation |
| `overlay_size_check.py` | is the overlay long or short, and is it text or bss |
| `orphan_check.py` | is there uncommitted `src/` work about to be destroyed |
| `permuter_stall.py` | has a permuter run stopped making progress |
| `permuter_promote.py` | promote a better permuter result to the seed |
| `opencode_size_bisect.py` | at what prompt size a provider starts failing |
| `probe_provider.py` | is a backend reachable and does it return content |

### Auditing

| script | answers |
|---|---|
| `matched_audit.py` | is every record marked matched actually present in the tree |
| `match_provenance.py` | which mechanism produced each match; `--no-git` is much faster |
| `provenance_check.py` | how close a body is to upstream's |
| `quality_audit.py` | fake symbols, magic numbers, raw byte casts, duplicates |
| `review_checks.py` | the gate the worker runs before building |
| `decomp_fidelity.py` | callee recall and constant coverage against the asm |
| `escalation_triage.py` | why each escalated record failed |
| `deferred_triage.py` | why each deferred record was deferred, and whether it still holds |
| `empty_response_audit.py` | dead-call rate per model. Reads current logs only unless you pass `--archived` |
| `fleet_forensics.py` | what a fleet run actually did |
| `reasoning_audit.py` | reasoning-effort A/B results |
| `quality_ab.py` | quality comparison between two configurations |
| `progress_table.py` | per-overlay completion from the linker maps |
| `readme_status.py` | regenerates the README status tables and prose |
| `queue_coverage.py` | queue against tree |

### Maintenance and self-test

| script | answers |
|---|---|
| `run_selftests.py` | runs every `test_*.py` and prints one table |
| `fix_seed_declarations.py` | retrofit missing declarations into permuter seeds |
| `permuter_supervisor.py` | the auto-queueing permuter driver. **Use `job_start`** |
| `test_connector_surfaces.py` | REGISTRY vs decorators vs manifest, plus portability and doc checks |

The remaining `test_*.py` scripts are all callable through `run_analysis` and
each explains itself when run. `run_selftests.py` is the one to reach for.

## 7. Scoped filesystem

| tool | when to call it |
|---|---|
| `read_file` | read an in-repo text file |
| `write_file` | overwrite or create an in-repo text file; respects dry-run |
| `list_dir` | list an in-repo directory |
| `search_repo` | search the tree. **Pass `regex=True` for alternation**; without it the pattern is literal and an alternation silently matches nothing |

All four are confined to the repository and refuse paths inside `.git`.

## 8. Packaging

| tool | when to call it |
|---|---|
| `mcpb_info` | inspect a built `.mcpb` bundle |
| `mcpb_validate` | validate a bundle manifest against the schema. It checks the manifest only, never the archive contents |
| `mcpb_pack` | pack a bundle directory into an `.mcpb` |

Only relevant to Claude Desktop packaging. See `docs/CONNECTORS.md` section 1.

## 9. Introspection

| tool | when to call it |
|---|---|
| `list_allowed` | first call in an unfamiliar session. Returns the shell allowlist, the callable tool surface, and the dry-run state, and says which is which |

A name present in one surface and absent from the other is a **wiring bug, not a
capability**. `list_allowed` reports both precisely so that reading it cannot
look like confirmation when it is not.
