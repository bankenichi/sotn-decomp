# Instrumented Search System Implementation Plan

Date: 2026-08-26
Design: `docs/superpowers/specs/2026-08-26-instrumented-search-system-design.md`
Schema: `automation/search-ledger.schema.json`
Roadmap: #274
Implementation owner: Luna at max reasoning for bounded coding tasks
Review and integration owner: root

## 1. Delivery contract

The implementation is complete only when:

- the append-only ledger and immutable archive recover without process-local
  state;
- score vectors and typed mutation events are emitted by the vendored
  permuter;
- the central coordinator can run an explicit subset and cannot pull from
  another queue state;
- scalar elite, bounded Pareto, recombination and minimization behavior are
  tested;
- every lane has a common adapter and receipt contract;
- interrupted and uninterrupted reference runs converge to the same logical
  state under fault injection;
- score zero is routed to the existing full build and checksum oracle;
- all focused and consolidated automation tests pass;
- root reviews every touched file and runs the only builds;
- `ROADMAP.md`, architecture and operator documentation record the outcome.

No worker or subagent may build, run git, alter the live queue, apply a candidate
to `src/`, or push. Luna may run focused Python tests through the approved
connector only. Root owns build, oracle, staging, commits and push.

## 2. Dirty-tree boundary

Before each implementation batch, record `git_state` and the exact pre-existing
dirty paths. The following paths were already dirty when this plan was written
and must be treated as owner work unless root explicitly assigns a hunk:

- `automation/permuter_supervisor.py`;
- `automation/transplant.py`;
- `automation/upstream_harvest.py`;
- `automation/worker_direct.py`;
- existing modified tests and generated candidate or rejection histories.

Any edit to an already dirty file must be minimal, preceded by a read of the
current content, and reviewed as a diff against the recorded starting state.
Prefer new modules and narrow adapters over broad rewrites.

## 3. Planned modules

New tracked modules:

- `automation/search_types.py`
- `automation/search_ledger.py`
- `automation/search_archive.py`
- `automation/search_frontier.py`
- `automation/search_mutations.py`
- `automation/search_coordinator.py`
- `automation/search_lanes.py`
- `automation/search_recovery.py`
- `automation/search_cli.py`
- `automation/test_search_schema.py`
- `automation/test_search_ledger.py`
- `automation/test_search_archive.py`
- `automation/test_search_frontier.py`
- `automation/test_search_mutations.py`
- `automation/test_search_coordinator.py`
- `automation/test_search_recovery.py`
- `automation/test_search_subset.py`
- `automation/test_search_historical_fixture.py`
- `automation/fixtures/search/func_us_801B001C/`

Expected narrow edits:

- `tools/decomp-permuter/src/candidate.py`
- `tools/decomp-permuter/src/randomizer.py`
- `tools/decomp-permuter/src/scorer.py`
- `tools/decomp-permuter/src/permuter.py`
- `tools/decomp-permuter/src/main.py`
- `tools/decomp-permuter/test/test_perm.py`
- `automation/permuter_supervisor.py`
- `automation/mcp/commands_client.py`
- `automation/mcp/sotn_cmd_mcp.py`
- `automation/test_connector_surfaces.py`
- `automation/run_selftests.py`
- `automation/README.md`
- `docs/HARNESS-ARCHITECTURE.md`
- `docs/TOOLING.md`
- `ROADMAP.md`

A phase may prove that a proposed module should be merged with another. Any
such reduction must preserve the contracts and be called out for root review.
Do not introduce parallel sources of truth.

## 4. Phase 0: Freeze fixtures and compatibility baselines

### Task 0.1: Capture scorer compatibility fixtures

Files:

- create `automation/fixtures/search/scorer-v1.json`;
- add fixture support to `tools/decomp-permuter/test/test_perm.py`.

Work:

1. Select small, already-imported permuter examples covering exact match,
   reorder, register, stack, insertion, deletion and compile failure.
2. Record the current scalar score, object hash and disassembly identity.
3. Store only stable inputs and expected values, not temporary build paths.
4. Add a test that can compare the legacy scalar with the future vector total.

Acceptance:

- the fixture is deterministic;
- it does not run a full repository build;
- the pre-instrumentation scorer passes it unchanged.

### Task 0.2: Build the historical recombination fixture

Files:

- create fixture files beneath
  `automation/fixtures/search/func_us_801B001C/`;
- create `automation/test_search_historical_fixture.py`.

Work:

1. Copy only the required preserved hypothesis bodies from
   `nonmatchings/func_us_801B001C`.
2. Record that the original output lineage is unavailable.
3. Represent the four score-70 contributions as synthetic siblings of a known
   fixture base.
