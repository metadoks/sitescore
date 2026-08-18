# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.4
CHECKPOINT_TITLE: Visual Report + PDF Rendering

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 30a12424cebfb6bcd53ad6fcd5d5db1b2315d9ae
CODE_BRANCH: faz5/5-4-visual-report-pdf-rendering
REVIEWED_HEAD_SHA: NONE
PR: NONE

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED
FAZ_5_1_STATUS: LOCKED
FAZ_5_2_STATUS: LOCKED
FAZ_5_3_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
BLOCKERS: NONE
```

---

# 1. POST-LOCK VERIFICATION — FAZ 5.3

Reviewer independently verified live GitHub state after user-authorized LOCK.

```text
PR: #19
state: CLOSED
merged: TRUE
base SHA: 8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
reviewed/merged head: fe937664a781a04e29a09e574bba46e371e26b90
merge commit: 30a12424cebfb6bcd53ad6fcd5d5db1b2315d9ae
post-lock main: 30a12424cebfb6bcd53ad6fcd5d5db1b2315d9ae
```

Implementer coordination record also states USER_LOCK_AUTHORIZED=YES and records exact merge parents as pre-lock main + reviewed head. No evidence of 5.4 work existed before this Reviewer transition.

Therefore:

```text
FAZ_5_3_STATUS: LOCKED
```

Locked 5.3 authority is now upstream truth for 5.4:

```text
factory-owned ReportDomainModel
-> factory-owned ApprovedNarrativeContext
-> closed canonical-state NarrativeClaimId selection
-> exact claim/section/evidence validation
-> code-owned deterministic narrative templates
-> factory-owned ValidatedReportNarrative
```

The LLM remains non-authoritative. No 5.4 implementation may weaken or bypass that boundary.

---

# 2. FAZ 5.4 PURPOSE

Convert exact locked report facts + exact validated narrative into a customer-ready visual report and PDF without creating new analytical truth.

Canonical target:

```text
canonical ReportDomainModel
+ exact canonical ValidatedReportNarrative bound to that model
-> deterministic presentation projection
-> tables
-> charts
-> controlled HTML/CSS layout
-> PDF bytes
```

Selected stack for this checkpoint:

```text
Jinja2
controlled application-owned HTML/CSS templates
Matplotlib deterministic chart assets
WeasyPrint PDF rendering
```

Renderer/presentation code is a view layer only.

---

# 3. PACKAGE / SCOPE CONTRACT

Primary product scope:

```text
sitescore-report/**
```

Advance package version appropriately from locked `sitescore-report==0.2.0` for this checkpoint.

Direct dependencies added for 5.4 must be exact-pinned and limited to the selected rendering stack and truly required helpers. Do not upgrade unrelated frozen/locked dependencies merely for convenience.

No change to frozen FAZ 3/4 packages.
No semantic change to locked sitescore-api 5.1 lifecycle.
No reopening of 5.2/5.3 authority unless Reviewer explicitly escalates.

5.4 must NOT introduce 5.5 durable report resources/storage semantics or FAZ 6 behavior.

---

# 4. AUTHORITY / LINEAGE REQUIREMENTS

The renderer must require exact factory-owned upstream authority.

Required source relationship:

```text
ReportDomainModel A
ValidatedReportNarrative N
N.approved_context.report_domain_model is A
```

A renderer call with:

```text
ReportDomainModel A + narrative from ReportDomainModel B
```

must fail closed.

Do not accept as rendering authority:

```text
plain dict / JSON projection
analysis_fingerprint alone
caller scores
caller financials
caller decision/confidence
caller-authored chart values
caller HTML/CSS
caller narrative text
forged/copy report domain
forged/copy validated narrative
```

If 5.4 introduces a factory-owned presentation/render model, it must preserve exact source identity/semantic binding and fail closed on copy/substitution/mutation in the same spirit as locked report/narrative authority.

---

# 5. NO ANALYTICAL RECOMPUTATION

Presentation code MUST NOT calculate or reinterpret:

```text
Location Score
category scores
financial feasibility
break-even
BEC
operating margin
rent burden
structural band
financial band
decision
confidence
normalization
benchmark percentile
readiness
analysis fingerprint
```

Charts and tables consume canonical values; they do not own formulas.

A display transform such as formatting/rounding is permitted only as presentation policy and must never feed back into authority or change semantic classification.

---

# 6. PRESENTATION / ROUNDING POLICY

Implement a code-owned, versioned presentation policy.

It must define, at minimum, consistent handling for:

```text
score decimals
money/currency formatting
percent display
ratio/BEC display
confidence labels
boolean/status labels
missing/None values
risk flags
```

Requirements:

```text
same canonical value -> same displayed value wherever repeated
chart label/table cell must not disagree because of independent rounding
0..1 canonical rates must not accidentally be shown as raw fraction when a percentage label is claimed
already-percentage canonical fields must not be multiplied again
None/missing must never become zero, neutral, good, or fabricated value
```

The presentation policy is not analytical authority.

---

# 7. TABLE REQUIREMENTS

Customer-facing report should truthfully render applicable canonical sections, including at least the material classes available in the locked domain:

```text
analysis/sector
category scores
location result
financial result / economics
canonical decision/headline/risk flags
confidence
data-quality / missingness context
validated narrative sections
model/report provenance where appropriate
```

Exact page design is implementation-owned within this contract.

Financial tables must be sourced from exact `ReportDomainModel.financial` facts. Do not recompute subtotal/derived economics merely to populate a table.

---

# 8. CHART REQUIREMENTS

Matplotlib charts are deterministic report assets generated only from canonical report facts.

At minimum provide useful visual representation of core report values where applicable, but do not invent a chart solely to satisfy count.

Rules:

```text
chart data source = canonical report values
chart labels = presentation policy
chart/table repeated values agree
no hidden normalization that changes meaning
no missing-value substitution
no stochastic layout/data generation
no external network assets
```

Prefer in-memory deterministic SVG/PNG assets suitable for controlled embedding.

Charts must not become a new authority surface.

---

# 9. TEMPLATE / HTML / CSS SECURITY

Jinja2 templates and CSS are controlled, application-owned versioned assets.

Never allow:

```text
LLM-generated arbitrary HTML as trusted template
LLM-generated CSS as trusted stylesheet
caller-provided template source
caller-provided CSS
untrusted file:// or remote URL asset loading
arbitrary local filesystem reads through template/asset paths
```

Narrative content enters templates only as data/text already present in exact `ValidatedReportNarrative`.

Escaping/safe rendering must ensure narrative strings or canonical labels cannot inject template/HTML authority.

Do not mark untrusted text as safe HTML merely for formatting convenience.

---

# 10. PDF RENDERING CONTRACT

WeasyPrint is the selected PDF renderer.

Implement a narrow rendering boundary that returns deterministic-in-content PDF bytes for exact canonical presentation inputs, subject to normal PDF metadata/library constraints.

Required failure behavior:

```text
invalid/noncanonical source -> hard fail before rendering
source/narrative mismatch -> hard fail
chart generation failure -> explicit render failure
missing required template/stylesheet -> explicit render failure
WeasyPrint exception -> explicit render failure
broken required asset -> explicit render failure
```

Do not convert a failed render into an empty or fake-valid PDF.

5.4 may produce PDF bytes in memory or a narrowly scoped ephemeral/test artifact. Durable report IDs, storage keys, object storage and report lifecycle belong to 5.5.

---

# 11. MISSINGNESS / OPTIONAL CONTENT

Canonical missingness must remain truthful visually.

Examples:

```text
None -> explicit unavailable/not available presentation token
missing mapping key -> remains absent/unavailable
low confidence -> visibly low, never neutralized
stress failure -> visibly preserved
weak/non-viable decision state -> visibly preserved
```

Do not hide an unfavorable/missing canonical fact merely because it creates layout inconvenience.

Optional sections may be omitted only when omission itself does not imply a false positive/complete state; where omission would mislead, render an explicit unavailable indicator.

---

# 12. PAGINATION / LAYOUT ROBUSTNESS

The template must withstand realistic report content without corrupting meaning.

Test at minimum:

```text
multi-page output
long narrative text / long risk lists where canonical test fixture allows
long labels
unicode text
page breaks
header/footer behavior if used
tables crossing pages
chart placement
no clipped critical values
no overlapping critical content
```

A visually attractive PDF with clipped/wrong material facts is a blocker.

---

# 13. FONT / ASSET POLICY

Use deterministic, package-controlled or environment-stable fonts/assets compatible with validated deployment/runtime.

Do not depend on network font downloads.

If custom packaged assets are added, include only redistributable project assets and bind access to package-controlled paths.

Renderer must not expose arbitrary asset path traversal.

---

# 14. VERSION / PROVENANCE

5.4 should define code-owned presentation/render identities such as, as applicable:

```text
presentation schema/version
template version
stylesheet version
chart version
renderer version identity
```

These are provenance/presentation metadata only, not scoring/report authority tokens.

No durable `report_id` is introduced in 5.4.

---

# 15. CURRENT PRODUCTION LIMITATION

Locked real production truth remains unchanged:

```text
COMB-005 = NOT_APPROVED
real production lifecycle -> not_score_ready
```

5.4 must not fabricate a scored production report or PDF from current real NOT_SCORE_READY execution.

Positive rendering tests may use the same established test-only upstream SCORE_READY substitution to create genuine factory-owned ApplicationAnalysisResult -> ReportDomainModel -> ValidatedReportNarrative authority.

Do not forge top-level report/narrative authority directly.

---

# 16. REQUIRED TESTS

Add broad deterministic/adversarial coverage.

## Authority / binding

```text
noncanonical ReportDomainModel rejected
noncanonical ValidatedReportNarrative rejected
narrative/report cross-source substitution rejected
plain dict/JSON rejected as authority
copy/manual-shell/substitution rejected where presentation authority object exists
```

## Fidelity

```text
category score displayed from exact canonical source
location score/structural band fidelity
financial table canonical-value fidelity
decision/headline/risk fidelity
confidence score/label fidelity
stress-test state fidelity
missing/None fidelity
chart/table repeated-value agreement
presentation rounding policy consistency
percentage/fraction scale correctness
```

## Security

```text
narrative special characters escaped as data
no arbitrary HTML/CSS injection
no external network asset dependency
asset/path traversal fail closed
```

## Rendering robustness

```text
PDF begins with valid PDF signature / parser-readable PDF
non-empty pages generated
multi-page realistic report
unicode
long content/page overflow case
missing optional sections
broken chart asset/render failure
renderer exception propagation/wrapping
```

## Regression

```text
all locked 5.2/5.3 report tests green
locked API 88 green
frozen baseline 1375 green
```

If report suite total after 5.4 is R, combined expected count remains:

```text
1463 + R
```

unless a Reviewer-authorized test baseline change is explicitly documented.

---

# 17. VISUAL REVIEW EVIDENCE

Because PDF layout correctness cannot be established only through object-level tests, validation evidence must include deterministic generated test PDF artifact(s) from representative fixtures.

Implementer should provide enough evidence for Reviewer to inspect rendered pages/artifacts during review, while keeping temporary validation artifacts/workflows out of the final product diff unless they are intentional project test fixtures.

Representative visual fixtures should include at least:

```text
normal/strong case
weak or financially stressed case
low-confidence / incomplete-evidence case
```

Use genuine factory-owned test authority chain.

---

# 18. VALIDATION REQUIREMENTS

Before final handoff:

```text
Python 3.11
exact direct dependency versions printed
sitescore-report full suite
locked API 88
frozen baseline 1375
real PostgreSQL migration regression where established workflow uses it
real Celery + Redis locked regression where established workflow uses it
PDF structural validity tests
representative generated PDF visual artifacts
```

No live OpenAI API call/key is required: 5.3 provider boundary remains fakeable/deterministic in tests.

If a temporary GitHub validation workflow is used:

```text
validate exact product/test/doc SHA
record run + job + counts
remove temporary workflow only after success
prove validated SHA -> final HEAD delta is workflow removal only
```

Any product/test/doc/dependency change after validation requires fresh validation.

---

# 19. EXPLICIT OUT OF SCOPE — 5.4

Do NOT implement:

```text
report_id
analysis_id <-> durable report resource binding
PostgreSQL report metadata/resource tables
S3/object storage
storage_key
report API routes
POST /v1/reports
GET /v1/reports/{report_id}
GET report content endpoint
Stripe/payment
n8n workflow
email delivery
commercial order workflow
frontend application
empirical validation
FAZ 6+
```

Those later concerns belong to 5.5 / FAZ 6 as already frozen by roadmap.

---

# 20. REVIEWER ACCEPTANCE GATE

Reviewer will independently inspect exact future PR head for:

```text
exact base = 30a12424cebfb6bcd53ad6fcd5d5db1b2315d9ae
one branch / one PR
scope limited to 5.4
exact pinned render dependencies
locked 5.2/5.3 authority preserved
source/narrative binding
no analytical recomputation
consistent presentation/rounding policy
chart/table fidelity
missingness fidelity
HTML/CSS/template security
asset path safety
render failure semantics
PDF structural validity
pagination/layout evidence
representative visual artifact inspection
full regression
exact validation evidence
no 5.5/FAZ6 leakage
```

Decision will be one of:

```text
NEEDS_HARDENING / HARDEN
READY_TO_LOCK / LOCK_IF_USER_AUTHORIZED
```

No auto-lock. Reviewer never merges.

Current action:

```text
IMPLEMENTER_ACTION: IMPLEMENT
USER_LOCK_AUTHORIZED: NO
MERGE: NO
START_5_5: NO
```

Implementer should create the checkpoint branch from exact base, implement 5.4, open one PR, update `implementer.md`, then STOP for Reviewer.

> Mathematically validated scoring engine; empirical validation pending.
