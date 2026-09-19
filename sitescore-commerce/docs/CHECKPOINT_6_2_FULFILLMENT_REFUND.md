# FAZ 6.2 — Paid Fulfillment Binding + Canonical Unfulfillable Full Refund Authority

## Scope

FAZ 6.2 extends `sitescore-commerce==0.3.0` only. It does not modify frozen FAZ 3/4/5 packages and does not implement FAZ 6.3 n8n orchestration, FAZ 6.4 delivery/email, or FAZ 6.5 broad recovery scanning.

Commerce consumes the frozen SiteScore API exclusively over its authenticated HTTP `/v1` surface. It does not import `sitescore_api`, write frozen API/report tables, invoke Celery tasks, or access report artifact storage/content.

## Server authority

Browser/client/n8n values cannot author payment, analysis, report, fulfillment, or refund truth. The automation POST accepts only the URL `order_id` as a trigger and requires an empty body. The automation bearer is checked before order lookup.

The response exposes only sanitized commerce state and guidance:

- `api_version`
- `order_id`
- `order_state`
- `payment_state`
- `fulfillment_state`
- `retryable`
- `terminal`
- `next_action`

No Stripe IDs, SiteScore resource IDs, provider payloads, credentials, raw errors, or report content are returned.

## Durable analysis operation

Before SiteScore network I/O, `commerce.fulfillment_bindings` durably records:

- order identity
- immutable SiteScore target ID and base URL snapshot
- `sitescore_analysis_v1` operation version
- stable `sitescore:analysis:v1:<order_id>` idempotency key
- exact stored order `analysis_request`
- canonical request SHA-256
- later server-observed analysis/report IDs and states

Config drift does not rewrite an existing operation. Provider I/O occurs after the transaction that creates/loads the snapshot is closed.

Analysis state mapping is exact:

- `queued` -> `analysis_pending`
- `running` -> `analysis_running`
- `completed` -> `report_pending`
- `not_score_ready` -> `not_score_ready`
- `failed` -> `analysis_failed`
- `timed_out` -> `analysis_timed_out`

Network errors, auth failures, 404, 409, 429, 5xx, malformed responses, unknown states, API-version mismatch, and resource-ID mismatch do not become terminal business truth and cannot authorize refunds.

## Report binding

Report resolution is allowed only after a bound analysis is server-observed `completed`. Commerce uses the frozen canonical report resolver and stores the returned report identity. A report identity cannot be overwritten or shared across orders.

- `ready` -> `delivery_pending`
- `failed` -> `report_failed`

`delivery_pending` is the FAZ 6.2 boundary. Report content is not downloaded and no delivery grant/email is created.

## Canonical refund eligibility

Only these server-observed unfulfillable states are eligible:

- `not_score_ready` -> `analysis_not_score_ready`
- `analysis_failed` -> `analysis_failed`
- `analysis_timed_out` -> `analysis_timed_out`
- `report_failed` -> `report_failed`

Before refund authority is materialized, Commerce re-reads the exact bound SiteScore analysis/report resource and re-proves the terminal state. Cached local state alone is insufficient.

`commerce.refund_eligibility` persists the immutable reason, resource type/ID, observed terminal state, target ID, and observation timestamp.

## Stripe full-refund authority

`commerce.refund_operations` is one durable operation per order with:

- `stripe_full_refund_v1`
- stable `sitescore:refund:v1:<order_id>` provider idempotency key
- immutable eligibility identity
- exact bound PaymentIntent ID
- server-observed positive `amount_received`
- `USD`
- later Stripe Refund identity/status/evidence

Before mutation Commerce retrieves the exact FAZ 6.1 PaymentIntent and verifies local binding, order/product metadata, livemode, positive amount, and USD currency. It lists existing refunds before create.

Provider-history policy is fail-closed:

- no refunds -> create one explicit full refund
- exactly one matching SiteScore refund -> recover/reconcile it
- exactly one unattributed already-succeeded full refund -> reconcile as externally fully refunded, no second refund
- partial, multiple, mixed, or conflicting refunds -> `attention_required`, no blind top-up
- SiteScore-shaped but mismatching refund metadata -> `attention_required`

Create parameters use the explicit server-observed full amount and metadata:

- `sitescore_order_id`
- `sitescore_refund_operation=stripe_full_refund_v1`
- `sitescore_refund_reason`

Stripe API version remains explicitly pinned to `2026-07-29.dahlia`.

Refund state mapping:

- `succeeded` -> order/payment `refunded`
- `pending` -> payment `refund_pending`
- `requires_action` -> `attention_required` + `refund_pending`
- `failed` / `canceled` -> `attention_required` + `refund_failed`

The canonical terminal fulfillment reason is preserved; a successful refund does not rewrite it to a fabricated fulfillment outcome.

## Crash windows and concurrency

The implementation assumes at-least-once execution, not exactly-once delivery.

- analysis POST response loss -> repeat the exact durable POST target/key/payload
- analysis response/local bind loss -> same operation is retried
- bound analysis -> poll exact resource, do not mint another analysis identity
- report resolver response/local bind loss -> retry canonical resolver and converge on the same report identity
- refund create response loss/local bind loss -> re-prove eligibility, retrieve PaymentIntent, list refunds, recover the matching provider refund
- concurrent analysis triggers -> one durable analysis operation/binding
- concurrent refund triggers -> one local refund operation and one logical provider money effect via stable Stripe idempotency identity
- provider already fully refunded -> reconcile without a second refund
- partial/conflicting external history -> attention, never automatic top-up

No PostgreSQL transaction is intentionally held across SiteScore or Stripe network I/O.

## Migration

Migration head: `0003_fulfillment_refund`.

Tables added under schema `commerce` only:

- `fulfillment_bindings`
- `refund_eligibility`
- `refund_operations`

Downgrade removes only revision-owned tables and preserves the `commerce` schema so `commerce.alembic_version` remains valid for downgrade/upgrade cycles.

## Explicitly not implemented

- n8n workflow JSON / scheduling
- outbox dispatcher changes for orchestration
- report PDF/content download
- delivery grants
- Postmark/email
- customer-facing delivery endpoint
- broad reconciliation/recovery scanner
- refund reasons outside the four canonical unfulfillable states
- caller-selected refund amount or provider IDs
- any direct frozen SiteScore API database access
