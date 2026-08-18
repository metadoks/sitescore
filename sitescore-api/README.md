# sitescore-api

`sitescore-api==0.3.0` preserves the locked FAZ 5.1 analysis lifecycle and adds the FAZ 5.5 delivery-ready report artifact resource boundary.

## V1 resources

Analysis endpoints remain:

- `POST /v1/analyses` — Bearer scope `analysis:write`, required `Idempotency-Key`, durable `202` acceptance.
- `GET /v1/analyses/{analysis_id}` — Bearer scope `analysis:read`, consumer-owned polling resource.

Report artifact endpoints are:

- `POST /v1/reports` — Bearer scope `report:write`; body is exactly `{analysis_id}` and resolves an already-created durable artifact.
- `GET /v1/reports/{report_id}` — Bearer scope `report:read`; consumer-owned metadata.
- `GET /v1/reports/{report_id}/content` — Bearer scope `report:read`; authenticated, integrity-verified PDF bytes.

`POST /v1/reports` is **not** a generation endpoint. It never reruns analysis and never reconstructs report authority from `AnalysisModel.result_body`, JSON, fingerprints, IDs, hashes, or caller values.

## Live canonical report generation

The only report-generation authority is the exact live worker result:

```text
CanonicalAnalysisExecutor
-> CanonicalCompletedOutcome
-> exact factory-owned ApplicationAnalysisResult
-> sitescore-report 0.3.0 canonical facts/domain/narrative/rendering
-> exact in-memory PDF bytes
-> SHA-256
-> private S3-compatible object
-> PostgreSQL report metadata/resource row
```

If report rendering or object storage fails after analytical success, the analysis remains `completed` while the report becomes terminal `failed`. A failed report has no downloadable storage contract and V1 does not regenerate it.

The currently frozen COMB-005 road/parking authority remains not approved, so the real production acquisition path is still expected to terminate `not_score_ready`; 5.5 does not manufacture a scored report from that state.

## Durable truth and storage

- PostgreSQL is durable truth for consumers, API keys, analyses, report IDs, report state, ownership binding, provenance, SHA-256, MIME type, size, safe filename, and private storage locator.
- Private S3-compatible object storage contains PDF bytes only.
- Redis/Celery remain transport only.
- PDF bytes are not stored in PostgreSQL.
- `storage_key`, bucket, provider credentials, and endpoint configuration are never returned to callers.
- Content retrieval performs object existence/size checks, exact SHA-256 verification, and `%PDF-` signature verification before streaming.
- ETag is not treated as a content hash.

The server owns object keys and filenames. Current artifact identity is versioned as `sitescore-report-artifact-v1` with uniqueness on `(analysis_id, report_artifact_version)`.

## Explicit exclusions

FAZ 5.5 does not implement payment/Stripe, n8n, email delivery, commercial order state, frontend behavior, callbacks/webhooks, or FAZ 6 orchestration.

See:

- `docs/CHECKPOINT_5_1_API_CONSUMER_LIFECYCLE.md`
- `docs/CHECKPOINT_5_5_DELIVERY_READY_REPORT_ARTIFACT.md`

> Mathematically validated scoring engine; empirical validation pending.
