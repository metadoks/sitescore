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
IMPLEMENTER_ACTION: RESUME_7_1_WITH_UPSTREAM_FAITHFUL_HARDENED_N8N_REBUILD_PROBE
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: 9123fef933c2faf5ab5f9b644f3d92aa4e7601f7
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_UNDER_HARDENED_REBUILD_PROBE

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

The original FAZ 7.1 contract remains authoritative except where later Reviewer addenda explicitly supersede it.

```text
original full 7.1 contract coordination commit:
  c61c772ccd8192cce0475b4fd30a0cb0a74b1b37
original full 7.1 reviewer.md blob:
  d9acb7edca3a8b125bb557dd230ee62611f98299

initial n8n security reopen coordination commit:
  54ca116bc3bb8e8ddd90839630231e3b6ba5449b
initial n8n security reopen reviewer.md blob:
  245878e51f0e6ea41bbce3318b5e4c16f6d44591

actionable-triage decision coordination commit:
  bb2c72a75eba92f825e0be4d873f030f13e97c46

verified vendor OpenVEX reconciliation decision coordination commit:
  deb05237d075fac4f046264ada5933fb8a0de813
```

Nothing here weakens exact-head review/LOCK, frozen SiteScore application/business semantics, frozen n8n workflow bytes, GitHub governance, supply-chain evidence, or the prohibition on FAZ 7.2 / FAZ 8 start.

This addendum changes only the previously forbidden `custom n8n rebuild` disposition. A narrowly defined, upstream-faithful security rebuild **probe** is now authorized because the exact official stable image remains unable to satisfy the production security gate after raw scan, actionable triage, and cryptographically-bound vendor OpenVEX reconciliation.

---

# 2. INDEPENDENT REVIEWER FINDING

Implementer correctly executed the verified vendor OpenVEX reconciliation and stopped when the gate failed.

Exact evidence independently rechecked:

```text
selected official stable n8n = 2.37.7
release id = 381094367
published_at = 2026-09-02T08:41:33Z
linux/amd64 digest = sha256:869500232f49760d6a422d320d3ead3cb28ee93a00e6f67c89eb3d6b81acd6be
runtime user = node
runtime/loadability = PASS
order workflow hash = PASS / unchanged
recovery workflow hash = PASS / unchanged

OpenVEX asset id = 540887241
OpenVEX metadata digest = sha256:a2b6a9444b21027742cf4b120f3b6e22d745c9d3a025d766635b6e2304ed41d7
OpenVEX downloaded-byte digest = same / VERIFIED

reconciliation run = 33672995576
reconciliation job = 100390875934
source SHA = d008f7b9689a936afd09ac55397c82647477b644
artifact id = 9863430544
artifact digest = sha256:44392e3f74a9affac469441712dd4f30fa1ce47b64ed2e70a4d3e05a00da70ec
```

Verified reconciliation summary:

```text
N8N_RAW_CRITICAL = 12
N8N_RAW_HIGH = 36
N8N_CISA_KEV_MATCHES = 0
N8N_VENDOR_AFFECTED_CRITICAL = 0
N8N_VENDOR_AFFECTED_HIGH = 0
N8N_VENDOR_UNDER_INVESTIGATION_CRITICAL = 0
N8N_VENDOR_UNDER_INVESTIGATION_HIGH = 0
N8N_VEX_SCANNER_CONFLICT_CRITICAL = 0
N8N_VEX_SCANNER_CONFLICT_HIGH = 0
N8N_REMEDIABLE_UNDISPOSITIONED_CRITICAL = 11
N8N_REMEDIABLE_UNDISPOSITIONED_HIGH = 33
N8N_UNDISPOSITIONED_CRITICAL = 1
N8N_UNDISPOSITIONED_HIGH = 3
N8N_ACTIONABLE_GATE = FAIL
```

Reviewer additionally inspected the preserved per-finding evidence. The 48 raw HIGH/CRITICAL matches decompose as:

```text
APK / Alpine OS:
  CRITICAL = 12
  HIGH = 33
  total = 45

npm:
  CRITICAL = 0
  HIGH = 3
  total = 3
```

Of the OS findings, 41 are explicitly remediable by newer package versions and four remain scanner-unknown/no applicable VEX. Representative affected runtime families include:

```text
libssl3 / libcrypto3 3.5.7-r1 -> fixed 3.5.8-r0
openssh 10.3_p1-r0 -> fixed 10.3_p1-r1
libexpat 2.8.2-r0 -> fixed 2.8.4-r0
graphicsmagick 1.3.47-r0 -> unresolved scanner findings
tiff 4.7.1-r0 -> unresolved scanner findings
```

The three npm HIGH findings are:

```text
brace-expansion 5.0.8 -> fixed 5.0.9
ip-address 10.2.0 -> fixed 10.3.1
nodemailer 8.0.10 -> fixed 9.0.1
```

No CISA KEV match was found in the verified evidence.

---

# 3. UPSTREAM BUILD / SECURITY EVIDENCE

Reviewer independently inspected the exact upstream n8n 2.37.7 build files and current upstream master build files.

Exact 2.37.7 n8n Dockerfile pins:

```text
BUILDER_IMAGE = node:26.5.1-alpine3.24@sha256:233761595746769ebfdb6090f44fc7cdf818ae0ce62d2b37e0367723b9823e36
RUNTIME_IMAGE = n8nio/base:26.5.1@sha256:1b0bca5c94bbd04ad2120b9e9892a8bc717a1d88efa76fefe452c59bdc611d25
```

The exact upstream `n8n-base` Dockerfile states that patched bytes are expected to arrive by bumping the pinned upstream base digest rather than by an uncontrolled blanket `apk upgrade`.

Current upstream master has already advanced the official build chain to:

```text
BUILDER_IMAGE = node:26.7.0-alpine3.24@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019
RUNTIME_IMAGE = n8nio/base:26.7.0@sha256:33687300c4e94dc00f42ec79ae15082ae07330ecd82ae1167125905b65908ff8
```

Current upstream master also contains security overrides for:

```text
ip-address@10 = 10.3.1
brace-expansion@5 = 5.0.9
```

but still carries:

```text
nodemailer = 8.0.10
```

Therefore SiteScore may not invent an unreviewed nodemailer 9 migration as part of this checkpoint.

---

# 4. FROZEN SITESCORE N8N ATTACK SURFACE

Reviewer independently re-read both frozen SiteScore workflow JSON files.

The frozen workflows use only the following functional node classes:

```text
webhook
if
respondToWebhook
httpRequest
noOp
stopAndError
wait
scheduleTrigger
```

No frozen workflow contains:

```text
Send Email / n8n-nodes-base.emailSend
Code node
Execute Command
Read/Write File
SSH node
image-processing node
```

The workflow byte hashes remain authoritative and must not change:

```text
order-paid:
02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1

recovery:
f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

Because the frozen workflows use HTTP Request nodes, the `ip-address` SSRF-class advisory cannot be accepted as unreachable; it must be remediated in the hardened candidate.

Because the frozen workflows do not use Send Email and SiteScore does not assign email transport authority to n8n, the residual nodemailer advisory may be considered for one narrowly-scoped reachability-based risk disposition only under Section 8 below.

---

# 5. DESIGN DECISION — AUTHORIZE UPSTREAM-FAITHFUL HARDENED N8N REBUILD PROBE

```text
DECISION: AUTHORIZE_UPSTREAM_FAITHFUL_HARDENED_N8N_REBUILD_PROBE
PURPOSE: remove/remediate generic upstream-image vulnerabilities without changing frozen SiteScore orchestration semantics
STATUS: PROBE_ONLY_UNTIL_ALL_GATES_PASS
```

The Implementer must first re-enumerate the latest official stable non-draft/non-prerelease n8n release at execution time.

If a newer official stable release than 2.37.7 exists and its exact official image satisfies the verified security gate, the custom hardened path MUST be abandoned and that official image must be used instead.

Only if the latest official stable image still fails may the hardened rebuild probe proceed.

The hardened image may be built only from the exact selected official stable n8n source/tag. Application source files may not be edited.

Authorized permanent candidate image identity, if this path ultimately passes Reviewer audit:

```text
ghcr.io/metadoks/sitescore-n8n
```

No image may be published as a production/locked baseline before exact-head Reviewer `READY_TO_LOCK` plus literal user `LOCK`. Pre-LOCK CI may build/load/scan the image locally and may retain evidence artifacts.

---

# 6. AUTHORIZED HARDENING DELTAS

Only the following classes of n8n rebuild delta are authorized.

## 6.1 Runtime base / Node build-chain hardening

Preference order:

```text
A. exact selected stable source + a newer immutable official n8nio/base digest for the same Node line, if upstream currently publishes one and it materially reduces the blocking findings;

B. if A is unavailable or insufficient, exact selected stable source rebuilt using the exact current upstream n8n master builder/runtime pair and build mechanics, provided:
   - both builder and runtime refs come directly from current upstream n8n build files;
   - Alpine minor remains the upstream-selected line;
   - native modules are rebuilt, not copied across an unverified ABI boundary;
   - runtime n8n --version remains the selected stable version;
   - full startup/loadability and workflow compatibility gates pass.
```

Arbitrary Debian/Ubuntu/Alpine images, arbitrary Node images, local package mirrors, or unpublished custom bases are forbidden.

Blanket floating `apk upgrade` is forbidden.

## 6.2 SiteScore-specific removal of unused generic OS capabilities

The hardened runtime may omit generic packages that are not required by either frozen SiteScore workflow, but only with exact before/after package inventory and runtime proof.

Explicitly authorized for removal testing:

```text
openssh family

