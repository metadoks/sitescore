# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.2
CHECKPOINT_TITLE: Paid Fulfillment Binding + Canonical Unfulfillable Full Refund Authority

REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 8027239b4b168e98e8ee16e15787366632017156
LIVE_MAIN_SHA_AT_REVIEW: 8027239b4b168e98e8ee16e15787366632017156
CODE_BRANCH: faz6/6-2-fulfillment-refund
PR: TBA

BLOCKERS: NONE
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: LOCKED
FAZ_6_1_STATUS: LOCKED
FAZ_6_2_STATUS: IMPLEMENTATION_REQUESTED
START_6_2: YES
START_6_3: NO
```

---

# 1. POST-LOCK BASE PROOF

Reviewer independently verified the 6.1 lock before opening this checkpoint.

```text
PR #24: MERGED
reviewed head:
719a17c4359524337f57298252a59ccb89dcd0aa

merge commit / live main:
8027239b4b168e98e8ee16e15787366632017156

merge parent 1:
af3b9567d644f6bcf0410af704dd7d86de41b5ce

merge parent 2:
719a17c4359524337f57298252a59ccb89dcd0aa
```

No unreviewed 6.1 head was merged. FAZ 6.1 is therefore LOCKED.

---

# 2. CHECKPOINT PURPOSE

FAZ 6.2 turns a durably paid commerce order into a server-controlled fulfillment lifecycle and makes canonical unfulfillable outcomes refundable without giving money authority to n8n, the browser, or a SiteScore API client response alone.

Target successful path:

```text
paid order
-> ensure_analysis(order_id)
-> durable analysis binding
-> server-side SiteScore analysis polling
-> canonical completed
-> ensure_report(order_id)
-> durable report binding
-> report ready
-> delivery_pending
```

Target unfulfillable path:

```text
paid order
-> bound SiteScore resource
-> server-side canonical terminal verification
-> not_score_ready | failed | timed_out | report_failed
-> durable refund eligibility snapshot
-> server-side Stripe refund reconciliation
-> one full refund operation
-> refunded
```

Delivery, email, customer download grants, n8n workflow JSON, and broad recovery scanning are NOT part of 6.2.

---

# 3. PACKAGE / DEPENDENCY BASELINE

Implement on a new branch from exact base:

```text
main@8027239b4b168e98e8ee16e15787366632017156
branch: faz6/6-2-fulfillment-refund
```

Expected package version:

```text
sitescore-commerce==0.3.0
Python >=3.11
```

Keep existing exact runtime pins and promote the existing test-only HTTP client to a runtime dependency because commerce now calls the frozen SiteScore API over HTTP:

```text
fastapi==0.140.0
pydantic==2.13.4
SQLAlchemy==2.0.51
alembic==1.18.5
psycopg[binary]==3.3.4
stripe==15.4.0
httpx==0.28.1
```

Dev/test:

```text
pytest==8.4.2
```

Hard boundary:

```text
NO runtime dependency on sitescore-api
NO runtime import from sitescore-api
NO direct reads/writes of frozen SiteScore API tables
NO direct Redis/Celery task manipulation
NO direct report object-storage access
```

Commerce consumes only the frozen authenticated HTTP `/v1` contract.

---

# 4. FROZEN SITESCORE HTTP CONSUMER CONTRACT

The authoritative frozen consumer routes remain exactly:

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

6.2 needs only the first four routes. Report PDF content is a delivery concern and remains out of scope until 6.4.

Commerce must authenticate to SiteScore with a server-held scoped service credential. n8n must never receive that credential.

Required configuration conceptually:

```text
SITESCORE_API_BASE_URL
SITESCORE_API_SERVICE_KEY
SITESCORE_API_TARGET_ID
SITESCORE_API_TIMEOUT_SECONDS
```

Production base URL must be HTTPS. Secrets must never be persisted in commerce tables or emitted in responses/logs.

The durable operation snapshot must bind a stable target identity so a restart/configuration drift cannot silently replay the same logical analysis against a different SiteScore deployment.

---

# 5. DURABLE FULFILLMENT BINDING

Add commerce migration:

```text
0003_fulfillment_refund
```

Add a durable fulfillment binding table, conceptually:

```text
commerce.fulfillment_bindings
```

At minimum persist:

```text
order_id                       PK/FK
sitescore_api_target_id
sitescore_api_base_url         non-secret target snapshot
analysis_operation_version
analysis_idempotency_key
analysis_request_json          exact immutable AnalysisRequest payload
analysis_request_sha256
analysis_id                    nullable, unique when present
analysis_state                 nullable closed frozen state
analysis_last_observed_at      nullable
report_id                      nullable, unique when present
report_state                   nullable closed frozen state
report_last_observed_at        nullable
created_at
updated_at
```

Stable SiteScore analysis provider key:

```text
sitescore:analysis:v1:<order_id>
```

The exact analysis payload is the durable order's stored `analysis_request`, not caller-supplied data from an automation request.

Persist the immutable operation snapshot before the first SiteScore POST.

A later deployment/config drift must not change the target identity, payload, request hash, or idempotency key of an existing order's analysis operation.

---

# 6. ENSURE_ANALYSIS AUTHORITY

Conceptual server operation:

```text
ensure_analysis(order_id)
```

Precondition:

```text
order_state == paid OR fulfillment_in_progress
payment_state == paid
order is not refunded
```

An unpaid, expired, refund-pending, refunded, or payment-failed order must never create a SiteScore analysis.

Creation request:

```http
POST /v1/analyses
Authorization: Bearer <server-held SiteScore key>
Idempotency-Key: sitescore:analysis:v1:<order_id>
Content-Type: application/json

