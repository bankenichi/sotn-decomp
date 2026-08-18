# Queue Evidence Truncation and Recovery, 2026-08-17

## Status

The writer defect is fixed and covered by tests. The two known damaged live
records were repaired on 2026-08-18 after the `sotn-cmd` connector restarted
and loaded the fixed client. A fresh build verified 81/81 immediately before
both replacement reports, and a matched-record readback confirmed that each
note ends with its intended final sentence.

The missing trailing prose cannot be recovered byte-for-byte. It was discarded
before the scheduler received it, so neither the live queue nor any snapshot
ever contained those bytes. The technical facts survived in source comments.
The replacement payloads below reconstruct those facts and explicitly
supersede the truncated fragments.

## Cause and scope

`automation/mcp/commands_client.py` silently sliced every note to 250
characters and every proof to 200 characters. The scheduler had a second
silent 1000-character cap when `--keep-note` accumulated notes. Several direct
scheduler callers in the worker, permuter supervisor, and escalation triage
also sliced evidence before reporting it. The claim-limit breaker separately
sliced its accumulated note to 1000 characters.

All known queue writers now forward complete notes and proofs. The scheduler
preserves complete accumulated notes. Removing the caps was not sufficient for
the Windows workers because a large note could exceed the Windows command-line
limit before reaching WSL. Those workers now remove notes and proof from argv,
serialize them as JSON on stdin, and select the scheduler's
`--evidence-stdin` transport. The transport regression sends a 40,000-character
note and proof across that boundary and verifies the exact queue values. Other
regressions cover direct reports, `--keep-note`, the claim-limit breaker, and
reject sliced direct `--notes` or `--proof` arguments in Python writers under
`automation/`.

## Known damaged records

### `us:ST/RNO0:EntityClockRoomController`

The live note ends with `(1) DECLARATION ORDE`. The proof preserved in the
committed snapshots is:

```text
verify_build us: 81/81 OK, failed=[]; build/us/RNO0.BIN checked against config/check.us.sha [scheduler-verified: 81/81 artifacts byte-exact]
```

The reconstruction is supported by
`src/st/rno0/e_clock_room.c`: the local statue enum and declaration ordering
are documented at lines 4 through 28, the RNO0 divergences at lines 114 through
149, and the signed counter at lines 154 through 160.

Use this complete replacement note:

```text
MATCHED 2026-08-17 by hand-derivation from asm/us/st/rno0/nonmatchings/e_clock_room/EntityClockRoomController.s, not by harvest and not by permuter. Verified 81/81 with the controller compiled in. Two silent codegen issues kept the derived body from landing. (1) DECLARATION ORDER: src/st/clock_room_entities.h is included at the end of e_clock_room.c, so the controller needs earlier declarations for g_Statues and OVL_EXPORT(EInitCommon), with g_EInitCommon mapped to OVL_EXPORT(EInitCommon). The shared header does not provide the per-overlay Statues enum; RNO0 must declare RIGHT_STATUE=0 and LEFT_STATUE=1. (2) SIGNEDNESS: relicsMissing must be s16. The target emptiness test is `sll $v0, $v1, 16` followed by bnez. A u16 counter emits `andi 0xffff` instead, which was the final byte mismatch. This is not a twin port. Six divergences are inverted-castle constants, while the seventh is different logic: RNO0 checks RELIC_HEART_OF_VLAD through RELIC_EYE_OF_VLAD for RELIC_FLAG_FOUND instead of the donor's gold-ring and silver-ring condition. The loop must spell g_Status.relics[i], not status->relics[i], to rematerialise %hi(g_Status). Step 2 snaps the player's X to 0x60 or 0xA0, and substeps 0 through 3 must remain separate blocks.
```

### `us:BOSS/BO6:func_us_801B6998`

The live note ends after the first sentence of the corrected diagnosis. The
proof preserved in the committed snapshots is:

```text
verify_build us: 81/81 OK, failed=[]; build/us/BO6.BIN checked against config/check.us.sha [scheduler-verified: 81/81 artifacts byte-exact]
```

The reconstruction is supported by `src/boss/bo6/richter.c` lines 705 through
734. The four live cases are documented in the body at lines 737 through 766.

Use this complete replacement note:

```text
MATCHED 2026-08-17 by hand-derivation from asm/us/boss/bo6/nonmatchings/richter/func_us_801B6998.s. This supersedes the 2026-08-16 upstream-harvest attempt, and the diagnosis recorded that day was wrong: the delay-slot nop at +21 was a codegen symptom, not the source-level cause. The target uses a 51-entry jump table for the exact case range 0 through 50. Empty cases 0 and 50 are load-bearing. Omitting them makes the compiler emit a compare chain for the four live cases and leaves the function 0xB4 bytes short. Case 0 is the initial value; RichterThinking case 40 parks the driver at the no-op case 50. The branch delay slot at +21 must contain `ori $v0, $zero, 1`. Statement order produces it: g_unkGraphicsStruct.pauseEnemies=true must precede D_us_801D11C0=0. The boolean constant is a single register-immediate instruction that the scheduler can hoist over the branch, while the global store expands to an indivisible lui/%lo pair. Swapping the stores adds one word. The only live cases are 10, 11, 20, and 40.
```

## Safe live repair after restart

The following procedure was executed successfully on 2026-08-18 and is kept
here as the recovery record:

1. Wait for any active build or main-thread mutation to finish.
2. Run `make_build` through a background job, then require `verify_build` to
   return 81/81.
3. Report each record as `matched` with its replacement note, the proof prefix
   below, and `keep_note=False`. Replacement is intentional because each full
   note supersedes its truncated prefix.
4. Let the scheduler append a fresh `[scheduler-verified: ...]` suffix. Do not
   pass the old suffix back in or it will be duplicated.
5. Read the two matched records back and confirm that both notes end at their
   intended final sentences.

Proof prefixes to pass:

```text
EntityClockRoomController: verify_build us: 81/81 OK, failed=[]; build/us/RNO0.BIN checked against config/check.us.sha
func_us_801B6998: verify_build us: 81/81 OK, failed=[]; build/us/BO6.BIN checked against config/check.us.sha
```

Do not create a queue snapshot merely for these two ordinary reports. The
canonical snapshot frequency rule is in
`automation/queue/snapshots/README.md`.
