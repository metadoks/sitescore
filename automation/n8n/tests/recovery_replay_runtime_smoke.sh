#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKFLOW="$ROOT/automation/n8n/workflows/sitescore-order-paid-v1.json"
FAKE_SERVER="$ROOT/automation/n8n/tests/fake_recovery_replay_commerce.py"
IMAGE="n8nio/n8n:2.33.4"
RUN_TOKEN="${GITHUB_RUN_ID:-local}-$$"
VOLUME="sitescore-n8n65-replay-${RUN_TOKEN}"
CONTAINER="sitescore-n8n65-replay-${RUN_TOKEN}"
TMP_DIR="$(mktemp -d)"; EXPORT_DIR="$TMP_DIR/export"; RUNTIME_OK=0
mkdir -p "$EXPORT_DIR"; chmod 777 "$EXPORT_DIR"

cleanup(){
  if [[ "$RUNTIME_OK" != "1" ]] && docker inspect "$CONTAINER" >/dev/null 2>&1; then docker logs "$CONTAINER" >&2 || true; fi
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
for value in "$ENC_KEY" "$INGRESS_SECRET" "$AUTOMATION_KEY" "$OWNER_PASSWORD"; do echo "::add-mask::$value"; done

docker pull "$IMAGE" >/dev/null
VERSION="$(docker run --rm "$IMAGE" --version | tail -n1 | tr -d '\r')"; test "$VERSION" = "2.33.4"
DIGEST="$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"; case "$DIGEST" in n8nio/n8n@sha256:*) ;; *) exit 1;; esac
test "$(sha256sum "$WORKFLOW" | awk '{print $1}')" = '02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1'
echo "N8N_RECOVERY_REPLAY_RUNTIME_VERSION=$VERSION"
echo "N8N_RECOVERY_REPLAY_IMAGE_DIGEST=$DIGEST"

docker volume create "$VOLUME" >/dev/null
common_env=(
  -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_HOST=0.0.0.0 -e N8N_PORT=5680 -e N8N_PROTOCOL=http
  -e N8N_WEBHOOK_URL=http://127.0.0.1:5680/ -e N8N_SECURE_COOKIE=false -e N8N_DIAGNOSTICS_ENABLED=false
  -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -e N8N_PERSONALIZATION_ENABLED=false -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false
  -e N8N_USE_WORKFLOW_PUBLICATION_SERVICE=false -e EXECUTIONS_DATA_SAVE_ON_ERROR=none -e EXECUTIONS_DATA_SAVE_ON_SUCCESS=none
  -e COMMERCE_N8N_INGRESS_SECRET="$INGRESS_SECRET" -e COMMERCE_AUTOMATION_API_KEY="$AUTOMATION_KEY"
  -e SITESCORE_COMMERCE_AUTOMATION_BASE_URL=http://host.docker.internal:18082 -e SITESCORE_N8N_POLL_SECONDS=1 -e SITESCORE_N8N_MAX_POLLS=5
)
wait_health(){ for _ in $(seq 1 120); do curl -fsS http://127.0.0.1:5680/healthz >/dev/null 2>&1 && return 0; sleep .5; done; return 1; }

docker run -d --name "$CONTAINER" -p 5680:5680 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/dev/null
wait_health
SETUP_CODE=$(curl -sS -o "$TMP_DIR/owner.body" -w '%{http_code}' -H 'Content-Type: application/json' -X POST http://127.0.0.1:5680/rest/owner/setup -d '{"email":"sitescore-recovery-replay@example.test","firstName":"SiteScore","lastName":"RecoveryReplay","password":"'"$OWNER_PASSWORD"'"}')
test "$SETUP_CODE" = 200
docker stop "$CONTAINER" >/dev/null; docker rm "$CONTAINER" >/dev/null

docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$ROOT/automation/n8n/workflows:/workflows:ro" "$IMAGE" import:workflow --input=/workflows/sitescore-order-paid-v1.json >/tmp/n8n65-replay-import.log
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$EXPORT_DIR:/out" "$IMAGE" export:workflow --all --output=/out/workflows.json >/tmp/n8n65-replay-export.log
WORKFLOW_ID="$(python - "$EXPORT_DIR/workflows.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); items=p if isinstance(p,list) else [p]
m=[x for x in items if x.get('name')=='SiteScore Order Paid Orchestration v1.1.0']; assert len(m)==1,m
assert m[0].get('id')=='sitescoreOrderPaidV1'; print(m[0]['id'])
PY
)"
set +e
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" "$IMAGE" publish:workflow --id="$WORKFLOW_ID" >/tmp/n8n65-replay-publish.log 2>&1
PUBLISH_EXIT=$?; set -e; test "$PUBLISH_EXIT" = 0 || test "$PUBLISH_EXIT" = 1

