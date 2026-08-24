#!/usr/bin/env python3
"""Tier 2: read the escalated pool, classify it, and resolve what is mechanical.

WHY THIS EXISTS (ROADMAP P6 item 2)
    `escalated` had no automated consumer. Records accumulated until someone
    picked them up by hand, and "someone picks it up" is how a record sits for a
    week carrying a note about a failure that was never its fault.

    The pool is not homogeneous. Measured over the live queue, escalations fall
    into four classes with four completely different correct actions, and only
    ONE of them is "a human should read the assembly":

      symbol    the model invented an identifier. `RIC_step' undeclared,
                `structure has no member named unk24'. MECHANICAL: the real name
                exists, and the fix is a rename, not a rewrite. This tool
                resolves the invented name against the actual declarations and
                emits the mapping.
      nocode    the model produced nothing. "attempt 4 timed out", "failed:
                RuntimeError". Says nothing about the function. Requeue.
      harness   the harness could not do its job. "INCLUDE_ASM stub not found"
                was six bo6 stubs that clang-format had wrapped onto two lines,
                invisible to a line-by-line scan. Fix the harness, requeue.
      real      a genuine decompilation problem. Needs a human or a strong model.

    Only `real` deserves expensive attention. Everything else is either free or
    a harness defect, and spending model quota on it is the waste the tiering
    was built to prevent.

WRITE BOUNDARY
    The default report is read-only. --repair-candidates may refresh only
    preserved automation/rejected artifacts, with immutable history, and is a
    dry run unless --apply is also present. It never edits src/, builds, or
    mutates the queue. Compilation and routing stay with transplant.py.

Usage:
    python3 automation/escalation_triage.py
    python3 automation/escalation_triage.py --json out.json
    python3 automation/escalation_triage.py --repair-candidates
    python3 automation/escalation_triage.py --repair-candidates --apply
    python3 automation/escalation_triage.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[1]))
PYTHON = os.environ.get("SOTN_PYTHON", sys.executable)

# One authoritative copy of "does this overlay define the symbol itself".
# deferred_triage needed it first, for the zero-blocked class; the rule is the
# same on both sides and a second implementation would drift.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from deferred_triage import defines_in_own_overlay  # noqa: E402
from artifact_store import publish_versioned_artifact  # noqa: E402
from data_declarations import declaration as retained_data_declaration  # noqa: E402
from ext_demand import analyse as analyse_ext_demand  # noqa: E402
from member_types import _declared_type_at, _declared_type_ranges  # noqa: E402
from quality_audit import _mask_c_comments_and_literals  # noqa: E402

# ---------------------------------------------------------------------------
# classification
#
# Ordered, and the order is load-bearing: a note can carry more than one
# signal, and the FIRST match should be the one that decides what to do. A
# record whose build failed because a stub was not found is a harness problem
# even though the note also contains "BUILD FAILED".

_CLASSES = [
    # FIRST, and its own class. Every quality reject used to fall through to
    # `unknown: read it` -- 19 of 77 records on 2026-08-10, which made the
    # largest actionable group in the queue look like a residue nobody had
    # classified. A quality reject is not a build failure and not a symbol
    # problem; it is a verdict about STYLE, written by our own gate, and it
    # can go stale when the gate's cause is fixed upstream of the model.
    #
    # Matched before `symbol` deliberately: several of these notes say
    # "`Entity` has no member `unk80`", which would otherwise be read as a
    # compiler diagnostic rather than as our own reviewer talking.
    ("quality", re.compile(
        r"quality reject|SYMBOL_DISPOSITION #241: quality", re.I)),
    # A durable disposition is evidence that the old compiler receipt has been
    # read and is no longer an unresolved symbol lookup. It must outrank the
    # historical diagnostic retained later in the same note.
    ("real", re.compile(r"SYMBOL_DISPOSITION #241: real", re.I)),
    ("harness", re.compile(
        r"INCLUDE_ASM stub not found|BUILD DIRTY|stub not parsed", re.I)),
    ("nocode", re.compile(
        r"timed out|failed: \w*Error|produced no candidate|generation errors",
        re.I)),
    ("symbol", re.compile(
        r"undeclared|has no member named|parse error before", re.I)),
    # "byte mismatch" and "bytes differ" are the same condition written two
    # ways by two different call sites; matching only one of them classified a
    # real near as `unknown`.
    ("real", re.compile(
        r"BUILD FAILED|checksum|bytes? (?:differ|mismatch)|permuter candidate",
        re.I)),
]

# GCC 2.7 diagnostics. No `error:` keyword, which is why an error:-only grep
# found nothing here for a long time.
_UNDECLARED = re.compile(r"`([A-Za-z_]\w*)' undeclared")
_NO_MEMBER = re.compile(
    r"(?:structure|union) has no member named `([A-Za-z_]\w*)'")
_PARSE_ERR = re.compile(r"parse error before `([A-Za-z_]\w*)'")


def is_c89_declaration_error(note: str) -> bool:
    """Is this the C89 declaration-after-statement error, wearing a disguise?

    GCC 2.7 is C89: every declaration must precede every statement in a block.
    When a model emits `s16 distX = ...;` after a statement, GCC does NOT say
    "declarations must come first". It says:

        parse error before `distX'
        `distX' undeclared (first use this function)

    which reads exactly like a wrong field name, and gets triaged as one. The
    tell is that the SAME identifier appears in both messages and is declared
    nowhere in the tree -- a real-but-misnamed symbol would exist somewhere.

    This matters because the two fixes are unrelated. A field-name problem needs
    the assembly read; this needs the declarations moved to the top of the
    block, which is mechanical and needs no analysis at all.
    """
    parsed = set(_PARSE_ERR.findall(note or ""))
    if not parsed:
        return False
    undecl = set(_UNDECLARED.findall(note or ""))
    # The identifier that broke the parse is also reported undeclared, or the
    # declaration it belonged to is: either way the block is mixing the two.
    if not (parsed & undecl) and not undecl:
        return False
    return all(declared_at(n) is None for n in parsed)


# A quality reject whose CAUSE has since been fixed upstream of the model.
# The record was never judged on its merits: the gate was describing a prompt
# that no longer exists.
#
# ext.ILLEGAL is the case that matters. Task #82 removed ILLEGAL from the
# SYSTEM rule, from ENTITY_LAYOUT and from the per-offset hint, and made the
# offset table pointer-type aware, so the model is no longer being handed the
# thing this gate rejects it for. 13 of the 19 quality rejects were this.
#
# Keyed by the fix that invalidated it, so the next entry has to say WHY it is
# stale rather than just adding a pattern.
STALE_QUALITY = [
    (re.compile(r"ext\.ILLEGAL", re.I),
     "task #82 removed ILLEGAL from the prompt, the entity layout and the "
     "per-offset hint, and made the offset table pointer-type aware"),
]


def stale_quality_reason(note: str) -> str:
    """Why this quality reject no longer describes the current prompt, or ""."""
    for rx, why in STALE_QUALITY:
        if rx.search(note or ""):
            return why
    return ""


def classify(note: str) -> str:
    for name, rx in _CLASSES:
        if rx.search(note or ""):
            return name
    return "unknown"


def bad_identifiers(note: str) -> list[str]:
    """Every identifier the compiler rejected, deduplicated, in order."""
    out, seen = [], set()
    for rx in (_UNDECLARED, _NO_MEMBER, _PARSE_ERR):
        for m in rx.finditer(note or ""):
            s = m.group(1)
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


# ---------------------------------------------------------------------------
# resolution
#
# The dominant failure is an invented FLAT name for something that is really a
# struct path: RIC_posX_i_hi for RIC.posX.i.hi, RIC_step for RIC.step. That is
# exactly the mistake ROADMAP P2b warns about ("resolve every global BY ADDRESS,
# not by name affinity"), and it is mechanical to undo.

def _split_flat(name: str) -> list[str]:
    return [p for p in name.split("_") if p]


def suggest_struct_path(name: str, known: set[str]) -> str | None:
    """Turn a flat invented name back into a dotted path, if one exists.

    RIC_posX_i_hi -> RIC.posX.i.hi, but ONLY when the leading component is a
    real object. Without that guard this happily "corrects" any identifier
    containing an underscore, which would be worse than saying nothing.

    THE HEAD IS THE LONGEST KNOWN PREFIX, NOT THE FIRST TOKEN. This took
    parts[0], so for `g_GpuBuffers_0_draw_g0` it asked whether "g" is a known
    object, got no, and gave up. Every global in this tree is named `g_
    something`, so the resolver only ever worked for the handful of objects
    with no underscore in their name -- RIC and PLAYER, which is exactly the
    set it was tested on. func_us_801B3368 has been sitting in the
    "needs a human: names not resolvable" bucket since, for a name that
    resolves mechanically.

    NUMERIC COMPONENTS ARE SUBSCRIPTS. g_GpuBuffers is `GpuBuffer[2]`
    (include/game.h:2149), so the `0` is an index, not a member:

        g_GpuBuffers_0_draw_g0  ->  g_GpuBuffers[0].draw.g0

    which is a real path: GpuBuffer.draw is a DRAWENV and DRAWENV carries
    r0/g0/b0. Only PURELY numeric parts become subscripts, so `g0` stays a
    member name rather than becoming `g[0]`.

    Still advisory. The caller labels every suggestion UNVERIFIED, and it
    should: this reads names, not the asm. Note too that some flat names are
    REAL in this tree -- game.h:2151 declares `g_GpuBuffers_1_buf_draw_clip_y`
    as an extern in its own right -- but those are found by the declaration
    index before this is ever reached.
    """
    parts = _split_flat(name)
    if len(parts) < 2:
        return None
    # Longest first, so `g_GpuBuffers` wins over `g` if both are somehow known.
    head_len = 0
    for i in range(len(parts) - 1, 0, -1):
        if "_".join(parts[:i]) in known:
            head_len = i
            break
    if not head_len:
        return None
    out = "_".join(parts[:head_len])
    for p in parts[head_len:]:
        out += f"[{p}]" if p.isdigit() else f".{p}"
    return out


def known_objects() -> set[str]:
    """Globals the tree actually declares, from the C sources and headers.

    Deliberately broad and cheap: this only has to answer "is the first
    component of this flat name a real object", so a name-level index is
    enough and no parsing of types is needed.
    """
    out: set[str] = set()
    rx = re.compile(r"\bextern\s+[A-Za-z_][\w \*]*?\b([A-Za-z_]\w*)\s*(?:\[|;)")
    for p in list((REPO / "include").rglob("*.h")) + \
            list((REPO / "src").rglob("*.h")):
        try:
            out.update(rx.findall(p.read_text(errors="ignore")))
        except OSError:
            continue
    # The two the boss overlays actually use, which are #defines rather than
    # externs and so are invisible to the pattern above.
    out.update({"RIC", "PLAYER", "g_Ric", "g_Player", "g_CurrentEntity"})
    return out


_DECL_INDEX: dict[str, list[str]] | None = None


def _build_decl_index() -> dict[str, list[str]]:
    """symbol -> every "path:line" file-scope declaration in the tree.

    Built ONCE and cached. The first version re-scanned src/ and include/ for
    each identifier, which is O(tree x names) over a slow mount and did not
    finish inside a 45s call. One pass with one regex is the same answer.

    Matches `extern <type> name;` and file-scope `<type> name =`, anchored at
    column 0 so a local variable inside a function body cannot register as a
    declaration.
    """
    idx: dict[str, list[str]] = defaultdict(list)
    rx = re.compile(
        r"^(?!static\b)(?:extern\s+)?[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*"
        r"(?:\[[^\]]*\])?\s*(?:=[^=]|;)", re.M)
    for root in ("include", "src"):
        base = REPO / root
        if not base.is_dir():
            continue
        for p in base.rglob("*.[ch]"):
            low = str(p).lower()
            if "_psp" in low or "saturn" in low or "/psp/" in low:
                continue
            try:
                text = p.read_text(errors="ignore")
            except OSError:
                continue
            rel = p.relative_to(REPO).as_posix()
            for m in rx.finditer(text):
                name = m.group(1)
                location = f"{rel}:{text.count(chr(10), 0, m.start()) + 1}"
                if location not in idx[name]:
                    idx[name].append(location)
    return dict(idx)


def declared_at(name: str, record_id: str = "") -> str | None:
    """Where the tree already declares this symbol, if anywhere.

    THE question to ask before proposing any rename: is the identifier the
    compiler rejected actually REAL somewhere else? If it is, the record failed
    for want of a declaration in one file, and renaming would silently change
    what the function does.

    Same-overlay declarations outrank shared and cross-overlay hits. This check
    was missing from the first version and it produced a confidently
    wrong answer on the very first real record. BO6_CheckHighJumpInput failed on
    `RIC_step' undeclared, and both this tool and a subagent proposed rewriting
    it to RIC.step. But `extern u16 RIC_step;' is declared at
    src/boss/bo6/us_39144.c:15. The symbol is real; it is simply not declared in
    richter.c where the new function lives. The fix is one extern line.
    """
    global _DECL_INDEX
    if _DECL_INDEX is None:
        _DECL_INDEX = _build_decl_index()
    found = _DECL_INDEX.get(name, [])
    if not found:
        return None
    overlay = _overlay_of(record_id) if record_id else ""
    if overlay:
        same = [location for location in found
                if _overlay_of(location) == overlay]
        if same:
            return same[0]
        shared = [location for location in found if not _overlay_of(location)]
        if shared:
            return shared[0]
    return found[0]


_ENTITY: list[tuple[int, str, str]] | None = None
_EXT: set[str] | None = None


def entity_fields() -> list[tuple[int, str, str]]:
    """(offset, type, name) for every field of Entity, from its own annotations.

    include/game.h annotates Entity with real offsets (`/* 0x24 */ u16
    zPriority;`), so this is ground truth rather than a guess about layout.

    This replaced a resolver that indexed EVERY struct under include/ and
    answered "which struct has a member called unk8" with
    ['(anonymous)', 'Collider', 'PspUsbCamSetupVideoExParam']. PSP SDK camera
    structs have nothing to do with this game; that output was noise wearing the
    shape of evidence.
    """
    global _ENTITY
    if _ENTITY is not None:
        return _ENTITY
    text = (REPO / "include" / "game.h").read_text(errors="ignore")
    m = re.search(r"typedef struct Entity \{(.*?)\n\} Entity;", text, re.S)
    out: list[tuple[int, str, str]] = []
    if m:
        for line in m.group(1).splitlines():
            f = re.match(
                r"\s*/\* (0x[0-9A-Fa-f]+) \*/\s+(.+?)\s+\*?(\w+)\s*(?:\[|;|:)",
                line)
            if f:
                out.append((int(f.group(1), 16), f.group(2).strip(), f.group(3)))
    _ENTITY = sorted(out)
    return _ENTITY


def ext_members() -> set[str]:
    """The TOP-LEVEL member names of the Ext union in include/entity.h.

    Ext is a union of ~341 per-entity structs, each named (`factory`,
    `subweapon`, `orob`). A model that writes `self->ext.generic` has invented a
    member; naming what really exists is the useful answer.
    """
    global _EXT
    if _EXT is not None:
        return _EXT
    text = (REPO / "include" / "entity.h").read_text(errors="ignore")
    try:
        end = text.index("} Ext;")
    except ValueError:
        _EXT = set()
        return _EXT
    depth, i = 0, end
    while i > 0:
        i -= 1
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                break
            depth -= 1
    _EXT = {n for _t, n in
            re.findall(r"^\s*(\w+)\s+(\w+)\s*;\s*$", text[i + 1:end], re.M)}
    return _EXT


def resolve_entity_offset(name: str) -> str | None:
    """`unk24' -> the Entity field really at 0x24, or the field containing it.

    The name IS the evidence: splat and the models both spell an unknown field
    as unk<HEX OFFSET>, so `unk24' is a claim about offset 0x24 and can be
    checked against the annotated struct instead of guessed at.

    Reports the CONTAINING field when the offset lands inside one. `unk29' is
    not a field: 0x29 is the second byte of pfnUpdate at 0x28, and saying so is
    far more useful than saying no such member exists.
    """
    m = re.fullmatch(r"unk([0-9A-Fa-f]{1,3})", name)
    if not m:
        return None
    off = int(m.group(1), 16)
    fields = entity_fields()
    if not fields:
        return None
    for i, (o, ty, nm) in enumerate(fields):
        if o == off:
            return f"Entity+{off:#x} is `{nm}` ({ty})"
        if o > off:
            po, pty, pnm = fields[i - 1]
            return (f"Entity+{off:#x} is INSIDE `{pnm}` ({pty}) which starts at "
                    f"{po:#x}; there is no field at {off:#x}")
    return None


def exact_entity_field(name: str) -> str | None:
    """Return the field exactly at unk<hex>, never a containing-field hint."""
    m = re.fullmatch(r"unk([0-9A-Fa-f]{1,3})", name)
    if not m:
        return None
    off = int(m.group(1), 16)
    for field_off, _field_type, field_name in entity_fields():
        if field_off == off:
            return field_name
    return None


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# queue access

def queue_is_snapshot() -> str | None:
    """Is the queue this environment sees a read-only migrated snapshot?

    scheduler.py copies the legacy in-repo queue into ~/sotn-work the first time
    any environment touches it, and stamps the copy. Mutations are refused, but
    READS are allowed, so a stale snapshot answers questions silently and
    plausibly. This tool asked the snapshot for the escalated pool and got 3
    records when the live queue had 16 -- a wrong answer with no error.

    Returns the stamp text when the queue is a snapshot, else None.
    """
    q = Path(os.path.expanduser(
        os.environ.get("SOTN_QUEUE", "~/sotn-work/queue.jsonl")))
    stamp = q.with_suffix(".jsonl.from-legacy")
    try:
        return stamp.read_text().strip() if stamp.exists() else None
    except OSError:
        return None


def read_escalated() -> list[dict]:
    """Escalated records, via the scheduler so the live queue path is honoured.

    Never reads a queue file directly: SOTN_QUEUE resolves per environment and
    a direct read is how a stale snapshot gets mistaken for the real thing.
    """
    r = subprocess.run(
        [PYTHON, str(REPO / "automation" / "scheduler.py"),
         "list", "--status", "escalated"],
        capture_output=True, text=True, timeout=120, cwd=str(REPO))
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line.startswith("escalated"):
            continue
        rest = line.split(None, 2)
        if len(rest) < 3:
            continue
        tail = rest[2]
        rid, _, note = tail.partition("|")
        out.append({"id": rid.strip(), "note": note.strip()})
    return out


def _union_member_error(note: str, name: str) -> bool:
    """Did GCC specifically say this name is not a UNION member?

    Distinguishes `ext.generic' (a real union-member mistake) from a local
    variable that merely failed to resolve for some other reason.
    """
    return bool(re.search(
        r"union has no member named `" + re.escape(name) + r"'", note or ""))


def _overlay_of(path_or_id: str) -> str:
    """The overlay a queue id or a repo path belongs to, lowercased."""
    t = path_or_id.lower().replace("\\", "/")
    m = re.search(r"src/(?:st|boss|servant)/([a-z0-9_]+)/", t)
    if m:
        return m.group(1)
    m = re.search(r"us:(?:st|boss|servant)/([a-z0-9_]+):", t)
    if m:
        return m.group(1)
    return ""


def _cross_overlay(rec_id: str, decl_path: str) -> bool:
    a, b = _overlay_of(rec_id), _overlay_of(decl_path)
    return bool(a and b and a != b)


def _data_overlay_of(record_id: str) -> str:
    """Return the complete queue overlay key used by retained-data evidence."""
    parts = record_id.split(":", 2)
    return parts[1] if len(parts) == 3 else ""


def _retained_data_fix(name: str, record_id: str) -> dict | None:
    """Resolve one raw label without borrowing another overlay's address."""
    found = retained_data_declaration(name, _data_overlay_of(record_id))
    if not found:
        return None
    declared_head = found.split(";", 1)[0]
    if re.search(rf"\b{re.escape(name)}\b", declared_head):
        return {
            "invented": name,
            "kind": "retained-data-declaration",
            "declaration": found,
            "executable": True,
            "likely": f"retained overlay data proves `{found}`",
            "why": ("the target overlay's retained assembly fixes the label, "
                    "storage unit and byte span"),
        }
    return {
        "invented": name,
        "kind": "address-alias-diagnostic",
        "executable": False,
        "likely": found,
        "why": ("configured address anchors identify the object, but the "
                "candidate still needs the raw label replaced by that path"),
    }


