# SiteScore AI — Implementer → Reviewer Handoff

HANDOFF_PROTOCOL_VERSION: 1.0

AUTHORITATIVE_REPO: metadoks/sitescore

COORDINATION_BRANCH: ops/reviewer-implementer-handoff

FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 3.4

CURRENT_CHECKPOINT: 3.4-4

IMPLEMENTER_STATE: READY_FOR_REVIEW

CODE_BRANCH:

faz3.4/cp3.4-4-benchmark-distribution

BASE_SHA:

91608d7f70e2cdb28ba6aa9c287baea0af9f2275

CODE_HEAD_SHA:

09657fb6a35e79725fac372f7dc1d9a40ebb938c

PR:

#1

CONTRACT_CHANGE_REQUIRED:

0

---

## 1. Executive implementation summary

FAZ 3.4-4 implements the benchmark-side structural bridge from an already constructed `CommercialFrame` to a complete raw real-unit benchmark distribution artifact.

The implemented flow is:

```text
CommercialFrame
→ exact eligible benchmark-cell population
→ exactly one DerivedMetricMeasurement attempt per eligible cell
→ canonical metric/precision/unit validation
→ derived coverage accounting
→ metric-specific compatibility evaluation
→ finite real-unit numeric observation subset
→ BenchmarkDistributionArtifact
```

The implementation is additive and confined to `sitescore-benchmarks`. It consumes the public `sitescore-metrics==0.1.0` contracts instead of duplicating metric definitions or changing frozen upstream packages.

The checkpoint deliberately stops at raw real-unit benchmark distributions. No ECDF, percentile/rank calculation, 0–100 normalization, competition opportunity inversion, COMB-005 composition, readiness orchestration, CategoryScores, Location Score, or `core.analyze()` integration was added.

No new source, test, dependency, or checkpoint logic was changed during the handoff-protocol migration that produced this report. This report records the already completed code state.

---

## 2. Git state

```text
repository: metadoks/sitescore
main HEAD: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
base SHA: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
code branch: faz3.4/cp3.4-4-benchmark-distribution
code branch HEAD: 09657fb6a35e79725fac372f7dc1d9a40ebb938c
PR: #1
PR title: FAZ 3.4-4 — Benchmark Measurement + Distribution Artifacts
PR state: open
PR draft: false
PR mergeable at latest fetch: true
PR merged: false
PR base: main
PR base SHA: 91608d7f70e2cdb28ba6aa9c287baea0af9f2275
PR head: faz3.4/cp3.4-4-benchmark-distribution
PR head SHA: 09657fb6a35e79725fac372f7dc1d9a40ebb938c
PR commits: 9
PR changed files: 12
PR additions: 1607
PR deletions: 27
```

The code branch was independently re-fetched during protocol migration and still matched the PR head SHA above.

The coordination branch is separate from the code branch. This `implementer.md` update is being committed only to `ops/reviewer-implementer-handoff` and must not alter the code branch HEAD.

---

## 3. Changed files

The PR changes exactly these 12 files, all under `sitescore-benchmarks`:

1. `sitescore-benchmarks/README.md`
   - Updated package description/scope to include benchmark measurement and raw distribution responsibilities introduced in 3.4-4.

2. `sitescore-benchmarks/docs/CHECKPOINT_3_4_4_BENCHMARK_MEASUREMENT_DISTRIBUTION.md`
   - Added the checkpoint implementation record, public contracts, completeness/missingness/compatibility semantics, dependency notes, test baseline, unresolved decisions, and scope boundary.

3. `sitescore-benchmarks/pyproject.toml`
   - Added exact direct dependency `sitescore-metrics==0.1.0` alongside `sitescore-spatial==0.1.0`.
   - Updated package description.

4. `sitescore-benchmarks/requirements.lock`
   - Added exact internal pin `sitescore-metrics==0.1.0`.
   - No new direct third-party runtime dependency.

5. `sitescore-benchmarks/src/sitescore_benchmarks/__init__.py`
   - Publicly exports the new measurement, population, and distribution modules.

