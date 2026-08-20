from __future__ import annotations

import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

EXPECTED_KEY = os.environ["FAKE_RECOVERY_REPLAY_AUTOMATION_KEY"]
PORT = int(os.getenv("FAKE_RECOVERY_REPLAY_PORT", "18082"))

ANALYSIS = "65000000-0000-4000-8000-000000000101"
REPORT = "65000000-0000-4000-8000-000000000102"
REFUND = "65000000-0000-4000-8000-000000000103"
DELIVERY = "65000000-0000-4000-8000-000000000104"

LOCK = threading.Lock()
STATE = {
    ANALYSIS: {"advance_calls": 0, "deliver_calls": 0, "delivery_effects": 0, "analysis_identity_mints": 1},
    REPORT: {"advance_calls": 0, "deliver_calls": 0, "delivery_effects": 0, "analysis_identity_mints": 1},
    REFUND: {"stage": 0, "advance_calls": 0, "pending_reads": 0, "refund_effects": 0, "response_loss_injected": 0},
    DELIVERY: {"deliver_calls": 0, "delivery_effects": 0, "provider_uncertain_observations": 0},
}
REQUESTS: list[dict[str, object]] = []


def status(order_id, order_state, payment_state, fulfillment_state, retryable, terminal, next_action):
    return {
        "api_version": "v1",
        "order_id": order_id,
        "order_state": order_state,
        "payment_state": payment_state,
        "fulfillment_state": fulfillment_state,
        "retryable": retryable,
        "terminal": terminal,
        "next_action": next_action,
    }


def projection(order_id, *, from_get: bool = False):
    row = STATE[order_id]
    if order_id == ANALYSIS:
        if row["deliver_calls"]:
            return status(order_id, "fulfilled", "paid", "completed", False, True, "none")
        if row["advance_calls"] < 7:
            return status(order_id, "fulfillment_in_progress", "paid", "analysis_pending", True, False, "advance")
        return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")
    if order_id == REPORT:
        if row["deliver_calls"]:
            return status(order_id, "fulfilled", "paid", "completed", False, True, "none")
        if row["advance_calls"] < 7:
            return status(order_id, "fulfillment_in_progress", "paid", "report_pending", True, False, "advance")
        return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")
    if order_id == REFUND:
        if row["stage"] == 0:
            return status(order_id, "fulfillment_in_progress", "paid", "analysis_failed", True, False, "refund")
        reads = row["pending_reads"]
        if from_get:
            row["pending_reads"] = reads + 1
        if reads < 6:
            return status(order_id, "fulfillment_in_progress", "refund_pending", "analysis_failed", True, False, "wait")
        return status(order_id, "refunded", "refunded", "analysis_failed", False, True, "none")
    if order_id == DELIVERY:
        if row["deliver_calls"] < 7:
            return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")
        return status(order_id, "fulfilled", "paid", "completed", False, True, "none")
    raise KeyError(order_id)


def record(method, path, body_len, auth_valid, outcome="normal"):
    REQUESTS.append({
        "method": method,
        "path": path,
        "body_len": body_len,
        "auth_valid": auth_valid,
        "outcome": outcome,
        "at_monotonic": round(time.monotonic(), 6),
    })


class Handler(BaseHTTPRequestHandler):
    server_version = "SiteScoreRecoveryReplayCommerce/1"

    def log_message(self, fmt, *args):
        return

    def _json(self, code, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _auth(self):
        return self.headers.get("Authorization") == f"Bearer {EXPECTED_KEY}"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/__stats":
            with LOCK:
                payload = {"state": json.loads(json.dumps(STATE)), "requests": list(REQUESTS), "projections": {oid: projection(oid, from_get=False) for oid in STATE}}
            self._json(200, payload)
            return
        prefix = "/v1/automation/orders/"
        if not parsed.path.startswith(prefix):
            self._json(404, {"error": "not_found"}); return
        order_id = parsed.path[len(prefix):]
        valid = self._auth()
        with LOCK:
            record("GET", parsed.path, 0, valid)
            if not valid:
                self._json(401, {"error": "unauthorized"}); return
            try:
                payload = projection(order_id, from_get=(order_id == REFUND and STATE[order_id]["stage"] == 1))
            except KeyError:
                self._json(404, {"error": "not_found"}); return
        self._json(200, payload)

    def do_POST(self):
        parsed = urlparse(self.path)
        prefix = "/v1/automation/orders/"
        if not parsed.path.startswith(prefix):
            self._json(404, {"error": "not_found"}); return
        if parsed.path.endswith("/advance"):
            operation = "advance"; order_id = parsed.path[len(prefix):-len("/advance")]
        elif parsed.path.endswith("/deliver"):
            operation = "deliver"; order_id = parsed.path[len(prefix):-len("/deliver")]
        else:
            self._json(404, {"error": "not_found"}); return
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        valid = self._auth()
        with LOCK:
            if order_id not in STATE:
                record("POST", parsed.path, len(body), valid, "unknown"); self._json(404, {"error": "not_found"}); return
            if not valid:
                record("POST", parsed.path, len(body), valid, "unauthorized"); self._json(401, {"error": "unauthorized"}); return
            if body not in {b"", b"{}"}:
                record("POST", parsed.path, len(body), valid, "invalid_body"); self._json(400, {"error": "body_must_be_empty"}); return
            row = STATE[order_id]
            if operation == "advance" and order_id in {ANALYSIS, REPORT}:
                row["advance_calls"] += 1
                record("POST", parsed.path, len(body), valid)
                payload = projection(order_id)
            elif operation == "advance" and order_id == REFUND:
                row["advance_calls"] += 1
                if row["stage"] == 0:
                    row["stage"] = 1; row["refund_effects"] += 1
                    if row["response_loss_injected"] == 0:
                        row["response_loss_injected"] = 1
                        record("POST", parsed.path, len(body), valid, "response_loss_after_refund_effect")
                        try:
                            self.connection.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                        self.connection.close()
                        return
                record("POST", parsed.path, len(body), valid)
                payload = projection(order_id)
            elif operation == "deliver" and order_id in {ANALYSIS, REPORT, DELIVERY}:
                row["deliver_calls"] += 1
                if order_id == DELIVERY and row["deliver_calls"] < 7:
                    row["provider_uncertain_observations"] += 1
                if row["deliver_calls"] >= 7 and row.get("delivery_effects", 0) == 0:
                    row["delivery_effects"] = 1
                record("POST", parsed.path, len(body), valid)
                payload = projection(order_id)
            else:
                record("POST", parsed.path, len(body), valid, "wrong_operation"); self._json(409, {"error": "wrong_operation"}); return
        self._json(200, payload)


if __name__ == "__main__":
    # Host-side probes use loopback while the pinned n8n container reaches this
    # fake Commerce boundary through host.docker.internal/host-gateway.
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
