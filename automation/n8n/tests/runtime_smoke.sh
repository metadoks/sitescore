#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKFLOW="$ROOT/automation/n8n/workflows/sitescore-order-paid-v1.json"
FAKE_SERVER="$ROOT/automation/n8n/tests/fake_commerce_server.py"
IMAGE="n8nio/n8n:2.33.4"
RUN_TOKEN="${GITHUB_RUN_ID:-local}-$$"
VOLUME="sitescore-n8n64-${RUN_TOKEN}"
CONTAINER="sitescore-n8n64-${RUN_TOKEN}"
TMP_DIR="$(mktemp -d)"; EXPORT_DIR="$TMP_DIR/export"; FAKE_LOG="$TMP_DIR/fake-commerce.jsonl"; RUNTIME_OK=0
mkdir -p "$EXPORT_DIR"; chmod 777 "$EXPORT_DIR"
cleanup(){
  if [[ "$RUNTIME_OK" != "1" ]] && docker inspect "$CONTAINER" >/dev/null 2>&1; then docker logs "$CONTAINER" >&2 || true; fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  if [[ -n "${FAKE_PID:-}" ]]; then kill "$FAKE_PID" >/dev/null 2>&1 || true; fi
  docker volume rm "$VOLUME" >/dev/null 2>&1 || true; rm -rf "$TMP_DIR"
}
trap cleanup EXIT
ENC_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
INGRESS_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
AUTOMATION_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
OWNER_PASSWORD="$(python -c 'import secrets; print("A9!"+secrets.token_urlsafe(28))')"
for secret in "$ENC_KEY" "$INGRESS_SECRET" "$AUTOMATION_KEY" "$OWNER_PASSWORD"; do echo "::add-mask::$secret"; done

docker pull "$IMAGE" >/dev/null
VERSION="$(docker run --rm "$IMAGE" --version | tail -n1 | tr -d '\r')"; test "$VERSION" = "2.33.4"
DIGEST="$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"; case "$DIGEST" in n8nio/n8n@sha256:*) ;; *) exit 1;; esac
echo "N8N_RUNTIME_VERSION=$VERSION"; echo "N8N_VALIDATED_IMAGE_DIGEST=$DIGEST"; echo "WORKFLOW_SHA256=$(sha256sum "$WORKFLOW" | awk '{print $1}')"
docker volume create "$VOLUME" >/dev/null
common_env=(
  -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_HOST=0.0.0.0 -e N8N_PORT=5678 -e N8N_PROTOCOL=http
  -e N8N_WEBHOOK_URL=http://127.0.0.1:5678/ -e N8N_SECURE_COOKIE=false -e N8N_DIAGNOSTICS_ENABLED=false
  -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -e N8N_PERSONALIZATION_ENABLED=false -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false
  -e N8N_USE_WORKFLOW_PUBLICATION_SERVICE=false -e EXECUTIONS_DATA_SAVE_ON_ERROR=none -e EXECUTIONS_DATA_SAVE_ON_SUCCESS=none
  -e COMMERCE_N8N_INGRESS_SECRET="$INGRESS_SECRET" -e COMMERCE_AUTOMATION_API_KEY="$AUTOMATION_KEY"
  -e SITESCORE_COMMERCE_AUTOMATION_BASE_URL=http://host.docker.internal:18080 -e SITESCORE_N8N_POLL_SECONDS=1 -e SITESCORE_N8N_MAX_POLLS=5
)
wait_health(){ for _ in $(seq 1 120); do curl -fsS http://127.0.0.1:5678/healthz >/dev/null 2>&1 && return 0; sleep .5; done; return 1; }

docker run -d --name "$CONTAINER" -p 5678:5678 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/dev/null
wait_health
SETUP_CODE=$(curl -sS -o "$TMP_DIR/owner.body" -w '%{http_code}' -H 'Content-Type: application/json' -X POST http://127.0.0.1:5678/rest/owner/setup -d '{"email":"sitescore-ci-owner@example.test","firstName":"SiteScore","lastName":"CI","password":"'"$OWNER_PASSWORD"'"}')
test "$SETUP_CODE" = 200; echo N8N_INSTANCE_PROVISIONING=PASS
docker stop "$CONTAINER" >/dev/null; docker rm "$CONTAINER" >/dev/null

docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$ROOT/automation/n8n/workflows:/workflows:ro" "$IMAGE" import:workflow --input=/workflows/sitescore-order-paid-v1.json >/tmp/n8n64-import.log
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$EXPORT_DIR:/out" "$IMAGE" export:workflow --all --output=/out/workflows.json >/tmp/n8n64-export.log
WORKFLOW_ID="$(python - "$EXPORT_DIR/workflows.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); items=p if isinstance(p,list) else [p]
m=[x for x in items if x.get('name')=='SiteScore Order Paid Orchestration v1.1.0']; assert len(m)==1,m; assert m[0].get('id')=='sitescoreOrderPaidV1'; print(m[0]['id'])
PY
)"
set +e
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" "$IMAGE" publish:workflow --id="$WORKFLOW_ID" 2>&1 | tee /tmp/n8n64-publish.log
PUBLISH_EXIT=${PIPESTATUS[0]}; set -e; test "$PUBLISH_EXIT" = 0 || test "$PUBLISH_EXIT" = 1
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$EXPORT_DIR:/out" "$IMAGE" export:workflow --id="$WORKFLOW_ID" --output=/out/published.json >/tmp/n8n64-published.log
python - "$EXPORT_DIR/published.json" "$WORKFLOW_ID" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); items=p if isinstance(p,list) else [p]; w=items[0]
assert len(items)==1 and w.get('id')==sys.argv[2] and w.get('active') is True
assert w.get('activeVersionId') and w.get('versionId') and w['activeVersionId']==w['versionId']; print('N8N_PUBLISH_DURABLE_STATE=PASS')
PY

