# Instrumentation Completion Implementation Plan

> Execution: lead-owned inline implementation. The owner authorized implementation order and design decisions on 2026-09-04. No additional design approval or worker delegation is required or inferred.

**Goal:** Complete ROADMAP #283 through #292 with executable providers, measured candidate evaluation, trustworthy recovery and provenance, and a reproducible knowledge-transfer acceptance experiment.

**2026-09-05 owner sequencing correction:** Model/fleet expansion advanced before
the systemic programmatic path was complete. That sequencing is retracted.
Preserve the implemented model code and telemetry as evidence, defer its
production activation, and complete deterministic factory wiring, crash
recovery, knowledge transfer and consolidated end-to-end acceptance first.
Neither the previous completion entries nor the focused suites establish this
end-to-end boundary. Do not claim the prior automation is all complete.

**Architecture:** Retain the canonical factory, manifest, archive, coordinator, ledger and recovery authorities. Correct the local executor and renderer first. Add an immutable target compiler recipe and isolated evaluation service, then bind concrete lane providers at factory creation and reconstruct them at start/resume. Keep proposal discovery read-only with respect to source and queue; evaluated score zero remains pending the existing full-oracle landing authority.

**Tech Stack:** Existing Python standard-library harness, vendored decomp-permuter and m2c, repository target compiler pipeline, sotn-cmd jobs.

**Spec:** `docs/audit/2026-09-04-automation-instrumentation-review.md`, extending `docs/superpowers/specs/2026-08-30-production-indexed-search-runtime-design.md`.

## Global constraints

- The owner permits direct native file reads and edits. Git uses sotn-cmd; long operations run as jobs.
- Preserve all existing work and all superseded evidence.
- No source or queue changes during proposal/evaluation acceptance.
- Preserve the 113-artifact baseline from the just-completed review; do not repeat it at implementation start.
- Every claimed production capability must have immutable input/tool binding, concrete dispatch, reconstruction, recovery, ordinary receipts and public reachability.
- No em dashes or emojis in new content.
- No model calls until the programmatic path is qualified. Model replay tests use durable deterministic fixture responses; paid execution is not part of acceptance.
- Run focused regressions after edits and one consolidated suite when the final implementation stabilizes.
- Stage explicit paths and perform the exact clean-tree build/oracle/push gate before publication.

## Task 1: Correct executable local semantics (#285, #289)

**Files:** `automation/search_target_renderer.py`, `automation/test_search_target_renderer.py`, `automation/search_permuter_executor.py`, `automation/test_search_permuter_executor.py`.

**Interfaces:** preserve `deterministic_local_draft(...)` and `PermuterExecutor.__call__(request)`.

- [x] Add regressions for OR-immediate with overlapping bits and stack operations that change the return register; unsupported stack data is refused.
- [x] Exercise the complete executor call with process termination mocked only at the process boundary. Assert a typed response and actual process output parsing.
- [x] Run those new tests to confirm the pre-fix failures.
- [x] Render OR with its actual operator, refuse unproven stack traffic, and pass process return values by explicit named arguments.
- [x] Run both focused suites and retain the outcomes.

The process boundary must explicitly unpack:
```python
returncode, output, controlled_stop = self._run_process(...)
response = self._parse_output(..., output=output,
                              returncode=returncode,
                              controlled_stop=controlled_stop, ...)
```

## Task 2: Bind the real target evaluator (#284, #285)

**Files:** create `automation/search_evaluator.py` and `automation/test_search_evaluator.py`; integrate `automation/search_permuter_executor.py`, `automation/search_run_factory.py`, `automation/search_supervisor.py`.

**Interfaces:** Reuse the existing `CompilerPipelineIdentity` and `compiler_corpus` pipeline rather than introducing a duplicate recipe; `IsolatedEvaluator` consumes archived source and target objects and returns an archived typed evaluation. It accepts no caller executable or shell body.

- [ ] Derive fixed argv stages from the repository-owned version compiler configuration and hash executables, flags, environment and include dependencies.
- [ ] Compile only inside isolated scratch, preserve compiler diagnostics and produced object bytes, and reject the wrong object architecture.
- [x] Bind the evaluator identity into the factory manifest and revalidate before execution.
- [x] Schedule evaluated candidate results through coordinator tasks; distinguish generated, evaluated, budget-skipped and pending-oracle outcomes.
- [x] Prove a known target candidate and a compiling mismatch through the real isolated compiler without editing source or queue.

