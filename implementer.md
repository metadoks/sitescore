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
IMPLEMENTER_ACTION: STOP_FOR_REVIEWER_DESIGN_DECISION
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
CURRENT_HEAD_SHA: b012d4ee69257c4a6652340fda935690a28d8ffa
CURRENT_CHANGED_FILE_COUNT: 20

OPS71_GHA_EXEC_001_STATUS: RESOLVED_CONFIRMED
OPS71_GOV_001_STATUS: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71_N8N_VULN_001_STATUS: BLOCKED_NEW_CRITICAL_HIGH_PACKAGE_FAMILY_TOML_ON_LATEST_STABLE_2_37_10

DESIGN_DECISION_REVIEW_REQUIRED: 1
CONTRACT_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
MERGE_PERFORMED: NO
FAZ_7_2_STARTED: NO

LATEST_OFFICIAL_STABLE: 2.37.10
LATEST_OFFICIAL_DIGEST_AMD64: sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
NEW_N8N_BASELINE_STATUS: NOT_SELECTED_NEW_PACKAGE_FAMILY_REQUIRES_REVIEWER_DECISION
SELECTED_N8N_VERSION: NONE
SELECTED_N8N_DIGEST: NONE

APPLICATION_SOURCE_CHANGE: NONE
BUSINESS_SEMANTICS_CHANGE: NONE
N8N_WORKFLOW_JSON_CHANGE: NONE
N8N_APPLICATION_SOURCE_PATCH: NONE
SCANNER_SUPPRESSION: NONE
BLANKET_CVE_IGNORE: NONE
SITE_SCORE_AUTHORED_VEX: NONE
CLOUD_RESOURCE_MUTATION: NONE
PRODUCTION_SECRET_COMMITTED: NONE
```

---

## 1. Reviewer patch-forward decision consumed exactly

The current Reviewer decision authorized continuous FAZ 7.1 completion under n8n 2.37.9 hardened rebuild authority and Section 9 patch-forward continuity.

For a newer patch-level stable, Implementer was permitted to continue without another Reviewer round-trip only if every CRITICAL/HIGH remained within already-authorized package/advisory families and no new CISA KEV, package family, security exception, base design or workflow/API/credential migration appeared.

Reviewer Section 9.3 explicitly requires STOP on a new CRITICAL/HIGH package family.

No authorization was found for `toml` remediation or a `toml` residual-risk exception.

---

## 2. n8n 2.37.9 was superseded correctly by the latest-stable guard

The corrected 2.37.9 hardened probe reached its mandatory fresh stable enumeration and stopped before building because a new official stable existed:

```text
new official stable 2.37.10 exists; stop and validate official image first
```

No 2.37.9 candidate was promoted.

---

## 3. Exact n8n 2.37.10 official-first validation

Upstream release/source identity:

```text
version = 2.37.10
tag = n8n@2.37.10
release id = 382600929
published_at = 2026-09-04T09:13:04Z
source commit = 5542b8b6419cb6925cca8f11b270c9bfbe09d85e
source tree = 8d44b0feb4a74c9fb07f4156793e3c7eaee30fc0
OpenVEX asset id = 544085903
OpenVEX sha256 = a2b6a9444b21027742cf4b120f3b6e22d745c9d3a025d766635b6e2304ed41d7
```

Official linux/amd64 image:

```text
n8nio/n8n@sha256:307d6065be25619aa24cfc63a7c2f04ca56d084a08c05c8e9f189a89f353b1ec
arch = amd64
user = node
runtime version = 2.37.10
```

Official probe:

```text
workflow = faz7-7-1-n8n-23710-official-probe
run = 33972295439
job = 101322830102
source PR head = b9ad4809a88b7e4f7ffcf0ffb5739fb7974ede5e
artifact id = 9971353356
artifact sha256 = 2b3300eb002da3cd710984df689c4cb57ceed4cf97b838c67283d85c78dfcba7
artifact size = 1061775 bytes
created_at = 2026-09-05T14:41:41Z
expires_at = 2026-09-19T14:41:39Z
```

Compatibility/evidence before security decision:

```text
latest-stable enumeration = PASS
exact release/source/tree binding = PASS
frozen workflow hashes = PASS
linux/amd64 = PASS
non-root = PASS
n8n --version 2.37.10 = PASS
startup/healthz = PASS
order-paid frozen workflow import = PASS
recovery frozen workflow import = PASS
pinned Syft SPDX = PASS
pinned Grype = PASS
exact-release OpenVEX digest verification = PASS
CISA KEV correlation execution = PASS
```

Frozen hashes remained exact:

```text
order-paid = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery   = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

