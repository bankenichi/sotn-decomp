# Rejected candidate evidence

This directory contains generated C bodies that failed compilation or the
pre-build review gate. They are retained because the failure and attempted
shape can prevent a full model retry after declarations, members, or other
blocking context become known.

Rejected bodies are not permuter seeds until they compile. Each save first
creates an immutable `history/<record>.vNNNN.c` generation, then atomically
refreshes the stable top-level `<record>.c` current view. The queue's
`rejected=` field names the exact immutable generation.

On the first versioned save, any legacy top-level rejection is copied
byte-for-byte into history before replacement. The root agent stages both the
new immutable generation and the changed stable view by explicit path in the
same work batch that records the outcome.