Proof so far: renderer/executor regressions passed in job `run_automation-213737-85`; selected-function and branch-rebasing compiler tests passed in `run_automation-024117-85`; public factory/start evaluation, durable retry, oracle gating, supervisor and schema passed in `run_automation-024514-85`. Candidate sampling/disposition and the permuter compiler binding remain open.

September 6 update: the earlier sampling/binding statement is superseded by
factory-bound evaluation, measured minima and explicit unexamined dispositions.
The live `programmatic-wiring-20260906` completed, exposing worker failures that
the original funnel hid. Seed validation, durable failed-worker prefixes and
full-overlay source transport now run through ordinary receipts. The successor
`programmatic-transplant-20260906` adds concrete automatic transplant preparation.
Neither a completed run nor an isolated zero is full-oracle match evidence.

## Task 3: Implement measured strategies and recovery (#286, #287, #288)

**Files:** `automation/search_permuter_executor.py`, `automation/search_permuter_lanes.py`, `automation/search_mutations.py`, vendor instrumentation where needed, and their focused tests.

**Interfaces:** existing provider request/result/checkpoint records remain authoritative; strategy identity is distinct from scorer identity.

- [ ] Use the vendor's deterministic per-task entry point and structured mutation/score events instead of inferring iterations from output directories.
- [x] Random search derives each mutation seed from immutable session input and task ordinal.
- [x] Targeted search restricts the mutation family explicitly; recombination uses `recombine_grouped_patches`; minimization uses `minimize_grouped_patch` with the real evaluator.
- [x] Persist actual candidate source, parent, mutation, iteration and evaluation identities.
- [x] Separate immutable session inputs from phase-specific scratch. Resume from durable task progress without replaying already evaluated work.
- [ ] Compare interrupted and uninterrupted sequences and budgets; test nonconsecutive improvement iterations.

## Task 4: Close every provider and public acceptance path (#283)

**Files:** `automation/search_run_factory.py`, `automation/search_provider_lanes.py`, generated/model/idiom provider modules, `automation/search_supervisor.py`, `automation/search_recovery.py`, `automation/search_cli.py`, `automation/mcp/commands_client.py`, `automation/mcp/sotn_cmd_mcp.py`, focused integration tests.

**Interfaces:** factory publishes the existing `provider_state_document` envelope from concrete typed providers. Public create/start/resume reconstructs it without callback injection.

- [ ] Capture target-only context and actual immutable provider inputs for all nine missing lanes.
- [ ] Add transitive executable and input identities to lane bindings and seed derivation.
- [ ] Publish provider state with crash-safe exact retries, then verify it before task scheduling.
- [ ] Replace obsolete callback-injecting factory tests with production-bound fixtures.
- [ ] Complete indexed snapshot publication and typed runtime selection, avoiding implicit latest selection.
- [ ] Make the production audit and public lane execution matrix pass without allowlisting missing implementations as values.

## Task 5: Provider telemetry, corpus scope and learning experiment (#290, #291, #292)

**Files:** model executor/lane records and tests; `automation/search_indexed_runtime.py`, `automation/search_patterns.py`; create `automation/search_production_acceptance.py` and `automation/test_search_production_acceptance.py`.

**Interfaces:** versioned provider telemetry accompanies existing response artifacts; explicit contributing-run identities define corpus membership; `run_production_acceptance` emits an immutable report.

- [ ] Preserve sanitized response metadata, usage, provider model, finish reason and exact transport outcome; absent measurements remain null.
- [ ] Keep operational timing outside deterministic replay identity.
- [ ] Publish an explicit immutable contributing-run set and retain exclusion/refusal records.
- [ ] Derive the recipient/lane funnel from ledger evidence with denominators and explicit unevaluated dispositions.
- [ ] Run equal-budget retrieval/control arms with held-out recipient families; archive corpus membership, candidate/evaluator identities and measured transfer.
- [ ] Expose acceptance as a bounded connector job and prove stop/recovery/replay plus source/queue input preservation.

## Task 6: Consolidation and landing

- [ ] Reconcile every review finding against measured implementation; explicitly retract any disproven diagnosis.
- [ ] Update existing documentation surgically and mark roadmap outcomes with exact proof.
- [ ] Run connector surfaces and consolidated automation selftests once on the stable final inputs.
- [ ] Audit every touched generated store and explicit staged path.
- [ ] Commit, require clean state, run fresh make_build then verify_build, push to origin as a job, and confirm synchronization.
