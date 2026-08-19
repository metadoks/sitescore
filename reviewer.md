# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.1
CHECKPOINT_TITLE: Stripe Webhook Payment Authority + Durable Reconciliation

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: af3b9567d644f6bcf0410af704dd7d86de41b5ce
CODE_BRANCH: faz6/6-1-webhook-payment-authority
PR: TBC

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: LOCKED
FAZ_6_1_STATUS: IMPLEMENTATION_REQUESTED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
BLOCKERS: NONE

START_6_1: YES
START_6_2: NO
```

---

# 1. POST-LOCK VERIFICATION — FAZ 6.0

Reviewer independently verified the 6.0 user-authorized merge before opening 6.1.

```text
PR #23:
CLOSED / MERGED

reviewed head:
8a4e358709ae7a662bf079722db042fb6e319ffd

merge commit:
af3b9567d644f6bcf0410af704dd7d86de41b5ce

live main:
af3b9567d644f6bcf0410af704dd7d86de41b5ce

merge parents:
0e370940ee5c8c1253db72fa7e33078fb4ef3b2c
8a4e358709ae7a662bf079722db042fb6e319ffd
```

FAZ 6.0 is therefore LOCKED.

Frozen 6.0 authority remains:

```text
sitescore-commerce order domain
POST /v1/orders
server-owned location_report_v1 catalog
server-owned Stripe Price and redirect semantics
card-only hosted Checkout
stable caller idempotency
stable provider idempotency
immutable durable Checkout operation snapshot
PostgreSQL commerce schema
initial state only:
  pending_payment / pending / not_started
Checkout URL/browser redirect is NOT payment authority
```

The 6.0 validation baseline to preserve is:

```text
sitescore-commerce: 52 PASS
frozen FAZ 3/4/5 total: 1504 PASS
combined: 1556 PASS
PostgreSQL 16.15 upgrade/downgrade/upgrade: PASS
```

---

# 2. CHECKPOINT 6.1 OBJECTIVE

6.1 introduces the first authoritative payment-state transition.

Canonical commerce flow after this checkpoint:

```text
pending order
-> Stripe Checkout Session
-> Stripe webhook arrives
-> raw body signature verified
-> event durably recorded / deduplicated
-> Stripe Checkout Session is retrieved server-side
-> retrieved provider truth is reconciled against durable local Checkout operation
-> PostgreSQL transition is applied atomically
-> if and only if payment truth is authoritative:
     order_state = paid
     payment_state = paid
     fulfillment_state = not_started
