# SiteScore AI — FAZ 7.1 Container, Supply-Chain and GitHub Governance Record

## Status

```text
PHASE: FAZ 7
CHECKPOINT: 7.1
CHECKPOINT_TITLE: Reproducible Containers + Supply Chain + GitHub Governance
BASE_BRANCH: main
BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
PR: #34
STATE: IMPLEMENTATION_IN_PROGRESS
USER_LOCK_AUTHORIZED: NO
FAZ_7_2_STARTED: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

This record documents production-container and source-control supply-chain boundaries only. It does not authorize production deployment, scoring readiness, empirical validation, DigitalOcean resource creation, or FAZ 7.2.

Canonical product statement remains:

> Mathematically validated scoring engine; empirical validation pending.

`COMB-005` remains `NOT_APPROVED`; the approved composition registry remains empty and a real analysis may legitimately terminate `not_score_ready`.

The Reviewer terminal-closure policy dated 2026-09-07 supersedes the earlier moving-latest n8n selection language in this record and the historical n8n 2.33.4 identity in `docs/FAZ7_PRODUCTION_RUNTIME_CONTRACT.md` section 4.6 for the FAZ 7.1 release candidate. That older identity remains historical evidence only.

## 1. Canonical application images

SiteScore builds two application images and one frozen automation image:

```text
ghcr.io/metadoks/sitescore-api
ghcr.io/metadoks/sitescore-commerce
ghcr.io/metadoks/sitescore-n8n
```

All target exactly:

```text
linux/amd64
```

One API image supplies the `api-web`, `api-worker`, and `api-beat` roles. One Commerce image supplies the `commerce-web` and `commerce-dispatcher` roles. Role differences are launch-command differences, not application-byte forks.

The n8n image is a deterministic FAZ 7.1 hardened candidate built from the exact frozen upstream n8n 2.37.10 source identity and the exact authorized Snowflake-only capability reduction described below. It does not change frozen SiteScore workflow JSON bytes.

No `latest`, staging, or production tag is deployment authority. A human-readable `sha-<full-source-SHA>` tag may be published after LOCK, but the authoritative deployment identity is the immutable registry digest.

## 2. Python/base-image identity

```text
Python: 3.11.16
Base tag: python:3.11.16-slim-bookworm
Base digest: sha256:2e32f7d302adc1c37428355c1e646897c0c53f4fd60b6a551245fb90ee129f91
Target platform: linux/amd64
Debian snapshot: 20260821T000000Z
Deployment-only ASGI server: uvicorn==0.52.1
Runtime UID:GID: 10001:10001
```

`uvicorn` is a deployment/runtime dependency only. Frozen `sitescore-api` and `sitescore-commerce` package metadata are not modified by 7.1.

The Dockerfiles are multi-stage. Frozen SiteScore packages are built from repository-local source as wheels using pinned build tooling with `--no-build-isolation`, then installed `--no-deps`. Third-party runtime resolution is provided by hashed lock files and installed with `pip --require-hashes`.

The final runtime images do not intentionally include compiler/build-tool/test source merely because builder/test stages require them.

## 3. Dependency and native-runtime locks

Canonical lock/evidence inputs include:

```text
deploy/containers/base-image.lock
deploy/containers/build-tools.lock
deploy/containers/test-tools.lock
deploy/containers/supply-chain-tools.lock
deploy/containers/api/requirements.lock
deploy/containers/api/apt-runtime.lock
deploy/containers/commerce/requirements.lock
deploy/containers/n8n-image.lock
deploy/containers/nodemailer-risk-record.md
deploy/containers/n8n-frozen-candidate-ci.sh
deploy/containers/n8n_prune_closure.py
deploy/containers/n8n_openvex_reconcile.py
```

Exact final SHA-256 identities for repository lock/evidence files remain **PENDING terminal exact-head validation** and must be recorded before `READY_FOR_REVIEW`.

The API native runtime is resolved from the fixed Debian snapshot and currently pins:

```text
fontconfig=2.14.1-4
fonts-dejavu-core=2.37-6
libffi8=3.4.4-1
libjpeg62-turbo=1:2.1.5-2
libopenjp2-7=2.5.0-2+deb12u3
libpango-1.0-0=1.50.12+ds-1
libpangoft2-1.0-0=1.50.12+ds-1
libharfbuzz-subset0=6.0.0+dfsg-3
shared-mime-info=2.2-1
```

This is the native support boundary for the frozen WeasyPrint/Matplotlib/PyProj/Shapely report runtime. Report CSS/source is not altered to satisfy containerization.

## 4. Runtime role commands

### API web

```text
python -m uvicorn sitescore_api.app:app --host 0.0.0.0 --port ${PORT} --workers 1
```

### API worker

```text
celery -A sitescore_api.tasks:celery_app worker --concurrency ${CELERY_CONCURRENCY:-1}
```

`CELERY_CONCURRENCY` must be a positive integer. Exact later production scaling belongs to FAZ 7.2/7.5.

### API beat

```text
celery -A sitescore_api.tasks:celery_app beat
```

Schedule and pid state are constrained to explicit writable paths under `/tmp`. Production intends exactly one beat scheduler instance.

### Commerce web

```text
python -m uvicorn sitescore_commerce.api:create_app --factory --host 0.0.0.0 --port ${PORT} --workers 1
```

### Commerce dispatcher

The frozen child command remains exactly:

```text
sitescore-commerce-dispatch-paid-outbox
```

`deploy/containers/runtime/commerce-dispatcher-supervisor.py` is an operations-only supervisor. It may repeat the one-shot child, sleep after success, apply bounded backoff after failure, and terminate the child on SIGTERM/SIGINT. It does not import `sitescore_commerce`, access Commerce PostgreSQL, parse business stdout, interpret order/outbox state, construct payloads, mint identifiers, or mark records published.

## 5. Runtime filesystem/non-root contract

Both SiteScore application images run as numeric:

```text
USER 10001:10001
```

The frozen n8n candidate must also prove a non-root runtime user.

Writable cache/runtime surfaces are directed under `/tmp`, including API Matplotlib/XDG cache behavior. CI must prove runtime `id -u`/`id -g` are non-zero and perform read-only-root style smoke execution with only explicit `/tmp` tmpfs writable where practical.

Production credentials are forbidden from Docker build args, baked `ENV`, layers, image config, history, SBOM evidence, or repository files.

## 6. API PDF/font contract

The API production candidate is not accepted on import success alone. CI must prove:

```text
sitescore_api import
sitescore_report import
weasyprint import
matplotlib import
shapely import
pyproj import
celery import
uvicorn import
Jinja2 == 3.1.6
matplotlib == 3.11.1
weasyprint == 69.0
uvicorn == 0.52.1
DejaVu Sans resolves through fontconfig
frozen visual-report rendering regression executes successfully
resulting frozen renderer path produces valid PDF bytes
```

The preferred frozen rendering regression remains `sitescore-report/tests/test_visual_report_rendering.py`.

## 7. Supply-chain tool identities

```text
Syft: anchore/syft:v1.44.0
Syft digest: sha256:86fde6445b483d902fe011dd9f68c4987dd94e07da1e9edc004e3c2422650de6
Grype: anchore/grype:v0.116.1
Grype digest: sha256:1e71065c0a4cff3e6bd3b8add525ffac4343eb4971694eb90a31cf6d4d3e85db
Cosign: ghcr.io/sigstore/cosign/cosign:v3.1.2
Cosign digest: sha256:d91bc4e7e95e8d2f549c747a72dc174f90579e410a1695f57f686674f84ce849
SBOM format: SPDX JSON
Provenance/signing mode: Cosign keyless with GitHub OIDC
```

Application-image vulnerability policy remains:

```text
CRITICAL -> FAIL / LOCK BLOCKER
HIGH with available fixed version -> FAIL / LOCK BLOCKER
blanket ignore -> forbidden
scanner disablement -> forbidden
```

The n8n candidate is governed by the stricter terminal policy in section 8, including OpenVEX and CISA KEV reconciliation.

## 8. Frozen n8n 2.37.10 candidate and security policy

FAZ 6 historical identity is preserved as historical evidence only:

```text
FAZ6_HISTORICAL_N8N_VERSION=2.33.4
FAZ6_HISTORICAL_N8N_DIGEST=sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
FAZ7_HISTORICAL_STATUS=SUPERSEDED_FOR_SECURITY
```

The historical image failed the FAZ 7.1 vulnerability gate. Reviewer subsequently froze the terminal FAZ 7.1 candidate boundary to:

```text
N8N_VERSION=2.37.10
N8N_SOURCE_COMMIT=5542b8b6419cb6925cca8f11b270c9bfbe09d85e
N8N_SOURCE_TREE=8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
N8N_OFFICIAL_AMD64_DIGEST_REFERENCE=sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
CANDIDATE_CUTOFF_DATE=2026-09-07
TARGET_PLATFORM=linux/amd64
```

Ordinary newer n8n patch releases after the cutoff do not automatically restart FAZ 7.1. Reopen is limited to the Reviewer emergency criteria: a candidate-present CISA KEV, a new undispositioned CRITICAL, a materially reachable vulnerability defeating the enabled SiteScore boundary, or inability to build/run the frozen candidate safely without broader design change.

The exact frozen build inputs additionally include:

```text
builder = node:26.5.1-alpine3.24@sha256:233761595746769ebfdb6090f44fc7cdf818ae0ce62d2b37e0367723b9823e36
runtime base = dhi.io/node:26.5.1-alpine3.24-dev@sha256:c4062f85acd1ca91ffb7d15048dcc5f15a922d630e65eb3c3c0dcdcef6ea36d8
pnpm = 11.22.0
fast-uri target = 3.1.6
fast-uri upstream-adoption reference = 33eb5c196e0ce3a2c71525929a4ef861cb94b168
```

The authorized capability reduction is exactly:

```text
n8n-nodes-base@2.37.4
└─ snowflake-sdk@2.1.0
   └─ toml@3.0.0
