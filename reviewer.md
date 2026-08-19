# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.0
CHECKPOINT_TITLE: Commerce / Order Domain + Stripe Checkout Foundation

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 0e370940ee5c8c1253db72fa7e33078fb4ef3b2c
CODE_BRANCH: faz6/6-0-commerce-order-checkout
PR: TBC

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: IMPLEMENTATION_REQUESTED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
BLOCKERS: NONE
START_FAZ6: YES
```

---

# 1. LIVE BOOTSTRAP VERIFICATION

Reviewer independently re-read live GitHub before opening FAZ 6.

Verified live state:

```text
live main:
0e370940ee5c8c1253db72fa7e33078fb4ef3b2c

main commit message:
Merge PR #22: FAZ 5-FINAL integrated product audit and freeze gate

merge parent 1:
8f757b81c0cb69e5e6be62f45e94ff9a57432cca

merge parent 2 / exact reviewed 5-FINAL head:
50d24cb612339f9dd178aca6916eaa04f1c1b61f

PR #22:
CLOSED / MERGED
merge commit:
0e370940ee5c8c1253db72fa7e33078fb4ef3b2c

Reviewer FAZ 5 handoff:
FAZ_5_STATUS: FROZEN
BLOCKERS: NONE

FAZ 6 code branch search:
no existing faz6 branch found
```

Root repository inspection shows no `sitescore-commerce` package and no production `automation/n8n` tree at the FAZ 6 base. Search found no Postmark implementation. Existing Stripe/n8n references are documentation / handoff references, not a commercial runtime subsystem.

The frozen automation-consumer handoff remains authoritative:

```text
AUTOMATION_CONSUMER_HANDOFF.md

n8n = orchestration consumer
n8n != scoring/report truth authority
FAZ 5 contains no production n8n workflow
```

The frozen public SiteScore API remains exactly:

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

The current frozen `AnalysisRequest` public consumer shape remains the four strict sector payloads:

```text
coffee
restaurant
gym
beauty
```

with `extra=forbid`, US address rules, sector-specific business inputs and operating costs.

No FAZ 3/4/5 reopen is authorized or required for 6.0.

---

# 2. CHECKPOINT PURPOSE

Implement **only FAZ 6.0**:

```text
sitescore-commerce
commerce PostgreSQL persistence
commerce Alembic migration foundation
order resource
server-owned product catalog
idempotent order creation
Stripe Checkout Session adapter
server-owned Stripe Price binding
safe success/cancel redirect construction
Stripe SDK + API version pin
```

This checkpoint creates a Checkout URL and a durable **pending-payment** commerce resource.

It MUST NOT establish payment truth.

Canonical boundary:

```text
customer purchase intent
-> commerce order
-> server-owned catalog lookup
-> durable pending-payment order
-> server-created Stripe Checkout Session
-> Checkout URL

STOP
```

Not in 6.0:

```text
verified payment
Stripe webhook processing
payment reconciliation
paid outbox
analysis dispatch
report binding
refund
n8n production workflow
delivery grant
Postmark
email
fulfillment completion
FAZ 7 work
```

---

# 3. BRANCH / BASE CONTRACT

Implementer MUST create exactly one checkpoint branch from the exact frozen base:

```text
base branch: main
base SHA: 0e370940ee5c8c1253db72fa7e33078fb4ef3b2c
branch: faz6/6-0-commerce-order-checkout
```

Before writing code, Implementer must prove:

```text
git merge-base --is-ancestor 0e370940ee5c8c1253db72fa7e33078fb4ef3b2c HEAD
```

and report the actual branch base.

One PR only for 6.0. Any hardening remains on the same branch/PR.

---

# 4. FROZEN PACKAGE PROTECTION

FAZ 3/4/5 packages are frozen.

6.0 MUST NOT edit runtime source, migrations, package versions or semantic tests under:

```text
sitescore-core
sitescore-data
sitescore-providers
sitescore-spatial
sitescore-metrics
sitescore-benchmarks
sitescore-pipeline
sitescore-app
sitescore-report
sitescore-api
```

Allowed read-only use:

```text
public docs
public OpenAPI/runtime contract inspection
frozen request-shape conformance tests
```

`sitescore-commerce` MUST NOT write directly to `sitescore-api` tables and MUST NOT treat their PostgreSQL rows as cross-service API truth.

Future cross-service SiteScore truth remains consumed through the frozen `/v1` API.

Runtime imports from `sitescore_api` are forbidden.

---

# 5. NEW PACKAGE

Create:

```text
sitescore-commerce/
  pyproject.toml
  README.md
  alembic.ini
  alembic/
  src/sitescore_commerce/
  tests/
  docs/CHECKPOINT_6_0_COMMERCE_ORDER_STRIPE_CHECKOUT.md
