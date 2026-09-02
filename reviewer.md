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
IMPLEMENTER_ACTION: RESUME_7_1_WITH_ACTIONABLE_N8N_VULNERABILITY_TRIAGE
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_HEAD_SHA: fe916813dbe7da3e413682275285b4fb7a4a5067
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
OPS71-N8N-VULN-001: SECURITY_REOPEN_CONTINUES_UNDER_ACTIONABLE_TRIAGE

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

---

# 1. AUTHORITY CONTINUITY

The complete original FAZ 7.1 contract remains authoritative except where later Reviewer addenda explicitly supersede it:

```text
original full 7.1 contract coordination commit:
  c61c772ccd8192cce0475b4fd30a0cb0a74b1b37
original full 7.1 reviewer.md blob:
  d9acb7edca3a8b125bb557dd230ee62611f98299

n8n security-reopen coordination commit:
  54ca116bc3bb8e8ddd90839630231e3b6ba5449b
n8n security-reopen reviewer.md blob:
  245878e51f0e6ea41bbce3318b5e4c16f6d44591

platform-remediation coordination commit:
  6a79d05f1c7c6279d356b4d2395ce53285eae06b
platform-remediation reviewer.md blob:
  7ea1bad7ec0fb847073f084e750150c2a96c1dc9
```

All unchanged requirements remain mandatory, especially exact-head evidence, frozen application/business semantics, workflow byte identity, non-root runtime, immutable digests, SBOM/provenance, permanent `faz7 / required-gate`, GitHub governance, no cloud deployment in 7.1, no secrets, and literal user LOCK before merge.

---

# 2. INDEPENDENT REVIEWER FINDINGS

Reviewer independently verified:

```text
PR #34 = OPEN / DRAFT / MERGEABLE / UNMERGED
base = main@fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
head = fe916813dbe7da3e413682275285b4fb7a4a5067
changed files = 20
main remains unprotected
merge commits enabled
squash + rebase still enabled
```

GitHub-hosted Actions execution is restored. Resume probe run `32567312841`, attempt 2, contains real runner steps and successful enumeration plus ten successful exact-image scan jobs.

Reviewer independently checked representative raw scan logs:

```text
2.34.6
  digest = sha256:dacee4491f8f6078a78cfa3803b2e728e6eec0878ce92df7f0d323def70bbecd
  CRITICAL = 13
  HIGH = 62
  result = REJECTED under prior raw-zero gate

2.36.9
  digest = sha256:af28db468b622a96fa8078ddad120e461adb1b2c2bc20802c9e6d5c915b3af89
  CRITICAL = 10
  HIGH = 36
  result = REJECTED under prior raw-zero gate
```

The scan matrix also included `2.35.3`, `2.35.4`, `2.35.5`, `2.35.6`, `2.35.7`, `2.36.6`, `2.36.7`, and `2.36.8`; none satisfied raw `CRITICAL=0/HIGH=0`.

Current upstream release state was independently rechecked on 2026-09-02. `n8n@2.36.9` is an official non-draft, non-prerelease release. `n8n@2.37.0` and `n8n@2.38.1` are currently marked prerelease and therefore remain ineligible under the stable-only rule.

Therefore the prior `raw CRITICAL=0 / raw HIGH=0` replacement rule is currently unsatisfiable by the official stable upstream line. Continuing to require raw-zero would permanently block the checkpoint without distinguishing remediable vulnerabilities from upstream-unfixed findings.

---

# 3. DESIGN DECISION — ACTIONABLE VULNERABILITY TRIAGE

The prior replacement acceptance criterion:

```text
raw CRITICAL = 0
raw HIGH = 0
```

is superseded for the n8n production-candidate image only by the following stricter evidence-based actionable gate.

This is NOT a blanket waiver and is NOT permission to ignore scanner findings.

```text
N8N_RAW_CRITICAL: MUST_BE_RECORDED
N8N_RAW_HIGH: MUST_BE_RECORDED
N8N_REMEDIABLE_CRITICAL: MUST_EQUAL_0
N8N_REMEDIABLE_HIGH: MUST_EQUAL_0
N8N_CISA_KEV_MATCHES: MUST_EQUAL_0
N8N_UNDISPOSITIONED_CRITICAL: MUST_EQUAL_0
N8N_UNDISPOSITIONED_HIGH: MUST_EQUAL_0
SCANNER_SUPPRESSION: NONE
BLANKET_IGNORE: NONE
CUSTOM_PATCHED_N8N_IMAGE: FORBIDDEN
```

Definitions:

```text
REMEDIABLE = scanner/advisory evidence reports a fixed version or otherwise confirms a fix is available for the affected package, while the candidate image still contains the vulnerable version.

UNDISPOSITIONED = a CRITICAL/HIGH finding that has not been individually tied to package, installed version, advisory identity, fix state, and explicit disposition evidence.
```

Any CRITICAL/HIGH finding with a fix available is a hard blocker. Do not accept an official image merely because upstream has not yet consumed its available fix.

