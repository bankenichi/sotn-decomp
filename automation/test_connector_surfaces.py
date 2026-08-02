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

    print("\npush remains unparameterised")
    import inspect
    sig = inspect.signature(cc.REGISTRY["git_push"])
    check(not sig.parameters,
          "git_push takes no arguments, so no caller can choose the remote")

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
