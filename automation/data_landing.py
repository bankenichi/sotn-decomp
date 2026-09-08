"""Prepare and land calibrated shared data through the existing build authority."""
from __future__ import annotations

import json
from pathlib import Path
import re

from .data_search import DataSearchError, _file, _load_single, verify
from .search_archive import ContentAddressedArchive
from .search_types import ArtifactRef, hash_canonical, hash_bytes


def _splice_config(raw, start, end, stem, section="data"):
    lines = raw.decode("utf-8").splitlines(keepends=True)
    marker = re.compile(r"^(\s*)-\s*\[\s*(0x[0-9a-fA-F]+|[0-9]+)\s*,\s*([^,\]]+)")
    entries = [(i, int(m[2], 0), m[1], m[3].strip()) for i, line in enumerate(lines)
               if (m := marker.match(line))]
    containing = [row for row in entries if row[1] <= start]
    if not containing:
        raise DataSearchError("candidate lacks a config range")
    anchor = max(containing, key=lambda row: (row[1], row[0]))
    if anchor[3] != section:
        raise DataSearchError("data preparation requires an unnamed data owner")
    newline = "\r\n" if "\r\n" in raw.decode() else "\n"
    additions = [(start, "." + section + ", " + stem)]
    if not any(offset == end for _, offset, _, _ in entries):
        additions.append((end, section))
    insert = "".join(f"{anchor[2]}- [0x{offset:X}, {kind}]{newline}" for offset, kind in additions)
    lines.insert(anchor[0] + 1, insert)
    return "".join(lines).encode()


def prepare(repo: Path, root: Path):
    result = verify(root)
    archive = ContentAddressedArchive(root)
    if (archive.artifacts_root / "preparations").exists():
        intent = _load_single(archive, "preparations")
        validate_preparation(intent, result, archive)
        return intent
    request = _load_single(archive, "requests")
    if request["version"] != "us" or request["section"] != "data" or not request["target"].startswith("st"):
        raise DataSearchError("shared-header landing currently requires US stage data")
    candidates = [c for c in result["candidates"] if c["eligible_for_preparation"]]
    if len(candidates) != 1 or candidates[0]["range"]["ownership"] != "inferred":
        raise DataSearchError("preparation requires one unowned calibrated byte range")
    candidate = candidates[0]
    stage, stem = request["target"][2:], request["stem"]
    source_path, header_path = f"src/st/{stage}/{stem}.c", f"src/st/{stem}.h"
    source = _file(repo, source_path).read_bytes()
    header = _file(repo, header_path).read_bytes()
    from .shim_sweep import defined_functions
    stubs = re.findall(r'INCLUDE_ASM\("([^"\n]+)",\s*([A-Za-z_][A-Za-z0-9_]*)\);', source.decode())
    if not stubs or any(path != f"st/{stage}/nonmatchings/{stem}" for path, _ in stubs):
        raise DataSearchError("source lacks exact same-stem assembly stubs")
    functions = [fn for _, fn in stubs]
    if not set(functions).issubset(defined_functions(header.decode())):
        raise DataSearchError("shared header does not implement every source stub")
    stripped = re.sub(r'/\*[\s\S]*?\*/|//[^\n]*', '', source.decode())
    stripped = re.sub(r'INCLUDE_ASM\([^;]+;', '', stripped)
    stripped = re.sub(r'^\s*#include\s+"' + re.escape(stage) + r'\.h"\s*$', '', stripped, flags=re.M)
    if stripped.strip():
        raise DataSearchError("shared-header preparation would replace unrelated source")
    after_source = re.sub(r'INCLUDE_ASM\([^;]+;\s*', '', source.decode()).rstrip() + f'\n\n#include "../{stem}.h"\n'
    config_path = f"config/splat.us.{request['target']}.yaml"
    snapshot = next(s for s in request["snapshots"] if s["config_path"] == config_path)
    config = archive.verify(ArtifactRef.from_dict(snapshot["config"]))
    if _file(repo, config_path).read_bytes() != config:
        raise DataSearchError("target config changed since discovery")
    after_config = _splice_config(config, candidate["range"]["start"], candidate["range"]["end"], stem)
    from .data_dependencies import capture, derive
    dependencies = capture(repo, request, archive, functions, header)
    closure = derive(request, dependencies, archive)
    for table in closure["tables"]:
        after_config = _splice_config(after_config, table["start"], table["end"], stem, "rodata")
    modifications = [(source_path, source, after_source.encode()), (config_path, config, after_config)]
    if closure["aliases"]:
        original_symbols = archive.verify(ArtifactRef.from_dict(dependencies["symbols"]))
        additions = "\n" + "".join(f"{a['name']} = 0x{a['address']:08X};\n" for a in closure["aliases"])
        modifications.append((dependencies["symbols_path"], original_symbols, original_symbols + additions.encode()))
    from .search_full_oracle import capture_binding
    binding = capture_binding(repo)
    # Data preparation and its parser are part of immutable execution authority.
    dependency_paths = [item["path"] for entry in dependencies["entries"] for item in entry["files"]]
    for rel in ("automation/data_search.py", "automation/data_landing.py", "automation/data_dependencies.py",
                "automation/shim_sweep.py", header_path, dependencies["symbols_path"], *dependency_paths):
        content = _file(repo, rel).read_bytes()
        if rel not in {item["path"] for item in binding["files"]}:
            binding["files"].append({"path": rel, "content_hash": hash_bytes(content), "byte_size": len(content)})
    intent = {"protocol": "sotn-data-landing-v1", "request_identity": result["request_identity"],
              "candidate_id": candidate["candidate_id"], "binding": binding,
              "dependencies": dependencies,
              "records": [f"us:ST/{stage.upper()}:{fn}" for fn in functions],
              "changes": [{"path": path,
                           "before": archive.put_bytes(before, category="before").to_dict(),
                           "after": archive.put_bytes(after, category="after").to_dict()}
                          for path, before, after in modifications]}
    validate_preparation(intent, result, archive)
    archive.put_json(intent, category="preparations")
    return intent