FAKE_RECOVERY_REPLAY_AUTOMATION_KEY="$AUTOMATION_KEY" python "$FAKE_SERVER" >/tmp/n8n65-replay-fake.log 2>&1 & FAKE_PID=$!
for _ in $(seq 1 50); do curl -fsS http://127.0.0.1:18082/__stats >/dev/null 2>&1 && break; sleep .2; done
curl -fsS http://127.0.0.1:18082/__stats >/dev/null

docker run -d --name "$CONTAINER" --add-host=host.docker.internal:host-gateway -p 5680:5680 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/dev/null
wait_health
WEBHOOK="http://127.0.0.1:5680/webhook/sitescore-order-paid-v1"
make_payload(){ printf '{"event_id":"%s","event_type":"order.paid.v1","order_id":"%s","occurred_at":"2026-08-20T01:30:00Z"}' "$1" "$2"; }
post_payload(){ local payload="$1" out="$TMP_DIR/r-$RANDOM.json"; curl -sS -o "$out" -w '%{http_code}' -H 'Content-Type: application/json' -H "Authorization: Bearer $INGRESS_SECRET" -X POST "$WEBHOOK" -d "$payload"; }
READINESS="$(make_payload readiness 65000000-0000-4000-8000-000000000101)"
for _ in $(seq 1 60); do code=$(curl -sS -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' -X POST "$WEBHOOK" -d "$READINESS" || true); [[ "$code" = 401 ]] && break; sleep 1; done
test "$code" = 401

ANALYSIS=65000000-0000-4000-8000-000000000101
REPORT=65000000-0000-4000-8000-000000000102
REFUND=65000000-0000-4000-8000-000000000103
DELIVERY=65000000-0000-4000-8000-000000000104

# analysis_pending: first orchestration exhausts the finite horizon. The exact same
# durable outbox payload is then replayed and the locked workflow converges.
P_ANALYSIS="$(make_payload 65000000-0000-4000-8000-00000000a101 "$ANALYSIS")"
test "$(post_payload "$P_ANALYSIS")" = 202; sleep 8
python - "$ANALYSIS" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); s=d['state'][o]; p=d['projections'][o]
assert 5 <= s['advance_calls'] <= 6 and s['deliver_calls']==0 and s['analysis_identity_mints']==1,(s,p)
assert p['fulfillment_state']=='analysis_pending' and p['next_action']=='advance' and p['terminal'] is False,p
PY
test "$(post_payload "$P_ANALYSIS")" = 202; sleep 7
python - "$ANALYSIS" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); s=d['state'][o]; p=d['projections'][o]
assert s['advance_calls']>=7 and s['analysis_identity_mints']==1 and s['delivery_effects']==1,(s,p)
assert p['order_state']=='fulfilled' and p['fulfillment_state']=='completed' and p['terminal'] is True,p
PY
echo N8N_RECOVERY_REPLAY_ANALYSIS_PENDING=PASS

