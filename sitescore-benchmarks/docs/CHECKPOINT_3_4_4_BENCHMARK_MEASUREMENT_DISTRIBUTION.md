# FAZ 3.4 — CHECKPOINT 3.4-4 BENCHMARK MEASUREMENT + DISTRIBUTION ARTIFACTS

## Status

`READY FOR REVIEW` after implementation, regression execution, and checkpoint-wide self-audit. This record does **not** declare the checkpoint LOCKED.

## Purpose and scope

Checkpoint 3.4-4 creates the structural bridge:

```text
CommercialFrame
→ complete eligible cell population
→ exactly one measurement attempt per eligible cell
→ derived coverage accounting
→ compatibility / inclusion decision
→ raw real-unit observations
→ BenchmarkDistributionArtifact
```

Owned here: benchmark-cell subject adaptation, attempt-population completeness, coverage, raw observation inclusion, distribution artifacts, and benchmark compatibility lineage.

Explicitly out of scope: provider acquisition, metric formulas, ECDF/percentile/tie policy, 0–100 normalization, competition opportunity inversion, COMB-005, readiness, pipeline orchestration, CategoryScores, Location Score, and `core.analyze()`.

## Public contracts

### BenchmarkSubjectAdapterPolicy

V1 derives `MeasurementSubject(kind=BENCHMARK_CELL)` from actual immutable `CommercialFrame`, `CommercialFrameCell`, `LatticeCellArtifact`, and attached canonical `MetricEvidence`. The subject binds frame ID, frame-cell ID, lattice-cell ID, and evidence-derived scope references. Callers do not supply detached frame/cell IDs or arbitrary evidence scopes through the adapter.

### BenchmarkMeasurementDistributionPolicy

V1 freezes only structural behavior owned by this checkpoint:

- `EXACTLY_ONE_ATTEMPT_PER_ELIGIBLE_FRAME_CELL`;
- `AVAILABLE_SCORE_ELIGIBLE_FINITE_VALUE` numeric-candidate semantics;
- exact source/bundle compatibility semantics.

It contains no minimum N, coverage percentage, CRS, cell size, scalar reduction, or composite weight.

### BenchmarkCellMeasurement

Binds an actual frame, actual frame cell, actual canonical `DerivedMetricMeasurement`, and the benchmark policy. Construction recomputes the expected benchmark subject from the attached measurement evidence and rejects detached frame/cell/subject relationships.

### BenchmarkMetricCompatibility

Accepts one actual `DerivedMetricMeasurement` and derives canonical definition, derivation policy, measurement precision, unit, and metric-specific `source_bundle_compatibility`. There is no detached caller-supplied compatibility payload.

### BenchmarkMeasurementSet

Binds one actual frame and one exact canonical metric semantic family. It rejects missing eligible attempts, duplicate attempts, foreign/extra cells, foreign frames, wrong definition/policy, precision mismatch, unit mismatch, and detached subjects. Input order is non-semantic only after uniqueness/completeness validation.

### BenchmarkCoverage

Accepts only the actual measurement set. Counts and reason breakdowns are derived, never caller asserted. Required arithmetic:

```text
attempt_count == eligible_cell_count
numeric_included_count + excluded_count == attempt_count
```

### BenchmarkObservation

Accepts only an actual numeric benchmark attempt. Value and unit are derived directly from `DerivedMetricMeasurement.metric_value`; no independent numeric payload exists.

### BenchmarkDistributionArtifact

Accepts only the complete measurement set. Coverage, state, compatibility, and observations are derived. Structural states are:

- `AVAILABLE`;
- `EMPTY_ELIGIBLE_POPULATION`;
- `NO_NUMERIC_OBSERVATIONS`;
- `INCOMPATIBLE_MEASUREMENT_LINEAGE`.

`AVAILABLE` is not an empirical adequacy claim.

## Complete eligible-cell population

The target population is exactly `CommercialFrame.eligible_cell_ids`, i.e. the locked frame semantics requiring commercial `ELIGIBLE` plus boundary `MEMBER`.

For eligible cells A/B/C, canonical attempts must be exactly A/B/C once each. A/B, A/B/C/C, and A/B/C/D are rejected. There is no successful-only sampling and no silent deduplication.

Frame eligibility and metric availability are independent: an eligible cell with missing or unresolved metric evidence remains represented as an attempt.