def validate_preparation(intent, result, archive):
    request = _load_single(archive, "requests")
    fields = {"protocol", "request_identity", "candidate_id", "binding", "records", "changes"}
    if (set(intent) not in (fields, fields | {"dependencies"})
            or intent["protocol"] != "sotn-data-landing-v1"
            or intent["request_identity"] != result["request_identity"]
            or request["version"] != "us" or request["section"] != "data"
            or not request["target"].startswith("st")):
        raise DataSearchError("preparation is not bound to data request")
    candidates = [c for c in result["candidates"] if c["eligible_for_preparation"]]
    if len(candidates) != 1 or candidates[0]["candidate_id"] != intent["candidate_id"]:
        raise DataSearchError("preparation differs from the unique calibrated candidate")
    candidate = candidates[0]
    stage, stem = request["target"][2:], request["stem"]
    paths = [f"src/st/{stage}/{stem}.c", f"config/splat.us.{request['target']}.yaml"]
    closure = {"aliases": [], "tables": []}
    if "dependencies" in intent:
        from .data_dependencies import derive
        closure = derive(request, intent["dependencies"], archive)
        if intent["dependencies"]["symbols_path"] != f"config/symbols.us.{request['target']}.txt":
            raise DataSearchError("dependency symbols path differs from target")
        if closure["aliases"]:
            paths.append(intent["dependencies"]["symbols_path"])
    if [c["path"] for c in intent["changes"]] != paths:
        raise DataSearchError("preparation changes unrelated paths")
    contents = []
    for change in intent["changes"]:
        if set(change) != {"path", "before", "after"}:
            raise DataSearchError("preparation change fields differ")
        contents.append(tuple(archive.verify(ArtifactRef.from_dict(change[key])) for key in ("before", "after")))
    source, config = contents[:2]
    expected_source = (re.sub(r'INCLUDE_ASM\([^;]+;\s*', '', source[0].decode()).rstrip()
                       + f'\n\n#include "../{stem}.h"\n').encode()
    expected_config = _splice_config(config[0], candidate["range"]["start"], candidate["range"]["end"], stem)
    for table in closure["tables"]:
        expected_config = _splice_config(expected_config, table["start"], table["end"], stem, "rodata")
    if closure["aliases"]:
        symbols = archive.verify(ArtifactRef.from_dict(intent["dependencies"]["symbols"]))
        additions = "\n" + "".join(f"{a['name']} = 0x{a['address']:08X};\n" for a in closure["aliases"])
        if contents[2] != (symbols, symbols + additions.encode()):
            raise DataSearchError("dependency symbol edits differ from calibrated contexts")
    if source[1] != expected_source or config[1] != expected_config:
        raise DataSearchError("preparation changed outside the derived header/range edits")
    expected_records = [f"us:ST/{stage.upper()}:{fn}" for fn in re.findall(
        r'INCLUDE_ASM\("[^"\n]+",\s*([A-Za-z_][A-Za-z0-9_]*)\);', source[0].decode())]
    if not expected_records or intent["records"] != expected_records:
        raise DataSearchError("preparation recipient records differ")
    snapshot = next(s for s in request["snapshots"] if s["config_path"] == paths[1])
    if config[0] != archive.verify(ArtifactRef.from_dict(snapshot["config"])):
        raise DataSearchError("preparation config differs from captured target")
    from .search_full_oracle import validate_binding
    validate_binding(intent["binding"], hash_canonical(intent["binding"]))


