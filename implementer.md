# SiteScore AI — Implementer → Reviewer Handoff

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
CHECKPOINT_TITLE: Reproducible Containers + Supply Chain + GitHub Governance
IMPLEMENTER_STATE: IMPLEMENTING_AFTER_N8N_SECURITY_REOPEN
IMPLEMENTER_ACTION: CONTINUE_7_1
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
LIVE_MAIN_AT_LAST_CHECK: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
PR_STATE: OPEN
PR_DRAFT: TRUE
PR_MERGEABLE_AT_LAST_CHECK: TRUE
PR_MERGED: FALSE
CURRENT_HEAD_SHA: 18a182e8956d86b908e194f6f79f719a9d1646e6
CURRENT_CHANGED_FILE_COUNT: 20

BLOCKER_ID: OPS71-N8N-VULN-001
BLOCKER_CLASS: FROZEN_N8N_SUPPLY_CHAIN_VULNERABILITY_POLICY
BLOCKER_DISPOSITION: NARROW_SECURITY_BASELINE_REOPEN_AUTHORIZED
REVIEWER_DECISION: AUTHORIZE_N8N_SECURITY_BASELINE_REOPEN
REPLACEMENT_SELECTION_STATUS: IN_PROGRESS
DESIGN_DECISION_REVIEW_REQUIRED: 0
CONTRACT_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO

FAZ6_HISTORICAL_N8N_VERSION: 2.33.4
FAZ6_HISTORICAL_N8N_DIGEST: sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
FAZ7_HISTORICAL_N8N_STATUS: SUPERSEDED_FOR_SECURITY
NEW_N8N_BASELINE_STATUS: CANDIDATE_NOT_FROZEN
SELECTED_N8N_VERSION: PENDING_CANDIDATE_PROBE
SELECTED_N8N_DIGEST: PENDING_CANDIDATE_PROBE

