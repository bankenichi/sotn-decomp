# Test honesty audit — 2026-08-02

Independent, adversarial review of the hand-written self-test scripts in
`automation/`. The question asked of every assertion was not "does it pass"
(they all pass) but **"would it fail if the thing it claims to test were
broken?"**

Method: each test file and the code under test read in full; every test
executed to observe real behaviour; the two questionable cases probed with a
throwaway script. No repo file was modified and nothing was built.

**Five of six suites run green in under two seconds.** The sixth
(`test_shim_gate.py`) was green through every assertion up to its final
population sweep, which did not complete in five minutes — see that section.
Green is the point of the exercise: green is cheap, and some of these checks
would be green against a stub.

---

## Summary table

| Suite | Verdict | Checks | Of which load-bearing |
|---|---|---|---|
| `automation/test_shim_gate.py` | **MISLEADING** | 26 | ~9 |
| `automation/test_build_classifier.py` | **SOUND** | 13 | 10 |
| `automation/test_review_gate.py` | **WEAK** | 20 | ~8 |
| `automation/test_twin_wiring.py` | **WEAK** | 30 | ~14 |
| `automation/overlay_size_check.py --self-test` | **SOUND** | 14 | 13 |
| `automation/relocation_check.py --self-test` | **SOUND** | 9 | 9 |

---

## 1. `automation/test_shim_gate.py` — MISLEADING

### The structural problem

`shim_gate()` returns `(defer: bool, reason: str)`. **Not one assertion in this
file ever observes `defer == True`.** Every single `check(..., not d, ...)`
asserts the gate declined to defer — lines 69, 93, 107, 113, 123, 129 — and
line 171 asserts globally that across all 417 stubs in `src/st` the count of
deferrals is exactly zero.

So the entire positive branch of `shim_gate` (worker_direct.py:2411-2417, the
`return True, "...replace this file's body with #include..."` path) is
**never executed by any test**. It could be deleted, or could return the wrong
path string, or could crash, and this suite stays green.

Worse, the `not d` assertions carry no information *individually*. `False` is
the correct answer for every input the test supplies, including the garbage
ones. An implementation of

```python
def shim_gate(ctx): return False, "shared impl exists but blocked: ..."
```

passes lines 69, 93, 107, 109, 113, 123 (partly), 129, 171 and 172. The names —
"stage-data obligation **blocks** the shim", "size divergence **blocks** the
shim" — read as if a blocking decision is being verified. What is actually
verified is a substring of the explanation string.

### The strongest assertions (keep these)

- **72** `"'.data, e_breakable'" in why` and **74** the peer citation. These are
  the only checks that pin `shim_needs_stage_data`'s real logic
  (worker_direct.py:2295-2340): it must have read a *peer stage's* `.c`, found
  `static` file-scope data with `_STATIC_DEF_RX`, and found no `named_data`
  segment for rno0. Hard to satisfy accidentally.
- **94** `"larger" in why` / `"smaller" in why` for rchi/e_breakable and
  rno0/e_lock_camera. This is the genuinely good pair: it pins *both directions*
  of `shim_size_divergence` (2243-2287), and the too-small direction is exactly
  the case a naive ratio check misses. Backed by real segment arithmetic out of
  `config/splat.us.st*.yaml`.
- **120** `src/st/rchi_psp/e_breakable.c` and `rno0_psp/e_lock_camera.c`. Real:
  these are files that *would* otherwise reach the shared-impl logic, so the
  `_psp` guard at 2371-2372 is actually exercised. The other entries in that
  loop (`src/dra/menu.c`, `""`, `"weird"`) only exercise the `len(parts) != 4`
  early return.

### The weak, tautological or dead ones

- **171-172.** `check("no stub is falsely claimed shimmable", deferred == 0)`
  followed by `check("deferrals could never stall the fleet", deferred < generated * 0.10)`.
  The second is **strictly implied by the first** — `0 < generated * 0.10` for
  any non-zero `generated`. It is presented as an independent safety bound; it
  is arithmetic. And the pair together assert the gate is *entirely inert*. This
  suite's headline claim is that the gate works; what it proves is that the gate
  currently never fires.
