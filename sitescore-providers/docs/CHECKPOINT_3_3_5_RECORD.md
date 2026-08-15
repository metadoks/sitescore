# SiteScore Providers — Checkpoint 3.3-5 Record

## Scope

Pedestrian/walking-network acquisition identity and Valhalla isochrone evidence only.
No GTFS, vehicle road, parking, demographic overlay, benchmark ECDF, normalization, or core/app integration.

## Official source verification (2026-08-13)

Primary references reviewed before implementation:

- Valhalla Isochrone API: https://valhalla.github.io/valhalla/api/isochrone/
  - `pedestrian` is the walking costing name.
  - time contours are specified in minutes; distance contours in kilometres.
  - `polygons=true` returns Polygon or MultiPolygon GeoJSON contours.
  - `show_locations=true` returns exact input and snapped network-node locations.
  - `denoise` and `generalize` alter contour geometry and therefore are identity-bearing options.
- Valhalla releases: https://github.com/valhalla/valhalla/releases
  - current reviewed release: 3.8.3 (release date 2026-07-24).
  - 3.8.0 removed the legacy `json` request parameter. Checkpoint 3.3-5 therefore uses JSON POST semantics.
- Valhalla Status API: https://valhalla.github.io/valhalla/api/status/
  - exposes engine version and tileset metadata; runtime status is diagnostic, not the canonical graph identity used here.
- Valhalla change-identification docs: https://valhalla.github.io/valhalla/concepts/change-identification/
  - tileset identifiers/checksums have distinct scopes. SiteScore therefore carries its own exact graph content hash plus trusted compatibility identity rather than treating one runtime field as universal identity.
- OpenStreetMap copyright/license: https://www.openstreetmap.org/copyright
  - OSM data is ODbL-licensed and requires OpenStreetMap/contributor attribution.
- OpenStreetMap planet/extract docs: https://wiki.openstreetmap.org/wiki/Planet.osm
  - planet data is available in PBF/XML and new planet versions are published regularly; mutable live data is not a canonical SiteScore source identity.
- RFC 7946 GeoJSON: https://www.rfc-editor.org/rfc/rfc7946
  - GeoJSON geographic positions use WGS84 and longitude/latitude order.

No Valhalla/OSM “latest/current” value is hard-coded as a production dataset identity.

## Frozen contract audit

Authoritative `sitescore-data v0.1.0` files inspected directly.

### `src/sitescore_data/schemas/pedestrian.py`

`PedestrianCatchmentArtifact` actual fields:

- `catchment_id`
- `origin_location_ref`
- `origin_latitude`
- `origin_longitude`
- `travel_mode`
- `travel_cost_budget_seconds`
- `geometry_ref`
- `source_refs`
- `policy_version`
- `generated_at`

`IsochroneSnapshot` actual fields:

- `snapshot_id`
- `catchment_ref`
- `area_km2`
- `source_refs`
- `availability`
- `data_quality`
- `method_version`
- `generated_at`

### `src/sitescore_data/schemas/common.py`

`MetricValue` and `SourceMetadata` were mapped without modification.

### `src/sitescore_data/schemas/geography.py`

`ResolvedLocation` actual fields were used as the canonical requested-origin input.

`CONTRACT_CHANGE_REQUIRED = 0`.

## Provider-layer contracts

- `PedestrianNetworkManifest`: pinned network source/extract/content/release/format/acquisition identity.
- `PedestrianRoutingEngineManifest`: engine/version, graph-build method/version, pedestrian profile/version, explicit costing options, request grammar.
- `PedestrianGraphCompatibility`: trusted config binding network manifest + routing engine manifest + exact graph content hash/artifact ref.
- `WalkingBudgetPolicy`: caller-supplied ordered network travel-time scales; one or more scales, no universal radius.
- `PedestrianRoutingOrigin`: explicit `ResolvedLocation` semantic identity and exact coordinates.
- `PedestrianGeometryPolicy`: GeoJSON/WGS84 polygon, denoise/generalize and canonical geometry policy identity.
- `PedestrianAreaPolicy`: caller/precomputed area method identity; no naive WGS84 degree-squared area computation.
- `PedestrianIsochroneEvidence`: request, snap, contours, raw/parsed lineage.
- `PedestrianAreaEvidence`: numeric area tied to exact geometry identity + area policy.
- `PedestrianDerivationEvidence`: provider-side lineage from isochrone evidence to frozen catchment/snapshot IDs.