# report_pending uses the same paid-event identity replay and does not mint analysis identity.
P_REPORT="$(make_payload 65000000-0000-4000-8000-00000000a102 "$REPORT")"
test "$(post_payload "$P_REPORT")" = 202; sleep 8
python - "$REPORT" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); s=d['state'][o]; p=d['projections'][o]
assert 5 <= s['advance_calls'] <= 6 and s['deliver_calls']==0 and s['analysis_identity_mints']==1,(s,p)
assert p['fulfillment_state']=='report_pending' and p['next_action']=='advance',p
PY
test "$(post_payload "$P_REPORT")" = 202; sleep 7
python - "$REPORT" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); s=d['state'][o]; p=d['projections'][o]
assert s['advance_calls']>=7 and s['analysis_identity_mints']==1 and s['delivery_effects']==1,(s,p)
assert p['order_state']=='fulfilled' and p['terminal'] is True,p
PY
echo N8N_RECOVERY_REPLAY_REPORT_PENDING=PASS

# Refund side effect is made durable but its first HTTP response is lost. One or more
# exact same-identity recovery replays resume only from commerce next_action guidance.
P_REFUND="$(make_payload 65000000-0000-4000-8000-00000000a103 "$REFUND")"
test "$(post_payload "$P_REFUND")" = 202; sleep 3
python - "$REFUND" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); s=d['state'][o]; p=d['projections'][o]
assert s['stage']==1 and s['refund_effects']==1 and s['response_loss_injected']==1,(s,p)
assert p['payment_state']=='refund_pending' and p['next_action']=='wait' and p['terminal'] is False,p
PY
test "$(post_payload "$P_REFUND")" = 202; sleep 8
# If the first recovery replay itself reaches the finite horizon, the next scheduled
# replay is intentionally identical and must converge without repeating refund effect.
if ! python - "$REFUND" <<'PY'
import json,sys,urllib.request
d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); raise SystemExit(0 if d['projections'][sys.argv[1]]['terminal'] else 1)
PY
then
  test "$(post_payload "$P_REFUND")" = 202; sleep 5
fi
python - "$REFUND" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); s=d['state'][o]; p=d['projections'][o]
assert s['refund_effects']==1 and s['response_loss_injected']==1,(s,p)
assert p['order_state']=='refunded' and p['payment_state']=='refunded' and p['terminal'] is True,p
PY
echo N8N_RECOVERY_REPLAY_REFUND_RESPONSE_LOSS=PASS

# Delivery remains provider-uncertain/retryable through the first finite horizon.
# Replaying the same durable paid event resumes the existing /deliver semantics.
P_DELIVERY="$(make_payload 65000000-0000-4000-8000-00000000a104 "$DELIVERY")"
test "$(post_payload "$P_DELIVERY")" = 202; sleep 8
python - "$DELIVERY" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); s=d['state'][o]; p=d['projections'][o]
assert 5 <= s['deliver_calls'] <= 6 and s['delivery_effects']==0 and s['provider_uncertain_observations']>=5,(s,p)
assert p['fulfillment_state']=='delivery_pending' and p['next_action']=='delivery' and p['terminal'] is False,p
PY
test "$(post_payload "$P_DELIVERY")" = 202; sleep 7
python - "$DELIVERY" <<'PY'
import json,sys,urllib.request
o=sys.argv[1]; d=json.load(urllib.request.urlopen('http://127.0.0.1:18082/__stats')); s=d['state'][o]; p=d['projections'][o]
assert s['deliver_calls']>=7 and s['delivery_effects']==1,(s,p)
assert p['order_state']=='fulfilled' and p['fulfillment_state']=='completed' and p['terminal'] is True,p
r=[x for x in d['requests'] if o in x['path']]; assert all(x['auth_valid'] for x in r); assert all(x['body_len'] in (0,2) for x in r if x['method']=='POST')
assert all(not x['path'].endswith('/advance') for x in r),r
PY
echo N8N_RECOVERY_REPLAY_DELIVERY_UNCERTAIN=PASS

RUNTIME_OK=1
echo N8N_RECOVERY_REPLAY_LOCKED_WORKFLOW_CONVERGENCE=PASS