```

Package identity:

```text
sitescore-commerce==0.1.0
Python >=3.11
```

Use the established repository style where sensible, but do not copy frozen API authority into commerce.

---

# 6. DEPENDENCY CONTRACT

Direct runtime dependencies must be exact pins, not ranges.

Required baseline:

```text
fastapi==0.140.0
pydantic==2.13.4
SQLAlchemy==2.0.51
alembic==1.18.5
psycopg[binary]==3.3.4
stripe==15.4.0
```

Dev/test baseline:

```text
httpx==0.28.1
pytest==8.4.2
```

Do not add Redis, Celery, boto3, Postmark/n8n SDKs or frozen SiteScore packages as commerce runtime dependencies in 6.0.

### Stripe version lock

For this checkpoint freeze:

```text
STRIPE_PYTHON_VERSION: 15.4.0
STRIPE_API_VERSION: 2026-07-29.dahlia
```

The implementation must explicitly bind outgoing Stripe requests to this API version using the supported `stripe-python` client/request version mechanism. Do not silently inherit the Stripe account default API version.

The future webhook endpoint created/configured in 6.1 must use the same API version unless a later Reviewer-authorized contract explicitly changes it.

Preview / beta / alpha Stripe SDK versions are forbidden.

---

# 7. COMMERCE DATABASE OWNERSHIP

Commerce gets its own PostgreSQL namespace and Alembic history.

Required logical isolation:

```text
commerce schema
commerce-owned tables only
commerce-owned Alembic version table
SITESCORE_COMMERCE_DATABASE_URL
```

The initial migration must create the schema and required 6.0 tables without touching frozen `sitescore-api` migration history or tables.

Recommended durable tables for 6.0:

```text
commerce.orders
commerce.order_idempotency
commerce.checkout_sessions
commerce.alembic_version   # or equivalently isolated Alembic version table
```

Exact physical names may vary only if semantics remain identical and are documented.

## 7.1 Order identity

```text
order_id = server-generated UUIDv4
```

Caller cannot choose `order_id`.

## 7.2 State dimensions

Persist **separate** state dimensions now so later checkpoints do not collapse business truth:

Order state closed set:

```text
pending_payment
paid
fulfillment_in_progress
fulfilled
attention_required
expired
refunded
```

Payment state closed set:

```text
pending
paid
failed
expired
refund_pending
refunded
refund_failed
```

Fulfillment state closed set:

```text
not_started
analysis_pending
analysis_running
report_pending
delivery_pending
completed
not_score_ready
analysis_failed
analysis_timed_out
report_failed
delivery_failed
```

In **6.0**, the only state tuple that order creation may author is:

```text
order_state       = pending_payment
payment_state     = pending
fulfillment_state = not_started
```

No 6.0 code path may transition to `paid`, `fulfilled`, `refunded`, or any analytical/report terminal state.

Use database constraints/checks so invalid enum-like strings cannot be persisted.

---

# 8. ORDER PURCHASE-INTENT CONTRACT

Public concept:

```text
POST /v1/orders
```

Required header:

```http
Idempotency-Key: <opaque caller retry key>
```

Recommended maximum aligns with existing SiteScore ingress discipline:

```text
<= 200 UTF-8 bytes
non-empty after validation
```

Request body must be strict (`extra=forbid`) and contain only purchase intent needed for this product:

```json
{
  "product_code": "location_report_v1",
  "customer_email": "customer@example.com",
  "analysis_request": {
    "sector": "coffee|restaurant|gym|beauty",
    "location": {},
    "business_inputs": {},
    "costs": {}
  }
}
```

`analysis_request` is **caller intent**, not analytical authority.

Commerce-local request models must remain compatible with the current frozen public `sitescore-api` `AnalysisRequest` shape for all four sectors while avoiding a runtime dependency on `sitescore_api`.

Implementer must add a test-time conformance mechanism proving that commerce accepts/rejects representative four-sector payloads consistently with the frozen public request contract. Test-only inspection/import is permitted; runtime dependency/import is not.

The order must durably retain the server-normalized purchase intent and a deterministic canonical request/purchase-intent hash for idempotency and future `ensure_analysis(order_id)` derivation.

Do not store fake score/readiness/decision/report authority in the purchase intent.

---

# 9. CALLER-FORBIDDEN FIELDS

The caller MUST NOT be able to choose or override any of the following:

```text
amount
unit_amount
currency
Stripe Price ID
Stripe Product ID
quantity
discount
coupon
promotion-code authority
Stripe customer ID
Stripe Checkout Session ID
Stripe PaymentIntent ID
payment_status
paid
trusted
score_ready
analysis_id
report_id
refund state
success_url
cancel_url
Stripe metadata
```

Unknown fields must fail closed with validation error.

`product_code` is the only commerce product selector and must be an allowlisted closed value.

For V1 6.0:

```text
allowed product_code = location_report_v1
```

---

# 10. SERVER-OWNED PRODUCT CATALOG

Create an explicit server-owned product catalog abstraction.

Canonical V1 entry:

```text
product_code: location_report_v1
catalog_version: v1
quantity: 1
currency expectation: USD
Stripe Price ID: deployment configuration only
```

Required environment/config concept:

```text
STRIPE_PRICE_LOCATION_REPORT_V1
```

The raw Stripe Price ID must never come from request JSON.

The catalog should validate configuration at startup/use time and fail closed for missing/blank/malformed server configuration.

The catalog may retrieve/validate the Stripe Price object if needed, but it must not create ad-hoc `price_data` from caller amount/currency.

Checkout must use the existing server-configured Price ID:

```text
line_items[0].price = server catalog Price ID
line_items[0].quantity = 1
```

No inline caller-derived price creation.

---

# 11. STRIPE CHECKOUT CREATION CONTRACT

Use Stripe Checkout Sessions, hosted flow, one-time payment:

```text
mode = payment
ui_mode = hosted
quantity = 1
```

For 6.0, restrict the accepted payment surface to synchronous card semantics:

```text
payment_method_types = [card]
```

This is deliberate to avoid silently enabling delayed-method payment semantics before 6.1 payment-authority review. Wallets surfaced through the card rail are not a separate commerce truth authority.

Required server-owned binding fields:

```text
client_reference_id = order_id
Checkout Session metadata.sitescore_order_id = order_id
Checkout Session metadata.sitescore_product_code = location_report_v1
Checkout Session metadata.sitescore_catalog_version = v1
PaymentIntent metadata.sitescore_order_id = order_id
PaymentIntent metadata.sitescore_product_code = location_report_v1
```

Do not place the full analysis request, street address, financial inputs or secrets in Stripe metadata.

`customer_email` may be passed to Stripe Checkout from the validated order purchase intent.

Explicitly keep out of 6.0:

```text
allow_promotion_codes = false / not enabled
automatic discount authority = none
subscription mode = forbidden
manual caller price_data = forbidden
advanced tax engine = out of scope
```

---

# 12. SAFE SUCCESS / CANCEL URL CONTRACT

Success and cancel URLs are server configuration, not caller input.

Use deployment-owned configured HTTPS origins/paths. Local tests may use explicit test URLs.

At minimum validate:

```text
absolute URL
allowed http/https policy by environment
no embedded credentials
no arbitrary caller host/path override
no fragment-based authority
```

The success URL may contain order/session correlation data for presentation, but this data is never payment proof.

Hard invariant:

```text
success redirect != paid
cancel redirect  != failed/expired payment truth
browser return   != Stripe authority
```

No redirect route or query parameter may mutate payment/order/fulfillment state in 6.0.

---

# 13. ORDER CREATION IDEMPOTENCY

Order creation must be PostgreSQL-backed, not memory-backed.

Required identity semantics:

```text
Idempotency-Key digest
+ canonical normalized request hash
+ database uniqueness
```

Rules:

```text
same key + same canonical request
-> same durable order_id
-> same logical Checkout Session operation

