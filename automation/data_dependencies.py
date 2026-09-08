"""Derive shared-header symbol and jump-table ownership from frozen binaries."""
from __future__ import annotations

from difflib import SequenceMatcher
import re
import yaml

from .data_search import DataSearchError, _file
from .search_types import ArtifactRef

ROW = re.compile(r"/\* ([0-9A-Fa-f]+) ([0-9A-Fa-f]+) ([0-9A-Fa-f]{8}) \*/\s+([^\n]+)")
RELOC = re.compile(r"%(hi|lo)\((\w+)\)")


def instructions(raw, binary):
    rows = []
    for offset, address, encoded, text in ROW.findall(raw.decode()):
        if text.startswith("."):
            continue
        offset, address = int(offset, 16), int(address, 16)
        if binary[offset:offset + 4] != bytes.fromhex(encoded):
            raise DataSearchError("dependency assembly differs from original binary")
        normalized = RELOC.sub(r"%\1(SYM)", re.sub(r"\.L\w+", "LABEL", text))
        rows.append((offset, address, text, normalized))
    if not rows or any(b[0] != a[0] + 4 for a, b in zip(rows, rows[1:])):
        raise DataSearchError("dependency function lacks contiguous original instructions")
    return rows


def capture(repo, request, archive, functions, header):
    target_path = f"config/splat.us.{request['target']}.yaml"
    entries = []
    for snapshot in request["snapshots"]:
        config = yaml.safe_load(archive.verify(ArtifactRef.from_dict(snapshot["config"])))
        is_target = snapshot["config_path"] == target_path
        if not is_target and not any(r["owner"] == request["stem"] for r in snapshot["ranges"]):
            continue
        asm_root = config["options"].get("asm_path")
        if not isinstance(asm_root, str):
            continue
        files = []
        for function in functions:
            # Target INCLUDE_ASM explicitly selects nonmatchings. Split output
            # from a restored trial can retain an older matching-side file.
            kinds = ("nonmatchings",) if is_target else ("matchings",)
            matches = [_file(repo, f"{asm_root}/{kind}/{request['stem']}/{function}.s") for kind in kinds]
            matches = [p for p in matches if p.is_file()]
            if len(matches) != 1:
                if is_target:
                    raise DataSearchError("target dependency assembly is ambiguous or absent")
                continue
            path = matches[0]
            files.append({"function": function, "path": path.relative_to(repo).as_posix(),
                          "artifact": archive.put_bytes(path.read_bytes(), category="dependency-asm", suffix=".s").to_dict()})
        if files:
            entries.append({"config_path": snapshot["config_path"], "files": files})
    symbol_path = f"config/symbols.us.{request['target']}.txt"
    raw = _file(repo, symbol_path).read_bytes()
    return {"entries": entries, "header": archive.put_source(header.decode()).to_dict(),
            "symbols_path": symbol_path, "symbols": archive.put_bytes(raw, category="before").to_dict()}


def derive(request, inputs, archive):
    """Require consistent relocation contexts from independent peer binaries.

    These are preparation hypotheses. Only the complete configured checksum
    oracle can accept the resulting source, names and segment ownership.
    """
    snapshots = {s["config_path"]: s for s in request["snapshots"]}
    target_path = f"config/splat.us.{request['target']}.yaml"
    target = snapshots[target_path]
    binary = archive.verify(ArtifactRef.from_dict(target["binary"]))
    header = archive.verify(ArtifactRef.from_dict(inputs["header"])).decode()
    externs = set(re.findall(r"extern\s+[^;()]+?\b([A-Za-z_]\w*)\s*(?:\[[^;]*\])?\s*;", header))
    parsed = {}
    for entry in inputs["entries"]:
        snapshot = snapshots[entry["config_path"]]
        original = archive.verify(ArtifactRef.from_dict(snapshot["binary"]))
        parsed[entry["config_path"]] = {
            item["function"]: instructions(archive.verify(ArtifactRef.from_dict(item["artifact"])), original)
            for item in entry["files"]}
    target_functions = parsed[target_path]
    votes = {}
    for config_path, functions in parsed.items():
        if config_path == target_path:
            continue
        for function, donor_rows in functions.items():
            target_rows = target_functions[function]
            blocks = SequenceMatcher(None, [r[3] for r in donor_rows], [r[3] for r in target_rows], autojunk=False).get_matching_blocks()
            for block in blocks:
                if block.size < 16:
                    continue
                for index in range(block.size):
                    donor, recipient = donor_rows[block.a + index], target_rows[block.b + index]
                    left, right = RELOC.search(donor[2]), RELOC.search(recipient[2])
                    if not left or not right or left[2] not in externs or left[2] == right[2]:
                        continue
                    label = re.fullmatch(r"D_us_([0-9A-Fa-f]{8})", right[2])
                    if label:
                        votes.setdefault(left[2], {}).setdefault(int(label[1], 16), set()).add(snapshot_identity(snapshots[config_path]))
    symbols_raw = archive.verify(ArtifactRef.from_dict(inputs["symbols"]))
    symbols = {name: int(address, 16) for name, address in re.findall(r"^(\w+)\s*=\s*0x([0-9A-Fa-f]+);", symbols_raw.decode(), re.M)}
    aliases = []
    for name, alternatives in sorted(votes.items()):
        if name in symbols:
            continue
        if len(alternatives) != 1 or len(next(iter(alternatives.values()))) < 2:
            raise DataSearchError("dependency symbol lacks independent consistent donor contexts: " + name)
        address = next(iter(alternatives))
        if not any(r["section"] == "data" and r["vram"] is not None and r["vram"] <= address < r["vram"] + r["end"] - r["start"] for r in target["ranges"]):
            raise DataSearchError("dependency alias does not point into target data")
        aliases.append({"name": name, "address": address, "donors": sorted(alternatives[address])})
    tables = []
    for function, rows in target_functions.items():
        addresses = {r[1] for r in rows}
        references = {int(m[1], 16) for row in rows for m in re.finditer(r"jtbl_us_([0-9A-Fa-f]{8})", row[2])}
        for address in sorted(references):
            ranges = [r for r in target["ranges"] if r["section"] == "rodata" and r["owner"] is None
                      and r["vram"] is not None and r["vram"] <= address < r["vram"] + r["end"] - r["start"]]
            if len(ranges) != 1:
                raise DataSearchError("jump table lacks unowned target rodata")
            span = ranges[0]
            start = span["start"] + address - span["vram"]
            end = start
            while end + 4 <= span["end"] and int.from_bytes(binary[end:end + 4], "little") in addresses:
                end += 4
            if end - start < 8 or end - start > 1024:
                raise DataSearchError("jump table lacks bounded local function targets")
            tables.append({"function": function, "start": start, "end": end})
    return {"aliases": aliases, "tables": tables}


def snapshot_identity(snapshot):
    return snapshot["binary"]["content_hash"]