FAKE_COMMERCE_AUTOMATION_KEY="$AUTOMATION_KEY" FAKE_COMMERCE_LOG_FILE="$FAKE_LOG" python "$FAKE_SERVER" >/tmp/n8n64-fake.log 2>&1 & FAKE_PID=$!
for _ in $(seq 1 30); do curl -fsS http://127.0.0.1:18080/__stats >/dev/null 2>&1 && break; sleep .2; done
curl -fsS http://127.0.0.1:18080/__stats >/dev/null
docker run -d --name "$CONTAINER" --add-host=host.docker.internal:host-gateway -p 5678:5678 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/dev/null
wait_health
webhook="http://127.0.0.1:5678/webhook/sitescore-order-paid-v1"
make_payload(){ printf '{"event_id":"%s","event_type":"%s","order_id":"%s","occurred_at":"2026-08-20T00:30:00Z"}' "$1" "${3:-order.paid.v1}" "$2"; }
post_code(){ local auth="$1" payload="$2" output="$TMP_DIR/r-$RANDOM.json"; if [[ "$auth" = __none__ ]]; then curl -sS -o "$output" -w '%{http_code}' -H 'Content-Type: application/json' -X POST "$webhook" -d "$payload"; else curl -sS -o "$output" -w '%{http_code}' -H 'Content-Type: application/json' -H "Authorization: Bearer $auth" -X POST "$webhook" -d "$payload"; fi; }
DELIVERY=00000000-0000-4000-8000-000000000001; ADVANCE=00000000-0000-4000-8000-000000000002
NOT_SCORE_READY=00000000-0000-4000-8000-000000000003; ANALYSIS_FAILED=00000000-0000-4000-8000-000000000004; ANALYSIS_TIMED_OUT=00000000-0000-4000-8000-000000000005; REPORT_FAILED=00000000-0000-4000-8000-000000000006
ANALYSIS_PENDING=00000000-0000-4000-8000-000000000007; ATTENTION=00000000-0000-4000-8000-000000000008; EXPIRED=00000000-0000-4000-8000-000000000009; REFUND_PENDING=00000000-0000-4000-8000-000000000010
ANALYSIS_RUNNING=00000000-0000-4000-8000-000000000011; PERMANENT_ADVANCE=00000000-0000-4000-8000-000000000012; HTTP_5XX=00000000-0000-4000-8000-000000000013; UNCERTAIN_RESPONSE=00000000-0000-4000-8000-000000000014
RESTART_ADVANCE=00000000-0000-4000-8000-000000000015; DUPLICATE_ADVANCE=00000000-0000-4000-8000-000000000016; DELIVERY_RETRY=00000000-0000-4000-8000-000000000017; DELIVERY_FAILED=00000000-0000-4000-8000-000000000018
DELIVERY_RESTART=00000000-0000-4000-8000-000000000019; DELIVERY_PERMANENT_RETRY=00000000-0000-4000-8000-000000000020
READINESS_PAYLOAD="$(make_payload 10000000-0000-4000-8000-00000000aa01 "$DELIVERY")"
wait_webhook_ready(){ local code=000; for _ in $(seq 1 60); do code="$(post_code __none__ "$READINESS_PAYLOAD" || true)"; [[ "$code" = 401 ]] && { echo N8N_PRODUCTION_WEBHOOK_READY=PASS; return 0; }; [[ "$code" = 404 || "$code" = 000 ]] || return 1; sleep 1; done; return 1; }
assert_paced_order(){ python - "$1" "$2" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; minimum=int(sys.argv[2]); d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
posts=[(i,x) for i,x in enumerate(r) if x['method']=='POST']; assert len(posts)>=minimum,(o,r)
for i,p in posts:
    later=next((x for x in r[i+1:] if x['method']=='GET'),None)
    if later is not None: assert later['at_monotonic']-p['at_monotonic']>=.75,(o,p,later,r)
assert all(x['body_len'] in (0,2) for x in r if x['method']=='POST'),(o,r)
PY
}
wait_webhook_ready

