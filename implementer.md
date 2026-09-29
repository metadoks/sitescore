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
IMPLEMENTER_STATE: LIBEXPAT_SECURITY_CORRECTIVE_READY_FOR_REVIEW
IMPLEMENTER_ACTION: REVIEWER_LIBEXPAT_CORRECTIVE_EXACT_HEAD_AUDIT_REQUIRED
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: dcd3f350fac54ab42ebf8ed8d35012c1125a87ed
CODE_BRANCH: faz7/7-1-libexpat-2-8-5-r0-security-corrective
PR: #36
PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE_AT_LAST_CHECK: TRUE
PR_MERGED: FALSE

CURRENT_HEAD_SHA: 2bf60b3af0c1d9f0357e5d7834c61751bd220601
REVIEWED_HEAD_SHA: PENDING_REVIEWER_AUDIT
MERGE_COMMIT_SHA: 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
LOCK_MERGED_AT_UTC: 2026-09-19T19:45:21Z
FINAL_GREEN_RUN: 35459207216
FINAL_GREEN_RUN_EVENT: push

CORRECTIVE_BASE_SHA: 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
CORRECTIVE_BRANCH: faz7/7-1-publish-policy-parity-corrective
CORRECTIVE_PR: #35
CORRECTIVE_PR_STATE: CLOSED
CORRECTIVE_PR_DRAFT: FALSE
CORRECTIVE_PR_MERGEABLE: TRUE
CORRECTIVE_PR_MERGED: TRUE
CORRECTIVE_HEAD_SHA: fffe943723b230d73d0afa079b736e06c0b3a6a4
CORRECTIVE_FINAL_GREEN_RUN: 35474113362
CORRECTIVE_REQUIRED_GATE_JOB: 105983845465
CORRECTIVE_APPLICATION_ARTIFACT_ID: 10594027965
CORRECTIVE_N8N_ARTIFACT_ID: 10594375006
CORRECTIVE_CHANGED_FILES: 1
CORRECTIVE_POLICY_PARITY: EXACT_SEMANTIC_MATCH_PLUS_NODE_26_7_0
CORRECTIVE_READY_FOR_REVIEW: YES
CORRECTIVE_READY_TO_LOCK: NO
CORRECTIVE_USER_LOCK_AUTHORIZED: NO
CORRECTIVE_MERGE_PERFORMED: NO

OPS71_GHA_EXEC_001_STATUS: RESOLVED_CONFIRMED
OPS71_GOV_001_STATUS: RESOLVED_LIVE_RULESET_VERIFIED
OPS71_APP_BASE_001_STATUS: RESOLVED_EXACT_REVIEWER_AUTHORIZED_RESIDUAL
OPS71_N8N_DHI_001_STATUS: RESOLVED_AUTHENTICATED_PULL_PASS
OPS71_N8N_VULN_001_STATUS: LIBEXPAT_2_8_5_R0_CORRECTIVE_GREEN_PENDING_REVIEW

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
READY_FOR_REVIEW: YES
READY_TO_LOCK: NO
MERGE_PERFORMED: YES
FAZ_7_2_STARTED: NO
PUBLIC_LAUNCH_AUTHORIZED: NO

APPLICATION_SOURCE_CHANGE: NONE
BUSINESS_SEMANTICS_CHANGE: NONE
N8N_SOURCE_COMMIT_CHANGE: NONE
N8N_SOURCE_TREE_CHANGE: NONE
N8N_WORKFLOW_JSON_CHANGE: NONE
SCANNER_SUPPRESSION: NONE
BLANKET_CVE_IGNORE: NONE
SITE_SCORE_AUTHORED_VEX: NONE
SECURITY_THRESHOLD_WEAKENING: NONE
ALTERNATIVE_CI_USED: NONE
SELF_HOSTED_RUNNER_USED: NONE
CLOUD_RESOURCE_MUTATION: NONE
PRODUCTION_SECRET_COMMITTED: NONE
```

---

## 0. Post-LOCK merge closure

User supplied the required literal `LOCK` authorization in the Implementer chat. Immediately before merge, live GitHub state was re-verified against the Reviewer handoff:

```text
REVIEWER_STATE = READY_TO_LOCK
IMPLEMENTER_ACTION = AWAIT_LITERAL_USER_LOCK_THEN_MERGE_EXACT_REVIEWED_HEAD
reviewed head = f54e3c25a0aca26782b94bb427a14744c6b6fa14
live PR head = f54e3c25a0aca26782b94bb427a14744c6b6fa14
base/main = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
PR #34 = OPEN / MERGEABLE / DRAFT before ready transition
faz7 / required-gate = SUCCESS
technical/security blockers = NONE
governance blockers = NONE
```

The PR was transitioned out of draft as authorized, re-read with the exact same head/base, and merged using GitHub's normal merge-commit path with exact-head protection:

```text
expected_head_sha = f54e3c25a0aca26782b94bb427a14744c6b6fa14
merge method = merge
merge result = SUCCESS
merge commit = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
merged at = 2026-09-19T19:45:21Z
```

Post-merge live verification:

```text
PR #34 = CLOSED / MERGED
main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
compare merge-commit...main = IDENTICAL
ahead = 0
behind = 0
reviewed PR head remained = f54e3c25a0aca26782b94bb427a14744c6b6fa14
FAZ_7_2_STARTED = NO
PUBLIC_LAUNCH_AUTHORIZED = NO
```

Implementer merge work is complete. Per protocol, the next authority is Reviewer post-merge verification of the resulting main/merge commit before FAZ 7.1 is declared `LOCKED_VERIFIED`.

## 1. One exact final green head/run

Exact head:

```text
f54e3c25a0aca26782b94bb427a14744c6b6fa14
```

Terminal GitHub-hosted run:

```text
run = 35459207216
event = push
status = COMPLETED
conclusion = SUCCESS

