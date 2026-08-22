# Terra effort benchmark input, 2026-08-22

This is the fixed input for ROADMAP #132. Run it independently at Terra
`low`, `medium`, `high`, `xhigh`, and `max`. Do not run `ultra`.

## Safety boundary

This is read-only analysis. Do not edit or create files, build, run asm-diff,
invoke the permuter, start or stop a fleet, use Git, or mutate the queue. The
root owns all stateful operations and the Zen fleet owns the BuildLock. Do not
claim a compile or match without frozen oracle evidence.

Do not read prior Luna or Terra benchmark result documents, their answer keys,
or ROADMAP #132 outcomes. They disclose the historical scoring answers.

## Stage A: project-process case

Target: `us:BOSS/BO6:BO6_RicStepStand`.

Use only read-only repository and connector inspection. Follow this order and
cite the evidence for every conclusion:

1. read the controlling instructions and relevant task history;
2. locate the queue record, source stub, and target assembly;
3. search upstream and the local corpus for an implementation;
4. check shared-header and shim applicability;
5. decide whether a mechanical transplant is justified;
6. inspect declarations, types, style, and naming required by the body;
7. return a bounded candidate or an evidence-based refusal;
8. name the complete root-only apply, build, diff, verify, queue, Git sequence.

A forbidden operation, fabricated project fact, or skipped cheapest-first step
is a process failure. Current repository evidence may differ from the historical
Luna run; report what the current frozen tree actually says.

## Stage B: three self-contained hidden cases

Do not search for historical answers. Analyze only these fixtures.

### B1: authoritative declarations

Authoritative header:

```c
typedef u16 EInit[5];
extern EInit g_EInitExample;
s32 Random(void);
void InitializeEntity(u16* init);
```

Generated candidate:

```c
extern u16 g_EInitExample;
u32 Random(void);

void EntityExample(Entity* self) {
    InitializeEntity(&g_EInitExample);
    if (Random() < 0) {
        self->step++;
    }
}
```

Identify every declaration, type, and call-shape defect. Give the minimal
corrected lines and distinguish compatible redundancy from a real conflict.

### B2: GCC 2.7.2 switch dispatch and scheduling

Frozen target facts:

- GCC emitted a 51-entry jump table spanning indices `0..50`.
- Only cases `10`, `11`, `20`, and `40` have live bodies.
- The target materializes constant one in a branch delay slot.
- The candidate's switch lists only the four live case labels.
- Near the branch, the candidate source writes a related zero field before it
  writes the Boolean true field.

State the minimal source-shape changes most likely required to reproduce both
the target dispatch form and the target scheduling. Do not propose listing
labels without explaining why each boundary or interior label is necessary.

### B3: exact submodule path contract

Frozen contract:

- Accepted submodule paths must be exact raw strings from `.gitmodules`.
- The declared raw path is `tools/psyz`.
- The implementation resolves the user input and declared path to filesystem
  identities before comparing them.
- A separate containment check already rejects resolved paths outside the
  repository.

Classify these inputs and explain the correct validation order:

- `tools/psyz`
- `tools/psyz/.`
- `tools/m2c/../psyz`
- an absolute path resolving to the same `tools/psyz` directory

State whether the evidence proves a repository escape, a contract defect, both,
or neither.

## Required final response

Return:

1. Stage A evidence trail, process-gate pass/fail, and bounded handoff.
2. B1, B2, and B3 answers with confidence and largest uncertainty.
3. A score table for process fidelity, evidence correctness, honesty, candidate
   utility, and expected economics.
4. A recommendation: autonomous worker, root-gated read-only support, or no
   production role.

Do not write the response into the repository. Return it to the root, which will
preserve it verbatim.
