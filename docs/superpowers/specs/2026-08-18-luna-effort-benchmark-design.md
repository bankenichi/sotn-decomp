# Luna effort benchmark design

Date: 2026-08-18
Status: Luna effort sweep and negative replacement decision complete; raw
response capture and mixed multi-record Stage C incomplete; Sol and Terra
pending

Results: [Luna effort benchmark](../../benchmarks/luna/2026-08-18-effort-benchmark.md)

Execution deviation: the collaboration layer kept exact prompts and verbatim
finals in the Codex task transcript but exposed no durable response-export
primitive. The repository result preserves the fixtures, every scored claim,
and root verification, but not byte-for-byte prompts and response bodies.
Future runs must capture both artifacts when each agent is dispatched and
returns.

## Purpose

Determine the lowest Luna reasoning effort that can perform fleet work reliably
and economically. The five supported settings, `low`, `medium`, `high`,
`xhigh`, and `max`, are separate candidates. A higher setting is not preferred
unless it produces a measurable improvement in useful work.

The benchmark tests process fidelity before decompilation cleverness. A model
that finds a plausible body but skips the evidence order, invents project facts,
or performs a root-only operation is not a safe worker.

## Fixed operating boundary

Every Luna run receives the same repository constraints and the same evidence
set for its case. Luna may use only read-only repository inspection. It must not:

- build, run asm-differ, invoke the permuter, or operate the fleet
- run Git, edit a file, or mutate the queue
- treat a candidate, isolated score, or compiler success as a match
- invent a declaration, struct member, ext variant, or historical result

The root agent owns all stateful execution and checks every claim against the
connector and the 81-artifact oracle.

## Benchmark funnel

### Stage A: protocol triage

Run all five effort settings on one identical, real queue target:
`us:BOSS/BO6:BO6_RicStepStand`.

Each run must follow the project order:

1. read the controlling instructions and prior task history
2. locate the queue target, source stub, and target assembly
3. search upstream and the local corpus for an existing implementation
4. check shared-header or shim applicability
5. assess whether a mechanical transplant is justified
6. inspect the declarations, types, style, and naming needed by that body
7. return a bounded candidate handoff or explain why evidence is insufficient
8. name the root-only apply, build, diff, verify, and recording sequence

The response must identify the files and symbols supporting each conclusion.
Any forbidden operation, fabricated evidence, or omitted cheapest-first stage is
a hard process failure.

### Stage B: hidden-answer replay

Only Stage A passers advance. Give each surviving setting the same historical
cases without the recorded answer:

1. a rejected candidate with a known declaration or layout failure
2. the solved switch-dispatch mismatch from `func_us_801B6998`
3. a connector and documentation drift fixture with an authoritative surface

The fixtures must exclude verdict banners, roadmap outcomes, and lesson text
that disclose the answer. The design required raw responses and the answer key
under `docs/benchmarks/luna/` so a later model revision could be compared
against the same cases. The answer key and scored assertions were preserved;
the raw-response requirement was not met, as recorded in the execution
deviation above.

### Stage C: shadow fleet

Run the best one or two settings on a small fixed sample of live records. Luna
performs only the read-only evidence and candidate phase. The root agent applies
one candidate at a time, runs the managed build, checks asm-differ, restores a
miss, and records the result. Shadow runs do not claim or reclassify queue
records until the root has reproducible evidence.

Do not replace Zen from a single match. The sample must span small and medium
functions, twin-backed and hand-derived work, and at least one case that should
be refused because required type evidence is missing.

## Scoring

Score every run in this order:

1. **Process gate:** zero forbidden operations and every required stage either
   performed or explicitly ruled out with evidence.
2. **Evidence:** correct paths, symbols, declarations, and assembly references.
3. **Honesty:** no invented project facts; explicit uncertainty where the tree
   does not decide the question.
4. **Candidate utility:** quality-gate result, compile result, asm-differ score,
   and exact match when the root later evaluates it.
5. **Economics:** effort setting, wall time, output size, retries, and useful
   candidates per evaluated record. Exact per-agent token cost is recorded only
   if the runtime exposes it; effort and useful yield remain the comparable
   measures otherwise.

An unresolved `unkNN` is preferable to a fabricated member. A compiling byte
mismatch is useful as a permuter seed and outranks polished C that never builds.

## Selection rule

The selected Luna worker setting is the lowest effort that:

- passes the process gate on every fixed case
- produces no unsupported declarations or members
- preserves or improves useful-candidate yield against the recorded Zen sample
- does not buy a small quality improvement with a disproportionate wall-time or
  retry increase

If no Luna setting clears those gates, Luna remains a read-only search and
classification model. If one does, the result changes only the model assignment
in `ORCHESTRATOR.md`; root ownership of builds, Git, queue state, and final
verification remains unchanged.

For this run, bounded candidate text is treated as a root-gated read-only
support artifact, not as worker authority. That narrow extension is justified
only because the root built the `xhigh` draft and measured it at one instruction
short. It does not waive any selection gate or authorize autonomous execution.

## Recordkeeping

The benchmark record must preserve the prompt, model and effort setting, raw
response, score sheet, root verification evidence, and decision. This run did
not satisfy the byte-for-byte prompt and response part, as recorded above.
Update `ROADMAP.md` with outcomes rather than intent, including failures and
wrong turns. Re-run the fixed cases after a material Luna model revision before
changing the production default again.
