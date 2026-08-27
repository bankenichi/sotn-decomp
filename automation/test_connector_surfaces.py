#!/usr/bin/env python3
"""The connector has TWO surfaces. This asserts they agree.

WHY
    commands_client.REGISTRY is the allowlist of shell actions.
    The @mcp.tool() decorators in sotn_cmd_mcp.py are what a caller can actually
    invoke. They are separate lists maintained by hand, and a name in one but not
    the other is a wiring bug that presents as a capability.

    It has bitten twice. verify_build existed only as a decorator, so a
    REGISTRY-only audit under-reported it. Later an action was added to REGISTRY
    but never decorated: it was uncallable, list_allowed still showed it, and
    reading that list looked like confirmation. Both cost a connector restart,
    which is the most expensive unit of work in this project.

    Restarts are why this is a test and not a runtime check. A runtime check
    tells you after you have already paid.

Run: python3 automation/test_connector_surfaces.py
"""
from __future__ import annotations

import errno
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch as _patch

REPO = Path(__file__).resolve().parent.parent
MCP = REPO / "automation" / "mcp"
sys.path.insert(0, str(MCP))

import pathlib

FAILS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def decorated_tools() -> set[str]:
    """Parse the decorators out of the source.

    Deliberately textual rather than importing the module and inspecting
    FastMCP. Importing pulls in the mcp package and constructs a server, and the
    registry attribute names differ between FastMCP versions; a test that breaks
    on an unrelated upgrade is worse than no test.
    """
    src = (MCP / "sotn_cmd_mcp.py").read_text()
    return set(re.findall(r"@mcp\.tool\(\)\s*\ndef\s+(\w+)\s*\(", src))


