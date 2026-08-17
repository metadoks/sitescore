# sitescore-api

FAZ 5.0 external API ingress foundation for SiteScore AI.

This package provides strict Pydantic request schemas, server-owned request/analysis identity creation, an injected analysis lifecycle port, stable SiteScore error envelopes, and versioned FastAPI routes under `/v1`.

The production/default FAZ 5.0 lifecycle backend is intentionally unavailable. It does not persist analyses and therefore returns `503 analysis_lifecycle_unavailable` for valid POST/GET analysis-resource requests. Durable lifecycle, authentication, idempotency, PostgreSQL, Celery and Redis belong to FAZ 5.1.

See `docs/CHECKPOINT_5_0_EXTERNAL_API_INGRESS.md` for the exact checkpoint contract.