-> one durable order-paid outbox record is created
```

Webhook payload alone is NOT payment truth.

The authority rule is:

```text
verified Stripe webhook
+ server-side Stripe resource reconciliation
+ durable local order/session/catalog binding
+ atomic PostgreSQL state transition
= payment authority
```

No browser redirect, client flag, n8n signal, request field, metadata field by itself, webhook event type by itself, or Checkout URL may mark an order paid.

---

# 3. SCOPE / BRANCH / PACKAGE

Implement from exactly:

```text
main@af3b9567d644f6bcf0410af704dd7d86de41b5ce
```

Use one implementation branch:

```text
faz6/6-1-webhook-payment-authority
```

Fail closed if the branch base differs. Do not silently rebase onto a later `main` and continue.

6.1 may modify only:

```text
sitescore-commerce/
checkpoint-specific docs/tests
optional temporary exact-head validation workflow
```

Frozen FAZ 3/4/5 packages remain source-immutable.

Do not write directly to frozen `sitescore-api` tables.

Package version for 6.1:

```text
sitescore-commerce==0.2.0
```

Keep exact runtime pins unless a new dependency is strictly required and documented:

```text
fastapi==0.140.0
pydantic==2.13.4
SQLAlchemy==2.0.51
alembic==1.18.5
psycopg[binary]==3.3.4
stripe==15.4.0
```

Stripe API version remains exactly:

```text
2026-07-29.dahlia
```

Do not move to preview/beta Stripe SDK/API versions.

---

# 4. EXPLICITLY FORBIDDEN 6.1 SCOPE

Do NOT implement:

```text
analysis dispatch
report dispatch
fulfillment worker
refund creation
refund reconciliation
n8n production workflow
Postmark/email
delivery grants
public report download
frontend/UI
6.2+
```

The 6.1 paid outbox is durable state only. It MUST NOT dispatch analysis yet.

---

# 5. WEBHOOK ENDPOINT CONTRACT

Add exactly the commerce Stripe webhook ingress:

```text
POST /v1/webhooks/stripe
```

This endpoint is not authenticated with SiteScore API keys. Its authenticity boundary is Stripe webhook signature verification.

Required configuration additions:

```text
STRIPE_WEBHOOK_SECRET
STRIPE_EXPECTED_LIVEMODE
```

Existing configuration remains authoritative:

```text
STRIPE_SECRET_KEY
STRIPE_API_VERSION=2026-07-29.dahlia
SITESCORE_COMMERCE_DATABASE_URL
```

Secret values must never appear in repository content, docs, tests, responses, or logs.

Webhook body requirements:

```text
maximum accepted raw body: 256 KiB
required header: Stripe-Signature
signature verification input: exact raw request bytes
signature tolerance: 300 seconds
```

Critical rule:

```text
DO NOT parse through a Pydantic request model,
DO NOT JSON-normalize,
DO NOT reserialize,
DO NOT alter whitespace/encoding
before Stripe signature verification.
```

Use the official Stripe SDK webhook verification path against the exact raw body.

Failure behavior:

```text
missing signature -> 400
invalid signature -> 400
malformed signed event -> 400
oversized body -> 413
no event/order/payment DB mutation before valid signature
```

Do not log raw webhook bodies.

---

# 6. STRIPE EVENT DESTINATION VERSION / MODE BINDING

The Stripe webhook event destination used by this service must be configured for:

```text
API version = 2026-07-29.dahlia
```

Incoming verified Event `api_version` must match the expected checkpoint version when present.

A version mismatch:

```text
must never mutate payment/order truth
must be durably visible as an attention/invariant condition when persistence is available
must not be silently interpreted using guessed schema semantics
```

The configured expected livemode must also match both:

```text
Event.livemode
retrieved Checkout Session.livemode
```

A test-mode event must never pay a live-mode order, and vice versa.

---

# 7. REQUIRED EVENT SURFACE FOR V1 CARD-ONLY CHECKOUT

FAZ 6.0 hard-froze:

```text
payment_method_types = [card]
```

Therefore 6.1 deliberately narrows the required webhook processing surface to:

```text
checkout.session.completed
checkout.session.expired
```

The production Stripe event destination for this checkpoint should subscribe only to the required event types.

The following delayed-payment events are NOT required in 6.1 because delayed payment methods are not enabled:

```text
checkout.session.async_payment_succeeded
checkout.session.async_payment_failed
```

If any unsupported but correctly signed event reaches the endpoint because of destination misconfiguration, it must cause no commerce state transition and may be durably marked ignored.

Do not broaden payment methods to justify async event handling.

---

# 8. DURABLE STRIPE EVENT INBOX

Add a new commerce migration after `0001_commerce_order_checkout`.

Create a durable event inbox under schema `commerce`, conceptually:

```text
commerce.stripe_event_inbox
```

At minimum persist:

```text
stripe_event_id               primary/unique identity
stripe_event_type
stripe_object_id              Checkout Session ID for relevant events
event_api_version
livemode
event_created_at
raw_body_sha256               hash only; do not persist raw body by default
processing_state
failure_code / attention_code nullable
received_at
processed_at nullable
attempt_count or equivalent retry evidence
```

Recommended processing states:

```text
received
processed
ignored
attention_required
```

Event ID is the minimum transport dedupe authority.

Requirements:

```text
same Stripe event ID delivered repeatedly -> one durable inbox identity
concurrent same-event deliveries -> one logical processing authority
processed duplicate -> safe 2xx without duplicate money transition
received-but-not-processed duplicate -> resumes processing, not blindly ignored
```

A duplicate event ID whose essential signed identity conflicts with the already stored event identity must fail closed and never mutate payment state.

Two distinct Stripe Event IDs that refer to the same Checkout Session must still be safe: order-state and paid-outbox idempotency must prevent duplicate payment effects.

---

# 9. WEBHOOK EVENT IS A TRIGGER, NOT PAYMENT TRUTH

Never execute conceptually:

```text
if event.type == checkout.session.completed:
    mark_paid()
