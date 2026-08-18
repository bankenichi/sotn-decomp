"""
commands_client: a hard-allowlisted command runner for the SOTN decomp repo.

Security model:
  - There is NO general shell. Only the actions in REGISTRY can run.
  - Every argument is validated (enums, strict regexes, in-repo path checks).
  - subprocess is always invoked with an argv list, never shell=True.
  - stdout/stderr are truncated to keep the caller's context small.
  - Each action has a timeout. Set SOTN_CMD_DRYRUN=1 to return argv without running.

Stdlib only, so it is importable and unit-testable anywhere.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import shutil
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[2]))
# The MCP server runs from automation/mcp/.venv, which intentionally carries
# only the connector dependencies. Child tools such as asm-differ and the
# permuter use the root repo venv. Falling back to bare `python3` crosses that
# boundary and fails later on imports such as watchdog or toml.
_VENV_PYTHON = REPO / ".venv" / (
    "Scripts/python.exe" if os.name == "nt" else "bin/python")
PYTHON = os.environ.get("SOTN_PYTHON") or (
    str(_VENV_PYTHON) if _VENV_PYTHON.is_file() else sys.executable)
# Fail CLOSED. If the variable is missing or empty we assume dry-run, because
# an unset safety flag must never mean "execute for real". This bit us once:
# MCP `env` entries are set on the Windows wsl.exe process and do NOT propagate
# into WSL without WSLENV, so the server saw nothing and silently ran live.
# The launcher now passes it inline in the bash command instead.
_dr = os.environ.get("SOTN_CMD_DRYRUN")
DRYRUN = True if _dr is None or _dr.strip() == "" else \
    _dr.strip().lower() not in ("0", "false", "no", "off")
MAX_OUT = int(os.environ.get("SOTN_CMD_MAXOUT", "20000"))

VERSIONS = {"us", "hd", "pspeu", "saturn"}
SYMBOL_RX = re.compile(r"^[A-Za-z0-9_]{1,64}$")
OVERLAY_RX = re.compile(r"^[A-Za-z0-9_]{1,32}$")
FMT = {"plain", "color", "json", "html"}


class Rejected(ValueError):
    """Raised when an argument fails validation. Never executes anything."""


def _v(version: str) -> str:
    if version not in VERSIONS:
        raise Rejected(f"version must be one of {sorted(VERSIONS)}")
    return version


def _sym(symbol: str) -> str:
    if not SYMBOL_RX.match(symbol or ""):
        raise Rejected("symbol must match ^[A-Za-z0-9_]{1,64}$")
    return symbol


def _ov(overlay: str) -> str:
    if not OVERLAY_RX.match(overlay or ""):
        raise Rejected("overlay must match ^[A-Za-z0-9_]{1,32}$")
    return overlay


def _inrepo(p: str, must_be_dir: bool = False, must_exist: bool = True) -> str:
    """An in-repo path, or Rejected.

    CONTAINMENT IS A PARENT CHECK, NOT A PREFIX CHECK. This used to test
    `str(rp).startswith(str(REPO.resolve()))`, which is a string comparison
    wearing a path's clothes: with REPO=/repo, the path `../repo-evil/x`
    resolves to /repo-evil/x, and "/repo-evil/x".startswith("/repo") is True.
    So a sibling directory whose name merely begins with the repo's name was
    accepted, and _inrepo guards the arguments handed to git.

    The correct test already existed a few hundred lines down in `_resolve`;
    the two had simply drifted. Found by an external audit of the fork,
    2026-08-09. Same rule now, and `.git` is refused as well, because handing
    git a path inside its own object store is never a legitimate request from
    this layer.
    """
    rp = (REPO / p).resolve()
    root = REPO.resolve()
    if rp != root and root not in rp.parents:
        raise Rejected("path must resolve inside the repo")
    git_dir = root / ".git"
    if rp == git_dir or git_dir in rp.parents:
        raise Rejected("path is inside .git")
    if must_exist and not rp.exists():
        raise Rejected(f"path does not exist: {p}")
    if must_be_dir and rp.exists() and not rp.is_dir():
        raise Rejected(f"path is not a directory: {p}")
    return str(rp)


def _relpath(abs_path: str) -> str:
    """An absolute in-repo path, back to repo-root-relative, with / separators.

    `git show <ref>:<path>` REQUIRES a path relative to the repo root. An
    absolute one is rejected by git with "fatal: <path> is outside repository",
    which is why this exists rather than passing _inrepo's output through: every
    other caller hands its path to git as a PATHSPEC, where absolute is fine,
    and only the `ref:path` form is different.

    Takes _inrepo's output, so containment has already been enforced; this only
    changes the spelling. as_posix() matters on Windows, where the repo is
    reached through a WSL mount and git will not accept backslashes.
    """
    return Path(abs_path).resolve().relative_to(REPO.resolve()).as_posix()


def _submodule_dir(path: str) -> str:
    """A declared submodule directory, or Rejected.

    Root Git reports only that a gitlink is dirty. That is insufficient for a
    standalone fork which may vendor intentional dependency changes: the work
    has to be inspected before it can be preserved. Keep this narrower than a
    general cwd option by accepting only exact `path =` values from
    `.gitmodules`.
    """
    modules = REPO / ".gitmodules"
    declared = set()
    if modules.is_file():
        for line in modules.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*path\s*=\s*(.+?)\s*$", line)
            if match:
                declared.add(Path(match.group(1)).as_posix())
    if path not in declared:
        raise Rejected("path must exactly match a submodule declared in .gitmodules")
    return _inrepo(path, must_be_dir=True)


def _restorable(path: str, confirm_orphan: bool = False) -> str:
    """An in-repo path safe to discard, or Rejected.

    THE DANGEROUS CASE IS UNEXPLAINED WORK UNDER src/. On 2026-08-10 two files
    sat modified with candidate bodies over three INCLUDE_ASM stubs and no
    crash journal. Everything about them said "debris from a killed worker".
    They were three genuine matches: the tree verified 81/81 with them
    applied. A single git_restore would have destroyed all three, and nothing
    here would have objected.

    So the test is not "is this a match" -- proving that needs a full build,
    which does not belong in an argv builder and must not be forced on every
    restore. The test is whether anything still KNOWS what this edit is:

      - not under src/          -> not our concern; automation/ churns
                                   constantly and its edits are disposable.
      - unmodified              -> nothing to lose.
      - a crash journal covers it -> this is normal recovery of an
                                   in-flight apply. The journal holds the
                                   original and the worker or the replay will
                                   deal with it. Allowed, unchanged.
      - modified, under src/,
        and NOTHING references it -> REFUSE. This is the exact shape of the
                                   near-miss: work whose only record is the
                                   file itself.

    Refusal is not a veto, it is a speed bump: pass confirm_orphan=True to
    proceed. The point is that discarding an orphan should be a decision
    somebody made, not a default.
    """
    p = _inrepo(path, must_exist=False)
    if confirm_orphan:
        return p
    try:
        rel = Path(p).resolve().relative_to(REPO.resolve()).as_posix()
    except (ValueError, OSError):
        return p
    if not rel.startswith("src/"):
        return p
    try:
        r = subprocess.run(["git", "status", "--porcelain", "--", rel],
                           cwd=str(REPO), capture_output=True, text=True,
                           timeout=60)
        if r.returncode != 0 or not (r.stdout or "").strip():
            return p                      # clean, or git could not say
    except (OSError, subprocess.SubprocessError):
        return p                          # never block on a broken check

    pending = REPO / "automation" / "logs" / "pending"
    try:
        for jf in pending.glob("*.json"):
            try:
                with open(jf, encoding="utf-8") as f:
                    if json.load(f).get("src_rel", "") == rel:
                        return p          # in flight; normal recovery
            except (OSError, ValueError, AttributeError):
                continue
    except OSError:
        pass

    raise Rejected(
        f"refusing to discard {rel}: it is modified and NO crash journal "
        f"covers it, so the file itself is the only record of whatever is in "
        f"it. That is the shape of a landed match nobody committed -- three "
        f"were found that way on 2026-08-10 and would have been destroyed by "
        f"this command. Run `run_analysis orphan_check.py --build` to find "
        f"out whether it matches. If you already know it is worthless, pass "
        f"confirm_orphan=True.")


def _adoptable(path: str, confirm_overwrite: bool = False) -> str:
    """An in-repo path safe to WRITE OVER from another ref, or Rejected.

    This is the mirror of _restorable. _restorable guards `checkout HEAD --
    <path>`, where the incoming content is the committed state and the thing
    at risk is an uncommitted edit. This guards `checkout <ref> -- <path>`,
    where the incoming content comes from somewhere else entirely -- normally
    upstream/master -- and the thing at risk is the same uncommitted edit.

    The risk cases are not symmetric, so the test is not the same one:

      - destination does not exist -> adopting a NEW file. Nothing to lose.
                                      This is the ordinary harvest case.
      - destination is clean       -> the pre-adoption content is in HEAD, so
                                      git_restore_from_head undoes this. Allowed.
      - destination is dirty       -> REFUSE. An uncommitted edit is about to
                                      be replaced by upstream's version of the
                                      same file, and unlike a restore there is
                                      no ref that holds what was there.

    Deliberately NOT limited to src/, which _restorable is. A harvest also
    overwrites config/ and include/, and a hand-edited splat config is exactly
    as unrecoverable as a hand-edited source file.

    confirm_overwrite=True proceeds, same speed-bump-not-veto shape.
    """
    p = _inrepo(path, must_exist=False)
    if confirm_overwrite:
        return p
    if not Path(p).exists():
        return p
    try:
        rel = Path(p).resolve().relative_to(REPO.resolve()).as_posix()
    except (ValueError, OSError):
        return p
    try:
        r = subprocess.run(["git", "status", "--porcelain", "--", rel],
                           cwd=str(REPO), capture_output=True, text=True,
                           timeout=60)
        if r.returncode != 0 or not (r.stdout or "").strip():
            return p                      # clean, or git could not say
    except (OSError, subprocess.SubprocessError):
        return p                          # never block on a broken check

    raise Rejected(
        f"refusing to overwrite {rel} from another ref: it has uncommitted "
        f"changes, and the incoming content is NOT this repo's history, so "
        f"nothing here would hold what is about to be replaced -- "
        f"git_restore_from_head could not bring it back. Commit or stash it "
        f"first, or pass confirm_overwrite=True if you know it is worthless.")


def _rel(p: str) -> str:
    """An absolute in-repo path as repo-root-relative posix, or '' if it is not.

    Same conversion _relpath does, but total: callers here want to fall back to
    "cannot tell" rather than raise, because a guard that throws on an odd path
    blocks a legitimate operation.
    """
    try:
        return Path(p).resolve().relative_to(REPO.resolve()).as_posix()
    except (ValueError, OSError):
        return ""


def _is_tracked(rel: str) -> bool | None:
    """True/False, or None if git could not answer."""
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", "--", rel],
                           cwd=str(REPO), capture_output=True, text=True,
                           timeout=60)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None


def _is_dirty(rel: str) -> bool | None:
    """True/False, or None if git could not answer."""
    try:
        r = subprocess.run(["git", "status", "--porcelain", "--", rel],
                           cwd=str(REPO), capture_output=True, text=True,
                           timeout=60)
        if r.returncode != 0:
            return None
        return bool((r.stdout or "").strip())
    except (OSError, subprocess.SubprocessError):
        return None


# A splat subsegment naming a stem: `- [0x4A320, c, unk_4A320]`, or with a
# section: `- [0x1DD4, .data, e_thornweed_corpseweed]`. The stem is the last
# field, so it is anchored on `, <stem>]` with optional trailing comment.
def _splat_refs(rel: str) -> list[str]:
    """Every splat subsegment still naming this source file's stem.

    WHY THIS GUARD EXISTS. splat resolves a `[addr, c, stem]` subsegment to
    `<src_path>/<stem>.c`, so the segment and the filename are one fact written
    in two places. Deleting or renaming the file without editing the config
    does not fail loudly at the point of the mistake: it fails later, in a
    build, as a missing input with no hint that a config still points at it.

    Returns strings like
        config/splat.us.strno0.yaml:215  - [0x4A320, c, unk_4A320]
    so a refusal can name exactly what has to be edited first. Empty list means
    no config mentions the stem, which is the state a rename should be in
    BEFORE the file moves: edit the config, then move the file.

    Only meaningful for .c files under src/. Headers are pulled in by #include
    and never named in a splat config, so they are not checked.
    """
    if not (rel.startswith("src/") and rel.endswith(".c")):
        return []
    stem = Path(rel).stem
    rx = re.compile(r"^\s*-\s*\[[^\]]*,\s*" + re.escape(stem) + r"\s*\]")
    out: list[str] = []
    try:
        for cfg in sorted((REPO / "config").glob("splat.*.yaml")):
            try:
                lines = cfg.read_text(encoding="utf-8",
                                      errors="ignore").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                if rx.match(line):
                    out.append(f"{_rel(str(cfg))}:{n} {line.strip()}")
    except OSError:
        pass
    return out


def _removable(path: str, confirm_dirty: bool = False,
               confirm_splat_ref: bool = False) -> str:
    """An in-repo path safe to DELETE from the tree and the index, or Rejected.

    The third member of the family, after _restorable (discard an edit) and
    _adoptable (overwrite from another ref). This one destroys the file itself,
    so it is the strictest:

      - not tracked   -> REFUSE. `git rm` is for files git knows about. An
                         untracked file has no history at all, so removing it
                         through git is both wrong and unrecoverable.
      - a directory   -> REFUSE. There is no recursive form here on purpose;
                         `git rm -r src` is one typo away from catastrophic and
                         nothing in this project needs it.
      - dirty         -> REFUSE unless confirm_dirty. Committed content is
                         recoverable from HEAD; an uncommitted edit is not.
      - still named by a splat subsegment -> REFUSE unless confirm_splat_ref.
                         See _splat_refs: this one is not about recoverability,
                         it is about not leaving the build pointing at a file
                         that no longer exists.
    """
    p = _inrepo(path, must_exist=False)
    rel = _rel(p)
    if Path(p).is_dir():
        raise Rejected(
            f"refusing to remove {rel or path}: it is a directory. This action "
            f"has no recursive form deliberately -- one path at a time, and "
            f"`git rm -r` on a source tree is a typo away from catastrophic.")
    if not rel:
        raise Rejected("could not resolve the path relative to the repo root")
    if _is_tracked(rel) is False:
        raise Rejected(
            f"refusing to remove {rel}: git does not track it, so there is no "
            f"history to recover it from and `git rm` is the wrong tool. If it "
            f"is scratch output, leave it or remove it outside the repo.")
    if not confirm_dirty and _is_dirty(rel):
        raise Rejected(
            f"refusing to remove {rel}: it has uncommitted changes, so HEAD "
            f"does not hold what is about to be destroyed. Commit or stash "
            f"first, or pass confirm_dirty=True.")
    if not confirm_splat_ref:
        refs = _splat_refs(rel)
        if refs:
            raise Rejected(
                f"refusing to remove {rel}: a splat subsegment still names its "
                f"stem, so the next build would look for a file that is gone:\n"
                + "\n".join("    " + r for r in refs)
                + "\n  Edit the config first -- for a rename that means "
                  "pointing the segment at the new stem, which is also the "
                  "order that keeps every intermediate state buildable. "
                  "confirm_splat_ref=True overrides.")
    return p


def _movable(src: str, dst: str, confirm_overwrite: bool = False,
             confirm_splat_ref: bool = False) -> list:
    """A tracked source and a free destination for `git mv`, or Rejected.

    Returns [src_abs, dst_abs] so the argv builder can splat it in.

    THE SPLAT RULE IS DIRECTIONAL, and that is the whole design. A rename has
    to touch two things, the file and the subsegment that names its stem, and
    only one ordering leaves every intermediate state buildable:

        1. point the splat subsegment at the NEW stem
        2. git_mv the file

    Do it the other way and the tree spends a step with a config referring to a
    file that no longer exists. So this refuses while the OLD stem is still
    declared anywhere, which is exactly the state that ordering eliminates.
    After step 1 there are no references left to the old stem and the move is
    allowed without ceremony.
    """
    s = _inrepo(src, must_exist=True)
    d = _inrepo(dst, must_exist=False)
    s_rel, d_rel = _rel(s), _rel(d)
    if Path(s).is_dir():
        raise Rejected(
            f"refusing to move {s_rel or src}: it is a directory. One file at "
            f"a time, for the same reason there is no recursive remove.")
    if not s_rel or not d_rel:
        raise Rejected("could not resolve both paths relative to the repo root")
    if _is_tracked(s_rel) is False:
        raise Rejected(
            f"refusing to move {s_rel}: git does not track it, so `git mv` "
            f"would not preserve any history. Write the new file directly.")
    if Path(d).exists() and not confirm_overwrite:
        raise Rejected(
            f"refusing to move onto {d_rel}: it already exists. Pass "
            f"confirm_overwrite=True only if you mean to destroy it.")
    if not confirm_splat_ref:
        refs = _splat_refs(s_rel)
        if refs:
            raise Rejected(
                f"refusing to move {s_rel}: a splat subsegment still names its "
                f"OLD stem, so the move would leave the config pointing at a "
                f"file that is gone:\n"
                + "\n".join("    " + r for r in refs)
                + f"\n  Point those at `{Path(d_rel).stem}` FIRST, then move. "
                  f"That order is the one where every intermediate state still "
                  f"builds. confirm_splat_ref=True overrides.")
    return [s, d]


def _reject_fmt(fmt):
    raise Rejected(f"fmt must be one of {sorted(FMT)}")


STATUSES = {"todo", "claimed", "near", "matched", "escalated", "deferred"}

# A git revision: branch, tag, sha, HEAD, HEAD~3, abc123^2, origin/master.
# Deliberately excludes the `@{...}` reflog forms and anything with a space,
# colon (refspecs) or dash-prefix (flag injection), so a ref can never be
# mistaken for an option or a remote refspec.
_REF_RX = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./~^-]{0,99}$")
_RESET_MODES = {"soft", "mixed", "hard"}


def _ref(rev: str) -> str:
    if not _REF_RX.match(rev or ""):
        raise Rejected("ref must match ^[A-Za-z0-9_][A-Za-z0-9_./~^-]{0,99}$ "
                       "(no spaces, colons, or leading dashes)")
    return rev


def _count(n, lo: int = 1, hi: int = 500) -> str:
    try:
        v = int(n)
    except (TypeError, ValueError):
        raise Rejected("count must be an integer")
    if not lo <= v <= hi:
        raise Rejected(f"count must be between {lo} and {hi}")
    return str(v)


# git config is a general key/value store that can rewrite how git itself
# behaves (core.hooksPath, alias.*, credential.helper), so it is NOT open.
# These are the keys this project actually sets.
_CFG_KEYS = {"user.name", "user.email"}


def _cfg_key(key: str) -> str:
    if key not in _CFG_KEYS:
        raise Rejected(f"git config key must be one of {sorted(_CFG_KEYS)}")
    return key


def _cfg_value(value: str) -> str:
    v = (value or "").strip()
    if not (1 <= len(v) <= 120) or "\n" in v:
        raise Rejected("git config value must be 1-120 chars, single line")
    return v


def _bad_algo(a):
    raise Rejected("algorithm must be difflib or levenshtein")


def _bad_mode(mode):
    raise Rejected(f"reset mode must be one of {sorted(_RESET_MODES)}")


def _confirmed(confirm, what: str) -> None:
    """Destructive git actions require an explicit opt-in, not a default.

    Every one of these can throw away work that has no other copy. Making the
    caller pass confirm=True means the destructive form can never be reached by
    a default argument or a forgotten parameter.
    """
    if confirm is not True:
        raise Rejected(f"{what} is destructive; pass confirm=True to proceed")

# Read-only analysis tools that may be run through the connector.
#
# WHY THIS EXISTS: these were being run from the Cowork sandbox, which has a
# hard 45s ceiling per call and reaches the repo over a slow Windows mount.
# asm_twin_finder spent 1.8s of CPU and 37s of wall clock on I/O, and a single
# extra command after it blew the limit. That accounted for most of the 40
# sandbox timeouts in one day, each one costing a full re-run.
#
# Here there is no ceiling and the repo is local to WSL.
#
# All but two of these are read-only: they analyse and report, and none edits a
# source file or builds. The exceptions are permuter_promote.py, which rewrites
# base.c inside a nonmatchings/ work directory, and permuter_supervisor.py,
# which calls promote and starts/cancels permuter jobs. That is deliberate and its
# blast radius is bounded three ways: it only ever touches nonmatchings/, which
# holds permuter scratch and no shipped source; it copies the pristine seed to
# base.c.orig before the first write and never overwrites that copy; and
# --revert restores it. Nothing under src/, include/ or config/ is reachable
# from it.
#
# If another writing script is ever added here, say so in this comment. A
# blanket "these are all read-only" that has quietly stopped being true is
# worse than no comment, because it is the thing a reviewer trusts instead of
# checking.
ANALYSIS_SCRIPTS = {
    "asm_twin_finder.py",
    "match_provenance.py",
    "fleet_forensics.py",
    "reasoning_audit.py",
    "quality_ab.py",
    "decomp_fidelity.py",
    "probe_provider.py",
    "test_call_telemetry.py",
    "test_stream_salvage.py",
    "codebase_index.py",
    "queue_coverage.py",
    "quality_audit.py",
    "provenance_check.py",
    "review_checks.py",
    "decl_coverage.py",
    "test_twin_wiring.py",
    "opencode_size_bisect.py",
    # Ranks the ext-union fields whose absence is blocking the most functions.
    # Read-only: it reports where a header change is needed, never makes one.
    "ext_demand.py",
    # Map vs symbol addresses; attributes an overlay size delta to TEXT or BSS.
    # It is listed in HARNESS-ARCHITECTURE's component table and wired to a
    # dashboard button, but was never allowlisted, so both were dead ends that
    # only failed when pressed. The drift check below now compares that table
    # against this list so the next omission is caught before someone finds it.
    "overlay_size_check.py",
    "test_build_classifier.py",
    "test_review_gate.py",
    "test_shim_gate.py",
    "relocation_check.py",
    "find_data_segment.py",
    "test_journal_replay.py",
    # A cancelled job must not be indistinguishable from a crashed one.
    "test_job_cancel.py",
    "fn_diff.py",
    "shim_sweep.py",
    "test_shim_sweep.py",
    "test_queue_owner.py",
    "test_connector_surfaces.py",
    "test_build_attribution.py",
    "escalation_triage.py",
    "deferred_triage.py",
    "member_types.py",
    "upstream_harvest.py",
    "transplant.py",
    "asm_delta.py",
    "test_stub_locate.py",
    "test_permuter_seed.py",
    "permuter_stall.py",
    "permuter_promote.py",
    "permuter_supervisor.py",
    "test_permuter_settings.py",
    "empty_response_audit.py",
    "test_prompt_compaction.py",
    # Added 2026-08-09. progress_table.py reads the linker maps and prints
    # per-overlay completion; it writes nothing and talks to no network,
    # unlike tools/progress.py which posts to frogress and Discord.
    "progress_table.py",
    # The day's two new suites. Both were runnable from a shell and NOT from
    # the connector, which is the same two-surfaces gap this file warns about
    # a few lines up: a test nobody can reach from the dashboard is a test
    # that stops being run.
    "test_draft_cleaning.py",
    "test_salvage_degeneration.py",
    "test_build_lock.py",
    "test_stub_declarations.py",
    "test_candidate_validation.py",
    "test_m2c_only.py",
    "test_targeted_claim.py",
    # Regenerates the README status tables. Read-only without --write, and
    # --write only splices between markers, so it cannot append a second table.
    "readme_status.py",
    # Retrofits stub declarations onto seeds written before the fix. Dry-run
    # by default; --apply is what writes.
    "fix_seed_declarations.py",
    # Classifies uncommitted src/ work as a landed match or as debris. Never
    # writes; --build only builds. This is the tool _restorable points at.
    "orphan_check.py",
    # Cross-checks every `matched` record against HEAD. Finds records that
    # are simply false, which no build can detect. Read-only.
    "matched_audit.py",
    # Runs every test_*.py and reports one table. Read-only.
    "run_selftests.py",
}
# Deliberately narrow: flags, numbers, and in-repo-looking relative paths.
# No spaces, quotes, semicolons, redirects, or leading dashes-with-spaces, so
# nothing here can be reinterpreted by a shell even if one were ever involved.
_ARG_RX = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./=-]{0,120}$|^--?[A-Za-z0-9][A-Za-z0-9_-]{0,40}$")


_REMOTES = frozenset({"origin", "upstream"})
# A revision range is two refs and dots, nothing else. Keeping this narrow is
# what stops `rng` becoming a general argv escape into git.
_RANGE_RX = re.compile(r"^[A-Za-z0-9_./-]{1,80}\.\.\.?[A-Za-z0-9_./-]{1,80}$")


def _remote(name: str) -> str:
    if name not in _REMOTES:
        raise Rejected(f"remote must be one of {sorted(_REMOTES)}")
    return name


def _rev_range(rng: str) -> str:
    if not _RANGE_RX.match(rng or ""):
        raise Rejected("range must look like `A..B` or `A...B`")
    return rng


def _script(name: str) -> str:
    if name not in ANALYSIS_SCRIPTS:
        raise Rejected(f"script must be one of {sorted(ANALYSIS_SCRIPTS)}")
    return f"automation/{name}"


def _args(argstr: str) -> list[str]:
    if not argstr:
        return []
    toks = argstr.split()
    if len(toks) > 12:
        raise Rejected("at most 12 arguments")
    for t in toks:
        if not _ARG_RX.match(t):
            raise Rejected(f"rejected argument {t!r}")
    return toks


def _pattern(p: str) -> str:
    """A prune pattern must be a compilable regex of sane length.

    Deliberately NOT restricted to a character class: pruning by overlay
    (`^us:MAIN:`) and by symbol shape (`a[A-Z0-9]`) both need real regex. The
    protection against a careless pattern is elsewhere and stronger: prune is
    dry-run by default and refuses any record that is not `todo`.
    """
    if not isinstance(p, str) or not 1 <= len(p) <= 200:
        raise Rejected("prune pattern must be 1-200 chars")
    try:
        re.compile(p)
    except re.error as e:
        raise Rejected(f"prune pattern is not a valid regex: {e}")
    return p


def _status(status: str) -> str:
    if status not in STATUSES:
        raise Rejected(f"status must be one of {sorted(STATUSES)}")
    return status


# `us:ST/RDAI:func_us_801C2418` -- version, overlay path, symbol.
QUEUE_ID_RX = re.compile(r"^[a-z0-9]{1,8}:[A-Z0-9/_]{1,32}:[A-Za-z0-9_]{1,64}$")


def _queue_id(qid: str) -> str:
    """Shape check only. Existence is the scheduler's call, not ours.

    Deliberately not validated against the queue file here: this process does
    not hold the queue lock, so any answer it gave could be stale by the time
    the worker claims. `scheduler.py next --only` already refuses an id that is
    missing, already claimed, or already matched, and it decides that inside
    the transaction where the answer is still true.
    """
    if not QUEUE_ID_RX.match(qid or ""):
        raise Rejected("queue id must look like us:ST/RDAI:func_us_801C2418")
    return qid


def _msg_argv(message: str) -> list[str]:
    """Build the -m arguments for a commit message, subject and body.

    Multi-line is supported deliberately. The old rule was "1-200 chars, single
    line", and the practical effect of that on 2026-08-02 was to push two real
    commits out to sandbox-side git, which is the one thing the git_restore
    comment below says must never happen. Both commits then had to be rewritten
    (wrong author) and the rebase that did it was killed by the sandbox's 45s
    cap, leaving a stale index.lock and a worktree rolled back three files.

    A commit message length limit was never a safety property. The safety
    properties are that argv is a list, that no shell is involved, and that the
    subject stays a single line. Those all still hold: git treats each -m as its
    own paragraph, so nothing here is reinterpreted.
    """
    raw = (message or "").replace("\r\n", "\n").strip()
    if not raw:
        raise Rejected("commit message must not be empty")
    if len(raw) > 8000:
        raise Rejected("commit message must be at most 8000 chars")
    subject, _, body = raw.partition("\n")
    subject = subject.strip()
    if not 1 <= len(subject) <= 200:
        raise Rejected("commit subject (first line) must be 1-200 chars")
    argv = ["-m", subject]
    body = body.strip("\n")
    if body.strip():
        argv += ["-m", body]
    return argv


# ---- argv builders (validate then return an argv list) ----

def _make(goal: str, version: str | None = None):
    argv = ["make", goal]
    if version is not None:
        argv.append(f"VERSION={_v(version)}")
    return argv


# ------------------------------------------------------------------ mcpb CLI
#
# The connector bundles itself. Packing and validating them was the one routine
# job that could only be done by asking a human to run a command, which is a
# capability gap, not a fact of life.
#
# Resolution mirrors the OpenCode one in worker_direct: mcpb is an npm global
# installed on WINDOWS, and this runs inside WSL. WSL appends the Windows PATH
# so the file is reachable, but Linux exec has no PATHEXT, so a bare `mcpb`
# never matches and you get FileNotFoundError. The extensions must be listed.
MCPB_BIN = os.environ.get("MCPB_BIN", "").strip()
_MCPB_RESOLVED: str | None = None


def resolve_mcpb() -> str:
    """An executable path for the mcpb CLI, or Rejected with how to install it.

    THE EXTENSIONLESS NAME IS A TRAP ON WSL, and taking it first is exactly the
    bug this hit on the first real call:

        /mnt/c/Users/kenic/AppData/Roaming/npm/mcpb: exec: node: not found

    npm writes THREE launchers into its global dir: a Unix shell script with no
    extension, plus `.cmd` and `.ps1` for Windows. From WSL the Windows npm dir
    is on PATH, so the extensionless shell script matches first -- and it then
    execs `node`, which does not exist inside this WSL distro. The `.cmd` is
    the one that works, because WSL interop hands it to Windows, which has
    node.

    A NATIVE Linux install must still win when there is one: it is also
    extensionless, but it lives outside /mnt. So the rule is not "prefer .cmd",
    it is "an extensionless launcher under /mnt is a Windows Unix-wrapper and
    cannot run here".
    """
    global _MCPB_RESOLVED
    if _MCPB_RESOLVED:
        return _MCPB_RESOLVED
    if MCPB_BIN:
        _MCPB_RESOLVED = MCPB_BIN
        return _MCPB_RESOLVED
    hits = [p for p in (shutil.which(n) for n in
                        ("mcpb", "mcpb.cmd", "mcpb.CMD", "mcpb.exe", "mcpb.bat"))
            if p]

    def usable(p: str) -> bool:
        """False for a Unix wrapper sitting in a Windows npm directory."""
        return not (p.replace("\\", "/").startswith("/mnt/")
                    and not os.path.splitext(p)[1])

    for p in hits:
        if usable(p):
            _MCPB_RESOLVED = p
            return p
    if hits:
        raise Rejected(
            f"found mcpb at {hits[0]}, but that is npm's UNIX launcher inside "
            f"a Windows npm directory: it execs `node`, which is not installed "
            f"in this WSL distro. Install the Windows variant (mcpb.cmd should "
            f"sit beside it), install node in WSL, or set MCPB_BIN.")
    raise Rejected(
        "the mcpb CLI was not found on PATH. Install it with "
        "`npm install -g @anthropic-ai/mcpb`, or set MCPB_BIN to its full "
        "path. Inside WSL a Windows npm global usually lives at "
        "/mnt/c/Users/<you>/AppData/Roaming/npm/mcpb.cmd")


def _mcpb_dir(p: str) -> str:
    """A bundle directory inside the repo that actually holds a manifest.

    Checked here rather than letting mcpb fail: `mcpb pack` on the wrong
    directory silently produces a bundle of whatever it found, and a bundle
    with the wrong contents is exactly the failure this whole exercise was
    about.
    """
    d = _inrepo(p, must_be_dir=True)
    if not (Path(d) / "manifest.json").is_file():
        raise Rejected(f"no manifest.json in {p}; that is not a bundle source")
    return d


def _win_path(p: str) -> str:
    """/mnt/c/Users/x -> C:\\Users\\x. Unchanged if it is not a /mnt path.

    cmd.exe does not understand WSL paths, so anything handed to a .cmd has to
    be translated. Done here rather than by shelling out to `wslpath` because
    this runs on every mcpb call and the mapping is mechanical.
    """
    m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", p)
    if not m:
        return p
    return f"{m.group(1).upper()}:\\" + m.group(2).replace("/", "\\")


def _mcpb_launch(binary: str, args: list) -> list:
    """The argv that actually runs mcpb, given how it is installed.

    A `.cmd` IS NOT EXECUTABLE FROM LINUX. WSL's binfmt handler runs `.exe`
    directly, but a `.cmd` is a batch script: it needs cmd.exe to interpret
    it, and Python's exec reports the confusing

        [Errno 8] Exec format error: .../npm/mcpb.cmd

    So a Windows batch launcher gets wrapped, and every path argument is
    translated, because cmd.exe cannot see /mnt paths. A native Linux binary
    is run as-is.
    """
    if os.path.splitext(binary)[1].lower() in (".cmd", ".bat"):
        cmd = shutil.which("cmd.exe") or "/mnt/c/Windows/System32/cmd.exe"
        if not Path(cmd).exists():
            raise Rejected(
                f"mcpb is installed as a Windows batch launcher ({binary}), "
                f"which needs cmd.exe to run, and cmd.exe was not found. "
                f"Either WSL interop is disabled for this distro, or install "
                f"mcpb natively in WSL and set MCPB_BIN.")
        return [cmd, "/c", _win_path(binary)] + [_win_path(a) for a in args]
    return [binary] + args


def _mcpb_default_out(directory: str) -> str:
    """automation/mcpb/sotn-cmd -> automation/mcpb/sotn-cmd.mcpb

    Repo-relative, so _inrepo still gets to vet it.
    """
    rel = str(directory).replace("\\", "/").rstrip("/")
    return f"{rel}.mcpb"


def _mcpb_argv(sub: str, path_arg: str, extra: list | None = None) -> list:
    """VALIDATE THE ARGUMENTS FIRST, resolve the binary second.

    The obvious `[resolve_mcpb(), sub, _check(path)]` evaluates left to right,
    so a caller who passes a directory with no manifest, or one outside the
    repo, is told "the mcpb CLI was not found on PATH". That is a true
    statement about a machine without mcpb and a completely misleading answer
    to what they actually got wrong -- and on a machine WITH mcpb the same
    call would report the real problem, so the error would depend on
    unrelated state. Argument errors are the caller's; a missing binary is
    the environment's. Report the caller's first, always.
    """
    checked = (_mcpb_dir(path_arg) if sub in ("validate", "pack")
               else _inrepo(path_arg))
    return _mcpb_launch(resolve_mcpb(), [sub, checked] + (extra or []))


REGISTRY = {
    # mcpb bundles. Read-only validate/info; pack writes ONE .mcpb beside the
    # manifest it was given.
    "mcpb_validate": lambda directory: _mcpb_argv("validate", directory),
    # ALWAYS pass an explicit output. `mcpb pack` writes to the CURRENT
    # DIRECTORY, and this runs with cwd=REPO, so the default dropped
    # sotn-cmd.mcpb in the repo root -- next to the Makefile, nowhere near the
    # bundle, and not where the installed one lives. Default it to
    # <bundle-dir>.mcpb, which is the existing convention:
    # automation/mcpb/sotn-cmd/ packs to automation/mcpb/sotn-cmd.mcpb.
    "mcpb_pack":     lambda directory, output=None: _mcpb_argv(
        "pack", directory,
        [_inrepo(output, must_exist=False)] if output
        else [_inrepo(_mcpb_default_out(directory), must_exist=False)]),
    "mcpb_info":     lambda path: _mcpb_argv("info", path),
    # make goals
    "make_build":             lambda version="us": _make("build", version),
    "make_extract":           lambda version="us": _make("extract", version),
    "make_expected":          lambda version="us": _make("expected", version),
    "make_clean":             lambda version="us": _make("clean", version),
    "make_force_symbols":     lambda version="us": _make("force_symbols", version),
    "make_function_finder":   lambda version=None: _make("function-finder",
                                                         version if version else None),
    "make_reports":           lambda: _make("reports"),
    "make_duplicates_report": lambda: _make("duplicates-report"),
    # asm-differ
    "asm_diff": lambda symbol, version="us", overlay="dra", make_first=True, fmt="plain": (
        [PYTHON, "tools/asm-differ/diff.py"]
        + (["-m"] if make_first else [])
        + (["--format", fmt] if (fmt in FMT or _reject_fmt(fmt)) else [])
        + ["--version", _v(version), "--overlay", _ov(overlay), _sym(symbol)]
    ),
    # decomp-permuter
    # decomp-permuter. Every one of these flags was defaulted away until
    # 2026-08-03, and the defaults are bad for this project:
    #
    #   -j            the permuter is MULTITHREADED and defaults to ONE thread.
    #                 Five seeds were searched for hours on one core each.
    #   --stop-on-zero  without it a run that FINDS a match keeps going, so the
    #                 job never ends and nothing downstream notices the win.
    #   --better-only  the log was one line per iteration at ~10/second, which
    #                 is what made the stall analysis parse 141k lines to find
    #                 one number. Only improvements are interesting.
    #   --algorithm   difflib is the default; levenshtein scores differently and
    #                 is worth A/B-ing on a stalled seed.
    #
    # threads is capped: this box also runs a 4-worker fleet and a build, and
    # oversubscribing turns a background search into a foreground stall.
    # debug=True is `--debug`: compile and score the BASE ONLY, then exit. It
    # does not search at all, and that is the point.
    #
    # SCORE ONE CANDIDATE IN SECONDS INSTEAD OF BUILDING FOR MINUTES. Until this
    # was exposed there were exactly two ways to find out whether a hand-written
    # body matched: a full `make build` plus verify_build, which is minutes and
    # exclusive and can only test one tree state at a time, or an unbounded
    # permuter search, which answers a different question. So every codegen
    # hypothesis -- statement order, which local holds a value, whether a
    # constant is folded -- cost a build, and the CONSTANT_DIVERGENT twin ports
    # are nothing but a series of those hypotheses. func_us_801C2044_from_no0
    # burned two builds on guesses that this would have scored in seconds each.
    #
    # It is a SCORE, not a verdict. Same caveat as a zero from a search: the
    # permuter compiles the one function in isolation against target.o, so it
    # sees neither the overlay's size nor the 81 SHA-1s. Zero here means "worth
    # a build"; only verify_build means matched.
    "permuter": lambda work_dir, threads=4, stop_on_zero=True,
                       better_only=True, algorithm="", debug=False: (
        [PYTHON, "tools/decomp-permuter/permuter.py"]
        + (["--debug"] if debug else
           ["-j", _count(threads, 1, 16)]
           + (["--stop-on-zero"] if stop_on_zero else [])
           + (["--better-only"] if better_only else []))
        + (["--algorithm", algorithm] if algorithm in ("difflib", "levenshtein")
           else [] if not algorithm else _bad_algo(algorithm))
        + [_inrepo(work_dir, must_be_dir=True)]),
    "permuter_import": lambda c_file, asm_file: [
        PYTHON, "tools/decomp-permuter/import.py",
        _inrepo(c_file), _inrepo(asm_file)],
    # queue seeding. MUST go through the connector rather than a sandbox shell:
    # SOTN_QUEUE defaults to ~/sotn-work/queue.jsonl, so a different HOME
    # resolves to a DIFFERENT queue file. The sandbox's copy reported 33 matched
    # while the real one had 134, and seeding the wrong file would have forked
    # the harness's state silently. init is additive and skips existing ids.
    "queue_init": lambda from_file="automation/seed.us.txt": [
        PYTHON, "automation/scheduler.py", "init",
        "--from", _inrepo(from_file)],
    # Attach twin candidates to queue records. Non-destructive (it writes only
    # the `twin` field, never status), idempotent, and dry-run unless apply.
    # MUST run here rather than in a sandbox shell: SOTN_QUEUE resolves via
    # $HOME, so a different environment annotates a different queue file.
    # Discard uncommitted changes to ONE path. Destructive by design, which is
    # why it takes an explicit in-repo path and has no default and no recursive
    # "restore everything" form.
    #
    # WHY IT LIVES HERE: reverting a failed experiment used to mean running
    # `git checkout --` from the Cowork sandbox. That sandbox tears down its PID
    # namespace when a call ends or hits the 45s cap, which killed git
    # mid-operation and left a stale .git/index.lock that blocked every
    # subsequent commit. Git WRITES must run on this side; the sandbox may read
    # the repo but must never mutate it.
    "git_restore": lambda path, confirm_orphan=False: (
        ["git", "checkout", "--",
         _restorable(path, confirm_orphan)]),
    # Run a read-only analysis script in WSL, where there is no 45s ceiling.
    "run_analysis": lambda script, args="": (
        [PYTHON, _script(script)] + _args(args)),
    # ONE record, named, in the foreground.
    #
    # fleet_start was the only way to run a worker, and it launches N detached
    # loops that claim by rank. That is right for production and useless for
    # verification: proving the m2c-only path meant working one specific
    # 68865-char function that sat at the BOTTOM of a 160-record todo list, so
    # a fleet would have worked something else and reported success. The
    # options without this were to reorder the live queue or to run the worker
    # from a sandbox shell, and both are worse than a flag.
    #
    # WRITES. It edits the source file, builds, and reports to the queue,
    # exactly as a fleet worker does -- the point is that it is the SAME code
    # path, not a simulation of it. So: no default id, and start_job takes the
    # exclusive lock, which is what stops it racing a fleet or a build.
    #
    # MODEL_BACKEND IS PINNED, NOT INHERITED. This runs as a child of the
    # connector process, so without `env` it would silently take whatever
    # MODEL_BACKEND that process happens to hold. Every run here goes through
    # zen: the OpenCode CLI relays only `content` while these models fill
    # `reasoning_content` first, so it comes back empty most of the time, and
    # worse the larger the context. worker_once exists to test big functions.
    "worker_once": lambda only, dry_run=False: (
        ["env", "MODEL_BACKEND=zen", PYTHON,
         "automation/win/worker_direct.py", "once",
         "--only", _queue_id(only)] + (["--dry-run"] if dry_run else [])),
    "queue_annotate": lambda from_file="automation/twins.us.json", apply=False: (
        [PYTHON, "automation/scheduler.py", "annotate",
         "--from", _inrepo(from_file)] + (["--apply"] if apply else [])),
    # queue pruning. The ONLY destructive queue action, so it is dry-run unless
    # apply=True is passed explicitly, and scheduler.py refuses to touch
    # anything that is not `todo`.
    "queue_prune": lambda pattern, apply=False: (
        [PYTHON, "automation/scheduler.py", "prune", "--pattern", _pattern(pattern)]
        + (["--apply"] if apply else [])),
    # QUEUE BACKUP. The live queue is outside the repo (see scheduler.py's
    # _DEFAULT_QUEUE: a cloud sync daemon destroyed the in-repo one in 2026-07),
    # and until 2026-08-17 that meant it had no backup at all. A git checkpoint
    # protected the source and not the record of how it was produced.
    #
    # snapshot is read-only with respect to the queue and takes the writer's
    # lock, so it cannot catch a running fleet mid-write. `out` is validated as
    # an in-repo path: a snapshot that lands outside the repo cannot be
    # committed, which defeats the entire point.
    "queue_snapshot": lambda out="": (
        [PYTHON, "automation/scheduler.py", "snapshot"]
        + (["--out", _inrepo(out, must_exist=False)] if out else [])),
    # restore is the most destructive action in this file: it replaces every
    # record. Hence confirm, and hence scheduler.py snapshotting what it is
    # about to replace before replacing it.
    "queue_restore": lambda from_file, confirm=False: (
        [PYTHON, "automation/scheduler.py", "restore",
         "--from", _inrepo(from_file)] + (["--confirm"] if confirm else [])),
    # queue visibility (read-only): lets the orchestrator poll in one call
    "queue_stats": lambda: [PYTHON, "automation/scheduler.py", "stats"],
    "queue_list":  lambda status="": ([PYTHON, "automation/scheduler.py", "list"]
                                      + (["--status", _status(status)] if status else [])),
    # scoped git (no general shell): status, stage-all, commit, push
    "git_status":  lambda: ["git", "status", "--short"],
    "git_add_all": lambda: ["git", "add", "-A"],
    "git_commit":  lambda message: ["git", "commit"] + _msg_argv(message),
    # Restore paths from HEAD, not from the index.
    #
    # git_restore above is `git checkout -- <path>`, which restores from the
    # INDEX. That is the wrong tool after anything has staged a bad state, and
    # there was no right tool: recovering three files on 2026-08-02 meant
    # running `git checkout HEAD -- ...` in the sandbox, which hit a stale
    # index.lock left by an earlier sandbox git that the 45s cap had killed.
    # Every git write belongs on this side; that means every git write we
    # actually need has to exist here.
    "git_restore_from_head": lambda path, confirm_orphan=False: (
        ["git", "checkout", "HEAD", "--",
         _restorable(path, confirm_orphan)]),

    # ---- the rest of git ----
    #
    # ALL of git lives here now, by instruction: the Cowork sandbox is forbidden
    # from running git against this repo at all. It is not a style preference.
    # The sandbox reaches the repo over a Windows mount and dies at 45s, and on
    # 2026-08-02 that killed a rebase mid-flight, left a stale .git/index.lock,
    # and rolled three source files back to a pre-shim state while the commits
    # themselves stayed correct. Recovering took four more sandbox git calls,
    # two of which also timed out.
    #
    # There is still no general `git` passthrough. Each action below is a fixed
    # argv shape with validated arguments, and everything destructive needs
    # confirm=True.

    # read-only
    "git_log": lambda n=15, path="": (
        ["git", "log", f"-{_count(n)}", "--format=%h %an <%ae> %ad %s",
         "--date=short"] + (["--", _inrepo(path, must_exist=False)] if path else [])),
    "git_diff": lambda path="", staged=False, ref="": (
        ["git", "diff"] + (["--staged"] if staged else [])
        + ([_ref(ref)] if ref else [])
        + (["--", _inrepo(path, must_exist=False)] if path else [])),
    "git_diff_stat": lambda ref="", staged=False: (
        ["git", "diff", "--stat"] + (["--staged"] if staged else [])
        + ([_ref(ref)] if ref else [])),
    "git_submodule_state": lambda path: (
        ["git", "-C", _submodule_dir(path), "status", "--porcelain=v2",
         "--branch"]),
    "git_submodule_diff": lambda path, staged=False, stat=False: (
        ["git", "-C", _submodule_dir(path), "diff"]
        + (["--staged"] if staged else [])
        + (["--stat"] if stat else [])),
    "git_show": lambda ref="HEAD", path="": (
        ["git", "show", "--format=%h %an <%ae> %ad%n%n%B", "--date=short",
         _ref(ref)] + (["--", _inrepo(path, must_exist=False)] if path else [])),
    # READ A FILE AS IT EXISTS AT A REF. git_show CANNOT DO THIS: `git show
    # <ref> -- <path>` prints the diff that commit made to that path, which is
    # empty for every commit that did not touch it. The content form is
    # `git show <ref>:<path>`, and _ref REFUSES colons -- correctly, since a
    # ref is not a pathspec -- so the two halves were assembled here instead of
    # loosening the ref rule.
    #
    # Built 2026-08-16 because the RCEN harvest needed upstream's
    # splat.us.strcen.yaml to learn where unk_1F0D8's .data segment starts,
    # and there was no way to read an upstream file at all. `git_diff` shows
    # what differs but not what IS, and the harvest is a question about what
    # upstream has, not about the delta. The whole 42-function harvest is
    # blocked on questions of exactly this shape.
    #
    # Read-only by construction: `git show` of a blob writes nothing, and the
    # path still goes through _inrepo, so this cannot read outside the repo or
    # inside .git.
    "git_show_file": lambda ref="HEAD", path="": (
        ["git", "show",
         f"{_ref(ref)}:{_relpath(_inrepo(path, must_exist=False))}"]),
    # ADOPT A FILE FROM ANOTHER REF INTO THE WORKING TREE.
    #
    # git_show_file made upstream READABLE; this makes it ADOPTABLE. The
    # difference is not convenience, it is whether the harvest can run at all:
    # src/st/e_thornweed_corpseweed.h is 884 lines, and the only way to bring it
    # in without this was to read all 884 through the model's context and type
    # them back out through write_file. Three of the four shared headers left in
    # the ST/RNO0 harvest are that size or larger, and a transcription is a
    # chance to introduce a difference into a file whose entire value is being
    # byte-for-byte upstream's.
    #
    # `git checkout <ref> -- <path>` also stages the path. That is correct here
    # and worth stating: the standing rule is to stage files explicitly and
    # never `git add -A`, and this stages exactly the one path asked for.
    #
    # Guarded by _adoptable, not _restorable: see that docstring for why the
    # test is "is the destination dirty" rather than "is it an orphan".
    "git_checkout_path": lambda ref, path, confirm_overwrite=False: (
        ["git", "checkout", _ref(ref), "--",
         _adoptable(path, confirm_overwrite)]),
    # DELETE ONE TRACKED FILE, from the tree and the index together.
    #
    # There was no way to delete a file at all, and that gap had already shaped
    # the tree: src/st/rno0/unk_4A320.c is a shim over giantbro_helpers_2.h and
    # should be named after it, but a rename means removing the old path, so
    # the wrong name was committed with a comment explaining why it had to
    # stay. Retiring src/st/en_thornweed_corpseweed.h, which upstream replaced
    # and which four overlays still compile beside its replacement, is blocked
    # on the same thing.
    #
    # -f ONLY under confirm_dirty. `git rm` refuses a file with uncommitted
    # changes by itself, which is the same judgement _removable makes; without
    # forwarding the flag the override would be cosmetic and git would veto
    # what this layer just allowed.
    "git_rm": lambda path, confirm_dirty=False, confirm_splat_ref=False: (
        ["git", "rm"] + (["-f"] if confirm_dirty else [])
        + ["--", _removable(path, confirm_dirty, confirm_splat_ref)]),
    # RENAME, preserving history and staging both halves.
    #
    # Not git_rm plus a fresh write: that loses the connection between the two
    # paths, and for a file whose value is being byte-identical to upstream the
    # rewrite is also a chance to introduce a difference. See _movable for why
    # the splat guard only looks at the SOURCE stem.
    "git_mv": lambda src, dst, confirm_overwrite=False,
                     confirm_splat_ref=False: (
        ["git", "mv", "--"]
        + _movable(src, dst, confirm_overwrite, confirm_splat_ref)),
    # FETCH IS READ-ONLY and the only way to learn what upstream has done.
    # Without it the fork could not even measure its own drift: on 2026-08-09
    # the local upstream/master was still f6bfa379, last fetched 2026-08-01,
    # and "how far behind are we" was unanswerable.
    #
    # Safe by construction: fetch writes only remote-tracking refs, never the
    # working tree, never HEAD, and never a branch this repo builds from.
    # Merging or rebasing that ref remains a separate, deliberate act.
    # `upstream` push is DISABLED at the remote level, so this cannot become a
    # route to publishing anything.
    "git_fetch": lambda remote="upstream": (
        ["git", "fetch", "--no-tags", "--prune", _remote(remote)]),
    "git_log_range": lambda rng="", n=40, path="": (
        ["git", "log", f"-{_count(n)}", "--format=%h %ad %s", "--date=short"]
        + ([_rev_range(rng)] if rng else [])
        + (["--", _inrepo(path, must_exist=False)] if path else [])),
    "git_diff_stat_range": lambda rng="": (
        ["git", "diff", "--stat", _rev_range(rng)]),
    "git_rev_parse": lambda ref="HEAD": ["git", "rev-parse", _ref(ref)],
    "git_branch_list": lambda: ["git", "branch", "-vv", "--no-color"],
    "git_remote_list": lambda: ["git", "remote", "-v"],
    "git_ls_files": lambda path="": (
        ["git", "ls-files"] + ([_inrepo(path, must_exist=False)] if path else [])),
    "git_config_get": lambda key: (
        ["git", "config", "--get", _cfg_key(key)]),
    "git_stash_list": lambda: ["git", "stash", "list"],
    # Is a merge/rebase/cherry-pick half-finished? Answers the question that
    # sent this whole mess sideways, without needing a shell to stat .git.
    "git_state": lambda: ["git", "status", "--porcelain=v2", "--branch"],

    # write, non-destructive
    "git_config_set": lambda key, value: (
        ["git", "config", _cfg_key(key), _cfg_value(value)]),
    "git_add": lambda path: ["git", "add", "--", _inrepo(path, must_exist=False)],
    # Untrack a path WITHOUT deleting it from disk.
    #
    # The gap this fills: .gitignore does not untrack anything already committed,
    # and on 2026-08-02 four workers' generated ctx.<name>.c files (38k lines)
    # were committed because the ignore rules listed two exact filenames rather
    # than a pattern. Fixing the pattern was not enough; the files had to come
    # out of the index, and there was no allowlisted way to do it.
    #
    # --cached is the whole point: the fleet is usually still writing these
    # files, so removing them from disk would break a running worker.
    "git_rm_cached": lambda path, confirm=False: (
        _confirmed(confirm, "git rm --cached")
        or ["git", "rm", "--cached", "-r", "--",
            _inrepo(path, must_exist=False)]),
    "git_commit_amend": lambda message="", reset_author=False: (
        ["git", "commit", "--amend"]
        + (["--reset-author"] if reset_author else [])
        + (_msg_argv(message) if message else ["--no-edit"])),
    "git_checkout_branch": lambda name, create=False: (
        ["git", "checkout"] + (["-b"] if create else []) + [_ref(name)]),
    "git_stash_push": lambda message="": (
        ["git", "stash", "push"] + (["-m", _msg_argv(message)[1]] if message else [])),

    # write, destructive: confirm=True required
    "git_reset": lambda mode="mixed", ref="HEAD", confirm=False: (
        _confirmed(confirm, f"git reset --{mode}")
        or ["git", "reset", f"--{mode if mode in _RESET_MODES else _bad_mode(mode)}",
            _ref(ref)]),
    "git_stash_pop": lambda confirm=False: (
        _confirmed(confirm, "git stash pop") or ["git", "stash", "pop"]),
    "git_rebase_abort": lambda confirm=False: (
        _confirmed(confirm, "git rebase --abort") or ["git", "rebase", "--abort"]),
    "git_rebase_continue": lambda confirm=False: (
        _confirmed(confirm, "git rebase --continue")
        or ["git", "rebase", "--continue"]),
    "git_merge_abort": lambda confirm=False: (
        _confirmed(confirm, "git merge --abort") or ["git", "merge", "--abort"]),
    "git_cherry_pick_abort": lambda confirm=False: (
        _confirmed(confirm, "git cherry-pick --abort")
        or ["git", "cherry-pick", "--abort"]),
    # Removes UNTRACKED files. Scoped to one path and never -x, so it cannot
    # reach .gitignore'd build output or the venv.
    "git_clean": lambda path, confirm=False: (
        _confirmed(confirm, "git clean -fd")
        or ["git", "clean", "-fd", "--", _inrepo(path, must_exist=False)]),
    # Push takes NO ARGUMENTS, and that is the safety property. There is no
    # remote to choose, no refspec to craft and no flag to pass, so there is
    # nothing to validate and nothing to get wrong. It always means "publish the
    # current branch to our fork".
    #
    # Why that matters here: this repo has TWO remotes, and `upstream` is
    # Xeeynamo/sotn-decomp with a push URL configured. A parameterised push
    # action would put "which remote" in the hands of the caller, one typo away
    # from pushing 104 local commits at the project we forked from. `origin` is
    # hard-coded, and the upstream push URL is separately disabled in the repo
    # config (git remote set-url --push upstream DISABLED) as a second layer.
    #
    # No --force, no --delete, no --mirror, no --all, no `src:dst` refspec: none
    # of them are reachable, because none of them are expressible.
    "git_push":    lambda: ["git", "push", "origin", "HEAD"],
}


def build_argv(action: str, **kwargs) -> list[str]:
    if action not in REGISTRY:
        raise Rejected(f"unknown action '{action}'. allowed: {sorted(REGISTRY)}")
    try:
        return REGISTRY[action](**kwargs)
    except TypeError as e:
        raise Rejected(f"bad arguments for {action}: {e}")


# Actions whose useful content is at the START of the output. Truncating from
# the tail (the default, right for build logs) destroyed asm-differ's header,
# which is exactly where the match percentage lives, and did so silently.
_HEAD_TRUNCATE = {"asm_diff"}


# How old an index.lock must be before we will call it abandoned. Every git
# operation this connector runs finishes in well under a second on this repo;
# two minutes is far beyond any legitimate hold.
_LOCK_STALE_SECONDS = 120


def clear_stale_index_lock() -> dict | None:
    """Remove a git index.lock that is provably abandoned.

    WHY THIS IS NEEDED. `.git/index.lock` is created by any git command that
    refreshes the index, including read-only-looking ones like `git status`.
    If that git is KILLED mid-operation the lock survives and blocks every
    later commit until someone deletes it by hand. Two ways that happens here:

      - a git command run from the Cowork sandbox, which kills every call at
        45s, over a slow Windows mount. Observed twice on 2026-08-02, both
        times during read-only audit work.
      - run()'s own subprocess timeout, which kills the child the same way.

    SAFETY. This will not touch a lock that might be live. It requires the file
    to be older than _LOCK_STALE_SECONDS, and it reports what it did rather
    than deleting silently. A fresh lock is left alone and the caller gets
    git's normal "another git process seems to be running" error, which is the
    correct outcome when a real one is.
    """
    lock = REPO / ".git" / "index.lock"
    try:
        st = lock.stat()
    except FileNotFoundError:
        return None
    except OSError:
        return None
    age = time.time() - st.st_mtime
    if age < _LOCK_STALE_SECONDS:
        return {"stale_lock": "present but FRESH; left alone",
                "age_seconds": round(age, 1)}
    try:
        lock.unlink()
    except OSError as e:
        return {"stale_lock": f"could not remove: {e}",
                "age_seconds": round(age, 1)}
    return {"stale_lock": "REMOVED (abandoned)", "age_seconds": round(age, 1),
            "note": "a git process was killed mid-operation. Do not run git "
                    "from the Cowork sandbox; it is capped at 45s."}


# Actions that read or write the shared build state. The fleet serialises
# exactly these with automation/.build.lock; this connector did not take part
# in that protocol at all, which is a direct path from an unverified edit to a
# recorded match: verify_build could report all_ok about a tree containing a
# worker's applied candidate.
_NEEDS_BUILD_LOCK = {
    "make_build", "make_extract", "make_clean", "make_expected",
    "make_force_symbols", "make_reports", "make_duplicates_report",
    "make_function_finder", "verify_build", "asm_diff", "git_restore",
}
# Matches BuildLock.stale_after in worker_direct.py. A lock older than this is
# from a crashed worker and the fleet itself would take it over.
_BUILD_LOCK_STALE_SECONDS = 3600


def build_lock_holder() -> dict | None:
    """Is a fleet worker inside its apply/build/verify critical section?

    Returns a description when the lock is held and FRESH, else None. Callers
    should refuse rather than proceed: running a build here while a worker has
    its candidate applied verifies the wrong source, and running one while it
    builds corrupts the shared build directory.
    """
    lock = REPO / "automation" / ".build.lock"
    try:
        st = lock.stat()
        body = lock.read_text(errors="replace").strip()
    except (FileNotFoundError, OSError):
        return None
    age = time.time() - st.st_mtime
    if age > _BUILD_LOCK_STALE_SECONDS:
        return None                       # stale; the fleet would take it over
    return {"held_by": body or "unknown", "age_seconds": round(age, 1)}


def run(action: str, timeout: float = 3600, **kwargs) -> dict:
    # LINE SLICING, for git_show_file only. Popped BEFORE build_argv, because
    # these are not git arguments: they post-filter git's output.
    #
    # Why it is worth having. Harvesting from upstream means lifting two or
    # three functions out of a file that is often 1500 lines, and the whole
    # file is then carried around for the rest of the session. us_3E79C.c
    # alone is 42KB in this fork and larger upstream. Slicing at the source
    # turns "read everything to use 3% of it" into a bounded read, and the
    # hunk headers from git_diff already say which lines to ask for.
    #
    # Deliberately dumb: no `sed`, no shell, just a slice of the captured
    # stdout, so it cannot change what git is asked to do.
    _start = kwargs.pop("start", 0) or 0
    _count = kwargs.pop("count", 0) or 0
    argv = build_argv(action, **kwargs)
    if DRYRUN:
        return {"action": action, "argv": argv, "dry_run": True}
    run_cwd = REPO
    debug_output_dir = None
    if action == "permuter" and kwargs.get("debug"):
        # Upstream debug mode writes two fixed relative paths with replacement:
        # ./debug_source.c and ./debug_compiled_object.o. Running from REPO
        # therefore overwrote unrelated untracked evidence. Give every debug
        # pass an owned, unique directory beneath the seed that produced it.
        work_dir = Path(argv[-1]).resolve()
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        debug_root = work_dir / "debug-runs"
        debug_root.mkdir(parents=True, exist_ok=True)
        try:
            resolved_debug_root = debug_root.resolve(strict=True)
            resolved_debug_root.relative_to(work_dir)
        except (OSError, ValueError) as exc:
            raise Rejected(
                "permuter debug-runs must resolve inside its work directory"
            ) from exc
        suffix = 0
        while True:
            tail = f"{stamp}-{os.getpid()}" + (f"~{suffix}" if suffix else "")
            candidate = resolved_debug_root / tail
            try:
                candidate.mkdir()
                debug_output_dir = candidate
                break
            except FileExistsError:
                suffix += 1
        run_cwd = debug_output_dir

        # The script path is fixed by REGISTRY but relative to REPO. An explicit
        # SOTN_PYTHON may also be a repo-relative path. Once cwd belongs to the
        # seed, make both path-like command entries absolute. Leave bare names
        # such as python3 alone so normal PATH lookup still works.
        if (not Path(argv[0]).is_absolute()
                and ("/" in argv[0] or "\\" in argv[0])):
            argv[0] = str((REPO / argv[0]).resolve())
        script = Path(argv[1])
        if not script.is_absolute():
            argv[1] = str((REPO / script).resolve())
    if action in _NEEDS_BUILD_LOCK:
        holder = build_lock_holder()
        if holder:
            return {
                "action": action, "argv": argv, "dry_run": False,
                "refused": True, "build_lock": holder,
                "error": (
                    f"REFUSED: a fleet worker holds automation/.build.lock "
                    f"({holder['held_by']}, {holder['age_seconds']}s ago). It "
                    f"has a candidate applied to the tree, so building or "
                    f"verifying now would inspect the wrong source and could "
                    f"record a false match. Stop the fleet first, or wait."),
            }
    lock_note = None
    if argv and argv[0] == "git":
        lock_note = clear_stale_index_lock()
    try:
        p = subprocess.run(argv, cwd=str(run_cwd), capture_output=True, text=True,
                           timeout=timeout)
        head = action in _HEAD_TRUNCATE
        cut = (lambda s: s[:MAX_OUT]) if head else (lambda s: s[-MAX_OUT:])
        _sliced = None
        if (_start or _count) and p.returncode == 0:
            _all = p.stdout.splitlines()
            _lo = max(0, int(_start) - 1) if _start else 0
            _hi = _lo + int(_count) if _count else len(_all)
            # Numbered, because the point of asking for a range is usually to
            # ask for a neighbouring one next, and counting from a bare slice
            # is how off-by-one errors get made.
            p_stdout = "\n".join(f"{_lo + i + 1}\t{ln}"
                                 for i, ln in enumerate(_all[_lo:_hi]))
            _sliced = {"total_lines": len(_all),
                       "returned": f"{_lo + 1}..{min(_hi, len(_all))}"}
            p = subprocess.CompletedProcess(p.args, p.returncode,
                                            p_stdout, p.stderr)
        out = {
            "action": action, "argv": argv, "dry_run": False,
            "returncode": p.returncode,
            "stdout": cut(p.stdout), "stderr": cut(p.stderr),
            "truncated": len(p.stdout) > MAX_OUT or len(p.stderr) > MAX_OUT,
            "truncated_from": ("tail" if not head else "end (head kept)"),
        }
        if lock_note:
            out["index_lock"] = lock_note
        if _sliced:
            out["slice"] = _sliced
        if debug_output_dir is not None:
            out["debug_output_dir"] = str(debug_output_dir)
        return out
    except subprocess.TimeoutExpired:
        # A killed git leaves .git/index.lock behind. Say so here rather than
        # letting the NEXT caller discover it as a confusing failure.
        res = {"action": action, "argv": argv, "dry_run": False,
               "timed_out": True, "timeout": timeout}
        if debug_output_dir is not None:
            res["debug_output_dir"] = str(debug_output_dir)
        if argv and argv[0] == "git":
            res["warning"] = ("git was killed by the timeout; it may have left "
                              ".git/index.lock. The next git action through "
                              "this connector will clear it if it is stale.")
        return res


def allowed() -> list[str]:
    return sorted(REGISTRY)


# ---------------------------------------------------------------------------
# Asynchronous execution.
#
# `run()` above holds the request open until the command finishes. For a build
# that is minutes, and the MCP transport gives up first: 8 tool calls died with
# "MCP error -32001: Request timed out" in a single day while the build carried
# on in the background. The caller then cannot tell a finished build from a
# half-finished one, which is the dangerous part -- verifying a mid-build tree
# reports a stale pass.
#
# So long actions get started and polled instead. argv still comes from
# build_argv, so the allowlist remains the only way to construct a command.
# ---------------------------------------------------------------------------

# Imported defensively. A bare `import jobs` resolves only when this module's
# own directory happens to be on sys.path, which is true when the connector is
# launched as a script from automation/mcp and false if anything imports
# commands_client from elsewhere. A module-level ImportError here would take the
# whole connector down at startup, which has already happened once with a
# different missing name. Fall back to an explicit path load, and if even that
# fails, degrade to async being unavailable rather than to a dead server.
try:                                                    # noqa: E402
    import jobs as _jobs
except ImportError:                                     # pragma: no cover
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "jobs", str(Path(__file__).resolve().parent / "jobs.py"))
        _jobs = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_jobs)
    except Exception:
        _jobs = None

LONG_ACTIONS = {
    "make_build", "make_extract", "make_expected", "make_clean",
    "make_force_symbols", "make_reports", "make_duplicates_report",
    # A worker's per-function budget is minutes: m2c, then up to three
    # model calls, each followed by a full build. It is never a run() call.
    "make_function_finder", "run_analysis", "permuter", "worker_once",
}


def _need_jobs() -> dict | None:
    if _jobs is None:
        return {"error": "async jobs unavailable: automation/mcp/jobs.py could "
                         "not be imported. Use run() with a generous timeout, "
                         "and expect the transport to cut it off."}
    return None


def start_job(action: str, **kwargs) -> dict:
    unavailable = _need_jobs()
    if unavailable:
        return unavailable
    if action not in LONG_ACTIONS:
        raise Rejected(f"start_job is for long actions: {sorted(LONG_ACTIONS)}. "
                       f"Call run() for {action!r}; it returns promptly.")
    argv = build_argv(action, **kwargs)
    if DRYRUN:
        return {"action": action, "argv": argv, "dry_run": True, "started": False}
    # The permuter owns its work_dir and shares nothing: it compiles into that
    # directory, never writes build/, and never runs make. So N seeds can be
    # searched at once, and serialising them wasted the most valuable pool the
    # project has. Everything else stays exclusive -- concurrent `make build`s
    # share one build directory and produce artifacts matching nothing.
    if action == "permuter":
        return _jobs.start(action, argv, cwd=str(REPO), exclusive=False,
                           slug=Path(kwargs.get("work_dir", "")).name)
    return _jobs.start(action, argv, cwd=str(REPO))


def job_status(job_id: str, wait_s: float = 25.0, tail_lines: int = 40) -> dict:
    return _need_jobs() or _jobs.status(job_id, wait_s=wait_s,
                                        tail_lines=tail_lines)


def job_list(limit: int = 20) -> dict:
    return _need_jobs() or _jobs.list_jobs(limit=limit)


def job_cancel(job_id: str) -> dict:
    return _need_jobs() or _jobs.cancel(job_id)


# ---------------------------------------------------------------------------
# Scoped in-repo filesystem access.
#
# These let the harness read, navigate, and edit the WSL2 repo tree THROUGH the
# connector when Cowork is not connected directly to the WSL2 clone. They are
# direct file operations (not a shell), constrained to the repo, with .git and
# size guards. Reads/list/search are read-only and always run; writes respect
# SOTN_CMD_DRYRUN so a dry-run connector never mutates files.
# ---------------------------------------------------------------------------

FS_MAX_READ = int(os.environ.get("SOTN_FS_MAXREAD", "400000"))     # bytes returned
FS_MAX_WRITE = int(os.environ.get("SOTN_FS_MAXWRITE", "2000000"))  # bytes accepted
FS_ACTIONS = ["read_file", "write_file", "list_dir", "search_repo"]


def _resolve(path: str, must_exist: bool, want_dir: bool | None) -> Path:
    rp = (REPO / path).resolve()
    root = REPO.resolve()
    if rp != root and root not in rp.parents:
        raise Rejected("path must resolve inside the repo")
    if rp == (root / ".git") or (root / ".git") in rp.parents:
        raise Rejected("path is inside .git and is not writable/readable here")
    if must_exist and not rp.exists():
        raise Rejected(f"path does not exist: {path}")
    if want_dir is True and rp.exists() and not rp.is_dir():
        raise Rejected(f"not a directory: {path}")
    if want_dir is False and rp.exists() and not rp.is_file():
        raise Rejected(f"not a file: {path}")
    return rp


def fs_read(path: str) -> dict:
    rp = _resolve(path, must_exist=True, want_dir=False)
    data = rp.read_bytes()
    text = data[:FS_MAX_READ].decode("utf-8", errors="replace")
    return {"path": path, "bytes": len(data),
            "truncated": len(data) > FS_MAX_READ, "content": text}


def fs_write(path: str, content: str) -> dict:
    rp = _resolve(path, must_exist=False, want_dir=False)
    enc = content.encode("utf-8")
    if len(enc) > FS_MAX_WRITE:
        raise Rejected(f"content exceeds {FS_MAX_WRITE} bytes")
    if DRYRUN:
        return {"path": path, "dry_run": True, "would_write_bytes": len(enc)}
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_bytes(enc)
    return {"path": path, "dry_run": False, "bytes_written": len(enc)}


def fs_list(path: str = ".") -> dict:
    rp = _resolve(path, must_exist=True, want_dir=True)
    entries = []
    for child in sorted(rp.iterdir()):
        entries.append({
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
            "size": (child.stat().st_size if child.is_file() else None),
        })
    return {"path": path, "entries": entries[:1000], "count": len(entries)}


def fs_search(query: str, path: str = ".", max_results: int = 200) -> dict:
    if not (1 <= len(query) <= 200):
        raise Rejected("query must be 1-200 chars")
    rp = _resolve(path, must_exist=True, want_dir=None)
    # ripgrep if available, else grep; query passed as argv (no shell).
    #
    # -E IS LOAD-BEARING. `grep -e` is BASIC regular expressions, where `|`
    # and `()` are ordinary characters, so `a|b` searched for the literal
    # three-character string "a|b" and returned nothing. ripgrep uses Rust
    # regex and treats the same pattern as alternation, so the two backends
    # silently disagreed and the answer depended on whether rg happened to be
    # installed.
    #
    # It failed toward FALSE NEGATIVES, which is the worst direction for a
    # search tool: "0 matches" reads as "this symbol does not exist". On
    # 2026-08-10 that produced four wrong conclusions in one session,
    # including a claim in a commit message that three BO6 functions had no
    # twin anywhere in the tree. `PAL_ARMOR_LORD_UNK|E_ARMOR_LORD_UNK2`
    # returned 0 while the plain substring `ARMOR_LORD_UNK` returned 18.
    #
    # --no-ignore for the same reason: rg honours .gitignore and grep does
    # not, so a search under a gitignored path (nonmatchings/, build/) found
    # results or not depending on the backend. Both now see the same files.
    tool = "rg" if _has("rg") else "grep"
    if tool == "rg":
        argv = ["rg", "-n", "--no-heading", "--no-ignore", "-e", query,
                str(rp)]
    else:
        argv = ["grep", "-rnE", "-e", query, str(rp)]
    p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                       timeout=120)
    lines = [ln for ln in p.stdout.splitlines() if ln][:max_results]
    out = {"query": query, "path": path, "matches": lines,
           "count": len(lines), "engine": tool,
           "truncated": len(p.stdout.splitlines()) > max_results}
    # grep exits 1 for "no match" and >=2 for a REAL error (bad regex,
    # unreadable path). Those were indistinguishable before: both surfaced as
    # a clean, confident zero.
    if p.returncode >= 2:
        out["error"] = (p.stderr or "").strip()[:300] or f"rc={p.returncode}"
        out["count"] = -1
    return out


def _has(prog: str) -> bool:
    from shutil import which
    return which(prog) is not None


def verify_build(version: str = "us") -> dict:
    """THE ORACLE. Rebuild-independent check that every artifact hash matches.

    The charter defines correctness as "all hashes in config/check.<v>.sha
    reproduce", but make_build returns 0 on a tree whose artifacts do not
    match, so success there proves nothing. This is the missing tool: it runs
    the checksum file and reports a structured verdict.
    """
    # THE ORACLE MUST NOT READ A TREE SOMEONE ELSE IS MUTATING.
    #
    # verify_build lives only on the @mcp.tool() surface, not in REGISTRY, so
    # run()'s build-lock guard never sees it. Without this check it could
    # report all_ok about a tree containing a worker's applied, unverified
    # candidate -- a direct route from a non-matching change to a recorded
    # `matched`. Found by audit 2026-08-02 (F3).
    holder = build_lock_holder()
    if holder:
        return {"refused": True, "build_lock": holder, "all_ok": False,
                "verdict": "REFUSED: build lock held",
                "error": (
                    f"REFUSED: a fleet worker holds automation/.build.lock "
                    f"({holder['held_by']}, {holder['age_seconds']}s ago) and "
                    f"has a candidate applied. Verifying now would judge the "
                    f"wrong source. Stop the fleet first.")}
    v = _v(version)
    sha_file = f"config/check.{v}.sha"
    if not (REPO / sha_file).exists():
        raise Rejected(f"missing {sha_file}")
    tool = "shasum" if _has("shasum") else "sha1sum"
    p = subprocess.run([tool, "-c", sha_file], cwd=str(REPO),
                       capture_output=True, text=True, timeout=600)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    ok = [l for l in lines if l.endswith(": OK")]
    bad = [l for l in lines if not l.endswith(": OK")]
    total = sum(1 for l in (REPO / sha_file).read_text().splitlines() if l.strip())
    return {
        "version": v, "matched": len(ok), "expected": total,
        "failed": bad[:20], "all_ok": len(ok) == total and not bad,
        "verdict": (f"{len(ok)}/{total} OK" if len(ok) == total and not bad
                    else f"{len(ok)}/{total} OK, {len(bad)} FAILED"),
    }


def queue_report(function_id: str, status: str, proof: str = "",
                 score: str = "", notes: str = "",
                 keep_note: bool = True) -> dict:
    """Record an outcome through scheduler.py, the single queue writer.

    Without this the orchestrator can verify a match but has no sanctioned way
    to record it, and the charter forbids hand-editing work/queue.jsonl.
    The scheduler still refuses `matched` unless proof is supplied.
    """
    argv = [PYTHON, "automation/scheduler.py", "report",
            "--id", function_id, "--status", _status(status)]
    if proof:
        # Proof is a single-line provenance string (a path and a sha1), not a
        # commit message. It was validated with the old _msg(); that helper is
        # now multi-line-aware and belongs to commits only, so validate here.
        # Never shorten it here. Queue evidence is durable data, not display
        # text, and silent slicing previously destroyed the artifact details.
        p = " ".join(str(proof).split())
        if not p:
            raise Rejected("proof must not be blank")
        argv += ["--proof", p]
    if score:
        argv += ["--score", score]
    if notes:
        # The scheduler owns the record and must receive the complete note.
        # Any future size policy must reject loudly, never accept a prefix.
        argv += ["--notes", notes]
    if keep_note:
        argv.append("--keep-note")
    if DRYRUN:
        return {"action": "queue_report", "argv": argv, "dry_run": True}
    p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                       timeout=120)
    return {"action": "queue_report", "returncode": p.returncode,
            "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


FLEET_LOGS = "automation/logs"
FLEET_PIDS = "automation/logs/fleet.pids"
# Written by a deliberate fleet_stop. While it exists, fleet_start refuses.
#
# Rationale: an unattended watchdog with authority to start work will restart a
# fleet that a human stopped on purpose (e.g. while reconfiguring llama-server),
# and then quietly mutate the queue underneath them. A crashed fleet never calls
# fleet_stop, so no sentinel exists and automatic recovery still works. Only a
# deliberate stop is sticky.
FLEET_HOLD = "automation/logs/FLEET_HOLD"


# Worker log/PID basenames per backend. _fleet_pids_alive globs worker-*.pid and
# fleet_status globs worker-*.log, so any name of that shape is reaped and
# reported. Keeping the backend IN the name is what makes a mixed fleet legible:
# "worker-oc-2.log" says which model produced a given line without cross-
# referencing anything.
_BACKEND_TAG = {"llama": "llama", "cli": "oc", "zen": "zen"}


def opencode_preflight(timeout: int = 90) -> dict:
    """Ask the worker itself whether the OpenCode CLI is usable.

    Delegated rather than reimplemented: the worker owns binary resolution, so
    a check written here would be a second implementation free to drift from
    the one that actually runs.
    """
    argv = [PYTHON, "automation/win/worker_direct.py", "preflight"]
    env = dict(os.environ, MODEL_BACKEND="cli")
    try:
        p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                           timeout=timeout, env=env)
    except subprocess.SubprocessError as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    out = (p.stdout or "").strip()
    try:
        return json.loads(out.splitlines()[-1]) if out else {
            "ok": False, "error": "preflight produced no output",
            "stderr": (p.stderr or "")[:400]}
    except (ValueError, IndexError):
        return {"ok": False, "error": "preflight output was not JSON",
                "stdout": out[:400], "stderr": (p.stderr or "")[:400]}


def fleet_start(workers: int = 4, max_functions: int = 0,
                force: bool = False, backend: str = "zen",
                cli_workers: int = 0, opencode_model: str = "",
                reasoning: str = "") -> dict:
    """Launch detached worker_direct.py processes inside WSL.

    Lets the orchestrator run the volume tier without a human at a PowerShell
    prompt. Workers run natively here (worker_direct.py is OS-aware), write to
    automation/logs/worker-<tag>-N.log, and record their PIDs so fleet_stop can
    reap them.

    backend:
      "zen"   - `workers` workers on the Zen HTTP API. THE DEFAULT AND THE
                ONE TO USE.
      "llama" - `workers` local llama workers (the original behaviour)
      "cli"   - `workers` OpenCode CLI workers, same models via the CLI
      "mixed" - `workers` llama workers AND `cli_workers` OpenCode workers,
                against the same queue

    THE NAME NOW MATCHES THE THING. "http" used to mean local llama, which was
    backwards: zen is the backend that talks HTTP, llama is the one that is
    llama. The old name misled a caller into starting a cli fleet on
    2026-08-09. "http" is still accepted and now resolves to "zen", because
    that is what the word describes.

    Why mixed is worth having: the two backends fail differently. llama is free
    and unlimited but has plateaued; the Zen models may be stronger but draw on
    a shared account-wide quota that parallel workers drain proportionally
    faster. Running both means the quota is spent on functions llama has already
    failed rather than on ones it would have got anyway.

    opencode_model and reasoning are both PER-WORKER LISTS, comma-separated and
    assigned round-robin. One value applies to every worker; N values give N
    workers one each. This is how a bake-off runs as a single fleet rather than
    as a sequence of them:

        fleet_start(workers=4, reasoning="none,low")
            -> w1 none, w2 low, w3 none, w4 low

    All four claim from the same queue at the same moment, so which arm gets
    which function is decided by claim order rather than by the experimenter,
    and the tree is in one state for the whole run. Two consecutive fleets
    would confound the arm with everything that changed between them.

    reasoning accepts "low" (the worker default) and "none"/"off"/"0". Nothing
    else: Zen answers 503 to medium, 500 to high, and ignores reasoning_budget.

    Total workers is generations in flight. apply/build/verify is serialised by
    a lock, so beyond ~4 the extras mostly queue. llama-server must be started
    with --parallel >= the llama worker count or generation serialises too.
    """
    backend = (backend or "zen").strip().lower()
    # Legacy alias. Resolve it before validation so exactly one spelling
    # reaches the rest of the function and the returned plan reports the
    # backend that actually ran.
    if backend == "http":
        backend = "zen"
    if backend not in ("llama", "cli", "mixed", "zen"):
        raise Rejected("backend must be zen, llama, cli or mixed")

    # `zen` reuses the HTTP worker path, pointed at OpenCode Zen instead of
    # localhost. It exists because `opencode run` relays only `content` and
    # these are reasoning models: while one thinks, our stdout is empty and
    # indistinguishable from a dead call. Going direct captures
    # reasoning_content too, and drops opencode's ~14s per-call git snapshot.
    n_zen = int(workers) if backend == "zen" else 0
    n_llama = int(workers) if backend in ("llama", "mixed") else 0
    n_cli = (int(workers) if backend == "cli"
             else int(cli_workers) if backend == "mixed" else 0)
    if backend == "mixed" and n_cli < 1:
        raise Rejected("backend=mixed needs cli_workers >= 1")
    # n_zen belongs in the total. Omitting it made backend="zen" fail the
    # 1-16 check with "got 0" even though workers=2 was requested: the
    # count existed, it just was not being counted.
    total = n_llama + n_cli + n_zen
    if not 1 <= total <= 16:
        raise Rejected(f"total workers must be 1-16 (got {total})")

    # May be a comma-separated LIST, one entry per worker, assigned round-robin
    # exactly like opencode_model. That list form is what makes the #111 A/B a
    # SINGLE fleet: `reasoning="none,low"` puts both arms on the same queue at
    # the same moment, so claim order randomises which arm gets which function
    # and the tree state is identical for both. Running two fleets one after
    # the other would confound the arm with everything that changed in between,
    # which is the whole failure this experiment is meant to avoid.
    efforts = [e.strip().lower() for e in (reasoning or "").split(",") if e.strip()]
    # Only the two values the provider actually distinguishes. `medium` is
    # HTTP 503 on Zen and `high` is HTTP 500, and reasoning_budget is ignored
    # outright, so anything else would be a knob that reads as configured and
    # does nothing -- the failure mode this project keeps finding.
    bad = [e for e in efforts if e not in ("none", "off", "0", "low")]
    if bad:
        raise Rejected(f"reasoning entries must be 'low' (the default) or "
                       f"'none'/'off'/'0'; Zen 503s on medium and 500s on "
                       f"high. Rejected: {', '.join(sorted(set(bad)))}")

    plan = {"backend": backend, "llama_workers": n_llama, "zen_workers": n_zen, "cli_workers": n_cli,
            "opencode_model": opencode_model or "(worker default)",
            "reasoning": ",".join(efforts) or "(worker default: low)"}
    if DRYRUN:
        return {"action": "fleet_start", "dry_run": True, **plan,
                "note": "would launch detached workers"}

    (REPO / FLEET_LOGS).mkdir(parents=True, exist_ok=True)
    hold = REPO / FLEET_HOLD
    if hold.exists() and not force:
        try:
            why = hold.read_text(encoding="utf-8").strip()
        except OSError:
            why = "(unreadable)"
        return {"action": "fleet_start", "started": 0, "held": True,
                "hold_written": why,
                "note": "fleet is on HOLD after a deliberate fleet_stop and will "
                        "NOT auto-start. An unattended caller must respect this. "
                        "To override intentionally: fleet_start(force=True)."}
    if force and hold.exists():
        try:
            hold.unlink()
        except OSError:
            pass
    running = _fleet_pids_alive()
    if running:
        return {"action": "fleet_start", "started": 0, "already_running": running,
                "note": "fleet already active; call fleet_stop first"}

    # Preflight BEFORE spawning anything. A cli worker that cannot reach the CLI
    # still claims queue records and escalates them, so the damage is a poisoned
    # queue rather than a clean failure. Check once; refuse if it fails.
    pf = None
    if n_cli:
        pf = opencode_preflight()
        if not pf.get("ok"):
            return {"action": "fleet_start", "started": 0, **plan,
                    "preflight": pf,
                    "note": "OpenCode CLI is not usable from the worker's "
                            "environment, so NO workers were started. The fleet "
                            "runs inside WSL; opencode is installed on Windows. "
                            "Set OPENCODE_BIN, or launch via "
                            "automation\\win\\start_fleet.ps1 on Windows."}

    extra = f" --max {int(max_functions)}" if int(max_functions) > 0 else ""
    # One bash invocation launches every worker and writes the pid file, so a
    # slow MCP round trip cannot leave a half-started, untracked fleet.
    #
    # Env is set per-worker on the command line rather than exported once: the
    # two groups need DIFFERENT values for MODEL_BACKEND, and a single export
    # would silently give every worker the last one set. That is exactly how the
    # original version ended up unable to launch anything but llama.
    parts = [f"cd {shlex.quote(str(REPO))} && mkdir -p {FLEET_LOGS} && "
             f"_stamp=$(date +%Y%m%d-%H%M%S) && : > {FLEET_PIDS}"]
    # opencode_model may be a comma-separated LIST. Each cli worker is then
    # assigned one round-robin, which is how a model bake-off runs: launch N cli
    # workers across N models and compare hit rates from one fleet. A single
    # value assigns that model to every cli worker, unchanged.
    models = [m.strip() for m in (opencode_model or "").split(",") if m.strip()]
    for be, count in (("llama", n_llama), ("cli", n_cli), ("zen", n_zen)):
        if not count:
            continue
        tag = _BACKEND_TAG[be]
        if be == "zen" and models:
            # Same per-worker model rotation as cli. OPENCODE_MODEL is reused
            # as the selector; worker_direct strips the `opencode/` prefix,
            # since that prefix is a CLI concept and Zen wants a bare id.
            arr = " ".join(shlex.quote(m) for m in models)
            model_setup = f"_m=({arr}); "
            pick = '_sel=${_m[$(((i-1) % ${#_m[@]}))]}; '
            env = "MODEL_BACKEND=zen OPENCODE_MODEL=$_sel"
        elif be == "cli" and models:
            # Bash array indexed by worker number so each gets its own model.
            arr = " ".join(shlex.quote(m) for m in models)
            model_setup = f"_m=({arr}); "
            pick = '_sel=${_m[$(((i-1) % ${#_m[@]}))]}; '
            env = "MODEL_BACKEND=cli OPENCODE_MODEL=$_sel"
        else:
            model_setup = ""
            pick = ""
            env = f"MODEL_BACKEND={be}"
        # The A/B knob (#111). worker_direct reads REASONING_EFFORT and
        # thinking_params() returns NO_THINKING for none/off/0; the sweep in
        # its header already proved the server honours `enable_thinking:
        # false` and produces 0 reasoning tokens, so the OFF arm is real
        # rather than a flag the provider ignores. Everything finer --
        # reasoning_budget, medium, high -- is ignored or errors on Zen, which
        # is why this is a two-value experiment and not a sweep.
        #
        # Its own bash array, indexed by worker number like the model array, so
        # ONE fleet can run both arms. `_r` and `_re` rather than reusing `_m`
        # and `_sel`: the two lists rotate independently and may be different
        # lengths, and 2 models x 2 efforts across 4 workers only covers all
        # four combinations if the indices are separate.
        #
        # Empty means "do not set it", so the default path is byte-identical
        # to before and an unrelated fleet cannot be silently re-tuned.
        if efforts:
            earr = " ".join(shlex.quote(e) for e in efforts)
            model_setup += f"_r=({earr}); "
            pick += '_re=${_r[$(((i-1) % ${#_r[@]}))]}; '
            env = "REASONING_EFFORT=$_re " + env
        parts.append(
            f"{model_setup}for i in $(seq 1 {count}); do "
            f"  {pick}"
            # ARCHIVE, do not delete. `rm -f` here destroyed the evidence
            # for every earlier run, so an empty-response audit could only
            # ever see the current fleet. The cost of keeping them is a few
            # KB per run; the cost of deleting them is being unable to tell
            # whether a model is getting worse.
            f"  if [ -s {FLEET_LOGS}/worker-{tag}-$i.log ]; then "
            f"    mkdir -p {FLEET_LOGS}/archive/$_stamp && "
            f"    mv {FLEET_LOGS}/worker-{tag}-$i.log "
            f"       {FLEET_LOGS}/archive/$_stamp/ ; fi; "
            f"  {env} WORKER_NAME=fleet-{tag}-$i setsid nohup python3 "
            f"automation/win/worker_direct.py loop{extra} "
            f"> {FLEET_LOGS}/worker-{tag}-$i.log 2>&1 < /dev/null & "
            f"  echo $! >> {FLEET_PIDS}; "
            f"  sleep 0.4; "
            f"done"
        )
    parts.append(f"cat {FLEET_PIDS}")
    script = " && ".join(parts)

    p = subprocess.run(["bash", "-lc", script], cwd=str(REPO),
                       capture_output=True, text=True, timeout=120)
    pids = [int(x) for x in p.stdout.split() if x.isdigit()]
    out = {"action": "fleet_start", "started": len(pids), "pids": pids,
           **plan, "logs": FLEET_LOGS,
           "note": "detached; poll with fleet_status, stop with fleet_stop"}
    if pf:
        out["preflight"] = pf
    if len(pids) != total:
        out["warning"] = (f"expected {total} workers, launched {len(pids)}; "
                          f"stderr: {(p.stderr or '')[:300]}")
    return out


def _fleet_pids_alive() -> list[int]:
    """Live worker PIDs, from pid files only.

    Sources, in order: the launcher's pid file, then per-worker pid files that
    each worker writes for itself on startup. Both are cross-checked against
    /proc so dead entries are ignored.

    Deliberately NOT pgrep. Matching on the command line is unsafe: any shell
    running a command that merely mentions worker_direct.py matches too. In
    testing that returned pids 1, 2 and 5 (the sandbox init and two of my own
    shells), which fleet_stop would then have tried to kill. Self-registration
    is the only source that cannot produce a false positive.
    """
    candidates: set[int] = set()
    f = REPO / FLEET_PIDS
    if f.exists():
        candidates |= {int(x) for x in f.read_text().split() if x.isdigit()}
    d = REPO / FLEET_LOGS
    if d.is_dir():
        for pf in d.glob("worker-*.pid"):
            try:
                t = pf.read_text().strip()
            except OSError:
                continue
            if t.isdigit():
                candidates.add(int(t))

    alive: list[int] = []
    for pid in sorted(candidates):
        proc = Path("/proc") / str(pid)
        if not proc.exists():
            continue
        # Confirm it is genuinely a worker, not a recycled pid.
        try:
            text = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace")
        except OSError:
            continue
        if "worker_direct.py" in text and "python" in text:
            alive.append(pid)
    return alive


def fleet_status(tail: int = 2) -> dict:
    """Which workers are alive, plus the last line of each log.

    A silent fleet is indistinguishable from a stuck one, so always look at the
    log tails, not just the PID count.
    """
    alive = _fleet_pids_alive()
    logs = {}
    d = REPO / FLEET_LOGS
    if d.is_dir():
        for lf in sorted(d.glob("worker-*.log")):
            try:
                lines = [l for l in lf.read_text(errors="replace").splitlines() if l.strip()]
                logs[lf.name] = lines[-int(tail):] if lines else ["(empty)"]
            except OSError:
                logs[lf.name] = ["(unreadable)"]
    return {"action": "fleet_status", "alive": alive, "count": len(alive),
            "logs": logs}


def refresh_zen_models(timeout: float = 20.0) -> dict:
    """Reconcile opencode.json against the live Zen catalogue.

    RUNS ON FLEET STOP, not start. Start must not block on a network call, and
    at stop nothing is racing for the config; the refreshed list is then in
    place for the NEXT run, which is when it matters.

    The catalogue drifts and the harness never noticed. Measured 2026-08-03:
    `hy3-free` had been withdrawn but was still configured and burned a worker
    slot on every rotation, while FOUR free models (laguna-s-2.1-free,
    ling-3.0-flash-free, ling-3.0-tiny-free, longcat-2.0-free) were live and
    absent from the config -- the fleet had been running on 5 of 9 available
    models without anyone knowing.

    Free-tier only. The endpoint serves 61 models and most of them bill; the
    filter is a `-free` suffix plus `big-pickle`, which is free without one.

    BEST EFFORT, ALWAYS. Any failure here returns a note and nothing else. A
    stop that fails because a catalogue lookup timed out would strand claimed
    queue records, which is far worse than a stale model list.
    """
    import urllib.request
    cfg_path = str(REPO / "automation" / "opencode" / "opencode.json")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        slot = cfg["provider"]["opencode"]["models"]
        base = cfg["provider"]["opencode"]["options"]["baseURL"].rstrip("/")
        req = urllib.request.Request(
            base + "/models",
            headers={"User-Agent": "opencode/1.18.12",
                     "x-opencode-client": "cli"})
        key = os.environ.get("MODEL_API_KEY", "").strip()
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.load(r)
        live = [m.get("id", "") for m in (doc.get("data") or [])]
        if not live:
            return {"ok": False, "note": "endpoint returned no models; "
                                         "config left alone"}
        free = sorted(m for m in live
                      if m.endswith("-free") or m == "big-pickle")
        added = [m for m in free if m not in slot]
        gone = [m for m in slot if m not in live]
        if not added and not gone:
            return {"ok": True, "changed": False, "free_models": len(free)}
        for m in gone:
            slot.pop(m, None)
        for m in added:
            slot[m] = {"name": m}
        tmp = cfg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
            f.write("\n")
        os.replace(tmp, cfg_path)          # atomic; a torn config breaks every worker
        return {"ok": True, "changed": True, "added": added, "removed": gone,
                "free_models": len(free),
                "note": "new models are UNTESTED; run probe_provider.py "
                        "--battery before trusting one"}
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "note": f"{type(e).__name__}: {str(e)[:160]}"}


def fleet_stop(hold: bool = True) -> dict:
    """Stop all workers and return their claimed records to 'todo'.

    A killed worker cannot release its own claim, so records would otherwise
    sit 'claimed' forever and be skipped by every later run. Always reclaim.
    """
    if DRYRUN:
        return {"action": "fleet_stop", "dry_run": True}
    alive = _fleet_pids_alive()
    for pid in alive:
        subprocess.run(["bash", "-lc", f"kill {pid} 2>/dev/null || true"],
                       cwd=str(REPO), capture_output=True, text=True, timeout=30)
    time.sleep(1)
    still = _fleet_pids_alive()
    for pid in still:
        subprocess.run(["bash", "-lc", f"kill -9 {pid} 2>/dev/null || true"],
                       cwd=str(REPO), capture_output=True, text=True, timeout=30)
    r = subprocess.run([PYTHON, "automation/scheduler.py", "reclaim",
                        "--older-than-min", "0"], cwd=str(REPO),
                       capture_output=True, text=True, timeout=120)
    lock = REPO / "automation" / ".build.lock"
    if lock.exists():
        try:
            lock.unlink()
        except OSError:
            pass
    # RESTORE SOURCE HERE, not in the dying workers. Each worker's SIGTERM
    # handler already calls replay_pending_journals, but it runs inside the
    # process being killed and takes BuildLock first; during a fleet stop the
    # lock's owner is also being killed, so the handler can block and the
    # `kill -9` above lands before it restores anything. On 2026-08-09 that
    # left src/st/rchi/e_gaibon.c holding a candidate, with its journal still
    # on disk, after a stop that reported success.
    #
    # This runs in a process nobody is killing, after every worker is dead and
    # after the stale lock is gone, so it cannot lose that race. It is also
    # idempotent: a journal whose owner is still alive is skipped, and one
    # already replayed is gone.
    restored = 0
    replay_note = ""
    unaccounted = ""
    # COUNT THE JOURNALS FIRST. On 2026-08-10 this reported restored=0 while
    # the file HAD been restored and the journal HAD been consumed, which is a
    # contradiction the output could not explain: the count is the only thing
    # recorded, so a zero is indistinguishable from "there was nothing to do".
    #
    # replay_pending_journals() walks the WHOLE pending directory, so the
    # journal this call was going to restore can legitimately be consumed by
    # any other process that replays first. That makes the count a property of
    # global state rather than of this call, and it cannot be fixed by
    # counting harder. What it can be is SELF-EXPLANATORY: record what was
    # pending going in, and if the replay claims zero against a non-empty
    # directory, surface the subprocess's own log instead of a bare number.
    try:
        pending_before = sorted(
            p.name for p in (REPO / "automation" / "logs" / "pending")
            .glob("*.json"))
    except OSError:
        pending_before = []
    try:
        rp = subprocess.run(
            [PYTHON, "automation/win/worker_direct.py", "replay"],
            cwd=str(REPO), capture_output=True, text=True, timeout=120)
        for line in (rp.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("{"):
                restored = int(json.loads(line).get("restored") or 0)
        if rp.returncode != 0:
            replay_note = (rp.stderr or rp.stdout or "").strip()[-200:]
        elif pending_before and not restored:
            # Not necessarily wrong: another process may have got there first,
            # and the tree can be perfectly fine. So this is NOT routed into
            # replay_note, which raises "JOURNAL REPLAY FAILED"; it gets its
            # own field. Crying failure at a benign race is how a real failure
            # stops being believed.
            unaccounted = (
                f"replay restored 0 but {len(pending_before)} journal(s) were "
                f"pending on entry ({', '.join(pending_before[:4])}). Most "
                f"likely another process replayed them first. Worker log: "
                + ((rp.stderr or "").strip()[-400:] or "(silent)"))
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        # A failed replay must not stop the rest of the teardown, but it must
        # be LOUD: the tree may still hold a candidate.
        replay_note = f"{type(e).__name__}: {e}"
    try:
        (REPO / FLEET_PIDS).unlink()
    except OSError:
        pass
    held = False
    if hold:
        # A deliberate stop is sticky: fleet_start refuses until someone passes
        # force=True. Automated recycling must call fleet_stop(hold=False).
        try:
            (REPO / FLEET_HOLD).write_text(
                f"stopped at {dt.datetime.now().isoformat(timespec='seconds')}; "
                f"fleet_start will refuse until force=True", encoding="utf-8")
            held = True
        except OSError:
            pass
    out = {"action": "fleet_stop", "stopped": alive, "hold": held,
           "reclaim": r.stdout.strip(),
           "restored_files": restored,
            # Refreshed here so the NEXT run starts from a current catalogue.
            "models": refresh_zen_models(),
           "note": "claims released, lock cleared"
                   + (f"; restored {restored} source file(s) from journal"
                      if restored else "")
                   + ("; HOLD set, fleet_start will refuse without force"
                      if held else "; no hold (recycle allowed)")}
    if replay_note:
        out["replay_error"] = replay_note
        out["note"] += ("; JOURNAL REPLAY FAILED, check `git status src/` "
                        "before building")
    if unaccounted:
        # Distinct from replay_error on purpose: the tree is probably fine.
        # This exists so the count and the directory can never disagree
        # silently again, which is what made the 2026-08-10 occurrence
        # unexplainable after the fact.
        out["replay_unaccounted"] = unaccounted
        out["note"] += ("; journals were pending but this call restored none "
                        "(see replay_unaccounted)")

    # P2 (#108): A MATCH THAT IS ONLY IN THE WORKING TREE IS NOT SAFE YET.
    #
    # The queue records `matched` the instant the oracle accepts, but the body
    # is still uncommitted at that point, and nothing ever said so. On
    # 2026-08-16 that cost five verified matches: func_us_801B1C60,
    # EntityOlroxAfterImage, func_801904B8, func_us_801CFC98 and
    # BO6_RicEntityCrashReboundStone. git history shows their bodies were never
    # committed AT ALL -- not reverted, never landed. Two of them shared a
    # working tree with func_us_801B1E5C, which WAS committed (c36ee5742) and
    # survives; the other two went with the tree.
    #
    # matched_audit could have caught every one of them at any point. Nobody
    # ran it, because nothing asked. Fleet stop is the moment the risk window
    # opens: work has finished, the operator is walking away, and any
    # uncommitted match is now one `git restore` from being a false record.
    #
    # REPORT ONLY. It does not commit: what to commit and how to describe it is
    # a human call, and a teardown path is the worst place to start writing
    # history. It just refuses to let the window open quietly.
    try:
        ma = subprocess.run(
            [PYTHON, "automation/matched_audit.py"],
            cwd=str(REPO), capture_output=True, text=True, timeout=300)
        for line in (ma.stdout or "").splitlines():
            if line.startswith("SUMMARY "):
                out["matched_audit"] = line.strip()
                # uncommitted is the actionable one: real work, one restore
                # from becoming a lie. LOST is already lost and needs triage,
                # not urgency.
                if " uncommitted 0 " not in line:
                    out["note"] += ("; UNCOMMITTED MATCHES EXIST -- commit them "
                                    "before any restore or reset, see "
                                    "matched_audit")
                elif " LOST 0 " not in line:
                    out["note"] += ("; matched records are LOST (claimed but "
                                    "absent from the tree), run matched_audit")
                break
    except (subprocess.SubprocessError, OSError):
        # Never let a diagnostic break a teardown.
        out["matched_audit"] = "could not run"
    return out


def capabilities() -> dict:
    return {"commands": sorted(REGISTRY), "filesystem": FS_ACTIONS,
            "dry_run": DRYRUN, "repo": str(REPO)}
