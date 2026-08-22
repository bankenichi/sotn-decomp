# Matching lessons (evidence-backed)

## 0. READ ANY UNFAMILIAR SCRIPT BEFORE RUNNING IT

This rule sits first because violating it cost more than every matching mistake in
this document combined.

`make function-finder` sounds like a read-only reporting command. It is not. It
depends on `prepare-reports`, which runs `fix_matchings.py`, which **renames files
on disk**. Running it once relocated 803 data symbols and broke the build (see 8d).

Before invoking ANY repo script, tool or make target for the first time:

1. Read it. Specifically grep for `rename`, `unlink`, `rmtree`, `remove`,
   `shutil.move`, `os.replace`, `> file`, `git checkout`, `git reset`.
2. Read what it DEPENDS on. `make X` may run three other things first. The
   dangerous one is rarely the target you typed.
3. Ask what its blast radius is if it is wrong, and whether that damage is
   recoverable from git.

**The last point is the real exposure here.** `asm/` is gitignored
(`.gitignore:8,13`), and so is `automation/` (via `.git/info/exclude`). Git cannot
restore either. A tool that corrupts `asm/` forces a full re-extract from the disc
image; a tool that corrupts `automation/` destroys the harness outright. Do not
assume a bad run is undoable just because the repo is under version control.

Preconditions for running something unvetted:
- commit or stash everything first, so `git status` is clean and the diff
  afterwards is unambiguous
- know which directories it can write to
- prefer a read-only mode or a dry-run flag if one exists
- if it touches generated directories, confirm the regeneration path actually
  works BEFORE you need it. `make extract` does NOT restore files that were moved
  out of `nonmatchings/`, which we discovered only while trying to recover.


Heuristics that have actually produced verified byte-exact matches in this repo, with
the evidence that established each one. Every claim here was confirmed by
`verify_build us` returning every hash OK, not by reasoning alone. That was 77/77
when these were written and is 81/81 since the upstream merge added RCHI and RDAI.

Read this before writing C for any INCLUDE_ASM stub. Tier 0 through 3 agents should be
primed with sections 1 to 3, because those three checks accounted for every match
obtained on 2026-07-19.

---

## 1. Check for an existing shared body BEFORE writing any code

`src/st/st_common.h` contains real C implementations of common entity helpers.
Roughly 31 overlay `st_common.c` files consume them with a two-line file:

```c
#include "no0.h"
#include "../st_common.h"
```

Some overlays do NOT do this and instead carry INCLUDE_ASM stubs for functions whose
bodies already exist in that header. For those, the fix is to copy the existing body
verbatim. No new code is written and no reasoning about assembly is required.

**Evidence.** `src/st/rno0/st_common.c` includes only `rno0.h`, never `../st_common.h`.
Five of its stubs had bodies sitting in the shared header. Copying them verbatim matched
all five in a single build, first try:

| Function | Shared body | Result |
|---|---|---|
| `GetDistanceToPlayerX` | `st_common.h:111` | matched |
| `GetDistanceToPlayerY` | `st_common.h:122` | matched |
| `GetSideToPlayer` | `st_common.h:138` | matched |
| `GetSineScaled` | `st_common.h:360` | matched |
| `GetAngleBetweenEntities` | `st_common.h:420` | matched |

### 1a. The technique only works for functions with NO static support data

This is the single best predictor, established 2026-07-20 across 4 files and 12
failures. Relocating a shared-header body works when the function needs only code.
It fails when the function references **static support data** (lookup tables, anim
frames, hitbox arrays, init structs), because RNO0 has that data only as unnamed
raw-address globals like `D_us_801D4B4C`. Relocating the body then forces you to
define new named data, which creates duplicate rodata/BSS that does not land at the
original addresses. It compiles cleanly and produces wrong bytes every time.

**Cheap pre-check, do this BEFORE attempting anything.** Look at the function's
`.s` stub under `asm/us/.../nonmatchings/`:

- zero `D_us_` references -> likely a free match, attempt it
- ~~any `D_us_` references -> it will compile and fail. Skip it.~~

**SUPERSEDED 2026-08-02. Do not skip on this signal alone.** The whole shim
campaign of that day contradicts it: `e_red_door`, `st_update`, `collision`,
`e_particles`, `e_medusa_head` and `e_lock_camera` all reference `D_us_`
support data and all MATCHED. Eleven functions.

What changed is that a `D_us_` reference is now a solvable placement problem
rather than a wall:

- give the stem its own `.data, <stem>` (and `.bss, <stem>` where the header
  declares uninitialised storage) splat segment, so the compiled C owns those
  bytes instead of duplicating them;
- NAME the symbol in `config/symbols.us.<overlay>.txt` or in the owning `.c`,
  so siblings referencing the same storage still link. `g_ItemIconSlots` (was
  `D_us_801D4B4C`) and `g_EInitDamageNum` (was `D_us_80180ABC`) are worked
  examples.

The revised rule: a `D_us_` reference means **do the placement work first**, not
**give up**. What genuinely blocks a shim is the stage's code or data being a
different SIZE from what the header emits; see `docs/shared-header-
parameterisation.md`.

Evidence:

| Function | file | `D_us_` refs | Result |
|---|---|---|---|
| AnimateEntity | st_common.c | none | matched |
| BottomCornerText | popup.c | none | matched |
| the 19 st_common.c harvest | st_common.c | none | 19/19 matched |
| Update | st_update.c | `g_ItemIconSlots` | compiled, wrong bytes |
| HitDetection | collision.c | 9 lookup tables | compiled, wrong bytes |
| EntityThornweed | e_thornweed_corpseweed.c | sensors, anim, hitbox | compiled, wrong bytes |
| EntityClockHands + 2 | e_clock_room.c | positions, anim, shadow | compiled, wrong bytes |

**Probe one function per file before batching.** Viability is per-file, because
whether the overlay carries named symbols varies by file. If the probe fails,
abandon the whole file rather than grinding; every "then" function in that file
will fail for the same reason.

**Important caveat.** Do not blanket-add `#include "../st_common.h"` to such a file.
`rno0/st_common.c` already defines its own `MoveEntity`, `FallEntity`, `GetSine`,
`Ratan2Shifted`, `Ratan2`, `SetStep`, `SetSubStep` and `EntityDummy`, so a blanket
include causes redefinition errors. Replace stubs individually.

**Second caveat: divergent variants exist.** RNO0's own `GetSine` and `Ratan2` have
different signatures and bodies from the shared header versions:

```c
// rno0/st_common.c:44           st_common.h:365
s16 GetSine(s32 arg0) {          s16 GetSine(u8 arg0) {
    return g_SineTable[arg0 & 0xFF];  return g_SineTable[arg0]; }
```

So a shared body is a strong candidate, not a guarantee. Always confirm with a build.

---

## 2. Infer parameter width from the absence of masking

If the target assembly stores an argument with **no preceding `andi $aN, 0xff` or
`andi $aN, 0xffff`**, the parameter is full width (`s32`), not `u8` or `u16`.

Declaring a narrow parameter makes the compiler emit a truncation instruction the
original does not contain, so the function compiles cleanly and produces wrong bytes.

**Evidence.** `BO6_RicSetStep` in `src/boss/bo6/us_39144.c`. Target asm is three
instructions with no mask:

```
lui $at, %hi(RIC_step)
sh  $a0, %lo(RIC_step)($at)
lui $at, %hi(D_80076306)
sh  $zero, %lo(D_80076306)($at)
jr  $ra
```

With `void BO6_RicSetStep(u8 step)` the build produced `BO6.BIN: FAILED`.
The only change to `s32` matched it:

```c
extern u16 RIC_step;
extern u16 D_80076306;

void BO6_RicSetStep(s32 step) {   // s32, NOT u8
    RIC_step = step;
    D_80076306 = 0;
}
```

Update the forward declaration too (`us_39144.c:111`), or the signatures conflict.

---

## 3. Mirror neighbouring matched functions

Style in this repo is load-bearing for byte-exactness, not cosmetic. Before writing,
read the already-matched functions in the same file and copy their conventions: how they
type their locals, whether they declare globals `extern` inline above the body or reach
through a struct pointer, and how they structure early returns.

**Evidence.** The `s32` parameter for `BO6_RicSetStep` was corroborated by its matched
neighbour `func_us_801B9ACC` in the same file, which also takes `s32 arg0` and declares
its target global `extern` immediately above a short body.

---

## 4. Declaration placement can break a build; function order changes layout

Declarations emit no code, so they may be moved freely. Function definitions may NOT be
reordered, because their order determines the binary layout.

