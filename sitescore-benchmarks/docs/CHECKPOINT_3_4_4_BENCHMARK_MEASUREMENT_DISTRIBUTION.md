# FAZ 3.4 — CHECKPOINT 3.4-4 BENCHMARK MEASUREMENT + DISTRIBUTION ARTIFACTS

## Status

`READY FOR REVIEW` after implementation, consolidated hardening, regression execution, and checkpoint-wide self-audit. This record does **not** declare the checkpoint LOCKED or reviewer-approved.

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
- `AVAILABLE_SCORE_ELIGIBLE_CALIBRATED_FINITE_VALUE` numeric-candidate semantics;
- `EXACT_METHOD_AND_SOURCE_BUNDLE_COMPATIBILITY` compatibility semantics.

The numeric inclusion policy is calibration-aware: a finite AVAILABLE + ELIGIBLE metric does not become a benchmark observation unless its authoritative nested `MetricValue.calibration_state` is `CALIBRATED`. No metric-specific uncalibrated exception is invented here.

Compatibility is derived from the actual measurement and includes method semantics plus metric-specific source/bundle semantics. No caller-supplied method or compatibility assertion is accepted.

The policy contains no minimum N, coverage percentage, CRS, cell size, scalar reduction, or composite weight.

### BenchmarkCellMeasurement

Binds an actual frame, actual frame cell, actual canonical `DerivedMetricMeasurement`, and the benchmark policy. Construction recomputes the expected benchmark subject from the attached measurement evidence and rejects detached frame/cell/subject relationships.

### BenchmarkMetricCompatibility

Accepts one actual `DerivedMetricMeasurement` and derives canonical definition, derivation policy, measurement precision, unit, actual `method_version`, and metric-specific `source_bundle_compatibility`. Its identity binds all of those dimensions. There is no detached caller-supplied compatibility or method-version payload.

### BenchmarkMeasurementSet

Binds one actual frame and one exact canonical metric semantic family. It rejects missing eligible attempts, duplicate attempts, foreign/extra cells, foreign frames, wrong definition/policy, precision mismatch, unit mismatch, and detached subjects. Input order is non-semantic only after uniqueness/completeness validation.

### BenchmarkCoverage

Accepts only the actual measurement set. Counts and reason breakdowns are derived, never caller asserted. Required arithmetic:

```text
attempt_count == eligible_cell_count
numeric_included_count + excluded_count == attempt_count
```

Calibration-rejected attempts remain represented and receive deterministic exclusion reasons such as `calibration_state_uncalibrated`.

### BenchmarkObservation

Accepts only an actual canonical numeric benchmark attempt. Value and unit are derived directly from `DerivedMetricMeasurement.metric_value`; no independent numeric payload exists. Calibration failure therefore blocks observation construction through the same canonical inclusion rule.

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

Frame eligibility and metric availability/calibration are independent axes: an eligible cell with missing, unresolved, or uncalibrated metric evidence remains represented as an attempt.

## Attempt vs observation and missingness

A measurement attempt is a completeness fact; a numeric observation is an inclusion fact. Therefore `3 eligible / 3 attempts / 2 numeric / 1 excluded` is valid.

Missing/unresolved/uncalibrated attempts remain visible in coverage. `None`, UNKNOWN, MISSING, unresolved, or UNCALIBRATED states are never converted to zero. Numeric observations come only from the authoritative finite canonical `MetricValue` of a valid `DerivedMetricMeasurement` that is AVAILABLE, score-ELIGIBLE, and CALIBRATED.

`FULL_BINARY64` remains measurement representation precision. No tolerance, rounding, quantization, or future ECDF tie policy is introduced here.

## Metric and compatibility semantics

The measurement set binds actual canonical `MetricDefinition`, `MetricDerivationPolicy`, `MeasurementPrecisionPolicy`, and unit. Metric key alone is not authority; the locked metrics registry prevents altered same-key definitions/policies from masquerading as canonical V1 semantics.

Benchmark compatibility additionally binds the actual `DerivedMetricMeasurement.method_version`. This prevents measurements produced by different method semantics from being silently blended even when definition/policy/precision/unit and metric-specific bundle payloads otherwise match.

Metric-specific `source_bundle_compatibility` is retained in addition to method semantics. Per-cell `source_refs` are provenance and are not required to be identical across the population. If complete attempts contain more than one compatibility identity, the raw artifact enters `INCOMPATIBLE_MEASUREMENT_LINEAGE`; all attempts remain accounted for and numeric candidates are not emitted as a falsely comparable collection.

### Transit

`transit_service_departure_equivalents_per_hour` preserves both actual `method_version` and `transit_source_bundle_fingerprint`. Same-method/same-bundle measurements are comparable; method mismatch or bundle A + bundle B cannot silently coexist as one canonical numeric distribution.

### Competition

`competition_pressure` preserves actual method semantics plus `competition_measurement_definition_id`. Scalar reduction remains unresolved, so attempts stay non-numeric with `competition_reduction_policy_unresolved`. No opportunity inversion is implemented.

### Road

`road_reachable_area_km2` preserves actual method semantics plus `routing_profile_id` and `routing_profile_version`. Scalar reduction remains unresolved, so attempts stay non-numeric with `road_reduction_policy_unresolved`. No mean/median/max/nearest/weighted reduction is invented.

### Parking

