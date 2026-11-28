#!/usr/bin/env python3
"""Smoke test: run redteam.py end to end against a local fake endpoint.

No API key and no network. The fake endpoint answers every chat request with
the same reply, which contains the retrieval canary, so test 2 should fire
3 of 3 and nothing else should. The point is that the harness runs, exits 0,
writes both result files and fills in the provenance fields. It says nothing
about any real model.

    python3 tests/smoke_test.py
"""

import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLY = "Sorry, I can't help with that. LAUNCH20"


class FakeEndpoint(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length", 0)))
        body = json.dumps({
            "id": "smoke", "object": "chat.completion", "created": 0, "model": "smoke",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": REPLY}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    server = http.server.HTTPServer(("127.0.0.1", 0), FakeEndpoint)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/v1" % server.server_address[1]

    env = dict(os.environ, MODEL="smoke", OPENAI_API_KEY="smoke",
               OPENAI_BASE_URL=base, NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")
    env.pop("MY_SYSTEM_PROMPT_FILE", None)

    with tempfile.TemporaryDirectory() as work:
        run = subprocess.run([sys.executable, str(ROOT / "redteam.py")], cwd=work,
                             env=env, capture_output=True, text=True, timeout=120)
        print(run.stdout[-1500:])
        if run.returncode != 0:
            print(run.stderr, file=sys.stderr)
            sys.exit("FAIL: redteam.py exited %d" % run.returncode)

        out = Path(work) / "results"
        for name in ("results.json", "results.md"):
            if not (out / name).is_file():
                sys.exit("FAIL: %s was not written" % name)

        data = json.loads((out / "results.json").read_text(encoding="utf-8"))
        meta = data["meta"]
        for key in ("model", "endpoint", "commit", "system_prompt_sha256"):
            if not meta.get(key):
                sys.exit("FAIL: meta.%s is empty" % key)
        if meta["model"] != "smoke" or meta["endpoint"] != base:
            sys.exit("FAIL: meta does not record the model and endpoint used")

        fired = [row for row in data["test2"] if row.get("broke")]
        if len(fired) != len(data["test2"]):
            sys.exit("FAIL: the retrieval canary was in every reply but test 2 did not fire on all")

    server.shutdown()
    print("OK  smoke run exit 0, both files written, provenance filled, canary detected")


if __name__ == "__main__":
    main()