static-contracts      = SUCCESS  job 105939893814
faz6-commerce-replay  = SUCCESS  job 105939893861
source-boundary       = SUCCESS  job 105939893917
n8n-validation        = SUCCESS  job 105939893927
container-validation  = SUCCESS  job 105939893937
required-gate         = SUCCESS  job 105943963854
```

This run is on the exact current PR head. PR #34 remains open, draft, mergeable, and unmerged.

A duplicate pull_request-triggered run exists for the same exact head. At the last read its source-boundary/static/replay/container jobs were already SUCCESS while its duplicate n8n job was still in progress. It is not needed to establish the final green exact-head run because run 35459207216 is already fully terminal and green, including `required-gate`.

---

## 2. Exact-head artifacts

Application artifact:

```text
name = faz7-application-image-evidence-f54e3c25a0aca26782b94bb427a14744c6b6fa14
artifact_id = 10589397389
archive_sha256 = ee513e71bc05c6d3b453178b5e58156bf27ea3c7f49cc52f887d412517a51b66
```

n8n artifact:

```text
name = faz7-n8n-final-evidence-f54e3c25a0aca26782b94bb427a14744c6b6fa14
artifact_id = 10588888591
archive_sha256 = cc9519f68badb127b604cced62f5dbdd9b614573fbf3044883c82f7c41abc402
```

---

## 3. Final application security state

Application container-validation is GREEN on the exact final head.

Reviewer-authorized exact residual remains only:

```text
CVE-2026-82049
package = CPython 3.11.16
classification = REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
```

The exact application runtime identity remains:

```text
python:3.11.16-slim-trixie
sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72
DEBIAN_SUITE=trixie
target=linux/amd64
```

CI evidence proves the required reachability containment and keeps the raw Grype finding visible. Application policy blocker count is zero under the exact Reviewer-authorized classification.

All required application regressions/runtime gates remained green, including:

```text
API regression = PASS
report regression = PASS
Commerce regression = PASS with exactly one authorized deselect
FAZ6 Commerce replay = 417 PASS
non-root/read-only runtime = PASS
API web/worker/beat runtime = PASS
PDF/font runtime = PASS
Commerce runtime roles = PASS
SBOM/Grype/image hygiene = PASS
```

No generic Python HIGH waiver, scanner suppression, beta Python upgrade, or local CPython patch was introduced.

---

## 4. Final n8n security state

Frozen n8n identity remains unchanged:

```text
n8n version = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
target = linux/amd64
builder = Node 26.7.0 / Alpine 3.24 immutable digest
DHI runtime = Node 26.7.0 / Alpine 3.24 immutable digest
```

Final security summary on the exact green run:

```text
BLOCKING_CRITICAL = 0
BLOCKING_HIGH = 0
BLOCKING_HIGH_DETAILS = []
CISA_KEV = 0
ACTIONABLE_OS_HIGH = 0
NEW_UNDISPOSITIONED_HIGH = 0
```

Forbidden-package HIGH counts:

```text
adm-zip = 0
brace-expansion = 0
fast-uri = 0
git = 0
ip-address = 0
pcre2 = 0
snowflake-sdk = 0
toml = 0
```

Authorized exact residual HIGH set is bounded to four findings only:

```text
zlib 1.3.2-r0:
  CVE-2026-85091

nodemailer 8.0.10:
  GHSA-P6GQ-J5CR-W38F
  GHSA-2X7J-588G-CCC2

@tiptap/core 3.27.0:
  GHSA-J95F-988M-3J2F