- **99-100.** `shim_size_divergence("rno0", "no_such_stem", idx) == ""` only
  reaches the first line of the function (`mine` is `None` → early return at
  2278). It does not test the divergence logic; it tests an unknown-key lookup.
  The two other early returns that matter — `len(peers) < 2` (2284) and
  `med == 0` (2287) — are untested.
- **95-96.** `"0x" in why and "x," in why` as a proxy for "the reason gives both
  sizes". `"x,"` matches the `{ratio:.2f}x,` fragment, not a size. Any message
  containing a hex number and the ratio passes; a message that dropped one of
  the two sizes would still pass.
- **140.** `src.index("_defer, _why = shim_gate(ctx)") < src.index("build_prompt(rec, ctx)")`,
  labelled *"it runs BEFORE the first model call"*. **The anchor is wrong.**
  `build_prompt(rec, ctx)` (exact substring, closing paren) occurs once, at
  worker_direct.py:2715 — inside the `if dry:` prompt-preview block. The real
  model call is at 2770 and reads `build_prompt(rec, ctx, feedback)`, which this
  substring does not match. The assertion therefore compares the gate against
  the *dry-run print*, not against the model call it names.
- **137-142.** Source-text greps generally. They do catch outright removal of the
  call, which is worth something, but they are pinned to local variable names
  (`_defer, _why`) and exact spacing. A cosmetic rename breaks them with no
  behaviour change. Classification: **fragile — will be deleted the first time
  it fails.** They should assert on behaviour (call `process_one` with a
  deferrable record under `dry=True` and observe the `sched("report", ...
  deferred)` argv) rather than on the file's own text.
- **41-42.** `def idx_for(wd)` ignores its parameter. **147.** `idx = json.loads(...)`
  is assigned and never used — the population loop below calls `wd.shim_gate`,
  which loads the index itself. Dead code in a file whose job is to be read as
  evidence.
- **103-104.** The comment describes `rno0/e_blade` and `rno0/collision`; the
  loop underneath iterates `collision` and `e_collect`. Doc drift.
- **126-131.** The "missing index" case sets `WIN_REPO` to a bad path, but
  `_CI_MOD` is already cached from the earlier calls (worker_direct.py:2195-2205),
  so what is exercised is the `open(index.us.json)` `FileNotFoundError`, not a
  failure to load `codebase_index`. Fine as far as it goes; the claim
  "degrades to no-defer" is only checked for `d`, not for `why == ""`, so a
  version that returned a bogus reason string would pass.

### A practical problem: this test does not finish in reasonable time

The population sweep at lines 150-159 calls `wd.shim_gate(...)` once per `.c`
file under `src/st` (1,253 candidates). `shim_gate` re-opens and re-parses
`automation/index.us.json` — **7.8 MB** — on *every single call*
(worker_direct.py:2379-2381; the `_CI_MOD` cache covers the module, not the
JSON). The other five suites in this audit each complete in under two seconds;
this one was still running after five minutes and was abandoned. Every
assertion before line 147 had already printed `ok`.

That matters for honesty as much as for convenience: a test nobody waits for is
a test nobody runs, and the two assertions gated behind the sweep (171, 172) are
the ones the file presents as its safety bound. Hoisting the index load out of
the loop, or memoising it, would make this a two-second test.

### Most important untested behaviour

1. **The deferral path itself.** No fixture makes the gate say `True`. Given the
   population is currently zero, this needs a *synthetic* index (`shared_impls`
   entry + a stage with a `named_data` segment + peer sizes inside the band) so
   the happy path and its message are pinned. Without it, the deferral message
   the fleet would act on has never been produced by a test.
2. `shim_size_divergence` boundary conditions: ratio exactly `0.75` and `1.25`
   (`_SHIM_SIZE_LO/HI`, 2241) are inclusive-pass; nothing pins that.
3. `_c_segment_sizes` parsing (2210-2232) — the last `c` segment in a file gets
   no entry at all (the loop only records `i+1 < len(lines)`), so the final file
   of every overlay is permanently unmeasurable and silently exempt from the
   size check. No test notices.
4. Case: a stage that *has* a `.data, <stem>` segment must return `""` from
   `shim_needs_stage_data` (2323-2324). Untested.

