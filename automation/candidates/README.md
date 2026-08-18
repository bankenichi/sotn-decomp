# Candidate evidence

This directory contains compiling C bodies that do not yet match the target.
They are durable evidence and potential permuter or model-review seeds, not
scratch output.

Every candidate must identify its queue record and measured outcome in its
header. Each save first creates an immutable
`history/<record>.vNNNN.c` generation, then atomically refreshes the stable
top-level `<record>.c` current view. The queue's `seed=` field names the exact
immutable generation. The supervisor's non-recursive top-level scan sees only
the stable current view and does not mistake history for additional work.
When reconciliation finds a stable current seed, it records the byte-identical
immutable generation when one exists and otherwise retains the legacy stable
path.

On the first versioned save, any legacy top-level candidate is copied
byte-for-byte into history before replacement. The root agent stages both the
new immutable generation and the changed stable view by explicit path in the
same work batch. A candidate is never applied to `src/` merely because it
compiles or has a low isolated score.

Per-run compiler artifacts belong under the owned permuter work directory and
are not stored here.