4. Preserve the score-10 combined form and the final two-hunk zero mutation.
5. Test that the two final hunks are one atomic edit group.

Acceptance:

- no invented original event IDs or timestamps;
- the fixture can prove recombination semantics without claiming historical
  lineage recovery.

## 5. Phase 1: Typed records and schema validation

### Task 1.1: Implement immutable Python record types

Files:

- create `automation/search_types.py`;
- create `automation/test_search_schema.py`.

Work:

1. Define frozen dataclasses or equivalent immutable value types for every
   schema definition.
2. Provide canonical JSON serialization with sorted keys, UTF-8 and stable
   separators.
3. Reject unknown fields when loading.
4. Validate nonnegative counts, content hashes, IDs, lane names and tier names.
5. Keep score components raw and weights explicit.
6. Model compile failure without fake zero scores or object hashes.

Acceptance:

- round-trip tests cover every record;
- invalid unknown fields, negative components and malformed hashes fail;
- serialized fixtures conform to `automation/search-ledger.schema.json`.

### Task 1.2: Add schema self-validation

Files:

- extend `automation/test_search_schema.py`;
- register the test in `automation/run_selftests.py`.

Work:

1. Parse the tracked JSON schema.
2. If the repository already carries a compatible JSON Schema library, validate
   representative valid and invalid events with it.
3. If not, keep runtime validation in the typed loader and make the test verify
   that schema enums and required fields agree with the Python declarations.
4. Do not add a network-installed dependency only for validation.

Acceptance:

- schema and Python types cannot silently drift;
- event variants and lane enums have exact parity.

Commit boundary: schema, types and tests only.

## 6. Phase 2: Durable ledger and immutable archive

### Task 2.1: Implement content-addressed artifacts

Files:

- create `automation/search_archive.py`;
- create `automation/test_search_archive.py`.

Work:

1. Hash bytes with SHA-256 and name artifacts by content.
2. Reject absolute paths and traversal.
3. Write through a unique temporary sibling, flush, fsync, close and atomically
   rename.
4. Fsync the parent directory where supported.
5. Treat an existing same-hash, different-byte artifact as corruption.
6. Return typed artifact references.
7. Never overwrite an immutable artifact.

Acceptance:

- repeat writes deduplicate;
- simulated collision or corrupted existing content refuses;
- interruption before rename leaves no authoritative artifact;
- interruption after rename yields a valid reusable artifact.

### Task 2.2: Implement append-only hash-chained ledger

Files:

- create `automation/search_ledger.py`;
- create `automation/test_search_ledger.py`.

Work:

1. Require `run_started` at sequence zero.
2. Canonicalize and hash events excluding `event_hash`.
3. Append one complete UTF-8 JSON line, flush and fsync.
4. Validate sequence and previous hash before append.
5. Verify referenced artifacts before accepting an event.
6. Scan to the last complete newline on recovery.
7. Treat a partial trailing line as an interrupted append, preserve it as
   forensic evidence, and truncate only through an explicit recovery operation.
8. Reject gaps, duplicates, invalid payloads and broken chains.

Acceptance:

- a ledger reconstructed from disk matches the in-memory committed prefix;
- corruption tests fail closed;
- no checkpoint is required for recovery.

Commit boundary: archive, ledger and their focused tests.

## 7. Phase 3: Instrument the vendored permuter

### Task 3.1: Return full score vectors

Files:

- edit `tools/decomp-permuter/src/scorer.py`;
- edit `tools/decomp-permuter/src/candidate.py`;
- edit `tools/decomp-permuter/src/permuter.py`;
- extend `tools/decomp-permuter/test/test_perm.py`.

Work:

1. Introduce a typed score result retaining raw components, weights, total,
   object hash, mismatch signature, first divergence and instruction counts.
2. Keep a compatibility property or adapter for callers expecting the scalar.
3. Change caches to store the complete immutable score result.
4. Preserve current scoring behavior and default output.
5. Ensure compile failure cannot masquerade as an evaluated score.

Acceptance:

- every baseline scalar and object hash from Phase 0 is unchanged;
- vector totals exactly equal the legacy scalar;
- component tests exercise every dimension.

### Task 3.2: Return typed mutation events

Files:

- edit `tools/decomp-permuter/src/randomizer.py`;
- edit `tools/decomp-permuter/src/candidate.py`;
- extend `tools/decomp-permuter/test/test_perm.py`.

Work:

1. Give each public mutation pass a stable name.
2. Make randomization receive an explicit random source or seed.
3. Return the chosen pass, attempts, seed, before source and after source.
4. Derive one grouped patch from the complete before and after source.
5. Record no-change and failed-attempt outcomes explicitly.
6. Preserve the existing weighted pass distribution under the same seed.

