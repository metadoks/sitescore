from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

TOKEN = os.environ["FAKE_RECOVERY_AUTOMATION_KEY"]
LOCK = threading.Lock()
REQUESTS: list[dict[str, object]] = []


class Handler(BaseHTTPRequestHandler):
    server_version = "SiteScoreFakeRecovery/1"

    def log_message(self, fmt, *args):
        return

    def _json(self, code: int, payload: object):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path != "/__stats":
            self._json(404, {"error": "not_found"})
            return
        with LOCK:
            payload = {"requests": list(REQUESTS)}
        self._json(200, payload)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        valid = self.headers.get("Authorization") == f"Bearer {TOKEN}"
        with LOCK:
            REQUESTS.append(
                {
                    "method": "POST",
                    "path": parsed.path,
                    "body_len": len(body),
                    "auth_valid": valid,
                    "at_monotonic": time.monotonic(),
                }
            )
        if parsed.path != "/v1/automation/recovery/run":
            self._json(404, {"error": "not_found"})
            return
        if not valid:
            self._json(401, {"error": "automation_unauthorized"})
            return
        if body:
            self._json(400, {"error": "body_must_be_empty"})
            return
        self._json(
            200,
            {
                "api_version": "2026-08-20",
                "run_id": "65000000-0000-4000-8000-000000000099",
                "claimed": 2,
                "reconciled": 1,
                "published": 0,
                "replayed": 0,
                "deferred": 1,
                "attention": 0,
            },
        )


if __name__ == "__main__":
    # CI keeps probing through 127.0.0.1, while the pinned n8n container reaches
    # the host through host.docker.internal/host-gateway. Listen on all host
    # interfaces so both paths exercise the same fake Commerce recovery server.
    ThreadingHTTPServer(("0.0.0.0", 18081), Handler).serve_forever()
