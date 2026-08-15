# FAZ 3.4 — Checkpoint 3.4-7

## COMB-005 Road + Parking Composite Gating Foundation

Status: implementation complete, **not LOCKED**.

Base: `8bfe2eb92ea3d52f30d14a4333927f76f8630b0a`

## Purpose

Checkpoint 3.4-7 owns only the structural COMB-005 foundation for the frozen downstream feature:

`road_parking_access_score`

The frozen invariant is preserved:

- road and parking remain separate real-world metrics/evidence;
- no approved empirical COMB-005 weight set currently exists;
- therefore canonical production COMB-005 is unavailable and cannot emit a numeric score;
- missing, unknown, unresolved, uncalibrated or incompatible components are never substituted with `0`, `50`, the other side, or renormalized weights.

## Frozen component semantics

The structural component family keeps three distinct metric identities:

- `road_reachable_area_km2`
- `parking_public_offstreet_capacity`
- `parking_legal_curb_length_m`

No public downstream feature slots named `road_access_score`, `parking_access_score`, or `curb_access_score` are introduced.

`RoadParkingComponentArtifact` is an internal prerequisite/lineage artifact, not a new downstream feature. It binds:

- component kind;
- exact frozen metric key;
- normalization lineage identity;
- explicit component state;
- optional normalized score only when state is `AVAILABLE`.

An available component score must be finite and within `[0,100]`. Every non-available component state requires `score=None`.

Current production road and parking normalization/reduction approvals remain unresolved. The component artifact does not make those reductions canonical.

## Policy contract

`RoadParkingCompositePolicy` binds:

- policy id;
- policy version;
- approval state;
- required component semantics;
- weights/composition parameters;
- composition method;
- missing-side behavior;
- output feature key;
- output unit.

Required missing-side behavior is exactly:

`REQUIRE_ALL_COMPONENTS_NO_SUBSTITUTION`

Canonical V1 policy declaration:

- id: `comb005-road-parking`
- version: `UNAPPROVED_V1`
- approval: `NOT_APPROVED`
- weights: empty
- composition method: `UNRESOLVED`
- output feature: `road_parking_access_score`
- unit: `score_0_100`

Production approved registry:

`APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 = ()`

Therefore no canonical production weight vector exists.

## Canonical execution authority

Canonical API:

`evaluate_road_parking_composite(components=())`

It accepts no caller-supplied:

- policy;
- weights;
- approval flag;
- detached score.

It always derives authority from the canonical V1 policy declaration. Because that declaration is not approved, current production execution returns:

- state: `POLICY_NOT_APPROVED`
- score: `None`
- reason: `comb005_policy_not_approved`

Candidate component availability cannot override policy approval.

## Controlled noncanonical fixture path

A private `_compose_with_policy` helper exists only to test structural gating and identity behavior with deliberately noncanonical approved fixtures. Such fixtures:

- are absent from the canonical registry;
- cannot be supplied to the canonical production API;
- require all three distinct components;
- use `WEIGHTED_LINEAR_SUM_NO_SUBSTITUTION` only for controlled tests;
- require explicit weights for every component;
- require exact weight sum `1.0`;
- never renormalize when any component is missing/unavailable;
- never clamp invalid output.

These fixture weights are not production policy.

## Typed states

Composite states:

- `POLICY_NOT_APPROVED`
- `INPUT_NOT_AVAILABLE`
- `INPUT_NOT_ELIGIBLE`
- `INPUT_NOT_CALIBRATED`
- `INPUT_INCOMPATIBLE`
- `AVAILABLE`

Component states:

- `AVAILABLE`
- `UNAVAILABLE`
- `UNRESOLVED`
- `INCOMPATIBLE`
- `INELIGIBLE`
- `UNCALIBRATED`

Unavailable/gated composite results always carry `score=None`.

## No substitution / no invented weights

Explicitly absent:

- 50/50 default;
- any production road/parking weights;
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

Canonical road contribution may therefore remain unavailable until its own approved reduction/normalization policy exists.

## Parking distinctions