---

## 2. `automation/test_build_classifier.py` — SOUND

The best file in the set, and the only one where a constant-returning
implementation fails immediately in both directions: `return True` fails case 1
(line 49), `return False` fails cases 2-8 (lines 51-66).

### Strongest assertions

- **51-52** `"src/boss/bo0/2D26C.c:133: structure has no member named \`unk32'"` →
  `True`. This is the case the naive `"error:" in out` implementation gets
  wrong, and it pins `_DIAG_RX` (worker_direct.py:2534) rather than
  `_COMPILE_FAIL_MARKS`.
- **63-64** `"src/x.c:9: parse error\ncheck: checksum check failed"` → `True`.
  The precedence case. This is the assertion that stops broken C reaching the
  permuter, and it is the reason the whole file is worth keeping.
- **42-45** `REAL_CHECKSUM_ONLY`, kept verbatim from the misclassified
  worker-oc-2 tail. This is a fixture that genuinely pins a bug that actually
  happened: the emoji/`✅` lines and the bare `check: checksum check failed`
  are what the real tail looked like, and a synthetic approximation could
  plausibly have omitted the `check:` prefix.
- **68-69** `rc=0` with checksum text → `False`. Pins the ordering of the `rc == 0`
  short-circuit at 2560.

### Weak ones

- **92-99**, the three "contract" greps. Same fragility class as the shim gate's:
  `'return False, ("BUILT, CHECKSUM MISMATCH' in src` is coupled to the exact
  line break and parenthesis placement at worker_direct.py:2629. Reformatting
  that call breaks the test. They do encode a genuine cross-function invariant
  (routing at 2898 keys off the literal `"BUILD FAILED"`), which is worth
  asserting — but it should be asserted by calling the classifier and the
  routing predicate together, not by grepping source.
- **57-58** `"include/game.h:44: parse error"` is not really a separate case from
  the `.c` one; both exercise the same `(?:c|h)` alternation. Cheap, harmless.

### Most important untested behaviour — and a latent bug it hides

`_DIAG_RX = re.compile(r"[^\s]+\.(?:c|h):\d+:")` matches **compiler warnings**
just as readily as errors. A checksum-only failure whose 40-line tail happens to
contain

