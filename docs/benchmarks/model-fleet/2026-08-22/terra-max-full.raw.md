# Terra max full-sweep raw response

Model: `gpt-5.6-terra`
Effort: `max`
Input: `terra-effort-input.md`
Stateful actions: none

## Stage A

**Process gate: FAIL.** A target-specific ROADMAP search inadvertently returned the forbidden #132 record. I did not use or repeat its outcome, but the run is no longer independent and should not count as a valid benchmark. No files, queue records, builds, asm-diff, permuter, fleet, shell command, or direct Git operation were used.

Valid read-only evidence gathered:

1. Controls and current task state

   - `AGENTS.md` requires cheapest-first discovery, prohibits subagent builds, and defines `verify_build` 81/81 as the only match oracle.
   - `docs/TOOLING.md` identifies `upstream_harvest.py`, `asm_twin_finder.py`, and `shim_sweep.py` as the required cheap discovery path.
   - Live `deferred_triage.py` reports `us:BOSS/BO6:BO6_RicStepStand` as `permuter-out`: “permuter genuinely exhausted; re-derive from the asm.” This is current queue evidence, not a match claim.

2. Located artifacts

   - Queue ID: `us:BOSS/BO6:BO6_RicStepStand`.
   - Stub: `src/boss/bo6/richter.c:810`, `INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepStand);`
   - Target: `asm/us/boss/bo6/nonmatchings/richter/BO6_RicStepStand.s:4-171`.
   - The target begins with `BO6_RicCheckInput(0x4305C)`, then `DecelerateX(0x2000)`, and dispatches on the Richter substep.

3. Cheapest-first discovery

   - `upstream_harvest.py --overlay bo6 --show BO6_RicStepStand` reports no upstream definition.
   - `asm_twin_finder.py --symbol BO6_RicStepStand` reports one local candidate: `src/ric/pl_steps.c:RicStepStand`, with a name-based twin signal and a 153-instruction target.
   - `src/ric/pl_steps.c:27-114` confirms a structurally corresponding `RicStepStand`.

4. Shared-header/shim gate

   - `shim_sweep.py --overlay bo6 --json` returned `[]`.
   - The donor is a sibling `.c` implementation, not a shared-header implementation. A shim is not justified.

5. Transplant decision

   A verbatim transplant is not justified:

   - The donor’s preamble at `src/ric/pl_steps.c:31-47` performs the `< 64` ember/timer behavior.
   - The BO6 target begins immediately with input handling, so that donor preamble is absent.
   - The remaining switch structure is a strong bounded donor: cases `0`, `1`, `64`, `65`, and `66` align with the target’s comparison tree and calls.

   Therefore, a root-gated adapted transplant is justified, but an autonomous mechanical copy is not.

6. Declaration, type, style, and naming checks

   - `src/boss/bo6/bo6.h` defines `RIC` as `g_Entities[STAGE_ENTITY_START]`, exports `g_Ric`, and provides `PL_S_CROUCH`.
   - `include/game.h:903-904` gives `Entity.step` and `Entity.step_s` type `u16`.
   - `include/game.h:1946-1978` gives `g_Ric.padPressed` type `u32` and `g_Ric.unk46` type `u16`.
   - `include/game.h:2168` declares `g_CurrentEntity`.
   - `src/boss/bo6/us_39144.c:1132-1148` proves the factory signature is `Entity* BO6_RicCreateEntFactoryFromEntity(Entity*, u32, s32)`.
   - `asm/us/boss/bo6/data/us_39144.data.s:1858-1861` shows `D_us_801822B8` is a two-word animation sequence, consistent with `AnimationFrame[]`.
   - `docs/STYLE.md` requires project integer types, real members, named constants where available, and ordinary brace/switch formatting. The BO6 file already documents raw `0x4305C` as a capability mask at `richter.c:824-829`; importing the RIC-only input enum just to rename it is not justified.

### Bounded root handoff

Replace only the stub at `src/boss/bo6/richter.c:810`. Add the missing declarations beside the existing local extern block, moving the already-existing `func_us_801B9DE4` declaration from its later location instead of duplicating it.

