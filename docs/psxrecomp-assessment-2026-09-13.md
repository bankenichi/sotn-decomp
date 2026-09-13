# PSXRecomp and recomp-ui assessment

Assessment date: 2026-09-13. Scope: usefulness to this fork's US matching
harness and knowledge base. This is a source/documentation review, not a
runtime qualification or an authorization to start live matching.

## Recommendation

Treat PSXRecomp as a pinned reference for selected MIPS analysis methods and
regression scenarios. Do not replace the matching pipeline or import its
generated C as matching source. Defer recomp-ui until a playable native port
becomes an explicit project objective. Neither repository closes #302 or #299.

| Potential use | PSXRecomp | recomp-ui |
|---|---|---|
| Recover C that matches the original US binary | Low direct value | No direct value |
| Improve MIPS analysis and renderer regression coverage | Moderate potential; concrete relevant implementation exists | Negligible |
| Supply SOTN donor implementations or target types | Not established | Not applicable |
| Diagnose translated-code behavior | Promising, but substantial integration and qualification needed | Presentation only |
| Build a future native playable port | Plausible framework; SOTN compatibility unverified here | Useful launcher/settings component once a host exists |
| Replace the harness dashboard | Poor fit | Poor fit without substantial custom integration |

## Evidence inspected

The external revisions were pinned while reading:

- PSXRecomp: `85cd26f05c44999731f6b3320fb8a871fba68e9b`.
- recomp-ui: `cb7e54b41b6d75a6233de0083914e270f3902f4c`.
- Local starting HEAD: `ff832bba1c2ead0c8c1d40b37f9d5ee7a85c1660`.

Read the external repository trees, architecture and execution documentation,
AOT overlay guide, game and BIOS code emitters, function analysis implementation,
selected regression tests, lockstep implementation, launcher model and CMake
integration, and licenses. Local comparison used ROADMAP.md, harness/tooling
documentation, relevant matching lessons, and search_target_renderer.py.
The initial on-disk US oracle returned 113/113. No external build, external
test execution, game playthrough, candidate evaluation, or speedup measurement
was performed. Test source is evidence of intended coverage, not a passing
result in this assessment.

## Why recompilation does not finish matching

PSXRecomp's game emitter produces C operating on `cpu->gpr[]`, guest addresses,
runtime memory helpers and explicit control-flow labels. Its purpose is to
execute translated PS1 instructions on the host. Our renderer must recover
target declarations, named members and source shapes that the original US
compiler turns back into the exact original bytes. Generated native-runtime C
does not solve that inverse-compiler problem. Even semantically correct C can
have the wrong stack frame, register allocation, switch table or section layout.