**Evidence.** `GetSineScaled` sat at `rno0/st_common.c:40` but
`extern s16 g_SineTable[];` was declared at line 42. Replacing the stub in place would
have referenced the symbol before its declaration. The fix was to move the **extern**
above the function and leave the function where it was. Moving the function instead
would have changed the layout of RNO0.BIN.

---

## 5. Unnamed union offsets are a defer signal, not a guess target

Entity code frequently indexes `g_CurrentEntity` as an array with stride `0xBC`
(`sizeof(Entity)`, `include/game.h:944`) and writes into the `Ext ext` union
(`include/entity.h:4484`, spanning 0x7C to 0xB8).

When the assembly touches an offset with no clearly named member in that roughly
80-member union, an agent guessing a member name produces code that fails to **compile**,
which is a different and less useful failure than wrong bytes.

**Evidence.** `func_us_801CFE6C` stores `sb $zero` at Ext-relative offset 0x2E, which no
documented member covers. It was the single `BUILD FAILED` among 15 escalations while the
other 14 compiled. Correctly deferred rather than guessed.

Either identify the true member from `include/entity.h`, or use an explicit byte cast:

```c
*((u8*)&g_CurrentEntity[i].ext + 0x2E) = 0;
```

---

## 6. Failure taxonomy: "compiles but wrong bytes" is not "failed"

The queue's `escalated` status flattens four materially different outcomes. Distinguish
them by the `notes` field, because each routes somewhere different:

| Notes contain | Meaning | Route to |
|---|---|---|
| `built, but ... does not match` | compiled, wrong bytes | next model tier, then permuter |
| `BUILD FAILED` | did not compile | usually a scope or union-naming problem |
| `worker error:` | harness defect, never got a fair attempt | fix the harness, then requeue |
| `INCLUDE_ASM stub not found` | stale seed entry | verify against tree before requeueing |

On 2026-07-19, 14 of 15 escalations were the first kind. Treating them as outright
failures understated how close they were.

---

## 7. Verify the baseline before testing anything

A dirty tree invalidates every conclusion. Matched functions legitimately remain applied,
so `git status` showing modified files is normal and does **not** by itself mean the tree
is broken. Confirm with the oracle instead:

```
make_build VERSION=us   then   verify_build us   ->  expect 81/81 OK
```

A worker killed mid-run cannot execute its own `restore()`, so orphaned edits are
possible in principle. On 2026-07-19 the baseline was verified clean at 77/77 after a
hard fleet kill, so `restore()` held, but the check is cheap and must not be skipped.

---

## 7b. verify_build hashes DISK, so always build immediately before verifying

`verify_build` recomputes hashes of the artifacts currently on disk. It does not
build. If a source edit has not been compiled and linked, or a worker was killed
mid-flight, it reports on a stale tree and can show a FAILED artifact that is not
actually broken.

Observed 2026-07-20: an agent finished a batch at a genuine 77/77, the fleet
worker was then killed mid-build, and the next bare `verify_build` reported
`RNO0.BIN: FAILED`. A plain `make_build` recompiled two stragglers
(`create_entity.c`, `no2/stage_data.c`) and it returned to 77/77 with no source
change at all.

Always `make_build` then `verify_build`, as one pair. Never trust a bare
`verify_build` after any interruption, and never revert a function on the strength
of one without rebuilding first.

## 8. Annotation is part of the deliverable, and it is free

A byte-exact decompilation nobody can read has little value. `CONTRIBUTING.md:11`
says the same thing from the project's side: placeholder names prefixed `func_`,
`D_` or `Unk` are meant to be identified and renamed, and readability is deferred
work, not optional work.

**Comments and local variable names cannot change the generated machine code.**
They are free. There is never a matching-related reason to omit them.

Required of every generated function:
- a short comment above it saying what it does in terms of game behaviour (which
  entity, which state, what effect), not a restatement of the C
- locals named for meaning (`angle`, `distance`, `prim`, `timer`), never m2c
  artefacts like `arg0`, `var_a0`, `temp_v1`, `phi_a1`
- a comment on any line whose reason is not obvious: a magic constant, a shift
  used as a divide, a fixed-point scale, a deliberate signed/unsigned choice, or
  a field reached by raw offset
- honest uncertainty. "unclear, possibly a cooldown" is useful; a confident wrong
  explanation is worse than none

Prefer named struct fields over raw offsets where the field exists. Compare two
real proposals for `UnkPolyFunc0`, both byte-exact:

```c
*(u8*)((char*)prim + 0x2B) = 0;       // opaque
prim->p3 = 0;                          // same bytes, actually readable
```

### Two harness bugs that were suppressing this (fixed 2026-07-20)

1. The system prompt said "output ONLY C code, no markdown fences, **no
   commentary**". That was meant to stop the model wrapping output in prose, but
   it reads as "do not write comments", and the model complied. Now states that
   "no prose" refers to text outside the C and explicitly requires comments.

2. `clean_code()` deleted every function-level doc comment anyway. `_C_START` put
   `#`, `//` and `/*` inside an alternation ending in `\b`, and there is no word
   boundary between `/` and a following space, so comment lines never matched and
   were treated as leading prose. This also silently dropped any `#include` the
   model emitted. Fixed by moving the non-word tokens to their own branch with no
   `\b`.

Both bugs were invisible in the output: the code matched, so nothing failed. The
only symptom was that 33 matched functions carry zero explanatory comments.

### Outstanding debt

Everything matched before 2026-07-20 is unannotated, and 64 machine-generated
identifiers remain across `src/st/rno0/` and `src/boss/bo6/`. Backfilling is ideal
haiku work: it is mechanical, and since comments and local names cannot affect
codegen, a full `verify_build` after each file should still return 81/81. If it
ever does not, something other than a comment was changed.

## 8b. Running the decomp-permuter (first working procedure, 2026-07-20)

The permuter was installed but had never been run. It needed two fixes before it
worked at all. Both are committed; you should not have to repeat them.

**Setup fixes that were required:**

1. `import.py` searched only `permuter_settings.toml`, `tools/permuter_settings.toml`
   and `config/permuter_settings.toml`, but this project's real settings live at
   `tools/sotn_permuter/permuter_settings.us.toml`, which it never checks. Without
   a settings file it falls back to Makefile dry-run discovery and fails with
   "Failed to find compile command", because this build is ninja-driven.
   Fix: `config/permuter_settings.toml` now exists as a copy, so auto-discovery
   finds `compiler_command` / `assembler_command` directly.
2. `tools/decomp-permuter/src/objdump.py` looked for `mips-linux-gnu-objdump`;
   this toolchain only has `mipsel-linux-gnu-objdump`. It also used
   `-m mips:4300` where the PSX target is r3000.
   Fix: added the mipsel executable to MIPS_SETTINGS and changed the arch to
   `-m mips:3000`. This mirrors what `permuter_loader.py` already patches in
   process, which the connector's CLI path bypasses.

**Procedure:**

1. The permuter needs a COMPILING, NON-MATCHING function as its seed. Our `near`
   records were reverted to `INCLUDE_ASM` stubs, so you must first re-apply
   compiling C to the stub and build to confirm it compiles.
2. `permuter_import c_file=<the .c file> asm_file=<asm/us/.../NAME.s>`
   Creates a work dir at `nonmatchings/<NAME>/` in the repo root, containing
   `base.c`, `target.o`, `target.s`, `compile.sh`, `settings.toml`.
3. `permuter work_dir=nonmatchings/<NAME>`
4. Results appear as `output-<score>-<n>/` directories, each with `score.txt`,
   `diff.txt` and `source.c`. Score 0 means the isolated function object agrees.
   It is worth a build, not yet a match. Anything above 0 is a near miss; lower
   is closer after relocation aliases have been normalized.
5. Always revert the seed C to the stub afterwards unless you got a real match,
   then `make_build` + `verify_build` to confirm 81/81.

**Operational rule:** run searches with `job_start(action="permuter", ...)` and
poll `job_status`. Debug mode is bounded and may run synchronously. Do not
relaunch on top of a live search.

**Do NOT point the permuter at a static-data failure.** It searches for equivalent
code generation. It cannot change where rodata or BSS lands, so any function
failing per section 1a (duplicate data at the wrong address) is out of scope. Of
13 `near` records, only about 5 were genuine permuter candidates; the other 8 were
1a failures.

### 8c. Historical first campaign: reason about types before searching

Honest scoreboard after the first campaign: **5 permuter runs, 0 matches.** Best
scores were 340 on `BO6_ReboundStoneBounce2` and 220 on two others. Meanwhile 4 of
the 5 targets were resolved by other means in the same session.

What actually solved them:

- `func_us_801AD2F0`: the asm had an `sll`/`sra 16` pair. That sign-extension is
  only emitted for a parameter NARROWER than a register, so the params had to be
  `s16`, not `s32`. Changing the types matched it outright. The permuter had been
  stuck at 220 with the wrong types, and no amount of searching would have fixed
  a type error.
