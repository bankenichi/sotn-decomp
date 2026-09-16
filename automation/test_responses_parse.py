#!/usr/bin/env python3
"""Offline fixtures for Muse / Zen /v1/responses parse and token budget.

WHY THIS EXISTS
    Fleet logs on 2026-09-16 showed two stacked failures on muse-spark:

      1. Dashboard effort 0 (labelled low) sent no reasoning list, so
         REASONING_EFFORT was omitted and every worker defaulted to none.
      2. `_responses_generate` then reported "0 chars, 0 reasoning items"
         after ~100s with no status, incomplete_details, or usage.

    A live probe of https://opencode.ai/zen/v1/responses showed the empty
    reply is an incomplete body: status=incomplete, reason=max_output_tokens,
    empty output array, reasoning_tokens consuming the whole budget. A
    completed reply puts the C in a message part with type=output_text.

    This suite is offline. It pins the parse of those two JSON shapes, the
    muse max_output_tokens floor, and the dashboard-to-env mapping comments
    in worker_direct, without calling the provider or building the game.

Run: python3 automation/test_responses_parse.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAILS: list[str] = []

# Measured 2026-09-16: effort=xhigh, max_output_tokens=256.
INCOMPLETE = {
    "id": "resp_incomplete_fixture",
    "status": "incomplete",
    "incomplete_details": {"reason": "max_output_tokens"},
    "output": [],
    "usage": {
        "input_tokens": 12,
        "output_tokens": 256,
        "output_tokens_details": {"reasoning_tokens": 253},
    },
}

# Measured 2026-09-16: effort=xhigh, max_output_tokens=4000. Summary empty,
# encrypted_content present, message part type=output_text.
COMPLETED = {
    "id": "resp_completed_fixture",
    "status": "completed",
    "output": [
        {
            "type": "reasoning",
            "summary": [],
            "encrypted_content": "enc-not-the-answer",
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "output_text", "text": "void func_us_801B21F0(void) {}"},
            ],
        },
    ],
    "output_text": "void func_us_801B21F0(void) {}",
    "usage": {
        "input_tokens": 12,
        "output_tokens": 80,
        "output_tokens_details": {"reasoning_tokens": 40},
    },
}


def check(cond: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


def load():
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    wd = load()

    print("\nincomplete Responses bodies are not silent empties")
    parsed = wd.parse_responses_output(INCOMPLETE)
    check(parsed["text"] == "",
          "starved incomplete has no message text")
    check(parsed["reasoning_n"] == 0,
          "empty output array means zero reasoning items to walk")
    check(parsed["status"] == "incomplete",
          "status is incomplete, the field the live log omitted")
    check(parsed["incomplete_details"] == {"reason": "max_output_tokens"},
          "incomplete_details.reason is max_output_tokens")
    check((parsed["usage"] or {}).get("output_tokens_details", {})
          .get("reasoning_tokens") == 253,
          "usage still reports the reasoning tokens that ate the budget")

    print("\ncompleted Responses keep output_text message parts")
    parsed = wd.parse_responses_output(COMPLETED)
    check("void func_us_801B21F0" in parsed["text"],
          "message output_text parts are captured as the function body")
    check(parsed["reasoning_n"] == 1,
          "a reasoning item with empty summary still counts")
    check(parsed["status"] == "completed", "status is completed")
    check(parsed["incomplete_details"] is None,
          "completed replies have no incomplete_details")

    print("\noutput_text convenience is a fallback, not a double-count")
    only_convenience = {
        "status": "completed",
        "output": [],
        "output_text": "s32 helper(void) { return 0; }",
    }
    parsed = wd.parse_responses_output(only_convenience)
    check("s32 helper" in parsed["text"],
          "top-level output_text is used when output is empty")
    both = {
        "status": "completed",
        "output": [{
            "type": "message",
            "content": [{"type": "output_text", "text": "from-part"}],
        }],
        "output_text": "from-convenience",
    }
    parsed = wd.parse_responses_output(both)
    check(parsed["text"] == "from-part",
          "walking output wins when both the part and convenience exist")

    print("\nmuse max_output_tokens cannot starve the message")
    floor = max(wd.REASONING_MAX_TOKENS + wd.CONTENT_MAX_TOKENS,
                wd.MUSE_RESPONSES_MIN_OUTPUT_TOKENS)
    for effort in ("none", "low", "xhigh"):
        got = wd._responses_max_output_tokens(
            effort, "muse-spark-1.3-contributor-free")
        check(got == floor,
              f"muse effort={effort} requests {floor} tokens "
              f"(got {got}), including none")
    chat_none = wd._responses_max_output_tokens("none", "mimo-v2.5-free")
    check(chat_none == wd.CONTENT_MAX_TOKENS,
          "non-muse none still uses CONTENT_MAX only")
    chat_low = wd._responses_max_output_tokens("low", "mimo-v2.5-free")
    check(chat_low == wd.REASONING_MAX_TOKENS + wd.CONTENT_MAX_TOKENS,
          "non-muse low uses reasoning plus content headroom")

    print("\nResponses payload sends effort and summary when thinking is on")
    muse = "muse-spark-1.3-contributor-free"
    px = wd._responses_payload("prompt", effort="xhigh", model=muse)
    check(px["reasoning"] == {"effort": "xhigh", "summary": "auto"},
          "xhigh sends effort plus summary=auto")
    check(px["max_output_tokens"] == floor,
          "xhigh payload uses the muse floor")
    pl = wd._responses_payload("prompt", effort="low", model=muse)
    check(pl["reasoning"]["effort"] == "low",
          "low is an explicit effort, not omitted")
    pn = wd._responses_payload("prompt", effort="none", model=muse)
    check("reasoning" not in pn,
          "none omits the reasoning object so the API default stays off")
    check(pn["max_output_tokens"] == floor,
          "muse none still keeps reasoning headroom because muse still thinks")

    print("\nempty or incomplete outcomes are logged, not just char counts")
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        encoding="utf-8")
    check("responses status=" in src and "incomplete=" in src and "usage=" in src,
          "_responses_generate prints status, incomplete_details and usage "
          "when the body is empty or incomplete")

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
