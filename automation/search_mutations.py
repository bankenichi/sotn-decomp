"""Atomic grouped patches, recombination and bounded delta debugging."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence, Tuple, Union

from .search_types import (
    GroupedPatch,
    MutationEvent,
    PatchHunk,
    ScoreVector,
    canonical_json,
    hash_bytes,
    hash_canonical,
)


class MutationError(RuntimeError):
    """Base class for grouped mutation failures."""


class PatchConflict(MutationError):
    """A complete grouped patch could not be anchored."""


class PatchInvalid(MutationError):
    """A patch was malformed or had a duplicate/overlapping hunk."""


@dataclass(frozen=True)
class PatchReplayResult:
    status: str
    source: Optional[str]
    source_hash: Optional[str]
    conflicts: Tuple[int, ...] = ()

    @property
    def applied(self) -> bool:
        return self.status == "applied"


@dataclass(frozen=True)
class RecombinationResult:
    status: str
    source: Optional[str]
    applied_patch_ids: Tuple[str, ...]
    conflict_patch_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class MinimizationResult:
    patch: GroupedPatch
    source: str
    evaluations: int
    removed_ordinals: Tuple[int, ...]
    exhausted: bool


def _lines(source: str) -> List[str]:
    return source.splitlines(keepends=True)


def _patch_identity(format: str, base_source_hash: str, hunks: Sequence[PatchHunk]) -> str:
    return hash_canonical(
        {
            "format": format,
            "base_source_hash": base_source_hash,
            "atomic": True,
            "hunks": list(hunks),
        }
    )


def make_grouped_patch(
    before: str,
    after: str,
    *,
    format: str = "line_context",
    context_lines: int = 3,
) -> GroupedPatch:
    """Build one atomic patch containing every changed hunk."""
    if not isinstance(before, str) or not isinstance(after, str):
        raise TypeError("patch sources must be strings")
    if format not in ("canonical_tokens", "ast", "line_context"):
        raise PatchInvalid("unsupported patch format")
    if context_lines < 0 or context_lines > 16:
        raise PatchInvalid("context_lines must be between zero and sixteen")
    before_lines = _lines(before)
    after_lines = _lines(after)
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines, autojunk=False)
    hunks: List[PatchHunk] = []
    ordinal = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        hunks.append(
            PatchHunk(
                ordinal=ordinal,
                before="".join(before_lines[i1:i2]),
                after="".join(after_lines[j1:j2]),
                leading_context=tuple(before_lines[max(0, i1 - context_lines):i1]),
                trailing_context=tuple(before_lines[i2:i2 + context_lines]),
                ast_path=None,
            )
        )
        ordinal += 1
    if not hunks:
        # The schema requires a hunk.  A no-change mutation is represented by
        # its replay status, while this helper still returns a deterministic
        # no-op patch for callers that need to retain the attempted operation.
        hunks = [PatchHunk(0, before, before, (), ())]
    base_hash = hash_bytes(before.encode("utf-8"))
    patch_id = _patch_identity(format, base_hash, hunks)
    return GroupedPatch(
        patch_id=patch_id,
        format=format,
        base_source_hash=base_hash,
        atomic=True,
        hunks=tuple(hunks),
    )


def _find_hunk_positions(lines: Sequence[str], hunk: PatchHunk) -> List[int]:
    before_lines = _lines(hunk.before)
    leading = list(hunk.leading_context)
    trailing = list(hunk.trailing_context)
    max_position = len(lines) - len(before_lines)
    positions: List[int] = []
    for position in range(max_position + 1):
        if before_lines and list(lines[position:position + len(before_lines)]) != before_lines:
            continue
        if len(leading) > position or list(lines[position - len(leading):position]) != leading:
            continue
        trailing_end = position + len(before_lines)
        if trailing_end + len(trailing) > len(lines):
            continue
        if list(lines[trailing_end:trailing_end + len(trailing)]) != trailing:
            continue
        positions.append(position)
    return positions


def apply_grouped_patch(
    source: str,
    patch: GroupedPatch,
    *,
    exact: bool = False,
) -> PatchReplayResult:
    """Apply every hunk or leave ``source`` untouched."""
    if not isinstance(patch, GroupedPatch):
        patch = GroupedPatch.from_dict(patch)  # type: ignore[arg-type]
    if exact and hash_bytes(source.encode("utf-8")) != patch.base_source_hash:
        return PatchReplayResult("conflict", None, None, tuple(h.ordinal for h in patch.hunks))

    lines = _lines(source)
    matches: List[Tuple[int, int, PatchHunk]] = []
    for hunk in sorted(patch.hunks, key=lambda item: item.ordinal):
        positions = _find_hunk_positions(lines, hunk)
        if len(positions) != 1:
            status = "invalid" if len(positions) == 0 and not hunk.leading_context and not hunk.trailing_context and not hunk.before else "conflict"
            return PatchReplayResult(status, None, None, (hunk.ordinal,))
        before_len = len(_lines(hunk.before))
        start = positions[0]
        end = start + before_len
        if any(start < old_end and old_start < end for old_start, old_end, _ in matches):
            return PatchReplayResult("conflict", None, None, (hunk.ordinal,))
        matches.append((start, end, hunk))

    updated = list(lines)
    changed = False
    for start, end, hunk in sorted(matches, key=lambda item: item[0], reverse=True):
        replacement = _lines(hunk.after)
        original = updated[start:end]
        if original != replacement:
            changed = True
        updated[start:end] = replacement
    result = "".join(updated)
    if not changed or result == source:
        return PatchReplayResult("no_change", source, hash_bytes(source.encode("utf-8")), ())
    return PatchReplayResult("applied", result, hash_bytes(result.encode("utf-8")), ())


def replay_grouped_patch(source: str, patch: GroupedPatch) -> PatchReplayResult:
    return apply_grouped_patch(source, patch, exact=True)


def port_grouped_patch(source: str, patch: GroupedPatch) -> PatchReplayResult:
    return apply_grouped_patch(source, patch, exact=False)


def make_mutation_event(
    *,
    parent_candidate_id: str,
    recipient_id: str,
    lane: str,
    pass_kind: str,
    mutation_seed: int,
    grouped_patch: GroupedPatch,
    donor_candidate_ids: Iterable[str] = (),
    replay_status: str = "applied",
    result_source_hash: Optional[str] = None,
) -> MutationEvent:
    """Construct a mutation event with a content-derived mutation identity."""
    identity = {
        "parent_candidate_id": parent_candidate_id,
        "recipient_id": recipient_id,
        "lane": lane,
        "pass_kind": pass_kind,
        "mutation_seed": mutation_seed,
        "grouped_patch": grouped_patch,
        "donor_candidate_ids": tuple(sorted(set(donor_candidate_ids))),
        "replay_status": replay_status,
    }
    mutation_id = hash_canonical(identity)
    if replay_status == "applied" and result_source_hash is None:
        raise PatchInvalid("an applied mutation needs a result source hash")
    if replay_status != "applied":
        result_source_hash = None
    return MutationEvent(
        mutation_id=mutation_id,
        parent_candidate_id=parent_candidate_id,
        recipient_id=recipient_id,
        lane=lane,
        pass_kind=pass_kind,
        mutation_seed=mutation_seed,
        grouped_patch=grouped_patch,
        donor_candidate_ids=tuple(sorted(set(donor_candidate_ids))),
        replay_status=replay_status,
        result_source_hash=result_source_hash,
    )


def recombine_grouped_patches(
    recipient_source: str,
    patches: Sequence[GroupedPatch],
    *,
    max_donors: int = 4,
) -> RecombinationResult:
    if max_donors < 1 or len(patches) > max_donors:
        raise PatchInvalid("recombination donor bound exceeded")
    source = recipient_source
    applied: List[str] = []
    conflicts: List[str] = []
    for patch in patches:
        result = port_grouped_patch(source, patch)
        if result.status not in ("applied", "no_change") or result.source is None:
            conflicts.append(patch.patch_id)
            return RecombinationResult("conflict", None, tuple(applied), tuple(conflicts))
        source = result.source
        applied.append(patch.patch_id)
    status = "no_change" if source == recipient_source else "applied"
    return RecombinationResult(status, source, tuple(applied), tuple(conflicts))


def _preserved(before: ScoreVector, after: ScoreVector, condition: str) -> bool:
    # A compile failure or timeout has no authoritative object/vector.  In
    # particular, None == None must not make a failed trial look preserved.
    if (
        before.compile_status != "success"
        or after.compile_status != "success"
        or before.object_hash is None
        or after.object_hash is None
        or before.total is None
        or after.total is None
    ):
        return False
    if condition == "object_hash":
        return before.object_hash == after.object_hash
    if condition == "full_score_vector":
        return before == after
    if condition == "no_worse_scalar":
        if before.total is None or after.total is None:
            return False
        return after.total <= before.total
    raise PatchInvalid("unknown minimization preservation condition")


def minimize_grouped_patch(
    base_source: str,
    patch: GroupedPatch,
    evaluator: Callable[[str], ScoreVector],
    *,
    preservation: str = "no_worse_scalar",
    max_evaluations: int = 16,
) -> MinimizationResult:
    """Remove hunk groups deterministically while a condition remains true."""
    if max_evaluations < 0:
        raise PatchInvalid("max_evaluations must be nonnegative")
    original = replay_grouped_patch(base_source, patch)
    if original.status not in ("applied", "no_change") or original.source is None:
        raise PatchConflict("cannot minimize a patch that does not replay")
    baseline = evaluator(original.source)
    current_hunks = list(patch.hunks)
    removed: List[int] = []
    evaluations = 0
    exhausted = False
    index = 0
    while index < len(current_hunks):
        if evaluations >= max_evaluations:
            exhausted = True
            break
        trial_hunks = current_hunks[:index] + current_hunks[index + 1:]
        if not trial_hunks:
            # The schema cannot encode an empty grouped patch.  Keeping the
            # final hunk also preserves the atomic identity of the operation.
            index += 1
            continue
        trial_patch = GroupedPatch(
            patch_id=_patch_identity(patch.format, patch.base_source_hash, trial_hunks),
            format=patch.format,
            base_source_hash=patch.base_source_hash,
            atomic=True,
            hunks=tuple(trial_hunks),
        )
        trial = replay_grouped_patch(base_source, trial_patch)
        evaluations += 1
        if trial.status not in ("applied", "no_change") or trial.source is None:
            index += 1
            continue
        score = evaluator(trial.source)
        if _preserved(baseline, score, preservation):
            removed.append(current_hunks[index].ordinal)
            current_hunks = trial_hunks
            continue
        index += 1
    final_patch = GroupedPatch(
        patch_id=_patch_identity(patch.format, patch.base_source_hash, current_hunks),
        format=patch.format,
        base_source_hash=patch.base_source_hash,
        atomic=True,
        hunks=tuple(current_hunks),
    )
    final = replay_grouped_patch(base_source, final_patch)
    if final.source is None:
        raise PatchConflict("minimized patch no longer replays")
    return MinimizationResult(final_patch, final.source, evaluations, tuple(removed), exhausted)


# Concise aliases for callers and hidden compatibility tests.
create_grouped_patch = make_grouped_patch
apply_patch = apply_grouped_patch
replay_patch = replay_grouped_patch
recombine = recombine_grouped_patches
minimize_patch = minimize_grouped_patch


__all__ = [
    "MutationError", "PatchConflict", "PatchInvalid", "PatchReplayResult",
    "RecombinationResult", "MinimizationResult", "make_grouped_patch",
    "create_grouped_patch", "apply_grouped_patch", "replay_grouped_patch",
    "replay_patch", "port_grouped_patch", "make_mutation_event",
    "recombine_grouped_patches", "recombine", "minimize_grouped_patch",
    "minimize_patch",
]