- `func_us_801B77D8`: the target branches `bgtz` to the store-1 block with store-0
  as fallthrough. That layout only reproduces if the condition is written
  INVERTED, `if (diff <= 0) {0} else {1}`. A natural if/else and a ternary both
  failed. Branch *form*, not just branch semantics, is load-bearing.
- `func_801D0B40` and `func_801CE228`: already implemented and already matching.
  The queue held stale `near` records for them.

The lesson: a permuter score that plateaus (220, 340) usually means the seed is
wrong in a way the search cannot reach, typically a parameter type, a signedness,
or a branch form. Treat a plateau as a signal to go back and re-read the asm, not
as a reason to search longer. Use the permuter only after types, widths and branch
shape are confirmed correct and the remaining difference really is scheduling.

Also: verify a `near` record still reproduces before spending effort on it. Two of
these four needed no work at all.

### 8c-1. Relocation spelling is not codegen, and scheduling needs its own class

The BO6 CrashBibleBeam seed exposed two different phenomena that the old score
collapsed. The target used `g_api_PlaySfx` while C emitted `g_api+0x68`, and an
interior data label while C emitted `array+2`. They resolve to the same addresses
and produce the same linked bytes. Scoring their object-file spelling added six
false register differences and hid the real result.

New imports record the overlay link map. The vendored scorer resolves symbols
and addends to address identities, with MIPS `%hi/%lo` semantics, before it
compares operands. The same seed then reported zero register differences and one
reordering, score 60. Do not make source uglier to imitate a relocation alias.

The remaining reordering was legal output from the exact PSYQ 4.0 compiler and
the project's real flags. It came from source alias and API call surface, not a
wrong compiler executable. Treat this as a bounded search problem: compare
`g_api.Member`, `g_api_Member`, cached function pointers and temporary placement,
then use the permuter. `asm_delta.py` now calls this `schedule-only` when the
instruction-shape multiset is identical.

### 8c-2. Reconcile disjoint best outputs before declaring a plateau

`func_us_801B001C` stalled at score 90 for 39,751 iterations, but the stopped
workdir held four score-70 outputs. Each changed a different collision path from
an explicit `velocityY` temporary to a direct field update, and each removed 20
points independently. Applying all four preserved diffs to the same seed reached
score 10. A separate score-80 output assigned the byte parameter through a
temporary inside the compound addition; adding that disjoint finding reached
score 0 and the controlled full build verified 81/81.

The best numeric directory is not always the best complete answer. Before
calling a search stalled, read every lowest-score `diff.txt`, identify changes
whose hunks do not overlap, combine only independently proven improvements, and
rescore their union. Preserve the original outputs as the evidence for every
combined mutation.

One more boundary matters: sequence alignment over a structural near miss may
pair unrelated `jal` instructions. It once proposed `rand -> InitializeEntity`.
Near alignment may provide diagnostics and codegen hints, but only a clean,
position-aligned twin may perform automatic operand substitutions.

First run result: `BO6_ReboundStoneBounce2`, best score 340 across several
outputs, no match. A negative result on a genuinely hard scheduling difference.

## 8d. DO NOT run `make function-finder` unpatched. It breaks the build.

Diagnosed 2026-07-21 after it moved **803 data symbols** and took the build down.

**What happens.** `make function-finder` depends on `prepare-reports`
(`Makefile:296-298`), which runs `tools/function_finder/fix_matchings.py`. That
script, NOT the finder itself, relocates `.s` files from `nonmatchings/` to
`matchings/` (`fix_matchings.py:89-92`):

```python
for path in actually_matches:
    new_path = Path(path.as_posix().replace("nonmatchings", "matchings"))
    new_path.parent.mkdir(parents=True, exist_ok=True)
    path.rename(new_path)
```

**The bug.** The disk sweep takes EVERY `.s` under `nonmatchings/`, data included
(`fix_matchings.py:9-16`). But the "still not matching" set it compares against is
filtered to code only (`fix_matchings.py:28`):

```python
map_file = map_file.filterBySectionType(".text")
```

Rodata symbols like `D_us_801A7028` live in `.rodata`, so they can never appear in
that set. Line 82-84 then computes `actually_matches` as "on disk but not in the
non-matching map", which classifies **every data symbol as matching** and moves it.
The disk scan covers data; the correctness check does not.

**Why that breaks the build.** `INCLUDE_RODATA(FOLDER, NAME)` expands to a literal
hardcoded path (`include/include_asm.h:46-49`). There is no search across
`nonmatchings/` and `matchings/`. `fix_matchings.py` renames the file and never
touches the `.c`, so the source still points at the old path and the assembler
fails with "can't open ... nonmatchings/.../D_us_801A7028.s".

**`make extract` will NOT repair it.** `asm/` is gitignored (`.gitignore:8,13`),
and splat only ever populates `nonmatchings/`. Once a file has been relocated into
`matchings/` it is orphaned from both the source path and the extractor output.
Recovery is a manual move back, which is what we did for all 803.

**Its legitimate purpose** is narrow, per its own header comment
(`fix_matchings.py:3-4`): cases where splat wrongly assumes a FUNCTION does not
match, e.g. code `#ifdef`-ed out for a version. It was never meant for data.

**Rule:** never run `make function-finder` or `fix_matchings.py` on this repo
unpatched. To get the report without the mover, run
`tools/function_finder/function_finder_psx.py` directly; it only reads
(`function_finder_psx.py:44` requires `"nonmatchings" in str(path)`) and moves
nothing.

## 9. Renaming placeholder symbols (func_XXXXXX, D_XXXXXXXX, Unk*)

Comments and local names are free. Symbol renames are NOT. A placeholder name
appears in at least four places that must change together:

- the source `.c`, plus any forward declaration or header
- `config/symbols.us.strno0.txt` (name = address)
- `config/symbols.pspeu.strno0.txt`, the other version's table
- `asm/us/st/rno0/nonmatchings/<file>/<symbol>.s`, whose path encodes the symbol

So it is a scripted, atomic, multi-file operation followed by a full
`verify_build`, not a hand edit. Do it in its own pass, never mixed into a
matching or annotation change.

**Rename only from evidence, never from a guess.** In priority order:

1. **A sibling overlay already named it.** Around 26 overlays share
   implementations. If RNO0 has `func_801CF778` and NO0 or NP3 has the same
   function under a real name, take that name. Zero inference, highest
   confidence. This is how `func_801CF778` was identified: an already-matched
   sibling with the same opcode sequence exists under `asm/us/st/np3/`.
2. **Call sites.** What calls it, from which state, usually fixes the role.
3. **Observed behaviour.** Weakest; keep the placeholder unless it is clear.

**Let the annotation pass select the candidates.** Annotate first, since that is
safe and free. A function whose comment states a confident purpose is a rename
candidate. A function whose comment hedges, "unclear, possibly a cooldown", is
NOT. The hedge is the signal, and renaming on a hedge bakes a guess into a symbol
name where it looks authoritative forever.

**Follow the project's existing conventions** rather than inventing a scheme:
`EntityDiplocephalusTorso`, `BO6_RicSetStep`, `GetAngleBetweenEntities`. Note this
is a fork of an upstream project, so gratuitous renames create merge conflicts;
prefer names upstream would plausibly choose, and consider contributing them back.

Be especially conservative with `D_` globals: they can be referenced from several
overlays, so the blast radius is wider than a static function's.

## 10. Build serialization is mandatory

`worker_direct.py` serializes apply, build and verify behind `BuildLock`. The MCP
connector's `make_build` does **not** take that lock.

Therefore parallel agents must never build. Two agents editing different `.c` files and
building the same tree will interleave, and each will read the other's failure as its own.

The working pattern is: parallelize analysis, serialize the build.

## 10b. A generation failure must cost one attempt, never the function

Until 2026-07-21 the generation call in the attempt loop was unguarded. Any
exception escaped to the per-function handler, which abandoned the function and
discarded every remaining attempt.

It hid for weeks because the http backend never triggered it: streaming plus the
degeneration detector always cut in before a hard timeout. The cli backend has
neither, so the timeout IS its normal failure mode. First cli run: attempt 1/4 on
`BO6_CheckHighJumpInput` hit the 191s attempt budget, and the worker moved
straight to another function, throwing away three unused attempts.

Two lessons, and the second is the general one:

- Retries are the ONLY consumer of asm-differ feedback. Attempt 1 has no diff to
  learn from by definition, so silently losing attempts 2-4 does not cost 75% of
  the effort, it costs 100% of the *informed* effort.
