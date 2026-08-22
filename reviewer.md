# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
CHECKPOINT_TITLE: Reproducible Containers + Supply Chain + GitHub Governance
REVIEWER_STATE: CONTRACT_ISSUED
IMPLEMENTER_ACTION: IMPLEMENT_CHECKPOINT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: TBD
REVIEWED_HEAD_SHA: NONE

FAZ_7_0_STATUS: LOCKED_VERIFIED
FAZ_7_0_PR: #33
FAZ_7_0_REVIEWED_HEAD: 106e392b4143818298fd9ea9dcbb06def5ad3de8
FAZ_7_0_MERGE_COMMIT: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
FAZ_7_0_MERGE_TREE: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
OPS70_H001_H004: CLOSED_OR_RESOLVED

MAIN_BRANCH_PROTECTED_AT_7_1_ENTRY: FALSE
REQUIRED_STATUS_CHECKS_AT_7_1_ENTRY: NONE
REPO_ALLOW_MERGE_COMMIT: TRUE
REPO_ALLOW_SQUASH_MERGE: TRUE
REPO_ALLOW_REBASE_MERGE: TRUE
CANONICAL_PRODUCTION_DOCKER_ASSETS_AT_ENTRY: NONE_OBSERVED
PERMANENT_GITHUB_ACTIONS_WORKFLOWS_AT_ENTRY: NONE_OBSERVED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

---

# 1. FAZ 7.0 POST-LOCK VERIFICATION

Reviewer independently verified the user-authorized FAZ 7.0 merge before opening 7.1.

Live GitHub proof:

```text
PR #33 = CLOSED / MERGED
reviewed head = 106e392b4143818298fd9ea9dcbb06def5ad3de8
merge commit = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
live main = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
merge tree = 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
parent 1 = 3762ec643426e310ff82bdb00b20f58fb4ae9e09
parent 2 = 106e392b4143818298fd9ea9dcbb06def5ad3de8
```

The merge commit is GitHub-verified and its message records user-authorized LOCK against the exact Reviewer-approved head.

Disposition:

```text
FAZ 7.0: LOCKED_VERIFIED
FAZ 7.1: AUTHORIZED TO IMPLEMENT
```

No FAZ 7.2 work is authorized by this contract.

---

# 2. CHECKPOINT PURPOSE

FAZ 7.1 creates the first canonical production-candidate container and source-control supply-chain boundary for SiteScore AI.

This checkpoint must establish all of the following without changing frozen application/business semantics:

```text
1. reproducible Linux/AMD64 production images for SiteScore API and Commerce
2. exact runtime launch commands for web / worker / beat / dispatcher roles
3. non-root runtime images
4. deterministic dependency resolution with immutable base-image inputs
5. frozen n8n image-digest verification and scan evidence
6. permanent PR CI for container build/runtime/supply-chain validation
7. post-LOCK main publishing path to GHCR by immutable digest
8. SBOM + vulnerability scan + provenance/attestation evidence
9. GitHub main-branch protection / required checks
10. repository merge-method governance compatible with exact-head LOCK protocol
```

FAZ 7.1 must **not** create DigitalOcean resources, deploy App Platform services, configure PostgreSQL/Valkey/Spaces, create OpenTofu stacks, configure Cloudflare/Better Stack, or perform production/staging deployment.

---

# 3. FROZEN AUTHORITY — MUST NOT MOVE

All 7.0 authority boundaries remain mandatory:

```text
Stripe = external processor evidence
Commerce PostgreSQL = durable commercial truth
SiteScore API/PostgreSQL = analysis/report durable truth
Redis/Valkey/Celery = execution/transport only
n8n = orchestration only
Postmark = email transport/provider evidence
Spaces = report artifact byte storage only
```

Analytical composition remains:

```text
COMB-005 approval_state = NOT_APPROVED
approved registry = ()
weights = ()
composition = UNRESOLVED
real production may legitimately terminate not_score_ready
```

Canonical product statement remains:

```text
Mathematically validated scoring engine; empirical validation pending.
```

