from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = os.getenv("FAKE_COMMERCE_HOST", "0.0.0.0")
PORT = int(os.getenv("FAKE_COMMERCE_PORT", "18080"))
EXPECTED_KEY = os.environ["FAKE_COMMERCE_AUTOMATION_KEY"]
LOG_PATH = Path(os.getenv("FAKE_COMMERCE_LOG_FILE", "/tmp/sitescore-fake-commerce.jsonl"))

DELIVERY = "00000000-0000-4000-8000-000000000001"
ADVANCE = "00000000-0000-4000-8000-000000000002"
NOT_SCORE_READY = "00000000-0000-4000-8000-000000000003"
ANALYSIS_FAILED = "00000000-0000-4000-8000-000000000004"
ANALYSIS_TIMED_OUT = "00000000-0000-4000-8000-000000000005"
REPORT_FAILED = "00000000-0000-4000-8000-000000000006"
ANALYSIS_PENDING = "00000000-0000-4000-8000-000000000007"
ATTENTION = "00000000-0000-4000-8000-000000000008"
EXPIRED = "00000000-0000-4000-8000-000000000009"
REFUND_PENDING = "00000000-0000-4000-8000-000000000010"
ANALYSIS_RUNNING = "00000000-0000-4000-8000-000000000011"
PERMANENT_ADVANCE = "00000000-0000-4000-8000-000000000012"
HTTP_5XX = "00000000-0000-4000-8000-000000000013"
UNCERTAIN_RESPONSE = "00000000-0000-4000-8000-000000000014"
RESTART_ADVANCE = "00000000-0000-4000-8000-000000000015"
DUPLICATE_ADVANCE = "00000000-0000-4000-8000-000000000016"
DELIVERY_RETRY = "00000000-0000-4000-8000-000000000017"
DELIVERY_FAILED = "00000000-0000-4000-8000-000000000018"

