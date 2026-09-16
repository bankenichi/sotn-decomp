# Loop and per-iteration-call outcome: what landed, what refused, and why calls stay open

Date: 2026-09-16. Branch: `automation/instrumented-search`. Oracle: 113/113 throughout.
Historical status, before the September 15 review below: do-while, while-form,
and in-loop branch joins were landed with the fixture coverage listed here.
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

## September 15 review and correction

The preceding report was dated September 16 by its author; this review uses
the session date, September 15. Earlier outcomes and diagnoses remain above
as evidence, with the following explicit corrections.

**Verdict:** bounded target-owned rendering is useful as a deterministic
candidate generator, but the existing fixtures did not establish general
loop correctness. Nor did the large structural refusal count establish that
adding calls alone would unlock complete functions. Task #302 stays open.

**Retracted diagnosis:** loop-carried registers are not necessarily volatile,
and a caller must not assume volatile registers survive a call. Exempting them
from invalidation would generate incorrect C. The actual conflict was between
mutable C storage and the interpreter's map of currently valid register
values. `_define` can process multiple definitions when these are separate.
The existing `call_result_` temporary already provides a distinct call result;
it must be assigned at the call site inside the loop, not hoisted.

Reproductions against the previous implementation exposed an infinite loop
when a latch delay slot changed its predicate operand, a skipped delay-slot
effect on zero-trip exit, and `NameError` in `_assign_carried`. Review also
found stale join initialization and loss of a value assigned inside a while
loop but used only after exit. These are renderer defects, not compiler quirks.

The repair shares direct/API call lowering between ordinary paths and loops.
A bounded discovery pass records actual live-ins, including implicit call
arguments after delay slots and conditional reads. Emission uses separate
carrier storage and valid-value maps, instruction-local snapshots, predicates
captured before delay slots, and joins initialized at the branch site. Known
live-outs retain storage on zero-trip paths. Backedge validation refuses any
lost live-in. Both passes consume the existing path budget.

Call clobbering remains mandatory for volatile registers, argument-home stack
words and HI/LO state. Missing declarations, unsafe frames, unbound indirect
calls, and reads of clobbered values refuse. Loop stack writes, nonlocal exits,
multiple exits, nested loops and in-loop switch dispatch remain unsupported.
Standalone switch dispatch was already implemented in #308; the earlier
unqualified "switch dispatch" deferral above referred to composition in loops.

Focused proof includes timeout-bounded host executables, real PSX compilation
with `jal` and `jalr`, archived target replay, ordinary indexed-lane receipts,
factory provider reconstruction without live source, and archive tamper
refusal. Jobs `run_automation-164009-57561` and
`run_automation-164043-57561` passed all selected suites. No live queue search,
candidate landing or indexed-runtime publication is part of this review.
Existing published generations retain their old source identities; an explicit
successor publication is required before using changed code with those indexes.

Default-bound remeasurement `run_automation-164159-57561` completed in 466
seconds: 260 active files, 23 stale matched files skipped, zero missing queue
records, zero errors, zero complete renders. Structural admission now covers
164 files, but whole-file clean regions leave 39 declared files over the
64-instruction cap and seven without declarations; no declared, within-bound
file is left blocked solely after loop admission. There are still 63
undeclared files overall. Refusal file-votes are branch-in-loop 87,
nested-loop 29, multi-exit 27, nonlocal-exit 26, barred-op 24,
outside-entry 15, frame-adjust 3, return-in-loop 3, while-no-exit 2,
crossing-branch 1. Calls no longer hide these later structural checks.
This is a new structural tally, not 164 compilable candidates.

Consolidated job `run_automation-165036-57561` passed 110/110 suites (74 test
suites and 36 module self-tests). The renderer now has 88 tests and the real
compiler driver has 17. Required build `make_build-164704-57561` succeeded;
the following `verify_build` returned every expected checksum, 113/113 OK.

Raised-limits remeasurement `run_automation-165425-57561` completed with zero errors over the same 260 active files: zero complete renders, structural admission 164, blocked_decl 7, blocked_shape 32, blocked_size 7. The raised ceiling moves 32 files from size-blocked to shape-blocked; the remaining shape refusals lead with branch-in-loop 87, nested-loop 29, multi-exit 27 and nonlocal-exit 26. Size cap is not the next practical blocker.

## Multi-exit joins (#311)

Shared-continuation multi-exit loops are admitted: the region records every
forward exit, admission requires all exits to share one continuation, and the
nonlocal-exit check requires that continuation immediately after the loop.
Lowering emits one predicate snapshot, delay slot and break per exit and keeps
only bindings valid on every exit path plus the latch exit. Split
continuations still refuse multi-exit and join-plus-multi composition stays
refused as branch-in-loop until each shape is proven separately.

Fixture proof: region tests for admission, split-continuation, nonlocal and
join-composition refusals; host-executed do-break and while-form loops with
either break firing; a draft-shape test asserting two breaks render.

Default-bound pool remeasurement `run_automation-174248-70861` completed
with zero errors over the same 260 active files and zero complete renders:
multi-exit file-votes fall from 27 to 17, branch-in-loop rises from 87 to 92
(deferred join-plus-multi composition), nonlocal-exit rises from 26 to 28
(shared but nonlocal exits now surfacing). Structural admission holds at 164
files with 39 declared files over the size cap and 7 without declarations.

## In-loop returns (#312)