6. `sitescore-benchmarks/src/sitescore_benchmarks/measurement.py`
   - Adds benchmark subject-adapter policy, measurement/distribution policy, benchmark-cell subject derivation, canonical metric validation, `BenchmarkCellMeasurement`, `BenchmarkMetricCompatibility`, and builders/helpers.

7. `sitescore-benchmarks/src/sitescore_benchmarks/population.py`
   - Adds `BenchmarkMeasurementSet` and its builder.
   - Enforces complete eligible-cell coverage and canonical metric/precision/unit coherence.

8. `sitescore-benchmarks/src/sitescore_benchmarks/distribution.py`
   - Adds `BenchmarkDistributionState`, `BenchmarkCoverage`, `BenchmarkObservation`, `BenchmarkDistributionArtifact`, numeric inclusion/exclusion logic, compatibility conflict handling, and distribution builder.

9. `sitescore-benchmarks/tests/cp344_helpers.py`
   - Adds checkpoint-specific fixtures/helpers for complete frame populations and actual frozen schema-compatible demographic, isochrone, transit, parking, competition, and road measurement inputs.

10. `sitescore-benchmarks/tests/test_architecture.py`
    - Extends architecture checks for approved package dependencies, exact pins, no forbidden domain imports, no later-checkpoint surface, and no hidden production constants.

11. `sitescore-benchmarks/tests/test_benchmark_distribution.py`
    - Adds compatibility, distribution-state, identity, determinism, coverage derivation, empty/non-numeric population, parking separation, and scope-regression tests.

12. `sitescore-benchmarks/tests/test_benchmark_measurement_population.py`
    - Adds exact population completeness, duplicate/foreign/missing rejection, frame/subject binding, canonical metric binding, precision/unit behavior, missingness, authoritative value, non-finite, and transit tests.

No final PR file exists outside `sitescore-benchmarks`.

---

## 4. Public contracts added or changed

### `BenchmarkSubjectAdapterPolicy`

Versioned V1 policy defining the benchmark-cell subject contract and evidence-scope derivation algorithm.

Canonical instance:

```text
BENCHMARK_SUBJECT_ADAPTER_V1
```

Its identity binds:

```text
policy_id
policy_version
subject_contract
subject_contract_version
evidence_scope_algorithm
```

### `BenchmarkMeasurementDistributionPolicy`

Versioned structural policy for 3.4-4.

Canonical instance:

```text
BENCHMARK_MEASUREMENT_DISTRIBUTION_V1
```

V1 fixes only:

```text
EXACTLY_ONE_ATTEMPT_PER_ELIGIBLE_FRAME_CELL
AVAILABLE_SCORE_ELIGIBLE_FINITE_VALUE
EXACT_SOURCE_BUNDLE_COMPATIBILITY
```

It intentionally has no minimum N, minimum coverage percentage, CRS, cell size, overlap threshold, road/parking weights, reduction selector, or scoring threshold.

### `adapt_benchmark_cell_subject(...)`

Public adapter deriving `MeasurementSubject(kind=BENCHMARK_CELL)` from an actual `CommercialFrame`, actual `CommercialFrameCell`, actual `MetricEvidence` tuple, and the canonical adapter policy.

### `BenchmarkCellMeasurement`

Canonical benchmark measurement-attempt wrapper binding:

```text
CommercialFrame
CommercialFrameCell
DerivedMetricMeasurement
BenchmarkMeasurementDistributionPolicy
```

### `build_benchmark_cell_measurement(...)`

Public constructor helper for `BenchmarkCellMeasurement`.

### `BenchmarkMetricCompatibility`

Compatibility view derived from one actual `DerivedMetricMeasurement`. It exposes/derives:

```text
MetricDefinition
MetricDerivationPolicy
MeasurementPrecisionPolicy
unit
source_bundle_compatibility
compatibility identity
```

### `BenchmarkMeasurementSet`

Complete, single-metric semantic attempt population for one actual `CommercialFrame`.

### `build_benchmark_measurement_set(...)`

