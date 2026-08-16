# FAZ 4.1 — Category Aggregation Authority

## Status

This checkpoint implements only the application-layer category aggregation boundary authorized by the Reviewer.

```text
BASE_SHA: 67333dc0189e43cdca6347e9115a8426cac5ce19
CHECKPOINT: FAZ 4.1
FAZ 3: FROZEN
FAZ 4.0: HISTORICALLY LOCKED / MERGED
AUTHORITY CORRECTIVE REOPEN: LOCKED / MERGED
FAZ 4.2+: NOT STARTED
```

## Canonical execution path

Production category aggregation accepts only the exact factory-owned canonical:

```text
ApplicationScoringInput
```

The application aggregation module uses the existing resolver-backed scoring-input properties. Each property access revalidates the already locked application/pipeline authority chain. The aggregation path validates the scoring capability before computation and again after computation before granting a new downstream authority object.

No detached sector, normalized-feature object, readiness flag/fingerprint, category value, or weight vector can grant category aggregation authority.

## Frozen core authority

FAZ 4.1 adds exactly one authorized runtime dependency:

```text
sitescore-app -> sitescore-core==0.1.0
```

The application package version remains:

```text
sitescore-app==0.1.0
```

The implementation closure-captures the actual frozen core authorities directly:

```text
sitescore.config.sectors.Sector
sitescore.config.subfeature_weights.DEMAND_SUBFEATURE_WEIGHTS
sitescore.config.subfeature_weights.ACCESSIBILITY_SUBFEATURE_WEIGHTS
```

No local production copy, override, environment configuration, alternate weight table, or missing-value renormalization is introduced.

## Exact sector resolution

The data-layer `SectorKey` remains opaque. FAZ 4.1 resolves its exact bound `.value` through the frozen core `Sector` enum.

Only these values are accepted:

```text
coffee
restaurant
gym
beauty
```

Unsupported values fail closed. There is no default sector, aliasing, case repair, fuzzy matching, feature-based inference, or neutral-sector behavior.

## Exact category formulas

Demand is the frozen core sector-specific weighted sum of:

```text
walkable_population_score
target_population_density_score
age_target_concentration_score
```

Competition is exactly:

```text
competition_opportunity_score.value
```

Accessibility is the frozen core sector-specific weighted sum of:

```text
walkable_reach_area_score
transit_access_score
road_parking_access_score
```

Economics is exactly:

```text
household_income_score.value
```

All required normalized inputs must already be numeric `score_0_100` values. Missing values fail closed. FAZ 4.1 does not create zero fill, neutral 50 fill, partial scoring, feature substitution, mean fill, or weight renormalization. The frozen age neutral fallback remains an upstream-only policy and is merely consumed if it already passed readiness.

No presentation rounding is applied.

## Factory-owned category result

`ApplicationCategoryAggregationResult` is constructor-blocked and factory-owned.

Canonical binding is held in closure-private state and includes:

```text
exact canonical ApplicationScoringInput
resolved frozen core Sector
exact normalized-feature object used for computation
readiness fingerprint
demand
competition
accessibility
economics
```

`require_canonical_application_category_aggregation_result(...)` requires:

```text
factory registration identity
+ result-field integrity
+ exact nested ApplicationScoringInput still canonical
+ exact normalized-feature identity still bound
+ readiness fingerprint still bound
+ frozen sector resolution still identical
```

Direct post-registration `object.__setattr__` mutation of a category value or nested authority invalidates canonicality. Manually allocated and copy-equivalent result shells do not inherit authority.

## COMB-005 / current production truth

This checkpoint does not modify road/parking approval or calibration state.

```text
COMB-005: NOT_APPROVED
approved registry: ()
weights: ()
composition_method: UNRESOLVED
production composite score: None
```

Controlled SCORE_READY fixtures exist only in tests to prove deterministic category mechanics. They do not create a production SCORE_READY path or empirical approval.

## 4.2+ firewall

FAZ 4.1 does not construct or invoke:

```text
sitescore.schemas.location.CategoryScores
SECTOR_CATEGORY_WEIGHTS
AnalysisInput
core analyze()
Location Score
penalty/dealbreaker execution
Decision Layer
financial engine
HTTP/API transport
auth/payment
report/PDF
UI
queue/deployment
n8n
```

Future FAZ 4.2 must consume only the canonical application category aggregation authority rather than four detached caller-supplied floats.
