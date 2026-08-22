# Terra low full-sweep raw response

Model: `gpt-5.6-terra`
Effort: `low`
Input: `terra-effort-input.md`
Stateful actions: none

## Terra low benchmark, 2026-08-22

### 1. Stage A: `us:BOSS/BO6:BO6_RicStepStand`

**Process gate: PASS, with one retrieval limitation.** I performed only read-only connector and repository inspection. I did not edit files, build, run `asm_diff`, invoke the permuter, operate a fleet, use Git, or mutate the queue. The live queue’s filtered listings did not return this exact ID, so I cannot honestly quote its per-record history. This is an evidence gap, not evidence that the record does not exist.

Evidence trail, in required cheapest-first order:

1. **Controlling instructions and task history**
   - `AGENTS.md` requires read-only delegation, prohibits subagent builds, and makes the root responsible for edits, queue, Git, and verification.
   - `ORCHESTRATOR.md` section 2 confirms that subagents may not build, edit, mutate the queue, or run Git; section 7 gives the required progression: upstream/twin search, shim sweep, transplant, hand derivation, model analysis, then permuter.
   - `docs/TOOLING.md` says a match is only `verify_build` at 81/81, immediately after a managed build. No such evidence was requested or produced here.
   - `queue_list` was queried for every exposed status (`todo`, `near`, `escalated`, `deferred`, `matched`, `claimed`), but no response contained `us:BOSS/BO6:BO6_RicStepStand`. Because connector output is capped, the honest conclusion is: per-record history was not retrievable in this benchmark run.

2. **Stub, source context, and target assembly**
   - The live stub is `src/boss/bo6/richter.c:810`: `INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepStand);`
   - The target is `asm/us/boss/bo6/nonmatchings/richter/BO6_RicStepStand.s:4`, 153 instructions.
   - The assembly establishes the target’s main structure:
     - `BO6_RicCheckInput(0x4305C)`;
     - `DecelerateX(0x2000)` when input handling declines;
     - a compare-chain dispatch on a 16-bit substep at `D_80076306`, with cases `0`, `1`, `0x40`, `0x41`, and `0x42`;
     - calls to `BO6_RicCheckFacing`, `BO6_RicSetAnimation`, `BO6_DisableAfterImage`, `BO6_RicSetStand`, `func_us_801B9DE4`, and `BO6_RicCreateEntFactoryFromEntity`;
     - accesses to `RIC_step`, `RIC_anim`, `RIC_pose`, `RIC_poseTimer`, and fields of `g_Ric`.

3. **Upstream and local-corpus search**
   - `upstream_harvest.py --show BO6_RicStepStand` returned: “upstream has no definition for BO6_RicStepStand.” Therefore there is no upstream mechanical copy to harvest.
   - `asm_twin_finder.py --symbol BO6_RicStepStand` returned one strong named twin: `src/ric/pl_steps.c:RicStepStand`. The other token-only candidates are animation helpers, not credible whole-function donors.
   - `RicStepStand` has the same high-level layout: input gate, deceleration, switch on substep, live cases `0`, `1`, `64`, `65`, and `66`.
   - It is not a verbatim transplant: the target uses BO6-prefixed helpers, different capability mask and animation data, and its assembly shows scalar/global access shapes that must be preserved.

4. **Shared header and shim applicability**
   - `shim_sweep.py --overlay bo6 --json` returned `[]`.
   - The local twin is a `.c` body in `src/ric/pl_steps.c`, not a peer-proven shared implementation header. A shim is therefore not justified.

5. **Mechanical-transplant decision**
   - A **bounded adaptation is justified**, but not a blind copy. The target and `RicStepStand` share the full five-case state-machine skeleton, while the target assembly proves BO6-specific helper names, constants, and data symbols.
   - This is suitable for root-controlled adaptation and comparison, not autonomous landing.