```

Instead, after signature verification and durable inbox recording, use the event only to identify a Checkout Session to reconcile.

The service MUST retrieve the current Checkout Session server-side using the commerce Stripe secret and explicit API version:

```text
2026-07-29.dahlia
```

Also retrieve/inspect the Session line-item evidence needed to prove exact purchase binding.

The server-retrieved Stripe resource is then validated against durable commerce truth.

---

# 10. REQUIRED SERVER-SIDE CHECKOUT RECONCILIATION

Before any paid transition, prove all applicable invariants:

```text
retrieved object is a Checkout Session
retrieved session ID == event Checkout Session ID
retrieved session ID == local bound session ID,
  OR passes the safe unbound-session recovery flow in section 11
mode == payment
livemode == STRIPE_EXPECTED_LIVEMODE
client_reference_id == durable order_id
metadata.sitescore_order_id == durable order_id
metadata.sitescore_product_code == durable product_code
metadata.sitescore_catalog_version == durable catalog_version
line-item count == exactly 1
line-item Price ID == durable checkout snapshot stripe_price_id
line-item quantity == durable quantity == 1
line-item currency == USD
```

For a paid decision additionally require:

```text
session.status == complete
session.payment_status == paid
payment_intent identity is present and server-observed
```

`payment_status=no_payment_required` is NOT a paid state for `location_report_v1` and must fail closed.

The webhook event snapshot's own payment fields may be retained as evidence but may never override the server-retrieved resource.

---

# 11. CRITICAL RECOVERY — PROVIDER SUCCESS / LOCAL BIND LOSS / WEBHOOK FIRST

FAZ 6.0 already proved this external-call uncertainty window:

```text
Stripe creates Session
-> process loses/fails local session binding
-> retry with same provider idempotency key can recover
```

6.1 must additionally recover when the webhook arrives BEFORE a browser/client retry repairs the local binding.

Required safe flow:

```text
1. raw webhook signature is verified
2. event provides a candidate Checkout Session ID and candidate order identity
3. candidate order is loaded from commerce DB
4. candidate checkout operation may still have stripe_checkout_session_id = NULL
5. server retrieves the candidate Session directly from Stripe
6. retrieved Session is validated against the durable 6.0 operation snapshot:
     order_id
     product_code
     catalog_version
     stripe_price_id
     quantity
     client_reference_id
     metadata
     mode
     livemode
7. only after complete reconciliation may the previously unbound local checkout row be bound to that Session
8. payment transition may then proceed if paid authority is also proven
```

Event metadata/client_reference_id alone is insufficient to bind the Session.

If the durable checkout row is already bound to a different Stripe Session ID, never overwrite it from webhook input.

This recovery must not create a second Checkout Session or a second provider idempotency identity.

---

# 12. DURABLE PAYMENT EVIDENCE

Extend commerce persistence so the last authoritative Stripe reconciliation can be audited without trusting logs.

At minimum persist server-observed evidence equivalent to:

```text
stripe_checkout_session_id
stripe_payment_intent_id nullable until observed
stripe_session_status
stripe_payment_status
stripe_livemode
reconciled_at
last_reconciliation_event_id
```

This can be implemented as additive checkout-session fields or a dedicated commerce payment-evidence table.

Do not persist Stripe secret material.

Do not use event JSON as the sole durable payment evidence.

---

# 13. PAYMENT / ORDER STATE MACHINE FOR 6.1

Allowed newly implemented transitions are deliberately narrow.

Successful payment reconciliation:

```text
BEFORE:
order_state = pending_payment
payment_state = pending
fulfillment_state = not_started

