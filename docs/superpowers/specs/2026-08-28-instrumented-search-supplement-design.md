# Instrumented Search Supplement: Integration-First Delivery and Evidence Reuse

Date: 2026-08-28
Status: Owner-approved supplemental design
Parent design: `docs/superpowers/specs/2026-08-26-instrumented-search-system-design.md`
Parent plan: `docs/superpowers/specs/2026-08-26-instrumented-search-system-implementation-plan.md`
Roadmap context: #274, #277

## 1. Decision

The instrumented search system is integrated into the existing operator and
queue boundaries before it is expanded with new context, donor or layout
lanes. Tasks 8.1, 8.2 and 8.3 are therefore the integration boundary. They
precede Tasks 9.3 and 9.4:

1. Task 8.1 provides explicit subset planning, run creation, status, stop,
   resume and ledger verification.
2. Task 8.2 makes the supervisor and coordinator mutually exclusive and keeps
   the existing score-zero landing gate authoritative.
3. Task 8.3 exposes only the bounded connector operations needed to plan and
   supervise a run.
4. Task 9.3 may then add context and cross-version donor evidence.
5. Task 9.4 may then add struct-layout evidence.

This order is a safety decision, not a preference about implementation
convenience. Without the integration boundary, a new lane could claim work
outside its manifest, schedule beside the legacy supervisor, or report a
candidate without a durable receipt. The 2026-08-26 design and plan remain the
source for the ledger, archive, scorer, mutation, recovery and lane contracts.
This supplement narrows their rollout and adds evidence reuse decisions.

The current `tools/m2c` state is clean and detached at
`94098d4de68c2fcc13fb8cf1096a1520eb171abe`. Any suggestion that this checkout
is already modified is stale and must not be used as a reason to vendor,
revert, or fork the provider.

## 2. Scope and non-goals

This document records decisions only. It does not define source edits, queue
edits, connector implementation, compiler patches or a new schema. All
proposals described here flow through the existing typed records, immutable
artifacts, append-only ledger and ordinary candidate evaluator.

The supplement does not:

- make an isolated score authoritative over the full build and checksum oracle;
- permit an implicit queue query, queue-state fallback or live subset drift;
- make a worker, supervisor, donor index or tuner authoritative for run state;
- treat a version-specific donor body, register choice or branch displacement
  as portable source;
- rewrite or revert a matched `src/` file for search, training or tuning;
- vendor a speculative m2c revision;
- bring data-segment search into the function-search schema.

Data-segment search remains the separate deferred subsystem recorded by roadmap
#277. It is not a hidden dependency of this function-search integration.

## 3. Run creation and integration boundary

### 3.1 Frozen subset and selected lanes

For the first integration runs, run creation resolves a complete, explicit
subset of the exact `todo` population observed at creation time. A direct-ID
`plan` is only syntactic and read-only: it does not claim a record or establish
that the ID is currently eligible. Authoritative run creation resolves those
IDs through scheduler-owned todo evidence, archives that status-bound evidence,
and binds its `queue_evidence_identity`. Separately, it archives the canonical
selection-only payload of sorted record IDs and binds its `subset_identity`.
It also resolves a complete, explicit set of selected lane names. The run
manifest stores the selection, queue evidence and lanes before any task is
created, alongside repository source, target, compiler, tool, configuration
and schema identities.

The subset is frozen at run creation. Later queue changes do not add records,
remove records, change eligibility or change lane selection. A resume uses the
same manifest and refuses if any bound identity changed. An operator who wants
different records or lanes creates a new run or an explicit fork, leaving the
original run immutable.

A record that is not in the frozen `todo` population is not imported as a
convenience. A future owner-approved run may define another explicit source
population, but it must name that population in its manifest and cannot use
this integration boundary as a fallback.

