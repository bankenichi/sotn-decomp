#!/usr/bin/env python3
"""Which remaining INCLUDE_ASM stubs could be retired by including a shared header?

WHY THIS EXISTS
    src/st (and src/boss, src/servant) deduplicate by putting one implementation
    in <dir>/<name>.h and reducing each stage's .c to a two-line shim. When a
    stage still carries INCLUDE_ASM stubs for a file that 20 other stages shim,
    those stubs are not decompilation work. They are configuration work, and
    they are far cheaper.

    Nine files in rno0 were retired this way between 2026-08-01 and 2026-08-02,
    worth 23 matched functions, every one of them found by hand. This does the
    finding.

THE RULE THAT MATTERS
    A stage file is matched to a shared header by what its PEERS INCLUDE, not by
    what the file is called. Twenty stages implement entity_lock_camera.h from a
    file named e_lock_camera.c. A filename rule sees zero shimmers and reports
    the header as unused; that exact bug sat in codebase_index.py until an audit
    on 2026-08-02 found it, and while it sat there it caused real work to be
    written into ROADMAP.md as "actively wrong". See build_shared_impls().

WHAT A HIT DOES AND DOES NOT MEAN
    A hit means: peers prove this header can implement this file, and we still
    have stubs. It does NOT mean the shim will build. Three things routinely
    block one, and this script reports each as a RISK rather than pretending to
    resolve it:

      data      the header emits .data or .bss that splat currently disassembles
                as raw bytes. Needs a segment in config/splat.us.st<ovl>.yaml
                before it will link. Use find_data_segment.py.
      variance  peers disagree about the compiled size of the file, so there are
                per-stage differences. May still be shimmable if the header is
                already parameterised, or if you add a parameter (see
                docs/shared-header-parameterisation.md and the
                GIANTBRO_ZPRIORITY_ADJUST precedent).
      symbols   the header references globals this overlay names by raw address
                (D_us_...). Those must be renamed first, and note that GCC 2.7
                only WARNS about an undeclared one while passing it by value.

Usage:
    python3 automation/shim_sweep.py                  # ranked report
    python3 automation/shim_sweep.py --overlay rno0
    python3 automation/shim_sweep.py --min-peers 5 --json
    python3 automation/shim_sweep.py --json-out automation/shim-viability.us.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOTS = ("src/st", "src/boss", "src/servant")

_INCLUDE = re.compile(r'#\s*include\s+"(?:\.\./)?([A-Za-z_]\w*)\.h"')
_ASM = re.compile(r"\bINCLUDE_ASM\b")
_ASM_FN = re.compile(r'INCLUDE_ASM\("[^"]*",\s*([A-Za-z_]\w*)')
# Anything the compiler would emit into .data / .bss from the header itself.
_STATIC_DATA = re.compile(
    r"^\s*(?:static\s+)?(?:const\s+)?[A-Za-z_]\w*[\w \*]*\s+\w+\s*"
    r"(?:\[[^\]]*\])*\s*=\s*[\{\"]", re.M)
_STATIC_BSS = re.compile(r"^\s*static\s+(?!.*=)[A-Za-z_]\w*[\w \*]*\s+\w+\s*"
                         r"(?:\[[^\]]*\])*\s*;", re.M)
_COND = re.compile(r"^\s*#\s*(?:if|ifdef|ifndef|elif)\b", re.M)
_FN_DEF = re.compile(
    r"^(?:static\s+)?(?!return|else|typedef)[A-Za-z_]\w*[\w \*]*?\s+\*?"
    r"([A-Za-z_]\w*)\s*\([^;{)]*\)\s*\{", re.M)
_KEYWORDS = {"if", "for", "while", "switch", "sizeof", "return", "do", "else"}
_RAW_SYM = re.compile(r"\bD_(?:us|hd)_[0-9A-Fa-f]{6,8}\b")
_PORT = re.compile(r"_(?:psp|saturn|hd|pspeu)$")


def read(p: Path) -> str:
    try:
        return p.read_text(errors="ignore")
    except OSError:
        return ""


def shared_headers() -> dict[str, Path]:
    """<root>/<stem>.h, keyed by stem. These are the shareable implementations."""
    out = {}
    for root in ROOTS:
        for h in sorted((REPO / root).glob("*.h")):
            out[h.stem] = h
    return out


def stage_files() -> list[Path]:
    out = []
    for root in ROOTS:
        for c in sorted((REPO / root).glob("*/*.c")):
            out.append(c)
    return out


def defined_functions(text: str) -> set[str]:
    return {m for m in _FN_DEF.findall(text) if m not in _KEYWORDS}


def build_peer_map(headers: dict, files: list[Path]) -> tuple[dict, dict]:
    """filename stem -> {header stem: [stages that shim it]}, and per-file state.

    A stage counts as shimming a header only when its .c includes that header,
    carries no INCLUDE_ASM, AND defines no function bodies of its own. That last
    clause is what separates a SHIM from a file that merely uses a helper.

    Without it the report is dominated by noise. src/st/pad2_anim_debug.h is a
    two-function debug helper that plenty of fully-implemented files include; on
    an includes-only rule every one of those files "shimmed" it, and the sweep
    then advised converting e_floor_trap.c into an include of a debug helper
    that does not contain EntityFloorTrap at all. Same story for the twelve
    cutscene_*.h helpers against bo6/cutscene.c.
    """
    peers: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    state: dict[Path, dict] = {}
    for c in files:
        body = read(c)
        stage = c.parent.name
        stubs = _ASM.findall(body)
        incs = {m for m in _INCLUDE.findall(body) if m in headers}
        # Never let a file vouch for a header it does not include, and never let
        # the stage's own umbrella header (rno0.h etc.) count as a shared impl.
        incs.discard(stage)
        own = defined_functions(body)
        state[c] = {"stage": stage, "stem": c.stem, "stubs": len(stubs),
                    "includes": sorted(incs), "own_bodies": len(own),
                    "stub_fns": _ASM_FN.findall(body)}
        if not stubs and not own:
            for h in incs:
                peers[c.stem][h].append(stage)
    return peers, state


def header_risks(hdr: Path) -> list[str]:
    return header_risks_text(read(hdr))


def header_risks_text(text: str) -> list[str]:
    r = []
    if _STATIC_DATA.search(text):
        r.append("data")
    if _STATIC_BSS.search(text):
        r.append("bss")
    n = len(_COND.findall(text))
    if n:
        r.append(f"cond:{n}")
    return r


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overlay", help="restrict to one stage dir, e.g. rno0")
    ap.add_argument("--min-peers", type=int, default=1,
                    help="require at least N stages already shimming (default 1)")
    ap.add_argument("--include-ports", action="store_true",
                    help="also report *_psp and *_saturn stages. Off by default: "
                         "those build a different target and none of their "
                         "output is covered by config/check.us.sha, so a shim "
                         "there cannot be verified by our oracle. They still "
                         "count as PEERS, which is correct, because a PSP stage "
                         "shimming a header is real evidence the header works.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--json-out", default="", metavar="PATH",
                    help="write the same deterministic JSON report in-repo")
    a = ap.parse_args()

    headers = shared_headers()
    files = stage_files()
    peers, state = build_peer_map(headers, files)

    hits = []
    for c, st in state.items():
        if not st["stubs"]:
            continue
        if a.overlay and st["stage"] != a.overlay:
            continue
        if not a.include_ports and _PORT.search(st["stage"]):
            continue
        cands = peers.get(st["stem"], {})
        for hstem, shimmers in sorted(cands.items()):
            shimmers = [s for s in shimmers if s != st["stage"]]
            if len(shimmers) < a.min_peers:
                continue
            hdr = headers[hstem]
            body = read(c)

            # THE decisive test: does this header actually define the functions
            # we have stubbed? Peer evidence alone is not enough, because a peer
            # may include a header for one helper while implementing the rest
            # itself. If the header defines none of our stubs, including it
            # cannot retire any of them.
            hdr_fns = defined_functions(read(hdr))
            mine = st["stub_fns"]
            covered = [f for f in mine if f in hdr_fns]
            if not covered:
                continue

            risks = header_risks(hdr)
            if _RAW_SYM.search(body):
                risks.append("raw-syms")
            if len(covered) < len(mine):
                risks.append(f"partial:{len(covered)}/{len(mine)}")

            hits.append({
                "overlay": st["stage"],
                "file": c.relative_to(REPO).as_posix(),
                "header": hdr.relative_to(REPO).as_posix(),
                "stubs": st["stubs"],
                "covered": covered,
                "uncovered": [f for f in mine if f not in hdr_fns],
                "peers": len(shimmers),
                "peer_stages": sorted(shimmers),
                "risks": risks,
                "already_includes": st["includes"],
            })

    hits.sort(key=lambda h: (-len(h["covered"]), -h["peers"], h["file"]))

    rendered = json.dumps(hits, indent=2) + "\n"
    if a.json_out:
        out = (REPO / a.json_out).resolve()
        try:
            out.relative_to(REPO.resolve())
        except ValueError:
            print("json-out must stay inside the repository")
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"wrote {out.relative_to(REPO)}: {len(hits)} candidate(s), "
              f"{sum(len(hit['covered']) for hit in hits)} covered stub(s)")
    if a.json:
        print(rendered, end="")
    if a.json or a.json_out:
        return 0

    if not hits:
        print("No stub file matches a shared header that any peer already shims.")
        return 0

    tot = sum(len(h["covered"]) for h in hits)
    print(f"{len(hits)} shim candidate(s), {tot} stub(s) covered by a shared "
          f"header that defines them\n")
    for h in hits:
        risk = ", ".join(h["risks"]) or "none detected"
        print(f"{len(h['covered']):3d}/{h['stubs']} covered  {h['file']}")
        print(f"           -> {h['header']}  ({h['peers']} peers already shim it)")
        print(f"           risks: {risk}")
        print(f"           covered: {', '.join(h['covered'][:6])}"
              + (" ..." if len(h["covered"]) > 6 else ""))
        if h["uncovered"]:
            print(f"           NOT in header: {', '.join(h['uncovered'][:6])}"
                  + (" ..." if len(h["uncovered"]) > 6 else ""))
        print()
    print("risks legend: data/bss = header emits storage, needs a splat segment "
          "before it links (find_data_segment.py). cond:N = N preprocessor "
          "conditionals, so the header is already stage-dependent; check whether "
          "one of them is your case before adding a new parameter. raw-syms = "
          "this file still references D_us_ addresses that the header will want "
          "by name.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