Builder resolving `MetricDefinition` and `MetricDerivationPolicy` from the canonical `sitescore-metrics` V1 registries by `metric_key`, while retaining exact identity validation.

### `BenchmarkDistributionState`

Structural states:

```text
AVAILABLE
EMPTY_ELIGIBLE_POPULATION
NO_NUMERIC_OBSERVATIONS
INCOMPATIBLE_MEASUREMENT_LINEAGE
```

`AVAILABLE` is a structural raw-distribution state only; it does not claim empirical adequacy.

### `BenchmarkCoverage`

Derived accounting object over an actual `BenchmarkMeasurementSet`.

### `BenchmarkObservation`

Numeric observation wrapper that takes only a `BenchmarkCellMeasurement`; value and unit are derived from the canonical measurement and cannot be independently supplied.

### `BenchmarkDistributionArtifact`

Raw real-unit distribution artifact over a complete `BenchmarkMeasurementSet`. Coverage, state, compatibility, and observation population are all derived.

### `build_benchmark_distribution(...)`

Public builder returning `BenchmarkDistributionArtifact`.

### Public exports

`sitescore_benchmarks.__init__` now exports `measurement`, `population`, and `distribution` public names through module wildcard exports, alongside the existing frame contracts/builders.

---

## 5. Exact implemented behavior

### Eligible cell population

The canonical target is exactly:

```text
CommercialFrame.eligible_cell_ids
```

The checkpoint does not create a second benchmark eligibility rule.

### Exactly one measurement attempt

`BenchmarkMeasurementSet.__post_init__` extracts every attempt's `frame_cell.cell_id`, rejects duplicate cell IDs, rejects duplicate attempt IDs, then requires exact set equality:

```text
set(attempt cell ids) == set(frame.eligible_cell_ids)
```

Therefore:

```text
A/B/C     accepted when A/B/C are the eligible cells
A/B       rejected as incomplete
A/B/C/C   rejected as duplicate
A/B/C/D   rejected as containing an extra/foreign attempt
```

There is no silent deduplication and no successful-only sampling.

### Foreign cell and frame rejection

`assert_frame_cell_target(...)` requires the supplied cell to be present in the supplied frame and to be canonically eligible.

`BenchmarkMeasurementSet` additionally verifies each attempt's `attempt.frame.frame_id` equals the measurement set's frame ID.

### Subject adaptation

`adapt_benchmark_cell_subject(...)` derives a `BENCHMARK_CELL` subject with semantic payload containing:

```text
commercial_frame_cell_id
commercial_frame_id
lattice_cell_id
```

Scope refs include:

```text
benchmark_cell:<cell id>
benchmark_frame:<frame id>
```

plus a canonical scope derived from actual attached `MetricEvidence`, e.g. geography/catchment/transit/parking/competition/road snapshot scope as applicable.

Duplicate evidence is rejected. Unsupported evidence roles or evidence lacking canonical scope are rejected.

### Frame/cell/measurement subject binding

`BenchmarkCellMeasurement` recomputes the expected benchmark subject from the actual frame, cell, and the measurement's attached evidence inputs, then requires subject identity equality with the actual `DerivedMetricMeasurement.subject`.

This rejects combinations such as:

```text
cell A + subject derived for cell B
frame A + cell from foreign frame
canonical-looking subject plus detached caller scope
measurement whose subject does not match actual frame/cell/evidence
```

### Metric binding

`validate_canonical_metric_pair(...)` requires both the definition and derivation policy to exist in the locked V1 `DEFINITIONS`/`POLICIES` registries and requires identity equality with the canonical registry objects.

Metric key alone is therefore not authority. A same-key altered definition or derivation policy cannot masquerade as the V1 contract.

### Precision and unit binding

`BenchmarkMeasurementSet` binds one explicit `MeasurementPrecisionPolicy` and checks every measurement precision-policy identity against it.

The set also requires every measurement's metric-value unit to equal `MetricDefinition.unit`.

V1 defaults to `FULL_BINARY64`; no quantization, epsilon, rounding, or tie precision was added.

### Coverage accounting