```

Required deterministic package delta:

```text
removed = [snowflake-sdk@2.1.0, toml@3.0.0]
added = []
version_changes = []
shared_non_snowflake_removed = []
n8n-nodes-base@2.37.4 = PRESENT exactly once
```

The hardened image must retain:

```text
NODES_EXCLUDE =
  n8n-nodes-base.executeCommand
  n8n-nodes-base.localFileTrigger
  n8n-nodes-base.emailSend
  n8n-nodes-base.snowflake
```

Frozen SiteScore workflow bytes remain authority and may not change:

```text
sitescore-order-paid-v1.json SHA256 = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
sitescore-recovery-schedule-v1.json SHA256 = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

Terminal n8n security evidence must prove at the exact candidate run:

```text
CISA KEV = 0
blocking CRITICAL = 0
OS HIGH = 0
fast-uri vulnerable findings = 0
ip-address vulnerable findings = 0
brace-expansion vulnerable findings = 0
toml vulnerable findings = 0
Snowflake vulnerable closure = absent
no new undispositioned HIGH introduced by hardening
SPDX generated
raw Grype generated
exact-release upstream OpenVEX asset digest verified
provenance generated
```

The previously-reviewed `nodemailer@8.0.10` HIGH associated with `GHSA-p6gq-j5cr-w38f` may remain only as the sole residual HIGH exception if all recorded containment controls remain true. Zero residual nodemailer findings is also acceptable. No second residual HIGH/CRITICAL exception is authorized.

