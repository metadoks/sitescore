# FAZ 3.3 — Checkpoint 3.3-2: US Geocoding + Census Geography Resolution

Status: implementation complete; review pending.

## Scope

Implemented only the US V1 Census Geocoder / Census GeoLookup boundary:

`address -> Census geocode raw response -> parsed artifact -> typed geocode evidence -> acceptance policy -> coordinate GeoLookup -> typed geography evidence -> GeographyRef[] -> ResolvedLocation`

Not implemented: ACS demographics, Mapbox fallback, Overture, OSM, Valhalla, GTFS, road, parking, benchmark builders, normalization, sitescore-core/app integration.

## Authoritative frozen contracts audited

From `sitescore-data-v0.1.0.zip`:

- `src/sitescore_data/schemas/geography.py::GeographyRef`
  - `geography_type`
  - `geography_id`
  - `name`
  - `country_code`
  - `source_ref`
  - `source_version`
- `src/sitescore_data/schemas/geography.py::ResolvedLocation`
  - `latitude`
  - `longitude`
  - `formatted_address`
  - `country_code`
  - `geography_refs`
  - `source_refs`
  - `resolution_method_version`
  - `generated_at`

No frozen schema change was required.

## Official Census verification (checked 2026-08-12)

Primary API documentation:

- https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html
- https://www.census.gov/programs-surveys/geography/technical-documentation/complete-technical-documentation/census-geocoder.html
- https://www.census.gov/data/developers/data-sets/Geocoding-services.html

Policy / use:

- https://www.census.gov/data/developers/about/terms-of-service.html
- https://www.census.gov/about/policies/open-gov.html

TIGERweb layer naming/reference:

- https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer
- https://tigerweb.geo.census.gov/arcgis/rest/services/Census2020/tigerWMS_Census2020/MapServer

Verified API semantics:

- single structured address endpoint: `/geocoder/locations/address`
- coordinate geography endpoint: `/geocoder/geographies/coordinates`
- structured address requires `street` plus ZIP, or `street` + city + state
- `x` is longitude and `y` is latitude
- geocoder locator identity is selected by `benchmark`
- geography identity is selected by `vintage`
- `layers` may explicitly request geography layers
- Census documents that `Current` benchmark/vintage values change over time; canonical SiteScore manifests therefore reject `Current`
- response JSON uses `result.input.benchmark`, `result.addressMatches`, coordinates `x/y`, `matchedAddress`, and optional `tigerLine` evidence
- geography responses use `result.geographies` and geography records such as `GEOID` and `NAME`
- Census Geocoder covers the United States, Puerto Rico, and U.S. Island Areas; Checkpoint 3.3-2 intentionally limits final `ResolvedLocation` construction to the 50 states + DC until territory country-code policy is explicit
- official API documentation states batch files are limited to 10,000 records; batch is out of scope here
- no documented numeric single-record request-rate limit was found in the reviewed geocoder documentation; Census Terms reserve the right to impose access/call/use limitations

## HTTP boundary

`sitescore_providers.http` introduces:

- `HTTPRequest`
- `HTTPResponse`
- `HTTPTransport` protocol
- `UrllibHTTPTransport`

The concrete transport uses Python stdlib only. No `requests`, `httpx`, `aiohttp`, retry framework, cache, auth framework, or provider-specific transport logic was added.

Default tests use fake transport only; they make no network calls.

## Census manifest

`CensusGeographyManifest` carries:

- explicit `manifest_version`
- pinned `geocoder_benchmark`
- pinned `geography_vintage`
- ordered supported geography-layer specs
- deterministic content identity

Mutable values containing `Current` are rejected for canonical manifest identity.

Core layers:

- State
- County
- Census Tract
- Census Block Group

Optional supported mappings:

- CBSA from Metropolitan **or** Micropolitan Statistical Area response layers
- Metropolitan Division
- CSA
- ZCTA, with version-dependent Census response-key aliases

Missing optional layers are omitted, never fabricated.

## Match semantics

Provider-local states:

- `MATCHED`: exactly one Census address match
- `NO_MATCH`: Census established no address match in this response
- `AMBIGUOUS`: multiple Census address matches

These are provider observations, not frozen `MISSING/UNKNOWN/UNAVAILABLE` states and not claims about real-world address existence.

`GeocodeAcceptancePolicy` is explicit/versioned. V1 accepts a single structurally valid match, rejects ambiguous/no-match evidence, and records fallback eligibility without executing any fallback. Optional `accepted_match_types` exists only for an explicit provider match-type value; the current official JSON documentation does not define a required canonical match-type field, so no match-type threshold/value is invented.

Census documentation describes returned coordinates as calculated/interpolated or approximated along MAF/TIGER address ranges. The provider evidence therefore records `ADDRESS_RANGE_INTERPOLATED` rather than inventing a numeric confidence score.

## Geography and country semantics

GeoLookup uses the accepted coordinate with the same pinned manifest benchmark/vintage. Geography records use Census-returned `GEOID` directly; no FIPS/GEOID concatenation is synthesized.

`COUNTRY=US` is derived only when a State geography is resolved and its state FIPS is within the 50-state + DC US V1 set. Puerto Rico and Island Areas are rejected at the final US V1 builder boundary rather than silently coerced to US country semantics.

## Persistence / policy

No Census legal rule was hard-coded into foundation classes.

The client requires a caller-supplied `ProviderPolicyDecision`. `SOURCE_POLICY` remains unresolved and is rejected before artifact acquisition; `DO_NOT_PERSIST` is also rejected because the locked raw artifact contract requires a resolvable artifact reference. Concrete `PERSIST` or `TRANSIENT` decisions may proceed through the caller-selected `ArtifactStore` boundary.

Official Census Terms permit using the API to retrieve, search, display, analyze and view Census data, and Census describes its public data as open data available for use/re-use. The reviewed geocoder/API terms did not publish a provider-specific cache TTL. No default persistence duration was therefore invented in Checkpoint 3.3-2.

## Lineage

Every successful HTTP response becomes a locked-foundation `RawAcquisitionArtifact` with exact-byte SHA-256 identity. JSON parsing then passes through `build_parsed_artifact()` with fixed operation-specific parser ID/version. Typed Census evidence is built only after that raw/parsed lineage exists.

Geocoding and coordinate geography lookups remain separate raw artifacts and therefore produce separate `SourceMetadata` records through the locked `build_source_metadata()` path.

## Failure semantics

Execution failures use locked provider acquisition semantics:

- transport outage -> provider failure / unavailable
- HTTP 429 -> provider failure / rate limit
- HTTP 401/403 -> provider failure / authentication
- HTTP 5xx -> provider failure / unavailable
- rejected HTTP request -> provider failure / invariant
- malformed UTF-8/JSON -> `ProviderMalformedResponseError`
- malformed/inconsistent Census response schema -> `ProviderMalformedResponseError` / `ProviderInvariantError`

`NO_MATCH`, `AMBIGUOUS`, missing optional geography layers and unsupported geography are domain/provider evidence states, not execution errors and not negative location scores.

## Deferred blockers / calibration

- exact production benchmark/vintage manifest values: deployment/config decision; no `latest` discovery
- Mapbox or other fallback: later checkpoint/decision
- territory/PR ISO country-code and product-scope policy
- empirical geocoder acceptance/coverage analysis, if later required
- provider-specific operational throttling/retry SLOs; no documented numeric single-record Census rate limit was found
- any ACS demographic compatibility work
