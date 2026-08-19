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
  -e SITESCORE_N8N_POLL_SECONDS=2
  -e SITESCORE_N8N_MAX_POLLS=10
)

wait_health(){
  for _ in $(seq 1 120); do
    if curl -fsS http://127.0.0.1:5678/healthz >/dev/null 2>&1; then return 0; fi
    sleep .5
  done
  return 1
}

# A clean n8n instance must be initialized before CLI workflow import: the
# importer assigns Git-controlled workflows to the owner personal project.
docker run -d --name "$CONTAINER" -p 5678:5678 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/dev/null
wait_health
SETUP_CODE=$(curl -sS -o "$TMP_DIR/owner.body" -w '%{http_code}' -H 'Content-Type: application/json' -X POST http://127.0.0.1:5678/rest/owner/setup -d '{"email":"sitescore-ci-owner@example.test","firstName":"SiteScore","lastName":"CI","password":"'"$OWNER_PASSWORD"'"}')
test "$SETUP_CODE" = 200
echo N8N_INSTANCE_PROVISIONING=PASS
docker stop "$CONTAINER" >/dev/null
docker rm "$CONTAINER" >/dev/null

# Import the sanitized repository artifact, then publish exactly that workflow.
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
WAIT_ORDER=00000000-0000-4000-8000-000000000007
ATTENTION=00000000-0000-4000-8000-000000000008
EXPIRED=00000000-0000-4000-8000-000000000009
REFUND_PENDING=00000000-0000-4000-8000-000000000010
READINESS_PAYLOAD="$(make_payload 10000000-0000-4000-8000-00000000aa01 "$DELIVERY")"

wait_webhook_ready(){
  local code=000
  for _ in $(seq 1 60); do
    code="$(post_code __none__ "$READINESS_PAYLOAD" || true)"
    if [[ "$code" = 401 ]]; then
      echo N8N_PRODUCTION_WEBHOOK_READY=PASS
      return 0
    fi
    if [[ "$code" != 404 && "$code" != 000 ]]; then
      echo "unexpected webhook readiness status: $code" >&2
      return 1
    fi
    sleep 1
  done
  echo "production webhook did not register before readiness deadline" >&2
  return 1
}

# /healthz becomes available before ActiveWorkflowManager has necessarily
# registered production webhooks.  Security rejection (401) proves the live
# route exists without touching commerce business state.
wait_webhook_ready

test "$(post_code __none__ "$(make_payload 10000000-0000-4000-8000-000000000001 "$DELIVERY")")" = 401
test "$(post_code wrong-secret "$(make_payload 10000000-0000-4000-8000-000000000002 "$DELIVERY")")" = 401
test "$(post_code "$INGRESS_SECRET" '{"event_type":"order.paid.v1"}')" = 400
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000003 "$DELIVERY" order.fake.v1)")" = 400
python - <<PY
import json,urllib.request
d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['requests']==[],d
PY

delivery_payload="$(make_payload 10000000-0000-4000-8000-000000000010 "$DELIVERY")"
test "$(post_code "$INGRESS_SECRET" "$delivery_payload")" = 202
sleep 1
python - <<PY
import json,urllib.request
o='$DELIVERY'; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert r and r[0]['method']=='GET',r
assert not [x for x in r if x['method']=='POST'],r
assert all(x['auth_valid'] for x in r),r
PY

advance_payload="$(make_payload 10000000-0000-4000-8000-000000000020 "$ADVANCE")"
test "$(post_code "$INGRESS_SECRET" "$advance_payload")" = 202
sleep 2
python - <<PY
import json,urllib.request
o='$ADVANCE'; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert [x['method'] for x in r][:3]==['GET','POST','GET'],r
assert all(x['body_len'] in (0,2) for x in r if x['method']=='POST'),r
assert d['logical_effects'][o]==1,d
PY

test "$(post_code "$INGRESS_SECRET" "$advance_payload")" = 202
test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000021 "$ADVANCE")")" = 202
sleep 1
python - <<PY
import json,urllib.request
d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); assert d['logical_effects']['$ADVANCE']==1,d
PY

for order in "$NOT_SCORE_READY" "$ANALYSIS_FAILED" "$ANALYSIS_TIMED_OUT" "$REPORT_FAILED"; do
  test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000030 "$order")")" = 202
done
sleep 2
python - <<PY
import json,urllib.request
orders=['$NOT_SCORE_READY','$ANALYSIS_FAILED','$ANALYSIS_TIMED_OUT','$REPORT_FAILED']; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats'))
for o in orders:
 r=[x for x in d['requests'] if o in x['path']]
 assert r and r[0]['method']=='GET',(o,r)
 assert any(x['method']=='POST' and x['body_len'] in (0,2) for x in r),(o,r)
 assert d['logical_effects'][o]==1,(o,d)
PY

test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000040 "$REFUND_PENDING")")" = 202
sleep 6
python - <<PY
import json,urllib.request
o='$REFUND_PENDING'; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert d['logical_effects'][o]==1,d
assert sum(1 for x in r if x['method']=='GET')>=2,r
PY

for order in "$ATTENTION" "$EXPIRED"; do
  test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000050 "$order")")" = 202
done
sleep 1

test "$(post_code "$INGRESS_SECRET" "$(make_payload 10000000-0000-4000-8000-000000000060 "$WAIT_ORDER")")" = 202
sleep .5
docker stop "$CONTAINER" >/dev/null
docker start "$CONTAINER" >/dev/null
wait_health
wait_webhook_ready
sleep 6
python - <<PY
import json,urllib.request
o='$WAIT_ORDER'; d=json.load(urllib.request.urlopen('http://127.0.0.1:18080/__stats')); r=[x for x in d['requests'] if o in x['path']]
assert sum(1 for x in r if x['method']=='GET')>=3,r
assert not [x for x in r if x['method']=='POST'],r
PY

RUNTIME_OK=1
echo N8N_WORKFLOW_IMPORT=PASS
echo N8N_PUBLISH_STATE_PROOF=PASS
echo N8N_WEBHOOK_AUTH=PASS
echo N8N_ORCHESTRATION_INTEGRATION=PASS
echo N8N_WAIT_RESTART=PASS