Acceptance:

- the same parent and seed replay the same pass and source;
- separated hunks from one pass remain one atomic event;
- no ambient module-level random state is authoritative.

### Task 3.3: Emit machine-readable instrumentation

Files:

- edit `tools/decomp-permuter/src/permuter.py`;
- edit `tools/decomp-permuter/src/main.py`;
- extend vendored tests.

Work:

1. Add an opt-in event sink or callback.
2. Emit typed mutation and evaluation results without parsing console text.
3. Preserve legacy CLI behavior when instrumentation is disabled.
4. Do not add dynamic mutable permuter spawning.
5. Expose a bounded single-task execution entry point suitable for the
   coordinator.

Acceptance:

- legacy command tests pass;
- one deterministic task returns a complete mutation and score record;
- instrumentation disabled has no new output files or behavior changes.

Commit boundary: vendored permuter instrumentation and its tests.

## 8. Phase 4: Candidate graph, cache and frontier

### Task 4.1: Implement candidate graph and recipient-local cache

Files:

- create `automation/search_frontier.py`;
- create `automation/test_search_frontier.py`.

Work:

1. Index candidates by content hash and preserve multiple provenance edges.
2. Key evaluations by recipient, candidate or mutation and evaluator identity.
3. Never reuse donor score for a recipient.
4. Track scalar elite independently of Pareto membership.
5. Reconstruct all indexes from ledger events.

Acceptance:

- identical source deduplicates while provenance remains plural;
- cross-recipient cache lookups miss;
- recovery creates the same indexes as uninterrupted execution.

### Task 4.2: Implement bounded Pareto selection

Files:

- extend `automation/search_frontier.py`;
- extend `automation/test_search_frontier.py`.

Work:

1. Define lower-is-better dominance over the five raw components.
2. Always retain the scalar elite.
3. Keep at most the manifest frontier cap.
4. Break excess non-dominated ties deterministically using mismatch-signature
   diversity, scalar total, candidate hash.
5. Record every retain or archive decision.

Acceptance:

- result is independent of worker completion order;
- a useful worse-scalar sibling can survive through component or signature
   diversity;
- cap and elite invariants hold for randomized test sequences.

Commit boundary: graph, cache and frontier.

## 9. Phase 5: Replay, recombination and minimization

### Task 5.1: Implement atomic grouped patches

Files:

- create `automation/search_mutations.py`;
- create `automation/test_search_mutations.py`.

Work:

1. Produce canonical-token or AST-aware grouped patches.
2. Replay exactly against the recorded parent.
3. Port to a sibling through bounded three-way/context anchoring.
4. Apply every hunk or none.
5. Return typed conflict, invalid and no-change results.
6. Verify the result source hash.

Acceptance:

- exact replay is byte identical;
- ambiguous anchors reject;
- a conflict in any hunk leaves the source unchanged;
- the historical two-hunk fixture cannot partially apply.

### Task 5.2: Implement recombination

Files:

- extend `automation/search_mutations.py`;
- extend frontier and historical tests.

Work:

1. Select donor mutations from retained siblings.
2. Apply mutations to the recipient without carrying donor score.
3. Evaluate on the recipient and cache with recipient-local identity.
4. Bound donor count and recombination depth in the manifest.
5. Record rejected conflicts as evidence.

Acceptance:

- the synthetic historical fixture reaches the preserved combined form;
- donor provenance is retained;
- donor evaluations are not copied.

### Task 5.3: Implement bounded delta debugging

Files:

- extend `automation/search_mutations.py`;
- extend tests.

Work:

1. Minimize only configured improvements.
2. Support preservation by object hash, full score vector or no-worse scalar.
3. Keep original mutation immutable and create derived minimized mutations.
4. Charge every evaluation to the task's declared budget.
5. Stop deterministically at the budget boundary.

Acceptance:

- unnecessary edit groups are removed;
- required separated hunks remain atomic;
- resume does not double-charge a ddmin evaluation.

Commit boundary: replay, recombination, minimization and historical fixture.

## 10. Phase 6: Coordinator and exact recovery

### Task 6.1: Implement deterministic scheduling

Files:

- create `automation/search_coordinator.py`;
- create `automation/test_search_coordinator.py`.

Work:

1. Load one immutable manifest.
2. Generate deterministic task IDs and seeds.
3. Enforce tier completion before scheduling the next tier.
4. Schedule within a tier by measured lane yield and stable tie breakers.
5. Dispatch immutable tasks.
6. Buffer concurrent results and commit them in task-ID order at bounded epoch
   boundaries.
