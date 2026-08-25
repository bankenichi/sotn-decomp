#!/usr/bin/env python3
"""Where does a shared header's .data land in an overlay that has not named it?

WHY THIS EXISTS
    Seven rno0 stems are blocked on one thing each: a missing
    '.data, <stem>' splat segment. Without it the unnamed data blob emits the
    header's arrays a second time and every later address shifts. Finding that
    address is the entire job, and doing it by hand seven times invites seven
    chances to be off by a row.

THE METHOD, AND WHY IT IS TRUSTWORTHY
    When a shared header defines its own file-scope data, those bytes are
    IDENTICAL in every overlay that shims it -- same initialisers, same
    compiler. So a stage that already declares '.data, <stem>' gives us the
    exact byte pattern to look for, and its declared address gives us a way to
    check the search itself.

    Every run therefore does two things:

      1. CALIBRATE. Take the pattern from peer A, search peer B's binary, and
         confirm the hit equals the address peer B's splat config already
         declares. If that fails, the method does not apply to this stem and
         the tool says so instead of producing a number.
      2. SEARCH. Only then look in the target overlay.

    A technique that reproduces a known boundary can be believed on an unknown
    one. This is the same check that made the e_red_door address trustworthy
    (validated against RCEN.BIN's 0xE78 before being used on RNO0.BIN).

    A unique hit is required. Multiple hits mean the pattern is not
    distinctive and the answer is refused rather than guessed.

Usage:
    python3 automation/find_data_segment.py --stage rno0 --stem e_misc
    python3 automation/find_data_segment.py --stage rno0 --all
    python3 automation/find_data_segment.py --shim-report automation/shim-viability.us.json \\
        --json-out automation/shim-data-segments.us.json
    python3 automation/find_data_segment.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# rno0 and friends load at this base; vaddr = file offset + BASE.
OVL_BASE = 0x80180000
_ORACLE_CACHE: dict[str, str] | None = None
_ORACLE_BYTES: bytes | None = None
_BIN_CACHE: dict[str, tuple[bytes | None, dict]] = {}

_SEG_RX = re.compile(r"^\s*-\s*\[\s*(0x[0-9A-Fa-f]+)\s*,\s*([^,\]]+?)\s*(?:,\s*([^\]]+?)\s*)?\]")


def segments(stage: str) -> list[tuple[int, str, str]]:
    """(addr, kind, name) for one overlay's splat config, in file order."""
    p = REPO / "config" / f"splat.us.st{stage}.yaml"
    out = []
    if not p.exists():
        return out
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _SEG_RX.match(ln)
        if m:
            out.append((int(m.group(1), 16), m.group(2).strip(),
                        (m.group(3) or "").strip()))
    return out


def data_span(stage: str, stem: str) -> tuple[int, int] | None:
    """(start, size) of an overlay's '.data, <stem>' segment, if declared."""
    segs = segments(stage)
    for i, (addr, kind, name) in enumerate(segs):
        if kind == ".data" and name == stem:
            for naddr, _k, _n in segs[i + 1:]:
                if naddr > addr:
                    return addr, naddr - addr
            return addr, 0
    return None


def overlay_bin(stage: str) -> Path:
    return REPO / "build" / "us" / f"{stage.upper()}.BIN"


