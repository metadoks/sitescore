#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKFLOW="$ROOT/automation/n8n/workflows/sitescore-order-paid-v1.json"
FAKE_SERVER="$ROOT/automation/n8n/tests/fake_commerce_server.py"
IMAGE="n8nio/n8n:2.33.4"
RUN_TOKEN="${GITHUB_RUN_ID:-local}-$$"
VOLUME="sitescore-n8n63-${RUN_TOKEN}"
CONTAINER="sitescore-n8n63-${RUN_TOKEN}"
TMP_DIR="$(mktemp -d)"
EXPORT_DIR="$TMP_DIR/export"
FAKE_LOG="$TMP_DIR/fake-commerce.jsonl"
RUNTIME_OK=0
mkdir -p "$EXPORT_DIR"; chmod 777 "$EXPORT_DIR"

cleanup(){
  if [[ "$RUNTIME_OK" != "1" ]] && docker inspect "$CONTAINER" >/dev/null 2>&1; then
    echo "--- n8n container logs after runtime failure ---" >&2
    docker logs "$CONTAINER" >&2 || true
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  if [[ -n "${FAKE_PID:-}" ]]; then kill "$FAKE_PID" >/dev/null 2>&1 || true; fi
  docker volume rm "$VOLUME" >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ENC_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
INGRESS_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
AUTOMATION_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
OWNER_PASSWORD="$(python -c 'import secrets; print("A9!"+secrets.token_urlsafe(28))')"
for secret in "$ENC_KEY" "$INGRESS_SECRET" "$AUTOMATION_KEY" "$OWNER_PASSWORD"; do echo "::add-mask::$secret"; done

docker pull "$IMAGE" >/dev/null
VERSION="$(docker run --rm "$IMAGE" --version | tail -n1 | tr -d '\r')"
test "$VERSION" = "2.33.4"
DIGEST="$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"
case "$DIGEST" in n8nio/n8n@sha256:*) ;; *) echo "unexpected n8n digest: $DIGEST" >&2; exit 1;; esac
echo "N8N_RUNTIME_VERSION=$VERSION"
echo "N8N_VALIDATED_IMAGE_DIGEST=$DIGEST"
echo "WORKFLOW_SHA256=$(sha256sum "$WORKFLOW" | awk '{print $1}')"

docker volume create "$VOLUME" >/dev/null

common_env=(
  -e N8N_ENCRYPTION_KEY="$ENC_KEY"
  -e N8N_HOST=0.0.0.0
  -e N8N_PORT=5678
  -e N8N_PROTOCOL=http
  -e N8N_WEBHOOK_URL=http://127.0.0.1:5678/
  -e N8N_SECURE_COOKIE=false
  -e N8N_DIAGNOSTICS_ENABLED=false
  -e N8N_VERSION_NOTIFICATIONS_ENABLED=false
  -e N8N_PERSONALIZATION_ENABLED=false
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false
  -e N8N_USE_WORKFLOW_PUBLICATION_SERVICE=false
  -e EXECUTIONS_DATA_SAVE_ON_ERROR=none
  -e EXECUTIONS_DATA_SAVE_ON_SUCCESS=none
  -e COMMERCE_N8N_INGRESS_SECRET="$INGRESS_SECRET"
  -e COMMERCE_AUTOMATION_API_KEY="$AUTOMATION_KEY"
  -e SITESCORE_COMMERCE_AUTOMATION_BASE_URL=http://host.docker.internal:18080
  -e SITESCORE_N8N_POLL_SECONDS=1
  -e SITESCORE_N8N_MAX_POLLS=5
)

wait_health(){
  for _ in $(seq 1 120); do
    if curl -fsS http://127.0.0.1:5678/healthz >/dev/null 2>&1; then return 0; fi
    sleep .5
  done
  return 1
}

# Clean n8n volumes need an owner/personal project before CLI import.
docker run -d --name "$CONTAINER" -p 5678:5678 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/dev/null
wait_health
SETUP_CODE=$(curl -sS -o "$TMP_DIR/owner.body" -w '%{http_code}' -H 'Content-Type: application/json' -X POST http://127.0.0.1:5678/rest/owner/setup -d '{"email":"sitescore-ci-owner@example.test","firstName":"SiteScore","lastName":"CI","password":"'"$OWNER_PASSWORD"'"}')
test "$SETUP_CODE" = 200
echo N8N_INSTANCE_PROVISIONING=PASS
docker stop "$CONTAINER" >/dev/null
docker rm "$CONTAINER" >/dev/null

# Import and publish the sanitized repository authority.
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$ROOT/automation/n8n/workflows:/workflows:ro" "$IMAGE" import:workflow --input=/workflows/sitescore-order-paid-v1.json >/tmp/n8n63-import.log
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$EXPORT_DIR:/out" "$IMAGE" export:workflow --all --output=/out/workflows.json >/tmp/n8n63-export.log
WORKFLOW_ID="$(python - "$EXPORT_DIR/workflows.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); items=p if isinstance(p,list) else [p]
m=[x for x in items if x.get('name')=='SiteScore Order Paid Orchestration v1.0.0']
assert len(m)==1,m
assert m[0].get('id')=='sitescoreOrderPaidV1',m[0]
print(m[0]['id'])
PY
)"
echo N8N_IMPORTED_WORKFLOW_ID=sitescoreOrderPaidV1