<exact durable AnalysisRequest snapshot>
```

Rules:

```text
same order -> same SiteScore Idempotency-Key
same order -> exact same logical payload
uncertain POST -> retry same key + same payload + same durable target
never mint a second analysis key because of timeout/restart
never accept caller analysis_id
```

Validate the response before binding:

```text
api_version == v1
analysis_id is valid server-returned UUID
state is one of queued|running|completed|not_score_ready|failed|timed_out
```

If local `analysis_id` is already bound, never overwrite it with a different ID.

A lost HTTP response followed by retry must converge on the same durable SiteScore analysis through the frozen consumer idempotency contract.

No PostgreSQL transaction may be held open across the SiteScore network call.

---

# 7. ANALYSIS RECONCILIATION

Once an analysis is bound, subsequent progress uses:

```http
GET /v1/analyses/{bound_analysis_id}
```

The response must be checked against the exact bound ID and frozen closed state set.

State mapping:

```text
queued
-> order_state = fulfillment_in_progress
-> payment_state = paid
-> fulfillment_state = analysis_pending

running
-> order_state = fulfillment_in_progress
-> payment_state = paid
-> fulfillment_state = analysis_running

completed
-> order_state = fulfillment_in_progress
-> payment_state = paid
-> fulfillment_state = report_pending

not_score_ready
-> fulfillment_state = not_score_ready
-> candidate refund eligibility

failed
-> fulfillment_state = analysis_failed
-> candidate refund eligibility

timed_out
-> fulfillment_state = analysis_timed_out
-> candidate refund eligibility
```

Do NOT refund because of:

```text
network timeout
DNS/TLS error
HTTP 401/403
HTTP 404 without a coherent bound-resource investigation
HTTP 429
HTTP 5xx
malformed response
unknown future state
ID mismatch
target mismatch
```

Those are retry/attention conditions, not canonical unfulfillable truth.

---

# 8. ENSURE_REPORT AUTHORITY

Conceptual server operation:

```text
ensure_report(order_id)
```

It is allowed only after the bound analysis has been server-observed as canonical `completed`.

Request:

```http
POST /v1/reports
Authorization: Bearer <server-held SiteScore key>
Content-Type: application/json

{"analysis_id":"<bound analysis_id>"}
```

The frozen endpoint is a resolver, not a generator. Commerce must not synthesize or regenerate report truth.

Validate before binding:

```text
returned analysis_id == bound analysis_id when present in contract
report_id is valid server-returned UUID
state is ready|failed
```

If a report ID is already bound, never overwrite it with a different ID.

Repeated resolution of the same completed analysis must converge on the frozen durable report resource.

State mapping:

```text
ready
-> order_state = fulfillment_in_progress
-> payment_state = paid
-> fulfillment_state = delivery_pending

