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
IMPLEMENTER_ACTION: RESUME_7_1_WITH_N8N_SECURITY_REOPEN
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
EXPECTED_BASE_TREE_SHA: 2eeeb2f89ab08f52ab1d77f4d373bb06ae93a77b
CODE_BRANCH: faz7/7-1-reproducible-containers-supply-chain-governance
PR: #34
OBSERVED_BLOCKED_HEAD_SHA: b2dc44a3c1a93c5918bd3185ccafbb0b4ce6cc4b
REVIEWED_HEAD_SHA: NONE

FAZ_7_0_STATUS: LOCKED_VERIFIED
FAZ_7_0_MERGE_COMMIT: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_AT_DECISION: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
LIVE_MAIN_UNCHANGED_FROM_7_1_BASE: YES

BLOCKER_ID: OPS71-N8N-VULN-001
BLOCKER_CLASS: FROZEN_N8N_SUPPLY_CHAIN_VULNERABILITY_POLICY
BLOCKER_DISPOSITION: NARROW_SECURITY_BASELINE_REOPEN_AUTHORIZED
DESIGN_DECISION: AUTHORIZE_N8N_SECURITY_BASELINE_REOPEN

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

---

# 1. CONTRACT CONTINUITY / INCORPORATION BY REFERENCE

The complete original FAZ 7.1 contract remains authoritative and is incorporated here by exact immutable reference except where this security addendum explicitly supersedes the n8n version/digest clauses:

```text
reviewer coordination commit:
  c61c772ccd8192cce0475b4fd30a0cb0a74b1b37

reviewer.md blob containing full FAZ 7.1 contract:
  d9acb7edca3a8b125bb557dd230ee62611f98299
```

All unchanged requirements from that contract remain mandatory, including:

```text
- exact base/main lineage
- no application/business semantic mutation
- reproducible linux/amd64 API + Commerce images
- non-root runtime
- hashed dependency locks
- PDF/runtime smoke
- dispatcher supervisor isolation
- permanent full-SHA-pinned GitHub Actions
- SBOM/vulnerability/provenance evidence
- GHCR digest authority
- main branch protection/governance
- no DigitalOcean/OpenTofu/cloud deployment in 7.1
- no production secrets
- no FAZ 7.2/FAZ 8 start
- literal user LOCK required before merge
```

This addendum does **not** authorize merge and does **not** make the current PR head review-ready.

---

# 2. INDEPENDENT REVIEWER FINDING

Implementer correctly stopped on the exact frozen FAZ 6 n8n image instead of weakening the security gate or silently upgrading it.

Frozen image that failed the 7.1 supply-chain gate:

```text
n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
version = 2.33.4
architecture = linux/amd64
runtime user = node / non-root probe PASS
```

Evidence identity reported at the blocked head:

```text
PR = #34
blocked evidence head = b2dc44a3c1a93c5918bd3185ccafbb0b4ce6cc4b
workflow run = 32560317363
n8n job = 97000785115
evidence artifact = faz7-7-1-bootstrap-evidence
artifact id = 9472649384
artifact digest = sha256:4e8b07fb00c00b7e1e25e7a8fcc4a20c6c1f9d20f9f16df83cd41b4013bd9d5e
```

Raw Grype findings:

```text
CRITICAL = 4
HIGH = 34
MEDIUM = 33
LOW = 4
```

Policy blockers generated from those findings:

```text
blocker_count = 30
CRITICAL blockers = 4
HIGH-with-fix blockers = 26
unique advisory IDs = 22
affected package families = 13
```

Representative critical findings include vulnerable `vm2` instances with a reported fixed version and `graphicsmagick` CVE-2025-32460. The evidence is therefore sufficient to reject the old digest as a FAZ 7 production-candidate supply-chain baseline.

Reviewer also independently rechecked live GitHub state at decision time:

```text
PR #34 = OPEN / DRAFT / MERGEABLE / UNMERGED
PR base = main@fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
PR head = b2dc44a3c1a93c5918bd3185ccafbb0b4ce6cc4b
live main = fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
```

No user LOCK exists for 7.1.

---

# 3. DESIGN DECISION — OPS71-N8N-VULN-001

```text
DECISION: AUTHORIZE_N8N_SECURITY_BASELINE_REOPEN
RATIONALE: frozen 2.33.4 exact digest fails mandatory production supply-chain vulnerability gate
SCOPE: n8n runtime image version + immutable digest identity only, plus exact repository references/tests/docs needed to keep that identity coherent
BUSINESS/WORKFLOW SEMANTICS: FROZEN
SCANNER POLICY: MUST NOT BE WEAKENED
```

The FAZ 6 n8n image identity is no longer acceptable as a FAZ 7 production-candidate runtime input.

