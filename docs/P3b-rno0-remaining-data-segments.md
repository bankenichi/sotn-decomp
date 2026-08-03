# rno0's shim blockers: ONE cause, five stems, ~23 stubs

## UPDATE 2026-08-02 (post-audit): the blocker is a single, shared cause

The audit showed `e_blade`, `e_gurkha` and `e_hammer` DO have shared
implementations (no2 and np3 shim all three), retracting a false "no shared
impl" claim. All three were then attempted end to end. All three fail the same
way as `e_misc` and `e_room_fg`, and the numbers are striking:

| stem | rno0 text | no2 | np3 | delta |
|---|---|---|---|---|
| `e_hammer` | 0x12B8 | 0x12AC | 0x12AC | **+0xC** |
| `e_gurkha` | 0x1294 | 0x1288 | 0x1288 | **+0xC** |
| `e_blade`  | 0x1544 | 0x1538 | 0x1538 | **+0xC** |

Exactly +0xC in all three, against two independent peers that agree with each
other. That is three extra instructions per file, in the same amount, which is
a systematic difference rather than three coincidences. `overlay_size_check`
localised the first one to `EntityHammer` being 0x14 short.

Their `.data` addresses ARE correct and were confirmed three ways: derived
starts (0x2124 / 0x26A0 / 0x2B90) reproduce the peer-declared sizes exactly
(0x26A0-0x2124 = 0x57C, 0x2B90-0x26A0 = 0x4F0), and no2 and np3 independently
declare 0x57C / 0x4F0 / 0x698. Placement was never the problem.

**So five stems are blocked on one thing: rno0's function bodies differ in size
from what the shared header emits.**

```
e_misc     14 stubs   header emits 0xB8, rno0's slot is 0xB4   (-0x4)
e_hammer    3 stubs   +0xC per file
e_gurkha    2 stubs   +0xC per file
e_blade     2 stubs   +0xC per file
e_room_fg   1 stub    header emits 0x8C, rno0's slot 0x78      (one ObjInit)
```

That is ~22 stubs behind a single capability: parameterising the shared headers
so a stage can supply its own variant. `entity_lock_camera.h` already proves the
pattern works, and it produced a match. The identical +0xC across three
unrelated giant-bro files is the best available lead: find that difference once
and three stems may fall together.

Scoped as task #64. Do NOT attempt these individually again without it; that has
now been tried and reverted twice.

---

# Original: rno0's last three shim blockers: `e_misc`, `e_collect`, `e_room_fg`

## RESULT 2026-08-02: none of them is shimmable. This is a dead end.

Tried `e_room_fg` and `e_misc` end to end. Both fail the same way, and the
reason is not placement, so no amount of segment work fixes it:

**rno0's data slot is SMALLER than the shared header can emit.**
*(FALSE for both rows. The table is kept as the record of what was measured;
see the retraction below it for what each measurement actually meant. In both
cases the slot was measured from the wrong starting address or compared against
the wrong variant, not genuinely too small.)*

| stem | header emits | rno0's slot | short by | evidence |
|---|---|---|---|---|
| `e_room_fg` | 0x8C | 0x78 | 0x14 | declaring 0x48 shifted the build +0x44 (= 0x8C-0x48); declaring 0x8C orphaned `D_us_80181DC4`/`D_us_80181DD4`, which `e_floor_trap` and `e_thornweed_corpseweed` reference |
| `e_misc` | 0xB8 | 0xB4 | 0x04 | declaring 0xB4 left the build 0x4 short; declaring 0xB8 orphaned `D_us_80181A74`, which `e_background_pillars` references |

**BOTH CLAIMS BELOW ARE RETRACTED (2026-08-02). Both files are now shimmed.**
The original text is kept because the reasoning errors are more instructive than
the conclusions were.

> `e_room_fg`'s is exactly one `ObjInit` entry: the header emits 0x14 of anim
> tables plus SIX entries of 0x14 each; rno0 has five. And `e_room_fg.h` has
> ZERO preprocessor conditionals, so it cannot produce a five-entry variant for
> anyone.
>
> `e_misc.h` does have 6 conditionals, so a per-stage size was plausible there,
> but none of them yields 0xB4 for rno0.
>
> Both would need the SHARED HEADER parameterised, which changes a file 23 and
> 27 stages respectively depend on. [...] not worth one stub for `e_room_fg`.

