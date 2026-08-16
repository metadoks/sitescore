# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.1
CHECKPOINT_TITLE: Category Aggregation Authority

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 67333dc0189e43cdca6347e9115a8426cac5ce19
CODE_BRANCH: faz4/4.1-category-aggregation-authority
REVIEWED_HEAD_SHA: NONE
PR: NONE

CONTRACT_CHANGE_REQUIRED: 0
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
DEPENDENCY_CHANGE_AUTHORIZED: sitescore-app -> sitescore-core==0.1.0 ONLY

FAZ_3_STATUS: FROZEN
FAZ_4_0_STATUS: HISTORICALLY_LOCKED_MERGED
AUTHORITY_CORRECTIVE_REOPEN_STATUS: LOCKED_MERGED
FAZ_4_1_IMPLEMENTATION_STATUS: IMPLEMENTATION_REQUESTED
FAZ_4_2_IMPLEMENTATION_STATUS: NOT_STARTED
FAZ_4_3_IMPLEMENTATION_STATUS: NOT_STARTED
FAZ_4_4_IMPLEMENTATION_STATUS: NOT_STARTED

BLOCKERS: NONE
```

---

# 1. TRANSITION AUTHORITY / EXACT BASE

The user requested continuation after the authority corrective reopen was independently verified LOCKED / MERGED.

Reviewer independently verified current `main`:

```text
67333dc0189e43cdca6347e9115a8426cac5ce19
```

The previous corrective merge is complete. FAZ 4.1 is therefore authorized to begin from exactly this base.

Historical truth must remain intact:

```text
FAZ 3: FROZEN
FAZ 4.0: HISTORICALLY LOCKED / MERGED
Authority corrective reopen: LOCKED / MERGED
FAZ 4.1: NOW AUTHORIZED
FAZ 4.2+: NOT STARTED
```

Do not reopen or modify prior locked checkpoints except where this 4.1 instruction explicitly permits an additive `sitescore-app` dependency/source change.

---

# 2. CHECKPOINT OBJECTIVE

Implement exactly one capability:

```text
canonical ApplicationScoringInput
-> frozen-sector resolution
-> frozen subfeature-weight aggregation
-> factory-owned application category-aggregation authority
```

FAZ 4.1 owns calculation of the four application category scores:

```text
demand
competition
accessibility
economics
```

It does NOT own:

```text
core AnalysisInput adaptation
core CategoryScores construction
core analyze()
Location Score
penalty/dealbreaker execution
Decision Layer
financial orchestration
HTTP/API transport
```

Those remain later checkpoints.

`SCORE_READY != SCORED` remains true at the frozen pipeline boundary. A canonical `ApplicationScoringInput` grants permission for this 4.1 aggregation stage; it does not itself contain category scores.

---

# 3. CANONICAL INPUT AUTHORITY

The only production authority input to category aggregation must be the exact factory-owned canonical:

```text
ApplicationScoringInput
```

produced by the already locked `sitescore-app` application boundary.

Do NOT accept detached authority parameters such as:

```text
SectorKey
Sector
NormalizedLocationFeatures
RealDataPipelineResult
ScoringReadinessResult
readiness_fingerprint
ready=True
trusted=True
force=True
skip_readiness=True
raw category values
caller-supplied weights
```

A raw/caller-created/copy-equivalent object with matching fields is not authority.

The 4.1 aggregation path must consume the already closure-bound canonical scoring authority and preserve the corrected post-registration mutation defenses from APP-H002 / APP-H002-R001.

Preferred architecture:

```text
extend/use the existing closure-owned application authority installer
-> resolve canonical ApplicationScoringInput once to trusted bound authority
-> capture exact sector/features/readiness identity from that trusted binding
-> compute categories
-> revalidate nested scoring authority before registering the category result
```

Do not downgrade to:

```text
require_canonical_application_scoring_input(input)
-> later trust caller-mutable public references without integrity revalidation
```

An equivalent architecture is acceptable only if it demonstrably preserves construction-time origin + semantic integrity and cannot be redirected through the project's `object.__setattr__` adversarial model.

---

# 4. FROZEN CORE AUTHORITY — DIRECT CONSUMPTION, NO COPIES

FAZ 4.1 is explicitly authorized to add this one downstream runtime dependency:

```text
sitescore-app -> sitescore-core==0.1.0
```

Expected `sitescore-app` runtime dependencies after this checkpoint:

```text
sitescore-data==0.1.0
sitescore-pipeline==0.1.0
sitescore-core==0.1.0
```

No other new runtime dependency is authorized.

Package version remains:

```text
sitescore-app==0.1.0
```

The app must consume the actual frozen core authorities directly:

```text
sitescore.config.sectors.Sector
sitescore.config.subfeature_weights.DEMAND_SUBFEATURE_WEIGHTS
sitescore.config.subfeature_weights.ACCESSIBILITY_SUBFEATURE_WEIGHTS
```

Do NOT copy/redeclare/re-encode the numeric weight tables in `sitescore-app` production source, JSON, config, tests-as-runtime-data, or another package.

Do NOT introduce alternate weights, configurable overrides, environment-variable weights, category-specific renormalization, or caller-supplied weights.

The frozen weight authority remains `sitescore-core`.

---

# 5. SECTOR RESOLUTION

`sitescore_data.validation.SectorKey` is intentionally an opaque normalized identifier and does not enforce the frozen business vocabulary.

FAZ 4.1 is the application boundary where semantic sector resolution must become exact.

Allowed canonical sectors are only the frozen core values:

```text
coffee
restaurant
gym
beauty
```

Resolve the canonical scoring input's exact bound `SectorKey.value` to the frozen core `Sector` enum.

Unsupported identifiers must fail closed.

Forbidden behavior:

```text
default to coffee
alias mapping
case repair
prefix/suffix stripping
fuzzy matching
unknown -> neutral sector
unknown -> average weights
```

No sector may be inferred from feature values or caller metadata.

---

# 6. EXACT CATEGORY SEMANTICS

The eight frozen normalized feature slots remain exactly:

```text
walkable_population_score
target_population_density_score
age_target_concentration_score
competition_opportunity_score
walkable_reach_area_score
transit_access_score
road_parking_access_score
household_income_score
```

No slot may be added, removed, renamed, substituted, or silently ignored.

## 6.1 Demand

Demand is the exact sector-specific frozen weighted sum:

```text
walkable_population_score
+ target_population_density_score
+ age_target_concentration_score
```

mapped to the core weight keys:

```text
walkable_population
target_population_density
age_target_concentration
```

Frozen core weights:

```text
COFFEE:     0.70 / 0.20 / 0.10
RESTAURANT: 0.50 / 0.30 / 0.20
GYM:        0.30 / 0.40 / 0.30
BEAUTY:     0.20 / 0.40 / 0.40
```

Do not hard-code these values in app production source; this table is recorded here for Reviewer acceptance only. Production execution must read the core mapping.

## 6.2 Competition

Competition category score is exactly:

```text
competition_opportunity_score.value
```

No additional inversion, weighting, exponent, percentile transform, smoothing, or penalty is permitted. The normalization layer already owns the competition-direction semantics.

## 6.3 Accessibility

Accessibility is the exact sector-specific frozen weighted sum:

```text
walkable_reach_area_score
+ transit_access_score
+ road_parking_access_score
```

mapped to the core weight keys:

```text
walkable_reach_area
transit_access
road_parking_access
```

Frozen core weights:

```text
COFFEE:     0.50 / 0.30 / 0.20
RESTAURANT: 0.40 / 0.30 / 0.30
GYM:        0.10 / 0.20 / 0.70
BEAUTY:     0.10 / 0.20 / 0.70
```

Again: production execution must consume the actual core mapping, not a local copy.

## 6.4 Economics

Economics category score is exactly:

```text
household_income_score.value
```

No rent, cost, revenue, affordability, financial-engine output, ratio, or external economic input may enter this checkpoint.

---

# 7. NUMERIC / MISSINGNESS RULES

FAZ 4.1 must preserve all frozen missingness and calibration rules.

Canonical aggregation requires actual numeric 0..100 values for every required normalized feature used by the four categories.

If a required numeric value is absent or the canonical scoring authority has lost integrity, fail closed.

Absolutely forbidden:

```text
None -> 0
None -> 50
generic neutral fill
mean fill
last-known-value fill
weight renormalization around missing inputs
partial category scoring
substitution between features
```

The sole frozen age exception remains upstream:

```text
age_target_concentration_score = 50
only under age_neutral_fallback / 1.0
proxy=True
reason=age_affinity_not_calibrated
```

4.1 does not create, broaden, reinterpret, or re-approve that fallback. It merely consumes the canonical ready normalized feature value that already passed the upstream readiness authority.

No arbitrary output rounding is permitted. Preserve the deterministic weighted-sum float result. Presentation rounding belongs elsewhere.

---

# 8. FACTORY-OWNED CATEGORY AGGREGATION AUTHORITY

The four computed values must not become downstream production authority merely because a public DTO has the same shape.

Introduce a factory-owned app-layer category aggregation result/capability, for example:

```text
ApplicationCategoryAggregationResult
```

Equivalent naming is acceptable, but the authority semantics are mandatory.

Recommended public production API shape:

```text
aggregate_application_category_scores(
    application_scoring_input: ApplicationScoringInput,
) -> ApplicationCategoryAggregationResult

