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
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
IMPLEMENTER_ACTION: OWNER_ACTION_REQUIRED_RESTORE_GITHUB_HOSTED_ACTIONS_EXECUTION
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
PR_STATE: OPEN
PR_DRAFT: TRUE
PR_MERGEABLE_AT_LAST_CHECK: TRUE
PR_MERGED: FALSE
CURRENT_HEAD_SHA: 4c7bdabdc2e3198ce57d6b39404ddad149c3d2ca
CURRENT_CHANGED_FILE_COUNT: 25

OPS71_GHA_EXEC_001_STATUS: REOPENED_EXTERNAL_ACCOUNT_OR_PLATFORM_EXECUTION_BLOCKER_CONFIRMED_ON_EXACT_CURRENT_HEAD
OPS71_GOV_001_STATUS: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71_N8N_VULN_001_STATUS: FROZEN_2_37_10_PERMANENT_HARDENING_AND_PUBLICATION_MECHANICS_COMPLETE_PENDING_REAL_HOSTED_EXECUTION

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
MERGE_PERFORMED: NO
FAZ_7_2_STARTED: NO

FROZEN_N8N_VERSION: 2.37.10
FROZEN_N8N_NODES_BASE_VERSION: 2.37.4
APPLICATION_SOURCE_CHANGE: NONE
BUSINESS_SEMANTICS_CHANGE: NONE
N8N_WORKFLOW_JSON_CHANGE: NONE
SCANNER_SUPPRESSION: NONE
BLANKET_CVE_IGNORE: NONE
SITE_SCORE_AUTHORED_VEX: NONE
ALTERNATIVE_CI_USED: NONE
SELF_HOSTED_RUNNER_USED: NONE
CLOUD_RESOURCE_MUTATION: NONE
PRODUCTION_SECRET_COMMITTED: NONE
```

---

## 1. Reviewer terminal policy consumed

FAZ 7.1 remains frozen to the exact 2026-09-07 candidate boundary:

```text
n8n runtime version = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
official amd64 digest reference = sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
cutoff date = 2026-09-07
```

The authoritative internal package identity is distinct from the n8n runtime version:

```text
n8n 2.37.10
└─ n8n-nodes-base@2.37.4
   └─ snowflake-sdk@2.1.0
      └─ toml@3.0.0
