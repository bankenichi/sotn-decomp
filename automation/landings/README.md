# Verified landing evidence

This directory contains append-only snapshots of replacement blocks that passed
the complete 81/81 oracle in a worker before the matching source was committed.

The snapshot closes the unsafe interval between queue reporting and root-owned
Git landing. A source restore cannot erase it, and the queue note identifies its
path. It is recovery evidence, not another source file compiled by the build.

For every new snapshot, the root agent must:

1. verify that its queue record is `matched` and names the snapshot;
2. review and stage the corresponding `src/` path explicitly;
3. stage the snapshot explicitly in the same work batch;
4. retain it after the source commit.

A later snapshot for the same record receives a numeric suffix. Existing
snapshots are never overwritten or deleted.
