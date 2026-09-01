# Production Indexed Search Runtime Design

## Purpose

The evidence corpus, completed-lineage projection, four-version donor index,
bounded donor query, and indexed-lane adapter are incomplete until they are
reachable through the normal instrumented search production path. This design
closes that gap permanently. It replaces callback-only assembly with an
immutable runtime generation that the factory binds into a run and the
supervisor reconstructs on both start and resume.

## Completion definition

The tranche is complete only when all of these statements are true:

1. Every exported production interface added by the evidence and donor tranche
   has a reachable caller from a typed connector action or from another
   reachable production interface.
2. US, HD, PSPEU, and Saturn are each scanned exactly once for a generation.
   Recipient queries never rescan a tree or provider.
3. Corpus, pattern, donor, query, adapter, receipt, ledger, archive, stop,
   recovery, and replay behavior is exercised with real repository evidence.
4. Indexed runs use the ordinary factory, manifest, coordinator, supervisor,
   lane-result, receipt, ledger, checkpoint, and recovery authorities. No
   parallel manifest, queue, task, archive, or receipt truth is introduced.
5. Production execution is read-only with respect to the live queue, source,
   build inputs, and checksum oracle.
6. Missing, corrupt, stale, ambiguous, incompatible, unsupported, partial, or
   cross-subset evidence fails closed with a typed durable disposition.
7. A repeated publication, creation, query, start, stop, or resume with the
   same immutable inputs is byte-identical or an idempotent no-op.

## Architecture

### Runtime publication

A new `automation/search_indexed_runtime.py` module owns publication and
loading of an `IndexedRuntimeGeneration`. Publication accepts an explicit
completed integration run ID and four explicit pinned revision descriptors.
It validates the integration gate through
`search_supervisor.validate_integration_gate`, builds the evidence corpus,
builds the donor index once, and writes a self-contained content-addressed
runtime generation beneath the canonical search evidence root.

The generation contains the complete gate receipt and bindings, corpus
artifact, donor-index artifact, four pinned revision descriptors, scanner,
signature, schema, configuration, compiler, renderer, and runtime identities.
No caller may select a generation by modification time or by an implicit
"latest" rule.

### Four-platform repository scanner

A new `automation/search_donor_scan.py` module maps the repository's canonical
US, HD, PSPEU, and Saturn configurations and source families. It derives
version-specific source manifests from the exact pinned repository revision and
the matching configuration files. It extracts C functions and assembly
functions deterministically, then emits `DonorEvidence` with exact symbol and
version-aware path, normalized instruction, CFG, and dataflow signatures,
declaration closure, safe semantic constants, compatibility facts, structural
differences, and archive-owned source references.

The scanner publishes no donor body in the index. It records enough semantic
structure for target rendering and refuses forbidden register allocation,
relocation, branch displacement, or raw object-byte fields. File order,
timestamps, abbreviated commits, and working-tree drift cannot influence a
generation.

### Target query and rendering

`automation/search_indexed_runtime.py` reconstructs one query closure per
indexed lane. Query construction uses only the recipient and its archived
target evidence from the frozen run. It binds the recipient ID, platform,
source path, symbol, instruction signature, CFG signature, dataflow signature,
compiler identity, configuration identity, and bounded limit.

The target renderer receives only typed `DonorSemanticClaim` values. It emits
target-specific candidates from target assembly and declaration context, using
the deterministic local draft generator where a complete compilable target
translation is available. Donor source bodies, register choices, relocations,
and branch displacements are never copied. Unsupported semantic shapes produce
a typed `target_context_unsupported` refusal rather than an empty success.

### Factory and manifest binding

Runtime publication is separate from run creation. The caller supplies the
exact runtime generation ID when creating a run that includes
`multi_donor` or `cfg_dataflow`. The factory loads and validates the
generation, archives its complete binding into the run evidence index, adds the
runtime, query, scanner, and renderer identities to `tool_identities`, and
includes them in seed and manifest identity calculations.

