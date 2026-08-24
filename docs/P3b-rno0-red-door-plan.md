# P3b / task #51 — shim `e_red_door.h` into rno0

Status: **APPLIED** in `7c6ad016c` (task #51). `e_red_door.h` is shimmed into
rno0, `EntityRedDoor` matched, and the duplicate implementation deleted. The plan
below is kept as the derivation, not as work to do: re-running it would re-apply
a change that is already in the tree.

Every address below is measured, not inferred. It said "analysed, not applied"
for longer than it was true, and a 2026-08-15 audit read it as outstanding work.

## The headline: this is far smaller than P3b assumed

The roadmap entry says "segment rno0's `.data`", implying the same multi-segment
surgery `.bss` needed. It is not. rno0's `unk_39A8C` segment **already is**
`e_red_door.c`; it is merely misnamed. The work is one `.data` split plus two
renames.

Proof, from `config/splat.us.strcen.yaml` and `config/splat.us.strno0.yaml`:

| | rcen (already shimmed) | rno0 (this task) | size |
|---|---|---|---|
| `c` | `0x22BD4 .. 0x23884` | `0x39A8C .. 0x3A73C` | both **0xCB0** |
| `.data` | `0xE78 .. 0xE90` | `0x1454 .. 0x146C` | both **0x18** |

A byte-identical text span is not a coincidence across two overlays.

## How the `.data` address was found

`g_eRedDoorUV` is `static`, so it has no symbol to look up. It does have a
distinctive 24-byte initialiser in `src/st/e_red_door.h`:

```
B1 B7 B1 B7 21 21 5F 5F
88 A8 88 A8 21 21 5F 5F
A8 88 A8 88 21 21 5F 5F
```

Searching `build/us/RNO0.BIN` finds it exactly once, at file offset `0x1454`
(vaddr `0x80181454`; rno0's mapping is `vaddr = offset + 0x80180000`, confirmed
by `func_us_801B9A8C` at offset `0x39A8C` / vaddr `0x801B9A8C`).

**The method was validated against a known answer before being trusted.** The
same search on `build/us/RCEN.BIN` returns `0xE78`, which is precisely what
rcen's splat config already declares. A technique that reproduces a known
segment boundary can be believed on an unknown one.

The bytes at `0x146C` begin `00 00 65 00 C9 00 2D 01 91 01 ...`, a monotonically
increasing 16-bit table, so `0x146C` is a real boundary and not the middle of an
array.

## The `.rodata` is already exclusively red-door

`asm/us/st/rno0/data/unk_39A8C.rodata.s` contains one object, `jtbl_us_801B5B00`,
a six-entry jump table whose targets (`0x801B9B60`, `0x801B9EAC`, `0x801BA038`,
`0x801BA0E8`, `0x801BA134`, `0x801BA17C`) all land inside `EntityRedDoor`
(`0x801B9B04`) and before `DestroyEntity` (`0x801BA73C`). It is `EntityRedDoor`'s
own switch table, so the segment only needs renaming.

## The hand-matched copy is character-identical to upstream

`func_us_801B9A8C` in `src/st/rno0/unk_39A8C.c` and `EntityIsNearPlayer` in
`src/st/e_red_door.h` are the same function: same four separate `s16` locals,
same `abs()`, same 16 and 32 constants. The shim deletes the copy rather than
merely hiding it.

No inverted-castle parameterisation is expected: `rare`, `rcat`, `rcen`, `rchi`
and `rdai` are all second-castle overlays and all shim this header unmodified.

## Steps

1. `config/splat.us.strno0.yaml`, `.data` — split the unnamed blob in three:

   ```yaml
         - [0xE20, data]
         - [0x1454, .data, e_red_door]   # g_eRedDoorUV, 0x18 bytes
         - [0x146C, data]
   ```

2. Same file, `.rodata` — rename, do not move:

   ```yaml
         - [0x35B00, .rodata, e_red_door]
   ```

3. Same file, `c` — rename, do not move:

   ```yaml
         - [0x39A8C, c, e_red_door]
   ```

4. Delete `src/st/rno0/unk_39A8C.c`. Create `src/st/rno0/e_red_door.c` matching
   the sibling overlays exactly:

   ```c
   // SPDX-License-Identifier: AGPL-3.0-or-later
   #include "rno0.h"

   #include "../e_red_door.h"
   ```

5. `make extract` then a full build.

## Acceptance criteria

- `config/check.us.sha` verifies **113/113**. Anything less is a revert.
- `EntityRedDoor` no longer appears in any `INCLUDE_ASM`; queue record
  `us:ST/RNO0:EntityRedDoor` moves to `matched`.
- `src/st/rno0/unk_39A8C.c` is gone and `func_us_801B9A8C` appears nowhere in
  `src/`, i.e. the duplicated `EntityIsNearPlayer` is deleted, not orphaned.
- `automation/overlay_size_check.py` reports rno0 `BSS_START == TEXT_END`. A
  shifted bss with internally-correct symbols means a TEXT size error, which is
  the failure mode that cost a day on the clock-room shim.

## If it fails

Revert with `git_restore` and re-verify before doing anything else; never leave
the tree dirty for the fleet. The likeliest error is an off-by-one on the
`0x146C` boundary, which will surface as a `.data` size mismatch rather than a
checksum failure, so read the build error before assuming the address is wrong.