def _source_line(source: str, repo_root: Path = REPO) -> str:
    """Read the exact physical source line named by a path:line receipt."""
    path_text, sep, line_text = source.rpartition(":")
    if not sep or not line_text.isdigit():
        raise ValueError(f"invalid declaration source {source!r}")
    path = repo_root / path_text
    lines = path.read_text(errors="ignore").splitlines()
    line_no = int(line_text)
    if not 1 <= line_no <= len(lines):
        raise ValueError(f"declaration source line is outside {path_text}")
    return lines[line_no - 1]


def _internal_linkage(source: str, repo_root: Path = REPO) -> bool:
    """Whether a located definition is unavailable outside its source file."""
    return bool(re.match(r"\s*static\b", _source_line(source, repo_root)))


def _internal_linkage_fix(name: str, source: str) -> dict:
    return {
        "invented": name,
        "kind": "internal-linkage-definition",
        "source": source,
        "executable": False,
        "likely": (f"defined with internal linkage at {source}; it cannot be "
                   "made visible from another source file with extern"),
        "why": ("a file-scope static definition belongs only to its own "
                "translation unit; deriving extern from it would name an "
                "object the linker cannot provide"),
    }


def triage(records: list[dict]) -> list[dict]:
    known = known_objects()
    ext = ext_members()
    rows = []
    for rec in records:
        note = rec["note"]
        cls = classify(note)
        bad = bad_identifiers(note)
        if cls == "symbol" and is_c89_declaration_error(note):
            cls = "c89"
            # The identifiers here are LOCAL VARIABLES the parser rejected, not
            # names that need resolving. Reporting "resolutions" for them
            # invites someone to apply a rename that has nothing to do with the
            # actual defect.
            rows.append({
                "id": rec["id"], "class": cls, "bad_identifiers": bad,
                "resolvable": [], "unresolved": [],
                "action": ("move every declaration to the top of its block; "
                           "GCC 2.7 is C89. The names below are locals, not "
                           "fields: " + ", ".join(bad[:6])),
            })
            continue
        fixes, unknowns = [], []
        for b in bad:
            # FIRST: does the name already exist somewhere in the tree?
            #
            # This check has to come before any rewrite suggestion, and leaving
            # it out produced a confidently wrong answer on the very first real
            # record. BO6_CheckHighJumpInput failed on `RIC_step' undeclared,
            # and both this tool and a subagent proposed rewriting it to
            # RIC.step. But `extern u16 RIC_step;' is declared at
            # src/boss/bo6/us_39144.c:15 -- the symbol is real, it is simply not
            # declared in richter.c where the new function lives.
            #
            # The correct fix is one extern line. Rewriting to a struct path
            # would have compiled and produced DIFFERENT CODE, which is the
            # failure this whole pipeline exists to avoid: plausible beats
            # verified right up until the bytes disagree.
            where = declared_at(b, rec["id"])
            # A declaration in ANOTHER overlay is not evidence.
            #
            # Overlays have separate address spaces, so a raw-address name like
            # D_us_8018206C means a different object in rbo5 than it does in
            # rno0. The first live run proposed exactly that: it told an rno0
            # record to adopt a declaration from src/boss/rbo5/. Following it
            # would have bound the function to an unrelated address.
            #
            # Same-overlay hits stay trustworthy: RIC_step in bo6 pointing at
            # another bo6 file is the real missing-declaration case.
            # BEFORE giving up: does THIS overlay define it?
            #
            # declared_at finds `extern` declarations. A symbol that exists
            # only as a DEFINITION -- `EInit g_EInitGaibon = {...}` -- matches
            # no extern pattern, so it reads as "declared nowhere" or, worse,
            # resolves to some other overlay's extern and gets refused as
            # cross-overlay. Both outcomes say "unresolved" about a symbol
            # sitting in the record's own directory.
            #
            # That is exactly what happened to EntityGaibonLeg. The only
            # `extern ... g_EInitGaibon` in the tree is src/st/nz0/nz0.h, a
            # different overlay, so the guard correctly refused it -- and
            # stopped, having never looked at src/st/rchi/e_init.c:96 where
            # RCHI defines its own. The record sat deferred for want of one
            # line that a directory listing would have found.
            own = defines_in_own_overlay(b, rec["id"])
            data_fix = _retained_data_fix(b, rec["id"])
            if where and _cross_overlay(rec["id"], where):
                if own:
                    if _internal_linkage(own):
                        fixes.append(_internal_linkage_fix(b, own))
                        continue
                    fixes.append({
                        "invented": b,
                        "kind": "declaration-definition",
                        "source": own,
                        "executable": True,
                        "likely": f"THIS overlay defines it at {own}; add "
                                  f"`extern` for it to this file",
                        "why": f"the only declaration in the tree is at "
                               f"{where}, a DIFFERENT overlay, and borrowing "
                               f"it would name a different object; the "
                               f"definition here is the right one"})
                    continue
                if data_fix:
                    fixes.append(data_fix)
                    continue
                unknowns.append(
                    f"{b} (only declared in another overlay at {where}; "
                    f"raw-address names are overlay-local, so this is NOT the "
                    f"same object -- resolve it from this overlay's asm)")
                continue
            if not where and own:
                if _internal_linkage(own):
                    fixes.append(_internal_linkage_fix(b, own))
                    continue
                fixes.append({
                    "invented": b,
                    "kind": "declaration-definition",
                    "source": own,
                    "executable": True,
                    "likely": f"defined in this overlay at {own}; add "
                              f"`extern` for it to this file",
                    "why": "a DEFINITION with no extern anywhere, which a "
                           "declaration-only search cannot see"})
                continue
            if where:
                fixes.append({
                    "invented": b,
                    "kind": "declaration",
                    "source": where,
                    "executable": True,
                    "likely": f"already declared at {where}; add that "
                              f"declaration to this file",
                    "why": "symbol EXISTS elsewhere, so this is a missing "
                           "declaration, not a wrong name"})
                continue
            if data_fix:
                fixes.append(data_fix)
                continue
            path = suggest_struct_path(b, known)
            if path:
                fixes.append({"invented": b, "likely": path,
                              "kind": "struct-path-unverified",
                              "executable": False,
                              "why": "flat name whose head is a real object, "
                                     "and no declaration of it exists anywhere "
                                     "(UNVERIFIED: confirm against the asm)"})
            elif _union_member_error(note, b) and ext:
                # ONLY when GCC actually said "union has no member named `b'".
                #
                # The first version fired on any unresolved name, and told a C89
                # record that its local variable `distX' was not a member of the
                # Ext union. That is a confident answer to a question nobody
                # asked, and it is how a wrong fix gets applied.
                sample = ", ".join(sorted(ext)[:6]) if ext else ""
                fixes.append({
                    "invented": b,
                    "kind": "ext-member-diagnostic",
                    "executable": False,
                    "likely": f"not a member of the Ext union ({len(ext)} real "
                              f"members, e.g. {sample}); pick the one for this "
                              f"entity, or read the asm offsets",
                    "why": "Ext is a union of per-entity structs, not a generic "
                           "bag"})
            elif resolve_entity_offset(b):
                field = exact_entity_field(b)
                fixes.append({
                    "invented": b,
                    "kind": "entity-field" if field else "entity-offset-diagnostic",
                    "replacement": field or "",
                    "executable": False,
                    "requires_candidate_receiver_type": "Entity" if field else "",
                    "likely": resolve_entity_offset(b),
                    "why": "unk<hex> names an OFFSET; resolved against "
                           "the annotated Entity in include/game.h"})
            else:
                unknowns.append(b)
        stale = stale_quality_reason(rec.get("note", "")) if cls == "quality" else ""
        if stale:
            cls = "quality-stale"
        rows.append({
            "id": rec["id"], "class": cls, "bad_identifiers": bad,
            "resolvable": fixes, "unresolved": unknowns,
            "stale_reason": stale,
            "action": {
                "harness": "fix the harness, then requeue as todo",
                "nocode": "requeue as todo; the note says nothing about the code",
                "symbol": ("requeue with the mapping below as feedback"
                           if fixes else "needs a human: names not resolvable"),
                "c89": ("move every declaration to the top of its block; "
                        "GCC 2.7 is C89 and this is NOT a wrong field name"),
                "real": "needs a strong model or a human",
                "quality": ("a real style defect against the CURRENT prompt; "
                            "rework the candidate, do not just requeue it"),
                "quality-stale": (f"requeue as todo: {stale}. The gate was "
                                  f"describing a prompt that no longer "
                                  f"exists, so this was never judged on its "
                                  f"merits"),
            }.get(cls, "read it"),
        })
    return rows


