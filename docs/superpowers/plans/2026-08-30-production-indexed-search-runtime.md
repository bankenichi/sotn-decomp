# Production Indexed Search Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the complete evidence-corpus and four-platform donor system a permanent, typed, read-only production path through the instrumented search connector.

**Architecture:** Publish one explicit immutable indexed runtime generation from a completed integration gate and four pinned platform revisions. Bind that generation into factory evidence and the manifest tool identities, reconstruct real indexed adapters in the supervisor on start and resume, and route all results through the existing coordinator, archive, receipt, ledger, checkpoint, and recovery authorities.

**Tech Stack:** Python 3 dataclasses and standard library, existing content-addressed archive, JSON schema, instrumented search coordinator and supervisor, MCP connector, repository C and MIPS parsing utilities.

**Spec:** `docs/superpowers/specs/2026-08-30-production-indexed-search-runtime-design.md`

## Global Constraints

- Todo records are the only live queue scope until todo reaches zero.
- Production indexed search is read-only with respect to queue, source, builds, and checksum oracle.
- The manifest is the only recipient scope authority.
- Runtime, corpus, index, query, candidate, receipt, and replay identities are content-addressed.
- US, HD, PSPEU, and Saturn are scanned exactly once per generation.
- Recipient queries never scan a provider or repository tree.
- Every runtime input is explicit. There is no latest-generation or queue fallback.
- Existing non-indexed runs remain behaviorally compatible.
- All long production actions use connector jobs.
- No em dash or emoji is added to repository content.

---

### Task 1: Production call-graph closure and four-platform scanner

**Files:**
- Create: `automation/search_production_audit.py`
- Create: `automation/test_search_production_audit.py`
- Create: `automation/search_donor_scan.py`
- Create: `automation/test_search_donor_scan.py`
- Modify: `automation/asm_twin_finder.py` only if a reusable parser must be exposed without changing its CLI behavior

**Interfaces:**
- Consumes: repository root, four `DonorRevision` values, `ContentAddressedArchive`, canonical platform configuration files.
- Produces: `scan_repository_revision(revision, *, repo, archive) -> tuple[DonorEvidence, ...]`, `audit_production_exports(repo) -> ProductionAuditReport`.

- [ ] Write scanner tests with real miniature US, HD, PSPEU, and Saturn trees. Assert one scan per revision, canonical order, deterministic signatures, safe constants, declarations, source artifacts, no donor body, and refusal of raw bytes, registers, relocations, or branch displacements.
- [ ] Run `run_selftests.py --only test_search_donor_scan.py --only test_search_production_audit.py --jobs 2 --timeout 600` and retain the expected failing result.
- [ ] Implement strict platform root discovery from explicit version configuration, full revision validation, deterministic C and assembly parsing, normalized instruction, CFG and dataflow signatures, declaration closure, compatibility facts, and immutable archive references.
- [ ] Implement an AST-based export audit for the tranche modules. An exported non-dataclass production callable must have a production caller chain ending at CLI or connector registration; allowlisted pure value constructors must carry an explicit annotation in the audit table.
- [ ] Re-run the focused suites once after the final Task 1 edit. Require every platform and every new export classification to pass.

### Task 2: Immutable indexed runtime publication and loading

**Files:**
- Create: `automation/search_indexed_runtime.py`
- Create: `automation/test_search_indexed_runtime.py`
- Modify: `automation/search_evidence_corpus.py`
- Modify: `automation/search_patterns.py`

**Interfaces:**
- Consumes: exact completed gate run root, four pinned revisions, real scanner, completed ledger contexts, lesson citations, scorer taxonomy, corpus and donor builders.
- Produces:
  - `IndexedRuntimeBinding`
  - `IndexedRuntimeGeneration`
  - `publish_indexed_runtime(gate_run_id, revisions, *, repo) -> IndexedRuntimeGeneration`
  - `load_indexed_runtime(runtime_id, *, repo) -> IndexedRuntimeGeneration`
  - `verify_indexed_runtime(generation, *, repo) -> None`

- [ ] Write failing tests for real gate validation, complete gate binding, corpus and index inclusion, exact four-revision requirement, publication idempotence, ordering independence, changed-input generation identity, partial publication recovery, archive collision, and corrupt, missing, stale, or wrong-root refusals.
- [ ] Run `run_selftests.py --only test_search_indexed_runtime.py --jobs 1 --timeout 600` and retain the failure.
- [ ] Implement a canonical global archive under `nonmatchings/search-evidence/indexed-runtimes/<runtime-id>`. Publish intent before artifacts, fsync file and directory boundaries, and make retry either reconstruct the exact winner or refuse inconsistent partial state.
- [ ] Build the corpus from the validated completed gate and real completed-lineage contexts. Preserve negative and refusal evidence and diagnose historical missing evaluators without promoting them.
- [ ] Build the donor index by invoking the production scanner exactly once for each pinned revision. Store the corpus, index, gate, scanner, signature, compiler, config, schema, renderer, and runtime identities in one self-verifying generation.
- [ ] Implement strict loader and verifier functions that revalidate every referenced artifact and exact binding without rescanning.
- [ ] Re-run the Task 2 focused suite once after the final edit.

