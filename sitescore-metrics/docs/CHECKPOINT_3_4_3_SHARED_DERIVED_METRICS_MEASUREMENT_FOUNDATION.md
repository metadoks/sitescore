# FAZ 3.4 — Checkpoint 3.4-3 Shared Derived Metrics / Measurement Foundation

## Scope
`sitescore-metrics` owns provider-neutral real-unit measurement semantics shared by site and benchmark-cell paths. It does not own benchmark frames/distributions, ECDF, normalization, readiness, COMB-005, category aggregation, core analyze(), or pipeline orchestration.

## Dependency DAG
`sitescore-metrics -> sitescore-data==0.1.0, sitescore-providers==0.1.0, sitescore-spatial==0.1.0`.
Forbidden dependencies: `sitescore-core`, `sitescore-benchmarks`, `sitescore-pipeline`.

## Canonical contracts
- `MeasurementPrecisionPolicy`: V1 is explicit `FULL_BINARY64`, with no quantization parameter. This is real-unit representation semantics, not future ECDF tie precision.
- `MeasurementSubject`: content-bound provider-neutral subject sidecar with explicit `SITE` / `BENCHMARK_CELL` kind, contract/version, canonical semantic payload, and canonical scope refs.
- `MetricDefinition`: metric key/version/unit/implementation status.
- `MetricDerivationPolicy`: actual policy object; V1 distinguishes provider-derived pass-through from unresolved allocation/target/denominator/reduction boundaries.
- `MetricEvidence`: carries an actual frozen snapshot object, never only a detached input hash.
- `DerivedMetricMeasurement`: carries actual definition/policy/precision/subject/evidence plus the authoritative frozen `MetricValue`. `measurement_id` is derived only.

Successful provider-derived measurements constructor-verify that the output `MetricValue` is exactly the canonical metric field on the attached frozen snapshot, that the evidence role is correct, that subject scope is compatible, and that source-bundle compatibility lineage matches actual evidence. Thus an actual snapshot plus a fabricated numeric output is rejected.

## Metric matrix
| Metric | V1 semantic | Input evidence | Unit | Status | Policy state / reason | Site/benchmark parity | Future dependency |
|---|---|---|---|---|---|---|---|
| `walkable_population` | population inside approved walking catchment allocation | `DemographicSnapshot` + `IsochroneSnapshot` | `people` | STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED | population allocation policy unresolved; no area/centroid/dasymetric default | same future allocator/policy for both subjects | approved allocation policy |
| `target_population_density` | approved target-population per area | `DemographicSnapshot` | `people_per_km2` | STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED | target population definition unresolved; no age-band invention | same future target definition | approved target definition |
| `household_income` | canonical frozen demographic household-income statistic | `DemographicSnapshot.household_income` | `usd_per_household` | PASS_THROUGH_PROVIDER_DERIVED | resolved pass-through; no mean/per-capita/family substitution | exact same pass-through implementation | none |
| `household_income_ratio` | income divided by approved reference denominator | `DemographicSnapshot` + future reference evidence | `ratio` | STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED | denominator policy unresolved | same future denominator semantics | approved denominator policy |
| `competition_pressure` | scalar reduction of frozen multi-scale competition curve | `CompetitionSnapshot` | `competition_pressure` | STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED | no nearest/mean/median/max/AUC/weights selected | same future reduction | approved competition reduction |
| `walkable_reach_area_km2` | authoritative provider-derived isochrone area | `IsochroneSnapshot.area_km2` | `km2` | PASS_THROUGH_PROVIDER_DERIVED | exact provider metric pass-through; no second geometry-area definition | exact same pass-through implementation | none |
| `transit_service_departure_equivalents_per_hour` | frozen 168-hour walking-accessible GTFS service supply | `TransitSnapshot.service_departure_equivalents_per_hour` | `departure_equivalents_per_hour` | PASS_THROUGH_PROVIDER_DERIVED | exact provider metric; source-bundle fingerprint retained/validated | same pass-through and bundle semantics | benchmark compatibility in later checkpoint |
| `road_reachable_area_km2` | scalar reduction of multi-scale road reachable-area evidence | `RoadAccessSnapshot` | `km2` | STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED | no scale selection or aggregation selected | same future reduction | approved road reduction |
| `parking_public_offstreet_capacity` | known eligible public off-street capacity | `ParkingSnapshot.known_public_offstreet_capacity` | `spaces` | PASS_THROUGH_PROVIDER_DERIVED | exact provider metric; unknown capacity remains missing/unknown, not zero | exact same pass-through implementation | none |
| `parking_legal_curb_length_m` | mapped legal public curb length | `ParkingSnapshot.mapped_legal_curb_length_m` | `m` | PASS_THROUGH_PROVIDER_DERIVED | exact provider metric; kept separate from capacity | exact same pass-through implementation | none |

## Failure / missing semantics
Missing evidence, unresolved policy, incompatible bundle, provider failure, and out-of-validity are not numeric zero. Unresolved derivations return state-aware `MetricValue(value=None, availability=UNKNOWN, ...)` with explicit reasons. A public unresolved policy cannot emit a numeric value.

## Source/bundle compatibility
- Transit measurement binds the actual `TransitSnapshot.source_bundle_fingerprint` and rejects a mismatched expected bundle.
- Competition unresolved measurement preserves the actual `CompetitionSnapshot.measurement_definition_id`; mismatched expected definition is rejected.
- Road unresolved measurement preserves the actual routing profile id/version.
- Frozen snapshot evidence itself is carried as an actual object. Evidence identity excludes `generated_at`/`retrieved_at` and canonicalizes set-like `source_refs`/`reason_codes` ordering.

