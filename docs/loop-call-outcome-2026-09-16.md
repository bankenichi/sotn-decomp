# Loop and per-iteration-call outcome: what landed, what refused, and why calls stay open

Date: 2026-09-16. Branch: `automation/instrumented-search`. Oracle: 113/113 throughout.
Status: do-while, while-form, and in-loop branch joins are landed and proven.
Per-iteration calls are NOT landed. Both working-tree files were reverted to
the last green commit after a long variant sweep broke invariants.

## What landed

Do-while lowering (commit `9daec3468`): admitted straight-line regions with
one backward conditional latch lower to `do {} while ()` with materialized
loop-carried scalars and pointers, a load-first exemption for scratch temps,
one shared `loop_regions` admission helper serving lowering and census, and
every definition site routed through `_define`. Fixture proof: counter,
pointer-walk sum, and store loops render host-exact, plus 7 refusal shapes
(nested, call, mult, while-shape, marker, delay-hazard, outside-entry).

While-form lowering (commit `fb4de9db4`): unconditional backward latches with
exactly one forward exit lower to do-while-break or test-first while via exact
operator negation (beq to bne, bltz to bgez, bgtz to blez). Old `while-latch`
refusals absorbed into 33 admitted while regions. Fixture proof: sentinel-sum
(catches delay-slot misordering), zero-trip while (n=0 returns 0, proving
while-vs-do fidelity), early-exit counter. Renderer 73/73, measure 10/10.

In-loop branch joins (commit `86c91ed99`): bare-if spans inside admitted
regions lower with exact taken/fall merging. Join temps are pre-initialized so
the taken arm consumes prior-iteration state exactly once. Regions route by
start so no double lowering. Refusal taxonomy split into nested-loop,
call-in-loop, return-in-loop, crossing-branch, and branch-in-loop, each with
focused tests. Fixture proof: divergent-value join host-exact plus
scratch-temp coverage. Renderer 75/75.

## Measured effect

Sharded pool over the live queue at default limits (4 shards, 283 files, zero
errors): 260 active files after 23 stale matched skips, 0 new renders.
Admitted-but-blocked is only 6 declared plus 16 size-limited, so loop support
is additive and waiting on other slices. Refusal file-votes: call-in-loop 112,
branch-in-loop 49, undeclared TU 63, multi-exit 27, nested-loop 26,
outside-entry 14, barred-op 11, return-in-loop 3, while-no-exit 2,
crossing-branch 1.

Raised limits (`--limits raised`) add 0 flips: 213 of 282 unrendered files
fit within 512 instructions and refuse on shape, only 69 exceed it, and most
of those carry loops that refuse first anyway.

## Why calls stay open

Every variant broke one of two invariants, and all were reverted:

1. The existing call lowering pops every volatile after each `jal`.
   Loop-carried registers are exactly the volatiles that must survive, so each
   variant either corrupted the carrier set or refused every call site.
2. The `_define` materialization path assumes one value per destination per
   pass. A call result that must be fresh each iteration fights that
   assumption: routing through `_define` stuck, bypassing it corrupted
   carriers.

Secondary finding: the admission helper could not distinguish declared from
declared-and-loop-safe without threading callee facts through `loop_regions`,
and that threading interacted badly with the receiver path. A long probe
series (LOOPCALL markers) confirmed each failure point before the revert.

## What next needs

Calls need a fresh design from a call-free loop corpus, not another variant
sweep: a per-iteration call-result temp that is neither a carrier nor a plain
volatile, plus callee-declared admission decided once per region. After that:
multi-exit joins, nesting, return-in-loop, switch dispatch, then bigger
ceilings for the 69 size-blocked files. Queue lanes stay deferred by the
September 8 owner order.
