# FAZ 6-FINAL — Integrated Commerce Audit + Freeze Candidate

## Audit decision scope

This artifact audits the already locked FAZ 6.0–6.5 commerce stack after the corrective runtime HTTP-surface lock. It is **audit/freeze-only**: it introduces no new commerce capability, authority path, state transition, endpoint, migration, dependency, provider behavior, n8n behavior, scoring behavior, or report behavior.

Product truth remains exactly:

> Mathematically validated scoring engine; empirical validation pending.

Engineering, integration, concurrency, migration, transport, recovery, and freeze validation are **not empirical business-outcome validation**.

## 1. Exact final base and lock provenance

The resumed 6-FINAL candidate is based exactly on:

```text
main@df4e3181712e7f426f8f1752628952a620c98f05
```

The prior final PR #29 was based on pre-corrective `main@287367ce8eb708efce0ebae0a2f9c90d681cce01` and is not lock-eligible after the corrective merge. This rebuilt candidate removes that stale lineage.

| Checkpoint | PR | Approved head | Merge commit | Merge parent 1 | Merge parent 2 |
|---|---:|---|---|---|---|
| 6.0 | #23 | `8a4e358709ae7a662bf079722db042fb6e319ffd` | `af3b9567d644f6bcf0410af704dd7d86de41b5ce` | `0e370940ee5c8c1253db72fa7e33078fb4ef3b2c` | `8a4e358709ae7a662bf079722db042fb6e319ffd` |
| 6.1 | #24 | `719a17c4359524337f57298252a59ccb89dcd0aa` | `8027239b4b168e98e8ee16e15787366632017156` | `af3b9567d644f6bcf0410af704dd7d86de41b5ce` | `719a17c4359524337f57298252a59ccb89dcd0aa` |
| 6.2 | #25 | `3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628` | `acc213ac52f980789164d9fedcd4e18deeefcf75` | `8027239b4b168e98e8ee16e15787366632017156` | `3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628` |
| 6.3 | #26 | `64887a560c4af492312e726f990363fc5010345d` | `7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba` | `acc213ac52f980789164d9fedcd4e18deeefcf75` | `64887a560c4af492312e726f990363fc5010345d` |
| 6.4 | #27 | `1f22c4a09c08c2803c746b87a20209d7fdf6c574` | `bdf43a891ca14941ba2f2c4f115e4a15bec0015a` | `7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba` | `1f22c4a09c08c2803c746b87a20209d7fdf6c574` |
| 6.5 | #28 | `4ed902dd9ebf230dcb983392705ab0d95bb0c846` | `287367ce8eb708efce0ebae0a2f9c90d681cce01` | `bdf43a891ca14941ba2f2c4f115e4a15bec0015a` | `4ed902dd9ebf230dcb983392705ab0d95bb0c846` |
| corrective HTTP surface | #30 | `813e3436bc3f899a774c853a6a81ba7924b54c42` | `df4e3181712e7f426f8f1752628952a620c98f05` | `287367ce8eb708efce0ebae0a2f9c90d681cce01` | `813e3436bc3f899a774c853a6a81ba7924b54c42` |

Corrective lock resolves `FIN6-H002`: the actual constructed FastAPI application now has only the authorized seven routes, with OpenAPI/Swagger/ReDoc/OAuth helper routes disabled. `FIN6-H001` remains covered by the fail-closed source registration gate as defense in depth.

## 2. Frozen runtime identities

```text
sitescore-commerce: 0.6.0
migration head: 0005_recovery_reconciliation
Python: 3.11
PostgreSQL: 16
Stripe SDK: 15.4.0
Stripe API: 2026-07-29.dahlia
httpx: 0.28.1
n8n runtime: 2.33.4
n8n image: n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
order workflow SHA256: 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery workflow SHA256: f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
frozen FAZ 3/4/5 baseline: 1504 PASS
```

Migration chain remains:

```text
0001_commerce_order_checkout
-> 0002_webhook_payment_authority
-> 0003_fulfillment_refund
-> 0004_delivery_email
-> 0005_recovery_reconciliation
```

## 3. Integrated business-authority chain

Canonical successful path:

```text
purchase intent
-> durable order/catalog snapshot
-> Stripe Checkout
-> verified Stripe payment authority
-> durable paid transition + exactly-one durable order.paid.v1 identity
-> at-least-once outbox dispatch
-> bounded n8n orchestration
-> frozen SiteScore /v1 analysis/report truth
-> digest-only delivery grant
-> validated Postmark acceptance evidence
-> fulfilled
```

Canonical unfulfillable path:

```text
paid
-> authoritative SiteScore not_score_ready / analysis failure / timeout / report failure
-> fresh server-side proof
-> exact full Stripe refund authority
-> durable refunded
```

Recovery never creates a parallel business-authority path. It uses fresh provider evidence, existing durable identities, lease fencing, and the already locked payment/fulfillment/refund/delivery primitives.

## 4. Exact resolved Commerce HTTP surface

