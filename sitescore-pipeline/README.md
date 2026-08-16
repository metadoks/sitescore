# sitescore-pipeline

FAZ 3.4-8 integration package for canonical normalized-feature assembly, scoring-readiness derivation, and the frozen `RealDataPipelineResult` terminal envelope.

## Scope

The package consumes locked `sitescore-benchmarks` normalization / COMB-005 artifacts and frozen `sitescore-data` DTOs. It does not redefine those contracts and does not perform category aggregation, Location Score computation, penalties, decision logic, reporting, or `core.analyze()`.

Canonical flow:

```text
actual 3.4-6 FeatureNormalizationResult artifacts
+ exact locked age fallback authority
+ actual 3.4-7 RoadParkingCompositeResult
→ factory-owned NormalizedFeatureAssembly
→ factory-owned ReadinessEvaluation
+ coherent DerivedLocationMetrics
→ RealDataPipelineResult
```

All eight frozen normalized slots are preserved. Missing/unresolved/incompatible evidence remains nonnumeric; no 0 or neutral 50 is invented. The exact locked age fallback is the sole numeric uncalibrated exception. Current COMB-005 remains unapproved, so canonical production readiness remains blocked.

## Hardened production authority

`NormalizedFeatureAssembly` and `ReadinessEvaluation` are factory-owned intermediates. Their direct constructors are disabled. Canonical object registration is held in closure-owned factory state, not in importable module-level tokens or hashes.

Consequently:

- reproducing `assembly_id` does not make an object canonical;
- `object.__new__` or other caller allocation does not register an assembly/readiness object;
- `derive_scoring_readiness()` accepts only the exact assembly object returned by canonical assembly;
- `build_real_data_pipeline_result()` accepts only the exact readiness object returned by canonical readiness derivation;
- no module-level `_ASSEMBLY_TOKEN`, `_READINESS_TOKEN`, or equivalent hash helper grants production authority.

The assembly retains the actual six `FeatureNormalizationResult` objects, so production authority is tied to real nested site measurements rather than only to detached normalized DTOs.

Controlled `SCORE_READY` tests exercise the frozen data validator directly as test-local fixtures; they are not pipeline-authority bypasses.

## Terminal real-unit coherence

Before terminal construction, every real-unit field that overlaps the six direct normalization results must exactly match the actual site `MetricValue` used by those normalization artifacts.

The comparison binds:

```text
value
unit
availability
data_quality
score_eligibility
calibration_state
is_estimate
is_proxy
source_refs
method_version
reason_codes
```

Contradictory household-income, transit, walkable-reach, competition, walkable-population, or target-density DTO values/lineage are rejected. Non-overlapping frozen `DerivedLocationMetrics` fields remain caller-supplied without invented semantics.

## Determinism and status

Readiness fingerprint and assembly identity are semantic and timestamp-independent. Competition measurement-definition and transit source-bundle compatibility remain derived from actual normalization/benchmark lineage.

Caller cannot assert `is_score_ready`, readiness summaries/fingerprint, or terminal status. Terminal status derives from canonical readiness:

```text
ready     → SCORE_READY
not ready → NOT_SCORE_READY
stage failure → PIPELINE_ERROR
```

`SCORE_READY != SCORED`; this package still owns no category or Location Score computation.

## Dependencies

Direct runtime dependencies are exact-pinned:

- `sitescore-data==0.1.0`
- `sitescore-benchmarks==0.1.0`

There is no `sitescore-core` dependency and no reverse dependency from frozen upstream packages.