require_canonical_application_category_aggregation_result(
    value: ApplicationCategoryAggregationResult,
) -> ApplicationCategoryAggregationResult
```

The category result must be construction-time bound in closure-private state to at least:

```text
exact canonical ApplicationScoringInput
resolved frozen core Sector
exact normalized-feature authority used for computation
readiness fingerprint
computed demand
computed competition
computed accessibility
computed economics
aggregation-policy identity/version if one is introduced
```

Canonical downstream validation must establish:

```text
factory-owned registered result identity
+
construction-time category binding integrity
+
nested ApplicationScoringInput still canonical
+
category values have not diverged after registration
```

Direct `object.__setattr__` mutation of the result or its nested authority references must fail closed.

Future FAZ 4.2 must be able to accept only this canonical application aggregation authority, not four detached caller floats.

Do not use a public hash/token/boolean/sentinel as sole authority.

---

# 9. ReadyCategoryScorePayload BOUNDARY

Frozen `sitescore-data` explicitly states that `ReadyCategoryScorePayload` validates four already-computed values and does NOT compute category aggregation.

Therefore:

```text
ReadyCategoryScorePayload shape != application scoring authority
```

FAZ 4.1 MAY materialize a `ReadyCategoryScorePayload` as a non-authoritative DTO after computing canonical category values only if every field, including `normalization_policy_version`, can be populated with an already-defined truthful canonical meaning.

Do NOT invent a placeholder normalization identity merely to populate that DTO.

Whether or not this DTO is materialized, downstream execution authority for 4.2 must remain the factory-owned app category aggregation result, not a caller-constructible `ReadyCategoryScorePayload`.

No modification to frozen `sitescore-data` is authorized for this purpose.

---

# 10. STRICT 4.2+ FIREWALL

FAZ 4.1 must stop after category aggregation authority.

Explicitly forbidden in production source during this checkpoint:

```text
sitescore.schemas.location.CategoryScores construction
sitescore.config.category_weights.SECTOR_CATEGORY_WEIGHTS usage
sitescore.engines.location execution
sitescore.analyze / core analyze()
AnalysisInput construction
RevenueInput / financial inputs
LocationResult / Location Score
penalty multiplier execution
dealbreaker execution
Decision Layer execution
confidence execution based on category result
financial engine invocation
HTTP/API routes or framework
FastAPI / Flask / Django / Starlette
request/response transport models
auth/accounts
Stripe/payment/webhooks
report/PDF generation
email delivery
UI/frontend
queue/deployment
n8n
```

Importing `sitescore-core` in 4.1 is authorized only for the exact sector/subfeature-weight authorities specified in Section 4.

`SECTOR_CATEGORY_WEIGHTS` combines the four category scores into Location Score and therefore belongs to later core scoring, not 4.1.

---

# 11. COMB-005 / CURRENT PRODUCTION TRUTH

FAZ 4.1 must not fabricate a real production SCORE_READY path.

Current frozen truth remains:

```text
COMB-005: NOT_APPROVED
approved registry: ()
weights: ()
road_parking_access_score: unavailable / nonnumeric in current production truth
```

Therefore current real production evidence may remain `NOT_SCORE_READY` and category aggregation may remain blocked in the real-path regression.

For deterministic unit/adversarial testing of 4.1 math, a controlled test-only canonical SCORE_READY fixture may be used, following the existing app test technique, provided it does not change frozen production configuration or claim COMB-005 approval.

Test-only synthetic ready surfaces are evidence for aggregation mechanics, not evidence that empirical production readiness has been achieved.

---

# 12. MANDATORY TEST MATRIX

At minimum add/maintain tests proving all of the following.

## Authority / anti-forgery

```text
1. raw RealDataPipelineResult rejected
2. raw NormalizedLocationFeatures rejected
3. raw SectorKey / Sector cannot invoke category aggregation authority
4. manually allocated ApplicationScoringInput rejected
5. copied/reconstructed ApplicationScoringInput rejected
6. detached ready/status/fingerprint/feature arguments do not exist
7. manually allocated category-result shell rejected
8. copied/reconstructed category-result shell rejected
9. category result redirected to another scoring input -> rejected
10. category values mutated post-registration with object.__setattr__ -> rejected
11. nested scoring authority mutated after category aggregation -> category result no longer canonical
```

## Exact sector / frozen weight semantics

Use deliberately asymmetric feature values so swapped mappings cannot accidentally pass.

Prove exact expected demand and accessibility aggregation for all four sectors:

```text
coffee
restaurant
gym
beauty
```

Also prove:

```text
competition == competition_opportunity_score.value exactly
economics == household_income_score.value exactly
```

Unsupported `SectorKey` must fail closed.

## Missingness / no hidden repair

Prove no production code path performs:

```text
neutral 50 fill
zero fill
renormalization
partial-category scoring
feature substitution
```

Mutation of a previously canonical normalized feature toward missing/forged semantics must invalidate upstream app authority and block aggregation rather than being locally repaired.

## Core authority / checkpoint firewall

Tests/static architecture checks must establish:

```text
sitescore-app depends on sitescore-core==0.1.0
no upstream frozen package imports sitescore_app
no local app production copy of frozen subfeature weight tables
no SECTOR_CATEGORY_WEIGHTS usage
no CategoryScores construction
no core analyze() call
no AnalysisInput construction
no HTTP/payment/report/UI/n8n dependencies
```

## Production truth

Maintain a real-path regression showing current canonical production readiness remains blocked where COMB-005 remains unavailable; 4.1 must not turn that path SCORE_READY.

---

# 13. EXPECTED CHANGE SCOPE

Allowed production changes are downstream/additive under `sitescore-app`, expected to include only what is necessary, such as:

```text
sitescore-app/src/sitescore_app/gating.py and/or a narrowly scoped aggregation module
sitescore-app/src/sitescore_app/__init__.py
sitescore-app/pyproject.toml
sitescore-app/tests/...
sitescore-app/docs/CHECKPOINT_4_1_CATEGORY_AGGREGATION_AUTHORITY.md
```

A small root-level governance doc is acceptable if needed.

Do NOT modify production source under:

```text
sitescore-core/
sitescore-data/
sitescore-pipeline/
sitescore-benchmarks/
sitescore-metrics/
sitescore-spatial/
sitescore-providers/
```

The only authorized dependency metadata change is adding:

```text
sitescore-core==0.1.0
```

to `sitescore-app`.

If implementation appears to require a frozen upstream production change, STOP and report:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

Do not silently perform it.

---

# 14. FULL REGRESSION / ACTIONS REQUIREMENT

Before returning READY_FOR_REVIEW, validate all packages:

```text
sitescore-app
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Use GitHub Actions evidence Reviewer can independently inspect.

