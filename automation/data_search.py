#!/usr/bin/env python3
"""Calibrated data-byte search with immutable inputs and archive-only replay.

This runtime owns data ranges, not function CandidateRecords. Equal bytes are
search evidence; only a subsequent configured full oracle can prove a landing.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.search_archive import ContentAddressedArchive
from automation.search_types import ArtifactRef, canonical_bytes, hash_bytes, hash_canonical

ROOT = Path(__file__).resolve().parents[1]
STORE = Path("nonmatchings/search-evidence/data-runs")
PROTOCOL = "sotn-data-search-v1"
VERSIONS = ("us", "hd", "pspeu", "saturn")
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]{0,79}\Z")


class DataSearchError(ValueError):
    """Invalid input, conflicting ownership or unverified data evidence."""


@dataclass(frozen=True)
class DataScore:
    mismatched_bytes: int
    mismatched_bits: int
    missing_bytes: int
    extra_bytes: int
    first_difference: int | None

    @property
    def exact(self):
        return not (self.mismatched_bytes or self.missing_bytes or self.extra_bytes)


def score_bytes(candidate: bytes, target: bytes) -> DataScore:
    differences = [i for i, (a, b) in enumerate(zip(candidate, target)) if a != b]
    first = differences[0] if differences else (
        min(len(candidate), len(target)) if len(candidate) != len(target) else None
    )
    return DataScore(len(differences), sum((a ^ b).bit_count() for a, b in zip(candidate, target)),
                     max(0, len(target) - len(candidate)), max(0, len(candidate) - len(target)), first)


def _name(value, label):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise DataSearchError(f"invalid {label}")
    return value


def _file(repo: Path, relative: str) -> Path:
    if not isinstance(relative, str) or "\\" in relative:
        raise DataSearchError("invalid input path")
    rel = Path(relative)
    if rel.is_absolute() or any(p in ("..", ".git") for p in rel.parts) or ":" in relative:
        raise DataSearchError("input path escapes repository")
    path = repo / rel
    current = repo
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            raise DataSearchError("input path must not be a symlink")
    path.resolve().relative_to(repo.resolve())
    return path


def ranges(document: dict, size: int) -> list[dict]:
    """Use explicit ROM boundaries; never treat BSS or code as owned data.

    Duplicate zero-size markers occur in real splat files. Named ownership at
    the same offset wins over a generic marker; two named owners are refused.
    Nested segment formats are deliberately rejected until their ROM mapping
    is implemented, rather than interpreting their addresses as file offsets.
    """
    groups = document.get("segments")
    if not isinstance(groups, list):
        raise DataSearchError("config has no segment list")
    boundaries = {size}
    records = []
    for group in groups:
        if isinstance(group, list):
            if group and type(group[0]) is int:
                boundaries.add(group[0])
            continue
        if not isinstance(group, dict):
            raise DataSearchError("unsupported segment format")
        start = group.get("start")
        if type(start) is not int:
            raise DataSearchError("segment has no explicit ROM offset")
        boundaries.add(start)
        vram = group.get("vram")
        for entry in group.get("subsegments", []):
            if not isinstance(entry, list) or len(entry) < 2 or type(entry[0]) is not int:
                raise DataSearchError("unsupported nested subsegment format")
            offset, kind = entry[:2]
            boundaries.add(offset)
            if kind not in ("data", ".data", "rodata", ".rodata"):
                continue
            if not 0 <= offset < size:
                raise DataSearchError("data offset outside binary")
            owner = entry[2] if len(entry) >= 3 else None
            if owner is not None and not isinstance(owner, str):
                raise DataSearchError("data owner is not text")
            records.append({"start": offset, "section": kind.lstrip("."), "owner": owner,
                            "vram": vram + offset - start if type(vram) is int else None})
    output = []
    ordered = sorted(boundaries)
    for offset in sorted({row["start"] for row in records}):
        at_offset = [row for row in records if row["start"] == offset]
        named = [row for row in at_offset if row["owner"] is not None]
        selected = named or at_offset
        if len({canonical_bytes(row) for row in selected}) != 1:
            raise DataSearchError("conflicting data range owners")
        row = dict(selected[0])
        row["end"] = next(bound for bound in ordered if bound > offset)
        if row["end"] > size:
            raise DataSearchError("data end outside binary")
        output.append(row)
    return output


def _snapshot(repo, path, archive):
    raw = path.read_bytes()
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict):
        raise DataSearchError("config is not a mapping")
    target = doc.get("options", {}).get("target_path")
    expected = doc.get("sha1")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise DataSearchError("config has no exact binary SHA-1")
    binary = _file(repo, target).read_bytes()
    if hashlib.sha1(binary).hexdigest() != expected:
        raise DataSearchError("original binary differs from configured SHA-1")
    spans = ranges(doc, len(binary))
    return {"config_path": path.relative_to(repo).as_posix(), "binary_path": target,
            "config": archive.put_bytes(raw, category="configs", suffix=".yaml").to_dict(),
            "binary": archive.put_bytes(binary, category="binaries", suffix=".bin").to_dict(),
            "sha1": expected, "ranges": spans}


def _verified_snapshot(snapshot, archive):
    expected_fields = {"config_path", "binary_path", "config", "binary", "sha1", "ranges"}
    if not isinstance(snapshot, dict) or set(snapshot) != expected_fields:
        raise DataSearchError("snapshot fields differ")
    raw = archive.verify(ArtifactRef.from_dict(snapshot["config"]))
    binary = archive.verify(ArtifactRef.from_dict(snapshot["binary"]))
    doc = yaml.safe_load(raw)
    if (doc.get("sha1") != snapshot["sha1"]
            or hashlib.sha1(binary).hexdigest() != snapshot["sha1"]
            or doc.get("options", {}).get("target_path") != snapshot["binary_path"]
            or ranges(doc, len(binary)) != snapshot["ranges"]):
        raise DataSearchError("snapshot disagrees with archived config or binary")
    return binary


def _hits(binary, needle, allowed):
    output = []
    for span in allowed:
        pos = binary.find(needle, span["start"], span["end"])
        while pos != -1:
            output.append(pos)
            if len(output) == 256:
                return output, True
            pos = binary.find(needle, pos + 1, span["end"])
    return sorted(set(output)), False


def derive(request, archive):
    """Re-derive candidates and dispositions exclusively from frozen inputs."""
    if set(request) != {"protocol", "version", "target", "stem", "section", "tool",
                        "snapshots", "excluded"} or request["protocol"] != PROTOCOL:
        raise DataSearchError("request schema differs")
    if request["version"] not in VERSIONS or request["section"] not in ("data", "rodata"):
        raise DataSearchError("request platform or section differs")
    _name(request["target"], "target")
    _name(request["stem"], "stem")
    archive.verify(ArtifactRef.from_dict(request["tool"]))
    snapshots = request["snapshots"]
    paths = [s["config_path"] for s in snapshots]
    if paths != sorted(set(paths)):
        raise DataSearchError("snapshot inventory must be unique and sorted")
    target_path = f"config/splat.{request['version']}.{request['target']}.yaml"
    targets = [s for s in snapshots if s["config_path"] == target_path]
    if len(targets) != 1:
        raise DataSearchError("request lacks exact target snapshot")
    binaries = {s["config_path"]: _verified_snapshot(s, archive) for s in snapshots}
    target = targets[0]
    binary = binaries[target_path]
    allowed = [span for span in target["ranges"] if span["section"] == request["section"]
               and span["owner"] in (None, request["stem"])]
    groups = {}
    for snapshot in snapshots:
        if snapshot is target:
            continue
        for span in snapshot["ranges"]:
            if span["section"] != request["section"] or span["owner"] != request["stem"]:
                continue
            donor = binaries[snapshot["config_path"]][span["start"]:span["end"]]
            groups.setdefault(donor, []).append({"config_path": snapshot["config_path"],
                "binary_identity": snapshot["binary"]["content_hash"], "range": span})
    candidates, dispositions = [], []
    for donor, origins in sorted(groups.items(), key=lambda pair: hash_bytes(pair[0])):
        origins.sort(key=lambda o: (o["config_path"], o["range"]["start"]))
        identity = hash_bytes(donor)
        calibrated = len({o["binary_identity"] for o in origins}) >= 2
        status = "calibrated" if calibrated else "insufficient_independent_peers"
        if len(donor) < 8 or len(set(donor)) < 3:
            status = "non_distinctive_pattern"
        hits, truncated = _hits(binary, donor, allowed) if status == "calibrated" else ([], False)
        if status == "calibrated":
            status = "ambiguous" if len(hits) > 1 or truncated else "unique" if hits else "no_hit"
        dispositions.append({"candidate_bytes": identity, "origins": origins, "status": status,
                             "hits": hits, "hits_truncated": truncated})
        # Preserve measurements for a known owned segment even when the peer
        # serialization differs; near scores never authorize an inferred range.
        owned = [span for span in allowed if span["owner"] == request["stem"]]
        measured = [(span["start"], span["end"], "declared") for span in owned]
        measured += [(pos, pos + len(donor), "inferred") for pos in hits
                     if not any(span["start"] == pos and span["end"] == pos + len(donor) for span in owned)]
        for start, end, ownership in measured:
            score = score_bytes(donor, binary[start:end])
            candidate = {"bytes_identity": identity, "serialized_hex": donor.hex(), "origins": origins,
                         "target_binary_identity": target["binary"]["content_hash"],
                         "range": {"start": start, "end": end, "ownership": ownership},
                         "section": request["section"], "stem": request["stem"],
                         "score": asdict(score), "exact": score.exact,
                         "eligible_for_preparation": score.exact and status == "unique"}
            candidate["candidate_id"] = hash_canonical(candidate)
            candidates.append(candidate)
    candidates.sort(key=lambda c: c["candidate_id"])
    return {"protocol": PROTOCOL, "request_identity": hash_canonical(request),
            "candidates": candidates, "dispositions": dispositions,
            "funnel": {"snapshots": len(snapshots), "excluded_configs": len(request["excluded"]),
                       "unique_patterns": len(groups), "calibrated_patterns": sum(
                           d["status"] in ("unique", "ambiguous", "no_hit") for d in dispositions),
                       "measured": len(candidates), "exact": sum(c["exact"] for c in candidates),
                       "eligible": sum(c["eligible_for_preparation"] for c in candidates)},
            "landing_status": "not_attempted"}


def _load_single(archive, category):
    directory = archive.artifacts_root / category
    if directory.is_symlink():
        raise DataSearchError("receipt directory must not be a symlink")
    paths = list(directory.glob("*.json"))
    if len(paths) != 1 or paths[0].is_symlink():
        raise DataSearchError(f"expected one immutable {category} receipt")
    raw = paths[0].read_bytes()
    if paths[0].stem != hash_bytes(raw).split(":")[1]:
        raise DataSearchError("receipt filename differs from content")
    document = json.loads(raw)
    if canonical_bytes(document) != raw:
        raise DataSearchError("receipt is not canonical")
    return document


def verify(root):
    archive = ContentAddressedArchive(root)
    request = _load_single(archive, "requests")
    result = _load_single(archive, "results")
    if result != derive(request, archive):
        raise DataSearchError("result differs from independently replayed data search")
    return result


def search(repo, run_id, *, version, target, stem, section="data"):
    from automation.search_supervisor import SupervisorLease
    _name(run_id, "run id")
    root = _file(repo, (STORE / run_id).as_posix())
    with SupervisorLease(mode="instrumented", run_id=run_id, record_ids=(),
                         path=root / "ownership.json"):
        return _search_held(repo, run_id, version=version, target=target, stem=stem, section=section)


def _search_held(repo, run_id, *, version, target, stem, section="data"):
    _name(run_id, "run id")
    _name(target, "target")
    _name(stem, "stem")
    if version not in VERSIONS or section not in ("data", "rodata"):
        raise DataSearchError("unsupported version or section")
    root = _file(repo, (STORE / run_id).as_posix())
    archive = ContentAddressedArchive(root)
    if (archive.artifacts_root / "requests").exists():
        request = _load_single(archive, "requests")
        if any(request[key] != value for key, value in
               (("version", version), ("target", target), ("stem", stem), ("section", section))):
            raise DataSearchError("run id already belongs to another request")
    else:
        snapshots, excluded = [], []
        target_path = f"config/splat.{version}.{target}.yaml"
        for path in sorted((repo / "config").glob(f"splat.{version}.*.yaml")):
            try:
                snapshots.append(_snapshot(repo, _file(repo, path.relative_to(repo).as_posix()), archive))
            except (DataSearchError, OSError, yaml.YAMLError) as exc:
                if path.relative_to(repo).as_posix() == target_path:
                    raise DataSearchError(f"target capture failed: {exc}") from exc
                excluded.append({"config_path": path.relative_to(repo).as_posix(),
                                 "reason": type(exc).__name__, "detail": str(exc)})
        request = {"protocol": PROTOCOL, "version": version, "target": target, "stem": stem,
                   "section": section, "snapshots": snapshots, "excluded": excluded,
                   "tool": archive.put_bytes(Path(__file__).read_bytes(), category="tools", suffix=".py").to_dict()}
        derive(request, archive)  # Refuse invalid target inventory before publication.
        archive.put_json(request, category="requests")
    result = derive(request, archive)
    archive.put_json(result, category="results")
    return verify(root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--version", choices=VERSIONS, default="us")
    parser.add_argument("--target")
    parser.add_argument("--stem")
    parser.add_argument("--section", choices=("data", "rodata"), default="data")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--land", action="store_true")
    args = parser.parse_args(argv)
    _name(args.run_id, "run id")
    if sum((args.verify, args.prepare, args.land)) > 1:
        parser.error("select only one of verify, prepare and land")
    if args.prepare or args.land:
        from automation.data_landing import prepare, land
        from automation.search_supervisor import SupervisorLease
        root = _file(ROOT, (STORE / args.run_id).as_posix())
        with SupervisorLease(mode="instrumented", run_id=args.run_id, record_ids=(), path=root / "ownership.json"):
            result = (land if args.land else prepare)(ROOT, root)
        print(json.dumps({"run_id": args.run_id, "receipt_identity": hash_canonical(result),
                          "records": result["records"], "matched": result.get("matched"),
                          "detail": result.get("detail"), "receipt_root": root.as_posix()}, sort_keys=True))
        return 0
    if args.verify:
        result = verify(_file(ROOT, (STORE / args.run_id).as_posix()))
    else:
        if not args.target or not args.stem:
            parser.error("search requires --target and --stem")
        result = search(ROOT, args.run_id, version=args.version, target=args.target,
                        stem=args.stem, section=args.section)
    print(json.dumps({"run_id": args.run_id, "request_identity": result["request_identity"],
                      "funnel": result["funnel"], "landing_status": result["landing_status"],
                      "receipt_root": (STORE / args.run_id).as_posix()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