`parking_public_offstreet_capacity` and `parking_legal_curb_length_m` remain different components and different metric identities.

This checkpoint does not infer:

- capacity from polygon area;
- unknown capacity as zero;
- curb length as parking-space count;
- private/customer-only parking as public parking;
- a scalar parking reduction.

## 3.4-6 compatibility

Locked 3.4-6 direct feature normalization remains unchanged.

No direct policy was added to `FEATURE_NORMALIZATION_POLICIES_V1` for:

- `road_reachable_area_km2`
- `parking_public_offstreet_capacity`
- `parking_legal_curb_length_m`

`feature_normalization_policy()` continues to reject these metrics as direct V1 normalized features.

## Output semantics

The only final target is:

- feature: `road_parking_access_score`
- unit: `score_0_100`

If an approved future policy and all required valid components exist, any available controlled result must be finite and within `[0,100]`. Invalid math is rejected; it is not clamped.

Current canonical result remains unavailable.

## Identity / lineage

Policy identity binds policy id/version, approval state, exact required metric semantics, weights, composition method, missing behavior, output feature and unit.

Component identity binds component kind, exact metric key, normalization lineage, state and score.

Result identity binds:

- actual policy identity;
- policy approval state;
- component identities in canonical kind order;
- output feature key/unit;
- state;
- reason codes;
- score when available.

Changing policy weights in controlled fixtures changes policy/result identity. Changing component lineage changes result identity. Caller component ordering does not change semantic result identity.

## Architecture boundary

Implementation remains additive in `sitescore-benchmarks`.

No dependency metadata changed. Existing direct runtime dependencies remain:

- `sitescore-spatial==0.1.0`
- `sitescore-metrics==0.1.0`

No direct `sitescore-core`, `sitescore-data`, `sitescore-providers`, or pipeline dependency was added.

`CONTRACT_CHANGE_REQUIRED = 0`.

## Adversarial regression matrix

Implemented coverage includes:

- COMB-001 no approved policy -> no score;
- COMB-002 no implicit 50/50 / no canonical approved weights;
- COMB-003 road-only substitution forbidden;
- COMB-004 parking-only substitution forbidden;
- COMB-005 no missing-side neutral;
- COMB-006 no renormalization;
- COMB-007 unresolved road remains unavailable;
- COMB-008 parking capacity and curb length remain distinct;
- COMB-009 no downstream component feature-slot invention;
- COMB-010 canonical API has no self-authorization parameters;
- COMB-011 result identity changes with controlled policy weights;
- COMB-012 result identity changes with component lineage;
- COMB-013 controlled available result remains within bounds without clamping;
- COMB-014 no later-scope leakage;
- COMB-015 canonical production remains unavailable after generic helpers exist.

Additional regressions verify nonavailable component states cannot carry scores, component ordering is nonsemantic, and locked 3.4-6 continues rejecting direct road/parking normalization.

## Validation

Initial full checkpoint-wide GitHub Actions validation:

- workflow: `cp347-validation`
- run: `31906632814`
- validated SHA: `8001c1dc2dc2279ac6207ce6b679cbc0fc837db8`
- conclusion: SUCCESS

Exact summaries visibly emitted:

- `sitescore-benchmarks`: `187 passed`
- `sitescore-metrics`: `67 passed`

The same job successfully completed:

- `sitescore-spatial`
- `sitescore-providers`
- `sitescore-data`
- `sitescore-core`

Exact counts are not claimed here for suites whose summary count was not explicitly captured.

A final documentation-inclusive validation is required before review handoff. The temporary workflow must then be removed and final review HEAD compared against the successful validated SHA.

## Explicitly out of scope

Not implemented:

- approved empirical COMB-005 weights;
- production road scalar reduction;
- production parking scalar reduction;
- complete `NormalizedLocationFeatures` assembly;
- `ScoringReadiness`;
- `RealDataPipelineResult` orchestration;
- CategoryScores;
- Location Score;
- `core.analyze()`;
- checkpoint 3.4-8 implementation.