7. Keep budget ownership in the coordinator.

Acceptance:

- shuffled completion order produces identical ledger events;
- no worker can allocate a task or budget;
- an incomplete cheaper tier blocks expensive work.

### Task 6.2: Implement recovery and checkpoints

Files:

- create `automation/search_recovery.py`;
- create `automation/test_search_recovery.py`.

Work:

1. Rebuild all state from manifest, ledger and artifacts.
2. Detect scheduled or started tasks without terminal events.
3. Reissue the same task identity and seed without consuming another unit.
4. Write checksummed checkpoints only after ledger durability.
5. Ignore missing checkpoints and reject invalid ones.
6. Refuse changed-input resume.
7. Implement explicit run fork preserving parent identity.

Acceptance:

- deleting checkpoints does not change recovered state;
- a changed compiler or config refuses resume;
- explicit fork starts a new run and leaves the parent untouched.

### Task 6.3: Fault injection at every transition

Files:

- extend `automation/test_search_recovery.py`.

Work:

1. Provide named fault points around archive write, rename, ledger append,
   epoch commit, checkpoint and graceful stop.
2. Run a reference scenario uninterrupted.
3. Kill and resume after every fault point.
4. Compare committed task IDs, graph, cache, budgets, elite, frontier and
   receipts with the reference result.
5. Test duplicate result delivery and partial trailing JSON.

Acceptance:

- every injected run converges or fails closed on intentional corruption;
- no injected run consumes duplicate logical budget.

Commit boundary: coordinator, recovery and fault-injection tests.

## 11. Phase 7: Lane adapters

Implement adapters incrementally. Each adapter returns candidates or a typed
refusal/exhaustion receipt. It does not alter `src/` or the queue.

### Task 7.1: Current deterministic lanes

Files:

- create `automation/search_lanes.py`;
- add focused lane tests using fixtures;
- make narrow imports from `upstream_harvest.py`,
  `asm_twin_finder.py`, `shim_sweep.py` and `transplant.py`.

Work:

1. Current upstream and pinned-ref harvest.
2. Preserved candidates and landing evidence.
3. Shared-header viability.
4. Twin and transplant analysis.
5. Whole-TU and dependency/data closure.

Acceptance:

- each lane runs on exactly the manifest subset;
- read-only mode cannot apply or queue-report;
- inapplicable lanes emit a receipt.

### Task 7.2: mipsmatch exact lane

Files:

- extend `automation/search_lanes.py`;
- add mipsmatch fixtures and provenance tests;
- narrowly integrate existing `tools/make-config.py` behavior.

Work:

1. Expose fingerprint, scan and exact body discovery to queue records.
2. Preserve reference identity and body source.
3. Reconcile hits with existing exact-copy provenance.
4. Avoid double-counting the current 88 exact-copy records.

Acceptance:

- one exact hit produces one candidate with all provenance;
- repeat discovery deduplicates;
- exact-copy reporting is stable.

### Task 7.3: Multi-donor and structural signatures

Files:

- extend `automation/search_lanes.py`;
- add bounded fixture corpus.

Work:

1. Gather donors by symbol, instruction, CFG and dataflow signatures.
2. Triangulate declarations, constants and structural differences.
3. Produce candidates only when every edit has evidence.
4. Emit refusal categories for incompatible donors.

Acceptance:

- donor selection is deterministic;
- no raw register or branch displacement is treated as a semantic constant;
- incompatibility is evidence, not a silent skip.

### Task 7.4: m2c ensemble

Files:

- extend `automation/search_lanes.py`;
- reuse and extend `automation/test_m2c_only.py`.

Work:

1. Enumerate a bounded manifest-defined matrix over supported m2c switches.
2. Support multiple contexts and deterministic variable naming.
3. Deduplicate identical output before compilation.
4. Record invocation and tool identity for every variant.
5. Stop at the declared budget.

Acceptance:

- the existing single invocation is one matrix member;
- identical variants compile once;
- every omitted variant has an explicit budget or compatibility reason.

### Task 7.5: Idiom atlas and bounded synthesis

Files:

- create `automation/compiler_idioms.py`;
- create `automation/test_compiler_idioms.py`;
- extend `automation/search_lanes.py`.

Work:

1. Mine proven local source/object pairs into typed compiler idioms.
2. Bind each idiom to compiler and target identities.
3. Apply only structurally compatible substitutions.
4. Synthesize only bounded residual regions with explicit grammars.
5. Route all results through the ordinary evaluator.

Acceptance:

- idioms never cross compiler identities;
- synthesis space and budget are manifest fields;
- no result bypasses scoring or archive rules.

