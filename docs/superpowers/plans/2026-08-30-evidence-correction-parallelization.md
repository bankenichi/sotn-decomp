# Evidence Correction Parallelization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the reviewed evidence-corpus and donor-index corrections, then implement verified donor queries and the semantic-only indexed lane adapter without overlapping ownership or repeated validation.

**Architecture:** GLM released the first six-path correction after entering the pattern validator before seeing the attempted two-path release. Root review found a second bounded correction tranche that also requires `search_lanes.py` and its focused test. Because GLM is temporarily unavailable, one Luna max worker owns those eight paths through R42 while root works only on specifications and documentation. Once root accepts the correction tranche, a later Luna max worker implements the compiler binding, followed by query records and archive verification in a focused `search_donor_query.py` module. Root freezes and accepts that public interface before another worker implements the lane adapter against it. Root alone owns orchestration, review, documentation, commits, builds, oracle calls, and pushes.

**Tech Stack:** Python 3 dataclasses, immutable mappings and tuples, the existing content-addressed archive, canonical JSON and hash helpers, `unittest`, and the `sotn-cmd` connector.

**Spec:** `docs/superpowers/plans/2026-08-28-evidence-corpus-donor-index.md`, amended by findings R19 through R42 in `.zcode/parallel-coordination.md`.

## Global Constraints

- Read `AGENTS.md`, `ROADMAP.md`, the source plan, and `.zcode/parallel-coordination.md` before every worker turn.
- The shared ledger's latest append-only ownership fence is authoritative.
- Workers perform substantive implementation only. Root retains planning, orchestration, documentation, review, final acceptance, Git landing, and push authority.
- No worker runs a build or checksum oracle. Focused automation tests are allowed through `sotn-cmd`. The worker that makes the final R36 through R42 edit may run the one consolidated automation suite; root treats that proof as current and does not repeat it unless a relevant file changes.
- No queue, source, candidate store, generated documentation, connector, or donor source tree mutation belongs to these tasks unless root adds a later explicit fence.
- No task starts while any owned path is dirty under another worker.
- Preserve every record and refusal. Never remove failed or superseded evidence from scope.
- Use no em dash or emoji in code, comments, commits, or documents.

---

### Task 1: Finish GLM's corpus and donor correction boundary

**Files:**

- Modify: `automation/search_evidence_corpus.py`
- Modify: `automation/test_search_evidence_corpus.py`
- Modify: `automation/search_donor_index.py`
- Modify: `automation/test_search_donor_index.py`

**Interfaces:**

- Consumes: the accepted Task 0 through Task 5 types and root findings R19 through R22 and R25 through R29.
- Produces: strictly typed `CorpusEvidence`, `CorpusGeneration`, promotion and refusal wrappers, verified report consumption, and a canonically gate-validated `DonorIndexGeneration`.

- [ ] **Step 1: Complete the failing correction tests**

Add direct-construction, parser, missing-artifact, corrupt-artifact, nested unsafe evidence, refusal replay, typed generation, required support, and wrapper mismatch cases. The gate-order test must use a scanner that raises if called:

```python
calls = 0

def forbidden_scan(_revision):
    nonlocal calls
    calls += 1
    raise AssertionError("scanner ran before gate validation")

with self.assertRaises(IntegrationGateError):
    build_donor_index(
        revisions,
        integration_gate=forged_gate,
        integration_archive=gate_archive,
        scan_revision=forbidden_scan,
        archive=index_archive,
        **binding_inputs,
    )
self.assertEqual(calls, 0)
```

- [ ] **Step 2: Run focused tests and confirm the new tests fail for the intended missing invariant**

Run through `sotn-cmd`:

```text
run_selftests.py --only test_search_evidence_corpus.py --jobs 1
run_selftests.py --only test_search_donor_index.py --jobs 1
```

Expected: failures name the incomplete R19 through R22 or R25 through R29 invariant, not import, fixture, or unrelated suite failures.

