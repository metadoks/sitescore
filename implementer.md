# SiteScore AI — Implementer → Reviewer Handoff

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
CHECKPOINT_TITLE: Reproducible Containers + Supply Chain + GitHub Governance
IMPLEMENTER_STATE: BLOCKED_ON_GITHUB_ACTIONS_EXECUTION
IMPLEMENTER_ACTION: STOP
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
LIVE_MAIN_AT_LAST_CONFIRMED_CHECK: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
PR_STATE: OPEN
PR_DRAFT: TRUE
PR_MERGEABLE_AT_LAST_CHECK: TRUE
PR_MERGED: FALSE
CURRENT_HEAD_SHA: 519fcaa8013bc1146d0827b343a027108e76951f
CURRENT_CHANGED_FILE_COUNT: 20

PRIMARY_BLOCKER_ID: OPS71-GHA-EXEC-001
PRIMARY_BLOCKER_CLASS: GITHUB_ACTIONS_PRE_STEP_EXECUTION_GATE
PRIMARY_BLOCKER_STATUS: OPEN
SECONDARY_BLOCKER_ID: OPS71-N8N-VULN-001
SECONDARY_BLOCKER_STATUS: REOPEN_AUTHORIZED_REPLACEMENT_SELECTION_INCOMPLETE

DESIGN_DECISION_REVIEW_REQUIRED: 1
CONTRACT_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO

FAZ6_HISTORICAL_N8N_VERSION: 2.33.4
FAZ6_HISTORICAL_N8N_DIGEST: sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
FAZ7_HISTORICAL_N8N_STATUS: SUPERSEDED_FOR_SECURITY
NEW_N8N_BASELINE_STATUS: CANDIDATE_NOT_FROZEN
SELECTED_N8N_VERSION: NONE
SELECTED_N8N_DIGEST: NONE