# ---------------------------------------------------------------------------
# rejected-candidate repair

def potentially_mechanical(row: dict) -> bool:
    """True when fixes are executable directly or after a receiver-type check."""
    fixes = row.get("resolvable", [])
    return bool(
        row.get("class") == "symbol" and fixes and
        not row.get("unresolved") and
        all(fix.get("executable") is True or fix.get("kind") in {
            "entity-field", "internal-linkage-definition"}
            for fix in fixes))


def entity_field_access_spans(text: str, name: str) -> list[tuple[int, int]]:
    """Return only field-token spans whose active receiver type is Entity."""
    masked = _mask_c_comments_and_literals(text)
    ranges = _declared_type_ranges(masked)
    out = []
    access = re.compile(
        rf"\b(?P<receiver>[A-Za-z_]\w*)\s*->\s*"
        rf"(?P<field>{re.escape(name)})\b")
    for match in access.finditer(masked):
        receiver = match.group("receiver")
        declared = _declared_type_at(ranges, receiver, match.start())
        if declared is None and receiver == "g_CurrentEntity":
            declared = "Entity"
        if declared == "Entity":
            out.append(match.span("field"))
    return out


def entity_field_receiver_is_entity(text: str, name: str) -> bool:
    """Whether at least one direct field use has a proven Entity receiver."""
    return bool(entity_field_access_spans(text, name))


