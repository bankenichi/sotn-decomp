# Independent US Switch Recovery Implementation Plan

> Execution: lead implements inline under the owner's instruction to rederive and write useful functionality from scratch. No delegation or live matching.

**Goal:** Recover bounded switches from archived US MIPS assembly and produce ordinary target-context C candidates.

**Architecture:** A pure SOTN-specific reader extracts local read-only label tables. A verifier proves a dispatch from the assembly's own unsigned guard, scaled index, symbolic table load and delayed register jump. The existing renderer expands validated cases with its existing state, memory, ABI and path budgets. Raw target assembly remains the immutable evidence.

**Tech Stack:** Python standard library, existing renderer/archive/factory, C89 host behavioral fixtures and the repository PSX compiler.

**Derivation:** The functional idea of switch recovery was identified in the PSXRecomp assessment. That source was previously inspected, so this is not a claim of an isolated clean-room process. Implementation must use this repository's assembly conventions and the IDT R30xx manual, without copying or translating external code, comments, tests, API structure or arbitrary limits. No external dependency is introduced and no categorical legal clearance is claimed.

## Design and alternatives

Implementing a native emulator and record/replay system would introduce substantial runtime work without addressing the current renderer gap. A standalone recognizer would produce analysis but no usable candidates. Integrating local table recovery with the existing renderer provides a bounded matching-oriented capability and uses evidence the factory already freezes.

The observed local example is asm/us/boss/bo0/matchings/2B9EC/func_us_801AB9EC.s: its read-only table has five local labels; sltiu compares the selector to five; beqz selects default; its delay slot scales the selector; LUI/ADDU/LW materialize the indexed table entry; NOP separates load and JR. This example supplies the dispatch form, not an assertion that its entire function is supported.

## Constraints and acceptance

- US target only; donor platforms stay read-only.
- September 14 owner clarification: normal non-Git tools are authorized for Astra and Fable only. Use normal file tools for this work; keep Git on the sotn-cmd connector and long validation/publication operations as background jobs. The lead's failure to switch file-writing tools after acknowledging this direction is recorded in AGENTS.md constraint 25.
- Initial scope: no live queue execution, source landing, new runtime publication or matches claimed. September 14 amendment: the no-new-publication restriction is superseded below; the other boundaries remain.
- Preserve current 64-instruction, path-expansion and C-output limits.
- Accept complete local .rodata tables with symbolic local targets. Reject mutable, malformed, missing, duplicate, external, partial or unused tables.
- Prove the guard, index and table are connected. Require a legal load delay and inert indirect-jump slot for the initial bounded implementation.
- Reject incoming edges to the dispatch interior, backward case targets, slot entry and unknown instructions.
- Preserve the guard slot on default and case paths. Table-address registers become unavailable values, never invented C pointers.
- Emit switch cases, including repeated target labels, only when every reachable path can render.
- Bind the new source dependency in indexed-runtime identity and factory recovery.
- Demonstrate ordinary archived candidate/refusal results, compiled branch outcomes, default and word boundaries, target compilation and dependency-tamper refusal.
- Run focused suites after edits, consolidated selftests once, then final commit and fresh build/checksum/push gate.

## Implementation steps

- [x] Add independently authored switch fixtures to automation/test_search_target_renderer.py. Baseline valid switches must currently refuse, while the existing forward-branch control succeeds.
- [x] Add automation/search_mips_switch.py for read-only table parsing and dispatch proof. Keep raw assembly signatures unchanged.
- [x] Integrate recovery into automation/search_target_renderer.py and emit C switches through the ordinary deterministic renderer.
- [x] Add the module to RENDERER_DEPENDENCIES in automation/search_target_layout.py and immutable factory source bindings in automation/search_run_factory.py.
- [x] Exercise archived rendering, malformed/refusal cases, compiled semantics, compiler acceptance and recovery dependency mutation.
- [x] Run focused and consolidated validation, review all edits and record measured outcomes here and in ROADMAP.md.

Landing procedure after the evidence commit: audit exact committed paths, build
and verify all 113 expected checksums, push origin via job and confirm clean
synchronized state. The resulting job receipts carry the post-commit proof.

## Sources

- Local SOTN assembly and existing harness implementation.
- IDT R30xx Family Software Reference Manual, revision 1.0, 1994: https://usermanual.wiki/Document/r3000manual.723589236/html
- Copyright Office distinction between program expression and ideas/methods: https://www.copyright.gov/register/tx-programs.html

## Outcome

