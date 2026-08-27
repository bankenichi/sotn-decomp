# Instrumented Search System Design

Date: 2026-08-26
Roadmap: #274
Status: Draft for owner review

## 1. Decision

Build one recoverable search system around all candidate-producing lanes. The
system will combine deterministic discovery, structural repair, generated
candidates, compiler-guided mutation, recombination, minimization and bounded
synthesis. It will preserve every candidate and decision as evidence.

The design has two parts:

1. Typed instrumentation inside the vendored `tools/decomp-permuter`, so
   mutation events and full score vectors are observable at their source.
2. A central coordinator in `automation/`, so every lane uses the same
   archive, provenance, evaluation, frontier, budget and recovery rules.

This does not replace the full build oracle. An isolated score of zero only
makes a candidate eligible for the existing `make_build -> verify_build`
landing gate.

## 2. Problem

The current harness preserves useful seeds and can supervise isolated permuter
runs, but it cannot explain or reproduce the complete path by which a search
arrived at a candidate.

Current limits include:

- `CandidateResult` exposes a scalar score, object hash and source, but no
  score components or mutation lineage.
- `Randomizer.randomize` chooses among 34 passes and retries failures without
  returning a typed event.
- The scorer calculates stack, register allocation, reordering, insertion and
  deletion components internally, then discards the vector.
- Per-worker mutable continuation and integer-only caches make process state
  authoritative.
- Output directories contain source, score and diff files, but not a durable
  search history.
- The supervisor performs external stall and promotion cycles, but has no
  bounded Pareto frontier, candidate graph or exact recovery boundary.
- Mechanical lanes, m2c variants and structural evidence do not share a common
  exhaustion contract.

A historical case proves that scalar hill climbing is insufficient.
`func_us_801B001C` combined four independent score-70 sibling changes into a
score-10 candidate, then reached zero using a useful mutation found on a worse
score-80 sibling. The preserved files under
`nonmatchings/func_us_801B001C` show the final mutation was one atomic event
with two separated hunks: declaring `new_var`, then assigning through it in
case 1. The original permuter output directories no longer exist, so this is
incomplete historical evidence. Tests must reconstruct a synthetic fixture
from the preserved hypotheses and queue notes and must not claim the original
lineage was recovered.

## 3. Goals

The system must:

- reproduce any completed decision after a graceful stop or hard process loss;
- recover authoritative state from an append-only ledger and immutable
  artifacts alone;
- preserve full score vectors and mismatch signatures;
- represent every mutation as an atomic, replayable, grouped edit;
- search multiple candidate lineages without losing the scalar best candidate;
- recombine and minimize useful sibling mutations;
- keep mutation fitness local to the recipient candidate;
- run any lane against any explicit subset of eligible queue records;
- enforce mechanical and deterministic work before generated, fleet or
  expensive AI work;
- emit a durable exhaustion or refusal receipt for every lane skipped or
  completed;
- use all candidate-producing lanes through one coordinator;
- refuse an unsafe resume if source, target, compiler, tool, schema or
  configuration identity changed.

## 4. Non-goals

This system will not:

- weaken or replace `verify_build`;
- make workers authoritative for archive, frontier, budget or queue state;
- infer that a donor's score applies to a recipient;
- use global mutation rankings across unrelated functions;
- dynamically spawn mutable permuter instances;
- promise bit-identical wall-clock interleavings;
- delete queue records, roadmap tasks, failed candidates or superseded
  evidence;
- send a candidate directly into `src/` from an isolated score.

## 5. Architecture

The coordinator is the only authority for search state.

```text
queue subset
    |
    v
central coordinator
    |-- deterministic discovery lanes
    |-- structural and dependency lanes
    |-- generated candidate lanes
    |-- instrumented permuter lanes
    |
    v
immutable task -> stateless worker -> immutable result
    |
    v
candidate archive -> isolated evaluator -> decision ledger
    |
    +-- scalar elite
    +-- bounded Pareto frontier
    +-- recombination and minimization
    +-- exhaustion receipt
    |
    v
score zero candidate -> existing full build and checksum oracle
```