---

## 4. Official 2.37.10 security result — FAIL

Verified reconciliation result:

```text
N8N_CISA_KEV_MATCHES = 0
N8N_RAW_CRITICAL = 12
N8N_RAW_HIGH = 42
N8N_REMEDIABLE_UNDISPOSITIONED_CRITICAL = 11
N8N_REMEDIABLE_UNDISPOSITIONED_HIGH = 39
N8N_UNDISPOSITIONED_CRITICAL = 1
N8N_UNDISPOSITIONED_HIGH = 3
N8N_ACTIONABLE_GATE = FAIL
OPENVEX_ASSET_SHA256_VERIFIED = true
```

The official image still contains package families already covered by the prior hardened authority, including:

```text
openssh family
graphicsmagick/tiff closure
libcrypto3
libssl3
libexpat
brace-expansion
ip-address
fast-uri
nodemailer residual candidate
```

However the official 2.37.10 image also introduces a CRITICAL/HIGH blocker package family not covered by the current Reviewer decision:

```text
package = toml
package type = npm
installed = 3.0.0
HIGH advisories:
  GHSA-v5mp-jgw5-2x6j
  GHSA-82x6-q7mm-w9cf
count = 2 HIGH
```

This is a new package family relative to the authorized closure. Therefore Reviewer Section 9.3 is triggered literally.

No local `toml` dependency override, suppression, reachability exception, VEX, arbitrary dependency upgrade or alternate base was attempted.

---

## 5. Why hardened 2.37.10 was NOT started

The patch-forward authority requires all CRITICAL/HIGH package families to remain already-authorized families. `toml` violates that precondition.

Therefore the Implementer did NOT self-authorize:

```text
toml version override
toml lockfile override
toml reachability exception
scanner suppression
SiteScore-authored VEX
new base/runtime design
```

The correct terminal state is a true Reviewer design/security decision, not another mechanical remediation loop.

---

## 6. Permanent CI status reached before mandatory STOP

On the recent exact-head permanent CI work:

```text
source-boundary = PASS
frozen application source diff = NONE
frozen n8n workflow hashes = PASS
full-40-character Action pin checker = PASS
static-contracts = PASS
FAZ6 historical Commerce replay = PASS
```

Historical replay has already been proven at:

```text
417 passed, 139 warnings
```

Application container validation reached:

```text
API image build = PASS
Commerce image build = PASS
amd64/non-root/labels/read-only contract = PASS
API regression = 114 PASS
report regression = 24 PASS
Commerce = 416 PASS + 1 phase-local final-freeze test accidentally executed
```

The Commerce issue is a known mechanics-only deselection-path defect: pytest working directory uses relative node ID `tests/...`, while the current command passed an absolute `/testsrc/sitescore-commerce/tests/...` deselect path. The frozen test itself is unchanged. This mechanics fix was deliberately not continued after the mandatory Section 9.3 security STOP.

Permanent n8n baseline remains unselected, so `n8n-validation` / aggregate required gate are not yet expected to pass.

---

## 7. Cleanup / exact live PR state

All temporary n8n 2.37.9 / 2.37.10 probe workflows were removed after evidence preservation.

Current PR #34:

```text
head = b012d4ee69257c4a6652340fda935690a28d8ffa
base = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
state = OPEN
DRAFT = TRUE
mergeable = TRUE
merged = FALSE
changed files = 20
```

The changed-file scope is back to the original permanent FAZ 7.1 set. No frozen application or n8n workflow JSON path is changed.

---

## 8. Reviewer decision required

Single true technical blocker requiring Reviewer authority:

```text
OPS71-N8N-VULN-001:
LATEST_STABLE_2_37_10_INTRODUCES_NEW_HIGH_PACKAGE_FAMILY_TOML

package = toml
installed = 3.0.0
advisories = GHSA-v5mp-jgw5-2x6j, GHSA-82x6-q7mm-w9cf
CISA KEV = 0
```

Reviewer must decide whether and under what exact upstream-bound conditions `toml` may be remediated or otherwise dispositioned. Implementer will not infer this authority.

Owner governance remains separately pending and unchanged, but it was not the cause of this technical STOP.

```text
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```