def main() -> int:
    import commands_client as cc

    registry = set(cc.REGISTRY)
    tools = decorated_tools()

    print(f"\nREGISTRY actions: {len(registry)}   @mcp.tool() functions: {len(tools)}")

    # Tools with no REGISTRY action are legitimate: they are implemented in
    # Python inside commands_client rather than as a shell argv.
    print("\nevery REGISTRY action is callable")
    uncallable = sorted(registry - tools)
    check(not uncallable,
          f"no REGISTRY action lacks an @mcp.tool() (missing: {uncallable})")

    print("\ngit is fully covered on both surfaces")
    git_reg = {a for a in registry if a.startswith("git_")}
    git_tools = {t for t in tools if t.startswith("git_")}
    check(git_reg <= git_tools,
          f"every git_* action is callable (missing: {sorted(git_reg - git_tools)})")
    # The operations that a session actually needs, named explicitly. This is
    # the list that was incomplete on 2026-08-02 and forced git into the
    # sandbox, which is now forbidden.
    required = {
        "git_status", "git_state", "git_log", "git_diff", "git_diff_stat",
        "git_submodule_state", "git_submodule_diff",
        "git_show", "git_rev_parse", "git_branch_list", "git_remote_list",
        "git_ls_files", "git_add", "git_add_all", "git_commit",
        "git_commit_amend", "git_push", "git_restore", "git_restore_from_head",
        "git_reset", "git_checkout_branch", "git_clean",
        "git_stash_push", "git_stash_pop", "git_stash_list",
        "git_rebase_abort", "git_rebase_continue", "git_merge_abort",
        "git_cherry_pick_abort", "git_config_get", "git_config_set",
    }
    missing = sorted(required - git_tools)
    check(not missing, f"no required git operation is absent (missing: {missing})")

    print("\nsubmodule inspection is read-only and declaration-scoped")
    _sm_state = cc.REGISTRY["git_submodule_state"](path="tools/psyz")
    check(_sm_state[:3] == ["git", "-C", str((REPO / "tools/psyz").resolve())],
          "submodule state uses a fixed git -C path inside the repo")
    check(_sm_state[3:] == ["status", "--porcelain=v2", "--branch"],
          "submodule state has a fixed read-only argv tail")
    _sm_diff = cc.REGISTRY["git_submodule_diff"](
        path="tools/saturn-splitter", staged=True, stat=True)
    check(_sm_diff[-3:] == ["diff", "--staged", "--stat"],
          "submodule diff exposes only staged and stat switches")
    for _bad_submodule in (
        "src", "tools", "../outside", "tools/psyz/.",
        "tools/m2c/../psyz", str((REPO / "tools/psyz").resolve()),
    ):
        try:
            cc.REGISTRY["git_submodule_state"](path=_bad_submodule)
            check(False, f"undeclared submodule path is refused: {_bad_submodule}")
        except cc.Rejected:
            check(True, f"undeclared submodule path is refused: {_bad_submodule}")

    print("\ndestructive git actions cannot run by default")
    must_confirm = ["git_reset", "git_clean", "git_stash_pop",
                    "git_rebase_abort", "git_rebase_continue",
                    "git_merge_abort", "git_cherry_pick_abort"]
    for act in must_confirm:
        kw = {"path": "automation"} if act == "git_clean" else {}
        try:
            cc.REGISTRY[act](**kw)
            check(False, f"{act} refuses without confirm=True")
        except cc.Rejected:
            check(True, f"{act} refuses without confirm=True")

    print("\nno tool is defined after mcp.run(), which would never register it")
    # THE failure this missed. mcp.run() serves forever, so a tool defined below
    # the __main__ guard is never executed and never registered -- while a
    # source-grepping test like this one sees it and passes. On 2026-08-02
    # exactly that happened: 25 git tools were appended after the guard,
    # `commands` listed all of them, `mcp_tools` listed none, and it cost two
    # connector restarts to find. Grepping the source is not enough; the ORDER
    # is the property that matters.
    src_order = (MCP / "sotn_cmd_mcp.py").read_text()
    guard = src_order.find('if __name__ == "__main__":')
    check(guard != -1, "the __main__ guard exists")
    after = src_order[guard:]
    orphans = re.findall(r"@mcp\.tool\(\)\s*\ndef\s+(\w+)", after)
    check(not orphans,
          f"no @mcp.tool() is defined after mcp.run() (unreachable: {orphans})")
    last_tool = src_order.rfind("@mcp.tool()")
    check(last_tool < guard,
          "the entry point is the LAST thing in the file")

    print("\njob_start forwards the arguments each action needs")
    import inspect as _i
    src_mcp = (MCP / "sotn_cmd_mcp.py").read_text()
    i = src_mcp.find("def job_start(")
    body = src_mcp[i:src_mcp.find("\n@mcp.tool()", i)]   # whole function
    check("work_dir" in src_mcp[i:src_mcp.find(")", i)],
          "job_start accepts work_dir")
    check('"work_dir": work_dir' in body,
          "job_start forwards work_dir for the permuter")
    # The permuter tuning must reach the argv too, or -j silently stays at the
    # library default of ONE thread -- which is what every run did until
    # 2026-08-03.
    for k in ("threads", "stop_on_zero", "better_only", "algorithm"):
        check(f'"{k}": {k}' in body, f"job_start forwards {k} to the permuter")
    # The regression: `elif action != "permuter"` left kw empty, so
    # cc.start_job("permuter") raised on the missing positional.
    check('elif action != "permuter"' not in body,
          "the branch that silently dropped permuter's argument is gone")
    for act in ("permuter", "run_automation", "run_analysis", "git_push"):
        check(act in body, f"job_start still handles {act}")
    check('elif action == "git_push"' in body and 'kw = {}' in body,
          "background git_push forwards no caller-controlled arguments")

    print("\nthe generic automation runner states and bounds its real authority")
    check("run_automation" in cc.REGISTRY,
          "run_automation is the canonical registry action")
    _auto_argv = cc.REGISTRY["run_automation"](
        script="readme_status.py", args="--drift")
    _alias_argv = cc.REGISTRY["run_analysis"](
        script="readme_status.py", args="--drift")
    check(_auto_argv == _alias_argv,
          "run_analysis remains an equal-authority compatibility alias")
    _required_mutators = {
        "artifact_store.py", "asm_twin_finder.py", "codebase_index.py",
        "deferred_triage.py", "escalation_triage.py",
        "fix_seed_declarations.py", "orphan_check.py",
        "permuter_promote.py", "permuter_supervisor.py",
        "probe_provider.py", "quality_ab.py", "readme_status.py",
        "transplant.py",
    }
    check(_required_mutators <= set(cc.AUTOMATION_MUTATORS),
          "every known privileged automation writer is inventoried")
    check(set(cc.AUTOMATION_MUTATORS) <= set(cc.AUTOMATION_SCRIPTS),
          "every privileged writer is also explicitly allowlisted")
    try:
        cc.REGISTRY["run_automation"](
            script="quality_audit.py",
            args="--json automation/../../outside.json")
        check(False, "generic automation arguments reject path traversal")
    except cc.Rejected:
        check(True, "generic automation arguments reject path traversal")
    _auto_block = src_mcp[
        src_mcp.find("def run_automation("):
        src_mcp.find("\n@mcp.tool()", src_mcp.find("def run_automation("))]
    _alias_block = src_mcp[
        src_mcp.find("def run_analysis("):
        src_mcp.find("\n@mcp.tool()", src_mcp.find("def run_analysis("))]
    check("NOT A READ-ONLY BOUNDARY" in _auto_block,
          "the canonical MCP description denies read-only authority")
    check("NOT read-only" in _alias_block,
          "the compatibility MCP description denies read-only authority")
    _manifest_text = (
        REPO / "automation" / "mcpb" / "sotn-cmd" / "manifest.json"
    ).read_text(encoding="utf-8")
    check('"name": "run_automation"' in _manifest_text and
          "not a read-only boundary" in _manifest_text,
          "the install manifest exposes the canonical tool and honest alias")

    print("\npermuter jobs run concurrently, builds do not")
    # The permuter takes a work_dir, compiles into it alone, and never touches
    # build/ or runs make -- so N seeds share nothing and serialising them
    # wasted the near pool, which is the most valuable pool the project has.
    # `make build` is the opposite: two of them share one build directory and
    # produce artifacts matching nothing. Both properties are asserted, because
    # relaxing the wrong one is silent corruption.
    cc_src = (MCP / "commands_client.py").read_text()
    i2 = cc_src.find("def start_job(")
    j2 = cc_src.find("\ndef ", i2 + 1)          # end of start_job, not a fixed slice
    sjb = cc_src[i2:j2]
    check('if action == "permuter"' in sjb and "exclusive=False" in sjb,
          "permuter starts with exclusive=False")
    check("slug=" in sjb, "permuter passes a slug so ids stay unique")
    # The fallthrough must still be the plain exclusive call. Asserted by
    # presence of the bare line rather than by where a slice happens to end.
    check("return _jobs.start(action, argv, cwd=str(REPO))\n" in sjb,
          "every other action still uses the exclusive default")
    check(sjb.index('if action == "permuter"')
          < sjb.index("return _jobs.start(action, argv, cwd=str(REPO))\n"),
          "the permuter branch is checked BEFORE the exclusive fallthrough")
    jobs_src = (MCP / "jobs.py").read_text()
    check("exclusive: bool = True" in jobs_src,
          "jobs.start still DEFAULTS to exclusive")
    check("slug: str = \"\"" in jobs_src, "jobs.start accepts a slug")
    check("_paths(job_id)[0].exists()" in jobs_src,
          "job ids are bumped on collision, so two runs cannot share a log")

    print("\npush remains unparameterised and background-safe")
    import inspect
    sig = inspect.signature(cc.REGISTRY["git_push"])
    check(not sig.parameters,
          "git_push takes no arguments, so no caller can choose the remote")
    check("git_push" in cc.LONG_ACTIONS,
          "large pushes can run as observable background jobs")
    _push_argv = cc.REGISTRY["git_push"]()
    check(_push_argv == [cc.PYTHON, "automation/mcp/verified_push.py"],
          "git_push starts the fixed verified-push runner")
    check("_managed_doc_drift_gate()" not in sjb
          and "subprocess.run(" not in sjb,
          "job_start performs no synchronous preflight before returning a job id")
    _verified_push = (MCP / "verified_push.py").read_text(encoding="utf-8")
    check('["git", "status", "--porcelain"]' in _verified_push
          and '[sys.executable, str(README_STATUS), "--drift"]' in _verified_push
          and '["git", "diff", "--check", "HEAD^", "HEAD"]' in _verified_push
          and '["git", "push", "origin", "HEAD"]' in _verified_push,
          "the background runner gates cleanliness, drift, and commit whitespace "
          "before its fixed origin push")
    check("len(sys.argv) != 1" in _verified_push
          and "shell=True" not in _verified_push,
          "the verified-push runner accepts no arguments and invokes no shell")

    print("\nconnector writes are atomic and retry transient drvfs failures")
    real_replace = cc.os.replace
    calls = []
    with tempfile.TemporaryDirectory(
            prefix="connector-write-", dir=REPO / "automation") as td:
        target = Path(td) / "probe.txt"
        rel = target.relative_to(REPO).as_posix()

        def flaky_replace(src, dst):
            calls.append((src, dst))
            if len(calls) == 1:
                raise OSError(errno.EINVAL, "simulated transient drvfs error")
            return real_replace(src, dst)

        with _patch.object(cc.os, "replace", side_effect=flaky_replace):
            written = cc.fs_write(rel, "durable payload")
        check(target.read_text() == "durable payload",
              "a transient EINVAL preserves and eventually writes the payload")
        check(written.get("write_attempts") == 2,
              "the successful response reports the bounded retry")
        check(not list(target.parent.glob(".*.sotn-write-*")),
              "failed temporary write files are cleaned up")

    print("\ncommit synchronizes living documents without sweeping prose")
    _cp = subprocess.CompletedProcess
    with _patch.object(
            cc, "_managed_doc_paths",
            return_value=(["README.md", "ROADMAP.md"], "")), \
            _patch.object(cc.subprocess, "run") as _run:
        _run.return_value = _cp([], 0, "ROADMAP.md\n", "")
        _dirty = cc._sync_managed_docs_for_commit()
        check(not _dirty["ok"] and _run.call_count == 1,
              "unstaged managed prose refuses before generation or staging")
    with _patch.object(
            cc, "_managed_doc_paths",
            return_value=(["README.md", "ROADMAP.md"], "")), \
            _patch.object(cc.subprocess, "run") as _run:
        _run.side_effect = [
            _cp([], 0, "", ""),
            _cp([], 0, "updated 2 managed living documents\n", ""),
            _cp([], 0, "", ""),
            _cp([], 0, "", ""),
        ]
        _clean = cc._sync_managed_docs_for_commit()
        _add_argv = [call.args[0] for call in _run.call_args_list[2:]]
        check(_clean["ok"] and _add_argv == [
            ["git", "add", "--", "README.md"],
            ["git", "add", "--", "ROADMAP.md"],
        ], "generated documents are staged one explicit path at a time")
    print("\nevery git_* capability is on BOTH surfaces")
    # REGISTRY and @mcp.tool() are separate lists. A name in one but not the
    # other is uncallable, and it fails at call time rather than at load time,
    # so it looks like a missing feature rather than a wiring bug.
    import re as _re
    _cc = (MCP / "commands_client.py").read_text()
    _mc = (MCP / "sotn_cmd_mcp.py").read_text()
    _reg = set(_re.findall(r'^\s*"(\w+)":\s*lambda', _cc, _re.M))
    _tools = set(_re.findall(r'@mcp\.tool\(\)\s*\ndef (\w+)', _mc))
    _git_gap = sorted(n for n in _reg if n.startswith("git_")
                      and n not in _tools)
    check(not _git_gap,
          f"no git_* command is stranded in the registry ({_git_gap})")
    # fetch specifically: without it the fork cannot measure drift at all.
    check("git_fetch" in _reg and "git_fetch" in _tools,
          "git_fetch exists and is callable")
    check("_remote(remote)" in _cc and "_REMOTES" in _cc,
          "fetch cannot target an arbitrary remote")
    check("_rev_range(rng)" in _cc and "_RANGE_RX" in _cc,
          "a revision range is validated, not passed through")

    # --- backend names must match the backends they select -----------------
    #
    # "http" used to select LOCAL LLAMA while "zen" selected the HTTP API.
    # The fleet_start help then listed http/cli/mixed and never mentioned zen
    # at all, so an agent reading it started a cli fleet when zen was the
    # agreed configuration. Three separate defects: a supported value missing
    # from its own help, a default pointing at the wrong tier, and a name
    # describing a different backend than the one it picks.
    #
    # These assertions call the real thing in DRYRUN rather than grepping for
    # the words, because the words are also in this comment.
    import importlib
    _cc_mod = importlib.import_module("mcp.commands_client")
    _was = _cc_mod.DRYRUN
    _cc_mod.DRYRUN = True
    try:
        plans = {b: _cc_mod.fleet_start(workers=2, backend=b)
                 for b in ("zen", "llama", "cli", "http")}
        default = _cc_mod.fleet_start(workers=2)
        subset = _cc_mod.fleet_start(
            workers=2, only=("us:ST/RNO4:func_us_801C8C54,"
                             "us:ST/RNO4:LoadFerrymanGateTiles"))
    finally:
        _cc_mod.DRYRUN = _was

    check(default["backend"] == "zen",
          f"fleet_start defaults to zen (got {default['backend']})")
    check(default["reasoning"] == "(worker default: none)",
          f"fleet plan exposes the measured no-reasoning default "
          f"(got {default['reasoning']!r})")
    check(subset["only"] == ["us:ST/RNO4:func_us_801C8C54",
                              "us:ST/RNO4:LoadFerrymanGateTiles"],
          f"fleet plan preserves the exact queue-id subset ({subset['only']!r})")
    _worker = (pathlib.Path(__file__).parent / "win" /
               "worker_direct.py").read_text(encoding="utf-8")
    check('os.environ.get("REASONING_EFFORT", "none")' in _worker,
          "the real Zen worker defaults to no reasoning")
    check('p2.add_argument("--allowlist"' in _worker
          and "allowlist=allowlist" in _worker
          and '_next_args += ["--allowlist"' in _worker,
          "the real fleet worker filters normal todo claims by allowlist")
    check(plans["zen"]["zen_workers"] == 2 and plans["zen"]["llama_workers"] == 0,
          "backend=zen starts zen workers and no llama workers")
    check(plans["llama"]["llama_workers"] == 2 and plans["llama"]["zen_workers"] == 0,
          "backend=llama starts llama workers, so the name matches the thing")
    check(plans["cli"]["cli_workers"] == 2, "backend=cli still starts cli workers")
    check(plans["http"]["backend"] == "zen" and plans["http"]["zen_workers"] == 2,
          "the legacy name http resolves to zen, since zen is the HTTP backend")
    check(plans["http"]["backend"] != "http",
          "and the returned plan reports what actually ran, not the alias")
    bad = None
    try:
        _cc_mod.DRYRUN = True
        _cc_mod.fleet_start(workers=1, backend="nonsense")
    except Exception as e:            # Rejected
        bad = str(e)
    finally:
        _cc_mod.DRYRUN = _was
    check(bad is not None and "llama" in bad and "zen" in bad,
          f"an unknown backend is rejected and the error lists the real names "
          f"({bad!r})")

    # The MCP surface is what an agent reads, so it must name every accepted
    # value. This one IS a text check, because the text is the defect.
    _help = (pathlib.Path(__file__).parent / "mcp" / "sotn_cmd_mcp.py").read_text(
        encoding="utf-8")
    _fs = _help.split("def fleet_start(", 1)[1].split('"""')[1]
    for name in ("zen", "llama", "cli", "mixed"):
        check(f'"{name}"' in _fs,
              f"fleet_start help documents the {name} backend")

    # --- the SHELL wrapper is a third surface ---------------------------------
    #
    # automation/bin/sotn-run maps a command NAME to a backend, and nothing
    # checked that mapping. `runfleet-llama` passed `http`, which fleet_start
    # resolves to `zen` (tested twelve lines up), so the one command named
    # after llama was the one command that could not start llama -- and there
    # was no `runfleet-zen` either, so zen was unreachable by name from the
    # shell entirely. Both defects are invisible to every Python test, because
    # the wrapper is bash.
    _run = (pathlib.Path(__file__).parent / "bin" / "sotn-run").read_text(
        encoding="utf-8")
    # Collect the arms by pattern over the WHOLE file rather than by slicing
    # to the first `esac`: the run-permuter arm contains a nested
    # `case "$VERB" in ... esac`, so slicing stops before the fleet arms are
    # reached. The first version of this did exactly that, found nothing, and
    # reported "no dispatch line" three times while the sibling check
    # `"http" not in _disp` passed on the same empty slice -- a vacuous pass
    # sitting next to the failures that explained it.
    _arms = dict(re.findall(r"^\s*(runfleet[\w-]*)\)\s*fleet\s+(\w+)",
                            _run, re.M))
    check(len(_arms) == 3,
          f"found the fleet dispatch arms ({sorted(_arms)})")
    for cmd, backend in (("runfleet", "zen"),
                         ("runfleet-cli", "cli"),
                         ("runfleet-llama", "llama")):
        check(_arms.get(cmd) == backend,
              f"{cmd} launches the {backend} backend "
              f"(got {_arms.get(cmd)!r})")
    check("http" not in _arms.values(),
          "and no wrapper routes through the http alias, which resolves to "
          "zen and so hides which backend actually starts")
    _installed = _run.split("COMMANDS=(", 1)[1].split(")", 1)[0].split()
    for cmd in ("runfleet", "runfleet-cli", "runfleet-llama"):
        check(cmd in _installed,
              f"{cmd} is in COMMANDS, so installation puts it on PATH")

    # --- two permuter jobs must not share one work dir ----------------------
    #
    # TASK #87, "phantom permuter candidates": the dashboard showed duplicate
    # func_us_801B8E80 and func_us_8019AA04-2 rows with DIFFERENT iteration
    # counts. Neither the rows nor the work dirs were phantoms -- func_us_
    # 8019AA04-2 is a real directory, and the panel faithfully rendered two
    # real jobs. The defect was upstream: permuter passes exclusive=False so
    # that separate work dirs can search concurrently, and that read as no
    # exclusion at all, so two jobs could be started on the SAME dir. They then
    # interleave output-<score>-<n>/ writes and race each other's promotions.
    # permuter_supervisor guarded this with already_busy(); the dashboard
    # button and job_start() did not.
    import importlib.util as _ilu2
    _js = _ilu2.spec_from_file_location("jobs_t", MCP / "jobs.py")
    _jobs_t = _ilu2.module_from_spec(_js)
    _js.loader.exec_module(_jobs_t)

    print("\none parser for the slug in a job id")
    # Two copies existed and they disagreed: the dashboard's kept the `~<n>`
    # collision bump inside the name, so a bumped job rendered as a work dir
    # that does not exist and its all-time best silently read as None.
    check(_jobs_t.slug_of("permuter-143902-55599-func_us_8019AA04-2")
          == "func_us_8019AA04-2",
          "a slug containing a hyphen survives intact")
    check(_jobs_t.slug_of("permuter-143902-55599-func_us_801B8E80~1")
          == "func_us_801B8E80",
          "and the ~n collision bump is stripped, not left in the name")
    check(_jobs_t.slug_of("make_build-110820-9159") == "",
          "a job with no slug reports none rather than a pid fragment")
    _dash = (pathlib.Path(__file__).parent / "dashboard.py").read_text(
        encoding="utf-8")
    # CODE ONLY. The comment recording why the old parse was wrong quotes it
    # verbatim, so searching the raw file finds the string it is asserting is
    # gone and the check fails on its own documentation. Exactly the trap that
    # made `extern int declaration();` out of a sentence about C89.
    _dash_code = "\n".join(l for l in _dash.splitlines()
                           if not l.lstrip().startswith("#"))
    check("jobs.slug_of(jid)" in _dash_code,
          "the dashboard calls the shared parser")
    check('jid.split("-", 3)' not in _dash_code,
          "and no longer carries its own copy")

    print("\nand a second job on the same work dir is refused")
    _real_running = _jobs_t.running_jobs
    try:
        _jobs_t.running_jobs = lambda a=None: [
            "permuter-143902-55599-func_us_801B8E80"]
        r = _jobs_t.start("permuter", ["true"], cwd=str(_cc_mod.REPO),
                          exclusive=False, slug="func_us_801B8E80")
        check(r.get("started") is False
              and r.get("reason") == "slug_already_running",
              f"refused, with the reason ({r.get('reason')})")
        check("work dir" in (r.get("hint") or ""),
              "and the hint says why two on one dir is wrong")
        # The whole point of exclusive=False survives: a DIFFERENT seed still
        # starts, which is what makes parallel searching possible.
        r2 = _jobs_t.start("permuter", ["true"], cwd=str(_cc_mod.REPO),
                           exclusive=False, slug="func_us_801C4B2C")
        check(r2.get("started") is True,
              f"while a different work dir still starts ({r2.get('reason')})")
        if r2.get("job_id"):
            _jobs_t.cancel(r2["job_id"])
    finally:
        _jobs_t.running_jobs = _real_running

    # --- teardown must restore source itself ---------------------------------
    #
    # Each worker's SIGTERM handler calls replay_pending_journals, but it runs
    # inside the process being killed and takes BuildLock first. During a
    # fleet stop the lock's owner is also being killed, so the handler can
    # block and the `kill -9` lands before it restores anything. On
    # 2026-08-09 that left src/st/rchi/e_gaibon.c holding a candidate, with
    # its journal still on disk, after a stop that reported success.
    #
    # Driven end to end against a REAL journal and a REAL file, because the
    # bug was that a code path nobody exercised did not run.
    import json as _j, time as _t
    # A THROWAWAY FILE, never a real source file. The first version of this
    # test dirtied src/st/rchi/e_gaibon.c and restored it in `finally`. That
    # is one interrupted run away from leaving a candidate in the tree, which
    # is the exact failure being tested for. logs/ is gitignored, and replay
    # resolves any repo-relative src_rel, so nothing tracked is ever touched.
    _victim = _cc_mod.REPO / "automation" / "logs" / "selftest-victim.c"
    _pend = _cc_mod.REPO / "automation" / "logs" / "pending"
    _jf = _pend / "selftest-dead-worker.json"
    _orig = "// self-test fixture, not a real source file\nvoid f(void) {}\n"
    _was = _cc_mod.DRYRUN
    _models_path = (_cc_mod.REPO / "automation" / "opencode" /
                    "opencode.json")
    _models_before = _models_path.read_bytes()
    _real_refresh_models = _cc_mod.refresh_zen_models
    try:
        _pend.mkdir(parents=True, exist_ok=True)
        # A successful transaction now deliberately retains an empty committed
        # journal until the next replay. That makes the rename which disarms a
        # transaction durable without depending on a second unlink. Such a
        # record is harmless and fleet_stop consumes it before replaying the
        # fixture below; only an actionable leftover violates the precondition.
        _stray = sorted(p.name for p in _pend.glob("*.json"))
        _actionable = []
        for _name in _stray:
            try:
                _record = _j.loads((_pend / _name).read_text(encoding="utf-8"))
                if _record.get("files") or _record.get("state") != "committed":
                    _actionable.append(_name)
            except (OSError, ValueError):
                _actionable.append(_name)
        check(not _actionable,
              f"the pending dir contains no actionable journal before this "
              f"test writes one; empty committed records are expected "
              f"({_actionable})")
        _victim.write_text(_orig, encoding="utf-8")
        _jf.write_text(_j.dumps({
            "src_rel": "automation/logs/selftest-victim.c",
            "original": _orig, "worker": "selftest-dead-worker",
            "pid": 999997,            # a pid that is not alive
            "at": _t.time()}), encoding="utf-8")
        _victim.write_text(_orig + "// STRANDED BY A KILLED WORKER\n",
                           encoding="utf-8")
        _cc_mod.DRYRUN = False
        # fleet_stop refreshes the live Zen catalogue into a tracked config.
        # That production side effect does not belong in a self-test, whose
        # contract is to leave every tracked byte unchanged.
        _cc_mod.refresh_zen_models = lambda: {
            "ok": True, "changed": False, "self_test": True}
        _r = _cc_mod.fleet_stop(hold=True)
        check(_r.get("restored_files") == 1,
              f"fleet_stop restores source left by a dead worker "
              f"(restored_files={_r.get('restored_files')})")
        check(_victim.read_text(encoding="utf-8") == _orig,
              "and restores it byte-for-byte, not approximately")
        check(not _jf.exists(), "and consumes the journal so it cannot be "
                                "replayed over a later edit")
        check("restored 1 source file" in (_r.get("note") or ""),
              "and says so in the note, because a silent restore is "
              "indistinguishable from no restore")
        check("replay_unaccounted" not in _r,
              f"and the count agrees with the directory "
              f"({_r.get('replay_unaccounted', '')[:120]})")
        # P2 (#108). Stopping the fleet is the moment the risk window opens:
        # work has finished and any match still only in the working tree is
        # one `git restore` from becoming a false record. Five verified
        # matches were lost exactly that way, and matched_audit could have
        # named every one of them at any point -- nothing ever asked it to.
        check("matched_audit" in _r,
              f"fleet_stop reports the matched-vs-committed audit "
              f"({_r.get('matched_audit', 'MISSING')})")
        check(str(_r.get("matched_audit", "")).startswith("SUMMARY ")
              or _r.get("matched_audit") == "could not run",
              f"and it is the summary line, not raw output "
              f"({str(_r.get('matched_audit'))[:80]})")
    finally:
        _cc_mod.DRYRUN = _was
        _cc_mod.refresh_zen_models = _real_refresh_models
        _victim.unlink(missing_ok=True)
        _jf.unlink(missing_ok=True)
    check(_models_path.read_bytes() == _models_before,
          "and the self-test does not rewrite the tracked model catalogue")

    print("\na count of zero against a non-empty pending dir is not silent")
    # The guard that makes the next occurrence self-diagnosing. Drive it by
    # leaving a journal owned by a LIVE pid, which replay must skip: pending
    # is non-empty on entry and the restore count is legitimately 0.
    _jf2 = _pend / "selftest-live-owner.json"
    _was2 = _cc_mod.DRYRUN
    _real_refresh_models2 = _cc_mod.refresh_zen_models
    try:
        _victim.write_text(_orig, encoding="utf-8")
        _jf2.write_text(_j.dumps({
            "src_rel": "automation/logs/selftest-victim.c",
            "original": _orig, "worker": "selftest-live-owner",
            "pid": __import__("os").getpid(),   # alive by construction
            "at": _t.time()}), encoding="utf-8")
        _cc_mod.DRYRUN = False
        _cc_mod.refresh_zen_models = lambda: {
            "ok": True, "changed": False, "self_test": True}
        _r2 = _cc_mod.fleet_stop(hold=True)
        check(_r2.get("restored_files") == 0,
              f"a live owner's journal is left alone "
              f"({_r2.get('restored_files')})")
        check("replay_unaccounted" in _r2,
              "and the zero is explained rather than reported bare")
        check("pending on entry" in (_r2.get("replay_unaccounted") or ""),
              "naming how many journals were there")
        check("JOURNAL REPLAY FAILED" not in (_r2.get("note") or ""),
              "without crying failure: the tree is fine, and a false alarm "
              "here is how a real replay_error stops being believed")
    finally:
        _cc_mod.DRYRUN = _was2
        _cc_mod.refresh_zen_models = _real_refresh_models2
        _jf2.unlink(missing_ok=True)
        _victim.unlink(missing_ok=True)
    check(_models_path.read_bytes() == _models_before,
          "and the second fleet-stop fixture also preserves that config")

    # --- path containment is a PARENT check, not a prefix check -------------
    #
    # `_inrepo` guards the paths handed to git. It used to test
    # str(resolved).startswith(str(REPO)), so with REPO=/repo the sibling
    # /repo-evil passed: "/repo-evil/x".startswith("/repo") is True. The
    # correct parent-based test already existed in `_resolve` in the same
    # file; the two had drifted. Reported by an external audit 2026-08-09 and
    # confirmed against the code before fixing.
    # --- mcpb: the connector can rebuild its own bundles ---------------------
    #
    # Packing a bundle used to require a human at a shell. That gap cost three
    # failed reinstalls of the ChatGPT share reader: the source was edited, the
    # stale .mcpb beside it was not rebuilt, and each reinstall restored the
    # old code. A capability that can be built should not be a manual step.
    print("\nmcpb bundles can be validated and packed through the connector")
    for _n in ("mcpb_validate", "mcpb_pack", "mcpb_info"):
        check(_n in _cc_mod.REGISTRY, f"{_n} is in REGISTRY")
        check(_n in decorated_tools(), f"{_n} is callable (@mcp.tool)")

    # ARGUMENT ERRORS BEAT ENVIRONMENT ERRORS. The natural
    # [resolve_mcpb(), sub, check(path)] evaluates left to right, so a bad
    # directory reports "mcpb CLI not found" on a machine without mcpb and the
    # real problem on a machine with it -- the error would depend on unrelated
    # state. These assertions hold either way, which is the point.
    for _bad, _want in (("automation", "no manifest.json"),
                        ("src", "no manifest.json"),
                        ("../evil", "inside the repo"),
                        ("automation/mcpb/nope", "does not exist")):
        _err = ""
        try:
            _cc_mod.build_argv("mcpb_pack", directory=_bad)
        except Exception as e:                              # Rejected
            _err = str(e)
        check(_want in _err and "mcpb CLI" not in _err,
              f"{_bad!r} is refused for the RIGHT reason ({_err[:52]!r})")

    # A real bundle dir must clear the argument checks. It may still fail on a
    # missing binary, and that is a correct, different failure.
    _real = ""
    try:
        _cc_mod.build_argv("mcpb_pack", directory="automation/mcpb/sotn-cmd")
    except Exception as e:                                  # noqa: BLE001
        _real = str(e)
    check(_real == "" or "mcpb CLI" in _real,
          f"a real bundle dir passes validation and only the binary can stop "
          f"it ({_real[:52]!r})")
    check((_cc_mod.REPO / "automation/mcpb/sotn-cmd/manifest.json").is_file(),
          "and that bundle dir really does hold a manifest, so the check above "
          "is not passing vacuously")

    # An extensionless launcher in a WINDOWS npm dir is npm's Unix shell
    # wrapper. From WSL it matches first and then execs `node`, which this
    # distro does not have -- the real first call failed exactly that way:
    #   /mnt/c/.../npm/mcpb: exec: node: not found
    # The .cmd works, via interop. But a NATIVE Linux install is extensionless
    # too and must still win, so the rule is about /mnt, not about extensions.
    print("\nmcpb resolution survives the WSL PATHEXT trap")
    import shutil as _sh
    _real_which, _saved = _sh.which, _cc_mod._MCPB_RESOLVED
    _win = "/mnt/c/Users/k/AppData/Roaming/npm/"
    for _label, _table, _want in (
            ("the unix wrapper alone is refused, with the reason",
             {"mcpb": _win + "mcpb"}, None),
            ("the .cmd is preferred over the unix wrapper",
             {"mcpb": _win + "mcpb", "mcpb.cmd": _win + "mcpb.cmd"},
             _win + "mcpb.cmd"),
            ("a native linux install still wins",
             {"mcpb": "/usr/local/bin/mcpb", "mcpb.cmd": _win + "mcpb.cmd"},
             "/usr/local/bin/mcpb")):
        _cc_mod._MCPB_RESOLVED = None
        _sh.which = lambda n, _t=_table: _t.get(n)
        try:
            _got, _err = _cc_mod.resolve_mcpb(), ""
        except Exception as e:                              # Rejected
            _got, _err = "", str(e)
        if _want:
            check(_got == _want, f"{_label} ({_got or _err[:40]!r})")
        else:
            check(not _got and "node" in _err,
                  f"{_label} ({_err[:60]!r})")
    _sh.which, _cc_mod._MCPB_RESOLVED = _real_which, _saved

    # A .cmd is a batch script, not an executable. WSL's binfmt runs .exe
    # directly but cannot exec a .cmd, and Python reports the unhelpful
    #   [Errno 8] Exec format error: .../npm/mcpb.cmd
    # It has to go through cmd.exe, and every path argument has to become a
    # Windows path because cmd.exe cannot see /mnt.
    print("\na Windows batch launcher is invoked through cmd.exe")
    check(_cc_mod._win_path("/mnt/c/a/b") == "C:\\a\\b",
          "a /mnt path becomes a drive path with backslashes")
    check(_cc_mod._win_path("/usr/local/bin/mcpb") == "/usr/local/bin/mcpb",
          "and a native Linux path is left alone")
    _wrapped = _cc_mod._mcpb_launch("/mnt/c/npm/mcpb.cmd",
                                    ["validate", "/mnt/c/repo/b"])
    check(_wrapped[1:2] == ["/c"] and _wrapped[0].endswith("cmd.exe"),
          f"a .cmd is wrapped in cmd.exe /c ({_wrapped[:2]})")
    check(all("/mnt/" not in a for a in _wrapped[2:]),
          f"and no /mnt path survives into the arguments ({_wrapped[2:]})")
    _native = _cc_mod._mcpb_launch("/usr/local/bin/mcpb", ["validate", "/mnt/x"])
    check(_native == ["/usr/local/bin/mcpb", "validate", "/mnt/x"],
          "a native binary is run directly, paths untouched")

    # `mcpb pack` writes to the CURRENT DIRECTORY, and this runs with
    # cwd=REPO. The first real pack therefore dropped sotn-cmd.mcpb in the
    # repo root, next to the Makefile, nowhere near the bundle and not where
    # the installed one lives. An explicit output is always passed now.
    print("\npack writes beside the bundle, not into the repo root")
    check(_cc_mod._mcpb_default_out("automation/mcpb/sotn-cmd")
          == "automation/mcpb/sotn-cmd.mcpb",
          "the default output sits beside the bundle directory")
    check(_cc_mod._mcpb_default_out("automation/mcpb/sotn-cmd/")
          == "automation/mcpb/sotn-cmd.mcpb",
          "a trailing slash does not produce a doubled name")
    _packargv = _cc_mod.build_argv("mcpb_pack",
                                   directory="automation/mcpb/sotn-cmd")
    check(_packargv[-1].lower().endswith("sotn-cmd.mcpb"),
          f"so pack always names its output explicitly ({_packargv[-1]!r})")
    check("mcpb" in _packargv[-1].replace("\\", "/").lower().rsplit("/", 2)[-2],
          "and that output is inside automation/mcpb, not the repo root")

    print("\nin-repo path containment cannot be defeated by a name prefix")
    _root = _cc_mod.REPO.resolve()
    _evil = f"../{_root.name}-evil/x"
    _rejected = None
    try:
        _cc_mod._inrepo(_evil, must_exist=False)
    except Exception as e:                                  # Rejected
        _rejected = str(e)
    check(_rejected is not None,
          f"a sibling dir whose name merely EXTENDS the repo name is refused "
          f"({_evil})")
    _abs = None
    try:
        _cc_mod._inrepo("/etc/passwd", must_exist=False)
    except Exception as e:                                  # Rejected
        _abs = str(e)
    check(_abs is not None,
          "an absolute path outside the repo is refused, even though "
          "pathlib's `/` lets it replace the base entirely")
    _dotgit = None
    try:
        _cc_mod._inrepo(".git/config", must_exist=False)
    except Exception as e:                                  # Rejected
        _dotgit = str(e)
    check(_dotgit is not None,
          "and .git is refused: this layer has no business handing git a path "
          "inside its own object store")
    _ok = None
    try:
        _ok = _cc_mod._inrepo("automation", must_be_dir=True)
    except Exception as e:                                  # noqa: BLE001
        _ok = None
        check(False, f"a genuine in-repo path still works ({e})")
    if _ok:
        check(_ok.endswith("automation"),
              "a genuine in-repo path still resolves normally")

    print("\nsearch alternation actually alternates")
    # `grep -e` is BRE, where `|` and `()` are literal characters, so `a|b`
    # searched for the three-character string "a|b" and returned nothing while
    # ripgrep, if installed, treated it as alternation. Silent false
    # negatives: "0 matches" reads as "does not exist". Four wrong conclusions
    # in one session on 2026-08-10, one of them in a commit message.
    _one = _cc_mod.fs_search("PAL_ARMOR_LORD_UNK", "src/st")
    _two = _cc_mod.fs_search("E_ARMOR_LORD_UNK2", "src/st")
    _alt = _cc_mod.fs_search("PAL_ARMOR_LORD_UNK|E_ARMOR_LORD_UNK2", "src/st")
    if _one["count"] > 0 and _two["count"] > 0:
        check(_alt["count"] >= max(_one["count"], _two["count"]),
              f"alternation finds at least as much as either branch "
              f"({_one['count']} | {_two['count']} -> {_alt['count']})")
        check(_alt["count"] > 0,
              "and is not the silent zero that started this")
    else:
        print(f"  skip  the probe symbols are gone from the tree "
              f"({_one['count']}, {_two['count']})")

    _grp = _cc_mod.fs_search("(EInit|Entity) g_EInit", "src/st")
    check(_grp["count"] > 0,
          f"a parenthesised group is a group, not literal parens "
          f"({_grp['count']})")

    print("\nand a broken pattern is an error, not a confident zero")
    _bad = _cc_mod.fs_search("[unterminated", "src/st")
    check(_bad["count"] == -1 and "error" in _bad,
          f"a bad regex reports an error rather than 0 matches ({_bad})")

    print("\ndiscarding ORPHANED src/ work is refused, not silently done")
    # The near-miss this guards: src/boss/bo6/richter.c and us_39144.c sat
    # modified with three matching function bodies and no crash journal. A
    # single git_restore would have destroyed all three; nothing objected.
    import json as _json
    import subprocess as _sp
    _repo = _cc_mod.REPO
    _victim_rel = "src/_orphan_guard_probe.c"
    _victim = _repo / _victim_rel
    _pending = _repo / "automation" / "logs" / "pending"
    _jf = _pending / "_orphan_guard_probe.json"
    _had = _victim.exists()
    try:
        # A file git reports as modified/untracked under src/, with no journal.
        _victim.write_text("/* probe */\n", encoding="utf-8")
        _sp.run(["git", "add", "-N", "--", _victim_rel], cwd=str(_repo),
                capture_output=True, text=True, timeout=60)
        _blocked = None
        try:
            _cc_mod._restorable(_victim_rel)
        except Exception as e:                                  # Rejected
            _blocked = str(e)
        check(_blocked is not None,
              "an orphaned, modified src/ file is refused")
        if _blocked:
            check("orphan_check" in _blocked,
                  "and the refusal names the tool that answers the question")
            check("confirm_orphan" in _blocked,
                  "and says how to override deliberately")

        check(_cc_mod._restorable(_victim_rel, True).endswith(
            "_orphan_guard_probe.c"),
            "confirm_orphan=True lets it through: a speed bump, not a veto")

        # A journal's original can itself be valuable uncommitted work. Raw
        # checkout would ignore that baseline, so only journal replay is safe.
        _pending.mkdir(parents=True, exist_ok=True)
        _journal_original = "/* complete pre-apply uncommitted baseline */\n" + (
            "preserve-me\n" * 200)
        _jf.write_text(_json.dumps({"src_rel": _victim_rel,
                                    "original": _journal_original}),
                       encoding="utf-8")
        _journal_blocked = None
        try:
            _cc_mod._restorable(_victim_rel)
        except Exception as e:                                  # Rejected
            _journal_blocked = str(e)
        check(_journal_blocked is not None,
              "raw restore refuses a journal-covered source file")
        if _journal_blocked:
            check("fleet_stop" in _journal_blocked,
                  "the refusal directs recovery through journal replay")
        _journal_after = _json.loads(_jf.read_text(encoding="utf-8"))
        check(_journal_after.get("original") == _journal_original,
              "the complete pre-apply baseline remains available for replay")
        check(_cc_mod._restorable(_victim_rel, True).endswith(
            "_orphan_guard_probe.c"),
            "the explicit destructive override still permits raw restore")
    finally:
        _jf.unlink(missing_ok=True)
        _sp.run(["git", "rm", "--cached", "-q", "--", _victim_rel],
                cwd=str(_repo), capture_output=True, text=True, timeout=60)
        if not _had:
            _victim.unlink(missing_ok=True)

    # Files outside src/ are disposable; automation/ churns constantly.
    _auto = None
    try:
        _auto = _cc_mod._restorable("automation/dashboard.py")
    except Exception as e:                                      # noqa: BLE001
        check(False, f"a non-src path must never be blocked ({e})")
    check(bool(_auto), "a path outside src/ is never blocked")

    print("\nboth destructive git entry points carry the guard")
    _src_cc = pathlib.Path(_cc_mod.__file__).read_text(errors="ignore")
    for _name in ("git_restore", "git_restore_from_head"):
        _seg = _src_cc.split(f'"{_name}": lambda')[1].split("),\n")[0]
        check("_restorable(" in _seg,
              f"{_name} routes its path through _restorable")
        check("_inrepo(" not in _seg,
              f"and {_name} no longer bypasses it with a bare _inrepo")

    # ------------------------------------------------------------------
    # ADOPTING A FILE FROM ANOTHER REF (git_checkout_path).
    #
    # The mirror of the orphan guard, and its failure mode is worse. A restore
    # brings back HEAD, so the thing it overwrites is at least comparable to
    # something in history. An adoption writes UPSTREAM's version of the file,
    # and if the destination held an uncommitted edit there is no ref anywhere
    # that holds what was there -- git_restore_from_head cannot undo it.
    print("\nadopting a file from another ref is guarded, in the other "
          "direction")
    check("git_checkout_path" in _reg,
          "git_checkout_path is in REGISTRY")
    check("git_checkout_path" in _tools,
          "git_checkout_path is callable (@mcp.tool)")
    _seg_cp = _src_cc.split('"git_checkout_path": lambda')[1].split("),\n")[0]
    check("_adoptable(" in _seg_cp,
          "git_checkout_path routes its path through _adoptable")
    check("_ref(ref)" in _seg_cp,
          "and its ref is validated, not passed through")

    # A path that does not exist yet is the ordinary harvest case: adopting a
    # new shared header. It must not need a flag.
    _fresh = None
    try:
        _fresh = _cc_mod._adoptable("src/_adopt_probe_does_not_exist.h")
    except Exception as e:                                      # noqa: BLE001
        check(False, f"a nonexistent destination must not be blocked ({e})")
    check(bool(_fresh),
          "a destination that does not exist yet is allowed without ceremony")

    # A clean tracked file is recoverable from HEAD, so it is allowed too.
    #
    # DISCOVERED, not named. This was automation/dashboard.py, which made the
    # check depend on nobody having edited the dashboard: on 2026-08-17 a
    # one-line dashboard change turned this into a reported guard defect that
    # did not exist. Any test whose subject is "a CLEAN file" has to go and find
    # one rather than assume a particular file is clean.
    _clean, _clean_dest = None, None
    for _cand in sorted((_repo / "automation").glob("*.py")):
        _rel = _cand.relative_to(_repo).as_posix()
        if _cc_mod._is_tracked(_rel) and not _cc_mod._is_dirty(_rel):
            _clean_dest = _rel
            break
    check(_clean_dest is not None,
          f"found a clean tracked destination to test with ({_clean_dest})")
    if _clean_dest:
        try:
            _clean = _cc_mod._adoptable(_clean_dest)
        except Exception as e:                                  # noqa: BLE001
            _clean = None
            check(False, f"a clean destination must not be blocked ({e})")
    check(bool(_clean),
          "a clean destination is allowed: HEAD still holds what it replaces")

    _av_rel = "src/_adopt_guard_probe.c"
    _av = _repo / _av_rel
    _av_had = _av.exists()
    try:
        _av.write_text("/* uncommitted work */\n", encoding="utf-8")
        _sp.run(["git", "add", "-N", "--", _av_rel], cwd=str(_repo),
                capture_output=True, text=True, timeout=60)
        _ablocked = None
        try:
            _cc_mod._adoptable(_av_rel)
        except Exception as e:                                  # Rejected
            _ablocked = str(e)
        check(_ablocked is not None,
              "a DIRTY destination is refused")
        if _ablocked:
            check("confirm_overwrite" in _ablocked,
                  "and says how to override deliberately")
            check("git_restore_from_head" in _ablocked,
                  "and names why this is worse than a restore: nothing here "
                  "would hold what is replaced")
        check(_cc_mod._adoptable(_av_rel, True).endswith(
            "_adopt_guard_probe.c"),
            "confirm_overwrite=True lets it through: a speed bump, not a veto")

        # NOT limited to src/. A hand-edited splat config is exactly as
        # unrecoverable as a hand-edited source file, and the harvest overwrites
        # config/ and include/ too.
        _cfg_rel = "config/_adopt_guard_probe.yaml"
        _cfgp = _repo / _cfg_rel
        try:
            _cfgp.write_text("probe: 1\n", encoding="utf-8")
            _sp.run(["git", "add", "-N", "--", _cfg_rel], cwd=str(_repo),
                    capture_output=True, text=True, timeout=60)
            _cblocked = None
            try:
                _cc_mod._adoptable(_cfg_rel)
            except Exception as e:                              # Rejected
                _cblocked = str(e)
            check(_cblocked is not None,
                  "a dirty destination OUTSIDE src/ is refused too, unlike "
                  "_restorable")
        finally:
            _sp.run(["git", "rm", "--cached", "-q", "--", _cfg_rel],
                    cwd=str(_repo), capture_output=True, text=True, timeout=60)
            _cfgp.unlink(missing_ok=True)
    finally:
        _sp.run(["git", "rm", "--cached", "-q", "--", _av_rel],
                cwd=str(_repo), capture_output=True, text=True, timeout=60)
        if not _av_had:
            _av.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # THE PERMUTER'S FAST LOOP. --debug scores base.c and exits, which is the
    # only way to test a codegen hypothesis without an exclusive minutes-long
    # build. It must not be mixed with the search flags: -j, --stop-on-zero and
    # --better-only all describe a search that --debug does not run.
    print("\nthe permuter can score one candidate without searching")
    _dbg = _cc_mod.build_argv("permuter", work_dir="automation", debug=True)
    check("--debug" in _dbg, "debug=True passes --debug")
    for _flag in ("-j", "--stop-on-zero", "--better-only"):
        check(_flag not in _dbg,
              f"and drops {_flag}, which only means something to a search")
    _srch = _cc_mod.build_argv("permuter", work_dir="automation", threads=6)
    check("--debug" not in _srch, "debug defaults off, so search is unchanged")
    check("-j" in _srch and "6" in _srch,
          "and the search still gets its thread count")
    check("--stop-on-zero" in _srch,
          "and still stops on zero, so a win is not searched past")
    # The help is read textually for the same reason the surface lists are:
    # importing sotn_cmd_mcp constructs a live FastMCP server.
    _pm_doc = src_mcp.split("def permuter(")[1].split('"""')[1]
    check("debug=True" in _pm_doc,
          "permuter's help documents the debug mode")
    check("verify_build" in _pm_doc,
          "and says a zero here is not a match, which is the whole caveat")
    check("debug: bool" in src_mcp.split("def permuter(")[1].split(")")[0],
          "and the @mcp.tool signature actually accepts it, so the help is "
          "not describing an argument no caller can pass")

    # Upstream debug mode writes ./debug_source.c and
    # ./debug_compiled_object.o with unconditional replacement. The connector
    # must give each run an owned directory under its work dir, or running the
    # fast loop can silently replace unrelated untracked evidence at repo root.
    print("\npermuter debug output is unique and owned by its work directory")
    _saved_subprocess_run = _cc_mod.subprocess.run
    _saved_cc_dryrun = _cc_mod.DRYRUN
    _saved_cc_repo = _cc_mod.REPO
    _saved_cc_python = _cc_mod.PYTHON
    _captured_debug_runs = []
    _fake_debug_mode = {"value": "success"}

    def _fake_debug_run(argv, **kwargs):
        _cwd = Path(kwargs["cwd"])
        _captured_debug_runs.append({"argv": argv, "cwd": str(_cwd)})
        (_cwd / "debug_source.c").write_text("new source", encoding="utf-8")
        if _fake_debug_mode["value"] == "timeout":
            raise _cc_mod.subprocess.TimeoutExpired(argv, 1)
        (_cwd / "debug_compiled_object.o").write_bytes(b"new object")
        _rc = 7 if _fake_debug_mode["value"] == "nonzero" else 0
        return _cc_mod.subprocess.CompletedProcess(argv, _rc, "", "")

    try:
        with tempfile.TemporaryDirectory(dir=REPO / "automation") as _td:
            _fake_repo = Path(_td)
            _work_dir = _fake_repo / "seed"
            _work_dir.mkdir()
            _script = _fake_repo / "tools" / "decomp-permuter" / "permuter.py"
            _script.parent.mkdir(parents=True)
            _script.touch()
            _root_source = _fake_repo / "debug_source.c"
            _root_object = _fake_repo / "debug_compiled_object.o"
            _root_source.write_text("old source", encoding="utf-8")
            _root_object.write_bytes(b"old object")

            _cc_mod.REPO = _fake_repo
            _cc_mod.PYTHON = ".venv/bin/python"
            _cc_mod.subprocess.run = _fake_debug_run

            _cc_mod.DRYRUN = True
            _dry_plan = _cc_mod.run(
                "permuter", work_dir=str(_work_dir), debug=True, timeout=1)
            check(_dry_plan.get("dry_run") is True
                  and not (_work_dir / "debug-runs").exists(),
                  "dry-run previews without creating an output directory")

            _cc_mod.DRYRUN = False
            _debug_result_1 = _cc_mod.run(
                "permuter", work_dir=str(_work_dir), debug=True, timeout=1)
            _debug_result_2 = _cc_mod.run(
                "permuter", work_dir=str(_work_dir), debug=True, timeout=1)
            _debug_cwd_1 = Path(_captured_debug_runs[0].get("cwd", REPO))
            _debug_cwd_2 = Path(_captured_debug_runs[1].get("cwd", REPO))
            check(_debug_cwd_1 != REPO and _work_dir in _debug_cwd_1.parents,
                  "debug files cannot land at repo root or outside the seed")
            check(_debug_cwd_1.is_dir() and _debug_cwd_2.is_dir(),
                  "the connector creates the owned debug output directory")
            check(_debug_cwd_1 != _debug_cwd_2,
                  "repeated debug runs never replace one another")
            check((_debug_cwd_1 / "debug_source.c").read_text() == "new source"
                  and (_debug_cwd_1 / "debug_compiled_object.o").read_bytes()
                  == b"new object",
                  "upstream's fixed debug filenames land in the owned directory")
            check(_root_source.read_text() == "old source"
                  and _root_object.read_bytes() == b"old object",
                  "pre-existing root debug evidence remains byte-identical")
            _debug_python = Path(_captured_debug_runs[0]["argv"][0])
            _debug_script = Path(
                _captured_debug_runs[0].get("argv", ["", ""])[1])
            check(_debug_python == (_fake_repo / ".venv/bin/python").resolve(),
                  "a relative SOTN_PYTHON remains relative to the repo")
            check(_debug_script == _script.resolve(),
                  "permuter.py remains resolvable from the owned directory")
            check(_debug_result_1.get("debug_output_dir") == str(_debug_cwd_1)
                  and _debug_result_2.get("debug_output_dir") == str(_debug_cwd_2),
                  "the caller is told where the preserved debug artifacts live")

            _fake_debug_mode["value"] = "nonzero"
            _nonzero = _cc_mod.run(
                "permuter", work_dir=str(_work_dir), debug=True, timeout=1)
            check(_nonzero.get("returncode") == 7
                  and Path(_nonzero["debug_output_dir"]).is_dir(),
                  "nonzero compiles still preserve and report their artifacts")

            _fake_debug_mode["value"] = "timeout"
            _timed_out = _cc_mod.run(
                "permuter", work_dir=str(_work_dir), debug=True, timeout=1)
            _timeout_dir = Path(_timed_out["debug_output_dir"])
            check(_timed_out.get("timed_out") is True
                  and (_timeout_dir / "debug_source.c").is_file(),
                  "timeouts report the directory holding partial artifacts")

            _fake_debug_mode["value"] = "success"
            with ThreadPoolExecutor(max_workers=2) as _pool:
                _parallel = list(_pool.map(
                    lambda _: _cc_mod.run(
                        "permuter", work_dir=str(_work_dir), debug=True,
                        timeout=1),
                    range(2)))
            _parallel_dirs = {r["debug_output_dir"] for r in _parallel}
            check(len(_parallel_dirs) == 2,
                  "concurrent debug calls receive distinct output directories")

            _escape_work = _fake_repo / "escape-seed"
            _escape_work.mkdir()
            _outside_seed = _fake_repo / "outside-seed"
            _outside_seed.mkdir()
            try:
                (_escape_work / "debug-runs").symlink_to(
                    _outside_seed, target_is_directory=True)
            except OSError:
                _source = (MCP / "commands_client.py").read_text()
                check("debug_root.resolve(" in _source and
                      "resolved_debug_root.relative_to(work_dir)" in _source,
                      "source validates debug-root containment when symlinks "
                      "are unavailable")
            else:
                try:
                    _cc_mod.run(
                        "permuter", work_dir=str(_escape_work), debug=True,
                        timeout=1)
                    check(False,
                          "a debug-runs symlink outside its seed is refused")
                except _cc_mod.Rejected:
                    check(True,
                          "a debug-runs symlink outside its seed is refused")
    finally:
        _cc_mod.subprocess.run = _saved_subprocess_run
        _cc_mod.DRYRUN = _saved_cc_dryrun
        _cc_mod.REPO = _saved_cc_repo
        _cc_mod.PYTHON = _saved_cc_python

    # ------------------------------------------------------------------
    # DELETING AND RENAMING. The third and fourth members of the guard family,
    # after _restorable (discard an edit) and _adoptable (overwrite from a ref).
    # These destroy the file itself, so they are the strictest.
    print("\ndeleting a tracked file is possible, and guarded four ways")
    for _n in ("git_rm", "git_mv"):
        check(_n in _reg, f"{_n} is in REGISTRY")
        check(_n in _tools, f"{_n} is callable (@mcp.tool)")
    _seg_rm = _src_cc.split('"git_rm": lambda')[1].split("),\n")[0]
    check("_removable(" in _seg_rm, "git_rm routes its path through _removable")
    check('"-r"' not in _seg_rm and "'-r'" not in _seg_rm,
          "and there is no recursive form, which is the one flag that turns a "
          "delete into a catastrophe")
    check('["-f"] if confirm_dirty' in _seg_rm,
          "and -f rides on confirm_dirty, or git would veto what the guard "
          "just allowed and the override would be cosmetic")
    _seg_mv = _src_cc.split('"git_mv": lambda')[1].split("),\n")[0]
    check("_movable(" in _seg_mv, "git_mv routes its paths through _movable")

    # _splat_refs is the interesting half: it encodes that a subsegment and a
    # filename are ONE fact in two places. Anchor the test on a reference that
    # really exists, so it cannot pass by finding nothing.
    #
    # The anchor is DISCOVERED, not hardcoded. It used to name
    # src/st/rno0/unk_4A320.c literally, and on 2026-08-17 that file was renamed
    # to giantbro_helpers_2.c -- by git_mv, the very tool this block tests. The
    # test then failed three checks and crashed on the fourth, reporting a guard
    # defect where there was none. A test that names a moving target is a test
    # that will one day lie about the thing it guards, and this one lied about a
    # security guard. Pick any tracked, splat-referenced source file instead.
    # Two things make an anchor usable, and the second is not obvious. It must be
    # tracked and splat-referenced, AND its stem must be distinctive. The first
    # candidate found by a naive scan was src/st/rno0/bss.c, whose stem `bss`
    # appears in 52 subsegments across every overlay's config, so the reference
    # this block wants to assert on was buried behind config/splat.hd.dra.yaml.
    # A generic stem does not prove the tool located THIS file's subsegment.
    _live, _ref = None, None
    for _cand in sorted((_repo / "src" / "st" / "rno0").glob("*.c")):
        _rel = _cand.relative_to(_repo).as_posix()
        if not _cc_mod._is_tracked(_rel):
            continue
        _hits = _cc_mod._splat_refs(_rel)
        _own = [r for r in _hits
                if "splat.us.strno0.yaml" in r and _cand.stem in r]
        # One reference, in this overlay's own config, is the unambiguous case.
        if _own and len(_hits) <= 4:
            _live, _ref = _rel, _own[0]
            break
    check(_live is not None,
          f"found a tracked, splat-referenced anchor with a distinctive stem "
          f"({_live})")
    _refs = _cc_mod._splat_refs(_live) if _live else []
    check(bool(_refs),
          f"_splat_refs finds the live subsegment for {_live} ({len(_refs)})")
    if _ref:
        check("splat.us.strno0.yaml" in _ref and Path(_live).stem in _ref,
              f"and names the config and the line ({_ref.strip()})")
    check(_cc_mod._splat_refs("src/st/e_floor_trap.h") == [],
          "a header is never splat-referenced, so it is not checked")
    check(_cc_mod._splat_refs("automation/dashboard.py") == [],
          "and neither is anything outside src/")

    # A file that a splat config still points at must not vanish.
    _blocked_splat = None
    try:
        _cc_mod._removable(_live)
    except Exception as e:                                      # Rejected
        _blocked_splat = str(e)
    check(_blocked_splat is not None,
          "removing a splat-referenced source file is refused")
    if _blocked_splat:
        check("splat.us.strno0.yaml" in _blocked_splat,
              "and the refusal names the config that has to be edited first")
        check("confirm_splat_ref" in _blocked_splat,
              "and says how to override deliberately")
    check(_cc_mod._removable(_live, False, True).endswith(Path(_live).name),
          "confirm_splat_ref=True lets it through")

    # Untracked and directories are refused outright, with no override.
    _untracked_rel = "src/_rm_guard_probe.c"
    _untracked = _repo / _untracked_rel
    _u_had = _untracked.exists()
    try:
        _untracked.write_text("/* probe */\n", encoding="utf-8")
        _blocked_untracked = None
        try:
            _cc_mod._removable(_untracked_rel)
        except Exception as e:                                  # Rejected
            _blocked_untracked = str(e)
        check(_blocked_untracked is not None,
              "removing an UNTRACKED file is refused")
        if _blocked_untracked:
            check("does not track" in _blocked_untracked,
                  "and says why: there is no history to recover it from")
    finally:
        if not _u_had:
            _untracked.unlink(missing_ok=True)

    _blocked_dir = None
    try:
        _cc_mod._removable("src/st")
    except Exception as e:                                      # Rejected
        _blocked_dir = str(e)
    check(_blocked_dir is not None, "removing a DIRECTORY is refused")
    if _blocked_dir:
        check("recursive" in _blocked_dir,
              "and says there is no recursive form, deliberately")

    # A clean, tracked, unreferenced file is removable without ceremony: that
    # is the ordinary case and it must not need a flag.
    #
    # DISCOVERED, not named, and for a sharper reason than the anchor above.
    # This used to be automation/dashboard.py, which meant the check asserted
    # "the guard permits a clean file" only while nobody was editing the
    # dashboard. On 2026-08-17 a one-line dashboard change made it dirty and
    # this failed, reporting a defect in _removable that did not exist. A test
    # whose subject is "clean" must not name a file a developer might have open.
    _plain, _plain_path = None, None
    for _cand in sorted((_repo / "automation").glob("*.py")):
        _rel = _cand.relative_to(_repo).as_posix()
        if _cc_mod._is_tracked(_rel) and not _cc_mod._is_dirty(_rel):
            _plain_path = _rel
            break
    check(_plain_path is not None,
          f"found a clean tracked file to test the ordinary case ({_plain_path})")
    if _plain_path:
        try:
            _plain = _cc_mod._removable(_plain_path)
        except Exception as e:                                  # noqa: BLE001
            check(False, f"a clean tracked file must be removable ({e})")
    check(bool(_plain),
          "a clean, tracked, unreferenced file needs no override")

    # _movable's guard is DIRECTIONAL: it looks at the source stem only, so the
    # config-first ordering is the one that passes.
    # The destination is a name that does not exist, for the same reason the
    # anchor is discovered: a real filename here becomes wrong the moment
    # somebody renames it.
    _dest = "src/st/rno0/_mv_guard_probe_dest.c"
    _blocked_mv = None
    try:
        _cc_mod._movable(_live, _dest)
    except Exception as e:                                      # Rejected
        _blocked_mv = str(e)
    check(_blocked_mv is not None,
          "moving a file whose OLD stem is still declared is refused")
    if _blocked_mv:
        check("_mv_guard_probe_dest" in _blocked_mv,
              "and the refusal names the new stem the config should point at")
        check("FIRST" in _blocked_mv,
              "and states the ordering, which is the actual lesson")
    check(_cc_mod._movable(_live, _dest, False, True)[0]
          .endswith(Path(_live).name),
          "confirm_splat_ref=True lets it through and returns both paths")
    _mv_onto = None
    try:
        _cc_mod._movable("automation/dashboard.py", "automation/scheduler.py")
    except Exception as e:                                      # Rejected
        _mv_onto = str(e)
    check(_mv_onto is not None and "already exists" in (_mv_onto or ""),
          "moving onto an existing file is refused")

    # ------------------------------------------------------------------
    # QUEUE BACKUP.
    #
    # The live queue is outside the repo because a cloud sync daemon destroyed
    # the in-repo one in 2026-07. That was the right call and it left a gap
    # nobody looked at for a month: a git checkpoint protected src/ and the docs
    # and not the queue, so the record of HOW 259 matches were produced existed
    # in one place with no history.
    #
    # These checks are about the shape of the fix, not the copy itself: the
    # destination must be in-repo or it cannot be committed, and restore must
    # not be able to fire by accident.
    # ------------------------------------------------------------------
    print("\nqueue reports preserve the existing derivation note by default")
    _saved_dryrun = cc.DRYRUN
    cc.DRYRUN = True
    try:
        try:
            _report_plan = cc.queue_report(
                "us:BOSS/BO6:BO6_RicStepStand", "near",
                notes="new evidence")
            _replace_plan = cc.queue_report(
                "us:BOSS/BO6:BO6_RicStepStand", "near",
                notes="superseding evidence", keep_note=False)
            _verdict_plan = cc.queue_report(
                "us:BOSS/BO6:BO6_RicEntityCrashBibleBeam", "deferred",
                verdict_kind="permuter-exhausted",
                verdict_seed_current=True,
                verdict_source="controlled receipt")
        except TypeError:
            _report_plan = {}
            _replace_plan = {}
            _verdict_plan = {}
    finally:
        cc.DRYRUN = _saved_dryrun
    check("--keep-note" in _report_plan.get("argv", []),
          "commands_client preserves notes when keep_note is omitted")
    check("--keep-note" not in _replace_plan.get("argv", []),
          "commands_client permits an explicit note replacement")
    check("--verdict-kind" in _verdict_plan.get("argv", [])
          and "--verdict-seed-current" in _verdict_plan.get("argv", [])
          and "--verdict-source" in _verdict_plan.get("argv", []),
          "commands_client forwards structured search authority")
    _mcp_queue_src = (MCP / "sotn_cmd_mcp.py").read_text(encoding="utf-8")
    check(re.search(r"def queue_report\([^)]*keep_note\s*:\s*bool\s*=\s*True",
                    _mcp_queue_src, re.S) is not None,
          "the MCP queue_report schema defaults keep_note to True")
    check("keep_note=keep_note" in _mcp_queue_src,
          "the MCP wrapper forwards keep_note rather than accepting it cosmetically")
    check("verdict_kind=verdict_kind" in _mcp_queue_src
          and "verdict_seed_current=verdict_seed_current" in _mcp_queue_src
          and "verdict_source=verdict_source" in _mcp_queue_src,
          "the MCP wrapper forwards every structured verdict field")

    _long_note = "derivation:" + ("N" * 2048)
    _long_proof = "verified:" + ("P" * 1024)
    _saved_dryrun = cc.DRYRUN
    cc.DRYRUN = True
    try:
        _long_report = cc.queue_report(
            "us:BOSS/BO6:BO6_RicStepStand", "near",
            notes=_long_note, proof=_long_proof)
    finally:
        cc.DRYRUN = _saved_dryrun
    _long_argv = _long_report.get("argv", [])
    _note_arg = (_long_argv[_long_argv.index("--notes") + 1]
                 if "--notes" in _long_argv else "")
    _proof_arg = (_long_argv[_long_argv.index("--proof") + 1]
                  if "--proof" in _long_argv else "")
    check(_note_arg == _long_note,
          "commands_client forwards the complete queue note without truncation")
    check(_proof_arg == _long_proof,
          "commands_client forwards the complete proof without truncation")

    print("\nexact queue lookup returns one complete durable record")
    check("queue_get" in registry, "queue_get is in REGISTRY")
    check("queue_get" in tools, "queue_get is callable (@mcp.tool)")
    _queue_get = getattr(cc, "queue_get", None)
    check(callable(_queue_get), "commands_client exposes queue_get")
    _get_plan = {}
    if callable(_queue_get):
        _saved_dryrun = cc.DRYRUN
        cc.DRYRUN = True
        try:
            _get_plan = _queue_get("us:BOSS/BO6:BO6_RicStepStand")
        finally:
            cc.DRYRUN = _saved_dryrun
    check(_get_plan.get("argv", [])[-3:] ==
          ["get", "--id", "us:BOSS/BO6:BO6_RicStepStand"],
          "queue_get validates and forwards the exact full queue id")
    _complete = False
    if callable(_queue_get):
        _saved_dryrun = cc.DRYRUN
        _saved_run = cc.subprocess.run
        long_record = {
            "id": "us:BOSS/BO6:BO6_RicStepStand",
            "status": "deferred",
            "notes": "N" * 40000,
        }
        cc.DRYRUN = False
        try:
            cc.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(
                a[0] if a else [], 0, json.dumps(long_record), "")
            got = _queue_get(long_record["id"])
            _complete = got.get("record", {}).get("notes") == long_record["notes"]
        finally:
            cc.subprocess.run = _saved_run
            cc.DRYRUN = _saved_dryrun
    check(_complete,
          "queue_get returns evidence above MAX_OUT without truncation")
    _scheduler_src = (REPO / "automation" / "scheduler.py").read_text(
        encoding="utf-8")
    check("def cmd_get(" in _scheduler_src
          and 'sub.add_parser("get")' in _scheduler_src,
          "scheduler owns the exact read-only lookup")
    check("return cc.queue_get(" in _mcp_queue_src,
          "the MCP wrapper uses the lossless commands_client path")

    print("\ncompiling reconciliation artifacts have one immutable publisher")
    check("candidate_publish" in registry,
          "candidate_publish is in REGISTRY")
    check("candidate_publish" in tools,
          "candidate_publish is callable (@mcp.tool)")
    _publish_plan = _cc_mod.build_argv(
        "candidate_publish",
        function_id="us:ST/RDAI:func_us_801C4B2C",
        source_file="automation/candidates/us_ST_RDAI_func_us_801C4B2C.c")
    check("artifact_store.py" in _publish_plan[1]
          and _publish_plan[-4:] == [
              "--id", "us:ST/RDAI:func_us_801C4B2C", "--from-file",
              str(REPO / "automation" / "candidates" /
                  "us_ST_RDAI_func_us_801C4B2C.c")],
          "candidate publication validates the exact id and source argv")
    _bad_publish = None
    try:
        _cc_mod.build_argv(
            "candidate_publish", function_id="not-an-exact-id",
            source_file="automation/candidates/us_ST_RDAI_func_us_801C4B2C.c")
    except Exception as exc:
        _bad_publish = str(exc)
    check(_bad_publish is not None,
          "candidate publication refuses a non-queue identity")
    check('return cc.run(\n        "candidate_publish"' in _mcp_queue_src,
          "the MCP wrapper forwards candidate publication to the allowlist")

    print("\nthe queue can be snapshotted into the repo and restored")
    check("queue_snapshot" in registry, "queue_snapshot is in REGISTRY")
    check("queue_snapshot" in tools, "queue_snapshot is callable (@mcp.tool)")
    check("queue_restore" in registry, "queue_restore is in REGISTRY")
    check("queue_restore" in tools, "queue_restore is callable (@mcp.tool)")

    _snap = _cc_mod.build_argv("queue_snapshot")
    check(_snap[-1] == "snapshot" and "scheduler.py" in " ".join(_snap),
          f"queue_snapshot runs scheduler.py snapshot ({_snap[-2:]})")
    # A snapshot outside the repo cannot be committed, which is the whole point.
    _out_escape = None
    try:
        _cc_mod.build_argv("queue_snapshot", out="../queue-escape.jsonl")
    except Exception as e:                                      # Rejected
        _out_escape = str(e)
    check(_out_escape is not None,
          "a snapshot destination outside the repo is refused")
    _in = _cc_mod.build_argv(
        "queue_snapshot", out="automation/queue/snapshots/probe.jsonl")
    check(_in[-1].endswith("automation/queue/snapshots/probe.jsonl"),
          "an in-repo destination that does not exist yet is accepted")

    # restore replaces every record, so it must be inert without confirm.
    _res = _cc_mod.build_argv(
        "queue_restore", from_file="automation/scheduler.py")
    check("--confirm" not in _res,
          "queue_restore omits --confirm by default, so it cannot fire by accident")
    _res_ok = _cc_mod.build_argv(
        "queue_restore", from_file="automation/scheduler.py", confirm=True)
    check("--confirm" in _res_ok, "and confirm=True passes it through")

    _sched = (REPO / "automation" / "scheduler.py").read_text(encoding="utf-8")
    check('"restore"' in _sched.split("_MUTATING")[1].split("}")[0],
          "scheduler counts restore as MUTATING, so the queue-owner guard covers it")
    check('"snapshot"' not in _sched.split("_MUTATING")[1].split("}")[0],
          "and snapshot as non-mutating, so a read-only copy is never blocked")
    check("pre-restore" in _sched,
          "restore snapshots what it is about to replace, so it is reversible")
    check("q.transaction(fn)" in _sched.split("def cmd_snapshot")[1]
          .split("def cmd_restore")[0],
          "snapshot borrows the writer's lock, so a running fleet cannot be "
          "caught mid-write")

    # ------------------------------------------------------------------
    # THE THIRD SURFACE: the MCPB bundle manifest.
    #
    # REGISTRY and @mcp.tool() were the two surfaces this file was written for.
    # There is a third, and it drifted furthest of all: automation/mcpb/
    # sotn-cmd/manifest.json carries a `tools` array that is what anyone reading
    # the bundle sees as the connector's capabilities. It said 21 while the
    # connector exposed 72 -- not a stale detail but a wrong answer to "what can
    # this thing do", given to exactly the reader least able to check.
    #
    # Same failure mode as the stale server/ snapshots that were deleted on
    # 2026-08-09: a hand-maintained copy of something authoritative, sitting
    # where a reader lands first.
    # ------------------------------------------------------------------
    import json as _json

    print("\nthe MCPB manifest agrees with the callable surface")
    _man_path = REPO / "automation" / "mcpb" / "sotn-cmd" / "manifest.json"
    check(_man_path.is_file(), "automation/mcpb/sotn-cmd/manifest.json exists")
    if _man_path.is_file():
        _man = _json.loads(_man_path.read_text(encoding="utf-8"))
        _man_tools = {t["name"] for t in _man.get("tools", [])}
        _missing = sorted(tools - _man_tools)
        _extra = sorted(_man_tools - tools)
        check(not _missing,
              f"every callable tool is listed in the manifest (missing: {_missing})")
        check(not _extra,
              f"the manifest lists no tool that does not exist (extra: {_extra})")
        # The manifest must say out loud that it is a launcher for one client,
        # not the server, or `platforms: [win32]` reads as "Windows only".
        _ld = _man.get("long_description", "")
        check("NOT THE SERVER" in _ld.upper(),
              "the manifest states it is not the server and is not required")
        check("clients/" in _ld,
              "and points at automation/mcp/clients/ for other MCP clients")

    # ------------------------------------------------------------------
    # PORTABILITY. The servers must run under any MCP client, not just Claude
    # Desktop. Kenichi is migrating to OpenAI Codex, and "the mcpb work probably
    # covered it" was an assumption worth testing rather than repeating: MCPB is
    # a Claude Desktop packaging format and its ${user_config} substitution is a
    # Claude Desktop feature, so the bundles prove nothing about portability.
    #
    # What actually has to hold is smaller and checkable:
    #   1. no client-specific import or branch in the server sources
    #   2. sibling imports survive a launch form where sys.path[0] is not the
    #      script directory, which is why each server inserts its own path
    #   3. every default is derived from the file's own location, so a client
    #      that can set neither cwd nor env still gets a working server
    #   4. a registration snippet exists for a non-Anthropic client
    # ------------------------------------------------------------------
    print("\nthe servers carry no client-specific code")
    _cmd_src = (MCP / "sotn_cmd_mcp.py").read_text(encoding="utf-8")
    _loc_src = (MCP / "sotn_local_mcp.py").read_text(encoding="utf-8")
    _cc_src = (MCP / "commands_client.py").read_text(encoding="utf-8")
    for _name, _src in (("sotn_cmd_mcp.py", _cmd_src),
                        ("sotn_local_mcp.py", _loc_src),
                        ("commands_client.py", _cc_src)):
        _code = "\n".join(
            ln for ln in _src.splitlines()
            if not ln.lstrip().startswith("#"))
        # Comments and docstrings may discuss clients; executable lines may not
        # import one or branch on one.
        check(not re.search(r"^\s*(import|from)\s+\w*(claude|anthropic|openai)",
                            _code, re.I | re.M),
              f"{_name} imports no vendor client SDK")
        check("CLAUDE_" not in _code and "ANTHROPIC_" not in _code,
              f"{_name} reads no client-specific environment variable")

    print("\nsibling imports do not depend on the launch form")
    for _name, _src in (("sotn_cmd_mcp.py", _cmd_src),
                        ("sotn_local_mcp.py", _loc_src)):
        check("sys.path.insert" in _src,
              f"{_name} puts its own directory on sys.path before importing siblings")

    print("\nevery default is self-locating, so no cwd and no env are required")
    check("Path(__file__).resolve().parents[2]" in _cc_src,
          "commands_client derives REPO from its own location when SOTN_REPO is unset")
    # Proven rather than asserted: import the module with the repo variable
    # cleared and confirm it still lands on this repo.
    import os as _os
    import importlib as _il
    _saved = _os.environ.pop("SOTN_REPO", None)
    try:
        _il.reload(cc)
        check(Path(cc.REPO).resolve() == REPO.resolve(),
              "with SOTN_REPO unset the module still resolves to this repo")
    finally:
        if _saved is not None:
            _os.environ["SOTN_REPO"] = _saved
        _il.reload(cc)

    # The MCP server has its own small venv, while asm-differ and the permuter
    # depend on the root repository venv. A bare `python3` fallback silently
    # crosses that environment boundary and fails only when the child imports a
    # module such as watchdog or toml.
    print("\nchild Python defaults to the repository tool venv")
    _saved_repo = _os.environ.get("SOTN_REPO")
    _saved_python = _os.environ.pop("SOTN_PYTHON", None)
    try:
        with tempfile.TemporaryDirectory() as _td:
            _fake_repo = Path(_td)
            _suffix = Path("Scripts/python.exe") if _os.name == "nt" else Path("bin/python")
            _fake_python = _fake_repo / ".venv" / _suffix
            _fake_python.parent.mkdir(parents=True)
            _fake_python.touch()
            _os.environ["SOTN_REPO"] = str(_fake_repo)
            _il.reload(cc)
            check(Path(cc.PYTHON) == _fake_python,
                  "with SOTN_PYTHON unset child tools select the root repo venv")

            _override = str(_fake_repo / "explicit-python")
            _os.environ["SOTN_PYTHON"] = _override
            _il.reload(cc)
            check(cc.PYTHON == _override,
                  "an explicit SOTN_PYTHON still overrides the discovered venv")

            _os.environ.pop("SOTN_PYTHON", None)
            _repo_without_venv = _fake_repo / "without-venv"
            _repo_without_venv.mkdir()
            _os.environ["SOTN_REPO"] = str(_repo_without_venv)
            _il.reload(cc)
            check(cc.PYTHON == sys.executable,
                  "without a root repo venv child tools retain the current interpreter")
    finally:
        if _saved_repo is None:
            _os.environ.pop("SOTN_REPO", None)
        else:
            _os.environ["SOTN_REPO"] = _saved_repo
        if _saved_python is None:
            _os.environ.pop("SOTN_PYTHON", None)
        else:
            _os.environ["SOTN_PYTHON"] = _saved_python
        _il.reload(cc)

    print("\nnon-Anthropic clients have a registration to copy")
    _clients = REPO / "automation" / "mcp" / "clients"
    for _f in ("README.md", "codex.config.toml",
               "mcp_servers.native.json", "mcp_servers.windows-wsl.json"):
        check((_clients / _f).is_file(), f"automation/mcp/clients/{_f} exists")
    if (_clients / "codex.config.toml").is_file():
        _codex = (_clients / "codex.config.toml").read_text(encoding="utf-8")
        check("[mcp_servers.sotn-cmd]" in _codex,
              "the Codex snippet uses Codex's [mcp_servers.<name>] table syntax")
        check("sotn_cmd_mcp.py" in _codex,
              "and launches the real server script by absolute path")
        check("SOTN_CMD_DRYRUN = \"1\"" in _codex,
              "and ships dry-run ON, like every other registration")

    # ------------------------------------------------------------------
    # THE DOCS ARE A SURFACE TOO. docs/TOOLING.md tells an agent which tool to
    # call; a tool named there that does not exist sends the agent down a path
    # that ends in an error it cannot diagnose. Same class of harm as the stale
    # manifest, so it gets the same treatment.
    # ------------------------------------------------------------------
    print("\nthe docs name only tools and scripts that exist")
    _tooling = REPO / "docs" / "TOOLING.md"
    check(_tooling.is_file(), "docs/TOOLING.md exists")
    if _tooling.is_file():
        _doc = _tooling.read_text(encoding="utf-8")
        # Tool and script names are written in a leading table cell. The old
        # `\w+` pattern silently ignored every `.py` row while claiming to
        # validate scripts too.
        _named = set(re.findall(
            r"^\|\s*`([A-Za-z0-9_]+(?:\.py)?)`", _doc, re.M))
        _known = tools | set(cc.FS_ACTIONS if hasattr(cc, "FS_ACTIONS") else ())
        _known |= {"read_file", "write_file", "list_dir", "search_repo"}
        _known |= set(cc.AUTOMATION_SCRIPTS)
        _known |= {s[:-3] for s in cc.AUTOMATION_SCRIPTS}
        _ghosts = sorted(n for n in _named if n not in _known)
        check(not _ghosts,
              f"no doc row names a tool or script that does not exist: {_ghosts}")
        _doc_scripts = set(re.findall(
            r"^\|\s*`([A-Za-z0-9_]+\.py)`", _doc, re.M))
        _missing_script_files = sorted(
            name for name in _doc_scripts
            if not (REPO / "automation" / name).is_file()
        )
        check(not _missing_script_files,
              f"every documented analysis script exists on disk: "
              f"{_missing_script_files}")
        _uncallable_doc_scripts = sorted(
            _doc_scripts - set(cc.AUTOMATION_SCRIPTS)
        )
        check(not _uncallable_doc_scripts,
              f"every documented analysis script is callable: "
              f"{_uncallable_doc_scripts}")
        _undocumented = sorted(tools - _named)
        check(not _undocumented,
              f"every callable tool has a reference row: {_undocumented}")

        # TOOLING.md says every remaining top-level test is callable through
        # run_automation. That is a machine claim, so a threshold or spot check
        # would merely postpone the next stale-doc failure.
        _tests = {p.name for p in (REPO / "automation").glob("test_*.py")}
        _uncallable_tests = sorted(_tests - set(cc.AUTOMATION_SCRIPTS))
        check(not _uncallable_tests,
              f"every focused test named by the blanket doc claim is callable: "
              f"{_uncallable_tests}")

    print("\nAGENTS.md points at the roadmap and requires keeping it current")
    _agents = REPO / "AGENTS.md"
    check(_agents.is_file(), "AGENTS.md exists")
    if _agents.is_file():
        _a = _agents.read_text(encoding="utf-8")
        check("ROADMAP.md" in _a, "AGENTS.md references ROADMAP.md")
        check("docs/TOOLING.md" in _a, "AGENTS.md references docs/TOOLING.md")
        check("docs/CONNECTORS.md" in _a, "AGENTS.md references docs/CONNECTORS.md")
        check(len(_a) > 2000,
              f"AGENTS.md is not a stub ({len(_a)} bytes; it was 47)")
    check((REPO / "docs" / "CONNECTORS.md").is_file(), "docs/CONNECTORS.md exists")

    print("\nevery repo path named in the new docs resolves")
    for _docname in ("docs/TOOLING.md", "docs/CONNECTORS.md", "AGENTS.md"):
        _p = REPO / _docname
        if not _p.is_file():
            continue
        _bad = []
        for _ref in set(re.findall(r"`((?:automation|docs|config|src|include|tools)"
                                   r"/[A-Za-z0-9_./-]+)`",
                                   _p.read_text(encoding="utf-8"))):
            if "<" in _ref or "*" in _ref:
                continue
            if not (REPO / _ref).exists():
                _bad.append(_ref)
        check(not _bad, f"{_docname} names only paths that exist: {sorted(_bad)}")

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