set +e
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" "$IMAGE" publish:workflow --id="$WORKFLOW_ID" 2>&1 | tee /tmp/n8n63-publish.log
PUBLISH_EXIT=${PIPESTATUS[0]}
set -e
test "$PUBLISH_EXIT" = "0" || test "$PUBLISH_EXIT" = "1"
echo "N8N_PUBLISH_CLI_EXIT=$PUBLISH_EXIT"

docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$EXPORT_DIR:/out" "$IMAGE" export:workflow --id="$WORKFLOW_ID" --output=/out/published.json >/tmp/n8n63-published-export.log
python - "$EXPORT_DIR/published.json" "$WORKFLOW_ID" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); items=p if isinstance(p,list) else [p]
assert len(items)==1,items
w=items[0]
assert w.get('id')==sys.argv[2],w
assert w.get('active') is True,w
assert isinstance(w.get('activeVersionId'),str) and w['activeVersionId'],w
assert isinstance(w.get('versionId'),str) and w['versionId'],w
assert w['activeVersionId']==w['versionId'],w
print('N8N_PUBLISH_DURABLE_STATE=PASS')
PY

FAKE_COMMERCE_AUTOMATION_KEY="$AUTOMATION_KEY" FAKE_COMMERCE_LOG_FILE="$FAKE_LOG" python "$FAKE_SERVER" >/tmp/n8n63-fake-commerce.log 2>&1 & FAKE_PID=$!
for _ in $(seq 1 30); do if curl -fsS http://127.0.0.1:18080/__stats >/dev/null 2>&1; then break; fi; sleep .2; done
curl -fsS http://127.0.0.1:18080/__stats >/dev/null

docker run -d --name "$CONTAINER" --add-host=host.docker.internal:host-gateway -p 5678:5678 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/tmp/n8n63-container-id
wait_health

webhook="http://127.0.0.1:5678/webhook/sitescore-order-paid-v1"
make_payload(){ printf '{"event_id":"%s","event_type":"%s","order_id":"%s","occurred_at":"2026-08-19T15:30:00Z"}' "$1" "${3:-order.paid.v1}" "$2"; }
post_code(){
  local auth="$1" payload="$2" output="$TMP_DIR/response-$RANDOM.json"
  if [[ "$auth" = __none__ ]]; then
    curl -sS -o "$output" -w '%{http_code}' -H 'Content-Type: application/json' -X POST "$webhook" -d "$payload"
  else
    curl -sS -o "$output" -w '%{http_code}' -H 'Content-Type: application/json' -H "Authorization: Bearer $auth" -X POST "$webhook" -d "$payload"
  fi
}

DELIVERY=00000000-0000-4000-8000-000000000001
ADVANCE=00000000-0000-4000-8000-000000000002
NOT_SCORE_READY=00000000-0000-4000-8000-000000000003
ANALYSIS_FAILED=00000000-0000-4000-8000-000000000004
ANALYSIS_TIMED_OUT=00000000-0000-4000-8000-000000000005
REPORT_FAILED=00000000-0000-4000-8000-000000000006
ANALYSIS_PENDING=00000000-0000-4000-8000-000000000007
ATTENTION=00000000-0000-4000-8000-000000000008
EXPIRED=00000000-0000-4000-8000-000000000009
REFUND_PENDING=00000000-0000-4000-8000-000000000010
ANALYSIS_RUNNING=00000000-0000-4000-8000-000000000011
PERMANENT_ADVANCE=00000000-0000-4000-8000-000000000012
HTTP_5XX=00000000-0000-4000-8000-000000000013
UNCERTAIN_RESPONSE=00000000-0000-4000-8000-000000000014
RESTART_ADVANCE=00000000-0000-4000-8000-000000000015
DUPLICATE_ADVANCE=00000000-0000-4000-8000-000000000016
READINESS_PAYLOAD="$(make_payload 10000000-0000-4000-8000-00000000aa01 "$DELIVERY")"

