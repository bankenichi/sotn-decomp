"""Bounded deterministic permutation strategies with durable evaluation events."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.compiler_corpus import compile_against_object
from automation.search_archive import ContentAddressedArchive
from automation.search_mutations import make_grouped_patch, recombine_grouped_patches, minimize_grouped_patch
from automation.search_types import ArtifactRef, ScoreVector, canonical_bytes, hash_bytes, hash_canonical
from automation.search_source_context import preprocess_for_mutation
from automation.search_process_lock import worker_session_lock, WorkerStillRunning

PROTOCOL = "sotn-permuter-evaluation-v1"
CATEGORY = "permuter-evaluations"
TARGETED_PASSES = frozenset({"perm_temp_for_expr", "perm_reorder_decls", "perm_expand_expr"})


class PhaseComplete(Exception):
    pass


def load_events(archive: ContentAddressedArchive, session_identity: str):
    directory = archive.artifacts_root / CATEGORY
    if directory.is_symlink():
        raise ValueError("permuter event directory must not be a symlink")
    if not directory.exists():
        return []
    events = []
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise ValueError("permuter event archive contains an unexpected entry")
        raw = path.read_bytes()
        reference = ArtifactRef(
            hash_bytes(raw), path.relative_to(archive.run_root).as_posix(), "application/json", len(raw),
        )
        archive.verify(reference)
        event = json.loads(raw)
        if raw != canonical_bytes(event) or event.get("protocol") != PROTOCOL:
            raise ValueError("permuter event is not canonical")
        if event.get("session_identity") == session_identity:
            for key in ("source", "object", "disassembly", "diagnostic"):
                if event.get(key) is not None:
                    archive.verify(ArtifactRef.from_dict(event[key]))
            ScoreVector.from_dict(event["score"])
            events.append((reference, event))
    events.sort(key=lambda item: item[1]["iteration"])
    if [event["iteration"] for _, event in events] != list(range(1, len(events) + 1)):
        raise ValueError("permuter evaluation sequence is not contiguous")
    return events


def execute_strategy(base, mutate, evaluate, *, strategy, operation):
    """Run concrete transformations; scorer choice is independent of strategy."""
    if strategy in {"random", "targeted"}:
        source, mutation = mutate(operation, 0, strategy == "targeted")
        provenance = {"strategy": strategy, "operation": operation, "mutation": mutation}
        evaluate(source, provenance)
        return provenance
    first, first_mutation = mutate(operation, 0, False)
    if strategy == "recombine":
        second, second_mutation = mutate(operation, 1, False)
        patches = (make_grouped_patch(base, first), make_grouped_patch(base, second))
        result = recombine_grouped_patches(base, patches, max_donors=2)
        provenance = {
                "strategy": strategy, "operation": operation,
                "parents": [hash_bytes(first.encode()), hash_bytes(second.encode())],
                "mutations": [first_mutation, second_mutation],
                "patches": [patch.to_dict() for patch in patches],
                "recombination_status": result.status,
                "conflict_patch_ids": list(result.conflict_patch_ids),
            }
        if result.source is not None:
            evaluate(result.source, provenance)
        return provenance
    if strategy == "ddmin":
        patch = make_grouped_patch(base, first)
        provenance = {
            "strategy": strategy, "operation": operation,
            "parent": hash_bytes(first.encode()), "mutation": first_mutation,
            "patch": patch.to_dict(),
        }
        # The callback charges every actual compile, including the baseline.
        # Durable source-local scores let a restarted minimization replay its
        # decisions without recompiling its earlier baseline or trials.
        minimized = minimize_grouped_patch(
            base, patch, lambda source: evaluate(source, provenance),
            preservation="no_worse_scalar", max_evaluations=len(patch.hunks),
        )
        result = {
            **provenance, "removed_ordinals": list(minimized.removed_ordinals),
            "minimized_patch": minimized.patch.to_dict(),
        }
        evaluate(minimized.source, result)
        return result
    raise ValueError("unsupported permutation strategy")


def run(work: Path, run_root: Path) -> dict:
    marker = json.loads((work / "executor-request.json").read_text())
    request = marker["request"]
    session = request["session_identity"]
    archive = ContentAddressedArchive(run_root)
    events = load_events(archive, session)
    if len(events) < request["start_iteration"]:
        raise ValueError("resume is missing durable evaluation events")
    prior = json.loads((work / "prior-state.json").read_text())
    if request["phase"] == "resume":
        expected = prior.get("evaluation_artifacts")
        actual = [ref.to_dict() for ref, _ in events[:request["start_iteration"]]]
        if expected != actual:
            raise ValueError("resume checkpoint differs from durable evaluation prefix")
    cache = {}
    for reference, event in events:
        if (
            event["evaluator_identity"] != request["evaluator_identity"]
            or event["target_identity"] != request["target_identity"]
            or event["strategy"] != request["algorithm"]
        ):
            raise ValueError("permuter event binding differs")
        cache[event["source"]["content_hash"]] = ScoreVector.from_dict(event["score"])

    # Load the verified vendor snapshot, using a fresh candidate and explicit
    # RNG seed for each operation. No mutable random stream survives a task.
    sys.path.insert(0, str(work / "vendor"))
    from src.candidate import Candidate
    from src.perm.eval import perm_evaluate_one
    from src.perm.parse import perm_parse
    from src.perm.perm import EvalState
    from src.randomizer import RANDOMIZATION_PASSES
    import tomllib
    tables = tomllib.loads((work / "vendor/default_weights.toml").read_text())
    weights = {**tables["base"], **tables.get("gcc", {})}
    function = (work / "function.txt").read_text().strip()
    def mutate(operation, donor, targeted):
        seed = int(hash_canonical({
            "session": session, "operation": operation, "donor": donor,
        })[7:23], 16)
        selected = {
            method.__name__: weights[method.__name__]
            if not targeted or method.__name__ in TARGETED_PASSES else 0.0
            for method in RANDOMIZATION_PASSES
        }
        candidate = Candidate.from_source(base, EvalState(), function, selected, rng_seed=seed)
        mutation = candidate.randomizer.randomize(
            candidate.ast, function, seed=seed, max_attempts=64,
        )
        return mutation.after_source, mutation.to_dict()

    phase_limit = (request["max_iterations"] if request["phase"] == "resume" else min(
        request["max_iterations"], request["checkpoint_interval"],
    ))

    def evaluate(source, provenance):
        source_id = hash_bytes(source.encode("utf-8"))
        if source_id in cache:
            return cache[source_id]
        if len(events) >= phase_limit:
            raise PhaseComplete()
        observation = compile_against_object(
            source, (work / "target.o").read_bytes(),
            expected_pipeline_identity=request["evaluator_identity"], symbol=function,
            recipient_id=request["recipient_id"],
        )
        source_ref = archive.put_source(source)
        obj = archive.put_object(observation.object_bytes) if observation.object_bytes is not None else None
        disassembly = archive.put_text(
            observation.disassembly, category="disassembly", suffix=".txt",
        ) if observation.disassembly is not None else None
        diagnostic = archive.put_text(
            observation.diagnostic, category="diagnostics", suffix=".txt",
        ) if observation.diagnostic is not None else None
        score = dict(observation.score)
        score["diagnostic_artifact"] = diagnostic.to_dict() if diagnostic else None
        event = {
            "protocol": PROTOCOL, "session_identity": session,
            "iteration": len(events) + 1,
            "evaluator_identity": request["evaluator_identity"],
            "target_identity": request["target_identity"],
            "strategy": request["algorithm"], "provenance": provenance,
            "source": source_ref.to_dict(), "object": obj.to_dict() if obj else None,
            "disassembly": disassembly.to_dict() if disassembly else None,
            "diagnostic": diagnostic.to_dict() if diagnostic else None,
            "score": score,
        }
        reference = archive.put_json(event, category=CATEGORY)
        events.append((reference, event))
        vector = ScoreVector.from_dict(score)
        cache[source_id] = vector
        print(json.dumps({"evaluation_artifact": reference.to_dict(), "iteration": len(events)}), flush=True)
        return vector

    # Charge and persist the actual input before the randomizer can inspect an
    # invalid typemap. A broken seed is evidence, not an inapplicable strategy.
    seed = (work / "base.c").read_text()
    baseline = evaluate(seed, {"strategy": request["algorithm"], "kind": "seed_baseline"})
    if baseline.compile_status != "success":
        return {
            "completed": False, "status": "refused", "refusal_code": "seed_compile_failed",
            "reason": "archived seed failed target compilation before mutation",
            "evaluation_artifacts": [ref.to_dict() for ref, _ in events],
            "absolute_iterations": len(events),
        }
    preprocessed = preprocess_for_mutation(
        seed, request["recipient_id"], request["evaluator_identity"], work,
    )
    source, state = perm_evaluate_one(perm_parse(preprocessed))
    base = Candidate.from_source(source, state, function, weights, rng_seed=0).get_source()
    completed = True
    try:
        for operation in range(request["max_iterations"]):
            result = execute_strategy(base, mutate, evaluate, strategy=request["algorithm"], operation=operation)
            archive.put_json({
                "protocol": "sotn-permuter-operation-v1", "session_identity": session,
                "operation": operation, "strategy": request["algorithm"],
                "result": result,
            }, category="permuter-operations")
    except PhaseComplete:
        completed = False
    return {
        "completed": completed,
        "evaluation_artifacts": [ref.to_dict() for ref, _ in events],
        "absolute_iterations": len(events),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    marker = json.loads((args.work / "executor-request.json").read_text())
    try:
        with worker_session_lock(args.run_root, marker["request"]["session_identity"]):
            result = run(args.work, args.run_root)
    except WorkerStillRunning as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(75)
    print(json.dumps({"permuter_terminal": result}), flush=True)


if __name__ == "__main__":
    main()