SiteScore-authored VEX, blanket scanner suppression, blanket CVE ignores, unrelated dependency upgrades, incompatible TOML overrides, Snowflake application-source patching, alternate CI, and self-hosted-runner workarounds remain forbidden.

## 9. Permanent PR CI

Canonical PR validation workflow:

```text
.github/workflows/faz7-container-ci.yml
workflow name = faz7
required aggregate context = faz7 / required-gate
```

Logical mandatory gates include:

```text
source/frozen-byte boundary
dispatcher supervisor tests
n8n static tests
API/report/Commerce applicable regressions
FAZ6 Commerce exact-base replay
linux/amd64 API + Commerce image builds
non-root/runtime/role/socket smokes
API PDF/font proof
API/Commerce/n8n SPDX SBOM generation
application vulnerability policy
frozen n8n 2.37.10 source/build/prune/runtime/security gate
image history/config secret sanity
full-SHA Actions dependency pinning
```

`required-gate` uses `if: always()` semantics and accepts only `success` from every mandatory upstream job; skipped mandatory jobs are not accepted.

## 10. Post-LOCK GHCR publication

Canonical publishing workflow:

```text
.github/workflows/faz7-publish-images.yml
trigger = push to main
```

It is a publication workflow, not a deployment workflow. It uses repository `GITHUB_TOKEN` for GHCR and GitHub OIDC for keyless Cosign signing/attestation.

After LOCK/merge, it publishes exactly the immutable linux/amd64 application and automation candidates:

```text
ghcr.io/metadoks/sitescore-api:sha-<full-main-SHA>
ghcr.io/metadoks/sitescore-commerce:sha-<full-main-SHA>
ghcr.io/metadoks/sitescore-n8n:sha-<full-main-SHA>
```

The n8n publication path rebuilds and revalidates the exact frozen candidate from `deploy/containers/n8n-image.lock`, pushes that validated local image, resolves the registry digest, and requires the pulled published image ID to equal the exact locally validated image ID before signing/attesting it. Published n8n SBOM evidence must still show `n8n-nodes-base@2.37.4`, no `snowflake-sdk`, and no `toml@3.0.0`.

All three published digest subjects receive SPDX and provenance attestations and keyless Cosign signatures. No DigitalOcean deployment is performed by this workflow.

Authoritative post-LOCK identities are not yet available:

```text
API_GHCR_DIGEST=PENDING_POST_LOCK_MAIN_PUBLISH
COMMERCE_GHCR_DIGEST=PENDING_POST_LOCK_MAIN_PUBLISH
N8N_GHCR_DIGEST=PENDING_POST_LOCK_MAIN_PUBLISH
SBOM_PROVENANCE_EVIDENCE=PENDING_POST_LOCK_MAIN_PUBLISH
```

These future exact digests become FAZ 7.2 staging inputs only after post-lock verification.

## 11. GitHub governance target

Entry state at `main@fff9cb2...`:

```text
main protected = false
required checks = none
merge commit = enabled
squash merge = enabled
rebase merge = enabled
auto-merge = disabled
```

Required 7.1 final state remains:

```text
pull request before merge = required
status checks before merge = required
required check = faz7 / required-gate
strict/up-to-date with main = required
force pushes = blocked
branch deletion = blocked
administrative bypass = disabled where repository capability supports enforcement
merge commit = enabled
squash merge = disabled
rebase merge = disabled
auto-merge = disabled
linear-history requirement = disabled
```

Live governance mutation is **PENDING**. This document must not be interpreted as proof that branch protection has already been applied.

## 12. Validation baselines to record before review

Required terminal exact-head evidence remains:

```text
API current suite = 114 PASS
Report current suite = 24 PASS
Commerce forward applicable = 416 PASS with only the known phase-local provenance test deselected
FAZ6 frozen Commerce base replay = 417 PASS
n8n static = 12 PASS
dispatcher supervisor = 7 PASS
API image linux/amd64 = PASS
Commerce image linux/amd64 = PASS
n8n frozen candidate linux/amd64 = PASS
SiteScore image non-root = PASS
n8n non-root = PASS
API PDF/font/runtime = PASS
Commerce web/runtime = PASS
n8n startup/import/order-paid/recovery smokes = PASS
Snowflake node unavailable = PASS
CISA KEV = 0
blocking CRITICAL = 0
OS HIGH = 0
forbidden npm-family vulnerable findings = 0
no new undispositioned HIGH
only the authorized nodemailer residual if still present and containment passes
API/Commerce/n8n SPDX SBOM = generated
raw Grype evidence = generated
OpenVEX reconciliation = complete
provenance = complete
image history/config secret sanity = PASS
permanent Actions uses full-SHA = PASS
faz7 / required-gate = PASS on exact final head
main protection/governance = required final state
cloud mutation = NONE
production secrets committed/injected = NONE
```

Exact terminal run/job/artifact IDs remain **PENDING final-head hosted execution**.

## 13. Current hosted-Actions execution condition

As of 2026-09-11, exact-head PR workflow runs are still being accepted by GitHub but mandatory jobs terminate before normal hosted-runner execution with no step graph (`steps = null`). This record therefore does not claim terminal CI PASS.

The required owner acceptance criterion is that a new/rerun exact-head job enters ordinary GitHub-hosted runner execution and exposes normal steps/logs. Project policy forbids weakening `faz7 / required-gate`, changing CI providers, or using a self-hosted runner as a workaround.

## 14. Deferred scope

Explicitly deferred beyond 7.1:

```text
DigitalOcean App Platform deployment
OpenTofu infrastructure
Managed PostgreSQL/Valkey/Spaces creation
VPC/trusted-source wiring
Cloudflare/Better Stack configuration
production/staging secret injection
capacity tuning
observability/SLO implementation
backup/restore/DR drills
staging E2E/load/failure drills
FAZ 7.2+
```

No item in this document authorizes those actions.