wait_webhook_ready(){
  local code=000
  for _ in $(seq 1 60); do
    code="$(post_code __none__ "$READINESS_PAYLOAD" || true)"
    if [[ "$code" = 401 ]]; then echo N8N_PRODUCTION_WEBHOOK_READY=PASS; return 0; fi
    if [[ "$code" != 404 && "$code" != 000 ]]; then echo "unexpected webhook readiness status: $code" >&2; return 1; fi
    sleep 1
  done
  echo "production webhook did not register before readiness deadline" >&2
  return 1
}

assert_paced_order(){
  local order="$1" minimum_posts="$2"
  python - "$order" "$minimum_posts" <<'PY'
import json,sys,urllib.request
order=sys.argv[1]; minimum=int(sys.argv[2])
d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats'))
r=[x for x in d['requests'] if order in x['path']]
posts=[(i,x) for i,x in enumerate(r) if x['method']=='POST']
assert len(posts)>=minimum,(order,r)
for i,p in posts:
    later=next((x for x in r[i+1:] if x['method']=='GET'),None)
    if later is not None:
        assert later['at_monotonic']-p['at_monotonic']>=0.75,(order,p,later,r)
assert all(x['body_len'] in (0,2) for x in r if x['method']=='POST'),(order,r)
PY
}

# /healthz can precede active webhook registration; 401 proves protected route readiness.
wait_webhook_ready

test "$(post_code __none__ "$(make_payload 10000000-0000-4000-8000-000000000001 "$DELIVERY")")" = 401
test "$(post_code wrong-secret "$(make_payload 10000000-0000-4000-8000-000000000002 "$DELIVERY")")" = 401
test "$(post_code "$INGRESS_SECRET" '{"event_type":"order.paid.v1"}')" = 400
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000003 "$DELIVERY" order.fake.v1)")" = 400
python - <<'PY'
import json,urllib.request
d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['requests']==[],d
PY

# Delivery boundary: authoritative GET only, no fulfillment mutation.
delivery_payload="$(make_payload 10000000-0000-4000-8000-000000000010 "$DELIVERY")"
test "$(post_code "$INGRESS_SECRET" "$delivery_payload")" = 202
sleep 1
python - "$DELIVERY" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert r and r[0]['method']=='GET',r
assert not [x for x in r if x['method']=='POST'],r
assert all(x['auth_valid'] for x in r),r
PY

# Normal advance is now always paced before the authoritative re-read.
advance_payload="$(make_payload 10000000-0000-4000-8000-000000000020 "$ADVANCE")"
test "$(post_code "$INGRESS_SECRET" "$advance_payload")" = 202
sleep 3
assert_paced_order "$ADVANCE" 1
python - "$ADVANCE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert [x['method'] for x in r][:3]==['GET','POST','GET'],r
assert d['logical_effects'][o]==1,d
PY

# Real FAZ 6.2 projection: paid analysis_pending keeps returning advance for several cycles.
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000070 "$ANALYSIS_PENDING")")" = 202
sleep 5
assert_paced_order "$ANALYSIS_PENDING" 3
python - "$ANALYSIS_PENDING" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats'))
assert d['state'][o]['advance_calls']==3,d
assert d['state'][o]['analysis_identity_mints']==1,d
PY
echo N8N_REAL_ANALYSIS_PENDING_PACING=PASS

# Real paid analysis_running remains advance, then report_pending also remains advance.
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000071 "$ANALYSIS_RUNNING")")" = 202
sleep 6
assert_paced_order "$ANALYSIS_RUNNING" 4
python - "$ANALYSIS_RUNNING" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats'))
assert d['state'][o]['advance_calls']==4,d
assert d['state'][o]['analysis_identity_mints']==1,d
PY
echo N8N_REAL_ANALYSIS_RUNNING_REPORT_PACING=PASS

# Same-event and different-event duplicate delivery may create duplicate transport executions,
# but all executions use the same order identity and cannot mint a replacement analysis identity.
dup_same="$(make_payload 10000000-0000-4000-8000-000000000080 "$DUPLICATE_ADVANCE")"
test "$(post_code "$INGRESS_SECRET" "$dup_same")" = 202
test "$(post_code "$INGRESS_SECRET" "$dup_same")" = 202
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000081 "$DUPLICATE_ADVANCE")")" = 202
sleep 5
python - "$DUPLICATE_ADVANCE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert d['state'][o]['analysis_identity_mints']==1,d
assert d['state'][o]['advance_calls']>=3,d
assert all(x['body_len'] in (0,2) for x in r if x['method']=='POST'),r
PY
echo N8N_DUPLICATE_REPLAY_CONVERGENCE=PASS

