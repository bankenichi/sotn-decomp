#!/usr/bin/env python3
"""Which functions we are still fighting has upstream already decompiled?

WHY THIS EXISTS
    On 2026-08-09 the fork was 56 commits and 1,061 files behind upstream
    (+47,188/-14,397). A merge of that size is a long, risky operation that
    would invalidate the queue mid-flight, and most of it is Saturn, PSP and
    asset tooling this fork does not touch.

    But buried in it is the thing that matters most: upstream has decompiled
    functions THIS FORK IS STILL SPENDING MODEL TIME ON. `RNO0 e_breakable`
    (#3468) landed upstream on 2026-08-02; our fleet burned four attempts and
    a build cycle failing that same file on 2026-08-09.

    A function upstream has already matched is not a decompilation problem for
    us. It is a copy, and the build says whether the copy is right.

WHAT THIS DOES
    For every unmatched record in the queue, asks whether upstream/master has
    a REAL definition rather than an INCLUDE_ASM stub, and reports the ones it
    does. The default report is read-only. `--publish <record-id> --apply`
    substitutes only that definition into the target translation unit and
    publishes the complete, declaration-ready result into the immutable
    candidate store. It never edits src/, builds or mutates the queue.

WHY IT SHELLS OUT TO GIT
    The comparison is against a ref, not the working tree, so `search_repo`
    and the filesystem cannot answer it. This runs on the machine that owns
    the repo (via run_analysis), never in the sandbox.

NOT A MATCH ORACLE
    Upstream's C is written against upstream's headers. It may not compile
    here, and compiling is not matching. Every harvested function still has to
    go through apply -> build -> verify like anything else. This only says
    where it is worth looking.

Usage:
    python3 automation/upstream_harvest.py
    python3 automation/upstream_harvest.py --overlay rno0
    python3 automation/upstream_harvest.py --show <function>
    python3 automation/upstream_harvest.py --overlay ST/RNO0 \
        --publish <function> --apply
    python3 automation/upstream_harvest.py --self-test
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYTHON = str(REPO / ".venv" / "bin" / "python")
if not Path(PYTHON).exists():                                # pragma: no cover
    PYTHON = sys.executable

UPSTREAM = "upstream/master"
ARTIFACT_SCHEMA = "upstream-harvest-v3-us-conditional-extraction"
_UPSTREAM_COMMIT = ""

sys.path.insert(0, str(REPO / "automation"))
from artifact_store import candidate_path, publish_versioned_artifact  # noqa: E402

# A definition, not a declaration and not a stub.
RX_INCLUDE_ASM = re.compile(r'INCLUDE_ASM\([^)]*?,\s*(\w+)\s*\)')


def _git(*args: str, timeout: int = 120) -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True,
                           timeout=timeout, cwd=str(REPO))
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def upstream_commit() -> str:
    """Resolve the moving upstream name once, then use its immutable object ID."""
    global _UPSTREAM_COMMIT
    if not _UPSTREAM_COMMIT:
        value = _git("rev-parse", UPSTREAM).strip()
        if re.fullmatch(r"[0-9a-fA-F]{40}", value):
            _UPSTREAM_COMMIT = value.lower()
    return _UPSTREAM_COMMIT


def artifact_is_current(text: str, record_id: str, path: str,
                        commit: str) -> bool:
    """Only immutable source provenance may satisfy batch resume."""
    def exact_line(label: str, value: str) -> bool:
        return bool(re.search(
            rf"(?m)^\s*{re.escape(label)}\s*:\s*{re.escape(value)}\s*$",
            text))

    return (bool(commit)
            and exact_line("method", "METHOD=UPSTREAM-HARVEST")
            and exact_line("generator", ARTIFACT_SCHEMA)
            and exact_line("record", record_id)
            and exact_line("source", f"{commit}:{path}"))


def unmatched_records() -> list[tuple[str, str, str]]:
    """(id, overlay, function) for everything not matched, via the scheduler."""
    out = []
    for status in ("todo", "escalated", "deferred", "near"):
        r = subprocess.run(
            [PYTHON, str(REPO / "automation" / "scheduler.py"),
             "list", "--status", status],
            capture_output=True, text=True, timeout=180, cwd=str(REPO))
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line.startswith(status):
                continue
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            rid = parts[2].partition("|")[0].strip()
            bits = rid.split(":")
            if len(bits) >= 3:
                out.append((rid, bits[1], bits[2]))
    return out


_UF_CACHE: dict[str, dict[str, str]] = {}
_UF_PATHS: dict[str, list[str]] | None = None
_US_CACHE: set[str] | None = None


def upstream_files(overlay_hint: str = "") -> dict[str, str]:
    """{function name: upstream path} for every real definition upstream has.

    One `git grep` over the ref rather than a show per file: the per-file
    version is hundreds of subprocesses and minutes of wall clock.
    """
    # CACHED. Each call is a git grep over the whole upstream tree, roughly
    # 30 seconds. transplant --scan asks per record, so without this a scan of
    # 250 records spends over two hours re-reading the same ref.
    global _UF_PATHS
    if overlay_hint in _UF_CACHE:
        return _UF_CACHE[overlay_hint]
    if _UF_PATHS is None:
        # `git grep -n` over a ref searches that ref's tree without checking it
        # out. Preserve every path: the first global definition may be a
        # structurally different shared helper while the target overlay has its
        # own exact body.
        pattern = r"^[A-Za-z_][A-Za-z0-9_ \t*]*\b\w+\s*\("
        ref = upstream_commit()
        raw = _git("grep", "-nE", pattern, ref, "--", "src/", timeout=300)
        paths: dict[str, list[str]] = {}
        rx = re.compile(
            r"^[^:]+:(?P<path>[^:]+):\d+:"
            r"[A-Za-z_][A-Za-z0-9_ \t*]*?\b(?P<fn>\w+)\s*\([^;]*$")
        for line in raw.splitlines():
            m = rx.match(line)
            if not m:
                continue
            paths.setdefault(m.group("fn"), []).append(m.group("path"))
        _UF_PATHS = paths
    token = overlay_hint.rsplit("/", 1)[-1].lower()
    defs: dict[str, str] = {}
    for fn, paths in _UF_PATHS.items():
        if token:
            exact = [path for path in paths
                     if f"/{token}/" in f"/{path.lower()}/"]
            if exact:
                defs[fn] = exact[0]
        elif paths:
            defs[fn] = paths[0]
    _UF_CACHE[overlay_hint] = defs
    return defs


def upstream_stubs() -> set[str]:
    """Functions upstream still has as INCLUDE_ASM, i.e. NOT decompiled."""
    global _US_CACHE
    if _US_CACHE is None:
        raw = _git("grep", "-hE", "INCLUDE_ASM", upstream_commit(), "--", "src/",
                   timeout=300)
        _US_CACHE = set(RX_INCLUDE_ASM.findall(raw))
    return _US_CACHE


def harvest_path(base: str, overlay: str = "") -> str:
    """Return a real upstream definition, preferring the exact overlay.

    A same-named INCLUDE_ASM in some other overlay is irrelevant. The former
    global stub veto hid common functions such as EntityBreakable even when
    the target overlay itself already had a concrete definition upstream.
    """
    return upstream_files(overlay).get(base) or upstream_files().get(base, "")


def harvest(overlay: str = "") -> list[tuple[str, str, str]]:
    """(function, our overlay, upstream path) worth copying."""
    recs = unmatched_records()
    if overlay:
        recs = [r for r in recs if overlay.lower() in r[1].lower()]
    out = []
    for _rid, ovl, fn in recs:
        # Strip the `_from_<overlay>` suffix the queue adds for shimmed stubs;
        # upstream names the function without it.
        base = re.sub(r"_from_\w+$", "", fn)
        path = harvest_path(base, ovl)
        if path:
            out.append((base, ovl, path))
    return sorted(set(out))


def report(overlay: str = "") -> int:
    ref = _git("rev-parse", "--short", UPSTREAM).strip()
    if not ref:
        print(f"cannot resolve {UPSTREAM}; run git_fetch first")
        return 1
    behind = _git("rev-list", "--count", f"HEAD..{UPSTREAM}").strip()
    print(f"upstream/master {ref}, {behind} commits ahead of HEAD\n")

    rows = harvest(overlay)
    if not rows:
        print("nothing to harvest: upstream has no definition for any "
              "function we are still missing")
        return 0
    print(f"{len(rows)} unmatched function(s) upstream HAS decompiled\n")
    print(f"{'function':34}{'our overlay':16}upstream path")
    print("-" * 96)
    for fn, ovl, path in rows:
        print(f"{fn[:32]:34}{ovl[:14]:16}{path}")
    print("\nEach still has to survive apply -> build -> verify here:")
    print("upstream's C is written against upstream's headers, and compiling")
    print("is not matching. This says where to look, not what is true.")
    # REPEATED AT THE END. The header counts are the answer, and every caller
    # reading this through the connector sees only the TAIL -- a long list
    # pushes the count out of view, which is exactly what happened to
    # matched_audit and cost a whole diagnosis to a list with no header.
    by_ovl: dict[str, int] = {}
    for _fn, ovl, _p in rows:
        by_ovl[ovl] = by_ovl.get(ovl, 0) + 1
    spread = "  ".join(f"{o} {n}" for o, n in sorted(by_ovl.items()))
    print(f"\nSUMMARY  {len(rows)} harvestable  from upstream/master {ref} "
          f"({behind} commits ahead)  |  {spread}")
    return 0


def show(fn: str) -> int:
    defs = upstream_files()
    base = re.sub(r"_from_\w+$", "", fn)
    path = defs.get(base)
    if not path:
        print(f"upstream has no definition for {base}")
        return 1
    ref = upstream_commit()
    body = _git("show", f"{ref}:{path}")
    if not body:
        print(f"could not read {path} at {UPSTREAM}")
        return 1
    print(f"=== {UPSTREAM}:{path} ===\n")
    print(body)
    return 0


def _candidate_body(source: str, base: str, target: str) -> str:
    """Extract one body with the visibility required by a live queue symbol."""
    body = _extract(source, base)
    if not body:
        return ""
    if target != base:
        body = re.sub(rf"\b{re.escape(base)}\b", target, body)
    # Upstream may make a helper static after decompiling every caller into the
    # same translation unit. This fork can still have assembly callers in other
    # objects, and an INCLUDE_ASM queue symbol must retain external visibility
    # until those callers move. Static changes no function instructions, but it
    # makes the partial-tree linker unable to satisfy the preserved call.
    body = re.sub(r"(?m)^static\s+(?=[A-Za-z_])", "", body, count=1)
    return body


def publish(record_id: str, apply: bool = False,
            records: dict[str, tuple[str, str]] | None = None) -> int:
    """Publish one exact upstream definition as immutable candidate evidence."""
    if records is None:
        records = {
            rid: (overlay, fn) for rid, overlay, fn in unmatched_records()
        }
    if record_id not in records:
        print("record is not an exact unmatched queue id")
        return 1
    overlay, fn = records[record_id]
    base = re.sub(r"_from_\w+$", "", fn)
    path = harvest_path(base, overlay)
    if not path:
        print(f"upstream has no definition for {base}")
        return 1
    ref = upstream_commit()
    if not ref:
        print(f"cannot resolve {UPSTREAM}; run git_fetch first")
        return 1
    source = _git("show", f"{ref}:{path}")
    body = _candidate_body(source, base, fn)
    if not body:
        print(f"could not extract {base} from {path}")
        return 1
    import permuter_supervisor as ps  # type: ignore
    found = ps.find_stub(fn, overlay)
    if found is None:
        print(f"no exact live INCLUDE_ASM stub for {record_id}")
        return 1
    target_path, asm_rel, _stub = found
    target_rel = target_path.resolve().relative_to(REPO.resolve()).as_posix()
    sys.path.insert(0, str(REPO / "automation" / "win"))
    import worker_direct as wd  # type: ignore
    ctx = {"src_rel": target_rel, "asm_rel": asm_rel}
    whole = wd.virtual_apply(ctx, fn, body)
    if not whole:
        print(f"candidate no longer replaces the exact stub in {target_rel}")
        return 1
    # The published seed is a complete translation unit. Scan that complete
    # unit too: pre-existing C functions can retain C89 implicit calls which
    # compile in the game build but leave decomp-permuter's typemap incomplete.
    whole = wd._declare_stub_siblings(whole, whole)
    provenance = (
        "/* UPSTREAM CANDIDATE -- complete target translation unit.\n"
        "   method : METHOD=UPSTREAM-HARVEST\n"
        f"   generator: {ARTIFACT_SCHEMA}\n"
        f"   record : {record_id}\n"
        f"   upstream: {UPSTREAM}\n"
        f"   source : {ref}:{path}\n"
        f"   target : {target_rel}\n"
        "   content: WHOLE FILE (stub substituted, declarations complete)\n"
        "   verdict: candidate evidence only; isolated score and verify_build "
        "remain required. */\n")
    artifact = provenance + whole
    stable = candidate_path(record_id, REPO)
    print(f"record: {record_id}")
    print(f"source: {ref}:{path}")
    print(f"target: {target_rel}")
    print(f"stable: {stable.relative_to(REPO).as_posix()}")
    if not apply:
        print("dry run: re-run with --apply to publish immutable evidence")
        return 0
    version = publish_versioned_artifact(
        stable, artifact, "upstream candidate", REPO)
    print(f"immutable: {version}")
    return 0


def _replace_existing_function(whole: str, fn: str, body: str) -> str:
    """Replace one uniquely owned live definition without touching its neighbors."""
    current = _extract(whole, fn)
    if not current:
        return ""
    starts = [match.start() for match in re.finditer(re.escape(current), whole)]
    if len(starts) != 1:
        return ""
    start = starts[0]
    return whole[:start] + body + whole[start + len(current):]


def republish_artifact(path_text: str, apply: bool = False) -> int:
    """Refresh upstream evidence after its queue record has already closed."""
    artifact_path = (REPO / path_text).resolve()
    try:
        artifact_path.relative_to(REPO.resolve())
    except ValueError:
        print("republish artifact must stay inside the repository")
        return 1
    text = artifact_path.read_text(encoding="utf-8", errors="replace")
    provenance = _ARTIFACT_PROVENANCE_RE.search(text)
    target_match = re.search(r"(?m)^\s*target\s*:\s*(\S+)\s*$", text)
    if not provenance or not target_match:
        print("artifact lacks complete upstream record/source/target provenance")
        return 1
    record_id, _recorded_ref, source_path = provenance.groups()
    stable = candidate_path(record_id, REPO).resolve()
    if artifact_path != stable:
        print("republish accepts only the exact stable artifact path")
        return 1
    target_rel = target_match.group(1)
    target_path = (REPO / target_rel).resolve()
    try:
        target_path.relative_to(REPO.resolve())
    except ValueError:
        print("artifact target escapes the repository")
        return 1
    fn = record_id.rsplit(":", 1)[-1]
    base = re.sub(r"_from_\w+$", "", fn)
    ref = upstream_commit()
    if not ref:
        print(f"cannot resolve {UPSTREAM}; run git_fetch first")
        return 1
    source = _git("show", f"{ref}:{source_path}")
    body = _candidate_body(source, base, fn)
    if not body:
        print(f"could not extract {base} from {source_path} at {ref}")
        return 1

    whole = target_path.read_text(encoding="utf-8", errors="replace")
    replaced = _replace_existing_function(whole, fn, body)
    if not replaced:
        import permuter_supervisor as ps  # type: ignore
        overlay = record_id.split(":", 2)[1]
        found = ps.find_stub(fn, overlay)
        if found is None:
            print("target has neither one owned definition nor an exact live stub")
            return 1
        _target_path, asm_rel, _stub = found
        sys.path.insert(0, str(REPO / "automation" / "win"))
        import worker_direct as wd  # type: ignore
        replaced = wd.virtual_apply(
            {"src_rel": target_rel, "asm_rel": asm_rel}, fn, body)
    sys.path.insert(0, str(REPO / "automation" / "win"))
    import worker_direct as wd  # type: ignore
    replaced = wd._declare_stub_siblings(replaced, replaced)
    header = (
        "/* UPSTREAM CANDIDATE -- complete target translation unit.\n"
        "   method : METHOD=UPSTREAM-HARVEST\n"
        f"   generator: {ARTIFACT_SCHEMA}\n"
        f"   record : {record_id}\n"
        f"   upstream: {UPSTREAM}\n"
        f"   source : {ref}:{source_path}\n"
        f"   target : {target_rel}\n"
        "   content: WHOLE FILE (definition refreshed, declarations complete)\n"
        "   verdict: candidate evidence only; isolated score and verify_build "
        "remain required. */\n")
    print(f"record: {record_id}\nsource: {ref}:{source_path}\ntarget: {target_rel}")
    if not apply:
        print("dry run: re-run with --apply to publish immutable evidence")
        return 0
    version = publish_versioned_artifact(
        stable, header + replaced, "upstream candidate", REPO)
    print(f"immutable: {version}")
    return 0


def publish_ids(data: object) -> list[str]:
    """Normalize either supported batch-input shape to exact queue IDs."""
    ids = list(data) if isinstance(data, dict) else data
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise ValueError(
            "publish-file must be a JSON object keyed by ID or a list of IDs")
    return ids


def publish_file(path_text: str, apply: bool = False,
                 overlay: str = "") -> int:
    """Publish every harvestable unmatched ID named by one JSON input.

    The normal priority map is an object keyed by exact queue ID. A JSON list
    of IDs is accepted as well. Keeping the process alive matters: the
    upstream definition index and worker declaration indexes each take tens of
    seconds to build, while publishing sixty records one process at a time
    rebuilds both sixty times.
    """
    path = (REPO / path_text).resolve()
    try:
        path.relative_to(REPO.resolve())
    except ValueError:
        print("publish-file must stay inside the repository")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"could not read publish-file: {exc}")
        return 1
    try:
        ids = publish_ids(data)
    except ValueError as exc:
        print(exc)
        return 1

    ref = upstream_commit()
    if not ref:
        print(f"cannot resolve {UPSTREAM}; run git_fetch first")
        return 1

    records = {
        rid: (record_overlay, fn)
        for rid, record_overlay, fn in unmatched_records()
    }
    selected = [rid for rid in ids if rid in records]
    if overlay:
        selected = [
            rid for rid in selected
            if overlay.lower() in records[rid][0].lower()
        ]

    # Resume safely after interruption without manufacturing duplicate immutable
    # generations. Only the exact current upstream provenance qualifies.
    remaining: list[str] = []
    resumed = 0
    for record_id in selected:
        record_overlay, fn = records[record_id]
        base = re.sub(r"_from_\w+$", "", fn)
        source = harvest_path(base, record_overlay)
        stable = candidate_path(record_id, REPO)
        if source and stable.is_file():
            text = stable.read_text(encoding="utf-8", errors="replace")
            if artifact_is_current(text, record_id, source, ref):
                resumed += 1
                continue
        remaining.append(record_id)

    # Complete-file candidate generation asks worker_direct for declarations.
    # Prewarm its declaration cache with the union of every remaining body, so
    # the batch scans src/include in bounded chunks instead of once per record.
    if remaining:
        sys.path.insert(0, str(REPO / "automation" / "win"))
        import worker_direct as wd  # type: ignore
        source_cache: dict[str, str] = {}
        called: list[str] = []
        for record_id in remaining:
            record_overlay, fn = records[record_id]
            base = re.sub(r"_from_\w+$", "", fn)
            source = harvest_path(base, record_overlay)
            if not source:
                continue
            if source not in source_cache:
                source_cache[source] = _git("show", f"{ref}:{source}")
            source_text = source_cache[source]
            body = _candidate_body(source_text, base, fn)
            for name in wd._RX_CALL.findall(wd._strip_comments_and_strings(body)):
                if name not in wd._NOT_CALLS and not name.isupper() and name not in called:
                    called.append(name)
        for start in range(0, len(called), 40):
            wd.lookup_declarations(called[start:start + 40])

    attempted = published = skipped = failed = 0
    for record_id in remaining:
        record_overlay, fn = records[record_id]
        base = re.sub(r"_from_\w+$", "", fn)
        source = harvest_path(base, record_overlay)
        if not source:
            skipped += 1
            continue
        attempted += 1
        print(f"\n[{attempted}] {record_id}", flush=True)
        rc = publish(record_id, apply, records)
        if rc:
            failed += 1
        else:
            published += 1
    print(f"\nSUMMARY {published} published, {resumed} already current, "
          f"{skipped} not harvestable, {failed} failed from "
          f"{len(selected)} selected unmatched IDs")
    return 1 if failed else 0


_ARTIFACT_PROVENANCE_RE = re.compile(
    r"method\s*:\s*METHOD=UPSTREAM-HARVEST.*?"
    r"record\s*:\s*(\S+).*?source\s*:\s*([^:\s]+(?:/[^:\s]+)*):([^\s]+)",
    re.DOTALL)
_PERMUTER_DECL_BLOCK_RE = re.compile(
    r"\n?/\* Added by the permuter-seed writer\..*?"
    r"/\* End permuter-seed writer declarations\. \*/\n?",
    re.DOTALL)


def _normalize_provenance_candidate(text: str) -> tuple[str, list[str]]:
    """Remove only deterministic publication scaffolding before body lineage."""
    clean, count = _PERMUTER_DECL_BLOCK_RE.subn("\n", text)
    transforms = (["removed permuter-seed writer declaration block",
                   "canonicalized nonliteral whitespace for lineage comparison"]
                  if count else [])
    return clean, transforms


def _canonical_c_whitespace(text: str) -> str:
    """Collapse whitespace outside literals/comments without changing tokens."""
    out: list[str] = []
    state = "code"
    pending_space = False
    index = 0
    while index < len(text):
        char = text[index]
        pair = text[index:index + 2]
        if state == "code":
            if pair == "//":
                if pending_space and out:
                    out.append(" ")
                pending_space = False
                out.append(pair)
                state = "line-comment"
                index += 2
                continue
            if pair == "/*":
                if pending_space and out:
                    out.append(" ")
                pending_space = False
                out.append(pair)
                state = "block-comment"
                index += 2
                continue
            if char in ('"', "'"):
                if pending_space and out:
                    out.append(" ")
                pending_space = False
                out.append(char)
                state = "string" if char == '"' else "char"
            elif char.isspace():
                pending_space = True
            else:
                if pending_space and out:
                    out.append(" ")
                pending_space = False
                out.append(char)
        else:
            out.append(char)
            if char == "\\" and state in ("string", "char") and index + 1 < len(text):
                index += 1
                out.append(text[index])
            elif state == "line-comment" and char == "\n":
                state = "code"
                pending_space = True
            elif state == "block-comment" and pair == "*/":
                index += 1
                out.append("/")
                state = "code"
            elif (state == "string" and char == '"') or (
                    state == "char" and char == "'"):
                state = "code"
        index += 1
    return "".join(out).strip()


def _commit_candidates(path: str, head: str) -> list[str]:
    """Enumerate history only through the manifest's pinned upstream head."""
    commits = [head] if head else []
    history = _git("log", "--format=%H", head, "--", path, timeout=300)
    for commit in history.splitlines():
        commit = commit.strip().lower()
        if re.fullmatch(r"[0-9a-f]{40}", commit) and commit not in commits:
            commits.append(commit)
    return commits