Commit boundaries: one commit for each adapter group.

## 12. Phase 8: Operator, subset and connector wiring

### Task 8.1: Add a safe CLI

Files:

- create `automation/search_cli.py`;
- create `automation/test_search_subset.py`;
- register the test in `automation/run_selftests.py`.

Commands:

- `plan --records <explicit ids> --lanes <explicit lanes>`;
- `run --manifest <path>`;
- `resume --run <path>`;
- `stop --run <path>`;
- `status --run <path>`;
- `verify-ledger --run <path>`;
- `fork --run <path> --config <path>`.

Work:

1. Require explicit record IDs or an explicit saved subset artifact.
2. Forbid implicit fallback to all todo, near, escalated or deferred records.
3. Make planning read-only.
4. Keep run output beneath the designed run root.
5. Expose machine-readable status and receipts.

Acceptance:

- one-record, multiple-record and empty-subset cases are tested;
- attempts to read another queue state fail;
- stop and resume preserve exact task boundaries.

### Task 8.2: Integrate the supervisor narrowly

Files:

- edit current dirty `automation/permuter_supervisor.py` only after root
  records its existing diff;
- add focused supervisor tests.

Work:

1. Replace log-parsed search control with the coordinator adapter when enabled.
2. Preserve legacy behavior behind an explicit compatibility mode during
   rollout.
3. Prevent duplicate scheduling between legacy supervisor and coordinator.
4. Route score zero to the existing landing gate.
5. Never re-run the full build merely to upload or archive an unchanged
   isolated result.

Acceptance:

- legacy fixtures still pass;
- instrumented mode uses typed events;
- no state is authoritative in the supervisor process.

### Task 8.3: Add connector surfaces

Files:

- edit `automation/mcp/commands_client.py`;
- edit `automation/mcp/sotn_cmd_mcp.py`;
- edit `automation/test_connector_surfaces.py`.

Surfaces:

- start a long search job from a manifest;
- status and stop by run ID;
- verify a ledger;
- plan a named explicit subset.

Work:

1. Keep argv validation narrow.
2. Register long execution through `job_start`.
3. Do not expose arbitrary paths or a general command.
4. Mark mutating surfaces correctly.
5. Require a connector restart after landing.

Acceptance:

- connector inventory tests pass;
- traversal and unrecognized lane arguments refuse;
- long runs return job IDs rather than blocking transport.

Commit boundary: CLI, supervisor and connector wiring.

## 13. Phase 9: Documentation and roadmap reconciliation

Files:

- surgically update `docs/HARNESS-ARCHITECTURE.md`;
- surgically update `docs/TOOLING.md`;
- surgically update `automation/README.md`;
- surgically update `ROADMAP.md`.

Work:

1. Document authority, lifecycle, storage and recovery.
2. Document subset syntax, tier enforcement, receipts and score-zero handling.
3. Record every surprising implementation finding.
4. Mark #274 complete only after validation.
5. Re-evaluate #257 through #273 against measured lane coverage.
6. Mark tasks superseded or re-scoped with evidence, never delete them.

Acceptance:

- operator docs contain a crash-resume procedure;
- roadmap outcomes describe what exists, not future intent;
- no existing document is wholesale rewritten.

## 13A. Evidence-derived search supplement

> **For agentic workers:** implement each task with a focused failing test,
> stop at its commit boundary, and return the exact changed paths and test
> verdict. Subagents do not build, use git, write the queue or edit `src/`.

**Goal:** turn proven draft corrections and the exact PSX compiler into
reusable, compiler-bound search evidence, then consume that evidence in the
existing lane and ledger contracts.

**Architecture:** two producers publish immutable compiler observations: a
provenance-strict draft-to-landed miner and an exact `cc1-psx-26`
micro-corpus. Deterministic lane adapters consume those observations through
the ordinary candidate evaluator. A separate read-only aggregator learns from
completed ledger lineages without changing an active run.

**Tech stack:** Python standard library, the existing PSX preprocessing and
compiler pipeline, vendored decomp-permuter scorer types, JSON schema and the
content-addressed search archive.

**Spec:** `docs/superpowers/specs/2026-08-26-instrumented-search-system-design.md`

### Task 9.1: Exact compiler micro-harness and real scorer fixtures

**Files:**

- create `automation/compiler_corpus.py`;
- create `automation/test_compiler_corpus.py`;
- replace `automation/fixtures/search/scorer-v1.json`;
- modify `tools/decomp-permuter/test/compile.sh`;
- modify `tools/decomp-permuter/test/test_perm.py`;
- modify `automation/test_search_permuter_vendor.py`.

**Interfaces:**

