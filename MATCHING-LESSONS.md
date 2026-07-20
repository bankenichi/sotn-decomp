# Matching lessons (evidence-backed)

Heuristics that have actually produced verified byte-exact matches in this repo, with
the evidence that established each one. Every claim here was confirmed by
`verify_build us` returning 77/77, not by reasoning alone.

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
- any `D_us_` references -> it will compile and fail. Skip it.

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
make_build VERSION=us   then   verify_build us   ->  expect 77/77 OK
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
codegen, a full `verify_build` after each file should still return 77/77. If it
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
   `diff.txt` and `source.c`. **Score 0 means a match.** Anything above 0 is a
   near miss; lower is closer.
5. Always revert the seed C to the stub afterwards unless you got a real match,
   then `make_build` + `verify_build` to confirm 77/77.

**Operational hazard:** the `permuter` MCP call reliably exceeds the transport
timeout and returns error -32001, but the process KEEPS RUNNING server-side and
still writes output directories. Do not interpret the timeout as failure, and do
not relaunch on top of a still-running search. Poll the `nonmatchings/<NAME>/`
directory for `output-*` instead.

**Do NOT point the permuter at a static-data failure.** It searches for equivalent
code generation. It cannot change where rodata or BSS lands, so any function
failing per section 1a (duplicate data at the wrong address) is out of scope. Of
13 `near` records, only about 5 were genuine permuter candidates; the other 8 were
1a failures.

### 8c. The permuter has not yet solved anything here. Reason about types first.

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

First run result: `BO6_ReboundStoneBounce2`, best score 340 across several
outputs, no match. A negative result on a genuinely hard scheduling difference.

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