def write_provenance_manifest(path_text: str) -> int:
    """Map every harvested artifact hash to immutable upstream provenance.

    Older evidence headers named the moving `upstream/master` ref. Immutable
    history must not be rewritten, so this independently extracts each recorded
    function and finds the exact upstream commit/path that reproduces its body.
    """
    output = (REPO / path_text).resolve()
    try:
        output.relative_to(REPO.resolve())
    except ValueError:
        print("provenance manifest must stay inside the repository")
        return 1
    preferred = upstream_commit()
    if not preferred:
        print(f"cannot resolve {UPSTREAM}; run git_fetch first")
        return 1

    source_cache: dict[tuple[str, str], str] = {}
    commit_cache: dict[str, list[str]] = {}
    match_cache: dict[tuple[str, str, str, str], str] = {}
    records, unclassified = [], []
    candidates_root = REPO / "automation" / "candidates"
    for artifact in sorted(candidates_root.rglob("*.c")):
        text = artifact.read_text(encoding="utf-8", errors="replace")
        match = _ARTIFACT_PROVENANCE_RE.search(text)
        if not match:
            continue
        record_id, recorded_ref, source_path = match.groups()
        function = record_id.rsplit(":", 1)[-1]
        base = re.sub(r"_from_\w+$", "", function)
        normalized_text, transformations = _normalize_provenance_candidate(text)
        artifact_body = _extract(text, function)
        body = _extract(normalized_text, function)
        artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
        body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest() if body else ""
        cache_key = (source_path, base, function, body_sha)
        commit = match_cache.get(cache_key, "")
        ancestor_commit = ""
        ancestor_body = ""
        if body and not commit:
            if re.fullmatch(r"[0-9a-fA-F]{40}", recorded_ref):
                commits = [recorded_ref.lower()]
            else:
                commits = commit_cache.setdefault(
                    source_path, _commit_candidates(source_path, preferred))
            for candidate_commit in commits:
                source_key = (candidate_commit, source_path)
                if source_key not in source_cache:
                    source_cache[source_key] = _git(
                        "show", f"{candidate_commit}:{source_path}")
                source = source_cache[source_key]
                if not source:
                    continue
                expected = _candidate_body(source, base, function)
                if expected and not ancestor_commit:
                    ancestor_commit = candidate_commit
                    ancestor_body = expected
                if (expected.strip() == body.strip()
                        or (transformations
                            and _canonical_c_whitespace(expected)
                            == _canonical_c_whitespace(body))):
                    commit = candidate_commit
                    match_cache[cache_key] = commit
                    break
        if not ancestor_commit and commit:
            ancestor_commit = commit
            ancestor_body = body
        classification = ("exact-upstream" if commit else
                          "derived-upstream-candidate" if ancestor_commit else
                          "unclassified")
        delta = {}
        if classification == "derived-upstream-candidate":
            ancestor_lines = _canonical_c_whitespace(ancestor_body).splitlines()
            artifact_lines = _canonical_c_whitespace(body or normalized_text).splitlines()
            unified = "\n".join(difflib.unified_diff(
                ancestor_lines, artifact_lines,
                fromfile="upstream-ancestor", tofile="preserved-artifact",
                lineterm=""))
            delta = {
                "ancestor_function_body_sha256": hashlib.sha256(
                    ancestor_body.encode("utf-8")).hexdigest(),
                "canonical_unified_diff_sha256": hashlib.sha256(
                    unified.encode("utf-8")).hexdigest(),
                "upstream_canonical_lines": len(ancestor_lines),
                "artifact_canonical_lines": len(artifact_lines),
                "added_diff_lines": sum(line.startswith("+") and
                                         not line.startswith("+++")
                                         for line in unified.splitlines()),
                "removed_diff_lines": sum(line.startswith("-") and
                                           not line.startswith("---")
                                           for line in unified.splitlines()),
                "reproducible_exactly_from_ancestor": False,
                "reason": ("historical generated or target-adapted artifact; "
                           "preserved without claiming exact upstream identity"),
            }
        item = {
            "artifact": artifact.relative_to(REPO).as_posix(),
            "artifact_sha256": artifact_sha,
            "record": record_id,
            "artifact_function_body_sha256": (hashlib.sha256(
                artifact_body.encode("utf-8")).hexdigest()
                if artifact_body else ""),
            "normalized_function_body_sha256": body_sha,
            "deterministic_transformations": transformations,
            "source_path": source_path,
            "source_commit": commit,
            "classification": classification,
            "ancestor_commit": ancestor_commit,
            "derived_transformation_evidence": delta,
            "recorded_ref": recorded_ref,
        }
        records.append(item)
        if classification == "unclassified":
            unclassified.append(item)

    document = {
        "generator": "automation/upstream_harvest.py --provenance-manifest",
        "upstream_ref": UPSTREAM,
        "upstream_head_at_generation": preferred,
        "artifacts": records,
        "summary": {"artifacts": len(records),
                    "exact_upstream": sum(item["classification"] ==
                                          "exact-upstream" for item in records),
                    "derived_upstream_candidate": sum(item["classification"] ==
                                                       "derived-upstream-candidate"
                                                       for item in records),
                    "unclassified": len(unclassified),
                    "normalized": sum(bool(item["deterministic_transformations"])
                                       for item in records)},
    }
    publication = json.dumps(document, indent=2) + "\n"
    version = publish_versioned_artifact(
        output, publication, "upstream provenance manifest", REPO)
    exact = sum(item["classification"] == "exact-upstream" for item in records)
    derived = sum(item["classification"] == "derived-upstream-candidate"
                  for item in records)
    print(f"wrote {output.relative_to(REPO)}: {exact} exact, {derived} derived, "
          f"{len(unclassified)} unclassified; immutable {version}")
    if unclassified:
        for item in unclassified[:20]:
            print(f"UNCLASSIFIED {item['artifact']} -> {item['source_path']}")
        return 1
    return 0