### Task 3: Production target query and renderer

**Files:**
- Create: `automation/search_target_renderer.py`
- Create: `automation/test_search_target_renderer.py`
- Modify: `automation/search_donor_query.py`
- Modify: `automation/search_indexed_lane.py`
- Modify: `automation/test_search_donor_query.py`
- Modify: `automation/test_search_indexed_lane.py`

**Interfaces:**
- Consumes: manifest-bound runtime generation, archived target evidence, typed recipient, typed semantic claims.
- Produces:
  - `query_for_recipient(manifest, target_index, recipient) -> DonorQuery`
  - `render_target_candidate(manifest, target_index, recipient, claims) -> LaneCandidate | tuple[LaneCandidate, ...]`
  - `production_indexed_adapters(manifest, runtime, run_archive) -> LaneAdapters`

- [ ] Write failing tests for target-only signature construction, exact recipient binding, multi-platform compatible claims, deterministic rendering, complete source artifact identity, and typed unsupported-context refusal.
- [ ] Add negative tests proving donor bodies, registers, relocations, branch displacements, another recipient's target, and unarchived source cannot reach the renderer.
- [ ] Run the target renderer, donor query, indexed lane, and ordinary lane focused suites once and retain the expected failures.
- [ ] Implement target query construction from the run's archived target assembly and target index. No live queue or repository scan is permitted.
- [ ] Implement deterministic target rendering using target assembly, target declarations, and the local deterministic draft generator. Donor claims may guide semantic structure and declarations but may not supply version-specific source bytes.
- [ ] Return a typed `target_context_unsupported` refusal with full query provenance when no complete target translation can be rendered.
- [ ] Bind both `multi_donor` and `cfg_dataflow` callbacks through `indexed_lane_adapter` and return an ordinary `LaneAdapters` instance.
- [ ] Re-run the four focused suites once after the final Task 3 edit.

### Task 4: Factory and immutable run binding

**Files:**
- Modify: `automation/search_types.py`
- Modify: `automation/search-ledger.schema.json`
- Modify: `automation/search_run_factory.py`
- Modify: `automation/search_cli.py`
- Modify: `automation/test_search_schema.py`
- Modify: `automation/test_search_run_factory.py`
- Modify: `automation/test_search_subset.py`

**Interfaces:**
- Consumes: optional exact `runtime_id` at production run creation.
- Produces: `create_instrumented_run(..., runtime_id: str | None = None)` with runtime evidence archived and bound into manifest tool identities.

- [ ] Write failing tests that indexed lanes require an explicit valid runtime, non-indexed lanes reject an irrelevant runtime, runtime identity changes alter run seed and manifest identity, and same-name retries cannot change runtime.
- [ ] Add tests for complete evidence-index references and tamper detection of the runtime artifact, gate, corpus, donor index, scanner, query, and renderer identities.
- [ ] Run factory, schema, subset, and CLI focused suites once and retain the failures.
- [ ] Extend the factory intent and evidence index with an optional typed runtime binding. Add required runtime tool keys for indexed lanes and include them in seed computation.
- [ ] Preserve exact byte behavior for non-indexed creation. Refuse implicit latest selection and cross-root runtime references.
- [ ] Extend CLI creation with `--runtime-id` and fixed validation. Do not accept paths.
- [ ] Re-run the four focused suites once after the final Task 4 edit.

### Task 5: Supervisor, ledger, stop, recovery, and replay

**Files:**
- Modify: `automation/search_supervisor.py`
- Modify: `automation/search_recovery.py`
- Modify: `automation/search_coordinator.py` only if a missing typed disposition cannot use the existing receipt protocol
- Modify: `automation/test_search_supervisor.py`
- Modify: `automation/test_search_recovery.py`
- Modify: `automation/test_search_coordinator.py`
- Modify: `automation/test_search_ledger.py`

**Interfaces:**
- Consumes: manifest and factory-archived runtime binding.
- Produces: automatic production adapter reconstruction on start and resume, with no caller callback injection.

- [ ] Write failing tests for automatic adapter reconstruction, explicit rejection of production callback overrides, exact query and candidate receipt durability, and runtime revalidation before every fresh or resumed task.
- [ ] Add one-shot fault tests before and after runtime load, query result archive, lane-result archive, task terminal commit, checkpoint commit, stop commit, and resume commit.
- [ ] Assert replay creates no duplicate query, task, receipt, budget, or terminal events and performs no rescan.
- [ ] Run supervisor, recovery, coordinator, and ledger focused suites once and retain the failures.
- [ ] Load production adapters after factory archive verification and before task scheduling. Use the same adapters for fresh and resumed execution.
- [ ] Persist typed query refusals and unsupported renderer outcomes through ordinary lane receipts. Keep coordinator task and budget authority unchanged.
- [ ] Re-run the four focused suites once after the final Task 5 edit.

### Task 6: Typed connector production control

**Files:**
- Modify: `automation/mcp/commands_client.py`
- Modify: `automation/mcp/sotn_cmd_mcp.py`
- Modify: `automation/test_connector_surfaces.py`
- Modify: `automation/test_search_cli.py` if present, otherwise keep CLI assertions in the factory suite

