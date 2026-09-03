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
IMPLEMENTER_STATE: BLOCKED_LATEST_STABLE_2_37_9_REQUIRES_NEW_SECURITY_DESIGN_DECISION
IMPLEMENTER_ACTION: STOP_FOR_REVIEWER_DESIGN_DECISION
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
PR_STATE: OPEN
PR_DRAFT: TRUE
PR_MERGEABLE_AT_LAST_CHECK: TRUE
PR_MERGED: FALSE
CURRENT_HEAD_SHA: 609adf39771fb1bb7dfacfb78ccfe65f4471c4a3
CURRENT_CHANGED_FILE_COUNT: 20

OPS71_GHA_EXEC_001_STATUS: RESOLVED_CONFIRMED
OPS71_GOV_001_STATUS: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71_N8N_VULN_001_STATUS: LATEST_STABLE_2_37_9_OFFICIAL_GATE_FAILED_NEW_DESIGN_REQUIRED

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

FAZ6_HISTORICAL_N8N_VERSION: 2.33.4
FAZ6_HISTORICAL_N8N_DIGEST: sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
FAZ7_HISTORICAL_N8N_STATUS: SUPERSEDED_FOR_SECURITY
PREVIOUS_REVIEWER_BOUND_STABLE: 2.37.7
LATEST_OFFICIAL_STABLE: 2.37.9
NEW_N8N_BASELINE_STATUS: NOT_SELECTED_LATEST_OFFICIAL_SECURITY_GATE_FAILED
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

## 1. Reviewer decision consumed exactly

The latest Reviewer decision was read before continuing implementation. It authorized the exact three-package Alpine runtime remediation only for the then-bound n8n 2.37.7 hardened rebuild identities:

```text
libcrypto3: 3.5.7-r1 -> 3.5.8-r0
libssl3:    3.5.7-r1 -> 3.5.8-r0
libexpat:   2.8.3-r1 -> 2.8.4-r0
```

The Reviewer explicitly prohibited floating `apk upgrade`, arbitrary package versions, another Alpine minor, another Node line/base distribution, scanner suppression, and SiteScore-authored VEX. Permanentization remained conditional on the complete security/runtime gate.

No such prohibited substitution was made.

---

## 2. Exact 2.37.7 patched candidate reached the intended security state

Before the upstream stable changed, the Reviewer-authorized exact three-package patch was executed against the exact bound 2.37.7 source/build chain.

Relevant completed probe:

```text
workflow = faz7-7-1-n8n-patched-final-probe
run = 33741721597
job = 100604947932
source head = 425f35c80da22c373f50140c70bb81f6743a8ba0
artifact id = 9889756482
artifact sha256 = 14d22c2c419e5e407b592d83c154e30b13d5a86e36eb5c962173ea6cacdf7259
artifact size = 1260955 bytes
created_at = 2026-09-03T10:49:12Z
expires_at = 2026-09-17T10:49:11Z
```

The exact package-delta construction and security evaluation reached:

```text
RAW_CRITICAL = 0
RAW_HIGH = 1
BLOCKING_CRITICAL = 0
CISA_KEV = 0
OS_HIGH_BLOCKING = 0
IP_ADDRESS_HIGH_BLOCKING = 0
BRACE_EXPANSION_HIGH_BLOCKING = 0
NEW_HIGH_INTRODUCED = 0
OTHER_HIGH = 0
NODEMAILER_EXCEPTION_CANDIDATES = 1
```

The sole residual was the already-authorized conditional exception candidate:

```text
package = nodemailer
installed = 8.0.10
advisory = GHSA-p6gq-j5cr-w38f
fixed = 9.0.1+
```

The generic upstream OpenVEX reconciliation truthfully remained `FAIL` because that HIGH remained undispositioned; it was not suppressed or rewritten. The temporary probe had a CI control-flow defect that skipped the separately-authorized nodemailer containment/static/runtime branch even though the machine-readable security summary had reached the sole-nodemailer state.

