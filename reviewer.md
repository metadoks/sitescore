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
REVIEWER_STATE: DESIGN_DECISION_ISSUED
IMPLEMENTER_ACTION: APPLY_EXACT_ALPINE_RUNTIME_SECURITY_PINS_AND_COMPLETE_7_1
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 14754b74ecd6a2c2018acc11f52fc989ff9abb4a
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
LIVE_MAIN_PROTECTED: FALSE
LIVE_REQUIRED_CHECKS: NONE

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: EXACT_RUNTIME_SECURITY_PIN_REMEDIATION_AUTHORIZED

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

# 1. AUTHORITY CONTINUITY

The original FAZ 7.1 contract and all later Reviewer security decisions remain authoritative except where this decision explicitly supersedes the prior prohibition on locally changing the three exact Alpine runtime package versions listed in Section 4.

Key prior Reviewer decisions remain in force:

```text
original 7.1 contract:
  c61c772ccd8192cce0475b4fd30a0cb0a74b1b37
verified vendor OpenVEX reconciliation:
  deb05237d075fac4f046264ada5933fb8a0de813
upstream-faithful hardened rebuild decision:
  b4053b3d6e01dc4aa6f42b83b12c3336d07c0b89
corrected runtime-base construction:
  afabb82f6cdcbb77f647de889d8433b3d0092984
APK-solver attribution decision:
  f518b7a8dc649d5d7dc99d96f7977d01b176fc0d
standing mechanical remediation + libc6 provider decision:
  c3d435ae851dc47b3335d55725c643e62f335bf1
```

Nothing here weakens frozen SiteScore application/business semantics, frozen n8n workflow bytes, vulnerability visibility, exact-head review/LOCK, governance, or no-FAZ-7.2/no-FAZ-8 boundaries.

---

# 2. INDEPENDENT REVIEWER AUDIT — FINAL HARDENED PROBE REACHED THE REAL SECURITY GATE

Reviewer independently audited live PR #34 and the exact current-head hardened probe.

```text
PR #34 = OPEN / DRAFT / MERGEABLE / UNMERGED
base = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
head = 14754b74ecd6a2c2018acc11f52fc989ff9abb4a
changed files = 21
21st path = .github/workflows/faz7-7-1-n8n-hardened-final-probe.yml
```

No frozen SiteScore application source or frozen n8n workflow JSON path is changed.

Exact probe:

```text
workflow = faz7-7-1-n8n-hardened-final-probe
run = 33716905456
job = 100527891394
artifact id = 9879672843
artifact sha256 = 5b935f403ce42273eb14baec5666741722502470a89f3e0a4b36c7aee0204f92
```

The probe passed all mechanics through the real vulnerability evaluation:

```text
latest stable re-enumeration = PASS
exact upstream source/build binding = PASS
hardened runtime base construction = PASS
libc6-compat capability/provider proof = PASS
stable n8n production closure build = PASS
final hardened n8n image build = PASS
linux/amd64 = PASS
non-root = PASS
n8n --version = 2.37.7 = PASS
startup/loadability = PASS
frozen workflow imports = PASS
SPDX = PASS
raw Grype = PASS
verified upstream OpenVEX = PASS
CISA KEV correlation = PASS
security-gate execution = PASS
```

Exact final probe image identity:

```text
image id/digest = sha256:6a4caf1fa739c31a5af3255167a3824a00c0f9930695c10654dfab405c02a46b
arch = amd64
user = node
version = 2.37.7
```

The security result itself is a TRUE FAIL, not a mechanics failure:

```text
RAW_CRITICAL = 4
RAW_HIGH = 17
CISA_KEV = 0
NEW_HIGH_INTRODUCED = 0
BRACE_EXPANSION_HIGH_BLOCKING = 0
IP_ADDRESS_HIGH_BLOCKING = 0
OS_HIGH_BLOCKING = 16
NODEMAILER_EXCEPTION_CANDIDATES = 1
PRELIMINARY_HARDENED_SECURITY_PASS = false
```

Verified reconciliation:

```text
N8N_ACTIONABLE_GATE = FAIL
N8N_REMEDIABLE_UNDISPOSITIONED_CRITICAL = 4
N8N_REMEDIABLE_UNDISPOSITIONED_HIGH = 17
N8N_VENDOR_AFFECTED_CRITICAL/HIGH = 0
N8N_VENDOR_UNDER_INVESTIGATION_CRITICAL/HIGH = 0
N8N_VEX_NOT_AFFECTED_ALLOWED_CRITICAL/HIGH = 0
N8N_CISA_KEV_MATCHES = 0
OPENVEX_ASSET_SHA256_VERIFIED = true
```

Because real security evaluation failed, nodemailer reachability proof, n8n static contracts and order/recovery runtime smokes were correctly not promoted as final pass evidence in this run.

---

# 3. EXACT ROOT CAUSE — THREE STALE ALPINE RUNTIME PACKAGES PLUS THE ALREADY-KNOWN NODEMAILER HIGH

All 4 CRITICAL and 16 of 17 HIGH findings are concentrated in three retained Alpine runtime packages. They are scanner-reported as FIXED and remediable.

## OpenSSL runtime pair

Installed:

```text
libcrypto3 = 3.5.7-r1
libssl3    = 3.5.7-r1
```

Scanner fixed version for all corresponding findings:

```text
3.5.8-r0
```

CRITICAL findings are the two advisories duplicated across the two split packages:

```text
CVE-2026-63073
CVE-2026-75803
```

HIGH advisories duplicated across the pair:

```text
CVE-2026-18798
CVE-2026-63076
CVE-2026-14457
CVE-2026-14456
CVE-2026-63072
CVE-2026-54874
CVE-2026-63075
```

## Expat runtime

Installed:

```text
libexpat = 2.8.3-r1
```

Scanner fixed version:

```text
2.8.4-r0
```

HIGH findings:

```text
CVE-2026-66046
CVE-2026-76641
```

## npm residual

The 17th HIGH is the already-known exact residual candidate:

```text
package = nodemailer
installed = 8.0.10
advisory = GHSA-p6gq-j5cr-w38f
fixed = 9.0.1+
```

No other CRITICAL/HIGH package family remains in the probe evidence.

Current upstream n8n master build-base workflow still binds Node 26.7.0 to the same DHI digest used by the probe, so simply repeating the same upstream runtime chain cannot remediate the three stale Alpine runtime packages. Current public 2.38.x releases observed by Reviewer are prereleases; the selected non-prerelease 2.x stable path remains 2.37.7 under the existing official-first enumeration rule.

---

# 4. DESIGN DECISION — AUTHORIZE EXACT, PINNED ALPINE RUNTIME SECURITY DELTA

The prior prohibition on locally changing `libssl3`, `libcrypto3`, and `libexpat` is superseded ONLY for the exact version remediation below.

Implementer is authorized to rebuild the hardened runtime base from the same exact upstream source/build identities and same Alpine 3.24 repositories, then BEFORE final `apk-tools` removal apply exactly:

```text
libcrypto3: 3.5.7-r1 -> 3.5.8-r0
libssl3:    3.5.7-r1 -> 3.5.8-r0
libexpat:   2.8.3-r1 -> 2.8.4-r0
```

Recommended package-manager form is an exact-version transaction equivalent to:

```sh
apk add --no-cache --upgrade \
  'libcrypto3=3.5.8-r0' \
  'libssl3=3.5.8-r0' \
  'libexpat=2.8.4-r0'
```

This is NOT authorization for:

```text
apk upgrade
floating package upgrades
another Alpine minor
another Node line
another base distribution
arbitrary OS package updates
manual library copying
scanner suppression
SiteScore-authored VEX
```

The exact package transaction must use the same repository configuration already present in the bound DHI/Alpine base. Do not add an unbound third-party package repository.

Required evidence around this exact security delta:

```text
/etc/apk/repositories before transaction
apk world before/after
full installed DB/package inventory before/after
apk transaction log
apk policy/candidate evidence for all three pins
machine-readable package delta
```

The package delta must prove:

```text
- the only intentional version changes are the three exact pins above;
- no package is downgraded;
- no new arbitrary top-level capability is introduced;
- openssh remains absent;
- graphicsmagick remains absent;
- apk-tools is removed from the final base;
- libc6-compat capability remains satisfied by the proven APK provider;
- tini/tzdata/ca-certificates/librdkafka and required Node/runtime libraries remain present.
```

