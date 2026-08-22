# Terra high full-sweep raw response

Model: `gpt-5.6-terra`
Effort: `high`
Input: `terra-effort-input.md`
Stateful actions: none

## Stage A

Process-gate result: **pass for read-only triage; autonomous application blocked.** I performed no edits, builds, asm-diff, permuter, fleet, Git command, or queue mutation. The only state-adjacent call was `transplant.py` without `--apply`; it reported a dry run and wrote nothing.

Evidence trail:

1. Controls: the benchmark input, repository `AGENTS.md`, `docs/TOOLING.md`, `docs/STYLE.md`, and `docs/NAMING.md` require cheapest-first discovery, real declarations/members, and root-owned build and queue operations.

2. Target location:
   - Stub: `src/boss/bo6/richter.c:810`, `INCLUDE_ASM(..., BO6_RicStepStand)`.
   - Target assembly: `asm/us/boss/bo6/nonmatchings/richter/BO6_RicStepStand.s`, 153 instructions.
   - The live queue is not directly addressable by ID through the exposed read-only surface. However, `queue_coverage.py --overlay BOSS/BO6` reports 44 live stubs, 123 queue records, and `BLIND (0)`, proving a live BO6 queue record exists for every stub including this one. The available status listings are truncated before this target, so I cannot honestly state its current status or note.

3. Upstream/local corpus:
   - `upstream_harvest.py --show BO6_RicStepStand` returned: “upstream has no definition.”
   - `asm_twin_finder.py --symbol BO6_RicStepStand` found one strong local donor: `src/ric/pl_steps.c:RicStepStand`.
   - The local donor is not a mechanical copy. Its opening ember-spawn block and playable-Richter state accesses are absent from the BO6 target, whose first operation is `BO6_RicCheckInput(0x4305C)`.

4. Shared-header/shim gate:
   - `shim_sweep.py --overlay bo6` returned: “No stub file matches a shared header that any peer already shims.”
   - Therefore, no header/shim route is justified.

5. Mechanical-transplant gate:
   - Dry-run `transplant.py --function BO6_RicStepStand` labeled the local body “ready,” but that only establishes a textual donor. The target assembly disproves a straight transplant because it lacks the donor’s initial `PLAYER.step < 64` ember logic and uses BO6-specific helpers/data.
   - Conclusion: **do not mechanically transplant the generated 2681-character donor.**

6. Relevant preserved target history:
   - `automation/candidates/history/us_BOSS_BO6_BO6_RicStepStand.v0005.c` is a bounded, compiling historical candidate. Its frozen receipt says `make_build` completed and `verify_build` was 80/81, with only `BO6.BIN` different; `overlay_size_check.py` localized the function to `-0x4` bytes.
   - `MATCHING-LESSONS.md` independently records the 80/81 result and explains why preserving the exact compiling body matters.
   - This is frozen historical evidence, not a current match claim. I did not recompile it.

7. Declaration/type evidence for that candidate:
   - `src/boss/bo6/bo6.h` defines `RIC` as `g_Entities[STAGE_ENTITY_START]` and declares `PlayerState g_Ric`.
   - `config/symbols.us.bobo6.txt:17` defines the required flat symbol `RIC_step = 0x80076304`.
   - Existing BO6 code declares `D_us_80181F1C` and `D_us_80182130` as `AnimationFrame[]`; the preserved candidate supplies the remaining target-specific declarations, including `D_us_801822B8`, `RIC_anim`, `RIC_pose`, and `RIC_poseTimer`.
   - The candidate’s old-style `func_us_801B9DE4(void)` declaration is not the authoritative type. The actual definition is `func_us_801B9DE4(s32 unused)`; a root retest should use `extern void func_us_801B9DE4(s32);` and call `func_us_801B9DE4(0)`. The preserved note says this typed-call variant remained `-0x4`, so it is not presented as a solved codegen change.

Bounded handoff:

- Start from the exact body in `automation/candidates/history/us_BOSS_BO6_BO6_RicStepStand.v0005.c`, not the naïve `RicStepStand` transplant.
- Treat it as a **near candidate**, not a match. The remaining error is four bytes in BO6 and needs root-owned asm-diff/codegen work.
- The highest-value next comparison is the control shape around the five `RIC.step_s` cases. The target:
  - has no ember preamble;
  - uses `BO6_RicCheckInput(0x4305C)` and `DecelerateX(0x2000)`;
  - calls `func_us_801B9DE4(0)` in cases 0 and 1;
  - writes flat `RIC_step` and `RIC_anim` in case `0x40`;
  - preserves `BO6_RicCheckFacing()` calls for their side effects even when their return is unused.

Required root-only sequence:

1. Confirm a green baseline with `verify_build`, and obtain the exact queue record/status through an untruncated root-owned queue inspection.
2. Acquire the BuildLock only when Zen is idle; surgically replace the one `INCLUDE_ASM` stub with the bounded candidate and its exact, typed declarations.
3. Run `make_build`, then immediately `verify_build`. Do not call it a match unless this returns exactly 81/81.
4. If not green, use `asm_diff` and `overlay_size_check` on BO6 to explain the residual, archive the tested candidate generation, and restore or retain it only under the owner’s chosen near-candidate workflow.
5. If and only if 81/81, call `queue_report(... status="matched", proof=<full verify evidence>, keep_note=True)`. Otherwise report/retain `near` evidence, never `matched`.
6. Update `ROADMAP.md` with the observed outcome, then explicitly stage each changed path, commit, and push only to `origin`.