A narrow follow-up changed only the probe control flow: the generic OpenVEX truth remained visible, while exception eligibility was re-read from the persisted JSON and required exact zero counts for all other blockers. No vulnerability threshold, application source, workflow, or scanner result was changed.

Control-flow-only commit:

```text
6fb603124a99185064b9855ad6028716e6c0e347
```

The corrected 2.37.7 probe did not proceed to candidate promotion because the required latest-stable guard detected a new upstream stable first.

---

## 3. Latest-stable guard detected n8n 2.37.9 and correctly stopped 2.37.7 promotion

Corrected probe run:

```text
workflow = faz7-7-1-n8n-patched-final-probe
run = 33794600549
job = 100779133721
source head = 6fb603124a99185064b9855ad6028716e6c0e347
```

The first authoritative stable enumeration stopped with:

```text
new official stable 2.37.9; official-first revalidation required
```

Therefore the successful 2.37.7 security reduction was not permanentized and was not selected as the FAZ 7.1 n8n baseline.

This is required by the existing official-first policy, not a 2.37.7 security regression.

---

## 4. Official n8n 2.37.9 was revalidated before any custom hardening

Because a new non-prerelease stable existed, Implementer created a temporary official-image-only probe. It did not rebuild or patch n8n and did not transfer the 2.37.7 package remediation to 2.37.9.

Probe source commit:

```text
6eeafd4167f8c58cd12a8eb7683f5721f5f8325d
```

Exact run/evidence:

```text
workflow = faz7-7-1-n8n-latest-official-probe
run = 33795008277
job = 100780473708
artifact id = 9909036938
artifact sha256 = 3a504c9bee16b79be01a40cd1b21adb2bab322c9c58c8dc94cf30cf85aa07d42
artifact size = 1059491 bytes
created_at = 2026-09-03T19:18:25Z
expires_at = 2026-09-17T19:18:24Z
```

Release/image identity:

```text
version = 2.37.9
release tag = n8n@2.37.9
release id = 382036593
published_at = 2026-09-03T13:16:03Z
linux/amd64 official digest = n8nio/n8n@sha256:ed6bbab565eddbb688f394594cb2932d2b3b24f02240299a8fcce78bfe4201db
```

Official image pre-security compatibility evidence passed:

```text
latest stable enumeration = PASS
linux/amd64 image binding = PASS
n8n --version = 2.37.9 = PASS
startup/loadability = PASS
frozen order-paid workflow import = PASS
frozen recovery workflow import = PASS
workflow hashes = exact frozen values
SPDX generation = PASS
raw Grype = PASS
exact-release OpenVEX asset digest verification = PASS
CISA KEV correlation = PASS
```

Frozen hashes remained:

```text
order-paid = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery   = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

---

## 5. Official 2.37.9 security gate is a true FAIL

Verified reconciliation:

```text
N8N_CISA_KEV_MATCHES = 0
N8N_VENDOR_AFFECTED_CRITICAL = 0
N8N_VENDOR_AFFECTED_HIGH = 0
N8N_VENDOR_UNDER_INVESTIGATION_CRITICAL = 0
N8N_VENDOR_UNDER_INVESTIGATION_HIGH = 0
N8N_VEX_SCANNER_CONFLICT_CRITICAL = 0
N8N_VEX_SCANNER_CONFLICT_HIGH = 0
N8N_REMEDIABLE_UNDISPOSITIONED_CRITICAL = 11
N8N_REMEDIABLE_UNDISPOSITIONED_HIGH = 37
N8N_UNDISPOSITIONED_CRITICAL = 1
N8N_UNDISPOSITIONED_HIGH = 3
N8N_RAW_CRITICAL = 12
N8N_RAW_HIGH = 40
N8N_VEX_NOT_AFFECTED_ALLOWED_CRITICAL = 0
N8N_VEX_NOT_AFFECTED_ALLOWED_HIGH = 0
N8N_ACTIONABLE_GATE = FAIL
OPENVEX_ASSET_SHA256_VERIFIED = true
```

Direct official-gate summary:

```text
BLOCKING_CRITICAL = 12
BLOCKING_HIGH = 40
CISA_KEV = 0
OFFICIAL_LATEST_SECURITY_PASS = false
```

Blocking findings grouped by package:

```text
brace-expansion          = 1
fast-uri                 = 4
graphicsmagick           = 2
ip-address               = 1
libcrypto3               = 9
libexpat                  = 2
libssl3                   = 9
nodemailer                = 1
openssh                   = 3
openssh-client-common     = 3
openssh-client-default    = 3
openssh-keygen            = 3
openssh-server            = 3
openssh-server-common     = 3
openssh-sftp-server       = 3
tiff                      = 2
```

The presence of `fast-uri` blockers and the changed official-image vulnerability closure means the previous 2.37.7 design decision cannot safely be treated as blanket authorization for a 2.37.9 rebuild. In particular, the Reviewer authorization named exact 2.37.7-bound source/build/runtime identities and exact package-version deltas.

Implementer therefore did NOT:

```text
- copy the 2.37.7 three-package pin transaction onto 2.37.9;
- invent a fast-uri remediation;
- arbitrarily upgrade npm dependencies;
- alter workflow semantics;
- suppress or ignore the 12 CRITICAL / 40 HIGH findings;
- select 2.37.9 as production baseline;
- fall back to 2.37.7 despite the official-first latest-stable rule.
```

---

## 6. Temporary probes removed; PR restored to permanent 20-file scope

Temporary diagnostic/probe workflows were removed after evidence preservation:

```text
.github/workflows/faz7-7-1-ci-diagnostics.yml
.github/workflows/faz7-7-1-n8n-latest-official-probe.yml
.github/workflows/faz7-7-1-n8n-patched-final-probe.yml
```

Cleanup commits included:

```text
dc778074969a71653dde3564d0d458dcc28f061f
1168ce71ae86017beaf808468d900db381f39260
609adf39771fb1bb7dfacfb78ccfe65f4471c4a3
```

Current PR #34 state after cleanup:

```text
head = 609adf39771fb1bb7dfacfb78ccfe65f4471c4a3
base = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
OPEN = true
DRAFT = true
MERGEABLE = true
MERGED = false
changed files = 20
additions = 3864
deletions = 0
```

Changed paths are again exactly the original permanent FAZ 7.1 20-file set. No probe-only workflow remains in the PR diff.

---

## 7. Mandatory STOP / requested Reviewer decision

A fresh Reviewer design decision is now required because the selected latest non-prerelease stable changed from 2.37.7 to 2.37.9 after the prior exact-remediation authorization, and the new official image fails with a different blocker closure.

```text
IMPLEMENTER_STATE: BLOCKED_LATEST_STABLE_2_37_9_REQUIRES_NEW_SECURITY_DESIGN_DECISION
IMPLEMENTER_ACTION: STOP_FOR_REVIEWER_DESIGN_DECISION
OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-N8N-VULN-001: LATEST_STABLE_2_37_9_OFFICIAL_GATE_FAILED_NEW_DESIGN_REQUIRED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
DESIGN_DECISION_REVIEW_REQUIRED: 1
CONTRACT_CHANGE_REQUIRED: 0
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
USER_LOCK_AUTHORIZED: NO
MERGE: NO
FAZ_7_2_STARTED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

Reviewer must decide whether FAZ 7.1 should now:

```text
A. bind and harden exact stable 2.37.9 under a newly-scoped upstream-faithful remediation decision, including explicit treatment of the newly observed fast-uri and other current blockers; or
B. issue another explicit policy/design path consistent with the official-first requirement.
```

Until Reviewer issues that decision, Implementer will not transfer the 2.37.7 security patch authorization to 2.37.9, will not permanentize an n8n baseline, will not merge PR #34, and will not start FAZ 7.2 or FAZ 8.
