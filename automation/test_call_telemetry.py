#!/usr/bin/env python3
"""Does the instrumentation actually capture what the diagnosis needs?

WHY THIS EXISTS
    Phase 1 of docs/fleet-dead-time.md exists to answer one question: of the
    93% of calls that return zero bytes, how many never got a first byte, and
    what did the provider say about it. Two fields carry that answer --
    `ttfb_s` and `stderr_head` -- and both are captured on the path where the
    child is KILLED, which is the hardest path to get right and the easiest to
    silently break.

    Reading the source is not enough. The previous version of the timeout
    handler looked correct and threw stderr away, because the read happened
    after a `raise` that never ran. So this drives the real
    `_opencode_run_once` against fake `opencode` binaries that reproduce each
    failure shape, and asserts on the JSONL that comes out the other end.

WHAT EACH FAKE REPRODUCES
    1. writes to stderr, then hangs      the 724-call case: a provider that
                                         explains itself and never answers
    2. streams a whole function, hangs   the 2-call case: salvage, plus a real
                                         ttfb measurement
    3. exits rc=0 having written nothing the 154-call case

Run: python3 automation/test_call_telemetry.py
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap

REPO = pathlib.Path(__file__).resolve().parent.parent
FAILS: list[str] = []

SCHEMA = {"ts", "worker", "model", "prompt_chars", "ttfb_s", "total_s",
          "stream_chars", "rc", "outcome", "stderr_head"}


def check(cond: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


def load_worker():
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Harness:
    """Runs the real function against a fake child, in a throwaway repo."""

    def __init__(self, wd):
        self.wd = wd
        self.dir = pathlib.Path(tempfile.mkdtemp())
        (self.dir / "automation" / "logs").mkdir(parents=True)
        wd.WIN_REPO = str(self.dir)
        wd.OPENCODE_MODEL = "test/model"
        wd.resolve_opencode = lambda: sys.executable

    def run(self, body: str, timeout: float):
        script = self.dir / "fake_opencode.py"
        script.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body),
                          encoding="utf-8")
        real = subprocess.Popen

        def popen(argv, **kw):                    # ignore argv, run the fake
            return real([sys.executable, str(script)], **kw)

        subprocess.Popen = popen
        try:
            try:
                return self.wd._opencode_run_once("PROMPT", timeout=timeout), None
            except Exception as e:                # noqa: BLE001
                return None, type(e).__name__
        finally:
            subprocess.Popen = real

    def records(self) -> list[dict]:
        f = self.dir / "automation" / "logs" / "calls.jsonl"
        if not f.is_file():
            return []
        return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]

    def last(self) -> dict:
        recs = self.records()
        return recs[-1] if recs else {}


def main() -> int:
    wd = load_worker()
    h = Harness(wd)

    print("\na provider that explains itself then never answers")
    # THE case: 724 of 726 timeouts looked exactly like this, and every
    # explanation was discarded with the killed child.
    h.run("""
        import sys, time
        sys.stdin.read()
        sys.stderr.write("429 Too Many Requests: quota exhausted\\n")
        sys.stderr.flush()
        time.sleep(60)
        """, 3)
    r = h.last()
    check(r.get("outcome") == "timeout_no_bytes",
          f"classified as timeout_no_bytes ({r.get('outcome')})")
    check("429" in (r.get("stderr_head") or ""),
          "the provider's reason SURVIVES the kill", repr(r.get("stderr_head")))
    check(r.get("ttfb_s") is None,
          "ttfb_s is null, not 0, when no byte ever arrived")

    print("\na model that finishes the code and then stops talking to us")
    out, _ = h.run("""
        import sys, time
        sys.stdin.read()
        time.sleep(1.0)
        sys.stdout.write("void f(void) {\\n"); sys.stdout.flush()
        sys.stdout.write("  int a = 1;\\n}\\n"); sys.stdout.flush()
        time.sleep(60)
        """, 4)
    r = h.last()
    check(r.get("outcome") == "timeout_complete",
          f"classified as timeout_complete ({r.get('outcome')})")
    check(r.get("ttfb_s") is not None and 0.5 < r["ttfb_s"] < 5.0,
          f"ttfb_s measures when the first byte landed ({r.get('ttfb_s')})")
    check(bool(out) and "void f" in (out or ""),
          "and the finished answer is RETURNED, not raised away")

    print("\na provider that returns success and nothing else")
    out, err = h.run("""
        import sys
        sys.stdin.read()
        """, 10)
    r = h.last()
    check(r.get("outcome") == "empty", f"classified as empty ({r.get('outcome')})")
    check(r.get("rc") == 0, "the exit code is recorded, so rc=0-with-no-bytes "
                            "is distinguishable from a crash")
    check(err == "_EmptyOutput", f"still raises for the retry loop ({err})")

    print("\nevery record is complete and machine-readable")
    recs = h.records()
    check(len(recs) == 3, f"one record per call, no more, no fewer ({len(recs)})")
    missing = {k for rec in recs for k in SCHEMA - set(rec)}
    check(not missing, f"every record carries the full schema ({missing})")
    check(all(isinstance(rec.get("total_s"), (int, float)) for rec in recs),
          "total_s is numeric on every record")
    check(all(rec.get("worker") for rec in recs),
          "every record names the worker that produced it")
    # THE #111 ARM. The first A/B had to be read off log file SIZES, because
    # nothing in calls.jsonl said which effort a call ran at; the arm lived in
    # the launch command and nowhere in the data. Set in emit_call rather than
    # at the call sites so no path can miss it.
    check(all(rec.get("effort") for rec in recs),
          "and the reasoning effort it ran at, on EVERY record")
    check(all(rec["effort"] != "" for rec in recs),
          "never blank: '' cannot distinguish 'ran at the default' from "
          "'predates this field', and those need opposite handling")

    print("\ntelemetry can never take a run down with it")
    wd_broken = load_worker()
    wd_broken.WIN_REPO = "/proc/nonexistent/cannot/create"
    try:
        wd_broken.emit_call({"outcome": "produced"})
        check(True, "an unwritable telemetry path is swallowed, not raised")
    except Exception as e:                        # noqa: BLE001
        check(False, "an unwritable telemetry path is swallowed, not raised",
              f"{type(e).__name__}: {e}")

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