- [ ] **Step 3: Complete the minimal implementation**

The corrected public boundaries have these shapes:

```text
CORPUS_EVIDENCE_PROTOCOL = "sotn-corpus-evidence-v1"

@dataclass(frozen=True)
class CorpusEvidence:
    protocol: str
    evidence_id: str
    kind: str
    outcome: str
    lane: str | None
    scorer_algorithm: str | None
    schema_identity: str | None
    pattern_identity: str | None
    refusal_receipt: EvidenceRefusalReceipt | None
    # Existing typed identity and evidence fields remain.

CorpusEvidence.from_dict(value: Mapping[str, Any]) -> CorpusEvidence

collect_recurring_first_divergence(
    report: SearchPatternReport,
    contexts: Sequence[CompletedLineageContext | CompletedLineageDiagnostic],
    *,
    report_archive: ContentAddressedArchive,
    min_independent_lineages: int = 2,
) -> tuple[CorpusEvidence]

build_donor_index(
    revisions: Sequence[DonorRevision],
    *,
    integration_gate: IntegrationGateReceipt,
    integration_archive: ContentAddressedArchive,
    scan_revision: Callable[[DonorRevision], Iterable[DonorEvidence]],
    archive: ContentAddressedArchive,
    **bound_identities: Any,
) -> DonorIndexGeneration
```

`validate_integration_gate` runs exactly once before revision or scanner consumption. `CorpusGeneration.entries` remains typed in memory. Corpus support is mechanically derived and validated from nested records. Refusal receipts survive serialization and replay.

- [ ] **Step 4: Run the two focused suites once after the final edit**

Expected: both suites pass with exact test counts recorded in the ledger.

- [ ] **Step 5: Stop at the worker review boundary**

GLM re-reads the ledger, appends exact files and tests, releases all four paths, and leaves the diff uncommitted. Root reviews every changed line before any consolidated suite.

---

### Task 2: Complete GLM's active pattern recommendation validator

**Files:**

- Modify: `automation/search_patterns.py`
- Modify: `automation/test_search_patterns.py`

**Interfaces:**

- Consumes: production `_lineage_key`, `SearchPatternReport`, canonical hash helpers, and report artifact conventions.
- Produces: `validate_pattern_recommendation(value, *, report_source_ledgers) -> Mapping[str, object]`, used by report construction and corpus recurrence.

- [ ] **Step 1: Preserve the active ownership fence**

GLM had already modified `automation/search_patterns.py` before it could observe the attempted release. To avoid discarding or duplicating active work, GLM retains both pattern paths through this task. No second worker touches either path.

- [ ] **Step 2: Add strict failing recommendation tests**

Cover missing and unknown fields, wrong field types, changed pattern identity, unsorted or duplicate sources, lineage count disagreement, impossible aggregate counts, incorrect success rate, a recommendation citing a ledger outside the report, duplicate pattern IDs, recommendations outside production ranking order, and forged artifact metadata.

```python
for field in PRODUCTION_RECOMMENDATION_FIELDS:
    forged = dict(valid_recommendation)
    forged.pop(field)
    with self.assertRaises(PatternInputError):
        validate_pattern_recommendation(
            forged,
            report_source_ledgers=report.source_ledgers,
        )
```

- [ ] **Step 3: Implement one shared validator**

```python
PRODUCTION_RECOMMENDATION_FIELDS = frozenset({
    "pattern_id", "pass_kind", "patch_id", "lane", "overlay",
    "function_archetype", "first_divergence", "compiler_identity",
    "config_identity", "schema_identity", "scorer_algorithm",
    "lane_tool_identity", "recipient_id", "target_identity",
    "evaluator_identity", "sample_count", "successes", "failures",
    "success_rate", "source_ledgers", "lineage_ids",
})

def validate_pattern_recommendation(
    value: Mapping[str, Any],
    *,
    report_source_ledgers: Sequence[str],
) -> Mapping[str, object]:
    """Return one frozen production-shaped recommendation or refuse it."""
```

