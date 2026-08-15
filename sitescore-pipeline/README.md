# sitescore-pipeline

FAZ 3.4-8 integration package for canonical normalized-feature assembly, scoring-readiness derivation, and the frozen `RealDataPipelineResult` terminal envelope.

## Scope

The package consumes locked `sitescore-benchmarks` normalization / COMB-005 artifacts and frozen `sitescore-data` DTOs. It does not redefine the data contracts and does not perform category aggregation, Location Score computation, dealbreaker penalties, decision logic, reporting, or `core.analyze()`.

Canonical flow:

```text
actual 3.4-6 FeatureNormalizationResult artifacts
+ exact locked age fallback authority
+ actual 3.4-7 RoadParkingCompositeResult
+ persisted benchmark-reference bindings where available
→ NormalizedLocationFeatures
→ derived ScoringReadinessResult
→ derived RealDataPipelineResult status
```

All eight frozen normalized feature slots are preserved. Missing/unresolved/incompatible evidence stays nonnumeric; it is never replaced by 0 or neutral 50. The sole numeric uncalibrated exception is the exact locked age fallback.

Current canonical COMB-005 remains unapproved, so `road_parking_access_score` remains unavailable and blocks canonical scoring readiness. A controlled complete feature fixture exists only in tests to prove generic `SCORE_READY` terminal semantics.

## Production authority

Canonical assembly does not accept an arbitrary `NormalizedLocationFeatures` object or eight caller-authored `MetricValue` scores. Canonical readiness does not accept caller `is_score_ready`, summary arrays, or a detached readiness fingerprint. Canonical terminal result creation does not accept caller pipeline status.

Readiness fingerprint and assembly identity are content-derived and exclude evaluation/generation timestamps from semantic identity. Competition measurement-definition and transit source-bundle compatibility are retained from actual normalization/benchmark lineage.

## Dependencies

Direct runtime dependencies are exact-pinned:

- `sitescore-data==0.1.0`
- `sitescore-benchmarks==0.1.0`

There is no `sitescore-core` dependency and no reverse dependency from frozen upstream packages.