```
src/st/rno0/e_gorgon.c:88: warning: unused variable `tmp'
check: checksum check failed
```

is classified `True` — BUILD FAILED — which is precisely the misrouting this
function exists to prevent. There is **no test case containing the word
`warning`**. The docstring's claim of being "deliberately CONSERVATIVE" is
accurate about the direction of the design, but the tests only demonstrate
conservatism where it is safe; they never probe where it costs a `near`
classification. This is the single highest-value missing case in the suite.

Also untested: multi-overlay output where one overlay printed a diagnostic and
a later one printed `check: checksum check failed`; and `rc != 0` with completely
empty output (falls to `return "checksum check failed" not in out` → `True`,
which is the intended conservative answer but is unpinned).

---

## 3. `automation/test_review_gate.py` — WEAK

Genuinely good in one half, and contains one **provably vacuous** assertion.

### Strongest assertions

- **60-66.** The `UNIQUE_CANARY_9137` round-trip through `virtual_apply` against
  a real shipping file (`src/st/rno0/e_gorgon.c`). This is the right shape: it
  asserts the marker *appears* and the stub *disappears*, so a `virtual_apply`
  that silently returned the unmodified file — the documented dangerous failure
  — fails here. Line 68 (`sibling stubs are left alone`) additionally pins
  `count=1`.
- **89-96.** The `static`-across-a-TU-boundary case on `func_801CE04C`. Three
  assertions on the finding text, against a real function whose callers really
  are `INCLUDE_ASM` stubs in sibling files. If `review_gate` returned `[]` for
  everything, these fail. This is the founding-bug fixture and it genuinely
  reproduces the founding bug.
- **99-102.** The same function *without* `static` must return `[]`. This is what
  makes the previous three meaningful rather than "the gate rejects everything".
  Good pairing.
- **70.** `virtual_apply(ctx, "NoSuchFunction", body) == ""` pins the "stub not
  found" guard at 2455-2456 — the case that would otherwise let the gate inspect
  the wrong text.

### Weak / vacuous, with line numbers

- **114-118 is VACUOUS.** Verified by execution: running the five wired checks
  against that exact fixture produces **zero findings of any kind** (`noisy ==
  []`). The assertion `all("SomeOtherHelper" not in f for f in noisy)` is
  therefore `all([])` → `True` for structural reasons, not behavioural ones.
  The per-function filter it claims to test — worker_direct.py:2483-2486, the
  `if f.get("function") and f["function"] != fn: continue` that the comment says
  prevents a record becoming "unmatchable forever" — **can be deleted outright
  and this suite still passes green.** The name overclaims maximally: "a finding
  about another function is not attributed here" describes an experiment that
  never produced a finding.
- **108-109, 123, 101-102** all assert `== []`. Three of the twenty checks are
  satisfied by `def review_gate(...): return []`. Not wrong to have, but they
  are the cheap half.
- **126-129.** `"angle" not in wd._REVIEW_GATE_CHECKS` etc. These assert the
  literal contents of a tuple defined 40 lines away in the same module
  (worker_direct.py:2421). They restate a constant. Their only value is as a
  tripwire against someone adding `angle` — real, but it is a policy assertion,
  not a test.
- **138-140.** Source greps again, same fragility class. `src.index("defects += review_gate") < src.index("with BuildLock(")` is a *textual* ordering claim standing in for a
  control-flow claim. Here it happens to be sound (2830 < 2861, same function,
  straight-line), but the technique does not generalise and reads as stronger
  evidence than it is.
- **130-132.** `all(k in wd._review_checks_module().CHECKS for k in _REVIEW_GATE_CHECKS)`
  is a decent integration assertion — it catches a rename in `review_checks.py`
  — but note that `review_gate` itself does `rc.CHECKS.get(key)` and
  `if fnc is None: continue` (2472-2474), i.e. it **silently skips a missing
  check**. So without this assertion a renamed check would degrade the gate to a
  no-op with no error. Worth keeping; it is doing more work than it looks like.

### Most important untested behaviour

1. **The lockstep claim is not asserted.** The docstring at worker_direct.py:2445-2450
   says `virtual_apply` is "kept deliberately in lockstep with `apply_code`'s
   substitution". The regexes at 2451-2454 and 2506-2509 are duplicated source,
   not shared. The test verifies `virtual_apply` substitutes; it never verifies
   the two produce the *same* result. Drift in `apply_code` is invisible here.
   (There is already a small real divergence: `virtual_apply` opens with default
   newline translation, `apply_code` uses `_read_raw` and preserves CRLF.)
2. The `ext`, `static`, `signature`, `stub` checks are all wired
   (`_REVIEW_GATE_CHECKS`, 2421) and **only `linkage` is ever demonstrated to
   fire**. Four of five gate checks have no fixture.
3. The per-check exception swallow at 2475-2478 (a check that raises is ignored)
   is untested — a check that always throws would silently disable itself.
4. CRLF source files. `virtual_apply`'s lookahead is `(?=\r?$)`, and the file it
   is tested against is LF.

---

## 4. `automation/test_twin_wiring.py` — WEAK

Broad, and about half of it is real. The other half asserts on string constants
that `twin_for` appends unconditionally.

### Strongest assertions

- **86-95.** The collision pair. `twin_for("EntityBreakable", "st/rchi")` must
  report `156 instructions` and `st/rno0` must report `92`. Both numbers come
  from `twins.us.json`, both records are real, and the assertion is the only
  thing distinguishing the two calls — the candidate lists are identical by
  design. This is the best test in the file and the docstring's account of it
  (including the admission at lines 24-28 that the author's first assertion here
  was simply wrong) is honest. **Judgement on live-data coupling: good, pins
  real data.** If `asm_twin_finder.py` regenerates the file and these numbers
  move, that is a fact worth being told about.
- **102-104.** `unique symbol + wrong overlay resolves` vs `colliding symbol +
  wrong overlay stays silent`. This is the actual dangerous behaviour — the
  `len(hits) != 1` fallback at worker_direct.py:1706-1709 — and the two
  assertions bracket it from both sides. Cannot be faked by a constant.
- **82.** `"similar symbols" not in s` for `BO6_RicStepStand`. **Verified
  non-vacuous**: that record has `name_twins: 1` *and* `token_twins: 3`, so the
  suppression at 1731-1735 is genuinely exercised. Easy to mistake for a
  vacuous check; it is not.
- **70-73.** Key uniqueness and "exactly two `EntityBreakable` records" asserted
  against the on-disk `twins.us.json`. Pins the schema decision (key on
  `<overlay>/<symbol>`) that the earlier bug violated. Good.
- **136-141.** `WIN_REPO = "/nonexistent-path"` → silence. Real: exercises the
  `except (OSError, ValueError, AttributeError)` at 1670-1671.
- **148-153.** `build_prompt` actually contains the twin section, before the
  assembly. This is behavioural (it calls the function) rather than a source
  grep, which is how the wiring assertions in the other files should have been
  written.

### Weak / tautological, with line numbers

- **131 is TAUTOLOGICAL.** `check("shared-impl twin names the shim rule", "#include shim" in bat)`.
  The string `"the answer there is a one-line #include shim, not a copy."` is
  part of the **unconditional trailer** appended to *every* twin section
  (worker_direct.py:1765-1766). It has nothing to do with `EntityBat` being a
  shared implementation. The identical assertion passes for
  `twin_for("BO6_RicStepStand", "boss/bo6")`. What the name claims — that a
  shared-impl twin is *routed differently* — is not tested at all, and
  `twin_for` in fact contains no shared-impl routing; it emits the same advice
  to everyone.
- **79, 80** (`"DIFF IT AGAINST THE ASSEMBLY"`, `"BY ADDRESS"`) are the same
  trailer constants. They are not wrong — they do pin that the framing text
  survives — but together with 131 they are three assertions that reduce to
  "the output is non-empty".
- **121, 123** (`"0xE4"`, `"SHARED header"`) sit inside the same
  `if _is_inverted(...)` block already pinned by 119-120. Three checks, one
  branch. Redundant rather than dishonest.
- **113-116.** `_is_inverted("st/rno0")`, `not _is_inverted("st/no0")`, etc.
  assert membership in the hardcoded `_INVERTED` set at 1640-1643. Restating a
  literal. Note the set contains `"rcen"` while the comment immediately above it
  (1637-1639) uses `st/rcen` as the example of a name that would *misfire* — a
  contradiction between comment and data that no test can see, because the test
  only re-asserts the data.
- **65** `len(twins) > 0` and **88, 89** `!= ""` are presence checks, not
  behaviour checks.
- **54, 134, 141.** The test manipulates module globals `wd._TWINS` directly.
  Necessary given the caching, but it means the test is coupled to the private
  memoisation shape.

### Most important untested behaviour

1. **`shape_twins` output (1727-1730)** — including the `identical_constants`
   →`"identical"`/`"DIFFERENT"` branch — has no fixture. That branch tells the
   model whether the constants match, which is exactly the class of divergence
   the docstring says burned four of six BO6 ports.
2. **The `token_twins`-only path.** Line 82 asserts tokens are suppressed when a
   name twin exists; nothing asserts they are *emitted* when nothing stronger
   fired (1733-1735). Both halves of a conditional, one tested.
3. A record present in `twins.us.json` but with all three lists empty must
   return `""` (1721-1723). Untested.
4. `_overlay_of` on a Windows-style path (`src\st\no0\x.c`) — the
   `.replace("\\", "/")` at 1648 is untested despite the worker being the
   Windows-side runner.

---

## 5. `automation/relocation_check.py --self-test` — SOUND

The best-designed self-test in the repo, and the docstring at line 71 ("Pure
function, so the self-test is real") is the reason: `classify()` takes two byte
strings and returns a dict, so the fixtures are complete and the test is
hermetic.

### Strongest assertions

- **232-234, 239-240.** `scattered deltas → "mixed"` and `one real difference
  among nine relocations → "code"`. These are the two failure modes that matter:
  naming a bogus constant, and letting a real code difference hide behind
  relocation noise. Both are constructed to *defeat* the obvious wrong
  implementation, which is what a fixture is for.
- **226-229.** A changed register with the same opcode is `code`, not
  `relocation`. This pins the `(a >> 16) == (b >> 16)` term at line 91, which is
  the subtle half of the predicate and the one a reimplementation would drop.
- **247-250.** The `lui` scaling (`0x10000` at line 95). Constructed so that
  getting the scale wrong yields `0x1` instead of `0x10000` and fails.
- **211-216.** The `0xE4` fixture. It corresponds to a real project constant
  (`RCEN_OPEN - CEN_OPEN`), and unlike most "founding bug" fixtures in this repo
  it is checked for the *specific* delta, not just the verdict.

### Weak ones

- **207-208.** `classify(a, a)["verdict"] == "identical"` compares a buffer with
  itself. Trivially true for any implementation with the `total == 0` early
  return. Harmless, low value.
- **243-244.** Size mismatch — reaches line 72, the first branch. Also cheap.
- No assertion anywhere checks `_DOMINANCE = 0.80` (line 63) at its boundary.
  The "mixed" fixture at 232 is far from 0.80; a drift to 0.5 or 0.95 would not
  be noticed.

### Untested

`staleness_warning()` (147-177) — the function whose docstring records a real
2026-08-02 incident where a stale `build/us/RCEN.BIN` produced a verdict about a
candidate nobody was working on. It is untestable as written because it walks
the live repo, and it is untested. Given it is the guard against the entire tool
lying, it deserves to be refactored to take `(newest_src, oldest_bin)` and get a
three-line fixture. Same for `overlay_pair`'s `F_` prefix stripping (139) and
the `ST`/`BOSS`/`SERVANT` search order.

---

## 6. `automation/overlay_size_check.py --self-test` — SOUND

### Strongest assertions

- **232-243, 246-249.** The three-way `section_verdict` discrimination: bss
  symbol with a correct `BSS_START` → "INSIDE bss"; symbol below `BSS_START` →
  text/data; `BSS_START` itself shifted → upstream. Each of the three branches
  (worker file lines 160-181) has its own fixture, and **236** explicitly asserts
  the *old wrong answer* is absent (`"fault is in TEXT" not in joined`). That is
  the correct way to pin a fixed bug: assert the old behaviour is gone, not just
  that some new string appeared. The best single assertion in the whole suite.
- **251-253.** `expected_bss_start("strno0") == 0x801D3EB8` parses the live
  `config/splat.us.strno0.yaml` through the real two-stage regex at 131-137.
  **Judgement on live-data coupling: good, pins real data** — the value is a
  structural property of the overlay, it does not churn, and if it changes, the
  attribution logic in `section_verdict` genuinely needs re-checking. Note the
  other `section_verdict` fixtures depend on this same parse succeeding, so this
  assertion is load-bearing for three others.
- **260-263.** First-symbol divergence yields no culprit — pins the `i > 0` guard
  at 192 and the corresponding "the fault is before it" message path.
- **266-267.** `_locate([("Z", 0x9000)], {})` — symbols absent from the map are
  not divergences. Pins the `got is not None` guard at 189, which is exactly the
  check whose absence would produce a flood of false positives on any partial
  map.

### Weak ones

- **218-223.** The A..F fixture is good, but `first == "F"` / `delta == 0x10` /
  `culprit == "E"` are three assertions on one call; the file's 14 checks are
  really about 8 independent behaviours.
- **256-257.** `expected_bss_start("stnosuch") is None` reaches the
  `if not p.exists()` first line (128). Cheap.
- The `check()` function itself (lines ~60-122, the part that consumes a real
  `.map` and `symbols.us.*.txt`) is **entirely untested** — `self_test` only
  covers the two pure helpers it extracts. The docstring at 198-202 claims "this
  proves it DETECTS", which is true of `_locate` and `section_verdict` and not
  true of the tool.

---

## Overall judgement

### How much confidence is this suite actually worth?

**Partial, and unevenly distributed.** Roughly 60% of the assertions across the
six files would fail if the code under test were broken. The other 40% split
into three categories:

1. **Source-text greps** (`test_shim_gate.py` 137-142, `test_build_classifier.py`
   92-99, `test_review_gate.py` 137-140). These assert that a literal string
   appears in `worker_direct.py`. They catch deletion; they do not catch
   behavioural change; they break on cosmetic edits; and one of them
   (test_shim_gate.py:140) is anchored on the wrong call site. They are the
   likeliest checks in the repo to be deleted the first time they go red for a
   harmless reason, which means the wiring guarantee they represent is the
   least durable one.
2. **Constant restatement** (`test_review_gate.py` 126-129, `test_twin_wiring.py`
   113-116, and the trailer-string checks 79/80/121/123/131). These re-assert
   literals defined a few dozen lines away in the code under test. They cannot
   discriminate.
3. **Two checks that are provably incapable of failing**: `test_review_gate.py`
   114-118 (vacuous — verified: zero findings produced) and
   `test_twin_wiring.py` 131 (tautological — the string is in the unconditional
   trailer). Both have names that describe behaviour the suite does not test.

The **docstrings systematically overclaim**. Every file opens with a compelling
incident narrative — the four hand-retriaged records, the `StepTowards` link
break, the collapsed `EntityBreakable` key, the two build cycles lost to a wrong
TEXT diagnosis. Those narratives are, as far as I can verify, true. But the
narrative describes the *bug*, and the reader is invited to infer that the
assertions below cover it. In three of six files they only partly do:

- `test_shim_gate.py` narrates a gate that defers work and then asserts it never
  defers anything.
- `test_review_gate.py` narrates the "unmatchable forever" failure and then
  tests it with a fixture that produces no findings.
- `test_twin_wiring.py` narrates shared-implementation routing and then asserts
  a string that is printed unconditionally.

The two `--self-test` modes are the honest ones, and the reason is structural,
not a matter of care: `classify`, `_locate` and `section_verdict` are pure
functions over small inputs, so their fixtures are complete and their assertions
are forced to be behavioural. Where the repo has extracted a pure function, the
test is sound. Where the test must reach into a 3,100-line worker module, it
degrades into grepping source text and checking substrings of prose.

**What this suite is genuinely good for:** the build classifier's two-directional
case table, `relocation_check`'s discrimination fixtures, `overlay_size_check`'s
three-way section attribution, and the `EntityBreakable` collision pair. Those
four are real regression protection and should be cited as such.

**What it should not be cited for:** "the shim gate works" (its deferral path has
never run), "the review gate filters foreign findings" (that filter is
unexercised), "twins route shared implementations to a shim" (no such routing
exists), or "the gates are wired into the worker" (asserted by grep, on one
occasion against the wrong anchor).

### The single test I would write first

**A checksum-only build failure whose output also contains a compiler warning.**

```python
("a warning does not turn a checksum miss into a build failure",
 2, "src/st/rno0/e_gorgon.c:88: warning: unused variable `tmp'\n"
    "check: checksum check failed", False),
```

Reasons it comes first, ahead of the more structurally embarrassing gaps:

- It is a **currently-failing** test. `_DIAG_RX` (`worker_direct.py`:2534)
  matches any `file.c:NN:` prefix and has no notion of `warning:`, so this
  input returns `True` today. Every other gap in this audit is a missing test
  for correct code; this is a missing test for incorrect code.
- It reopens exactly the failure the file was written to close. Four `near`
  records were retriaged by hand on 2026-08-01, and this path still misroutes
  them whenever a warning lands in the last 40 lines of output — which is not
  an exotic condition in a GCC 2.7 tree.
- The consequence is silent and expensive in both directions: the record is
  escalated to a better model instead of the permuter, *and* the permuter seed
  is never saved (`worker_direct.py`:2898-2907 gates on `"BUILD FAILED" not in
  detail`), so the compiled candidate is discarded.
- It costs one line in an existing table.

Second and third, in order: a synthetic-index fixture that drives `shim_gate`
down its `return True` branch (test_shim_gate.py currently proves only that the
gate is inert), and a real fixture for the per-function finding filter that
replaces the vacuous check at test_review_gate.py:114-118 — pick a file that
genuinely produces a `linkage` or `ext` finding on a *different* function and
assert it is dropped.