The validator requires the exact production field set and the current optionality of `pass_kind`, `patch_id`, and `first_divergence`. It recomputes `pattern_id` from `_lineage_key`, validates every hash, lane, selector, divergence field and collection, enforces `successes + failures == sample_count`, requires `len(lineage_ids) == sample_count`, and recomputes the six-decimal success rate. Source ledgers and lineage IDs are nonempty, sorted and unique, and recommendation ledgers are a subset of the report ledgers. `SearchPatternReport.__post_init__` rejects duplicate pattern IDs and recommendations outside the exact `_recommendations` ranking order. It also verifies content hash, JSON media type, byte size, and the exact `artifacts/pattern_reports/<digest>.json` path.

- [ ] **Step 4: Run the focused pattern suite once**

Run:

```text
run_selftests.py --only test_search_patterns.py --jobs 1
```

Expected: the complete suite passes and the worker records the exact test count.

- [ ] **Step 5: Stop at the worker review boundary**

GLM appends a ledger response, releases both paths together with the four Task 1 paths, and leaves the diff uncommitted. Root reviews the validator and then adjusts the corpus import or call site if Task 1 used a temporary local equivalent.

---

### Task 2A: Close the second review tranche before acceptance

**Files:**

- Modify: the six Task 1 and Task 2 paths
- Modify only for donor deep immutability: `automation/search_lanes.py`
- Modify only for donor deep-immutability regressions: `automation/test_search_lanes.py`

**Interfaces:**

- Consumes: the released R19 through R33 implementation and root findings R36 through R42.
- Produces: exact corpus discriminants, deeply immutable donor evidence, stable donor and corpus parser error domains, complete nested support provenance, contributor-based recurrence independence, and production-exact pattern values and path authority.

- [x] **Step 1: Add failing regressions for every root finding**

Cover hybrid corpus variants, missing factory-specific pairs, falsey non-array replay fields, malformed direct-construction collections, full-shape nested donor parser failures, post-construction mutation of nested donor input, forbidden keys under constants, scorer object and measurement support, refusal receipt set canonicality, two cited context runs with lineage contributions from only one, integer and nonfinite success rates, and a no-root path object that proves it was not read.

- [x] **Step 2: Implement R36 through R42 inside the eight-file fence**

Use exact variant tables rather than permissive field checks. Deep-freeze donor JSON values at their owning record boundary and thaw independent JSON values only for serialization. Catch only expected exceptions and translate them into the public module's stable error hierarchy. Derive nested provenance rather than trusting caller-maintained support. Determine independence from the context runs actually named by lineage ids, not from every cited context. Refuse a path before any read when no archive root authorizes it.

- [x] **Step 3: Run current focused and consolidated proof once**

After the final relevant edit, run the corpus, donor-index, pattern and lane focused suites once, followed by one consolidated `run_selftests.py --jobs 8`. Record exact counts and the consolidated job identity. Do not build or call the checksum oracle.

- [x] **Step 4: Release all eight paths for root acceptance**

The Luna max worker rereads the ledger, returns its implementation and proof report, releases every acquired path, and leaves the diff uncommitted. Root records the accepted worker outcome in the shared ledger.

Accepted outcome: root's first release review opened R43 and R44 for two remaining public-boundary gaps. Luna corrected both in the four affected paths. The final proof is corpus 60/60, donor-index 27/27, patterns 38/38, lanes 27/27, and consolidated job `run_automation-154506-6216` with 84/84 suites passed. Root accepted the R19 through R44 correction boundary without repeating unchanged validation.

---

### Task 3: Root integration and correction acceptance

**Files:**

- Review: all eight Task 1, Task 2 and Task 2A paths
- Modify later, root only: `ROADMAP.md`
- Modify later, root only: `automation/search_evidence_corpus.py` module documentation
- Modify later, root only: `docs/superpowers/plans/2026-08-28-evidence-corpus-donor-index.md`