Confidence: **0.91**. Largest uncertainty: the connector cannot return the individual live queue record without truncation, and the exact source-shape cause of the archived `-0x4` residual needs a fresh root-owned diff.

## Stage B1: authoritative declarations

Defects:

- `extern u16 g_EInitExample;` conflicts with `extern EInit g_EInitExample;`. `EInit` is `u16[5]`, not one `u16`.
- `u32 Random(void);` conflicts with authoritative `s32 Random(void);`. It also changes `Random() < 0` from a meaningful signed test into an always-false unsigned comparison.
- `InitializeEntity(&g_EInitExample);` passes `EInit*`, a pointer to an array of five `u16`, where the function requires `u16*`. Array-to-pointer decay is required here.
- The fixture does not authoritatively declare `Entity` or its `step` member. In a standalone unit, `Entity* self` and `self->step` require the real entity header. Do not invent an `Entity` layout.

Minimal corrected lines:

```c
/* Prefer including the authoritative header and deleting duplicate prototypes. */
extern EInit g_EInitExample;
s32 Random(void);

InitializeEntity(g_EInitExample);
```

An exact repeated declaration, such as `extern EInit g_EInitExample;`, `s32 Random(void);`, or `void InitializeEntity(u16*);`, is compatible redundancy, although unnecessary. The candidate’s scalar `g_EInitExample` declaration and unsigned `Random` declaration are real conflicts.

Confidence: **0.99**. Largest uncertainty: only the omitted authoritative Entity declaration, not the listed extern/call issues.

## Stage B2: GCC 2.7.2 switch dispatch and scheduling

The candidate’s four-label switch is too sparse to explain a target 51-entry table covering `0..50`.

Most likely required source shape:

- Establish the lower and upper table bounds with explicit `case 0` and `case 50`.
- Give every hole in `0..50` an explicit route to the common default path, grouped by intervals:
  - `0..9` before live case 10;
  - `12..19` between live cases 11 and 20;
  - `21..39` between live cases 20 and 40;
  - `41..50` after live case 40.
- Retain individual live bodies only at 10, 11, 20, and 40.

The endpoints are necessary because they establish the target table’s range. The interior hole labels are necessary to make their indices explicit jump-table entries to the common default target and to provide the density GCC needs to prefer a table over comparisons. Merely adding the endpoints does not establish the target’s internal dispatch mapping or necessarily satisfy GCC 2.7.2’s table-selection heuristic.

For scheduling, reverse the related stores so the direct Boolean-true assignment occurs before the related zero assignment, and keep it as a direct `field = 1`/`field = true` statement in the same control region. The target’s constant-one materialization in a branch delay slot is evidence that this source ordering and local branch pressure matter. Avoid wrapping the true assignment in a helper or folding it into an expression, because either can remove the scheduling opportunity.

The frozen facts do not determine the mathematically smallest set of explicit hole labels: that depends on GCC 2.7.2’s heuristic and on whether its common-default labels coalesce identically. The conservative all-indices shape is the evidence-based route to test; the exact minimal form requires compiler output comparison.

Confidence: **0.84**. Largest uncertainty: GCC’s precise jump-table density threshold and label coalescing for this switch.

## Stage B3: exact submodule path contract

Classification:

| Input | Result |
|---|---|
| `tools/psyz` | Accept: exact declared raw string, then identity and containment checks pass. |
| `tools/psyz/.` | Reject: resolves to the same directory but is not the declared raw string. |
| `tools/m2c/../psyz` | Reject: resolves to the same directory but is not the declared raw string. |
| Absolute path resolving to `tools/psyz` | Reject: identity is not authorization; it is not the declared raw string. |

Correct validation order:

1. Preserve the caller’s raw string.
2. Require exact membership in the raw `.gitmodules` path set.
3. Resolve the selected declared path and the caller path to filesystem identities.
4. Apply containment checks to resolved paths.
5. Require identity equality as a defense against symlink/race/path-resolution surprises.

Resolving before enforcing exact raw membership turns aliases into accepted inputs. The stated containment check means this evidence does **not** prove a repository escape. It proves a **contract defect** if the implementation accepts the three aliases solely because their resolved identities match.

Confidence: **0.96**. Largest uncertainty: whether an unmentioned raw-string membership check already precedes the identity comparison. If it does, the implementation rejects the aliases and there is neither escape nor defect.

## Score table

| Dimension | Score | Basis |
|---|---:|---|
| Process fidelity | 9/10 | Used only read-only repository/connector inspection and exhausted upstream, twin, shim, then transplant gates. |
| Evidence correctness | 9/10 | Every Stage A conclusion is tied to a live file/tool result or explicitly labeled frozen historical evidence. |
| Honesty | 10/10 | No current compile or match is claimed; queue-record status and residual cause are explicitly unresolved. |
| Candidate utility | 8/10 | Preserved 80/81, `-0x4` body is a strong bounded near candidate, but not safe to apply autonomously. |
| Expected economics | 8/10 | Avoids rediscovering a compiling body; one root-owned diff cycle is much cheaper than model-fleet retries. |

Recommendation: **root-gated read-only support**. The model can reliably collect evidence and prepare a bounded handoff, but this candidate is intentionally one build-verification step short of a match and must remain under root/BuildLock control.