graphicsmagick and its image-only dependency chain, including tiff where removal follows dependency resolution
```

Removal is allowed only if:

```text
- n8n process starts normally;
- both frozen workflows load/import successfully;
- n8n static contract suite passes;
- order-paid webhook compatibility smoke passes;
- recovery workflow compatibility smoke passes;
- no required SiteScore runtime node becomes unavailable;
- workflow JSON remains byte-identical.
```

Do not remove `libssl3`, `libcrypto3`, `libexpat`, libc/runtime libraries, or any package required by Node/n8n. Required runtime libraries must be patched through the approved upstream base/build chain.

## 6.3 npm security backports

The hardened build may apply only dependency-version changes already adopted by current upstream n8n master, with exact upstream file/commit evidence retained.

Currently authorized:

```text
brace-expansion@5 -> 5.0.9
ip-address@10 -> 10.3.1
```

No arbitrary dependency upgrade is authorized.

`nodemailer 8.0.10 -> 9.x` is NOT currently authorized as a local dependency migration because current upstream master still carries 8.0.10.

If upstream master or a newer official stable release adopts a fixed nodemailer version before the final candidate is frozen, the Implementer must use the upstream-adopted fixed version/path and the Section 8 residual-risk allowance becomes unavailable.

---

# 7. HARDENED CANDIDATE SECURITY GATE

The hardened candidate must be scanned from its final Linux/AMD64 image bytes with the pinned Syft/Grype toolchain and the same verified CISA KEV / upstream VEX reconciliation process.

Mandatory baseline:

```text
CISA KEV matches = 0
CRITICAL findings = 0
```

All CRITICAL findings must be eliminated or covered by an exact applicable verified upstream `not_affected` VEX statement. No local SiteScore VEX may be authored for n8n.

For HIGH findings:

```text
- ip-address advisory must be eliminated;
- brace-expansion advisory must be eliminated;
- all OS HIGH findings must be eliminated or covered by exact applicable upstream vendor VEX;
- no HIGH finding with a fixed version may remain merely because the build chose not to update it;
- no new HIGH finding may be introduced by the hardened rebuild.
```

The only possible residual HIGH exception is the exact nodemailer advisory described in Section 8. Any other residual HIGH causes STOP.

The final evidence must retain both raw and reconciled counts. Scanner output must not be filtered, suppressed, severity-remapped, or rewritten.

---

# 8. SINGLE RESIDUAL NODEMAILER REACHABILITY EXCEPTION

This is not a general vulnerability waiver.

Only this exact residual may be considered:

```text
package = nodemailer
installed = 8.0.10
advisory = GHSA-p6gq-j5cr-w38f
severity = HIGH
fixed version = 9.0.1+
```

It may be accepted only if **all** of the following are proven on the final hardened candidate and production runtime contract:

```text
1. CISA KEV match = 0.
2. No other CRITICAL or HIGH finding remains.
3. Both frozen SiteScore workflow hashes remain exact.
4. Neither frozen workflow contains n8n-nodes-base.emailSend.
5. NODES_EXCLUDE explicitly includes n8n-nodes-base.emailSend.
6. Runtime proof demonstrates the excluded Send Email node cannot execute / is unrecognized or unavailable.
7. No SMTP credential, SMTP host/user/password, or n8n user-management mail transport is configured or injected for the SiteScore n8n runtime.
8. n8n editor/admin/API remains non-public per the frozen production runtime contract.
9. No Code / Execute Command / Read-Write File capability is newly enabled to synthesize an alternate nodemailer execution path.
10. A permanent documented risk record identifies the exact advisory, exploit preconditions, controls, review owner, and automatic expiry condition.
```

Automatic expiry / mandatory re-review occurs on the earliest of:

```text
- upstream stable n8n adopts fixed nodemailer;
- upstream master adopts a fixed nodemailer path suitable for safe backport;
- SiteScore introduces any email-capable n8n workflow/node;
- SiteScore configures SMTP for n8n;
- the advisory enters CISA KEV;
- public exposure model changes;
- FAZ 7 final production-readiness audit.
```

If any condition above cannot be proven, STOP with `DESIGN_DECISION_REVIEW_REQUIRED: 1`.

---

# 9. REPRODUCIBILITY / PROVENANCE REQUIREMENTS FOR THE HARDENED BUILD

The hardened build must be reproducible and auditable. Before it can become a FAZ 7 baseline, retain at least:

```text
selected upstream stable tag/version/release id
selected upstream source commit/tree
exact upstream Dockerfile/build-file identities used
exact builder/base image digests
exact SiteScore hardening patch/delta manifest
exact removed package inventory
exact npm override diff and upstream-master evidence for each override
Linux/AMD64 final image digest
non-root runtime user
n8n --version
SPDX JSON SBOM
raw Grype JSON
verified CISA KEV evidence
verified upstream OpenVEX evidence
per-finding reconciliation output
Cosign/SLSA-style provenance/attestation evidence as required by the original 7.1 contract
secret/history sanity evidence
```

No n8n application source file may differ from the selected official stable tag except dependency lock/workspace metadata explicitly authorized in Section 6.3 and build/container metadata explicitly authorized above.

No SiteScore application/package/business source may change.

---

# 10. REQUIRED N8N FUNCTIONAL COMPATIBILITY

Before the hardened candidate may be accepted:

```text
architecture = linux/amd64
runtime user = non-root
runtime startup/loadability = PASS
n8n --version = selected stable version
order workflow hash = exact unchanged
recovery workflow hash = exact unchanged
n8n static/contract suite = PASS
order-paid webhook/auth/payload compatibility smoke = PASS
recovery schedule/API compatibility smoke = PASS
no workflow migration = required
no credential semantic migration = required
no node substitution = required
no business/orchestration semantic change = required
```

If the newer upstream build chain or dependency backports require a workflow JSON migration, node replacement, application-source patch, credential semantic change, or payload/API change, STOP. Do not auto-migrate.

---

# 11. IF THE HARDENED N8N GATE PASSES

Only after the hardened candidate passes Sections 7–10 is the Implementer authorized to continue the remaining original 7.1 work:

```text
- create deploy/containers/n8n-image.lock with exact accepted hardened image/source/base/delta identities;
- add permanent reproducible hardened n8n build/verification assets under deploy/containers/** as needed;
- extend permanent 7.1 CI/publish workflows for ghcr.io/metadoks/sitescore-n8n;
- preserve FAZ6 historical n8n 2.33.4 identity as SUPERSEDED_FOR_SECURITY;
- correct source-boundary shallow-fetch/merge-base CI mechanics;
- restore exact FAZ6 Commerce 417 PASS replay environment;
- complete API 114 PASS;
- complete report 24 PASS;
- complete Commerce forward 416 PASS + exact one phase-local deselect;
- complete API/Commerce/n8n image, runtime, SBOM, vulnerability, provenance and required-gate evidence;
- produce exact-head `faz7 / required-gate` PASS.
```

If the hardened n8n gate fails, STOP before unrelated remaining work and report exact residual blockers.

---

# 12. GOVERNANCE REMAINS MANDATORY

No GitHub governance requirement is waived.

Before `READY_FOR_REVIEW`:

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

Manual owner configuration remains authorized because the connected GitHub toolset exposes no branch-protection / repository merge-setting mutation action.

Do not configure the required check as a substitute for making the check green; the permanent `faz7 / required-gate` must first pass on the exact final head.

---

# 13. REQUIRED IMPLEMENTER HANDOFF

If the hardened probe cannot satisfy the security/compatibility conditions, update `implementer.md` and STOP with exact evidence and:

```text
OPS71-N8N-VULN-001: HARDENED_REBUILD_GATE_FAILED
DESIGN_DECISION_REVIEW_REQUIRED: 1
READY_FOR_REVIEW: NO
READY_TO_LOCK: NO
```

If the hardened n8n candidate passes and all remaining 7.1 gates are completed, update `implementer.md` with:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
USER_LOCK_AUTHORIZED: NO

BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
PR: #34
HEAD_SHA: <exact final head>

OPS71-N8N-VULN-001: RESOLVED_BY_UPSTREAM_FAITHFUL_HARDENED_BASELINE
SELECTED_N8N_VERSION: <exact official stable semantic version>
UPSTREAM_N8N_SOURCE: <exact tag/commit>
HARDENED_N8N_IMAGE_DIGEST: <exact linux/amd64 sha256>
N8N_CRITICAL: 0
N8N_HIGH: 0 or exact single authorized nodemailer residual only
N8N_KEV: 0
N8N_WORKFLOW_HASHES: PASS
N8N_RUNTIME: PASS
N8N_STATIC: PASS
N8N_SBOM: PASS
N8N_PROVENANCE: PASS

API_TESTS: 114 PASS
REPORT_TESTS: 24 PASS
COMMERCE_FORWARD: 416 PASS + exact one phase-local deselect
FAZ6_COMMERCE_REPLAY: 417 PASS
API_IMAGE: PASS
COMMERCE_IMAGE: PASS
REQUIRED_GATE: PASS
MAIN_BRANCH_PROTECTED: TRUE
MERGE_SETTINGS: COMPLIANT

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

Do not merge. Do not start FAZ 7.2. Do not start FAZ 8.
