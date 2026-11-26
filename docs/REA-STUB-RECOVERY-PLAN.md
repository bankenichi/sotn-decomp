# US stub recovery plan and REA evidence record, 2026-11-02

Companion investigation requested by the owner: check the repo, use REA to
figure out the remaining functions, and produce a plan with evidence to
decompile them. This session was read-only for tree, git and queue. Nothing was
committed, no queue record was changed, and no build was started.

Scope note: US is the only target. Saturn sources under `src/saturn/` and the
`*_psp` trees in `src/` are donor corpora and are excluded from every number
below, per AGENTS.md constraint 24.

---

## 1. What actually remains

Live status (`automation/readme_status.py`, currently green on the whole
oracle, 94.9 percent decompiled) reports **535 US INCLUDE_ASM stubs**. A raw scan of
`src/**/*.c` for `INCLUDE_ASM("segment", Symbol)` openings counts **538**. The
3 stub delta is `SERVANT/FNAME` (3 stubs in `src/servant/fname/`): the live
generator excludes it because it compiles only under the HD config
(`automation/queue_coverage.py` `collect()`, comment "SERVANT/FNAME is HD-only"). No
other delta exists; the two numbers describe the same population.

Joining the raw scan against the existing harness inventories
(`automation/upstream-wave-20260916.us.json` 225 ids, wave2 111, wave3 8,
`automation/twins.us.json` 227 candidate-bearing stubs, precedence: upstream
harvest first, then twins) gives, of 538:

| route | stubs | meaning |
|---|---:|---|
| upstream-harvest | 166 | a full decompiled implementation exists in upstream (Xeeynamo); adoption route |
| twin-name | 40 | same function exists in-tree under a different overlay; name twin |
| twin-shape/token | 42 | shape or token twin; diff-then-port route |
| orphan | 290 | no twin candidate on record and not in a harvest wave |

The shim route is deliberately not a fourth bucket: `automation/shim-viability.us.json`
holds 22 shared-header opportunities covering 48 stubs, and nearly all of those
ids also appear in the harvest waves (shared headers are upstream content), so
they are inside the 166. They are the mechanically cheapest slice of it.

The 290 orphans split again:

| subtype | stubs | meaning |
|---|---:|---|
| donor-named | 46 | symbol name carries the donor mapping, for example `func_us_801C15F8_from_no4` |
| raw | 244 | no recorded route of any kind |

Note the twins inventory covers only same-tree candidates; the `_from_<donor>`
suffixes in queue ids record donor overlays (NO4, RNZ1, RCEN, RBO2, BO0, ARE,
CAT), so donor provenance is in-tree data even when twins has no candidate
entry for the stub. The twins file itself does hold 27 `_from_` entries with
candidates (for example `boss/bo3/func_us_801C12B0_from_no4`).

Inventory freshness: `automation/twins.us.json` shows `generated_from:
b9d298824` (2026-09-17 regeneration) while HEAD is `798481a9`. The counts above
are therefore a few stubs off at most, and Wave 0 includes regenerating them
before any landing wave per `automation/twins.us.json` `regenerate` field.

### Orphans by overlay

```
boss/bo0        42   boss/rbo6 23   st/rno4 23   st/rno0 20
boss/bo3        37   st/rdai   16   st/rlib 15   st/rno2 11   st/rnz1 11
boss/bo5        10   boss/rbo2 10   st/rno1 10   boss/bo2  9   boss/rbo8 9
boss/bo6         8   boss/rbo1  8   st/rcen   7   boss/rbo7 6   boss/bo7 5
boss/rbo4        5   servant/fname 3        main/psxsdk 2
```

`st/rchi` (9) and `st/sel` (1) have zero orphans: every remaining stub there is
covered by a twin or harvest cue, which matches `automation/shim-viability.us.json`
concentrating rchi/rno0/rnz1/rno2/rbo6 entries.

### Scheduler state backing this

