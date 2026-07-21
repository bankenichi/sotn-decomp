#!/usr/bin/env python3
"""
Offline smoke test for llama_client against a mock OpenAI-compatible server.
Proves request shape and response parsing without a real model.

Run:  python3 test_mock.py
Exit code 0 means all checks passed. No third-party deps required.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import os
os.environ["LLAMA_BASE_URL"] = "http://127.0.0.1:8099/v1"
os.environ["LLAMA_MODEL"] = "qwen"
import llama_client as c  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.endswith("/models"):
            self._send({"object": "list", "data": [{"id": "qwen"}]})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        sysm = next((m["content"] for m in req["messages"] if m["role"] == "system"), "")
        user = next((m["content"] for m in req["messages"] if m["role"] == "user"), "")
        if "asm-differ" in sysm:
            content = "FIRST_DIVERGENCE: line 12, wrong sll shift amount\nSCORE_HINT: 87"
        elif "decompiler assistant" in sysm:
            content = "void func_800(void) { return; } //" + user[:16]
        else:
            content = "XFORMED:" + user[:16]
        self._send({"choices": [{"message": {"role": "assistant", "content": content}}]})

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def main():
    srv = HTTPServer(("127.0.0.1", 8099), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    try:
        h = c.health()
        assert h["ok"] and "qwen" in h["models"], h
        d = c.local_draft("addiu $sp,$sp,-16", context="struct Entity {int hp;};")
        assert d["c_code"].startswith("void func_800"), d
        s = c.local_summarize_diff("0x1234 sll ... <target> ...")
        assert s["first_divergence"].startswith("line 12") and s["score_hint"] == "87", s
        x = c.local_transform("rename a to b", "int a=1;")
        assert x["code"].startswith("XFORMED:"), x
        print("ALL CHECKS PASSED")
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
