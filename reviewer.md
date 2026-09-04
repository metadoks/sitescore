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
IMPLEMENTER_ACTION: RESUME_7_1_WITH_N8N_2_37_9_UPSTREAM_ADOPTED_SECURITY_BACKPORTS_AND_RUNTIME_HARDENING
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 247a54b2a657bf5b8fdbc1558ceec818c2ec41f9
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
LIVE_MAIN_PROTECTED: FALSE
LIVE_REQUIRED_CHECKS: NONE

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_UNDER_N8N_2_37_9_HARDENED_REBUILD_AUTHORITY

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

The original FAZ 7.1 contract and all later Reviewer security/governance decisions remain authoritative except where this decision explicitly rebinds the selected n8n stable and broadens the already-authorized security remediation only to the exact upstream-adopted dependency backports and exact runtime package controls listed below.

No frozen SiteScore scoring/business/application semantics may change. Frozen n8n workflow JSON bytes remain immutable. No scanner suppression, blanket ignore, SiteScore-authored VEX, deployment shortcut, merge, FAZ 7.2 work, or FAZ 8 work is authorized.

Standing mechanical remediation authority remains active: Implementer should continue through ordinary YAML/shell/build/test-environment/evidence defects without returning to Reviewer unless a true design/security/governance blocker occurs.

---

# 2. FRESH REVIEWER FINDING — LATEST OFFICIAL STABLE IS 2.37.9

Reviewer independently re-enumerated upstream n8n releases on 2026-09-04. The current official non-draft/non-prerelease stable remains:

```text
version = 2.37.9
release tag = n8n@2.37.9
release id = 382036593
published_at = 2026-09-03T13:16:03Z
source commit = 073ec4552a6675a10f5b212d55bdc00c91d4829b
source tree = e825fca3c49cca4c0dddf23a9fc426a289118ed1
official linux/amd64 image = n8nio/n8n@sha256:ed6bbab565eddbb688f394594cb2932d2b3b24f02240299a8fcce78bfe4201db
```

Exact official 2.37.9 Docker recipe remains on the older upstream release build chain:

```text
NODE_VERSION = 26.5.1
builder = node:26.5.1-alpine3.24@sha256:233761595746769ebfdb6090f44fc7cdf818ae0ce62d2b37e0367723b9823e36
runtime = n8nio/base:26.5.1@sha256:1b0bca5c94bbd04ad2120b9e9892a8bc717a1d88efa76fefe452c59bdc611d25
release Dockerfile blob = c46edacc7bcf7d5d8c74beb174c1a713b97c6f14
```

Current upstream master has already moved its n8n build mechanics to:

```text
master observed commit = fd105a6dc2cd51b5e5fd64c2efad57e6801d2325
master Dockerfile blob = f72e1a3f3aae40319e58989e5fc2a71e687a1b59
NODE_VERSION = 26.7.0
builder = node:26.7.0-alpine3.24@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019
runtime = n8nio/base:26.7.0@sha256:33687300c4e94dc00f42ec79ae15082ae07330ecd82ae1167125905b65908ff8
```

The prior Reviewer rule permitting exact stable source to be rebuilt with exact current upstream master build mechanics remains valid.

---

# 3. INDEPENDENT REVIEWER AUDIT — OFFICIAL 2.37.9 SECURITY GATE REALLY FAILS

Reviewer independently inspected the Implementer evidence from:

```text
workflow = faz7-7-1-n8n-latest-official-probe
run = 33795008277
job = 100780473708
artifact id = 9909036938
artifact sha256 = 3a504c9bee16b79be01a40cd1b21adb2bab322c9c58c8dc94cf30cf85aa07d42
```

Official-image compatibility passed before the security gate:

```text
linux/amd64 binding = PASS
n8n --version = 2.37.9 = PASS
startup/loadability = PASS
frozen order workflow import = PASS
frozen recovery workflow import = PASS
frozen workflow hashes = PASS
SPDX generation = PASS
raw Grype generation = PASS
exact release OpenVEX digest verification = PASS
CISA KEV correlation = PASS
```

The security result is a true failure:

```text
RAW_CRITICAL = 12
RAW_HIGH = 40
BLOCKING_CRITICAL = 12
BLOCKING_HIGH = 40
CISA_KEV = 0
OFFICIAL_LATEST_SECURITY_PASS = false
```

Exact blocker families:

```text
OS:
  libcrypto3 3.5.7-r1
  libssl3 3.5.7-r1
  libexpat 2.8.2-r0
  openssh family 10.3_p1-r0
  graphicsmagick 1.3.47-r0
  tiff 4.7.1-r0

npm:
  brace-expansion 5.0.8
  ip-address 10.2.0
  fast-uri 3.1.5
  nodemailer 8.0.10
```

Scanner fixed versions include:

```text
libcrypto3/libssl3 -> 3.5.8-r0
libexpat -> 2.8.4-r0
openssh family -> 10.3_p1-r1
brace-expansion -> 5.0.9
ip-address -> 10.3.1
fast-uri -> 3.1.6
nodemailer -> 9.0.1+
```

No CISA KEV match exists in this evidence.

---

# 4. UPSTREAM-ADOPTED NPM SECURITY BACKPORTS — NOW AUTHORIZED FOR EXACT 2.37.9 SOURCE

Reviewer independently verified current upstream n8n master already carries the following production dependency overrides:

```text
fast-uri: 3.1.6
ip-address@10: 10.3.1
brace-expansion@5: 5.0.9
```

The exact upstream evidence commit containing these overrides is:

```text
64de0e71db286afb7537324aa4367a3f97cd6d19
```

Therefore the previous upstream-adopted-backport rule is extended to exact n8n 2.37.9 source. Implementer MAY apply only these exact dependency overrides to the selected stable build metadata/lock closure:

```text
fast-uri -> 3.1.6
ip-address@10 -> 10.3.1
brace-expansion@5 -> 5.0.9
```

Required controls:

```text
- retain exact upstream file/commit evidence;
- show the stable-source pre/post dependency metadata delta;
- rebuild the complete production closure from exact 2.37.9 source;
- no n8n application-source edits;
- no arbitrary npm/pnpm dependency upgrades;
- no package-manager floating resolution beyond the exact authorized values;
- verify the resulting lock graph actually contains the fixed versions and no vulnerable production copy remains.
```

`nodemailer 8.0.10 -> 9.x` remains NOT authorized as a local SiteScore backport because current upstream master still uses nodemailer 8.0.10. The previously-defined single residual nodemailer reachability exception remains the only possible residual HIGH path.

---

# 5. N8N 2.37.9 HARDENED RUNTIME AUTHORITY

Implementer is authorized to rebuild exact n8n 2.37.9 source using the exact current upstream master Node 26.7.0 builder/runtime mechanics identified in Section 2, preserving Alpine 3.24 and rebuilding native modules through the upstream mechanics. Do not copy unverified native modules across ABI boundaries.

## 5.1 Remove unused generic OS capabilities through APK solver

The prior authorization is carried forward to 2.37.9 for SiteScore's frozen workflow surface:

```text
apk del openssh graphicsmagick
```

or the exact package-manager-equivalent transaction using the same bound Alpine repository configuration.

The solver may remove the dependency closure it proves is no longer required, including tiff where that occurs naturally. Implementer MUST retain:

```text
apk world before/after
installed DB before/after
solver transaction log
reference-minus-hardened inventory
proof that explicit removals + solver closure equal actual removals
```

Do not hand-maintain a guessed transitive removal list. Do not remove required runtime libraries.

## 5.2 Apply exact retained-runtime security pins

After the bound runtime base is constructed, and before final apk-tools removal, apply exactly:

```text
libcrypto3 = 3.5.8-r0
libssl3    = 3.5.8-r0
libexpat   = 2.8.4-r0
```

using the same bound Alpine 3.24 repository configuration.

This authorization is target-version based: the starting libexpat version may differ between the official 2.37.9 image and the rebuilt Node 26.7.0 base, but the final accepted installed version must be exactly `2.8.4-r0` unless a later patch-forward case in Section 9 applies.

This is NOT authorization for:

```text
apk upgrade
floating package upgrades
another Alpine minor
another Node line not selected by upstream build mechanics
another Linux distribution
manual library copying
third-party package repositories
scanner suppression
SiteScore-authored VEX
```

If the exact target versions cannot be resolved from the bound repository set, STOP as a true design/security blocker.

Canonical image characterization after this remediation:

```text
N8N_APPLICATION_SOURCE: EXACT_OFFICIAL_STABLE_SOURCE
N8N_BUILD_MECHANICS: EXACT_UPSTREAM_BOUND
N8N_RUNTIME_BASE: UPSTREAM_DERIVED_SITE_SCORE_HARDENED
N8N_RUNTIME_SECURITY_DELTA: APK_SOLVER_CAPABILITY_REMOVAL_PLUS_EXACT_PINNED_RUNTIME_PATCHES
N8N_DEPENDENCY_SECURITY_DELTA: EXACT_UPSTREAM_ADOPTED_BACKPORTS
```

---

# 6. COMPLETE SECURITY GATE — NO PARTIAL PROMOTION

The rebuilt final candidate must be scanned from its final linux/amd64 bytes with the same pinned Syft/Grype + exact release OpenVEX + CISA KEV reconciliation method.

Mandatory result:

```text
CISA_KEV = 0
CRITICAL = 0
OS_HIGH = 0
brace-expansion vulnerable finding = 0
ip-address vulnerable finding = 0
fast-uri vulnerable findings = 0
no new HIGH introduced
```

No exact fixed/remediable HIGH may remain just because the build skipped an authorized fixed version.

The only possible residual HIGH remains exactly:

```text
package = nodemailer
installed = 8.0.10
advisory = GHSA-p6gq-j5cr-w38f
fixed = 9.0.1+
```

It may be accepted only if literally no other CRITICAL/HIGH remains and ALL previously-authorized containment conditions are proven, including:

```text
workflow hashes exact
frozen workflows contain no emailSend
NODES_EXCLUDE includes n8n-nodes-base.emailSend
runtime proves emailSend unavailable/non-executable
no SMTP host/user/pass/credential or user-management mail transport configured/injected
editor/admin/API non-public
no new Code/ExecuteCommand/ReadWriteFile path enabling alternate access
permanent risk record with exact advisory, controls, owner and expiry/re-review triggers
```

Any failure of those conditions means security gate FAIL and requires STOP.

---

# 7. N8N FUNCTIONAL COMPATIBILITY GATE

The successful security candidate must also prove:

```text
linux/amd64
non-root
n8n --version = selected stable version
startup/loadability
exact frozen workflow hashes
both frozen workflow imports
n8n static contracts
order-paid webhook/auth/payload compatibility smoke
recovery schedule/API compatibility smoke
no workflow migration
no node substitution
no credential semantic migration
no SiteScore business/orchestration semantic change
```

Frozen workflow hashes remain:

```text
order-paid = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery   = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

If satisfying the selected stable requires workflow JSON migration, node replacement, application-source patch, credential semantic change, or payload/API semantic change, STOP.

---

# 8. AFTER N8N PASS — COMPLETE ALL REMAINING 7.1 WORK CONTINUOUSLY

Do not return to Reviewer for ordinary mechanics. Once the n8n candidate passes, permanentize it and finish all original 7.1 gates on one exact final PR head.

Required permanent n8n outcome includes:

```text
deploy/containers/n8n-image.lock
reproducible hardened n8n build assets under deploy/containers/**
selected stable release/tag/source commit/tree
upstream builder/runtime/Dockerfile identities
exact upstream-adopted dependency delta manifest
exact OS security delta manifest
APK removal/solver evidence
final linux/amd64 digest
non-root/runtime identity
SPDX
raw Grype
CISA KEV + exact release OpenVEX reconciliation
nodemailer residual risk record if applicable
provenance/attestation evidence
```

Permanent publish target remains:

```text
ghcr.io/metadoks/sitescore-n8n
```

Pre-LOCK candidate build/load/scan/evidence is allowed. Production/locked baseline publish/deployment remains prohibited until Reviewer `READY_TO_LOCK` for the exact final SHA and user literal `LOCK` through the Implementer protocol.

Current live PR scope is back to the original 20 permanent files; no frozen source/workflow path is changed. Keep final scope within the original 7.1 authorization plus narrowly necessary `deploy/containers/**` n8n hardening assets explicitly enumerated in Implementer handoff.

Current exact-head CI already shows:

```text
source-boundary = PASS
static-contracts = PASS
```

Remaining mechanical gates must be fixed without weakening them:

```text
API = 114 PASS
report = 24 PASS
Commerce forward-applicable = 416 PASS + exact one phase-local deselect
FAZ6 frozen Commerce replay = 417 PASS
API/Commerce runtime/non-root/PDF-font smokes = PASS
API/Commerce/n8n SBOM + vulnerability policy = PASS
n8n permanent identity/runtime/security validation = PASS
full-40-char Action pins = PASS
faz7 / required-gate = PASS on exact final head
frozen application source diff = NONE
frozen n8n workflow diff = NONE
cloud/IaC mutation = NONE
committed production secret = NONE
```

---

# 9. PATCH-FORWARD CONTINUITY RULE — AVOID ANOTHER REVIEWER ROUND-TRIP FOR AN IDENTICAL CLOSURE

At every fresh candidate run, Implementer MUST re-enumerate the latest official non-draft/non-prerelease stable.

If a newer official stable appears before READY_FOR_REVIEW:

## 9.1 Official image passes

Use the newer official image if all original security/runtime/workflow gates pass. No custom hardened path is needed.

## 9.2 Official image fails but closure is materially identical/subset

Implementer MAY continue without another Reviewer decision only if ALL are true:

```text
- release is a patch-level stable within the same 2.x operational line;
- frozen workflows import unchanged and hashes remain exact;
- no workflow/API/credential semantic migration is required;
- upstream build mechanics remain Alpine 3.24 and an already-authorized Node/build lineage;
- every CRITICAL/HIGH belongs only to package/advisory families already covered by this decision;
- every npm remediation is exactly one of the upstream-adopted fixed versions already authorized here, or a newer exact upstream-master-adopted security fix for the same package family;
- every OS remediation is the same capability removal or an exact fixed version for the same retained package family from the same bound Alpine repository set;
- no new CISA KEV appears;
- no new package family, new vulnerability class requiring different reachability reasoning, new base distribution, or new architecture decision appears.
```

For a newer exact fixed version in the same already-authorized OS package family, retain upstream repository/package-policy evidence and prove it is a non-downgrade security fix. Do not float.

## 9.3 Mandatory STOP for materially new closure

Return to Reviewer if any newer stable introduces:

```text
new CRITICAL/HIGH package family
new KEV
new dependency fix not adopted upstream
new Node/Alpine/base-distribution design
workflow/node/credential migration
new public exposure assumption
new security exception requirement
```

This rule does not authorize arbitrary tracking of upstream master application code; exact official stable source remains mandatory.

---

# 10. GOVERNANCE REMAINS MANDATORY

Current live repository governance remains noncompliant:

```text
main protected = FALSE
required checks = NONE
merge commits = enabled
squash = enabled
rebase = enabled
auto-merge = disabled
```

Final required state remains:

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

Complete all technical/evidence CI work first. If connected tooling still cannot mutate these settings, return one consolidated owner-action blocker only at the end. If the GitHub plan itself makes the frozen governance requirement impossible, report `OPS71-GOV-001: PLAN_CAPABILITY_BLOCKED` with evidence and STOP.

---

# 11. REQUIRED NEXT IMPLEMENTER HANDOFF

The next useful handoff must be terminal for this implementation cycle:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

with exact final head and complete evidence, or:

```text
IMPLEMENTER_STATE: BLOCKED_TRUE_DESIGN_SECURITY_OR_OWNER_GOVERNANCE_ACTION
```

with one consolidated true blocker.

Do not return merely for another YAML/shell/parser/history/test-environment/evidence-path defect covered by standing mechanical authority.

```text
READY_TO_LOCK: NO
MERGE: NO
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```