**Interfaces:**

- Consumes: released Task 1, Task 2 and Task 2A diffs and their focused and consolidated proof.
- Produces: one accepted correction boundary and frozen Task 6 interfaces.

- [x] **Step 1: Review every changed line and map it to R19 through R44**

Root rejects broad exception catches, duplicate validators, caller-maintained provenance, raw generation mappings, and tests that fabricate artifacts without archive publication.

- [x] **Step 2: Run focused or consolidated suites only if root changes implementation or tests**

Use the affected commands from Tasks 1, 2 and 2A. Do not repeat unchanged worker proof.

- [x] **Step 3: Accept one current consolidated automation suite**

If Task 2A supplied this proof after its final correction edit, review and retain it. Otherwise run:

```text
run_selftests.py --jobs 8
```

Expected: every discovered suite passes once on the final correction tree. No build or checksum oracle runs at this stage.

- [ ] **Step 4: Make surgical documentation corrections**

Root updates the stale module summary, records Tasks 3 through 5 outcomes in `ROADMAP.md`, explicitly retracts entry 280's false R6 closure, and amends the source plan signatures and coverage without deleting historical text.

- [ ] **Step 5: Commit the accepted correction with explicit paths**

Root audits and stages each coherent path through `sotn-cmd`; workers do not commit.

---

### Task 3A: Bind the verified integration compiler into each donor generation

**Files:**

- Modify: `automation/search_supervisor.py`
- Modify: `automation/test_search_supervisor.py`
- Modify: `automation/search_donor_index.py`
- Modify: `automation/test_search_donor_index.py`

**Interfaces:**

- Consumes: the canonical `validate_integration_gate` path, its already loaded and verified `RunManifest`, and the accepted donor generation boundary.
- Produces: `validate_integration_gate(...) -> RunManifest` and `DonorIndexBinding.compiler_identity`, derived from that returned manifest rather than copied from a caller.

- [x] **Step 1: Add the failing compiler-binding tests**

Prove the validator returns the exact verified manifest, donor generation records its compiler identity, replay validates the compiler field as a content identity, and a query cannot use an index generated under another compiler. Existing callers may ignore the validator's return value. Do not claim that an in-memory generation constructor by itself proves an archive relationship; that comparison belongs to the archive-backed query boundary.

- [x] **Step 2: Implement the narrow return and binding extension**

`validate_integration_gate` already loads and validates the manifest. Return that typed manifest after every existing check succeeds, without adding another manifest reader or a second gate validator. `build_donor_index` uses the returned manifest to populate the binding. The public query boundary repeats the one canonical gate validation and compares the returned compiler identity with the binding before reading entries.

- [x] **Step 3: Run the focused supervisor and donor suites once**

Run:

```text
run_selftests.py --only test_search_supervisor.py --only test_search_donor_index.py --jobs 2
```

- [x] **Step 4: Stop for root review and interface freeze**

This is a substantive Luna max correction task after GLM releases all eight paths. The worker leaves the diff uncommitted, records exact test counts, and releases only the four files above. Root accepts this compiler binding before Task 4 begins.

Accepted outcome: `validate_integration_gate` returns the manifest it already verified, and `build_donor_index` derives `DonorIndexBinding.compiler_identity` from that single return. Supervisor 39/39 and donor-index 29/29 passed in the focused two-suite run. Root accepted and froze the interface without repeating validation.

---

### Task 4: Implement verified donor query core and semantic claims

**Files:**

- Create: `automation/search_donor_query.py`
- Create: `automation/test_search_donor_query.py`
- Modify narrowly: `automation/search_donor_index.py` to expose `DonorIndexGeneration.payload()` if required

**Interfaces:**

- Consumes: accepted `DonorIndexGeneration`, `DonorIndexBinding`, `DonorIndexEntry`, both content-addressed archives, and the canonical integration gate validator.
- Produces: `DonorQuery`, `DonorSemanticClaim`, `DonorQueryHit`, typed query receipts, `DonorQueryResult`, `make_donor_query`, `query_donor_index`, and `bind_donor_query(...) -> Callable[[DonorQuery], DonorQueryResult]`.