AFTER:
order_state = paid
payment_state = paid
fulfillment_state = not_started
```

Expired Checkout reconciliation:

```text
provider session.status = expired
provider session.payment_status = unpaid

BEFORE:
order_state = pending_payment
payment_state = pending
fulfillment_state = not_started

AFTER:
order_state = expired
payment_state = expired
fulfillment_state = not_started
```

6.1 must NOT implement:

```text
fulfillment_in_progress
fulfilled
refund_pending
refunded
analysis_pending
report_pending
delivery_pending
completed
```

Terminal safety:

```text
paid must never be downgraded by a late/duplicate/expired webhook
expired must never be silently overwritten by contradictory provider evidence
contradictory terminal truth -> attention/invariant path, not guessed transition
```

Webhook delivery order must not be assumed.

---

# 14. DURABLE PAID OUTBOX

The first successful paid transition must atomically create exactly one durable paid-outbox record in the SAME PostgreSQL transaction as the state change.

Create a commerce table conceptually:

```text
commerce.outbox_events
```

Minimum fields:

```text
outbox_id UUID
order_id
outbox_type = order.paid.v1
payload_version
minimal safe payload
created_at
published_at nullable
```

Required uniqueness:

```text
(order_id, outbox_type)
```

The outbox payload should contain only the minimum identity needed for later server-owned fulfillment, preferably order identity/version fields. Do not copy customer email or full analysis request unless a later contract explicitly requires it.

In 6.1:

```text
published_at remains NULL
no dispatcher exists
no n8n call exists
no sitescore-api call exists
```

Crash guarantee:

```text
paid state cannot commit without its paid outbox
paid outbox cannot commit for an order that failed to become paid
```

---

# 15. NETWORK / TRANSACTION BOUNDARY

Do not hold an open PostgreSQL transaction across Stripe network I/O.

Required architecture pattern:

```text
A. verify signature
B. short DB transaction: persist/dedupe inbox receipt
C. load local correlation state
D. Stripe retrieve/list-line-items outside DB transaction
E. validate provider resource
F. short DB transaction with row locks:
     re-read order/session/inbox
     re-check local binding
     optionally recover unbound Session binding
     persist reconciliation evidence
     apply monotonic order/payment transition
     insert paid outbox if newly paid
     mark inbox processed
