# Zen reasoning A/B results, 2026-08-22

## Design

ROADMAP #111 ran as one controlled production fleet:

- backend: Zen, default `mimo-v2.5-free`;
- four workers;
- alternating efforts `none,low`;
- workers 1 and 3: `none`;
- workers 2 and 4: `low`;
- three queue claims per worker;
- four model attempts per claim;
- twelve distinct records sampled from the same live `todo` queue;
- one shared tree and one serialized BuildLock.

The before snapshot is
`automation/queue/snapshots/queue.20260822-004016.be31d15.jsonl`.
The after snapshot is
`automation/queue/snapshots/queue.20260822-012647.ba995c3.jsonl`.

The fleet stopped naturally. `fleet_stop` then released zero stale claims,
cleared the lock, set HOLD, and reported 294/294 matched records present with
zero lost.

## Generation telemetry

| effort | calls | produced | empty | total seconds | average seconds | forced extractions | stream chars | content tokens | reasoning tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 24 | 24 | 0 | 440.9 | 18.4 | 0 | 86,014 | 7,253 | 0 |
| low | 24 | 18 | 6 | 2,303.1 | 96.0 | 17 | 55,097 | 192 | 51,755 |

Low reasoning was 5.22 times slower and returned no usable content on 25% of
calls. Most of its usable text required the worker's forced-code extraction
path because the model filled `reasoning_content` rather than ordinary content.

## Queue outcomes

| effort | worker | record | outcome | class |
|---|---|---|---|---|
| none | 1 | `us:BOSS/BO0:func_us_801B2690` | escalated | unbalanced braces |
| none | 1 | `us:ST/RNO0:func_us_801C7F24` | near | compiled, bytes differ |
| none | 1 | `us:BOSS/BO0:func_us_801B30AC` | escalated | unbalanced braces |
| none | 3 | `us:BOSS/BO0:func_us_801BB08C` | escalated | unbalanced braces |
| none | 3 | `us:ST/RCEN:func_us_8019C4EC` | escalated | invented Entity ext member |
| none | 3 | `us:BOSS/BO0:func_us_801B001C` | near | compiled, bytes differ |
| low | 2 | `us:ST/RCEN:func_us_8019B6D4` | escalated | undeclared symbols |
| low | 2 | `us:BOSS/BO0:func_us_801B9BEC` | escalated | undeclared symbols and ext member |
| low | 2 | `us:ST/SEL:func_801B9C80` | escalated | raw byte-pointer casts |
| low | 4 | `us:ST/RNO0:func_us_801B7104` | escalated | undeclared symbols |
| low | 4 | `us:BOSS/BO0:func_us_801B76E4` | escalated | invented Entity ext member |
| low | 4 | `us:ST/RCEN:func_us_8019FE9C` | escalated | undeclared symbols |

| effort | compiling near | compiler failure | quality rejection | exact match |
|---|---:|---:|---:|---:|
| none | 2/6 | 0/6 | 4/6 | 0/6 |
| low | 0/6 | 4/6 | 2/6 | 0/6 |

The two near seeds are preserved as immutable generations:

- `automation/candidates/history/us_ST_RNO0_func_us_801C7F24.v0001.c`
- `automation/candidates/history/us_BOSS_BO0_func_us_801B001C.v0001.c`

All rejected candidates and compiler evidence are also retained under
`automation/rejected/history/` and in the after snapshot.

## Decision

No reasoning wins this A/B. It produced every call, used one fifth of the wall
time, and generated both compiling candidates. Low reasoning generated more
analysis text but converted none of its six records into a compiling seed.

This does not prove every no-reasoning sample is easier. Claim order randomizes
rather than pairs functions, and six records per arm is a small sample. It does
show that enabling low reasoning as the production default is not justified:
the direction agrees with the earlier 90-generation quality battery, where
`none` also had the best fabrication rate and lowest time.

The Zen worker default changes to `none`. Explicit `reasoning="low"` remains
available for future experiments and targeted cases. The production harness
continues to own quality gates, builds, candidate preservation, queue reports,
and verification.
