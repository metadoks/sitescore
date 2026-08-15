# Checkpoint 3.3-6 Transit Hardening

## TRANSIT-001
`ReachableTransitStopSet.identity` now commits to `walk_catchment_ref` and
`access_geometry_quality`, because both are emitted into frozen `TransitStopRef`
semantics. The GTFS `TransitSourceBundle.fingerprint` remains transit-source-only
and is intentionally unchanged by pedestrian/site reachability semantics.

## TRANSIT-002
A trip `service_id` absent from `calendar.txt` is resolvable through
`calendar_dates.txt` only when at least one `exception_type=1` row explicitly
activates that service. Removal-only (`exception_type=2`) rows cannot establish a
calendar-dates-only service and are rejected when such a service is referenced by
a trip. Base-calendar services may still be removed by exception_type=2 rows.

No GTFS Realtime, road, parking, ECDF, normalization, or core/app integration was
added.
