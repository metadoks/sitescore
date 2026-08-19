from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = os.getenv("FAKE_COMMERCE_HOST", "0.0.0.0")
PORT = int(os.getenv("FAKE_COMMERCE_PORT", "18080"))
EXPECTED_KEY = os.environ["FAKE_COMMERCE_AUTOMATION_KEY"]
LOG_PATH = Path(os.getenv("FAKE_COMMERCE_LOG_FILE", "/tmp/sitescore-fake-commerce.jsonl"))

DELIVERY="00000000-0000-4000-8000-000000000001"; ADVANCE="00000000-0000-4000-8000-000000000002"; NOT_SCORE_READY="00000000-0000-4000-8000-000000000003"; ANALYSIS_FAILED="00000000-0000-4000-8000-000000000004"; ANALYSIS_TIMED_OUT="00000000-0000-4000-8000-000000000005"; REPORT_FAILED="00000000-0000-4000-8000-000000000006"; WAIT="00000000-0000-4000-8000-000000000007"; ATTENTION="00000000-0000-4000-8000-000000000008"; EXPIRED="00000000-0000-4000-8000-000000000009"; REFUND_PENDING="00000000-0000-4000-8000-000000000010"
LOCK=threading.Lock()
STATE={ADVANCE:{"stage":0,"logical_effects":0},NOT_SCORE_READY:{"stage":0,"logical_effects":0},ANALYSIS_FAILED:{"stage":0,"logical_effects":0},ANALYSIS_TIMED_OUT:{"stage":0,"logical_effects":0},REPORT_FAILED:{"stage":0,"logical_effects":0},WAIT:{"get_reads":0,"logical_effects":0},REFUND_PENDING:{"stage":0,"pending_reads":0,"logical_effects":0}}
REQUESTS=[]

def status(order_id,order_state,payment_state,fulfillment_state,retryable,terminal,next_action):
    return {"api_version":"v1","order_id":order_id,"order_state":order_state,"payment_state":payment_state,"fulfillment_state":fulfillment_state,"retryable":retryable,"terminal":terminal,"next_action":next_action}

def projection(order_id):
    if order_id==DELIVERY: return status(order_id,"paid","paid","delivery_pending",False,False,"delivery")
    if order_id==ATTENTION: return status(order_id,"attention_required","paid","analysis_failed",False,True,"none")
    if order_id==EXPIRED: return status(order_id,"expired","expired","not_started",False,True,"none")
    if order_id==ADVANCE:
        return status(order_id,"paid","paid","not_started" if STATE[order_id]["stage"]==0 else "delivery_pending",STATE[order_id]["stage"]==0,False,"advance" if STATE[order_id]["stage"]==0 else "delivery")
    refund_states={NOT_SCORE_READY:"not_score_ready",ANALYSIS_FAILED:"analysis_failed",ANALYSIS_TIMED_OUT:"analysis_timed_out",REPORT_FAILED:"report_failed"}
    if order_id in refund_states:
        if STATE[order_id]["stage"]==0: return status(order_id,"paid","paid",refund_states[order_id],True,False,"refund")
        return status(order_id,"refunded","refunded",refund_states[order_id],False,True,"none")
    if order_id==WAIT:
        reads=STATE[order_id]["get_reads"]; STATE[order_id]["get_reads"]=reads+1
        if reads<2: return status(order_id,"paid","paid","analysis_running",True,False,"wait")
        return status(order_id,"paid","paid","delivery_pending",False,False,"delivery")
    if order_id==REFUND_PENDING:
        row=STATE[order_id]
        if row["stage"]==0: return status(order_id,"paid","paid","analysis_failed",True,False,"refund")
        reads=row["pending_reads"]; row["pending_reads"]=reads+1
        if reads<2: return status(order_id,"paid","refund_pending","analysis_failed",True,False,"wait")
        return status(order_id,"refunded","refunded","analysis_failed",False,True,"none")
    raise KeyError(order_id)

def advance(order_id):
    if order_id in {ADVANCE,NOT_SCORE_READY,ANALYSIS_FAILED,ANALYSIS_TIMED_OUT,REPORT_FAILED,REFUND_PENDING}:
        row=STATE[order_id]
        if row["stage"]==0: row["logical_effects"]+=1; row["stage"]=1
    return projection(order_id)

def record(method,path,body_len,auth_valid):
    item={"method":method,"path":path,"body_len":body_len,"auth_valid":auth_valid}; REQUESTS.append(item)
    with LOG_PATH.open("a") as handle: handle.write(json.dumps(item,sort_keys=True)+"\n")

class Handler(BaseHTTPRequestHandler):
    server_version="SiteScoreFakeCommerce/1"
    def log_message(self,fmt,*args): return
    def json_response(self,code,payload):
        body=json.dumps(payload,separators=(",",":")).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def auth_valid(self): return self.headers.get("Authorization")==f"Bearer {EXPECTED_KEY}"
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=="/__stats":
            with LOCK: payload={"requests":list(REQUESTS),"logical_effects":{k:v.get("logical_effects",0) for k,v in STATE.items()},"state":STATE}
            self.json_response(200,payload); return
        prefix="/v1/automation/orders/"
        if not parsed.path.startswith(prefix): self.json_response(404,{"error":"not_found"}); return
        order_id=parsed.path[len(prefix):]; valid=self.auth_valid(); record("GET",parsed.path,0,valid)
        if not valid: self.json_response(401,{"error":"unauthorized"}); return
        try:
            with LOCK: payload=projection(order_id)
        except KeyError: self.json_response(404,{"error":"not_found"}); return
        self.json_response(200,payload)
    def do_POST(self):
        parsed=urlparse(self.path); prefix="/v1/automation/orders/"
        if not parsed.path.startswith(prefix) or not parsed.path.endswith("/advance"): self.json_response(404,{"error":"not_found"}); return
        order_id=parsed.path[len(prefix):-len("/advance")]; length=int(self.headers.get("Content-Length","0") or "0"); body=self.rfile.read(length) if length else b""; valid=self.auth_valid(); record("POST",parsed.path,len(body),valid)
        if not valid: self.json_response(401,{"error":"unauthorized"}); return
        if body not in {b"",b"{}"}: self.json_response(400,{"error":"body_must_be_empty"}); return
        try:
            with LOCK: payload=advance(order_id)
        except KeyError: self.json_response(404,{"error":"not_found"}); return
        self.json_response(200,payload)

if __name__=="__main__":
    LOG_PATH.parent.mkdir(parents=True,exist_ok=True); LOG_PATH.write_text(""); ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