Containerization, successful image build, vulnerability scan, SBOM generation, loadability, CI success or GHCR publication must never be represented as empirical business validation or score readiness.

---

# 4. ENTRY BASELINE / SOURCE FACTS

Reviewer independently reverified at `main@fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7`:

```text
main protected = false
required status-check enforcement = off
canonical production Dockerfile set = not observed
permanent .github/workflows directory/workflows = not observed
repository merge settings:
  merge commit = enabled
  squash merge = enabled
  rebase merge = enabled
  auto-merge = disabled
```

Current runtime source facts:

```text
sitescore-api == 0.3.0
sitescore-commerce == 0.6.0
sitescore-report == 0.3.0
n8n == 2.33.4
```

API and Commerce do **not** currently pin an ASGI server in their package metadata. 7.1 therefore owns a deployment-level ASGI runtime dependency, without modifying frozen package metadata.

The selected deployment ASGI server for 7.1 is:

```text
uvicorn == 0.52.1
```

It is a deployment/runtime dependency only. Do not add it to frozen `sitescore-api` or `sitescore-commerce` `pyproject.toml` in this checkpoint.

Current report CSS explicitly depends on:

```text
DejaVu Sans
```

and current renderer requires exact runtime versions:

```text
Jinja2 3.1.6
matplotlib 3.11.1
weasyprint 69.0
```

The API image must therefore prove that its Linux runtime includes the required native/font dependencies and can execute the frozen PDF renderer successfully.

---

# 5. PLATFORM / BUILD COMPATIBILITY CONTRACT

Current selected-platform facts rechecked for 7.1:

```text
DigitalOcean App Platform supports GHCR container images.
DigitalOcean App Platform production image target is Linux AMD64.
DigitalOcean App Platform can consume image digests and recommends digest use for immutable deployment identity.
GHCR supports publication from GitHub Actions with repository GITHUB_TOKEN and packages:write.
GitHub recommends immutable full-length commit-SHA pinning for Actions dependencies.
GitHub supports artifact attestations for container image provenance and SBOM subjects.
```

Therefore production-candidate application images in 7.1 must target exactly:

```text
linux/amd64
```

Do not treat ARM64-only or multi-arch success as sufficient proof for App Platform.

---

# 6. AUTHORIZED PERMANENT REPOSITORY SCOPE

Permanent 7.1 changes are limited to production-container/supply-chain/governance assets under these paths:

```text
.dockerignore

deploy/containers/build-tools.lock
deploy/containers/api/Dockerfile
deploy/containers/api/requirements.lock
deploy/containers/commerce/Dockerfile
deploy/containers/commerce/requirements.lock

deploy/containers/runtime/api-web.sh
deploy/containers/runtime/api-worker.sh
deploy/containers/runtime/api-beat.sh
deploy/containers/runtime/commerce-web.sh
deploy/containers/runtime/commerce-dispatcher-supervisor.py

deploy/containers/tests/test_dispatcher_supervisor.py
deploy/containers/verify_image_contract.py

.github/workflows/faz7-container-ci.yml
.github/workflows/faz7-publish-images.yml

docs/FAZ7_1_CONTAINER_SUPPLY_CHAIN_GOVERNANCE.md
```

Minor helper files below `deploy/containers/` are allowed only when directly necessary for the above build/verification flow and must be enumerated in `implementer.md`.

Still forbidden without a new Reviewer decision:

```text
sitescore-core/**
sitescore-data/**
sitescore-providers/**
sitescore-spatial/**
sitescore-metrics/**
sitescore-benchmarks/**
sitescore-pipeline/**
sitescore-app/**
sitescore-report/**
sitescore-api/**
sitescore-commerce/**
automation/n8n/workflows/**
automation/n8n/runtime/docker-compose.yml
Alembic migrations/package versions/business routes/scoring logic
OpenTofu/Terraform
DigitalOcean App specs/resources
Cloudflare/Better Stack config
production/staging secrets
```

If correct containerization proves impossible without modifying frozen source/package metadata, stop and report:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

Do not opportunistically patch application code.

---

# 7. APPLICATION IMAGE MODEL