**Interfaces:**
- Produces:
  - `search_publish_indexed_runtime(gate_run_id, revisions)`
  - `search_verify_indexed_runtime(runtime_id)`
  - extended `search_create_instrumented(..., runtime_id=None)`
  - existing start, stop, resume, status, and ledger verification remain unchanged

- [ ] Write failing connector tests for discovery and callability, exact full revisions, typed IDs, no arbitrary paths or argv, background publication jobs, and connector restart reconstruction.
- [ ] Implement fixed argv builders and dedicated MCP tools. Register every executable production script and test, but keep pure library modules off the generic automation allowlist.
- [ ] Run `test_connector_surfaces.py` and the exact CLI/factory connector coverage once after the final edit.

### Task 7: Exhaustive production acceptance and real Task #257 execution

**Files:**
- Create: `automation/search_production_acceptance.py`
- Create: `automation/test_search_production_acceptance.py`
- Modify: `automation/run_selftests.py` only if serial isolation is required
- Modify: `automation/README.md`
- Modify: `docs/HARNESS-ARCHITECTURE.md`
- Modify: `docs/CONNECTORS.md`
- Modify: `docs/TOOLING.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Produces: `run_production_acceptance(...) -> ProductionAcceptanceReport` and one typed connector action for the exhaustive acceptance job.

- [ ] Implement the call-graph closure gate. It must fail if any tranche export is test-only, callback-only, or unreachable from production.
- [ ] Implement the full scanner, corpus, query-disposition, adapter, factory, connector, corruption, fault-point, stop, recovery, resume, replay, and idempotence matrix from the design.
- [ ] Capture before-state hashes for selected queue records, queue counts, tracked source and build inputs. The acceptance runner may write only immutable search evidence and run artifacts.
- [ ] Publish and verify one runtime from completed gate run `task257-indexed-runtime-gate-v1`.
- [ ] Create a several-record Task #257 run using todo records from distinct overlays and both indexed lanes. Start it through the connector, stop it during an active boundary, verify the ledger, resume it, verify terminal completion, then replay status and verification.
- [ ] Re-run the identical query set and require byte-identical query, candidate or refusal, receipt, ledger-terminal, and runtime identities with zero rescans.
- [ ] Prove selected queue records and aggregate counts are unchanged, Git tracked source and build inputs are unchanged, no checksum oracle was invoked, and no claim is stranded.
- [ ] Run the affected focused matrix once after the final source edit, then run the full consolidated automation selftests once.
- [ ] Update documentation and ROADMAP with measured counts and exact runtime and run identities. Do not claim completeness if the production audit reports any unreachable export.
- [ ] If code or tracked documentation changed, use explicit-path staging, commit, perform the mandatory fresh clean-tree build and 113-artifact oracle, push through a background job, and confirm branch synchronization.

### Task 8: Close every advertised lane

**Files:**
- Create: `automation/search_generated_lanes.py`
- Create: `automation/test_search_generated_lanes.py`
- Create: `automation/search_provider_lanes.py`
- Create: `automation/test_search_provider_lanes.py`
- Modify: `automation/search_lanes.py`
- Modify: `automation/search_supervisor.py`
- Modify: `automation/search_run_factory.py`
- Modify: `automation/search_types.py`
- Modify: `automation/test_search_lanes.py`
- Modify: `automation/test_search_supervisor.py`
- Modify: `automation/test_search_run_factory.py`

**Interfaces:**
- Produces production adapters for `m2c_ensemble`, `idiom_atlas`, `bounded_synthesis`, four permuter lanes, `model_fleet`, and `model_expensive`.

- [ ] Write a failing table-driven test asserting every member of `search_types.LANES` has a factory tool binding, supervisor adapter or built-in dispatcher, ordinary lane outcome, and receipt path.
- [ ] Implement `m2c_ensemble` with the pinned vendored revision matrix, target-only inputs, deterministic output deduplication, and per-unique-candidate budget charging.
- [ ] Implement `idiom_atlas` by wiring `mine_draft_landed`, compiler-idiom measurement and deduplication, corpus selection, applicability checking, and grouped-patch replay.
- [ ] Implement bounded synthesis over target-derived expressions, statements, declaration shapes, and control-flow forms under immutable manifest budgets.
- [ ] Implement all four permuter providers with isolated scratch artifacts, pinned seed/weights/algorithm, bounded work, checkpoint recovery, and no source or queue writes.
- [ ] Implement both model providers as proposal-only calls with complete provider/model/prompt/reasoning/budget/response identities, durable result handoff, and typed unavailable-provider refusal.
- [ ] Route all nine through ordinary `execute_task`, candidate fan-out, receipts, ledger, stop, and resume. Remove no lane merely to satisfy the audit.
- [ ] Run generated-provider, lanes, factory, supervisor, coordinator, recovery, permuter-vendor, compiler-idiom, and draft-miner suites once after the final edit.
- [ ] Extend production acceptance to execute all local providers and the deterministic model-provider replay, and require the export and lane closure audits to report zero unreachable surfaces.

