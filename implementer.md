# SiteScore AI — Implementer → Reviewer Handoff

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.0
CHECKPOINT_TITLE: Commerce / Order Domain + Stripe Checkout Foundation
IMPLEMENTER_STATE: READY_FOR_REVIEW
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 0e370940ee5c8c1253db72fa7e33078fb4ef3b2c
LIVE_MAIN_SHA_AT_HANDOFF: 0e370940ee5c8c1253db72fa7e33078fb4ef3b2c
CODE_BRANCH: faz6/6-0-commerce-order-checkout
PR: #23
PR_STATE: OPEN
PR_DRAFT: FALSE
PR_MERGEABLE: TRUE
PR_MERGED: FALSE
HEAD_SHA: 6790cc2eccb858f80857103e99f9b5562e8db485

REVIEWER_STATE_SEEN: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION_SEEN: IMPLEMENT
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
BLOCKERS_REPORTED_BY_REVIEWER: NONE
BLOCKERS_REPORTED_BY_IMPLEMENTER: NONE

VALIDATED_SHA: 3cb5427b663ef38876c9f9f62e12e6bbb29f48d8
VALIDATION_WORKFLOW: faz6-6-0-exact-head-validation
VALIDATION_RUN_ID: 32238540680
VALIDATION_JOB_ID: 96023819318
VALIDATION_CONCLUSION: SUCCESS
EXACT_HEAD_CHECKOUT_ASSERTION: PASS
TEMP_VALIDATION_WORKFLOW_REMOVED: YES
VALIDATED_TO_FINAL_COMMITS: 1
VALIDATED_TO_FINAL_DELTA: ONLY .github/workflows/faz6-6-0-validation.yml REMOVAL

LOCAL_PREPUBLICATION_COMMERCE_TESTS: 38 PASS
SITESCORE_COMMERCE_CI_TESTS: 49 PASS
SITESCORE_REPORT_TESTS: 24 PASS
SITESCORE_API_TESTS: 105 PASS
FROZEN_PACKAGE_REGRESSION_TESTS: 1375 PASS
FROZEN_TOTAL_TESTS: 1504 PASS
COMBINED_PYTEST_TOTAL: 1553 PASS

POSTGRESQL_VERSION: 16.15
COMMERCE_MIGRATION: 0001_commerce_order_checkout PASS
COMMERCE_SCHEMA_ISOLATION: PASS
COMMERCE_ALEMBIC_VERSION_TABLE: commerce.alembic_version PASS
PRIVATE_S3_COMPATIBLE_STORAGE_REGRESSION: PASS
REDIS_CELERY_EXECUTION_TRANSPORT: PASS
SECRET_SCAN: PASS
FROZEN_SCOPE_SCAN: PASS