There is no fallback to all `todo`, `near`, `escalated` or `deferred` records.
There is no fallback from an unknown or inapplicable lane to another lane. A
lane that cannot operate on a selected record emits a typed inapplicable or
refusal receipt. An empty subset is a valid, explicit plan that performs no
work and emits a plan receipt.

The queue remains owned by the scheduler. A search run can propose a receipt
for a later queue report, but it cannot claim, reprioritize, close or reopen a
record by writing the queue directly. The scheduler receives an immutable
receipt identity and remains the single queue writer.

### 3.2 Shadow-first rollout

The first integration check is a read-only one-record shadow plan. It resolves
the named record, selected lanes, manifest identities, task IDs and expected
receipt destinations without claiming, applying, compiling, building, landing,
or writing the queue. Its output is a typed plan or refusal proposal and an
immutable plan artifact.

Only after the one-record shadow is reviewed may the same contracts run on a
bounded multi-record subset. The multi-record run remains bounded by the
manifest and initially read-only. It proves deterministic task creation,
subset isolation, lane applicability, receipt production and restart/replay
equivalence before any source-changing integration is considered.

A later run may use the existing explicit landing workflow, but source landing
is still outside the shadow. Each proposed landing must pass the normal
compiler, build and checksum authority. A shadow result is never a permission
to bypass that gate.

### 3.3 Legacy and instrumented mutual exclusion

The supervisor has one explicit execution mode per run: legacy or
instrumented. The legacy mode retains its existing behavior. The instrumented
mode delegates task creation, budget, evaluation, archive and receipt state to
the coordinator. The two modes cannot schedule the same run or record the same
task concurrently.

Mode selection is part of the run identity. A resume cannot silently switch
modes. The supervisor must refuse when an instrumented run is already active,
when a legacy run owns the same record subset, or when a coordinator task would
duplicate a legacy task. An explicit operator stop and a new run are required
to change modes.

The supervisor is an adapter and observability surface, not a second ledger.
It may report coordinator status and forward typed results. It does not own
frontier membership, budget consumption, retry identity or recovery state.

### 3.4 Coordinator tasks and typed receipt proposals

The coordinator creates immutable tasks from the frozen manifest, selected
lane, recipient, parent candidate identities, operation and deterministic
ordinal. Each task carries the evaluator, compiler, tool, target and config
identities needed to reject stale results.

Workers receive an immutable task and return either a typed result proposal or
a typed refusal proposal. A proposal names the run and task, selected record,
lane, input artifact identities, output artifact identities, score vector or
compile failure, mismatch and FirstDivergence data when available, and the
reason for any refusal. A proposal is not a committed decision until the
coordinator validates it, archives referenced artifacts, and appends the
ordered ledger event.

Receipt proposals cover success, rejection, inapplicability, exhaustion,
interruption and changed-input refusal. Prose in a worker log is diagnostic
only. It cannot replace a typed receipt or make an incomplete task complete.

### 3.5 Score-zero landing handoff

An isolated score zero is a typed candidate handoff, never a direct source
write. The handoff names the exact recipient, candidate source artifact,
target, compiler, tool, configuration, evaluator and score receipt. The
existing full build and checksum oracle remains the final landing authority.

The first handoff of a candidate without a valid full-build receipt must run
the normal `make_build` then `verify_build` gate under its existing authority.
If the exact immutable candidate, target, compiler, tool and configuration are
unchanged and a valid full-build receipt already covers that candidate, a
retry used only to archive or forward the handoff reuses that receipt. It does
not rebuild an unchanged source merely to upload, annotate or repeat a
transport step. A missing, corrupt or stale receipt refuses the handoff and
requires a fresh gate.

No isolated score, object hash or prior handoff can justify a source landing
when the target or any compiler/configuration identity differs. The landing
proposal and the full-build receipt remain linked immutable evidence.

## 4. Authority, durability and provenance

The authority chain is:

1. The frozen run manifest defines scope, identities, lanes, seed, budgets and
   policy.