## HTTP boundary decision

The locked Checkpoint 3.3-1 `HTTPTransport` has no request-body field. Valhalla 3.8.0 removed its legacy `json` query parameter, so mutating the locked foundation transport would be the wrong compatibility tradeoff.

Checkpoint 3.3-5 therefore defines a narrow provider-specific `ValhallaJSONTransport` protocol and a stdlib-only `UrllibValhallaJSONTransport` implementation for JSON POST. No external HTTP dependency was added.

Endpoint URL, execution headers, retry metadata and credentials are execution state and are excluded from request fingerprints/artifact identities.

## Request semantics

Canonical request fingerprint commits to:

- exact requested origin
- exact walking budget scales
- network manifest / graph-build / graph-content identity
- routing engine/version
- pedestrian profile/version and explicit costing options
- polygon/denoise/generalize semantics
- `show_locations=true`
- `reverse=false`

The actual Valhalla JSON payload uses:

- `locations[{lat, lon}]`
- `costing="pedestrian"`
- time contours converted from SiteScore seconds to Valhalla minutes
- optional `costing_options.pedestrian`
- `polygons=true`
- `show_locations=true`
- `reverse=false`

## Geometry / snap semantics

Parser accepts only canonical Polygon/MultiPolygon time-contour features for requested scales and validates longitude/latitude order and finite bounds.

Geometry canonicalization is intentionally not a GIS/topology engine. It only removes serialization-order noise by canonicalizing ring start/direction, hole order, and MultiPolygon member order. It does not calculate area or repair invalid topology.

Requested-origin and snapped network-node evidence remain distinct. Missing/partial snap evidence is `UNKNOWN`; it is never converted to zero reach. Valhalla error 171 is a separate typed provider failure reason (`no_suitable_edges_near_location`).

## Area semantics

No area calculation dependency was introduced. Caller/precomputed `PedestrianAreaEvidence` supplies `area_km2` together with an exact `PedestrianAreaPolicy` method/version identity and matching geometry identity.

A genuine explicit area value of zero is preserved. Missing contour or unresolved snap cannot manufacture zero area.

## Frozen mapping

For every requested walking scale, the builder emits:

1. one `PedestrianCatchmentArtifact` with network travel budget in seconds and a provider-side content-addressed geometry ref;
2. one `IsochroneSnapshot` whose `area_km2` is `AVAILABLE`, `DIAGNOSTIC_ONLY`, and `UNCALIBRATED` when fully evidenced.

`source_refs` include distinct network-source and routing-response `SourceMetadata.source_id` values. Network content hash and routing-response content hash are never conflated.

## Persistence / licensing

Canonical network source evidence requires `PersistenceClass.PERSIST`. Network manifest identity includes exact source content hash and release identity; mutable live OSM is not accepted as reproducible identity.

OSM policy is supplied through the existing provider policy boundary. The checkpoint can record `ODbL-1.0` and attribution requirement in `SourceMetadata`, but it does not attempt to encode or interpret broader database-license obligations in business logic.

The routing graph is bound by exact graph content hash + artifact ref + trusted network/engine compatibility artifact. No concrete filesystem/S3/database storage backend is selected.

## Failure semantics

- transport/server outage -> provider `UNAVAILABLE` failure
- HTTP 429 -> rate-limit failure
- auth rejection -> authentication failure
- Valhalla error 171 -> distinct `no_suitable_edges_near_location` invariant/coverage condition
- malformed GeoJSON -> malformed-response error
- graph/provider/request lineage mismatch -> invariant error
- missing/duplicate requested contour -> invariant error
- absent snap evidence -> provider evidence `UNKNOWN`, not zero accessibility
- explicit valid area zero -> preserved as true measured zero

No straight-line fallback exists.

## Dependency / stop boundary

Runtime dependency remains exactly `sitescore-data==0.1.0`.

No third-party GIS, HTTP, OSM, or Valhalla Python dependency was added.

Deferred:

- concrete OSM download/extract backend
- concrete graph build/deployment pipeline
- calibrated walking budgets
- calibrated snap tolerances
- production costing options
- geodesic/equal-area computation implementation
- GTFS/transit
- vehicle road accessibility
- parking
- demographic overlay
- benchmark/ECDF/normalization
- app/core integration