`automation/priority.us.json` ranks 398 unmatched records (5 marked blocked, at
ranks 393 to 397, all in RBO6/RNO1/RNO2 house-and-vortex helpers). Top of the
rank for orphans specifically begins at `us:ST/RNO4:func_us_801D5E90`
(rank 14), `us:ST/RNO2:func_us_801C39A4` (rank 15), `us:ST/RLIB:func_us_801AE8E8_from_lib`
(rank 17), `us:BOSS/RBO4:func_us_80197938` (rank 18).

The two `near` records are NOT quick wins and should not be re-attacked with
the permuter, per their own recorded evidence:

* `us:ST/RNO0:func_us_801CFD70` (near, score 15.0): permuter exhausted at
  isolation score 0 while the overlay checksum still differs. Linked audit
  #232 identified the real gap: target uses frame `0x10` versus current `8`,
  and the target's first `blez` reaches the second guard where the current
  source folds straight to return. Route: target-led frame correction plus
  removal of the redundant guard. Do not re-run the exhausted seed.
* `us:ST/RNO0:EntitySealedDoor` (near, score 50.0): compiled, byte mismatch;
  candidate `automation/candidates/history/us_ST_RNO0_EntitySealedDoor.v0001.c`
  is the seed to diff against.

## 2. REA status on this host, with observed evidence

The REA MCP server is connected and was exercised directly. Its own
introspection and a live open attempt establish what is and is not possible
here. Quote-accurate results:

* `tools.rea.binary_session {}`: provider candidates and availability.
  * `ghidra`: `unavailable`, code `not_configured`
    ("Set GHIDRA_INSTALL_DIR to an extracted Ghidra 12.1.x release directory."),
    plus `java_probe_failure` with code `ERR_REA_WINDOWS_NATIVE` (no Java runtime
    reachable on this machine; `java` resolves to nothing and no Ghidra
    directory exists under `C:\Program Files`, `C:\ghidra*` or the home dir).
  * `hopper`: `unavailable`, code `unsupported_host` (Windows integration not
    supported; macOS launcher path only).
  * `ida`: `unavailable`, code `not_configured`
    ("Set REA_IDA_MCP_CONFIG to an upstream IDA MCP JSON registration").
  * `kuna`: `not_configured` (`REA_KUNA_COMMAND` unset).
* `tools.rea.open_binary` on `disks/us/SLUS_000.67` returned a typed refusal:
  `target_unavailable`, category `unsupported_target`, reason
  `unsupported binary format`, constraint `file_format_rejected`, retryable
  `false`. This is direct evidence, not inference.
* Provider target-admission text in the Ghidra Windows bridge limitations:
  "Windows Ghidra P0 accepts native x86, x86-64, ARMNT (Thumb-2) and ARM64 PE
  applications and DLLs, and explicitly selected raw 6502 images". A MIPS PSX
  EXE or overlay is outside that admission set, so installing Ghidra on this
  Windows host would still not unlock PSX targets through REA.
* Kuna upstream documentation (`rea/docs/kuna-provider.md`, main):
  "Windows is not supported yet. Supported targets are ELF and thin Mach-O
  executables for x86-64, AArch64 and ARM; PE and universal Mach-O are
  rejected with a typed reason." MIPS R3000A is outside Kuna's target set on
  every host, so Kuna cannot decompile SOTN content in any configuration.
* Environment check on this machine: no `REA_*`, `GHIDRA`, `KUNA`, `HOPPER`
  variables set; `java` not on PATH.

Conclusion drawn from observations: **open_binary, pseudocode, xrefs, callees
and analyze_function from REA are unreachable for MIPS R3000A PSX artifacts on
this Windows host through all four deep providers.** The
repository-side binary truth (retail `.s` disassembly per stub) remains the
oracle-side evidence base, and it is complete: for every one of the 538 stubs
the exact retail MIPS listing already exists under `asm/us/<overlay>/
nonmatchings/<TU>/<Symbol>.s`.

### What REA still adds once enabled, and where

To obtain REA decompiler evidence (pseudocode, cross-references, callee/caller
graphs, string/data references) for the remaining functions, one of the
following enablement paths is required. Both need owner approval because they
install or configure third-party software, which AGENTS.md requires confirming
first.

