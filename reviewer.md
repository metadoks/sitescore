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
IMPLEMENTER_ACTION: RESUME_7_1_WITH_VENDOR_OPENVEX_RECONCILIATION
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: fc144059406b31d2f8b6a1d71df7a4d552e8faba
REVIEWED_HEAD_SHA: NONE

LIVE_MAIN_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_PROTECTED: FALSE
LIVE_REQUIRED_CHECKS: NONE
LIVE_ALLOW_MERGE_COMMIT: TRUE
LIVE_ALLOW_SQUASH_MERGE: TRUE
LIVE_ALLOW_REBASE_MERGE: TRUE
LIVE_ALLOW_AUTO_MERGE: FALSE

OPS71-GHA-EXEC-001: RESOLVED_CONFIRMED
OPS71-GOV-001: MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_UNDER_VERIFIED_VENDOR_OPENVEX_RECONCILIATION

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

---

# 1. AUTHORITY CONTINUITY

The original full FAZ 7.1 contract remains authoritative except where later Reviewer addenda explicitly supersede it.

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
```

Nothing here weakens exact-head review/LOCK, workflow-byte immutability, frozen application/business semantics, supply-chain evidence, GitHub governance, or the prohibition on FAZ 7.2/FAZ 8 start.

---

# 2. INDEPENDENT REVIEWER FINDING

Implementer correctly stopped after the first actionable-triage gate failed on official stable n8n 2.37.7.

Exact evidence independently rechecked:

```text
triage run = 33666579707
triage job = 100369715633
source SHA = 7f9d274ac078a078faa756604b359e800cc8282e
selected version = 2.37.7
selected linux/amd64 digest = sha256:869500232f49760d6a422d320d3ead3cb28ee93a00e6f67c89eb3d6b81acd6be
runtime user = node
runtime version = 2.37.7
runtime/loadability = PASS
workflow hashes = unchanged / PASS
SPDX generation = PASS
raw Grype generation = PASS
CISA KEV acquisition = PASS
upstream release OpenVEX acquisition = PASS
```

Observed first-pass summary:

```text
N8N_RAW_CRITICAL = 12
N8N_RAW_HIGH = 36
N8N_REMEDIABLE_CRITICAL = 11
N8N_REMEDIABLE_HIGH = 33
N8N_CISA_KEV_MATCHES = 0
N8N_UNDISPOSITIONED_CRITICAL = 1
N8N_UNDISPOSITIONED_HIGH = 3
N8N_ACTIONABLE_GATE = FAIL
```

The failure itself is valid under the previous contract. However, Reviewer found that the first-pass disposition algorithm evaluated `fixed_versions/fix_state` before applying verified upstream OpenVEX status. Therefore an official vendor `not_affected` statement could not neutralize a scanner package-level false positive even when upstream explicitly attested that the vulnerable code is not in the n8n execution path.

This is a triage-policy ordering gap, not authorization to ignore vulnerabilities.

Upstream n8n explicitly publishes `vex.openvex.json` with releases and documents OpenVEX as its mechanism to distinguish vulnerabilities that actually affect n8n from scanner false positives. The exact 2.37.7 release contains a `vex.openvex.json` asset.

---

# 3. DESIGN DECISION — VERIFIED VENDOR OPENVEX RECONCILIATION

```text
DECISION: AUTHORIZE_VERIFIED_VENDOR_OPENVEX_RECONCILIATION
CUSTOM_N8N_REBUILD: FORBIDDEN
SCANNER_SUPPRESSION: FORBIDDEN
BLANKET_CVE_IGNORE: FORBIDDEN
WORKFLOW_SEMANTIC_CHANGE: FORBIDDEN
BUSINESS_SEMANTIC_CHANGE: FORBIDDEN
```

Implementer must re-enumerate the latest official stable upstream `n8nio/n8n` release at execution time. Draft/prerelease/nightly releases remain forbidden.

For the selected stable release, resolve the exact Linux/AMD64 digest and retain:

```text
- upstream release/tag/id/published_at
- exact linux/amd64 digest
- runtime architecture/user/version proof
- runtime/loadability proof
- raw Grype JSON
- SPDX JSON SBOM
- exact upstream release OpenVEX asset metadata + bytes
- CISA KEV feed used for the decision
- per-finding reconciliation output
```

The official upstream OpenVEX evidence must be cryptographically/source-bound as far as the available upstream release evidence supports. At minimum, the downloaded VEX bytes must hash to the GitHub release asset digest recorded by the exact selected release metadata. If the existing pinned toolchain can verify the upstream OpenVEX image attestation/provenance without introducing an unrelated toolchain change, that verification must also be retained.

---

# 4. REQUIRED ADVISORY/ALIAS RECONCILIATION

The previous exact-string advisory lookup is insufficient by itself. Implementer must normalize vulnerability identity across scanner aliases before applying VEX.

For every raw CRITICAL/HIGH Grype match, retain at least:

```text
scanner advisory id
all scanner-provided related/alias IDs available in evidence
package name/type/version
fix state
fixed versions
CISA KEV correlation using CVE identity/aliases
all applicable upstream VEX statements after alias reconciliation
VEX product applicability evidence
final disposition
rationale
```

Only an upstream VEX statement that is applicable to the selected n8n product/release/image context may affect disposition. A same-CVE statement for an unrelated product identifier is not sufficient.

Mandatory disposition precedence:

```text
1. CISA KEV exact/alias match
   => BLOCKED_KEV