test "$(post_code __none__ "$(make_payload e1 "$DELIVERY")")" = 401
test "$(post_code wrong "$(make_payload e2 "$DELIVERY")")" = 401
test "$(post_code "$INGRESS_SECRET" '{"event_type":"order.paid.v1"}')" = 400
python - <<'PY'
import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['requests']==[],d
PY

# FAZ 6.4 delivery: GET authority first, bodyless /deliver, paced GET, then terminal fulfilled.
test "$(post_code "$INGRESS_SECRET" "$(make_payload d1 "$DELIVERY")")" = 202; sleep 3
assert_paced_order "$DELIVERY" 1
python - "$DELIVERY" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert r[0]['method']=='GET',r; posts=[x for x in r if x['method']=='POST']; assert len(posts)==1 and posts[0]['path'].endswith('/deliver') and posts[0]['body_len'] in (0,2),r
assert d['delivery_effects'][o]==1 and d['state'][o]['deliver_calls']==1,d
PY
echo N8N_DELIVERY_ACCEPTED_TO_FULFILLED=PASS

# Retryable delivery remains commerce-owned delivery guidance and is paced before retry.
test "$(post_code "$INGRESS_SECRET" "$(make_payload d2 "$DELIVERY_RETRY")")" = 202; sleep 5
assert_paced_order "$DELIVERY_RETRY" 2
python - "$DELIVERY_RETRY" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
posts=[x for x in r if x['method']=='POST']; assert len(posts)==2 and all(x['path'].endswith('/deliver') for x in posts),r
assert d['delivery_effects'][o]==1,d
PY
echo N8N_DELIVERY_RETRY_PACING=PASS

# Delivery-specific persisted Wait restart: first /deliver leaves commerce authoritative state pending,
# n8n is stopped while waiting, then the same durable n8n volume resumes/converges without /advance.
test "$(post_code "$INGRESS_SECRET" "$(make_payload dr "$DELIVERY_RESTART")")" = 202
DELIVERY_RESTART_CALLS=0
for _ in $(seq 1 50); do
  DELIVERY_RESTART_CALLS="$(python - "$DELIVERY_RESTART" <<'PY'
import json,sys,urllib.request
d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); print(d['state'][sys.argv[1]]['deliver_calls'])
PY
)"
  [[ "$DELIVERY_RESTART_CALLS" = 1 ]] && break
  sleep .1