* **Recommended: REA on a Linux host with Ghidra.** REA's Linux Ghidra profile
  does not carry the Windows P0 admission text; a Linux-side REA instance with
  `GHIDRA_INSTALL_DIR` and a JDK is the realistic route for MIPS ELF analysis
  with pseudocode plus typed reference data. Practically this means running REA
  (and OpenCode itself or a second OpenCode/MCP registration pointing at it)
  inside the existing WSL2 environment, where the SOTN build toolchain already
  lives. Effort: extract Ghidra 12.1.x into WSL, install JDK 21+, set
  `GHIDRA_INSTALL_DIR` in that environment, register/attach REA from there,
  restart the agent session. Target admission for MIPS ELF on the Linux
  profile is undocumented-unverified and must be proven on one small overlay
  before any batch work.
* **Alternative: IDA Pro through the REA IDA adapter.** If the owner owns IDA
  Pro (IDA handles MIPS R3000A natively and its PSX loader support is mature),
  install `mrexodia/ida-pro-mcp`, set `REA_IDA_MCP_CONFIG` to its registration
  JSON, and REA binds `provider_id: "ida"`. This is the single most direct REA
  route for PSX decompilation; it requires an IDA license, which is an owner
  decision.
* **Not viable: Kuna.** Unsupported on Windows, and MIPS is outside its
  target set on every host. Recorded here so nobody re-attempts it.

When an enabled provider exists, the per-overlay analysis recipe is already
prepared by the splat configs: every US boss and ST overlay loads its image
base at `0x80180000` (for example `config/splat.us.bobo3.yaml`: target
`disks/us/BOSS/BO3/BO3.BIN`, `vram: 0x80180000`), so each `*.BIN` can be
wrapped in a minimal ELF32 MIPS little-endian image with `p_vaddr
0x80180000`, or the matching Ghidra loader for PSX EXEs can be used for
`disks/us/SLUS_000.67`. I verified the retail bytes against their config SHA-1
for the five orphan-heaviest overlays:

| overlay | file | sha1 | match |
|---|---|---|---|
| BO0 | `disks/us/BOSS/BO0/BO0.BIN` | `c9e00e7555c363d11b6e451403b59d96d3e591af` | yes |
| BO3 | `disks/us/BOSS/BO3/BO3.BIN` | `fadd860dff5f0c89f9dd7e3004172f901a2bdd66` | yes |
| RBO6 | `disks/us/BOSS/RBO6/RBO6.BIN` | `16dc70420615488b1414e46d855b0cd6de759c02` | yes |
| RNO4 | `disks/us/ST/RNO4/RNO4.BIN` | `7fde040adf8bf5c9a8f22fba694249cf9278dcf7` | yes |
| RNO0 | `disks/us/ST/RNO0/RNO0.BIN` | `125003c7fe5d3510fddee22d4f5e5390fe507acf` | yes |

## 3. Evidence already available in-tree (no REA required)

The "figure out the remaining functions" data source that exists today:

* **Per-stub retail assembly.** One `.s` file per stub, place-named. Example:
  the BO0 transparent-shadow cluster is stubbed in `src/boss/bo0/2D26C.c` (7
  INCLUDE_ASM openings), and each body's exact machine code is listed at
  `asm/us/boss/bo0/nonmatchings/2D26C/` including semantically named neighbours
  such as `EntityOlroxAfterImage.s`; `config/symbols.us.bobo0.txt` carries
  `EntityOlroxAfterImage = 0x801AFF78`, so addresses around a cluster bind to
  real game concepts already.
* **Candidate drafts.** `automation/candidates/history/` holds 1,607 prior C
  drafts keyed by record ids, including the EntitySealedDoor and permuter
  seeds cited above.
* **Donor corpora in-tree.** `src/st/`, `src/saturn/` and the `_psp` trees
  provide source-level implementations of the shared engine functions
  (`e_spikes`, `e_breakable`, `prim_helpers`, `e_red_door`, medusa heads,
  Valhalla knight, red Venus Weed family), which is why the 22 shim
  opportunities exist and why 46 orphans already carry `_from_` names.