Create exactly two canonical SiteScore-built application images:

```text
ghcr.io/metadoks/sitescore-api
ghcr.io/metadoks/sitescore-commerce
```

n8n is **not rebuilt** by SiteScore in 7.1. It remains the frozen upstream image identity:

```text
n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
```

7.1 must pull/inspect/scan that exact n8n digest and include it in supply-chain evidence. Do not silently upgrade or retag to a different digest.

## 7.1 API image

One immutable API image must serve all three runtime roles from identical application bytes:

```text
api-web
api-worker
api-beat
```

Required exact command semantics:

```text
api-web:
  python -m uvicorn sitescore_api.app:app
  --host 0.0.0.0
  --port ${PORT}
  --workers 1

api-worker:
  celery -A sitescore_api.tasks:celery_app worker
  bounded concurrency
  deployment may set exact concurrency in 7.2/7.5

api-beat:
  celery -A sitescore_api.tasks:celery_app beat
  one scheduler instance only
  any beat schedule/pid files must use an explicitly writable ephemeral path such as /tmp
```

The launch scripts must use `exec` where appropriate so Uvicorn/Celery receives termination signals directly.

Do not enable multiple Uvicorn process workers inside one container. Horizontal service replicas belong to App Platform/capacity policy later.

## 7.2 Commerce image

One immutable Commerce image must serve:

```text
commerce-web
commerce-dispatcher
```

Required command semantics:

```text
commerce-web:
  python -m uvicorn sitescore_commerce.api:create_app
  --factory
  --host 0.0.0.0
  --port ${PORT}
  --workers 1
```

The dispatcher process must execute the operations-owned supervisor described below.

---

# 8. COMMERCE DISPATCHER SUPERVISOR CONTRACT

The frozen console command remains:

```text
sitescore-commerce-dispatch-paid-outbox
```

It remains one-shot. The 7.1 supervisor exists only to repeatedly invoke it as an App Platform worker process.

Required supervisor properties:

```text
business package imports: FORBIDDEN
Commerce DB access by supervisor: FORBIDDEN
payment/order/outbox state interpretation: FORBIDDEN
stdout business-state parsing: FORBIDDEN
alternate payload construction: FORBIDDEN
outbox ID creation/mutation: FORBIDDEN
mark-published logic: FORBIDDEN
```

The child executable must be fixed to the frozen console script, not arbitrary operator input.

Permitted behavior:

```text
spawn frozen one-shot command
rc == 0 -> short bounded sleep then next invocation
rc != 0 -> bounded exponential/backoff delay then retry
SIGTERM/SIGINT -> stop loop, propagate/terminate child cleanly, exit
reset backoff after successful child execution
log only operational state / exit code / backoff duration
never log secret environment values
```

Using the same short sleep for `EMPTY` and `PUBLISHED` is acceptable and preferred to parsing business output.

Unit tests must prove:

```text
SUP-001 child command is fixed
SUP-002 success resets backoff
SUP-003 failure backoff is bounded
SUP-004 no busy loop on success/failure
SUP-005 SIGTERM/SIGINT stop behavior
SUP-006 no sitescore_commerce import/business call in supervisor
SUP-007 no environment dump/secret logging
```

---

# 9. BASE IMAGE / DEPENDENCY REPRODUCIBILITY

Application images must use an exact CPython 3.11 patch-level Linux base and immutable digest.

Target family:

```text
python:3.11.16-slim-bookworm@sha256:<resolved immutable digest>
```

If that exact image is not available or fails compatibility, choose another exact Python 3.11 patch-level slim Debian image only after recording the reason. A floating `python:3.11`, `python:3.11-slim`, `latest`, unpinned distro tag, or digest-less production base is forbidden.

Required build behavior:

```text
base image digest pinned
linux/amd64 build
multi-stage build
no apt-get upgrade
no curl | sh installer
no mutable latest dependencies
no pip install --upgrade pip without exact pin/hash
no build isolation that can silently fetch a new setuptools version
```

Use pinned build tooling from `deploy/containers/build-tools.lock` and `--no-build-isolation` where local package wheels are built.

