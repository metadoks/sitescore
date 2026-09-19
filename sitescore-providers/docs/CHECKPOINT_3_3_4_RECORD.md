# Checkpoint 3.3-4 — Competition / Overture Places

Scope is limited to pinned Overture Places release evidence, release-specific taxonomy mapping, exact-ID deduplication, caller-supplied precomputed multi-scale catchment membership, and frozen competition contracts. No routing, benchmark ECDF, normalization, scoring, or core integration is implemented.

## Official Overture verification (2026-08-12)

Official sources reviewed:

- https://docs.overturemaps.org/release-calendar/
- https://docs.overturemaps.org/guides/places/
- https://docs.overturemaps.org/guides/places/taxonomy/
- https://docs.overturemaps.org/schema/reference/places/place/
- https://docs.overturemaps.org/schema/reference/places/types/taxonomy/
- https://docs.overturemaps.org/schema/reference/places/types/operating_status/
- https://docs.overturemaps.org/gers/
- https://docs.overturemaps.org/gers/registry/
- https://docs.overturemaps.org/attribution/
- https://docs.overturemaps.org/blog/2026/06/17/release-notes/

Verified design facts:

- Overture data releases use date-based identifiers and schema releases use semantic versions.
- Official Overture release documentation verified on 2026-08-12 identifies `2026-07-22.0` as the current data release and `v1.18.0` as its schema version. Production code still does not auto-discover or hard-code a "latest" release; exact release/schema/taxonomy configuration remains trusted deployment input.
- Overture publicly retains release data for a maximum of 60 days, so canonical SiteScore competition evidence requires content-addressed persisted partition artifacts rather than replay by remote URL alone.
- Places are distributed as GeoParquet on official AWS/Azure release paths; Overture is a data-product distribution, not a point-query API.
- Places use `id`, point geometry, optional `operating_status`, optional `confidence`, `basic_category`, `taxonomy`, and `sources` metadata. Taxonomy exposes `primary`, ordered `hierarchy`, and unordered `alternates`.
- `operating_status` values are `open`, `temporarily_closed`, and `permanently_closed`; status is optional. `permanently_closed` must not become active competition evidence; null/unknown is not silently active.
- Confidence is 0..1 and may be absent. This checkpoint preserves it and applies no arbitrary threshold.
- Places IDs are the dataset identity used for matching/GERS workflows. Checkpoint 3.3-4 deduplicates only by exact Overture place ID within a pinned release; it performs no distance-based heuristic collapse.
- Places is multi-license. Current official attribution lists CDLA-Permissive-2.0, Apache-2.0, and CC0 sources. Provider-side source/license evidence is retained instead of reducing the whole Places theme to one license string.

## Identity boundaries

`OverturePlacesReleaseManifest` commits to exact release, schema, theme/type, taxonomy identity/version, acquisition identity/version, parser version, manifest/canonicalization grammar.

`OvertureCompetitionTaxonomyMapping` is release-bound and commits to exact rules, semantic class, inclusion/conditional/exclusion result, conditions, and mapping version. No global unversioned Overture category dictionary exists.

`measurement_definition_id` commits to provider/dataset, release/schema/taxonomy, taxonomy mapping, lifecycle policy, exact-ID dedup policy, catchment semantic policy, travel mode/cost scales, spatial predicate, projection/area method, count/density methods, and method version. It excludes site-specific membership, catchment area, artifact/storage refs, retrieved time, processing order, ECDF, percentiles, and normalized scores.

## Acquisition boundary

`OverturePlacesRecordReader` is a backend-neutral protocol. A concrete Parquet/S3/Azure/filesystem dependency is deliberately not selected in this checkpoint. `OverturePartitionDescriptor` + exact content hash + artifact ref provide replay identity. The decoded reader row boundary normalizes point geometry to `{type: Point, coordinates: [lon, lat]}` before the provider parser; no spatial engine is implemented here.

Canonical competition snapshots require partition persistence class `PERSIST`, because public remote releases expire and reproducibility cannot rely on remote retention.

## Coverage and zero semantics

`CoverageState.SUFFICIENT` is required before an AVAILABLE curve is emitted. UNKNOWN/INSUFFICIENT coverage produces a non-AVAILABLE curve state, not zero competition. Zero count is emitted only when source/measurement coverage is declared sufficient and all relevant in-catchment taxonomy/status decisions are resolved.

## Deferred

- exact production release/schema/taxonomy pin
- release-specific category mapping population
- empirical coverage sufficiency policy
- concrete GeoParquet/storage backend
- network catchment generation
- benchmark frame/ECDF/normalization


## Competition semantic hardening

- Taxonomy resolution is explicitly versioned and hierarchy-first: HIERARCHY -> PRIMARY -> BASIC_CATEGORY fallback/QA. ALTERNATE matches are supporting-only and never independently qualify or veto a place.
- `OvertureCompetitionTaxonomyMapping.identity` commits to `TaxonomyResolutionPolicy.identity`, so changes to resolution semantics change downstream measurement identity.
- Exact-ID dedup compares full canonical measurement-relevant place evidence, including taxonomy hierarchy/alternates, lifecycle status, confidence, and source attribution. Conflicting duplicates are rejected; identical duplicates collapse.
- Taxonomy hierarchy/alternates are raw-type validated before canonicalization. A valid taxonomy requires a non-empty hierarchy, `primary == hierarchy[-1]`, unique collection values, and alternates outside the hierarchy.
- Lifecycle and entity-dedup policy identities explicitly bind their grammar versions and provider canonicalization version.
