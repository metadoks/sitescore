# FAZ 3.4 — Checkpoint 3.4-8

## Scoring Readiness + RealDataPipelineResult Integration

Status: implementation complete, **not LOCKED**.

Base SHA: `c8514401f1b9e2a671c00477219f6f930a594bc8`

## Purpose

Checkpoint 3.4-8 is the terminal implementation checkpoint before FAZ 3.4-FINAL audit. It integrates the already locked real-data, benchmark-normalization, age-fallback, and COMB-005 artifacts into the frozen data-layer readiness and terminal pipeline contracts.

The boundary is deliberately:

```text
actual artifacts
→ honest NormalizedLocationFeatures
→ derived ScoringReadinessResult
→ derived RealDataPipelineResult
```

It stops before category aggregation or core scoring.

## Package / DAG

New additive package: `sitescore-pipeline==0.1.0`.

Direct dependencies:

```text
sitescore-data==0.1.0
sitescore-benchmarks==0.1.0
```

No frozen upstream source was modified. The pipeline does not import `sitescore-core`; no upstream package imports pipeline.

## Frozen DTO reuse

The implementation consumes the existing frozen data contracts directly:

- `MetricValue`
- `NormalizedLocationFeatures`
- `FeatureReadinessPolicy`
- `ReadinessCompatibilityInput`
- `ApprovedFallbackPolicyRef`
- `ScoringReadinessResult`
- `ScoringReadinessValidator`
- `RealDataPipelineResult`
- `PipelineStatus`

No lookalike DTOs were forked.

## Eight required slots

Canonical assembly preserves exactly:

1. `walkable_population_score`
2. `target_population_density_score`
3. `age_target_concentration_score`
4. `competition_opportunity_score`
5. `walkable_reach_area_score`
6. `transit_access_score`
7. `road_parking_access_score`
8. `household_income_score`

The six direct slots must come from actual `FeatureNormalizationResult` artifacts. Missing direct mappings are rejected by assembly; unavailable direct artifacts yield honest nonnumeric `MetricValue` state, never 0/50 substitution.

## Direct normalization adaptation

For an actual AVAILABLE `FeatureNormalizationResult`, the adapter uses the actual derived score with:

```text
unit = score_0_100
availability = AVAILABLE
score_eligibility = ELIGIBLE
calibration_state = CALIBRATED
```

Quality, proxy/estimate flags and provenance are derived from actual nested measurement plus bound benchmark reference provenance. The method version is derived from the locked normalization policy.

For nonavailable states, score remains `None`; state/quality/eligibility/calibration are represented conservatively without inventing numeric evidence.

## Age fallback authority

Canonical assembly requires an actual `AgeTargetConcentrationFallback` whose policy identity exactly equals `AGE_TARGET_CONCENTRATION_FALLBACK_V1`.

The emitted age slot is the sole frozen numeric uncalibrated exception:

```text
value = 50
unit = score_0_100
availability = AVAILABLE
score_eligibility = ELIGIBLE
calibration_state = UNCALIBRATED
is_proxy = true
reason = age_affinity_not_calibrated
method_version = age_neutral_fallback/1.0
```

The trusted `ApprovedFallbackPolicyRef` passed to the frozen validator is derived from this actual locked authority. Caller id/version strings are not accepted by the production assembly API.

## COMB-005 current truth

Canonical assembly consumes an actual `RoadParkingCompositeResult`.

Because checkpoint 3.4-7 froze the current canonical policy as unapproved, the current road/parking result is:

```text
POLICY_NOT_APPROVED
score = None
```

The assembled `road_parking_access_score` is therefore nonnumeric and unready. `road_parking_composite_policy_version` remains `None`; `UNAPPROVED_V1` is not misrepresented as an approved resolved scoring policy.

The frozen readiness validator consequently emits `ROAD_PARKING_COMPOSITE_UNAVAILABLE` and blocks score readiness.

## Competition / transit compatibility

`BenchmarkReferenceBinding` ties a frozen data-layer `BenchmarkReference` to the actual normalization artifact by requiring:

```text
reference.benchmark_id == actual distribution_id
reference.frame_id == actual frame_id
```

Competition and transit feature lineage are derived from actual site and benchmark compatibility artifacts:

- competition site measurement-definition identity → normalized feature metadata;
- competition benchmark measurement-definition identity → readiness compatibility input;
- transit site source-bundle fingerprint → normalized feature metadata;
- transit benchmark source-bundle fingerprint → readiness compatibility input.

Thus mismatches remain visible to the frozen validator and cannot be overridden by an available numeric score.

## Assembly authority / identity

Canonical `assemble_normalized_location_features()` accepts only:

```text
direct_results
age_fallback
road_parking_result
benchmark_bindings
generated_at
```

It does not accept an arbitrary normalized feature surface, detached scores, readiness status, or caller policy summaries.

