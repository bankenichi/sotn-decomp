# Evaluated Candidate Seed Handoff Implementation Plan

**Goal:** Close roadmap #299 by feeding actually measured programmatic candidates
into subsequent permuter tasks, with deterministic archived recovery.

**Architecture:** Keep immutable factory inputs intact. At a permuter task's
scheduled ledger boundary, derive a task-local input from earlier successful
nonzero evaluations, ordered by score then candidate and measurement identity.
Archive the selection, exact source and measurement reference before dispatch.
Reconstruction rederives that selection from the same ledger prefix. No live
queue, mutable best-file lookup or provider-state replacement is involved.

**Constraints:** US only; implementation and fixture execution only; no live
matching, candidate landing, models or delegation. Git and build jobs retain
their existing authorities. Preserve historical gates and factory evidence.

## Deliverable and checks

- Add `automation/search_seed_handoff.py` with `bind_task_provider(provider,
  task, events)` and `validate_seed_handoffs(manifest, archive, events)`. A
  content-addressed decision includes the scheduled event hash, frozen input,
  selected candidate, exact successful evaluation receipt and derived input.
- Bind the module in factory core evidence. Historical archives may omit the
  new binding; current runtime reconstruction must require current identities.
- Let `PermuterLaneProvider` consume a task-local input while keeping factory
  serialization unchanged. Carry handoff provenance and the selected parent
  through its ordinary discovery callback.
- Bind concrete providers in the supervisor after scheduling and before
  dispatch. Validate archived decisions and request consumption during recovery.
- Extend existing evaluator/provider fixtures: prove different measured source
  reaches the concrete worker, fallback without an eligible measurement,
  deterministic tie selection, restart without recompilation, exact source
  preservation, and refusal of corrupt or conflicting handoff evidence.
- Run focused checks, one consolidated self-test suite, update #299 and tooling,
  then audit explicit committed paths and run the fresh build/oracle/push gate.

The alternative of changing the provider's frozen input map would invalidate
factory identity and make recovery depend on mutable state. A task-local input
preserves that authority while binding each worker session to its actual seed.

## September 14 outcome

Implemented and wired through the production factory, concrete permuter provider,
supervisor, ordinary candidate receipts and offline recovery. Fixtures prove exact
measured source reaches the worker's base.c after interruption, tied-score
selection is stable, fallback retains the original seed, and corrupt or conflicting
decisions refuse. New output records its selected parent; existing-source
convergence retains consumed-seed provenance without a graph back-edge.

Consolidated run_automation-072503-8358 passed 100/108 suites. The eight affected
rechecks passed in run_automation-124252-15237 and run_automation-124319-15237.
Corrections covered the shared fixture's new dependency, content-addressed
filename verification and static tracking of task-local adapter copies/updates.
The recovery guard also distinguishes worker tasks from candidate child tasks.

The historical gate and indexed-runtime checks pass. No donor index or renderer
inputs changed, so the already published switch runtime remains applicable.
No live matching, queue writes or candidate landing occurred. Exact commit-path
audit and the fresh build/checksum/push gate follow.
