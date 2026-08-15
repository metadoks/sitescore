# FAZ 3.4 — Checkpoint 3.4-8

## Scoring Readiness + RealDataPipelineResult Integration

Status: implementation + Reviewer hardening complete, **not LOCKED**.

Base SHA: `c8514401f1b9e2a671c00477219f6f930a594bc8`

## Purpose and boundary

Checkpoint 3.4-8 integrates locked metric/normalization/fallback/COMB-005 artifacts into the frozen data-layer readiness and terminal pipeline contracts:

```text
actual metric artifacts
→ actual FeatureNormalizationResult artifacts
→ honest NormalizedLocationFeatures
→ derived ScoringReadinessResult
→ coherent RealDataPipelineResult
```

It stops before category aggregation or core scoring.

## Package / DAG

New additive package: `sitescore-pipeline==0.1.0`.

Direct runtime dependencies are exactly:

```text
sitescore-data==0.1.0
sitescore-benchmarks==0.1.0
```

No `sitescore-core` import/dependency, frozen upstream source mutation, or reverse dependency is introduced.

## Frozen DTO reuse

The implementation directly reuses frozen `MetricValue`, `NormalizedLocationFeatures`, readiness contracts/validator, `DerivedLocationMetrics`, `RealDataPipelineResult`, and `PipelineStatus`. No lookalike data-contract fork exists.

## Eight-slot normalized surface

The six direct slots come only from actual `FeatureNormalizationResult` artifacts:

- `walkable_population_score`
- `target_population_density_score`
- `competition_opportunity_score`
- `walkable_reach_area_score`
- `transit_access_score`
- `household_income_score`

Together with exact locked age fallback and actual COMB-005 output they populate all eight frozen normalized slots. Missing/unresolved/incompatible results remain nonnumeric. No missing→0, generic 50, substitution, or hidden renormalization is introduced.

## Age fallback

Canonical assembly requires an actual `AgeTargetConcentrationFallback` whose policy identity equals `AGE_TARGET_CONCENTRATION_FALLBACK_V1`. It remains the sole frozen numeric uncalibrated exception:

```text
score = 50
availability = AVAILABLE
eligibility = ELIGIBLE
calibration = UNCALIBRATED
proxy = true
reason = age_affinity_not_calibrated
```

Approval passed to the frozen readiness validator is derived from that actual authority, not caller strings.

## COMB-005

Canonical assembly consumes an actual `RoadParkingCompositeResult`. Current locked COMB-005 is still `POLICY_NOT_APPROVED`, score `None`; therefore `road_parking_access_score` remains unavailable and the frozen validator emits `ROAD_PARKING_COMPOSITE_UNAVAILABLE`. No empirical weights or replacement semantics are invented.

## Competition / transit compatibility

Benchmark references bind actual distribution/frame identity. Competition measurement-definition and transit source-bundle compatibility are derived from actual site/benchmark compatibility artifacts. A score cannot override incompatible lineage.

# PIPE-H001 — RESOLVED

## Original gap

The initial implementation used importable module globals (`_ASSEMBLY_TOKEN`, `_READINESS_TOKEN`, `_assembly_identity`) as authority. Ordinary Python callers could import the same values used by tests and forge a pipeline-recognized assembly/readiness wrapper.

## Hardened authority model

`NormalizedFeatureAssembly` and `ReadinessEvaluation` are factory-owned (`init=False`) and their direct constructors reject callers.

Canonical registration is maintained by closure-owned state created when the three production factories are installed:

```text
assemble_normalized_location_features()
derive_scoring_readiness()
build_real_data_pipeline_result()
```

The registries/capabilities do not exist as module-level names. The installer itself is deleted from module namespace after the closures are installed.

`derive_scoring_readiness()` accepts only the exact object returned and registered by canonical assembly. `build_real_data_pipeline_result()` likewise accepts only the exact readiness object produced and registered by canonical readiness derivation.

`assembly_id` remains deterministic evidence, not authority. Even if a caller allocates an object manually and reproduces the exact assembly hash, it is not present in the closure-owned registry and is rejected.

The old module-level authority names no longer exist:

```text
_ASSEMBLY_TOKEN
_READINESS_TOKEN
_assembly_identity
_install_canonical_factories
```

The canonical assembly also retains the actual six `FeatureNormalizationResult` objects in `direct_results`; readiness provenance is therefore bound to actual nested artifacts, not only to a detached normalized surface.

## H001 regressions