* **Cross-platform donor index.** Roadmap #302 published runtime
  `1097fb7a8a2fa36f5d8da2afa121a37f6ca6be3440278ca7c690d82cb0f11fec` with 3,634
  donor functions (US 1,750, HD 99, PSPEU 1,440, Saturn 345). Retrieval runs
  remain deferred by owner order; the index is published evidence.

## 4. The plan

Owner boundary, restated: implementation, wiring and testing first; matching
runs against the live queue and candidate landing stay deferred until the owner
resumes that phase (AGENTS.md constraint 23). The waves below are written for
that resumed phase; Wave 0 is within the current implementation scope because
it only regenerates read-side inventories.

### Wave 0, implementation scope now

1. Regenerate the twin and shim inventories against the current head so every
   later wave starts from tree truth: re-run the `asm_twin_finder.py` corpus
   step and `queue_annotate` (dry run first, then `apply=True`), then
   `shim_sweep.py`. Deliverables: refreshed `automation/twins.us.json`,
   `automation/shim-viability.us.json`, annotated queue records. No queue state
   changes beyond twin annotations.
2. Re-cluster the orphan population with the refreshed files using the
   classification used in this document (upstream id join, shim symbol join,
   case-insensitive twin join, `_from_` subtype split). The counts in section 1
   become the wave baseline.
3. If REA enablement is approved, do the Linux/WSL Ghidra bring-up first and
   prove it on the smallest cluster, BO7 (5 raw orphans), before any batch
   pseudocode work. That proof also settles the one documented unknown: target
   admission for MIPS ELF on the Linux Ghidra profile.

### Wave 1, harvest landing (166 stubs, owner-resumed)

Adopt whole files from the named upstream ref (`git_checkout_path`, file by
file, never whole dest directories from the wrong remote, and never from
`origin/master` on `automation/instrumented-search`). The 22 shared-header
shim opportunities are the first sub-batch because they retire several stubs
per header (`shim_sweep.py`). After each sub-batch: `make_build ->
verify_build`, then per record reporting with the documented proof fields.

### Wave 2, twins (82 stubs: 40 name + 42 shape/token)

Per `automation/twins.us.json` how_to_read: a twin is a starting point, not an
answer; diff the twin against the stub `.s` before porting, because sibling
overlays differ by one constant or one branch. The shape/token twin set is
measured, so each transplant is a bounded diff, not a rewrite.

### Wave 3, donor-named orphans (46 stubs)

These records already name their donor overlay in the queue id
(`_from_no4`, `_from_rcen`, `_from_rbo2`, `_from_bo0`, `_from_are`,
`_from_cat`). Route: donor overlay `.c` plus the target `.s` per
`automation/transplant-score*.us.json`; mechanical transplant through the
existing `transplant.py` surface where the score is high enough. REA evidence
useful here: callee graph of the donor function to bind shared-header symbols
and the data-references the donor body touches.

### Wave 4, raw orphans (244 stubs), ordered by the scheduler rank

Per-cluster pull order (from section 1 counts, biggest first): BO0 then BO3,
then RBO6, RNO4, RNO0, RDAI, RLIB, RNO2/RNZ1, and so on. Per record:
1. m2c draft exists for almost every one (m2c is the worker's first step;
   candidates history holds the previous outputs).
2. REA evidence when available: `analyze_function` for the stub's entry from
   the per-address map, `procedure_callers`/`xrefs` to bind entity tables and
   the SAVE-asset data segments, `list_strings`/`search_strings` scoped to the
   overlay's `.rodata` for readable behaviour validation.
3. Qualification through the implemented programmatic funnel (#277 data-search
   and #302 indexed donors as evidence pumps; no rerun of the exhausted
   permuter seeds).
4. The two RNO0 `near` records follow the recorded target-led frame-guard
   diagnosis, not a fresh permuter pass.

### Explicit non-claims

* No stub was decompiled or landed in this session. No `queue_report` was
  written. No build was run. The working tree was not modified; the only new
  file is this document, created for review.
* Nothing here claims the 166 harvest functions or the 290 orphans cannot
  land; the Sept 17 audit explicitly left that question unanswered because the
  ordered method was never completed.