`BenchmarkCoverage` accepts only the actual measurement set. Callers do not supply counts.

Derived values include:

```text
eligible_cell_count
attempt_count
numeric_candidate_count
numeric_included_count
non_numeric_count
incompatible_numeric_count
excluded_count
reason_counts
compatibility_identities
```

Required reconciliation:

```text
attempt_count == eligible_cell_count
numeric_included_count + excluded_count == attempt_count
```

### Numeric inclusion

A measurement is a numeric candidate only when:

```text
metric_value.value is not None
availability == available
score_eligibility == eligible
value is finite
```

If value is `None`, the first measurement reason code is preserved where available; otherwise availability drives the exclusion reason.

Non-finite canonical numeric candidates raise instead of entering the distribution.

### Compatibility decision

Each attempt's compatibility identity is derived from the actual measurement's:

```text
MetricDefinition identity
MetricDerivationPolicy identity
MeasurementPrecisionPolicy identity
unit
source_bundle_compatibility
```

If a complete measurement set contains multiple compatibility identities, coverage records a compatibility conflict. Numeric candidates remain accounted for but are not emitted as numeric observations. The artifact state becomes:

```text
INCOMPATIBLE_MEASUREMENT_LINEAGE
```

### `BenchmarkDistributionArtifact`

The artifact is constructed only from a complete measurement set.

It derives:

```text
coverage
state
reason_codes
compatibility
observations
distribution_id
```

Empty eligible population is explicit. Complete but all-non-numeric population is explicit. Compatibility conflict is explicit. Raw observations retain real units.

---

## 6. Missingness semantics

The implementation preserves these separations:

```text
missing != zero
unresolved != zero
eligible benchmark cell != numeric observation
measurement attempt != numeric observation
```

Every eligible cell must remain present as an attempt even when the metric for that cell is missing/unresolved/non-numeric.

Example supported arithmetic:

```text
3 eligible cells
3 attempts
2 numeric included observations
1 excluded/non-numeric attempt
```

A missing isochrone-area measurement remains one attempt and contributes no fabricated zero observation.

Competition and road metrics can have complete attempt populations while producing zero numeric observations because their scalar reduction policies remain unresolved.

A zero-eligible-cell frame produces `EMPTY_ELIGIBLE_POPULATION`; it does not fabricate cells or values.

A non-empty complete attempt population with zero numeric observations produces `NO_NUMERIC_OBSERVATIONS`; it is not treated as zero score, neutral score, percentile, or rank.

---

## 7. Compatibility semantics

### `MetricDefinition`

Definition identity is checked against canonical `sitescore-metrics.DEFINITIONS[metric_key]`.

### `MetricDerivationPolicy`

Derivation policy identity is checked against canonical `sitescore-metrics.POLICIES[metric_key]`, and its `metric_key` must match the definition.

### `MeasurementPrecisionPolicy`

Every attempt in a set must use the same explicitly bound precision-policy identity. V1 builder default is `FULL_BINARY64`.

### Unit

Every measurement unit must exactly equal `MetricDefinition.unit`. Observation unit is derived from the underlying `MetricValue` and is not caller-supplied.

### Transit

`transit_service_departure_equivalents_per_hour` retains:

```text
transit_source_bundle_fingerprint
```

Same-bundle attempts can form an available raw distribution. Mixed bundle fingerprints create a compatibility conflict; numeric candidates are not silently combined.

### Competition

`competition_pressure` retains:

```text
competition_measurement_definition_id
```

The scalar reduction remains unresolved. Complete attempts remain non-numeric with `competition_reduction_policy_unresolved`. Mixed measurement-definition IDs create incompatible lineage rather than a blended distribution.

### Road

`road_reachable_area_km2` retains:

```text
routing_profile_id
routing_profile_version
```

The scalar reduction remains unresolved. Mixed routing profile compatibility becomes incompatible lineage.

### Parking

`parking_public_offstreet_capacity` and `parking_legal_curb_length_m` remain distinct metric/distribution families with units `spaces` and `m`; the checkpoint does not combine them.

---

## 8. Identity / lineage design