- **A backend swap changes which failure modes are reachable, not just speed.**
  Guards that were never exercised on one backend become the hot path on
  another. When adding a backend, ask which existing safety nets depended on
  properties (streaming, incremental output, local latency) that the new one
  does not have.

Related: budgets must be backend-aware. `FUNC_BUDGET` now defaults to 1800s for
cli and 900s for http, because measured OpenCode attempts run 120-190s against a
191s slice. Raise the budget rather than cutting `MAX_ATTEMPTS`; trading away
retries makes every attempt a blind first attempt.

## 10c. Identical wrong output from two models means look upstream of the model

On 2026-07-21, `func_us_801B9DE4` was generated by local llama and by
OpenCode `big-pickle` seven hours apart. The two outputs were logically
identical, including the odd part: a store of 8 to `timers[1]` immediately
overwritten by 0xC.

Two unrelated models converging that precisely is not a coincidence, and it is
worth stopping to investigate rather than escalating to a bigger model.

The investigation, all read-only and costing nothing:

- Hypothesis: `timers[]` aliases distinct struct fields, so no C could
  reproduce the stores. **Falsified.** `include/game.h:1959` puts
  `s16 timers[16]` at `0x330`, so `timers[1]` is `0x332` and `timers[8]` is
  `0x340`, matching the assembly exactly. `unk44` is `0x394`, also correct.
- The redundant store is genuinely present in the original assembly
  (`asm/us/boss/bo6/nonmatchings/us_39144/func_us_801B9DE4.s`): `0x332 = 8`,
  then `0x340 = 0xC`, then `0x332 = 0xC`.

So the models understood the function correctly, mapped every offset correctly,
and still did not match. The remaining difference is codegen shape, not
comprehension.

**Consequence for routing:** a bigger model cannot fix semantically correct C.
This is permuter work. See 10d.

Corollary worth remembering: when two independent systems produce the same wrong
answer, the fault is almost always in what they were both given, not in either
of them. Check the shared input before replacing either consumer.

## 10d. Route by failure KIND: "compiled but wrong bytes" is a `near`, not an `escalated`

`scheduler.py:303` has always said it plainly: report *"'near' if it compiles but
does not match"*. The worker did not. Until 2026-07-21 it reported EVERY
exhausted function as `escalated` with `score 0`, whether the C compiled and
missed by a few instructions or never built at all.

Why that matters, and it is not cosmetic:

- The tier table routes `near` records to the **permuter, first, because it costs
  no tokens**. Codegen near-misses are precisely what the permuter solves.
- `escalated` routes to the paid model tiers.

So the harness was sending its free-to-solve records to the expensive tier, and
starving the free tool of the only inputs it can use. Every `escalated` count
reported before this date is inflated and should not be read as "needs a
stronger model".

The fix tracks whether any attempt compiled (`compiled_once`) and picks the
status from that. Note the asymmetry: ONE attempt compiling is enough to make it
`near`, because that proves the function is reachable in C.

Preserve the body before restoring the source. Write the exact applied C to
`automation/candidates/`, report the record as `near` with the seed path and
build evidence, then snapshot the queue. On 2026-08-18 the Luna shadow run
compiled `BO6_RicStepStand` at 80/81 and localized it to `-0x4`, but the root
restored the stub before saving the body. The exact patch was recoverable from
the Codex task transcript and was saved later. That recovery was luck. A green
restored tree does not excuse losing the only compiling form.

An exact body is not yet a usable permuter seed. The body may have compiled only
because its original file supplied a local header or an earlier flat extern.
Keep the captured body unchanged, add the same standalone context around it,
then require both a clean `permuter_import` and a successful debug compile.
Retracted 2026-08-18: `permuter_import` no longer reports a parse error and then
returns success. It first retries after replacing unrelated function bodies with
declarations, which lets an ordinary target coexist with GNU computed goto code
elsewhere in the file. If the selected function itself cannot parse, import exits
nonzero and creates no work directory. A debug compile remains the validation
gate because parsing alone does not prove codegen.

General form: when a pipeline records outcomes, a single "failed" bucket
collapses distinctions the downstream router needs. If two failures have
different owners, they need different statuses.

## 10e. Whole-tree verification must happen inside the build lock

`scheduler.py` refuses `matched` unless it can re-verify, and it re-verifies the
WHOLE tree: all 81 hashes, not just the overlay in question. That check is right
and worth keeping. It is what stops a worker claiming a match while the tree is
broken.

But the worker reported the match AFTER releasing `BuildLock`. In that window
another worker applied its own edit, and the scheduler saw
`76/77 OK, 1 MISMATCHED` for an overlay the reporting function never touched. A
real, verified match was rejected and filed as `escalated`.

The defect is structural and provable by reading the code: the report was
outside the lock, and the scheduler's check is global. It does not depend on any
particular record to be real.

**What is NOT established: that it has actually cost a match yet.** The retriage
first flagged `func_us_801B9D74` and `func_us_801B20F4` as confirmed casualties,
on the strength of a scheduler rejection naming an overlay those functions never
touched. That was wrong, and checking took ten minutes:

- `func_us_801B9D74`'s archived C references `g_Ric.unk394`, a field that exists
  nowhere in the tree. It also omits two stores the asm makes (`0x28` to
  `g_Ric + 0x346`, and `RIC_velocityY = 0`). It cannot have compiled.
- `best_score` 100 was not evidence either. `scheduler.py` `sys.exit`s on a
  rejected `matched` BEFORE `q = Queue()`, so that path never writes a score.

Both were then requeued as ordinary `near` records.

The meta-lesson, which is the expensive one: **a plausible mechanism plus a
suggestive error message is not a confirmed instance.** The race was genuine, so
the story felt complete, and that is exactly when the evidence stops being
checked. Confirm the instance separately from the mechanism, and label them
differently until you have.

The rule: **if a check is global, every mutation it can observe must be
serialised with it.** A lock that covers apply and build but not the verification
that consumes them is not a lock, it is a race with extra steps. Section 10 said
parallel agents must never build; this is the same hazard one level up, where the
verifier is the thing being raced.

Symptom to recognise: a rejection naming an artifact your change does not touch.
That is never a real failure of your function. Treat it as evidence of a
concurrency defect, not of a hard function.

## 10f. Give the model the declarations, or it will guess a type and miss

`build_prompt` used to send exactly two things: the assembly and the m2c draft.
Nothing told the model which symbols existed, what type they were, or that it
had to declare them. So it guessed. A guess can be semantically right and still
generate different code.

Measured, 2026-07-21. `func_us_801B9DE4` and `BO6_RicSetSlide` sat as
near-misses for hours and were used as evidence that the local model had
plateaued. Both matched on the first try after one change:

```c
extern AnimationFrame D_us_80182010[];   /* was absent entirely */
BO6_RicSetAnimation(D_us_80182010);      /* model wrote &D_us_80182010 */
```

For `extern T NAME[]`, passing `NAME` and passing `&NAME` compile to different
code. The declaration was already present in the SAME source file. The harness
never showed it.

**The fix is to harvest, never to synthesise.** `lookup_declarations()` greps
`src/` and `include/` for how the tree already declares each symbol the asm
references, and puts those lines in the prompt verbatim. If the repo does not
declare a symbol, the prompt says nothing about it. A synthesised
`extern s32 D_us_X;` for something the repo declares as
`extern AnimationFrame D_us_X[];` would manufacture the exact bug this prevents.

Refinement, 2026-08-22: "the repo does not declare it" was too narrow because
the retained assembly is also repository evidence. A raw `D_*` label in an
overlay's data, rodata or bss assembly carries an exact owner, storage directive
and byte span; the target load opcode supplies signedness and access width.
Those facts support an address-based prompt declaration without inventing a
semantic type. Global addresses inside `g_Entities` can likewise be resolved
from configured array anchors, the 0xBC Entity stride and annotated member
offsets. `data_declarations.py` centralizes both paths for the worker and
coverage ranker, and refuses absent or conflicting evidence.

The wider lesson, and the reason this went unnoticed for so long: **two failing
consumers with a shared input means the input is the suspect** (see 10c). Both
models produced identical wrong code, which read as "the models agree, so the
function must be hard". It actually read "both were handed the same incomplete
context". A capability ceiling and a context defect look the same from the
outside; the difference is whether you checked what the model was given.

Corollary for triage: before escalating anything to a more expensive tier, ask
what the cheap tier was actually shown. Escalation cannot fix missing input, it
just pays more for the same guess.

## 10g. Audit the instrumentation before believing anything it reports

Two defects found in one pass on 2026-07-21, both silent, both invalidating
conclusions that had already been drawn and acted on.

**1. `rc` from a pipeline is the LAST stage's.**

