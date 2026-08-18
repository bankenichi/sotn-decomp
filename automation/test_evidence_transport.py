#!/usr/bin/env python3
"""Prove queue evidence crosses the Windows boundary without argv truncation."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


REPO = Path(__file__).resolve().parent.parent
SCHEDULER = REPO / "automation" / "scheduler.py"
FAILURES: list[str] = []


def check(condition: bool, label: str) -> None:
    print(("  ok   " if condition else "  FAIL ") + label)
    if not condition:
        FAILURES.append(label)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scheduler_round_trip(long_note: str, long_proof: str) -> None:
    print("\nscheduler accepts lossless evidence on stdin")
    with tempfile.TemporaryDirectory(prefix="evidence-transport-") as tmp:
        queue = Path(tmp) / "queue.jsonl"
        record = {
            "id": "us:ST/RDAI:Demo",
            "status": "todo",
            "build": "us",
            "function": "Demo",
            "overlay": "rdai",
            "tier": 0,
            "iterations": 0,
            "notes": "",
        }
        queue.write_text(json.dumps(record) + "\n", encoding="utf-8")
        env = dict(os.environ, SOTN_QUEUE=str(queue))
        payload = json.dumps(
            {"notes": long_note, "proof": long_proof}, ensure_ascii=True)
        proc = subprocess.run(
            [sys.executable, str(SCHEDULER), "report", "--id", record["id"],
             "--status", "near", "--evidence-stdin"],
            input=payload, capture_output=True, text=True, cwd=REPO, env=env,
            timeout=120)
        check(proc.returncode == 0,
              f"stdin report succeeds above the Windows argv limit ({proc.stderr.strip()})")
        saved = json.loads(queue.read_text(encoding="utf-8").splitlines()[0])
        check(saved.get("notes") == long_note,
              "the complete stdin note reaches the queue")
        check(saved.get("proof") == long_proof,
              "the complete stdin proof reaches the queue")


def direct_worker_transport(long_note: str, long_proof: str) -> None:
    print("\nworker_direct keeps evidence off the command line")
    module = load_module(
        "evidence_worker_direct",
        REPO / "automation" / "win" / "worker_direct.py")
    captured: dict[str, object] = {}

    def fake_wsl(cmd: str, timeout: float = 300,
                 input_text: str | None = None) -> tuple[int, str]:
        captured.update(cmd=cmd, input_text=input_text)
        return 0, "updated\n"

    module.wsl = fake_wsl
    record_id = "us:ST/RDAI:Demo"
    module._CURRENT_CLAIM = record_id
    module.sched("report", "--id", record_id, "--status", "near",
                 "--notes", long_note, "--proof", long_proof)
    command = str(captured.get("cmd", ""))
    evidence = json.loads(str(captured.get("input_text", "")))
    check(len(command) < 1000 and long_note not in command,
          "worker_direct argv stays short")
    check("--evidence-stdin" in command,
          "worker_direct selects scheduler stdin transport")
    check(evidence == {"notes": long_note, "proof": long_proof},
          "worker_direct stdin carries both complete fields")
    check(module._CURRENT_CLAIM is None,
          "a successful report clears the held claim")

    def failing_wsl(cmd: str, timeout: float = 300,
                    input_text: str | None = None) -> tuple[int, str]:
        return 1, "synthetic scheduler failure"

    module.wsl = failing_wsl
    module._CURRENT_CLAIM = record_id
    try:
        module.sched("report", "--id", record_id, "--status", "near",
                     "--notes", long_note)
    except RuntimeError:
        pass
    check(module._CURRENT_CLAIM == record_id,
          "a failed report retains the claim for the release handler")


def legacy_worker_transport(long_note: str, long_proof: str) -> None:
    print("\nworker_win keeps evidence off the command line")
    module = load_module(
        "evidence_worker_win",
        REPO / "automation" / "win" / "worker_win.py")
    captured: dict[str, object] = {}

    def fake_wsl(*args: str, check: bool = True,
                 input_text: str | None = None) -> str:
        captured.update(args=args, input_text=input_text)
        return "updated"

    module._wsl = fake_wsl
    module.sched("report", "--id", "us:ST/RDAI:Demo", "--status", "near",
                 "--notes", long_note, "--proof", long_proof)
    argv = list(captured.get("args", ()))
    evidence = json.loads(str(captured.get("input_text", "")))
    check(sum(len(str(arg)) for arg in argv) < 1000 and long_note not in argv,
          "worker_win argv stays short")
    check("--evidence-stdin" in argv,
          "worker_win selects scheduler stdin transport")
    check(evidence == {"notes": long_note, "proof": long_proof},
          "worker_win stdin carries both complete fields")


def main() -> int:
    long_note = "derivation:\u03bb:" + ("N" * 40000)
    long_proof = "proof:" + ("P" * 40000)
    scheduler_round_trip(long_note, long_proof)
    direct_worker_transport(long_note, long_proof)
    legacy_worker_transport(long_note, long_proof)
    print("\n" + ("all checks passed" if not FAILURES
                    else f"{len(FAILURES)} FAILED"))
    for failure in FAILURES:
        print("  - " + failure)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
