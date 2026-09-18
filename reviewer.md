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
REVIEWER_STATE: N8N_AUTH_PROTECTED_NODE_TYPES_MECHANICAL_REMEDIATION_AUTHORIZED
IMPLEMENTER_ACTION: REPLACE_UNAUTHENTICATED_TYPES_HTTP_PROBE_WITH_OFFICIAL_EXPORT_NODES_RUNTIME_INVENTORY_THEN_COMPLETE_TERMINAL_CI
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 1992bdd8f74a736ba7ee129d4d89a0c011386a76
REVIEWED_HEAD_SHA: NONE
LIVE_FAZ7_RUN: 35399578554
LIVE_CONTAINER_VALIDATION_JOB: 105776153359
LIVE_N8N_VALIDATION_JOB: 105776153483

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-APP-BASE-001: RESOLVED_GREEN_EXACT_HEAD
OPS71-N8N-DHI-001: RESOLVED_AUTHENTICATED_PULL_PASS
OPS71-N8N-VULN-001: MECHANICAL_AUTH_PROTECTED_NODE_TYPES_EVIDENCE_REMEDIATION_AUTHORIZED

FAZ71_CANDIDATE_CUTOFF_DATE: 2026-09-07
FAZ71_N8N_CANDIDATE_VERSION: 2.37.10
FAZ71_N8N_SOURCE_COMMIT: 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
FAZ71_N8N_SOURCE_TREE: 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
FAZ71_MOVING_LATEST_STABLE_GUARD: DISABLED_AFTER_CUTOFF_EXCEPT_EMERGENCY_REOPEN

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
```


---

## 0A. Superseding Reviewer decision — authenticated type-file root cause

Exact-head run:

```text
head = 1992bdd8f74a736ba7ee129d4d89a0c011386a76
run = 35399578554
n8n-validation job = 105776153483
```

Result:

```text
source-boundary       = PASS
static-contracts      = PASS
container-validation = PASS
faz6-commerce-replay  = PASS
DHI authentication   = PASS
hardened n8n image build = PASS
n8n-validation        = FAIL at node-type runtime evidence
required-gate         = FAIL only because n8n-validation failed
```

Uploaded final evidence artifact:

```text
artifact id = 10570901495
artifact sha256 = b26ccbe06134adf20562c694ced09f611eae4509095ce9e74f7ca4b6d8dccc72
```

Evidence proves n8n itself completed migrations, registered the JS task runner, reported version 2.37.10, completed workflow dependency indexing, and exposed the editor. The captured unauthenticated `/types/nodes.json` body remained:

```text
n8n is starting up. Please wait
```

Reviewer verified the exact frozen upstream source commit
`5542b8b6419cb6925cca8f11b270c9bfbe09d85e`:

- `packages/cli/src/server.ts` explicitly wraps
  `/types/nodes.json`, `/types/credentials.json`, and `/types/node-versions.json`
  in `AuthService.createAuthMiddleware(...)`.
- Therefore an unauthenticated `curl /types/nodes.json` is not a valid terminal runtime inventory contract for this frozen release.
- The same exact frozen source provides the official command
  `n8n export:nodes --output <path>`, implemented by
  `packages/cli/src/commands/export/nodes.ts`, which loads node types through
  `LoadNodesAndCredentials`.

Classification:

```text
CLASSIFICATION: MECHANICAL_EVIDENCE_IMPLEMENTATION_DEFECT
NEW_DESIGN_DECISION_REQUIRED: NO
EMERGENCY_SECURITY_REOPEN: NO
N8N_CANDIDATE_RESELECTION_REQUIRED: NO
```

Authorized remediation is narrow:

```text
REMOVE:
unauthenticated /types/nodes.json polling as the node inventory proof

KEEP:
healthz/startup runtime smoke
frozen n8n 2.37.10 identity
frozen DHI runtime digest
Snowflake/TOML pruning
NODES_EXCLUDE
all existing security thresholds
workflow hashes
application/business semantics

ADD/USE:
official frozen-runtime command:
n8n export:nodes --output <temporary evidence path>