```python
rc, out = wsl("make build ... 2>&1 | tail -40")   # rc is tail's. Always 0.
```

So `rc != 0` never fired and no compile failure was ever detected as one. Every
failed compile fell through to the hash check and was reported "built, but does
not match". Consequences: the failure taxonomy inverted (functions that never
compiled were filed `near`, i.e. permuter work), and retry feedback was useless
because the model was told "bytes differ" when the real message was
`structure has no member named unk32`. It repeated that same error on all four
attempts because nothing ever told it otherwise. Fix: `set -o pipefail`.

**2. A verification lookup that silently matches nothing.**

`overlay_artifact()` derived `build/<v>/<NAME>.BIN` from the overlay name. For
the MAIN overlay the real artifact is `build/us/main.exe`. The derived string
appears nowhere in `config/check.us.sha`, so
`grep -F <artifact> check.sha | shasum -c` matched no line and MAIN always
reported a mismatch. Nine functions were **unmatchable by construction**: a
byte-perfect answer would still have been recorded as a failure.

The pattern connecting them: a check that cannot report failure, and a lookup
that cannot report success. Neither raises. Neither logs. Both produce a
plausible-looking result forever.

Practical rules:

- Any `cmd | filter` whose exit status you read needs `set -o pipefail`.
- Any lookup keyed on a DERIVED string (artifact path, symbol name, file path)
  needs an audit that the derived value actually exists in the target. See
  `worker_direct.audit_artifact_mapping()`; it is read-only and takes a second.
- Before trusting a metric, ask what its failure mode looks like. If "broken"
  and "working" produce the same output, the metric is not evidence.

And the expensive meta-lesson: **a day of conclusions about model capability
were measured through both of these.** "Compiles but wrong bytes" frequently
meant "did not compile". Plateau claims, degeneration rates and the decision to
switch backends all rest on that data and should be re-derived, not cited.

## 10h. The m2c draft's struct fields are ground truth; models must not rewrite them

Failure ladder observed while getting the OpenCode models productive, each layer
uncovered only after the one above it was fixed:

1. Syntax: modern-C mid-block declarations, rejected by C89 (see the SYSTEM
   prompt's C89 block). Fixed first, dropped `parse error` from dominant to rare.
2. THEN the dominant build error became `structure has no member named unkNN`.

The second is a self-inflicted prompt bug. `tools/m2ctx.py` builds `ctx.c` with
the real struct definitions, and m2c resolves every field access against it, so
the draft's `self->step`, `ent->ext.ILLEGAL.s16[N]`, `->unk24` are correct BY
CONSTRUCTION. But the SYSTEM prompt told the model to "name locals for meaning",
and the models over-applied that to struct fields, renaming a correct `->unkA4`
into a guessed `->unk24` or `->state` that does not exist.

The fix is prompt-only and is the same principle as 10c/10f: harvest, do not
guess. The draft is the harvest. Two rules now:

- Struct-field accesses are copied from the draft VERBATIM; never rename,
  simplify, or invent a `->field`.
- The "name locals for meaning" licence is explicitly scoped to LOCAL VARIABLES,
  which cannot change codegen. It does not extend to fields.

Note what this did NOT require: injecting the ~80-member Entity union into every
prompt. The right context was already present in the draft; the model just had
to be told to trust it. Reach for the cheap "trust the existing resolved
context" fix before the expensive "inject more context" one.

## 10i. m2c cannot type function parameters; give the model the Entity offset map

The struct-field failure in 10h had a root cause one level deeper than "the
model invents fields". Traced on 2026-07-21 by running m2c by hand:

- m2c types GLOBALS from ctx.c, so `g_CurrentEntity->ext.ILLEGAL.u16[0xA]` comes
  out correct.
- m2c CANNOT type a function PARAMETER. `arg0` stays `void*`, so every access
  through it is emitted as a synthetic `arg0->unk24`, `arg0->unk90`. Those are
  not real fields and do not compile.
- Hinting m2c the parameter is `Entity*` does NOT fix it: it still emits
  `->unk24`, because the access WIDTH often differs from the field (e.g. `lbu`
  at 0x24 reads the low byte of the u16 `zPriority`), so m2c will not use the
  field name.

So the model is handed a draft that is half-right (globals) and half-synthetic
(`->unkNN` on parameters), and it cannot translate the synthetic half without
knowing the struct. The fix is to give it the map: `ENTITY_LAYOUT` in
worker_direct.py lists offset -> field for the Entity header (0x00-0x7B) from
include/game.h, injected whenever the function touches an entity, with the rule
"translate `->unkNN` to the field at 0xNN; 0x7C+ is the `ext` union; match the
asm's access width".

Two things this reframes:

- The earlier "copy the draft's field accesses verbatim" rule (10h) was half
  wrong: verbatim-copying a synthetic `arg0->unk24` propagates the error. The
  rule now distinguishes named accesses (keep) from `->unkNN` (translate).
- Injecting a map beats injecting the whole struct. The Entity `ext` union is
  large and per-type; dumping it would bloat every prompt and still not resolve
  a specific access. The compact header map plus the generic `ext.ILLEGAL`
  accessor is enough for the common case, and honest about the hard residue
  (byte-into-halfword accesses) that no map alone fixes.

That hard residue was closed on 2026-08-21. The assembly access opcode supplies
the missing width: signed fixed-point halfwords can use the real
`.i.lo` / `.i.hi` members, while other partial accesses use a typed view rooted
at the real aggregate, such as `((u8*)&self->params)[1]`. The root matters.
`(u8*)self + 0x31` preserves bytes but discards the Entity meaning, and assigning
`self->params` changes a byte store into a halfword store. The worker now performs
this translation before generation when the width is unambiguous and leaves an
explicit unresolved access when it is not. Unambiguous means one width from one
assembly base register: a stack slot and an Entity field can share displacement
0x24, and pooling those accesses would either widen the field or borrow the
stack slot's type.

## 10j. A byte match is the FLOOR. Upstream reviews for STRUCTURE, not bytes

Upstream reviewed this fork on 2026-07-21 and rejected matching code. The
verdict worth memorising: *"Matching is just the very most basic requirement for
decomp."* Every objection was mechanical, and every one is now detected by
`automation/quality_audit.py`:

1. **Fake symbols.** `extern u16 D_80076306;` is really `g_Entities[64].step_s`
   (verified: g_Entities=0x800733D8, sizeof(Entity)=0xBC, 0x2F2E = index 64
   remainder 0x2E = step_s). Declaring a new extern for an address that already
   has a meaning hides structure and is unmergeable.
2. **`ext.ILLEGAL` where a named variant exists.** `ext.ILLEGAL.u16[0]` should be
   `ext.reboundStone.stoneAngle`. **This one was self-inflicted**: the SYSTEM
   prompt had been changed hours earlier to actively recommend the generic
   accessor. We shipped 14 new instances of the anti-pattern (19 -> 33) by
   telling the model to.
3. **Magic bitmask literals.** `drawFlags &= 0xFB` should be
   `&= ~ENTITY_ROTATE`. The struct even names its enum in a comment
   (`u8 drawFlags; // refer to enum EntityDrawFlags`).
4. **Raw casts instead of an existing struct.** A wall of `*(u16*)(entry + 4)`
   where `SubweaponDef* p` gives `p->attackElement`.
5. **Copy-paste duplicates** of functions that already exist elsewhere.

Audit result on our 133 added functions: 39 findings across 19 functions
(18 fake symbols, 14 ILLEGAL, 5 duplicates, 2 magic masks). So ~86% were clean
and the damage was concentrated, but the concentrated part was exactly the part
a reviewer opens first.

**The tooling lesson.** Every one of these is detectable without a human, so
none of them should ever have reached review. `automation/codebase_index.py`
harvests the ground truth once (symbols, Entity layout, 461 ext variants, enum
groups, field->enum comments, 2656 function bodies) into `index.us.json`, and
both the audit AND the prompt read from it. Harvest once, reference everywhere.

**The advice lesson.** The first version of the bitmask check suggested
"DRAW_COLORS / PAD_L1 / ELEMENT_UNK_4" for bit 0x4 because it looked up the bare
value across the whole codebase, where ~50 constants share it. Wrong advice is
worse than silence: it invites picking a plausible wrong constant. Scoping by
the struct's own `// refer to enum X` comment makes the answer unique
(ENTITY_ROTATE) and is authoritative rather than guessed.

**The framing lesson, and the expensive one.** Every metric this project
optimised was "does it match". That target was measurable, automatable, and
insufficient, so the harness got very good at producing byte-identical code a
maintainer will not merge. When choosing what to measure, ask what the ACCEPTING
party checks, not what is easiest to check.

## 10k. Ask "does this already exist?" BEFORE decompiling anything

An independent expert audit (blind: given no prior findings) reached a verdict
neither the maintainer's review nor our own audit had reached:

**75 of 132 added function bodies (57%) were byte-identical, modulo comments and
whitespace, to code already in this repository.**

`src/st/` deduplicates by design. One implementation lives in `src/st/<name>.h`
and each stage's `.c` is a shim:

```c
// src/st/rcen/st_common.c -- the ENTIRE file
#include "rcen.h"
#include "../st_common.h"
```

25 stages do this. We wrote **707 lines** into `src/st/rno0/st_common.c` and
**429** into `create_entity.c`, re-deriving what a one-line include provides.
The copies carry the evidence: dead `#if defined(STAGE_IS_NO2)` branches in an
RNO0-only file, an upstream "BUG: Array out of bounds" analysis comment
reproduced verbatim, and upstream's doc comments replaced with terser
paraphrases. A maintainer reads that as their own work laundered back at them.

Worse, the near-copies were REGRESSIONS: `TERMINAL_VELOCITY`/`GRAVITY` replaced
by `0x5FFFF`/`0x4000`, `DRAW_HIDE`/`PRIM_GT4` replaced by `8`/`4`, `static`
dropped (creating new globals), m2c masks reintroduced.

**Our own audit tool could not see any of it.** `find_duplicates` built its
corpus from `(REPO/"src").rglob("*.c")` — `.c` only. Every shared implementation
is a `.h`. So it reported 5 duplicates against a true 76. One glob character
hid the largest defect in the project.

Three lessons, in order of value:

1. **The first question in any decomp is "does this already exist?", not "can I
   match this?"** The harness now runs `shared_implementation()` before
   generating and refuses re-implementation outright. Checking is nearly free;
   the omission cost ~57% of the output.
2. **A checker's CORPUS is as important as its rules.** The duplicate rule was
   correct and well-tested; it was simply pointed at the wrong file set, and a
   rule that cannot see the evidence reports clean. When a check reports far
   fewer hits than expected, suspect its inputs before trusting the result.
3. **Blind review finds what primed review cannot.** The auditor was given no
   list of suspected defects. Handed one, it would likely have confirmed the
   four classes we already knew and never questioned the corpus. Independence is
   what produced the finding, so do not brief the reviewer on the answer.

## 11. Probe the environment; never assert it from documentation

On 2026-07-21 the orchestrator told the operator a cli fleet could not run under
WSL, because `ORCHESTRATOR.md` said "OpenCode | Windows native, `opencode.CMD`".
The operator had already been running OpenCode inside WSL that day. The doc line
was a snapshot of one install, restated later as a property of the system.

Two distinct errors, worth separating:

1. **Reasoning from a doc instead of the machine.** A table row records what was
   true when someone wrote it. Environments change without the doc changing.
2. **Reporting an inference at the confidence of an observation.** The claim was
   phrased as "would almost certainly fail". Nothing had been run.

Cost: a fabricated blocker, and a recommendation to take a slower path around a
problem that did not exist.

The rule: an environment claim (a binary exists, a path resolves, a service
answers, a flag is supported) is only reportable if something was **run** to
establish it. If it cannot be run right now, say so and label the claim a guess.

Practical consequence, and why `opencode_preflight` exists: build the probe
instead of arguing about the answer. It is cheap, spends no quota, and settles
the question. Prefer a tool that reports what is true over a document that
asserts it. Doc rows describing the environment should point at the probe rather
than restate its result, which is why that row now reads "never assume; run
`opencode_preflight`".

## 12. Never derive the reference data from the work it is meant to check

`automation/codebase_index.py` originally read the working tree. That is a
circular dependency, and it was not theoretical:

- `src/boss/bo6/us_39144.c` declares `extern u16 D_80076306;`. Built from the
  working tree, the index's `declared_globals` listed that symbol as
  legitimately declared, so the check whose entire job is to flag invented
  symbols **suppressed its own warning**.
- `functions` feeds the "precedent" block in the model prompt. Built from the
  working tree, a model could be handed our own unreviewed output as the
  example to imitate, which launders a one-off mistake into a house convention.

The index now reads a git ref (`UPSTREAM_REF`, tracking `upstream/master`) via a
single `git cat-file --batch`. Two deliberate exceptions, both non-circular:
`unmatched` comes from `asm/`, which is extractor output from the original
binary, and `shared_impls.our_copies` is an explicit upstream-versus-working-tree
diff, where the difference IS the finding.

After merging upstream, re-point `UPSTREAM_REF` at `upstream/master`, never at
our `HEAD`. HEAD contains upstream's work plus ours, so indexing it restores the
exact circularity the constant exists to prevent.

## 13. "Is this a duplicate?" needs three states, not two

The first duplicate scan asked whether a file existed and concluded that rno0
had added nothing. It had added 708 lines. Upstream ships
`src/st/rno0/st_common.c` too, but upstream's is a 71-line `INCLUDE_ASM` stub
and ours is a full private implementation. Classifying on **presence** hid the
`stub -> private_impl` transition, which is the actual defect.

Three states are needed: `shim` (includes `../<stem>.h`), `stub` (more
`INCLUDE_ASM` than function bodies), `private_impl` (the reverse). Judge on the
transition from upstream's state, not on presence.

This also corrected the headline number. An audit reported "76 of 132 functions
are duplicates". Measured against upstream properly: **55 private
implementations are upstream's own** (rno3/water_effects 894 lines, mad/collision
568, nz1/e_breakable 323) and are not defects at all. Ours was 9 files, all in
rno0. A checker that flags upstream's own architecture files 17 false positives.

