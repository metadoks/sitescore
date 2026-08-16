# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.2
CHECKPOINT_TITLE: Canonical Core Analysis Adapter

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: b003089ef9351f7ee5ec5d53e596da6f83db23d4
CODE_BRANCH: faz4/4.2-canonical-core-analysis-adapter
REVIEWED_HEAD_SHA: NONE
PR: NONE

CONTRACT_CHANGE_REQUIRED: 0
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
DEPENDENCY_CHANGE_AUTHORIZED: NONE — reuse existing sitescore-core==0.1.0 dependency

FAZ_3_STATUS: FROZEN
FAZ_4_0_STATUS: HISTORICALLY_LOCKED_MERGED
AUTHORITY_CORRECTIVE_REOPEN_STATUS: LOCKED_MERGED
FAZ_4_1_IMPLEMENTATION_STATUS: LOCKED_MERGED
FAZ_4_2_IMPLEMENTATION_STATUS: IMPLEMENTATION_REQUESTED
FAZ_4_3_IMPLEMENTATION_STATUS: NOT_STARTED
FAZ_4_4_IMPLEMENTATION_STATUS: NOT_STARTED

BLOCKERS: NONE
```

---

# 1. TRANSITION AUTHORITY / EXACT BASE

The user requested continuation after FAZ 4.1 was independently verified LOCKED / MERGED.

Reviewer independently re-fetched current `main` and verified:

```text
b003089ef9351f7ee5ec5d53e596da6f83db23d4
```

FAZ 4.2 is authorized to begin from exactly that base.

Historical truth remains:

```text
FAZ 3: FROZEN
FAZ 4.0: HISTORICALLY LOCKED / MERGED
Authority corrective reopen: USER-AUTHORIZED, RESOLVED, LOCKED / MERGED
FAZ 4.1: LOCKED / MERGED
FAZ 4.2: NOW AUTHORIZED
FAZ 4.3+: NOT STARTED
```

Do not rewrite or reopen earlier history. Any additive change to locked 4.1 app source is permitted only where this instruction explicitly authorizes a narrow downstream trusted-consumer bridge; 4.1 aggregation semantics themselves must not change.

---

# 2. CHECKPOINT OBJECTIVE

Implement exactly one new application capability:

```text
canonical ApplicationCategoryAggregationResult
+
explicit typed business / financial / confidence input values
-> exact frozen core CategoryScores
-> exact frozen core AnalysisInput
-> factory-owned application core-analysis-input authority
```

Recommended output authority name:

```text
ApplicationCoreAnalysisInput
```

Recommended public factory/validator shape:

```text
build_application_core_analysis_input(...)
    -> ApplicationCoreAnalysisInput

require_canonical_application_core_analysis_input(value)
    -> ApplicationCoreAnalysisInput
