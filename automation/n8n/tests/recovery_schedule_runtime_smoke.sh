#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKFLOW="$ROOT/automation/n8n/workflows/sitescore-recovery-schedule-v1.json"
FAKE_SERVER="$ROOT/automation/n8n/tests/fake_recovery_server.py"
IMAGE="n8nio/n8n:2.33.4"
RUN_TOKEN="${GITHUB_RUN_ID:-local}-$$"
VOLUME="sitescore-n8n65-${RUN_TOKEN}"
CONTAINER="sitescore-n8n65-${RUN_TOKEN}"
TMP_DIR="$(mktemp -d)"
EXPORT_DIR="$TMP_DIR/export"
COOKIE_JAR="$TMP_DIR/cookies.txt"
mkdir -p "$EXPORT_DIR"; chmod 777 "$EXPORT_DIR"
RUNTIME_OK=0

cleanup(){
  if [[ "$RUNTIME_OK" != "1" ]] && docker inspect "$CONTAINER" >/dev/null 2>&1; then docker logs "$CONTAINER" >&2 || true; fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  if [[ -n "${FAKE_PID:-}" ]]; then kill "$FAKE_PID" >/dev/null 2>&1 || true; fi
  docker volume rm "$VOLUME" >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ENC_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
AUTOMATION_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
OWNER_PASSWORD="$(python -c 'import secrets; print("A9!"+secrets.token_urlsafe(28))')"
for value in "$ENC_KEY" "$AUTOMATION_KEY" "$OWNER_PASSWORD"; do echo "::add-mask::$value"; done

docker pull "$IMAGE" >/dev/null
VERSION="$(docker run --rm "$IMAGE" --version | tail -n1 | tr -d '\r')"
test "$VERSION" = "2.33.4"
DIGEST="$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"
case "$DIGEST" in n8nio/n8n@sha256:*) ;; *) exit 1;; esac
echo "N8N_RECOVERY_RUNTIME_VERSION=$VERSION"
echo "N8N_RECOVERY_IMAGE_DIGEST=$DIGEST"
echo "N8N_RECOVERY_WORKFLOW_SHA256=$(sha256sum "$WORKFLOW" | awk '{print $1}')"

docker volume create "$VOLUME" >/dev/null
common_env=(
  -e N8N_ENCRYPTION_KEY="$ENC_KEY"
  -e N8N_HOST=0.0.0.0
  -e N8N_PORT=5680
  -e N8N_PROTOCOL=http
  -e N8N_SECURE_COOKIE=false
  -e N8N_DIAGNOSTICS_ENABLED=false
  -e N8N_VERSION_NOTIFICATIONS_ENABLED=false
  -e N8N_PERSONALIZATION_ENABLED=false
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false
  -e N8N_USE_WORKFLOW_PUBLICATION_SERVICE=false
  -e SITESCORE_COMMERCE_AUTOMATION_BASE_URL=http://host.docker.internal:18081
  -e COMMERCE_AUTOMATION_API_KEY="$AUTOMATION_KEY"
)
wait_health(){ for _ in $(seq 1 120); do curl -fsS http://127.0.0.1:5680/healthz >/dev/null 2>&1 && return 0; sleep .5; done; return 1; }

docker run -d --name "$CONTAINER" -p 5680:5680 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/dev/null
wait_health
SETUP_CODE=$(curl -sS -c "$COOKIE_JAR" -o "$TMP_DIR/owner.body" -w '%{http_code}' -H 'Content-Type: application/json' -X POST http://127.0.0.1:5680/rest/owner/setup -d '{"email":"sitescore-recovery-ci@example.test","firstName":"SiteScore","lastName":"Recovery","password":"'"$OWNER_PASSWORD"'"}')
test "$SETUP_CODE" = 200
test -s "$COOKIE_JAR"
echo N8N_RECOVERY_INSTANCE_PROVISIONING=PASS
docker stop "$CONTAINER" >/dev/null; docker rm "$CONTAINER" >/dev/null

docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$ROOT/automation/n8n/workflows:/workflows:ro" "$IMAGE" import:workflow --input=/workflows/sitescore-recovery-schedule-v1.json >/tmp/n8n65-import.log

docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$EXPORT_DIR:/out" "$IMAGE" export:workflow --all --output=/out/workflows.json >/tmp/n8n65-export.log
WORKFLOW_ID="$(python - "$EXPORT_DIR/workflows.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); items=p if isinstance(p,list) else [p]
m=[x for x in items if x.get('name')=='SiteScore Recovery Scheduler v1.0.0']
assert len(m)==1,m
assert m[0].get('id')=='sitescoreRecoveryScheduleV1',m[0]
assert [n['type'] for n in m[0]['nodes']]==['n8n-nodes-base.scheduleTrigger','n8n-nodes-base.httpRequest']
print(m[0]['id'])
PY
)"
echo N8N_RECOVERY_WORKFLOW_IMPORT=PASS

