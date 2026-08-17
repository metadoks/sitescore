# sitescore-api

`sitescore-api==0.2.0` is the FAZ 5.1 machine-consumer boundary for SiteScore AI.

## V1 resource model

- `POST /v1/analyses` — Bearer scope `analysis:write`, required `Idempotency-Key`, durable `202` acceptance.
- `GET /v1/analyses/{analysis_id}` — Bearer scope `analysis:read`, consumer-owned polling resource.
- Public states: `queued`, `running`, `completed`, `not_score_ready`, `failed`, `timed_out`.
- Cancellation: **NOT_SUPPORTED**.
- Callback/webhook delivery: **NONE**. V1 uses polling.

PostgreSQL is the sole durable analysis/lifecycle/idempotency/auth metadata truth. Redis is broker transport only; Celery result state is not a public resource authority.

## Canonical provider acquisition

Production execution does **not** accept a plugin that returns assembled `ExecutionEvidence` or frozen snapshots. The former `SITESCORE_EVIDENCE_SOURCE_FACTORY` seam is removed.

When execution is enabled, `SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY` must return the exact server-owned `CanonicalAcquisitionDeployment`. That deployment supplies only true external boundaries and pinned server configuration: HTTP/Valhalla transports, artifact/reader boundaries, benchmark artifact authority, credentials, manifests, policies, and quality configuration.

`sitescore-api` itself then performs the frozen public authority chain:

```text
external AddressIntent
-> Census address + geography acquisition / parsing / lineage
-> ResolvedLocation
-> ACS acquisition / statistical evidence / DemographicSnapshot
-> Valhalla acquisition / parsing / pedestrian frozen result
-> Overture partition lineage / CompetitionSnapshot
-> GTFS acquisition / parsing / TransitSnapshot
-> server-owned BenchmarkDistributionArtifact loading
-> metrics / normalization / readiness / application gate
```

Caller JSON cannot supply trusted coordinates, provider manifests/policies, snapshots, benchmark distributions, source metadata, coverage authority, or input-quality authority. Missing deployment configuration fails closed.

The currently frozen COMB-005 road/parking authority is not approved. Therefore the real locked canonical production path is expected to terminate `not_score_ready`; this package does not manufacture a score or a `completed` result. `completed` remains a guarded lifecycle state that can be persisted only from a canonical frozen application analysis result.

See `docs/CHECKPOINT_5_1_API_CONSUMER_LIFECYCLE.md` for the complete consumer and operational contract.

> Mathematically validated scoring engine; empirical validation pending.
