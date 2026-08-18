# Versioned worker artifact design

Date: 2026-08-18
Roadmap: #161
Status: approved by the owner's standing archive-before-replacement policy and
instruction to proceed without routine approval stops

## Problem

`save_candidate()` and `save_rejected()` publish one stable path per queue
record with write mode `w`. A later attempt replaces the previous candidate or
rejection. That contradicts the repository rule that evidence is archived
before replacement.

The candidate path also has live consumers. Queue notes carry `seed=<path>`,
the permuter imports that path, and reconciliation scans only top-level
`automation/candidates/*.c`. A path change must preserve those contracts.

## Chosen design

Each artifact class keeps two views:

- `automation/<class>/<record>.c` is the stable current view used by top-level
  discovery and human inspection.
- `automation/<class>/history/<record>.vNNNN.c` is an immutable generation.

A shared publisher writes the immutable generation first, then atomically
refreshes the stable current view. The writer returns the immutable generation
path, so the queue note identifies the exact C associated with its verdict.

On the first replacement of a legacy stable file, the publisher preserves that
file byte-for-byte in `history/` before writing the new generation. It skips
that migration copy only when identical bytes are already present in history.

## Data flow

1. The candidate or rejection writer renders its complete header and C body in
   memory.
2. The publisher creates the next history file with exclusive-create semantics.
3. If a legacy current file is not already represented in history, it is
   archived first.
4. After the new immutable file exists, a same-directory temporary file is
   atomically replaced over the stable current path.
5. The writer returns the immutable path for `seed=` or `rejected=`.
6. The top-level current file remains available to reconciliation. The
   supervisor's non-recursive `*.c` scan ignores `history/`.

## Failure behavior

- If the legacy current file cannot be archived, the current file is not
  replaced and the writer reports save failure.
- If the new immutable generation cannot be written, the current file is not
  replaced and the writer reports save failure.
- If refreshing the stable view fails after the immutable generation exists,
  the writer returns the immutable path and reports that the stable view could
  not be refreshed. The generated evidence still survives and remains usable
  through its queue note.
- History files are never opened for overwrite and are never deleted by the
  publisher.

## Tests

Focused regressions cover both artifact classes:

- a second save receives a new immutable path;
- the first version remains byte-identical;
- the stable current file contains the newest generation;
- a pre-versioning legacy current file is preserved before replacement;
- candidate history remains outside the supervisor's top-level seed scan;
- the returned queue path names the immutable current generation.

## Documentation

The candidate and rejected directory contracts describe the stable view,
immutable history, exact queue paths, and explicit staging requirement. The
harness architecture removes the old overwrite behavior and records the
version-first publication order.
