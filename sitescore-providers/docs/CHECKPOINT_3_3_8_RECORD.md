# Checkpoint 3.3-8 — Parking Evidence Acquisition + ParkingSnapshot

Status: implementation complete; ready for source review.

## Scope

Implemented only parking evidence acquisition, source/coverage/eligibility semantics, static/dynamic evidence, road/pedestrian reachability binding, and frozen `ParkingSnapshot` construction.

Not implemented: road+parking composite, benchmark frame/ECDF, normalization, sitescore-app/core adapters.

## Official OSM verification

Primary references reviewed on 2026-08-13:

- https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dparking
- https://wiki.openstreetmap.org/wiki/Key:access
- https://wiki.openstreetmap.org/wiki/Street_parking
- https://wiki.openstreetmap.org/wiki/Key:capacity
- https://www.openstreetmap.org/copyright

Verified semantics used by the V1 OSM mapping adapter:

- `amenity=parking` represents a motor-vehicle parking facility and is commonly combined with `parking=*`, `access=*`, `capacity=*`, `fee=*`, and related tags.
- `access=yes`, `permissive`, `private`, `customers`, and `permit` carry different access semantics; an untagged parking facility does not provide affirmative public-access evidence for SiteScore.
- Current street-parking tagging uses `parking:left/right/both` plus side-specific legal properties such as `:access`, `:restriction`, and conditional restrictions. The older `parking:lane=*` / `parking:condition=*` scheme is deprecated.
- `no_parking`, `no_stopping`, `no_standing`, `loading_only`, and conditional restrictions cannot be treated as affirmative legal parking supply.
- `capacity=*` is an explicit count of parking spaces. This checkpoint never infers capacity from polygon area or curb length.
- OSM data is ODbL-licensed and attribution to OpenStreetMap contributors is required. No broader legal inference is encoded in the generic provider foundation.

## Frozen contract audit

Authoritative package: `sitescore-data v0.1.0`.

File: `src/sitescore_data/schemas/parking.py`

### `ParkingObservation`

Actual fields:

- `parking_id`
- `parking_mode`
- `access_class`
- `generic_public_supply_eligible`
- `capacity`
- `motor_vehicle_reachable`
- `walk_time_to_site_seconds`
- `curb_length_m`
- `occupancy`
- `available_spaces`
- `availability_timestamp`
- `source_ref`

Important frozen invariants verified directly from source:

- `generic_public_supply_eligible` iff access is PUBLIC/PERMISSIVE.
- capacity uses `spaces` and is non-negative when AVAILABLE.
- walk time uses seconds and is non-negative when AVAILABLE.
- curb length uses metres and is non-negative when AVAILABLE.
- occupancy uses ratio in `[0,1]` when AVAILABLE.
- available spaces uses spaces and is non-negative when AVAILABLE.
- occupancy AVAILABLE or available_spaces AVAILABLE requires an aware `availability_timestamp`.
- when no dynamic metric is AVAILABLE, `availability_timestamp` must be `None`.
- when both capacity and available_spaces are AVAILABLE, available_spaces must not exceed capacity.

### `ParkingSnapshot`

Actual fields:

- `snapshot_id`
- `observations`
- `mapped_public_facility_count`
- `known_public_offstreet_capacity`
- `unknown_capacity_facility_count`
- `mapped_legal_curb_length_m`
- `known_onstreet_capacity`
- `dynamic_availability_present`
- `source_refs`
- `availability`
- `data_quality`
- `score_eligibility`
- `generated_at`

Frozen summary units are deliberately separate: count, spaces, count, metres, spaces. No curb-length-to-space or polygon-area-to-capacity conversion is required or allowed by this checkpoint.

`MetricValue` and `SourceMetadata` were also audited from `src/sitescore_data/schemas/common.py`.

Disposition: `CONTRACT_CHANGE_REQUIRED = 0`.

## Provider contracts

### `ParkingSourceManifest`

Immutable/versioned source identity includes:

- source role: static inventory or dynamic availability
- source provider and dataset
- pinned release/vintage
- schema identity/version
- manifest-bound media type
- exact source content hash
- parser identity/version
- acquisition identity/version
- source authority and completeness semantics

Mutable release identities such as latest/current/live/today/now are rejected.

The locator/path is not semantic identity.

For source_provider `openstreetmap`, V1 structurally requires `COMMUNITY_MAPPED` authority and forbids `EXHAUSTIVE` completeness. Generic OSM therefore cannot self-assert authoritative true-zero inventory semantics.

### `ParkingSourceBundle`

V1 intentionally supports one canonical static inventory source plus at most one optional dynamic availability sidecar. Cross-inventory-source union/dedup is deferred rather than hidden in the builder.

### Mapping policy

`ParkingMappingPolicy` binds mapping profile/version and exact source interpretation semantics.

V1 profiles:

- `osm_parking_tags/v1`
- `normalized_parking_inventory/v1` for future municipal/provider adapters

OSM V1 access precedence is `motor_vehicle > vehicle > access`. Missing access maps to UNKNOWN, not public.

## Coverage / true zero

Provider-side `ParkingCoverageEvidence` distinguishes:

- SUFFICIENT
- UNKNOWN
- INSUFFICIENT
- FAILED
- UNSUPPORTED

True zero is only available when all of the following are affirmative:

- coverage SUFFICIENT
- source authority AUTHORITATIVE
- source completeness EXHAUSTIVE
- no unresolved eligibility/reachability axis
- zero canonical usable facilities

A generic OSM query with no records does not establish real-world zero parking and therefore produces UNKNOWN rather than AVAILABLE zero.

Provider failure/unsupported source cannot be converted into a zero ParkingSnapshot.

## Facility / capacity / curb evidence

`ParkingFacilityEvidence` preserves provider entity identity, geometry identity/type, optional source coordinate, type/access semantics, explicit capacity state/value/method, curb legality/length/method, source tags, and raw/parsed/source lineage.

Capacity states distinguish VALUE, MISSING, UNKNOWN, NOT_APPLICABLE. VALUE must be a non-negative integer; bool, NaN/inf, and negative values are rejected. No area-based capacity inference exists.

Curb legality and curb length are separate evidence. Curb length remains metres; no spaces-per-metre conversion exists. Conditional or unresolved legality remains UNKNOWN rather than legal supply.

## Eligibility

`ParkingEligibilityPolicy` V1 permits only PUBLIC/PERMISSIVE generic supply.

- PUBLIC -> ELIGIBLE
- PERMISSIVE -> ELIGIBLE
- PRIVATE/CUSTOMERS/PERMIT/RESTRICTED -> INELIGIBLE
- UNKNOWN -> UNKNOWN

Subject-property private/customer parking is not automatically promoted in V1.

On-street supply additionally requires explicit LEGAL curb semantics. RESTRICTED is ineligible; UNKNOWN remains unknown.

## Motor and pedestrian compatibility

Parking does not copy or invoke road/pedestrian routing engines.

`ParkingMotorReachabilityEvidence` binds:

- active parking source manifest identity
- road derivation identity
- graph compatibility identity
- drive-budget policy identity
- exact facility reachability records
- method/version and source refs

`ParkingPedestrianReachabilityEvidence` binds:

- active parking source manifest identity
- pedestrian derivation identity
- walking-budget policy identity
- exact facility reachability records
- walk time for REACHABLE facilities
- method/version and source refs

Foreign parking-source evidence or mismatched facility sets are rejected. No straight-line fallback exists.

Canonical usability requires ELIGIBLE + motor REACHABLE + pedestrian REACHABLE. UNKNOWN on a required axis remains unresolved and prevents a false zero/nonzero canonical supply claim.

## Static / dynamic evidence

`ParkingDynamicEvidence` is a separate provider-side immutable artifact. It preserves exact available-spaces/occupancy state/value and the source `availability_timestamp`.

