# Checkpoint 5.0 — External API Ingress + Versioned Contract Foundation

## Package and API version

- Package: `sitescore-api==0.1.0`
- API version: `v1`
- Framework: `FastAPI==0.140.0`
- External schema runtime: `Pydantic==2.13.4`
- Frozen ingress type dependency: `sitescore-core==0.1.0`

## Route inventory

- `POST /v1/analyses`
- `GET /v1/analyses/{analysis_id}`

OpenAPI is generated from the runtime FastAPI/Pydantic definitions. There is no handwritten OpenAPI authority.

## Request contract

The POST request is a strict discriminated union keyed by the exact frozen `sector` values:

- `coffee`
- `restaurant`
- `gym`
- `beauty`

Each sector accepts only its matching `business_inputs` model plus `location` and `costs`. Unknown fields are rejected at every external model boundary. Numeric fields reject booleans, non-numeric coercion, NaN, Infinity and values that cannot be represented as a finite float.

### Location

V1 in this checkpoint accepts a U.S. address only:

- `country_code`: required and exactly `US`
- `street`: required, trimmed, non-blank
- `city`: optional, trimmed, non-blank when supplied
- `state`: optional, trimmed, non-blank when supplied
- `zip_code`: optional, trimmed, non-blank when supplied

Valid shape is `street + zip_code` or `street + city + state`.

### Business input fields

Coffee: `target_population`, `target_rate`, conservative/base/optimistic capture rates, `visit_frequency_per_month`, `average_ticket`.

Restaurant: `seats`, `turnover_per_day`, conservative/base/optimistic utilization, `average_ticket`, `operating_days_per_month`.

Gym: `target_population`, conservative/base/optimistic penetration rates, `usable_area`, `members_per_area_unit`, `monthly_membership_fee`.

Beauty: `stations`, `operating_hours_per_week`, `average_service_duration_hours`, conservative/base/optimistic utilization, `average_ticket`.

Common costs: `monthly_rent`, `fixed_labor`, `fixed_overhead`.

The API performs no revenue, score, break-even, decision, confidence, normalization or benchmark calculation. After external validation, the server-owned ingress factory constructs the exact frozen sector-specific `RevenueInput` dataclass and preserves the caller's legitimate business/cost intent.

## Authority boundary

Untrusted JSON is request intent only. It cannot provide or assert canonical scoring/readiness/result/provider authority. Unknown-field rejection blocks attempts to inject values such as category/location scores, decision, confidence, readiness flags/fingerprints, analysis fingerprints, provider manifests, benchmark/vintage data, geographic/data-quality authority, source refs or artifact refs.

The server-owned `AnalysisIngressCommand` is immutable, factory-owned, and is not a Pydantic deserialization target. It contains only server-generated operational identities and legitimate validated caller intent. It does not create or manufacture pipeline/application/core authority objects.

The frozen FAZ 4 chain remains downstream authority. `sitescore-api` does not call `sitescore.analyze.analyze`, individual core engines, category aggregation, the pipeline terminal factory, or provider clients in its route layer.

## Request and analysis identity

Every request receives a server-generated UUIDv4 `request_id`. A caller-supplied `X-Request-ID` is not adopted as authority. SiteScore response envelopes expose the server ID and all responses carry it as the `X-Request-ID` header.

POST additionally generates a distinct server UUIDv4 `analysis_id` candidate before delegating to the lifecycle port. `request_id`, `analysis_id`, future worker task identity and core `analysis_fingerprint` are separate meanings.

A successful `202` schema exists for lifecycle-port compatibility testing, but the default FAZ 5.0 backend cannot produce it because it has no durable store and cannot truthfully claim resource creation.

## Lifecycle behavior

The package defines an injected backend interface with separate submit and retrieve operations. The default backend is deliberately unavailable and contains no in-memory dictionary, process-local queue, filesystem pseudo-database, or fake task table.

Default behavior:

- valid `POST /v1/analyses` -> `503 analysis_lifecycle_unavailable`
- valid `GET /v1/analyses/{analysis_id}` -> `503 analysis_lifecycle_unavailable`

No persisted analysis resource or lifecycle state is fabricated in 5.0.

## Error envelope

All `/v1` validation/lifecycle/internal errors use one machine-readable envelope:

- `api_version`
- `request_id`
- `error.code`
- `error.message`
- optional safe validation details

Stable 5.0 concepts include:

- `request_validation_failed` -> 422
- `analysis_lifecycle_unavailable` -> 503
- `internal_server_error` -> 500
- `route_not_found` -> 404 for unknown routes
- `method_not_allowed` -> 405 for unsupported methods

Tracebacks, exception reprs, credentials, secrets, internal paths and raw authority objects are not returned.

## Explicit 5.0 boundary

```text
AUTHENTICATION: NOT_IMPLEMENTED_IN_5_0
DURABLE_ANALYSIS_LIFECYCLE: NOT_IMPLEMENTED_IN_5_0
IDEMPOTENCY: NOT_IMPLEMENTED_IN_5_0
PRODUCTION_EXTERNAL_EXPOSURE: NOT_READY
```

Also not implemented: PostgreSQL, SQLAlchemy, Alembic, Celery, Redis, retry semantics, polling lifecycle states, report/PDF, OpenAI narrative, Jinja2, WeasyPrint, Matplotlib, S3, Stripe, n8n workflows or email delivery.

## Product validity

**Mathematically validated scoring engine; empirical validation pending.**