The **constructed runtime application**, not merely source text, is frozen to exactly:

```text
POST /v1/orders
POST /v1/webhooks/stripe
POST /v1/automation/orders/{order_id}/advance
POST /v1/automation/orders/{order_id}/deliver
GET  /v1/automation/orders/{order_id}
POST /v1/automation/recovery/run
GET  /d/{opaque_token}
```

The following framework routes are absent from the resolved application:

```text
/openapi.json
/docs
/redoc
/docs/oauth2-redirect
```

The permanent freeze gate constructs `create_app(...)`, inspects `app.routes`, and requires exact equality with the seven-route set. The AST route-registration gate remains an additional fail-closed detector for alternate methods, dynamic `api_route`, routers, mounts, websocket registration, and imperative route drift.

Automation POST bodies remain empty/server-owned. n8n cannot submit payment truth, target state, provider results, analysis/report identity, refund amount/reason, recipient, or delivery truth.

## 5. Order/catalog/Checkout invariants

- Product remains server-owned `location_report_v1`.
- Stripe Price, quantity `1`, USD binding, catalog version, redirect bases, and provider operation identity are server-owned.
- Purchase intent has immutable canonical request/hash lineage.
- Checkout operation snapshot is durable before provider I/O.
- Provider idempotency identity survives response loss, process restart, and deployment config drift.
- Browser redirect is presentation/correlation only and never payment authority.
- Caller cannot submit amount, currency, Stripe object identity, paid state, refund state, or fulfillment state.

## 6. Stripe payment authority invariants

- Webhook body is bounded before processing.
- Official Stripe signature verification is authoritative for webhook ingress.
- Real Stripe Event ID is semantic event identity; raw-body hash is byte evidence only.
- Duplicate same-event semantics are idempotent even if JSON serialization bytes differ.
- Fresh Checkout Session + line-item evidence is revalidated against exact order/catalog/Price/quantity/USD/livemode binding.
- Paid requires exact `complete + paid + PaymentIntent` evidence.
- Server-poll recovery uses a distinct immutable poll receipt and does not fabricate `evt_*`, webhook signature, or inbox identity.
- Webhook/poll races converge to one terminal payment truth and at most one durable paid outbox row.
- Paid-after-expired or expired-after-paid contradiction fails closed to attention.

## 7. Outbox, fulfillment, and frozen SiteScore boundary

- Paid transition and `order.paid.v1` identity remain atomic/idempotent.
- Replay uses the original outbox UUID, event type, order ID, and occurred-at value; publication history is not replaced.
- Commerce consumes SiteScore only through authenticated frozen `/v1` HTTP contracts.
- Commerce does not import frozen scoring/report authority or write frozen API-owned DB tables.
- Analysis/report IDs and operation identities are durable server-observed bindings.
- n8n branches only on Commerce projection and never becomes scoring/readiness/report/refund/delivery truth.

## 8. Refund money-safety invariants

- Email/delivery failure alone never authorizes refund.
- Refund eligibility comes from fresh canonical unfulfillable SiteScore evidence.
- Refund is full/exact for the original captured money/currency under the locked V1 contract.
- Stripe refund history is reconciled before create.
- Reserved `sitescore_*` refund metadata must exactly match the durable operation identity.
- Partial/mixed/multiple/malformed/conflicting refund history fails closed.
- Response-loss recovery converges to existing refund evidence without duplicate money movement.
- Refunded terminal state cannot later fabricate fulfillment.

## 9. Delivery/email invariants

- Delivery capability uses 32 random bytes and persists only SHA-256 token digest.
- Raw delivery token is not persisted or exported to n8n/provider metadata.
- Grant is exact order/report-bound, expiring, revocable, and validated at download time.
- `/d/{opaque_token}` revalidates paid/not-refunded state, report ownership/readiness, and content integrity, then proxies bytes instead of redirecting to private storage.
- Public base authority is server-configured HTTPS, not caller Host header.
- Postmark HTTP 200 alone is insufficient; `provider_accepted` requires complete validated acceptance evidence.
- Incomplete/unverifiable success-like response becomes `provider_uncertain` and cannot mark fulfilled.
- At-least-once retry may duplicate safe provider attempts but cannot claim exactly-once delivery.

## 10. Recovery/reconciliation invariants

- Candidate scanning is bounded and oldest-first.
- Claims use durable lease token/expiry and `FOR UPDATE SKIP LOCKED`.
- Claim transaction commits before Stripe/n8n I/O; no DB row lock spans network calls.
- Post-I/O writes re-lock exact state and require current lease identity; stale/reclaimed workers cannot overwrite newer results.
- Legacy pre-0005 verified Stripe inbox lineage resumes using original real event identity and structural correlation.
- Missing webhook can be recovered only by exact bound Checkout server poll with the same payment binding rules.
- Paid outbox recovery revalidates durable paid/Stripe authority before n8n I/O.
- Unpublished publish and published stale replay reuse the same durable event identity.
- 2xx confirms n8n transport acceptance only. Timeout/connection loss/429/5xx retry with bounded backoff; auth/contract rejection becomes durable attention rather than hot-looping.
- Missing/duplicate outbox, contradictory Stripe binding, reserved refund metadata conflict, or other impossible shapes produce sanitized durable findings instead of silent repair.
- Existing `attention_required` and terminal fulfilled/refunded/expired states are not automatically reopened.