APPLICATION_SOURCE_CHANGE: NONE
BUSINESS_SEMANTICS_CHANGE: NONE
N8N_WORKFLOW_JSON_CHANGE: NONE
CLOUD_RESOURCE_MUTATION: NONE
PRODUCTION_SECRET_COMMITTED: NONE
FAZ_7_2_STARTED: NO
MERGE_PERFORMED: NO
```

## 1. Reviewer security reopen remains accepted

Reviewer authorized a narrow n8n security-baseline reopen for `OPS71-N8N-VULN-001`. Historical FAZ 6 n8n `2.33.4` remains immutable historical evidence and is marked `SUPERSEDED_FOR_SECURITY`. Replacement remains restricted to the lowest official stable upstream `n8nio/n8n` release above the historical baseline that proves exact Linux/AMD64 digest, non-root runtime, loadability, raw `CRITICAL=0`, raw `HIGH=0`, no scanner suppression, and unchanged frozen workflow bytes.

## 2. First replacement probe produced valid partial security evidence

Exact first probe:

```text
RUN: 32562552155
JOB: 97006283464
PROBE_SOURCE_SHA: 831a91ade37214b849abb136b5286c1b5443de36
ARTIFACT: faz7-7-1-n8n-candidate-probe
ARTIFACT_ID: 9473402160
ARTIFACT_DIGEST: sha256:bcd62f5c66198c5d0aa56e6e9d6e3132e56c8fac0e25a27e0c74d19844b3be47
```

Verified rejected candidates, scanned with the pinned Grype 0.116.1 toolchain:

```text
2.33.5  sha256:24610830a7fda8cd84e6dcb004b858621191005c7d33c9e54f2adaeef1fcfc64  CRITICAL=4 HIGH=34 REJECTED
2.33.6  sha256:3a880a65b1f0d20c1b76bd4bf873bafb04131cdb678f80c8f34e2792ed0918fa  CRITICAL=4 HIGH=34 REJECTED
2.33.7  sha256:07a786a066e9230486a885da346e56b29c62fc2719560f1b5480afc55b70c09e  CRITICAL=4 HIGH=34 REJECTED
2.34.4  sha256:4c0c54bb6d89b2c7123c6c53d8ed6cba69263e165916560fa49a64a9b07674b6  CRITICAL=4 HIGH=34 REJECTED
2.34.5  sha256:7e82936bc03d310ddb8759c361f4e225412f0c3daad8d4b4e0d10c7e034c1b11  CRITICAL=4 HIGH=34 REJECTED
```

The first probe did **not** prove that no acceptable stable candidate exists. It failed while beginning `2.34.6` because the GitHub-hosted runner exhausted local disk:

```text
Grype database activation failed: database or disk is full
GitHub warning: free space left = 11 MB
```

Therefore candidate selection must resume strictly above `2.34.5`; the historical/rejected versions do not need to be rescanned for selection.

## 3. New GitHub Actions execution blocker

A disk-bounded resume probe was committed at exact SHA:

```text
9d5f99a4e211a0136862979d537e5e1eba3b5733
```

Its workflow run:

```text
RUN: 32567312841
created_at: 2026-08-22T10:19:33Z
updated_at: 2026-08-22T10:19:37Z
```

failed in approximately four seconds before the `enumerate` job executed any step. Connector evidence returns `steps=[]` for the failed `enumerate` job and the dependent scan job was skipped.

The permanent `faz7` workflow shows the same pre-step failure pattern: on run `32563254742`, `source-boundary`, `static-contracts`, `container-validation`, `n8n-validation`, and `faz6-commerce-replay` all concluded failure without executable step evidence.

This pattern prevents Implementer from obtaining the mandatory exact-final-head evidence. Available repository APIs do not expose the account billing/budget reason, so Implementer does **not** assert a specific billing root cause. The observed blocker is recorded only as `GITHUB_ACTIONS_PRE_STEP_EXECUTION_GATE`.

GitHub Actions execution is mandatory for 7.1 because the Reviewer contract requires the permanent `faz7 / required-gate` context green on the exact final head. The Implementer cannot substitute an unexecuted workflow definition for runtime evidence.

The temporary resume-probe workflow was removed after documenting the failure. Current PR tree is back to the 20 intended permanent files.

## 4. Repository-governance capability blocker

The Reviewer contract also requires before `READY_FOR_REVIEW`:

```text
main branch protection = ON
require pull request = ON
required status check = faz7 / required-gate
strict/up-to-date required checks = ON
force push = BLOCKED
branch deletion = BLOCKED
merge commits = ENABLED
squash merge = DISABLED
rebase merge = DISABLED
auto-merge = DISABLED
```

Live `main` was last observed unprotected, with merge/squash/rebase all enabled and auto-merge disabled. The currently available GitHub connector exposes repository reads and PR/file mutations but no branch-protection/ruleset or repository merge-setting mutation action. Plugin discovery for a branch-protection/settings capability returned no installable match.

Because both Actions execution and governance mutation are mandatory gates and the Implementer cannot autonomously choose a paid Actions budget, self-hosted runner strategy, alternate CI platform, manual governance procedure, or weaker protection model, Reviewer design disposition is required.

## 5. Permanent 7.1 implementation already present

Current PR permanent changed files remain exactly 20 paths under the Reviewer-authorized container/supply-chain/documentation scope:

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

Implemented but not yet accepted as final evidence:

```text
python:3.11.16-slim-bookworm@sha256:2e32f7d302adc1c37428355c1e646897c0c53f4fd60b6a551245fb90ee129f91
linux/amd64 target
hash-locked third-party Python dependencies
repo-local SiteScore wheels with --no-deps --no-build-isolation
Debian snapshot 20260821T000000Z
numeric runtime UID:GID 10001:10001
API web/worker/beat launchers
Commerce web launcher
Commerce dispatcher supervisor + SUP-001..SUP-007 tests
API PDF/font/runtime verifier
permanent workflow name = faz7
required context = faz7 / required-gate
post-LOCK GHCR publish/sign/attest workflow
```

No frozen application/business/workflow source bytes have been changed.

## 6. Required disposition

Implementer STOP.

Reviewer must decide the allowed resolution for `OPS71-GHA-EXEC-001` and the governance-mutation capability gap. Possible resolutions may involve account-level GitHub Actions budget/billing remediation, an explicitly authorized runner strategy, or an explicitly authorized manual/alternate governance procedure; Implementer must not choose among these autonomously.

After the execution environment is restored and Reviewer authorizes the path, n8n candidate scanning must resume above `2.34.5`; then the full exact-final-head 7.1 validation must run. No merge is authorized. No user LOCK is requested. FAZ 7.2 and FAZ 8 remain unauthorized.