_GENERATED_MARKER = "/* Mechanical symbol repair from escalation_triage.py. */"


def _generated_extern_span(text: str, name: str,
                           function: str) -> tuple[int, int] | None:
    """Find one generated extern, never an original candidate declaration."""
    marker = text.find(_GENERATED_MARKER)
    if marker < 0:
        return None
    definition = re.search(
        rf"(?m)^[A-Za-z_][^\n;{{}}]*\b{re.escape(function)}\s*"
        rf"\([^;{{}}]*\)\s*{{", text[marker:])
    if not definition:
        return None
    block_end = marker + definition.start()
    match = re.search(
        rf"(?m)^[ \t]*extern\b[^;\n]*\b{re.escape(name)}\b[^;\n]*;"
        rf"[ \t]*(?:\n|$)", text[marker:block_end])
    if not match:
        return None
    return marker + match.start(), marker + match.end()


def mechanically_repairable(row: dict, candidate_text: str = "") -> bool:
    """True only when every fix is proven in both tree and candidate context."""
    if not potentially_mechanical(row):
        return False
    for fix in row["resolvable"]:
        if fix.get("executable") is True:
            continue
        if (fix.get("kind") == "entity-field" and
                entity_field_receiver_is_entity(
                    candidate_text, fix["invented"])):
            continue
        if (fix.get("kind") == "internal-linkage-definition" and
                _generated_extern_span(
                    candidate_text, fix["invented"],
                    row["id"].rsplit(":", 1)[-1])):
            continue
        return False
    return True


def mechanical_subset(row: dict, candidate_text: str) -> dict:
    """Keep every independently proven fix, even if later work remains."""
    selected = []
    for fix in row.get("resolvable", []):
        if fix.get("executable") is True:
            selected.append(fix)
        elif (fix.get("kind") == "entity-field" and
              entity_field_receiver_is_entity(
                  candidate_text, fix["invented"])):
            selected.append(fix)
        elif (fix.get("kind") == "internal-linkage-definition" and
              _generated_extern_span(
                  candidate_text, fix["invented"],
                  row["id"].rsplit(":", 1)[-1])):
            selected.append(fix)
    subset = dict(row)
    subset["resolvable"] = selected
    subset["unresolved"] = []
    return subset


def rejected_path(record_id: str, repo_root: Path = REPO) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", record_id).strip("_")
    return repo_root / "automation" / "rejected" / f"{slug}.c"


def declaration_from_source(source: str, name: str,
                            repo_root: Path = REPO) -> str:
    """Derive one extern from the exact declaration or definition line."""
    line = re.sub(r"/\*.*?\*/", " ",
                  _source_line(source, repo_root)).strip()
    if re.match(r"static\b", line):
        raise ValueError(
            f"refusing internal-linkage declaration for {name}: {line!r}")
    if "=" in line:
        head = line.split("=", 1)[0].strip()
    elif ";" in line:
        head = line.split(";", 1)[0].strip()
    else:
        raise ValueError(f"declaration for {name} is not complete on one line")
    head = re.sub(r"^extern\s+", "", head).strip()
    if (not re.search(rf"\b{re.escape(name)}\b", head) or
            "(" in head or "," in head):
        raise ValueError(f"refusing ambiguous declaration for {name}: {line!r}")
    return f"extern {head};"


def repair_candidate_text(row: dict, text: str,
                          repo_root: Path = REPO) -> tuple[str, list[str]]:
    """Apply one fully mechanical triage row to preserved candidate text."""
    if not mechanically_repairable(row, text):
        raise ValueError("row contains unresolved or interpretive fixes")
    declarations: list[str] = []
    changes: list[str] = []
    for fix in row["resolvable"]:
        kind = fix["kind"]
        name = fix["invented"]
        if kind == "internal-linkage-definition":
            function = row["id"].rsplit(":", 1)[-1]
            span = _generated_extern_span(text, name, function)
            if not span:
                raise ValueError(
                    f"no generated extern exists to retract for {name}")
            old = text[span[0]:span[1]].strip()
            text = text[:span[0]] + text[span[1]:]
            changes.append(f"retract unsafe generated {old}")
            continue
        if kind in {"declaration", "declaration-definition",
                    "retained-data-declaration"}:
            if kind == "retained-data-declaration":
                declaration = fix["declaration"].strip()
            else:
                declaration = declaration_from_source(
                    fix["source"], name, repo_root)
            existing = re.search(
                rf"(?m)^[ \t]*extern\b[^;\n]*\b{re.escape(name)}\b[^;\n]*;"
                rf"[ \t]*(?:\n|$)", text)
            if existing and existing.group(0).strip() != declaration:
                text = text[:existing.start()] + declaration + "\n" + text[existing.end():]
                changes.append(
                    f"replace {existing.group(0).strip()} with {declaration}")
            elif not existing:
                declarations.append(declaration)
                changes.append(f"add {declaration}")
            continue
        if kind == "entity-field":
            replacement = fix["replacement"]
            spans = entity_field_access_spans(text, name)
            if not spans:
                raise ValueError(f"candidate does not contain ->{name}")
            for start, end in reversed(spans):
                text = text[:start] + replacement + text[end:]
            changes.append(
                f"replace {len(spans)} proven Entity use(s) of {name} "
                f"with {replacement}")
            continue
        raise ValueError(f"unsupported repair kind {kind}")

    if declarations:
        function = row["id"].rsplit(":", 1)[-1]
        definition = re.search(
            rf"(?m)^[A-Za-z_][^\n;{{}}]*\b{re.escape(function)}\s*"
            rf"\([^;{{}}]*\)\s*{{", text)
        if not definition:
            raise ValueError(f"candidate does not define {function}")
        block = (_GENERATED_MARKER + "\n" +
                 "\n".join(dict.fromkeys(declarations)) + "\n\n")
        text = text[:definition.start()] + block + text[definition.start():]
    marker = text.find(_GENERATED_MARKER)
    if marker >= 0:
        function = row["id"].rsplit(":", 1)[-1]
        definition = re.search(
            rf"(?m)^[A-Za-z_][^\n;{{}}]*\b{re.escape(function)}\s*"
            rf"\([^;{{}}]*\)\s*{{", text[marker:])
        if definition:
            block_end = marker + definition.start()
            if not re.search(r"(?m)^\s*extern\b", text[marker:block_end]):
                text = text[:marker] + text[block_end:]
    if not changes:
        raise ValueError("candidate already contains every requested repair")
    return text, changes


