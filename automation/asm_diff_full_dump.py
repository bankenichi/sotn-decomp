"""Dump the complete plain asm-diff output for one symbol into the build tree.

The MCP asm_diff tool truncates its captured stdout at 20k chars, which hides
everything after the first mismatching region. This helper runs diff.py
directly and writes the full text to a gitignored path so it can be read
whole without touching the git index.

Intended invocation: job_start(run_analysis, script="asm_diff_full_dump.py").
It ignores args and dumps func_us_80195C50 for the us bobo7 overlay.
"""

import os
import subprocess


def _repo_root():
    # automation/<this file> -> repo root is one directory up
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


root = _repo_root()

cmd = [
    ".venv/bin/python",
    "tools/asm-differ/diff.py",
    "-m",
    "--format",
    "plain",
    "--version",
    "us",
    "--overlay",
    "bobo7",
    "func_us_80195C50",
]

proc = subprocess.run(
    cmd,
    cwd=root,
    capture_output=True,
    text=True,
)

out_text = proc.stdout + "\n----- STDERR -----\n" + proc.stderr
out_path = os.path.join(root, "build", "us", "asm_diff_full_95c50.txt")

with open(out_path, "w", encoding="utf-8") as fh:
    fh.write(out_text)

print("dumped rc=%d stdout_chars=%d path=%s" % (proc.returncode, len(proc.stdout), out_path))