Implemented local table parsing, bounded dispatch proof, C89 switch rendering,
immutable source binding and ordinary archived integration. No external source,
tests or comments were copied or translated. The same agent had inspected
PSXRecomp previously; this is independent derivation, not an isolated clean-room
claim or a legal opinion.

### Scope amendment and production boundary

The initial prohibition on new runtime publication was a planning choice, not
an owner constraint. It is superseded: publishing a successor with the new
renderer identity is necessary to make this implementation available through
future indexed runs. The same four pinned donor revisions and the existing
completed gate are reused. No live matching or candidate landing is authorized.

### Measured evidence

- Red fixture run run_automation-195742-30: two expected positive switch tests failed before implementation; negative controls passed. The earlier run run_automation-195722-30 also lacked a donor claim in its archived fixture, which was corrected before accepting the red evidence.
- Focused six-suite run_automation-200348-30 passed, including host behavior, actual PSX compilation, factory binding and indexed-runtime identity checks.
- Host C89 execution covered 100 combinations: two selector forms, ten selector boundary values and five bias word boundaries, with repeated cases, default behavior and return delay slots.
- The reader recovered the five exact case labels in the real generated func_us_801AE858 assembly. That function includes one unreachable zero padding word after the odd-sized table. The complete function remains outside renderer limits.
- Ordinary indexed adapter and lane receipt replay passed in run_automation-004529-30. Its additional factory fixture initially failed due to a missing test import; the corrected archive-only seed reconstruction, table-tamper refusal and case-extraction control passed in run_automation-004628-30.
- Consolidated run_automation-004724-30 passed 108/108 in 160.8 seconds.
- First successor publication search_publish_indexed_runtime-005030-30 failed canonical integration-gate validation. Diagnosis: adding a mandatory current core module accidentally invalidated completed pre-switch archives. Historical validation now accepts their original dependency set; runtime verification still refuses dispatch without the current binding. The new compatibility regression and indexed-runtime suite passed in run_automation-005155-30. This is a production defect found by publication, not a bad historical gate.

### Read-only generated-assembly coverage

A direct canonical-WSL read traversed `asm/us/**/*.s`, selecting paths with a
`nonmatchings` component, then files containing both `.section .rodata` and
`%hi(jtbl`. It ran `split_local_tables`, the existing assembly parser with
relocations retained, and `recover_dispatches`; it did not generate candidates,
read or change queue records, or invoke a compiler.

There were 1,751 generated nonmatching assembly files, of which 151 met the
table filter. The verifier recovered every table in 98 files: 110 dispatches
and 899 indexed case entries. It refused 34 files with unaccounted read-only
data, 18 with unproved or unused tables, and one exceeding the table bound.
None of those 98 files fit the existing 64-instruction whole-function renderer.

This generated-file population includes retained assembly and is not the
authoritative 549 active-US-stub count. The measurements show useful control-flow
recovery, not 98 newly renderable functions or any new checksum match. Broader
function rendering, loops and unsupported schedules remain open under #302.

### Final validation and publication

Post-correction consolidated run_automation-005237-30 passed 108/108 in 178.7
seconds, including the legacy-archive/current-dispatch regression. Successor
publication search_publish_indexed_runtime-005237-30 completed successfully and
verified runtime
`sha256:99ded73daabda8e042761428d4318b98a2ed6312062478b17542c53ee8b8b935`.
It retains 6,798 donor functions (US 3,046, HD 595, PSPEU 2,812, Saturn 345),
the four pinned revisions `eb178335006be58f274d0c8157addae1461325bc`, and
completed gate `programmatic-tuning-context-20260907`. No additional runtime
verification is needed without a state change.

### Publication delay

The publication start metadata and completion-marker timestamp bound its run
to approximately 53 minutes 22 seconds, from 06:52:37 to 07:45:59 UTC on
September 14. A later status poll's elapsed field included time after completion
and is not the runtime duration. At the 18-minute sample the Python process had
used only 1 minute 34 seconds of CPU and showed `p9_client_rpc` filesystem wait;
I/O counters continued increasing. This supports a filesystem bottleneck during
the sampled period, not a full profile of all 53 minutes.

The current publisher rematerializes every immutable source, copies the stage
file by file, and verifies both manifests and the resulting runtime. A renderer
change therefore repeats substantial work on the Windows-mounted WSL path even
when donor revisions are unchanged. Reusing verified immutable materialization
and exposing phase timings are follow-up optimization opportunities; neither is
implemented here. Do not restart an active publication or repeat its completed
verification merely because polling is slow.