If APK cannot resolve these exact versions from the existing bound repositories, or if satisfying them requires a materially broader package/base/distribution change, STOP as a true design/security blocker. Do not silently substitute another version.

The resulting image must no longer be described as byte-equivalent to the upstream runtime base. Canonical characterization:

```text
N8N_APPLICATION_SOURCE: EXACT_OFFICIAL_STABLE_SOURCE
N8N_BUILD_MECHANICS: UPSTREAM_BOUND
N8N_RUNTIME_BASE: UPSTREAM_DERIVED_SITE_SCORE_HARDENED
N8N_RUNTIME_SECURITY_DELTA: EXACT_PINNED_3_PACKAGE_PATCH
```

Application source remains untouched.

---

# 5. RERUN THE COMPLETE SECURITY/RUNTIME GATE — NO PARTIAL PROMOTION

After applying the exact three-package runtime delta, rerun the complete final candidate pipeline from scratch.

Mandatory threshold remains:

```text
CISA KEV = 0
CRITICAL = 0
OS HIGH = 0
brace-expansion HIGH = 0
ip-address HIGH = 0
no new HIGH introduced
```

No vendor VEX exception is expected or required for the three patched Alpine packages; the fixed bytes themselves must eliminate those findings.

After OS CRITICAL/HIGH reach zero, evaluate the exact nodemailer residual. It may remain the sole HIGH only if EVERY previously-authorized containment condition passes, including:

```text
workflow hashes exact
frozen workflows contain no emailSend
NODES_EXCLUDE includes n8n-nodes-base.emailSend
runtime proves emailSend unavailable/non-executable
no SMTP host/user/pass/credential or n8n user-management mail transport configured/injected
editor/admin/API non-public
no newly-enabled Code/ExecuteCommand/ReadWriteFile alternate path
permanent risk record contains exact advisory, controls, owner, expiry/re-review triggers
```

If nodemailer is the sole HIGH and every containment proof passes, the residual exception may be accepted under the prior Reviewer decision. Otherwise security gate remains FAIL.

Then run all remaining n8n compatibility evidence:

```text
n8n static contracts = PASS
order-paid webhook/auth/payload smoke = PASS
recovery schedule/API smoke = PASS
workflow hashes = exact frozen values
no workflow migration
no node substitution
no credential semantic migration
```

---

# 6. PERMANENTIZE ONLY THE SUCCESSFUL CANDIDATE

Only after the patched final candidate passes Section 5, convert successful mechanics into permanent FAZ 7.1 assets.

Required permanent outcome includes:

```text
deploy/containers/n8n-image.lock
reproducible hardened n8n build assets under deploy/containers/**
exact stable source commit/tree identity
exact builder/DHI/upstream recipe identities
exact 3-package runtime security delta manifest
removed-capability inventory
final linux/amd64 digest
non-root/runtime identity
SPDX
raw Grype
CISA KEV/OpenVEX reconciliation
nodemailer residual record if still applicable
provenance/attestation evidence
```

Permanent publish target remains:

```text
ghcr.io/metadoks/sitescore-n8n
```

Do not publish/deploy a pre-LOCK production baseline. The PR and CI may build/load/scan candidate bytes and retain evidence.

Remove the temporary final-probe workflow if its mechanics are absorbed into permanent authorized CI; do not leave redundant temporary probe machinery in final scope without an explicit reason in Implementer handoff.

Permanent `n8n-validation` must validate the selected hardened SiteScore image identity, not the superseded official `n8nio/n8n@...` identity.

---

# 7. CURRENT PERMANENT CI FAILURES — CLASSIFIED AS MECHANICAL, FIX WITHOUT REVIEWER ROUND-TRIPS

Exact current-head permanent CI:

```text
workflow = faz7
run = 33716905493
head = 14754b74ecd6a2c2018acc11f52fc989ff9abb4a
conclusion = FAILURE
```

Independent Reviewer classification:

## source-boundary

```text
job = 100527891399
failure = fatal: <base>...<head>: no merge base
classification = shallow-history mechanics
```