set +e
docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" "$IMAGE" publish:workflow --id="$WORKFLOW_ID" 2>&1 | tee /tmp/n8n65-publish.log
PUBLISH_EXIT=${PIPESTATUS[0]}
set -e
test "$PUBLISH_EXIT" = 0 || test "$PUBLISH_EXIT" = 1

docker run --rm -e N8N_ENCRYPTION_KEY="$ENC_KEY" -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -v "$VOLUME:/home/node/.n8n" -v "$EXPORT_DIR:/out" "$IMAGE" export:workflow --id="$WORKFLOW_ID" --output=/out/published.json >/tmp/n8n65-published.log
python - "$EXPORT_DIR/published.json" "$WORKFLOW_ID" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); items=p if isinstance(p,list) else [p]; w=items[0]
assert len(items)==1 and w.get('id')==sys.argv[2] and w.get('active') is True,w
assert w.get('activeVersionId') and w.get('versionId') and w['activeVersionId']==w['versionId'],w
PY
echo N8N_RECOVERY_PUBLISH_STATE_PROOF=PASS

FAKE_RECOVERY_AUTOMATION_KEY="$AUTOMATION_KEY" python "$FAKE_SERVER" >/tmp/n8n65-fake.log 2>&1 & FAKE_PID=$!
for _ in $(seq 1 50); do curl -fsS http://127.0.0.1:18081/__stats >/dev/null 2>&1 && break; sleep .2; done
curl -fsS http://127.0.0.1:18081/__stats >/dev/null

# The n8n CLI execute command is a sub-workflow entry path and intentionally
# requires an Execute Workflow Trigger. The production artifact must remain a
# pure Schedule Trigger -> Commerce HTTP workflow, so exercise the exact saved
# workflow through n8n's manual-run API and explicitly select the Schedule
# Trigger as the start node. n8n 2.33.4 may return HTTP 200 with an empty body
# for this endpoint, so the proof is acceptance plus the exact Commerce side
# effect rather than a non-contractual response-body shape.
docker run -d --name "$CONTAINER" --add-host=host.docker.internal:host-gateway -p 5680:5680 "${common_env[@]}" -v "$VOLUME:/home/node/.n8n" "$IMAGE" >/dev/null
wait_health
RUN_CODE=$(curl -sS -b "$COOKIE_JAR" -o "$TMP_DIR/run.body" -w '%{http_code}' -H 'Content-Type: application/json' -X POST "http://127.0.0.1:5680/rest/workflows/$WORKFLOW_ID/run" -d '{"triggerToStartFrom":{"name":"Recovery Schedule"}}')
test "$RUN_CODE" = 200
echo N8N_RECOVERY_MANUAL_TRIGGER_HTTP=PASS

COUNT=0
for _ in $(seq 1 100); do
  if curl -fsS http://127.0.0.1:18081/__stats -o "$TMP_DIR/stats.json" 2>/dev/null && python - "$TMP_DIR/stats.json" >/tmp/n8n65-count 2>/dev/null <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); print(len(d['requests']))
PY
  then
    COUNT="$(cat /tmp/n8n65-count)"
  else
    COUNT=0
  fi
  [[ "$COUNT" = 1 ]] && break
  sleep .1
done

test "$COUNT" = 1
python - "$TMP_DIR/stats.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); r=d['requests']
assert len(r)==1,r
assert r[0]['method']=='POST' and r[0]['path']=='/v1/automation/recovery/run',r
assert r[0]['body_len']==0 and r[0]['auth_valid'] is True,r
PY
echo N8N_RECOVERY_SINGLE_BOUNDED_CALL=PASS

RUNTIME_OK=1
echo N8N_RECOVERY_SCHEDULER_RUNTIME=PASS
