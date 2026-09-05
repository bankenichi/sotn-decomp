# Automation instrumentation review, 2026-09-04

Review scope: `automation/instrumented-search` at `d22c3e61ff23f60aab30ed2da81143aa4139b9bd`, including the twelve modified tracked files and untracked `automation/m2c_revision_executor.py` present when this review began. The findings concern the working tree, not a claim that the ongoing tranche was ready to land. No implementation fixes or live model/search dispatch were performed.

The harness has a substantial evidence-preservation foundation. Immutable artifacts, exact subset selection, semantic ledger validation, durable terminal events and strict drift refusals directly support this fork's purpose. The largest remaining risk is that preserved evidence can accurately describe an incomplete or incorrectly executed experiment. Completion, candidate production, candidate evaluation and knowledge reuse need separate acceptance gates.

## Measured state

- The initial on-disk US oracle returned 113/113, with no failed artifacts. Final managed build job `make_build-212548-85` succeeded; the immediately following oracle again returned 113/113 with no failures.
- The live queue contains 983 records: 433 matched, 380 todo, 123 escalated, 41 deferred, 6 near and 0 claimed.
- Canonical WSL consolidated selftests, job `run_automation-212055-85`, passed 98/101 suites in 158.8 seconds of runner wall time.
- Failures: `readme_status.py --self-test` reports generated living-document drift; `test_search_production_audit.py` reports eleven unclosed lanes where its expected baseline lists nine; two cases in `test_search_run_factory.py` inject callbacks that the production reconstruction boundary now intentionally refuses. Focused diagnosis confirmed both factory errors are the explicit caller-override refusal. These errors are not evidence that ordinary non-indexed starts universally fail.
- Public status and ledger verification of `task257-indexed-runtime-gate-v1` succeeded: 27 events, sequence 26, terminal hash `sha256:f1b0cd536a4ffa3a9dc3d190e2d43338019cb1c1ede9a3aa628cda2f58dc46d7`. Its one-record manifest selects six non-indexed lanes. All six receipts are inapplicable; the ledger contains no candidate or evaluation events.
- The canonical `nonmatchings/search-evidence` directory was absent at inspection. The advertised exhaustive acceptance runner and its test are also absent from the automation directory. The current production plan leaves its acceptance checkboxes open.
- Implementation findings below are source-level deductions unless explicitly identified above as executed tests. No live permuter search was needed to establish the argument-order, compiler-wrapper, algorithm-routing or scratch-collision defects.

## Findings

### IR1. P1: Nine provider lanes have reconstruction consumers but no factory producer

Evidence: `automation/search_run_factory.py:118`, `:995`, `:1072`; `automation/search_provider_lanes.py:323`, `:595`, `:626`, `:651`.

The factory accepts every advertised lane and generates a lane hash, but only the indexed lanes have the new runtime input binding. The other nine provider lanes fall through to `{"kind": "none"}`; their concrete provider modules and input state are not captured. Reconstruction requires a canonical `artifacts/provider-state` document. The factory neither constructs the providers nor calls the state serializer to publish that document.

Consequently a normally created model, permuter, m2c, idiom or bounded-synthesis run cannot use the existing reconstruction path successfully. A registry entry or a generic lane hash is not closure. The production audit also reports the two indexed lanes, but that static report alone is not enough to diagnose their exact missing boundary.

Recommendation: finish immutable provider construction and state publication inside the factory; bind executable bytes and all actual inputs; exercise create, start, stop, resume and verification through the public connector. Rework factory fixtures around that path rather than weakening the no-override policy. Finish Task 7 acceptance and make its report a required gate.

### IR2. P1 instrumentation gap: Production completion does not establish an evaluated search

Evidence: `automation/search_supervisor.py:1649`, `:2085`, `:2423`; `automation/search_run_factory.py:1031`; `automation/search_lanes.py:3626`.