failed
-> fulfillment_state = report_failed
-> candidate refund eligibility
```

No report content download or customer delivery is implemented in 6.2.

---

# 9. REFUND ELIGIBILITY AUTHORITY

Automatic full refund is deliberately narrow.

Allowed canonical reasons exactly:

```text
analysis_not_score_ready
analysis_failed
analysis_timed_out
report_failed
```

Before a refund operation is created, commerce MUST re-read the bound SiteScore resource server-side and re-prove the terminal state that authorizes the refund.

A cached local fulfillment state, n8n branch, browser flag, caller parameter, worker status, or earlier transient HTTP error is insufficient.

Persist a durable eligibility snapshot containing at least:

```text
order_id
eligibility_reason
resource_type = analysis|report
resource_id
server_observed_terminal_state
observed_at
sitescore_api_target_id
```

Once persisted for an order, the refund reason cannot be changed by an untrusted caller.

---

# 10. DURABLE REFUND OPERATION

Add a durable refund operation table, conceptually:

```text
commerce.refund_operations
```

At minimum persist:

```text
order_id                       PK/FK
operation_version              stripe_full_refund_v1
provider_idempotency_key
eligibility_reason
eligibility_resource_type
eligibility_resource_id
stripe_payment_intent_id
original_amount_received
currency
stripe_refund_id               nullable, unique when present
stripe_refund_status           nullable
stripe_refund_amount           nullable
failure_code                   nullable
created_at
updated_at
last_reconciled_at             nullable
```

Stable Stripe mutation key:

```text
sitescore:refund:v1:<order_id>
```

Persist the operation snapshot before Stripe mutation.

Refund parameters must be constructed only from durable server-side evidence, never from n8n/browser/caller amount or currency.

---

# 11. STRIPE PRE-REFUND RECONCILIATION

Before creating a refund, server-side retrieve/reconcile the exact PaymentIntent bound in 6.1.

At minimum prove:

```text
PaymentIntent ID == durable 6.1 stripe_payment_intent_id
PaymentIntent is the paid order's provider resource
currency == usd
amount_received is positive and coherent
livemode == configured expected mode
```

Then list existing Refund objects filtered to that PaymentIntent before mutation.

Required behavior:

```text
no existing refunds
-> eligible to create the one SiteScore full-refund operation

existing refund with matching SiteScore order/operation metadata
-> recover/bind/reconcile it; do NOT create another

provider already shows the payment fully refunded
-> reconcile local order to refunded with durable evidence; do NOT create another refund

partial/conflicting/unattributed refund state
-> fail closed to attention_required; do NOT blindly top-up or create a competing refund in 6.2
```

This provider-side lookup is required so response-loss/restart recovery does not rely only on a temporary Stripe idempotency-key retention window.

---

# 12. STRIPE REFUND CREATE CONTRACT

Use Stripe server-side only, SDK pin:

```text
stripe-python == 15.4.0
Stripe API version == 2026-07-29.dahlia
```

Every Stripe request must explicitly bind the API version; do not depend on the account default.

Create exactly one full refund against the durable PaymentIntent using an explicit amount equal to the server-observed original amount received.

Conceptual provider parameters:

```text
payment_intent = durable stripe_payment_intent_id
amount = durable original_amount_received
metadata.sitescore_order_id = order_id
metadata.sitescore_refund_operation = stripe_full_refund_v1
metadata.sitescore_refund_reason = durable eligibility reason
```

Do not accept caller amount, currency, reason, PaymentIntent, Charge, Refund ID, or metadata authority.

Do not use `fraudulent`, `duplicate`, or `requested_by_customer` as a fabricated semantic reason for an unfulfillable SiteScore refund; business reason stays in SiteScore metadata.

All mutation retries for one refund operation must reuse:

```text
same provider idempotency key
same PaymentIntent
same amount
same metadata
same explicit Stripe API version
```

On connection uncertainty, never mint a new refund operation or a new provider key.

---

# 13. REFUND RESPONSE / STATUS AUTHORITY

Validate every returned or retrieved Refund object against durable truth:

```text
refund ID is provider-issued
payment_intent == durable PaymentIntent
amount == durable full amount
currency == usd
metadata order/operation/reason bindings match when created by SiteScore
```

Closed provider statuses to understand:

```text
pending
requires_action
succeeded
failed
canceled
```

Local mapping:

```text
succeeded
-> order_state = refunded
-> payment_state = refunded
-> preserve terminal fulfillment reason

pending
-> payment_state = refund_pending
-> order remains non-fulfilled and non-refunded

requires_action
-> order_state = attention_required
-> payment_state = refund_pending