# Canonical refund guidance still invokes only empty /advance and then paces re-observation.
for order in "$NOT_SCORE_READY" "$ANALYSIS_FAILED" "$ANALYSIS_TIMED_OUT" "$REPORT_FAILED"; do
  test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000090 "$order")")" = 202
done
sleep 4
python - "$NOT_SCORE_READY" "$ANALYSIS_FAILED" "$ANALYSIS_TIMED_OUT" "$REPORT_FAILED" <<'PY'
import json,sys,urllib.request
orders=sys.argv[1:]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats'))
for o in orders:
    r=[x for x in d['requests'] if o in x['path']]
    assert r and r[0]['method']=='GET',(o,r)
    assert any(x['method']=='POST' and x['body_len'] in (0,2) for x in r),(o,r)
    assert d['logical_effects'][o]==1,(o,d)
PY

# Refund-pending uses the same finite horizon/Wait path.
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000091 "$REFUND_PENDING")")" = 202
sleep 5
python - "$REFUND_PENDING" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert d['logical_effects'][o]==1,d
assert sum(1 for x in r if x['method']=='GET')>=2,r
PY

# Terminal / attention states are read-only stops.
for order in "$ATTENTION" "$EXPIRED"; do
  test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000092 "$order")")" = 202
done
sleep 1

# Restart while a real analysis_running advance cycle is sleeping. The persisted Wait or replay
# resumes against commerce durable state and converges without a new analysis identity.
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000100 "$RESTART_ADVANCE")")" = 202
sleep .3
docker stop "$CONTAINER" >/dev/null
docker start "$CONTAINER" >/dev/null
wait_health
wait_webhook_ready
sleep 5
assert_paced_order "$RESTART_ADVANCE" 3
python - "$RESTART_ADVANCE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats'))
assert d['state'][o]['advance_calls']==3,d
assert d['state'][o]['analysis_identity_mints']==1,d
PY
echo N8N_REAL_ADVANCE_WAIT_RESTART=PASS

# A real commerce 5xx is retried by the native HTTP node and converges on the same order.
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000110 "$HTTP_5XX")")" = 202
sleep 6
python - "$HTTP_5XX" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert d['state'][o]['get_5xx_injected']==1,d
assert sum(1 for x in r if x['method']=='GET')>=3,r
assert d['logical_effects'][o]==1,d
assert any(x['method']=='GET' and x['outcome']=='injected_5xx' for x in r),r
PY
echo N8N_COMMERCE_5XX_RECOVERY=PASS

# The first /advance side effect becomes durable but its response is delayed beyond n8n's
# 10-second timeout. Native retry/replay must discover the same durable operation, not mint one.
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000120 "$UNCERTAIN_RESPONSE")")" = 202
sleep 18
python - "$UNCERTAIN_RESPONSE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert d['state'][o]['uncertain_post_injected']==1,d
assert d['logical_effects'][o]==1,d
assert sum(1 for x in r if x['method']=='POST')>=2,r
assert any(x['method']=='POST' and x['outcome']=='accepted_response_delayed' for x in r),r
assert all(x['body_len'] in (0,2) for x in r if x['method']=='POST'),r
PY
echo N8N_COMMERCE_TIMEOUT_REPLAY_CONVERGENCE=PASS

# Permanently nonterminal paid advance state must hit the configured execution horizon.
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000130 "$PERMANENT_ADVANCE")")" = 202
sleep 8
BEFORE="$(python - "$PERMANENT_ADVANCE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats'))
print(d['state'][o]['advance_calls'])
assert d['state'][o]['analysis_identity_mints']==1,d
PY
)"
sleep 2
AFTER="$(python - "$PERMANENT_ADVANCE" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); print(d['state'][o]['advance_calls'])
PY
)"
test "$BEFORE" = "$AFTER"
test "$AFTER" -ge 5
test "$AFTER" -le 6
assert_paced_order "$PERMANENT_ADVANCE" 5
# Static graph proves the false horizon edge is Stop And Error; runtime proves traffic stops.
echo N8N_REAL_ADVANCE_POLL_HORIZON=PASS

RUNTIME_OK=1
echo N8N_WORKFLOW_IMPORT=PASS
echo N8N_PUBLISH_STATE_PROOF=PASS
echo N8N_WEBHOOK_AUTH=PASS
echo N8N_ORCHESTRATION_INTEGRATION=PASS
echo N8N_WAIT_RESTART=PASS