What actually happened:

- **`e_room_fg` needed no header change at all.** 0x78 is SIX `ObjInit` entries
  (6 * 0x14), not five. It was measured from `D_us_80181D4C`, where the
  `ObjInit` array starts, but the header declares the five 4-byte anim tables
  FIRST, so the file's data begins 0x14 earlier at 0x1D38 -- an address the
  config already carried as a raw `data` segment. 0x1D38..0x1DC4 = 0x8C, the
  size all 18 declaring peers use. The companion claim that `e_floor_trap` and
  `e_thornweed_corpseweed` reference addresses "inside" that range was an
  off-by-one: 0x1DC4 is the exclusive end.
- **`e_misc` needed a one-line change to an EXISTING conditional.** `cat` and
  `lib` also declare 0xB4 and both plain-shim the header, which by itself
  disproves "none of them yields 0xB4". The mechanism is `g_QuadIndices2`,
  which emits a trailing `0, 0` unless the stage is in an exclusion list that
  already held NZ0, NO1, CHI, ST0, LIB and CAT. rno0 joined it. 14 stubs.

Two general lessons, both cheap to apply:

1. **A segment starts at the first thing the FILE emits, not the first thing its
   code names.** Every wrong size here came from measuring at a referenced
   symbol rather than at the start of the file's data.
2. **Read a size histogram for its variants, not its mode.** `cat` and `lib`
   were visible in the same table that produced the wrong conclusion.

`e_collect` was not attempted here and remains the hard one: 79 conditionals and
the most raw `D_us_` externs. It was later attempted and reverted with evidence
that rno0's `EntityRelicOrb` is a genuinely different variant; see its queue
record.