## 14. A shim is blocked by placement far more often than by code

Four independent blockers, every one observed in a real build. Ask all four
before touching the C:

1. **Nothing shims it.** `shimmed_by == []` means there is no shared
   implementation to defer to.

   **CORRECTED 2026-08-02: `e_blade` and `e_gurkha` were named here as examples
   and they are NOT in this class.** Both headers exist and `no2` and `np3`
   shim them. The error was in `codebase_index.py`, which matched shims by
   FILENAME (`src/st/*/<stem>.c`), so any header shimmed from a differently
   named file looked unused. `entity_lock_camera.h` is the extreme case: 20
   stages shim it, all from a file called `e_lock_camera.c`, and it reported
   zero.

   The rule now matches on what a file INCLUDES. Before trusting
   `shimmed_by == []`, confirm the header genuinely has no includers, because
   this blocker is the only one of the four that says "do not try", and a false
   positive here is unfalsifiable in practice: nobody re-tests a documented
   impossibility.
2. **The stage needs functions the shared header lacks.** rno0's giantbro
   translation unit defines 22 functions against the shared header's 15, so it
   can never be a *pure* shim. It can still be a shim plus the extras, which is
   how the file should be structured.
3. **Uninitialised statics with no `.bss, <stem>` splat segment.** This is the
   one that looks like a code bug and is not. Shimming rno0/giantbro_helpers
   linked cleanly and every single instruction was correct; 50 regions differed
   and all 50 were relocations, with the overlay exactly 124 bytes too large
   (5 static s32 plus `STATIC_PAD_BSS(104)`). np3 shims the same file
   successfully because its config says `- [0x53378, .bss, giantbro_helpers]`,
   and the shared statics are named `D_801D3378` for exactly that reason. rno0
   has one undifferentiated `- [0x53EB8, bss]`, so the storage landed at
   0x801D3EB8 instead of rno0's real 0x801D4AC8 and shifted every later address.
   No amount of rewriting the C could ever have fixed it.
4. **Initialised data with no `.data, <stem>` splat segment.** rno0/e_particles
   passed blockers 1 to 3 and still failed: the shared header emits
   `g_ESoulStealOrbAngles`, rno0 keeps `.data` in an unnamed blob at 0xE20 that
   emits it too, so both land in the overlay. rno0's values differ from the
   shared ones besides (0x0597 repeated against 0x0820, 0x0840), making it a
   content difference and not only a placement one.

`shim_viable()` in `codebase_index.py` answers all four before a build. It
predicts; it does not prove. The build is still the oracle.

### 14a. When the diff is all relocations, stop reading the C

If a failing overlay's differences are dominated by address halves shifted by a
constant, and the artifact's size is off by that same constant, the fault is
section placement. Compute it directly: diff `build/us/<OVL>.BIN` against
`disks/us/ST/<OVL>/<OVL>.BIN`, group the differing bytes into runs, and map each
run through `build/us/<ovl>.map`. If every run is a `%hi`/`%lo` pair differing by
one fixed delta, no C change will help.

## 15. `extern <type> D_<addr>;` is upstream's own convention

