# FAZ 6.0 — Commerce / Order + Stripe Checkout

## Identity and scope

- Package: `sitescore-commerce==0.1.0`
- Frozen base: `0e370940ee5c8c1253db72fa7e33078fb4ef3b2c`
- Branch: `faz6/6-0-commerce-order-checkout`
- Route: `POST /v1/orders`
- Stripe SDK: `15.4.0`
- Stripe API version: `2026-07-29.dahlia`
- Migration: `0001_commerce_order_checkout`

## Authority boundary

6.0 owns order identity, normalized purchase intent persistence, server product selection, Checkout request construction, caller idempotency and durable Checkout binding. It does not own scoring, readiness, financial math, decision, confidence, report facts or PDF truth. Checkout creation, Checkout URL existence, browser success/cancel return and Stripe object IDs are not payment proof.

Payment authority is deliberately deferred to 6.1.

## Purchase intent and response

`POST /v1/orders` accepts only `product_code=location_report_v1`, customer email and the frozen-compatible four-sector analysis request. Models use `extra=forbid`; caller amount/currency/Price ID/quantity/discount/coupon/payment fields/redirect URLs/Stripe metadata/analysis and report IDs are rejected.

Response exposes only server request/order IDs, product code, exact initial state tuple, hosted Checkout URL and optional Checkout expiry. Internal hashes, provider idempotency identity and Stripe Session ID stay private.

## Product catalog and Checkout

The V1 server catalog fixes catalog version `v1`, quantity `1`, currency expectation `USD`, and selects `STRIPE_PRICE_LOCATION_REPORT_V1` from deployment configuration. Stripe receives an existing Price ID; there is no caller-derived `price_data`.

Checkout parameters are hosted one-time payment, `payment_method_types=[card]`, server success/cancel URLs, customer email, exact order/client-reference metadata, and PaymentIntent order/product metadata. Outgoing requests explicitly set Stripe API version `2026-07-29.dahlia`.

## Persistence and state

Commerce uses PostgreSQL schema `commerce` with its own `commerce.alembic_version` and tables `orders`, `order_idempotency`, `checkout_sessions`. Database check constraints close the three state sets. 6.0 only authors `pending_payment / pending / not_started`.

No frozen SiteScore table or migration namespace is written.

## Idempotency and external-call uncertainty

Caller `Idempotency-Key` is validated to at most 200 UTF-8 bytes and stored only as SHA-256 digest. A canonical normalized purchase-intent SHA-256 binds the key to content. Same key/same content returns the same durable order; same key/different content conflicts; database uniqueness resolves concurrent creates.

Stripe idempotency is server-owned: `sitescore:checkout:v1:<order_id>`. The order and Checkout operation row are committed before the provider call, and no database transaction remains open across Stripe I/O. Provider timeout or dropped response leaves the same order available for retry with the same operation key and same parameters. A Checkout URL is returned only after provider response binding is validated and persisted. If the provider succeeded but local binding fails, no unpersisted URL is returned and retry converges through Stripe idempotency.

## Security and redirects

Secrets are environment-only. Production success/cancel bases require HTTPS, embedded credentials/fragments/queries are rejected, and non-production HTTP is limited to localhost. Browser redirects are presentation correlation only and do not mutate commerce state.

Provider and database exception internals are not exposed through the API error contract.

## Deferred

Webhook verification/reconciliation, paid transition, paid outbox, SiteScore analysis/report dispatch, refunds, n8n, delivery grants and Postmark belong to 6.1+ and are not implemented here.