Fix fetch/history/merge-base mechanics and rerun. Do not weaken allowed/frozen path policy.

## n8n-validation

```text
job = 100527891300
failure occurs before image pull because deploy/containers/n8n-image.lock is not yet permanentized for the accepted hardened candidate
classification = expected pre-permanentization wiring
```

After security pass, write the final lock and make permanent validation consume the accepted SiteScore hardened image.

## FAZ6 Commerce replay

```text
job = 100527891485
frozen commit checkout = PASS
container/test invocation = FAILURE before preserved output was printed
classification = replay-environment/evidence mechanics pending exact diagnosis
```

Fix the replay environment/output capture without editing frozen FAZ6 source/tests and obtain exact `417 passed`.

## application container regression

```text
job = 100527891545
API/Commerce runtime/test image builds = PASS
non-root/runtime identity/read-only contract = PASS
regression command step = FAILURE before captured test output was printed
classification = test-environment/evidence mechanics pending exact diagnosis
```

Fix execution/output capture/environment only. Required results remain exactly:

```text
API = 114 passed
report = 24 passed
Commerce = 416 passed + exact one phase-local deselect
```

## static-contracts

```text
job = 100527891486
conclusion = SUCCESS
```

`required-gate` fails only because mandatory upstream jobs are currently red.

All of the above mechanical CI corrections remain covered by standing remediation authority. Do not return to Reviewer for them individually.

---

# 8. FINISH ALL 7.1 TECHNICAL GATES IN ONE CONTINUOUS IMPLEMENTER RUN

After n8n security passes, continue without Reviewer stop until all are true on the same exact final PR head:

```text
API current suite = 114 PASS
report = 24 PASS
Commerce forward-applicable = 416 PASS + exact one phase-local deselect
FAZ6 frozen Commerce replay = 417 PASS
dispatcher supervisor/static contracts = PASS
API image build/runtime/non-root/PDF/font = PASS
Commerce image build/runtime/non-root = PASS
API/Commerce/n8n SBOM = PASS
API/Commerce vulnerability policy = PASS
n8n security/runtime/workflow gate = PASS
permanent Actions full-40-char SHA pins = PASS
source-boundary = PASS
faz7 / required-gate = PASS on exact final head
frozen SiteScore app source diff = NONE
frozen n8n workflow JSON diff = NONE
cloud/IaC mutation = NONE
production secret committed = NONE
```

Do not begin FAZ 7.2 or FAZ 8.

---

# 9. GOVERNANCE — SINGLE EXPECTED OWNER-ACTION BLOCKER AFTER ALL TECHNICAL GATES

Live Reviewer check still shows:

```text
main protected = FALSE
required checks = NONE
repo visibility = private
allow_merge_commit = TRUE
allow_squash_merge = TRUE
allow_rebase_merge = TRUE
allow_auto_merge = FALSE
```

Required final governance remains:

```text
main protected = TRUE
PR required = TRUE
required status check = faz7 / required-gate
strict/up-to-date = TRUE
force push = blocked
branch deletion = blocked
bypass/admin bypass disabled where supported
merge commits = enabled
squash = disabled
rebase = disabled
auto-merge = disabled
```

Implementer must finish every technical/code/evidence gate first. If connected GitHub tooling still cannot mutate these owner settings, return one consolidated owner-action blocker only at the end. Do not stop earlier merely because governance is pending.

If GitHub plan/capability itself makes the frozen governance impossible, establish that exact limitation and return `OPS71-GOV-001: PLAN_CAPABILITY_BLOCKED` rather than weakening requirements.

---

# 10. TERMINAL HANDOFF ONLY

The next useful Implementer handoff must be exactly one of:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

with all technical gates + live governance compliant, or:

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

where the blocker is either:

```text
- the exact three-package patch cannot be resolved without a broader unauthorized security/base change;
- the final patched candidate still has non-authorized CRITICAL/HIGH/KEV;
- frozen workflow compatibility requires semantic modification;
- or all technical gates pass and only manual owner governance configuration remains.
```

Do NOT return for another mechanical shell/YAML/parser/history/test-output issue already authorized above.

```text
READY_TO_LOCK: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```