def oracle_hashes() -> dict[str, str]:
    """Expected SHA-1s keyed by repository-relative build path."""
    global _ORACLE_CACHE, _ORACLE_BYTES
    if _ORACLE_CACHE is None:
        out = {}
        manifest = REPO / "config" / "check.us.sha"
        _ORACLE_BYTES = manifest.read_bytes()
        for line in _ORACLE_BYTES.decode("utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and re.fullmatch(r"[0-9A-Fa-f]{40}", parts[0]):
                out[parts[1].replace("\\", "/")] = parts[0].lower()
        _ORACLE_CACHE = out
    return _ORACLE_CACHE


def oracle_manifest_bytes() -> bytes:
    """Return the exact manifest bytes that populated the oracle cache."""
    oracle_hashes()
    assert _ORACLE_BYTES is not None
    return _ORACLE_BYTES


def verified_binary(stage: str) -> tuple[bytes | None, dict]:
    """Read one target only when its bytes match the checked-in US oracle."""
    key = stage.lower()
    if key in _BIN_CACHE:
        return _BIN_CACHE[key]
    path = overlay_bin(stage)
    rel = path.relative_to(REPO).as_posix()
    expected = oracle_hashes().get(rel, "")
    proof = {"stage": key, "path": rel, "expected_sha1": expected}
    if not expected:
        proof["error"] = "binary is absent from config/check.us.sha"
        result = (None, proof)
    elif not path.is_file():
        proof["error"] = "binary is not built"
        result = (None, proof)
    else:
        data = path.read_bytes()
        actual = hashlib.sha1(data).hexdigest()
        proof["actual_sha1"] = actual
        proof["oracle_match"] = actual == expected
        if actual != expected:
            proof["error"] = "binary does not match config/check.us.sha"
            result = (None, proof)
        else:
            result = (data, proof)
    _BIN_CACHE[key] = result
    return result


def peers_with_segment(stem: str) -> list[str]:
    out = []
    for p in sorted((REPO / "config").glob("splat.us.st*.yaml")):
        stage = p.name[len("splat.us.st"):-len(".yaml")]
        if data_span(stage, stem) and overlay_bin(stage).exists():
            out.append(stage)
    return out


def find_unique(hay: bytes, needle: bytes) -> list[int]:
    hits, i = [], hay.find(needle)
    while i != -1:
        hits.append(i)
        i = hay.find(needle, i + 1)
        if len(hits) > 8:
            break
    return hits


def locate(stage: str, stem: str) -> dict:
    """Pure enough to reason about; all IO is reads."""
    peers = [p for p in peers_with_segment(stem) if p != stage]
    if len(peers) < 2:
        return {"ok": False, "why": f"need 2+ peers with a '.data, {stem}' "
                                    f"segment to calibrate, found {len(peers)}"}
    src_data, src_proof = verified_binary(stage)
    inputs = [src_proof]
    if src_data is None:
        return {"ok": False, "oracle_verified": False, "inputs": inputs,
                "why": f"target binary is not oracle-safe: "
                       f"{src_proof.get('error', 'unknown error')}"}

    a = peers[0]
    span = data_span(a, stem)
    peer_data: dict[str, bytes] = {}
    for peer in peers[:4]:
        data, proof = verified_binary(peer)
        inputs.append(proof)
        if data is None:
            return {"ok": False, "oracle_verified": False, "inputs": inputs,
                    "why": f"peer {peer} is not oracle-safe: "
                           f"{proof.get('error', 'unknown error')}"}
        peer_data[peer] = data
    pat = peer_data[a][span[0]:span[0] + span[1]]
    if len(pat) < 8 or len(set(pat)) < 3:
        return {"ok": False, "oracle_verified": True, "inputs": inputs,
                "why": f"peer {a}'s {stem} data is {len(pat)} bytes "
                       f"and not distinctive enough to search for"}

    # 1. CALIBRATE against a second peer whose answer we already know.
    calib = []
    for b in peers[1:4]:
        want = data_span(b, stem)[0]
        hits = find_unique(peer_data[b], pat)
        calib.append((b, want, hits))
    good = [c for c in calib if c[2] == [c[1]]]
    if not good:
        detail = "; ".join(f"{b}: expected {w:#x}, found "
                           f"{[hex(h) for h in h_] or 'nothing'}"
                           for b, w, h_ in calib)
        return {"ok": False, "calibrated": False, "oracle_verified": True,
                "inputs": inputs,
                "why": f"calibration FAILED, so the bytes are not stage-"
                       f"independent for {stem}. Do not trust a hit in {stage}. "
                       f"({detail})"}

    # 2. Only now, search the target.
    hits = find_unique(src_data, pat)
    if len(hits) != 1:
        return {"ok": False, "calibrated": True, "oracle_verified": True,
                "inputs": inputs,
                "why": f"pattern from {a} ({len(pat)} bytes) matched "
                       f"{len(hits)} times in {stage} ({[hex(x) for x in hits]}); "
                       f"a unique hit is required"}
    return {"ok": True, "calibrated": True, "oracle_verified": True,
            "inputs": inputs, "pattern_from": a,
            "calibrated_on": [c[0] for c in good], "size": len(pat),
            "addr": hits[0], "vaddr": hits[0] + OVL_BASE,
            "end": hits[0] + len(pat)}


def order_check(stage: str, found: dict) -> list[str]:
    """Do the located .data segments appear in the same order as the `c` ones?

    An independent confirmation that costs nothing. splat emits a file's data
    in the same order it emits its text, so if the addresses we just searched
    for are real, sorting them by .data address must reproduce the order of the
    matching `c` segments.

    It paid for itself immediately: st_update 0x1048..0x1094, collision
    0x1094..0x1454 and the hand-found e_red_door at 0x1454 tile with no gaps
    and in text order. Three independent searches agreeing on a contiguous
    run is far stronger evidence than any one of them alone.
    """
    ctext = {name: addr for addr, kind, name in segments(stage) if kind == "c"}
    known = dict(found)
    span = data_span(stage, "e_red_door")
    if span:
        known.setdefault("e_red_door", span[0])
    pairs = [(s, a, ctext[s]) for s, a in known.items() if s in ctext]
    by_data = [s for s, _, _ in sorted(pairs, key=lambda t: t[1])]
    by_text = [s for s, _, _ in sorted(pairs, key=lambda t: t[2])]
    notes = []
    if by_data == by_text:
        notes.append(f"ORDER OK: {' < '.join(by_data)} in both .data and .text")
    else:
        notes.append(f"ORDER MISMATCH -- .data says {by_data}, .text says "
                     f"{by_text}. At least one address is wrong; do not apply.")
    return notes


def self_test() -> int:
    ok = True

    def ck(name, cond, extra=""):
        nonlocal ok
        print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else "  " + extra))
        ok = ok and cond

    ck("segment parser reads a real config", len(segments("rno0")) > 20)
    span = data_span("rno0", "e_red_door")
    ck("finds the e_red_door segment we added", span is not None and span[0] == 0x1454,
       str(span))
    ck("its size is the 0x18 we declared", span and span[1] == 0x18, str(span))
    ck("absent segment returns None", data_span("rno0", "no_such_stem") is None)

    # THE calibration property, on a stem whose answer is already known.
    peers = peers_with_segment("e_misc")
    ck("e_misc has peers to calibrate with", len(peers) >= 3, str(peers[:5]))

    # A stem the tool must REFUSE: rno0 already declares e_red_door, so locating
    # it again must still agree with the declared address if it succeeds.
    r = locate("rno0", "e_red_door")
    if r.get("ok"):
        ck("re-locating a KNOWN segment reproduces its declared address",
           r["addr"] == 0x1454, str(r))
        ck("successful location records oracle proof for every input",
           r.get("oracle_verified") is True
           and all(item.get("oracle_match") for item in r.get("inputs", [])),
           str(r.get("inputs")))
    else:
        ck("re-locating a known segment is refused, not guessed",
           "calibrat" in r["why"] or "unique" in r["why"], r["why"][:120])

    with tempfile.TemporaryDirectory() as td:
        report = Path(td) / "shim.json"
        first_rows = [{"risks": ["data"], "overlay": "BOSS/BO5",
                       "header": "src/st/e_first.h",
                       "file": "src/boss/bo5/e_first.c", "covered": ["A"]}]
        original = json.dumps(first_rows).encode("utf-8")
        report.write_bytes(original)
        snapshotted = report.read_bytes()
        report.write_text(json.dumps([{**first_rows[0],
                                       "header": "src/st/e_second.h"}]))
        document = shim_report_document("shim.json", snapshotted, b"oracle\n")
        ck("report refresh cannot race its recorded source hash",
           document["source_sha256"] == hashlib.sha256(original).hexdigest()
           and document["results"][0]["stem"] == "e_first")
        ck("oracle hash is bound to the cached manifest bytes",
           document["oracle_manifest_sha256"]
           == hashlib.sha256(b"oracle\n").hexdigest())

    print()
    print("self-test PASSED" if ok else "self-test FAILED")
    return 0 if ok else 1


