# Data search and scorer tuning implementation plan

The owner delegated design and execution and prioritized both systems on
September 7. Root implements directly. This amendment extends the existing
function-search plan's deferred data subsystem and the August 28 Task 9.6
weight-tuner plan; neither historical plan is replaced.

**Goal:** Execute reproducible data searches and scorer trials from actual
repository evidence, then connect their accepted outputs to later matching.

**Architecture:** Keep data records separate from function CandidateRecord.
Freeze config, checksum manifest, binary and range bytes in the existing
content-addressed archive. Search calibrated peer segments, retain every
ambiguous/rejected candidate, score serialized bytes, and publish deterministic
receipts with range ownership. Tuning consumes archived compiler observations,
freezes lineage groups before trials, records bounded search outcomes, and
publishes immutable weights for explicit later-run adoption.

**Tech stack:** Existing Python, PyYAML, ContentAddressedArchive, compiler corpus,
instrumented factory, coordinator, and sotn-cmd background jobs.

**Specs:** `docs/superpowers/specs/2026-08-26-instrumented-search-system-design.md`
and `docs/superpowers/specs/2026-08-28-instrumented-search-supplement-design.md`.

## Task 1: Reconcile scope

- [x] Preserve history and append current status to ROADMAP and coordination.
- [x] Keep #287/#288/#291/#292/#299/#302 open; close stale completed entries.
- [x] Promote #277 and record #304; retain the model deferral.

## Task 2: Executable data search

Files: create `automation/data_search.py` and `automation/test_data_search.py`;
register both in `automation/mcp/commands_client.py`; document the actual CLI.

- [x] Capture configured data/rodata segments from explicit platform configs,
  verify original binary SHA-1 against config, and archive exact input bytes.
- [x] Search one explicitly named target stem using calibrated peer byte spans.
  Keep repeated/empty/unsupported results. Do not infer a range from code bytes.
- [x] Score byte mismatches and length differences; bind candidates to complete
  target binary identity and half-open owned ranges. Reject conflicting owners.
- [x] Publish content-addressed request/result receipts with deterministic replay
  and archive-only verification. CLI exposes search and verify through jobs.
- [ ] Exercise real RNO1/RNZ1 shared-data cases and retain output references.
- [x] Connect accepted candidates to journaled config/source preparation and the
  exact configured full-build oracle before claiming automated data landing.

## Task 3: Scorer tuning

Files: create `automation/weight_tuner.py` and `automation/test_weight_tuner.py`;
modify compiler/factory/CLI paths required by the existing Task 9.6 plan.

- [x] Consume validated completed integration evidence and archived measurements;
  refuse absent objects, mixed compiler/scorer identities and incomplete runs.
- [x] Freeze connected lineage/source/target groups before any trial, with both
  nonempty train and holdout partitions; publish dataset membership immutably.
- [x] Execute fixed equal-budget search trials under explicit weights and seeds.
  Select on training cases by exact target-object rediscovery, then common
  default-weight score, cost and artifact identity. Report holdout separately.
- [x] Verify reports by re-deriving metrics from immutable trial evidence; expose
  tuning and verification publicly. Retrospective reweighting is diagnostic only.
- [x] Bind opt-in weights at new factory creation; preserve active-run weights
  and require the runtime scorer to consume the archived configuration.
- [x] Exercise a real corpus and record measured results or exact data shortfall.

## Task 4: Continue programmatic matching and land

- [ ] Finish #299 evaluated-candidate handoff and #302 real cross-platform
  publication/consumption without redoing accepted provider infrastructure.
- [ ] Run focused behavioral checks after edits, consolidated suites once on
  the stable batch, then explicit-path commit and the fresh pre-push gate.
- [ ] Update outcomes and limitations in ROADMAP and coordination before push.

The data-search discovery phase does not claim data landing. A tuner schema or
fixture result does not claim useful learned weights. Each completion record
must identify the public execution and its actual archived outcome.

## September 7 implementation decisions and evidence

The schema 1.1 migration proposed on August 28 is superseded for scorer adoption.
The existing manifest tool identity map binds `scorer_weights` and the tuner
runtime, while the factory archives the exact weight document. Existing 1.0
runs retain their defaults and active runs cannot change their tuning input.
This preserves old evidence without a repository-wide schema conversion.

Raw scores under different weights are not comparable. Trials use their own
weights to choose mutations, but ranking uses the resulting component counts
under a common default score. Selection uses training families only. Holdout
results never choose the winning weights.

`programmatic-tuning-context-20260907` completed four real records. The tuner
retained four successful observations from two families and excluded two
compile failures. `tuning-isolated-context-20260907` ran three configurations,
four compiler evaluations per observation, 48 evaluations total. No exact
object was rediscovered; training and holdout median common scores were 350
and 125. All configurations tied on these measures. The selected artifact is
an experiment output, not evidence of improved weights or a new global default.

Expanded compiler input is now archived by the ordinary evaluator. The tuner
removes top-level assembly includes before mutation and requires the isolated
C baseline to reproduce the original function score and normalized object
identity. It never resolves those assembly includes against a later checkout.

The first RNO1 red-door data attempt found the exact 24-byte UV table but failed
on a missing tile-table alias and raw switch rodata. It restored the original
source/config and passed all 113 checksums. Preparation now derives aliases
from consistent independent donor instruction contexts and jump-table bounds
from original binary words pointing into the target function. These remain
preparation hypotheses until the complete checksum oracle accepts them.

The corrected data attempt `data-rno1-red-door-closure-v2-20260907` compiled and
linked, then failed the full checksum. Its three edits were restored and the
baseline verified. Receipt `0e9a5343bc4357c97bdc577871ba3c3d0a45703295ee4b689e9f587905f95592`
retains that outcome. The unreferenced string after the jump table remained
outside the inferred ownership range. No new function match is claimed.

The real report passed archive-only replay in `run_automation-154901-1984`.
`programmatic-weight-adoption-20260907` completed and all four ordinary
measurements used the frozen artifact `513fb8281679c11663bd7aaeee880173a413d3b6c390115f0d012ee58103554d`.
The separate `programmatic-weight-permuter-20260907` ledger reached terminal
completion with eight worker evaluations carrying those same weights.

Consolidated validation `run_automation-181944-67` passed 105/107 suites,
including the connector and journal suites. The two failures were stale living
documents and the argument-dependent script catalog in the dashboard.
`readme_status.py --write` refreshed the generated blocks, the catalog now
records the two explicit-input connector jobs, and `run_automation-182415-67`
passed both affected suites. No unchanged consolidated suites were repeated.