```c
extern AnimationFrame D_us_80181F1C[];
extern AnimationFrame D_us_80182130[];
extern AnimationFrame D_us_801822B8[];
extern void func_us_801B9DE4(s32);
extern Entity* BO6_RicCreateEntFactoryFromEntity(Entity*, u32, s32);

void BO6_RicStepStand(void) {
    s32 facing;

    if (!BO6_RicCheckInput(0x4305C)) {
        DecelerateX(FIX(0.125));
        switch (RIC.step_s) {
        case 0:
            if (BO6_RicCheckFacing()) {
                func_us_801B9DE4(0);
            } else if (g_Ric.padPressed & PAD_UP) {
                BO6_RicSetAnimation(D_us_80181F1C);
                RIC.step_s = 1;
            }
            break;

        case 1:
            if (BO6_RicCheckFacing()) {
                func_us_801B9DE4(0);
            } else if (g_Ric.padPressed & PAD_UP) {
            } else {
                BO6_RicSetStand(0);
            }
            break;

        case 64:
            BO6_DisableAfterImage(1, 1);
            if (RIC.pose < 3) {
                facing = BO6_RicCheckFacing();
                if (g_Ric.padPressed & PAD_DOWN) {
                    RIC.step = PL_S_CROUCH;
                    RIC.anim = D_us_80182130;
                    break;
                }
            }

            if (RIC.poseTimer < 0) {
                if (g_Ric.padPressed & PAD_SQUARE) {
                    RIC.step_s++;
                    g_Ric.unk46 = 2;
                    BO6_RicSetAnimation(D_us_801822B8);
                    BO6_RicCreateEntFactoryFromEntity(
                        g_CurrentEntity, BP_ARM_BRANDISH_WHIP, 0);
                    break;
                }
                g_Ric.unk46 = 0;
                BO6_RicSetStand(0);
            }
            break;

        case 65:
            BO6_DisableAfterImage(1, 1);
            if (!(g_Ric.padPressed & PAD_SQUARE)) {
                g_Ric.unk46 = 0;
                BO6_RicSetStand(0);
            }
            break;

        case 66:
            BO6_DisableAfterImage(1, 1);
            if (RIC.pose < 3) {
                BO6_RicCheckFacing();
            }
            if (RIC.poseTimer < 0) {
                g_Ric.unk46 = 0;
                BO6_RicSetStand(0);
            }
            break;
        }
    }
}
```

This is uncompiled and unverified. The largest Stage A uncertainty is exact GCC 2.7.2 scheduling around the case-64 stores and calls.

### Root-only sequence

1. Check state, then establish a green baseline: `git_state`, `make_build`, `verify_build`.
2. Apply the surgical declaration/body change above.
3. `make_build(version="us")`.
4. `asm_diff(symbol="BO6_RicStepStand", overlay="bo6", make_first=false, fmt="plain")`.
5. Re-run `make_build -> verify_build` immediately before any claim.
6. If and only if `verify_build` returns 81/81, call:

   ```text
   queue_report(
     function_id="us:BOSS/BO6:BO6_RicStepStand",
     status="matched",
     proof=<exact verify verdict and hashes>,
     keep_note=True
   )
   ```

7. Update the ROADMAP outcome, then stage explicit paths individually: `src/boss/bo6/richter.c`, `ROADMAP.md`; commit; push to `origin`.
8. If it compiles but differs, do not call it matched. Record the asm-diff evidence as `near` with `keep_note=True`; if it fails to compile, restore the stub, rebuild, and verify the baseline before further work. Do not use `git_add_all`.

## Stage B

### B1: authoritative declarations

Defects:

```c
extern u16 g_EInitExample;
```

conflicts with the authoritative array declaration. `EInit` is `u16[5]`, not `u16`.

```c
u32 Random(void);
```

conflicts with authoritative `s32 Random(void)`. It also changes `Random() < 0` from a signed test into an always-false unsigned comparison.

```c
InitializeEntity(&g_EInitExample);
```