BLOCKED_STEMS = ["e_misc", "collision", "st_update", "e_medusa_head",
                 "e_collect", "e_particles", "e_room_fg"]


def locate_shim_rows(rows: list[dict]) -> list[dict]:
    """Run the calibrated locator for already-snapshotted shim-report rows."""
    out = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if "data" not in row.get("risks", []):
            continue
        stage = row.get("overlay", "").lower()
        stem = Path(row.get("header", "")).stem
        key = (stage, stem)
        if not stage or not stem or key in seen:
            continue
        seen.add(key)
        item = {
            "overlay": stage,
            "stem": stem,
            "header": row.get("header", ""),
            "source_file": row.get("file", ""),
            "covered": row.get("covered", []),
        }
        if not item["source_file"].startswith("src/st/"):
            item["result"] = {
                "ok": False,
                "why": "boss overlay naming is not supported by the stage "
                       "binary locator",
            }
        else:
            item["result"] = locate(stage, stem)
        out.append(item)
    return out


def shim_report_document(source: str, report_bytes: bytes,
                         oracle_bytes: bytes) -> dict:
    """Bind generated results and hashes to one immutable input snapshot."""
    rows = json.loads(report_bytes.decode("utf-8"))
    return {
        "generator": "automation/find_data_segment.py --shim-report",
        "source": source,
        "source_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "oracle_manifest": "config/check.us.sha",
        "oracle_manifest_sha256": hashlib.sha256(oracle_bytes).hexdigest(),
        "results": locate_shim_rows(rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", default="rno0")
    ap.add_argument("--stem", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--shim-report", default="",
                    help="locate every data-risk stage shim in this JSON report")
    ap.add_argument("--json-out", default="",
                    help="write structured results for --shim-report")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if a.shim_report:
        report_path = Path(a.shim_report)
        report_bytes = report_path.read_bytes()
        document = shim_report_document(
            a.shim_report, report_bytes, oracle_manifest_bytes())
        results = document["results"]
        for item in results:
            result = item["result"]
            if result.get("ok"):
                print(f"{item['overlay']:8} {item['stem']:24} "
                      f"0x{result['addr']:X} size 0x{result['size']:X}")
            else:
                print(f"{item['overlay']:8} {item['stem']:24} "
                      f"NO: {result.get('why', 'unknown')}")
        if a.json_out:
            Path(a.json_out).write_text(json.dumps(document, indent=2) + "\n")
            print(f"wrote {a.json_out}: {len(results)} target/stem pairs")
        return 0

    stems = [a.stem] if a.stem else (BLOCKED_STEMS if a.all else [])
    if not stems:
        print("give --stem <name> or --all")
        return 2

    found: dict = {}
    for stem in stems:
        r = locate(a.stage, stem)
        if r.get("ok"):
            print(f"{stem:16} 0x{r['addr']:X}  size 0x{r['size']:X}  "
                  f"(vaddr 0x{r['vaddr']:08X}, ends 0x{r['end']:X})")
            print(f"                 pattern from {r['pattern_from']}, "
                  f"calibrated on {', '.join(r['calibrated_on'])}")
            print(f"                 - [0x{r['addr']:X}, .data, {stem}]")
        else:
            print(f"{stem:16} NO: {r['why']}")
            continue
        found[stem] = r["addr"]

    if found:
        print()
        for note in order_check(a.stage, found):
            print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