def repair_candidates(rows: list[dict], apply: bool = False,
                      repo_root: Path = REPO) -> int:
    """Repair preserved evidence only; compilation and queue routing are separate."""
    results = []
    for row in rows:
        if row.get("class") != "symbol":
            continue
        path = rejected_path(row["id"], repo_root)
        has_candidate_fix = any(
            fix.get("executable") is True or fix.get("kind") in {
                "entity-field", "internal-linkage-definition"}
            for fix in row.get("resolvable", []))
        if not has_candidate_fix:
            kinds = sorted({fix.get("kind", "unknown")
                            for fix in row.get("resolvable", [])})
            reason = "unresolved identifiers" if row.get("unresolved") else \
                "interpretive fixes: " + ", ".join(kinds or ["none"])
            results.append({"id": row["id"], "status": "skipped", "reason": reason})
            continue
        if not path.is_file():
            results.append({"id": row["id"], "status": "skipped",
                            "reason": "no preserved rejected candidate"})
            continue
        original = path.read_text(errors="ignore")
        subset = mechanical_subset(row, original)
        if not subset["resolvable"]:
            results.append({"id": row["id"], "status": "skipped",
                            "reason": "no candidate-local repair is proven"})
            continue
        try:
            repaired, changes = repair_candidate_text(
                subset, original, repo_root)
        except (OSError, ValueError) as exc:
            message = str(exc)
            status = "skipped" if "already contains" in message else "refused"
            results.append({"id": row["id"], "status": status,
                            "reason": message})
            continue
        item = {"id": row["id"], "status": "would-repair", "changes": changes,
                "stable": path.relative_to(repo_root).as_posix()}
        if apply:
            item["version"] = publish_versioned_artifact(
                path, repaired, "rejected candidate", repo_root)
            item["status"] = "repaired"
        results.append(item)

    for item in results:
        suffix = "; ".join(item.get("changes", [])) or item.get("reason", "")
        print(f"  {item['status']:12} {item['id']}: {suffix}")
        if item.get("version"):
            print(f"    immutable: {item['version']}")
    repaired = sum(item["status"] in {"would-repair", "repaired"} for item in results)
    skipped = len(results) - repaired
    verb = "repaired" if apply else "would repair"
    print(f"\n{repaired} {verb}; {skipped} skipped or refused")
    if not apply:
        print("Re-run with --repair-candidates --apply to publish immutable repairs.")
    return 0 if all(item["status"] != "refused" for item in results) else 1


# ---------------------------------------------------------------------------
# requeue
#
# Only classes that are NOT a verdict on the code. Everything else needs a
# human or a model, and requeueing it would spend a claim to reach the same
# conclusion.
#
# `quality` (as opposed to `quality-stale`) is deliberately absent: it is a
# real style defect against the CURRENT prompt, so the candidate needs
# reworking, and requeueing it unchanged invites the same rejection.
REQUEUE_TO = {
    "nocode": "todo",
    "c89": "todo",
    "quality-stale": "todo",
}

# Classes that ARE actionable without a model but need a code change FIRST, so
# requeueing them is premature rather than free. Reported, never written.
#
# `harness` was in the table above until the first dry run offered to requeue
# two records whose own action text reads "fix the harness, THEN requeue as
# todo". Sending them back before the stub lookup is fixed just re-escalates
# them, which is the same mistake deferred_triage's zero-blocked class exists
# to avoid: a class can be free of model cost and still not be free of work.
REQUEUE_BLOCKED_ON_WORK = {
    "harness": "the stub lookup has to be fixed before this can succeed",
    "quality": "the candidate has to be reworked against the current prompt",
}


def requeue(rows: list[dict], apply: bool = False) -> int:
    """Write the requeueable classes back, THROUGH scheduler.py.

    deferred_triage grew this first, and the reason applies here twice over:
    its --requeue-plan printed `scheduler.py set <id> --status todo` for
    months, an invocation that never existed, and nobody found out because
    printing advice is not the same as taking it. The escalated side has been
    printing advice for just as long.
    """
    blocked = [(r["class"], r["id"]) for r in rows
               if r["class"] in REQUEUE_BLOCKED_ON_WORK]
    if blocked:
        print("\n" + "=" * 78)
        print("\nNOT requeued, because a code change has to come first:\n")
        for cls, rid in blocked:
            print(f"  [{cls}] {rid}\n      {REQUEUE_BLOCKED_ON_WORK[cls]}")

    todo = [(r["class"], r["id"], r["action"]) for r in rows
            if r["class"] in REQUEUE_TO]
    if not todo:
        print("\nnothing to requeue")
        return 0
    print("\n" + "=" * 78)
    print(f"\nrequeue: {len(todo)} record(s)"
          + ("" if apply else "  [DRY RUN, nothing written]") + "\n")
    ok = bad = 0
    for cls, rid, action in todo:
        status = REQUEUE_TO[cls]
        if not apply:
            print(f"  {status:5} <- {cls:14} {rid}")
            continue
        note = f"requeued by escalation_triage [{cls}]: {action}"
        r = subprocess.run(
            [PYTHON, str(REPO / "automation" / "scheduler.py"), "report",
             "--id", rid, "--status", status, "--notes", note],
            capture_output=True, text=True, timeout=120, cwd=str(REPO))
        if r.returncode == 0:
            ok += 1
            print(f"  {status:5} <- {cls:14} {rid}")
        else:
            bad += 1
            err = (r.stderr or r.stdout or "").strip().splitlines()
            print(f"  FAILED {rid}: {err[-1] if err else r.returncode}")
    if apply:
        print(f"\n{ok} requeued, {bad} failed")
    else:
        print("\nRe-run with --apply to write.")
    return 1 if bad else 0


# ---------------------------------------------------------------------------

_LOCAL_PLACEHOLDER = re.compile(
    r"^(?:self|temp(?:_[A-Za-z0-9]+)*|code)$", re.I)


def _current_artifact(record_id: str) -> Path | None:
    """Prefer a compiling candidate, then the latest preserved reject."""
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", record_id) + ".c"
    for directory in (REPO / "automation" / "candidates",
                      REPO / "automation" / "rejected"):
        path = directory / stem
        if path.is_file():
            return path
    return None


def _wrong_receiver_member(row: dict, text: str) -> list[str]:
    """Names applied to a provably non-Entity receiver in preserved C."""
    if not text:
        return []
    masked = _mask_c_comments_and_literals(text)
    ranges = _declared_type_ranges(masked)
    wrong = []
    for name in row.get("bad_identifiers", []):
        access = re.compile(
            rf"\b(?P<receiver>[A-Za-z_]\w*)\s*->\s*{re.escape(name)}\b")
        for match in access.finditer(masked):
            receiver = match.group("receiver")
            declared = _declared_type_at(ranges, receiver, match.start())
            if declared and declared != "Entity":
                wrong.append(f"{receiver}:{declared}->{name}")
                break
    return wrong


def symbol_disposition(row: dict, record: dict) -> tuple[str, str]:
    """Close one old symbol label with evidence, without claiming a match."""
    note = record.get("notes", record.get("note", ""))
    artifact = _current_artifact(row["id"])
    text = artifact.read_text(errors="replace") if artifact else ""
    bad = row.get("bad_identifiers", [])
    wrong_receiver = _wrong_receiver_member(row, text)

    if (not bad and "parse error before" in note.lower()) or any(
            _LOCAL_PLACEHOLDER.fullmatch(name) for name in row.get("unresolved", [])):
        target = "quality"
        why = ("the retained compiler receipt describes malformed C syntax or "
               "a local placeholder, not an external symbol")
    elif wrong_receiver:
        target = "quality"
        why = ("member_types proves the rejected name was applied to the wrong "
               "receiver type: " + ", ".join(wrong_receiver[:4]))
    else:
        target = "real"
        kinds = sorted({fix.get("kind", "") for fix in row.get("resolvable", [])
                        if fix.get("kind")})
        if row.get("unresolved"):
            why = ("the remaining names require semantic reconstruction from "
                   "the target assembly: " + ", ".join(row["unresolved"][:6]))
        elif kinds:
            why = ("all compiler names now have typed evidence; remaining "
                   "work is candidate semantics/codegen, with fix kinds " +
                   ", ".join(kinds))
        else:
            why = ("the historical symbol label has no unresolved identifier; "
                   "the retained failure is a candidate/codegen problem")

    if artifact:
        rel = artifact.relative_to(REPO).as_posix()
        evidence = f" Current artifact: {rel}."
        score = re.search(
            r"(?m)^\s*score\s*:\s*(\d+)\s*$", text[:1600])
        receipt = re.search(
            r"(?m)^\s*receipt\s*:\s*([^\n]+)$", text[:1600])
        if score:
            evidence += f" Isolated score: {score.group(1)}."
        if receipt:
            evidence += f" Receipt: {receipt.group(1).strip()}."
        demand = analyse_ext_demand([artifact])
        if demand:
            ext_row = demand[0]
            offsets = ", ".join(
                f"0x{off:02X}" for off in sorted(ext_row["offsets"]))
            if ext_row["fits"]:
                evidence += (
                    f" ext_demand: {offsets}; {len(ext_row['fits'])} existing "
                    "Ext variants cover every offset, so no header expansion "
                    "is needed.")
            elif ext_row["uncovered"]:
                gaps = ", ".join(
                    f"0x{off:02X}" for off in ext_row["uncovered"])
                evidence += (
                    f" ext_demand: {offsets}; uncovered offsets {gaps} require "
                    "a header task before codegen.")
            else:
                evidence += (
                    f" ext_demand: {offsets}; fields exist but are split across "
                    "variants, so assembly must identify one coherent variant.")
    else:
        evidence = (" No generated body survives; the complete compiler receipt "
                    "remains in this queue record.")
    return target, why + evidence