G. return HTTP response
```

All steps must be retry-safe after crashes.

---

# 16. HTTP / FAILURE MODEL

Required failure semantics:

```text
invalid/missing Stripe signature -> 400, no DB mutation
oversized body -> 413, no DB mutation
DB unavailable before inbox durability -> 503
Stripe retrieve/network timeout -> 503; inbox remains retryable/unprocessed
DB failure after Stripe retrieve but before transition -> 503; no fabricated paid state
already processed duplicate -> 200
valid unsupported event -> 200 after safe ignore; no state transition
unknown/foreign Checkout Session -> no order transition
binding/catalog/Price/quantity/livemode mismatch -> no paid transition
payment_status != paid -> no paid transition
session.status != complete -> no paid transition
```

Permanent signed invariant mismatches should be durably marked `attention_required` rather than repeatedly mutating/guessing state.

Never include secrets, raw Stripe payloads, customer purchase intent, or internal exception details in HTTP responses.

---

# 17. SECURITY / LOGGING / PII

Do not log:

```text
STRIPE_WEBHOOK_SECRET
STRIPE_SECRET_KEY
raw Stripe webhook body
full order purchase_intent
full customer email unless explicitly redacted/minimized
```

Safe logs may contain opaque identities such as:

```text
order_id
Stripe event ID
Checkout Session ID
processing result code
```

Do not store the webhook signing secret in PostgreSQL.

Webhook metadata must remain limited to the safe 6.0 order/product/catalog binding.

---

# 18. MIGRATION REQUIREMENTS

Add a second commerce revision, e.g. conceptually:

```text
0002_webhook_payment_authority
```

The migration must:

```text
use commerce schema only
preserve commerce.alembic_version isolation
not alter frozen sitescore-api schema/tables
upgrade cleanly from locked 0001 state
support real downgrade back to 0001
re-upgrade successfully to 0002
```

Required real PostgreSQL 16 lifecycle:

```text
fresh DB -> upgrade head -> PASS
0001 DB -> upgrade 0002 -> PASS
0002 -> downgrade 0001 -> PASS
0001 -> upgrade 0002 -> PASS
```

Do not drop the commerce schema during revision downgrade.

---

# 19. MINIMUM ADVERSARIAL TEST MATRIX

Implement comprehensive tests. At minimum prove all of the following categories; do not satisfy them only with superficial mocked-route assertions.

```text
1. valid signed checkout.session.completed + provider paid -> paid exactly once
2. browser success redirect alone still cannot mark paid
3. event.type completed alone cannot mark paid
4. event payload says paid but server retrieve says unpaid -> NOT paid
5. server retrieve says paid and exact binding passes -> paid
6. missing Stripe-Signature -> 400 / no inbox / no state change
7. invalid signature -> 400 / no inbox / no state change
8. raw body mutation after signing -> verification fails
9. stale signature beyond tolerance -> verification fails
10. >256 KiB body -> 413
11. same event ID repeated -> one inbox logical identity
12. concurrent same event -> one paid transition / one outbox
13. distinct event IDs for same Session -> no duplicate paid effect/outbox
14. provider retrieve timeout -> 503 / retry later succeeds
15. crash/failure after inbox persistence before provider reconciliation -> retry resumes
16. crash/failure after provider retrieve before DB transition -> retry succeeds safely
17. response lost after paid commit -> webhook retry does not duplicate outbox
18. session ID mismatch -> NOT paid
19. client_reference_id mismatch -> NOT paid
20. metadata order mismatch -> NOT paid
21. metadata product mismatch -> NOT paid
22. metadata catalog mismatch -> NOT paid
23. Price ID mismatch -> NOT paid
24. quantity mismatch -> NOT paid
25. non-USD line-item currency -> NOT paid
26. mode != payment -> NOT paid
27. livemode mismatch -> NOT paid
28. webhook API-version mismatch -> NOT paid
29. paid result without PaymentIntent identity -> fail closed
30. payment_status=no_payment_required -> NOT paid
31. checkout.session.expired + provider expired/unpaid -> expired
32. late expired/duplicate event cannot downgrade paid
33. contradictory provider truth on already expired terminal order -> attention, no guessed transition
34. unsupported signed event -> ignored, no state transition
35. async-payment event cannot create paid transition in current card-only contract
36. provider-success/local-bind-loss + webhook-first -> safe Session bind + paid transition after full reconciliation
37. webhook-first unbound recovery with Price mismatch -> no bind / no paid
38. webhook-first unbound recovery with metadata/order mismatch -> no bind / no paid
39. existing different local Session binding can never be overwritten by webhook
40. paid state and order.paid.v1 outbox commit atomically
41. duplicate/concurrent paid processing -> exactly one outbox record
42. 6.1 outbox has no dispatcher and published_at remains NULL
43. no sitescore-api runtime import/call
44. no direct writes to frozen API tables
45. secrets/raw webhook body absent from logs
46. migration 0001 -> 0002 -> 0001 -> 0002 works on PostgreSQL 16
47. commerce version table remains isolated from public schema
48. all locked 6.0 tests continue to pass
49. frozen FAZ 3/4/5 regression baseline remains >=1504 PASS
```

Use the actual Stripe SDK signature-verification code path in webhook tests with a test signing secret; do not replace signature verification with a fake boolean.

Provider-reconciliation gateway/network behavior may be deterministically faked in unit/integration tests, but PostgreSQL durability/concurrency/crash-window claims require real PostgreSQL evidence.

---

# 20. CI / EVIDENCE REQUIREMENTS

Before handoff, provide fresh exact-head evidence for the 6.1 candidate.

Required:

```text
exact branch head SHA
PR number
base SHA
full changed-file inventory
git diff main...HEAD summary
sitescore-commerce total PASS count
new webhook/payment tests PASS
real PostgreSQL 16 migration lifecycle PASS
inbox duplicate/concurrency evidence
webhook-first local-bind-loss recovery evidence
paid/outbox atomicity evidence
exact stripe==15.4.0 pin proof
exact Stripe API version proof
pip check PASS
secret/raw-body logging scan PASS
frozen-scope scan PASS
frozen regression total >=1504 PASS
no 6.2+ scope leakage
```

If a temporary exact-head GitHub Actions workflow is used and later removed, final handoff must prove the validated-to-final delta consists only of that workflow removal.

Do not claim a final HEAD as validated when runtime/migration/test code changed after the validation run.

---

# 21. REQUIRED DOCUMENTATION

Update:

```text
sitescore-commerce/README.md
```

Add:

```text
sitescore-commerce/docs/CHECKPOINT_6_1_WEBHOOK_PAYMENT_AUTHORITY.md
```

Document at minimum:

```text
webhook raw-body/signature authority
Stripe event destination API-version requirement
card-only event surface
server-side reconciliation authority
safe unbound Session recovery
payment state machine
expired state behavior
event inbox dedupe/retry semantics
paid-outbox atomicity
failure/crash windows
secret/env names only, never values
why browser success is not payment authority
deferred 6.2 fulfillment/refund work
```

---

# 22. IMPLEMENTER HANDOFF CONTRACT

After implementation and fresh validation, Implementer updates only `implementer.md` and sets:

```text
CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.1
IMPLEMENTER_STATE: READY_FOR_REVIEW
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO
BASE_SHA: af3b9567d644f6bcf0410af704dd7d86de41b5ce
HEAD_SHA: <exact>
PR: #<n>
BLOCKERS_REPORTED_BY_IMPLEMENTER: <NONE or exact>
CONTRACT_CHANGE_REQUIRED: 0/1
DESIGN_DECISION_REVIEW_REQUIRED: 0/1
ADDITIONAL_REOPEN_REQUIRED: 0/1
START_6_2: NO
```

Include:

```text
changed files
test counts
migration evidence
signature verification evidence
Stripe API/version evidence
inbox idempotency/concurrency evidence
server reconciliation evidence
unbound Session webhook recovery evidence
paid transition/outbox evidence
secret/frozen-scope scans
exact Actions run/job IDs
validated-to-final delta if applicable
```

Then STOP.

Implementer MUST NOT merge, self-authorize LOCK, or start 6.2.

---

# 23. REVIEWER DECISION

```text
FAZ 6.0: LOCKED
LIVE_MAIN: af3b9567d644f6bcf0410af704dd7d86de41b5ce

FAZ 6.1: IMPLEMENTATION_REQUESTED
CODE_BRANCH: faz6/6-1-webhook-payment-authority
BASE: main@af3b9567d644f6bcf0410af704dd7d86de41b5ce

BLOCKERS: NONE
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

START_6_1: YES
START_6_2: NO
```

Implementer may now implement FAZ 6.1 only and STOP at `READY_FOR_REVIEW`.

Reviewer STOP.