def diagnose_provenance(path_text: str) -> int:
    """Explain why one harvested artifact does or does not content-pin."""
    artifact = (REPO / path_text).resolve()
    try:
        artifact.relative_to(REPO.resolve())
    except ValueError:
        print("artifact must stay inside the repository")
        return 1
    text = artifact.read_text(encoding="utf-8", errors="replace")
    match = _ARTIFACT_PROVENANCE_RE.search(text)
    if not match:
        print("artifact has no upstream-harvest provenance header")
        return 1
    record_id, recorded_ref, source_path = match.groups()
    function = record_id.rsplit(":", 1)[-1]
    base = re.sub(r"_from_\w+$", "", function)
    normalized, transformations = _normalize_provenance_candidate(text)
    body = _extract(normalized, function)
    preferred = upstream_commit()
    commits = ([recorded_ref.lower()]
               if re.fullmatch(r"[0-9a-fA-F]{40}", recorded_ref)
               else _commit_candidates(source_path, preferred))
    print(f"record={record_id} source={recorded_ref}:{source_path}")
    print(f"body_chars={len(body)} transformations={transformations}")
    body_key = _canonical_c_whitespace(body)
    for commit in commits:
        source = _git("show", f"{commit}:{source_path}")
        expected = _candidate_body(source, base, function) if source else ""
        print(f"commit={commit} expected_chars={len(expected)} "
              f"exact={expected.strip() == body.strip()} "
              f"canonical={_canonical_c_whitespace(expected) == body_key} "
              f"body_key_sha256={hashlib.sha256(body_key.encode()).hexdigest()} "
              f"expected_key_sha256={hashlib.sha256(_canonical_c_whitespace(expected).encode()).hexdigest()}")
    return 0