def resolve_symbols(rows: list[dict], records: list[dict],
                    apply: bool = False) -> int:
    """Append one durable disposition to every current symbol escalation."""
    by_id = {rec["id"]: rec for rec in records}
    symbols = [row for row in rows if row.get("class") == "symbol"]
    print(f"{len(symbols)} symbol disposition(s)"
          + ("" if apply else "  [DRY RUN, nothing written]"))
    ok = bad = 0
    for row in symbols:
        record = by_id[row["id"]]
        target, evidence = symbol_disposition(row, record)
        note = f"SYMBOL_DISPOSITION #241: {target}. {evidence}"
        if not apply:
            print(f"  {target:7} {row['id']} | {evidence}")
            continue
        result = subprocess.run(
            [PYTHON, str(REPO / "automation" / "scheduler.py"), "report",
             "--id", row["id"], "--status", "escalated", "--keep-note",
             "--notes", note],
            capture_output=True, text=True, timeout=120, cwd=str(REPO))
        if result.returncode == 0:
            ok += 1
            print(f"  {target:7} {row['id']}")
        else:
            bad += 1
            err = (result.stderr or result.stdout or "").strip().splitlines()
            print(f"  FAILED {row['id']}: {err[-1] if err else result.returncode}")
    if apply:
        print(f"\n{ok} dispositions recorded, {bad} failed")
    else:
        print("\nRe-run with --apply to append them to the live queue.")
    return 1 if bad else 0


# ---------------------------------------------------------------------------

