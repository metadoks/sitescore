# FAZ 6.1 — Stripe Webhook Payment Authority + Durable Reconciliation

## Scope

`sitescore-commerce==0.2.0` adds only Stripe webhook ingress, durable Stripe event inbox/dedupe, server-side Checkout reconciliation, narrow paid/expired state transitions, durable payment evidence, and the unpublished `order.paid.v1` outbox. No analysis/report dispatch, refund, n8n, Postmark, delivery, or 6.2+ behavior exists here.

## Payment authority

Payment truth requires all of:

1. exact raw webhook bytes verified by the official Stripe SDK using `Stripe-Signature` and the configured webhook secret;
2. durable event inbox identity/dedupe;
3. server-side retrieval of the Checkout Session and line items with the pinned Stripe API version `2026-07-29.dahlia`;
4. reconciliation against the durable 6.0 checkout operation snapshot and order binding;
5. atomic PostgreSQL state transition and outbox insertion.

A browser redirect, Checkout URL, event type, event payment fields, metadata, caller input, or n8n signal is never payment authority.

## Ingress

`POST /v1/webhooks/stripe`

- no SiteScore API-key auth;
- exact raw bytes are verified before parsing into application semantics;
- 256 KiB maximum body;
- required `Stripe-Signature`;
- 300-second signature tolerance;
- invalid/missing signatures -> 400 with no inbox/payment mutation;
- oversized body -> 413 before webhook service invocation;
- raw bodies are not persisted or logged; only SHA-256 evidence is stored.

Required configuration: `STRIPE_WEBHOOK_SECRET`, `STRIPE_EXPECTED_LIVEMODE`, existing `STRIPE_SECRET_KEY`, and exact `STRIPE_API_VERSION=2026-07-29.dahlia`.

## V1 event surface

Because FAZ 6.0 is card-only, 6.1 processes only:

- `checkout.session.completed`
- `checkout.session.expired`

Correctly signed unsupported/async-payment events are durable `ignored` triggers and never mutate order/payment state.

## Durable inbox

`commerce.stripe_event_inbox` uses `stripe_event_id` as the durable transport dedupe identity and stores event/object type, API version, livemode, event-created timestamp, raw-body SHA-256 evidence, processing state, failure/attention code, timestamps, and attempt count.

The raw-body SHA-256 is **delivery-byte evidence, not event identity**. The first accepted delivery digest is preserved for audit. Every redelivery is independently verified against its own exact raw bytes and `Stripe-Signature`; a semantically identical redelivery of the same Stripe Event ID may therefore have a different harmless JSON serialization without becoming an identity conflict. Essential signed semantics (event type, Checkout Session/object ID, API version, livemode, event-created timestamp) must still match or the duplicate fails closed.

Thus:

- same Event ID + same semantics + same bytes -> one inbox identity, retry-safe;
- same Event ID + same semantics + different valid JSON bytes -> one inbox identity, attempt evidence increments, processed duplicates return safely and `received` events resume processing;
- same Event ID + true semantic conflict -> `EventIdentityConflict`, no payment/order mutation.

## Server-side reconciliation

Before a paid transition, the server-retrieved Checkout evidence must match:

- object=`checkout.session`;
- exact Session identity;
- mode=`payment`;
- expected livemode;
- durable order `client_reference_id`;
- order/product/catalog metadata;
- exactly one line item;
- durable Stripe Price ID;
- quantity exactly 1;
- currency USD;
- status=`complete`;
- payment_status=`paid`;
- server-observed PaymentIntent identity present.

`no_payment_required` is not accepted as paid.

For expiration, provider truth must be `status=expired` and `payment_status=unpaid`.

## Webhook-first bind-loss recovery

If FAZ 6.0 created the Stripe Session but crashed before persisting the local Session binding, a verified webhook may correlate to the durable order, retrieve Stripe server-side, validate every durable operation invariant, and only then bind the previously-null local Session ID. This path does not create another Checkout Session or provider operation identity.

## State transitions

6.1 authors only:

`pending_payment/pending/not_started -> paid/paid/not_started`

or

`pending_payment/pending/not_started -> expired/expired/not_started`.

Paid cannot be downgraded by a late expiration event. Expired cannot be overwritten by later contradictory paid evidence. Contradictory terminal truth is recorded as attention rather than guessed.

## Paid outbox

The first authoritative paid transition atomically inserts exactly one `commerce.outbox_events` row with type `order.paid.v1`, unique on `(order_id, outbox_type)`. Payload is minimal order/event/version identity. `published_at` remains NULL in 6.1; there is no dispatcher and no downstream fulfillment call.

## Network/transaction boundary

No PostgreSQL transaction spans Stripe network I/O. The flow is short inbox transaction -> network retrieve -> short row-locked reconciliation transaction. Retry/crash convergence relies on durable event identity, monotonic state transitions, DB uniqueness, and server-side reconciliation; no exactly-once claim is made.