def land(repo: Path, root: Path):
    """One journaled attempt. A durable unfinished attempt is never retried blindly."""
    from .search_full_oracle import _supervisor, _worker
    from . import scheduler
    from types import SimpleNamespace
    intent = prepare(repo, root)
    archive = ContentAddressedArchive(root)
    identity = hash_canonical(intent)
    owner = "data-search:" + root.name
    ps, wd = _supervisor(), _worker(repo)
    changes = intent["changes"]
    before = {c["path"]: archive.verify(ArtifactRef.from_dict(c["before"])) for c in changes}
    after = {c["path"]: archive.verify(ArtifactRef.from_dict(c["after"])) for c in changes}

    def report_terminal(terminal):
        expected = after if terminal["matched"] else before
        for path, raw in expected.items():
            if _file(repo, path).read_bytes() != raw:
                raise DataSearchError("terminal data landing source/config differs; recovery required")
        marker = "data-oracle:" + identity
        for rid in intent["records"]:
            records = scheduler.Queue()._read()
            rec = next(r for r in records if r["id"] == rid)
            status = "matched" if terminal["matched"] else rec.get("claimed_from", "todo")
            if rec["status"] == status and marker in (rec.get("notes") or ""):
                continue
            if rec["status"] != "claimed" or rec.get("claimed_by") != owner:
                raise DataSearchError("data landing no longer owns queue claim")
            response = ps.report(rid, status, marker + "; " + terminal["detail"],
                                 proof=terminal["detail"] if terminal["matched"] else None,
                                 score=0 if terminal["matched"] else None)
            if response.startswith("QUEUE WRITE FAILED"):
                raise DataSearchError(response)

    with ps._build_lock()():
        if (archive.artifacts_root / "data-oracles").exists():
            terminal = _load_single(archive, "data-oracles")
            if (set(terminal) != {"protocol", "preparation_identity", "matched", "detail", "records"}
                    or terminal["protocol"] != "sotn-data-oracle-v1"
                    or terminal["preparation_identity"] != identity
                    or type(terminal["matched"]) is not bool
                    or terminal["records"] != intent["records"]
                    or not isinstance(terminal["detail"], str) or not terminal["detail"]):
                raise DataSearchError("terminal data oracle differs from preparation")
            report_terminal(terminal)
            return terminal
        if (archive.artifacts_root / "data-attempts").exists():
            raise DataSearchError("unfinished data oracle attempt requires journal recovery; not retried")
        for item in intent["binding"]["files"]:
            if hash_bytes(_file(repo, item["path"]).read_bytes()) != item["content_hash"]:
                raise DataSearchError("data landing inputs changed after preparation")
        if any(_file(repo, path).read_bytes() != raw for path, raw in before.items()):
            raise DataSearchError("data landing destination changed after preparation")

        def reserve(records):
            chosen = [r for r in records if r["id"] in intent["records"]]
            if len(chosen) != len(intent["records"]) or any(r["status"] != "todo" for r in chosen):
                raise DataSearchError("data landing needs every exact recipient unclaimed todo")
            for rec in chosen:
                scheduler._take(records, rec, SimpleNamespace(worker=owner, worktree=False))
            return records, {"reserved": list(intent["records"])}
        scheduler._require_queue_owner("next")
        scheduler.Queue().transaction(reserve)
        archive.put_json({"preparation_identity": identity}, category="data-attempts")
        originals = {path: raw.decode() for path, raw in before.items()}
        if not wd.journal_write_many(originals):
            raise DataSearchError("could not journal data landing originals")
        try:
            for path, raw in after.items():
                _file(repo, path).write_bytes(raw)
            record = {"build": "us", "overlay": "st/" + intent["records"][0].split(":")[1].split("/")[1].lower(),
                      "function": intent["records"][0].split(":")[2], "id": intent["records"][0]}
            ok, detail = wd.build_and_check(record)
            if ok:
                ok, detail = ps.verify_checksums("us")
            if not ok:
                wd.restore_many(originals)
                if any(_file(repo, path).read_bytes() != raw for path, raw in before.items()):
                    raise DataSearchError("data landing rollback differs")
                baseline_ok, baseline_detail = wd.build_and_check(record)
                if baseline_ok:
                    baseline_ok, baseline_detail = ps.verify_checksums("us")
                if not baseline_ok:
                    raise DataSearchError("restored baseline oracle failed: " + baseline_detail)
            terminal = {"protocol": "sotn-data-oracle-v1", "preparation_identity": identity,
                        "matched": ok, "detail": detail, "records": intent["records"]}
            archive.put_json(terminal, category="data-oracles")
            if not wd.journal_clear():
                raise DataSearchError("data landing journal could not be disarmed")
        except BaseException:
            if not (archive.artifacts_root / "data-oracles").exists():
                wd.restore_many(originals)
            raise
        report_terminal(terminal)
        return terminal