# --------------------------------------------------------------- comparison

RX_UNK_FIELD = re.compile(r"->\s*(unk[0-9A-Fa-f]{1,3})\b")
RX_ILLEGAL = re.compile(r"\bILLEGAL\b")
RX_FAKE_SYM = re.compile(r"\bD_(?:us_)?[0-9A-Fa-f]{8}\b")


def _mask_c_noncode(text: str) -> str:
    """Mask comments and literals byte-for-byte while preserving newlines."""
    chars = list(text)
    state = "code"
    index = 0
    while index < len(chars):
        char = chars[index]
        nxt = chars[index + 1] if index + 1 < len(chars) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                chars[index] = chars[index + 1] = " "
                state = "line-comment"
                index += 1
            elif char == "/" and nxt == "*":
                chars[index] = chars[index + 1] = " "
                state = "block-comment"
                index += 1
            elif char in ('"', "'"):
                chars[index] = " "
                state = "string" if char == '"' else "char"
        elif state == "line-comment":
            if char == "\n":
                state = "code"
            else:
                chars[index] = " "
        elif state == "block-comment":
            if char == "*" and nxt == "/":
                chars[index] = chars[index + 1] = " "
                state = "code"
                index += 1
            elif char != "\n":
                chars[index] = " "
        else:
            if char == "\\" and index + 1 < len(chars):
                chars[index] = " "
                if chars[index + 1] != "\n":
                    chars[index + 1] = " "
                index += 1
            elif ((state == "string" and char == '"')
                  or (state == "char" and char == "'")):
                chars[index] = " "
                state = "code"
            elif char != "\n":
                chars[index] = " "
        index += 1
    return "".join(chars)