`NormalizedFeatureAssembly.assembly_id` binds the normalized feature semantic surface, actual artifact identities, policy resolution inputs, compatibility authority, approved age fallback authority and benchmark bindings. Collection order is canonicalized. `generated_at` does not change semantic assembly identity.

## Readiness anti-self-assertion

Canonical `derive_scoring_readiness()` accepts only a canonical assembly plus `evaluated_at`.

It does not accept:

```text
is_score_ready
readiness_fingerprint
missing_required_features
uncalibrated_features
incompatible_features
reason_codes
feature_states
```

The pipeline derives a deterministic fingerprint from actual semantic assembly content and validator semantics, then invokes the frozen `ScoringReadinessValidator`.

`evaluated_at` is deliberately not part of the semantic readiness fingerprint.

## Data quality

No numeric quality threshold was invented. The frozen validator semantics are honored: `FULL` and `DEGRADED` are structurally acceptable; insufficient frozen quality states block readiness. The exact approved age fallback is not rejected merely for being proxy/uncalibrated.

## Terminal pipeline authority

Canonical `build_real_data_pipeline_result()` receives a canonical `ReadinessEvaluation`; caller status is not accepted.

It derives:

```text
readiness true  -> SCORE_READY
readiness false -> NOT_SCORE_READY + SCORING_NOT_READY
```

An explicit `PipelineStageFailure` is required by the separate error factory to produce:

```text
PIPELINE_ERROR + PIPELINE_STAGE_ERROR
scoring_readiness = None
```

Ordinary unavailable/unresolved evidence that successfully reaches readiness remains `NOT_SCORE_READY`, not `PIPELINE_ERROR`.

## SCORE_READY != SCORED

The pipeline owns no category score or Location Score computation. It does not import core and does not construct `ReadyCategoryScorePayload`.

`SCORE_READY` means only that later application-layer aggregation is permitted.

## Provenance

`NormalizedLocationFeatures.source_refs` is the canonical union needed to cover nested metric and bound benchmark references. `source_metadata` is separately sorted by `source_id` for the frozen terminal DTO and is not treated as a universal registry for every opaque artifact reference.

## Current production expectation

Current canonical real-data integration is expected to be `NOT_SCORE_READY` while COMB-005 remains unapproved and other upstream metric/benchmark artifacts may remain unresolved. This is an intended result, not a failure.

A controlled complete normalized feature fixture exists only in tests to prove generic readiness and `SCORE_READY` terminal semantics. It is not a production artifact-authority path.

## Adversarial regression matrix

Implemented coverage includes:

- READY-001 all eight slots required;
- READY-002 no missing neutralization;
- READY-003 ordinary uncalibrated numeric feature blocks;
- READY-004 exact age fallback requires actual trusted approval;
- READY-005 age exception cannot leak;
- READY-006 competition mismatch blocks;
- READY-007 transit bundle mismatch blocks;
- READY-008 current COMB-005 unavailable blocks with frozen reason;
- READY-009 missing policy blocks;
- READY-010 policy version mismatch blocks;
- READY-011 insufficient quality blocks;
- READY-012 readiness anti-self-assertion;
- PIPE-001 readiness false derives NOT_SCORE_READY;
- PIPE-002 controlled complete fixture derives SCORE_READY;
- PIPE-003 SCORE_READY is not scored output;
- PIPE-004 ordinary unready evidence is not PIPELINE_ERROR;
- PIPE-005 explicit stage failure derives PIPELINE_ERROR without readiness;
- PIPE-006 status anti-self-assertion;
- PIPE-007 frozen terminal feature-contract coherence rejection.

Additional regressions verify semantic fingerprints exclude timestamps and canonical production assembly does not accept arbitrary `MetricValue`/`NormalizedLocationFeatures` surfaces.

## Initial validation

GitHub Actions workflow `cp348-validation`, run `31908132238`, validated commit `836179a8065f71a8bd12f7c94b9f52397a21ca9e` with SUCCESS.

Exact visible summaries:

```text
sitescore-pipeline:   28/28 PASS
sitescore-benchmarks: 191/191 PASS
sitescore-metrics:    67/67 PASS
```

The same job completed spatial, providers, data and core test steps successfully. Exact cardinalities are not asserted where the final pytest summary was not visibly retained in the collected log.

A final documentation-inclusive validation is required before review handoff. The temporary workflow must then be removed and validated SHA → final review HEAD compared.

## Out of scope

Not implemented:

- CategoryScores;
- category weighting;
- base/final Location Score;
- dealbreaker penalties;
- Decision Layer;
- `core.analyze()`;
- report/PDF;
- empirical COMB-005 policy or weights;
- changes to unresolved upstream metric/benchmark semantics;
- FAZ 3.4-FINAL audit/freeze.

`CONTRACT_CHANGE_REQUIRED = 0`.
