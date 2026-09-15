# Loop-call review and repair plan

**Goal:** Assess the renderer approach and repair loop-call lowering with
independent behavioral evidence, without running live matching.

**Architecture:** Keep the bounded target-owned renderer and its archived
declaration boundary. Separate mutable loop storage from register validity,
share ordinary call lowering with loop bodies, and capture branch predicates
before delay slots. Calls retain the existing ABI checks and invalidate all
caller-saved values. Call-result temporaries execute at their instruction site.

**Scope:** US only; no queue mutation, candidate landing, model activation or
pull requests. File work is local; Git and WSL jobs use sotn-cmd. Historical
documents receive explicit corrections, not replacement.

## Acceptance gates and execution

- [x] Add failing host-compiled regressions in
  `automation/test_search_target_renderer.py` for loop latch delay timing,
  zero-trip exit-slot effects, conditional state, loop loads, and repeated
  direct/API calls. Execute generated C in timeout-bounded subprocesses.
- [x] Repair `automation/search_target_renderer.py`: reuse call lowering;
  separate carrier storage and valid values; preserve branch/exit timing;
  refuse unsafe backedges, unsupported stack state and missing declarations.
- [x] Prove direct and indirect loop calls compile with the real PSX toolchain
  in `automation/test_search_compile_driver.py`, and exercise archived rendering
  through the existing ordinary indexed evaluation fixtures.
- [x] Keep structural census and declaration-aware lowering distinct in
  `automation/measure_data_effect.py`; measure only after focused proof.
- [x] Run the focused regression suite after edits, then the consolidated
  `run_selftests.py` gate once. Inspect any failures before another run.
- [x] Record measured results, limitations and explicit retractions in
  `docs/loop-call-outcome-2026-09-16.md`, `MATCHING-LESSONS.md` and `ROADMAP.md`.
- [x] Build and verify; stage explicit paths; commit; audit the exact commit
  and generated stores; require clean state; build and verify again for the
  mandatory pre-push gate; push to origin as a job and confirm ahead is zero.
  Landed as commit 382904a0a with a green oracle and the branch in sync.

## Review decision

The approach remains useful as a bounded candidate generator. A compiled fixture
is not evidence of a live match or of completed cross-platform matching (#302).
The existing 0-new-render measurement is retained until measured again.

## Execution evidence

Focused jobs `run_automation-164009-57561` and
`run_automation-164043-57561` passed all selected suites. The final added
join-timing regression passed in `run_automation-165016-57561`.
Consolidated `run_automation-165036-57561` passed 110/110 suites.
Default-bound full-pool measurement `run_automation-164159-57561` found
zero renders and zero errors over 260 active files, with 39 structurally
admitted, declared files now blocked by the default size ceiling.
Required build `make_build-164704-57561` and the following oracle passed
113/113. Raised-limits remeasurement `run_automation-165425-57561` passed with zero errors and zero renders over 260 active files. The exact post-commit pre-push gate remains mandatory.