def _us_preprocessor_condition(expression: str) -> bool:
    values = {"VERSION_US": True, "VERSION_PSP": False,
              "VERSION_HD": False, "VERSION_PC": False}
    expr = expression.strip()
    expr = re.sub(
        r"!?defined\s*\(\s*([A-Za-z_]\w*)\s*\)",
        lambda match: str(int((not values.get(match.group(1), False))
                              if match.group(0).lstrip().startswith("!")
                              else values.get(match.group(1), False))), expr)
    expr = re.sub(r"\b([A-Za-z_]\w*)\b",
                  lambda match: str(int(values.get(match.group(1), False))), expr)
    expr = expr.replace("&&", " and ").replace("||", " or ")
    expr = re.sub(r"!(?!=)", " not ", expr)
    try:
        return bool(eval(expr, {"__builtins__": {}}, {}))
    except (SyntaxError, TypeError, ValueError):
        return True


def _mask_inactive_us(text: str) -> str:
    """Mask inactive PSP/HD branches for US brace matching, preserving offsets."""
    out: list[str] = []
    active = True
    stack: list[dict] = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        directive = re.match(r"#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)",
                             stripped)
        if directive:
            kind, tail = directive.groups()
            if kind in ("if", "ifdef", "ifndef"):
                if kind == "ifdef":
                    condition = _us_preprocessor_condition(
                        f"defined({tail.strip()})")
                elif kind == "ifndef":
                    condition = _us_preprocessor_condition(
                        f"!defined({tail.strip()})")
                else:
                    condition = _us_preprocessor_condition(tail)
                frame = {"parent": active, "taken": condition}
                stack.append(frame)
                active = active and condition
            elif kind == "elif" and stack:
                frame = stack[-1]
                condition = (not frame["taken"]
                             and _us_preprocessor_condition(tail))
                frame["taken"] = frame["taken"] or condition
                active = bool(frame["parent"] and condition)
            elif kind == "else" and stack:
                frame = stack[-1]
                condition = not frame["taken"]
                frame["taken"] = True
                active = bool(frame["parent"] and condition)
            elif kind == "endif" and stack:
                active = bool(stack.pop()["parent"])
            out.append("".join("\n" if char == "\n" else " " for char in line))
        elif active:
            out.append(line)
        else:
            out.append("".join("\n" if char == "\n" else " " for char in line))
    return "".join(out)