Report exact pass counts for every package and total.

If a temporary validation workflow is used, remove it before final review HEAD and report:

```text
validated SHA
final PR HEAD
exact validated SHA -> final HEAD comparison
```

Acceptable post-validation delta is normally only removal of the temporary workflow.

Any source/test/doc/dependency change after validation requires fresh validation or an exact re-reviewable validation chain.

---

# 15. IMPLEMENTER RETURN CONTRACT

When complete, update `implementer.md` with at least:

```text
CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.1
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: 67333dc0189e43cdca6347e9115a8426cac5ce19
CODE_BRANCH: faz4/4.1-category-aggregation-authority
CODE_HEAD_SHA: <exact>
PR: #N
CONTRACT_CHANGE_REQUIRED: 0
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
FAZ_4_1_IMPLEMENTATION_STATUS: IMPLEMENTED_READY_FOR_REVIEW
FAZ_4_2_IMPLEMENTATION_STATUS: NOT_STARTED
```

Also report:

- exact changed filenames;
- exact production-source changes;
- category-result authority design;
- exact sector resolution behavior;
- proof that frozen core weight maps are consumed directly;
- dependency metadata change (`sitescore-core==0.1.0`) and no other new deps;
- package version status;
- exact formulas tested for all four sectors;
- anti-forgery / object.__setattr__ regressions;
- COMB-005/current-production-truth verification;
- full Actions run/job IDs and conclusions;
- validated SHA -> final HEAD compare;
- firewall proof that 4.2+ work was not started.