```

Equivalent naming is acceptable if authority semantics are preserved.

This checkpoint builds the canonical adapter input for later core execution.

It MUST NOT call the core analysis orchestrator.

---

# 3. CRITICAL CORE BOUNDARY — `analyze()` IS 4.3, NOT 4.2

Frozen `sitescore-core` `analyze(data: AnalysisInput)` is not a simple DTO converter or Location Score helper. It executes the complete canonical engine chain:

```text
Revenue Engine
-> Location Engine
-> Financial Engine
-> Decision Engine
-> Confidence Engine
-> Model Metadata
-> deterministic fingerprint
-> CanonicalAnalysisResult
```

Therefore FAZ 4.2 MUST NOT import for execution or invoke:

```text
sitescore.analyze
sitescore.analyze.analyze
calculate_revenue
calculate_location_score
calculate_financial_metrics
calculate_decision
calculate_confidence
generate_analysis_fingerprint
```

No `CanonicalAnalysisResult`, Location Score, revenue result, financial result, decision result, confidence result or analysis fingerprint may be produced in 4.2.

Those belong to FAZ 4.3 Application Analyze Use-Case Orchestration.

---

# 4. CANONICAL 4.1 CATEGORY AUTHORITY — TRUSTED CONSUMPTION REQUIRED

The only category-score authority accepted by 4.2 is the exact factory-owned canonical:

```text
ApplicationCategoryAggregationResult
```

from locked FAZ 4.1.

Do NOT accept detached category values or alternate category carriers as execution authority:

```text
demand=float
competition=float
accessibility=float
economics=float
CategoryScores supplied by caller
ReadyCategoryScorePayload supplied by caller
raw NormalizedLocationFeatures
raw ApplicationScoringInput
raw RealDataPipelineResult
Sector / SectorKey supplied independently
trusted=True
ready=True
force=True
hash/token/sentinel authority
```

## 4.1 Trusted binding consumption

The 4.1 category object has public mutable slots under the project adversarial model because `object.__setattr__` can bypass frozen dataclass syntax.

4.2 MUST NOT downgrade to this pattern:

```text
require_canonical_application_category_aggregation_result(value)
-> then trust/read mutable public value.demand/value.accessibility/... as authority
```

The adapter must consume the construction-time closure-bound 4.1 category authority values.

A narrowly additive internal bridge in `sitescore-app` is explicitly authorized if needed, for example an internal/non-exported resolver that:

1. requires the exact canonical 4.1 result;
2. verifies current public/nested integrity;
3. returns the trusted closure-bound exact sector and four construction-time category values;
4. does not grant authority from caller-supplied values;
5. is not exported through `sitescore_app.__all__` as a public authority shortcut.

Equivalent architecture is acceptable if it demonstrably uses construction-time trusted category values and preserves APP-H002 / APP-H002-R001 / FAZ 4.1 mutation defenses.

The locked category formulas and weights MUST NOT change.

---

# 5. FROZEN CORE TYPES — DIRECT CONSTRUCTION, NO LOCAL REIMPLEMENTATION

FAZ 4.2 must consume the actual frozen core types already available through the existing dependency:

```text
sitescore-core==0.1.0
```

At minimum the adapter may directly use:

```text
sitescore.config.sectors.Sector
sitescore.schemas.location.CategoryScores
sitescore.schemas.analysis.AnalysisInput
sitescore.schemas.revenue_inputs.CoffeeRevenueInput
sitescore.schemas.revenue_inputs.RestaurantRevenueInput
sitescore.schemas.revenue_inputs.GymRevenueInput
sitescore.schemas.revenue_inputs.BeautyRevenueInput
sitescore.config.quality_levels.GeographicLevel
sitescore.config.quality_levels.CoverageLevel
sitescore.config.quality_levels.InputQuality
```

Do not copy/redeclare these enums, DTOs, validation tables or sector/revenue compatibility rules in app production code.

`sitescore-app` already depends on `sitescore-core==0.1.0`; no new runtime dependency is authorized or required.

Package version remains:

```text
sitescore-app==0.1.0
```

---

# 6. EXACT CATEGORY ADAPTATION

Construct an actual frozen core `CategoryScores` from the trusted closure-bound 4.1 values only:

```text
CategoryScores(
    demand=<trusted bound demand>,
    competition=<trusted bound competition>,
    accessibility=<trusted bound accessibility>,
    economics=<trusted bound economics>,
)
```

This checkpoint is explicitly authorized to construct core `CategoryScores`.

It is NOT authorized to use:

```text
SECTOR_CATEGORY_WEIGHTS
```

because those weights are consumed by the core Location Engine during later `analyze()` execution.

Do not recompute categories in 4.2. Do not re-read normalized features to produce category values. The canonical input is the 4.1 category authority.

---

# 7. EXPLICIT BUSINESS / FINANCIAL / CONFIDENCE INPUT CONTRACT

The core `AnalysisInput` also requires non-category inputs that are not currently canonical outputs of the location pipeline.

FAZ 4.2 must accept these as explicit typed adapter inputs; it must NOT invent or infer them from unrelated location evidence.

Expected adapter inputs, in addition to the canonical category result, are:

```text
revenue_input:
  CoffeeRevenueInput |
  RestaurantRevenueInput |
  GymRevenueInput |
  BeautyRevenueInput

monthly_rent: float
fixed_labor: float
fixed_overhead: float

geographic_level: GeographicLevel
data_age_years: int | None