Workers receive immutable tasks and return results. They do not choose the next
task, own a budget, mutate a shared frontier or write authoritative state.
The coordinator commits concurrent results in deterministic task-ID order at
epoch boundaries.

## 6. Storage layout

Run data is intentionally outside tracked source artifacts but inside the
existing durable nonmatching evidence area:

```text
nonmatchings/<function>/search-runs/<run-id>/
    manifest.json
    ledger.jsonl
    artifacts/
        sources/<sha256>.c
        objects/<sha256>.o
        patches/<sha256>.json
        diffs/<sha256>.txt
        receipts/<sha256>.json
    checkpoints/
        <sequence>-<sha256>.json
```

Files under `artifacts/` are content addressed and immutable. A writer uses a
temporary sibling, flushes and closes it, atomically renames it into place, and
only then appends the ledger event that references it. A conflicting existing
artifact with the same identity is corruption, not an overwrite opportunity.

The tracked schema is `automation/search-ledger.schema.json`. The JSONL file
contains one schema-valid event per line.

## 7. Identity and determinism

A run manifest binds:

- repository source identity;
- target object identity;
- function and queue-record subset;
- compiler executable and arguments;
- tool identities, including vendored dependency revisions;
- configuration and schema hashes;
- run seed;
- frontier cap, epoch size and tier order.

Each task has a deterministic ID derived from the run identity, lane, recipient,
parents, operation, budget ordinal and configuration. Its random seed is
derived from the run seed and task ID. Retrying an incomplete task therefore
does not consume a second logical budget unit and produces the same requested
operation.

Logical reproducibility means the same inputs, task IDs and committed decisions
are recovered. It does not require the same worker completion timing.

## 8. Event envelope and integrity

Every event has:

- `schema_version`;
- monotonic `sequence`;
- deterministic `event_id`;
- `previous_event_hash`;
- `event_hash`;
- UTC `recorded_at`;
- `run_id`;
- `event_type`;
- a typed `payload`.

The event hash covers the canonical JSON form of the event without
`event_hash`. The first event has a null previous hash. Every later event
names the exact hash of its predecessor. Recovery rejects a gap, duplicate
sequence, broken hash chain, invalid payload or missing referenced artifact.

## 9. Core records

### 9.1 ScoreVector

A score vector records:

- compile status and elapsed time;
- weighted scalar total;
- raw stack, register-allocation, reordering, insertion and deletion counts;
- the weights used to calculate the total;
- target and candidate instruction counts;
- candidate object hash when compilation succeeds;
- stable mismatch signature;
- first divergence when available;
- diagnostic artifact when compilation fails.

The evaluator must return the vector it actually used. Recalculation with
different weights is a new evaluation event, not a rewrite.

### 9.2 MutationEvent

A mutation event records:

- mutation content ID;
- exact parent candidate hash;
- recipient candidate ID;
- lane, pass kind and deterministic seed;
- one canonical grouped patch containing every hunk from that operation;
- donor candidate IDs as provenance only;
- replay outcome and resulting source hash.

All hunks from one mutation are atomic. Partial application is prohibited.
For exact same-parent replay, the system retains pass plus mutation seed. For
portable recombination, it retains an AST-aware or canonical-token grouped
patch and applies it with three-way/context anchoring. Any conflict rejects the
whole mutation.

### 9.3 CandidateRecord

A candidate records immutable source identity, parent candidates, producing
mutation or lane, full evaluation, depth and lifecycle status. Candidate IDs
are content based. Identical source produced by multiple routes keeps one
artifact and multiple provenance events.

### 9.4 EvaluationEvent

An evaluation binds an exact recipient and candidate to its before and after
vectors, component deltas, object identity, mismatch signature and decision.
The cache key is `(recipient, candidate-or-mutation identity, evaluator
identity)`, never mutation identity alone.

### 9.5 ExhaustionReceipt

A receipt binds target, lane, input identities, tool and configuration hashes,
budget, attempt counts, rejection classes, best candidates and completion
reason. A skipped lane needs a refusal receipt naming the mechanical reason it
was inapplicable. Prose alone is not machine authority.

The exact structures and required fields are defined in
`automation/search-ledger.schema.json`.

## 10. Search and acceptance rules

All score dimensions are lower-is-better.

