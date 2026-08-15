# Checkpoint 3.3-3 — ACS Acquisition + Statistical Evidence + Demographic Builder

Status: READY FOR REVIEW (implementation record; not LOCKED by this record)

## Scope

This checkpoint implements only US ACS 5-Year Detailed Tables acquisition, provider-side immutable statistical evidence, neutral age aggregation, and mapping into frozen `sitescore-data v0.1.0` demographic contracts.

Explicitly out of scope: Overture, OSM/Valhalla, GTFS, road, parking, benchmark normalization, sitescore-app, sitescore-core integration.

## Official Census references verified before implementation

- ACS 5-Year API landing page: https://www.census.gov/data/developers/data-sets/acs-5year.html
- 2024 ACS 5-Year Detailed Tables API: https://api.census.gov/data/2024/acs/acs5.html
- 2024 ACS 5-Year variables: https://api.census.gov/data/2024/acs/acs5/variables.html
- 2024 ACS 5-Year groups: https://api.census.gov/data/2024/acs/acs5/groups.html
- ACS API geography examples / supported geography links from the ACS developer documentation.
- ACS estimate / annotation special-value notes: https://www.census.gov/programs-surveys/acs/technical-documentation/table-and-geography-changes/2024/5-year.html and Census API notes linked by ACS developer metadata.
- Census API Terms of Service: https://www.census.gov/data/developers/about/terms-of-service.html
- ACS margins-of-error guidance and derived-estimate methodology published by the U.S. Census Bureau.

Verified implementation-driving facts:

1. The ACS 5-Year Detailed Tables API is release-addressed (`/{year}/acs/acs5`); production identity therefore pins an exact release and never uses a mutable `latest`/`current` alias.
2. Detailed Tables support small geographies including census tracts and block groups.
3. ACS API responses are tabular JSON arrays with a header row followed by data rows.
4. One API `get` request supports at most 50 variables; request planning therefore deterministically chunks complete semantic variable specifications.
5. ACS variables distinguish estimate (`E`), margin of error (`M`), and annotation (`EA`/`MA`) semantics.
6. Census publishes special numeric/string values that must not be treated as ordinary observations.
7. Published ACS margins of error are statistical evidence; derived MOE calculations require an explicit statistical method. This checkpoint retains raw-cell MOEs and deliberately does not silently sum them for derived age cohorts.

## Identity/configuration model

`ACSDatasetManifest` is immutable and commits to:

- manifest version
- exact dataset release / vintage
- product
- dataset identifier
- exact `ACSVariableManifest.identity`
- exact `ACSGeographyCompatibility.identity`
- parser version
- provider canonicalization version

Exact release/configuration is trusted deployment/configuration input. The package performs no live latest-release discovery.

`ACSVariableManifest` commits to every exact estimate/MOE/annotation variable mapping, semantic role, unit, and aggregation group. Variable IDs are not inferred by the client.

`AgeCohortAggregationPolicy` commits exact cohort intervals and exact source semantic keys. No sector affinity or global target-age policy exists.

## Request semantics

ACS request fingerprint identity is the semantic provider request:

- exact dataset release / dataset identifier
- exact frozen geography type/GEOID and deterministic `for`/`in` decomposition
- exact requested ACS variable IDs, normalized for order independence

API credentials, retrieved-at time, retry state, cache paths, and execution IDs are excluded.

Block group and tract requests are explicit. Unsupported geography is a typed domain/acquisition condition and is never silently converted to another geography.

## Statistical evidence

`ACSStatisticalEvidence` is provider-internal, immutable, and content/lineage bound. It preserves:

- semantic key plus exact originating estimate/MOE/EA/MA column IDs
- originating request fingerprint (for deterministic cross-chunk query-plan coherence)
- estimate and MOE separately
- estimate/MOE special-value state
- raw estimate/MOE representations
- estimate/MOE annotations
- geography identity
- ACS release/vintage
- dataset-manifest identity
- raw-content hash
- parsed-artifact derivation identity
- aggregation lineage

Frozen `DemographicSnapshot` does not contain numeric MOE fields. The approved Option A remains in force: numeric MOE and annotations remain in immutable provider-side evidence; `DemographicSnapshotLineage` binds every emitted frozen metric/cohort to the evidence identities from which it was derived.

Derived cohort MOE aggregation is deferred. Raw component-cell MOEs remain retained and reproducible.

## Frozen demographic mapping

Actual frozen classes were read directly from the authoritative `sitescore-data-v0.1.0` source tree.

`AgeCohortPopulation` fields:

- cohort_id
- age_min_inclusive
- age_max_exclusive
- population
- population_share

`DemographicSnapshot` fields:

- geography_ref
- total_population
- age_cohorts
- household_income
- source_refs
- availability
- data_quality
- generated_at

`MetricValue` scoring state is not fabricated. Normal numeric ACS estimates are emitted as diagnostic / uncalibrated rather than `ELIGIBLE + CALIBRATED`.

## Persistence

No provider-specific Census retention period is hard-coded into foundation or ACS production code. Persistence remains an explicit provider-policy/configuration decision. Census API terms were reviewed; this checkpoint does not turn those terms into a broad generic legal abstraction.

## Contract status

`sitescore-data v0.1.0` was not modified.

`CONTRACT_CHANGE_REQUIRED = 0`.

The absence of numeric MOE fields in the frozen demographic schema is intentionally handled by immutable provider-side evidence and lineage, per the accepted Option A disposition.


## Statistical evidence / chunking hardening

`ACSVariableSpec` is the atomic query-planning unit. Its E/M/optional EA/MA columns are never split across requests. Specs are sorted by semantic key before deterministic packing; every request remains at or below the Census 50-variable limit.

`ACSStatisticalEvidence` is self-contained for originating ACS column identity: it stores the exact estimate, MOE, estimate-annotation, and MOE-annotation column IDs as well as the immutable dataset-manifest identity, semantic key, and originating request fingerprint. Cross-chunk bundle construction recomputes the deterministic query plan and rejects manifest/release/vintage/geography mismatches, request-fingerprint mismatches, duplicate semantic keys, and duplicate/originating-column inconsistencies.

Any non-empty EA/MA annotation prevents the corresponding numeric representation from being exposed as ordinary `VALUE` evidence. Official numeric sentinel semantics take precedence when the raw numeric cell itself is a documented sentinel; raw values and annotation text remain retained either way. Unknown non-empty annotations are not silently treated as harmless metadata.

Determinism has two distinct scopes. With the same evidence, manifests/policies, and the same explicitly supplied `generated_at`, the frozen `DemographicSnapshot` primitive is deterministic. `DemographicSnapshotLineage.snapshot_identity` intentionally excludes `generated_at` and therefore identifies the demographic derivation rather than byte-for-byte/full-field snapshot serialization. Changing only `generated_at` changes the frozen snapshot primitive but not that derivation identity.