data_coverage: dict[str, CoverageLevel]
input_qualities: dict[str, InputQuality]
```

The exact API may use keyword-only arguments.

## 7.1 No invented semantics

Do NOT derive or guess:

```text
revenue_input
monthly rent
labor
fixed overhead
geographic level
data age
category coverage levels
input quality levels
```

from normalized location features, source metadata, sector defaults, heuristics, environment variables or hidden constants unless a separately frozen canonical policy already exists and is explicitly authorized. No such new policy is authorized in 4.2.

Do not create default revenue assumptions or default costs.

## 7.2 Core remains validation authority

Use the actual core constructors so frozen core remains authoritative for:

```text
sector <-> revenue input type compatibility
revenue input field bounds/order rules
non-negative cost rules
GeographicLevel typing
data-age validity
allowed coverage keys and CoverageLevel typing
allowed input-quality keys and InputQuality typing
```

Do not duplicate those business validation rules into a second app-owned table.

Do not silently add omitted coverage/quality keys; preserve the explicit caller mapping and let frozen core semantics govern missing entries later.

---

# 8. EXACT `AnalysisInput` CONSTRUCTION

Construct one actual frozen core `AnalysisInput` with:

```text
sector = trusted bound frozen core Sector from canonical 4.1 result
category_scores = newly constructed exact core CategoryScores
revenue_input = explicit typed revenue input
monthly_rent = explicit input
fixed_labor = explicit input
fixed_overhead = explicit input
geographic_level = explicit GeographicLevel
data_age_years = explicit int|None
data_coverage = adapter-owned copy of explicit mapping
input_qualities = adapter-owned copy of explicit mapping
```

The adapter should copy the caller-provided mutable dictionaries before constructing the core input so later mutation of the caller's original dictionaries cannot retroactively alter the canonical adapter object.

Do not mutate the caller dictionaries.

Do not call `analyze()` after construction.

---

# 9. FACTORY-OWNED APPLICATION CORE-INPUT AUTHORITY

A raw/caller-created core `AnalysisInput`, even if structurally valid, is NOT the application execution authority for 4.3.

The 4.2 factory must wrap/bind the exact core input in factory-owned app authority.

Recommended authority:

```text
ApplicationCoreAnalysisInput
```

The result should be constructor-blocked / factory-owned using the established closure-private pattern.

Construction-time binding must include at least:

```text
exact canonical ApplicationCategoryAggregationResult
trusted bound category sector
trusted bound demand/competition/accessibility/economics
exact constructed core CategoryScores object
exact typed revenue_input object and its construction-time semantic record
monthly_rent
fixed_labor
fixed_overhead
geographic_level
data_age_years
exact adapter-owned data_coverage dict + construction-time semantic contents
exact adapter-owned input_qualities dict + construction-time semantic contents
exact constructed core AnalysisInput object
construction-time recursive semantic record of the complete AnalysisInput authority surface
```

A recursive semantic record may be used, following the already accepted corrective authority model, provided it deterministically covers nested dataclasses/enums/dicts and fails closed for unsupported authority-bearing types.

---

# 10. MUTABILITY / INTEGRITY REQUIREMENTS

Frozen dataclass syntax is not sufficient authority under the project threat model.

`AnalysisInput` contains mutable dictionaries, and frozen core dataclasses can still be altered by direct `object.__setattr__` in adversarial tests.

Canonical 4.2 validation must therefore detect and reject at least:

```text
ApplicationCoreAnalysisInput redirected to another AnalysisInput
core AnalysisInput.sector mutation
core AnalysisInput.category_scores replacement
CategoryScores demand/competition/accessibility/economics mutation
core AnalysisInput.revenue_input replacement
revenue_input field mutation
monthly_rent mutation
fixed_labor mutation
fixed_overhead mutation
geographic_level mutation
data_age_years mutation
data_coverage mapping mutation
input_qualities mapping mutation
nested canonical 4.1 category authority mutation after 4.2 creation
```

Downstream 4.3 must be able to consume a trusted construction-time core-input binding, not merely:

```text
require_canonical_application_core_analysis_input(value)
-> later read mutable public value.analysis_input without integrity resolution
```

Prefer resolver-backed public properties and/or an internal trusted resolver for future 4.3 consumption.

No module-global mutable registry/token/hash may act as sole authority.

---

# 11. RAW CORE INPUT IS NOT APP AUTHORITY

Tests and public API must establish:

```text
valid caller-created AnalysisInput != ApplicationCoreAnalysisInput authority
```

A valid raw core `AnalysisInput` may be a useful core DTO, but 4.3 must later accept only the exact factory-owned app adapter authority produced from canonical 4.1 categories plus explicit adapter inputs.

Do not add a factory parameter that allows a caller to inject a prebuilt `AnalysisInput` and thereby bypass category authority.

---

# 12. `ReadyCategoryScorePayload` REMAINS NON-AUTHORITATIVE

Do not use caller-constructible `ReadyCategoryScorePayload` as the source of category authority.

Its shape remains a data DTO for already-computed values, not proof of 4.1 execution origin.

No frozen `sitescore-data` modification is authorized.

---

# 13. STRICT FAZ 4.3+ FIREWALL

FAZ 4.2 must stop after creating and integrity-binding the canonical core `AnalysisInput` adapter authority.

Explicitly forbidden in production execution during 4.2:

```text
core analyze()
Revenue Engine execution
Location Engine execution
SECTOR_CATEGORY_WEIGHTS usage by app
Financial Engine execution
Decision Engine execution
Confidence Engine execution
analysis fingerprint generation
CanonicalAnalysisResult construction
LocationResult construction
FinancialResult construction
DecisionResult construction
ConfidenceResult construction
application analyze use-case orchestration
HTTP/API routes/frameworks
request/response transport schemas
auth/accounts
Stripe/payment/webhooks
report/PDF generation
email delivery
UI/frontend
queue/deployment
n8n
```

FAZ 4.3 remains NOT_STARTED.
FAZ 4.4 remains NOT_STARTED.

---

# 14. COMB-005 / PRODUCTION TRUTH FIREWALL

FAZ 4.2 must not create a production SCORE_READY path or approve COMB-005.

Frozen truth remains:

```text
COMB-005: NOT_APPROVED
approved registry: ()
weights: ()
composition_method: UNRESOLVED
production road_parking_access_score: unavailable / non-authoritative
```

Current real production path may therefore remain blocked before 4.1/4.2.

Controlled test-only canonical SCORE_READY/category authority may be used to test adapter mechanics, but it is not evidence of production readiness or empirical calibration.

---

# 15. MANDATORY TEST MATRIX

At minimum add/maintain tests proving all of the following.

## 15.1 Canonical category authority / anti-forgery

```text
1. manual/caller-created ApplicationCategoryAggregationResult rejected
2. copy-equivalent category result rejected
3. category value object.__setattr__ mutation before adapter -> rejected
4. nested scoring/category authority mutation before adapter -> rejected
5. detached category floats do not exist in adapter signature
6. caller-supplied CategoryScores does not exist in adapter signature
7. caller-supplied AnalysisInput does not exist in adapter signature
```

## 15.2 Exact core adaptation

For controlled canonical category results, prove:

```text
8. exact frozen Sector is preserved
9. exact trusted four category values become actual core CategoryScores
10. competition/economics are not recomputed or transformed
11. correct sector RevenueInput type is accepted
12. wrong sector RevenueInput type fails through frozen core authority
13. negative/invalid core business inputs fail through frozen core constructors
14. actual GeographicLevel / CoverageLevel / InputQuality types are used
```

Use all four sectors for sector/revenue compatibility coverage where practical.

## 15.3 Caller mapping isolation

```text
15. mutate original caller data_coverage dict after factory return -> canonical adapter unaffected
16. mutate original caller input_qualities dict after factory return -> canonical adapter unaffected
```

because the adapter owns copies.

## 15.4 Post-registration core-input integrity

Direct adversarial mutation must invalidate canonical 4.2 authority:

```text
17. wrapper redirected to another AnalysisInput
18. AnalysisInput.sector changed
19. AnalysisInput.category_scores replaced
20. CategoryScores.demand changed
21. CategoryScores.competition changed
22. CategoryScores.accessibility changed
23. CategoryScores.economics changed
24. AnalysisInput.revenue_input replaced
25. nested revenue-input field changed
26. monthly_rent changed
27. fixed_labor changed
28. fixed_overhead changed
29. geographic_level changed
30. data_age_years changed
31. adapter-owned data_coverage dict changed
32. adapter-owned input_qualities dict changed
33. nested canonical 4.1 category result changed after 4.2 creation
```

All must fail closed under canonical validator/trusted resolver.

## 15.5 Manual/copy wrapper authority

```text
34. manually allocated ApplicationCoreAnalysisInput rejected
35. copy/reconstructed ApplicationCoreAnalysisInput rejected
36. raw valid core AnalysisInput is not accepted as app canonical authority
```

## 15.6 4.3+ firewall

Static/source tests must prove 4.2 production code does not invoke/import-for-execution:

```text
analyze()
calculate_revenue
calculate_location_score
calculate_financial_metrics
calculate_decision
calculate_confidence
generate_analysis_fingerprint
SECTOR_CATEGORY_WEIGHTS
FastAPI/Flask/Django/Starlette
Stripe
report/PDF libs
queue/n8n
```

## 15.7 Dependency/version/frozen packages

```text
sitescore-app version == 0.1.0
sitescore-app dependencies unchanged:
  sitescore-data==0.1.0
  sitescore-pipeline==0.1.0
  sitescore-core==0.1.0
