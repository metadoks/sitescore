#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
: "${GH_TOKEN:?GH_TOKEN is required}"

LOCK="$GITHUB_WORKSPACE/deploy/containers/n8n-image.lock"
# shellcheck disable=SC1090
set -a
. "$LOCK"
set +a

OUT="$GITHUB_WORKSPACE/deploy/containers/artifacts/n8n-final"
export OUT
SRC=/tmp/sitescore-n8n-src
mkdir -p "$OUT"
rm -rf "$SRC"

test "$N8N_BASELINE_STATUS" = FROZEN_CANDIDATE_2026_09_07
test "$N8N_VERSION" = 2.37.10
test "$N8N_SOURCE_COMMIT" = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
test "$N8N_SOURCE_TREE" = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
test "$N8N_OFFICIAL_AMD64_DIGEST" = sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
test "$N8N_CUTOFF_DATE" = 2026-09-07

test "$(sha256sum "$GITHUB_WORKSPACE/automation/n8n/workflows/sitescore-order-paid-v1.json" | awk '{print $1}')" = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
test "$(sha256sum "$GITHUB_WORKSPACE/automation/n8n/workflows/sitescore-recovery-schedule-v1.json" | awk '{print $1}')" = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
! grep -R -F 'n8n-nodes-base.snowflake' "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F 'n8n-nodes-base.emailSend' "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F 'n8n-nodes-base.executeCommand' "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F 'n8n-nodes-base.git' "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F 'n8n-nodes-base.gitTool' "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json