* REA provider enablement is proposed, not configured. No software was
  installed and no environment variable was changed.

## 5. Proposed ROADMAP ledger entry (not self-written)

The ROADMAP ledger tail is at #342, and the file carries owner edits in the
working tree, so this session did not touch it. Proposed line for the owner to
adopt, formatted like the existing rows:

`| 343 | **open** | REA-readiness record and US stub recovery plan produced
from a read-only session (docs/REA-STUB-RECOVERY-PLAN.md): 538 raw stubs join
to 166 harvest, 40 name-twin, 42 shape/token-twin, 46 donor-named and 244 raw
orphans; live generator's 535 excludes SERVANT/FNAME (HD-only). REA deep
providers are observed unavailable for MIPS PSX on this Windows host (typed
target_unavailable; Windows Ghidra P0 admission set excludes MIPS, Kuna
excludes MIPS everywhere). Proposed enablement: REA in WSL with Ghidra 12.1
plus JDK, verification on BO7 first, or IDA via REA_IDA_MCP_CONFIG if owned.
Wave 0 twin/shim regeneration is in current scope; waves 1 to 4 remain
owner-resumed matching-lane work. |`

---

## 6. Execution record: WSL2 Ghidra headless pilot, 2026-11-02

This addendum records what was actually installed and run after the plan was
written, on the owner's instruction to test the proposed approach on a new
branch. Branch `rea/us-stub-evidence` (from `automation/instrumented-search`
at `798481a9`). Nothing was committed, nothing landed, no queue record was
written.

### 6.1 Environment installed in WSL2 (Ubuntu-24.04)

* OpenJDK 21.0.12.1 via `openjdk-21-jdk-headless` (apt).
* Ghidra 12.1.4 (`ghidra_12.1.4_PUBLIC_20260921.zip`, 569,649,598 bytes,
  sha256 `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`)
  extracted to `/opt/ghidra_12.1.4_PUBLIC`, symlinked `/opt/ghidra`.
  12.1.x was chosen over the current 12.2 in order to also satisfy REA's
  documented `GHIDRA_INSTALL_DIR` requirement (12.1.x) for a later binding.