failed|canceled
-> order_state = attention_required
-> payment_state = refund_failed
```

A provider create HTTP 2xx is not by itself local `refunded`; Refund status must be server-observed and bound.

A failed refund must never change the canonical SiteScore terminal fulfillment reason.

---

# 14. AUTOMATION BOUNDARY FOR FUTURE N8N

6.2 must expose a narrow server-owned automation surface that 6.3 can orchestrate without receiving SiteScore or Stripe secrets.

Required conceptual routes:

```text
POST /v1/automation/orders/{order_id}/advance
GET  /v1/automation/orders/{order_id}
```

Protect them with a dedicated server-configured commerce automation bearer credential, conceptually:

```text
COMMERCE_AUTOMATION_API_KEY
```

Rules:

```text
missing/wrong credential -> 401 without existence disclosure
credential never logged/returned/persisted as plaintext
POST body carries no payment/refund/analysis/report truth fields
order_id is only a lookup/trigger identity
server state machine decides the permitted next action
```

`advance` is a trigger, not authority. It may call the internal ensure/reconcile operations above, but automation cannot choose `paid`, `completed`, `failed`, `refund`, amount, or provider IDs.

Return only a sanitized orchestration status such as:

```text
api_version
order_id
order_state
payment_state
fulfillment_state
retryable / terminal guidance
```

Do not return Stripe secret material, SiteScore service key, private report storage information, or provider raw responses.

6.3 will implement the n8n workflow using this narrow boundary. Do not add n8n workflow JSON in 6.2.

---

# 15. CONCURRENCY / CRASH WINDOWS

Prove at least these windows:

```text
A. analysis POST accepted -> commerce loses HTTP response
   retry same SiteScore key/payload -> one durable analysis

B. analysis response obtained -> local analysis bind commit fails
   restart -> same operation recovers same analysis

C. concurrent advance on paid/not_started order
   -> one logical analysis resource, one local analysis binding

D. report resolver response obtained -> local report bind commit fails
   -> retry converges on same report

E. refund create succeeds -> local refund bind commit fails
   -> restart/provider lookup recovers existing refund, no second refund

F. refund create response lost
   -> same operation/key/params and provider lookup; no duplicate refund

G. concurrent refund triggers
   -> at most one SiteScore refund operation / one full provider refund effect

H. provider shows full external refund before local bind
   -> reconcile to refunded, no second refund

I. provider shows partial/conflicting external refund
   -> attention_required, no blind additional refund
