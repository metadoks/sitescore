# SiteScore AI — Implementer → Reviewer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
CHECKPOINT_TITLE: Reproducible Containers + Supply Chain + GitHub Governance
IMPLEMENTER_STATE: BLOCKED_ON_EXTERNAL_GITHUB_PLATFORM_CONTROLS
IMPLEMENTER_ACTION: STOP_UNTIL_GITHUB_PLATFORM_REMEDIATED_THEN_RESUME_7_1
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
PRIMARY_BLOCKER_DISPOSITION: EXTERNAL_PLATFORM_REMEDIATION_REQUIRED
PRIMARY_BLOCKER_STATUS: OPEN

SECONDARY_BLOCKER_ID: OPS71-GOV-001
SECONDARY_BLOCKER_CLASS: GITHUB_GOVERNANCE_MUTATION_CAPABILITY
SECONDARY_BLOCKER_DISPOSITION: MANUAL_OWNER_GOVERNANCE_CONFIGURATION_AUTHORIZED
SECONDARY_BLOCKER_STATUS: PENDING_OWNER_CONFIGURATION_AFTER_REQUIRED_CONTEXT_EXISTS

N8N_BLOCKER_ID: OPS71-N8N-VULN-001
N8N_BLOCKER_DISPOSITION: SECURITY_REOPEN_REMAINS_AUTHORIZED
N8N_SELECTION_STATUS: INCOMPLETE_RESUME_ABOVE_2_34_5

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
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

## 1. Reviewer platform-remediation decision accepted

Reviewer independently verified `OPS71-GHA-EXEC-001` and issued:

```text
ROOT_CAUSE_CLASS: EXTERNAL_GITHUB_ACTIONS_EXECUTION_CONTROL
CODE_WORKAROUND_AUTHORIZED: NO
WEAKEN_REQUIRED_GATE: NO
REMOVE_REQUIRED_CI: NO
```

Normal GitHub-hosted Actions job execution must be restored for this private repository/account before FAZ 7.1 implementation can resume. A self-hosted runner or alternate CI platform is not authorized by the current addendum.

The account/repository owner may remediate the actual GitHub-side budget, billing, spending-limit, Actions enablement, policy, or hosted-runner availability issue shown by GitHub UI. No source-code change is authorized as a substitute.

## 2. Restoration recheck performed after Reviewer decision

Implementer did not change repository source. The existing exact-head permanent workflow run was used to test whether GitHub-hosted execution had recovered.

```text
WORKFLOW_RUN: 32567387440
RERUN_REQUESTED_JOB_ORIGINAL_ID: 97017896387
RERUN_REQUEST_ACCEPTED_BY_GITHUB: YES
RERUN_SOURCE_BOUNDARY_JOB_ID: 97018560486
RERUN_INITIAL_STATE: QUEUED
RERUN_FINAL_STATE: COMPLETED / FAILURE
RERUN_STEPS: NONE / null
```

The rerun briefly entered `queued` and then again failed before any executable workflow step was created. Other mandatory jobs in the same attempt also remained failures with no step evidence, and `required-gate` failed.

Disposition after recheck:

```text
OPS71-GHA-EXEC-001: STILL_OPEN
GITHUB_HOSTED_EXECUTION_RESTORED: NO
FAZ_7_1_RESUME_CONDITION_MET: NO
```

Implementer therefore remains stopped exactly as Reviewer required.

## 3. n8n security-reopen continuity

Historical FAZ 6 identity remains immutable historical evidence:

```text
version = 2.33.4
digest = sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
status = SUPERSEDED_FOR_SECURITY for FAZ 7 production-candidate purposes
```

First exact replacement probe evidence:

```text
RUN: 32562552155
JOB: 97006283464
PROBE_SOURCE_SHA: 831a91ade37214b849abb136b5286c1b5443de36
ARTIFACT: faz7-7-1-n8n-candidate-probe
ARTIFACT_ID: 9473402160
ARTIFACT_DIGEST: sha256:bcd62f5c66198c5d0aa56e6e9d6e3132e56c8fac0e25a27e0c74d19844b3be47
```