### Subject-adapter policy identity

Binds the exact versioned subject contract and evidence-scope algorithm.

### Benchmark attempt identity

`BenchmarkCellMeasurement.attempt_id` binds:

```text
frame_id
frame_cell_id
lattice_cell_id
measurement_id
measurement_policy_id
```

### Measurement-set identity

`BenchmarkMeasurementSet.measurement_set_id` binds:

```text
frame_id
MetricDefinition identity
MetricDerivationPolicy identity
MeasurementPrecisionPolicy identity
unit
benchmark measurement-policy identity
canonicalized attempt IDs
```

Attempt order is canonicalized only after duplicate/completeness validation, making worker/input ordering non-semantic without hiding duplicate attempts.

### Compatibility identity

`BenchmarkMetricCompatibility.identity_id` binds:

```text
MetricDefinition identity
MetricDerivationPolicy identity
MeasurementPrecisionPolicy identity
unit
source_bundle_compatibility
```

### Coverage identity

`BenchmarkCoverage.coverage_id` binds the measurement-set identity, derived population/count arithmetic, reason counts, and compatibility identities.

### Observation identity

`BenchmarkObservation.observation_id` binds:

```text
attempt_id
frame_cell_id
measurement_id
compatibility_id
authoritative value
authoritative unit
```

### Distribution identity

`BenchmarkDistributionArtifact.distribution_id` binds:

```text
measurement_set_id
measurement policy identity
frame_id
metric definition identity
metric derivation policy identity
measurement precision policy identity
unit
state
reason codes
coverage identity
compatibility identity when coherent
observation identities
```

### Anti-self-assertion behavior

The public artifact constructors do not accept detached caller claims for:

```text
observation value
observation unit
coverage counts
distribution state
distribution observations
compatibility status
```

Expected subject identity is recomputed from actual frame/cell/evidence instead of trusting matching-looking caller strings.

`generated_at` is not intentionally part of the new semantic distribution identity; regression coverage verifies timestamp changes on otherwise equivalent frame/measurement inputs do not change the distribution identity.

---

## 9. Dependency changes

`sitescore-benchmarks` direct runtime dependencies are now:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

The `sitescore-metrics` dependency was added explicitly because 3.4-4 consumes the locked public metric contracts and registries.

New direct third-party runtime dependency:

```text
none
```

`Shapely`/`pyproj` remain transitive through existing locked SiteScore package relationships; they were not newly declared as benchmark direct dependencies.

No dependency metadata outside `sitescore-benchmarks` changed.

---

## 10. Tests

A temporary branch-only GitHub Actions validation workflow was used to install all six packages and run each package suite from its package root.

Latest successful full regression run inspected during protocol migration:

```text
GitHub Actions run: 31893677619
run head SHA: a4c53f935f2b3cf6e889eb4c0cf57cd9fee5d03c
status: completed
conclusion: success
```

The run's six test steps all completed successfully.

Recorded exact suite counts:

```text
sitescore-benchmarks: 99/99 PASS
sitescore-metrics: 67/67 PASS
sitescore-spatial: 180/180 PASS
sitescore-providers: 418/418 PASS
sitescore-data: 361/361 PASS
sitescore-core: 86/86 PASS
--------------------------------
TOTAL EXECUTED: 1211/1211 PASS
```

The successful run at `a4c53f935f2b3cf6e889eb4c0cf57cd9fee5d03c` contains the final implementation, tests, and checkpoint documentation. GitHub compare between that tested SHA and final code HEAD `09657fb6a35e79725fac372f7dc1d9a40ebb938c` shows exactly one subsequent commit and exactly one file difference:

```text
.github/workflows/cp344-validation.yml — removed
```

No implementation source, checkpoint test, package metadata, or checkpoint documentation changed after that successful full regression run.

The final code HEAD itself has no retained temporary validation workflow, so there is no separate full-suite Actions run whose checkout SHA is `09657fb6...`; the evidence relationship is the successful `a4c53f...` run plus the GitHub compare showing workflow deletion only.