**What survives from this analysis:** the START rule is correct and is now
proven three times (`e_particles` 0x1CB8, `e_medusa_head` 0x3354, and the
starts derived here matched the failures' arithmetic exactly). The SIZE rule
does not exist; peers disagree and the next file's first reference is not a
boundary, because a file may reference another file's data.

Tree left at 81/81. Everything below is the original analysis, kept because the
addresses are right even though the conclusion changed.

---

Status: **analysed, applied, REJECTED.** Worth 16 stubs, of which `e_misc`
alone is 14.

## Why `find_data_segment.py` refuses these three

That tool locates a segment by taking a peer's bytes and searching for them.
It works when the shared header's data is stage-independent, and it calibrates
against a second peer before trusting a hit. For these three it correctly
refuses:

- `e_collect.h` has **79** preprocessor conditionals
- `e_misc.h` has **6**
- `e_room_fg.h` has none, yet peer bytes still differ

So the bytes are stage-dependent and byte-matching cannot work. A different
signal is needed.

## The signal that does work: reference order

splat emits a file's `.data` in the same order it emits that file's text. So
sorting overlays' files by `c` segment address and reading which data addresses
each one's assembly references reconstructs the `.data` layout.

Collected from `%hi(D_us_8018xxxx)` across every `asm/us/st/rno0/nonmatchings/<stem>/*.s`:

```
c-seg     stem                    data references
0x3bbec   e_collect               195c 1960 1970 1980 1990 19a0 19b0
0x3e55c   e_misc                  19c0 19d0 19e0 19f8 1a10 1a14 1a1c 1a24 1a34 1a54
0x408f8   e_background_pillars    1a74 1a84
0x40c54   e_clock_room            1a94 .. 1af0
0x457f0   e_particles             1cb8 1cc8 1d28          <- declared 0x1CB8
0x46034   e_room_fg               1d4c
0x46450   e_floor_trap            1dc4
0x524c8   e_medusa_head           3354 .. 33c2            <- declared 0x3354
```

**The method is validated by two already-correct answers.** `e_particles` is
declared at `0x1CB8` and `e_medusa_head` at `0x3354`; both equal the minimum of
their own reference cluster, and both build at 81/81. A rule that reproduces two
known segment starts can be believed on unknown ones.

Note each file also references low addresses in the shared `EInit` region
(`0x8f8`-`0xc00`). Those are other files' data and must be excluded; only the
high cluster belongs to the file.

## The trap: peer-majority size is WRONG for all three

The obvious next step is to take the size most peers use. That gives the wrong
answer every time here, and the ordering constraint catches it:

| stem | start | peer-majority size | that would end at | next file's first ref | verdict |
|---|---|---|---|---|---|
| `e_collect` | 0x195C | 0x354 (16/27) | 0x1CB0 | 0x19C0 (`e_misc`) | **overlaps 5 files** |
| `e_misc` | 0x19C0 | 0xB8 (14/27) | 0x1A78 | 0x1A74 (`e_background_pillars`) | **overlaps by 4** |
| `e_room_fg` | 0x1D4C | 0x8C (26/27) | 0x1DD8 | 0x1DC4 (`e_floor_trap`) | **overlaps by 0x14** |

In each case a MINORITY peer variant fits, which is consistent with these
headers being heavily conditional:

| stem | proposed | size | ends | fits a real peer variant? |
|---|---|---|---|---|
| `e_collect` | `[0x195C, .data, e_collect]` | 0x64 | 0x19C0 | yes, 4 peers use 0x64 |
| `e_misc` | `[0x19C0, .data, e_misc]` | 0xB4 | 0x1A74 | yes, 2 peers use 0xB4, and it lands EXACTLY on the next reference |
| `e_room_fg` | `[0x1D4C, .data, e_room_fg]` | 0x48 | 0x1D94 | yes, 1 peer, but leaves a 0x30 gap before 0x1DC4 |

Confidence: `e_misc` **high** (exact landing on the next boundary), `e_collect`
**high** (exact landing), `e_room_fg` **medium** (no size lands exactly; 0x78
would, but no peer uses 0x78, so either 0x48 plus a gap is right or the header
emits something this overlay does not reference).

A gap is not by itself an error. `e_particles` is declared 0x80 and ends at
0x1D38 while the next reference is at 0x1D4C, a 0x14 gap, and it builds clean.

## Before building each one, run the pre-flight

The `st_update` lesson: check for UNINITIALISED file-scope storage first, since
that needs a `.bss, <stem>` segment or the storage is appended after all other
bss and silently shifts the overlay.

Checked already:

- `e_misc.h` declares none. `.data` only.
- `e_room_fg.h` declares none. `.data` only.
- `e_collect.h` has one candidate line (`char* obtainedStr;`) which needs
  confirming as function-local rather than file-scope before building.

Also expect to NAME symbols. Every stem shimmed on 2026-08-02 needed at least
one, and the linker names it precisely. `e_collect.c` in particular already
carries several raw `extern u16 D_us_8018xxxx[]` declarations that the shared
header will want under real names.

## Order to apply, and why

1. **`e_room_fg`** first. One stub, one data reference, no bss, no conditionals
   in the header. It is the cheapest way to test the ordering method on an
   unknown, and its medium confidence means it is the one most worth learning
   from early.
2. **`e_misc`** second. 14 stubs, the whole point of this exercise, and the
   highest-confidence address of the three.
3. **`e_collect`** last. 79 conditionals, and its own file has the most raw
   `D_us_` externs to rename, so it is the most likely to need several
   link-error rounds.

## Acceptance criteria, per stem

- `verify_build` reports **81/81**. Anything less reverts.
- `automation/overlay_size_check.py` reports **0 shifted symbols**.
- The stem's `INCLUDE_ASM` count drops to 0 and its queue records move to
  `matched`.
- No new raw `D_us_` name is introduced; anything the linker demands gets a real
  name in `config/symbols.us.strno0.txt` or the owning `.c`.

## If a build fails

A link error is the GOOD outcome: it names the missing symbol and the file that
wants it, which is how `g_ItemIconSlots` and `g_EInitDamageNum` were both found
in one build each. A checksum failure is the harder one; run
`overlay_size_check.py` first, and trust its section attribution now that it
distinguishes bss-internal growth from text growth.