This distinction matters especially here: the roadmap records 94.1% decompiled
and 549 remaining US stubs. The missing value is increasingly target context,
structural source recovery and durable candidate handoff, not a way to execute
already-known instructions. See local MATCHING-LESSONS.md sections 22 and 26.
[Game emitter](https://github.com/RetroPortingToolKit/psxrecomp/blob/85cd26f05c44999731f6b3320fb8a871fba68e9b/recompiler/src/code_generator.cpp).

## Useful PSXRecomp material

1. **Bounded switch recovery.** `resolve_exact_bounded_jump_table` checks the
   index/bounds dependency chain, register clobbers, branches that bypass a
   definition, table contents, and producer intervals. It recognizes particular
   compiler scheduling forms rather than treating arbitrary nearby words as
   proof. This is relevant to future structured dispatch in #302, but it is not
   a general loop or typed-C recovery algorithm. Its conservative pattern limits
   must remain explicit.
   [Implementation](https://github.com/RetroPortingToolKit/psxrecomp/blob/85cd26f05c44999731f6b3320fb8a871fba68e9b/recompiler/src/function_analysis.cpp).
2. **CPU edge-case regression scenarios.** The LWL/LWR load-delay test captures
   a specific disagreement between native emission and interpretation. The
   reachable-discovery test uses synthetic PS-X EXEs to check bounds, unseen
   indirect callbacks and unsupported entries. These are useful scenario
   references for independently authored renderer tests, with architectural
   expectations established independently. They do not prove universal CPU
   correctness, and copied test code retains its license obligations.
   [Load-delay test](https://github.com/RetroPortingToolKit/psxrecomp/blob/85cd26f05c44999731f6b3320fb8a871fba68e9b/recompiler/tests/test_lwlr_load_delay_forward.py),
   [discovery test](https://github.com/RetroPortingToolKit/psxrecomp/blob/85cd26f05c44999731f6b3320fb8a871fba68e9b/recompiler/tests/test_reachable_discovery_codegen.py).
3. **Overlay identity and provenance.** Their AOT pipeline distinguishes
   original image reconstruction, safe native-cache selection, and actual
   execution correctness. Explicit producer ranges and byte guards address
   reused RAM addresses. This resembles our overlay-scoped identity problem,
   but our existing configs and symbol maps should remain authoritative.
   Discovery is not a reason to replace those with heuristics.
   [AOT guide](https://github.com/RetroPortingToolKit/psxrecomp/blob/85cd26f05c44999731f6b3320fb8a871fba68e9b/docs/AOT_SHARDING.md).
4. **Behavioral diagnostics.** Lockstep record/replay has concrete implementation
   in dirty_ram_interp.c. Debug tooling documents register, RAM and execution
   comparison with Beetle PSX. A future adapter could use this to localize a
   semantic disagreement. It would need controlled entry state, memory and
   side effects, plus independent qualification; agreement with a related
   interpreter can retain common bugs. It cannot replace verify_build.
   [Lockstep implementation](https://github.com/RetroPortingToolKit/psxrecomp/blob/85cd26f05c44999731f6b3320fb8a871fba68e9b/runtime/src/dirty_ram_interp.c),
   [debug protocol](https://github.com/RetroPortingToolKit/psxrecomp/blob/85cd26f05c44999731f6b3320fb8a871fba68e9b/docs/TCP_COMMANDS.md).

The immediate fit is implementation/testing under #302. PSXRecomp does not
provide our immutable assembly-backed donor publication, general donor C
preprocessing, target type recovery, or #299 evaluated-candidate chaining.
Its PS1 analysis is not a multi-architecture donor solution. Do not treat a
new decoder dependency as closing those production boundaries.

## recomp-ui fit

The repository contains a real Dear ImGui launcher with C-facing settings and
host callbacks, PSX profiles, and an in-game settings API. CMake integration
compiles the shared launcher/model and supports SDL backends with OpenGL.
The host must supply and apply actual capabilities. For example, a Mods page
requires a live mod provider; the frontend is not itself a mod engine.
[Integration code](https://github.com/RetroPortingToolKit/recomp-ui/blob/cb7e54b41b6d75a6233de0083914e270f3902f4c/recomp_ui.cmake),
[runtime API](https://github.com/RetroPortingToolKit/recomp-ui/blob/cb7e54b41b6d75a6233de0083914e270f3902f4c/src/recomp_runtime_ui.h).

It could save work on disc selection, controls, memory-card presentation and
settings for a future SOTN desktop game. It provides no ready integration for
our queue, candidate provenance, compiler differences, BuildLock, run recovery
or checksum evidence. Adopting it now would add a desktop C/C++ presentation
stack while leaving those integrations to us. A launcher checkbox also does
not implement SOTN widescreen, save-state correctness or other game behavior.

## Viability, maturity and licensing

Both trees have recent September 13 commits and substantive implementation.
PSXRecomp lists other playable game projects, including 2D titles. That supports
plausibility for a future port, not SOTN compatibility. Its AOT guide explicitly
acknowledges partial extraction support, per-title loader work and incomplete
execution coverage. Some other documentation is stale: EXECUTION_MODEL.md's
categorical claim that overlays cannot be found ahead of time conflicts with
the current disc-based AOT workflow. Use code and bounded receipts over blanket
accuracy claims. The latest inspected PSXRecomp commit fixes a build failure
when netplay is disabled, another reason to pin revisions rather than assume
every advertised configuration is qualified.
[Repository](https://github.com/RetroPortingToolKit/psxrecomp/tree/85cd26f05c44999731f6b3320fb8a871fba68e9b),
[build correction](https://github.com/RetroPortingToolKit/psxrecomp/commit/ab2aaf95be7fc2ef2f9c3ffe6bf7de9aa4b92acd).

PSXRecomp uses PolyForm Noncommercial 1.0.0, while recomp-ui uses MIT. Our root
LICENSE is AGPLv3. Do not assume PSXRecomp implementation can be copied into
the harness under the harness's existing terms. Resolve the intended reuse
and applicable component licenses before vendoring; separately licensed
dependencies must be evaluated under their own notices. Reference study and
independently established test expectations are the recommended starting point.
[PSXRecomp license](https://github.com/RetroPortingToolKit/psxrecomp/blob/85cd26f05c44999731f6b3320fb8a871fba68e9b/LICENSE),
[recomp-ui license](https://github.com/RetroPortingToolKit/recomp-ui/blob/cb7e54b41b6d75a6233de0083914e270f3902f4c/LICENSE).

## Proposed follow-up boundary

If this reference is used during later authorized #302 implementation, start
with a small fixture batch for switch recovery and delay-slot behavior.
Use our target types and ordinary renderer/evaluator interfaces. Record the
external revision, architectural expectation, current behavior and observed
improvement or refusal. Do not start a full SOTN runtime port merely to obtain
these tests. Keep live queue matching deferred under the September 8 control.

A separate search also found BlackLabelHQ/SymphonyRecomp, a SOTN-specific
recompilation using RecompOne. It is a potentially more relevant future runtime
reference, not evidence that these two repositories support SOTN and not a
replacement for matching. It was not audited in this assessment.
[Project](https://github.com/BlackLabelHQ/SymphonyRecomp).
