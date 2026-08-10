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

import re
import sys
from pathlib import Path

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
    for act in ("permuter", "run_analysis"):
        check(act in body, f"job_start still handles {act}")

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

    print("\npush remains unparameterised")
    import inspect
    sig = inspect.signature(cc.REGISTRY["git_push"])
    check(not sig.parameters,
          "git_push takes no arguments, so no caller can choose the remote")

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
    finally:
        _cc_mod.DRYRUN = _was

    check(default["backend"] == "zen",
          f"fleet_start defaults to zen (got {default['backend']})")
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
    try:
        _pend.mkdir(parents=True, exist_ok=True)
        # STATE THE PRECONDITION. This check went pass/fail/pass/pass across
        # four runs of unchanged code on 2026-08-10, and the failing run was
        # self-contradictory: the file WAS restored byte-for-byte and the
        # journal WAS consumed, but restored_files came back 0.
        #
        # replay_pending_journals() walks the WHOLE pending directory, so any
        # other process that replays first legitimately takes this journal and
        # leaves fleet_stop nothing to count. That makes the assertion below a
        # statement about global state unless the directory starts empty. Say
        # so rather than letting a leftover turn into a mystery failure.
        _stray = sorted(p.name for p in _pend.glob("*.json"))
        check(not _stray,
              f"the pending dir is empty before this test writes to it; a "
              f"leftover journal would be replayed by this same call and "
              f"change the count ({_stray})")
        _victim.write_text(_orig, encoding="utf-8")
        _jf.write_text(_j.dumps({
            "src_rel": "automation/logs/selftest-victim.c",
            "original": _orig, "worker": "selftest-dead-worker",
            "pid": 999997,            # a pid that is not alive
            "at": _t.time()}), encoding="utf-8")
        _victim.write_text(_orig + "// STRANDED BY A KILLED WORKER\n",
                           encoding="utf-8")
        _cc_mod.DRYRUN = False
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
    finally:
        _cc_mod.DRYRUN = _was
        _victim.unlink(missing_ok=True)
        _jf.unlink(missing_ok=True)

    print("\na count of zero against a non-empty pending dir is not silent")
    # The guard that makes the next occurrence self-diagnosing. Drive it by
    # leaving a journal owned by a LIVE pid, which replay must skip: pending
    # is non-empty on entry and the restore count is legitimately 0.
    _jf2 = _pend / "selftest-live-owner.json"
    _was2 = _cc_mod.DRYRUN
    try:
        _victim.write_text(_orig, encoding="utf-8")
        _jf2.write_text(_j.dumps({
            "src_rel": "automation/logs/selftest-victim.c",
            "original": _orig, "worker": "selftest-live-owner",
            "pid": __import__("os").getpid(),   # alive by construction
            "at": _t.time()}), encoding="utf-8")
        _cc_mod.DRYRUN = False
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
        _jf2.unlink(missing_ok=True)
        _victim.unlink(missing_ok=True)

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

        # A journalled file is ordinary in-flight recovery and must NOT block,
        # or every failed apply would need a confirmation flag.
        _pending.mkdir(parents=True, exist_ok=True)
        _jf.write_text(_json.dumps({"src_rel": _victim_rel,
                                    "original": ""}), encoding="utf-8")
        _passed = None
        try:
            _passed = _cc_mod._restorable(_victim_rel)
        except Exception as e:                                  # noqa: BLE001
            _passed = None
            check(False, f"a journalled file should not be blocked ({e})")
        check(bool(_passed),
              "a file covered by a crash journal restores without friction")
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