An audit flagged 8 "fake symbols" in `src/boss/bo6/richter.c`. Upstream then
decompiled `func_us_801B5A14` independently and used **exactly the two externs we
had used**, `D_us_801CF3C8` and `D_us_801CF3CC`.

The criterion is not "does the name look invented". It is **does that address
already have a name in the symbol table**. Checked against
`config/symbols.us*.txt`, none of richter.c's seven externs name an
already-named address, so none of them are defects. Naming an address that is
already named is the real error, and it is a much narrower thing.

The genuine instance of the real defect was elsewhere and cost a broken build:
`extern u32 RCEN_PrizeDrops;` in `src/st/rcen/e_shaft.c`. Upstream canonicalised
the symbol by dropping the per-overlay prefix, and our prefixed name stopped
resolving. The extracted asm was authoritative and settled both the name and the
type at once:

```
lui   $v0, %hi(PrizeDrops)
lw    $v0, %lo(PrizeDrops)($v0)
andi  $v0, $v0, 0x4
```

It names `PrizeDrops`, and `lw` is a 32-bit load. **Read the asm before renaming
or retyping anything.** It answers both questions without a build.

## 16. A character class matches newlines, and a regex audit is still code

Two defects in `shim_viable`, both of which produced confidently wrong verdicts:

- `^\s*static\b[^;=]*;$` was meant to find uninitialised statics. `[^;=]`
  matches newlines, so it ran from a function's opening line to the first `;`
  in its **body**. `static void PrizeDropFall2(u16 arg0) {` was read as storage,
  inventing five phantom bss objects in a header that has none. Fix: `[^;=()\n]`.
- Initialised statics were counted as bss. `static u16 tbl[] = {1,2};` is
  `.data`. Conflating them called `e_collect` bss-blocked when it reaches `.bss`
  not at all.

Also honour version guards. `e_particles.h`'s only static sits inside
`#if defined(VERSION_HD)` and does not exist for the US build, so counting it
blocked a file over storage that is never emitted.

The general rule: a checker is code and earns the same scepticism as the code it
checks. When it reports something surprising, print what it actually matched
before believing it. Both of these were found that way in one command.

## 17. A byte-identical match can still name the wrong thing

`BO6_RicEntitySubwpnCross` contained `self->ext.holywater.timer = 50;` in a
Cross Boomerang state machine whose other twenty `ext` accesses all said
`crossBoomerang`. `ET_HolyWater.timer` and `ET_CrossBoomerang.timer` are both
`s16` at ext+0x00, so the two spellings compile to the same instruction. Every
byte-comparing check passed it, forever, by construction.

The tell was not in the bytes but in the surrounding text: one access disagreed
with twenty. `check_ext_variant_outlier` in `automation/review_checks.py` looks
for exactly that shape, and only fires when one variant holds at least 80% of a
function's accesses and another appears exactly once.

The general principle: **the checks that compare against the binary can only
find defects the binary knows about.** A union member name, a parameter name, a
comment, and a `static` qualifier are all invisible to the oracle. Those need a
different kind of check, or a reader.

## 18. Identify an entity by its slot, not by its neighbours

`func_us_801C8590` used `ext.ILLEGAL.u16[0]` as a frame counter. 57 named ext
variants begin with a timer at that offset, so name affinity was hopeless, and
the first guess reached for `ext.vibhutiCrash` purely because
`BO6_RicEntityCrashVibhuti` sat next to it in the file.

Adjacency in a source file means nothing. Adjacency in the DISPATCH TABLE means
everything, because the table is the game's own index. BO6's `D_us_8018158C`
reads `AguneaCircle, AguneaLightning, THIS, HitByDark, HitByHoly`, and RIC's
equivalent table reads `AguneaCircle, AguneaLightning,
CrashReboundStoneParticles, HitByDark, HitByHoly`. One positional match against
a table both versions share, and the answer is certain rather than plausible.

Procedure, when an entity function's type is unknown:

1. `grep` the overlay's `data/*.s` for the function name; it will be a `.word`
   in a pointer table.
2. Find the same table in the version this overlay was derived from (BO6 mirrors
   RIC, rno0 mirrors no0, and so on).
3. Read off the counterpart at the same index. Its `ext` variant is yours.

## 19. `static` is a linker question, and the C sources do not answer it

Five reviewers were asked to flag functions that dropped `static` relative to
their shared header. One flagged `StepTowards`, reasoning that nothing in the
overlay referenced it. Nothing in the *C* did. `src/st/rno0/unk_4F968.c` still
holds `INCLUDE_ASM` stubs that `jal StepTowards` across the translation-unit
boundary. Adding `static` broke the link immediately.

A `grep` over `src/**/*.c` is structurally blind to this: the callers are
assembly. Before narrowing any symbol's linkage, resolve it the way the linker
will, which is what `check_linkage_vs_asm` does: scan the overlay's `.s` files
for `jal <name>` and `.word <name>`, map each hit back to the `.c` that
`INCLUDE_ASM`s it, and require every owner to be the defining file.

This generalises past `static`. Any reasoning of the form "nothing uses this"
is only as good as the corpus searched, and in a decomp mid-flight that corpus
is half C and half assembly.

## 20. Decide what NOT to automate, and record the measurement

Four candidate checks were written and run this session before being deleted,
each because it was measured rather than imagined:

| candidate | hits | real | why deleted |
|---|---|---|---|
| m2c register names (`temp_s0`) | 78 | 0 | upstream uses `var_s1` in 62 of its own files |
| noise comments | 6 | 1 | `// unused` and `// Empty stub` are content |
| bitmask name affinity | n/a | n/a | picked `DRAW_COLORS` over `ENTITY_ROTATE`, and flagged a local |
| "same as X except Y" comment diffing | n/a | n/a | needs a reader to judge what "except" covers |

A check that is mostly wrong is worse than no check, because it teaches people
to skip the output, and then the true positives go with it. The cost of finding
this out is one run, so run it before shipping it.

The corollary is the rule now enforced in `quality_audit.py`: **a finding whose
exact line exists verbatim upstream is not our finding.** That single rule
retired an entire category of argument, because most false positives here turn
out to be upstream's own conventions measured against a standard upstream never
adopted.

## 21. `ast.parse` is not a test, and a diagnostic must not be able to kill its host

Adding a startup guard to the MCP connector took the connector down. The guard's
job was to prevent a broken connector.

The code was syntactically perfect, so `ast.parse` passed. It referenced `sys`
and `Path`, and the module imported neither. The insert that was supposed to add
them was conditional on finding `from pathlib import Path`, which the file did
not contain, so it silently did nothing and reported success. Every check run
was a check of the wrong property.

Two rules, both cheap:

**Import it, do not just parse it.** Syntax checking cannot see a `NameError`.
When the real dependency is unavailable (here, the `mcp` package is not in the
sandbox), stub it and import anyway:

```python
fake = types.ModuleType("mcp"); ...
sys.modules.update({"mcp": fake, "mcp.server": srv, "mcp.server.fastmcp": fast})
import sotn_cmd_mcp            # now the NameError would actually fire
```

This is the same failure as the `args.include_deferred` incident: `py_compile`
could not see an unregistered argparse flag either, and five workers died.

**Wrap any startup diagnostic in `try/except Exception`.** A check that reports
a problem is worth having; a check that CAUSES one is strictly negative. If the
cross-check cannot run, it should say so on stderr and let the server start.

### 21a. An allowlist is not an interface

The same change exposed a second trap. The connector has two surfaces:
`commands_client.REGISTRY` decides what is *permitted*, and the `@mcp.tool()`
decorators in `sotn_cmd_mcp.py` decide what is *callable*. Adding `git_push` to
the registry alone made `list_allowed` truthfully report 18 commands including
it, while it remained impossible to invoke. The connector looked correctly
updated and was not, and it cost a restart to find out.

When adding an action, update both, and confirm by CALLING it rather than by
listing it. That is what the guard now checks automatically.

## 22. An isolated function score does not prove stack or jump-table placement

`BO6_RicStepCrouch` compiled instruction-for-instruction against its isolated
target with zero reported stack differences. The full link still failed. Two
properties had been normalised away by the scorer:

- the target reserves a 0x40-byte frame, while the candidate reserved 0x18;
- the target jump table begins at `0x801A6AC4`, but a normal C `switch` aligned
  the generated table to `0x801A6AC8` and shifted every later BO6 symbol.

The linked `asm_diff` exposed both immediately. A static computed-goto table
marked `ALIGNED4` emitted the same dispatch instructions while preserving the
four-byte table boundary. A volatile ten-word local restored the frame without
emitting runtime instructions. The resulting build verified 81/81.

Treat an isolated score of zero, or a score containing only relocation aliases,
as permission to build, never as proof of a match. For a function with a jump
table or an unexpectedly large frame, inspect the linked diff on failure before
changing the body. Section alignment and concrete stack immediates are outside
the isolated scorer's guarantee.