Candidate child tasks only materialize the lane's supplied candidate; they do not invoke an evaluator or produce an evaluation event. The factory does not bind `search_evaluator`. The receipt labels all candidate IDs as `best_candidate_ids`, and fan-out selects the first two by hash, without measuring quality. The coordinator supports typed evaluations and oracle requests, but support is not production scheduling.

Read-only indexed discovery is an intentional boundary and should remain so. The missing piece is an explicit successor evaluation mode. Without it, completed runs cannot measure score improvement, confidently identify structural failures, select promising candidates, or supply the evaluator-bound lineage needed by the learning system.

Recommendation: add a factory-bound isolated evaluation service and coordinator-owned evaluation tasks, preserving exact compiler, flags, dependencies, target and scorer identity. Record evaluated, unevaluated due to budget, rejected and pending-oracle states distinctly. Keep discovery completion separate from evaluated exhaustion. Route a zero only to the existing locked full-oracle authority.

### IR3. P1: The concrete permuter invocation has two execution blockers

Evidence: `automation/search_permuter_executor.py:137`, `:486`, `:508`, `:1624`, `:1631`, `:1792`; `tools/decomp-permuter/src/compiler.py:43`.

First, `_run_process` returns `(returncode, output, controlled_stop)`, while `_parse_output` expects `(output, returncode, controlled_stop)`. `__call__` forwards the tuple positionally. A returned process result therefore sends an integer into the iteration regex and raises `TypeError` before a typed terminal result.

Second, the uncommitted runtime hardening requires the exact wrapper `exec cc "$@"`, fixes PATH to host system directories, and rejects other wrapper bytes. The vendor supplies `input.c -o output.o`. This requests host compilation/linking without `-c`, not the pinned SOTN target compiler pipeline. A normal function-only seed has no `main`, and even a successful host output is the wrong architecture.

Recommendation: unpack process results explicitly or use a typed result record. Replace the host wrapper with a repository-owned target compiler recipe derived from the actual build configuration, including object-only compilation and dependencies. Verify ELF target architecture and compile one known target fixture through the real executor. The passing executor suite currently exercises important pieces without proving this complete invocation.

### IR4. P1: Named permuter strategies currently select scoring metrics

Evidence: `automation/search_permuter_executor.py:110`, `:1163`; `tools/decomp-permuter/src/main.py:715`.

The executor maps random and targeted to `difflib`, and recombine and ddmin to `levenshtein`. It otherwise launches the same vendor command. The vendor documents `--algorithm` as its diff algorithm. Changing a scoring metric does not implement targeted mutation, grouped-patch recombination or delta debugging.

Recommendation: wire the existing mutation/recombination machinery or explicit new strategy drivers to their actual operations. Record strategy identity separately from scorer identity. Use behavioral fixtures where targeting restricts the mutation family, recombination requires two parents, and ddmin removes an unnecessary patch while preserving the measured improvement.

### IR5. P1: Concrete permuter resume collides with its own immutable scratch

Evidence: `automation/search_permuter_lanes.py:2018`; `automation/search_permuter_executor.py:1347`, `:1434`, `:1482`.

Start and resume derive the same scratch path from session/input identity. Materialization writes `executor-request.json` there with phase and request identity. Resume necessarily changes those bytes, while `_write_exact` refuses any different existing bytes. Thus a real resume reaches an existing-scratch refusal.

After that collision is fixed, reusing the saved initial random seed with the original `base.c` still restarts the sequence. No vendor RNG/cursor restoration or replay-skip is applied. Adding the prior iteration count to fresh log numbers does not resume search progress.

Recommendation: separate immutable session inputs from phase-specific work files and capture actual resumable search state. Test an interrupted run against uninterrupted execution, including candidate sequence, unique evaluations and cumulative budget. A checkpoint deserialization test is insufficient.

### IR6. P1: Permuter candidate iteration provenance is invented from output order

Evidence: `automation/search_permuter_executor.py:1657`, `:1703`.