2. The coordinator defines task identity, deterministic commit order, budget
   ownership and receipt acceptance.
3. Workers provide untrusted typed result proposals for their assigned tasks.
4. The archive stores immutable source, object, patch, diff and receipt bytes.
5. The append-only ledger records accepted events and their hash chain.
6. The scheduler alone applies any later queue status transition.
7. The existing full build and checksum oracle alone authorizes a source
   landing.

Artifacts are materialized and verified before the ledger event that names
them. An existing content-addressed artifact with different bytes is
corruption. A worker result without a ledger event is not committed state. A
checkpoint can accelerate recovery but cannot replace the manifest, archive or
ledger.

Every cross-system handoff preserves the identities of its inputs and outputs.
That includes queue record ID, recipient, source and target artifact hashes,
full immutable commit or revision identities, compiler and tool identities,
configuration and schema hashes, evaluator identity, task ID, lane, seed,
score vector, mismatch signature and receipt identity. Mutable paths and
timestamps are context only and never establish ancestry or success.

## 5. Evidence-seeded compiler idiom corpus

The idiom corpus is a read-only evidence product. It supplies hypotheses to a
later candidate task; it does not rewrite an active run's policy or promote a
source body by itself.

### 5.1 Evidence sources

The corpus combines four separately identified evidence classes:

1. The exact scorer taxonomy: compile status, stack, register allocation,
   reordering, insertion and deletion components, their explicit weights,
   weighted total, instruction counts, object identity and mismatch or
   FirstDivergence signature. A scalar score without its taxonomy is not a
   reusable compiler observation.
2. Cited `MATCHING-LESSONS.md` rules. A citation uses the stable repository
   source identity and a review span, such as `MATCHING-LESSONS.md §7b,
   lines 263-278`, rather than an unstable copied excerpt. When the source
   changes, the corpus records a new content-addressed citation artifact and
   does not silently move the old citation.
3. Provenance-strict draft-to-landed observations. Both source endpoints,
   recipient, full commit or ref resolution, compiler/tool/config identities,
   atomic patch, measurement and supporting pair identity must be present.
   Ambiguous generations, missing bytes, altered identities and inferred
   ancestry are refusals, not corpus support.
4. Recurring FirstDivergence hypotheses from completed ledger lineages. A
   hypothesis enters the recurring set only after independent completed
   lineages show the same divergence class under compatible scorer and
   compiler identities. A running, partial or aborted lineage can remain
   diagnostic evidence but cannot teach the corpus.

The corpus retains the source, target, object, patch, score and citation
identities for every observation. It records negative and refused evidence so
that an attractive but unsupported transformation is not rediscovered as a
new fact.

### 5.2 Stable lesson citations

The following rules are corpus inputs and review anchors. The section heading
is the stable source identity; the line span is the locator in the captured
2026-08-28 source. A corpus artifact must bind the citation to the exact source
hash used for ingestion.

| Citation | Rule carried into the corpus |
|---|---|
| `MATCHING-LESSONS.md §2, lines 146-178` | Absence of `andi` narrowing before argument use is evidence for a full-width parameter. Narrow `u8` or `u16` declarations can inject masking and wrong bytes, so declaration consistency matters. |
| `MATCHING-LESSONS.md §7b, lines 263-278` | Build immediately before verification. A bare verification after interruption is stale evidence. |
| `MATCHING-LESSONS.md §8c-2, lines 432-448` | Preserve disjoint low-score findings, combine only non-overlapping proven changes, and rescore the union. |
| `MATCHING-LESSONS.md §22, lines 1287-1306` | An isolated zero is permission for the full build gate, not proof of stack, jump-table or placement equivalence. |
| `MATCHING-LESSONS.md §24, lines 1329-1381` | Compiler diagnostics, output streams, dependency context and queue identity are part of honest score evidence. |
| `MATCHING-LESSONS.md §25, lines 1424-1472` | A score receipt is compile evidence, not source text. Preserve raw and final artifacts, and do not rebuild an unchanged body for information already established. |
| `MATCHING-LESSONS.md §26, lines 1477-1488` | Branch opcode similarity does not prove branch-target similarity; retain target evidence in scoring. |
| `MATCHING-LESSONS.md §29, lines 1519-1544` | Target and donor body hashes, exact paths and invalidation ownership are required for duplicate or shared evidence. |