FAZ_3_STATUS_PRESERVED: FROZEN
FAZ_4_STATUS_PRESERVED: FROZEN
FAZ_5_STATUS_PRESERVED: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: READY_FOR_REVIEW
START_6_1: NO
```

## 1. Scope implemented

Only FAZ 6.0 was implemented. No 6.1+ subsystem was started.

The checkpoint adds a new isolated package:

```text
sitescore-commerce==0.1.0
```

Implemented capabilities:

1. dedicated PostgreSQL `commerce` schema;
2. dedicated Alembic history and `commerce.alembic_version`;
3. durable commerce order identity;
4. server-owned V1 product catalog containing only `location_report_v1`;
5. strict `POST /v1/orders` boundary;
6. caller `Idempotency-Key` semantics backed by durable PostgreSQL uniqueness;
7. canonical normalized request hash binding;
8. durable purchase-intent persistence sufficient for later server-owned analysis creation;
9. server-owned Stripe Price ID selection;
10. server-created hosted Stripe Checkout Session;
11. deterministic server-owned Stripe idempotency key based on `order_id`;
12. durable Checkout-operation and Stripe Session binding;
13. fail-closed Checkout response validation;
14. safe server-owned success/cancel redirect construction;
15. frozen four-sector AnalysisRequest conformance tests without a runtime `sitescore_api` import;
16. isolated HTTP and persistence error sanitization;
17. concurrency and external-response-loss recovery foundations for 6.0.

Explicitly NOT implemented:

```text
Stripe webhook/payment authority
paid transition
paid outbox
SiteScore analysis dispatch
report dispatch
refund
n8n
Postmark
delivery grants
public download
reconciliation workers
```

Those remain 6.1+ scope.

## 2. Changed files

Final PR #23 contains exactly 22 changed files, all under `sitescore-commerce/`:

```text
sitescore-commerce/README.md
sitescore-commerce/alembic.ini
sitescore-commerce/alembic/env.py
sitescore-commerce/alembic/versions/0001_commerce_order_checkout.py
sitescore-commerce/docs/CHECKPOINT_6_0_COMMERCE_ORDER_STRIPE_CHECKOUT.md
sitescore-commerce/pyproject.toml
sitescore-commerce/src/sitescore_commerce/__init__.py
sitescore-commerce/src/sitescore_commerce/api.py
sitescore-commerce/src/sitescore_commerce/checkout.py
sitescore-commerce/src/sitescore_commerce/contracts.py
sitescore-commerce/src/sitescore_commerce/db.py
sitescore-commerce/src/sitescore_commerce/service.py
sitescore-commerce/src/sitescore_commerce/settings.py
sitescore-commerce/tests/conftest.py
sitescore-commerce/tests/test_api.py
sitescore-commerce/tests/test_architecture.py
sitescore-commerce/tests/test_checkout_adapter.py
sitescore-commerce/tests/test_conformance.py
sitescore-commerce/tests/test_contracts.py
sitescore-commerce/tests/test_postgres_integration.py
sitescore-commerce/tests/test_service.py
sitescore-commerce/tests/test_settings.py
```

No frozen FAZ 3/4/5 runtime package is modified.

## 3. Dependencies and exact pins

Runtime:

```text
fastapi==0.140.0
pydantic==2.13.4
SQLAlchemy==2.0.51
alembic==1.18.5
psycopg[binary]==3.3.4
stripe==15.4.0
```

Test:

```text
httpx==0.28.1
pytest==8.4.2
```

Stripe API version is pinned fail-closed to:

```text
2026-07-29.dahlia
```

The deployment cannot silently substitute the Stripe account default API version; an unequal configured `STRIPE_API_VERSION` raises configuration failure.

## 4. Commerce persistence and migration

Migration:

```text
0001_commerce_order_checkout
```

Schema/tables:

```text
commerce.orders
commerce.order_idempotency
commerce.checkout_sessions
commerce.alembic_version
```

The migration touches only the `commerce` schema. Frozen `sitescore-api` tables and its Alembic history are not written by commerce.

Database check constraints close the declared order/payment/fulfillment state vocabularies.

6.0 authors only:

```text
order_state       = pending_payment
payment_state     = pending
fulfillment_state = not_started
```

Checkout creation does not author `paid`.

## 5. Public HTTP contract

Route:

```text
POST /v1/orders
```

Required header:

```text
Idempotency-Key
```

Request authority is limited to:

```text
product_code = location_report_v1
customer_email
analysis_request
```

`analysis_request` is a strict commerce-local mirror/conformance boundary for the frozen four-sector request shapes:

```text
coffee
restaurant
gym
beauty
```

Caller-controlled authority fields such as amount, currency, Stripe Price ID, quantity, discount/coupon authority, `paid`, payment status, redirect URLs, Stripe identities, `analysis_id`, `report_id`, or analytical trust flags are rejected via `extra=forbid`.

Success response exposes only:

```text
api_version
request_id
order_id
product_code
order_state
payment_state
fulfillment_state
checkout_url
checkout_expires_at
```

Internal request hashes, caller-key digests, provider idempotency identity and Stripe Checkout Session ID are not exposed in the V1 order-create response.

## 6. Product catalog and Stripe Checkout binding

The server-owned catalog fixes:

```text
product_code       = location_report_v1
catalog_version    = v1
quantity           = 1
currency_expectation = USD
stripe_price_id    = deployment configuration
```

Stripe Checkout construction is:

```text
mode = payment
ui_mode = hosted
payment_method_types = [card]
line_items = existing server-owned Price ID x quantity 1
client_reference_id = order_id
customer_email = durable order email
```

Server metadata binds:

```text
sitescore_order_id
sitescore_product_code
sitescore_catalog_version
```

PaymentIntent metadata additionally binds order/product identity.

No caller-derived `price_data` is used.

The provider response is validated for Session identity shape, HTTPS hosted URL, payment mode, exact order client reference, and expected metadata before durable binding.

## 7. Idempotency, concurrency, and uncertainty behavior

Caller idempotency:

- the raw `Idempotency-Key` is validated;
- it is stored only as SHA-256 digest;
- a canonical normalized request SHA-256 binds key to content;
- same key + same canonical request returns the same durable `order_id`;
- same key + different canonical request returns idempotency conflict;
- PostgreSQL uniqueness is the concurrency authority.

Stripe idempotency is separate and server-owned:

```text
sitescore:checkout:v1:<order_id>
```

The caller key is not forwarded to Stripe.

The order, caller-idempotency claim and Checkout-operation identity are committed before Stripe I/O. No database transaction is held open across the external Stripe call.

If Stripe creates the Checkout Session but the response is lost, retry uses the same server-owned operation key and same logical parameters. If provider response is observed but durable binding fails, the unpersisted URL is not returned; retry is expected to converge through provider idempotency.

## 8. Security controls

- Stripe secret and Price ID are environment configuration only.
- No production secret was committed.
- production success/cancel bases require HTTPS;
- embedded URL credentials, fragments and pre-existing query strings are rejected;
- HTTP redirect bases are limited to localhost in test/development;
- browser success/cancel return is correlation/presentation only, never payment authority;
- provider/database exception internals are sanitized from HTTP error responses;
- runtime source has no `sitescore_api` import;
- frozen scope scan is green;
- secret scan is green.

## 9. Validation chronology and hardening closure

### Validation run 1

```text
run: 32238187463
job: 96022738067
result: FAILED
```

A real PostgreSQL concurrency test exposed a persistence-ordering defect: because no ORM relationships intentionally exist between the rows, SQLAlchemy did not guarantee that the parent `orders` insert would precede `checkout_sessions`, causing an FK violation.

Fix on the same branch/PR:

- explicitly flush parent `orders` row first;
- then insert/flush the durable idempotency claim;
- then add the Checkout-operation child row;
- all remain inside the same PostgreSQL transaction.

This is persistence hardening only; no authority or state semantics changed.

### Validation run 2

```text
run: 32238407741
job: 96023408792
result: FAILED
```

The implementation was not reached. The temporary validation workflow used `fetch-depth: 2`; after the hardening commit, the frozen base commit was no longer present in the shallow checkout and the ancestry guard produced a false-negative.

Harness-only fix:

```text
fetch-depth: 0
```

### Authoritative validation run 3

```text
validated SHA: 3cb5427b663ef38876c9f9f62e12e6bbb29f48d8
run: 32238540680
job: 96023819318
conclusion: SUCCESS
```

Evidence:

```text
Python: 3.11.15
PostgreSQL: 16.15
exact dependency pins: PASS
pip check: PASS
commerce migration: PASS
commerce schema isolation: PASS
sitescore-commerce: 49 PASS
secret scan: PASS
frozen-scope scan: PASS
private S3-compatible report artifact regression: PASS
sitescore-report: 24 PASS
sitescore-api: 105 PASS
Redis/Celery execution transport: PASS
sitescore-app: 19 PASS
sitescore-pipeline: 53 PASS
sitescore-benchmarks: 191 PASS
sitescore-metrics: 67 PASS
sitescore-spatial: 180 PASS
sitescore-providers: 418 PASS
sitescore-data: 361 PASS
sitescore-core: 86 PASS
frozen package subtotal: 1375 PASS
frozen total incl. report/api: 1504 PASS
combined pytest total incl. commerce: 1553 PASS
```

The commerce suite emitted 3 Alembic configuration deprecation warnings concerning absent `path_separator`; they are non-failing warnings and do not affect migration correctness or test results. No test failure remains.

## 10. Temporary validation workflow cleanup proof

The exact-head workflow was intentionally temporary.

Validated SHA:

```text
3cb5427b663ef38876c9f9f62e12e6bbb29f48d8
```

Final review head:

```text
6790cc2eccb858f80857103e99f9b5562e8db485
```

GitHub compare proves:

```text
status: ahead
ahead_by: 1
behind_by: 0
total_commits: 1
only file delta:
.github/workflows/faz6-6-0-validation.yml -> REMOVED
```

There is no runtime/test/migration/doc code change between the validated SHA and final review head.

## 11. Final self-audit

```text
exact frozen base: PASS
live main unchanged at handoff: PASS
branch scope 6.0 only: PASS
PR #23 base main: PASS
PR #23 open: PASS
PR #23 draft false: PASS
PR #23 mergeable: PASS
PR #23 not merged: PASS
frozen package source changes: NONE
commerce package isolated: PASS
runtime sitescore_api import: NONE
server-owned product/Price identity: PASS
caller amount/currency/payment forgery prevention: PASS
strict request boundary: PASS
order idempotency: PASS
same-key/different-payload conflict: PASS
concurrent same-key uniqueness: PASS
server-owned Stripe idempotency identity: PASS
no transaction across Stripe I/O: PASS
Checkout result binding validation: PASS
payment authority not claimed: PASS
browser redirect not authority: PASS
secrets committed: NONE
secret scan: PASS
PostgreSQL 16 migration/integration: PASS
full frozen regression: PASS
validated-to-final delta proof: PASS
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
BLOCKERS_REPORTED_BY_IMPLEMENTER: NONE
```

## 12. Reviewer action requested

Reviewer should audit PR #23 at exact final review head:

```text
6790cc2eccb858f80857103e99f9b5562e8db485
```

against the FAZ 6.0 contract and the validated SHA/delta evidence above.

Implementer is now STOPPED at:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
```

No merge, semantic LOCK, FAZ 6.0 freeze, or FAZ 6.1 work has been performed.