An indexed lane without an explicit valid runtime generation is refused at
factory admission. Non-indexed runs remain byte-compatible with the existing
factory behavior.

### Supervisor, stop, recovery, and replay

On start and resume, the supervisor loads the runtime binding from the factory
archive, verifies every referenced artifact and identity, reconstructs both
indexed adapters, and passes the resulting `LaneAdapters` to the ordinary
`execute_task` path. Caller-supplied indexed callbacks are forbidden in the
production connector path.

Query results and refusals flow through ordinary lane results and receipt
proposals. Candidate fan-out, exhaustion, checkpoints, stop requests, resume
events, and terminal integration receipts remain coordinator and supervisor
owned. Recovery validates that the manifest-bound runtime generation still
matches the archived bytes before replaying a pending task.

### Connector surface

The connector exposes typed actions for:

- publishing or verifying one runtime generation from an exact gate run and
  exact four-version revision set;
- creating an instrumented run with an optional exact runtime generation ID;
- inspecting a runtime generation;
- existing start, stop, resume, status, and ledger verification.

Arguments are typed IDs and full revisions only. Arbitrary paths and argv are
not accepted. Long publication and execution operations run as jobs.

## Exhaustive acceptance gate

The permanent acceptance runner audits exported call-graph closure and runs the
following matrix:

- all four platform scanners, exactly-once accounting, ordering independence,
  and changed-revision identity;
- complete, empty, ambiguous, incompatible, stale, corrupt, and missing query
  dispositions;
- both indexed lanes, matched candidates, unsupported rendering, candidate
  identity checks, receipt provenance, and subset refusal;
- corpus citations, scorer taxonomy, completed-lineage grouping, historical
  missing-evaluator diagnosis, and recurring-divergence extraction;
- factory admission, runtime binding, name collision, partial publication,
  archive collision, and idempotent retry;
- supervisor start, stop at every named durable fault point, recovery, resume,
  completed replay, duplicate-event prevention, and budget idempotence;
- corruption of each artifact class, wrong archive root, wrong gate, wrong
  compiler or configuration, wrong revision, wrong recipient, and forged
  candidate or receipt identities;
- connector discovery, validation, job execution, status, and restart-safe
  reconstruction;
- one real single-record gate followed by one real several-record Task #257
  indexed run;
- byte-level before and after proof for the selected queue records, queue
  aggregate counts, tracked source, build inputs, and build-oracle state.

Passing synthetic unit tests without the real production runs is insufficient.
A production caller with an untested export or an unreachable connector action
is insufficient.

## Advertised lane closure

The production audit also covers every lane named by `search_types.LANES`.
The schema and manifest may not advertise a lane that has no dispatch path.
The following existing declarations require permanent providers in addition to
the indexed runtime work:

- `m2c_ensemble`: target-only drafts from the pinned m2c revision matrix, with
  deduplication before compilation and complete tool/configuration identities;
- `idiom_atlas`: completed draft-landed mining, compiler-idiom measurement,
  corpus lookup, target applicability checks, and grouped-patch replay;
- `bounded_synthesis`: deterministic target-derived expression, statement,
  declaration, and control-flow variants under explicit candidate budgets;
- `permuter_random`, `permuter_targeted`, `permuter_recombine`, and
  `permuter_ddmin`: isolated scratch-only vendor execution with pinned weights,
  seeds, algorithms, budgets, checkpoints, and resumable receipts;
- `model_fleet` and `model_expensive`: proposal-only provider calls over the
  frozen manifest context, with explicit model, prompt, reasoning, provider,
  budget, response, and refusal identities and no queue claims or source edits.

Each provider returns ordinary `LaneOutcome` and `LaneReceiptProposal` values,
uses the coordinator's task and budget authority, archives every input and
output, and resumes without duplicate provider calls after a durable result.
Provider unavailability is a typed durable refusal, not an unimplemented lane
or an exception that aborts unrelated work. The real acceptance run exercises
every mechanical and local provider. External model availability is verified
through the provider preflight and deterministic replay fixture; an unavailable
paid provider does not authorize a paid call or make the connector unreachable.