These citations are rules for evidence handling, not permission to generalize
an observation across recipients or compiler identities.

### 5.3 Promotion gate

An observed transformation is only a hypothesis until a later candidate task
applies it under a compatible compiler, tool, configuration, target and
recipient context. The ordinary evaluator must measure the original and
rewritten candidate with the same scorer identity.

Promotion requires at least one of the following authoritative outcomes:

- a strictly better full score vector under the declared lower-is-better
  ordering; or
- an exact target object or checksum identity under the same target and
  compiler-bound pipeline.

The output candidate, measurement, patch replay, evaluator identity and
promotion decision become new immutable artifacts and ledger events. A corpus
match, source similarity, commit adjacency, donor score or recurring name
alone cannot promote an idiom. A run cannot train on its own result and alter
its scheduling policy in place. A later run manifest may opt into a cited,
immutable corpus generation.

## 6. Immutable cross-version donor index

The donor index is a content-addressed semantic evidence store for US, HD,
PSPEU and Saturn. It is not a byte transplant store and it is not a mutable
"latest" view.

### 6.1 Revision and index identity

Each indexed version is bound to an exact pinned revision identity, source
artifact hash and version label. The index generation additionally binds:

- the indexer identity and its source hash;
- the index configuration, include and preprocessing policy, and its hash;
- the signature algorithm identity and configuration;
- the complete ordered revision set;
- the schema identity and generation ordinal.

Changing any revision, indexer, config, signature algorithm or schema creates a
new immutable index generation. It never updates or rewrites an existing
generation. A query records the index generation identity and the exact donor
evidence identities returned.

### 6.2 Query contract

Queries are bounded and deterministic. They search in this order:

1. exact symbol and version-aware path identity;
2. instruction-shape signature;
3. CFG signature;
4. dataflow signature.

The query may return semantic donor evidence, an ambiguity receipt or an
incompatible-donor receipt. Every result preserves version, revision, source
artifact, symbol or structural signature, match kind, compatibility evidence
and query identity. Ties are ordered by immutable evidence identity, never by
filesystem order or modification time.

US, HD, PSPEU and Saturn donors may explain control shape, declarations,
types, data dependencies or compiler idioms. Their version-specific bytes,
register allocations, relocations and branch displacements are not copied into
another version. A donor becomes a candidate only after target-context
rendering and compiler-bound evaluation.

### 6.3 Rebuild and invalidation

An index is rebuilt when any bound identity changes or when a source artifact
is missing, corrupt or no longer resolves to its pinned revision. Queries do
not repair an index in place. A stale index produces a typed refusal naming the
old generation and the changed identity, then waits for a new indexed
generation.

## 7. m2c revision provider and matrix

The m2c lane uses a revision provider that resolves exact pinned revisions and
returns the revision, provider, executable, arguments, configuration and source
identities used for each draft. A mutable checkout name is not enough to
establish the provider identity.

The current pinned revision at
`94098d4de68c2fcc13fb8cf1096a1520eb171abe` is the first matrix member and the
compatibility baseline. The provider records that it is clean and detached at
that revision. A missing or altered checkout is a typed provider refusal, not
an invitation to use an arbitrary local tree.

The matrix is manifest-defined and bounded. It can vary supported switches,
contexts and pinned provider revisions, but it must retain a stable ordinal,
task identity and budget charge for each unique compiled result. Identical
draft bytes under the same compiler-bound identity compile once and retain
all input provenance.