def self_test() -> int:
    fails = []

    def ck(c, l):
        print(("  ok   " if c else "  FAIL ") + l)
        if not c:
            fails.append(l)

    print("\nclassification, against real notes from the live queue")
    cases = [
        ("INCLUDE_ASM stub not found", "harness"),
        ("BUILD DIRTY: the build failed but no diagnostic names foo", "harness"),
        ("attempt 4 timed out", "nocode"),
        ("attempt 4 failed: RuntimeError", "nocode"),
        ("requeued: false escalation, model produced no candidate", "nocode"),
        ("BUILD FAILED: src/boss/bo6/richter.c:25: `RIC_step' undeclared",
         "symbol"),
        ("BUILD FAILED: 2D26C.c:68: structure has no member named `state'",
         "symbol"),
        ("BUILD FAILED: us_3E79C.c:1070: parse error before `randomIndex'",
         "symbol"),
        ("compiled, byte mismatch; permuter candidate", "real"),
        ("", "unknown"),
        # Every one of these used to be `unknown: read it`. 19 of 77 records
        # on 2026-08-10, the largest actionable group in the queue, sitting in
        # the bucket that means "nobody has looked at this".
        ("quality reject: uses `ext.ILLEGAL`; prefer the named ext variant",
         "quality"),
        ("quality reject: `self->drawFlags |= 0x20` should use the named "
         "constant ENTITY_MASK_G", "quality"),
        ("quality reject: 8 raw byte-pointer cast(s) like `*(u16*)((u8*)p+N)`",
         "quality"),
        # Reads like a compiler diagnostic and is not one; our own reviewer
        # wrote it. Ordering quality before symbol is what gets this right.
        ("quality reject: `Entity` has no member `unk80`; 0x80 falls inside "
         "`ext` (0x7C)", "quality"),
    ]
    for note, want in cases:
        got = classify(note)
        ck(got == want, f"{want:8} <- {note[:52]!r} (got {got})")

    print("\ndurable symbol dispositions outrank retained compiler receipts")
    ck(classify("SYMBOL_DISPOSITION #241: real. evidence || "
                "BUILD FAILED: `foo' undeclared") == "real",
       "a real disposition closes the historical symbol label")
    ck(classify("SYMBOL_DISPOSITION #241: quality. evidence || "
                "structure has no member named `code'") == "quality",
       "a quality disposition closes the historical symbol label")
    local_row = {"id": "us:TEST:f", "bad_identifiers": ["temp"],
                 "unresolved": ["temp"], "resolvable": []}
    local_rec = {"id": "us:TEST:f",
                 "notes": "BUILD FAILED: `temp' undeclared"}
    disposition, reason = symbol_disposition(local_row, local_rec)
    ck(disposition == "quality" and "local placeholder" in reason,
       "an undeclared generated local is quality, not a symbol lookup")

    print("\nharness beats BUILD FAILED when a note carries both")
    ck(classify("BUILD FAILED ... INCLUDE_ASM stub not found") == "harness",
       "a stub-not-found inside a BUILD FAILED note is still a harness problem")

    print("\nidentifier extraction")
    note = ("src/boss/bo0/2D26C.c:68: structure has no member named `state' "
            "src/boss/bo0/2D26C.c:78: structure has no member named `unk24' "
            "src/boss/bo6/richter.c:25: `RIC_step' undeclared "
            "us_3E79C.c:1070: parse error before `randomIndex'")
    got = bad_identifiers(note)
    ck("state" in got and "unk24" in got, "no-member names extracted")
    ck("RIC_step" in got, "undeclared names extracted")
    ck("randomIndex" in got, "parse-error names extracted")
    ck(got.count("unk24") == 1, "duplicates collapsed (GCC repeats them)")

    print("\nan existing symbol is a MISSING DECLARATION, never a rename")
    # The check that was missing, and the record that proved it.
    ck(declared_at("RIC_step") is not None,
       "RIC_step is declared somewhere in the tree (it is real)")
    ck(declared_at("totally_made_up_identifier_xyz") is None,
       "an invented name is declared nowhere")
    ck(declared_at("PrizeDrops", "us:ST/RCEN:EntityShaft") ==
       "src/st/rcen/e_shaft.c:48",
       "a same-overlay declaration outranks an unrelated shared-header name")

    print("\nunk<hex> resolves against the ANNOTATED Entity, not any struct")
    ck(len(entity_fields()) > 40,
       f"Entity parsed from its offset annotations ({len(entity_fields())} fields)")
    ck("zPriority" in (resolve_entity_offset("unk24") or ""),
       "unk24 -> zPriority (the offset IS the evidence)")
    ck("velocityX" in (resolve_entity_offset("unk8") or ""),
       "unk8 -> velocityX")
    ck("INSIDE" in (resolve_entity_offset("unk29") or ""),
       "unk29 is reported as INSIDE pfnUpdate, not as a missing member")
    ck(exact_entity_field("unk24") == "zPriority",
       "an exact offset is executable as a field replacement")
    ck(exact_entity_field("unk29") is None,
       "a containing-field diagnostic is not executable")
    ck(resolve_entity_offset("state") is None,
       "a non-unk name yields nothing here (no guessing)")
    ck(resolve_entity_offset("unkZZ") is None, "a non-hex suffix yields nothing")

    print("\nExt is a union of per-entity structs, not a generic bag")
    ck(len(ext_members()) > 300,
       f"Ext top-level members parsed ({len(ext_members())})")
    ck("generic" not in ext_members(), "`generic' is NOT an Ext member")
    ck("subweapon" in ext_members() and "factory" in ext_members(),
       "real Ext members are present")
    # The noise this replaced: PSP SDK structs answering questions about Entity.
    ck(not any("PspUsbCam" in m for m in ext_members()),
       "no PSP SDK struct leaks into the Ext answer")
    union_unk = triage([{
        "id": "us:BOSS/BO6:Function",
        "note": "BUILD FAILED: union has no member named `unk00'"}])[0]
    ck(union_unk["resolvable"][0]["kind"] == "ext-member-diagnostic",
       "a union-member diagnostic beats the numeric Entity-offset spelling")
    ck(not union_unk["resolvable"][0]["executable"],
       "an invented Ext member is never auto-repaired as an Entity field")

    print("\nretained overlay data closes raw-label declaration failures")
    ck(_data_overlay_of("us:BOSS/BO0:Function") == "BOSS/BO0",
       "the complete queue overlay key is preserved")
    data_fix = _retained_data_fix(
        "D_us_801A5ED4", "us:BOSS/BO0:func_us_801B13A8")
    ck(bool(data_fix) and data_fix["kind"] == "retained-data-declaration",
       "a BO0 retained-data label yields a typed declaration")
    ck(bool(data_fix) and data_fix["executable"],
       "a declaration that names the rejected label is executable")
    data_row = triage([{
        "id": "us:BOSS/BO0:func_us_801B13A8",
        "note": "BUILD FAILED: `D_us_801A5ED4' undeclared",
    }])[0]
    ck(not data_row["unresolved"] and
       data_row["resolvable"][0]["kind"] == "retained-data-declaration",
       "triage consults retained data before giving up on a raw label")
    alias_fix = _retained_data_fix(
        "D_80073510", "us:ST/RCEN:func_us_8019FE9C")
    ck(bool(alias_fix) and alias_fix["kind"] == "address-alias-diagnostic" and
       not alias_fix["executable"],
       "an address alias stays diagnostic until the candidate path is replaced")

    print("\nmechanical candidate repair has a narrow write boundary")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "src" / "st" / "test" / "defs.c"
        source.parent.mkdir(parents=True)
        source.write_text("s16 D_us_80180000[] = {1, 2};\n")
        row = {
            "id": "us:ST/TEST:Function", "class": "symbol", "unresolved": [],
            "resolvable": [
                {"invented": "D_us_80180000", "kind": "declaration-definition",
                 "source": "src/st/test/defs.c:1", "executable": True},
                {"invented": "unk24", "kind": "entity-field",
                 "replacement": "zPriority", "executable": False,
                 "requires_candidate_receiver_type": "Entity"},
            ],
        }
        original = "void Function(Entity* self) {\n    self->unk24 = D_us_80180000[0];\n}\n"
        ck(mechanically_repairable(row, original),
           "an Entity parameter proves the receiver type")
        repaired, changes = repair_candidate_text(row, original, root)
        ck("extern s16 D_us_80180000[];" in repaired,
           "a same-overlay definition yields an extern declaration")
        ck("self->zPriority" in repaired and "self->unk24" not in repaired,
           "an exact Entity offset is replaced in candidate text")
        ck(len(changes) == 2, "every applied repair is recorded")
        retained_row = {
            "id": "us:BOSS/BO0:func_us_801B13A8", "class": "symbol",
            "unresolved": [], "resolvable": [data_fix],
        }
        retained_original = (
            "void func_us_801B13A8(void) {\n"
            "    D_us_801A5ED4[0] = 0;\n"
            "}\n")
        retained_fixed, retained_changes = repair_candidate_text(
            retained_row, retained_original)
        ck("extern s32 D_us_801A5ED4[];" in retained_fixed,
           "immutable candidate repair inserts the retained-data declaration")
        ck(len(retained_changes) == 1,
           "the retained-data insertion is recorded")
        wrong = "extern u8 D_us_80180000[];\n" + original
        corrected, corrected_changes = repair_candidate_text(row, wrong, root)
        ck("extern s16 D_us_80180000[];" in corrected and
           "extern u8 D_us_80180000[];" not in corrected,
           "a prior mechanically wrong extern is corrected, not treated as present")
        ck(any("replace extern u8" in change for change in corrected_changes),
           "the declaration correction is recorded")
        primitive = original.replace(
            "Entity* self", "Entity* self, Primitive* prim").replace(
                "self->unk24", "prim->unk24")
        ck(not mechanically_repairable(row, primitive),
           "the same numeric member on Primitive is not an Entity field")
        shadowed = (
            "void Function(Entity* self) {\n"
            "    self->unk24 = 1;\n"
            "    { Primitive* self; self->unk24 = 2; }\n"
            "    // self->unk24 must stay in this comment\n"
            "    Log(\"self->unk24 must stay in this string\");\n"
            "}\n")
        shadow_row = dict(row)
        shadow_row["resolvable"] = [row["resolvable"][1]]
        shadow_fixed, shadow_changes = repair_candidate_text(
            shadow_row, shadowed, root)
        ck("self->zPriority = 1" in shadow_fixed and
           "self->unk24 = 2" in shadow_fixed,
           "only the lexically active Entity receiver is rewritten")
        ck("// self->unk24" in shadow_fixed and
           '"self->unk24' in shadow_fixed,
           "comments and literals are not rewritten")
        ck("1 proven Entity use" in shadow_changes[0],
           "the repair count includes only proven code spans")
        static_source = root / "src" / "st" / "test" / "private.c"
        static_source.write_text(
            "static u8 g_PrivateAnimations[] = {1, 2};\n")
        try:
            declaration_from_source(
                "src/st/test/private.c:1", "g_PrivateAnimations", root)
        except ValueError as exc:
            static_refused = "internal-linkage" in str(exc)
        else:
            static_refused = False
        ck(static_refused,
           "a cross-translation-unit static definition cannot yield extern")
        retract_row = {
            "id": "us:ST/TEST:Function", "class": "symbol", "unresolved": [],
            "resolvable": [_internal_linkage_fix(
                "g_PrivateAnimations", "src/st/test/private.c:1")],
        }
        unsafe = (_GENERATED_MARKER + "\n" +
                  "extern u8 g_PrivateAnimations[];\n\n" + original)
        retracted, retract_changes = repair_candidate_text(
            retract_row, unsafe, root)
        ck("extern u8 g_PrivateAnimations[];" not in retracted and
           _GENERATED_MARKER not in retracted,
           "an earlier generated static-derived extern is retracted")
        ck("retract unsafe generated" in retract_changes[0],
           "the retraction is recorded as evidence")
        interpretive = dict(row)
        interpretive["resolvable"] = [{
            "invented": "unk29", "kind": "entity-offset-diagnostic",
            "executable": False}]
        ck(not mechanically_repairable(interpretive),
           "inside-field diagnostics are refused")
        unverified = dict(row)
        unverified["resolvable"] = [{
            "invented": "RIC_posX_i_hi", "kind": "struct-path-unverified",
            "executable": False}]
        ck(not mechanically_repairable(unverified),
           "unverified struct paths are refused")
        mixed = dict(row)
        mixed["unresolved"] = ["still_needs_analysis"]
        mixed["resolvable"] = row["resolvable"] + [{
            "invented": "RIC_zPriority", "kind": "struct-path-unverified",
            "executable": False}]
        subset = mechanical_subset(mixed, original)
        ck(len(subset["resolvable"]) == 2 and not subset["unresolved"],
           "proven fixes are preserved as a mechanical subset when work remains")

    print("\na declaration in another overlay is not evidence")
    ck(_cross_overlay("us:ST/RNO0:EntityBladeSoldierDeathParts",
                      "src/boss/rbo5/unk_4648C.c:3976"),
       "rno0 record vs an rbo5 declaration is cross-overlay")
    ck(not _cross_overlay("us:BOSS/BO6:BO6_CheckHighJumpInput",
                          "src/boss/bo6/us_39144.c:15"),
       "bo6 record vs a bo6 declaration is NOT cross-overlay")
    ck(not _cross_overlay("us:ST/RNO0:func_801C7884", "src/st/e_collect.h:12"),
       "a shared src/st header belongs to no overlay, so it is not cross")
    ck(_overlay_of("src/st/rno0/e_misc.c") == "rno0", "overlay parsed from path")
    ck(_overlay_of("us:BOSS/BO0:func_x") == "bo0", "overlay parsed from queue id")

    print("\nC89 declaration-after-statement is not a field-name problem")
    print("\na quality reject can go stale when the PROMPT is fixed")
    ill = "quality reject: uses `ext.ILLEGAL`; prefer the named ext variant"
    ck(bool(stale_quality_reason(ill)),
       "an ILLEGAL reject is stale after #82")
    ck("#82" in stale_quality_reason(ill),
       "and the reason cites the change that invalidated it")
    rows_q = triage([{"id": "us:BOSS/BO0:f", "note": ill}])
    ck(rows_q[0]["class"] == "quality-stale",
       f"triage promotes it to quality-stale ({rows_q[0]['class']})")
    ck("requeue as todo" in rows_q[0]["action"], "and says to requeue it")

    print("\nbut a CURRENT style defect is not stale and is not requeued")
    mask = ("quality reject: `self->drawFlags |= 0x20` should use the named "
            "constant ENTITY_MASK_G")
    ck(stale_quality_reason(mask) == "", "no stale rule matches it")
    rows_m = triage([{"id": "us:ST/RCHI:EntitySlogra", "note": mask}])
    ck(rows_m[0]["class"] == "quality", f"stays quality ({rows_m[0]['class']})")
    ck("rework" in rows_m[0]["action"],
       "and the action says rework, not requeue")
    ck("quality" not in REQUEUE_TO,
       "a live quality reject is NOT in the requeue table")
    ck(REQUEUE_TO.get("quality-stale") == "todo",
       "while a stale one is")

    print("\nan own-overlay DEFINITION beats a cross-overlay declaration")
    # The EntityGaibonLeg shape. `extern ... g_EInitGaibon` exists only in
    # src/st/nz0/nz0.h, a different overlay, so the cross-overlay guard
    # correctly refused it and then stopped -- never looking at
    # src/st/rchi/e_init.c:96 where RCHI defines its own.
    if (REPO / "src" / "st" / "rchi").is_dir():
        rows_g = triage([{
            "id": "us:ST/RCHI:EntityGaibonLeg",
            "note": "BUILD FAILED: src/st/rchi/e_gaibon.c:12: "
                    "`g_EInitGaibon' undeclared (first use this function)"}])
        fx = rows_g[0]["resolvable"]
        ck(bool(fx), f"it resolves instead of going unresolved ({rows_g[0]})")
        if fx:
            ck("rchi" in fx[0]["likely"],
               f"and points at RCHI's own definition ({fx[0]['likely']})")
            ck("nz0" not in fx[0]["likely"],
               "not at nz0's extern, which would name a different object")
        ck(not rows_g[0]["unresolved"],
           f"and nothing is left unresolved ({rows_g[0]['unresolved']})")

    print("\nthe cross-overlay refusal still stands when there is no local one")
    # Retraction check. The audit claimed the guard covered only raw D_us_
    # names; it never did, it covers every symbol. What it lacked was the
    # local-definition fallback above. Both halves are pinned here.
    src_esc0 = Path(__file__).read_text(errors="ignore")
    tb = src_esc0.split("def triage(")[1].split("\ndef ")[0]
    ck("_cross_overlay(rec[\"id\"], where)" in tb,
       "the guard is applied to every symbol, not a D_us_ subset")
    ck(tb.index("defines_in_own_overlay") < tb.index("_cross_overlay"),
       "and the local definition is looked up BEFORE the refusal is written")
    ck("only declared in another overlay" in tb,
       "the refusal message still exists for the no-local-definition case")

    print("\nfree of model cost is not the same as free of work")
    # The first dry run offered to requeue two `harness` records whose own
    # action says "fix the harness, THEN requeue as todo". Sending them back
    # before the stub lookup is fixed just re-escalates them.
    ck("harness" not in REQUEUE_TO,
       "harness is not auto-requeued; its own action says fix it first")
    ck("harness" in REQUEUE_BLOCKED_ON_WORK,
       "it is reported as blocked-on-work instead of silently dropped")
    ck("quality" in REQUEUE_BLOCKED_ON_WORK,
       "and so is a live quality reject")
    ck(not (set(REQUEUE_TO) & set(REQUEUE_BLOCKED_ON_WORK)),
       "no class is in both tables")

    print("\nrequeue writes through the scheduler and is a dry run by default")
    src_esc = Path(__file__).read_text(errors="ignore")
    rq = src_esc.split("def requeue(")[1].split("\n# ---")[0]
    ck("scheduler.py" in rq, "writes go through scheduler.py")
    ck('"report"' in rq, "using the report subcommand, which exists")
    ck('"set"' not in rq,
       "not the `set` that deferred_triage advertised for months and that "
       "no scheduler has ever had")
    ck("if not apply:" in rq, "and nothing is written without --apply")
    ck(set(REQUEUE_TO.values()) == {"todo"},
       f"only todo is reachable ({sorted(set(REQUEUE_TO.values()))})")

    c89 = ("BUILD FAILED: us_3E79C.c:1070: parse error before `swapTarget' "
           "us_3E79C.c:1074: `swapTarget' undeclared (first use this function)")
    ck(is_c89_declaration_error(c89),
       "parse-error + undeclared on an unknown name is the C89 error")
    ck(classify(c89) == "symbol",
       "  classify() alone still calls it symbol (triage promotes it)")
    notc89 = "BUILD FAILED: richter.c:25: `RIC_step' undeclared"
    ck(not is_c89_declaration_error(notc89),
       "a real-but-undeclared symbol is NOT the C89 error")
    ck(not is_c89_declaration_error("attempt 4 timed out"),
       "a note with no parse error is not the C89 error")

    print("\nflat-name resolution, and its guard")
    known = {"RIC", "PLAYER"}
    ck(suggest_struct_path("RIC_posX_i_hi", known) == "RIC.posX.i.hi",
       "RIC_posX_i_hi -> RIC.posX.i.hi")
    ck(suggest_struct_path("RIC_step", known) == "RIC.step",
       "RIC_step -> RIC.step")
    ck(suggest_struct_path("some_random_local", known) is None,
       "an unknown head is NOT rewritten (the guard that stops noise)")
    ck(suggest_struct_path("RIC", known) is None,
       "a bare name with no underscore yields nothing")

    print("\nheads that CONTAIN an underscore, which is most of the tree")
    # This took parts[0], so the head of `g_GpuBuffers_0_draw_g0` was "g".
    # Every global here is named g_something, so the resolver only ever
    # worked for RIC and PLAYER -- the two names it was tested on.
    # func_us_801B3368 sat in "needs a human: names not resolvable" the whole
    # time, for a name that resolves mechanically.
    gk = {"g_GpuBuffers", "g_Ric", "PLAYER"}
    ck(suggest_struct_path("g_GpuBuffers_0_draw_g0", gk)
       == "g_GpuBuffers[0].draw.g0",
       f"g_GpuBuffers_0_draw_g0 -> g_GpuBuffers[0].draw.g0 "
       f"({suggest_struct_path('g_GpuBuffers_0_draw_g0', gk)})")
    ck(suggest_struct_path("g_Ric_step", gk) == "g_Ric.step",
       "and a two-part head with no index")

    print("\na PURELY numeric part is a subscript; a trailing digit is not")
    # g_GpuBuffers is GpuBuffer[2] (include/game.h:2149), so the 0 indexes it.
    # `g0` is a DRAWENV member and must survive as one -- turning it into
    # `g[0]` would be a confident wrong answer, which is worse than none.
    ck("[0]" in (suggest_struct_path("g_GpuBuffers_0_draw_g0", gk) or ""),
       "the index becomes a subscript")
    ck((suggest_struct_path("g_GpuBuffers_0_draw_g0", gk) or "").endswith(".g0"),
       "while g0 stays a member")

    print("\nthe longest known head wins, so a prefix cannot shadow it")
    ck(suggest_struct_path("g_GpuBuffers_0_draw_g0", gk | {"g"})
       == "g_GpuBuffers[0].draw.g0",
       "g_GpuBuffers beats a bare g even when both are known")

    print()
    if fails:
        print(f"{len(fails)} FAILED")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default="")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--notes-file", default="",
                    help="classify notes captured elsewhere, one 'id | note' "
                         "per line. Use when the live queue is only reachable "
                         "from another environment (see queue_is_snapshot).")
    ap.add_argument("--requeue", action="store_true",
                    help="requeue the classes that are not a verdict on the "
                         "code (harness, nocode, c89, quality-stale). "
                         "DRY RUN unless --apply is also given")
    ap.add_argument("--repair-candidates", action="store_true",
                    help="repair only fully mechanical symbol failures in "
                         "preserved rejected candidates. DRY RUN unless "
                         "--apply is also given; never edits src/ or the queue")
    ap.add_argument("--resolve-symbols", action="store_true",
                    help="append evidence-backed real/quality dispositions to "
                         "current symbol escalations; dry run unless --apply")
    ap.add_argument("--apply", action="store_true",
                    help="apply the selected write mode")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    modes = sum(bool(mode) for mode in
                (a.requeue, a.repair_candidates, a.resolve_symbols))
    if modes > 1:
        print("choose exactly one write mode", file=sys.stderr)
        return 2
    if a.apply and not modes:
        print("--apply does nothing on its own", file=sys.stderr)
        return 2

    if a.notes_file:
        recs = []
        for line in Path(a.notes_file).read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            rid, _, note = line.partition("|")
            recs.append({"id": rid.strip(), "note": note.strip()})
        print(f"classifying {len(recs)} record(s) from {a.notes_file}\n")
    else:
        stamp = queue_is_snapshot()
        if stamp:
            print("REFUSING: the queue this environment sees is a READ-ONLY "
                  "SNAPSHOT, not the live queue.", file=sys.stderr)
            print(f"  {stamp}", file=sys.stderr)
            print("Triaging it would report on records nobody is working. Run "
                  "this where the live queue is, or pass --notes-file with "
                  "output captured from there.", file=sys.stderr)
            return 2
        recs = read_escalated()
    rows = triage(recs)
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=2))
        print(f"wrote {a.json}")

    counts = Counter(r["class"] for r in rows)
    print(f"{len(rows)} escalated record(s)\n")
    for cls in ("harness", "nocode", "c89", "quality-stale", "quality",
                "symbol", "real", "unknown"):
        if counts.get(cls):
            print(f"  {cls:14} {counts[cls]:3d}")
    print()
    free = sum(counts.get(c, 0) for c in REQUEUE_TO)
    blocked_n = sum(counts.get(c, 0) for c in REQUEUE_BLOCKED_ON_WORK)
    print(f"{free} of {len(rows)} can be requeued right now with no model "
          f"call.")
    if blocked_n:
        # Distinguished on purpose: these are also not decompilation
        # problems, but requeueing one before its code change just sends it
        # back to the same wall.
        print(f"{blocked_n} more are not decompilation problems either, but "
              f"need a code change first\n(see the blocked-on-work list under "
              f"--requeue).")
    print()
    print("=" * 78)
    for r in sorted(rows, key=lambda x: x["class"]):
        print(f"\n[{r['class']}] {r['id']}")
        print(f"  action: {r['action']}")
        for f in r["resolvable"]:
            print(f"    {f['invented']}  ->  {f['likely']}     ({f['why']})")
        if r["unresolved"]:
            print(f"    unresolved: {', '.join(r['unresolved'][:6])}")

    if a.repair_candidates:
        return repair_candidates(rows, apply=a.apply)
    if a.resolve_symbols:
        if a.notes_file:
            print("\n--resolve-symbols needs complete live queue records.",
                  file=sys.stderr)
            return 2
        return resolve_symbols(rows, recs, apply=a.apply)
    if a.requeue:
        if a.notes_file:
            print("\n--requeue needs the live queue; it is meaningless "
                  "against --notes-file.", file=sys.stderr)
            return 2
        return requeue(rows, apply=a.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