The final runtime image must not contain compilers/build-essential/package-manager caches merely because the builder needed them.

## 9.1 Python lock requirements

Both `requirements.lock` files must contain exact resolved versions and hashes sufficient for:

```text
pip install --require-hashes
```

The lock must cover transitive runtime dependencies, not only direct `pyproject.toml` pins.

API lock must include all external runtime requirements needed by the local package chain plus:

```text
uvicorn==0.52.1
```

Commerce lock must include Commerce external runtime requirements plus:

```text
uvicorn==0.52.1
```

Frozen SiteScore packages should be built as local wheels from the exact repository source and installed `--no-deps`; the external lock remains the resolution authority for third-party dependencies.

Do not publish internal packages to PyPI and do not replace local package lineage with arbitrary remote packages of the same name.

---

# 10. API NATIVE/PDF RUNTIME CONTRACT

The API image must prove that frozen report generation works inside the production runtime layer.

At minimum ensure the image supplies runtime support for:

```text
WeasyPrint 69.0 native libraries
Matplotlib runtime
PyProj/Shapely runtime
Fontconfig/Pango-family libraries as actually required
DejaVu Sans
```

Do not modify report CSS or rendering source to make the image pass.

Required validation inside the built API image:

```text
python imports:
  sitescore_api
  sitescore_report
  weasyprint
  matplotlib
  shapely
  pyproj
  celery

runtime-version assertions:
  Jinja2 == 3.1.6
  matplotlib == 3.11.1
  weasyprint == 69.0

font proof:
  DejaVu Sans resolves in the container

PDF proof:
  frozen visual-report rendering test path executes successfully in an equivalent build/test stage or against the built runtime with test fixture support
  generated bytes begin with valid PDF signature
```

Preferred source regression proof:

```text
sitescore-report/tests/test_visual_report_rendering.py
```

Do not declare API image production-candidate merely because imports succeed while PDF rendering fails.

---

# 11. NON-ROOT / FILESYSTEM / SECRET HYGIENE

Both SiteScore application images must run as an explicit non-root numeric UID/GID.

Required:

```text
Config.User != empty
runtime id -u != 0
application source/wheels not writable by runtime user
no SSH server
no package-manager cache
no embedded Git credentials
no production secrets in ENV/ARG/history/layers
```

Set writable runtime/cache directories explicitly for libraries that need them, for example under `/tmp`, including Matplotlib/font/cache behavior as required.

Image smoke validation should test a read-only-root style invocation where practical, with only explicitly permitted `/tmp` writable space. Failure caused by hidden writes outside allowed runtime paths is a blocker to container readiness.

No `STRIPE_SECRET_KEY`, DB URL, Valkey credential, Postmark token, OpenAI key, API key pepper, automation key, n8n ingress secret or Spaces secret may be supplied as Docker build args or baked environment values.

---

# 12. OCI METADATA / IMAGE IDENTITY

Both SiteScore-built images must carry OCI labels including at least:

```text
org.opencontainers.image.source=https://github.com/metadoks/sitescore
org.opencontainers.image.revision=<exact source commit>
org.opencontainers.image.version=<SHA-derived immutable release/candidate identity>
org.opencontainers.image.title=<sitescore-api|sitescore-commerce>
```

No `latest` tag is authoritative.

Tagging policy:

```text
human-readable SHA tag may exist
DIGEST is deployment authority
mutable staging/prod/latest tags are not release authority
```

Later 7.2 App Platform specs must consume exact image digests, not floating tags.

---

# 13. PERMANENT GITHUB ACTIONS — PR CONTAINER CI

Create `.github/workflows/faz7-container-ci.yml`.

Trigger at minimum:

```text
pull_request -> main
push -> the active FAZ 7.1 branch is acceptable only while building this checkpoint if needed
```

Do **not** use `pull_request_target` for build/test of PR-controlled code.

Workflow permissions must be least privilege; PR validation should normally require only:

```text
contents: read
```

and any additional write permission must be justified by an explicit feature.