Alternate pinned revisions are eligible only after a fixed benchmark has been
run against the current baseline. The benchmark and its target/compiler/config
identities are immutable inputs. An alternate is admitted to the active
matrix only when the fixed benchmark demonstrates a unique candidate or a
measured improvement under the declared scorer taxonomy. A version that merely
exists, is newer, or produces a different filename does not qualify.

No speculative vendoring is allowed. The provider may resolve an explicitly
pinned revision that is already available under the configured tool boundary.
Making a revision available, changing submodules, or adding a new dependency
is a separate owner-approved change with its own identity and benchmark.

## 8. Task 9.6 weight tuner

The weight tuner is a later evidence consumer, not a live search controller.
It learns from immutable archived drafts and exact targets, then publishes an
immutable report and weights artifact for later manifests.

### 8.1 Fixed data and compiler boundary

The tuner input set is selected before training and consists of archived draft
artifacts, target artifacts, completed score vectors, object identities,
FirstDivergence signatures and the exact compiler, tool, evaluator and config
identities that produced them. Source paths and timestamps cannot define the
set.

The train and holdout split is fixed, content-addressed and recorded before
any weight search. Related generations, duplicate source bytes and repeated
observations are assigned deterministically so a draft and its near-identical
landing cannot leak across the split. The holdout is not used to tune, stop,
or rewrite the training policy.

Every trial records its seed, iteration bound, compiler and evaluator
identities, scorer taxonomy, candidate count, measured vectors and cost. A
trial with a changed compiler, target, scorer taxonomy or data split is a new
tuner run, not a continuation.

### 8.2 Selection order

Weight configurations are ranked lexicographically:

1. exact rediscovery on the fixed holdout, highest first;
2. median best score on the fixed holdout, lower first;
3. measured search cost, lower first;
4. immutable weight artifact identity, as the deterministic final tie-break.

Exact rediscovery means reproducing the declared target object or checksum
identity under the same compiler-bound pipeline. A lower scalar score that
does not rediscover the exact target cannot outrank an exact rediscovery.
Median best score is a secondary diagnostic, not a replacement for exact
identity.

### 8.3 Report and adoption

The tuner publishes one immutable report and one immutable weights artifact.
The report binds the archive and target identities, split identity, scorer
taxonomy, compiler/tool/config/evaluator identities, seeds, iteration bounds,
trial metrics, selection order and final weight artifact. A report with
missing, corrupt or partial trial evidence is refused.

Adoption is opt-in at later run creation. A later manifest records the exact
weights artifact identity before task creation. An active run cannot rewrite
its weights, rescore its own holdout to change scheduling, or replace the
artifact in place. A new tuning result creates a new artifact and requires a
new manifest or explicit fork.

The tuner never edits, reverts or re-lands matched `src/` content. It operates
on archived evidence and candidate artifacts only. A tuner result can suggest
a future search policy; it cannot reopen a matched record or turn a score into
source authority.

## 9. Failure modes and typed refusals

| Failure | Required response |
|---|---|
| Queue changes after run creation | Keep the frozen subset; record drift for status and refuse resume if a bound identity changed. |
| Missing or implicit record or lane selection | Refuse plan creation. Never query a broader queue state. |
| Legacy and instrumented scheduling overlap | Refuse the second owner and preserve the first run's task state. |
| Worker result lacks task, recipient or identity binding | Refuse the proposal; do not infer fields from filenames, order or logs. |
| Artifact is missing, corrupt or already exists with different bytes | Refuse as archive corruption before ledger append. |
| Provider revision is unavailable or altered | Emit provider refusal naming the expected pinned identity. |
| Donor query has ambiguous or incompatible matches | Emit an ambiguity or incompatibility receipt; do not select by path order. |
| Scorer taxonomy, compiler or config changed | Fork or start a new run; never mix measurements. |
| Isolated score zero lacks a current full-build receipt | Refuse landing handoff until the normal build and checksum gate succeeds. |
| Unchanged score-zero handoff is retried | Reuse a valid receipt by exact identity; do not repeat an unchanged build. |
| Index or tuner input is partial or stale | Refuse the generation and preserve the old immutable artifact. |
| Tuner data leaks or holdout is changed | Refuse the report; no weights artifact is eligible for later manifests. |
| Any operation proposes a matched source rewrite | Refuse and leave `src/` untouched. |