- produces `CompilerPipelineIdentity` with executable, executable hash,
  ordered arguments, environment defines and tool hashes;
- produces `compile_snippet(source: str, case_id: str) -> CorpusObservation`;
- `CorpusObservation` carries source hash, object hash, disassembly hash,
  score vector and pipeline identity;
- consumes no queue state and never invokes a full repository build.

```python
@dataclass(frozen=True)
class CompilerPipelineIdentity:
    executable: str
    executable_hash: str
    arguments: tuple[str, ...]
    environment_defines: tuple[str, ...]
    tool_hashes: tuple[tuple[str, str], ...]
```

- [ ] **Step 1: Make the vendored compatibility surface runnable**

Change the test compiler from the unavailable big-endian executable to the
little-endian cross compiler already required by this repository:

```bash
#!/bin/bash
mipsel-linux-gnu-gcc -O2 -fno-PIC -fno-common -ffreestanding \
  -mno-shared -mno-abicalls -G 0 -c "$@"
```

Keep the wrapper's focused rerun diagnostic. Do not convert a missing compiler
into a passing skip.

- [ ] **Step 2: Prove the vendored suite and subset runner**

Run:

```text
run_automation run_selftests.py --only test_selftest_runner.py \
  --only test_search_permuter_vendor.py --jobs 2
```

Expected: both suites pass. A missing executable must name that executable in
the final diagnostic line.

- [ ] **Step 3: Write the compiler-corpus failure tests**

The focused test constructs two identical cases and one changed case:

```python
first = compile_snippet("int f(int x) { return x + 1; }", "plus-one-a")
retry = compile_snippet("int f(int x) { return x + 1; }", "plus-one-b")
changed = compile_snippet("int f(int x) { return x + 2; }", "plus-two")
assert first.object_hash == retry.object_hash
assert first.disassembly_hash == retry.disassembly_hash
assert first.pipeline_identity == retry.pipeline_identity
assert changed.source_hash != first.source_hash
assert changed.object_hash != first.object_hash
```

The test also changes one compiler argument and asserts that the pipeline
identity changes before compilation.

- [ ] **Step 4: Implement one exact pipeline adapter**

`compiler_corpus.py` must use the repository's configured PSX stages and
record their hashes. It materializes all intermediates in one temporary
directory, validates every subprocess return code, hashes the final object and
normalized disassembly, then deletes the temporary directory. The stable
serialization is:

```python
@dataclass(frozen=True)
class CorpusObservation:
    case_id: str
    source_hash: str
    object_hash: str
    disassembly_hash: str
    pipeline_identity: str
    score: Mapping[str, object]
```

No path inside the temporary directory may appear in the record.

- [ ] **Step 5: Replace the synthetic scorer fixture**

Populate `scorer-v1.json` with actual observations covering exact match,
reordering, register allocation, stack differences, insertion, deletion and
compile failure. Each successful case carries real source, object,
disassembly, mismatch and compiler identities. Compile failure carries no fake
object hash or zero score.

- [ ] **Step 6: Run focused tests**

Run the compiler-corpus, vendored permuter, historical fixture and schema
suites through `run_selftests.py --only`. Expected: all pass without a full
repository build.

- [ ] **Step 7: Commit boundary**

Stage only the six paths named in this task and commit:
`feat: add exact compiler evidence fixtures`.

### Task 9.2: Provenance-strict draft-to-landed miner

**Files:**

- create `automation/draft_landed_miner.py`;
- create `automation/test_draft_landed_miner.py`;
- extend `automation/compiler_idioms.py`;
- extend `automation/test_compiler_idioms.py`;
- extend `automation/search-ledger.schema.json` only if the existing
  provenance record cannot represent the observation losslessly.

**Interfaces:**

- consumes candidate history, queue provenance and verified landing commits;
- produces `DraftLandedObservation` and zero or more
  `CompilerIdiomObservation` values;
- never chooses a "likely" draft when exact provenance is absent.

```python
@dataclass(frozen=True)
from search_types import ArtifactRef, GroupedPatch

@dataclass(frozen=True)
class CompilerIdiomObservation:
    observation_id: str
    compiler_identity: str
    before: ArtifactRef
    after: ArtifactRef
    grouped_patches: tuple[GroupedPatch, ...]
    supporting_pair_hashes: tuple[str, ...]

@dataclass(frozen=True)
class DraftLandedObservation:
    recipient_id: str
    draft: ArtifactRef
    landed: ArtifactRef
    landing_commit: str
    compiler_identity: str
    grouped_patches: tuple[GroupedPatch, ...]
    evidence: tuple[str, ...]
```

- [ ] **Step 1: Write refusal-first tests**