Tests not executed during this protocol-migration turn:

```text
none newly executed
```

Reason: migration was explicitly restricted to reading real GitHub state and writing the coordination handoff; no code changes were permitted. Existing GitHub Actions evidence above was re-fetched instead.

---

## 11. Adversarial regressions

The checkpoint regression suite includes tests covering at least these cases:

```text
complete eligible population accepted
missing eligible cell rejected
duplicate attempt rejected without deduplication
foreign extra attempt rejected
foreign frame cell rejected before subject adaptation
cell A + subject B mismatch rejected
forged extra caller evidence scope rejected
actual frame/cell/lattice/evidence scope derivation verified
wrong metric family rejected
altered same-key MetricDefinition cannot masquerade as canonical
altered same-key MetricDerivationPolicy cannot masquerade as canonical
precision mismatch rejected
unit/value are not independent caller inputs
unresolved measurements remain attempts but not observations
missing measurement does not become zero
numeric observation equals authoritative MetricValue
non-finite value has no benchmark observation bypass
transit same-bundle distribution accepted
transit cross-bundle population not silently mixed
competition measurement-definition lineage preserved
competition mixed measurement-definition lineage incompatible
road routing-profile lineage preserved
road mixed routing-profile lineage incompatible
parking capacity and curb-length remain independent distributions
empty eligible population explicit
all-attempts-non-numeric population representable
input order non-semantic after validation
identity changes with precision semantics
identity changes with source compatibility
generated_at non-semantic for equivalent distribution
coverage derived rather than caller asserted
distribution state/observations not self asserted
metric key alone not contract authority
no ECDF/percentile/normalization public surface
policy has no empirical threshold fields
```

---

## 12. Dependency / DAG audit

Final benchmark architecture tests inspect source imports and package metadata.

Reported boundary result:

```text
sitescore-benchmarks → sitescore-core imports: 0
sitescore-metrics → sitescore-benchmarks imports: 0
sitescore-data → sitescore-core imports: 0
sitescore-providers → sitescore-core imports: 0
new dependency cycles: 0 observed
```

The benchmark package architecture test explicitly permits only:

```text
sitescore_spatial
sitescore_metrics
```

as direct `sitescore_*` imports and explicitly rejects `sitescore_core`, `sitescore_pipeline`, `sitescore_data`, and `sitescore_providers` in benchmark source.

The full frozen package suites were also rerun in the successful GitHub Actions regression above, providing regression coverage for their existing architecture boundaries without modifying those packages.

No external frozen package source file appears in the final PR changed-file list.

---

## 13. Scope audit

The checkpoint intentionally does not implement:

```text
ECDF
mid-ECDF
percentile calculation
percentile rank
interpolation policy
tie-equality precision policy
0–100 feature normalization
competition opportunity inversion
feature directionality scoring
road/parking COMB-005 composite
minimum benchmark N policy
minimum benchmark coverage threshold
scoring readiness
RealDataPipelineResult orchestration
CategoryScores
Location Score
core.analyze()
```

Architecture regressions search benchmark source for later-checkpoint tokens and fail if those surfaces appear.

The 3.4-4 measurement/distribution policy constructor also has no empirical threshold or geometry/calibration fields such as `minimum_n`, `coverage_threshold`, `cell_size`, `equal_area_crs`, `overlap_threshold`, or road/parking weights.

---

## 14. Documentation updates

Added:

```text
sitescore-benchmarks/docs/CHECKPOINT_3_4_4_BENCHMARK_MEASUREMENT_DISTRIBUTION.md
```

The document records:

```text
checkpoint scope and structural bridge
public contracts
complete eligible-cell population semantics
attempt vs observation semantics
missingness behavior
metric/compatibility behavior
transit/competition/road/parking lineage notes
empty/no-numeric states
identity semantics
explicit unresolved/calibration-gated decisions
dependency DAG
test/adversarial coverage
executed regression baseline
CONTRACT_CHANGE_REQUIRED = 0
```

Also updated:

```text
sitescore-benchmarks/README.md
```

to reflect the expanded measurement/raw-distribution package responsibility.