a same key + different canonical request
-> 409 idempotency conflict

concurrent same-key same-request
-> exactly one durable order
-> exactly one logical Checkout operation
```

Store a digest/hash of the caller idempotency key rather than relying on raw secret-like retry material.

The canonical request hash must include all semantically relevant normalized purchase-intent fields, including product code, email and analysis request.

---

# 14. STRIPE-SIDE IDEMPOTENCY / UNCERTAIN RESPONSE

The caller's `Idempotency-Key` is **not** forwarded directly to Stripe as provider authority.

Derive a server-owned stable Stripe idempotency key from durable order identity and operation version, e.g. logical form:

```text
sitescore:checkout:v1:<order_id>
```

Exact encoding may vary but must be deterministic, bounded and documented.

All retries for the same Checkout creation operation must reuse the exact same Stripe idempotency key and exact same parameters.

Required crash/uncertainty behavior:

```text
1. durable order exists first
2. Checkout operation identity is deterministic from order
3. Stripe POST is attempted with stable Stripe idempotency key
4. timeout / dropped response does NOT create a new order
5. retry uses same order and same Stripe idempotency key
6. returned Checkout Session is validated against order/catalog binding before persistence
7. Checkout URL is returned only after durable binding is persisted
```

If Stripe outcome cannot be safely determined, fail closed. Do not mark paid and do not invent a Checkout Session ID.

The Stripe documentation guarantees idempotency for POST retries when the same key and parameters are reused; implementation must use that capability rather than an in-memory retry flag.

---

# 15. CHECKOUT SESSION DURABLE BINDING

Persist at least:

```text
order_id
stripe_checkout_session_id
server Stripe idempotency operation identity/digest
catalog_version
product_code
server-selected Stripe Price ID or irreversible deployment-safe reference
checkout URL
Checkout expiry timestamp if returned
created_at
updated_at
```

Constraints:

```text
order_id unique for active 6.0 binding
stripe_checkout_session_id unique
```

Before persistence/return, validate the returned Stripe object is coherent with the request you sent:

```text
mode == payment
client_reference_id == order_id
metadata order_id == order_id
metadata product_code == location_report_v1
```

Where the SDK response exposes line-item/payment binding only by expansion/retrieval, do not invent unavailable evidence; document what is and is not verified in 6.0.

A Stripe object ID is evidence/binding identity, not proof that money was paid.

---

# 16. PUBLIC RESPONSE CONTRACT

`POST /v1/orders` should return a strict resource projection containing no secrets and no payment forgery surface.

Minimum response:

```json
{
  "api_version": "v1",
  "request_id": "<server UUIDv4>",
  "order_id": "<server UUIDv4>",
  "product_code": "location_report_v1",
  "order_state": "pending_payment",
  "payment_state": "pending",
  "fulfillment_state": "not_started",
  "checkout_url": "<Stripe hosted Checkout URL>",
  "checkout_expires_at": "<timestamp-or-null>"
}
```

Do not expose:

```text
Stripe secret key
full config
internal DB identifiers
private provider credentials
raw idempotency-key digest
internal canonical request hash unless explicitly justified
internal Stripe request headers
```

A Stripe Checkout Session ID is not required in the public response and should remain internal unless a concrete consumer need is demonstrated.

---

# 17. PAYMENT AUTHORITY — ABSOLUTE 6.0 RULE

6.0 has **no payment-authority transition**.

None of these can set `payment_state=paid`:

```text
Checkout Session creation response
checkout_url existence
success_url visit
browser redirect
client request
client `paid=true`
caller metadata
Stripe object ID alone
n8n
```

Canonical FAZ 6 payment authority remains reserved for 6.1:

```text
verified Stripe webhook
+
server-side Stripe reconciliation
+
durable commerce DB transition
```

Do not partially implement that authority in 6.0.

---

# 18. AUTHORITY / TRUST BOUNDARIES

Commerce owns:

```text
order identity
purchase intent persistence
product catalog selection
Checkout Session creation request
order idempotency
Checkout binding
commerce DB state
```

Commerce does NOT own:

```text
location scoring
readiness
benchmark normalization
financial math
decision
confidence
report facts
PDF truth
```

No 6.0 source may calculate or copy analytical outputs as truth.

The purchase intent may contain the user inputs required by frozen SiteScore, but those inputs are not provider data, readiness evidence, score authority or report authority.

---

# 19. SECURITY / SECRET CONTRACT

Environment concepts may include:

```text
SITESCORE_COMMERCE_DATABASE_URL
STRIPE_SECRET_KEY
STRIPE_PRICE_LOCATION_REPORT_V1
STRIPE_API_VERSION
COMMERCE_SUCCESS_URL_BASE / exact deployment equivalent
COMMERCE_CANCEL_URL_BASE / exact deployment equivalent
```

Requirements:

```text
no secret committed
no .env committed
no Stripe secret in exception text/logs/tests/fixtures
no DB URL password in logs
no purchase-intent dump in ordinary logs
no full customer email in security/error logs unless explicitly redacted
```

`.gitignore` must cover local secret files if not already sufficient.

No Stripe webhook secret is required in 6.0; do not introduce fake webhook verification early.

---

# 20. FAILURE / TRANSACTION RULES

The database transaction must not be held open across a slow Stripe network call unless Implementer demonstrates a concrete safe reason. Prefer durable local state before external call and a separate safe persistence/reconciliation step afterward.

Required outcomes:

```text
DB order insert fails
-> no Stripe call