APPLICATION_SOURCE_CHANGE: NONE
BUSINESS_SEMANTICS_CHANGE: NONE
N8N_WORKFLOW_JSON_CHANGE: NONE
CLOUD_RESOURCE_MUTATION: NONE
PRODUCTION_SECRET_COMMITTED: NONE
FAZ_7_2_STARTED: NO
MERGE_PERFORMED: NO
```

## 1. Reviewer security-reopen decision accepted

Reviewer changed the prior blocker disposition from `DESIGN_DECISION_REVIEW_REQUIRED` to an authorized narrow security baseline reopen.

The historical FAZ 6 n8n identity remains historical evidence and is not erased or rewritten. The replacement must remain official upstream `n8nio/n8n`, stable, exact `linux/amd64` digest, non-root, operationally loadable, and must satisfy the stronger replacement gate:

```text
raw CRITICAL = 0
raw HIGH = 0
```

No scanner suppression, custom n8n rebuild, workflow JSON mutation, or silent baseline substitution is authorized.

## 2. Candidate discovery evidence currently executing

The first exact discovery probe remains GitHub Actions run:

```text
RUN: 32562552155
JOB: 97006283464
PROBE_SOURCE_SHA: 831a91ade37214b849abb136b5286c1b5443de36
STATUS_AT_LAST_CHECK: IN_PROGRESS
```

The probe enumerates official non-draft/non-prerelease `n8n@X.Y.Z` releases strictly above historical `2.33.4`, scans in ascending semantic-version order, resolves the exact `linux/amd64` manifest digest, proves a non-root runtime user, and uses the pinned Grype toolchain. Selection is permitted only for the first stable candidate with zero raw HIGH and zero raw CRITICAL findings.

Temporary bootstrap/candidate workflows have been removed from the current PR tree. Their historical Actions evidence remains available; they are not being claimed as permanent FAZ 7.1 workflows.

If no acceptable official stable candidate exists, implementation must stop again with `DESIGN_DECISION_REVIEW_REQUIRED: 1`.

## 3. Current permanent repository scope

Current PR changed files at head `18a182e8956d86b908e194f6f79f719a9d1646e6` are exactly:

```text
.dockerignore
.github/workflows/faz7-container-ci.yml
.github/workflows/faz7-publish-images.yml
deploy/containers/api/Dockerfile
deploy/containers/api/apt-runtime.lock
deploy/containers/api/requirements.lock
deploy/containers/base-image.lock
deploy/containers/build-tools.lock
deploy/containers/commerce/Dockerfile
deploy/containers/commerce/requirements.lock
deploy/containers/runtime/api-beat.sh
deploy/containers/runtime/api-web.sh
deploy/containers/runtime/api-worker.sh
deploy/containers/runtime/commerce-dispatcher-supervisor.py
deploy/containers/runtime/commerce-web.sh
deploy/containers/supply-chain-tools.lock
deploy/containers/test-tools.lock
deploy/containers/tests/test_dispatcher_supervisor.py
deploy/containers/verify_image_contract.py
docs/FAZ7_1_CONTAINER_SUPPLY_CHAIN_GOVERNANCE.md
```

No `sitescore-*` application package source, package metadata, Alembic migration, scoring/finance/business logic, or `automation/n8n/workflows/*.json` file is in the current PR diff.

## 4. Reproducible container boundary implemented so far

Canonical image targets:

```text
ghcr.io/metadoks/sitescore-api
ghcr.io/metadoks/sitescore-commerce
platform = linux/amd64
runtime UID:GID = 10001:10001
```

Base image authority:

```text
python:3.11.16-slim-bookworm@sha256:2e32f7d302adc1c37428355c1e646897c0c53f4fd60b6a551245fb90ee129f91
Debian snapshot = 20260821T000000Z
uvicorn = 0.52.1 deployment-only
```

Third-party Python dependencies are hash-locked; local SiteScore packages are wheel-built from the repository with `--no-deps --no-build-isolation`; final runtime layers are distinct from test/builder stages. API native packages are fixed from the Debian snapshot and include DejaVu/fontconfig/Pango-family support for frozen PDF rendering.

## 5. Runtime role boundary implemented

Canonical operations-owned launchers now exist for:

```text
api-web
api-worker
api-beat
commerce-web
commerce-dispatcher
```

The Commerce dispatcher supervisor fixes the child executable to `sitescore-commerce-dispatch-paid-outbox`, uses bounded sleep/backoff, handles SIGTERM/SIGINT, and contains no `sitescore_commerce` import, business database access, business-state interpretation, stdout parsing, payload construction, identifier creation, or mark-published logic.

Seven unit tests encode SUP-001 through SUP-007.

## 6. Permanent CI/publish boundary implemented

Permanent PR workflow:

```text
.github/workflows/faz7-container-ci.yml
workflow name = faz7
aggregate context = faz7 / required-gate
```

The aggregate is `if: always()` and requires all mandatory upstream results to be exactly `success`.

Permanent post-LOCK publication workflow:

```text
.github/workflows/faz7-publish-images.yml
trigger = push to main
```

It publishes only SHA-derived GHCR tags, resolves exact digests, generates/validates SBOM and vulnerability evidence, and performs keyless Cosign signing/attestation with GitHub OIDC. It contains no DigitalOcean deployment.

Post-LOCK GHCR digests do not exist as authoritative evidence yet and must not be claimed before a user-authorized merge and successful main publication run.

## 7. Remaining mandatory 7.1 work

Before `READY_FOR_REVIEW`, implementation still must complete and prove:

```text
1. exact acceptable n8n replacement version + linux/amd64 digest
2. deploy/containers/n8n-image.lock candidate identity
3. authorized n8n runtime identity coherence updates only
4. n8n static/runtime/SBOM/raw 0 HIGH / 0 CRITICAL validation
5. exact final-head API 114 PASS
6. exact final-head Report 24 PASS
7. exact final-head Commerce 416 PASS + one known phase-local deselect
8. FAZ6 frozen Commerce exact-base replay 417 PASS
9. dispatcher supervisor 7 PASS
10. API/Commerce linux/amd64 build/non-root/runtime/PDF/font/socket evidence
11. API/Commerce SBOM + vulnerability policy evidence
12. permanent faz7 / required-gate PASS on exact final head
13. exact lock-file SHA256 record
14. branch protection / required-check enforcement
15. merge-method governance: merge-only, squash/rebase/auto-merge disabled
16. final diff/scope/no-secret/no-cloud proof
```

GitHub `main` was still unprotected at the last live check. No governance success is claimed yet.

## 8. Historical blocker evidence retained

Historical frozen n8n scan evidence remains:

```text
RUN: 32560317363
JOB: 97000785115
ARTIFACT: faz7-7-1-bootstrap-evidence
ARTIFACT_ID: 9472649384
ARTIFACT_DIGEST: sha256:4e8b07fb00c00b7e1e25e7a8fcc4a20c6c1f9d20f9f16df83cd41b4013bd9d5e
HISTORICAL_RAW_CRITICAL: 4
HISTORICAL_RAW_HIGH: 34
HISTORICAL_POLICY_BLOCKERS: 30
```

This evidence is why the historical FAZ 6 n8n runtime is `SUPERSEDED_FOR_SECURITY`; it does not authorize changing frozen n8n workflow business semantics.

No merge has been performed. No LOCK is requested. FAZ 7.2 and FAZ 8 remain unauthorized.
