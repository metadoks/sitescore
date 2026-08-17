# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.2
CHECKPOINT_TITLE: Canonical Report Facts + Report Domain Model

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 9b7823c7354c54605f4dc800774ee1acc1bf9c8d
CODE_BRANCH: faz5/5-2-canonical-report-domain
REVIEWED_HEAD_SHA: NONE
PR: NONE

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED
FAZ_5_1_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
BLOCKERS: NONE
```

---

# 1. POST-LOCK VERIFICATION — FAZ 5.1

Reviewer independently verified the user-authorized FAZ 5.1 LOCK before opening this checkpoint.

```text
PR: #17
state: CLOSED
merged: TRUE
reviewed head: 2cebddd79b292c18babb2ea0258a15f6123a539a
merge commit: 9b7823c7354c54605f4dc800774ee1acc1bf9c8d
current main: 9b7823c7354c54605f4dc800774ee1acc1bf9c8d
```

Exact merge parents:

```text
parent 1: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
parent 2: 2cebddd79b292c18babb2ea0258a15f6123a539a
```

The merge commit message records the exact Reviewer-approved head, expected base, READY_TO_LOCK gate, user authorization, zero contract/design escalation and no blockers.

Therefore FAZ 5.1 is LOCKED and the authoritative FAZ 5.2 base is:

```text
9b7823c7354c54605f4dc800774ee1acc1bf9c8d
```

---

# 2. CHECKPOINT PURPOSE

Create the selected FAZ 5 report package:

```text
sitescore-report==0.1.0
```

and establish the canonical report-domain projection:

```text
factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
```

This checkpoint is a truth-preserving projection/domain checkpoint only.

It does NOT implement narrative generation, HTML, charts, PDF rendering, report persistence, report API routes, report IDs, S3/object storage, payment, n8n, email or FAZ 6 work.

---

# 3. AUTHORIZED SOURCE SCOPE

Product source for this checkpoint is limited to:

```text
sitescore-report/**
```

A temporary validation-only workflow under `.github/workflows/**` is authorized as described below and must be removed before the final review candidate.

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

If correct 5.2 implementation genuinely requires modifying a frozen/locked upstream contract or sitescore-api lifecycle semantics, STOP and report the exact gap rather than expanding scope silently.

No database migration is authorized in 5.2.

---

# 4. ACTUAL SOURCE FACTS THAT DEFINE THE PROJECTION

The frozen core canonical result is:

```text
CanonicalAnalysisResult
- analysis_fingerprint
- model_versions
- location
- financial
- decision
- confidence
```

It does NOT itself carry category scores or sector/input-quality context.

Those exact inputs remain available through the factory-owned frozen application result:

```text
ApplicationAnalysisResult
-> application_core_input
-> AnalysisInput
```

where `AnalysisInput` carries:

```text
sector
category_scores
revenue_input
monthly_rent
fixed_labor
fixed_overhead
geographic_level
data_age_years
data_coverage
input_qualities
```

Therefore 5.2 production projection authority MUST start from the exact factory-owned:

```text
ApplicationAnalysisResult
```

and MUST call the public frozen canonical requirement boundary:

```text
require_canonical_application_analysis_result(...)
```

before granting report authority.

---

# 5. STRICT REPORT AUTHORITY BOUNDARY

Production report factories MUST NOT accept any of the following as sufficient report authority:

```text
CanonicalAnalysisResult by itself
core_result.to_dict()
durable API result_body JSON
arbitrary dict/JSON
analysis_fingerprint string
model-version strings
caller-provided category scores
caller-provided decision/confidence/financial DTOs
copied/forged ApplicationAnalysisResult shell
ready/trusted/canonical flags
```

The report package must not expose a production factory that accepts detached pieces such as:

```text
core_result from analysis A
+
AnalysisInput/category scores from analysis B
```

and combines them into one authoritative report.

A valid report projection begins from one exact canonical `ApplicationAnalysisResult`, so the frozen application binding remains the cross-component authority.

`analysis_fingerprint` is preserved as provenance metadata only. It never becomes construction/authentication/resource authority.

---

# 6. IMPORTANT CURRENT PRODUCT LIMITATION — DO NOT FABRICATE A SCORED REPORT

FAZ 5.1 locked truth remains:

```text
COMB-005 = NOT_APPROVED
current real production lifecycle = queued -> running -> not_score_ready
completed is modeled but not currently reachable from the real production acquisition chain
```

5.2 must NOT weaken this truth.

Therefore:

```text
CanonicalReportFacts = projection of a genuine scored/factory-owned ApplicationAnalysisResult only.
```

Do not reinterpret `not_score_ready` as a scored report.
Do not manufacture category scores, location score, financial result, decision or confidence for a non-scored analysis.
Do not add a fake `completed` path merely to demonstrate report generation.

Unit/integration tests MAY construct genuine canonical scored `ApplicationAnalysisResult` values through the existing frozen public application factories in order to test the report package. Tests must not bypass the frozen factory authority with `object.__new__` or detached DTOs when establishing the positive authority fixture.

Documentation must state clearly that the current locked real production chain remains NOT_SCORE_READY until the frozen model later has genuinely approved score-ready evidence.

---

# 7. SERVER analysis_id IS NOT A 5.2 REPORT-FACT AUTHORITY

The 5.1 server lifecycle `analysis_id` is a durable external UUIDv4 resource identity, but it is not embedded in the frozen `ApplicationAnalysisResult` / `CanonicalAnalysisResult` authority object.

5.2 therefore MUST NOT simply accept an arbitrary `analysis_id` parameter and assert that it belongs to the supplied canonical result.

For 5.2:

```text
source analysis provenance = canonical analysis_fingerprint + exact model versions + canonical application result binding
```

The durable server:

```text
analysis_id <-> report/report-artifact
```

binding belongs to the later report resource/artifact checkpoint (5.5), where PostgreSQL ownership can prove the association.

Do not add `report_id` in 5.2.

---

# 8. REQUIRED CANONICAL REPORT FACTS

Define immutable typed report fact structures. Exact class/file names may vary, but the semantic surface must cover the following exact available facts.

## 8.1 Projection/schema provenance

At minimum:

```text
report package version = 0.1.0
report schema version = explicit V1 value
report projection version = explicit V1 value
source analysis_fingerprint
exact core ModelVersions fields
```

Do not recompute the core analysis fingerprint.
Do not create a second fake core/model fingerprint.

No wall-clock `generated_at` is required in 5.2. Prefer a deterministic fact projection; report resource/artifact generation timestamps belong later in the artifact lifecycle.

## 8.2 Analysis / sector input facts

Preserve exactly:

```text
sector
category scores:
  demand
  competition
  accessibility
  economics
```

Category scores are copied from the exact frozen `AnalysisInput.category_scores` belonging to the same canonical application result. They are never recalculated or reweighted.

## 8.3 Financial/business input facts

Preserve the exact canonical business assumptions used by the scored analysis so later narrative/PDF layers do not need to rediscover or recalculate them.

Common costs:

```text
monthly_rent
fixed_labor
fixed_overhead
```

Sector-specific tagged input facts must preserve the exact frozen fields.

Coffee:

```text
target_population
target_rate
capture_rate_conservative
capture_rate_base
capture_rate_optimistic
visit_frequency_per_month
average_ticket
```

Restaurant:

```text
seats
turnover_per_day
utilization_conservative
utilization_base
utilization_optimistic
average_ticket
operating_days_per_month
```

Gym:

```text
target_population
penetration_rate_conservative
penetration_rate_base
penetration_rate_optimistic
usable_area
members_per_area_unit
monthly_membership_fee
```

Beauty:

```text
stations
operating_hours_per_week
average_service_duration_hours
utilization_conservative
utilization_base
utilization_optimistic
average_ticket
```

Do not convert percentages/rates into a different scale in the domain model.

## 8.4 Location result facts

Preserve exactly:

```text
base_score
penalty_multiplier
final_score
structural_band
dominant_risk_category
```

## 8.5 Financial result facts

Preserve exactly:

```text
revenue.conservative
revenue.base
revenue.optimistic
variable_cost_base
contribution_margin_base
fixed_costs
operating_profit_base
break_even_revenue
bec_base
bec_conservative
rent_burden_pct
rent_burden_severity
operating_margin_pct
break_even_volume
stress_test_failed
```

`break_even_volume=None` must remain `None`.

## 8.6 Decision facts

Preserve exactly:

```text
decision_class
structural_band
financial_band
headline
risk_flags
```

Do not reinterpret, relabel, reorder or prioritize `risk_flags` in 5.2.

## 8.7 Confidence facts

Preserve exactly:

```text
overall_score
label
geographic_precision
data_vintage
data_coverage
input_completeness
```

No confidence upgrade/downgrade or new thresholding.

## 8.8 Data-quality/input context

Preserve exactly from the same `AnalysisInput`:

```text
geographic_level
data_age_years
data_coverage mapping
input_qualities mapping
```

Partial mappings remain partial. No missing key is filled with a default.

Do not invent readiness reason codes or provider warnings that are not actually carried by the canonical scored application-result surface.

Authoritative existing `decision.risk_flags` may be represented as risk facts; do not rename them into new semantic warning codes.

---

# 9. MISSINGNESS / PRECISION / FORMAT RULES

5.2 is a domain projection, not a presentation layer.

Strict:

```text
None -> None
missing key -> missing key
empty risk_flags -> empty risk_flags
boolean -> exact boolean
int -> exact int
float -> exact float
```

Forbidden:

```text
None -> 0
None -> 50
None -> "N/A" as semantic replacement
missing category -> neutral score
missing quality -> FULL/USER default
unknown -> positive interpretation
rounding for display
currency formatting
percentage-string conversion
customer-friendly relabeling that changes canonical meaning
```

Rounding, localization and visual formatting belong to later presentation checkpoints.

---

# 10. FACTORY-OWNED REPORT AUTHORITY

The top-level canonical report authority must be non-forgeable by normal public construction, following the project’s established factory-owned pattern.

Required conceptual public surface:

```text
build_canonical_report_facts(application_analysis_result)
-> CanonicalReportFacts

require_canonical_report_facts(value)
-> CanonicalReportFacts

build_report_domain_model(canonical_report_facts)
-> ReportDomainModel

require_canonical_report_domain_model(value)
-> ReportDomainModel
```

Exact names may differ, but equivalent authority guarantees are required.

Rules:

- `CanonicalReportFacts` cannot be granted from detached dicts/DTOs/fingerprint strings.
- A copied/forged top-level facts object must not become canonical merely because field values match.
- `ReportDomainModel` must bind to the exact canonical facts object used to create it.
- Swapping/replacing nested canonical facts after construction must fail closed.
- Any internal semantic snapshot/registry mechanism must not expose a public forgeable token.
- If a JSON-safe projection is provided, it is a transport/view only and not report authority.

A useful public method such as `to_dict()` is authorized if it returns a deep-owned JSON-safe value and does not mutate or replace canonical authority.

Mutating the returned dict/list must not mutate `CanonicalReportFacts` or `ReportDomainModel`.

---

# 11. REPORT DOMAIN MODEL

Create an explicit report-domain structure for later 5.3/5.4 consumption.

It should organize the canonical facts into stable sections such as:

```text
provenance
analysis / sector assumptions
category scores
location result
financial result
financial/business assumptions
decision / risks
confidence
data-quality context
```

This structure may reorganize facts for report consumption, but it may not create new analytical meaning.

Do NOT add narrative text generation, strengths/risks recommendations, chart series normalization, customer scoring labels or PDF-specific layout objects in 5.2.

---

# 12. PACKAGE / DEPENDENCY CONTRACT

Create:

```text
sitescore-report==0.1.0
```

Expected direct runtime dependencies:

```text
sitescore-app==0.1.0
sitescore-core==0.1.0
```

Dev/test:

```text
pytest==8.4.2
```

No new third-party runtime dependency is justified for this domain-only checkpoint.

Do NOT add in 5.2:

```text
OpenAI SDK
Jinja2
WeasyPrint
Matplotlib
boto3/S3 SDK
SQLAlchemy/Alembic
Celery/Redis
FastAPI
Stripe
```

The report package must NOT depend on `sitescore-api`; that would create the wrong direction for later API -> report integration and risks a dependency cycle.

Frozen/locked upstream packages must not import `sitescore_report`.

---

# 13. REQUIRED TESTS

Happy path alone is insufficient.

## 13.1 Canonical authority tests

Prove:

```text
real factory-owned ApplicationAnalysisResult -> report facts PASS
plain CanonicalAnalysisResult alone -> cannot grant report authority
core_result.to_dict() -> cannot grant report authority
forged ApplicationAnalysisResult shell -> rejected
copy.copy/copy.deepcopy or equivalent detached top-level authority -> rejected where applicable
fingerprint-only attempt -> rejected
no API accepts separate result-A + input-B pieces
```

## 13.2 Fidelity tests

For canonical scored fixtures, every projected value must equal the source value exactly.

Cover all four sectors’ revenue-input variants.

Prove exact preservation of:

```text
category scores
location result
financial inputs
financial result
decision/risk_flags
confidence
model versions
quality/input context
analysis_fingerprint
```

## 13.3 Missingness tests

At minimum:

```text
break_even_volume=None remains None
dominant_risk_category=None remains None
data_age_years=None remains None
partial data_coverage remains partial
partial input_qualities remains partial
empty risk_flags remains empty
```

No defaults/reweighting may appear.

## 13.4 Adversarial semantic fixtures

Use genuine canonical application results that exercise, as feasible:

```text
strong decision
weak/adverse decision
low confidence
financial stress / stress_test_failed
```

Report facts must preserve the canonical values; they do not “improve” or reinterpret them.

## 13.5 Domain authority / mutation tests

Prove:

```text
ReportDomainModel binds to exact CanonicalReportFacts
forged/copy domain model rejected
substituted facts rejected
JSON-safe projection mutation cannot mutate canonical report authority
```

## 13.6 Architecture tests

Prove:

```text
no sitescore.analyze import in sitescore-report production
no engine imports
no scoring/financial/readiness formula implementation
no sitescore-api dependency/import
no upstream -> sitescore-report reverse dependency
no OpenAI/Jinja/WeasyPrint/Matplotlib/S3/payment/n8n scope leakage
```

---

# 14. DOCUMENTATION

Add durable documentation, for example:

```text
sitescore-report/README.md
sitescore-report/docs/CHECKPOINT_5_2_CANONICAL_REPORT_DOMAIN.md
```

Document:

```text
package/version
scope
factory-owned authority chain
exact report facts schema
why ApplicationAnalysisResult is the authority input
why detached JSON/fingerprint is not authority
why server analysis_id is not arbitrarily attached in 5.2
current COMB-005 / NOT_SCORE_READY production limitation
missingness rules
precision/no-rounding rule
dependency direction
JSON projection authority warning
out-of-scope 5.3/5.4/5.5/FAZ6 items
canonical validity statement: Mathematically validated scoring engine; empirical validation pending.
```

---

# 15. VALIDATION / CI

Fresh exact-SHA validation is required.

A temporary workflow such as:

```text
.github/workflows/faz5-5-2-validation.yml
```

is authorized for validation only.

The validation environment should provision PostgreSQL and Redis as needed to rerun the locked `sitescore-api` regression suite, because the 5.1 baseline includes real DB/broker semantics.

Required fresh suites:

```text
sitescore-report: ALL PASS; report exact count
sitescore-api: 88 PASS baseline
sitescore-app: 19 PASS
sitescore-pipeline: 53 PASS
sitescore-benchmarks: 191 PASS
sitescore-metrics: 67 PASS
sitescore-spatial: 180 PASS
sitescore-providers: 418 PASS
sitescore-data: 361 PASS
sitescore-core: 86 PASS
```

Existing locked baseline excluding the new report package:

```text
1463 PASS
```

Final combined count must be:

```text
1463 + exact sitescore-report test count
```

Print/verify at minimum:

```text
Python version
sitescore-report 0.1.0
sitescore-app 0.1.0
sitescore-core 0.1.0
pytest 8.4.2
```

and preserve the exact locked 5.1 dependency environment for the API regression.

After successful validation:

1. remove the temporary validation workflow;
2. do not change product source/tests/docs afterward;
3. prove validated-SHA -> final-head delta is ONLY the authorized validation-workflow deletion.

If any product file changes after successful validation, rerun validation on the new candidate.

---

# 16. REVIEW BLOCKER FAMILY

Use consolidated blocker IDs beginning with:

```text
REPORT52-H001
REPORT52-H002
...
```

Likely true blockers include:

```text
report factory accepts detached JSON/result DTO as authority
report package accepts core result and unrelated category/input authority separately
category score/Location Score/financial/decision/confidence recomputation
missing -> zero/neutral/default
rounding/formatting changes semantic value
analysis_fingerprint treated as construction authority
arbitrary server analysis_id asserted as bound to result
report authority forgeable by plain dataclass/copy
JSON view mutation changes canonical facts
sitescore-report -> sitescore-api dependency
frozen upstream reverse dependency
not_score_ready converted into fake scored report
5.3/5.4/5.5/FAZ6 scope leakage
unvalidated final product changes
```

Do not block merely for naming/style preferences or theoretical future abstractions with no current incorrect path.

---

# 17. EXPLICIT EXCLUSIONS

Do NOT implement in checkpoint 5.2:

```text
OpenAI / LLM calls
narrative generation
strength/risk/recommendation prose
Jinja2 templates
HTML/CSS
Matplotlib charts
WeasyPrint/PDF
S3/object storage
report_id
report persistence tables
report API endpoints
report async lifecycle
new auth scopes/routes
Stripe/payment
n8n workflows
email delivery
empirical calibration/validation
FAZ 6+
```

Do not start 5.3.

---

# 18. IMPLEMENTER RETURN CONTRACT

After implementation:

1. create/use only branch:

```text
faz5/5-2-canonical-report-domain
```

2. open one PR against exact base `main`;
3. run fresh validation;
4. remove validation-only workflow after successful candidate validation;
5. update `implementer.md` with:

```text
CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.2
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: 9b7823c7354c54605f4dc800774ee1acc1bf9c8d
CODE_BRANCH: faz5/5-2-canonical-report-domain
CODE_HEAD_SHA: <exact>
PR: #<exact>
CONTRACT_CHANGE_REQUIRED: 0/1
DESIGN_DECISION_REVIEW_REQUIRED: 0/1
```

Report:

```text
sitescore-report package/version
exact dependency pins
public report factories/types
fact schema
canonical authority evidence
all four sector fidelity evidence
missingness/adversarial evidence
current NOT_SCORE_READY limitation documentation
fresh test counts
validation run/job/SHA
validated->final cleanup proof
full changed-file scope
```

Then STOP.

Do not merge.
Do not start 5.3.

---

# 19. CURRENT REVIEWER DECISION

```text
REVIEW_DECISION: IMPLEMENTATION_REQUESTED
READY_TO_LOCK: NO
LOCK_RESULT: NOT_APPLICABLE
CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.2
EXPECTED_BASE_SHA: 9b7823c7354c54605f4dc800774ee1acc1bf9c8d
CODE_BRANCH: faz5/5-2-canonical-report-domain
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: NONE
```

Implementer must now implement checkpoint 5.2 exactly as above and return for exact-head review.

STOP.