```

The verifier now correctly preserves `n8n-nodes-base@2.37.4` exactly once. The earlier temporary assumption that this internal package should be `2.37.10` was corrected before terminal execution.

Authorized deterministic removal remains exactly:

```text
removed = [snowflake-sdk@2.1.0, toml@3.0.0]
added = []
version_changes = []
shared_non_snowflake_removed = []
```

No moving-latest rebase was performed.

---

## 2. Permanent hardening mechanics now present on PR #34

The formerly probe-only n8n mechanics are now permanent FAZ 7.1 assets:

```text
deploy/containers/n8n-image.lock
deploy/containers/n8n-frozen-candidate-ci.sh
deploy/containers/n8n_prune_closure.py
deploy/containers/n8n_openvex_reconcile.py
deploy/containers/nodemailer-risk-record.md
```

Permanent `n8n-validation` now owns:

```text
exact frozen source commit/tree binding
exact builder/runtime-base identities
fast-uri 3.1.6 upstream-adopted backport
production graph materialization
Snowflake/TOML exclusive-closure proof
exact two-package prune
hardened runtime-base construction
linux/amd64 proof
non-root proof
NODES_EXCLUDE proof
startup / health / node-type proof
frozen workflow imports
SPDX generation
raw Grype generation
exact-release OpenVEX digest verification
CISA KEV reconciliation
terminal n8n security policy
order-paid runtime smoke
recovery schedule runtime smoke
recovery replay runtime smoke
provenance evidence
```

The frozen SiteScore workflow JSON files were not modified.

---

## 3. Post-LOCK publication permanentized

`.github/workflows/faz7-publish-images.yml` now publishes all three immutable subjects after LOCK/main merge:

```text
ghcr.io/metadoks/sitescore-api:sha-<main-SHA>
ghcr.io/metadoks/sitescore-commerce:sha-<main-SHA>
ghcr.io/metadoks/sitescore-n8n:sha-<main-SHA>
```

The n8n path rebuilds and fully validates the frozen candidate, pushes the exact validated image, resolves the registry digest, then requires:

```text
published image ID == locally validated candidate image ID
runtime version == 2.37.10
architecture == linux/amd64
required NODES_EXCLUDE entries present
published SPDX contains n8n-nodes-base@2.37.4
published SPDX contains no snowflake-sdk
published SPDX contains no toml@3.0.0
```

API, Commerce and n8n published digest subjects all receive keyless Cosign signatures plus SPDX and provenance attestations.

No deployment or cloud resource mutation is performed by the publish workflow.

---

## 4. Normative FAZ 7.1 record aligned

`docs/FAZ7_1_CONTAINER_SUPPLY_CHAIN_GOVERNANCE.md` now records the terminal frozen-candidate model and explicitly supersedes the historical n8n 2.33.4 identity in the older FAZ 7.0 runtime contract for the FAZ 7.1 candidate.

The updated record now captures:

```text
n8n 2.37.10 frozen source identity
n8n-nodes-base@2.37.4 package identity
Snowflake/TOML exact prune
NODES_EXCLUDE boundary
OpenVEX + CISA KEV policy
authorized nodemailer residual containment
n8n GHCR post-LOCK publication/signing/attestation
```

---

## 5. Preserved accepted evidence

Earlier real hosted runs established and remain useful historical evidence:

```text
source-boundary = PASS
static-contracts = PASS
FAZ6 Commerce replay = PASS
API regression = 114 PASS
report regression = 24 PASS
Commerce = 416 PASS + exactly one authorized phase-local deselect
frozen application source semantics change = NONE
frozen n8n workflow JSON change = NONE
Snowflake/TOML exclusive production closure = PROVEN
package delta = exactly two authorized removals
```

These historical passes are not represented as terminal exact-current-head evidence. Current-head terminal CI remains required.

---

## 6. Exact current-head GitHub-hosted Actions blocker

Current code head:

```text
4c7bdabdc2e3198ce57d6b39404ddad149c3d2ca
```

Current changed-file count:

```text
25
```

No temporary probe/patcher workflow remains in the PR.

Latest exact-head PR workflow:

```text
run = 34581786484
```

GitHub accepted and parsed the workflow, created all mandatory jobs, then every job terminated before ordinary hosted-runner step execution:

```text
n8n-validation        job 103206801712 -> failure, steps = null
source-boundary       job 103206801836 -> failure, steps = null
static-contracts      job 103206801973 -> failure, steps = null
faz6-commerce-replay  job 103206801996 -> failure, steps = null
container-validation job 103206802006 -> failure, steps = null
required-gate         job 103206819156 -> failure, steps = null
```

This is the same pre-run failure signature repeatedly observed on previous exact heads. No current-head SiteScore test failure, Docker failure, package-graph failure, vulnerability failure, shell error, or runtime error can be inferred because ordinary runner execution never began and no step graph/logs were produced.

The available GitHub API does not expose the account/UI pre-run reason. No unsupported assertion is made that the cause is specifically billing, quota, plan entitlement, account restriction, or another named GitHub condition.

---

## 7. Consolidated owner action

Owner must open run `34581786484` in the GitHub Actions UI and resolve the pre-run account/platform message presented by GitHub.

Acceptance criterion:

```text
new/rerun exact-head GitHub-hosted job enters normal runner execution
AND
ordinary job steps/logs are produced instead of immediate steps = null failure
```

Forbidden workarounds remain:

```text
weaken faz7 / required-gate
remove mandatory jobs
switch CI provider
use self-hosted runner
change frozen SiteScore business/application semantics
change frozen n8n workflow JSON
advance to FAZ 7.2
merge without Reviewer READY_TO_LOCK + literal user LOCK
```

When hosted execution is restored, Implementer should run the permanent exact-head pipeline and correct only genuine mechanical issues supported by real runner logs. The terminal handoff can become `READY_FOR_REVIEW` only after full current-head evidence and final governance verification are complete.

---

## 8. Live state

```text
PR #34 = OPEN / DRAFT / MERGEABLE / UNMERGED
base = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
head = 4c7bdabdc2e3198ce57d6b39404ddad149c3d2ca
changed files = 25
temporary probe workflows = NONE
temporary fixer workflows = NONE
frozen application source diff = NONE
frozen n8n workflow JSON diff = NONE
post-LOCK n8n publication mechanics = PERMANENTIZED
terminal current-head hosted evidence = BLOCKED BEFORE RUNNER EXECUTION
```

```text
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
USER_LOCK_AUTHORIZED: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```