---

## 15. Known unresolved / calibration-gated decisions preserved

The implementation intentionally does not create production answers for:

```text
equal-area CRS selection
lattice/cell resolution
lattice anchor
production boundary-membership semantics
commercial classification/mapping semantics
commercial cell applicability semantics
walkable population allocation
target population definition
household-income-ratio denominator
competition scalar reduction
road scalar reduction
minimum benchmark N / empirical adequacy
minimum benchmark coverage threshold
ECDF tie-equality precision
COMB-005 road/parking composition
age-affinity / empirical calibration
```

Relevant unresolved metric consequences remain explicit:

```text
walkable_population → population allocation unresolved
target_population_density → target population definition unresolved
household_income_ratio → denominator policy unresolved
competition_pressure → scalar reduction unresolved
road_reachable_area_km2 → scalar reduction unresolved
```

3.4-4 does not invent reductions merely to create numeric distributions.

---

## 16. Self-audit result

The implementation was self-audited against the complete checkpoint boundary after coding and before the original PR handoff.

Observed result recorded from the final source/tests/diff:

```text
foreign frame/cell bypass: covered by validation/regressions
subject self-assertion bypass: expected subject recomputed from actual frame/cell/evidence
same-key altered metric definition/policy bypass: registry identity validation present
caller-controlled observation value/unit: no independent constructor input
caller-controlled coverage counts: no independent constructor input
caller-controlled distribution state/observations: no independent constructor input
missing eligible attempt: rejected
duplicate eligible attempt: rejected
foreign/extra attempt: rejected
missing → zero conversion: not implemented
unresolved → numeric conversion: not implemented
transit cross-bundle mixing: surfaced as incompatible lineage; observations suppressed
competition reduction invention: not implemented
road reduction invention: not implemented
input order determinism: regression covered
precision/source compatibility identity sensitivity: regression covered
generated timestamp semantic leakage: regression covered as non-semantic
dependency additions: exact internal metric pin only
new direct third-party dependency: none
final PR scope outside sitescore-benchmarks: none
later-checkpoint normalization/scoring surface: architecture regression rejects it
full six-package regression: successful at tested source/doc SHA
```

One evidence nuance for Reviewer to preserve: the final code HEAD is one commit after the latest successful full regression SHA because the temporary validation workflow itself was removed. GitHub compare confirms that workflow removal is the only post-test difference.

`CONTRACT_CHANGE_REQUIRED` remains `0`: the checkpoint was implemented as an additive benchmark-layer extension consuming existing locked metric contracts.

---

## 17. Reviewer attention points

Please independently verify the actual PR/source rather than relying on this report, with particular attention to:

1. Whether `BenchmarkCellMeasurement` subject recomputation fully prevents detached frame/cell/evidence semantics under all supported metric evidence roles.
2. Whether `BenchmarkMeasurementSet` exact-set equality plus per-attempt checks are sufficient to prevent any foreign-frame or matching-looking-ID edge case.
3. Whether `BenchmarkMetricCompatibility` and the all-attempt compatibility conflict rule are the intended canonical interpretation for metrics with `source_bundle_compatibility`.
4. Whether numeric inclusion using availability + score eligibility + finite value is correctly aligned with the locked metric contract and does not accidentally admit an unresolved/calibration state that should remain non-numeric.
5. Whether compatibility conflict correctly suppresses all numeric candidates rather than permitting a misleading partial compatible subset.
6. Whether all semantic identity fields are sufficient and all runtime/non-semantic fields are correctly excluded.
7. Whether public wildcard exports introduce any unintended public-surface concern.
8. Whether the final dependency DAG remains acceptable with the new direct `sitescore-benchmarks → sitescore-metrics` edge.
9. Whether the successful Actions run at `a4c53f...` plus the one-file workflow-deletion compare to `09657fb...` is sufficient test evidence for the exact final review HEAD.
10. Whether any 3.4-5 or later scoring/normalization responsibility leaked despite the explicit architecture tests.

No new implementation was performed during the GitHub handoff protocol migration.