Refusal receipts are durable evidence. They carry the run, task or query
identity, affected input identities, reason code, observed identities and
whether a new run or index generation is required.

## 10. Acceptance criteria

The integration-first supplement is accepted when all of the following are
demonstrated by focused tests and immutable receipts:

- a one-record read-only shadow creates exactly the frozen subset, selected
  lanes and task plan without queue, source, build or landing side effects;
- a bounded multi-record shadow is deterministic under input and completion
  order and cannot observe records outside its manifest;
- legacy and instrumented supervisor modes cannot schedule the same run or
  task, and mode changes require an explicit new run or fork;
- coordinator tasks produce typed result or refusal proposals, and only the
  coordinator commits ordered receipts;
- score-zero handoff reaches the existing full build and checksum authority,
  while a valid unchanged receipt prevents a redundant build on retry;
- idiom corpus entries retain scorer taxonomy, stable lesson citations,
  provenance-strict draft-landed support and recurring completed-lineage
  FirstDivergence evidence;
- no idiom is promoted without compiler-bound measured improvement or exact
  target object identity;
- donor queries are reproducible from immutable US, HD, PSPEU and Saturn index
  generations, and identity changes force a rebuild;
- the current pinned m2c revision is benchmarked first, alternate pinned
  revisions require a unique or better fixed-benchmark result, and no
  speculative vendoring occurs;
- tuner reports reproduce from the fixed train and holdout artifacts, rank by
  exact rediscovery then median score then cost, and are usable only through a
  later manifest;
- crash, restart, changed-input, corrupt-artifact, ambiguity, provider and
  leakage cases fail closed with typed receipts;
- no test or run mutates matched `src/`, the live queue, or an immutable
  archive generation.

## 11. Ordering and deferrals

The delivery order is:

1. Complete and validate Task 8.1 subset planning and run authority.
2. Integrate Task 8.2 with explicit legacy/instrumented exclusion and the
   score-zero handoff.
3. Add Task 8.3 connector surfaces and restart validation.
4. Run the read-only one-record shadow, then a bounded multi-record shadow.
5. Continue with Task 9.3 context and cross-version donor evidence.
6. Continue with Task 9.4 struct-layout evidence.
7. Aggregate completed lineages for Task 9.5 when enough immutable receipts
   exist; do not train from an active run.
8. Run Task 9.6 weight tuning only after the fixed corpus, scorer identity,
   archive and holdout contracts are available.

Task 9.6 is deferred until its data boundary is real. It cannot be used to
justify skipping the integration shadow or to alter an active run. Data-segment
search remains deferred under #277. Existing roadmap tasks remain in scope and
are re-evaluated with measured receipts rather than deleted.

## 12. References and citation convention

- `docs/superpowers/specs/2026-08-26-instrumented-search-system-design.md`
  defines the coordinator, archive, ledger, scorer, frontier, lane and
  recovery architecture.
- `docs/superpowers/specs/2026-08-26-instrumented-search-system-implementation-plan.md`
  defines Tasks 8.1 through 9.5, their acceptance boundaries and the deferred
  data-segment subsystem. This supplement adds the integration-first ordering
  and Task 9.6 policy.
- `MATCHING-LESSONS.md` citations in this document use repository path plus
  section heading as the stable source identity and a line span as the review
  locator. Ingested citations must also bind the exact content-addressed source
  artifact. A source revision creates a new citation identity; it does not
  silently rewrite historical evidence.