def _extract(body_src: str, fn: str) -> str:
    """The single function `fn` out of a whole .c file, or ''. """
    sys.path.insert(0, str(REPO / "automation"))
    try:
        import member_types as mt                            # type: ignore
    except ImportError:                                      # pragma: no cover
        return ""
    # MATCH THE DEFINITION, NOT THE NAME. Searching the head text for the
    # function name also matches a forward declaration or an entry in a
    # pointer table, and then returns whatever region the brace matcher
    # happened to land on. src/boss/bo4/e_init.c only DECLARES
    # EntityDamageDisplay (line 7) and lists it in a table (line 36); the
    # loose version extracted 2,136 unrelated chars from it and reported three
    # raw D_ symbols we do not actually use. That is a fabricated finding, and
    # it is exactly the class of error this whole comparison exists to avoid.
    text = _mask_inactive_us(_mask_c_noncode(body_src))
    for m in mt.RX_FUNC_HEAD.finditer(text):
        if m.group(1) != fn:
            continue
        i = text.index("{", m.start())
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        return text[m.start():j + 1]
    return ""


def compare_matched(limit: int = 0) -> int:
    """Our matched C against upstream's INDEPENDENT decompilation of the same.

    THE FIRST EXTERNAL CHECK THIS PROJECT HAS HAD. Every quality measure so
    far -- invented(), degenerate(), fidelity, member_types -- is something we
    wrote, scoring output against a model of correctness we also wrote. Two of
    them have already been caught agreeing with each other rather than with
    the compiler.

    Upstream decompiled these functions without reference to us. Where both
    sides match the same assembly the SEMANTICS must agree, so every remaining
    difference is naming and shape -- which is exactly the axis our own
    metrics cannot see, and the axis a reviewer judges.

    A field they name and we call `unkNN` is a concrete, checkable upgrade,
    not an opinion.
    """
    ref = _git("rev-parse", "--short", UPSTREAM).strip()
    if not ref:
        print(f"cannot resolve {UPSTREAM}; run git_fetch first")
        return 1

    r = subprocess.run(
        [PYTHON, str(REPO / "automation" / "scheduler.py"),
         "list", "--status", "matched"],
        capture_output=True, text=True, timeout=180, cwd=str(REPO))
    ours = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line.startswith("matched"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        rid = parts[2].partition("|")[0].strip()
        bits = rid.split(":")
        if len(bits) >= 3:
            ours.append((bits[1], re.sub(r"_from_\w+$", "", bits[2])))
    if limit:
        ours = ours[:limit]

    up = upstream_files()
    stubs = upstream_stubs()
    rows, both = [], 0
    for ovl, fn in ours:
        if fn in stubs or fn not in up:
            continue                    # upstream has not done this one
        upath = up[fn]
        utext = _extract(_git("show", f"{upstream_commit()}:{upath}"), fn)
        # Ours: find the file in the working tree that defines it.
        hit = subprocess.run(
            ["git", "grep", "-lE", r"\b" + re.escape(fn) + r"\s*\(", "--",
             "src/"], capture_output=True, text=True, timeout=120,
            cwd=str(REPO)).stdout.split()
        otext = ""
        for h in hit:
            otext = _extract(Path(REPO / h).read_text(errors="ignore"), fn)
            if otext:
                break
        if not utext or not otext:
            continue
        both += 1
        o_unk = set(RX_UNK_FIELD.findall(otext))
        u_unk = set(RX_UNK_FIELD.findall(utext))
        rows.append({
            "fn": fn, "overlay": ovl, "path": upath,
            "our_unk": len(o_unk), "up_unk": len(u_unk),
            # Offsets THEY resolved and we did not: each is a rename we can
            # make with the answer already in hand.
            "upgradable": sorted(o_unk - u_unk)[:6],
            "our_illegal": len(RX_ILLEGAL.findall(otext)),
            "up_illegal": len(RX_ILLEGAL.findall(utext)),
            "our_fake": len(set(RX_FAKE_SYM.findall(otext))),
            "up_fake": len(set(RX_FAKE_SYM.findall(utext))),
            "our_lines": otext.count("\n"), "up_lines": utext.count("\n"),
        })

    print(f"upstream/master {ref}\n")
    if not rows:
        print("no matched function of ours is also decompiled upstream; "
              "nothing to compare")
        return 0
    print(f"{both} of our matched functions are ALSO decompiled upstream, "
          f"independently.\n")
    worse = [r for r in rows if r["our_unk"] > r["up_unk"]]
    better = [r for r in rows if r["our_unk"] < r["up_unk"]]
    ill = [r for r in rows if r["our_illegal"] > r["up_illegal"]]
    fake = [r for r in rows if r["our_fake"] > r["up_fake"]]
    print(f"  unresolved unkNN:  we name fewer fields in {len(worse)}, "
          f"more in {len(better)}, same in {both - len(worse) - len(better)}")
    print(f"  ext.ILLEGAL:       worse in {len(ill)}")
    print(f"  raw D_ symbols:    worse in {len(fake)}")
    tot_up = sum(len(r["upgradable"]) for r in rows)
    # STATE THE ABSOLUTE NUMBERS. "same in 35" is compatible with both sides
    # being zero, which would make the comparison vacuous while reading as a
    # clean bill of health. A parity claim has to show what it is parity AT.
    o_tot = sum(r["our_unk"] for r in rows)
    u_tot = sum(r["up_unk"] for r in rows)
    o_ill = sum(r["our_illegal"] for r in rows)
    u_ill = sum(r["up_illegal"] for r in rows)
    o_fk = sum(r["our_fake"] for r in rows)
    u_fk = sum(r["up_fake"] for r in rows)
    o_ln = sum(r["our_lines"] for r in rows)
    u_ln = sum(r["up_lines"] for r in rows)
    print(f"\n{'':22}{'ours':>8}{'upstream':>10}")
    print(f"  {'unresolved unkNN':20}{o_tot:>8}{u_tot:>10}")
    print(f"  {'ext.ILLEGAL':20}{o_ill:>8}{u_ill:>10}")
    print(f"  {'raw D_ symbols':20}{o_fk:>8}{u_fk:>10}")
    print(f"  {'body lines':20}{o_ln:>8}{u_ln:>10}")
    if o_tot == 0 and u_tot == 0:
        print("\n  NOTE: both sides are zero, so the unkNN comparison is "
              "saturated,\n  not passed. It confirms neither side ships "
              "unresolved offsets; it does\n  NOT show our naming matches "
              "theirs.")

    print(f"\n{tot_up} field name(s) upstream resolved that we left as unkNN.")
    print("Each is a rename with the answer already known -- no model, no "
          "build risk\nbeyond the usual verify.\n")

    if fake:
        print("\nfunctions where WE carry a raw D_ symbol and upstream does "
              "not:")
        for r in fake:
            print(f"  {r['fn'][:32]:34}ours {r['our_fake']} vs "
                  f"theirs {r['up_fake']}   {r['path']}")

    for r in sorted(rows, key=lambda x: -(x["our_unk"] - x["up_unk"]))[:20]:
        d = r["our_unk"] - r["up_unk"]
        if d <= 0 and not r["upgradable"]:
            continue
        print(f"  {r['fn'][:30]:32} ours {r['our_unk']:2} unk vs "
              f"theirs {r['up_unk']:2}   {r['upgradable']}")
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\nINCLUDE_ASM stubs are recognised as NOT decompiled")
    ck(RX_INCLUDE_ASM.findall(
        'INCLUDE_ASM("st/rchi/nonmatchings/e_breakable", EntityBreakable);')
        == ["EntityBreakable"], "the stub's function name is extracted")

    print("\nthe queue's _from_<overlay> suffix is stripped")
    # Shimmed records are named func_us_801CC750_from_no0 in the queue but
    # func_us_801CC750 upstream; without stripping, every shimmed record would
    # silently look un-harvestable.
    ck(re.sub(r"_from_\w+$", "", "func_us_801CC750_from_no0")
       == "func_us_801CC750", "suffix stripped")
    ck(re.sub(r"_from_\w+$", "", "EntityBreakable") == "EntityBreakable",
       "a name without the suffix is untouched")

    print("\nbatch publication accepts exact-ID maps and lists")
    ck(publish_ids({"us:ST/RNO0:One": {}, "us:ST/RNO0:Two": {}}) ==
       ["us:ST/RNO0:One", "us:ST/RNO0:Two"],
       "priority-map keys become exact IDs")
    ck(publish_ids(["us:ST/RNO0:One"]) == ["us:ST/RNO0:One"],
       "an exact-ID list remains unchanged")
    try:
        publish_ids(["us:ST/RNO0:One", 2])
        rejected_bad_batch = False
    except ValueError:
        rejected_bad_batch = True
    ck(rejected_bad_batch, "non-string batch IDs are rejected")

    print("\noverlay-local definitions outrank same-named global helpers")
    saved_paths, saved_cache, saved_stubs = _UF_PATHS, dict(_UF_CACHE), _US_CACHE
    try:
        globals()["_UF_PATHS"] = {
            "target": ["src/st/e_shared.h", "src/st/rno0/e_target.c"]}
        _UF_CACHE.clear()
        ck(upstream_files("ST/RNO0")["target"] ==
           "src/st/rno0/e_target.c",
           "RNO0 selects its own definition")
        ck(upstream_files()["target"] == "src/st/e_shared.h",
           "the global fallback remains available")
        globals()["_US_CACHE"] = {"target"}
        ck(harvest_path("target", "ST/RNO0") == "src/st/rno0/e_target.c",
           "a same-named stub elsewhere cannot hide the real overlay body")
    finally:
        globals()["_UF_PATHS"] = saved_paths
        globals()["_US_CACHE"] = saved_stubs
        _UF_CACHE.clear()
        _UF_CACHE.update(saved_cache)

    print("\ngit is reached through the repo, never the sandbox")
    src = Path(__file__).read_text(errors="ignore")
    ck('cwd=str(REPO)' in src, "every git call is cwd-pinned to the repo")
    ck("wd.virtual_apply" in src
       and "wd._declare_stub_siblings(whole, whole)" in src
       and "wd._declare_stub_siblings(replaced, replaced)" in src,
       "both publication paths declaration-scan the complete translation unit")
    ck("content: WHOLE FILE" in src,
       "the published artifact states its complete translation-unit boundary")
    ck("METHOD=UPSTREAM-HARVEST" in src,
       "the published artifact carries the canonical provenance marker")
    ck("already current" in src and "artifact_is_current" in src,
       "an interrupted batch resumes only immutable current provenance")
    sample = ("method : METHOD=UPSTREAM-HARVEST\n"
              f"generator: {ARTIFACT_SCHEMA}\n"
              "record : us:ST/RNO0:Function\n"
              "source : " + "a" * 40 + ":src/st/rno0/test.c\n")
    ck(artifact_is_current(sample, "us:ST/RNO0:Function",
                            "src/st/rno0/test.c", "a" * 40),
       "a matching pinned commit resumes")
    ck(not artifact_is_current(sample.replace(
        f"generator: {ARTIFACT_SCHEMA}\n", ""), "us:ST/RNO0:Function",
        "src/st/rno0/test.c", "a" * 40),
       "an older publication schema is regenerated")
    ck(not artifact_is_current(sample, "us:ST/RNO0:Function",
                                "src/st/rno0/test.c", "b" * 40),
       "the same path at a changed upstream commit is republished")
    ck(not artifact_is_current(sample, "us:ST/RNO0:FunctionExtra",
                               "src/st/rno0/test.c", "a" * 40),
       "a record-id prefix collision cannot satisfy resume")
    ck(not artifact_is_current(sample, "us:ST/RNO0:Function",
                               "src/st/rno0/test.c.extra", "a" * 40),
       "a source-path prefix collision cannot satisfy resume")
    replaced = _replace_existing_function(
        "void Closed(void) { old(); }\nvoid Neighbor(void) {}\n",
        "Closed", "void Closed(void) { upstream(); }")
    ck("upstream();" in replaced and "void Neighbor(void) {}" in replaced,
       "a closed-record refresh replaces only its owned live definition")
    commit_candidates_src = src[src.index("def _commit_candidates"):]
    commit_candidates_src = commit_candidates_src[
        :commit_candidates_src.index("\ndef write_provenance_manifest")]
    ck("UPSTREAM" not in commit_candidates_src
       and '_git("log", "--format=%H", head' in commit_candidates_src,
       "manifest history enumeration is pinned to its captured commit")
    provenance_sample = (
        "/* method : METHOD=UPSTREAM-HARVEST\n"
        "   record : us:ST/RNO0:Function\n"
        "   source : upstream/master:src/st/rno0/test.c */\n"
        "void Function(void) {}\n")
    parsed = _ARTIFACT_PROVENANCE_RE.search(provenance_sample)
    ck(parsed is not None and parsed.groups() == (
        "us:ST/RNO0:Function", "upstream/master", "src/st/rno0/test.c"),
       "moving-ref artifact provenance is parsed without rewriting history")
    nested_block = (
        "void Function(void) {\n"
        "/* Added by the permuter-seed writer. The permuter parses the complete\n"
        "   translation unit. */\nextern int Helper();\n"
        "/* End permuter-seed writer declarations. */\nHelper();\n}\n")
    normalized, transforms = _normalize_provenance_candidate(nested_block)
    ck("extern int Helper();" not in normalized and "Helper();" in normalized
       and transforms == ["removed permuter-seed writer declaration block",
                           "canonicalized nonliteral whitespace for lineage comparison"],
       "provenance removes and records deterministic seed scaffolding")
    ck(_canonical_c_whitespace('f("a  b");\n  x /* c  d */ = 1;')
       == 'f("a  b"); x /* c  d */ = 1;',
       "lineage whitespace normalization preserves literals and comments")
    manifest_src = src[src.index("def write_provenance_manifest"):]
    ck('"exact-upstream"' in manifest_src
       and '"derived-upstream-candidate"' in manifest_src
       and '"unclassified"' in manifest_src,
       "manifest keeps exact, derived and unclassified provenance distinct")
    ck("canonical_unified_diff_sha256" in manifest_src
       and "ancestor_function_body_sha256" in manifest_src,
       "derived artifacts carry hashed ancestor and transformation evidence")
    ck("publish_versioned_artifact(" in manifest_src,
       "a refreshed provenance report archives its prior stable generation")
    ck("wd.lookup_declarations" in src and "for start in range" in src,
       "batch publication prewarms declaration evidence in bounded chunks")
    # Check the CALL SITES, not the file text. The first version searched the
    # whole source for "merge" and matched the word in this module's own
    # docstring, failing a module that does nothing of the kind. A test that
    # reads prose is testing prose.
    subcmds = set(re.findall(r'_git\(\s*"(\w+)"', src))
    writers = subcmds & {"checkout", "merge", "reset", "rebase", "commit",
                         "clean", "apply", "cherry-pick", "push", "fetch"}
    ck(not writers, f"only read-only git subcommands are used ({subcmds})",
       f"writers found: {writers}")

    print("\na single function is extracted from a whole file")
    src2 = ("void other(Entity* e) { e->posX = 1; }\n"
            "void target(Entity* e) { e->unk1C = 2; e->unk80 = 3; }\n")
    got = _extract(src2, "target")
    ck("unk1C" in got and "posX" not in got,
       f"only the requested function comes back ({got[:40]!r})")
    ck(_extract(src2, "absent") == "", "a missing function yields nothing")
    # A declaration and a pointer-table entry are not definitions.
    decl_only = ("void target(Entity*);\n"
                 "EInit D_us_80180434 = {1, 2, 3};\n"
                 "void* tbl[] = { target, other };\n")
    ck(_extract(decl_only, "target") == "",
       f"a declaration alone yields nothing ({_extract(decl_only, 'target')[:40]!r})")
    conditional = (
        "#if defined(VERSION_PSP)\nbool StepTowards(void) { return false; }\n"
        "#else\nbool StepTowards(void) {\n"
        "#if !defined(VERSION_PSP)\nif (1) { return true; }\n#endif\n"
        "return false;\n}\n#endif\nvoid after(void) {}\n")
    conditional_body = _extract(conditional, "StepTowards")
    ck(conditional_body.startswith("bool StepTowards")
       and "#else" not in conditional_body and "void after" not in conditional_body,
       "US-aware extraction never splices mutually exclusive function heads")
    static_body = _candidate_body(
        "static void target(void) { target(); }", "target", "target_from_src")
    ck(static_body.startswith("void target_from_src") and
       "target_from_src();" in static_body,
       "a queued suffix is applied and partial-tree external visibility is kept")

    print("\nthe comparison metric is the one our own metrics cannot see")
    # Both sides match the same asm, so semantics agree and only naming can
    # differ. An offset THEY named and we did not is a checkable upgrade.
    ours = "void f(Entity* e) { e->unk1C = 1; e->unk80 = 2; }"
    theirs = "void f(Entity* e) { e->scaleY = 1; e->unk80 = 2; }"
    o = set(RX_UNK_FIELD.findall(ours)); u = set(RX_UNK_FIELD.findall(theirs))
    ck(sorted(o - u) == ["unk1C"],
       f"the upgradable offset is identified ({sorted(o - u)})")
    ck(sorted(u - o) == [], "and one we already named is not counted against us")

    print("\nthe ref is resolved before any conclusion is drawn")
    ck("cannot resolve" in src and "git_fetch first" in src,
       "a missing upstream ref is reported, not silently treated as empty")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overlay", default="", help="filter, e.g. rno0")
    ap.add_argument("--show", help="print upstream's file for one function")
    ap.add_argument("--publish",
                    help="unmatched function to publish; requires --overlay")
    ap.add_argument("--publish-file", default="", metavar="PATH",
                    help="publish every harvestable exact ID in one JSON "
                         "priority map or ID list")
    ap.add_argument("--republish-artifact", default="", metavar="PATH",
                    help="refresh one stable upstream artifact after queue closure")
    ap.add_argument("--apply", action="store_true",
                    help="write the selected --publish candidate")
    ap.add_argument("--compare-matched", action="store_true",
                    help="our matched C vs upstream's independent version")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--provenance-manifest", default="", metavar="PATH",
                     help="write artifact-hash to immutable upstream source proof")
    ap.add_argument("--diagnose-provenance", default="", metavar="ARTIFACT",
                    help="explain one artifact's immutable-source comparison")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.show:
        return show(a.show)
    if a.provenance_manifest:
        return write_provenance_manifest(a.provenance_manifest)
    if a.diagnose_provenance:
        return diagnose_provenance(a.diagnose_provenance)
    if a.publish:
        record_id = a.publish
        if ":" not in record_id:
            if not a.overlay:
                ap.error("--publish requires --overlay")
            record_id = f"us:{a.overlay.upper()}:{record_id}"
        return publish(record_id, a.apply)
    if a.republish_artifact:
        return republish_artifact(a.republish_artifact, a.apply)
    if a.publish_file:
        return publish_file(a.publish_file, a.apply, a.overlay)
    if a.apply:
        ap.error("--apply requires --publish, --publish-file or --republish-artifact")
    if a.compare_matched:
        return compare_matched(a.limit)
    return report(a.overlay)


if __name__ == "__main__":
    raise SystemExit(main())
