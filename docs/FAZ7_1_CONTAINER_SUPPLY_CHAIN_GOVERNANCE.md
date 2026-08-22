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

## 1. Canonical application images

SiteScore builds exactly two application images:

```text
ghcr.io/metadoks/sitescore-api
ghcr.io/metadoks/sitescore-commerce
```

Both target exactly:

```text
linux/amd64
```

One API image supplies the `api-web`, `api-worker`, and `api-beat` roles. One Commerce image supplies the `commerce-web` and `commerce-dispatcher` roles. Role differences are launch-command differences, not application-byte forks.

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

Canonical lock/evidence inputs:

```text
deploy/containers/base-image.lock
deploy/containers/build-tools.lock
deploy/containers/test-tools.lock
deploy/containers/supply-chain-tools.lock
deploy/containers/api/requirements.lock
deploy/containers/api/apt-runtime.lock
deploy/containers/commerce/requirements.lock
```

Exact final SHA-256 identities for these repository files are **PENDING final-head validation** and must be recorded before `READY_FOR_REVIEW`.

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

Application vulnerability policy remains:

```text
CRITICAL -> FAIL / LOCK BLOCKER
HIGH with available fixed version -> FAIL / LOCK BLOCKER
blanket ignore -> forbidden
scanner disablement -> forbidden
```

## 8. n8n historical identity and security reopen

FAZ 6 historical identity is preserved as historical evidence:

```text
FAZ6_HISTORICAL_N8N_VERSION=2.33.4
FAZ6_HISTORICAL_N8N_DIGEST=sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
FAZ7_HISTORICAL_STATUS=SUPERSEDED_FOR_SECURITY
```

The historical image failed the FAZ 7.1 vulnerability gate. Evidence run `32560317363`, job `97000785115`, artifact `faz7-7-1-bootstrap-evidence` recorded raw Grype findings including four CRITICAL and thirty-four HIGH findings.

Reviewer therefore authorized the narrow `OPS71-N8N-VULN-001` security baseline reopen. The replacement must be an official stable upstream `n8nio/n8n` release, selected as the lowest stable acceptable release above the historical baseline, resolved to an exact `linux/amd64` digest, non-root, operationally loadable, and scanned with:

```text
raw CRITICAL = 0
raw HIGH = 0
```

No vulnerability suppression or SiteScore-built n8n image is allowed.

Current replacement identity:

```text
SELECTED_N8N_VERSION=PENDING_CANDIDATE_PROBE
SELECTED_N8N_DIGEST=PENDING_CANDIDATE_PROBE
SELECTED_N8N_IMAGE=PENDING_CANDIDATE_PROBE
N8N_BASELINE_STATUS=CANDIDATE_NOT_FROZEN
```

The replacement becomes frozen only after Reviewer `READY_TO_LOCK` for the exact final PR head plus literal user `LOCK` and successful merge.

Frozen workflow bytes remain authority and may not change:

```text
sitescore-order-paid-v1.json SHA256 = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
sitescore-recovery-schedule-v1.json SHA256 = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

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
mandatory vulnerability policy
n8n exact candidate identity/runtime/security gate
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

It is a publication workflow, not a deployment workflow. It uses repository `GITHUB_TOKEN` for GHCR and GitHub OIDC for keyless Cosign signing/attestation. It builds only `linux/amd64`, publishes SHA-derived tags, resolves exact pushed digests, re-generates SBOM/vulnerability evidence against published digests, and signs/attests image subjects.

No DigitalOcean deployment is performed by this workflow.

Authoritative post-LOCK identities are not yet available:

```text
API_GHCR_DIGEST=PENDING_POST_LOCK_MAIN_PUBLISH
COMMERCE_GHCR_DIGEST=PENDING_POST_LOCK_MAIN_PUBLISH
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

Required final-head evidence remains:

```text
API current suite = 114 PASS
Report current suite = 24 PASS
Commerce forward applicable = 416 PASS with only the known phase-local provenance test deselected
FAZ6 frozen Commerce base replay = 417 PASS
n8n static = 12 PASS
dispatcher supervisor = 7 PASS
API image linux/amd64 = PASS
Commerce image linux/amd64 = PASS
SiteScore image non-root = PASS
API PDF/font/runtime = PASS
Commerce web/runtime = PASS
n8n replacement raw HIGH = 0
n8n replacement raw CRITICAL = 0
API/Commerce/n8n SPDX SBOM = generated
image history/config secret sanity = PASS
permanent Actions uses full-SHA = PASS
faz7 / required-gate = PASS on exact final head
main protection/governance = required final state
cloud mutation = NONE
production secrets committed/injected = NONE
```

Exact run/job/artifact IDs remain **PENDING final-head validation**.

## 13. Deferred scope

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