Any CISA Known Exploited Vulnerability match is a hard blocker regardless of fix state.

Unknown fix state is NOT automatically equivalent to `not fixed`; it must remain undispositioned unless independent advisory evidence establishes the state.

Upstream OpenVEX may be used as corroborating evidence only where the statement matches the exact advisory/package/product context. It may not be used as a blanket release-level waiver.

---

# 4. CANDIDATE SELECTION RULE IS UPDATED

The previous `lowest stable release that reaches raw-zero` rule is superseded because no such release currently exists.

Use the **latest official stable upstream n8nio/n8n release available at the time of final candidate validation**, not beta/rc/nightly/prerelease.

At this decision point the current eligible candidate is:

```text
version = 2.36.9
digest already observed = sha256:af28db468b622a96fa8078ddad120e461adb1b2c2bc20802c9e6d5c915b3af89
release state = stable / prerelease=false
```

Before freezing the candidate, re-enumerate official releases. If a newer stable release exists, it becomes the candidate and must be scanned/triaged instead. Do not silently remain on an older stable release.

The selected candidate still must prove:

```text
official upstream n8nio/n8n only
exact linux/amd64 digest
non-root runtime
runtime load/start proof
SPDX JSON SBOM
full raw Grype JSON retained
per-finding actionable disposition retained
REMEDIABLE CRITICAL = 0
REMEDIABLE HIGH = 0
CISA KEV = 0
UNDISPOSITIONED CRITICAL/HIGH = 0
workflow bytes unchanged
static/runtime compatibility PASS
```

If any of these gates fail, STOP again with `DESIGN_DECISION_REVIEW_REQUIRED: 1`.

---

# 5. REQUIRED PER-FINDING EVIDENCE

For every raw CRITICAL or HIGH match in the selected image, retain machine-readable evidence with at least:

```text
advisory_id
severity
package_name
package_type/ecosystem
installed_version
scanner_namespace/source
fix_state
fixed_versions (if any)
CISA_KEV_match
upstream_VEX_statement_if_exactly_applicable
disposition
rationale/evidence_source
```

Allowed dispositions are limited to:

```text
BLOCKED_REMEDIABLE
BLOCKED_KEV
UPSTREAM_UNFIXED_NO_KEV
UPSTREAM_VEX_NOT_AFFECTED_EXACT_MATCH
```

Anything else is `UNDISPOSITIONED` and blocks acceptance.

`UPSTREAM_UNFIXED_NO_KEV` is a temporary production-candidate risk disposition, not a claim that the vulnerability is harmless. It must remain visible in the SBOM/security evidence and be carried into FAZ 7 operational monitoring.

---

# 6. CONTAINMENT REQUIREMENTS FOR ANY UNFIXED CRITICAL/HIGH

If the selected official stable image contains any accepted `UPSTREAM_UNFIXED_NO_KEV` findings, the existing FAZ 7 topology constraints become mandatory acceptance conditions and may not be weakened later:

```text
n8n admin/editor/rest surface = NON_PUBLIC
public n8n surface = exact required webhook only
runtime = non-root
community/custom node installation = not introduced by SiteScore
workflow JSON bytes = frozen exact hashes
n8n remains orchestration-only
n8n does not become business-state authority
production persistence = dedicated PostgreSQL
network exposure = least privilege in FAZ 7.2
```

These are containment controls, not substitutes for patching. A future fixed stable upstream release must replace the accepted unfixed baseline through normal release governance.

---

# 7. WORKFLOW SEMANTICS REMAIN FROZEN

Mandatory workflow identities remain:

```text
order workflow SHA256:
02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1

recovery workflow SHA256:
f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

Still forbidden:

```text
automation/n8n/workflows/** changes
workflow/node semantic substitutions
webhook path/payload/auth changes
Commerce automation API changes
payment/order/recovery behavior changes
business-state interpretation changes
custom patched/rebuilt n8n lineage
scanner severity remapping
scanner disablement
blanket CVE ignore lists
```

---

# 8. AUTHORIZED 7.1 RESUME WORK

Implementer may now resume on the same PR and exact base.

Existing authorized 7.1 paths remain in force. The following work is explicitly authorized without reopening frozen application source:

```text
1. selected n8n stable identity/digest lock
2. full Grype JSON + SPDX SBOM + actionable disposition evidence
3. CISA KEV matching evidence
4. exact applicable upstream OpenVEX ingestion/correlation if useful
5. permanent CI enforcement of the actionable n8n gate
6. source-boundary workflow correction for the diagnosed shallow-fetch/merge-base issue
7. FAZ6 Commerce replay environment correction so historical frozen tests execute in an equivalent environment
8. existing container/runtime/PDF/non-root validation completion
9. permanent exact-head `faz7 / required-gate`
10. final scope/no-secret/no-cloud proof
```

CI corrections are limited to workflow/test-environment mechanics. They may not modify frozen application/package behavior merely to make tests pass.

For the FAZ6 replay, installing required frozen repository packages and required test tooling such as `git` in the replay environment is permitted. Altering frozen test assertions or application code is not.

---

# 9. GITHUB GOVERNANCE REMAINS A HARD GATE

`OPS71-GOV-001` remains:

```text
MANUAL_OWNER_CONFIGURATION_AUTHORIZED_PENDING
```

Before `READY_FOR_REVIEW` / `READY_TO_LOCK`, live repository state must prove:

```text
main protected = TRUE
pull request required = TRUE
required status check = faz7 / required-gate
strict/up-to-date check = TRUE
force pushes blocked
branch deletion blocked
merge commits enabled
squash merge disabled
rebase merge disabled
auto-merge disabled
```

Do not weaken the governance requirement because the connector cannot mutate these settings.

---

# 10. REQUIRED N8N FINAL VALIDATION

The selected candidate must satisfy:

```text
N8N-SEC-001 official stable identity
N8N-SEC-002 exact linux/amd64 digest
N8N-SEC-003 non-root
N8N-SEC-004 raw CRITICAL count recorded
N8N-SEC-005 raw HIGH count recorded
N8N-SEC-006 REMEDIABLE CRITICAL = 0
N8N-SEC-007 REMEDIABLE HIGH = 0
N8N-SEC-008 CISA KEV = 0
N8N-SEC-009 UNDISPOSITIONED CRITICAL/HIGH = 0
N8N-SEC-010 SPDX JSON SBOM retained
N8N-SEC-011 full raw Grype JSON retained
N8N-SEC-012 order workflow hash unchanged
N8N-SEC-013 recovery workflow hash unchanged
N8N-SEC-014 n8n static/contract PASS
N8N-SEC-015 runtime load/start PASS
N8N-SEC-016 webhook/workflow compatibility smoke PASS
N8N-SEC-017 no workflow JSON diff
N8N-SEC-018 no scanner suppression/blanket ignore
N8N-SEC-019 historical 2.33.4 remains recorded as superseded-for-security
N8N-SEC-020 containment requirements documented and enforced by later topology contract
```

---

# 11. FULL 7.1 GATES STILL APPLY

Before `READY_FOR_REVIEW`, all original 7.1 gates remain required, including:

```text
API current suite = 114 PASS
report current suite = 24 PASS
Commerce forward-applicable = 416 PASS + exact one phase-local deselect
FAZ6 frozen Commerce replay = 417 PASS
dispatcher supervisor tests PASS
API image build/runtime/non-root/PDF/font PASS
Commerce image build/runtime/non-root PASS
API/Commerce/n8n SBOMs PASS
permanent Actions full-SHA pins PASS
required-gate green on exact final head
frozen application source diff = NONE
n8n workflow JSON diff = NONE
cloud/IaC mutation = NONE
production secret committed = NONE
main governance = PASS
```

No merge. No FAZ 7.2. No FAZ 8.

---

# 12. REQUIRED IMPLEMENTER HANDOFF

When implementation and all evidence are complete, update `implementer.md` and STOP with:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
USER_LOCK_AUTHORIZED: NO

BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
PR: #34
HEAD_SHA: <exact final sha>

OPS71-GHA-EXEC-001: RESOLVED
OPS71-GOV-001: RESOLVED
OPS71-N8N-VULN-001: RESOLVED_BY_ACTIONABLE_SECURITY_BASELINE
SELECTED_N8N_VERSION: <latest stable exact>
SELECTED_N8N_DIGEST: <exact linux/amd64 sha256>
N8N_RAW_CRITICAL: <count>
N8N_RAW_HIGH: <count>
N8N_REMEDIABLE_CRITICAL: 0
N8N_REMEDIABLE_HIGH: 0
N8N_CISA_KEV: 0
N8N_UNDISPOSITIONED_CRITICAL_HIGH: 0
N8N_SBOM: PASS
N8N_RAW_GRYPE_EVIDENCE: PASS
N8N_ACTIONABLE_DISPOSITION_EVIDENCE: PASS
N8N_ORDER_WORKFLOW_HASH: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
N8N_RECOVERY_WORKFLOW_HASH: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
N8N_STATIC: PASS
N8N_RUNTIME_COMPATIBILITY: PASS

API_IMAGE_BUILD: PASS
COMMERCE_IMAGE_BUILD: PASS
API_IMAGE_NONROOT: PASS
COMMERCE_IMAGE_NONROOT: PASS
API_PDF_RENDER_SMOKE: PASS
FAZ6_COMMERCE_REPLAY: 417 PASS
REQUIRED_GATE: PASS
MAIN_BRANCH_PROTECTED: TRUE
MERGE_GOVERNANCE: PASS
FROZEN_APPLICATION_SOURCE_DIFF: NONE
N8N_WORKFLOW_JSON_DIFF: NONE

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

Reviewer will then independently audit the exact final PR head. Do not merge before Reviewer `READY_TO_LOCK` and literal user `LOCK`.