Tests prove:

1. direct assembly constructor is forbidden;
2. exact hash reproduction plus manually allocated assembly cannot obtain canonical readiness authority;
3. old importable token/hash authority names are absent;
4. direct readiness constructor is forbidden;
5. detached `ScoringReadinessResult` wrapped in a manually allocated readiness object cannot reach terminal construction;
6. production readiness API has no caller `is_score_ready`, fingerprint, reasons, or feature-state parameters;
7. controlled `SCORE_READY` coverage uses the frozen `ScoringReadinessValidator` directly as a test-local fixture and is explicitly not a production pipeline object.

# PIPE-H002 — RESOLVED

## Original gap

The initial terminal factory accepted an independently supplied `DerivedLocationMetrics` object and checked only frozen DTO/type/version invariants. It did not prove that overlapping real-unit fields were the same measurements that generated the direct normalization artifacts.

## Hardened terminal coherence

Canonical assembly retains actual `FeatureNormalizationResult.site_measurement` objects. Before terminal construction, `_validate_derived_metrics_coherence()` maps every direct normalized origin to the corresponding frozen `DerivedLocationMetrics` field:

```text
walkable_population → walkable_population
target_population_density → target_population_density
competition_pressure → competition_pressure
walkable_reach_area_km2 → walkable_reach_area_km2
transit_service_departure_equivalents_per_hour → transit_service_departure_equivalents_per_hour
household_income → household_income
```

For each overlapping field, the terminal metric must exactly equal the actual site measurement semantic record used by normalization. The comparison covers:

```text
value
unit
availability
data_quality
score_eligibility
calibration_state
is_estimate
is_proxy
source_refs (canonical order)
method_version
reason_codes
```

Feature-contract version alone is not sufficient. Non-overlapping frozen real-unit fields remain supplied honestly without invented semantics.

## H002 regressions

Tests prove rejection of household-income value/method mismatch, transit source-lineage mismatch, walkable-reach method mismatch, and an all-UNKNOWN placeholder surface when it contradicts actual overlapping site measurements. A coherent surface built from the actual overlapping measurements is accepted.

## Readiness and terminal status

Caller cannot provide `is_score_ready`, readiness summaries/fingerprint, or terminal status. Canonical readiness derives from the frozen validator and pipeline-owned semantic fingerprint; `evaluated_at` does not alter that fingerprint.

Terminal mapping remains:

```text
readiness true  → SCORE_READY
readiness false → NOT_SCORE_READY + SCORING_NOT_READY
actual stage failure → PIPELINE_ERROR + PIPELINE_STAGE_ERROR
```

Ordinary unresolved/unavailable evidence is not a pipeline execution error. `SCORE_READY != SCORED`: no CategoryScores, category weighting, Location Score, penalties, Decision Layer, or `core.analyze()` exist here.

## Current production truth

Current canonical production assembly is expected to remain `NOT_SCORE_READY`, principally because locked COMB-005 has no approved production policy. This is intentional and not treated as an execution failure.

## Final hardening validation evidence

Documentation-inclusive validation completed successfully:

```text
workflow: cp348-hardening-validation
run: 31909159381
validated SHA: ee76a7880926522bb6f7c824b1f7546562052b54
conclusion: SUCCESS
sitescore-pipeline: 25/25 PASS
sitescore-benchmarks: 191/191 PASS
sitescore-metrics: 67/67 PASS
sitescore-spatial: PASS
sitescore-providers: PASS
sitescore-data: PASS
sitescore-core: PASS
```

The exact 25/191/67 counts are explicitly visible in the job log. The other four package steps completed successfully; their exact cardinalities are not claimed from this log.

After validation, the temporary workflow was removed. The validated SHA → post-cleanup HEAD comparison contains exactly one file change: deletion of `.github/workflows/cp348-hardening-validation.yml`; source, tests, and this documentation are otherwise unchanged relative to the validated commit.

## Final scope expectation

Base → final review HEAD must contain only the additive `sitescore-pipeline` package. The final scope audit after temporary-workflow deletion shows eight package files and no frozen upstream source changes.

## Out of scope preserved

Not implemented:

- category scores/weighting;
- Location Score;
- penalties/dealbreakers;
- Decision Layer;
- `core.analyze()`;
- report/PDF;
- empirical COMB-005 policy/weights;
- upstream frozen contract changes;
- FAZ 3.4-FINAL.

`CONTRACT_CHANGE_REQUIRED = 0`.