done
test "$DELIVERY_RESTART_CALLS" = 1
python - "$DELIVERY_RESTART" "$AUTOMATION_KEY" <<'PY'
import json,sys,urllib.request
o,key=sys.argv[1:]
req=urllib.request.Request(f'http://127.0.0.1:18080/v1/automation/orders/{o}',headers={'Authorization':f'Bearer {key}'})
p=json.load(urllib.request.urlopen(req)); assert p['order_id']==o and p['payment_state']=='paid' and p['fulfillment_state']=='delivery_pending' and p['retryable'] is True and p['next_action']=='delivery' and p['terminal'] is False,p
d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert d['delivery_effects'][o]==0 and d['state'][o]['deliver_calls']==1,d
assert set(d['state'][o])=={'deliver_calls','delivery_effects'},d['state'][o]
assert all(not x['path'].endswith('/advance') for x in r),r
PY
docker stop "$CONTAINER" >/dev/null; docker start "$CONTAINER" >/dev/null; wait_health; wait_webhook_ready; sleep 5
assert_paced_order "$DELIVERY_RESTART" 2
python - "$DELIVERY_RESTART" "$AUTOMATION_KEY" <<'PY'
import json,sys,urllib.request
o,key=sys.argv[1:]
d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
posts=[x for x in r if x['method']=='POST']; assert len(posts)==2 and all(x['path'].endswith('/deliver') for x in posts),r
assert d['state'][o]['deliver_calls']==2 and d['delivery_effects'][o]==1,d
assert all(not x['path'].endswith('/advance') for x in r),r
req=urllib.request.Request(f'http://127.0.0.1:18080/v1/automation/orders/{o}',headers={'Authorization':f'Bearer {key}'})
p=json.load(urllib.request.urlopen(req)); assert p['order_id']==o and p['payment_state']=='paid' and p['fulfillment_state']=='completed' and p['order_state']=='fulfilled' and p['next_action']=='none' and p['terminal'] is True,p
PY
echo N8N_DELIVERY_WAIT_RESTART=PASS

# Permanently retryable delivery stays pending and is bounded by the shared finite poll horizon.
test "$(post_code "$INGRESS_SECRET" "$(make_payload dh "$DELIVERY_PERMANENT_RETRY")")" = 202; sleep 8
DELIVERY_BEFORE="$(python - "$DELIVERY_PERMANENT_RETRY" <<'PY'
import json,sys,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); print(d['state'][sys.argv[1]]['deliver_calls'])
PY
)"; sleep 2
DELIVERY_AFTER="$(python - "$DELIVERY_PERMANENT_RETRY" <<'PY'
import json,sys,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); print(d['state'][sys.argv[1]]['deliver_calls'])
PY
)"; test "$DELIVERY_BEFORE" = "$DELIVERY_AFTER"; test "$DELIVERY_AFTER" -ge 5; test "$DELIVERY_AFTER" -le 6
assert_paced_order "$DELIVERY_PERMANENT_RETRY" 5
python - "$DELIVERY_PERMANENT_RETRY" "$AUTOMATION_KEY" <<'PY'
import json,sys,urllib.request
o,key=sys.argv[1:]
d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
posts=[x for x in r if x['method']=='POST']; assert len(posts) in {5,6} and all(x['path'].endswith('/deliver') for x in posts),r
assert d['delivery_effects'][o]==0 and all(not x['path'].endswith('/advance') for x in r),d
req=urllib.request.Request(f'http://127.0.0.1:18080/v1/automation/orders/{o}',headers={'Authorization':f'Bearer {key}'})
p=json.load(urllib.request.urlopen(req)); assert p['payment_state']=='paid' and p['fulfillment_state']=='delivery_pending' and p['next_action']=='delivery' and p['terminal'] is False,p
PY
echo N8N_DELIVERY_POLL_HORIZON=PASS

# Nonretryable delivery failure returns next_action none; n8n cannot fabricate fulfilled.
test "$(post_code "$INGRESS_SECRET" "$(make_payload d3 "$DELIVERY_FAILED")")" = 202; sleep 3
python - "$DELIVERY_FAILED" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert sum(1 for x in r if x['method']=='POST')==1,r; assert d['state'][o]['deliver_calls']==1,d
PY
echo N8N_DELIVERY_FAILED_STOP=PASS

# Existing 6.3 analysis/advance path remains paced, then delivery is also commerce-only.
test "$(post_code "$INGRESS_SECRET" "$(make_payload a1 "$ADVANCE")")" = 202; sleep 4
assert_paced_order "$ADVANCE" 2
python - "$ADVANCE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['logical_effects'][o]==1 and d['delivery_effects'][o]==1,d
PY

test "$(post_code "$INGRESS_SECRET" "$(make_payload a2 "$ANALYSIS_PENDING")")" = 202; sleep 7
assert_paced_order "$ANALYSIS_PENDING" 4
python - "$ANALYSIS_PENDING" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['state'][o]['advance_calls']==3 and d['state'][o]['analysis_identity_mints']==1 and d['delivery_effects'][o]==1,d
PY
echo N8N_REAL_ANALYSIS_PENDING_PACING=PASS