Its historical record remains immutable and must be preserved as:

```text
FAZ6_HISTORICAL_N8N_VERSION = 2.33.4
FAZ6_HISTORICAL_N8N_DIGEST = n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
FAZ7_PRODUCTION_CANDIDATE_STATUS = SUPERSEDED_FOR_SECURITY
```

Do not rewrite FAZ 6 history to pretend another image was originally frozen.

A new FAZ 7 n8n security baseline becomes authoritative only after it satisfies this addendum, reaches Reviewer `READY_TO_LOCK`, and the exact PR head is user-LOCKed and merged.

Until then:

```text
NEW_N8N_BASELINE_STATUS = CANDIDATE_NOT_FROZEN
```

---

# 4. REPLACEMENT N8N SELECTION RULE

Implementer is authorized to evaluate official upstream `n8nio/n8n` stable releases beginning above the historical 2.33.4 baseline.

Select the **lowest stable supported release greater than or equal to the historical baseline that actually satisfies all acceptance gates below**. Do not choose a version merely because it is newest or because release notes claim security fixes.

For every candidate considered, resolve and record the exact Linux/AMD64 immutable digest before acceptance.

Required candidate properties:

```text
image source = official upstream n8nio/n8n only
release channel = stable; no beta/rc/nightly
platform = linux/amd64
identity = exact sha256 digest
runtime user = non-root
Grype CRITICAL raw count = 0
Grype HIGH raw count = 0
blanket ignore/waiver = NONE
scanner disablement = NONE
in-place package patching/rebuild of upstream n8n = FORBIDDEN
```

The replacement must pass the **same scanner/toolchain policy**, with the stronger replacement-baseline acceptance criterion of zero raw HIGH and zero raw CRITICAL findings.

Do not hide findings by:

```text
- changing scanner severity mapping
- excluding npm/OS packages
- filtering unfixed vulnerabilities
- blanket CVE ignores
- rebuilding n8n with locally patched packages
- replacing official image lineage with a custom SiteScore image
```

If no official stable candidate can satisfy `0 CRITICAL / 0 HIGH`, STOP again with:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
OPS71-N8N-VULN-001: OPEN
```

Do not weaken the gate autonomously.

---

# 5. WORKFLOW / ORCHESTRATION SEMANTICS REMAIN FROZEN

The security reopen is **not** authorization to alter n8n business/orchestration behavior.

These workflow byte identities remain mandatory:

```text
order workflow SHA256:
02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1

recovery workflow SHA256:
f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

Forbidden:

```text
workflow JSON changes
node substitutions that alter semantics
webhook path/payload/auth changes
Commerce automation API contract changes
order/payment/recovery behavior changes
business-state interpretation in n8n
new orchestration authority
new application routes
```

n8n remains:

```text
orchestration only
one initial replica
admin/editor/rest non-public
exact public order-paid webhook only
production persistence target = dedicated PostgreSQL in 7.2
```

---

# 6. NARROW REPOSITORY REOPEN AUTHORIZATION

The original 7.1 permanent scope remains in force. In addition, only the following n8n identity-coherence changes are authorized if actually required by the selected replacement baseline:

```text
automation/n8n/runtime/docker-compose.yml
  - version/tag/digest identity only
  - environment/security semantics may not be weakened

automation/n8n/tests/**
  - only expected runtime version/digest assertions or compatibility assertions necessary for the security baseline
  - deleting/weakening existing semantic checks is forbidden

docs/FAZ7_PRODUCTION_RUNTIME_CONTRACT.md
docs/PRODUCTION_OPERATIONS_HANDOFF.md
  - only n8n runtime identity/security-baseline references that would otherwise become factually stale

deploy/containers/**
  - n8n candidate/digest/SBOM/scan evidence and existing authorized 7.1 supply-chain assets
.github/workflows/**
  - authorized 7.1 CI/publish flows plus temporary candidate-probing workflow(s)
```

Still forbidden:

```text
automation/n8n/workflows/**
sitescore-core/**
sitescore-data/**
sitescore-providers/**
sitescore-spatial/**
sitescore-metrics/**
sitescore-benchmarks/**
sitescore-pipeline/**
sitescore-app/**
sitescore-report/**
sitescore-api/**
sitescore-commerce/**
Alembic migrations
business/payment/scoring/report semantics
OpenTofu/Terraform
DigitalOcean/Cloudflare/Better Stack resource mutation
production secrets
```

Any need outside this narrow list requires another explicit Reviewer decision.

---

# 7. REQUIRED N8N REVALIDATION

Before 7.1 may return to `READY_FOR_REVIEW`, the selected candidate must prove all of the following on the exact final PR head:

```text
N8N-SEC-001 official n8nio/n8n stable release identity recorded
N8N-SEC-002 exact linux/amd64 digest recorded and resolved reproducibly
N8N-SEC-003 runtime user non-root PASS
N8N-SEC-004 Grype raw CRITICAL = 0
N8N-SEC-005 Grype raw HIGH = 0
N8N-SEC-006 SPDX JSON SBOM generated and retained as reviewable evidence
N8N-SEC-007 order workflow SHA256 exact unchanged
N8N-SEC-008 recovery workflow SHA256 exact unchanged
N8N-SEC-009 n8n static/contract suite = expected 12 PASS, or exact successor count explained without weakening
N8N-SEC-010 runtime starts far enough to prove selected version/digest is operationally loadable
N8N-SEC-011 existing webhook/workflow contract compatibility smoke PASS
N8N-SEC-012 no workflow JSON diff
N8N-SEC-013 no scanner exception/suppression
N8N-SEC-014 historical 2.33.4 identity remains documented as superseded-for-security, not erased
```

If upstream version movement causes workflow format migration, node replacement, payload change, credential semantic change, or any other business/orchestration mutation, STOP with a new design-decision blocker. Do not auto-migrate workflow bytes.

---

# 8. FULL 7.1 REVALIDATION STILL REQUIRED

Resolving n8n does not waive any other 7.1 gate. Implementer must resume the complete original checkpoint and provide final-head evidence including at least:

```text
- base-to-head scope/diff proof
- frozen SiteScore source/package bytes unchanged
- deterministic/hashed lock validation
- linux/amd64 API image build PASS
- linux/amd64 Commerce image build PASS
- both SiteScore images non-root PASS
- API PDF/font/runtime smoke PASS
- API current suite = 114 PASS
- report current suite = 24 PASS
- Commerce forward-applicable = 416 PASS / exact one phase-local deselect
- FAZ6 frozen Commerce base replay = 417 PASS
- n8n replacement security/compatibility gates PASS
- API/Commerce/n8n SPDX SBOMs
- mandatory vulnerability gates PASS
- image secret/history sanity PASS
- permanent GitHub Actions `uses:` full-SHA pinned
- permanent `faz7 / required-gate` green on exact final head
- main branch protection enabled
- required status check configured
- force-push/deletion blocked
- merge-commit only; squash/rebase disabled; auto-merge disabled
- no cloud resource mutation
- no DigitalOcean deployment
- no production secret committed/injected
```

Temporary candidate-discovery/bootstrap workflows and evidence-only helpers that are not part of the final authorized design must be removed before `READY_FOR_REVIEW` unless specifically justified as permanent reproducibility machinery.

The final PR must remain DRAFT until the permanent final CI/gates are complete and green; then it may be made non-draft for Reviewer audit.

---

# 9. REQUIRED IMPLEMENTER HANDOFF AFTER RESUME

When all requirements pass, Implementer must update `implementer.md` and STOP with:

```text
CURRENT_PHASE: FAZ 7
CURRENT_CHECKPOINT: 7.1
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
USER_LOCK_AUTHORIZED: NO

BASE_SHA: fff9cb2b2f7fd142f1bdba436acf66f2948bc9b7
PR: #34
HEAD_SHA: <exact final SHA>

OPS71-N8N-VULN-001: RESOLVED_BY_SECURITY_BASELINE_REPLACEMENT
HISTORICAL_N8N: 2.33.4@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
SELECTED_N8N_VERSION: <exact stable version>
SELECTED_N8N_DIGEST: <exact sha256>
N8N_CRITICAL: 0
N8N_HIGH: 0
N8N_ORDER_WORKFLOW_HASH: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
N8N_RECOVERY_WORKFLOW_HASH: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
N8N_STATIC: PASS
N8N_RUNTIME_COMPATIBILITY: PASS
N8N_SBOM: PASS

API_IMAGE_BUILD: PASS
COMMERCE_IMAGE_BUILD: PASS
API_IMAGE_NONROOT: PASS
COMMERCE_IMAGE_NONROOT: PASS
API_PDF_RENDER_SMOKE: PASS
VULNERABILITY_GATE: PASS
FROZEN_APPLICATION_SOURCE_DIFF: NONE
REQUIRED_GATE: PASS
MAIN_BRANCH_PROTECTED: TRUE

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
NEXT_CHECKPOINT_AUTHORIZED: NO
START_FAZ8: NO
PUBLIC_LAUNCH_AUTHORIZED: NO
```

Do not merge. Do not start FAZ 7.2.

Reviewer will independently audit the exact final head and issue only:

```text
HARDENING_REQUIRED
```

or

```text
READY_TO_LOCK
```

Literal user `LOCK` remains mandatory for merge.
