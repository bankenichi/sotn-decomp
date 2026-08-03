"""
commands_client: a hard-allowlisted command runner for the SOTN decomp repo.

Security model:
  - There is NO general shell. Only the actions in REGISTRY can run.
  - Every argument is validated (enums, strict regexes, in-repo path checks).
  - subprocess is always invoked with an argv list, never shell=True.
  - stdout/stderr are truncated to keep Claude's context small.
  - Each action has a timeout. Set SOTN_CMD_DRYRUN=1 to return argv without running.

Stdlib only, so it is importable and unit-testable anywhere.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[2]))
PYTHON = os.environ.get("SOTN_PYTHON", "python3")
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
    rp = (REPO / p).resolve()
    if not str(rp).startswith(str(REPO.resolve())):
        raise Rejected("path must resolve inside the repo")
    if must_exist and not rp.exists():
        raise Rejected(f"path does not exist: {p}")
    if must_be_dir and rp.exists() and not rp.is_dir():
        raise Rejected(f"path is not a directory: {p}")
    return str(rp)


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
    "codebase_index.py",
    "quality_audit.py",
    "provenance_check.py",
    "review_checks.py",
    "decl_coverage.py",
    "test_twin_wiring.py",
    "opencode_size_bisect.py",
    "test_build_classifier.py",
    "test_review_gate.py",
    "test_shim_gate.py",
    "relocation_check.py",
    "find_data_segment.py",
    "test_journal_replay.py",
    "fn_diff.py",
    "shim_sweep.py",
    "test_shim_sweep.py",
    "test_queue_owner.py",
    "test_connector_surfaces.py",
    "test_build_attribution.py",
    "escalation_triage.py",
    "test_stub_locate.py",
    "test_permuter_seed.py",
    "permuter_stall.py",
    "permuter_promote.py",
    "permuter_supervisor.py",
}
# Deliberately narrow: flags, numbers, and in-repo-looking relative paths.
# No spaces, quotes, semicolons, redirects, or leading dashes-with-spaces, so
# nothing here can be reinterpreted by a shell even if one were ever involved.
_ARG_RX = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./=-]{0,120}$|^--?[A-Za-z0-9][A-Za-z0-9_-]{0,40}$")


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


REGISTRY = {
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
    "permuter": lambda work_dir, threads=4, stop_on_zero=True,
                       better_only=True, algorithm="": (
        [PYTHON, "tools/decomp-permuter/permuter.py",
         "-j", _count(threads, 1, 16)]
        + (["--stop-on-zero"] if stop_on_zero else [])
        + (["--better-only"] if better_only else [])
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
    "git_restore": lambda path: (
        ["git", "checkout", "--", _inrepo(path, must_exist=False)]),
    # Run a read-only analysis script in WSL, where there is no 45s ceiling.
    "run_analysis": lambda script, args="": (
        [PYTHON, _script(script)] + _args(args)),
    "queue_annotate": lambda from_file="automation/twins.us.json", apply=False: (
        [PYTHON, "automation/scheduler.py", "annotate",
         "--from", _inrepo(from_file)] + (["--apply"] if apply else [])),
    # queue pruning. The ONLY destructive queue action, so it is dry-run unless
    # apply=True is passed explicitly, and scheduler.py refuses to touch
    # anything that is not `todo`.
    "queue_prune": lambda pattern, apply=False: (
        [PYTHON, "automation/scheduler.py", "prune", "--pattern", _pattern(pattern)]
        + (["--apply"] if apply else [])),
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
    "git_restore_from_head": lambda path: (
        ["git", "checkout", "HEAD", "--", _inrepo(path, must_exist=False)]),

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
    "git_show": lambda ref="HEAD", path="": (
        ["git", "show", "--format=%h %an <%ae> %ad%n%n%B", "--date=short",
         _ref(ref)] + (["--", _inrepo(path, must_exist=False)] if path else [])),
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
    argv = build_argv(action, **kwargs)
    if DRYRUN:
        return {"action": action, "argv": argv, "dry_run": True}
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
        p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                           timeout=timeout)
        head = action in _HEAD_TRUNCATE
        cut = (lambda s: s[:MAX_OUT]) if head else (lambda s: s[-MAX_OUT:])
        out = {
            "action": action, "argv": argv, "dry_run": False,
            "returncode": p.returncode,
            "stdout": cut(p.stdout), "stderr": cut(p.stderr),
            "truncated": len(p.stdout) > MAX_OUT or len(p.stderr) > MAX_OUT,
            "truncated_from": ("tail" if not head else "end (head kept)"),
        }
        if lock_note:
            out["index_lock"] = lock_note
        return out
    except subprocess.TimeoutExpired:
        # A killed git leaves .git/index.lock behind. Say so here rather than
        # letting the NEXT caller discover it as a confusing failure.
        res = {"action": action, "argv": argv, "dry_run": False,
               "timed_out": True, "timeout": timeout}
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
    "make_function_finder", "run_analysis", "permuter",
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
    tool = "rg" if _has("rg") else "grep"
    if tool == "rg":
        argv = ["rg", "-n", "--no-heading", "-e", query, str(rp)]
    else:
        argv = ["grep", "-rn", "-e", query, str(rp)]
    p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                       timeout=120)
    lines = [ln for ln in p.stdout.splitlines() if ln][:max_results]
    return {"query": query, "path": path, "matches": lines,
            "count": len(lines), "truncated": len(p.stdout.splitlines()) > max_results}


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
                 score: str = "", notes: str = "") -> dict:
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
        p = " ".join(str(proof).split())
        if not p:
            raise Rejected("proof must not be blank")
        argv += ["--proof", p[:200]]
    if score:
        argv += ["--score", score]
    if notes:
        argv += ["--notes", notes[:250]]
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
_BACKEND_TAG = {"http": "llama", "cli": "oc"}


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
                force: bool = False, backend: str = "http",
                cli_workers: int = 0, opencode_model: str = "") -> dict:
    """Launch detached worker_direct.py processes inside WSL.

    Lets the orchestrator run the volume tier without a human at a PowerShell
    prompt. Workers run natively here (worker_direct.py is OS-aware), write to
    automation/logs/worker-<tag>-N.log, and record their PIDs so fleet_stop can
    reap them.

    backend:
      "http"  - `workers` local llama workers (the original behaviour)
      "cli"   - `workers` OpenCode CLI workers on the free Zen models
      "mixed" - `workers` llama workers AND `cli_workers` OpenCode workers,
                against the same queue

    Why mixed is worth having: the two backends fail differently. llama is free
    and unlimited but has plateaued; the Zen models may be stronger but draw on
    a shared account-wide quota that parallel workers drain proportionally
    faster. Running both means the quota is spent on functions llama has already
    failed rather than on ones it would have got anyway.

    Total workers is generations in flight. apply/build/verify is serialised by
    a lock, so beyond ~4 the extras mostly queue. llama-server must be started
    with --parallel >= the llama worker count or generation serialises too.
    """
    backend = (backend or "http").strip().lower()
    if backend not in ("http", "cli", "mixed"):
        raise Rejected("backend must be http, cli or mixed")

    n_http = int(workers) if backend in ("http", "mixed") else 0
    n_cli = (int(workers) if backend == "cli"
             else int(cli_workers) if backend == "mixed" else 0)
    if backend == "mixed" and n_cli < 1:
        raise Rejected("backend=mixed needs cli_workers >= 1")
    total = n_http + n_cli
    if not 1 <= total <= 16:
        raise Rejected(f"total workers must be 1-16 (got {total})")

    plan = {"backend": backend, "llama_workers": n_http, "cli_workers": n_cli,
            "opencode_model": opencode_model or "(worker default)"}
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
             f": > {FLEET_PIDS}"]
    # opencode_model may be a comma-separated LIST. Each cli worker is then
    # assigned one round-robin, which is how a model bake-off runs: launch N cli
    # workers across N models and compare hit rates from one fleet. A single
    # value assigns that model to every cli worker, unchanged.
    models = [m.strip() for m in (opencode_model or "").split(",") if m.strip()]
    for be, count in (("http", n_http), ("cli", n_cli)):
        if not count:
            continue
        tag = _BACKEND_TAG[be]
        if be == "cli" and models:
            # Bash array indexed by worker number so each gets its own model.
            arr = " ".join(shlex.quote(m) for m in models)
            model_setup = f"_m=({arr}); "
            pick = '_sel=${_m[$(((i-1) % ${#_m[@]}))]}; '
            env = "MODEL_BACKEND=cli OPENCODE_MODEL=$_sel"
        else:
            model_setup = ""
            pick = ""
            env = f"MODEL_BACKEND={be}"
        parts.append(
            f"{model_setup}for i in $(seq 1 {count}); do "
            f"  {pick}"
            f"  rm -f {FLEET_LOGS}/worker-{tag}-$i.log; "
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
    return {"action": "fleet_stop", "stopped": alive, "hold": held,
            "reclaim": r.stdout.strip(),
            "note": "claims released, lock cleared"
                    + ("; HOLD set, fleet_start will refuse without force"
                       if held else "; no hold (recycle allowed)")}


def capabilities() -> dict:
    return {"commands": sorted(REGISTRY), "filesystem": FS_ACTIONS,
            "dry_run": DRYRUN, "repo": str(REPO)}