The coordinator always retains the scalar elite. It additionally retains a
bounded Pareto archive, initially configurable to 8 or 16 candidates, selected
by non-dominance plus mismatch-signature diversity. The cap is a run-manifest
field, so changing it forks a run.

A mutation's observed utility belongs only to the recipient candidate on which
it was measured. Donor score is never inherited. Candidate-local pass efficacy
may tune later pass selection for descendants of that candidate. Lane-level
aggregate yield may schedule queue records, but cannot transfer mutation
fitness between unrelated candidates.

Initial target-guided pass priors use residual evidence:

- reordering residuals favor reorder passes;
- register-allocation residuals favor temporary, type and reference-shape
  passes;
- stack residuals favor declaration, padding and type-layout passes;
- insertion and deletion residuals favor expression and control-shape passes.

These are priors, not gates. Candidate-local measurements may refine them.

An improvement can enter bounded delta debugging. Minimization removes mutation
groups or patch hunks only when the configured preservation condition holds:
the same object hash, the same full score vector or no worse scalar score.
The condition is part of the task identity.

Legacy candidate output with a known common ancestor may be converted into
grouped edits and minimized. Unknown ancestry is never fabricated.

## 11. Candidate-producing lanes

All lanes use the same task, candidate, evaluation and receipt contracts.

### Tier 1: exact and deterministic discovery

1. Current upstream and pinned known-good references.
2. Open upstream pull-request refs when explicitly configured and fetched.
3. Existing `upstream_harvest.py` and `asm_twin_finder.py`.
4. Queue-facing `mipsmatch` exact fingerprint and body mining.
5. Existing preserved candidates and landing evidence.

The mipsmatch lane must reconcile with the existing exact-copy provenance
classifier so the same discovery is not counted twice.

### Tier 2: structural and dependency closure

1. Shared-header and shim analysis.
2. Existing transplant.
3. Whole-translation-unit closure.
4. Missing declaration, type, data and segment dependency closure.
5. Multi-donor triangulation.
6. CFG and dataflow signature matching.

These lanes may produce source candidates or typed refusal evidence.

### Tier 3: cheap generated candidates

1. An m2c ensemble over the tool's supported switches, including stack
   structures, pass selection, goto-only, switch and and/or forms, stack spill,
   register variables, deterministic variable naming and multiple contexts.
2. Compiler idiom atlas substitutions.
3. Bounded synthesis for small residual regions.

The current worker's single `m2c --target mipsel-gcc-c` draft is one ensemble
member, not the full lane.

### Tier 4: compiler-guided search

1. Independent deterministic mutation tasks.
2. Target-guided pass scheduling.
3. Bounded Pareto exploration.
4. Sibling mutation recombination.
5. Improvement minimization and pruning.
6. Algorithm variants such as difflib and Levenshtein when the scorer identity
   records the choice.