- [x] **Step 1: Add failing archive, ranking, ambiguity, and receipt tests**

```python
result = query_donor_index(
    index,
    query,
    expected_binding=index.binding,
    index_archive=index_archive,
    integration_archive=integration_archive,
)
self.assertEqual(result.status, "matched")
self.assertEqual(result.provenance_artifact, index.artifact)
```

Cover corrupt or missing index bytes, canonical index bytes that differ from the supplied in-memory generation, corrupt gate history, a compiler mismatch, stale binding, empty versus incompatible, all four ranks, ambiguity before limiting, deterministic reversed entries, `1 <= limit <= 8`, no scanner access, and original immutable donor references in results. Use exploding or otherwise observable entry inputs where practical to prove archive and compiler checks occur before entry consumption. Add direct-construction forgeries for every receipt, hit, semantic claim and result status. A public frozen record is not accepted merely because its factory creates valid examples.

- [x] **Step 2: Implement the frozen query interface**

```text
@dataclass(frozen=True)
class DonorSemanticClaim:
    recipient_id: str
    symbol: str | None
    signature: str
    instruction_signature: str | None
    cfg_signature: str | None
    dataflow_signature: str | None
    declarations: Mapping[str, Any]
    constants: Mapping[str, Any]
    structural_differences: tuple[str, ...]
    compatible: bool
    claim_identity: str

query_donor_index(
    index: DonorIndexGeneration,
    query: DonorQuery,
    *,
    expected_binding: DonorIndexBinding,
    index_archive: ContentAddressedArchive,
    integration_archive: ContentAddressedArchive,
) -> DonorQueryResult

bind_donor_query(
    index: DonorIndexGeneration,
    *,
    expected_binding: DonorIndexBinding,
    index_archive: ContentAddressedArchive,
    integration_archive: ContentAddressedArchive,
) -> Callable[[DonorQuery], DonorQueryResult]
```

`bind_donor_query` is the one durable verification boundary. It verifies the index artifact bytes and metadata, requires those bytes to equal the canonical payload of the supplied in-memory generation, calls the canonical integration gate validator once, and compares `index.binding.compiler_identity` with the compiler identity returned from that verified manifest before closing over the deeply immutable index. Missing or corrupt archive evidence raises a stable query artifact or integration-gate error; it is not mislabeled as an ordinary `stale` result. `query_donor_index` delegates to this binder and invokes the returned closure. Task 5 constructs the binder once, avoiding repeated large artifact reads without exposing a forgeable boolean or partially verified record.

The bound closure validates each query before reading entries, compares the query compiler identity with the already verified binding, and compares `expected_binding` with the exact index binding. Only the latter expected-versus-observed disagreement returns `stale`; a corrupt archive or a compiler disagreement with the verified manifest is a failed verification boundary.

Every query record is fail-closed under direct construction. Receipt IDs are hashes of fixed protocol payloads. `DonorSemanticClaim.claim_identity` covers only the renderer-safe semantic fields and deliberately excludes donor id, version, source artifact, source path, body and metadata, allowing equivalent support from distinct revisions to collapse to one claim. A hit validates its rank and match-kind pair, recomputes its semantic claim from the entry evidence, and binds the surrounding generation. A result validates its exact status, query and generation identities, sorted unique hits, hit-to-donor correspondence, receipt class and payload for refusal statuses, empty receipt for `matched` and `empty`, and exact equality between `provenance_artifact` and the verified index artifact. Rank all structural matches before applying compatibility, decide ambiguity across the complete best-rank set before limiting, and distinguish `empty` from `incompatible` by whether any structural match existed.

- [x] **Step 3: Run the focused query suite once**

Run:

```text
run_selftests.py --only test_search_donor_query.py --jobs 1
```