Fixtures cover an exact pair, two ambiguous draft generations, a missing
landing commit, mismatched recipients and a complete pair. The first four
cases must emit typed receipts and no observation.

- [ ] **Step 2: Implement exact endpoint resolution**

Resolve both artifacts from recorded provenance, confirm their content hashes
and recipient, confirm the landing commit contains the landed artifact, then
derive grouped patches. Do not read modification times or infer chronology
from filenames.

- [ ] **Step 3: Extract recurring transformations**

Normalize identifiers only where type and field evidence proves equivalence.
Keep declaration order, control-flow shape and expression shape as separate
features. An idiom observation records its support count and every contributing
pair hash.

- [ ] **Step 4: Measure rather than assume value**

For each mechanically applicable idiom, evaluate the original draft and the
rewritten draft through the same scorer identity. Publish the observation only
when the score vector improves or the rewrite produces an exact object hash.

- [ ] **Step 5: Run focused tests and commit**

Run both miner and idiom suites. Stage only this task's paths and commit:
`feat: mine proven draft corrections`.

### Task 9.3: Context search and cross-version semantic donors

**Files:**

- create `automation/search_contexts.py`;
- create `automation/test_search_contexts.py`;
- extend `automation/search_lanes.py`;
- extend `automation/test_search_lanes.py`.

**Interfaces:**

- `context_variants(manifest, recipient) -> tuple[ContextVariant, ...]`;
- `cross_version_donors(recipient) -> tuple[DonorEvidence, ...]`;
- every variant and donor has a content identity and bounded ordinal;
- results flow through the coordinator's ordinary candidate and receipt APIs.

```python
@dataclass(frozen=True)
from search_types import ArtifactRef

@dataclass(frozen=True)
class DonorEvidence:
    donor_id: str
    recipient_id: str
    version: str
    source: ArtifactRef
    match_kind: str
    signature: str

@dataclass(frozen=True)
class ContextVariant:
    context_id: str
    kind: str
    artifacts: tuple[ArtifactRef, ...]
    provenance: tuple[str, ...]
    ordinal: int
```

- [ ] **Step 1: Write subset and no-fallback tests**

A two-recipient manifest must produce no context task for a third recipient.
An unknown symbol and an incompatible version must emit explicit inapplicable
receipts rather than falling back to another queue record.

- [ ] **Step 2: Implement deterministic m2c context variants**

Enumerate minimal, declarations, whole-TU and donor-enriched contexts in stable
order. Deduplicate identical m2c output before compilation. Charge the manifest
budget per unique compiled candidate, not per identical context input.

- [ ] **Step 3: Implement semantic donor discovery**

Search US, HD, PSPEU and Saturn by exact symbol first, then bounded instruction,
CFG and dataflow signatures. Preserve version, source artifact and match reason.
Never transplant version-specific bytes, registers or branch displacements.

- [ ] **Step 4: Rank one model context package**

Before Tier 5, rank context packages using declaration closure, donor
compatibility and measured m2c score. Send one selected package to a model task.
The selection and rejected alternatives are durable task provenance.

- [ ] **Step 5: Run focused tests and commit**

Run context, lane and coordinator suites. Stage only this task's paths and
commit: `feat: search context and version donors`.

### Task 9.4: Struct-layout evidence lane

**Files:**

- create `automation/struct_layout_inference.py`;
- create `automation/test_struct_layout_inference.py`;
- extend `automation/search_lanes.py`;
- extend `automation/test_search_lanes.py`.

**Interfaces:**

- consumes matched source field accesses, assembly load/store widths and
  existing `member_types.py` results;
- produces `StructLayoutProposal` or a typed conflict receipt;
- proposals are compiler-bound evidence and cannot edit headers directly.

```python
@dataclass(frozen=True)
from search_types import ArtifactRef

@dataclass(frozen=True)
class FieldConstraint:
    offset: int
    width: int
    access_kind: str
    source: ArtifactRef

@dataclass(frozen=True)
class StructLayoutProposal:
    type_name: str
    compiler_identity: str
    fields: tuple[FieldConstraint, ...]
    supporting_artifacts: tuple[ArtifactRef, ...]
    conflicts: tuple[str, ...]
```

- [ ] **Step 1: Write constraint and conflict tests**

Cover compatible byte/halfword/word accesses, overlapping incompatible widths,
union alternatives and an offset already named by an existing member.

- [ ] **Step 2: Implement deterministic constraint aggregation**

Group observations by type identity and compiler, sort by offset and width, and
retain every source artifact. Never merge observations across compiler
identities.

- [ ] **Step 3: Route proposals through evaluation**

