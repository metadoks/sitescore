# SiteScore AI — FAZ 5.1 API Consumer Reliability + Execution Lifecycle

## Status and versions

- Package: `sitescore-api==0.2.0`
- External API: `/v1`
- Base checkpoint: locked FAZ 5.0
- PostgreSQL: durable product truth
- Redis: broker transport only
- Celery: execution infrastructure only; task results are ignored
- Frozen provider package: `sitescore-providers==0.1.0`

> Mathematically validated scoring engine; empirical validation pending.

## Authentication, ownership, and idempotency

V1 uses scoped machine-consumer Bearer service keys:

```http
Authorization: Bearer ssk1_<public-key-id>.<secret>
```

PostgreSQL stores only an HMAC-SHA256 verifier produced with a server-owned pepper. Raw secrets are never persisted. POST requires `analysis:write`; GET requires `analysis:read`. Every analysis belongs to one authenticated `consumer_id`; missing and foreign analysis IDs both return `404 analysis_not_found`.

`Idempotency-Key` is mandatory, opaque, nonblank/control-free, and limited to 200 UTF-8 bytes. The canonical request hash is SHA-256 over deterministic JSON serialization of the validated Pydantic request intent only. PostgreSQL UNIQUE `(consumer_id, idempotency_key)` is the concurrency authority. Same consumer/key/payload returns the same analysis resource; different payload is `409 idempotency_conflict`; another consumer has an independent namespace.

## Durable acceptance and outbox

POST atomically persists:

```text
analyses(state=queued)
dispatch_outbox(analysis_id, persisted task_id)
COMMIT
```

Broker publication happens only after durable acceptance. Redis failure does not erase either row. Redispatch reuses the persisted internal task ID. Celery messages contain only `analysis_id`; API credentials, caller result bodies, and canonical result objects never enter the broker payload.

## Public lifecycle

Exact V1 states:

```text
queued
running
completed
not_score_ready
failed
timed_out
```

Terminal states are immutable. Execution uses a deterministic PostgreSQL session-level advisory lock plus row-state checks. The SQLAlchemy physical connection remains pinned for the entire advisory-lock lifetime, preventing a pooled connection from making the same session lock re-entrant across concurrent workers.

The server owns durable `deadline_at`; timeout truth is reconciled by worker execution, periodic reconciliation, and owner-scoped GET. Redis/Celery state is never public lifecycle authority.

## Hardened canonical provider acquisition authority

### Removed post-provider seam

Production no longer supports `SITESCORE_EVIDENCE_SOURCE_FACTORY`. A deployment cannot provide an arbitrary object whose `acquire()` method returns assembled `ExecutionEvidence`, `ResolvedLocation`, frozen snapshots, source metadata, or benchmark distributions.

The only production factory hook is:

```text
SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY=<module:callable>
```

It must return the **exact** `CanonicalAcquisitionDeployment` type. The runtime then constructs `CanonicalProviderEvidenceSource` itself. If the deployment factory is absent, execution fails closed through `MissingExecutionEvidenceSource`.

The explicit `build_runtime(..., evidence_source=...)` argument remains an in-process test seam only; it is not reachable through production environment configuration.

### Allowed deployment boundaries

`CanonicalAcquisitionDeployment` may supply only server-owned configuration and true external boundaries:

- generic provider HTTP transport;
- Valhalla JSON transport;
- artifact store;
- raw deployment artifact/reader loader;
- server-owned benchmark artifact loader;
- pinned Census, ACS, pedestrian, Overture, and GTFS manifests/policies;
- provider credentials and endpoint configuration;
- server-owned quality configuration.

The raw artifact loader may provide bytes, decoded raw Overture records, precomputed pedestrian area values bound later to exact contour geometry identities, and raw transit reachable-stop IDs. It does not return frozen `ExecutionEvidence`, `DemographicSnapshot`, `IsochroneSnapshot`, `CompetitionSnapshot`, `TransitSnapshot`, or provider-built `ResolvedLocation`.

The benchmark loader is a distinct server-owned artifact authority and must return the exact V1 set of typed `BenchmarkDistributionArtifact` objects.

### External request to frozen provider chain

A durable 5.0 `AnalysisIngressCommand` contains caller intent but no provider authority. `CanonicalProviderEvidenceSource` builds authority server-side:

```text
AddressIntent
-> CensusAddressRequest using pinned benchmark/vintage/layers
-> CensusGeocoderClient acquire_geocode
-> persisted raw artifact
-> canonical Census parse_geocode_evidence
-> server GeocodeAcceptancePolicy
-> Census acquire_geography at accepted provider coordinates
-> canonical geography parsing / source lineage
-> build_resolved_location

ResolvedLocation
-> deterministic ACS query plan
-> ACSClient acquisition of every chunk
-> canonical statistical parsing
-> source metadata / evidence bundle
-> build_demographic_snapshot

ResolvedLocation
-> PedestrianIsochroneRequest from provider-built coordinates
-> PedestrianIsochroneClient / Valhalla transport
-> canonical Valhalla parsing
-> pinned network-byte hash verification
-> routing/network SourceMetadata
-> area evidence bound to exact contour geometry identities
-> build_pedestrian_frozen_result

ResolvedLocation + pedestrian catchments
-> pinned Overture partition descriptors/bytes/decoded rows
-> exact content-hash verification
-> build_partition_raw_artifact
-> parse_overture_partition
-> server-owned catchment policy
-> build_competition_snapshot

ResolvedLocation + pedestrian derivation
-> pinned GTFS ZIP bytes
-> acquire_gtfs_zip_bytes content-hash verification
-> parse_gtfs_zip
-> server-owned ReachableTransitStopSet bound to bundle/pedestrian identities
-> build_transit_snapshot

server-owned benchmark artifact loader
-> exact six BenchmarkDistributionArtifact values

provider-built typed evidence
-> frozen metrics
-> frozen benchmark normalization
-> frozen COMB-005
-> frozen normalized feature assembly
-> frozen readiness
-> frozen application gate
```

Caller JSON cannot assert trusted coordinates, provider manifests, compatibility/acceptance policies, persistence policy, provider source metadata, frozen snapshots, benchmark distributions, coverage level, input quality, scoring readiness, or result authority.

## Current canonical production truth

Frozen COMB-005 has no approved production road/parking composite policy. Its current canonical result is `POLICY_NOT_APPROVED` with no numeric score. The real locked production path therefore remains:

```text
queued -> running -> not_score_ready
```

For `NOT_SCORE_READY`, the canonical executor persists readiness/reason projection and **does not call core analyze**.

`completed` remains modeled but is not claimed reachable under the current locked model. It may be persisted only from the server-factory-owned capability bound to a genuine canonical frozen `ApplicationAnalysisResult`. Plain JSON, caller flags, fingerprints, detached DTOs, or stored request payloads cannot authorize `completed`.

## POST /v1/analyses

Required headers:

```http
Authorization: Bearer ...
Idempotency-Key: ...
```

A successful new resource or same-payload replay returns HTTP 202 with fresh server UUIDv4 `request_id`, durable UUIDv4 `analysis_id`, and current public state. Internal `task_id` is never returned. Nonterminal responses include `Retry-After`.

## GET /v1/analyses/{analysis_id}

Authenticated owner polling returns PostgreSQL truth:

- `queued` / `running`: nonterminal, poll again;
- `completed`: guarded canonical result;
- `not_score_ready`: no scored result, canonical readiness projection;
- `failed`: safe terminal execution metadata;
- `timed_out`: stable deadline terminal metadata.

V1 cancellation is **NOT_SUPPORTED**. Callback/webhook delivery is **NONE**; future n8n integration polls this API and must reuse the same Idempotency-Key after uncertain POST transport outcomes.

## Migrations and configuration

Alembic is production schema authority; `create_all()` is not used. Initial migration creates consumers, service keys, analyses, and dispatch outbox with FK/UNIQUE/CHECK/index constraints.

Required production configuration includes PostgreSQL URL, Redis broker URL, API-key pepper, deadline/worker limits, and—when canonical execution is enabled—`SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY` plus the deployment-owned provider credentials, manifests, policies, external boundaries, and benchmark artifacts.

No real credentials are committed. Missing required execution configuration fails closed. Persisted/public errors must not contain Authorization values, API-key secrets, provider credentials, or tracebacks.

## Explicitly out of scope

FAZ 5.1 does not implement Stripe/payment, payment webhooks, report endpoints/generation, OpenAI narrative, Jinja2/WeasyPrint/Matplotlib, S3 report delivery, n8n workflow JSON, customer email delivery, frontend account UI, empirical calibration/validation, V2/Compare/Find, or FAZ 6+ functionality.