test "$(post_code "$INGRESS_SECRET" "$(make_payload a3 "$ANALYSIS_RUNNING")")" = 202; sleep 8
assert_paced_order "$ANALYSIS_RUNNING" 5
python - "$ANALYSIS_RUNNING" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['state'][o]['advance_calls']==4 and d['state'][o]['analysis_identity_mints']==1 and d['delivery_effects'][o]==1,d
PY
echo N8N_REAL_ANALYSIS_RUNNING_REPORT_PACING=PASS

# Refund, terminal, and duplicate/replay authority remains unchanged.
for o in "$NOT_SCORE_READY" "$ANALYSIS_FAILED" "$ANALYSIS_TIMED_OUT" "$REPORT_FAILED" "$REFUND_PENDING"; do test "$(post_code "$INGRESS_SECRET" "$(make_payload r1 "$o")")" = 202; done
sleep 6
for o in "$ATTENTION" "$EXPIRED"; do test "$(post_code "$INGRESS_SECRET" "$(make_payload t1 "$o")")" = 202; done
DUP="$(make_payload dup "$DUPLICATE_ADVANCE")"; test "$(post_code "$INGRESS_SECRET" "$DUP")" = 202; test "$(post_code "$INGRESS_SECRET" "$DUP")" = 202; test "$(post_code "$INGRESS_SECRET" "$(make_payload dup2 "$DUPLICATE_ADVANCE")")" = 202; sleep 7
python - "$DUPLICATE_ADVANCE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['state'][o]['analysis_identity_mints']==1 and d['state'][o]['advance_calls']>=3 and d['delivery_effects'][o]==1,d
PY
echo N8N_DUPLICATE_REPLAY_CONVERGENCE=PASS

# Restart during persisted Wait still converges through delivery without reminting analytics identity.
test "$(post_code "$INGRESS_SECRET" "$(make_payload rs "$RESTART_ADVANCE")")" = 202; sleep .3; docker stop "$CONTAINER" >/dev/null; docker start "$CONTAINER" >/dev/null; wait_health; wait_webhook_ready; sleep 7
python - "$RESTART_ADVANCE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['state'][o]['advance_calls']==3 and d['state'][o]['analysis_identity_mints']==1 and d['delivery_effects'][o]==1,d
PY
echo N8N_REAL_ADVANCE_WAIT_RESTART=PASS

# Native HTTP retry after commerce 5xx and uncertain accepted /advance still converge.
test "$(post_code "$INGRESS_SECRET" "$(make_payload h5 "$HTTP_5XX")")" = 202; sleep 8
python - "$HTTP_5XX" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['state'][o]['get_5xx_injected']==1 and d['logical_effects'][o]==1,d
PY
echo N8N_COMMERCE_5XX_RECOVERY=PASS

test "$(post_code "$INGRESS_SECRET" "$(make_payload u1 "$UNCERTAIN_RESPONSE")")" = 202; sleep 20
python - "$UNCERTAIN_RESPONSE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]; assert d['state'][o]['uncertain_post_injected']==1 and d['logical_effects'][o]==1 and sum(1 for x in r if x['method']=='POST' and x['path'].endswith('/advance'))>=2,d
PY
echo N8N_COMMERCE_TIMEOUT_REPLAY_CONVERGENCE=PASS

# Finite horizon remains intact for permanently nonterminal advance.
test "$(post_code "$INGRESS_SECRET" "$(make_payload p1 "$PERMANENT_ADVANCE")")" = 202; sleep 8
BEFORE="$(python - "$PERMANENT_ADVANCE" <<'PY'
import json,sys,urllib.request; o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); print(d['state'][o]['advance_calls']); assert d['state'][o]['analysis_identity_mints']==1
PY
)"; sleep 2
AFTER="$(python - "$PERMANENT_ADVANCE" <<'PY'
import json,sys,urllib.request; o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); print(d['state'][o]['advance_calls'])
PY
)"; test "$BEFORE" = "$AFTER"; test "$AFTER" -ge 5; test "$AFTER" -le 6; assert_paced_order "$PERMANENT_ADVANCE" 5
echo N8N_REAL_ADVANCE_POLL_HORIZON=PASS

RUNTIME_OK=1
echo N8N_WORKFLOW_IMPORT=PASS; echo N8N_PUBLISH_STATE_PROOF=PASS; echo N8N_WEBHOOK_AUTH=PASS; echo N8N_ORCHESTRATION_INTEGRATION=PASS; echo N8N_WAIT_RESTART=PASS