6. **Declarations, types, style, and naming**
   - `src/boss/bo6/richter.c:812` already declares several required helpers:
     `BO6_RicCheckInput(s32)`, `DecelerateX(s32)`, `BO6_RicCheckFacing(void)`, `BO6_RicSetStand(s32)`, `BO6_RicSetSpeedX(s32)`, `BO6_RicSetAnimation(AnimationFrame*)`, and `BO6_DisableAfterImage(s32, s32)`.
   - `src/boss/bo6/bo6.h:49` supplies `RicSteps`; `src/boss/bo6/bo6.h:91` defines `RIC` as `g_Entities[STAGE_ENTITY_START]`; `ric_shared.h` supplies Richter timer and blueprint enums.
   - The target calls `BO6_RicCreateEntFactoryFromEntity`, so its exact prototype must be located or retained from an existing BO6 declaration before application. The assembly’s use of `g_CurrentEntity`, a factory value `0x11`, and zero third argument is evidence for call arguments, but not sufficient license to invent a prototype.
   - `docs/STYLE.md` requires project typedefs, braces, four-space indentation, named constants where available, and comments explaining load-bearing odd source shape. `docs/NAMING.md` calls the entity state field `step`.

7. **Bounded candidate**

   The root may start from the `RicStepStand` control-flow skeleton and adapt only the assembly-proven substitutions:

   - `RicCheckInput(...)` to `BO6_RicCheckInput(0x4305C)`
   - `RicDecelerateX(FIX(0.125))` to `DecelerateX(0x2000)`
   - `RicCheckFacing()` to `BO6_RicCheckFacing()`
   - `RicSetStand(0)` to `BO6_RicSetStand(0)`
   - `RicSetAnimation(...)` to `BO6_RicSetAnimation(...)`
   - `DisableAfterImage(1, 1)` to `BO6_DisableAfterImage(1, 1)`
   - player animation/data references to target symbols demonstrated by assembly, including `D_us_80181F1C`, `D_us_80182130`, and `D_us_801822B8`
   - use the exact target substep/pose/step globals or members dictated by the compiler output, rather than normalizing them to a prettier `RIC.*` form.

   The candidate must preserve case order and empty branches, particularly cases `1`, `0x41`, and `0x42`. The target’s case-66 path has a potentially load-bearing call argument/scheduling shape, so it should not be “cleaned up” before a diff.

8. **Complete root-only handoff sequence**

   1. Re-query or directly retrieve the queue record and preserve its existing note.
   2. Locate the exact existing declaration for `BO6_RicCreateEntFactoryFromEntity`; do not infer one.
   3. Apply one bounded `RicStepStand` adaptation to `src/boss/bo6/richter.c`.
   4. Run managed `make_build`.
   5. Run `asm_diff` for `BOSS/BO6` and `BO6_RicStepStand`.
   6. Iterate only on concrete first-divergence evidence, using declaration/access-form corrections before expensive search.
   7. Run managed `make_build` again, then `verify_build`; only 81/81 is a match.
   8. If matched, `queue_report` with a real proof string and `keep_note=True`.
   9. Update `ROADMAP.md` and any relevant lesson documentation.
   10. Stage explicit paths one at a time, commit, and push only to `origin`.

Largest Stage-A uncertainty: the exact source declaration and compiler-visible access form for the factory helper and several scalar aliases. The assembly establishes behavior and addresses, but not all C declaration shapes.

### 2. Stage B

#### B1: authoritative declarations

Real defects:

| Candidate line | Defect | Minimal correction |
|---|---|---|
| `extern u16 g_EInitExample;` | Conflicts with authoritative `extern EInit g_EInitExample;`. The object is an array of five `u16`, not one `u16`. | Remove it, or write `extern EInit g_EInitExample;` |
| `u32 Random(void);` | Conflicts with authoritative signed return type `s32`. It also changes the meaning of `Random() < 0`. | Remove it, or write `s32 Random(void);` |
| `InitializeEntity(&g_EInitExample);` | `&g_EInitExample` has type pointer-to-array, `u16 (*)[5]`; the callee requires `u16*`. | `InitializeEntity(g_EInitExample);` |

`Entity* self` and `self->step++` cannot be condemned from this fixture alone: the authoritative declarations do not define `Entity` or its members. They may be invalid in a real translation unit, but that is not proven here.