Every `uses:` dependency must be pinned to a full immutable 40-character commit SHA. Version tags such as `@v4`, `@main` or floating refs are forbidden in permanent supply-chain workflows.

The PR workflow must perform these logical gates:

```text
A. exact source/frozen-tree boundary check
B. dispatcher-supervisor unit tests
C. current API/report/Commerce/n8n applicable regression checks
D. linux/amd64 API image build
E. linux/amd64 Commerce image build
F. application image runtime/non-root/smoke checks
G. API PDF-render proof
H. SBOM generation
I. vulnerability scanning
J. n8n exact-digest pull/inspect/scan
K. image secret/history sanity
L. required-gate aggregation
```

Use one stable final required check context, recommended exact job display name:

```text
faz7 / required-gate
```

The aggregator must use `if: always()` or equivalent and fail unless every mandatory upstream gate is success. Do not let a skipped mandatory job satisfy the aggregate accidentally.

---

# 14. REGRESSION POLICY FOR 7.1

Frozen package/source bytes are not authorized to change; prove this first by base-to-head path diff.

In addition, before READY_FOR_REVIEW run at least:

```text
sitescore-api current suite -> expected 114 PASS
sitescore-report current suite -> expected 24 PASS
sitescore-commerce current applicable forward suite -> 416 PASS with only the known FAZ6 phase-local provenance test deselected
n8n static suite -> expected 12 PASS
```

The known phase-local Commerce test is:

```text
sitescore-commerce/tests/test_faz6_final_freeze_gate.py::test_final_candidate_is_based_on_corrective_locked_main_and_permanent_diff_is_audit_only
```

Do not delete, weaken or rewrite that test.

Also replay the exact FAZ 6 frozen Commerce base once during checkpoint validation and record:

```text
FAZ6 frozen base Commerce = 417/417 PASS
```

Current lower-package source trees are unchanged; a full lower-package rerun may be included but does not replace the required path-diff proof and image runtime proof.

---

# 15. SBOM / VULNERABILITY / PROVENANCE POLICY

For each of:

```text
sitescore-api image
sitescore-commerce image
frozen n8n digest
```

generate/store reviewable SBOM and vulnerability evidence.

Preferred SBOM format:

```text
SPDX JSON
```

Application image SBOMs must include OS + Python packages visible in final runtime layers.

Vulnerability gate:

```text
CRITICAL vulnerability -> FAIL / LOCK BLOCKER
HIGH vulnerability with an available fixed version -> FAIL / LOCK BLOCKER
blanket ignore list -> FORBIDDEN
scanner disablement -> FORBIDDEN
```

If a HIGH/CRITICAL issue is present in the frozen n8n digest or a dependency where fixing it would require changing a frozen version/business baseline, stop and report:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

Do not silently upgrade frozen n8n or frozen SiteScore packages to make the scanner green.

Any narrowly justified vulnerability exception must name:

```text
CVE/advisory
package/version
fix availability
runtime reachability rationale
expiry/review checkpoint
```

and requires Reviewer review before LOCK.

---

# 16. POST-LOCK GHCR PUBLISH / ATTESTATION WORKFLOW

Create `.github/workflows/faz7-publish-images.yml`.

This workflow may run on:

```text
push to protected main
```

It may build/publish images but **must not deploy them**.

Required permissions for the publishing job should be narrowly scoped to the actual GitHub-native flow, including only as needed:

```text
contents: read
packages: write
id-token: write
attestations: write
```

GHCR publication must authenticate with the repository `GITHUB_TOKEN`, not a long-lived PAT, for publishing images owned by this repository.

Publish:

```text
ghcr.io/metadoks/sitescore-api
ghcr.io/metadoks/sitescore-commerce
```

The workflow must output/record exact image digests.

Generate build provenance and SBOM attestation for each final image digest using GitHub-supported artifact attestation capability or an equivalently reviewable signed provenance mechanism.

Do not deploy to DigitalOcean in this workflow.

Post-LOCK Reviewer verification for 7.1 will require:

```text
main merge SHA
reviewed PR head SHA
API GHCR digest
Commerce GHCR digest
SBOM/provenance evidence
successful vulnerability gate
```

Those digests become authoritative 7.2 staging image inputs.

---

# 17. N8N SUPPLY-CHAIN CONTRACT

Do not rebuild n8n.

Required validation target is exactly:

```text
n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
```

Prove at minimum:

```text
resolved digest is exact frozen digest
Linux/AMD64 support is available for deployment target
runtime user is non-root or image inspection proves safe non-root runtime identity
SBOM generated
vulnerability scan completed under the same severity policy
frozen workflow JSON hashes remain unchanged
```

If the exact frozen digest cannot satisfy the mandatory production platform/security requirement, stop; do not substitute another n8n tag/digest.

---

# 18. GITHUB MAIN-BRANCH GOVERNANCE

7.1 explicitly authorizes repository-governance mutation after permanent CI exists and has produced the required status context.

Current entry state is insecure for production governance:

```text
main protected = false
required checks = none
merge commit = enabled
squash = enabled
rebase = enabled
```

Before READY_FOR_REVIEW, configure `main` through a GitHub ruleset or branch-protection rule that proves at least:

```text
require pull request before merge = ON
require status checks before merge = ON
required check includes exact permanent `faz7 / required-gate` context
required checks strict/up-to-date with main = ON
force pushes = BLOCKED
deletions = BLOCKED
administrative bypass = DISABLED where repository capability supports enforcement
```

If the account/repository plan cannot enforce the mandatory controls, stop with:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

Do not silently accept an unprotected `main`.

## 18.1 Merge-method compatibility with SiteScore LOCK protocol

The SiteScore protocol verifies merge parentage:

```text
parent 1 = pre-merge main
parent 2 = exact Reviewer-reviewed head
```

Therefore repository merge settings must become:

```text
merge commits = ENABLED
squash merge = DISABLED
rebase merge = DISABLED
auto-merge = DISABLED
```

Do **not** require linear history; it conflicts with the merge-commit parentage audit model.

Do **not** add a mandatory GitHub approval count merely to simulate the independent Reviewer chat. Semantic approval remains:

```text
Reviewer READY_TO_LOCK exact SHA
+
literal user LOCK
```

GitHub protection is an additional technical barrier, not a replacement for semantic LOCK authority.

---

# 19. SUPPLY-CHAIN DOCUMENTATION ARTIFACT

`docs/FAZ7_1_CONTAINER_SUPPLY_CHAIN_GOVERNANCE.md` must record:

```text
checkpoint base SHA/tree
application image names
base image tag+digest actually selected
Python version
uvicorn version
hashed lock file identities/SHA256
runtime UID/GID
exact role commands
native PDF/font dependencies
GHCR tag/digest policy
n8n frozen digest
SBOM format/tool/version
vulnerability scanner/tool/version/policy
GitHub action dependency SHAs
permanent workflow names/check contexts
main branch/ruleset configuration
repo merge-method configuration
known limitations/deferred items
```

It must distinguish:

```text
PR build evidence
post-LOCK main publication evidence
future 7.2 deployment
```

Do not claim GHCR image exists until it actually exists, and do not claim App Platform deployment in 7.1.

---

# 20. NO-SECRET / NO-CLOUD-MUTATION RULES

7.1 may use only GitHub-native ephemeral credentials required for CI/GHCR publication.

Forbidden:

```text
DigitalOcean API token usage
App Platform create/update/deploy
Managed PostgreSQL/Valkey/Spaces creation
Cloudflare API mutation
Better Stack mutation
Stripe/Postmark/OpenAI production credentials
production application secret injection
OpenTofu state creation
```

Docker build logs, SBOMs, attestations, image config/history and workflow artifacts must be checked for secret leakage.

---

# 21. REQUIRED VALIDATION EVIDENCE BEFORE READY_FOR_REVIEW

Implementer must provide exact evidence for the final PR head:

```text
1. BASE_SHA = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
2. exact final HEAD_SHA
3. PR number/state/base/head/mergeable
4. base-to-head diff --name-only/stat/check
5. frozen source/package/n8n workflow bytes unchanged
6. base-image exact digest(s)
7. hashed dependency lock verification
8. dispatcher supervisor unit tests PASS
9. API suite = 114 PASS
10. report suite = 24 PASS
11. Commerce forward-applicable = 416 PASS / one exact phase-local deselect
12. FAZ6 frozen-base Commerce replay = 417 PASS
13. n8n static = 12 PASS
14. API image linux/amd64 build PASS
15. Commerce image linux/amd64 build PASS
16. both SiteScore images non-root PASS
17. API PDF-render/font/runtime smoke PASS
18. Commerce web import/socket/route smoke PASS
19. API web/worker/beat command smoke PASS
20. dispatcher supervisor runtime smoke PASS
21. SBOM generated for API/Commerce/n8n
22. vulnerability policy PASS or explicit Reviewer decision required
23. image secret/history sanity PASS
24. all permanent Actions `uses:` full-SHA pinned
25. permanent PR workflow required-gate PASS on final head
26. live main protection = TRUE
27. required `faz7 / required-gate` check configured
28. force-push/deletion blocked
29. merge commit only; squash/rebase disabled; auto-merge disabled
30. no DigitalOcean/cloud/IaC deployment/resource mutation
31. no production secret committed/injected
```

If branch protection is configured after a successful CI run, re-fetch the PR to prove the current final head still satisfies the newly required check and remains mergeable once all protection requirements are met.

---

# 22. CHECKPOINT EXIT / STOP CONDITIONS

FAZ 7.1 may reach `READY_FOR_REVIEW` only if:

```text
canonical API/Commerce Docker assets exist
all base/dependency/runtime inputs are pinned strongly enough for deterministic rebuild intent
runtime images are non-root
API PDF renderer works in container
n8n frozen digest is supply-chain checked
SBOM/vulnerability/provenance path exists
permanent required CI is green on final head
main is protected
merge strategy matches exact-head merge-commit protocol
no frozen package/business authority changed
no cloud deployment occurred
no secrets leaked
```

If a platform, frozen runtime, or vulnerability issue makes this impossible, stop with the appropriate blocker/control flag.

Do not weaken a gate merely to obtain green CI.

---

# 23. IMPLEMENTER HANDOFF FORMAT

When implementation is complete, update `implementer.md` and stop with at least:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #N
HEAD_SHA: <exact final SHA>

API_IMAGE_BUILD: PASS
COMMERCE_IMAGE_BUILD: PASS
API_IMAGE_NONROOT: PASS
COMMERCE_IMAGE_NONROOT: PASS
API_PDF_RENDER_SMOKE: PASS
N8N_FROZEN_DIGEST_CHECK: PASS
SBOM_GATE: PASS
VULNERABILITY_GATE: PASS
FROZEN_SOURCE_DIFF: NONE

API_TESTS: 114 PASS
REPORT_TESTS: 24 PASS
COMMERCE_FORWARD_APPLICABLE: 416 PASS / 1 PHASE_LOCAL DESELECTED
FAZ6_COMMERCE_BASE_REPLAY: 417 PASS
N8N_STATIC: 12 PASS

MAIN_BRANCH_PROTECTED: TRUE
REQUIRED_CHECK: faz7 / required-gate
FORCE_PUSH: BLOCKED
BRANCH_DELETE: BLOCKED
MERGE_COMMIT: ENABLED
SQUASH_MERGE: DISABLED
REBASE_MERGE: DISABLED
AUTO_MERGE: DISABLED

CLOUD_RESOURCE_MUTATION: NONE
DIGITALOCEAN_DEPLOYMENT: NONE
PRODUCTION_SECRET_COMMITTED: NONE

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

Do not merge. Do not start FAZ 7.2.

Reviewer will independently inspect exact final PR head, workflow logs, image evidence, vulnerability/SBOM evidence and live GitHub governance, then issue:

```text
HARDENING_REQUIRED
```

or

```text
READY_TO_LOCK
```

Only literal user `LOCK` after exact-SHA `READY_TO_LOCK` authorizes merge.