PROVE FROM EXPORTED INVENTORY:
n8n-nodes-base.httpRequest = PRESENT
n8n-nodes-base.snowflake = ABSENT
n8n-nodes-base.emailSend = ABSENT
n8n-nodes-base.executeCommand = ABSENT
n8n-nodes-base.localFileTrigger = ABSENT
```

The export must execute from the final hardened candidate image with the frozen
`NODES_EXCLUDE` environment in force. The evidence path/output may be temporary
or artifact-only. Do not create an owner account, do not bypass authentication,
do not weaken authentication, and do not expose editor/admin/API surfaces merely
to read type files.

The prior wait-time increases were diagnostic mechanics only; do not increase
the HTTP polling timeout again. Continue directly to one exact-head terminal CI
run after this replacement.

Next Implementer handoff remains terminal-only:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

or a true design/security/owner-governance blocker.

---

## 0. Live reviewer observation — exact head 044cd95

Live PR #34 has advanced beyond the prior handoff to exact head:

```text
044cd95aadf170e44e7ee8d823e7735509a4539f
run = 35288901923
```

The delta from `1a01ec7de87692fc5d12b8520357d41a5d4dd14e` is confined to `deploy/containers/n8n-frozen-candidate-ci.sh`; no frozen application or n8n workflow JSON path changed.

Current exact-head jobs observed by Reviewer:

```text
source-boundary       = PASS
static-contracts      = PASS
container-validation = PASS
faz6-commerce-replay  = PASS
DHI authentication   = PASS
n8n-validation        = IN_PROGRESS at frozen source-build/hardening/security gate
required-gate         = pending n8n-validation
```

No new design/security decision is required at this observation point. Do not introduce further code churn unless this exact-head run produces a concrete terminal failure requiring remediation.

---

## 1. Exact-head state

Live PR #34 remains on exact head:

```text
1a01ec7de87692fc5d12b8520357d41a5d4dd14e
```

Latest exact-head rerun remains run:

```text
run = 35156778651
source-boundary = PASS
static-contracts = PASS
FAZ6 Commerce replay = PASS (417)
container-validation = PASS
n8n-validation = FAIL
required-gate = FAIL only because n8n-validation failed
```

The historical DHI owner-secret blocker is now RESOLVED. Exact job `105159800082` proves the permanent DHI authentication step passed and the frozen DHI digest was successfully pulled.

The n8n job then completed the exact frozen 2.37.10 source build and Snowflake/TOML pruning successfully:

```text
n8n source build = PASS
snowflake-sdk@2.1.0 = REMOVED
toml@3.0.0 = REMOVED
shared_non_snowflake_removed = []
version_changes = []
```

The first failing operation is later, while assembling the hardened DHI runtime base:

```text
apk add --no-cache busybox-binsh

installed/base busybox:
  busybox-1.38.0_git20260724-r5

repository busybox-binsh candidate:
  busybox-binsh-1.37.0_git20260817-r33
  requires busybox=1.37.0_git20260817-r33

result:
  package solver conflict
  exit code = 1
```

This is a MECHANICAL IMPLEMENTATION DEFECT, not a new security/design blocker. The build command itself is already executing under `/bin/sh` before the attempted `busybox-binsh` installation, so the explicit installation is redundant for this exact DHI base.

Reviewer decision:

```text
OPS71-N8N-VULN-001:
MECHANICAL_BUSYBOX_BINSH_PACKAGE_CONFLICT_REMEDIATION_AUTHORIZED

NEW_DESIGN_DECISION_REQUIRED: NO
EMERGENCY_SECURITY_REOPEN: NO
```

Authorized remediation is narrowly bounded:

```text
REMOVE ONLY:
apk add --no-cache busybox-binsh && \\

