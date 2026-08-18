# Candidate evidence

This directory contains compiling C bodies that do not yet match the target.
They are durable evidence and potential permuter or model-review seeds, not
scratch output.

Every candidate must identify its queue record and measured outcome in its
header. The root agent reports that outcome to the queue, stages the candidate
by explicit path, and commits it in the same work batch. A candidate is never
applied to `src/` merely because it compiles or has a low isolated score.

Per-run compiler artifacts belong under the owned permuter work directory and
are not stored here.