* `analyzeHeadless` smoke test passed. Installer script left at
  `...sotn-rea/wsl_install_ghidra.sh` (temp dir, self-contained, checksums the
  release via GitHub's digest field).

### 6.2 The wrapper approach (what made MIPS work)

Each overlay `.BIN` is exposed as a minimal ELF32 little-endian MIPS image:
one PT_LOAD with `p_offset 0x1000`, `p_vaddr 0x80180000`, so overlay byte at
file offset f maps at exactly `0x80180000 + f`, the same addressing every
splat symbol address is defined against (BO7 `EntityBreakable = 0x80193258`
lands at offset `0x13258` as expected). Ghidra 12.1.4 accepts it with
`-processor MIPS:LE:32:default` and engages the MIPS analysers (constant
reference analyzer, unaligned-instruction fix, switch analysis). This settles
the one documented unknown in section 2: MIPS ELF admission works on the
Linux/Wsl Ghidra route, which REA's Windows bridge cannot take.

Pipeline (temp dir, `C:\Users\kenic\AppData\Local\Temp\opencode\sotn-rea\`):

* `prepare_overlay.py <srcdir>`: sha1-checks the BIN against its splat config,
  builds the wrapper ELF, resolves every remaining stub of the overlay to an
  address (overlay symbol file, plus the name-encoding fallback
  `func_us_<vram>` for unmatched stubs; never applied to `_from_<donor>`
  names, whose embedded address belongs to the donor overlay), and emits a
  per-overlay WSL runner.
* `ghidra_scripts/SotnLabelPreScript.java` (before analysis): labels all
  in-window symbols, disassembles each target with flow following, forces
  existing-or-new Functions at each target.
* `ghidra_scripts/SotnExportPostScript.java` (after analysis): decompiles
  every target, writes `<name>.c` plus `summary.json` (status, body size,
  callees, callers, errors).
* Overlay `.s` ground truth checked before use: BO7 `nonmatchings` holds 33
  retail listings including all 5 orphan bodies. The "for every stub the
  exact retail listing exists" claim in section 2 stands for this pilot set.

### 6.3 Results: 231/231 stub targets decompiled (six overlays)

| overlay | targets | decomposed | route split |
|---|---:|---:|---|
| BO7 | 13 | 13 | 5 orphan + 8 upstream-harvest |
| BO0 | 46 | 46 | 42 orphan + 2 twin + 2 harvest |
| BO3 | 45 | 45 | 37 orphan + 4 twin + 4 harvest |
| RBO6 | 35 | 35 | 23 orphan + 1 twin + 11 harvest |
| RNO4 | 61 | 61 | 23 orphan + 5 twin-name + 11 twin-shape + 22 harvest |
| RNO0 | 31 | 31 | 20 orphan + 1 twin + 10 harvest |

That is 150 of the 244 raw orphans (the six heaviest clusters) plus every
twin/harvest-tagged stub that lives in those overlays. Both RNO0 `near`
records (`EntitySealedDoor`, `func_us_801CFD70`) now have fresh drafts for
the target-led frame diff their queue notes prescribe; neither was
re-permuted, consistent with their recorded exhaustion.

### 6.4 Draft quality, honestly classified

The Ghidra output is a starting point, not landed code. Concrete observations
from BO7:

Usable already:

* Entity state machines come out structured: the step tests decode into a
  jump-table-backed switch (`switchD_801956a4_caseD_4`) rather than nested
  if-chains.
* Cross-signed callees resolve to real names, including in-tree twin names
  (`AnimateEntity`, `AllocEntity`, `PlaySfxPositional`, and
  `func_us_80194338_from_rbo0` bound from the bobo7 symbol file). BO7's five
  orphans are in one TU (`unk_14CE0`) and all five are entity functions
  whose declarations already exist in `src/boss/bo7/e_init.c` as
  `void func(Entity*)`, so the rewrite target signature is known.
* The main entity is provably the Cerberus boss logic
  (`InitializeEntity(&g_EInitCerberos)`, prize-drop tables, state 8 switch).
  Comments can be written from evidence, not guesswork.

Needs the rewrite pass (the "not automated gibberish" work):

* `param_1` is `Entity*`, but fields appear as raw offsets (`0x2c`, `0x2e`,
  `0x50`); idiomatic output needs the typed struct members the repo already
  declares in `Entity`, so the rewrite is mostly mechanical renaming plus
  genuine semantic comments.
* Overlay data (`DAT_80180848`, `&DAT_801806fc`) and cross-overlay and
  main-DRA relocations (`func_0x80016d68`, `_DAT_8003c7c0`) come out
  under-typed; the latter need one future cross-link pass against the main
  EXE analysis, which the same wrapper scheme can extend to.

### 6.5 Oracle integration (the point that matters)

Byte identity stays proven by the fork's own machinery; nothing new is
invented. Per stub: diff the draft-derived rewrite against the retail `.s`
in `asm/us/<overlay>/nonmatchings/`. Per overlay: when all remaining stubs of
an overlay are landed as C, `make_build -> verify_build` (splat per-overlay
sha1, e.g. `dba86dc3b2709e37de651ad929ae29166a86f045` inside
`config/splat.us.bobo7.yaml`) is the accept/refuse line, exactly as for every
landed function before it. No candidate was landed here; there are no
matched records to report.

### 6.6 What is deliberately not done

* No landing waves, no queue writes, no active matching runs.
* No commit: the owner's staged files currently sit in the same index this
  session would commit from; committing any subset requires an owner
  decision first.
* REA-in-WSL MCP registration is still pending a session restart; the
  pipeline above runs without REA, so it is not a blocker for the
  decompile-diff-land loop.

## 7. Completion record: BO7 pilot C landing, 2026-11-04

This section records what the plan's wave 0 area produced first: five of
BO7's 13 `INCLUDE_ASM` stubs converted to C, byte-identical to retail, with
the checksum oracle green across the whole 113-artifact build. Donor
evidence, not REA output, drove every body; REA's role was to make the
problem legible, which section 6 records.

### 7.1 What landed

| function | BO7 file | donor twin |
|---|---|---|
| `EntityBigRedFireball` | `src/boss/bo7/e_misc.c` | `src/boss/bo3/e_misc.c` |
| `EntityDemonSwitch` | `src/boss/bo7/e_demon_switch_wall.c` | `src/st/chi/en_demon_switch_wall.c` |
| `EntityDemonSwitchWall` | `src/boss/bo7/e_demon_switch_wall.c` | `src/st/chi/en_demon_switch_wall.c` |
| `EntityBreakableWallDebris` | `src/boss/bo7/e_breakable_wall.c` | `src/st/chi/en_breakable_wall.c` (US donor; `chi_psp` is out of scope) |
| `EntityBreakableWall` | `src/boss/bo7/e_breakable_wall.c` | `src/st/chi/en_breakable_wall.c` (US donor; `chi_psp` is out of scope) |

Each `INCLUDE_ASM` was replaced in place, so the TU's function order still
matches retail address order. Data stays defined in `data/*.data.s`; the C
reaches it through externs, in the existing worker-injection comment style.

### 7.2 What the donor copy taught

The technique: copy the donor's C statement order verbatim in all
schedule-sensitive blocks, then let the per-symbol diff arbitrate. Same
toolchain, same translation-unit shape, so the retail schedule falls out of
the donor's plain statement order; reasoning about delay slots by hand would
have been slower and would still end at the oracle. Four order fixes were
needed beyond the straight copy:

* fireball INIT keeps `drawFlags`, `blendMode`, `opacity`, `zPriority` in
  the donor's emission order;
* switch INIT puts `animCurFrame` first, then `hitPoints`, then the hitbox
  triple (`hitboxState`, `hitboxWidth`, `hitboxHeight`); `0x7FFF` stays
  hex and the donor's `hitParams != 0` test was kept;
* debris INIT puts the `animCurFrame` assignment before
  `drawFlags`/`zPriority`;
* wall IDLE keeps the break sequence in one frame: `PlaySfx`,
  `breakCount++`, flags clear, then `hitPoints = 0x20` and the two hitbox
  subtractions.

Two donor quirks deserve a warning for future readers. The retail delay-slot
schedule is stronger than it looks: the donor order reproduces the
`EntityDemonSwitchWall` `li t0,0x6d` delay slot with no hoisting done in C.
And the wall donor repeats `remainingColumnCount = 0;` across branch arms
where it looks redundant; the arrangement survives the copy and the
byte-identical diff covers it, so treat it as verified rather than tidy it
up.

### 7.3 Oracle proof

Per-symbol `asm_diff(overlay=bo7, fmt=plain)` returned score `CURRENT (0)`,
no drift rows, for all five functions, checked after the reorder edits.
Incremental build job `make_build-091210-32` (rc=0) then read
`verify_build(us)` returned every expected checksum with `failed=[]`, so
`BO7.BIN` keeps its
retail sha1 `dba86dc3b2709e37de651ad929ae29166a86f045` against
`config/splat.us.bobo7.yaml`. All five queue records were then reported
`matched` with proof strings, `score=0`, and `keep_note=True`, so the
earlier derivation classification survives beneath each landing record.

### 7.4 Scope status, honestly

The checksum being green today is not at odds with 8 stubs still being
`INCLUDE_ASM`, because those emit retail bytes directly; BO7 is truly done
only when the last of them is C with the same oracle verdict. Remaining:
`EntityCerberusGateDebug` (`e_debug_cerberus_gate.c`, donor
`src/st/chi/en_debug_cerberus_gate.c`), `EntityBreakable` and
`EntityBreakableDebris` (`unk_13258.c`), and the five raw orphans
`func_us_80194D3C`, `func_us_801959E0`, `func_us_80195AF0`,
`func_us_80195C50` and `func_us_801963D8` (`unk_14CE0.c`). Each remaining
body follows the same route: donor or assembly, build, per-symbol
`asm_diff`, then `verify_build`.

Section 5's proposed ledger row was adopted as ROADMAP tasks 343 and 344 on
2026-11-04; 343 carries this document's existence and the pilot outcome, 344
carries this landing's proof.