Candidate output directories are sorted and enumerated, then their iteration is recorded as `start_iteration + index`. A candidate discovered at iteration 400 can become iteration 1. The ordinal is neither a measured iteration nor recovered from a vendor event. Immutable hashes would preserve the false attribution.

Recommendation: consume structured vendor events that bind source hash, actual iteration, parent, mutation and evaluator result. Store unknown where historical chronology is unavailable. Preserve the raw event artifact. Test improvements at nonconsecutive iterations and output names whose lexical ordering differs from discovery order.

### IR7. P1: The target renderer translates supported instructions incorrectly

Evidence: `automation/search_target_renderer.py:1195`, `:1203`, `:1235`.

A nonzero-register `ori` is rendered as addition. For `ori v0,a0,1; jr ra; nop`, the renderer can produce `return x + 1;`. At x=1 the target returns 1 and that expression returns 2. The same translator also drops every stack-based load/store, including loads that define the return value, without proving they are callee-save traffic.

Recommendation: implement bitwise OR distinctly or refuse it, and track register definitions through the supported instruction subset. Refuse stack data operations unless the ignored instruction is proven semantically irrelevant. Add the OR counterexample and a return-register stack reload fixture. A later checksum would reject a bad landing, but the proposal evidence should still accurately describe supported target semantics.

## Instrumentation gaps and recommended priorities

1. **Measure learning transfer, not just artifact integrity.** Use a frozen training corpus and held-out recipients grouped by function family, shared header and donor relationship. Compare the same search budget with and without retrieved evidence. Record unique evaluated candidates, useful score-component changes, compiler failures avoided, repeated known failures, and successful cross-recipient reuse. Keep oracle matches as one outcome, not the only outcome.

2. **Preserve provider economics and failure causes.** `search_model_executor.py:488` retains extracted content but discards the response envelope's usage, finish reason, returned model identity, reasoning and timing. It also groups rate limits/server errors as timeouts and socket timeouts as unavailability. Archive a sanitized envelope and typed transport outcome with request ID, status, token counts, timing, retry-after, finish reason and explicit missing values. Store operational timings separately from deterministic replay identity.

3. **Make corpus coverage explicit across runs.** `search_indexed_runtime.py:1859` mines only the gate snapshot. Publish an explicit immutable set of contributing runs, refusals, exclusions and superseded generations. Measure whether a newly understood failure becomes retrievable and changes the next applicable decision. A valid one-record smoke gate is not a representative knowledge corpus.

4. **Instrument the complete funnel by recipient and lane.** Report requested, applicable, executed, candidates generated, deduplicated, evaluated, improved, oracle-verified, rejected and learned outcomes with denominators. Separate missing wiring, unsupported target context, genuine inapplicability, budget exhaustion and infrastructure failure. Explain every unexamined candidate, including those beyond the two-child allowance.

5. **Finish behavioral acceptance before expanding the surface.** Task 7 already specifies much of the necessary acceptance. Add the concrete executor and renderer counterexamples above, then require a several-record public run with a useful candidate, a genuine negative result, restart recovery and measured input preservation. A structural export audit is useful but cannot prove strategy semantics or experimental value.

6. **Retain the deferred data work.** Roadmap #277 already owns data-segment instrumentation. After the function evaluation path is trustworthy, add byte-range ownership, serializer identity, data-specific differences and exact full-oracle routing. Preserve its separate scope rather than treating a function-lane receipt as data coverage.

Recommended order: fix IR3, IR5 and IR7; establish IR1 plus evaluated candidate flow from IR2; correct IR4 and IR6 before comparing strategies; then run a small held-out knowledge-reuse experiment and use its measured failures to choose further instrumentation. No new speculative lane is needed to establish whether the fork learns.

## Review disposition

The review and its recommendations are complete; implementation corrections remain open in ROADMAP. Existing worker edits were preserved. This report records a working-tree review, not production acceptance or a claim that the entire automation tree is correct.