## 11. n8n freeze invariants

- Runtime is exactly `2.33.4`; pinned image digest and both workflow hashes are frozen above.
- Order workflow has no Code/Function business-authority node.
- It uses only narrow Commerce HTTP boundaries and finite Wait/poll horizon.
- Duplicate trigger, timeout, response-loss, restart, delivery retry, and poll-horizon behavior converge from durable Commerce state.
- Recovery scheduler is a minimal five-minute Schedule Trigger -> one bodyless authenticated Commerce recovery POST.
- n8n has no direct Stripe, SiteScore, Postmark, DB, Redis, S3, recipient-email, raw-token, or report-byte authority.

## 12. Security/privacy/frozen-boundary invariants

Freeze scans must remain clean for:

- Stripe secret/webhook secret leakage;
- Postmark token leakage;
- SiteScore service credential leakage;
- DB/Redis/S3 credentials or private storage URLs;
- raw delivery token persistence/logging;
- recipient/customer email entering n8n state;
- raw provider response persistence;
- caller-controlled money/provider/business truth;
- frozen FAZ 3/4/5 source mutation or direct runtime imports.

Frozen SiteScore tests remain `1504 PASS`, including private S3 and Redis/Celery transport regressions.

## 13. State / money invariant matrix

| Class | Order state | Payment state | Fulfillment state | Money / authority invariant | Recovery behavior |
|---|---|---|---|---|---|
| pending payment | `pending_payment` | `pending` | `not_started` | no paid authority | stale exact Checkout may be server-polled |
| expired/unpaid | `expired` | `expired` | `not_started` | no capture/refund fabrication | terminal; no provider business I/O |
| paid + analysis pending/running | `fulfillment_in_progress` | `paid` | `analysis_pending` / `analysis_running` | capture authoritative; no fulfillment yet | same paid outbox identity resumes orchestration |
| paid + report pending | `fulfillment_in_progress` | `paid` | `report_pending` | no report-ready fabrication | same identity replay resumes Commerce authority |
| paid + delivery pending | `fulfillment_in_progress` | `paid` | `delivery_pending` | paid remains paid; delivery not yet accepted | replay re-enters locked delivery path |
| paid + provider_uncertain delivery | `fulfillment_in_progress` | `paid` | `delivery_pending` | uncertain email is not fulfillment proof | bounded retry/reconciliation |
| paid + delivery_failed/attention | `attention_required` | `paid` | `delivery_failed` | delivery failure is not refund authority | operator attention; no hot loop |
| fulfilled | `fulfilled` | `paid` | `completed` | accepted provider evidence exists | terminal/no recovery business I/O |
| refund pending | `fulfillment_in_progress` | `refund_pending` | canonical unfulfillable state | exact full refund operation already authorized | locked refund reconciliation resumes |
| refunded | `refunded` | `refunded` | canonical unfulfillable state | exact full refund evidence | terminal/no fulfillment fabrication |
| corrupt/impossible | safe unchanged or `attention_required` | unchanged authoritative truth | safe unchanged/failure state | no synthetic authority | sanitized finding/attention |

The system permits **at-least-once execution and duplicate-safe replay**. It does **not** claim exactly-once delivery or exactly-once execution. Business effects converge through durable uniqueness/idempotency plus authority revalidation.

## 14. Required final validation record

The final candidate requires fresh exact-head validation from the corrective base. Authoritative execution evidence is recorded in the Implementer handoff after the exact candidate runs complete. The audit record must be interpreted together with that exact-head coordination evidence; stale pre-corrective PR #29 validation is explicitly non-authoritative for the final freeze.

Required fresh gates are:

```text
full sitescore-commerce suite
final permanent freeze gate
resolved runtime exact-seven HTTP surface
OpenAPI/docs/ReDoc/OAuth helper routes absent
migration 0001 -> 0005, downgrade base, re-upgrade
migration head == 0005_recovery_reconciliation
n8n static baseline
locked order n8n 2.33.4 runtime
recovery scheduler runtime
recovery replay convergence
frozen FAZ 3/4/5 == 1504 PASS
private S3 regression
Redis/Celery transport
frozen-scope scan
secret-boundary scan
package/workflow/image identity checks
```

## 15. Freeze-candidate conclusion

On `main@df4e3181712e7f426f8f1752628952a620c98f05`, the locked FAZ 6.0–6.5 system plus corrective HTTP-surface lock forms one coherent production Commerce authority chain. This 6-FINAL candidate changes only this audit artifact and executable freeze-gate tests. Any newly discovered defect requiring production/runtime/migration/dependency/n8n semantic change must stop this audit and return to Reviewer authority; it must not be silently patched in 6-FINAL.
