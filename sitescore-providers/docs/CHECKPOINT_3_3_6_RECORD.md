# Checkpoint 3.3-6 — GTFS Static Acquisition + Reachable Service Supply + TransitSnapshot

## Scope
Only pinned GTFS Schedule acquisition/parsing, service calendars, precomputed pedestrian-reachable stop membership, scheduled/frequency service-supply derivation, 168-hour profile, and frozen TransitSnapshot mapping are implemented. No GTFS Realtime, road, parking, benchmark ECDF, normalization, or core/app integration.

## Official GTFS verification
Primary source: https://gtfs.org/documentation/schedule/reference/
Overview: https://gtfs.org/documentation/overview/

Verified implementation facts:
- GTFS Schedule is a ZIP of text files; file/field names are case-sensitive and files live at ZIP root.
- agency.agency_timezone is required; all agencies in one dataset must share it. stop_times use agency timezone, not stop_timezone.
- GTFS Time is service-day time. Values after midnight use >24:00:00 (e.g. 25:35:00) and preserve originating service-day activation.
- calendar_dates modifies calendar and may be used without calendar.txt; exception_type 1 adds and 2 removes service.
- stops location_type: 0 stop/platform, 1 station, 2 entrance/exit, 3 generic node, 4 boarding area; parent_station constraints are validated.
- stop_times pickup_type=1 means no pickup and cannot create boarding supply.
- frequencies exact_times=1 is compressed exact schedule; exact_times=0 or blank is headway-based service. headway_secs is positive and windows for a trip must not overlap.
- feed_info feed_start_date/feed_end_date describe the period of complete/reliable schedule information when supplied.

## Frozen contract audit
Authoritative file: sitescore-data v0.1.0 `src/sitescore_data/schemas/transit.py`.

Frozen classes used exactly:
- TransitStopRef(feed_id, stop_id, location_type, parent_station_id, canonical_station_id, latitude, longitude, access_geometry_quality, reachable_by_walk, walk_catchment_ref, source_ref)
- TransitServiceWindow(timezone, validity_state, validity_start, validity_end, reference_dates, temporal_policy_version, service_calendar_version, profile_type, hour_bins, calendar_exceptions_applied, service_day_over_24h_semantics)
- TransitObservation(hour_of_week, scheduled_exact_departures, frequency_departure_equivalents, total_departure_equivalents)
- TransitSnapshot(snapshot_id, stops, service_window, observations, service_departure_equivalents_per_hour, benchmark_ref, source_bundle_fingerprint, source_refs, availability, data_quality, generated_at)

Also uses frozen MetricValue and SourceMetadata from `src/sitescore_data/schemas/common.py`.

CONTRACT_CHANGE_REQUIRED = 0.

## Provider contracts
Production tree: `src/sitescore_providers/transit/{models.py,client.py,parser.py,builders.py,__init__.py}`.

V1 explicitly supports one GTFS feed per TransitSourceBundle. Feed-local stop_id/trip_id/route_id/service_id are therefore never namespace-less merged across feeds.

GTFSFeedManifest pins feed ID/provider, exact release, schema/parser versions, exact ZIP content hash, and acquisition method/version. Mutable latest/current/live release labels are rejected.

TransitSourceBundle binds:
- exact feed manifest / ZIP content identity
- exact component-file hashes (separate from ZIP hash)
- calendar policy
- stop hierarchy policy
- boarding policy
- frequency policy

Its fingerprint is transit-source semantics only and excludes site pedestrian reachability.

## Acquisition / provenance
`acquire_gtfs_zip_bytes()` takes exact ZIP bytes and validates them against the pinned manifest before persistence. Download URL/storage locator is not a semantic identity input. The raw request fingerprint commits to feed ID, exact release, and ZIP content hash.

`parse_gtfs_zip()` revalidates raw request fingerprint, provider identity, ZIP content hash, media type, stored bytes, and component-file hashes. ParsedArtifact and SourceMetadata use the locked 3.3-1 foundation. ParsedGTFSFeed rejects same bytes with unrelated SourceMetadata provider/dataset/release/schema semantics.