## Attempt vs observation and missingness

A measurement attempt is a completeness fact; a numeric observation is an inclusion fact. Therefore `3 eligible / 3 attempts / 2 numeric / 1 excluded` is valid.

Missing/unresolved attempts remain visible in coverage. `None`, UNKNOWN, MISSING, or unresolved values are never converted to zero. Numeric observations come only from the authoritative finite canonical `MetricValue` of a valid `DerivedMetricMeasurement`.

`FULL_BINARY64` remains measurement representation precision. No tolerance, rounding, quantization, or future ECDF tie policy is introduced here.

## Metric and compatibility semantics

The measurement set binds actual canonical `MetricDefinition`, `MetricDerivationPolicy`, `MeasurementPrecisionPolicy`, and unit. Metric key alone is not authority; the locked metrics registry prevents altered same-key definitions/policies from masquerading as canonical V1 semantics.

Metric-specific compatibility is retained from actual measurements. If complete attempts contain more than one compatibility identity, the raw artifact enters `INCOMPATIBLE_MEASUREMENT_LINEAGE`; all attempts remain accounted for and numeric candidates are not emitted as a falsely comparable collection.

### Transit

`transit_service_departure_equivalents_per_hour` preserves the actual `transit_source_bundle_fingerprint`. Same-bundle measurements are comparable; bundle A + bundle B cannot silently coexist as one canonical numeric distribution.

### Competition

`competition_pressure` preserves `competition_measurement_definition_id`. Scalar reduction remains unresolved, so attempts stay non-numeric with `competition_reduction_policy_unresolved`. No opportunity inversion is implemented.

### Road

`road_reachable_area_km2` preserves `routing_profile_id` and `routing_profile_version`. Scalar reduction remains unresolved, so attempts stay non-numeric with `road_reduction_policy_unresolved`. No mean/median/max/nearest/weighted reduction is invented.

### Parking

`parking_public_offstreet_capacity` (`spaces`) and `parking_legal_curb_length_m` (`m`) remain independent distributions. No parking inference or road/parking combination is introduced.

## Empty / zero-observation behavior

A frame with zero eligible cells is represented explicitly as `EMPTY_ELIGIBLE_POPULATION`; no cells or observations are fabricated. A complete population with zero numeric observations is represented as `NO_NUMERIC_OBSERVATIONS`; it is not converted to zero, a neutral score, or a statistical rank.

## Identity semantics

New identities bind semantic material as applicable: actual frame/cell/lattice identities, subject-adapter and measurement policy identities, canonical metric definition/policy/precision/unit, exact measurement membership, compatibility lineage, authoritative numeric value/unit, and complete coverage state. Set-like attempt order is canonicalized after duplicate validation. Generated timestamps, paths, and worker ordering are non-semantic.

## Explicit unresolved / calibration-gated decisions preserved

No production decision is invented for equal-area CRS, lattice resolution/anchor, boundary membership, commercial classification/applicability, population allocation, target-population definition, income-ratio denominator, competition reduction, road reduction, minimum benchmark N, minimum coverage, ECDF tie precision, COMB-005, or age affinity/calibration.

## Dependency DAG

`sitescore-benchmarks` now directly declares:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

No new direct third-party dependency is added. Expected DAG remains acyclic; benchmarks→core, metrics→benchmarks, data→core, and providers→core remain forbidden.

## Regression / adversarial coverage

Tests cover exact eligible-cell completeness; missing/duplicate/foreign attempts; cross-frame and subject mismatch; evidence-scope adaptation; wrong metric and altered same-key semantics; precision/unit bypasses; no missing→zero; authoritative observation values; non-finite bypass prevention; transit same/cross-bundle behavior; competition/road unresolved lineage; parking independence; empty/all-nonnumeric populations; order determinism; identity sensitivity; timestamp non-semanticity; derived counts/state; no ECDF/normalization surface; dependency boundaries; and hidden-production-constant audit.

## Tests executed

Actual executed suite counts and results are recorded in the implementation PR and final implementation handoff. This document does not invent unexecuted PASS counts.

## CONTRACT_CHANGE_REQUIRED

`0` — the checkpoint is representable as an additive `sitescore-benchmarks` extension consuming the locked `sitescore-metrics` public surface. No frozen external contract mutation is required.