An in-loop `jr $ra` is a return-exit: admission records validated return
sites (plain `jr $ra` with a non-control delay slot inside the body) and
lowering reuses the ordinary return preconditions, return address intact and
callee-saved state restored, at each site. The return emits directly; later
straight-line code in that segment is dynamically unreachable and marked
visited. Split continuations, nonlocal exits and the per-exit merge rules are
unchanged. Indirect jumps and control delay slots still refuse return-in-loop.

Fixture proof: region tests for admission, indirect-jump and control-slot
refusals; a host-executed conditional early-return loop verified against both
the early and the latch exit.

## Nested loops (#313)

Inner backward latches with fully contained spans lower recursively:
the admission pre-scan records inner spans whose branches never escape,
skips them in the outer control scan, exempts nested starts from the
outside-entry check, and refuses outer joins that land inside a span.
Lowering delegates to the loop lowerer at nested starts with save and
restore of carrier maps, the active region and the loop flag; ancestor
carrier storage is shared so every level sees one binding. Inner spans with
escaping branches stay refused as nested-loop.

Fixture proof: the canonical nested fixture now admits two regions; a
boundary test keeps inner-break composition refused; a host-executed nested
counter is arithmetically exact.

Default-bound pool remeasurement `run_automation-181430-70861` completed
with zero errors over the same 260 active files and zero complete renders:
nested-loop file-votes fall from 29 to 17, structural admission rises from
164 to 165 files, and newly admitted regions expose later blocks
(branch-in-loop 92 to 94, nonlocal-exit 28 to 32, size-blocked declared 39
to 45). Refusals move downstream as designed.

## Jump-over-else joins (#315)

The branch-in-loop subdivision reports an unconditional forward jump for
every one of the 94 files, with no bare-if shape failure: the shape is a
then-arm ending in a jump over an else arm. Admission records the head,
jump and end spans, skips both in the outside-entry scan, and defers
straight-line dead tails, nested intersections and escaping else branches.
Lowering emits if/else with join temps assigned at each arm end. The
admitted jump is skipped in the main control scan like the head.

Fixture proof: span tests plus a host-executed else accumulation loop
checked against both arm choices and the latch exit.

Default-bound pool remeasurement `run_automation-184535-70861` completed
with zero errors over the same 260 active files and zero complete renders:
branch-in-loop file-votes fall from 94 to 48, structural admission rises
from 165 to 179 files, and newly admitted regions expose later blocks
(size-blocked declared 45 to 64, barred-op 25 to 29, frame-adjust 4 to 7).
Refusals move downstream as designed.

## Paired multiply/divide (#316)

HI/LO triples fold inline per iteration, so paired producer/consumer spans
with no forks, exits, returns, nesting levels or calls admit; the model
triple never enters a required binding, so the backedge check needs no
change. Unpaired triples and fork-crossing state stay refused as barred-op.

Fixture proof: region tests for paired, lone-consumer and forked triples;
a host-executed multiply-accumulate loop verified arithmetically exact.

Default-bound pool remeasurement `run_automation-190032-70861` completed
with zero errors over the same 260 active files and zero complete renders:
barred-op file-votes fall from 29 to 24 with structural admission holding at
179 files.

## Loop-track closure: what stays refused and why

The remaining refusal classes have no bounded structural fix and are
deferred with cause, not parked silently. Split-continuation multi-exit
needs one break per continuation, which is goto or latch duplication.
Nonlocal exit needs the break path to skip tail code the latch path
executes, which is goto or tail restructuring. Unpaired or fork-crossing
HI/LO triples would carry model state across the backedge. Escaping nested
spans, join-plus-multi composition and exits inside arms are deferred
compositions. In-loop switch dispatch is absent from the pool: every
in-loop jump-register sits in three files, and unbound indirect calls stay
refused by design for lack of callee facts. Undeclared files belong to the
declaration-evidence track. Size ceilings are decided by measurement, not
assumption: raised-limits remeasurement `run_automation-191309-18743`
leaves 53 files shape-blocked against 11 size-blocked at the 512-instruction
ceiling, with zero renders and zero errors, so shapes stay ahead of
ceilings. The run names 20 shape-blocked records as concrete next targets.

## Sibling and header scopes (#318)

Capture archives same-overlay .c scopes whenever a referenced member
misses from the owning unit, plus raw header scopes for missing functions
and members; render-time projection falls back with single-signature
consensus and refuses static header definitions. Archive replay and source
binding cover the header shape with no protocol bump. Fixture proof spans
fallback, consensus, poisoning, capture archiving and tamper refusal.

Default-bound pool remeasurement shows zero movement with zero errors:
the missing symbols that matter are engine callees called but never
declared in-overlay, same-overlay queue dependencies that are themselves
todo, and data whose users exceed the default size cap. Scope expansion
cannot invent what is nowhere. Raised-limits remeasurement
`run_automation-213411-77098` with sibling scopes active still renders
nothing with zero errors: the decl-blocked 13 do not flip, so the missing
members are engine externs, todo-dependencies and uncapped cases, not
overlooked same-overlay declarations.

## Exit-shape classification (C0): ladders not plausible

Per-reason specimen lists (nonlocal_exit_ids, multi_exit_ids, capped at
20 like shape_ids) plus manual review of four shape-blocked files show
the multi-exit votes come from switch-case forests and cutscene state
machines whose exits target shared function epilogues. Shared epilogues
cannot nest, so else-if ladders have no specimens; remaining
branch-in-loop votes are epilogue jumps and continue-to-latch shapes, and
the clean loops inside those files are blocked by undeclared callees and
data relocations. C1 is a no-go and the exit refusals stand.
