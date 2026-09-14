# MIPS regression cases implementation plan

**Goal:** Add independently derived MIPS-I regression cases to the existing US renderer suites following owner approval on September 13.

**Architecture:** Exercise deterministic_local_draft and the archived render_target_candidate boundary. Supported snippets compile and run as C89 host fixtures with explicit arithmetic and memory expectations. Unsupported operations retain typed refusals. No external runtime or copied implementation is introduced.

**Tech stack:** Existing Python unittest, ctypes, host GCC and connector self-test jobs.

**Spec:** docs/psxrecomp-assessment-2026-09-13.md, proposed follow-up boundary, plus the owner's approval for MIPS regression case testing.

## Constraints

- Lead executes inline. No delegated work, live queue matching or candidate landing.
- US remains the only target. No expansion of loop, indirect-call or unaligned-access support is promised.
- External scenario references remain pinned; expected CPU behavior is checked against the IDT R30xx Family Software Reference Manual, revision 1.0, Appendix A load/store and branch/jump descriptions: https://usermanual.wiki/Document/r3000manual.723589236/html .
- Preserve verify_build as the only match oracle. Host behavior tests are supplementary.
- All Git/build/test execution uses the SOTN connector. The preceding normal-action override was for the assessment.

## Task 1: Supported scheduling and unsupported hazard fixtures

Files: modify automation/test_search_target_layout.py and automation/test_search_target_renderer.py. Record the outcome in ROADMAP.md and this plan.

Interfaces: deterministic_local_draft(assembly, symbol=..., declarations=...) returns C or None. render_target_candidate(manifest, index, recipient, claims) returns a LaneCandidate or TargetContextUnsupported with provenance.

- [x] Add a compiled memory-predicate fixture: load the old word, compare it with a scalar argument, overwrite the same memory in the branch delay slot, and write the returned value in the return delay slot. Expected result is old+7 for equality, old+3 otherwise, modulo 2^32; verify aliased and distinct destinations.
- [x] Add a legal scheduled-load fixture with an independent branch between the load and consumption in its delay slot. Check both branch outcomes and boundary values.
- [x] Add paired hazards for all five ordinary load widths: immediate arithmetic/store/predicate consumption must refuse; inserting one nop must admit the otherwise identical snippet. Cover ABI register spellings without changing expected semantics.
- [x] Cover a loaded pointer immediately used as an address, and load-in-control-slot rejection. Include LW-to-LWL/LWR and LWL/LWR pairs as explicitly unsupported cases, not claimed implementations of their special forwarding rule.
- [x] At the archived public boundary, require typed provenance-preserving refusals for a bounded indirect-dispatch shape and branch-into-delay-slot input; include an ordinary forward-branch positive control.
- [x] Run focused renderer/layout suites through run_selftests.py --only. Investigate a failure before any production edit; do not broaden supported instruction shapes just to make a regression pass.
- [x] Run the consolidated automation suite once after final edits. Record actual counts, failures and any corrected diagnosis.
Required landing procedure after recording this outcome: update ROADMAP.md, stage explicit paths, commit, audit the exact pending commit and generated changes, run the fresh pre-push build/checksum gate, push to origin through a job, and confirm the remote branch matches HEAD.

## Outcome

Completed four regression methods in the two existing suites. The five ordinary load forms, three consumer classes and four register spellings provide 60 paired hazard/control checks. Two C89 fixtures execute 60 input/alias combinations, checking the returned word and both memory destinations. Additional checks cover pointer-address dependency, load-in-return-slot refusal, unsupported merge-load pairs, and archived provenance-preserving refusals with a direct-branch positive control.

Focused job run_automation-194108-30 passed 2/2 suites with no skipped-test verdict. Consolidated job run_automation-194125-30 passed 108/108 suites in 159.2 seconds, including the existing real US compiler and connector checks. No production renderer defect was exposed; no production implementation, external dependency, indexed runtime or live queue record changed. These tests establish the existing acceptance/refusal boundaries and do not implement indirect dispatch or LWL/LWR semantics.

The assessment commit a4e6fa161 is already pushed. Its clean 113/113 post-build oracle supplied the baseline; this batch's mandatory fresh pre-push gate follows the test/documentation commit.
