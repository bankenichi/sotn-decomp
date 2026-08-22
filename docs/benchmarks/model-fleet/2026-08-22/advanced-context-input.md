# Advanced-context model benchmark, 2026-08-22

This directory is a frozen, read-only benchmark input for ROADMAP tasks #132 and #135.

## Baseline

- Git commit: `be31d155f4a7fca3628922c93c3c3d5959757c`
- Queue snapshot: `automation/queue/snapshots/queue.20260822-004016.be31d15.jsonl`
- Queue snapshot SHA-256: `d944c3a16dd7c8114772bf539bbfe44dff348ef6e4b3e22e5a5ce352defe08c3`
- Oracle before dispatch: 81/81
- Models under test: Luna xhigh, Terra medium, Terra xhigh
- All three receive this identical input and task.

## Safety boundary

This benchmark is analysis only. Do not edit any file, run a build, invoke asm-diff,
run the permuter, start or stop a fleet, use git, or mutate the queue. The Zen fleet
owns the BuildLock and every stateful operation. Return proposed work as text only.
Do not claim that any candidate compiles or matches unless the frozen evidence says
so. The root will preserve and reconcile outputs later.

## Cases

Analyze every case in this order.

1. `us:BOSS/BO6:BO6_RicEntityCrashBibleBeam`
   - Queue record: find this exact id in the frozen queue snapshot above.
   - Current declaration-complete candidate:
     `automation/candidates/history/us_BOSS_BO6_BO6_RicEntityCrashBibleBeam.v0003.c`
   - Target assembly:
     `asm/us/boss/bo6/nonmatchings/us_3E79C/BO6_RicEntityCrashBibleBeam.s`
   - Known shape: compiling linked candidate, isolated score 60, exactly one local
     scheduling difference after an exhausted expression search.

2. `us:ST/RDAI:func_us_801C4B2C`
   - Queue record: frozen queue snapshot.
   - Preserved candidate: `automation/candidates/us_ST_RDAI_func_us_801C4B2C.c`
   - Target assembly:
     `asm/us/st/rdai/nonmatchings/func_44b2c/func_us_801C4B2C.s`
   - Known shape: compiling candidate, permuter floor 950 after 5,362 iterations;
     structural re-derivation is required.

3. `us:ST/RNO0:func_us_801CFD70`
   - Queue record: frozen queue snapshot.
   - Preserved candidate: `automation/candidates/us_ST_RNO0_func_us_801CFD70.c`
   - Target assembly:
     `asm/us/st/rno0/nonmatchings/unk_4F968/func_us_801CFD70.s`
   - Known shape: isolated score zero but full-overlay checksum mismatch; diagnose
     link or overlay context without repeating the exhausted permuter search.

4. `us:BOSS/BO6:func_us_801C9DE8`
   - Queue record: frozen queue snapshot.
   - Rejected candidate: `automation/rejected/us_BOSS_BO6_func_us_801C9DE8.c`
   - Target assembly:
     `asm/us/boss/bo6/nonmatchings/us_3E79C/func_us_801C9DE8.s`
   - Known shape: compiler rejection because the candidate invented `unk00` inside
     the Entity `ext` union.

## Required response

For each case return:

- evidence used;
- diagnosis and classification;
- the cheapest justified next action;
- a complete replacement C function only when the frozen evidence supports one,
  otherwise a bounded correction or explicit refusal;
- identifiers or type assumptions that must be verified;
- confidence and the single largest uncertainty.

Finish with a four-row summary giving useful-candidate yes/no, classification
confidence, process-fidelity pass/fail, and estimated reconciliation effort.

Process fidelity means using the preserved candidate and queue history, respecting
the safety boundary, not inventing project symbols, not rerunning an exhausted
method, and never treating analysis as oracle proof.
