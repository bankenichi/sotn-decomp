"""Run the vendored decomp-permuter tests from their package directory."""

import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    vendor_root = (
        Path(__file__).resolve().parents[1] / "tools" / "decomp-permuter"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "test",
            "-p",
            "test_perm.py",
        ],
        cwd=vendor_root,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode == 0:
        print("vendored permuter tests passed")
        return 0

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    first = re.search(r"^(?:FAIL|ERROR): ([A-Za-z0-9_]+) \(([^)]+)\)$",
                      output, re.MULTILINE)
    detail_lines = lines[-16:]
    if first:
        test_name, owner = first.groups()
        probe = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", "test." + owner],
            cwd=vendor_root,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        probe_output = ((probe.stdout or "") + "\n" + (probe.stderr or "")).strip()
        detail_lines = [
            line.strip() for line in probe_output.splitlines() if line.strip()
        ][-16:]
    detail = " | ".join(detail_lines) or "no output"
    print("vendored permuter tests FAILED: " + detail)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
