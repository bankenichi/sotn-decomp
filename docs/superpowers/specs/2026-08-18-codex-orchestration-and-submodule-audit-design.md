# Codex orchestration and submodule audit design

Date: 2026-08-18
Status: approved by owner direction

## Purpose

Codex is the active orchestrator and maintainer for this standalone fork. The
previous Claude plan remains useful historical evidence and must be archived,
not deleted or silently rewritten. The replacement must use Codex models only,
keep the root agent responsible for every stateful operation, and measure model
capabilities before assigning production roles.

This project does not open pull requests. External repositories are reference
corpora and dependency sources. When a dependency must diverge, vendoring is
preferred over maintaining an upstream contribution workflow.

## Archive boundary

Preserve these materials under `docs/archive/claude-orchestration/`:

- the current `ORCHESTRATOR.md` as `ORCHESTRATOR.md`
- `.codex/agents/sotn-match-closer.toml` under `agents/`
- `.codex/agents/sotn-mechanical-loop.toml` under `agents/`

The archive is immutable historical context. New instructions must not be
patched into the archived copies. A short archive README records why they were
superseded and points to the active root `ORCHESTRATOR.md`.

## Active orchestration

The root agent owns all stateful work:

- connector calls that build or write
- Git staging, commits, branch changes, and pushes
- queue claims, reports, snapshots, and restores
- final verification through the 81-artifact oracle
- roadmap and knowledge-base updates

Subagents never build and never run Git. They receive bounded, read-only tasks
whose outputs are evidence or candidate reasoning. The root agent validates all
subagent conclusions against the connector and the binary oracle.

The provisional model roles are:

- Luna: fast corpus searches, consistency checks, mechanical classification,
  and narrow evidence extraction
- Terra: codebase exploration, twin comparison, candidate review, and ordinary
  static C or assembly reasoning
- Sol: hard compiler reasoning, architecture, adversarial review, and the last
  static-analysis pass before root-agent execution

These are hypotheses, not permanent assignments.

## Capability benchmark

Before productive delegation, Sol, Terra, and Luna receive the same three
read-only benchmark classes:

1. Identify a struct or member-layout failure from a saved rejected candidate.
2. Diagnose a compiler-control-flow mismatch from a previously solved case.
3. Audit a connector or documentation surface for drift against authoritative
   code.

Known historical outcomes provide the answer key but are withheld from the
agents. The root scores each result on factual correctness, evidence quality,
invented claims, adherence to repository constraints, wall time, and context
cost. A model is assigned a role only where it is reliable enough to save root
work. A failed benchmark is recorded as useful capability evidence, not hidden.

## Submodule audit connector

Add two read-only tools to `sotn-cmd`:

- `git_submodule_state(path)`: run porcelain-v2 status inside one declared
  submodule
- `git_submodule_diff(path, staged=False, stat=False)`: show its working-tree or
  staged diff, optionally as a stat

The path must exactly match a path declared in `.gitmodules`, must resolve
inside the repository, and must exist as a directory. The command shape is
fixed and no ref, remote, or arbitrary Git argument is accepted.

These tools reveal local dependency work without creating an upstream workflow.
After inspection, intentional divergence can be moved toward vendoring in a
separate recorded task. Generated dirt can be archived or removed only after
its provenance is understood.

## Error handling and safety

- Invalid or undeclared submodule paths fail before process creation.
- The connector remains fail-closed in dry-run mode.
- No generic shell or generic Git passthrough is introduced.
- Existing dirty files are never swept into a commit.
- Every file is staged with an individual `git_add` call.
- Superseded material is archived. Deletion is reserved for generated material
  whose provenance and recoverability have been established.

## Verification

The implementation is complete only when:

- connector surface tests cover both new actions and path rejection
- the MCP decorator surface and manifest agree
- the automation self-tests pass
- the new tools inspect both currently dirty submodules
- `make_build` completes through the managed job system
- `verify_build` returns 81/81
- roadmap outcomes name the archive, connector gap, and model benchmark state