## 23. Retained assembly is evidence; the live stub is the authority

This fork retains many individual `nonmatchings/*.s` files after their C bodies
land. `progress_table.py` treated every surviving file as an active stub and
undercounted the tree by 13 functions, including the already-landed BO6 entity
factory. The corrected count is 6372 of 6561 functions, with BO6 at 192 of 237.

For an individual function, ask whether a path-aware live `INCLUDE_ASM` still
owns that symbol. A same-named assembly file in another overlay is not evidence
about this one. Configured whole-file assembly and `.NON_MATCHING` symbols remain
authoritative negative evidence. `source_index.py` now supplies this boundary to
both progress reporting and twin discovery.

The inverse lesson unlocks mechanical twin work. A donor's extracted `.s` often
disappears or becomes stale precisely because the donor matched, but its current
`build/us/<source>.c.o` is fresh compiler evidence. `asm_delta.py` now
disassembles that object when no distinct donor listing exists. On the remaining
BO6 set this changed the transplant scan from 36 unresolved map cases to 22
structural or scheduling drafts that can be generated and inspected without a
model or a manual port.

## 24. A zero-exit compiler pipeline can still have rejected the C

The PSX compile command is a shell pipeline. Without `pipefail`, its exit status
comes from the final assembler, not from `cc1-psx`. The compiler can diagnose an
undeclared identifier, emit partial assembly, and fail while the assembler still
returns zero and leaves a plausible object. Decomp-permuter previously accepted
that object and assigned it a numeric score.

That produced four confident but false measurements during the first adaptable
draft sweep: `TryShoot` 500, `TryThrow` 1400,
`EntityJackOBonesDeathParts` 1260, and `DrawLaserRing` 1200. Those scores are
retracted. Their raw receipts remain archived because the stderr is the evidence
that exposed the defect.

The vendored compiler boundary now captures both output streams. A successful
permuter compile is silent; any diagnostic output or nonzero exit removes the
temporary object and returns compile failure. Test both sides of this boundary:
a wrapper that writes an object, prints an undeclared-symbol diagnostic, and
exits zero must fail, while a silent zero-exit wrapper must return its fresh
object.

Near-twin bodies often depend on file-local arrays and step enums that do not
travel with the function. The transplant scorer derives exact extern types and
numeric enum values from the donor's file scope. These declarations are labeled
score-only because they make isolated compilation honest but do not prove the
target symbol relationship. Function locals are removed from the dependency set
before donor globals are considered; otherwise a same-named donor global creates
noise such as an unnecessary `extern unused[]`.

Once the candidate compiles, a second safe normalization is possible. If stack,
reordering, insertion, and deletion penalties are all zero, paired MIPS adjusted
`%hi` and `%lo` rows identify the exact target address for an unresolved donor
symbol. Resolving that address through the overlay map and compiling once more
with the concrete `D_us_*` label distinguishes a relocation-name residue from a
code difference. Both receipts are retained and linked. The normalized zero is
still only permission to build; section placement, jump tables, and the full 81
artifact oracle remain outside the isolated score.

Three dependency details determine whether that score is honest. First, an
unsized donor array cannot be declared merely as `extern T name[]` when the body
uses `LEN(name)` or `sizeof(name)`. Count the donor's braced initializer and emit
the exact compile-only extent. Second, declarations guarded by `VERSION_PSP`
must not enter a US score. An `extern s32 E_ID(NAME)` from that branch expands to
an ordinary US enum member and can conflict with the enum constant. Third, an
enum declared inside the transplanted function is already self-contained. A
generated `#define INIT 0` before that body rewrites `INIT = 0` into invalid
`0 = 0`. Remove local enum members from the dependency set just like local
variables.

Queue identity is also part of compiler identity. `EntityShaft`,
`EntityBreakable`, and `EntityUnkId1B` each name more than one US target. A scan
that groups by the bare function name either guesses the wrong assembly or skips
real records as ambiguous. Carry the overlay from the queue ID through stub
lookup, import and scoring. In the 2026-08-18 sweep this turned three ambiguous
rows into six exact structural not-twin verdicts.

Finally, preserve both output streams from import. The importer prints progress
on stdout and its useful parse failure on stderr. Selecting stdout with an
`or stderr` fallback discarded the diagnostic precisely when it mattered. Join
the streams in the durable receipt, while keeping the display free to show only
a short summary.

Exact identity has to survive every public route, not only the path used during
the first measurement. Fixing scored scan while ordinary scan, batch apply or
live supervisor landing still passes a bare name leaves the same bug one command
away. Exercise repeated names through each route with their full queue ID. A
safe bare lookup returns no target when more than one stub exists.

Filesystem set differences do not establish process ownership. Between an
import and a later directory listing, another same-name import can create a
newer directory. Selecting the newest entry can score and archive the other
process's evidence while leaving the intended import live. The importer already
knows the directory it created, so print that exact path in a success receipt,
validate it beneath the work root, and pass it directly to every later step. A
same-name lock protects cooperating score calls, but the receipt is what makes
ownership true even beside an ordinary importer.

A compiled object is evidence only for the dependency state that produced it.
Comparing its timestamp with the C source and one shared header is incomplete:
any direct or transitive include can alter declarations, macros and codegen.
Use the build system's dependency database and reject the object when any
recorded input is missing or newer. The regression must change an included
header while leaving the C source older, because a source-only test proves the
weaker rule rather than the real boundary.

An aligned operand proposal must be a function, not a relation. If the same
donor symbol or numeric value maps to two target values, retaining the last row
creates a destructive rewrite that still looks position-proven. Mark the pair
structural-near, preserve the conflicting proposals as diagnostics, and emit no
automatic map. Runtime-table proof needs the same discipline: filter inactive
PSP branches before using `EntityUpdates` ordinals to authorize a US enum name.

A programmatic queue pass must report every exact record it examined. Silently
dropping ready twins and structural not-twins forces the operator to reconstruct
the missing accounting by hand. It must also return failure when any import,
debug, archive or restoration step fails; one numeric score elsewhere cannot
turn an incomplete sweep into a successful one.

## 25. Declaration recovery must parse C, not physical lines

The first low-score publication pass exposed two distinct false declarations.
`DrawLaserRing` already had a `static void` definition in its seed, but the
writer recognized only a one-token same-line declaration and added
`extern int DrawLaserRing();`. The real SDK declaration of `RotTransPers4` spans
several lines, so line-oriented grep missed it and added
`extern int RotTransPers4();`. `EntityRelicOrb` repeated the same failure with
its static `BlinkItem` definition and the multiline `LoadTPage` prototype.

These were not candidate failures. They were evidence-construction failures.
Declaration lookup now uses grep only to identify candidate files, then parses
complete declaration spans in Python. The recognizer accepts storage qualifiers,
multiword and pointer return types, balanced multiline arguments, static
definitions and multiline externs while rejecting call expressions.

A repair tool also needs an ownership boundary. Adding missing declarations to
an old generated block cannot remove a conflicting line already inside it.
Current blocks therefore carry an explicit end sentinel. The retrofit recognizes
that format and the older blank-delimited writer format, removes only the
writer-owned prelude, and regenerates it from the clean body. If the old boundary
is ambiguous it refuses to guess. The repaired seed becomes a new immutable
generation; the old bytes remain in history as the evidence for the defect.

After that repair, `DrawLaserRing` compiled at isolated score 0 and still changed
the linked RNO0 checksum. That is the useful final separation: the declaration
defect was fixed, and the preserved candidate was then proven to have a distinct
link-context mismatch. Rebuilding the same body again would add no information.
Restore 81/81, preserve the linked miss, record its terminal disposition, and
move on to a different method or a later advanced-worker sample.

## 26. A branch opcode match is not a branch target match

`func_us_801C7F24` exposed a false isolated score 0. The candidate and target
both contained `bnez v0` at file offset `0x4807c`, but the candidate jumped
nine instructions while the target jumped 27. The old vendored permuter replaced
every local destination with `<target>`, assuming semantic equivalence before
the binary oracle had established it. The full build correctly rejected the
candidate, and pre-restore relocation diagnostics localized the single differing
word as `0x14400009` versus `0x1440001b`.

Keep local branch destinations in the score. Once that normalization was
disabled, the same candidate scored 5 and the explicit `break` form scored 0.
Exposing the targets also reached a dormant parser bug: objdump emits
`R_MIPS_26` addends such as `1c8` as bare hexadecimal, which `int(value, 0)`
rejects. Parse that relocation shape as hexadecimal and retain the addend. Both
behaviors have direct regressions in `automation/test_permuter_settings.py`.