```

No pcre2 residual remains.

---

## 5. adm-zip closure

Reviewer-authorized patch backport completed:

```text
adm-zip 0.6.0 -> 0.6.1
parent = epub2@3.0.2
parent major change = NONE
n8n source patch = NONE
```

Evidence includes:

```text
pnpm why --prod --recursive adm-zip
machine-generated parent/override proof
compiled adm-zip = 0.6.1
GHSA-7q85-xj36-vmfc finding = 0
```

No unrelated n8n source/workflow semantic change was made.

---

## 6. Git / pcre2 capability pruning closure

Frozen workflows were proven not to use:

```text
n8n-nodes-base.git
n8n-nodes-base.gitTool
```

Both are excluded from the final node inventory.

Explicit runtime package pruning removed:

```text
git
git-init-template
pcre2
```

Machine-derived pruning evidence proves the removals are the exact Git-capability set and no shared non-Git runtime package was removed.

Final scanner evidence:

```text
pcre2 HIGH = 0
CVE-2026-89161 = ABSENT
CVE-2026-89157 = ABSENT
git HIGH = 0
```

No manual pcre2 copy, edge repository mixing, third-party repo, scanner ignore, VEX waiver, or residual pcre2 classification was used.

---

## 7. Frozen n8n runtime/functionality evidence

The exact final n8n run completed all required tests and emitted:

```text
12 passed
N8N_RUNTIME_VERSION=2.37.10
N8N_WORKFLOW_IMPORT=PASS
N8N_PUBLISH_STATE_PROOF=PASS
N8N_WEBHOOK_AUTH=PASS
N8N_ORCHESTRATION_INTEGRATION=PASS
N8N_WAIT_RESTART=PASS
N8N_RECOVERY_WORKFLOW_IMPORT=PASS
N8N_RECOVERY_NATURAL_SCHEDULE_TRIGGER=PASS
N8N_RECOVERY_SINGLE_BOUNDED_CALL=PASS
N8N_RECOVERY_SCHEDULER_RUNTIME=PASS
N8N_RECOVERY_REPLAY_ANALYSIS_PENDING=PASS
N8N_RECOVERY_REPLAY_REPORT_PENDING=PASS
N8N_RECOVERY_REPLAY_REFUND_RESPONSE_LOSS=PASS
N8N_RECOVERY_REPLAY_DELIVERY_UNCERTAIN=PASS
N8N_RECOVERY_REPLAY_LOCKED_WORKFLOW_CONVERGENCE=PASS
FROZEN_N8N_2_37_10_SNOWFLAKE_PRUNED_SECURITY_RUNTIME_GATE=PASS
```

Official `export:nodes` evidence remains the node-inventory authority. Required `httpRequest` remains present while frozen excluded nodes, including Snowflake, emailSend, executeCommand, localFileTrigger, Git and Git Tool, remain absent.

---

## 8. Security remediation delta summary

The hardening sequence reduced the previously observed n8n terminal blocker from:

```text
blocking CRITICAL = 2
raw HIGH = 25
```

to the final exact-head accepted state:

```text
blocking CRITICAL = 0
blocking HIGH = 0
CISA KEV = 0
new undispositioned HIGH = 0
only exact Reviewer-authorized residuals remain
```

Major bounded remediations included:

```text
Node/DHI base refresh to 26.7.0
libcurl = 8.22.0-r0
fast-uri = 3.1.6
js-yaml = 4.3.2
multer authorized ^2.3.0 policy
@xmldom/xmldom = 0.8.15
adm-zip = 0.6.1
Git/Git Tool node exclusion
git/git-init-template/pcre2 runtime pruning
```

No security threshold was weakened.

---

## 9. Governance remains owner action

Latest live repository readback still shows:

```text
main protected = FALSE
rulesets = 0
allow_merge_commit = TRUE
allow_squash_merge = TRUE
allow_rebase_merge = TRUE
allow_auto_merge = FALSE
```

Required terminal governance remains:

```text
main protected = TRUE
PR required = TRUE
required check = faz7 / required-gate
strict = TRUE
force push blocked
deletion blocked
admin/bypass disabled where supported
merge commit enabled
squash merge disabled
rebase merge disabled
auto merge disabled
```

The available GitHub connector exposes readback but not the required branch-protection/repository-setting mutation. This remains the already-authorized manual owner action `OPS71-GOV-001`.

Governance is therefore NOT claimed complete and lock is NOT authorized.

---

## 10. Final Implementer decision

All code/security/CI work authorized for FAZ 7.1 is complete on one exact final green head/run.

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
EXACT_HEAD: f54e3c25a0aca26782b94bb427a14744c6b6fa14
FINAL_GREEN_RUN: 35459207216
required-gate: SUCCESS
TECHNICAL_SECURITY_BLOCKERS: NONE
OWNER_GOVERNANCE_ACTION: PENDING
READY_TO_LOCK: NO
USER_LOCK_AUTHORIZED: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
FAZ_7_2_STARTED: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

Required next step:

```text
Reviewer independently audits exact head f54e3c25a0aca26782b94bb427a14744c6b6fa14
and exact green run 35459207216.