no new runtime dependencies
no frozen upstream production package changes
no upstream package imports sitescore_app
```

## 15.8 Production truth

Maintain a real-path regression demonstrating 4.2 does not bypass current NOT_SCORE_READY / COMB-005 production truth.

---

# 16. EXPECTED CHANGE SCOPE

Allowed changes are downstream/additive under `sitescore-app`, expected to include only what is necessary, such as:

```text
sitescore-app/src/sitescore_app/core_adapter.py
sitescore-app/src/sitescore_app/aggregation.py
  ONLY a narrow additive trusted-binding resolver/consumer bridge if required
sitescore-app/src/sitescore_app/__init__.py
sitescore-app/tests/...
sitescore-app/docs/CHECKPOINT_4_2_CANONICAL_CORE_ANALYSIS_ADAPTER.md
```

`sitescore-app/pyproject.toml` should normally remain unchanged because the required core dependency already exists.

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

Do NOT change the locked 4.1 category formulas, sector mapping or weight semantics.

If implementation appears to require a frozen upstream contract/source change, STOP and report:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

Do not silently perform it.

---

# 17. FULL REGRESSION / ACTIONS REQUIREMENT

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

Any production source/test/doc/dependency change after successful validation requires fresh validation or an exact re-reviewable validation chain.

---

# 18. IMPLEMENTER RETURN CONTRACT

When complete, update `implementer.md` with at least:

```text
CURRENT_PHASE: FAZ 4
CURRENT_CHECKPOINT: 4.2
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: b003089ef9351f7ee5ec5d53e596da6f83db23d4
CODE_BRANCH: faz4/4.2-canonical-core-analysis-adapter
CODE_HEAD_SHA: <exact>
PR: #N
CONTRACT_CHANGE_REQUIRED: 0
VERSION_CHANGE_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
FAZ_4_1_IMPLEMENTATION_STATUS: LOCKED_MERGED
FAZ_4_2_IMPLEMENTATION_STATUS: IMPLEMENTED_READY_FOR_REVIEW
FAZ_4_3_IMPLEMENTATION_STATUS: NOT_STARTED
```

Also report:

- exact changed filenames;
- exact production-source changes;
- trusted 4.1 category-consumption design;
- exact core `CategoryScores` construction path;
- exact core `AnalysisInput` construction path;
- explicit adapter input signature;
- proof no business/confidence defaults or inferred mappings were invented;
- mapping-copy/isolation behavior;
- factory-owned 4.2 authority design and construction-time semantic binding;
- direct `object.__setattr__` and dict-mutation adversarial regressions;
- proof raw core `AnalysisInput` is not app authority;
- package version/dependency status;
- COMB-005/current-production-truth verification;
- full Actions run/job IDs and conclusions;
- validated SHA -> final HEAD compare;
- firewall proof that `analyze()` / FAZ 4.3+ did not start.

Do NOT merge.
Do NOT self-LOCK.
Do NOT start FAZ 4.3.

STOP after Reviewer handoff.

---

# 19. REVIEWER ACCEPTANCE GATE

READY_TO_LOCK is possible only if Reviewer can truthfully conclude:

> FAZ 4.2 consumes only the canonical factory-owned FAZ 4.1 category authority through construction-time trusted bindings; constructs actual frozen core CategoryScores and AnalysisInput without recomputing categories or inventing business/confidence semantics; accepts explicit typed revenue/cost/geographic/vintage/coverage/quality inputs; isolates caller-owned mutable mappings; binds the complete core AnalysisInput authority surface against post-registration object/dict mutation; exposes only factory-owned app core-input authority for future 4.3; preserves package versions, dependencies, COMB-005 and all frozen upstream semantics; full regression is green; and does not call core analyze() or start FAZ 4.3+.

Until then:

```text
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
FAZ_4_2_IMPLEMENTATION_STATUS: IMPLEMENTATION_REQUESTED
FAZ_4_3_IMPLEMENTATION_STATUS: NOT_STARTED
```

STOP.