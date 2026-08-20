# SiteScore Commerce — FAZ 6.5 Recovery / Reconciliation Runbook

## Authority boundary

The recovery scanner is a bounded operational convergence mechanism. It is **not** a second business-authority layer.

It may only re-prove or replay authority already owned by the existing commerce/provider contracts:

- verified Stripe Event inbox recovery uses the original durable Stripe event identity and stored candidate-order correlation;
- missing-webhook recovery uses a fresh server-side retrieval of the exact bound Checkout Session and writes a distinct `stripe_checkout_server_poll_v1` receipt only when that poll wins the atomic pending → paid/expired transition;
- paid-outbox recovery sends or replays the exact durable `order.paid.v1` outbox event identity;
- downstream analysis/report/refund/delivery convergence remains owned by the locked n8n order workflow and existing commerce state machines.

Recovery never authors scoring, readiness, financial, report, payment, refund, fulfillment, delivery, or provider acceptance truth.

## Scheduler boundary

Production scheduling is the separate native n8n workflow:

`automation/n8n/workflows/sitescore-recovery-schedule-v1.json`

It is intentionally only:

`Schedule Trigger (5 minutes) -> POST Commerce /v1/automation/recovery/run -> stop`

The request uses the existing `COMMERCE_AUTOMATION_API_KEY`, has an empty body, and cannot select an order, state, timestamp, provider result, retry count, batch size, or recovery class. The scheduler has no Stripe, Postmark, SiteScore service, database, Redis, Celery, S3, delivery-token, customer, or report credentials/material.

The locked `sitescore-order-paid-v1` workflow remains the downstream convergence engine and is not redesigned by FAZ 6.5.

## Server-owned defaults and bounds

| Setting | Default | Bound |
| --- | ---: | ---: |
| Scheduler interval | 5 min | workflow-owned |
| `COMMERCE_RECOVERY_BATCH_SIZE` | 10 | 1–100 |
| `COMMERCE_RECOVERY_STALE_INBOX_SECONDS` | 120 s | 30–86400 |
| `COMMERCE_RECOVERY_PENDING_PAYMENT_SECONDS` | 300 s | 60–86400 |
| `COMMERCE_RECOVERY_PUBLISHED_REPLAY_SECONDS` | 1200 s | 120–604800 |
| `COMMERCE_RECOVERY_LEASE_SECONDS` | 120 s | 30–900 |
| `COMMERCE_RECOVERY_MAX_BACKOFF_SECONDS` | 3600 s | 60–86400 |

These are deployment configuration, never caller request fields.

## Durable recovery records

Migration `0005_recovery_reconciliation` owns:

- `recovery_runs`: aggregate counts only;
- `recovery_state`: deterministic eligibility, attempt/failure counters, next-attempt time, sanitized last action/outcome/error, and expiring UUID lease;
- `payment_poll_receipts`: immutable server-poll transition evidence with exact bound session observations and canonical evidence SHA-256;
- `outbox_replay_audit`: exact event replay attempt/result evidence;
- `recovery_findings`: sanitized operator-attention codes;
- `stripe_event_inbox.candidate_order_id`: the original verified Event candidate order correlation required for crash-safe `received`-row resumption.

No raw provider response body, secret, customer email, report bytes, private storage URL, raw/reversible delivery token, or n8n execution payload is persisted by these recovery records.

## Claim and crash model

Recovery is at-least-once and idempotent, never exactly-once.

1. bounded candidates are selected deterministically;
2. a recovery-state row is leased with `FOR UPDATE SKIP LOCKED`;
3. the lease transaction commits **before** any Stripe or n8n network I/O;
4. provider/transport work occurs with no recovery DB transaction or row lock held;
5. after I/O, the exact lease token and non-expired lease are re-proved before any result is written;
6. an expired or replaced lease cannot be finalized by a stale worker;
7. retryable/uncertain results use bounded exponential backoff;
8. non-retryable contract/auth/invariant findings are aged out of the hot loop and surfaced as sanitized operator attention.

## Recovery classes

### A — stale verified Stripe inbox `received`

Recovery uses the **original** real Stripe event ID and durable event metadata. The durable candidate order ID must exactly match the claimed order before provider I/O. Fresh Stripe Checkout evidence must then satisfy the existing API version, livemode, session, metadata, line-item, product, price, quantity, and payment/expiry authority checks. Existing `processed`, `ignored`, and `attention_required` rows are not reopened.

### B — missing webhook / server Checkout poll

Only the exact locally bound Checkout Session is retrieved. Outcomes:

- `complete + paid + payment_intent_id` → atomic paid transition plus exactly one `order.paid.v1` outbox;
- `expired + unpaid + no payment_intent_id` → atomic expired transition;
- valid nonterminal state → defer;
- contradictory or binding-invalid evidence → sanitized attention.

The poll path never creates a fake Stripe Event, fake Stripe inbox row, or fake `last_reconciliation_event_id`. Webhook and poll share the same locked payment-transition core but retain distinct authority records.

### C — unpublished paid outbox

The existing durable outbox UUID/order/type/original `created_at` is sent. Only confirmed 2xx marks that same row published. Timeout/connection loss stays uncertain; 429/5xx stays retryable and unpublished.

### D — published stale nonterminal order

The exact same already-published outbox identity is replayed. `published_at` is history and is never cleared/replaced. Each replay gets a durable replay-audit row; transport acceptance does not itself create business truth.

### E — downstream stuck convergence

Recovery replays the exact paid outbox so the locked order workflow re-enters commerce-owned `/advance` and `/deliver` state machines. The scanner does not call frozen analysis/report APIs, Stripe refund APIs, Postmark, or delivery providers directly.

### F — invariant corruption

Missing/duplicate/contradictory authority artifacts are not synthesized or repaired. Recovery records a sanitized finding and stops normal hot-loop retries for that candidate. Existing `attention_required` business states are not automatically reopened.

## Transport classification to n8n

- confirmed 2xx → transport accepted;
- timeout/connection/response loss → uncertain;
- 429 or 5xx → retryable rejection;
- 401/403 → attention (`n8n_auth_rejected`);
- 400/422 → attention (`n8n_contract_rejected`);
- other unexpected responses → fail-closed attention.

These classifications only drive replay scheduling. They never imply paid, fulfilled, delivered, refunded, or provider-accepted business state.

## Protected API response

`POST /v1/automation/recovery/run` requires the existing automation bearer and exactly zero request-body bytes. Its response is deliberately aggregate-only:

- `api_version`
- `run_id`
- `claimed`
- `reconciled`
- `published`
- `replayed`
- `deferred`
- `attention`

Do not add per-order IDs, Stripe IDs, provider payloads, email addresses, report IDs, delivery tokens, private URLs, or operator secrets to this response.

## Operator interpretation

`attention > 0` means durable sanitized findings were created. Investigate those findings and the authoritative commerce/provider records. Do not mutate commerce state manually through recovery endpoints: FAZ 6.5 intentionally provides no force-paid, force-refund, force-fulfilled, force-delivered, force-expired, arbitrary-order retry, or state-override API.