Dynamic numeric values require an aware source observation timestamp. Dynamic evidence identity includes the observation timestamp; retrieval time is not part of semantic measurement identity.

No freshness threshold is invented. AVAILABLE frozen dynamic metrics are marked diagnostic/degraded with `freshness_unassessed` until a future explicit freshness policy exists.

If static capacity and dynamic available spaces are both numeric, `available_spaces <= capacity` is enforced before frozen mapping.

## Acquisition / lineage

Existing provider foundation is reused:

- `RequestFingerprint`
- `ArtifactRef` / `ArtifactStore`
- `RawAcquisitionArtifact`
- `ParsedArtifact`
- `SourceMetadata`

`ParkingRawSourceEvidence` validates manifest/provider/content/media-type/SourceMetadata coherence. Static canonical inventory requires PERSIST replay. Source bytes are re-read from `ArtifactStore` and hashed against the pinned manifest content hash.

Media type is manifest-bound. No OSM-specific hard-coded media type exists.

`ParkingRecordReader` is a narrow provider-specific decoding boundary. No PBF/GIS/HTTP third-party runtime dependency was added.

## Parser strictness / dedup

The parser canonicalizes record processing order only after semantic validation.

It rejects malformed numeric values, invalid coordinates, invalid access/curb states, invalid timestamps, and conflicting duplicate provider entity IDs.

Within one pinned source, exact identical duplicate entity evidence collapses deterministically; exact-ID conflicts reject. No distance/name/geometry fuzzy dedup is implemented.

Unknown provider fields may remain in immutable sidecar tags; malformed canonical semantics are not silently normalized away.

## Measurement identity / determinism

Parking measurement identity commits to:

- source bundle and pinned content identity
- coverage evidence
- mapping policy
- eligibility policy
- motor reachability identity
- pedestrian reachability identity
- canonical per-facility evidence identities
- capacity/curb method identities
- dynamic evidence identities and source observation timestamps
- canonical eligibility/reachability/usability decisions
- parking mapping method version

Facility and dynamic inputs are sorted by parking_id before identity construction. Caller processing order does not affect measurement identity or snapshot ID.

Excluded semantic noise includes ArtifactRef/storage locator, URL, retrieved_at, worker/retry metadata, and processing order.

Frozen primitive determinism additionally requires the same explicit `generated_at` because the frozen snapshot carries that field.

## Frozen mapping

Canonical AVAILABLE observations contain only facilities for which eligibility, motor reachability, and pedestrian reachability are affirmatively resolved. Provider-side derivation evidence preserves diagnostics for ineligible, unreachable, and unresolved facilities.

Summary metrics:

- mapped public facility count = canonical usable facilities
- known public off-street capacity = sum of explicit off-street capacities only
- unknown-capacity facility count = usable facilities without explicit capacity
- mapped legal curb length = sum of explicit legal curb lengths only
- known on-street capacity = sum of explicit on-street capacities only

No inferred parking supply is emitted.

AVAILABLE metrics remain `DIAGNOSTIC_ONLY + UNCALIBRATED`. No parking normalization or road+parking composite is produced.

## Testing / architecture

Provider suite after Checkpoint 3.3-8: 407 tests.

Parking checkpoint/architecture tests: 32.

Frozen baselines remain:

- sitescore-data: 361 tests
- sitescore-core: 86 tests

Runtime dependency remains exactly `sitescore-data==0.1.0`.

No `sitescore-core` imports or new third-party runtime dependencies were introduced.

Locked Checkpoints 3.3-1 through 3.3-7 production files are byte-for-byte unchanged.

## Deferred

- concrete production OSM extract/query adapter
- concrete municipal inventory adapters
- cross-source parking entity reconciliation
- dynamic freshness/staleness policy
- subject-property private/customer qualification policy
- calibrated coverage sufficiency policy for nonauthoritative providers
- road+parking composite COMB-005
- benchmark frame / ECDF / normalization
- app/core integration