LOCK = threading.Lock()
STATE = {
    DELIVERY: {"deliver_calls": 0, "delivery_effects": 0},
    ADVANCE: {"stage": 0, "logical_effects": 0, "deliver_calls": 0, "delivery_effects": 0},
    NOT_SCORE_READY: {"stage": 0, "logical_effects": 0},
    ANALYSIS_FAILED: {"stage": 0, "logical_effects": 0},
    ANALYSIS_TIMED_OUT: {"stage": 0, "logical_effects": 0},
    REPORT_FAILED: {"stage": 0, "logical_effects": 0},
    REFUND_PENDING: {"stage": 0, "pending_reads": 0, "logical_effects": 0},
    ANALYSIS_PENDING: {"advance_calls": 0, "analysis_identity_mints": 1, "deliver_calls": 0, "delivery_effects": 0},
    ANALYSIS_RUNNING: {"advance_calls": 0, "analysis_identity_mints": 1, "deliver_calls": 0, "delivery_effects": 0},
    PERMANENT_ADVANCE: {"advance_calls": 0, "analysis_identity_mints": 1},
    HTTP_5XX: {"stage": 0, "logical_effects": 0, "get_5xx_remaining": 1, "get_5xx_injected": 0, "deliver_calls": 0, "delivery_effects": 0},
    UNCERTAIN_RESPONSE: {"stage": 0, "logical_effects": 0, "uncertain_post_injected": 0, "deliver_calls": 0, "delivery_effects": 0},
    RESTART_ADVANCE: {"advance_calls": 0, "analysis_identity_mints": 1, "deliver_calls": 0, "delivery_effects": 0},
    DUPLICATE_ADVANCE: {"advance_calls": 0, "analysis_identity_mints": 1, "deliver_calls": 0, "delivery_effects": 0},
    DELIVERY_RETRY: {"deliver_calls": 0, "delivery_effects": 0},
    DELIVERY_FAILED: {"deliver_calls": 0, "delivery_effects": 0},
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


def delivery_projection(order_id):
    row=STATE.get(order_id,{})
    calls=int(row.get("deliver_calls",0))
    if order_id == DELIVERY_RETRY:
        if calls < 2:
            return status(order_id,"fulfillment_in_progress","paid","delivery_pending",True,False,"delivery")
        return status(order_id,"fulfilled","paid","completed",False,True,"none")
    if order_id == DELIVERY_FAILED:
        if calls == 0:
            return status(order_id,"fulfillment_in_progress","paid","delivery_pending",True,False,"delivery")
        return status(order_id,"attention_required","paid","delivery_failed",False,False,"none")
    if "deliver_calls" in row and calls > 0:
        return status(order_id,"fulfilled","paid","completed",False,True,"none")
    return None


def projection(order_id):
    delivered=delivery_projection(order_id)
    if delivered is not None:
        if order_id in {DELIVERY_RETRY,DELIVERY_FAILED} or STATE[order_id].get("deliver_calls",0)>0:
            return delivered
    if order_id == DELIVERY:
        return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")
    if order_id == ATTENTION:
        return status(order_id, "attention_required", "paid", "analysis_failed", False, True, "none")
    if order_id == EXPIRED:
        return status(order_id, "expired", "expired", "not_started", False, True, "none")
    if order_id == ADVANCE:
        row = STATE[order_id]
        return status(order_id, "fulfillment_in_progress", "paid", "not_started" if row["stage"] == 0 else "delivery_pending", row["stage"] == 0, False, "advance" if row["stage"] == 0 else "delivery")

    refund_states = {
        NOT_SCORE_READY: "not_score_ready",
        ANALYSIS_FAILED: "analysis_failed",
        ANALYSIS_TIMED_OUT: "analysis_timed_out",
        REPORT_FAILED: "report_failed",
    }
    if order_id in refund_states:
        row = STATE[order_id]
        if row["stage"] == 0:
            return status(order_id, "fulfillment_in_progress", "paid", refund_states[order_id], True, False, "refund")
        return status(order_id, "refunded", "refunded", refund_states[order_id], False, True, "none")

    if order_id == REFUND_PENDING:
        row = STATE[order_id]
        if row["stage"] == 0:
            return status(order_id, "fulfillment_in_progress", "paid", "analysis_failed", True, False, "refund")
        reads = row["pending_reads"]
        row["pending_reads"] = reads + 1
        if reads < 2:
            return status(order_id, "fulfillment_in_progress", "refund_pending", "analysis_failed", True, False, "wait")
        return status(order_id, "refunded", "refunded", "analysis_failed", False, True, "none")

    if order_id == ANALYSIS_PENDING:
        calls = STATE[order_id]["advance_calls"]
        if calls < 3:
            return status(order_id, "fulfillment_in_progress", "paid", "analysis_pending", True, False, "advance")
        return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")

    if order_id == ANALYSIS_RUNNING:
        calls = STATE[order_id]["advance_calls"]
        if calls < 3:
            return status(order_id, "fulfillment_in_progress", "paid", "analysis_running", True, False, "advance")
        if calls == 3:
            return status(order_id, "fulfillment_in_progress", "paid", "report_pending", True, False, "advance")
        return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")

    if order_id == PERMANENT_ADVANCE:
        return status(order_id, "fulfillment_in_progress", "paid", "analysis_running", True, False, "advance")

    if order_id == RESTART_ADVANCE:
        calls = STATE[order_id]["advance_calls"]
        if calls < 3:
            return status(order_id, "fulfillment_in_progress", "paid", "analysis_running", True, False, "advance")
        return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")

    if order_id == DUPLICATE_ADVANCE:
        calls = STATE[order_id]["advance_calls"]
        if calls < 3:
            return status(order_id, "fulfillment_in_progress", "paid", "analysis_running", True, False, "advance")
        return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")

    if order_id in {HTTP_5XX, UNCERTAIN_RESPONSE}:
        row = STATE[order_id]
        if row["stage"] == 0:
            return status(order_id, "fulfillment_in_progress", "paid", "analysis_running", True, False, "advance")
        return status(order_id, "fulfillment_in_progress", "paid", "delivery_pending", True, False, "delivery")

    if order_id in {DELIVERY_RETRY,DELIVERY_FAILED}:
        return delivery_projection(order_id)
    raise KeyError(order_id)


def advance(order_id):
    if order_id in {ADVANCE, NOT_SCORE_READY, ANALYSIS_FAILED, ANALYSIS_TIMED_OUT, REPORT_FAILED, REFUND_PENDING, HTTP_5XX, UNCERTAIN_RESPONSE}:
        row = STATE[order_id]
        if row["stage"] == 0:
            row["logical_effects"] += 1
            row["stage"] = 1
        return projection(order_id)
    if order_id in {ANALYSIS_PENDING, ANALYSIS_RUNNING, PERMANENT_ADVANCE, RESTART_ADVANCE, DUPLICATE_ADVANCE}:
        STATE[order_id]["advance_calls"] += 1
        return projection(order_id)
    raise KeyError(order_id)


def deliver(order_id):
    if order_id not in STATE or "deliver_calls" not in STATE[order_id]:
        raise KeyError(order_id)
    row=STATE[order_id]
    row["deliver_calls"] += 1
    if order_id == DELIVERY_RETRY and row["deliver_calls"] < 2:
        return projection(order_id)
    if row.get("delivery_effects",0)==0:
        row["delivery_effects"] = 1
    return projection(order_id)


def record(method, path, body_len, auth_valid, outcome="normal"):
    item = {
        "method": method,
        "path": path,
        "body_len": body_len,
        "auth_valid": auth_valid,
        "outcome": outcome,
        "at_monotonic": round(time.monotonic(), 6),
    }
    REQUESTS.append(item)
    with LOG_PATH.open("a") as handle:
        handle.write(json.dumps(item, sort_keys=True) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "SiteScoreFakeCommerce/3"

    def log_message(self, fmt, *args): return

    def json_response(self, code, payload):
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers()
        try: self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError): pass

    def auth_valid(self): return self.headers.get("Authorization") == f"Bearer {EXPECTED_KEY}"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/__stats":
            with LOCK:
                payload = {
                    "requests": list(REQUESTS),
                    "logical_effects": {k: v.get("logical_effects", 0) for k, v in STATE.items()},
                    "delivery_effects": {k: v.get("delivery_effects", 0) for k, v in STATE.items()},
                    "state": json.loads(json.dumps(STATE)),
                }
            self.json_response(200, payload); return
        prefix = "/v1/automation/orders/"
        if not parsed.path.startswith(prefix): self.json_response(404,{"error":"not_found"}); return
        order_id = parsed.path[len(prefix):]; valid=self.auth_valid()
        with LOCK:
            if order_id == HTTP_5XX and STATE[order_id]["get_5xx_remaining"] > 0 and valid:
                STATE[order_id]["get_5xx_remaining"] -= 1; STATE[order_id]["get_5xx_injected"] += 1
                record("GET",parsed.path,0,valid,"injected_5xx"); self.json_response(500,{"error":"temporary_failure"}); return
            record("GET",parsed.path,0,valid)
            if not valid: self.json_response(401,{"error":"unauthorized"}); return
            try: payload=projection(order_id)
            except KeyError: self.json_response(404,{"error":"not_found"}); return
        self.json_response(200,payload)

    def do_POST(self):
        parsed=urlparse(self.path); prefix="/v1/automation/orders/"
        if not parsed.path.startswith(prefix): self.json_response(404,{"error":"not_found"}); return
        operation=None
        if parsed.path.endswith("/advance"): operation="advance"; order_id=parsed.path[len(prefix):-len("/advance")]
        elif parsed.path.endswith("/deliver"): operation="deliver"; order_id=parsed.path[len(prefix):-len("/deliver")]
        else: self.json_response(404,{"error":"not_found"}); return
        length=int(self.headers.get("Content-Length","0") or "0"); body=self.rfile.read(length) if length else b""; valid=self.auth_valid()
        if not valid:
            with LOCK: record("POST",parsed.path,len(body),valid)
            self.json_response(401,{"error":"unauthorized"}); return
        if body not in {b"",b"{}"}:
            with LOCK: record("POST",parsed.path,len(body),valid,"invalid_body")
            self.json_response(400,{"error":"body_must_be_empty"}); return
        uncertain=False
        with LOCK:
            try: payload=advance(order_id) if operation=="advance" else deliver(order_id)
            except KeyError:
                record("POST",parsed.path,len(body),valid,"not_found"); self.json_response(404,{"error":"not_found"}); return
            if operation=="advance" and order_id==UNCERTAIN_RESPONSE and STATE[order_id]["uncertain_post_injected"]==0:
                STATE[order_id]["uncertain_post_injected"]=1; uncertain=True; record("POST",parsed.path,len(body),valid,"accepted_response_delayed")
            else: record("POST",parsed.path,len(body),valid)
        if uncertain: time.sleep(11.0)
        self.json_response(200,payload)


if __name__ == "__main__":
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True); LOG_PATH.write_text("")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
