#!/usr/bin/env python3
"""Turn a ChatGPT share link into plain text, in one call.

WHY THIS EXISTS
    Reading a shared conversation by hand cost most of a session on
    2026-08-03. Every obvious route fails in a different way:

      WebFetch          returns the page SHELL only. The conversation is
                        client-rendered, so the HTML has a title and nothing
                        else.
      Scrolling the DOM lazy-loads. A share with 273 messages rendered 5, then
                        7 after interaction. Any count you take is a lower
                        bound on a moving target.
      Scraping the HTML the payload is inside a react-router turbo-stream blob
                        with escaped quotes, not `__NEXT_DATA__`, and the
                        message objects are not laid out the way older
                        scrapers expect.

    The route that actually works is the endpoint the page itself calls:

        GET https://chatgpt.com/backend-api/share/<share_id>

    which returns the whole conversation as JSON, all messages, no rendering,
    no scrolling. Share pages are public, so no credentials are involved.

WHAT IT RETURNS
    User and assistant prose only. Tool calls, system messages, and the
    reasoning/analysis channel are dropped by default: on the conversation that
    prompted this, 273 nodes reduced to 35 that a human would call "the
    conversation", and most of the remainder was the model narrating its own
    tool use.

Usage:
    python3 automation/mcp/chatgpt_share.py <url|share_id>
    python3 automation/mcp/chatgpt_share.py <url> --all      # keep tool/system
    python3 automation/mcp/chatgpt_share.py --file saved.json
    python3 automation/mcp/chatgpt_share.py --self-test

As an MCP server (register once, then any session can read a link):
    python3 automation/mcp/chatgpt_share.py --serve
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://chatgpt.com/backend-api/share/{}"
# Sent because the endpoint 403s a bare urllib default agent. Nothing here
# identifies a user; a share link is public by construction.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

_ID = re.compile(r"([0-9a-fA-F]{8}-[0-9a-fA-F-]{20,})")

# Channels the model talks to ITSELF on. `analysis` is chain-of-thought and
# `commentary` is tool preamble; neither is part of the conversation and both
# are large. Kept out unless --all.
_INTERNAL_CHANNELS = {"analysis", "commentary"}


def share_id(url_or_id: str) -> str:
    """The share id out of any form of the link.

    Accepts a bare id, a /share/<id> URL, and a /share/e/<id> URL, because all
    three get pasted and the difference is not interesting to the caller.
    """
    m = _ID.search(url_or_id or "")
    if not m:
        raise ValueError(f"no share id found in {url_or_id!r}")
    return m.group(1)


def fetch(url_or_id: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(API.format(share_id(url_or_id)),
                                 headers={"User-Agent": UA,
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _text_of(msg: dict) -> str:
    """The human-readable text of one message, whatever shape it is in.

    content.parts holds strings for ordinary messages but dicts for
    multimodal ones, and some message types use content.text instead. Taking
    parts[0] blindly raises on the first image in a conversation.
    """
    c = msg.get("content") or {}
    parts = c.get("parts")
    if isinstance(parts, list):
        out = []
        for p in parts:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, dict):
                out.append(p.get("text") or p.get("content") or "")
        return "\n".join(x for x in out if x)
    return c.get("text") or ""


def extract(doc: dict, keep_all: bool = False,
            min_chars: int = 1) -> list[dict]:
    """[{role, text}] in conversation order.

    Ordered by create_time, NOT by dict order: `mapping` is a tree keyed by
    uuid and its iteration order is insertion order, which is close to but not
    the same as chronological once a message has been edited or regenerated.
    Nodes with no timestamp sort last rather than raising.
    """
    mapping = doc.get("mapping") or {}
    nodes = [n for n in mapping.values() if isinstance(n, dict) and n.get("message")]
    nodes.sort(key=lambda n: (n["message"].get("create_time") is None,
                              n["message"].get("create_time") or 0))
    out = []
    for n in nodes:
        msg = n["message"]
        role = ((msg.get("author") or {}).get("role") or "").lower()
        chan = (msg.get("author") or {}).get("name") or ""
        meta_chan = (msg.get("metadata") or {}).get("message_type") or ""
        if not keep_all:
            if role not in ("user", "assistant"):
                continue
            if (msg.get("channel") or "") in _INTERNAL_CHANNELS:
                continue
            if chan or meta_chan == "tool":
                continue
        text = _text_of(msg).strip()
        if len(text) < min_chars:
            continue
        # A tool call serialised as an assistant message is JSON, not prose.
        if not keep_all and text[:1] in "{[" and text[-1:] in "}]":
            try:
                json.loads(text)
                continue
            except ValueError:
                pass
        out.append({"role": role, "text": text})
    return out


def render(doc: dict, turns: list[dict]) -> str:
    head = f"# {doc.get('title') or 'ChatGPT conversation'}\n"
    body = "\n\n".join(f"## {t['role']}\n\n{t['text']}" for t in turns)
    return head + "\n" + body + "\n"


# --------------------------------------------------------------- MCP server

def serve() -> None:
    from mcp.server.fastmcp import FastMCP           # noqa: PLC0415
    mcp = FastMCP("chatgpt-share")

    @mcp.tool()
    def read_chatgpt_share(url: str, keep_all: bool = False,
                           max_chars: int = 120000) -> str:
        """Read a public ChatGPT share link and return it as plain text.

        url: the share link, or just its id.
        keep_all: include tool calls, system messages and reasoning too.
        max_chars: truncate the result rather than flooding the caller.
        """
        doc = fetch(url)
        turns = extract(doc, keep_all=keep_all)
        text = render(doc, turns)
        if len(text) > max_chars:
            text = (text[:max_chars]
                    + f"\n\n[truncated at {max_chars} of {len(text)} chars; "
                      f"{len(turns)} turns total]")
        return text

    mcp.run()


# ------------------------------------------------------------------- tests

def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\nthe share id is found in every form the link gets pasted in")
    want = "6a7899f0-4bf4-83e8-8d0a-775007d6d9e5"
    for form in (want,
                 f"https://chatgpt.com/share/{want}",
                 f"https://chatgpt.com/share/e/{want}",
                 f"  https://chatgpt.com/share/{want}?utm=x  "):
        ck(share_id(form) == want, f"...{form[-22:]}")
    try:
        share_id("https://example.com/nope")
        ck(False, "a link with no id raises")
    except ValueError:
        ck(True, "a link with no id raises rather than fetching nonsense")

    print("\nmessages come back in conversation order, not dict order")
    doc = {"title": "T", "mapping": {
        "c": {"message": {"create_time": 3, "author": {"role": "assistant"},
                          "content": {"parts": ["third"]}}},
        "a": {"message": {"create_time": 1, "author": {"role": "user"},
                          "content": {"parts": ["first"]}}},
        "b": {"message": {"create_time": 2, "author": {"role": "assistant"},
                          "content": {"parts": ["second"]}}},
    }}
    got = [t["text"] for t in extract(doc)]
    ck(got == ["first", "second", "third"], f"sorted by create_time ({got})")

    print("\nthe noise that made this hard to read by hand is dropped")
    noisy = {"title": "T", "mapping": {
        "1": {"message": {"create_time": 1, "author": {"role": "system"},
                          "content": {"parts": ["you are chatgpt"]}}},
        "2": {"message": {"create_time": 2, "author": {"role": "tool"},
                          "content": {"parts": ["tool output"]}}},
        "3": {"message": {"create_time": 3, "author": {"role": "assistant"},
                          "content": {"parts": ['{"query":"a tool call"}']}}},
        "4": {"message": {"create_time": 4, "author": {"role": "assistant"},
                          "channel": "analysis",
                          "content": {"parts": ["thinking out loud"]}}},
        "5": {"message": {"create_time": 5, "author": {"role": "assistant"},
                          "content": {"parts": ["the actual answer"]}}},
    }}
    kept = extract(noisy)
    ck([t["text"] for t in kept] == ["the actual answer"],
       f"system, tool, JSON tool-calls and reasoning all dropped ({kept})")
    ck(len(extract(noisy, keep_all=True)) == 5,
       "--all keeps every one of them for when that is what you want")

    print("\nmessage shapes that used to raise are handled")
    odd = {"mapping": {
        "1": {"message": {"create_time": 1, "author": {"role": "user"},
                          "content": {"parts": [{"text": "multimodal part"}]}}},
        "2": {"message": {"create_time": 2, "author": {"role": "assistant"},
                          "content": {"text": "content.text instead of parts"}}},
        "3": {"message": {"create_time": 3, "author": {"role": "user"},
                          "content": {"parts": []}}},
        "4": {"no_message": True},
        "5": {"message": {"author": {"role": "user"},
                          "content": {"parts": ["no timestamp"]}}},
    }}
    got = [t["text"] for t in extract(odd)]
    ck("multimodal part" in got, "a dict part yields its text")
    ck("content.text instead of parts" in got, "content.text is read")
    ck(got[-1] == "no timestamp", "a message with no timestamp sorts last")
    ck(len(got) == 3, f"empty parts and non-messages are skipped ({got})")
    ck(extract({}) == [], "an empty document yields nothing rather than raising")

    print("\nrendering is plain text a human can read")
    out = render({"title": "My chat"}, [{"role": "user", "text": "hi"}])
    ck(out.startswith("# My chat"), "the title leads")
    ck("## user" in out and "hi" in out, "each turn is labelled with its role")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="share link or id")
    ap.add_argument("--all", action="store_true",
                    help="keep tool calls, system messages and reasoning")
    ap.add_argument("--file", help="parse a saved JSON body instead of fetching")
    ap.add_argument("--json", action="store_true", help="emit JSON turns")
    ap.add_argument("--serve", action="store_true", help="run as an MCP server")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.serve:
        serve()
        return 0
    if a.file:
        doc = json.loads(Path(a.file).read_text(encoding="utf-8"))
    elif a.url:
        try:
            doc = fetch(a.url)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} from the share endpoint. A private or "
                  f"deleted share returns 404; check the link is still shared.",
                  file=sys.stderr)
            return 2
        except (urllib.error.URLError, ValueError) as e:
            print(f"could not read the share: {e}", file=sys.stderr)
            return 2
    else:
        ap.error("give a url, --file, --serve or --self-test")

    turns = extract(doc, keep_all=a.all)
    if a.json:
        print(json.dumps({"title": doc.get("title"), "turns": turns}, indent=2))
    else:
        print(render(doc, turns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