2. applicable upstream VEX status = affected
   => BLOCKED_VENDOR_AFFECTED

3. applicable upstream VEX status = under_investigation
   => BLOCKED_VENDOR_UNDER_INVESTIGATION

4. applicable upstream VEX status = fixed, but Grype still reports selected image/package vulnerable
   => BLOCKED_VEX_SCANNER_CONFLICT

5. applicable upstream VEX status = not_affected
   => VEX_NOT_AFFECTED_ALLOWED
      only when applicability + justification/statement are retained
      scanner fix availability alone MUST NOT override a verified vendor not_affected statement

6. no applicable vendor VEX statement AND scanner reports a fixed version/fixed state
   => BLOCKED_REMEDIABLE_UNDISPOSITIONED

7. no applicable vendor VEX statement AND scanner reports not-fixed/wont-fix AND no KEV
   => UPSTREAM_UNFIXED_NO_KEV_RISK_RECORDED
      allowed only with explicit advisory/package evidence retained

8. ambiguous alias mapping, conflicting VEX statements, unknown fix state, or insufficient product applicability
   => BLOCKED_UNDISPOSITIONED
```

A VEX `not_affected` allowance is evidence-based vendor disposition, not a local SiteScore waiver. SiteScore must not author its own VEX statement for n8n in FAZ 7.1.

---

# 5. ACCEPTANCE GATE AFTER RECONCILIATION

Raw counts remain visible and are never rewritten to zero.

The selected official stable image may pass the n8n security gate only if:

```text
N8N_CISA_KEV_MATCHES = 0
N8N_VENDOR_AFFECTED_CRITICAL = 0
N8N_VENDOR_AFFECTED_HIGH = 0
N8N_VENDOR_UNDER_INVESTIGATION_CRITICAL = 0
N8N_VENDOR_UNDER_INVESTIGATION_HIGH = 0
N8N_VEX_SCANNER_CONFLICT_CRITICAL = 0
N8N_VEX_SCANNER_CONFLICT_HIGH = 0
N8N_REMEDIABLE_UNDISPOSITIONED_CRITICAL = 0
N8N_REMEDIABLE_UNDISPOSITIONED_HIGH = 0
N8N_UNDISPOSITIONED_CRITICAL = 0
N8N_UNDISPOSITIONED_HIGH = 0
```

`VEX_NOT_AFFECTED_ALLOWED` and `UPSTREAM_UNFIXED_NO_KEV_RISK_RECORDED` findings must remain explicitly counted and reviewable; they may not disappear from evidence.

If any blocking counter is nonzero, STOP again with:

```text
OPS71-N8N-VULN-001: VERIFIED_VENDOR_OPENVEX_GATE_FAILED
DESIGN_DECISION_REVIEW_REQUIRED: 1
READY_FOR_REVIEW: NO
```

Do not proceed to a custom rebuild, package overlay, custom patched n8n image, scanner ignore, or vulnerability waiver.

---

# 6. IF THE VERIFIED VEX GATE PASSES

Only if the gate above passes, Implementer is authorized to continue the existing 7.1 implementation on PR #34:

```text
- create/update deploy/containers/n8n-image.lock with exact accepted stable version/digest/evidence identity
- update only already-authorized stale n8n runtime identity references/tests/docs
- preserve historical FAZ6 n8n 2.33.4 identity as SUPERSEDED_FOR_SECURITY
- prove order workflow SHA256 remains 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
- prove recovery workflow SHA256 remains f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
- complete n8n static/runtime/compatibility/SBOM/security validation
- correct source-boundary CI shallow-fetch/merge-base mechanics without changing frozen-source policy
- correct FAZ6 Commerce replay environment mechanically until the exact frozen 417 PASS baseline is reproduced
- complete API/Commerce image, non-root, PDF/font/runtime, SBOM/vulnerability and required-gate evidence
```

No frozen application code, package metadata, migrations, business/payment/scoring/report semantics, or n8n workflow JSON may change.

---

# 7. GOVERNANCE REMAINS MANDATORY

Current live governance remains noncompliant:

```text
main protected = FALSE
required checks = NONE
merge commits = enabled
squash = enabled
rebase = enabled
auto-merge = disabled
```

Before `READY_FOR_REVIEW`, the original 7.1 governance contract still requires:

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

Manual owner configuration remains explicitly authorized because the connected GitHub toolset exposes no branch-protection/repository-merge-setting mutation action.

---

# 8. REQUIRED IMPLEMENTER HANDOFF

If the verified vendor OpenVEX gate fails, report exact blocker counters and STOP.

If it passes and all remaining 7.1 gates are completed, update `implementer.md` with `IMPLEMENTER_STATE: READY_FOR_REVIEW` and include exact final PR head, selected n8n version/digest, raw counts, every blocking counter at zero, allowed VEX/unfixed-risk counts, workflow hashes, API 114 PASS, report 24 PASS, Commerce forward 416 PASS + exact one phase-local deselect, FAZ6 frozen replay 417 PASS, image/runtime/SBOM/security results, `faz7 / required-gate` PASS, and live governance state.

Do not merge. Do not start FAZ 7.2. Do not start FAZ 8.