Owner governance configuration remains pending and must be live-read back
before READY_TO_LOCK can ever be issued.
```

---

## Post-LOCK publish policy parity corrective — in progress

Reviewer authorized a single-file corrective after post-LOCK publication run `35465322918` failed only because the publish workflow still used the older generic application vulnerability policy.

Corrective implementation state:

```text
base main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
branch = faz7/7-1-publish-policy-parity-corrective
PR = #35
corrective head = f58160e9bc97581a026b0b871f108e6879ab8fe1
changed files = 1
changed path = .github/workflows/faz7-publish-images.yml
merge performed = NO
FAZ 7.2 started = NO
```

The publish workflow now mirrors the already-frozen permanent application security policy for published API/Commerce digests:

```text
exact authorized residual = CVE-2026-82049 / python 3.11.16 only
classification = REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX
CISA KEV reconciliation = required
archive-extraction reachability proof = required
public tar/tar.gz ingress proof = required
raw Grype finding = preserved
all other CRITICAL or HIGH-with-fix = blocking
exact residual count = 1 per API/Commerce image
```

No application/business source, Dockerfile/base/dependency, n8n identity, frozen workflow JSON, scanner suppression, blanket ignore, VEX, threshold weakening, or FAZ 7.2 change was made.

Corrective PR CI:

```text
run = 35469603489
source-boundary = SUCCESS
static-contracts = IN_PROGRESS
faz6-commerce-replay = IN_PROGRESS
n8n-validation = IN_PROGRESS
container-validation = QUEUED
required-gate = PENDING
```

Per Reviewer protocol, this corrective must not merge until the exact corrective head receives the normal Reviewer READY_TO_LOCK gate and a literal user LOCK for that corrective merge.


### Corrective self-review amendment

During exact-policy parity self-review, the first corrective commit was found to have over-escaped Python regex backslashes in the copied reachability block. That head/run is superseded and is NOT authoritative.

```text
superseded head = f58160e9bc97581a026b0b871f108e6879ab8fe1
superseded run = 35469603489
reason = copied regex/backslash semantics were not byte-semantic parity with frozen CI policy
```

The same authorized single-file scope was corrected by copying the frozen policy block exactly, changing only the evidence artifact directory from `application-images` to `publish`.

```text
authoritative corrective head = e1597f77bcc8a65e2e00e9c5573e028cdbee337b
PR = #35
changed files = 1
changed path = .github/workflows/faz7-publish-images.yml
pre-policy semantic parity = TRUE
scanner-policy semantic parity = TRUE
new PR run = 35470194681
merge performed = NO
```

Only the new exact head/run may be reviewed for corrective LOCK.


---

## POST-LOCK CORRECTIVE — AUTHORITATIVE TERMINAL IMPLEMENTER HANDOFF

The bounded publish-policy corrective is complete on one exact authoritative head. The earlier first corrective head/run remains superseded and is not review authority.

```text
base main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
branch = faz7/7-1-publish-policy-parity-corrective
PR = #35
PR state = OPEN / READY / MERGEABLE / UNMERGED
exact corrective head = e1597f77bcc8a65e2e00e9c5573e028cdbee337b
commits = 2
changed files = 1
changed path = .github/workflows/faz7-publish-images.yml
```

Scope proof:

```text
application/business source change = NONE
Dockerfile/base/dependency change = NONE
n8n identity change = NONE
frozen n8n workflow JSON change = NONE
scanner suppression = NONE
blanket CVE ignore = NONE
SiteScore-authored VEX = NONE
security threshold weakening = NONE
FAZ 7.2 work = NONE
```

Exact policy parity self-review:

```text
publish reachability policy == frozen container CI policy = TRUE
publish scanner policy == frozen container CI policy = TRUE
only intentional path delta = evidence directory application-images -> publish
CVE-2026-82049 exact Python 3.11.16 residual policy preserved
CISA KEV reconciliation preserved
archive-extraction reachability proof preserved
public tar/tar.gz ingress proof preserved
raw Grype evidence preserved
all other CRITICAL or HIGH-with-fix remains blocking
```

Authoritative terminal PR CI:

```text
run = 35470194681
source-boundary       = SUCCESS  job 105969628018
static-contracts      = SUCCESS  job 105969628009
faz6-commerce-replay  = SUCCESS  job 105969627890
container-validation = SUCCESS  job 105969628033
n8n-validation        = SUCCESS  job 105969627988
required-gate         = SUCCESS  job 105974318886
```

Exact-head artifacts:

```text
application evidence artifact id = 10592383117
application artifact name = faz7-application-image-evidence-e1597f77bcc8a65e2e00e9c5573e028cdbee337b
n8n evidence artifact id = 10593570006
n8n artifact name = faz7-n8n-final-evidence-e1597f77bcc8a65e2e00e9c5573e028cdbee337b
```

Implementer terminal decision:

```text
IMPLEMENTER_STATE = POST_LOCK_CORRECTIVE_READY_FOR_REVIEW
CORRECTIVE_EXACT_HEAD = e1597f77bcc8a65e2e00e9c5573e028cdbee337b
CORRECTIVE_REQUIRED_GATE = SUCCESS
CORRECTIVE_TECHNICAL_BLOCKERS = NONE
CORRECTIVE_SCOPE_DRIFT = NONE
CORRECTIVE_READY_FOR_REVIEW = YES
CORRECTIVE_READY_TO_LOCK = NO  # Reviewer authority required
CORRECTIVE_USER_LOCK_AUTHORIZED = NO
CORRECTIVE_MERGE = NO
FAZ_7_2_STARTED = NO
PUBLIC_LAUNCH_AUTHORIZED = NO
```

**Implementer corrective work is complete.** Reviewer must independently audit exact head `e1597f77bcc8a65e2e00e9c5573e028cdbee337b`, PR #35, terminal run `35470194681`, single-file scope, and exact policy parity. Only Reviewer may advance this corrective to `READY_TO_LOCK`. No further Implementer code change is authorized unless Reviewer reopens the corrective.


---

## POST-LOCK CORRECTIVE — FINAL AUTHORITATIVE TERMINAL HANDOFF AFTER REVIEWER NODE PARITY REOPEN

Reviewer subsequently identified one additional mechanical publication drift within the same already-authorized permanent path: publish host Node setup/assertion still used `26.5.1` while the frozen n8n builder/runtime family is `26.7.0`.

The correction was applied only to the authorized file:

```text
path = .github/workflows/faz7-publish-images.yml
old host Node = 26.5.1
new host Node = 26.7.0
application/business source change = NONE
Python/base identity change = NONE
n8n source commit/tree change = NONE
n8n workflow JSON change = NONE
n8n hardening/pruning logic change = NONE
Cosign/SBOM/provenance design change = NONE
GitHub governance change = NONE
cloud/deployment state change = NONE
```

Final authoritative corrective state:

```text
base main = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
branch = faz7/7-1-publish-policy-parity-corrective
PR = #35
PR state = OPEN / READY / MERGEABLE / UNMERGED
exact corrective head = fffe943723b230d73d0afa079b736e06c0b3a6a4
commits = 3
changed permanent files = 1
changed path = .github/workflows/faz7-publish-images.yml
publish Node host/assertion = 26.7.0
publish application security policy parity = TRUE
merge performed = NO
```

Final exact-head PR CI:

```text
run = 35474113362
source-boundary       = SUCCESS  job 105980260645
static-contracts      = SUCCESS  job 105980260610
faz6-commerce-replay  = SUCCESS  job 105980260504
container-validation = SUCCESS  job 105980260713
n8n-validation        = SUCCESS  job 105980260588
required-gate         = SUCCESS  job 105983845465
```

Final exact-head evidence artifacts:

```text
application artifact id = 10594027965
application artifact name = faz7-application-image-evidence-fffe943723b230d73d0afa079b736e06c0b3a6a4
n8n artifact id = 10594375006
n8n artifact name = faz7-n8n-final-evidence-fffe943723b230d73d0afa079b736e06c0b3a6a4
```

Final Implementer decision:

```text
IMPLEMENTER_STATE = POST_LOCK_CORRECTIVE_READY_FOR_REVIEW
CORRECTIVE_EXACT_HEAD = fffe943723b230d73d0afa079b736e06c0b3a6a4
CORRECTIVE_REQUIRED_GATE = SUCCESS
CORRECTIVE_TECHNICAL_BLOCKERS = NONE
CORRECTIVE_SCOPE_DRIFT = NONE
CORRECTIVE_NODE_PARITY = 26.7.0 / PASS
CORRECTIVE_SECURITY_POLICY_PARITY = PASS
CORRECTIVE_READY_FOR_REVIEW = YES
CORRECTIVE_READY_TO_LOCK = NO
CORRECTIVE_USER_LOCK_AUTHORIZED = NO
CORRECTIVE_MERGE = NO
FAZ_7_2_STARTED = NO
PUBLIC_LAUNCH_AUTHORIZED = NO
```

The prior corrective exact head `e1597f77bcc8a65e2e00e9c5573e028cdbee337b` and run `35470194681` are superseded as lock-review authority because Reviewer reopened the bounded corrective for Node host parity. Only `fffe943723b230d73d0afa079b736e06c0b3a6a4` and run `35474113362` are authoritative for the next Reviewer audit.

**Implementer work is complete again. Reviewer must independently audit this exact final corrective head before READY_TO_LOCK may be issued. A new literal user LOCK is still required after Reviewer READY_TO_LOCK because the earlier LOCK was consumed by PR #34.**


---

## FINAL REVIEWER-CRITERIA SELF-AUDIT — NO ADDITIONAL CODE CHANGE REQUIRED

The latest Reviewer handoff restated ten exact publish-policy requirements. The current exact corrective head already satisfies all ten by using the same frozen application classifier semantics as `.github/workflows/faz7-container-ci.yml`; therefore no additional source commit is required and creating one would only invalidate the terminal green exact-head evidence.

```text
exact corrective head = fffe943723b230d73d0afa079b736e06c0b3a6a4
PR = #35
changed permanent files = 1
changed path = .github/workflows/faz7-publish-images.yml
terminal run = 35474113362
required-gate = SUCCESS / job 105983845465
```

Reviewer criterion mapping:

```text
1. CISA KEV + related vulnerability IDs = PASS
2. raw Grype evidence preserved = PASS
3. only exact CVE-2026-82049 / HIGH / python / 3.11.16 accepted = PASS
4. residual-risk record + exact classification string required = PASS
5. source/runtime/public archive reachability containment proof = PASS
6. exact authorized residual occurrence count == 1 per API/Commerce image = PASS
7. all other CRITICAL findings block = PASS
8. all other HIGH findings with actionable fixes block = PASS
9. Python 3.14.0b1 is not treated as approved same-series 3.11 remediation = PASS
10. raw scanner output is not suppressed/deleted/mutated = PASS
```

The relevant publish classifier is semantically the frozen container-validation classifier with only the evidence directory changed from `application-images` to `publish`. It also checks `relatedVulnerabilities` against CISA KEV, requires exactly one authorized residual per image via `len(residuals) != 1`, and raises on all policy blockers.

Additional previously reopened mechanical drift is also resolved:

```text
publish host Node = 26.7.0
explicit node --version assertion = v26.7.0
frozen n8n builder/runtime family = 26.7.0
NODE_PARITY = PASS
```

No additional code change is warranted. The terminal authoritative handoff remains:

```text
IMPLEMENTER_STATE = POST_LOCK_CORRECTIVE_READY_FOR_REVIEW
CORRECTIVE_EXACT_HEAD = fffe943723b230d73d0afa079b736e06c0b3a6a4
CORRECTIVE_RUN = 35474113362
CORRECTIVE_REQUIRED_GATE = SUCCESS
CORRECTIVE_TECHNICAL_BLOCKERS = NONE
CORRECTIVE_SCOPE_DRIFT = NONE
CORRECTIVE_READY_FOR_REVIEW = YES
CORRECTIVE_READY_TO_LOCK = NO
CORRECTIVE_USER_LOCK_AUTHORIZED = NO
CORRECTIVE_MERGE = NO
```

Reviewer must now independently audit this exact head. A new literal user `LOCK` remains mandatory only after Reviewer issues exact-head `READY_TO_LOCK`.


---

## LIVE REVALIDATION — 2026-09-28

Implementer revalidated the corrective after an extended idle period. No code or PR-head drift occurred.

```text
PR = #35
state = OPEN
merged = FALSE
draft = FALSE
mergeable = TRUE
base/main SHA = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
exact corrective head = fffe943723b230d73d0afa079b736e06c0b3a6a4
changed permanent files = 1
commits = 3
```

Exact-head workflow evidence remains terminal green:

```text
run = 35474113362
faz6-commerce-replay  = SUCCESS  job 105980260504
n8n-validation        = SUCCESS  job 105980260588
static-contracts      = SUCCESS  job 105980260610
source-boundary       = SUCCESS  job 105980260645
container-validation = SUCCESS  job 105980260713
required-gate         = SUCCESS  job 105983845465
```

Artifacts remain present and unexpired:

```text
application artifact id = 10594027965
n8n artifact id = 10594375006
```

No additional Implementer code change is authorized or necessary. The corrective remains READY_FOR_REVIEW and UNMERGED. Reviewer must independently audit exact head `fffe943723b230d73d0afa079b736e06c0b3a6a4` and may issue `READY_TO_LOCK` only for that exact SHA. A new literal user `LOCK` remains required after such Reviewer authorization.


---

## POST-MERGE CORRECTIVE LOCK EXECUTION AND NEW SECURITY REOPEN — 2026-09-28

Reviewer issued exact-head `READY_TO_LOCK: YES` for PR #35 head `fffe943723b230d73d0afa079b736e06c0b3a6a4`. The user then supplied a new literal `LOCK`, which was consumed for this corrective merge.

Exact merge execution:

```text
PR = #35
reviewed head = fffe943723b230d73d0afa079b736e06c0b3a6a4
expected base = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
merge method = normal merge commit
expected-head protection = fffe943723b230d73d0afa079b736e06c0b3a6a4
merge result = SUCCESS
merge commit / new main = dcd3f350fac54ab42ebf8ed8d35012c1125a87ed
merge tree = 3e1964663041b802d36749d4f5e5db8d3e658908
parent 1 = 3abbbd97b87b699d01f6013b560ee79e09d1cd8c
parent 2 = fffe943723b230d73d0afa079b736e06c0b3a6a4
PR #35 = CLOSED / MERGED
main protected = TRUE
required status check = required-gate
```

The automatic post-merge publication run started on the exact new main:

```text
workflow = faz7-publish-images
run = 36478260634
event = push
head/main = dcd3f350fac54ab42ebf8ed8d35012c1125a87ed
job = publish / 109117288504
final status = COMPLETED
final conclusion = FAILURE
```

Publication step state:

```text
Checkout exact main commit = SUCCESS
GHCR authentication = SUCCESS
Setup exact Node 26.7.0 = SUCCESS
Build and publish immutable linux amd64 application images = SUCCESS
Rebuild validate and publish exact frozen n8n candidate = FAILURE
Resolve exact published digests = SKIPPED
Published application SBOM/security policy = SKIPPED
Published n8n exact-image/SBOM proof = SKIPPED
Provenance = SKIPPED
Cosign signatures/attestations = SKIPPED
Publication evidence upload = SKIPPED
publication artifacts = NONE
```

### New security finding — true reopen

The frozen n8n security gate failed on a newly actionable OS HIGH discovered by the current scanner/vulnerability data:

```text
CVE = CVE-2026-93990
severity = HIGH
package = libexpat
installed version = 2.8.4-r0
fixed version = 2.8.5-r0
package type = apk
ACTIONABLE_OS_HIGH = 1
BLOCKING_HIGH = 1
CISA_KEV = 0
N8N_ACTIONABLE_GATE = FAIL
```

The four previously Reviewer-authorized exact residuals remain separately classified and were not the blocker:

```text
zlib 1.3.2-r0 / CVE-2026-85091
nodemailer 8.0.10 / GHSA-P6GQ-J5CR-W38F
nodemailer 8.0.10 / GHSA-2X7J-588G-CCC2
@tiptap/core 3.27.0 / GHSA-J95F-988M-3J2F
```

Frozen n8n authority still pins:

```text
n8n = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
builder = node:26.7.0-alpine3.24@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019
DHI runtime base = dhi.io/node:26.7.0-alpine3.24-dev@sha256:4b494d89fb26c950ce97865acf45b480dc7a6868fdc2b81c2d66599702eeac3f
```

This is not the previously corrected publication policy drift and is not an ordinary YAML/evidence mechanical issue. The existing security gate is correctly fail-closed: it detected a fixable apk HIGH and blocked publication before digest finalization/signing/attestation.

Implementer does **not** unilaterally waive the CVE, weaken the threshold, alter the frozen n8n runtime identity, or inject an apk/package remediation, because those actions exceed the currently authorized one-file publication corrective and the Reviewer explicitly required return on a true new security blocker.

Terminal handoff:

```text
IMPLEMENTER_STATE = POST_MERGE_SECURITY_REOPEN_REQUIRED
MERGE = COMPLETE / VALID
MAIN = dcd3f350fac54ab42ebf8ed8d35012c1125a87ed
POST_MERGE_PUBLISH_RUN = 36478260634 / FAILURE
SECURITY_REOPEN = CVE-2026-93990 / libexpat 2.8.4-r0 / fix 2.8.5-r0
CISA_KEV = 0
SECURITY_THRESHOLD_WEAKENING = NONE
SCANNER_SUPPRESSION = NONE
BLANKET_CVE_IGNORE = NONE
FAZ_7_1_LOCKED_VERIFIED = NO
READY_TO_LOCK = NO
NEXT_CHECKPOINT_AUTHORIZED = NO
FAZ_7_2_STARTED = NO
PUBLIC_LAUNCH_AUTHORIZED = NO
```

Reviewer must independently audit this post-merge security reopen and authorize the remediation path before any new permanent code/runtime-identity change is made.


---

## CVE-2026-93990 / LIBEXPAT 2.8.5-r0 CORRECTIVE — TERMINAL IMPLEMENTER HANDOFF

Reviewer authorized the exact bounded remediation after the post-merge n8n security reopen. Implementer changed only the authorized permanent file and completed the corrective to a terminal exact-head green PR.

```text
base main = dcd3f350fac54ab42ebf8ed8d35012c1125a87ed
branch = faz7/7-1-libexpat-2-8-5-r0-security-corrective
PR = #36
PR state = OPEN / READY / MERGEABLE / UNMERGED
exact corrective head = 2bf60b3af0c1d9f0357e5d7834c61751bd220601
commits = 1
changed permanent files = 1
changed path = deploy/containers/n8n-frozen-candidate-ci.sh
additions = 2
deletions = 2
```

Authorized code delta only:

```text
apk pin: libexpat=2.8.4-r0 -> libexpat=2.8.5-r0
final-installed assertion: P:libexpat / V:2.8.4-r0 -> V:2.8.5-r0
```

No scope drift:

```text
n8n version = 2.37.10 unchanged
n8n source commit/tree = unchanged
Node/DHI family = 26.7.0 / Alpine 3.24 unchanged
DHI immutable base digest = unchanged
libcrypto3/libssl3 pins = unchanged
libcurl pin = unchanged
Snowflake/TOML pruning = unchanged
Git/Git Tool pruning = unchanged
NODES_EXCLUDE contract = unchanged
frozen workflow hashes = unchanged
application/business source bytes = unchanged
application Python/Trixie identity = unchanged
published-image policy parity = unchanged
scanner suppression = NONE
blanket CVE ignore = NONE
SiteScore-authored VEX = NONE
security threshold weakening = NONE
FAZ 7.2 work = NONE
```

Exact-head hosted validation:

```text
run = 36483975872
source-boundary       = SUCCESS  job 109136217642
static-contracts      = SUCCESS  job 109136218926
faz6-commerce-replay  = SUCCESS  job 109136217588
container-validation = SUCCESS  job 109136217408
n8n-validation        = SUCCESS  job 109136217778
required-gate         = SUCCESS  job 109149098728
```

n8n security/runtime evidence from the exact-head job:

```text
libexpat package operation = 2.8.5-r0
runtime installation evidence = libexpat 2.8.5-r0
CISA_KEV = 0
ACTIONABLE_OS_HIGH = 0
BLOCKING_CRITICAL = 0
BLOCKING_HIGH = 0
BLOCKING_HIGH_DETAILS = []
NEW_UNDISPOSITIONED_HIGH = 0
ALLOWED_EXACT_RESIDUAL_HIGH = 4
CVE-2026-93990 blocking finding = ABSENT from final threshold summary
n8n static = 12 PASS
FROZEN_N8N_2_37_10_SNOWFLAKE_PRUNED_SECURITY_RUNTIME_GATE = PASS
```

The raw upstream reconciliation stage still prints its pre-existing aggregate marker `N8N_ACTIONABLE_GATE=FAIL` before the repository's final Reviewer-authorized residual classifier runs. This did not terminate the job. The subsequent fail-closed final classifier reports `ACTIONABLE_OS_HIGH=0`, `BLOCKING_HIGH=0`, `CISA_KEV=0`, and the frozen final runtime/security gate is PASS. This raw intermediate marker is preserved for Reviewer audit rather than suppressed or rewritten.

Exact-head artifacts:

```text
application evidence artifact id = 10998945741
application artifact name = faz7-application-image-evidence-2bf60b3af0c1d9f0357e5d7834c61751bd220601
expired = FALSE