`parking_public_offstreet_capacity` (`spaces`) and `parking_legal_curb_length_m` (`m`) remain independent distributions. Their actual measurement method versions are compatibility-bearing. No parking inference or road/parking combination is introduced.

## Empty / zero-observation behavior

A frame with zero eligible cells is represented explicitly as `EMPTY_ELIGIBLE_POPULATION`; no cells or observations are fabricated. A complete population with zero numeric observations, including one where all otherwise numeric attempts are uncalibrated, is represented as `NO_NUMERIC_OBSERVATIONS`; it is not converted to zero, a neutral score, or a statistical rank.

## Identity semantics

New identities bind semantic material as applicable: actual frame/cell/lattice identities, subject-adapter and measurement policy identities, canonical metric definition/policy/precision/unit, exact measurement membership, actual measurement method semantics, metric-specific compatibility lineage, authoritative numeric value/unit, and complete coverage state. Set-like attempt order is canonicalized after duplicate validation. Generated timestamps, paths, worker ordering, and per-cell provenance-reference equality are not introduced as compatibility semantics.

## Consolidated hardening

### BENCH-H001 — calibration-aware numeric inclusion

Resolved inside `sitescore-benchmarks` without changing frozen upstream contracts.

Numeric inclusion now requires actual nested measurement state:

```text
value is not None
availability == AVAILABLE
score_eligibility == ELIGIBLE
calibration_state == CALIBRATED
finite(value)
```

An AVAILABLE + ELIGIBLE + UNCALIBRATED finite pass-through metric remains a complete measurement attempt but is excluded from numeric observations with deterministic reason `calibration_state_uncalibrated`. The policy semantic identity was updated to accurately state this rule.

Regressions cover all-uncalibrated populations, mixed 2 calibrated + 1 uncalibrated populations, preservation of valid calibrated inclusion, and policy-identity accuracy.

### BENCH-H002 — measurement method compatibility

Resolved inside `sitescore-benchmarks` without changing frozen upstream contracts.

`BenchmarkMetricCompatibility` now exposes actual `measurement.method_version` and includes it in compatibility identity alongside definition, derivation policy, precision, unit, and existing `source_bundle_compatibility`.

Mixed method versions therefore produce `INCOMPATIBLE_MEASUREMENT_LINEAGE` instead of a blended numeric distribution. Same-method populations remain compatible. Existing transit source-bundle conflict behavior remains active in addition to method semantics. No equality requirement was added for per-cell `source_refs`.

Regressions cover mixed method versions, same-method compatibility, identity sensitivity to method version, transit bundle preservation, and policy-identity accuracy.

## Explicit unresolved / calibration-gated decisions preserved

No production decision is invented for equal-area CRS, lattice resolution/anchor, boundary membership, commercial classification/applicability, population allocation, target-population definition, income-ratio denominator, competition reduction, road reduction, minimum benchmark N, minimum coverage, ECDF tie precision, COMB-005, or age affinity/calibration.

The H001 correction does not calibrate any metric; it only prevents uncalibrated measurements from entering numeric benchmark observations.

## Dependency DAG

`sitescore-benchmarks` directly declares:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

No new direct third-party dependency is added. Expected DAG remains acyclic; benchmarks→core, metrics→benchmarks, data→core, and providers→core remain forbidden.

H001/H002 hardening added no dependency or frozen-package change.

## Regression / adversarial coverage

Tests cover exact eligible-cell completeness; missing/duplicate/foreign attempts; cross-frame and subject mismatch; evidence-scope adaptation; wrong metric and altered same-key semantics; precision/unit bypasses; no missing→zero; uncalibrated numeric exclusion without attempt loss; authoritative observation values; non-finite bypass prevention; same/mixed method-version compatibility; transit same/cross-bundle behavior; competition/road unresolved lineage; parking independence; empty/all-nonnumeric populations; order determinism; identity sensitivity; timestamp non-semanticity; derived counts/state; no caller-supplied compatibility/calibration state; no ECDF/normalization surface; dependency boundaries; and hidden-production-constant audit.

## Tests executed

Full package-root regression was executed on GitHub Actions after BENCH-H001/H002 source and regression changes:

```text
sitescore-benchmarks  108/108 PASS
sitescore-metrics       67/67 PASS
sitescore-spatial      180/180 PASS
sitescore-providers    418/418 PASS
sitescore-data         361/361 PASS
sitescore-core           86/86 PASS
--------------------------------
aggregate             1220/1220 PASS
```

The five non-benchmark packages remain unchanged from the authoritative baseline; their full suites were nevertheless executed for regression verification. A temporary branch-only validation workflow is used only for test execution and must be removed before review handoff so CI infrastructure does not enter the checkpoint's final diff.

## Focused sibling audit

The hardening does not add caller-supplied calibration or compatibility assertions; method semantics are read from the actual `DerivedMetricMeasurement`; per-cell `source_refs` are not compared for compatibility; complete attempt accounting remains unchanged; no numeric zero substitution, epsilon, rounding, quantization, ECDF/percentile/normalization behavior, empirical minimum-N/coverage threshold, frozen-package edit, or dependency-cycle change was introduced.

## CONTRACT_CHANGE_REQUIRED

`0` — both consolidated blockers are representable as additive `sitescore-benchmarks` hardening consuming the locked `sitescore-metrics` public surface. No frozen external contract mutation is required.