KEEP UNCHANGED:
frozen n8n 2.37.10 identity
frozen DHI runtime digest
Snowflake/TOML pruning
libcrypto3/libssl3/libexpat exact security pins
openssh/graphicsmagick removal
NODES_EXCLUDE contract
security thresholds
workflow hashes
application/business behavior
```

Do not replace the DHI base, do not pin a mismatched BusyBox family, and do not weaken the security gate. Implementer is authorized to perform this mechanical edit and continue directly to terminal CI without another Reviewer round trip unless a true design/security blocker appears.

---

## 2. Trixie bounded refresh is implemented

The Reviewer-authorized Bookworm → Trixie emergency expansion has been consumed on the live PR branch.

Current immutable application base lock is:

```text
PYTHON_IMAGE_TAG=python:3.11.16-slim-trixie
PYTHON_IMAGE_DIGEST=sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72
PYTHON_IMAGE=python:3.11.16-slim-trixie@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72
TARGET_PLATFORM=linux/amd64
DEBIAN_SUITE=trixie
DEBIAN_SECURITY_SUITE=trixie-security
DEBIAN_SNAPSHOT=20260916T000000Z
```

The exact-head workflow has already passed image build, non-root/read-only runtime proof, and the API/report/Commerce applicable regression step. Source-boundary also proves frozen application/workflow source boundaries remain intact.

Terminal application acceptance remains unchanged:

```text
API = 114 PASS
report = 24 PASS
Commerce = 416 PASS + exactly 1 authorized deselect
FAZ6 Commerce replay = 417 PASS
linux/amd64 = PASS
non-root/read-only = PASS
API web/worker/beat = PASS
Commerce web/dispatcher = PASS
PDF/font = PASS
CISA KEV = 0
CRITICAL = 0
OS HIGH = 0
no new undispositioned HIGH introduced by refresh
SBOM/Grype/image-hygiene evidence = COMPLETE
```

The first fully green exact Trixie candidate becomes frozen. Do not chase later routine base refreshes after that point.

---

## 3. DHI owner action is resolved

Repository Actions credentials are now present and the exact-head rerun proves:

```text
Authenticate frozen DHI runtime registry = PASS
dhi.io token exchange = PASS
frozen DHI metadata/pull = PASS
```

Therefore:

```text
OPS71-N8N-DHI-001: RESOLVED_AUTHENTICATED_PULL_PASS
```

No further owner credential action is required for the current frozen candidate. Do not expose, rotate, commit, print, or otherwise alter the credentials as part of this mechanical remediation.

---

## 4. Frozen n8n authority remains unchanged

```text
n8n = 2.37.10
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
Snowflake/TOML resolution = graph-proven unused-capability pruning
```

Required post-prune state:

```text
n8n-nodes-base@2.37.4 = PRESENT
snowflake-sdk@2.1.0 = ABSENT
toml@3.0.0 = ABSENT
shared_non_snowflake_removed = []
NODES_EXCLUDE retains executeCommand/localFileTrigger/emailSend/snowflake
```

The exact previously-authorized nodemailer residual HIGH may remain only if it is still the sole residual HIGH and all established containment controls are proven. No second residual CRITICAL/HIGH exception is authorized.

Forbidden:

```text
moving-latest n8n restart
weaker anonymous runtime-base fallback
scanner suppression / blanket CVE ignore
SiteScore-authored VEX waiver
incompatible TOML override
parent-source feature patch
frozen application/business semantic change
frozen n8n workflow JSON change
self-hosted/alternative CI
credential commit
```

---

## 5. Terminal completion contract

Implementer must now apply the single authorized BusyBox mechanical remediation and continue to one terminal handoff without returning for ordinary mechanics:

```text
[ ] application Trixie vulnerability policy GREEN
[ ] DHI authenticated pull PASS
[ ] frozen n8n hardened runtime build PASS
[ ] Snowflake/TOML final inventory exact
[ ] n8n workflow hashes/import/static/runtime smoke PASS
[ ] n8n security gate PASS under existing residual-risk contract
[ ] n8n SBOM/Grype/OpenVEX/provenance complete
[ ] API 114 PASS
[ ] report 24 PASS
[ ] Commerce 416 PASS + exactly 1 deselect
[ ] FAZ6 replay 417 PASS
[ ] source-boundary PASS
[ ] static-contracts PASS
[ ] container-validation PASS
[ ] n8n-validation PASS
[ ] faz7 / required-gate PASS on one exact final HEAD
[ ] temporary diagnostics absent
[ ] frozen application source diff NONE
[ ] frozen n8n workflow diff NONE
[ ] cloud/IaC mutation NONE
[ ] production secret commit NONE
```

Next Implementer handoff must be `READY_FOR_REVIEW`, except only a proven DHI entitlement blocker, emergency security reopen, or final owner-governance action.

---

## 6. Governance remains final gate

After the technical required-gate is fully green, enforce/verify:

```text
main protected = TRUE
pull request required = TRUE
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

Do not start FAZ 7.2 and do not merge before exact-head Reviewer `READY_TO_LOCK` plus literal user `LOCK` in the Implementer flow.

```text
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
USER_LOCK_AUTHORIZED: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
FAZ_7_2_STARTED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```


### Live superseding observation — 2026-09-19

Current PR #34 exact head has advanced to:

```text
1992bdd8f74a736ba7ee129d4d89a0c011386a76
run = 35399578554
```

Current exact-head state:

```text
source-boundary       = PASS
static-contracts      = PASS
container-validation = PASS
faz6-commerce-replay  = PASS
DHI authentication   = PASS
n8n-validation        = IN_PROGRESS
required-gate         = pending n8n-validation
```

The delta from the prior observed head is confined to `deploy/containers/n8n-frozen-candidate-ci.sh`; current commit only extends the bounded node-types readiness wait for n8n migrations. No frozen application or workflow JSON change is introduced. No new design/security decision is required while this exact-head run is active.
