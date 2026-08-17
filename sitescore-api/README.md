# sitescore-api

`sitescore-api==0.2.0` is the FAZ 5.1 machine-consumer boundary for SiteScore AI.

## V1 resource model

- `POST /v1/analyses` — Bearer scope `analysis:write`, required `Idempotency-Key`, durable `202` acceptance.
- `GET /v1/analyses/{analysis_id}` — Bearer scope `analysis:read`, consumer-owned polling resource.
- Public states: `queued`, `running`, `completed`, `not_score_ready`, `failed`, `timed_out`.
- Cancellation: **NOT_SUPPORTED**.
- Callback/webhook delivery: **NONE**. V1 uses polling.

PostgreSQL is the sole durable analysis/lifecycle/idempotency/auth metadata truth. Redis is broker transport only; Celery result state is not a public resource authority.

The currently frozen COMB-005 road/parking authority is not approved. Therefore the real locked canonical production path is expected to terminate `not_score_ready`; this package does not manufacture a score or a `completed` result. `completed` remains a guarded lifecycle state that can be persisted only from a canonical frozen application analysis result.

Deployment configuration is mandatory: PostgreSQL URL, Redis broker URL, API-key pepper, deadline settings, and a server-owned canonical execution evidence source. Missing production configuration fails closed.

See `docs/CHECKPOINT_5_1_API_CONSUMER_LIFECYCLE.md` for the complete consumer and operational contract.

> Mathematically validated scoring engine; empirical validation pending.