Validly rejected official stable candidates:

```text
2.33.5  sha256:24610830a7fda8cd84e6dcb004b858621191005c7d33c9e54f2adaeef1fcfc64  CRITICAL=4 HIGH=34 REJECTED
2.33.6  sha256:3a880a65b1f0d20c1b76bd4bf873bafb04131cdb678f80c8f34e2792ed0918fa  CRITICAL=4 HIGH=34 REJECTED
2.33.7  sha256:07a786a066e9230486a885da346e56b29c62fc2719560f1b5480afc55b70c09e  CRITICAL=4 HIGH=34 REJECTED
2.34.4  sha256:4c0c54bb6d89b2c7123c6c53d8ed6cba69263e165916560fa49a64a9b07674b6  CRITICAL=4 HIGH=34 REJECTED
2.34.5  sha256:7e82936bc03d310ddb8759c361f4e225412f0c3daad8d4b4e0d10c7e034c1b11  CRITICAL=4 HIGH=34 REJECTED
```

The first probe stopped while beginning 2.34.6 because the hosted runner reached approximately 11 MB free disk and Grype could not activate its database. That was a technical failure, not evidence that candidates above 2.34.5 are unacceptable.

Once normal Actions execution is restored, selection is authorized to resume strictly above `2.34.5`, choosing only the first official stable upstream candidate proving:

```text
linux/amd64 exact digest
non-root runtime
runtime loadability
raw CRITICAL = 0
raw HIGH = 0
frozen workflow JSON bytes unchanged
```

No scanner suppression, custom n8n rebuild, semantic workflow change, or silent retag is authorized.

## 4. Governance configuration path

Reviewer explicitly authorized repository-owner manual configuration because the available connector cannot mutate the required controls. The target remains mandatory:

```text
main pull request requirement = ON
required status checks = ON
required check = faz7 / required-gate
strict/up-to-date required checks = ON
force pushes = BLOCKED
branch deletion = BLOCKED
administrative bypass = DISABLED where capability permits
merge commits = ENABLED
squash merge = DISABLED
rebase merge = DISABLED
auto-merge = DISABLED
linear history = NOT REQUIRED
```

The exact required check must not be configured until GitHub has actually created the permanent `faz7 / required-gate` context through an executed workflow. Manual configuration is operational setup only; it is not source change, cloud deployment, user LOCK, or permission to merge.

If the repository/account plan cannot enforce a mandatory control, stop again with `OPS71-GOV-001: PLAN_CAPABILITY_BLOCKED` and `DESIGN_DECISION_REVIEW_REQUIRED: 1`.

## 5. Permanent PR scope retained

PR #34 remains on the intended 20 permanent paths:

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

No `sitescore-*` application source/package metadata, Alembic migration, scoring/finance/payment/report semantics, or `automation/n8n/workflows/*.json` file is changed.

## 6. STOP / resume conditions

Implementer STOP until normal GitHub-hosted Actions execution is demonstrably restored.

After restoration, the Reviewer addendum already authorizes continuation without another design decision:

```text
1. confirm live main still equals the expected base
2. resume n8n candidate scan above 2.34.5
3. select only first acceptable official stable 0 HIGH / 0 CRITICAL candidate
4. remove temporary probe machinery
5. run full permanent faz7 workflow on exact final head
6. prove all package/container/runtime/PDF/SBOM/vulnerability/regression gates
7. obtain exact faz7 / required-gate success
8. repository owner applies mandatory governance controls
9. live protection/settings are re-fetched and recorded
10. only then set IMPLEMENTER_STATE = READY_FOR_REVIEW and STOP
```

No merge is authorized. No user LOCK is requested. FAZ 7.2 and FAZ 8 remain unauthorized.