Compatible redundancy is repeating an **identical** declaration, for example `extern EInit g_EInitExample;` or `s32 Random(void);`. It is unnecessary but compatible. Replacing either authoritative declaration with an incompatible one is a real conflict.

Confidence: high. Largest uncertainty: none material, except that no `Entity` definition was supplied.

#### B2: GCC 2.7.2 dispatch and scheduling

To reproduce a 51-entry table for indices `0..50`, the source must retain the live bodies at `10`, `11`, `20`, and `40` **and explicitly make the range dense enough to force the table form**. The conservative source shape is explicit empty/fall-through labels for every otherwise-unused index in `0..50`, funneling them to the target’s default/no-op behavior.

- `case 0` and `case 50` establish the observed lower and upper table bounds.
- Empty labels between `0..9`, `12..19`, `21..39`, and `41..50` provide the interior density and individual table destinations. Merely adding the two endpoints leaves four live labels across a 51-value span and still permits GCC to choose a compare chain or a different sparse-switch representation.
- Each empty label must preserve the target’s semantics by falling through to the same default/no-op exit, not introduce a new body.

For scheduling, reorder the nearby source assignments so the Boolean-true write is sourced before the related zero-field write. That gives GCC a live constant-one value it can materialize in the conditional branch’s delay slot, matching the frozen target fact. Writing the zero field first can consume or reschedule the available instruction and change the delay-slot fill.

This is a source-shape recommendation, not a proof that any one rearrangement will force GCC 2.7.2’s exact register allocation. The root still needs a build and assembly comparison.

Confidence: medium-high. Largest uncertainty: exact delay-slot selection is compiler-context-sensitive, so the complete surrounding expression and declarations can still matter.

#### B3: exact submodule path contract

Classification:

| Input | Raw-string contract | Resolved identity | Classification |
|---|---|---|---|
| `tools/psyz` | Exact match | Same directory | Accept |
| `tools/psyz/.` | Not exact | Same directory | Reject: contract defect only |
| `tools/m2c/../psyz` | Not exact | Same directory | Reject: contract defect only |
| Absolute path to that directory | Not exact | Same directory | Reject: contract defect only |

Correct validation order:

1. Read the exact raw allowed paths from `.gitmodules`.
2. Require the supplied raw string to equal one declared raw path exactly.
3. Resolve the supplied and declared paths.
4. Apply the existing containment check to the resolved supplied path.
5. Compare resolved filesystem identities as a defense-in-depth consistency check.

The evidence proves **no repository escape**: all rejected examples resolve to the declared in-repository directory, and containment already rejects resolved paths outside the repository. It does prove a **contract defect** if the implementation accepts any of the three non-exact spellings merely because identity comparison succeeds.

Evidence: `.gitmodules:22` declares the raw path exactly as `tools/psyz`.

Confidence: high. Largest uncertainty: whether the current implementation currently accepts aliases was not tested, because this fixture supplies the implementation behavior abstractly rather than its source.

### 3. Score

| Dimension | Score | Rationale |
|---|---:|---|
| Process fidelity | 92/100 | Followed read-only and cheapest-first requirements. Per-record queue history could not be retrieved from capped connector output. |
| Evidence correctness | 88/100 | Strong live evidence for stub, assembly, upstream absence, twin, and no shim. Exact factory-helper declaration remains unverified. |
| Honesty | 98/100 | No match or compile claim; stated queue and declaration limitations directly. |
| Candidate utility | 84/100 | Gives a constrained donor-based adaptation and explicit root workflow, while refusing a blind transplant. |
| Expected economics | 86/100 | Cheap twin adaptation is worth a root diff; expensive search should wait for concrete divergence. |

### 4. Recommendation

**Root-gated read-only support.**

This run demonstrated useful evidence gathering, disciplined refusal to claim a match, and a bounded candidate/handoff. It did not establish reliability for autonomous stateful worker ownership, compiler-last-mile decisions, or queue/Git/build operations.