- [x] **Step 4: Stop for root review**

The Luna max worker releases only the three listed paths with an uncommitted diff and exact test evidence.

Accepted outcome: root reviewed the initial 11-test release and two bounded correction releases through R49. The final query interface requires durable archives and an expected binding, returns stale against the caller's expected compiler/config, replays only by archive-backed deterministic recomputation, isolates semantic claims from provenance, and rejects direct result and receipt forgeries. Final focused job `run_automation-163329-6216` passed 18/18 tests; root accepted it without repeating validation.

---

### Task 5: Implement the indexed lane adapter after accepting Task 4's interface

**Files:**

- Create: `automation/search_indexed_lane.py`
- Create: `automation/test_search_indexed_lane.py`
- Modify: `automation/search_lanes.py`
- Modify: `automation/test_search_lanes.py`

**Interfaces:**

- Consumes: the exact Task 4 query signatures, `DonorSemanticClaim`, `LaneCandidate`, `LaneAdapters`, and ordinary lane discovery normalization.
- Produces: `indexed_lane_adapter(...) -> Callable[[Recipient], Mapping[str, Any]]` and one narrow `candidates` dispatch branch.

- [x] **Step 0: Wait for the query-core release**

Root reviews Task 4, accepts its public records and callable signatures, and records the released commit or uncommitted review boundary in the ledger. The adapter worker must not import a query module that another worker is still editing.

- [x] **Step 1: Write failing semantic isolation and lane integration tests**

The renderer receives `tuple[DonorSemanticClaim, ...]`, never `DonorEvidence` or `ArtifactRef`:

```python
def render(recipient, claims):
    self.assertTrue(all(isinstance(item, DonorSemanticClaim) for item in claims))
    self.assertTrue(all(not hasattr(item, "source") for item in claims))
    return archived_target_candidate(recipient)
```

Cover matched output, empty, incompatible, ambiguity and stale refusals, exactly one query creation per recipient, recipient mismatch, lane mismatch, source identity mismatch, artifact metadata mismatch, and coordinator recovery of the accepted target-context candidate.

- [x] **Step 2: Implement the adapter against the frozen query contract**

```text
indexed_lane_adapter(
    index: DonorIndexGeneration,
    *,
    lane: str,
    expected_binding: DonorIndexBinding,
    index_archive: ContentAddressedArchive,
    integration_archive: ContentAddressedArchive,
    query_for: Callable[[Recipient], DonorQuery],
    render_target_context: Callable[
        [Recipient, tuple[DonorSemanticClaim, ...]],
        LaneCandidate | Sequence[LaneCandidate],
    ],
) -> Callable[[Recipient], Mapping[str, Any]]
```

Adapter construction binds the verified query closure once. Each callback invocation calls `query_for` once, renders only matched claims, and returns ordinary discovery fields and complete query, entry, revision, generation, and artifact provenance.

- [x] **Step 3: Add only the narrow dispatch branch**

```python
if (
    lane in {"multi_donor", "cfg_dataflow"}
    and isinstance(raw, Mapping)
    and "candidates" in raw
):
    return _discovery_from_values(raw, lane=lane, recipient=recipient, root=root)
```

Do not change subset checks, read-only controls, manifest lane validation, candidate identity validation, or other adapter arity behavior.

- [x] **Step 4: Run focused adapter and lane suites once**

Run:

```text
run_selftests.py --only test_search_indexed_lane.py --only test_search_lanes.py --jobs 2
```

- [x] **Step 5: Stop for root review**

The second Luna max worker releases only its four paths. Root reviews both Task 4 and Task 5 before any connector allowlist change or consolidated suite.

Accepted outcome: root reviewed the initial release and bounded R50 through R53
correction. The renderer receives one canonical semantic claim per identity,
while query hits, pinned revisions, claim identities, refusal receipts,
generation and verified artifacts remain external durable provenance. Stale
bindings are distinguished from exhausted searches, and target candidates must
carry exact canonical source metadata and bytes. Final focused job
`run_automation-195951-12593` passed the indexed adapter 12/12 and lanes 28/28.