n8n evidence artifact id = 11000008561
n8n artifact name = faz7-n8n-final-evidence-2bf60b3af0c1d9f0357e5d7834c61751bd220601
expired = FALSE
```

Implementer terminal decision:

```text
IMPLEMENTER_STATE = LIBEXPAT_SECURITY_CORRECTIVE_READY_FOR_REVIEW
CORRECTIVE_PR = #36
CORRECTIVE_BASE = dcd3f350fac54ab42ebf8ed8d35012c1125a87ed
CORRECTIVE_EXACT_HEAD = 2bf60b3af0c1d9f0357e5d7834c61751bd220601
CORRECTIVE_RUN = 36483975872
CORRECTIVE_REQUIRED_GATE = SUCCESS
CORRECTIVE_TECHNICAL_BLOCKERS = NONE
CORRECTIVE_SCOPE_DRIFT = NONE
CORRECTIVE_READY_FOR_REVIEW = YES
CORRECTIVE_READY_TO_LOCK = NO
CORRECTIVE_USER_LOCK_AUTHORIZED = NO
CORRECTIVE_MERGE = NO
FAZ_7_1_LOCKED_VERIFIED = NO
NEXT_CHECKPOINT_AUTHORIZED = NO
FAZ_7_2_STARTED = NO
PUBLIC_LAUNCH_AUTHORIZED = NO
```

Reviewer must independently audit exact PR #36 head `2bf60b3af0c1d9f0357e5d7834c61751bd220601`, run `36483975872`, the one-file/two-line scope, and the security evidence. A new literal user `LOCK` is required only after Reviewer issues exact-head `READY_TO_LOCK`.


---

## POST-PR36 MERGE PUBLICATION — COSIGN GHCR AUTH BLOCKER

PR #36 is already validly merged from the exact Reviewer-approved head. The current literal user LOCK does not require or permit a second merge.

```text
PR = #36
reviewed head = 2bf60b3af0c1d9f0357e5d7834c61751bd220601
merge commit / current main = 84b9cb1a5192bdddad6677cbbae8035b974b1167
merge tree = ec74a6da3384aaee51ab38dd25580f968be4f8ed
parent 1 = dcd3f350fac54ab42ebf8ed8d35012c1125a87ed
parent 2 = 2bf60b3af0c1d9f0357e5d7834c61751bd220601
main protected = TRUE
```

The required post-merge publication workflow ran on exact main:

```text
workflow = faz7-publish-images
run = 36519593932
head = 84b9cb1a5192bdddad6677cbbae8035b974b1167
attempt 1 = FAILURE
attempt 2 = FAILURE
```

Both attempts successfully completed all product/security/publication preparation before the same final signing blocker:

```text
application image build/publish = PASS
frozen n8n rebuild/validation/publish = PASS
digest resolution = PASS
published application SBOM/security policy = PASS
API_CISA_KEV_MATCHES = 0
API_POLICY_BLOCKERS = 0
COMMERCE_CISA_KEV_MATCHES = 0
COMMERCE_POLICY_BLOCKERS = 0
published n8n exact-candidate identity/SBOM = PASS
PUBLISHED_N8N_PRUNED_PACKAGE_IDENTITY = PASS
FROZEN_N8N_2_37_10_SNOWFLAKE_PRUNED_SECURITY_RUNTIME_GATE = PASS
provenance predicate creation = PASS
```

Attempt 2 published n8n digest observed before signing:

```text
n8n digest = sha256:e3383108d90c4a39252eaf7cfeaa6ac01b4de34c90ecc74aaef168667cf1d5a4
```

Both attempts fail at:

```text
step = Keyless sign images and attest SBOM plus provenance
first subject = ghcr.io/metadoks/sitescore-api
attempt 2 API digest = sha256:276173c6103f2364d11e6de01a3355535e7559e1b5a84017798684aa339a779a
error = UNAUTHORIZED: unauthenticated: User cannot be authenticated with the token provided
operation = cosign signature layer upload to GHCR
publication evidence upload = SKIPPED
publication artifacts = NONE
```

Workflow permissions are already:

```text
contents: read
packages: write
id-token: write
```

The same job successfully authenticates to GHCR with the ephemeral `GITHUB_TOKEN` and successfully pushes API, Commerce and n8n images before Cosign starts. The signing implementation then launches the pinned Cosign container and only bind-mounts the host Docker config at `/root/.docker:ro` while passing OIDC environment variables. The repeatable failure is therefore isolated to Cosign registry credential plumbing / GHCR signature upload authentication, not to the image/security gates or the libexpat corrective.

No security threshold, scanner output, n8n identity, application source, or governance state was weakened or changed. A third identical rerun is not justified after two deterministic failures.

Terminal handoff:

```text
IMPLEMENTER_STATE = POST_MERGE_PUBLICATION_COSIGN_AUTH_BLOCKER
MAIN = 84b9cb1a5192bdddad6677cbbae8035b974b1167
PR36_MERGE = VALID
LIBEXPAT_SECURITY_REOPEN = RESOLVED
POST_MERGE_RUN = 36519593932 / ATTEMPT_2_FAILURE
COSIGN_GHCR_AUTH = BLOCKED
FAZ_7_1_LOCKED_VERIFIED = NO
PUBLICATION_EVIDENCE_ARTIFACT = ABSENT
READY_TO_LOCK = NO
NEXT_CHECKPOINT_AUTHORIZED = NO
FAZ_7_2_STARTED = NO
PUBLIC_LAUNCH_AUTHORIZED = NO
```

Reviewer must audit this repeated Cosign/GHCR authentication blocker and authorize the exact remediation path before any permanent workflow change is made.


---

## COSIGN CONFIG CORRECTIVE PR #37 — NEW TRUE N8N SECURITY REOPEN

Reviewer authorized the final single-file Cosign Docker-config path corrective. Implementer applied exactly that mechanical change from protected main.

```text
base = 84b9cb1a5192bdddad6677cbbae8035b974b1167
branch = faz7/7-1-cosign-docker-config-auth-corrective
PR = #37
PR state = OPEN / MERGEABLE / UNMERGED
exact head = 29f3213cd32656166127dbcfdc7a11eac771adeb
commits = 1
changed permanent files = 1
changed path = .github/workflows/faz7-publish-images.yml
additions = 2
deletions = 1
```

Authorized semantic delta only:

```text
Cosign Docker config mount:
/root/.docker:ro -> /tmp/cosign-docker-config:ro
DOCKER_CONFIG=/tmp/cosign-docker-config added inside Cosign container
credential source = unchanged GITHUB_TOKEN
packages: write = unchanged
id-token: write = unchanged
Cosign image/digest = unchanged
keyless mode = unchanged
signatures/attestation requirements = unchanged
```

Exact-head CI run:

```text
run = 36546348304
source-boundary       = SUCCESS  job 109333559504
static-contracts      = SUCCESS  job 109333559768
faz6-commerce-replay  = SUCCESS  job 109333559908
container-validation = SUCCESS  job 109333559938
n8n-validation        = FAILURE  job 109333559851
required-gate         = FAILURE  job 109342767747
```

The n8n failure is unrelated to the Cosign YAML corrective and is a newly surfaced fail-closed security blocker from current vulnerability data:

```text
package = fast-uri
installed version = 3.1.6
fixed version = 3.1.7
severity = HIGH
advisory 1 = GHSA-58mr-gqgx-xq4g
advisory 2 = GHSA-qw65-cvwx-89v3
CISA_KEV = 0
ACTIONABLE_OS_HIGH = 0
BLOCKING_CRITICAL = 0
BLOCKING_HIGH = 2
FORBIDDEN_PACKAGE_HIGH.fast-uri = 2
NEW_UNDISPOSITIONED_HIGH = 1
final security threshold = FAIL
```

The four previously Reviewer-authorized exact residual HIGHs remain separately allowed. The libexpat 2.8.5-r0 remediation remains present; this is a distinct new dependency vulnerability result.

Exact-head evidence artifacts still uploaded despite fail-closed security exit:

```text
application evidence artifact id = 11022803088
n8n evidence artifact id = 11023946574
expired = FALSE
```

No scanner suppression, residual exception, dependency override, n8n source change, or security threshold weakening was applied. The current Reviewer authorization is restricted to the Cosign Docker-config path and does not authorize remediation of a new fast-uri dependency vulnerability.

Terminal handoff:

```text
IMPLEMENTER_STATE = COSIGN_CORRECTIVE_BLOCKED_BY_NEW_N8N_SECURITY_REOPEN
PR = #37
CORRECTIVE_EXACT_HEAD = 29f3213cd32656166127dbcfdc7a11eac771adeb
COSIGN_SCOPE = IMPLEMENTED_EXACTLY
COSIGN_FIX_REVIEWABLE = YES
NEW_SECURITY_BLOCKER = fast-uri 3.1.6 / GHSA-58mr-gqgx-xq4g + GHSA-qw65-cvwx-89v3 / fix 3.1.7
CISA_KEV = 0
SECURITY_THRESHOLD_WEAKENING = NONE
SCANNER_SUPPRESSION = NONE
PR_REQUIRED_GATE = FAILURE_DUE_NEW_SECURITY_BLOCKER
READY_TO_LOCK = NO
MERGE = NO
FAZ_7_1_LOCKED_VERIFIED = NO
NEXT_CHECKPOINT_AUTHORIZED = NO
FAZ_7_2_STARTED = NO
PUBLIC_LAUNCH_AUTHORIZED = NO
```

Per Reviewer instruction, this is a true new security blocker and requires Reviewer remediation authorization before any dependency/security-policy change.
