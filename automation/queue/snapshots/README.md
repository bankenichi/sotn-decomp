# Queue snapshots

Point-in-time copies of the live work queue, committed so a git checkpoint can
restore not just the source but the record of how it was produced.

## Why this directory exists

The live queue is at `~/sotn-work/queue.jsonl`, **outside the repo**, and that
is deliberate. Every scheduler transaction rewrites it through `os.replace`,
producing a fresh inode, hundreds of times per fleet session. On 2026-07-20 a
cloud sync daemon lost that race: it renamed the live file to
`queue (# Name clash 2026-07-20 8288wiC #).jsonl` and left a zero-byte
`queue.jsonl` behind, and all 438 records vanished from the harness's view. The
wreckage is still in `work/` as an untracked reminder. Moving the hot file to
WSL-native storage removed the daemon from the picture.

That decision answered *where the hot file should live*. It never answered
*what backs it up*, and until 2026-08-17 the answer was nothing. The queue
carries every derivation, every retraction, every proof string and every method
note behind the matched records. A backup branch protected `src/` and the docs
and left all of that on one disk with no history.

A snapshot resolves it without reopening the sync race. The hot file stays
where it is; a copy is written here **once, on demand, and never rewritten**, so
there is no race for a daemon to lose.

## Using it

```
queue_snapshot                      # or: python3 automation/scheduler.py snapshot
git_add automation/queue/snapshots/<the file it printed>
git_commit
```

Take one **once per deliberate recovery batch**, immediately before creating
its backup branch or other intentional recovery point. In this directory,
"checkpoint" does not mean every ordinary commit.

Do not take a snapshot after each `queue_report`, each function match, or each
ordinary source commit or push. Coalesce all queue changes from a work batch
into one snapshot. Take an additional snapshot in the same session only before
a manual bulk or destructive queue operation that does not already create its
own safety copy. Do not create another snapshot when the queue has not changed.

This gives a recovery point that restores both code and reasoning without
turning the full queue into per-report history. Queue history belongs in
the records themselves; snapshots are disaster-recovery artifacts.

Restoring:

```
queue_restore(from_file="automation/queue/snapshots/<file>", confirm=True)
```

`queue_restore` validates every line before touching anything, refuses without
`confirm`, and writes a `pre-restore` snapshot of what it is about to replace,
so the restore itself is reversible. **Stop the fleet first**: restoring under
running workers replaces the records they hold claims on.

## Naming

    queue.<UTC stamp>.<HEAD short hash>.jsonl     a deliberate snapshot
    queue.<UTC stamp>.pre-restore.jsonl           written automatically by restore

The HEAD hash is what makes a snapshot useful rather than merely present: it
says which commit's tree this queue state describes. A snapshot whose hash you
cannot match to a commit is a set of records with no idea what they refer to.

## These are checkpoints, not history

A snapshot is stale the moment the next `queue_report` lands. Do not read one to
answer "what is the queue doing" -- use `queue_stats` and `queue_list`, which
read the live file. These exist for one purpose: getting back to a known state
after something went wrong.