---

### Task 6: Root acceptance, landing, and push

**Files:**

- Review: every path from Tasks 1 through 5
- Modify narrowly if required: `automation/mcp/commands_client.py`, `automation/test_connector_surfaces.py`
- Modify root only: `ROADMAP.md`, applicable architecture and tooling documentation, and source-plan checkboxes or amendments

**Interfaces:**

- Consumes: every released implementation tranche and its current focused proof.
- Produces: one reviewed, documented, reproducible automation boundary on `origin/automation/instrumented-search`.

- [x] **Step 1: Review every worker diff and resolve all cross-lane type mismatches**

No worker proof substitutes for root review. Reject duplicate query or semantic-claim types and any adapter path that exposes donor artifacts to the renderer.

- [x] **Step 2: Register new focused test scripts only if live discovery requires it**

Keep pure libraries out of `AUTOMATION_SCRIPTS`. Add only executable test suites and their connector regression.

No registration change was required. `run_selftests.py` discovers both new
`test_*.py` suites, while the imported query and adapter modules remain pure
libraries rather than connector actions.

- [x] **Step 3: Run one final focused matrix and one consolidated suite**

Run after the final automation edit, without repetition:

```text
run_selftests.py --only test_search_supervisor.py --only test_search_evidence_corpus.py --only test_search_patterns.py --only test_search_donor_index.py --only test_search_donor_query.py --only test_search_indexed_lane.py --only test_search_lanes.py --jobs 7
run_selftests.py --jobs 8
```

- [x] **Step 4: Update documentation and roadmap surgically**

Record actual outcomes, supersede stale signatures and findings explicitly, preserve historical failure evidence, and run the living-document generator only on an otherwise clean relevant tree.

Accepted outcome: the seven-suite focused matrix passed in two disjoint jobs
because the connector caps generic argument vectors at 12 tokens. Job
`run_automation-200421-12520` passed 4/4 and job
`run_automation-200434-12520` passed 3/3 with no repeated suite. The first
consolidated run exposed exactly two integration defects, managed-document
drift and the two new executable suites missing from the connector allowlist.
Both were corrected mechanically. Commit `a866e5d556135af021ce3d6019606c379418bdca`
contains the reviewed implementation and the clean-tree generated document
sync. Final consolidated job `run_automation-201332-12520` then passed 86/86.

- [ ] **Step 5: Commit with explicit paths and perform the mandatory fresh pre-push gate**

After the final commit: require clean `git_state`, exact untruncated commit-path and generated-store audits, then one fresh `make_build` followed by `verify_build` with all 113 expected artifacts.

- [ ] **Step 6: Push through a background job and confirm synchronization**

Start `git_push` through `job_start`, poll it to completion, then confirm the branch is no longer ahead of `origin`. No prior build or oracle proof substitutes for this gate.

## Plan Self-Review

- Spec coverage: Tasks 1 through 3 close R19 through R33 and R36 through R42; Task 3A closes the compiler-binding gap R34; Task 4 closes R24, R35 and source-plan Task 6; Task 5 closes R30 and source-plan Task 7; Task 6 performs source-plan Task 8 acceptance and repository landing.
- Completeness scan: every task names concrete files, tests, ownership boundaries, and cross-task interfaces.
- Type consistency: `DonorSemanticClaim` is defined only in Task 4 and consumed unchanged by Task 5. Both public query and adapter receive the donor and integration archives. Only root changes connector and documentation paths.
- Parallel safety: one Luna max worker alone owns the eight active correction files while root works concurrently on review and root-owned documents. Task 3A starts only after Task 2A is accepted, and Task 5 starts only after Task 4's public interface is accepted, so no worker imports a module another worker is still editing. Root serializes integration, commits, build, oracle, and push; consolidated proof runs once on the final relevant correction tree.
