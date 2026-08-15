# FAZ 3.4 — Checkpoint 3.4-7

## COMB-005 Road + Parking Composite Gating Foundation

Status: implementation + authority hardening complete, **not LOCKED**.

Base: `8bfe2eb92ea3d52f30d14a4333927f76f8630b0a`

## Purpose

Checkpoint 3.4-7 owns only the structural COMB-005 foundation for the frozen downstream feature `road_parking_access_score`.

Frozen invariant:

- road and parking remain separate real-world evidence/metrics;
- no approved empirical COMB-005 weight set exists;
- no production road/parking component-normalization authority exists yet;
- canonical production COMB-005 is therefore unavailable;
- missing/unknown/unresolved/uncalibrated/incompatible evidence is never substituted with `0`, `50`, the other side, or renormalized weights.

## Frozen component semantics

Required component identities remain distinct:

- `road_reachable_area_km2`
- `parking_public_offstreet_capacity`
- `parking_legal_curb_length_m`

No downstream feature slots named `road_access_score`, `parking_access_score`, or `curb_access_score` are introduced.

### Production-facing prerequisite declaration

`RoadParkingComponentArtifact` is only a production prerequisite **status/lineage declaration**. It binds:

- component kind;
- exact frozen metric key;
- normalization lineage identifier;
- explicit non-AVAILABLE component state.

Because no canonical approved road/parking component-normalization path exists, the public production constructor **rejects `AVAILABLE`** and rejects every detached numeric component score.

Therefore ordinary production callers cannot fabricate a canonical AVAILABLE road/parking prerequisite from arbitrary `score + lineage` input.

Controlled AVAILABLE component fixtures used to exercise hypothetical future composition math exist only inside tests; they are not production symbols and are not accepted by the canonical production executor.

## Production policy authority

`RoadParkingCompositePolicy` remains a typed production policy declaration, but it is **not caller approval authority**.

It binds:

- policy id/version;
- approval state;
- exact required component semantics;
- weights/composition parameters;
- missing-side behavior;
- output feature/unit.

Current canonical V1 declaration:

- id: `comb005-road-parking`
- version: `UNAPPROVED_V1`
- approval: `NOT_APPROVED`
- weights: `()`
- composition method: `UNRESOLVED`
- missing behavior: `REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION`
- output feature: `road_parking_access_score`
- unit: `score_0_100`

Production approved registry:

`APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 = ()`

### COMB-H001 hardening

The public production constructor now rejects any caller-created policy with `approval_state=APPROVED`.

It also rejects any non-empty weight vector and any executable composition method while the policy is unapproved.

Therefore:

- a detached caller `policy_version` is not approval authority;
- `approved=True` does not exist in canonical execution;
- arbitrary caller weights cannot be represented as an approved production policy;
- there is no production-looking default or hidden weight set.

Any future empirical approval requires a separately frozen canonical authority/registry contract; it cannot be created by ordinary constructor input in 3.4-7.

## Final result construction authority

`RoadParkingCompositeResult` is now a derived production result object whose constructor accepts only:

- actual production `RoadParkingCompositePolicy` declaration;
- actual production `RoadParkingComponentArtifact` declarations.

The constructor no longer accepts caller-supplied:

- `state`;
- `reason_codes`;
- `score`.

These values are derived properties.

Current canonical production policy is unapproved, so production result semantics are constructively fixed to:

- state: `POLICY_NOT_APPROVED`
- reason: `comb005_policy_not_approved`
- score: `None`

### COMB-H002 hardening

Public API cannot directly self-assert an AVAILABLE final artifact because:

1. production policy constructor cannot manufacture `APPROVED`;
2. production component constructor cannot manufacture `AVAILABLE` or carry detached numeric component scores;
3. production result constructor has no state/score assertion fields;
4. canonical `evaluate_road_parking_composite()` accepts only production component declarations and always derives result from `COMB005_V1_POLICY`;
5. no approved production registry entry exists.

Missing, duplicate, unresolved or otherwise nonavailable component sets therefore cannot become AVAILABLE through any public production constructor/factory path.

## Canonical execution API

Canonical API:

`evaluate_road_parking_composite(components=())`

It accepts no caller-supplied:

- policy;
- weights;
- approval flag/state;
- result state;
- detached final score.

Current output is deterministically `POLICY_NOT_APPROVED` with `score=None`.

## Controlled composition tests are test-local only

The original production `_compose_with_policy` synthetic path was removed during authority hardening.

Hypothetical weighted composition math is now exercised only by private classes/helpers defined inside the test module. These test-local fixtures:

- are not exported package symbols;
- are not present in production source;
- cannot enter canonical production execution;
- require all three components;
- enforce no substitution/renormalization;
- use exact synthetic weight sum `1.0`;
- never clamp invalid output.

Their only purpose is to retain structural/adversarial verification without creating production approval authority.

## Typed states

Composite states remain:

- `POLICY_NOT_APPROVED`
- `INPUT_NOT_AVAILABLE`
- `INPUT_NOT_ELIGIBLE`
- `INPUT_NOT_CALIBRATED`
- `INPUT_INCOMPATIBLE`
- `AVAILABLE`

Component states remain:

- `AVAILABLE`
- `UNAVAILABLE`
- `UNRESOLVED`
- `INCOMPATIBLE`
- `INELIGIBLE`
- `UNCALIBRATED`

`AVAILABLE` values remain part of the structural vocabulary for a future separately approved policy/component authority, but current public production constructors cannot self-assert those states as canonical authority.

## No substitution / no invented weights

Explicitly absent:

- 50/50 default;
- any production road/parking weight vector;
- road-only composite;
- parking-only composite;
- missing-side neutral 50;
- missing-side zero;
- copy available side;
- weight renormalization;
- hidden fallback weights;
- nonlinear transform;
- clamping;
- rounding/quantization/smoothing.

## Road unresolved state

Checkpoint 3.4-7 does not alter `road_reachable_area_km2` semantics. No arbitrary contour selection, contour average, max/min, area sum, or fixed multi-scale reduction is introduced.

Canonical road contribution remains unavailable until a separately approved reduction/normalization contract exists.

## Parking distinctions

`parking_public_offstreet_capacity` and `parking_legal_curb_length_m` remain different metric identities/components.

This checkpoint does not infer:

- polygon area -> capacity;
- unknown capacity -> zero;
- curb length -> parking-space count;
- private/customer-only parking -> public parking;
- any scalar parking reduction.

## Locked 3.4-6 compatibility

`FEATURE_NORMALIZATION_POLICIES_V1` remains unchanged.

No direct normalization policy exists for:

- `road_reachable_area_km2`
- `parking_public_offstreet_capacity`
- `parking_legal_curb_length_m`

`feature_normalization_policy()` continues to reject those metrics as direct V1 normalized features.

## Identity / lineage

Production policy identity binds:

- policy id/version;
- NOT_APPROVED state;
- exact required component kinds/metric keys;
- empty weight vector;
- unresolved composition method;
- no-substitution behavior;
- output feature/unit.

Production component identity binds:

- component kind;
- exact metric key;
- normalization lineage id;
- explicit non-AVAILABLE state;
- `score=None`.

Production result identity binds:

- actual policy identity/approval state;
- component identities canonicalized by component kind;
- output feature/unit;
- derived state/reasons;
- `score=None`.

Caller component ordering is nonsemantic. Changing component lineage changes result identity.

Test-local controlled fixtures separately verify that hypothetical policy-weight changes would alter synthetic policy/result identity without exposing those weights as production authority.

## Architecture boundary

Implementation remains additive in `sitescore-benchmarks`.

No dependency metadata changed. Existing direct runtime dependencies remain:

- `sitescore-spatial==0.1.0`
- `sitescore-metrics==0.1.0`

No direct `sitescore-core`, `sitescore-data`, `sitescore-providers`, or pipeline dependency was added.

`CONTRACT_CHANGE_REQUIRED = 0`.

## Adversarial regression matrix

Original COMB-001..015 coverage is retained, adapted so synthetic approved/AVAILABLE fixtures are test-local only.

Authority hardening additionally proves:

- COMB-H001: exported production policy constructor rejects arbitrary caller-created `APPROVED` policies/weights while approved registry is empty;
- COMB-H002: exported production component constructor rejects detached AVAILABLE component scores;
- COMB-H002: exported production result constructor exposes only `policy, components` and has no caller `state/reason_codes/score` fields;
- COMB-H002: direct AVAILABLE final result assertion is impossible through public result construction;
- COMB-H002: missing/duplicate/nonavailable production component sets never yield AVAILABLE;
- locked 3.4-6 still rejects direct road/parking normalization;
- component caller ordering remains nonsemantic for production result identity.

## Hardening validation

Source/test hardening validation:

- workflow: `cp347-hardening-validation`
- run: `31907113612`
- validated SHA: `5cf8f26481a2489dc0e335744cb965fd9b26949a`
- conclusion: SUCCESS

Exact summaries visibly emitted:

- `sitescore-benchmarks`: `191 passed`
- `sitescore-metrics`: `67 passed`

The same job successfully completed:

- `sitescore-spatial`
- `sitescore-providers`
- `sitescore-data`
- `sitescore-core`

A documentation-inclusive validation is required after this document update. The temporary hardening workflow must then be removed and the successful validated SHA compared to final review HEAD.

## Explicitly out of scope

Not implemented:

- approved empirical COMB-005 weights;
- production road scalar reduction;
- production parking scalar reduction;
- approved road/parking component-normalization artifacts;
- complete `NormalizedLocationFeatures` assembly;
- `ScoringReadiness`;
- `RealDataPipelineResult` orchestration;
- CategoryScores;
- Location Score;
- `core.analyze()`;
- checkpoint 3.4-8 implementation.
