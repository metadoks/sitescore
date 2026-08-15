# sitescore-providers

Provider-neutral acquisition, artifact identity, persistence-policy, error, and provenance foundation for SiteScore FAZ 3.3.

Checkpoint 3.3-1 deliberately contains no concrete HTTP provider, geocoder, ACS, competition, routing, GTFS, parking, benchmark, normalization, app, or core adapter implementation.

## Checkpoint 3.3-5 execution/lineage hardening

See `docs/CHECKPOINT_3_3_5_EXECUTION_LINEAGE_HARDENING.md` for the final source-level hardening audit covering Valhalla execution limits, trusted deployment binding, warning preservation, show-locations role resolution, and network/graph provenance boundaries.

## Checkpoint 3.3-6
GTFS Static acquisition + reachable scheduled/headway service supply + frozen TransitSnapshot is implemented in `sitescore_providers.transit`. See `docs/CHECKPOINT_3_3_6_RECORD.md`. No GTFS Realtime, road, parking, benchmark ECDF, normalization, or core/app integration is included.