python - <<'PY'
import json, os, urllib.parse, urllib.request
out=os.environ['OUT']
tag=os.environ['N8N_RELEASE_TAG']
url='https://api.github.com/repos/n8n-io/n8n/releases/tags/'+urllib.parse.quote(tag, safe='')
req=urllib.request.Request(url,headers={'Authorization':f'Bearer {os.environ["GH_TOKEN"]}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'sitescore-faz7-frozen-n8n'})
with urllib.request.urlopen(req, timeout=30) as r:
    rel=json.load(r)
if rel.get('tag_name') != tag or rel.get('draft') or rel.get('prerelease'):
    raise SystemExit(f'exact frozen n8n release metadata invalid: {rel.get("tag_name")}')
ctx={'selected_version':os.environ['N8N_VERSION'],'release_id':rel['id'],'tag':rel['tag_name'],'published_at':rel.get('published_at'),'cutoff_date':os.environ['N8N_CUTOFF_DATE'],'source_commit':os.environ['N8N_SOURCE_COMMIT'],'source_tree':os.environ['N8N_SOURCE_TREE'],'official_image':os.environ['N8N_OFFICIAL_IMAGE'],'official_amd64_digest':os.environ['N8N_OFFICIAL_AMD64_DIGEST'],'dhi_ref':os.environ['N8N_DHI_RUNTIME_BASE'],'builder_image':os.environ['N8N_BUILDER_IMAGE'],'security_base_upstream_ref':os.environ['N8N_SECURITY_BASE_UPSTREAM_REF'],'upstream_runtime_reference':os.environ['N8N_UPSTREAM_RUNTIME_REFERENCE']}
json.dump(ctx,open(os.path.join(out,'source-context.json'),'w'),indent=2,sort_keys=True)
print(json.dumps(ctx,indent=2,sort_keys=True))
PY

docker pull --platform linux/amd64 "$N8N_OFFICIAL_IMAGE" >/dev/null
test "$(docker image inspect "$N8N_OFFICIAL_IMAGE" --format '{{.Architecture}}')" = amd64
test "$(docker run --rm "$N8N_OFFICIAL_IMAGE" n8n --version | tr -d '\r' | tail -n1)" = "$N8N_VERSION"

git clone --filter=blob:none --no-checkout https://github.com/n8n-io/n8n.git "$SRC"
git -C "$SRC" fetch --depth=1 origin "$N8N_SOURCE_COMMIT"
git -C "$SRC" checkout --detach "$N8N_SOURCE_COMMIT"
test "$(git -C "$SRC" rev-parse HEAD)" = "$N8N_SOURCE_COMMIT"
test "$(git -C "$SRC" rev-parse HEAD^{tree})" = "$N8N_SOURCE_TREE"
cp "$SRC/docker/images/n8n/Dockerfile" "$OUT/upstream-n8n-Dockerfile"
cp "$SRC/docker/images/n8n-base/Dockerfile" "$OUT/upstream-n8n-base-Dockerfile"
cp "$SRC/.github/workflows/build-base-image.yml" "$OUT/upstream-build-base-image.yml"
grep -F 'ARG BUILDER_IMAGE=node:26.5.1-alpine3.24@sha256:233761595746769ebfdb6090f44fc7cdf818ae0ce62d2b37e0367723b9823e36' "$SRC/docker/images/n8n/Dockerfile"
grep -F 'dhi.io/node:26.5.1-alpine3.24-dev@sha256:c4062f85acd1ca91ffb7d15048dcc5f15a922d630e65eb3c3c0dcdcef6ea36d8' "$SRC/.github/workflows/build-base-image.yml"
grep -F 'fast-uri: 3.1.5' "$SRC/pnpm-workspace.yaml"
grep -F 'ip-address@10: 10.3.1' "$SRC/pnpm-workspace.yaml"
grep -F 'brace-expansion@5: 5.0.9' "$SRC/pnpm-workspace.yaml"

curl --fail --location --silent --show-error "https://raw.githubusercontent.com/n8n-io/n8n/${N8N_SECURITY_BASE_UPSTREAM_REF}/docker/images/n8n/Dockerfile" -o "$OUT/upstream-security-n8n-Dockerfile"
curl --fail --location --silent --show-error "https://raw.githubusercontent.com/n8n-io/n8n/${N8N_SECURITY_BASE_UPSTREAM_REF}/.github/workflows/build-base-image.yml" -o "$OUT/upstream-security-build-base-image.yml"
curl --fail --location --silent --show-error "https://raw.githubusercontent.com/n8n-io/n8n/${N8N_SECURITY_BASE_UPSTREAM_REF}/pnpm-workspace.yaml" -o "$OUT/upstream-security-pnpm-workspace.yaml"
grep -F "$N8N_BUILDER_IMAGE" "$OUT/upstream-security-n8n-Dockerfile"
grep -F "$N8N_UPSTREAM_RUNTIME_REFERENCE" "$OUT/upstream-security-n8n-Dockerfile"
grep -F "$N8N_DHI_RUNTIME_BASE" "$OUT/upstream-security-build-base-image.yml"
grep -F 'fast-uri: 3.1.6' "$OUT/upstream-security-pnpm-workspace.yaml"
grep -F 'ip-address@10: 10.3.1' "$OUT/upstream-security-pnpm-workspace.yaml"
grep -F 'brace-expansion@5: 5.0.9' "$OUT/upstream-security-pnpm-workspace.yaml"
grep -F 'js-yaml: 4.3.2' "$OUT/upstream-security-pnpm-workspace.yaml"
grep -F 'multer: ^2.3.0' "$OUT/upstream-security-pnpm-workspace.yaml"

pushd "$SRC" >/dev/null
cp pnpm-workspace.yaml "$OUT/pnpm-workspace.stable.yaml"
cp pnpm-lock.yaml "$OUT/pnpm-lock.stable.yaml"
curl --fail --location --silent --show-error "https://raw.githubusercontent.com/n8n-io/n8n/${N8N_FAST_URI_UPSTREAM_REF}/pnpm-workspace.yaml" -o "$OUT/upstream-fast-uri-adoption.yaml"
grep -F "fast-uri: ${N8N_FAST_URI_TARGET}" "$OUT/upstream-fast-uri-adoption.yaml"
python - <<'PY'
from pathlib import Path
import os
p=Path('pnpm-workspace.yaml')
s=p.read_text()
replacements=[
    ('fast-uri: 3.1.5', f"fast-uri: {os.environ['N8N_FAST_URI_TARGET']}"),
    ('js-yaml: 4.3.1', f"js-yaml: {os.environ['N8N_JS_YAML_TARGET']}"),
    ('multer: ^2.2.0', f"multer: ^{os.environ['N8N_MULTER_TARGET']}"),
    ("'@xmldom/xmldom': 0.8.14", f"'@xmldom/xmldom': {os.environ['N8N_XMLDOM_TARGET']}"),
    ('adm-zip: 0.6.0', f"adm-zip: {os.environ['N8N_ADM_ZIP_TARGET']}"),
]
for old,new in replacements:
    assert s.count(old)==1, (old,s.count(old))
    s=s.replace(old,new,1)
p.write_text(s)
PY
pnpm install --lockfile-only --ignore-scripts
cp pnpm-workspace.yaml "$OUT/pnpm-workspace.backported.yaml"
cp pnpm-lock.yaml "$OUT/pnpm-lock.backported.yaml"
git diff -- pnpm-workspace.yaml pnpm-lock.yaml > "$OUT/security-backports.diff"
git diff --check -- pnpm-workspace.yaml pnpm-lock.yaml
test "$(git diff --name-only | sort | tr '\n' ' ')" = "pnpm-lock.yaml pnpm-workspace.yaml "
grep -F "fast-uri: $N8N_FAST_URI_TARGET" pnpm-workspace.yaml
grep -F "js-yaml: $N8N_JS_YAML_TARGET" pnpm-workspace.yaml
grep -F "multer: ^$N8N_MULTER_TARGET" pnpm-workspace.yaml
grep -F "'@xmldom/xmldom': $N8N_XMLDOM_TARGET" pnpm-workspace.yaml
grep -F "adm-zip: $N8N_ADM_ZIP_TARGET" pnpm-workspace.yaml
! grep -F 'fast-uri@3.1.5' pnpm-lock.yaml
! grep -F 'js-yaml@4.3.1' pnpm-lock.yaml
! grep -F 'multer@2.2.0' pnpm-lock.yaml
! grep -F '@xmldom/xmldom@0.8.14' pnpm-lock.yaml
! grep -F 'adm-zip@0.6.0' pnpm-lock.yaml
grep -F "fast-uri@$N8N_FAST_URI_TARGET" pnpm-lock.yaml
grep -F "js-yaml@$N8N_JS_YAML_TARGET" pnpm-lock.yaml
python - <<'PY'
import os
from pathlib import Path
prefix='  multer@'
versions=[]
for line in Path('pnpm-lock.yaml').read_text().splitlines():
    if not (line.startswith(prefix) and line.endswith(':')):
        continue
    version=line[len(prefix):-1]
    parts=version.split('.')
    if len(parts)==3 and all(part.isdigit() for part in parts):
        versions.append(version)
versions=sorted(set(versions))
if len(versions)!=1:
    raise SystemExit(f'unexpected multer lock versions: {versions}')
parts=tuple(map(int,versions[0].split('.')))
floor=tuple(map(int,os.environ['N8N_MULTER_TARGET'].split('.')))
if not (parts >= floor and parts[0] == 2):
    raise SystemExit(f'multer resolved outside authorized range: {versions[0]}')
Path(os.environ['OUT'],'multer-resolved-version.txt').write_text(versions[0]+'\n')
print('MULTER_RESOLVED_VERSION='+versions[0])
PY
grep -F "@xmldom/xmldom@$N8N_XMLDOM_TARGET" pnpm-lock.yaml
grep -F "adm-zip@$N8N_ADM_ZIP_TARGET" pnpm-lock.yaml
CI=true NODE_OPTIONS=--max-old-space-size=7168 pnpm install --frozen-lockfile
pnpm why --prod --recursive snowflake-sdk --json > "$OUT/pnpm-why-prod-snowflake-sdk.json"
pnpm why --prod --recursive toml --json > "$OUT/pnpm-why-prod-toml.json"
pnpm why --prod --recursive fast-uri --json > "$OUT/pnpm-why-prod-fast-uri.json"
pnpm why --prod --recursive ip-address --json > "$OUT/pnpm-why-prod-ip-address.json"
pnpm why --prod --recursive brace-expansion --json > "$OUT/pnpm-why-prod-brace-expansion.json"
pnpm why --prod --recursive js-yaml --json > "$OUT/pnpm-why-prod-js-yaml.json"
pnpm why --prod --recursive multer --json > "$OUT/pnpm-why-prod-multer.json"
pnpm why --prod --recursive @xmldom/xmldom --json > "$OUT/pnpm-why-prod-xmldom.json"
pnpm why --prod --recursive adm-zip --json > "$OUT/pnpm-why-prod-adm-zip.json"
pnpm why --prod --recursive @tiptap/core --json > "$OUT/pnpm-why-prod-tiptap-core.json"
python - <<'PY'
import json, os
from pathlib import Path
target=os.environ['N8N_ADM_ZIP_TARGET']
rows=[]
for p in Path('node_modules/.pnpm').rglob('package.json'):
    try:
        d=json.loads(p.read_text())
    except Exception:
        continue
    for section in ('dependencies','optionalDependencies'):
        dep=(d.get(section) or {}).get('adm-zip')
        if dep:
            rows.append({
                'parent':d.get('name'),
                'parent_version':d.get('version'),
                'section':section,
                'declared_range':dep,
            })
expected=[r for r in rows if r['parent']=='epub2' and r['parent_version']=='3.0.2']
if not expected:
    raise SystemExit('expected epub2@3.0.2 -> adm-zip parent not found')
unexpected=[r for r in rows if r['parent']!='epub2']
evidence={
    'override_target':target,
    'expected_parent':expected,
    'other_parents':unexpected,
    'override_mechanism':'pnpm-workspace override',
    'epub2_parent_major_change':False,
}
Path(os.environ['OUT'],'adm-zip-parent-override-proof.json').write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
if unexpected:
    raise SystemExit('unexpected adm-zip production parents: '+json.dumps(unexpected,sort_keys=True))
PY
grep -F snowflake-sdk "$OUT/pnpm-why-prod-snowflake-sdk.json"
grep -F toml "$OUT/pnpm-why-prod-toml.json"
python - <<'PY'
import json, os
from pathlib import Path
target=os.environ['N8N_XMLDOM_TARGET']
root=Path('node_modules/.pnpm')
rows=[]
for p in root.rglob('package.json'):
    try:
        d=json.loads(p.read_text())
    except Exception:
        continue
    for section in ('dependencies','optionalDependencies','peerDependencies'):
        dep=(d.get(section) or {}).get('@xmldom/xmldom')
        if dep:
            rows.append({'parent':d.get('name'),'parent_version':d.get('version'),'section':section,'declared_range':dep})
assert rows, 'no xmldom parents discovered'
bad=[]
for r in rows:
    spec=str(r['declared_range'])
    if spec.startswith('^0.8.'):
        floor=tuple(map(int,spec[1:].split('.')))
        cur=tuple(map(int,target.split('.')))
        ok=cur[0]==0 and cur[1]==8 and cur>=floor
    elif spec.startswith('~0.8.'):
        floor=tuple(map(int,spec[1:].split('.')))
        cur=tuple(map(int,target.split('.')))
        ok=cur[:2]==floor[:2] and cur>=floor
    else:
        ok=(spec==target)
    if not ok: bad.append(r)
Path(os.environ['OUT'],'xmldom-parent-ranges.json').write_text(json.dumps({'target':target,'parents':rows,'incompatible':bad},indent=2,sort_keys=True)+'\n')
if bad: raise SystemExit('xmldom parent-range incompatibility: '+json.dumps(bad,sort_keys=True))
PY
CI=true NODE_OPTIONS=--max-old-space-size=7168 RELEASE="$N8N_VERSION" pnpm build:n8n
test -d compiled
grep -R "\"version\": \"$N8N_FAST_URI_TARGET\"" compiled/node_modules/.pnpm/fast-uri@$N8N_FAST_URI_TARGET*/node_modules/fast-uri/package.json
grep -R '"version": "10.3.1"' compiled/node_modules/.pnpm/ip-address@10.3.1*/node_modules/ip-address/package.json
grep -R '"version": "5.0.9"' compiled/node_modules/.pnpm/brace-expansion@5.0.9*/node_modules/brace-expansion/package.json
grep -R "\"version\": \"$N8N_JS_YAML_TARGET\"" compiled/node_modules/.pnpm/js-yaml@$N8N_JS_YAML_TARGET*/node_modules/js-yaml/package.json
python - <<'PY'
import json, os
from pathlib import Path
floor=tuple(map(int,os.environ['N8N_MULTER_TARGET'].split('.')))
files=list(Path('compiled/node_modules/.pnpm').glob('multer@*/node_modules/multer/package.json'))
if len(files)!=1:
    raise SystemExit(f'unexpected compiled multer package files: {[str(p) for p in files]}')
version=json.loads(files[0].read_text())['version']
parts=tuple(map(int,version.split('.')))
if not (parts >= floor and parts[0] == 2):
    raise SystemExit(f'compiled multer outside authorized ^{os.environ["N8N_MULTER_TARGET"]} range: {version}')
print('COMPILED_MULTER_VERSION='+version)
PY
grep -R "\"version\": \"$N8N_XMLDOM_TARGET\"" compiled/node_modules/.pnpm/@xmldom+xmldom@$N8N_XMLDOM_TARGET*/node_modules/@xmldom/xmldom/package.json
grep -R "\"version\": \"$N8N_ADM_ZIP_TARGET\"" compiled/node_modules/.pnpm/adm-zip@$N8N_ADM_ZIP_TARGET*/node_modules/adm-zip/package.json
grep -R '"version": "8.0.10"' compiled/node_modules/.pnpm/nodemailer@8.0.10*/node_modules/nodemailer/package.json
grep -R '"version": "2.1.0"' compiled/node_modules/.pnpm/snowflake-sdk@2.1.0*/node_modules/snowflake-sdk/package.json
grep -R '"version": "3.0.0"' compiled/node_modules/.pnpm/toml@3.0.0*/node_modules/toml/package.json
python "$GITHUB_WORKSPACE/deploy/containers/n8n_prune_closure.py" compiled/node_modules "$OUT"
! find compiled/node_modules -type f -path '*/snowflake-sdk/package.json' -print -quit | grep .
! find compiled/node_modules -type f -path '*/toml/package.json' -exec grep -l '"version": "3.0.0"' {} + | grep .
popd >/dev/null

cat > /tmp/sitescore-n8n-base.Dockerfile <<'EOF'
ARG DHI_REF
FROM ${DHI_REF} AS evidence
ARG LIBCURL_TARGET
RUN apk --no-cache add --virtual .build-deps-fonts msttcorefonts-installer fontconfig && \
    update-ms-fonts && fc-cache -f && apk del .build-deps-fonts && \
    find /usr/share/fonts/truetype/msttcorefonts/ -type l -exec unlink {} \; && \
    apk add --no-cache openssh graphicsmagick tini tzdata ca-certificates libc6-compat librdkafka && \
    mkdir -p /security-evidence && \
    cp /etc/apk/repositories /security-evidence/repositories.before && \
    cp /etc/apk/world /security-evidence/world.before && \
    cp /lib/apk/db/installed /security-evidence/installed.before && \
    apk info | sort > /security-evidence/packages.before.txt && \
    apk policy libcurl git pcre2 zlib > /security-evidence/security-packages.policy.before.txt && \
    (apk del openssh graphicsmagick 2>&1 | tee /security-evidence/baseline-removal.log) && \
    apk info | sort > /security-evidence/packages.pre-git-prune.txt && \
    cp /etc/apk/world /security-evidence/world.pre-git-prune && \
    (apk del git git-init-template pcre2 2>&1 | tee /security-evidence/git-removal.log) && \
    apk info | sort > /security-evidence/packages.post-git-prune.txt && \
    cp /etc/apk/world /security-evidence/world.post-git-prune && \
    (apk add --no-cache --upgrade 'libcrypto3=3.5.8-r0' 'libssl3=3.5.8-r0' 'libexpat=2.8.4-r0' "libcurl=${LIBCURL_TARGET}" 2>&1 | tee /security-evidence/pins.log) && \
    apk policy libcrypto3 libssl3 libexpat libcurl pcre2 zlib > /security-evidence/policy.after.txt && \
    apk info | sort > /security-evidence/packages.after.txt && \
    cp /etc/apk/repositories /security-evidence/repositories.after && \
    cp /etc/apk/world /security-evidence/world.after && \
    cp /lib/apk/db/installed /security-evidence/installed.after && \
    rm -rf /tmp/* /root/.npm /root/.cache/node /opt/yarn*
FROM evidence AS final
RUN apk del apk-tools && rm -rf /security-evidence
RUN mkdir -p /usr/local/bin && ln -sf /usr/bin/node /usr/local/bin/node
WORKDIR /home/node
ENV NODE_PATH=/usr/local/lib/node_modules
EXPOSE 5678/tcp
EOF

docker build --platform linux/amd64 --no-cache --target evidence --build-arg DHI_REF="$N8N_DHI_RUNTIME_BASE" --build-arg LIBCURL_TARGET="$N8N_LIBCURL_TARGET" -f /tmp/sitescore-n8n-base.Dockerfile -t sitescore-n8n-base-pruned:evidence "$SRC"
eid="$(docker create sitescore-n8n-base-pruned:evidence)"
docker cp "$eid:/security-evidence/." "$OUT/apk-evidence"
docker rm "$eid" >/dev/null
python - <<'PY'
import json, os
from pathlib import Path
out=Path(os.environ['OUT'])/'apk-evidence'
pre=set((out/'packages.pre-git-prune.txt').read_text().splitlines())
post=set((out/'packages.post-git-prune.txt').read_text().splitlines())
removed=sorted(pre-post)
expected={'git','git-init-template','pcre2'}
shared_non_git=sorted(set(removed)-expected)
missing=sorted(expected-set(removed))
evidence={
    'pre_git_prune_contains':{name:(name in pre) for name in sorted(expected)},
    'removed_packages':removed,
    'expected_git_exclusive_removed':sorted(expected),
    'missing_expected_removals':missing,
    'shared_non_git_runtime_removed':shared_non_git,
}
(out/'git-capability-prune.json').write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
if any(name not in pre for name in expected):
    raise SystemExit('expected explicit git capability packages missing before prune')
if missing:
    raise SystemExit('git capability pruning missed packages: '+json.dumps(missing))
if shared_non_git:
    raise SystemExit('unexpected shared runtime packages removed by git prune: '+json.dumps(shared_non_git))
PY
docker build --platform linux/amd64 --no-cache --target final --build-arg DHI_REF="$N8N_DHI_RUNTIME_BASE" --build-arg LIBCURL_TARGET="$N8N_LIBCURL_TARGET" -f /tmp/sitescore-n8n-base.Dockerfile -t "$N8N_HARDENED_BASE_IMAGE" "$SRC"
docker run --rm --entrypoint sh "$N8N_HARDENED_BASE_IMAGE" -c 'cat /lib/apk/db/installed' > "$OUT/final-installed.raw"
test "$(docker image inspect "$N8N_HARDENED_BASE_IMAGE" --format '{{.Architecture}}')" = amd64
test "$(docker run --rm --entrypoint sh "$N8N_HARDENED_BASE_IMAGE" -c 'node --version')" = v26.7.0
! docker run --rm --entrypoint sh "$N8N_HARDENED_BASE_IMAGE" -c 'command -v apk >/dev/null'
python - <<'PY'
import os
raw=open(os.path.join(os.environ['OUT'],'final-installed.raw')).read()
for item in ('P:libcrypto3\nV:3.5.8-r0','P:libssl3\nV:3.5.8-r0','P:libexpat\nV:2.8.4-r0',f"P:libcurl\nV:{os.environ['N8N_LIBCURL_TARGET']}"):
    if item not in raw: raise SystemExit('required exact runtime pin missing: '+item)
for item in ('P:openssh\n','P:graphicsmagick\n','P:apk-tools\n','P:git\n','P:git-init-template\n','P:pcre2\n'):
    if item in raw: raise SystemExit('forbidden runtime package remains: '+item)
for item in ('P:tini\n','P:tzdata\n','P:ca-certificates\n','P:librdkafka\n','P:gcompat\n'):
    if item not in raw: raise SystemExit('required runtime package/provider missing: '+item)
PY

pushd "$SRC" >/dev/null
docker build --platform linux/amd64 --build-arg BUILDER_IMAGE="$N8N_BUILDER_IMAGE" --build-arg RUNTIME_IMAGE="$N8N_HARDENED_BASE_IMAGE" --build-arg N8N_VERSION="$N8N_VERSION" --build-arg N8N_RELEASE_TYPE=stable -f docker/images/n8n/Dockerfile -t sitescore-n8n-pruned-core:frozen .
popd >/dev/null
cat > /tmp/sitescore-n8n-contract.Dockerfile <<'EOF'
FROM sitescore-n8n-pruned-core:frozen
ENV NODES_EXCLUDE='["n8n-nodes-base.executeCommand","n8n-nodes-base.localFileTrigger","n8n-nodes-base.emailSend","n8n-nodes-base.snowflake","n8n-nodes-base.git","n8n-nodes-base.gitTool"]'
EOF
docker build --network=none --platform linux/amd64 -f /tmp/sitescore-n8n-contract.Dockerfile -t "$N8N_CANDIDATE_IMAGE" /tmp
docker image inspect "$N8N_CANDIDATE_IMAGE" > "$OUT/final-image-inspect.json"
docker image inspect "$N8N_CANDIDATE_IMAGE" --format '{{.Id}}' > "$OUT/final-image-id.txt"
test "$(docker image inspect "$N8N_CANDIDATE_IMAGE" --format '{{.Architecture}}')" = amd64
user="$(docker image inspect "$N8N_CANDIDATE_IMAGE" --format '{{.Config.User}}')"
test -n "$user" && test "$user" != root && test "$user" != 0
test "$(docker run --rm "$N8N_CANDIDATE_IMAGE" n8n --version | tr -d '\r' | tail -n1)" = "$N8N_VERSION"
envs="$(docker image inspect "$N8N_CANDIDATE_IMAGE" --format '{{json .Config.Env}}')"
printf '%s\n' "$envs" > "$OUT/image-env.json"
for node in n8n-nodes-base.executeCommand n8n-nodes-base.localFileTrigger n8n-nodes-base.emailSend n8n-nodes-base.snowflake n8n-nodes-base.git n8n-nodes-base.gitTool; do grep -F "$node" "$OUT/image-env.json"; done
cid="$(docker run -d --rm --tmpfs /tmp:rw,nosuid,nodev -e N8N_USER_FOLDER=/tmp/n8n -e N8N_ENCRYPTION_KEY=ci-only-frozen-key-000000000000000000000 -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_PERSONALIZATION_ENABLED=false -p 127.0.0.1:15678:5678 "$N8N_CANDIDATE_IMAGE")"
trap 'docker logs "$cid" > "$OUT/startup-runtime.log" 2>&1 || true; docker stop -t 5 "$cid" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 120); do curl -fsS http://127.0.0.1:15678/healthz >/dev/null 2>&1 && break; sleep .5; done
curl -fsS http://127.0.0.1:15678/healthz >/dev/null
docker stop -t 5 "$cid" >/dev/null
trap - EXIT

export_dir="$(mktemp -d)"
chmod 0777 "$export_dir"
trap 'rm -rf "$export_dir"' EXIT
docker run --rm --tmpfs /tmp:rw,nosuid,nodev \
  -e N8N_USER_FOLDER=/tmp/n8n \
  -e N8N_ENCRYPTION_KEY=ci-only-frozen-key-000000000000000000000 \
  -e N8N_DIAGNOSTICS_ENABLED=false \
  -e N8N_PERSONALIZATION_ENABLED=false \
  -v "$export_dir:/evidence" \
  "$N8N_CANDIDATE_IMAGE" export:nodes --output=/evidence/node-types.json \
  | tee "$OUT/export-nodes-runtime.log"
test -s "$export_dir/node-types.json"
cp "$export_dir/node-types.json" "$OUT/node-types.json"
rm -rf "$export_dir"
trap - EXIT
grep -Fq n8n-nodes-base.httpRequest "$OUT/node-types.json"
! grep -Fq n8n-nodes-base.snowflake "$OUT/node-types.json"
! grep -Fq n8n-nodes-base.emailSend "$OUT/node-types.json"
! grep -Fq n8n-nodes-base.executeCommand "$OUT/node-types.json"
! grep -Fq n8n-nodes-base.localFileTrigger "$OUT/node-types.json"
! grep -Fq n8n-nodes-base.git "$OUT/node-types.json"
! grep -Fq n8n-nodes-base.gitTool "$OUT/node-types.json"
vol="sitescore-frozen-import-${GITHUB_RUN_ID}"
docker volume create "$vol" >/dev/null
trap 'docker volume rm -f "$vol" >/dev/null 2>&1 || true' EXIT
for wf in sitescore-order-paid-v1.json sitescore-recovery-schedule-v1.json; do docker run --rm -e N8N_ENCRYPTION_KEY=ci-only-frozen-key-000000000000000000000 -e N8N_DIAGNOSTICS_ENABLED=false -v "$vol:/home/node/.n8n" -v "$GITHUB_WORKSPACE/automation/n8n/workflows:/workflows:ro" "$N8N_CANDIDATE_IMAGE" import:workflow --input="/workflows/$wf"; done
docker volume rm -f "$vol" >/dev/null
trap - EXIT

syft="$(awk -F= '$1=="SYFT_IMAGE" {print $2}' "$GITHUB_WORKSPACE/deploy/containers/supply-chain-tools.lock")"
grype="$(awk -F= '$1=="GRYPE_IMAGE" {print $2}' "$GITHUB_WORKSPACE/deploy/containers/supply-chain-tools.lock")"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$syft" "$N8N_CANDIDATE_IMAGE" -o spdx-json > "$OUT/n8n.spdx.json"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$grype" "$N8N_CANDIDATE_IMAGE" -o json > "$OUT/n8n.grype.json"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$grype" "$N8N_OFFICIAL_IMAGE" -o json > "$OUT/official.grype.json"
curl --fail --location --silent --show-error https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json -o "$OUT/cisa-kev.json"
python - <<'PY'
import hashlib, json, os, urllib.request
out=os.environ['OUT']; ctx=json.load(open(os.path.join(out,'source-context.json')))
req=urllib.request.Request(f'https://api.github.com/repos/n8n-io/n8n/releases/{ctx["release_id"]}/assets',headers={'Authorization':f'Bearer {os.environ["GH_TOKEN"]}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'sitescore-faz7-frozen-n8n'})
with urllib.request.urlopen(req,timeout=30) as r: assets=json.load(r)
asset=next((a for a in assets if a.get('name')=='vex.openvex.json'),None)
if not asset: raise SystemExit('exact frozen release OpenVEX asset missing')
urllib.request.urlretrieve(asset['browser_download_url'],os.path.join(out,'upstream.openvex.json'))
computed='sha256:'+hashlib.sha256(open(os.path.join(out,'upstream.openvex.json'),'rb').read()).hexdigest(); recorded=asset.get('digest'); verified=bool(recorded and recorded==computed)
json.dump(asset,open(os.path.join(out,'openvex-asset-metadata.json'),'w'),indent=2,sort_keys=True)
json.dump({'metadata_digest':recorded,'computed_digest':computed,'verified':verified},open(os.path.join(out,'openvex-asset-verification.json'),'w'),indent=2,sort_keys=True)
if not verified: raise SystemExit('OpenVEX digest verification failed')
ctx['selected_digest']=open(os.path.join(out,'final-image-id.txt')).read().strip(); json.dump(ctx,open(os.path.join(out,'release-context.json'),'w'),indent=2,sort_keys=True)
PY
python "$GITHUB_WORKSPACE/deploy/containers/n8n_openvex_reconcile.py" "$OUT"
! grep -Eiq 'tiptap|n8n-nodes-base\.markdown' "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F n8n-nodes-base.emailSend "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -Eiq 'SMTP|N8N_EMAIL_MODE|N8N_SMTP' "$GITHUB_WORKSPACE/automation/n8n/runtime/docker-compose.yml"
grep -F '127.0.0.1:5678:5678' "$GITHUB_WORKSPACE/automation/n8n/runtime/docker-compose.yml"
test -s "$GITHUB_WORKSPACE/deploy/containers/nodemailer-risk-record.md"
test -s "$GITHUB_WORKSPACE/deploy/containers/n8n-security-residual-risk-record.md"
python - <<'PY'
import json, os
out=os.environ['OUT']
rows=json.load(open(os.path.join(out,'n8n.vendor-openvex-reconciliation.json')))
official=json.load(open(os.path.join(out,'official.grype.json')))
inspect=json.load(open(os.path.join(out,'final-image-inspect.json')))
arch=inspect[0].get('Architecture') if isinstance(inspect,list) else inspect.get('Architecture')
critical=[r for r in rows if r['severity']=='CRITICAL' and r.get('final_disposition')!='VEX_NOT_AFFECTED_ALLOWED']
high=[r for r in rows if r['severity']=='HIGH' and r.get('final_disposition')!='VEX_NOT_AFFECTED_ALLOWED']
kev=[r for r in rows if r.get('CISA_KEV_alias_matches')]
allowed=[]; blocking=[]
allowed_ids={
  ('nodemailer','8.0.10','GHSA-P6GQ-J5CR-W38F'),
  ('nodemailer','8.0.10','GHSA-2X7J-588G-CCC2'),
  ('@tiptap/core','3.27.0','GHSA-J95F-988M-3J2F'),
  ('zlib','1.3.2-r0','CVE-2026-85091'),
}
for r in high:
    ids={str(x).upper() for x in (r.get('scanner_alias_ids') or [])}
    ids.add(str(r.get('scanner_advisory_id') or '').upper())
    matched=None
    for pkg,ver,aid in allowed_ids:
        if r.get('package_name')==pkg and r.get('installed_version')==ver and aid in ids:
            matched=(pkg,ver,aid); break
    if matched:
        pkg,ver,aid=matched
        if pkg=='zlib' and (r.get('fixed_versions') or []):
            blocking.append(r); continue
        allowed.append({'package':pkg,'version':ver,'advisory':aid,'reason':'reviewer-authorized exact residual'})
    else:
        blocking.append(r)
forbidden={n:[r for r in high if r.get('package_name')==n] for n in ('fast-uri','ip-address','brace-expansion','toml','snowflake-sdk','pcre2','adm-zip','git')}
official_high={(str((m.get('vulnerability') or {}).get('id')),str((m.get('artifact') or {}).get('name'))) for m in official.get('matches',[]) if str((m.get('vulnerability') or {}).get('severity') or '').upper()=='HIGH'}
new_blocking=[r for r in blocking if (str(r.get('scanner_advisory_id')),str(r.get('package_name'))) not in official_high]
os_blocking=[r for r in blocking if r.get('package_type')=='apk']
summary={
 'BLOCKING_CRITICAL':len(critical),
 'CISA_KEV':len(kev),
 'ACTIONABLE_OS_HIGH':len(os_blocking),
 'NEW_UNDISPOSITIONED_HIGH':len(new_blocking),
 'BLOCKING_HIGH':len(blocking),
 'ALLOWED_EXACT_RESIDUAL_HIGH':len(allowed),
 'ALLOWED_RESIDUALS':allowed,
 'BLOCKING_HIGH_DETAILS':[{'id':r.get('scanner_advisory_id'),'package':r.get('package_name'),'version':r.get('installed_version'),'fixed_versions':r.get('fixed_versions') or []} for r in blocking],
 'FORBIDDEN_PACKAGE_HIGH':{k:len(v) for k,v in forbidden.items()},
}
json.dump(summary,open(os.path.join(out,'security-summary.json'),'w'),indent=2,sort_keys=True)
json.dump({'architecture':arch,'allowed_residuals':allowed,'blocking_high':summary['BLOCKING_HIGH_DETAILS']},open(os.path.join(out,'reviewer-residual-risk-evidence.json'),'w'),indent=2,sort_keys=True)
print(json.dumps(summary,indent=2,sort_keys=True))
if critical or kev or os_blocking or new_blocking or blocking or any(forbidden.values()):
    raise SystemExit('final security threshold failed')
PY
! grep -R -F n8n-nodes-base.emailSend "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F n8n-nodes-base.snowflake "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F n8n-nodes-base.executeCommand "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F n8n-nodes-base.localFileTrigger "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F n8n-nodes-base.git "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -R -F n8n-nodes-base.gitTool "$GITHUB_WORKSPACE"/automation/n8n/workflows/*.json
! grep -Eiq 'SMTP|N8N_EMAIL_MODE|N8N_SMTP' "$GITHUB_WORKSPACE/automation/n8n/runtime/docker-compose.yml"
grep -F '127.0.0.1:5678:5678' "$GITHUB_WORKSPACE/automation/n8n/runtime/docker-compose.yml"
test -s "$GITHUB_WORKSPACE/deploy/containers/nodemailer-risk-record.md"
python -m pip install --disable-pip-version-check --no-input pytest==8.4.2
python -m pytest -q "$GITHUB_WORKSPACE/automation/n8n/tests" | tee "$OUT/static-tests.txt"
grep -E '12 passed' "$OUT/static-tests.txt"
python - <<'PY'
from pathlib import Path
import difflib, os
root=Path(os.environ['GITHUB_WORKSPACE'])
out=root/'deploy/containers/artifacts/n8n-final'
paths=[
    root/'automation/n8n/tests/runtime_smoke.sh',
    root/'automation/n8n/tests/recovery_schedule_runtime_smoke.sh',
    root/'automation/n8n/tests/recovery_replay_runtime_smoke.sh',
]
for p in paths:
    text=p.read_text()
    lines=text.splitlines()
    patched=[]
    skip_case=False
    digest_replaced=0
    case_removed=0
    pull_removed=0
    for line in lines:
        if line.strip()=='docker pull "$IMAGE" >/dev/null':
            pull_removed += 1
            continue
        if 'DIGEST="$(docker image inspect "$IMAGE" --format' in line and 'RepoDigests' in line:
            prefix=line.split('DIGEST=',1)[0]
            if '; case "$DIGEST" in ' in line:
                patched.append(prefix+'DIGEST="$(docker image inspect "$IMAGE" --format \'{{.Id}}\')"; test -n "$DIGEST"')
                case_removed += 1
            else:
                patched.append(prefix+'DIGEST="$(docker image inspect "$IMAGE" --format \'{{.Id}}\')"')
                patched.append(prefix+'test -n "$DIGEST"')
                skip_case=True
            digest_replaced += 1
            continue
        if skip_case and line.strip().startswith('case "$DIGEST" in '):
            case_removed += 1
            skip_case=False
            continue
        patched.append(line.replace('IMAGE="n8nio/n8n:2.33.4"','IMAGE="sitescore-n8n-frozen:2.37.10"').replace('test "$VERSION" = "2.33.4"','test "$VERSION" = "2.37.10"'))
    patched_text='\n'.join(patched)+'\n'
    if digest_replaced != 1 or case_removed != 1 or 'RepoDigests' in patched_text:
        raise SystemExit(f'failed to patch immutable-image identity in {p}: digest={digest_replaced} case={case_removed}')
    if 'IMAGE="sitescore-n8n-frozen:2.37.10"' not in patched_text or 'test "$VERSION" = "2.37.10"' not in patched_text:
        raise SystemExit(f'failed to patch frozen image/version in {p}')
    q=p.with_name('.faz7-'+p.name)
    q.write_text(patched_text)
    q.chmod(0o755)
    (out/(p.name+'.faz7.patch')).write_text(''.join(difflib.unified_diff(text.splitlines(True),patched_text.splitlines(True),fromfile=str(p),tofile=str(q))))
PY
trap 'rm -f "$GITHUB_WORKSPACE"/automation/n8n/tests/.faz7-runtime_smoke.sh "$GITHUB_WORKSPACE"/automation/n8n/tests/.faz7-recovery_schedule_runtime_smoke.sh "$GITHUB_WORKSPACE"/automation/n8n/tests/.faz7-recovery_replay_runtime_smoke.sh' EXIT
bash "$GITHUB_WORKSPACE/automation/n8n/tests/.faz7-runtime_smoke.sh" | tee "$OUT/order-paid-runtime-smoke.txt"
bash "$GITHUB_WORKSPACE/automation/n8n/tests/.faz7-recovery_schedule_runtime_smoke.sh" | tee "$OUT/recovery-schedule-runtime-smoke.txt"
bash "$GITHUB_WORKSPACE/automation/n8n/tests/.faz7-recovery_replay_runtime_smoke.sh" | tee "$OUT/recovery-replay-runtime-smoke.txt"
rm -f "$GITHUB_WORKSPACE"/automation/n8n/tests/.faz7-runtime_smoke.sh "$GITHUB_WORKSPACE"/automation/n8n/tests/.faz7-recovery_schedule_runtime_smoke.sh "$GITHUB_WORKSPACE"/automation/n8n/tests/.faz7-recovery_replay_runtime_smoke.sh
trap - EXIT
git -C "$GITHUB_WORKSPACE" diff --exit-code
python - <<'PY'
import hashlib, json, os, pathlib
out=pathlib.Path(os.environ['OUT']); lock=pathlib.Path(os.environ['GITHUB_WORKSPACE'])/'deploy/containers/n8n-image.lock'
predicate={'buildDefinition':{'buildType':'https://github.com/metadoks/sitescore/.github/workflows/faz7-container-ci.yml','externalParameters':{'platform':'linux/amd64','candidate':'n8n-2.37.10-snowflake-pruned'},'internalParameters':{'lock_sha256':hashlib.sha256(lock.read_bytes()).hexdigest()},'resolvedDependencies':[{'uri':'git+https://github.com/n8n-io/n8n','digest':{'gitCommit':os.environ['N8N_SOURCE_COMMIT'],'gitTree':os.environ['N8N_SOURCE_TREE']}},{'uri':'docker://n8nio/n8n','digest':{'sha256':os.environ['N8N_OFFICIAL_AMD64_DIGEST'].split(':',1)[1]}}]},'runDetails':{'builder':{'id':f'https://github.com/metadoks/sitescore/actions/runs/{os.environ["GITHUB_RUN_ID"]}'},'metadata':{'invocationId':f'{os.environ["GITHUB_RUN_ID"]}/{os.environ.get("GITHUB_RUN_ATTEMPT","1")}'}}}
(out/'n8n.provenance.json').write_text(json.dumps(predicate,indent=2,sort_keys=True)+'\n')
PY
for f in package-delta.json security-summary.json n8n.spdx.json n8n.grype.json n8n.provenance.json order-paid-runtime-smoke.txt recovery-schedule-runtime-smoke.txt recovery-replay-runtime-smoke.txt; do test -f "$OUT/$f"; done
echo FROZEN_N8N_2_37_10_SNOWFLAKE_PRUNED_SECURITY_RUNTIME_GATE=PASS | tee "$OUT/final-gate.txt"