Render a temporary candidate declaration or typed expression, compile and
score it, and archive the result. A proposal is not proof until an evaluation
records the effect.

- [ ] **Step 4: Run focused tests and commit**

Run layout, member-type, lane and schema suites. Stage only this task's paths
and commit: `feat: infer typed layout evidence`.

### Task 9.5: Completed-lineage success miner

**Files:**

- create `automation/search_patterns.py`;
- create `automation/test_search_patterns.py`;
- extend `automation/search_coordinator.py` only to read a prior immutable
  recommendation artifact at run creation;
- extend `automation/test_search_coordinator.py`.

**Interfaces:**

- consumes validated, completed ledger prefixes only;
- produces an immutable `SearchPatternReport`;
- cannot modify an active manifest, queue status or ledger history.

```python
from search_types import ArtifactRef

@dataclass(frozen=True)
class SearchPatternReport:
    report_id: str
    source_ledgers: tuple[str, ...]
    recommendations: tuple[Mapping[str, object], ...]
    artifact: ArtifactRef
```

- [ ] **Step 1: Write leakage-prevention tests**

A report generated during run A cannot change run A scheduling. Run B may use
that report only when its manifest records the report artifact hash. Corrupt or
partial ledgers are rejected.

- [ ] **Step 2: Aggregate winning evidence**

Rank mutation pass, grouped patch, lane, overlay, function archetype and first
divergence combinations. Record sample count, successes, failures and exact
source ledger hashes. Do not publish a recommendation from one observation.

- [ ] **Step 3: Publish derivation summaries**

Render bounded queue-note text from completed winning lineages. Publishing a
note remains a separate explicit queue operation; the miner itself is
read-only.

- [ ] **Step 4: Run focused tests and commit**

Run pattern, recovery, ledger and coordinator suites. Stage only this task's
paths and commit: `feat: aggregate successful search lineages`.

### Deferred subsystem: data-segment search

Do not generalize `CandidateRecord` during this delivery. Open a separate
design after function-search validation for byte-serialization candidates,
data-specific score vectors and data recipient identities. Preserve the
suggestion in `ROADMAP.md`; do not mark it complete or superseded.

## 14. Validation sequence

Luna may run focused Python tests after each edit. Luna must not build.

Root validation after receiving the implementation:

1. Inspect `git_state` and exact diffs, including each pre-existing dirty path.
2. Read every new module and every modified hunk.
3. Run focused tests for the touched phase.
4. Run vendored permuter tests.
5. Run `python3 automation/test_connector_surfaces.py` after MCP changes.
6. Run `python3 automation/run_selftests.py` after automation changes.
7. Run the historical fixture and fault-injection recovery suite.
8. Run a read-only one-record shadow plan.
9. Run one bounded isolated search without applying source.
10. Only after all code and docs are final, start `make_build` as a job and
    poll it.
11. Run `verify_build` and require every expected checksum.
12. Update the final roadmap outcome.
13. Stage explicit coherent paths only.
14. Commit.
15. Perform the fresh exact pre-push audit required by AGENTS.md.
16. Run a fresh `make_build -> verify_build` after the final commit.
17. Push to origin through `job_start` and confirm the branch is no longer
    ahead.

Do not repeat a focused suite or build unless state changed after its proof.

## 15. Luna handoff boundaries

Luna receives:

- the approved design and schema;
- this plan;
- the current dirty-path inventory;
- explicit permission to edit only the assigned phase files;
- permission to run non-build focused tests through the connector;
- a prohibition on git, builds, queue writes, source landing and pushing;
- a requirement to report every changed file, test result, unresolved issue
  and deviation from plan.

The initial Luna assignment covers Phases 0 through 6, the ledger and
instrumented-search core. Lane adapters and connector wiring are a second
bounded assignment after root reviews the core. This prevents a broad first
pass from entangling the already dirty supervisor and lane scripts before the
authority and recovery foundation is proven.

## 16. Root review checklist

For every Luna batch, root verifies:

- implementation matches the schema rather than weakening it;
- canonicalization and hashes are unambiguous;
- artifact-before-event durability order is real;
- recovery uses no hidden process state;
- task retries keep identity, seed and budget ordinal;
- commit order is deterministic under concurrent completion;
- cache identity includes recipient and evaluator;
- scalar elite cannot be evicted by Pareto capping;
- donor scores are never inherited;
- grouped patches are atomic;
- changed inputs refuse resume;
- checkpoints are optional;
- score zero cannot write `src/`;
- subset selection has no fallback;
- cheaper incomplete tiers block higher tiers;
- all inapplicable or exhausted lanes produce receipts;
- existing dirty work was preserved.