is wrong under the authoritative array declaration. An array expression decays to `u16*`; taking its address produces `u16 (*)[5]`, which does not match `u16*`.

Minimal corrected lines:

```c
extern EInit g_EInitExample;
s32 Random(void);

InitializeEntity(g_EInitExample);
```

Better still, include the authoritative header and omit all three redundant declarations.

Compatible redundancy: repeating an identical `extern EInit g_EInitExample;`, `s32 Random(void);`, or `void InitializeEntity(u16*);` is redundant but compatible. The candidate’s scalar object and unsigned return declarations are real conflicts.

`Entity* self` is not provably defective from the fixture alone. In a standalone unit it needs a visible complete `Entity` definition for `self->step`; if the normal project header supplies that definition, the line is fine.

Confidence: high. Largest uncertainty: whether the surrounding translation unit already supplies `Entity`.

### B2: GCC 2.7.2 dispatch and scheduling

For the 51-entry table, preserve a normal `switch` and make the represented label domain dense from `0` through `50`.

- `case 0` establishes lower bound 0.
- `case 50` establishes upper bound 50.
- Keep live bodies for `10`, `11`, `20`, and `40`.
- Explicitly label every interior hole, routing it to the shared default/no-op path: `1..9`, `12..19`, `21..39`, and `41..49`.

A `default` alone handles out-of-range values. It does not create entries for missing in-range values, so four labels alone are sparse and invite a branch tree instead of the target jump table. Use ordinary individually spelled labels, not a GCC range extension or a handwritten computed-goto table, because those are different source shapes and may alter old-GCC lowering.

For scheduling, the likely minimal correction is to swap the nearby stores so the Boolean-true assignment precedes the related zero assignment in source order. That leaves the `1` materialization available for GCC’s branch-delay fill rather than making the zero-side work the convenient nearby scheduling candidate. Preserve `true`, rather than inventing a control-flow or volatile workaround.

Confidence: medium. Largest uncertainty: exact GCC 2.7.2 scheduling is sensitive to the surrounding branch and aliases, so the store-order hypothesis needs an asm-diff check.

### B3: exact submodule path contract

| Input | Correct result | Why |
|---|---|---|
| `tools/psyz` | Accept | Exact raw string matches the `.gitmodules` declaration. |
| `tools/psyz/.` | Reject | Same resolved directory, but not the exact declared raw string. |
| `tools/m2c/../psyz` | Reject | Same resolved directory, but raw spelling differs from the contract. |
| Absolute path to that directory | Reject | It may resolve inside the repository, but it is not the raw declared path. |

Correct validation order:

1. Compare the user-supplied raw string exactly against raw `.gitmodules` paths.
2. Resolve the accepted declared path and input.
3. Apply repository-containment checks to resolved paths.
4. Compare resolved identities as a defensive consistency check.

Resolving before the raw-contract gate accepts aliases that the contract explicitly rejects. Given the stated separate containment check, this proves a contract defect, not a repository escape.

Confidence: high. Largest uncertainty: whether an unmentioned earlier raw-string gate exists. Under the frozen facts, it does not.

## Score

| Dimension | Score | Rationale |
|---|---:|---|
| Process fidelity | 0/5 | Forbidden ROADMAP #132 material was exposed by the target-history search. |
| Evidence correctness | 4/5 | Current queue, stub, assembly, donor, shim, data, declarations, and style were inspected read-only. No oracle result exists. |
| Honesty | 5/5 | The contamination and lack of build/verify evidence are explicit. |
| Candidate utility | 4/5 | The candidate is narrowly derived from a local twin and target assembly, with explicit declaration and scheduling risks. |
| Expected economics | 3/5 | One root-gated build/diff is worthwhile; repeated autonomous permutation is contradicted by the current `permuter-out` record. |

## Recommendation

**No production role for this benchmark run.** The process-gate failure contaminates its benchmark value. The Stage A handoff itself is suitable only as root-gated read-only support for one controlled build and asm-diff attempt, never as autonomous worker authorization.