```

Never hold a PostgreSQL transaction open across SiteScore or Stripe network I/O.

---

# 16. STATE / MONEY INVARIANTS

Required global invariants:

```text
unpaid order cannot start analysis
refunded order cannot restart fulfillment
fulfilled order cannot be automatically refunded by 6.2
analysis_id belongs to exactly one order binding
report_id belongs to exactly one order binding
refund operation belongs to exactly one order
one order cannot have two SiteScore-owned full refund operations
report ready never implies delivery completed
payment paid never implies analysis/report success
n8n/browser never write payment or refund truth
```

The following remains the only successful handoff into 6.4 delivery:

```text
order_state = fulfillment_in_progress
payment_state = paid
fulfillment_state = delivery_pending
bound report_state = ready
```

---

# 17. ERROR POLICY

Fail closed and sanitize errors.

Conceptual behavior:

```text
commerce DB unavailable -> 503
SiteScore network/429/5xx -> retryable 503, no refund
SiteScore auth/config failure -> attention/config error, no refund
malformed/mismatched SiteScore response -> invariant failure, no refund
Stripe network uncertainty -> refund_pending/retryable evidence, no second operation
Stripe invariant mismatch -> attention_required
unknown order behind automation auth -> non-disclosing 404
invalid automation credential -> 401
```

Do not expose tracebacks, service credentials, Stripe request bodies containing secrets, or frozen API internals.

---

# 18. MIGRATION / DATABASE PROOF

Real PostgreSQL 16 is mandatory.

Prove:

```text
upgrade 0002 -> 0003
full downgrade to base where supported
upgrade back to 0003
commerce.alembic_version remains under commerce schema
no public.alembic_version
all new FK/unique/check constraints are enforced by PostgreSQL
```

Downgrade must not destroy the `commerce` schema while Alembic still relies on `commerce.alembic_version`.

---

# 19. REQUIRED ADVERSARIAL TEST SURFACE

Add substantial deterministic coverage; target at least 60 new/expanded 6.2 cases across unit + real PostgreSQL integration.

Minimum categories:

```text
1. unpaid order cannot analyze
2. expired/refunded order cannot analyze
3. exact stored AnalysisRequest used
4. caller cannot inject analysis payload
5. stable SiteScore idempotency key
6. config drift cannot change existing analysis operation target/payload
7. same-key retry after lost response
8. analysis ID mismatch rejected
9. duplicate/conflicting analysis binding rejected
10. queued mapping
11. running mapping
12. completed mapping
13. not_score_ready refund eligibility
14. failed refund eligibility
15. timed_out refund eligibility
16. 401/403 does not refund
17. 404 does not blindly refund
18. 429/5xx/network does not refund
19. malformed/unknown analysis state does not refund
20. report resolver only after completed
21. report ready -> delivery_pending
22. report failed -> refund eligibility
23. report ID conflict rejected
24. report content not downloaded in 6.2
25. refund eligibility server-side re-verification required
26. local cached state alone cannot refund
27. n8n request cannot choose refund
28. browser cannot choose refund
29. PaymentIntent mismatch rejected
30. livemode mismatch rejected
31. non-USD mismatch rejected
32. amount_received invalid rejected
33. stable refund provider key
34. durable refund params survive config drift
35. full refund exact amount
36. no caller refund amount
37. no caller PaymentIntent/Charge/Refund ID
38. matching provider refund recovery
39. full pre-existing refund reconciliation
40. partial existing refund -> attention, no top-up
41. conflicting refund metadata -> attention
42. provider timeout retry same key/params
43. create-success/local-bind-loss recovery
44. response-loss recovery after restart
45. concurrent refund triggers
46. one local refund operation
47. succeeded -> refunded
48. pending -> refund_pending
49. requires_action -> attention + refund_pending
50. failed -> refund_failed
51. canceled -> refund_failed
52. refund object amount mismatch rejected
53. refund PI mismatch rejected
54. refund currency mismatch rejected
55. refund metadata mismatch rejected
56. terminal fulfillment reason preserved after refund
57. refunded order cannot re-enter fulfillment
58. automation auth missing/wrong
59. automation response secret-free
60. concurrent advance PostgreSQL safety
61. no DB transaction across provider I/O regression
62. migration constraints
63. secret scan
64. frozen-scope scan
```

---

# 20. CI / FREEZE REGRESSION GATE

Temporary exact-head validation workflow is allowed only for checkpoint validation and must be removed before final review unless repository policy says otherwise.

CI must prove at exact validated SHA:

```text
Python 3.11.x
PostgreSQL 16.x
exact dependency pins
sitescore-commerce full suite PASS
commerce migration upgrade/downgrade/upgrade PASS
commerce migration namespace PASS
secret scan PASS
frozen source-scope scan PASS
frozen FAZ 5 migrations PASS
sitescore-report 24 PASS
sitescore-api 105 PASS
sitescore-app 19 PASS
sitescore-pipeline 53 PASS
sitescore-benchmarks 191 PASS
sitescore-metrics 67 PASS
sitescore-spatial 180 PASS
sitescore-providers 418 PASS
sitescore-data 361 PASS
sitescore-core 86 PASS
frozen total 1504 PASS
private S3-compatible regression PASS
Redis/Celery transport regression PASS
```

If the validated SHA differs from the final review SHA, provide an exact compare proof and only non-product cleanup may remain.

---

# 21. EXPLICITLY OUT OF SCOPE

Do NOT implement in 6.2:

```text
n8n workflow JSON or deployment
Postmark email
customer delivery grant/token
public /d/{token}
report PDF streaming through commerce
outbox publisher/dispatcher as a production scheduler
broad periodic recovery scanner
manual admin refund UI
partial refund product policy
customer-requested discretionary refunds
new scoring/readiness/report semantics
FAZ 7 or FAZ 8 work
```

Do not alter frozen FAZ 3/4/5 packages or semantics.

---

# 22. IMPLEMENTER HANDOFF REQUIREMENTS

When implementation is complete, update `implementer.md` with:

```text
CURRENT_CHECKPOINT: 6.2
IMPLEMENTER_STATE: READY_FOR_REVIEW
exact expected base SHA
branch
PR number/state/draft/mergeable
final HEAD SHA
validated SHA
validated -> final delta proof
migration head
package/dependency versions
new durable tables/constraints
SiteScore operation idempotency evidence
refund provider idempotency + provider-lookup recovery evidence
automation auth boundary evidence
commerce test count
frozen 1504 baseline evidence
PostgreSQL version
validation run/job IDs
secret/frozen-scope scans
START_6_3: NO
```

Then STOP.

Reviewer will independently review live GitHub and exact SHA. Implementer must not merge without a later Reviewer `READY_TO_LOCK` and literal user `LOCK`.

Reviewer STOP.
