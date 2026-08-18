# Verified landing preservation design

Date: 2026-08-18
Status: approved for implementation by the owner's instruction to proceed in the
recommended order

## Problem

A worker records `matched` immediately after the oracle accepts a candidate,
while the matching body still exists only in the working tree. Five verified
matches were previously lost because they were never committed. The queue kept
their proof, but not the C that produced it.

The existing controls detect this state:

- `orphan_check.py` identifies unexplained source changes.
- connector restore actions refuse unjournalled dirty source by default.
- `fleet_stop` runs `matched_audit.py` and reports uncommitted matches.

Detection is necessary and still leaves the only copy of a verified body in
`src/` until the root agent lands it.

## Requirements

1. Preserve the exact replacement block before the queue can say `matched`.
2. Preserve the complete oracle proof without a character cap.
3. Never let a worker commit, stage, restore, or otherwise own Git history.
4. Never keep a successful undo journal that could replay the old stub.
5. Make every saved body visible to ordinary Git status and subject to explicit
   root staging.
6. Do not overwrite an earlier landing snapshot.
7. If preservation fails, restore the source and do not create a matched record.

## Considered approaches

### Worker auto-commit

Rejected. A worker does not know the intended commit boundary, may share a file
with other work, and cannot safely own Git. Git remains a root-only operation.

### Retain or repurpose the undo journal

Rejected. The journal's contract is to restore the pre-edit file after a crash.
Keeping it after success risks replaying the old `INCLUDE_ASM` stub over a real
match. Changing that contract would make recovery depend on interpreting two
opposite journal meanings.

### Append-only verified landing snapshot

Selected. Before reporting `matched`, the worker saves the exact block that
replaced the stub under `automation/landings/`. The snapshot records the queue
id, source path, assembly path, model, attempt, and full proof. It is outside
`src/`, so restoring a source path cannot erase it, and it is not ignored, so
the root sees and stages it deliberately.

## Match transaction

While holding the existing build lock:

1. Apply the candidate and build.
2. Verify the whole-tree oracle.
3. Save an append-only landing snapshot.
4. If saving fails, raise before queue reporting. The existing exception path
   restores the original source and reports the failure.
5. Report `matched`, including the snapshot path in the durable note.
6. Clear the undo journal.
7. Leave the matching source in the working tree for the root to review, stage,
   commit, and push.

A crash after step 3 leaves the body in the landing snapshot. A crash after step
5 leaves both queue proof and the snapshot. A crash before step 3 remains covered
by the existing undo journal.

## Artifact contract

The base path is `automation/landings/<queue-id-slug>.c`. If it already exists,
the writer chooses the next numeric suffix and never overwrites it.

Each file contains a comment header followed by the exact declaration injection
and function body used for the verified replacement. It is recovery evidence,
not an additional build source.

The directory README requires each snapshot to be:

- referenced by its queue record;
- staged explicitly with the corresponding source landing;
- retained after the source commit as proof of the pre-commit transaction;
- superseded by a later numbered snapshot, never replaced.

## Verification

A focused regression must prove:

- full proof text survives beyond the old evidence limits;
- the payload contains the exact replacement block;
- a second save for the same record preserves the first file;
- the path is under `automation/landings/`, not an ignored directory;
- the match path saves before queue reporting and clears the journal only after
  reporting;
- a save failure prevents the matched report contract.

Then run the complete automation self-test suite, a managed US build, and the
81/81 oracle. No connector restart is required because this changes worker
behavior, not the MCP surface.