Do NOT merge.
Do NOT self-LOCK.
Do NOT start FAZ 4.2.

STOP after Reviewer handoff.

---

# 16. REVIEWER ACCEPTANCE GATE

Reviewer will independently inspect actual PR metadata, base/head SHA, changed files, full patches, full changed source, relevant frozen core/data/app contracts, tests, dependency metadata, Actions jobs, docs, and validated-SHA integrity.

READY_TO_LOCK is possible only if Reviewer can truthfully conclude:

> FAZ 4.1 consumes only canonical factory-owned ApplicationScoringInput authority; resolves exactly the frozen core sector vocabulary; computes demand and accessibility directly from the frozen core subfeature-weight authorities without local copies, renormalization, substitution, or hidden neutralization; passes competition and economics through their exact normalized feature scores; binds the resulting four category values into factory-owned app authority resistant to forged/copied/post-registration mutation; adds only the authorized sitescore-app -> sitescore-core==0.1.0 dependency; preserves COMB-005 and all frozen upstream semantics; full regression is green; and FAZ 4.2+ remains not started.

Until then:

```text
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
FAZ_4_1_IMPLEMENTATION_STATUS: IMPLEMENTATION_REQUESTED
FAZ_4_2_IMPLEMENTATION_STATUS: NOT_STARTED
```

STOP.
