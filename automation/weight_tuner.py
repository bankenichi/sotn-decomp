#!/usr/bin/env python3
"""Fixed-corpus, bounded compiler trials for later-run scorer weights.

Only completed, verified run observations enter the corpus. Every trial owns
an immutable dataset and seed; neither training nor replay can change holdout
membership. The concrete runner compiles mutations and uses its own weights
to select the next parent. It does not relabel historical scalar scores.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import statistics
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.search_archive import ContentAddressedArchive
from automation.search_types import ArtifactRef, ScoreComponents, ScoreVector, hash_bytes, hash_canonical, canonical_bytes
from automation.data_search import _file, _name, _load_single
from automation.compiler_corpus import DEFAULT_WEIGHTS, compile_against_object, pipeline_identity

ROOT = Path(__file__).resolve().parents[1]
STORE = Path("nonmatchings/search-evidence/weight-tuning")
PROTOCOL = "sotn-weight-tuner-v1"
WEIGHT_KEY = "scorer_weights"


class TuningError(ValueError):
    """Missing, incompatible or incomplete tuning evidence."""


class ReplayArchive(ContentAddressedArchive):
    def put_bytes(self, data, *, category="objects", suffix=".bin", media_type="application/octet-stream"):
        ref = ArtifactRef(hash_bytes(data), f"artifacts/{category}/{hash_bytes(data)[7:]}{suffix}", media_type, len(data))
        self.verify(ref)
        return ref


def runner_binding():
    from automation.search_permuter_executor import vendored_tree_identity
    paths = ("automation/weight_tuner.py", "automation/compiler_corpus.py", "automation/search_types.py")
    return {"protocol": PROTOCOL, "compiler_identity": pipeline_identity().identity,
            "modules": {path: hash_bytes((ROOT / path).read_bytes()) for path in paths},
            "vendor_identity": vendored_tree_identity(ROOT / "tools/decomp-permuter")}


def checked_weights(value):
    result = ScoreComponents.from_dict(value).to_dict()
    if any(v <= 0 or v > 10000 for v in result.values()):
        raise TuningError("all five scorer weights must be between 1 and 10000")
    return result


def split_cases(cases, seed):
    """Union related families, source bytes and targets before a fixed split."""
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise TuningError("split seed must be an unsigned 64-bit integer")
    ids = [c["case_id"] for c in cases]
    if ids != sorted(set(ids)):
        raise TuningError("cases must have sorted unique identities")
    parents = {key: key for key in ids}

    def find(key):
        while parents[key] != key:
            key = parents[key]
        return key

    seen = {}
    for case in cases:
        for token in ("family:" + case["family"], "source:" + case["source"]["content_hash"],
                      "target:" + case["target"]["content_hash"], *case["lineage"]):
            if token in seen:
                first, second = sorted((find(case["case_id"]), find(seen[token])))
                parents[second] = first
            seen[token] = case["case_id"]
    groups = {}
    for key in ids:
        groups.setdefault(find(key), []).append(key)
    ordered = sorted(groups.values(), key=lambda keys: hash_canonical({"seed": seed, "cases": keys}))
    if len(ordered) < 2:
        raise TuningError("tuning requires at least two independent function families; holdout would leak")
    holdout_count = max(1, len(ordered) // 3)
    return {"seed": seed, "groups": ordered,
            "train": sorted(key for group in ordered[holdout_count:] for key in group),
            "holdout": sorted(key for group in ordered[:holdout_count] for key in group)}


def _copy_run(source, destination):
    from automation.search_indexed_runtime import _copy_tree
    from automation.search_patterns import _load_completed_ledger
    verified = _load_completed_ledger(source)
    target = ContentAddressedArchive(destination)
    for name in ("manifest.json", "ledger.jsonl"):
        raw = (source / name).read_bytes()
        path = destination / name
        target._ensure_directory(destination)
        if path.exists() and path.read_bytes() != raw:
            raise TuningError("contributing run snapshot changed")
        if not path.exists():
            # The shared archive writer supplies the durable no-replace boundary.
            _write_once(path, raw)
    _copy_tree(source / "artifacts", destination / "artifacts", label="tuner contributing artifacts")
    copied = _load_completed_ledger(destination)
    if copied.identity != verified.identity:
        raise TuningError("contributing ledger changed during capture")
    return copied


def _write_once(path, raw):
    # Hard-link publication never replaces a raced immutable snapshot.
    import os
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".tuner-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(name, path)
        except FileExistsError:
            if path.read_bytes() != raw:
                raise TuningError("immutable snapshot collision")
    finally:
        os.unlink(name)


def mutation_source(source):
    """Isolate C from top-level assembly, with measurement parity checked later.

    Expanded INCLUDE_ASM statements still read checkout assembly. They cannot
    enter an immutable corpus. Remove only top-level literal asm declarations;
    function-body assembly remains unsupported and is never silently changed.
    """
    tokens = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*[\s\S]*?\*/|//[^\n]*|\b__asm__\b|[{}]')
    declaration = re.compile(r'__asm__\s*\(\s*(?:"(?:\\.|[^"\\])*"\s*)+\)\s*;')
    depth, cursor, pieces = 0, 0, []
    for token in tokens.finditer(source):
        if token.start() < cursor:
            continue
        value = token.group()
        if value == "{":
            depth += 1
        elif value == "}":
            depth -= 1
        elif value == "__asm__":
            match = declaration.match(source, token.start())
            if depth or match is None:
                raise TuningError("corpus source contains unsupported inline assembly")
            pieces.append(source[cursor:token.start()])
            cursor = match.end()
    pieces.append(source[cursor:])
    return "".join(pieces)


def collect_cases(source_roots, archive):
    from automation.search_patterns import _load_completed_ledger
    from automation.search_evaluator import evaluation_receipts, validate_evaluation_receipts
    cases, excluded, sources = [], [], []
    for root in sorted(source_roots):
        run = _load_completed_ledger(root)
        src = ContentAddressedArchive(root)
        validate_evaluation_receipts(run.manifest, src)
        sources.append({"run_id": run.manifest.run_id, "ledger_identity": run.identity,
                        "manifest_identity": hash_canonical(run.manifest.to_dict())})
        # Only coordinator-committed evaluations count; stray worker artifacts
        # left by a failed subprocess cannot be promoted into completed cases.
        committed = {(e.payload.candidate_id, canonical_bytes(e.payload.after.to_dict()))
                     for e in run.events if e.event_type == "evaluation_completed"}
        parent_map = {e.payload.candidate_id: e.payload.parent_candidate_ids
                      for e in run.events if e.event_type == "candidate_materialized"}
        for ref, doc in evaluation_receipts(src):
            binding, score = doc["binding"], ScoreVector.from_dict(doc["score"])
            reason = None
            source_raw = src.verify(ArtifactRef.from_dict(binding["source"]))
            if doc.get("preprocessed_source") is not None:
                source_raw = src.verify(ArtifactRef.from_dict(doc["preprocessed_source"]))
            if (binding["candidate_id"], canonical_bytes(score.to_dict())) not in committed:
                reason = "not_committed_evaluation"
            elif score.compile_status != "success" or doc["object"] is None:
                reason = "not_successfully_compiled"
            elif re.search(rb"^\s*#\s*include\b", source_raw, re.M):
                reason = "requires_archived_preprocessed_context"
            if reason:
                excluded.append({"run_id": run.manifest.run_id, "evaluation": ref.to_dict(), "reason": reason})
                continue
            try:
                source_raw = mutation_source(source_raw.decode()).encode()
            except TuningError as exc:
                excluded.append({"run_id": run.manifest.run_id, "evaluation": ref.to_dict(), "reason": str(exc)})
                continue
            target = src.verify(ArtifactRef.from_dict(binding["target"]))
            object_raw = src.verify(ArtifactRef.from_dict(doc["object"]))
            lineage, pending = set(), [binding["candidate_id"]]
            while pending:
                key = pending.pop()
                if key in lineage:
                    continue
                lineage.add(key)
                pending.extend(parent_map.get(key, ()))
            case = {"recipient": binding["recipient_id"], "symbol": binding["symbol"],
                    "family": binding["symbol"], "lineage": sorted(lineage),
                    "source": archive.put_source(source_raw.decode()).to_dict(),
                    "target": archive.put_object(target).to_dict(),
                    "baseline_object": archive.put_object(object_raw).to_dict(),
                    "baseline_score": score.to_dict(), "source_run": run.manifest.run_id,
                    "source_ledger_identity": run.identity, "evaluation": ref.to_dict(),
                    "compiler_identity": run.manifest.compiler_identity,
                    "evaluator_identity": binding["evaluator_identity"],
                    "config_identity": run.manifest.config_identity,
                    "scorer_algorithm": score.scorer_algorithm}
            case["case_id"] = hash_canonical(case)
            cases.append(case)
    cases = list({c["case_id"]: c for c in cases}.values())
    cases.sort(key=lambda c: c["case_id"])
    identities = {(c["compiler_identity"], c["evaluator_identity"], c["config_identity"], c["scorer_algorithm"],
                   canonical_bytes(c["baseline_score"]["weights"])) for c in cases}
    if len(identities) > 1:
        raise TuningError("contributing observations have incompatible compiler/evaluator/config/scorer identities")
    return cases, excluded, sources


def snapshot_root(container, run_id):
    matches = sorted((container / "nonmatchings").glob(f"*/search-runs/{_name(run_id, 'snapshot run')}"))
    if len(matches) != 1:
        raise TuningError("snapshot must contain one canonical contributing run")
    return matches[0]


def copy_snapshot(source, container):
    destination = container / "nonmatchings" / source.parent.parent.name / "search-runs" / source.name
    _copy_run(source, destination)
    return destination


def build_dataset(repo, root, gate_run, source_runs, seed):
    from automation.search_indexed_runtime import _gate_root, _load_gate
    from automation.search_supervisor import validate_integration_gate
    gate_root, _, gate, _ = _load_gate(repo, gate_run)
    if gate.gate_kind != "multi_record":
        # Use the canonical constant below; historical smoke receipts cannot
        # qualify a corpus merely because they have a valid hash.
        from automation.search_supervisor import GATE_KIND_MULTI_RECORD
        if gate.gate_kind != GATE_KIND_MULTI_RECORD:
            raise TuningError("tuning requires the completed multi-record integration gate")
    gate_copy = copy_snapshot(gate_root, root / "gate")
    validate_integration_gate(gate, archive=ContentAddressedArchive(gate_copy))
    copied = []
    for run_id in sorted(set(source_runs)):
        _name(run_id, "source run")
        destination = copy_snapshot(_gate_root(repo, run_id), root / "sources")
        copied.append(destination)
    archive = ContentAddressedArchive(root)
    cases, excluded, sources = collect_cases(copied, archive)
    collection = {"protocol": PROTOCOL, "gate": gate.to_dict(), "sources": sources,
                  "cases": cases, "excluded": excluded, "split_seed": seed}
    archive.put_json(collection, category="collections")
    split = split_cases(cases, seed)
    dataset = {**collection, "split": split}
    dataset["dataset_id"] = hash_canonical(dataset)
    archive.put_json(dataset, category="datasets")
    return dataset


def verify_dataset(root):
    from automation.search_supervisor import IntegrationGateReceipt, validate_integration_gate
    archive = ContentAddressedArchive(root)
    dataset = _load_single(archive, "datasets")
    payload = {k: v for k, v in dataset.items() if k != "dataset_id"}
    if dataset["dataset_id"] != hash_canonical(payload):
        raise TuningError("dataset identity differs")
    gate = IntegrationGateReceipt.from_dict(dataset["gate"])
    validate_integration_gate(gate, archive=ContentAddressedArchive(snapshot_root(root / "gate", gate.run_id)))
    # Re-collect into a read-only archive facade: existing put operations must
    # find exact bytes, never repair missing evidence during verification.
    class ReadOnlyArchive:
        def put_source(self, source):
            return self._existing(source.encode(), "sources", ".c", "text/x-c")
        def put_object(self, raw):
            return self._existing(raw, "objects", ".o", "application/octet-stream")
        def _existing(self, raw, category, suffix, media):
            ref = ArtifactRef(hash_bytes(raw), f"artifacts/{category}/{hash_bytes(raw)[7:]}{suffix}", media, len(raw))
            archive.verify(ref)
            return ref
    cases, excluded, sources = collect_cases([snapshot_root(root / "sources", s["run_id"])
                                             for s in dataset["sources"]], ReadOnlyArchive())
    if (cases != dataset["cases"] or excluded != dataset["excluded"] or sources != dataset["sources"]
            or split_cases(cases, dataset["split_seed"]) != dataset["split"]):
        raise TuningError("dataset membership or source measurements differ")
    return dataset


def trial_specs(dataset, iterations, seed):
    if type(iterations) is not int or not 1 <= iterations <= 256:
        raise TuningError("iterations must be between 1 and 256")
    configurations = (DEFAULT_WEIGHTS, {"stack": 5, "regalloc": 10, "reordering": 60, "insertion": 100, "deletion": 100},
                      {"stack": 1, "regalloc": 5, "reordering": 20, "insertion": 100, "deletion": 100})
    result = []
    for weights in configurations:
        spec = {"dataset_id": dataset["dataset_id"], "weights": checked_weights(weights),
                "iterations": iterations, "seed": seed, "search": "greedy_ast_mutation_v1"}
        result.append({**spec, "trial_id": hash_canonical(spec)})
    return sorted(result, key=lambda t: t["trial_id"])


def _mutate(source, symbol, seed):
    vendor = ROOT / "tools/decomp-permuter"
    sys.path.insert(0, str(vendor))
    from src.candidate import Candidate
    from src.perm.perm import EvalState
    import tomllib
    table = tomllib.loads((vendor / "default_weights.toml").read_text())
    methods = {**table["base"], **table.get("gcc", {})}
    # The compiler preprocessor includes the assembler macro bootstrap. It is
    # not C syntax and has no AST to mutate; retain its exact bytes around the
    # C mutation, rather than resolving headers again or deleting assembly.
    bootstrap = '__asm__(".include \\"macro.inc\\"\\n");'
    has_bootstrap = bootstrap in source
    parsed_source = source.replace(bootstrap, "") if has_bootstrap else source
    candidate = Candidate.from_source(parsed_source, EvalState(), symbol, methods, rng_seed=seed)
    mutation = candidate.randomizer.randomize(candidate.ast, symbol, seed=seed, max_attempts=64)
    result = (bootstrap + "\n" if has_bootstrap else "") + mutation.after_source
    return result, mutation.to_dict()


def _existing_record(archive, category, identity):
    matches = []
    for path in sorted((archive.artifacts_root / category).glob("*.json")):
        raw = path.read_bytes()
        if path.is_symlink() or path.stem != hash_bytes(raw)[7:]:
            raise TuningError("trial receipt content address differs")
        doc = json.loads(raw)
        if canonical_bytes(doc) != raw:
            raise TuningError("trial receipt is not canonical")
        if doc.get("request_id") == identity:
            matches.append(doc)
    if len(matches) > 1:
        raise TuningError("ambiguous trial handoff")
    return matches[0] if matches else None


def run_trial(trial, dataset, archive, *, replay_only=False):
    results = []
    for case in dataset["cases"]:
        source = archive.verify(ArtifactRef.from_dict(case["source"])).decode()
        target = archive.verify(ArtifactRef.from_dict(case["target"]))
        best, best_source, exact, cost, evidence = None, source, False, 0, []
        common_best = None
        for iteration in range(trial["iterations"]):
            seed = int(hash_canonical({"seed": trial["seed"], "case": case["case_id"], "iteration": iteration})[7:23], 16)
            if iteration:
                source, mutation = _mutate(best_source, case["symbol"], seed)
            else:
                mutation = {"kind": "baseline"}
            source_ref = archive.put_source(source)
            request = {"trial_id": trial["trial_id"], "case_id": case["case_id"],
                       "iteration": iteration, "parent": hash_bytes(best_source.encode()),
                       "source": source_ref.to_dict(), "target": case["target"], "mutation": mutation}
            identity = hash_canonical(request)
            observation = _existing_record(archive, "trial-evaluations", identity)
            if observation is None:
                if replay_only:
                    raise TuningError("trial is missing a completed compiler observation")
                if _existing_record(archive, "trial-requests", identity) is not None:
                    raise TuningError("unfinished compiler request requires recovery; not invoked again")
                archive.put_json({**request, "request_id": identity}, category="trial-requests")
                measured = compile_against_object(source, target, expected_pipeline_identity=case["compiler_identity"],
                                                 symbol=case["symbol"], recipient_id=case["recipient"], weights=trial["weights"])
                obj = archive.put_object(measured.object_bytes) if measured.object_bytes is not None else None
                diagnostic = archive.put_text(measured.diagnostic, category="diagnostics", suffix=".txt") if measured.diagnostic else None
                score = dict(measured.score)
                score["diagnostic_artifact"] = diagnostic.to_dict() if diagnostic else None
                observation = {"request_id": identity, "request": request, "score": score,
                               "object": obj.to_dict() if obj else None, "cost_units": 1}
                archive.put_json(observation, category="trial-evaluations")
            score = ScoreVector.from_dict(observation["score"])
            if (observation["request"] != request or score.weights.to_dict() != trial["weights"]
                    or score.compiler_identity != case["compiler_identity"]
                    or type(observation["cost_units"]) is not int or observation["cost_units"] != 1
                    or (score.compile_status == "success") != (observation["object"] is not None)):
                raise TuningError("trial evaluation binding differs")
            if score.diagnostic_artifact:
                archive.verify(score.diagnostic_artifact)
            if iteration == 0 and "baseline_score" in case:
                original = ScoreVector.from_dict(case["baseline_score"])
                if (score.compile_status != "success" or score.object_hash != original.object_hash
                        or score.components != original.components):
                    raise TuningError("isolated C seed does not reproduce the archived function measurement")
            if observation["object"]:
                obj_raw = archive.verify(ArtifactRef.from_dict(observation["object"]))
                exact = exact or obj_raw == target
                common = score.components.weighted_total(ScoreComponents.from_dict(DEFAULT_WEIGHTS))
                common_best = common if common_best is None else min(common_best, common)
            cost += observation["cost_units"]
            evidence.append(hash_canonical(observation))
            if score.compile_status == "success" and (best is None or score.total < best):
                best, best_source = score.total, source
            if exact or (iteration == 0 and best is None):
                break
        results.append({"case_id": case["case_id"], "best_score": common_best, "search_best_score": best,
                        "exact_rediscovered": exact,
                        "cost_units": cost, "evaluations": evidence})
    result = {"trial": trial, "cases": results}
    archive.put_json(result, category="trials")
    return result


def rank_trials(results, dataset, partition="train"):
    holdout = set(dataset["split"][partition])
    ranked = []
    for result in results:
        rows = [c for c in result["cases"] if c["case_id"] in holdout]
        if {c["case_id"] for c in result["cases"]} != {c["case_id"] for c in dataset["cases"]}:
            raise TuningError("trial has incomplete case coverage")
        values = [c["best_score"] for c in rows if c["best_score"] is not None]
        metrics = {"exact": sum(c["exact_rediscovered"] for c in rows),
                   "median_best": statistics.median(values) if len(values) == len(rows) else None,
                   "cost": sum(c["cost_units"] for c in result["cases"])}
        weight_identity = hash_canonical(result["trial"]["weights"])
        ranked.append(((-metrics["exact"], metrics["median_best"] if metrics["median_best"] is not None else float("inf"),
                        metrics["cost"], weight_identity), result, metrics))
    return sorted(ranked, key=lambda r: r[0])


def tune(repo, run_id, *, gate_run, source_runs, iterations=8, seed=0):
    from automation.search_process_lock import worker_session_lock
    _name(run_id, "tuning run")
    root = _file(repo, (STORE / run_id).as_posix())
    archive = ContentAddressedArchive(root)
    with worker_session_lock(root, hash_canonical({"tuning_run": run_id})):
        if not source_runs or type(iterations) is not int or not 1 <= iterations <= 256:
            raise TuningError("explicit contributing runs and 1..256 iterations are required")
        policy = {"gate_run": gate_run, "source_runs": sorted(set(source_runs)), "iterations": iterations,
                  "seed": seed, "runner": runner_binding()}
        if (archive.artifacts_root / "policies").exists():
            if _load_single(archive, "policies") != policy:
                raise TuningError("tuning run already owns a different frozen policy")
        else:
            archive.put_json(policy, category="policies")
        dataset = (verify_dataset(root) if (archive.artifacts_root / "datasets").exists()
                   else build_dataset(repo, root, gate_run, source_runs, seed))
        if pipeline_identity().identity != dataset["cases"][0]["compiler_identity"]:
            raise TuningError("compiler pipeline changed before trials")
        trials = trial_specs(dataset, iterations, seed)
        results = [run_trial(trial, dataset, archive) for trial in trials]
        ranked = rank_trials(results, dataset)
        selected, metrics = ranked[0][1:]
        weight_document = {"protocol": PROTOCOL, "dataset_id": dataset["dataset_id"],
                           "selected_trial_id": selected["trial"]["trial_id"], "weights": selected["trial"]["weights"],
                           "compiler_identity": dataset["cases"][0]["compiler_identity"],
                           "config_identity": dataset["cases"][0]["config_identity"]}
        weights = archive.put_json(weight_document, category="scorer-weights")
        holdout_metrics = rank_trials([selected], dataset, "holdout")[0][2]
        report = {"protocol": PROTOCOL, "dataset_id": dataset["dataset_id"], "weights": weights.to_dict(),
                  "trials": [hash_canonical(r) for r in results], "metrics": metrics,
                  "holdout_metrics": holdout_metrics,
                  "ranked_trials": [r[1]["trial"]["trial_id"] for r in ranked]}
        archive.put_json(report, category="reports")
        return report


def verify_report(root):
    archive = ReplayArchive(root)
    dataset = verify_dataset(root)
    policy = _load_single(archive, "policies")
    if policy["runner"] != runner_binding():
        raise TuningError("tuner execution tools changed; historical verification requires their pinned runtime")
    trials = trial_specs(dataset, policy["iterations"], policy["seed"])
    results = [run_trial(trial, dataset, archive, replay_only=True) for trial in trials]
    ranked = rank_trials(results, dataset)
    selected, metrics = ranked[0][1:]
    weight_document = {"protocol": PROTOCOL, "dataset_id": dataset["dataset_id"],
                       "selected_trial_id": selected["trial"]["trial_id"], "weights": selected["trial"]["weights"],
                       "compiler_identity": dataset["cases"][0]["compiler_identity"],
                       "config_identity": dataset["cases"][0]["config_identity"]}
    weights = archive.put_json(weight_document, category="scorer-weights")
    expected = {"protocol": PROTOCOL, "dataset_id": dataset["dataset_id"], "weights": weights.to_dict(),
                "trials": [hash_canonical(r) for r in results], "metrics": metrics,
                "holdout_metrics": rank_trials([selected], dataset, "holdout")[0][2],
                "ranked_trials": [r[1]["trial"]["trial_id"] for r in ranked]}
    if _load_single(archive, "reports") != expected:
        raise TuningError("report differs from replayed trial evidence")
    return expected


def load_weights(repo, run_id):
    root = _file(repo, (STORE / _name(run_id, "tuning run")).as_posix())
    report = verify_report(root)
    return json.loads(ContentAddressedArchive(root).verify(ArtifactRef.from_dict(report["weights"])))


def weights_for_run(manifest, archive):
    identity = manifest.tool_identities.get(WEIGHT_KEY)
    if identity is None:
        return dict(DEFAULT_WEIGHTS)
    path = archive.artifacts_root / "scorer-weights" / (identity[7:] + ".json")
    if path.is_symlink():
        raise TuningError("scorer weights must not be a symlink")
    raw = path.read_bytes()
    if hash_bytes(raw) != identity:
        raise TuningError("scorer weights differ from manifest")
    document = json.loads(raw)
    if (canonical_bytes(document) != raw or document["protocol"] != PROTOCOL
            or document["compiler_identity"] != manifest.compiler_identity
            or document["config_identity"] != manifest.config_identity):
        raise TuningError("scorer weights have incompatible compiler/config binding")
    return checked_weights(document["weights"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--gate-run")
    parser.add_argument("--source-run", action="append")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--iterations", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    if args.verify:
        report = verify_report(_file(ROOT, (STORE / _name(args.run_id, "run id")).as_posix()))
    else:
        if not args.gate_run or not args.source_run:
            parser.error("tuning requires --gate-run and --source-run")
        report = tune(ROOT, args.run_id, gate_run=args.gate_run, source_runs=args.source_run,
                      iterations=args.iterations, seed=args.seed)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