## Identity and determinism
`measurement_id` commits to metric definition, derivation policy, measurement precision policy, subject, actual evidence identities, compatibility lineage, exact `MetricValue`, method version, and reasons. It excludes generation time and local/cache paths. Input evidence is canonical-sorted by derived identity.

Changing policy version, measurement precision policy, definition unit, subject identity, actual evidence semantics, compatibility semantics, or numeric result changes measurement identity. Site vs benchmark-cell subjects may therefore have different measurement IDs while using exactly the same algorithm/policy/value/unit semantics.

## Explicit deferred decisions
- walkable-population allocation/intersection method
- target population / age definition
- household-income denominator/reference
- competition multi-scale scalar reduction
- road multi-scale scalar reduction
- future benchmark numeric/tie quantization and ECDF semantics
- benchmark distributions and coverage policy
- normalization, COMB-005, readiness and pipeline integration

## Final-lock self-audit
Audited all public contracts for detached semantic IDs, duck-typed nested evidence, self-asserted successful values, unit/value mismatch, subject/evidence mismatch, policy/input mismatch, failure-to-zero collapse, identity omissions, source-ref/input ordering, forbidden imports, scope leakage, and artifact hygiene.

Checkpoint-local fixes include constructor-level pass-through evidence/output coherence, subject-scope checks, transit/competition/road compatibility checks, canonical set-like source-ref hashing, and no detached measurement/input identity constructor fields.

## Test baseline
`sitescore-metrics`: 43/43 PASS before final packaging. Locked/frozen baselines rerun without source changes: benchmarks 63, spatial 180, data 361, providers 418, core 86.

`CONTRACT_CHANGE_REQUIRED = 0`.

---

## Final Contract-Integrity Hardening — METRIC-H001 / METRIC-H002

### METRIC-H001 — canonical registry enforcement

`DerivedMetricMeasurement` is a canonical SiteScore V1 metric artifact, not an extension registry. Its constructor now requires:

- `definition.metric_key` to exist in both canonical `DEFINITIONS` and `POLICIES`;
- `definition.identity_id == DEFINITIONS[metric_key].identity_id`;
- `policy.identity_id == POLICIES[metric_key].identity_id`;
- PASS_THROUGH_PROVIDER_DERIVED definitions to use the canonical PASS_THROUGH_PROVIDER_DERIVED strategy;
- STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED definitions to use their exact canonical unresolved strategy.

Validation is semantic/content-based, not Python singleton identity. A separately reconstructed definition/policy with identical canonical semantics is accepted. Altered versions, statuses, policy IDs/versions/strategies, and unregistered metric keys are rejected. Future custom metrics require a separately versioned extension boundary and are outside Checkpoint 3.4-3.

### METRIC-H002 — canonical evidence/result schemas for all ten metrics

Every V1 metric now has an exact evidence cardinality, evidence family, evidence role, compatibility schema, and (for unresolved metrics) exact structural `MetricValue` state.

| Metric | Exact evidence schema | Compatibility | Canonical unresolved reason |
|---|---|---|---|
| walkable_population | DemographicSnapshot(`demographic_snapshot`) + IsochroneSnapshot(`isochrone_snapshot`) | none | `population_allocation_policy_unresolved` |
| target_population_density | DemographicSnapshot(`demographic_snapshot`) | none | `target_population_definition_unresolved` |
| household_income | DemographicSnapshot(`demographic_snapshot`) | none; pass-through | n/a |
| household_income_ratio | DemographicSnapshot(`demographic_snapshot`) | none | `household_income_denominator_policy_unresolved` |
| competition_pressure | CompetitionSnapshot(`competition_snapshot`) | exact `competition_measurement_definition_id` | `competition_reduction_policy_unresolved` |
| walkable_reach_area_km2 | IsochroneSnapshot(`isochrone_snapshot`) | none; pass-through | n/a |
| transit_service_departure_equivalents_per_hour | TransitSnapshot(`transit_snapshot`) | exact `transit_source_bundle_fingerprint` | n/a |
| road_reachable_area_km2 | RoadAccessSnapshot(`road_snapshot`) | exact routing profile ID/version | `road_reduction_policy_unresolved` |
| parking_public_offstreet_capacity | ParkingSnapshot(`parking_snapshot`) | none; pass-through | n/a |
| parking_legal_curb_length_m | ParkingSnapshot(`parking_snapshot`) | none; pass-through | n/a |

For every structural-unresolved measurement, the exact V1 result state is:

```text
value = None
availability = UNKNOWN
data_quality = MISSING
score_eligibility = INELIGIBLE
calibration_state = UNCALIBRATED
is_estimate = False
is_proxy = False
unit = canonical metric unit
source_refs = canonical-sorted union derived from actual evidence
method_version = sitescore_metrics.<metric_key>.v1
reason_codes = exact canonical unresolved reason
```

No arbitrary compatibility entries are permitted where no compatibility semantic is approved. Competition and road retain only their exact frozen compatibility lineage. Extra or unrelated evidence artifacts are rejected rather than becoming additional semantic input noise.

### MeasurementSubject clarification

`MeasurementSubject` remains a content-bound provider-neutral semantic subject descriptor. It is not a cryptographic proof that an external site or benchmark cell exists. Construction/adaptation of the external site/cell remains an integration responsibility; this hardening intentionally does not expand Checkpoint 3.4-3 into a cross-package authenticity framework.

### Final hardening regression baseline

```text
sitescore-metrics = 67/67 PASS
```

The final audit covers all 10 canonical metric keys for registry coherence, status/strategy coherence, evidence family/role/cardinality, canonical source refs, canonical compatibility lineage, canonical unresolved reasons/state, pass-through equality, unit coherence, non-finite rejection, set-like input determinism, and subject/evidence scope where defined.