This tier incorporates the useful intent of upstream decomp-permuter issues
[154](https://github.com/simonlindholm/decomp-permuter/issues/154) and
[155](https://github.com/simonlindholm/decomp-permuter/issues/155). It does not
adopt the mutable dynamic-spawning design in draft pull request
[158](https://github.com/simonlindholm/decomp-permuter/pull/158), whose recorded
race, slowdown and p-at-h concerns conflict with this coordinator model.

### Tier 5: model work

1. Cheap fleet workers with thinking enabled when the run configuration calls
   for the controlled comparison requested by the owner.
2. Expensive AI only after lower tiers have complete receipts.

The tier order is a hard scheduling constraint. Yield measurements may choose
within a tier, never jump over an incomplete cheaper tier.

## 12. Stop, crash and resume protocol

### Graceful stop

The coordinator stops scheduling, waits only for the configured bounded
commit boundary, commits completed results in task-ID order, records pending
tasks and appends `run_stopped`. Resume starts at the next uncommitted task.

### Hard process loss

On startup, recovery:

1. validates the manifest and hash chain;
2. validates every referenced immutable artifact;
3. reconstructs candidate graph, evaluations, cache, scalar elite, Pareto
   frontier, budgets and task states entirely from the ledger;
4. treats a scheduled or started task without a terminal event as incomplete;
5. reissues that same task ID and seed without charging budget again;
6. ignores a checkpoint unless its ledger prefix and checksum validate.

Workers own no recovery state. A result artifact without its ledger event is
uncommitted and may be reused only after validating it against the reissued
task. A ledger event cannot reference an artifact that was not durably
materialized first.

### Changed inputs

Resume refuses if any source, target, compiler, tool, config or schema hash
differs from the manifest. The operator may explicitly fork a new run. The fork
records the parent run and last valid sequence and leaves the original
immutable.

## 13. Checkpoints

A checkpoint is a checksummed materialized view of a known ledger prefix. It
may accelerate recovery but is never authoritative. Deleting every checkpoint
must leave full recovery possible.

The coordinator writes a checkpoint only after the referenced ledger event is
durable. It records the ledger sequence and hash from which it was derived.

## 14. Queue subset and ownership rules

Every run receives an explicit set of queue record IDs. No worker may claim or
read work from another queue state as a fallback. Eligibility is evaluated
before task creation. The manifest preserves the exact subset.

The coordinator does not hand-edit the queue. When a lane or full run
completes, the scheduler remains the single queue writer and receives a
summary that references immutable receipts. Existing notes are preserved.

## 15. Testing and acceptance

### Schema and integrity

- validate representative event fixtures;
- reject unknown fields and invalid event payloads;
- reject a broken previous-event hash;
- reject missing or corrupt artifacts;
- prove content-address collision handling is a refusal.

### Recovery equivalence

A fault-injection harness kills the coordinator after every durable transition.
Each resumed run must produce the same committed task IDs, candidate graph,
evaluations, budgets, scalar elite, Pareto frontier and terminal receipts as an
uninterrupted reference run.

The harness covers:

- kill before and after artifact rename;
- kill before and after ledger append;
- kill during an epoch with out-of-order worker completion;
- kill during checkpoint write;
- duplicate result delivery;
- graceful stop with pending tasks;
- changed-input resume refusal and explicit fork.

### Historical search fixture

Using the preserved `func_us_801B001C` hypotheses:

- represent the four sibling contributions independently;
- recombine them into the preserved score-10 form;
- represent the declaration and case-1 assignment as one two-hunk mutation;
- prove partial application is rejected;
- prove the worse sibling may donate a useful mutation without donating score;
- prove scalar elite retention and Pareto diversity both survive the sequence.

### Integration

- compare the instrumented scorer's scalar total with the pre-change scorer on
  a fixed corpus;
- replay each supported permuter pass from its recorded seed;
- run each lane against an explicit one-record and multi-record subset;
- prove workers never claim from another queue state;
- prove score zero routes to the existing full oracle rather than landing;
- prove every completed or skipped lane emits a receipt.

## 16. Rollout

1. Land the schema, ledger primitives and recovery tests.
2. Instrument scorer and randomizer without changing search behavior.
3. Add immutable archive, deterministic tasks and central coordinator.
4. Add scalar elite, bounded Pareto archive, recombination and minimization.
5. Adapt existing deterministic and structural lanes.
6. Add mipsmatch queue integration and exact-copy reconciliation.
7. Add the m2c ensemble, idiom atlas and bounded synthesis.
8. Wire subset execution, supervisor and connector surfaces.
9. Run the synthetic historical fixture and a small shadow corpus.
10. Enable queue-state changes only after shadow results and root review.

Existing roadmap tasks remain evidence. They may be marked superseded or
re-scoped after the new instrumentation measures their actual coverage, but
they are never deleted.

## 17. Rejected alternatives

- External log scraping only: cannot reliably recover typed mutation identity
  or score components.
- Instrumenting only the permuter: leaves other candidate lanes incomparable
  and unrecoverable.
- Global mutation fitness: transfers misleading evidence across recipients.
- Donor-score inheritance: confuses provenance with measurement.
- Unbounded nondominated archive: grows without a scheduling bound.
- Mutable dynamic permuter spawning: introduces shared-state races and unclear
  budget ownership.
- Checkpoint-only recovery: loses the decision trail and cannot prove exact
  replay.
- Re-running the full build for isolated candidates: wastes the exclusive
  oracle gate. Isolated evaluation is the search loop; the full build is the
  final authority.