## Parser / hierarchy semantics
V1 validates required core files, calendar/calendar_dates presence, key/reference integrity, shared agency timezone, GTFS location hierarchy, stop_times references, unique stop_sequence per trip, service_id resolution, frequency trip references and non-overlap.

Unknown extension columns are ignored semantically in V1; exact ZIP/component hashes still preserve source content lineage.

Reachability is a precomputed `ReachableTransitStopSet` bound to the exact TransitSourceBundle fingerprint and pedestrian derivation/walking-budget identity. No straight-line radius or walking router exists in this checkpoint.

Hierarchy resolution:
- reachable station/entrance/generic node resolves to station and its child platforms
- reachable platform remains that platform
- reachable boarding area resolves to its parent platform
- malformed parent hierarchy is rejected

## Service calendar / timezone / >24h
calendar weekly patterns are evaluated on the originating service date; calendar_dates exceptions override them. Calendar_dates-only feeds are supported.

168 bins are feed-local agency service-clock bins, Monday 00 through Sunday 23. No machine-local timezone conversion is used. A Monday service trip at 25:30 contributes to Tuesday 01 while retaining Monday service_id activation semantics.

This is intentionally service-clock profiling rather than elapsed-wall-clock/DST duration measurement. It follows GTFS service-day clock semantics and is independent of worker timezone.

## Trip-instance semantics
Canonical unit is unique reachable service trip instance. A scheduled trip crossing multiple reachable stops is counted once, using the earliest reachable boarding-capable departure_time under TransitBoardingPolicy. pickup_type=1 is excluded. If a reachable boarding-capable stop lacks departure_time, V1 refuses to infer/interpolate and rejects derivation rather than undercounting/zeroing it.

## frequencies.txt
- exact_times=1: deterministic exact instances at start_time + n*headway_secs while < end_time, shifted by the selected reachable stop offset from the template trip start.
- exact_times=0/blank: no fake exact timetable. V1 integrates the headway rate over shifted service-clock hour boundaries, yielding `frequency_departure_equivalents` including fractional hour-boundary contributions.
- overlapping windows and nonpositive headways are rejected.

## 168-hour representative profile
TransitWeeklyProfilePolicy V1 is explicit `median_same_weekday_hour` over caller-supplied exact reference_dates. Every weekday must be represented. Exact departure medians must remain integer because frozen TransitObservation stores exact departures as int; a fractional exact median is rejected rather than silently rounded. Frequency equivalents retain real-valued medians.

Derivation identity commits to source bundle fingerprint + reachability identity + exact weekly profile policy/date set. Changing walking catchment changes derivation identity but not TransitSourceBundle fingerprint.

## Validity / zero / missing
feed_info start/end are authoritative when both supplied. Otherwise validity can be derived from supplied feed-info boundary plus calendar range, or calendar/calendar_dates range. Out-of-validity and unknown validity never create a zero profile.

A valid feed + valid reachable stop set + no scheduled/headway instances is an AVAILABLE true-zero 168-hour profile.

Frozen TransitServiceWindow disallows out-of-range reference_dates alongside validity_start/end; therefore an OUT_OF_VALIDITY frozen snapshot carries no fabricated observations/reference dates. The requested date set remains committed through provider-side TransitWeeklyProfilePolicy identity.

## Frozen mapping
AVAILABLE snapshot:
- 168 ordered TransitObservation records
- primary MetricValue unit `departure_equivalents_per_hour`
- value = mean of 168 total departure-equivalent bins (required by frozen contract)
- ScoreEligibility.DIAGNOSTIC_ONLY
- CalibrationState.UNCALIBRATED
- benchmark_ref=None
- source_refs include GTFS SourceMetadata plus supplied pedestrian source refs

No transit score, percentile, ECDF, or normalized accessibility is produced.

## Deferred
- Multi-feed bundle/namespace merge policy
- stop_time interpolation for missing non-timepoint departures
- alternative representative-statistic policies / even-sample fractional exact medians
- GTFS Realtime / cancellations / observed reliability
- external feed discovery/latest selection
- road/parking/benchmark/normalization
