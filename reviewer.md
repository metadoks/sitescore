# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.3
CHECKPOINT_TITLE: Narrative / Insight Authority Boundary

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
CODE_BRANCH: faz5/5-3-narrative-insight-authority
REVIEWED_HEAD_SHA: NONE
PR: NONE

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED
FAZ_5_1_STATUS: LOCKED
FAZ_5_2_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
BLOCKERS: NONE
```

---

# 1. POST-LOCK VERIFICATION — FAZ 5.2

Reviewer independently verified the user-authorized FAZ 5.2 LOCK before opening this checkpoint.

```text
PR: #18
state: CLOSED
merged: TRUE
reviewed head: 538577f5f0a99973f1b295a6ece2b055abeb6377
merge commit: 8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
current main: 8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
```

Exact merge parents:

```text
parent 1: 9b7823c7354c54605f4dc800774ee1acc1bf9c8d
parent 2: 538577f5f0a99973f1b295a6ece2b055abeb6377
```

Thus the exact Reviewer-approved 5.2 product head was merged onto the exact expected pre-lock `main`.

FAZ 5.2 is now LOCKED. The authoritative 5.3 base is:

```text
8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
```

---

# 2. CHECKPOINT PURPOSE

Extend the locked report package from:

```text
factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
```

to the truth-preserving narrative chain:

```text
ReportDomainModel
-> ApprovedNarrativeContext
-> untrusted narrative provider draft
-> strict schema validation
-> deterministic semantic validation
-> ValidatedReportNarrative
```

Primary provider adapter:

```text
OpenAI Responses API
```

LLM role:

```text
LLM = narrator / language layer
LLM != scoring engine
LLM != financial calculator
LLM != decision authority
LLM != confidence authority
LLM != readiness authority
```

The final report narrative must remain usable when the provider is unavailable or returns invalid/contradictory output; therefore deterministic fallback is mandatory.

---

# 3. AUTHORIZED SOURCE SCOPE

Product changes are limited to:

```text
sitescore-report/**
```

A temporary exact-validation workflow under:

```text
.github/workflows/**
```

is authorized only for CI evidence and must be removed before the final review candidate.

Do NOT modify:

```text
sitescore-core/**
sitescore-data/**
sitescore-providers/**
sitescore-spatial/**
sitescore-metrics/**
sitescore-benchmarks/**
sitescore-pipeline/**
sitescore-app/**
sitescore-api/**
```

No DB migration, API route, report resource, report_id, analysis_id/report binding, PDF, template, storage or payment change is authorized in 5.3.

If correct 5.3 work genuinely requires changing frozen/locked upstream semantics, set:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

and STOP.

If the selected OpenAI Responses API architecture is technically incompatible, set:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

and STOP rather than silently substituting another provider architecture.

---

# 4. PACKAGE / VERSION TARGET

Advance the report package to:

```text
sitescore-report==0.2.0
```

Retain exact locked direct dependencies:

```text
sitescore-app==0.1.0
sitescore-core==0.1.0
```

Add only the dependencies genuinely required for the narrative adapter and typed local schema validation.

Expected:

```text
openai == exact pinned compatible version selected during implementation
pydantic == 2.13.4 if Pydantic models are used for provider/schema validation
pytest == 8.4.2 dev/test
```

Rules:

```text
no floating openai version range
no unrelated dependency upgrades
no sitescore-api dependency
no Jinja2
no WeasyPrint
no Matplotlib
no boto3/S3 SDK
no SQLAlchemy/Alembic
no Celery/Redis
no FastAPI
no Stripe
```

Implementer must record the exact selected OpenAI SDK version and prove the installed version in fresh CI.

---

# 5. CANONICAL NARRATIVE AUTHORITY

Production narrative authority MUST start only from the exact factory-owned locked 5.2 domain:

```text
ReportDomainModel
```

Required first gate:

```text
require_canonical_report_domain_model(...)
```

Create a factory-owned bounded context conceptually equivalent to:

```text
build_approved_narrative_context(report_domain_model)
-> ApprovedNarrativeContext
```

`ApprovedNarrativeContext` must bind to the exact canonical `ReportDomainModel` and, transitively, to the exact locked `CanonicalReportFacts` / application result authority.

It must NOT be constructible as authority from:

```text
dict/JSON
CanonicalReportFacts.to_dict()
ReportDomainModel.to_dict()
analysis_fingerprint
model-version strings
caller-provided category scores
caller-provided decision/financial/confidence values
forged/copy ReportDomainModel shell
```

A copied/equal-value context must not become canonical merely because values match.

`analysis_fingerprint` remains provenance metadata only.

---

# 6. BOUNDED NARRATIVE CONTEXT

The LLM must receive a deliberately bounded, report-safe context derived only from the exact canonical report domain.

It may include exact available report facts needed to explain the result, such as:

```text
sector
category scores
canonical location result
canonical financial result
canonical decision/headline/risk_flags
canonical confidence
canonical data-quality/input context
canonical business assumptions where useful
source analysis_fingerprint as provenance metadata
exact model/report schema versions
```

It must NOT include unrelated raw provider payloads, raw HTTP responses, hidden deployment credentials, API keys, database rows, Celery state or arbitrary caller text merely because those values exist elsewhere.

No report/narrative layer may recompute scoring, financial, confidence, decision, benchmark or readiness semantics while creating the context.

---

# 7. OPENAI RESPONSES API ADAPTER

Primary production adapter:

```text
OpenAI Responses API
```

Model identity must be configuration-driven.

Required behavior:

```text
model ID comes from server/deployment configuration
model ID is generation provenance, not business truth
API credential comes from secure environment/client configuration
raw API key is never persisted in report facts or logs
prompt/instruction version is code-owned and explicit
provider/model/prompt identity is recorded as narrative provenance
```

Use strict structured output through the Responses API JSON-schema/structured-output surface supported by the selected SDK/model.

Do not rely on free-form text followed by best-effort JSON scraping.

Provider request must use no external tools:

```text
no web search
no file search
no remote MCP
no function tools
```

The provider is given the bounded narrative context only.

Tests must not require a real paid OpenAI network call or secret. Fakes/mocks belong at the OpenAI client/transport boundary, not by minting a fake `ValidatedReportNarrative` authority object.

---

# 8. UNTRUSTED PROVIDER DRAFT SCHEMA

Provider output is an untrusted draft even when strict schema validation succeeds.

Define a strict typed/schema-validated draft surface with at least these customer-facing sections:

```text
executive_summary
strengths
risks
recommendations
caveats
```

Recommended exact shape:

```text
NarrativeDraft
  canonical_anchors
  executive_summary
  strengths[]
  risks[]
  recommendations[]
  caveats[]
```

`canonical_anchors` must echo exact context-owned semantic anchors sufficient for deterministic validation, at minimum:

```text
decision_class
structural_band
financial_band
confidence_label
stress_test_failed
source_analysis_fingerprint
```

Each strengths/risks/recommendations item should carry:

```text
text
one-or-more evidence_keys
```

where `evidence_keys` are selected only from an approved closed set of canonical context fact paths/identifiers.

Unknown evidence keys are invalid.

Recommendation text is advisory prose only; it may not assert a new canonical outcome.

Exact class names may differ, but equivalent machine-checkable anchors and evidence binding are required.

---

# 9. FINAL VALIDATED NARRATIVE AUTHORITY

Create a top-level factory-owned final authority conceptually equivalent to:

```text
ValidatedReportNarrative
```

A provider draft itself is never report authority.

Authority chain:

```text
canonical ReportDomainModel
-> canonical ApprovedNarrativeContext
-> provider draft OR deterministic fallback draft
-> schema validation
-> semantic validation
-> factory-owned ValidatedReportNarrative
```

`ValidatedReportNarrative` must bind to the exact `ApprovedNarrativeContext` used to create it.

A copied/forged final narrative, source-context substitution, nested semantic mutation, or equal-value object replacement must fail closed under the project’s established factory-owned pattern.

A JSON-safe `to_dict()` view is authorized only as a deep-owned non-authority projection.

---

# 10. DETERMINISTIC SEMANTIC VALIDATION — REQUIRED

Schema-valid JSON is NOT sufficient.

The deterministic semantic validator must reject contradictions against the exact canonical context.

At minimum validate all of the following families.

## 10.1 Canonical anchor equality

Provider-echoed anchors must exactly equal source context:

```text
decision_class
structural_band
financial_band
confidence_label
stress_test_failed
source_analysis_fingerprint
```

Any mismatch rejects the provider draft.

## 10.2 Evidence binding

Every evidence key must:

```text
exist in the approved context
refer to a fact actually present
not refer to a missing mapping key
not fabricate unavailable evidence
```

A narrative point may not cite a missing key as evidence.

## 10.3 Decision consistency

Reject prose/structured claims that contradict the exact canonical decision.

Examples:

```text
canonical dead_end -> provider presents prime opportunity
canonical tourist_trap -> provider says economics are strong
canonical structural_risk -> provider says location is structurally strong
```

Do not derive a second decision matrix in 5.3. Use exact canonical decision_class / structural_band / financial_band / headline as authority.

## 10.4 Financial consistency

Use exact canonical financial outputs/status fields as authority.

Reject contradiction examples such as:

```text
financial_band = non_viable -> "financially strong"
stress_test_failed = TRUE -> "stress test passed"
operating_margin_pct < 0 -> "positive base operating margin"
SEVERE_RENT_BURDEN present -> "rent burden is low"
```

Do NOT recompute financial feasibility thresholds in the narrative layer.

## 10.5 Confidence consistency

Reject certainty upgrades.

Examples:

```text
confidence label = low -> "high confidence" / "highly certain"
confidence label = medium -> "near certain"
unknown/degraded quality -> "complete evidence"
```

Use the canonical confidence label and exact data-quality context; do not create a second confidence formula.

## 10.6 Missingness consistency

Forbidden:

```text
None -> claim numeric zero
missing mapping key -> claim FULL/USER/default
unknown -> positive certainty
absent risk evidence -> invented risk fact
```

Missing remains missing.

## 10.7 Unsupported / prohibited claims

Reject claims equivalent to:

```text
empirically validated
proven in market
calibrated against real-world outcomes
financial guarantee
guaranteed success
certain profitability
risk-free
```

The canonical validity statement remains:

> Mathematically validated scoring engine; empirical validation pending.

## 10.8 Numeric invention control

LLM prose must not become a source of report numbers.

For V1 5.3, use the conservative rule:

```text
free-form LLM prose must not introduce numeric/currency/percentage literals
```

Exact numeric values are already canonical report facts and will be rendered deterministically by later presentation layers.

If provider prose contains numeric literals, reject it and use fallback rather than attempting fuzzy numeric reconciliation.

---

# 11. DETERMINISTIC FALLBACK — REQUIRED

Provider failure must not erase valid canonical report facts.

Fallback must activate for at least:

```text
provider/model unconfigured
OpenAI client/provider exception
network timeout
provider unavailable
refusal
incomplete response
schema-invalid output
unknown evidence key
canonical-anchor mismatch
semantic contradiction
prohibited empirical/guarantee claim
numeric invention rule violation
```

Fallback is built deterministically from exact canonical report/domain fields only.

Allowed fallback behavior includes controlled versioned mappings from already-canonical categorical/status fields such as:

```text
decision.headline
decision_class
structural_band
financial_band
risk_flags
confidence.label
stress_test_failed
data-quality missingness
```

Fallback MUST NOT:

```text
calculate new scores
calculate thresholds
re-evaluate BEC
recompute confidence
invent recommendations from unavailable data
turn a weak state into a positive state
```

Generic recommendation mappings based on exact existing canonical risk/status labels are permitted if explicit, deterministic, versioned and tested.

The final narrative provenance must clearly distinguish:

```text
generation_mode = llm | deterministic_fallback
provider
model_id or None
prompt_version
narrative_schema_version
fallback_reason or None
```

Do not expose API secrets/provider internals in provenance.

---

# 12. CURRENT PRODUCT LIMITATION — NOT_SCORE_READY REMAINS TRUTH

Locked FAZ 5.1/5.2 truth remains:

```text
COMB-005 = NOT_APPROVED
real production analysis lifecycle = queued -> running -> not_score_ready
```

5.3 must NOT manufacture a scored report/narrative from `not_score_ready`.

Positive narrative tests may create a genuine scored/factory-owned `ApplicationAnalysisResult` through the same frozen public application factories used by 5.2 test fixtures under a test-only upstream SCORE_READY boundary substitution.

Production code must contain no SCORE_READY-forcing seam.

No `analysis_id`, `report_id`, report lifecycle or artifact binding is introduced in 5.3.

---

# 13. PROMPT / INSTRUCTION CONTRACT

Define a code-owned prompt/instruction version, for example:

```text
NARRATIVE_PROMPT_VERSION = sitescore-narrative-prompt-v1
NARRATIVE_SCHEMA_VERSION = sitescore-narrative-v1
```

Prompt rules must explicitly tell the provider:

```text
use only supplied facts
never calculate or infer a new score/financial outcome/decision/confidence
never invent missing evidence
never claim empirical validation
never guarantee success/profitability
never output HTML/CSS
never introduce numeric/currency/percentage literals
return only the strict structured schema
bind every insight/recommendation to approved evidence keys
```

Prompt text/version must be deterministic application assets, not caller-controlled input.

Do not allow external request text to replace system/developer narrative instructions.

---

# 14. FAILURE / EXCEPTION CONTRACT

Narrative provider failure is recoverable through fallback unless the canonical report/domain authority itself is invalid.

Required distinction:

```text
invalid/forged ReportDomainModel or context authority
-> hard failure / reject

valid canonical context + LLM/provider failure
-> deterministic fallback narrative
```

Do not silently catch canonical authority failures and turn them into a successful fallback.

Fallback is for language/provider failure, not for bypassing report authority.

---

# 15. REQUIRED TESTS

Happy path alone is insufficient.

## 15.1 Authority tests

Prove:

```text
canonical ReportDomainModel -> ApprovedNarrativeContext PASS
plain dict/domain.to_dict -> cannot grant context authority
forged/copied ReportDomainModel -> rejected by upstream require
copied/manual ApprovedNarrativeContext -> rejected
provider draft alone -> not final authority
copied/manual ValidatedReportNarrative -> rejected
source-context substitution -> rejected
nested semantic mutation -> rejected
JSON view mutation cannot mutate narrative authority
```

## 15.2 Provider adapter tests

With a fake at the OpenAI client/transport boundary, prove:

```text
Responses API adapter path used
configured model ID used
strict structured JSON schema requested
bounded context only
no web/file/MCP/function tools
prompt version fixed by code
API secret absent from prompt/output/loggable narrative structures
```

No real paid OpenAI call is required in CI.

## 15.3 Semantic contradiction tests

At minimum:

```text
decision anchor mismatch -> fallback
wrong financial_band -> fallback
stress_test_failed TRUE + passed claim -> fallback
negative operating margin + positive-margin claim -> fallback
low confidence + high-certainty claim -> fallback
missing quality key + complete-evidence claim -> fallback
unknown evidence key -> fallback
wrong fingerprint anchor -> fallback
empirical-validation claim -> fallback
guaranteed-profit/success claim -> fallback
numeric/currency/percentage literal in LLM prose -> fallback
```

## 15.4 Truth-preserving success tests

For genuine scored canonical fixtures across all four sectors, prove valid provider drafts preserve:

```text
exact source binding
exact canonical anchors
risk/evidence references
no numeric mutation
no decision/confidence upgrade
```

## 15.5 Fallback tests

Prove deterministic fallback for:

```text
missing provider config
provider exception
timeout
refusal/incomplete response
schema-invalid response
semantic contradiction
```

Repeated fallback for the same canonical context must be byte/structure deterministic except fields explicitly excluded from deterministic narrative content.

## 15.6 Current NOT_SCORE_READY limitation

Prove 5.3 does not add a production path that narrates current canonical `not_score_ready` as scored success.

## 15.7 Architecture tests

Prove production `sitescore-report` narrative code has:

```text
no sitescore.analyze import
no scoring engine import
no financial engine import
no readiness evaluator formula
no sitescore-api import/dependency
no upstream -> sitescore-report reverse dependency
no Jinja2/WeasyPrint/Matplotlib/S3/payment/n8n scope leakage
no arbitrary HTML/CSS generation authority
```

---

# 16. DOCUMENTATION

Update durable `sitescore-report` docs to record:

```text
package/version 0.2.0
5.2 canonical report authority remains locked baseline
ApprovedNarrativeContext authority chain
OpenAI Responses API adapter boundary
model configuration semantics
prompt/schema versioning
strict structured output contract
provider draft is untrusted
semantic validator rules
numeric invention prohibition
unsupported empirical/guarantee claims
fallback triggers
fallback provenance
current NOT_SCORE_READY limitation
no analysis_id/report_id in 5.3
no HTML/PDF/storage/API routes in 5.3
canonical validity statement
```

Canonical validity statement:

> Mathematically validated scoring engine; empirical validation pending.

---

# 17. VALIDATION / CI

Fresh exact-SHA validation is required.

A temporary workflow such as:

```text
.github/workflows/faz5-5-3-validation.yml
```

is authorized for validation only.

CI must not require an OpenAI API key or real provider network call. The selected OpenAI SDK must nevertheless be genuinely installed and the adapter exercised against a deterministic fake client/transport boundary.

Fresh validation must include:

```text
sitescore-report: ALL tests PASS; record exact total
sitescore-api: 88 PASS
sitescore-app: 19 PASS
sitescore-pipeline: 53 PASS
sitescore-benchmarks: 191 PASS
sitescore-metrics: 67 PASS
sitescore-spatial: 180 PASS
sitescore-providers: 418 PASS
sitescore-data: 361 PASS
sitescore-core: 86 PASS
```

Locked non-report baseline remains:

```text
1463 PASS
```

Locked 5.2 combined baseline was:

```text
1470 PASS
```

If the final `sitescore-report` test count is `R`, total fresh combined expectation is:

```text
1463 + R
```

with the prior seven 5.2 report tests still passing.

Preserve the real locked 5.1 PostgreSQL/Redis/Celery validation environment when rerunning `sitescore-api`.

Print/verify at minimum:

```text
Python version
sitescore-report 0.2.0
sitescore-app 0.1.0
sitescore-core 0.1.0
pydantic version if direct dependency
openai exact installed version
pytest 8.4.2
```

After successful validation:

1. remove the temporary validation workflow;
2. do not change product source/tests/docs afterward;
3. prove validated SHA -> final HEAD delta is ONLY the authorized workflow deletion.

Any product change after the successful run requires a fresh run.

---

# 18. REVIEW BLOCKER FAMILY

Use consolidated blocker IDs:

```text
NARR53-H001
NARR53-H002
...
```

True blockers include reproducible paths where:

```text
LLM/provider can grant final narrative authority directly
forged/detached report data becomes narrative authority
provider receives raw/unbounded authority data
LLM calculates/replaces score/financial/decision/confidence
strict structured output is absent
semantic contradiction passes as valid narrative
unknown/missing evidence is narrated as known
low confidence is upgraded
financially weak state is described as strong
empirical validation or guarantees are claimed
LLM-provided numeric values become report truth
provider failure destroys otherwise valid canonical report generation instead of fallback
fallback recomputes analytical truth
fallback hides canonical authority failure
source context can be swapped across analyses
model ID is hard-coded as business-semantic authority
OpenAI secret appears in source/log/provenance
sitescore-report depends on sitescore-api
5.4/5.5/FAZ6 scope leakage
final product changed after validation without rerun
```

Do not block for naming/style preferences with no incorrect path.

---

# 19. EXPLICIT EXCLUSIONS

Do NOT implement in 5.3:

```text
Jinja2 templates
HTML/CSS report rendering
Matplotlib charts
WeasyPrint/PDF
report_id
report persistence tables
S3/object storage
report API routes
analysis/report lifecycle integration
new auth scopes/routes
Stripe/payment
n8n workflows
email delivery
frontend
empirical calibration/validation
FAZ 6+
```

Do not start 5.4.

---

# 20. IMPLEMENTER RETURN CONTRACT

Implementer must:

1. create/use only:

```text
faz5/5-3-narrative-insight-authority
```

2. base it exactly on:

```text
8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
```

3. open one PR against `main`;
4. implement only 5.3;
5. run fresh exact-SHA validation;
6. remove the temporary validation workflow only after success;
7. update `implementer.md` with at least:

```text
CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.3
IMPLEMENTER_STATE: READY_FOR_REVIEW
EXPECTED_BASE_SHA: 8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
CODE_BRANCH: faz5/5-3-narrative-insight-authority
CODE_HEAD_SHA: <exact>
PR: #<exact>
CONTRACT_CHANGE_REQUIRED: 0/1
DESIGN_DECISION_REVIEW_REQUIRED: 0/1
```

Report exact evidence for:

```text
sitescore-report version
OpenAI SDK exact pin
all direct dependencies
public narrative/context/final authority types and factories
strict provider schema
prompt/schema versions
bounded context fields
semantic guards
fallback behavior/provenance
all contradiction tests
all four-sector tests
fresh test counts
validation run/job/SHA
validated -> final cleanup compare
full changed-file scope
```

Then STOP.

Do not merge.
Do not start 5.4.

---

# 21. CURRENT REVIEWER DECISION

```text
REVIEW_DECISION: IMPLEMENTATION_REQUESTED
READY_TO_LOCK: NO
LOCK_RESULT: NOT_APPLICABLE
CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.3
EXPECTED_BASE_SHA: 8b856aafd64d862dee2f2c022b2f9e5a41dc3edf
CODE_BRANCH: faz5/5-3-narrative-insight-authority
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: NONE
```

Implementer must now implement checkpoint 5.3 exactly as above and return for exact-head review.

STOP.