Stripe Checkout create definitively fails
-> order remains pending_payment/payment=pending
-> sanitized provider error response
-> same order may be retried safely

Stripe response uncertain
-> no new order
-> retry stable provider idempotency operation

Stripe succeeds but local binding commit fails
-> do not return Checkout URL
-> retry same logical provider operation
-> persist same returned logical Session when recovered

success redirect hit
-> no state transition

cancel redirect hit
-> no authoritative state transition
```

Do not use `attention_required` as a convenient substitute for unresolved implementation bugs. It is a durable business state for later recovery logic, not a catch-all exception handler.

---

# 21. REQUIRED ADVERSARIAL TESTS

At minimum test all of the following:

```text
COM60-T001 valid location_report_v1 creates one pending order + one logical Checkout operation
COM60-T002 caller amount rejected
COM60-T003 caller currency rejected
COM60-T004 caller Stripe Price ID rejected
COM60-T005 caller discount/coupon rejected
COM60-T006 caller paid/payment_status rejected
COM60-T007 caller success_url/cancel_url rejected
COM60-T008 unknown product_code rejected
COM60-T009 configured catalog Price ID is the exact Stripe line-item price
COM60-T010 quantity is server-fixed at 1
COM60-T011 mode is payment and card-only payment surface is enforced
COM60-T012 Stripe metadata/client_reference_id bind exact server order_id
COM60-T013 same Idempotency-Key + same canonical payload returns same order
COM60-T014 same Idempotency-Key + different payload returns 409
COM60-T015 concurrent same-key same-payload creates one durable order
COM60-T016 concurrent/retried Checkout ensure uses one stable Stripe idempotency operation
COM60-T017 timeout after provider request reuses same provider idempotency key
COM60-T018 failed local binding commit never returns unpersisted Checkout URL
COM60-T019 Checkout creation never sets paid
COM60-T020 success redirect/correlation data never sets paid
COM60-T021 initial state tuple is exactly pending_payment/pending/not_started
COM60-T022 invalid state strings are rejected by DB constraints
COM60-T023 commerce runtime has no sitescore_api import/dependency
COM60-T024 commerce migration touches no frozen API table/migration namespace
COM60-T025 four-sector purchase-intent conformance with frozen AnalysisRequest
COM60-T026 unknown nested analysis_request fields fail closed
COM60-T027 secrets are absent from serialized API errors/log assertions
COM60-T028 Stripe API version is explicitly 2026-07-29.dahlia
COM60-T029 dependency is exactly stripe==15.4.0
COM60-T030 server restart does not lose order-idempotency truth
```

Add any further tests needed by the actual implementation design.

---

# 22. DATABASE / MIGRATION VALIDATION

Use a real PostgreSQL 16 instance for migration/integration evidence.

Required evidence:

```text
fresh database -> upgrade to commerce head: PASS
expected commerce schema/tables/constraints exist: PASS
frozen sitescore-api migration namespace unchanged: PASS
order idempotency uniqueness under concurrency: PASS
checkout session uniqueness: PASS
invalid state DB constraint rejection: PASS
```

If downgrade is implemented and safe, test `upgrade -> downgrade -> upgrade`; do not weaken forward migration correctness merely to make downgrade convenient.

SQLite-only evidence is not sufficient for PostgreSQL uniqueness/concurrency/migration authority.

---

# 23. API / ERROR CONTRACT

Use sanitized machine-readable errors consistent with repository style.

At minimum distinguish:

```text
request_validation_failed
idempotency_conflict
commerce_configuration_unavailable
commerce_persistence_unavailable
checkout_provider_unavailable
```

Do not leak Stripe SDK exception internals, request headers, API keys, DB internals or stack traces.

HTTP mapping may be refined by Implementer but must be deterministic and tested. Recommended classes:

```text
400 invalid/missing Idempotency-Key
409 idempotency conflict
422 strict request validation
500 invariant failure
502 definitive external provider failure where appropriate
503 unavailable configuration/persistence/provider transport where retry is safe
```

A provider failure must not be represented as a successful order payment.

---

# 24. DOCUMENTATION REQUIRED

Create durable 6.0 documentation that records actual implementation truth:

```text
sitescore-commerce/README.md
sitescore-commerce/docs/CHECKPOINT_6_0_COMMERCE_ORDER_STRIPE_CHECKOUT.md
```

Document at minimum:

```text
package/version
base SHA
branch
public route
request/response contract
product catalog
state sets
6.0-permitted state tuple
DB schema/migration identity
order idempotency
Stripe idempotency
Stripe SDK version
Stripe API version
Checkout parameters
server-owned Price configuration env name
success/cancel URL rule
security/secret boundary
external-call uncertainty behavior
explicit non-authorities
known deferrals to 6.1+
test baseline
```

Do not document future 6.1 behavior as if already implemented.

---

# 25. CI / VALIDATION EVIDENCE

Before `READY_FOR_REVIEW`, Implementer must provide exact-head evidence for:

```text
sitescore-commerce unit tests: PASS
real PostgreSQL 16 commerce migration/integration tests: PASS
pip check / dependency resolution: PASS
architecture boundary tests: PASS
secret/config scan for committed FAZ 6 files: PASS
frozen regression baseline: PASS
```

Frozen regression baseline must include the pre-existing locked suites and must not be reduced by deleting/skipping tests.

The authoritative pre-6.0 reference remains:

```text
sitescore-report: 24 PASS
sitescore-api:    105 PASS
frozen packages: 1375 PASS
TOTAL:            1504 PASS
```

6.0 adds commerce tests on top of that baseline.

A temporary exact-head GitHub Actions validation workflow is permitted if needed for real PostgreSQL evidence. If removed after a successful run, the only validated-to-final delta must be independently proved to be that workflow removal; otherwise rerun validation on final head.

No production Stripe secret is permitted in CI. Deterministic provider adapter tests should use fakes/mocks/test-mode-safe mechanisms without creating real charges.

---

# 26. REQUIRED IMPLEMENTER HANDOFF

When implementation is complete, update only `implementer.md` on the coordination branch with:

```text
CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.0
IMPLEMENTER_STATE: READY_FOR_REVIEW
EXPECTED_BASE_SHA
CODE_BRANCH
PR
HEAD_SHA
changed files
migration revision
package version
Stripe SDK version
Stripe API version
state sets
public route
runtime dependencies
exact test counts
PostgreSQL evidence
CI run/job identifiers if used
secret scan result
frozen regression result
CONTRACT_CHANGE_REQUIRED
DESIGN_DECISION_REVIEW_REQUIRED
ADDITIONAL_REOPEN_REQUIRED
BLOCKERS_REPORTED_BY_IMPLEMENTER
```

Also give a concise claim-by-claim summary of how the implementation satisfies sections 7–25 above.

Do not ask Reviewer to infer missing evidence from prose.

---

# 27. STOP CONDITION

After:

```text
code committed
PR opened
required tests green
implementer.md updated to READY_FOR_REVIEW
```

Implementer MUST STOP.

Do not merge.

Do not start 6.1.

Do not interpret this contract as LOCK authorization.

Next authority transition requires:

```text
User -> Devam
Reviewer -> independent exact-head review
```

Only if that review returns:

```text
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
BLOCKERS: NONE
```

may a later literal user `LOCK` authorize merge.

---

# 28. REVIEWER DECISION

```text
FAZ 6: OPENED
CHECKPOINT 6.0: IMPLEMENTATION_REQUESTED
EXPECTED_BASE_SHA: 0e370940ee5c8c1253db72fa7e33078fb4ef3b2c
CODE_BRANCH: faz6/6-0-commerce-order-checkout
BLOCKERS: NONE
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
```

Reviewer STOP.