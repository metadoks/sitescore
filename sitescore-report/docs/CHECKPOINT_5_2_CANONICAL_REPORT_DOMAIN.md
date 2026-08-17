# FAZ 5.2 — Canonical Report Facts + Report Domain Model

## Status

- Package: `sitescore-report==0.1.0`
- Report schema: `sitescore-report-v1`
- Projection: `application-analysis-result-v1`
- Product source scope: `sitescore-report/**`
- Upstream authority: frozen `sitescore-app==0.1.0` and `sitescore-core==0.1.0`
- Database migration: none

> Mathematically validated scoring engine; empirical validation pending.

## Authority chain

The only production entry to canonical report facts is:

```text
ApplicationAnalysisResult
-> require_canonical_application_analysis_result(...)
-> build_canonical_report_facts(...)
-> CanonicalReportFacts
-> build_report_domain_model(...)
-> ReportDomainModel
```

`CanonicalReportFacts` is factory-owned. It keeps a construction-time binding to the exact factory-owned application result, exact application core input, exact `AnalysisInput`, and exact `CanonicalAnalysisResult`. Every canonical-require operation revalidates the upstream application authority and verifies both nested section identity and deterministic semantic integrity.

`ReportDomainModel` is separately factory-owned and binds to the exact `CanonicalReportFacts` object used to construct it. Equal-value copies, manual shells, replaced nested sections, or changed source bindings fail closed.

These values are never sufficient authority:

```text
CanonicalAnalysisResult alone
CanonicalAnalysisResult.to_dict()
durable API result JSON
analysis_fingerprint
model-version strings
caller category scores
caller financial/decision/confidence values
separate result-A + input-B pieces
ready/trusted/canonical flags
```

`analysis_fingerprint` and model versions are retained only as provenance facts.

## Canonical report-fact surface

### Provenance

```text
report_package_version
report_schema_version
report_projection_version
source_analysis_fingerprint
model_versions.package_version
model_versions.canonical_schema_version
model_versions.feature_schema_version
model_versions.scoring_model_version
model_versions.financial_model_version
model_versions.decision_model_version
model_versions.confidence_model_version
```

No second analysis fingerprint or report fingerprint is computed. No `generated_at` is added in this domain-only checkpoint.

### Analysis and category facts

```text
sector
category_scores.demand
category_scores.competition
category_scores.accessibility
category_scores.economics
```

Category values are copied from the exact `AnalysisInput.category_scores`; they are not recalculated or reweighted.

### Business assumptions

Common values:

```text
monthly_rent
fixed_labor
fixed_overhead
```

Revenue assumptions are an explicit tagged union.

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

Rates are preserved on the frozen 0..1 input scale; 5.2 does not convert them to display percentages.

### Location

```text
base_score
penalty_multiplier
final_score
structural_band
dominant_risk_category
```

### Financial result

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

Optional `break_even_volume` remains optional; `None` is never replaced by zero or a presentation token.

### Decision

```text
decision_class
structural_band
financial_band
headline
risk_flags
```

Risk flags retain canonical order and values. 5.2 does not prioritize, rename, suppress, or add flags.

### Confidence

```text
overall_score
label
geographic_precision
data_vintage
data_coverage
input_completeness
```

No thresholding or confidence reinterpretation occurs in the report layer.

### Data-quality context

```text
geographic_level
data_age_years
data_coverage mapping
input_qualities mapping
```

Mappings are copied into immutable report-owned mappings. Partial mappings remain partial; missing keys are not filled.

## Missingness, precision, and formatting

The report domain uses exact source values:

```text
None -> None
missing key -> missing key
empty tuple -> empty tuple
bool -> exact bool
int -> exact int
float -> exact float
```

It does not perform display rounding, currency formatting, percentage-string conversion, neutral-score fill, missing-quality fill, or customer-facing relabeling.

## JSON-safe views

`CanonicalReportFacts.to_dict()` and `ReportDomainModel.to_dict()` are transport/view helpers only. They recursively convert enums to their values and tuples to lists, and allocate fresh mutable containers on each call.

Mutating the returned dict/list does not mutate canonical facts or domain authority. A returned dict is never accepted as report authority.

## Current production reachability

Locked FAZ 5.1 truth is unchanged:

```text
COMB-005 = NOT_APPROVED
real production lifecycle = queued -> running -> not_score_ready
completed = modeled but currently unreachable from real production acquisition
```

5.2 therefore does not generate a report from `not_score_ready`, does not add a fake scored path, and does not manufacture category/location/financial/decision/confidence results. Positive package tests create genuine scored `ApplicationAnalysisResult` authority only through the frozen public application factories under a test-only upstream SCORE_READY boundary substitution; production reachability is not changed.

## Durable resource identity

No `report_id` exists in 5.2. The 5.1 server `analysis_id` is also not accepted as report-fact authority because it is not embedded in the frozen application result. Durable server ownership/binding between analysis and future report artifacts belongs to the later report resource/artifact checkpoint.

## Dependency direction

Runtime dependencies are exactly:

```text
sitescore-app==0.1.0
sitescore-core==0.1.0
```

`sitescore-report` does not depend on `sitescore-api`, and frozen/locked upstream packages do not import `sitescore_report`.

No OpenAI/Jinja/WeasyPrint/Matplotlib/S3/SQLAlchemy/Alembic/Celery/Redis/FastAPI/Stripe dependency is introduced.

## Explicitly deferred

```text
narrative generation
recommendations
HTML/templates
charts
PDF rendering
report persistence
report API routes
report IDs
object storage / S3
payment
n8n
email delivery
FAZ 6+
```
