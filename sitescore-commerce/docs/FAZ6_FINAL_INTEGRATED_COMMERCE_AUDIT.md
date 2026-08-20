# FAZ 6-FINAL — Integrated Commerce Audit + Freeze Candidate

## Audit decision scope

This artifact audits the composition of the already locked FAZ 6.0–6.5 commerce stack. It does not introduce a new subsystem, state transition, provider authority, migration, dependency, endpoint, n8n behavior, or scoring/report behavior.

Product truth remains:

> Mathematically validated scoring engine; empirical validation pending.

Engineering, integration, concurrency, migration, transport, and recovery validation in this audit are **not** empirical business-outcome validation.

## 1. Exact base and lock provenance

6-FINAL base is exact `main@287367ce8eb708efce0ebae0a2f9c90d681cce01`.

| Checkpoint | PR | Approved head | Merge commit | Merge parent 1 | Merge parent 2 |
|---|---:|---|---|---|---|
| 6.0 | #23 | `8a4e358709ae7a662bf079722db042fb6e319ffd` | `af3b9567d644f6bcf0410af704dd7d86de41b5ce` | `0e370940ee5c8c1253db72fa7e33078fb4ef3b2c` | `8a4e358709ae7a662bf079722db042fb6e319ffd` |
| 6.1 | #24 | `719a17c4359524337f57298252a59ccb89dcd0aa` | `8027239b4b168e98e8ee16e15787366632017156` | `af3b9567d644f6bcf0410af704dd7d86de41b5ce` | `719a17c4359524337f57298252a59ccb89dcd0aa` |
| 6.2 | #25 | `3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628` | `acc213ac52f980789164d9fedcd4e18deeefcf75` | `8027239b4b168e98e8ee16e15787366632017156` | `3ed6f6e323fdf4e3b0ef63e8c083d4f978e12628` |
| 6.3 | #26 | `64887a560c4af492312e726f990363fc5010345d` | `7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba` | `acc213ac52f980789164d9fedcd4e18deeefcf75` | `64887a560c4af492312e726f990363fc5010345d` |
| 6.4 | #27 | `1f22c4a09c08c2803c746b87a20209d7fdf6c574` | `bdf43a891ca14941ba2f2c4f115e4a15bec0015a` | `7b0b63eb3f4a9fbd74a0bfd92ef793c7d7522fba` | `1f22c4a09c08c2803c746b87a20209d7fdf6c574` |
| 6.5 | #28 | `4ed902dd9ebf230dcb983392705ab0d95bb0c846` | `287367ce8eb708efce0ebae0a2f9c90d681cce01` | `bdf43a891ca14941ba2f2c4f115e4a15bec0015a` | `4ed902dd9ebf230dcb983392705ab0d95bb0c846` |

Live GitHub comparison from FAZ 6 start `0e370940...` to final locked `287367ce...` contains only `sitescore-commerce/**` and `automation/n8n/**`. Frozen FAZ 3/4/5 runtime/source trees were not mutated by FAZ 6.

Frozen runtime candidate:

- `sitescore-commerce == 0.6.0`
- migration head `0005_recovery_reconciliation`
- migration chain `0001_commerce_order_checkout -> 0002_webhook_payment_authority -> 0003_fulfillment_refund -> 0004_delivery_email -> 0005_recovery_reconciliation`
- Python target 3.11
- PostgreSQL target 16
- Stripe SDK `15.4.0`
- Stripe API `2026-07-29.dahlia`
- `httpx==0.28.1`
- n8n `2.33.4`
- n8n image `n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162`
- locked order workflow SHA-256 `02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1`
- recovery schedule workflow SHA-256 `f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c`
- frozen FAZ 3/4/5 baseline `1504 PASS`

## 2. Integrated authority chain

The composed authority chain is:

1. **Order/catalog/Checkout operation truth:** Commerce + PostgreSQL. The caller supplies purchase intent only; product, Price, quantity, redirects, provider idempotency identity, and immutable Checkout operation snapshot are server-owned.
2. **Payment truth:** Verified Stripe evidence plus Commerce durable transition. Browser redirects, Checkout URL existence, client fields, n8n execution, and hashes do not establish payment truth.
3. **Analysis/report truth:** Frozen SiteScore `/v1` HTTP service. Commerce does not score, normalize, benchmark, calculate financials/confidence, decide, or render report truth.
4. **Orchestration:** n8n is a consumer/coordinator only. It branches on Commerce projections and cannot author payment, analysis, report, refund, delivery, or fulfillment truth.
5. **Refund truth:** Fresh canonical unfulfillable SiteScore evidence plus Stripe PaymentIntent/refund-history evidence under the locked full-refund contract.
6. **Delivery capability truth:** Commerce/PostgreSQL digest-bound grant tied to the exact order/report.
7. **Email provider acceptance:** Validated Postmark response evidence. Acceptance/submission is not human receipt/read proof.
8. **Recovery truth:** Fresh provider evidence + existing durable identities + exact-lease-fenced Commerce writes. Recovery does not create a second authority path.

No storage URL, email-open assumption, Host header, request ID, n8n field, raw hash, or client field becomes business authority.

## 3. Frozen Commerce HTTP surface

The audited Commerce surface is exactly:

```text
POST /v1/orders
POST /v1/webhooks/stripe
POST /v1/automation/orders/{order_id}/advance
POST /v1/automation/orders/{order_id}/deliver
GET  /v1/automation/orders/{order_id}
POST /v1/automation/recovery/run
GET  /d/{opaque_token}
```

Automation endpoints require the existing automation Bearer authority. `advance`, `deliver`, and `recovery/run` POST bodies are empty/server-owned; callers cannot submit target state, order lists, timestamps, provider results, retry counters, analysis/report IDs, refund facts, or delivery facts. Public download accepts only the opaque capability token and does not accept caller-selected report/storage/provider authority.

Commerce consumes frozen SiteScore only through authenticated `/v1` HTTP contracts. No frozen SiteScore private DB write/import authority is introduced.

## 4. Order / Checkout / idempotency audit

- Product is server-owned `location_report_v1`; configured Stripe Price and quantity `1` are not caller-selectable.
- A complete immutable Checkout operation snapshot is committed before provider I/O.
- Provider idempotency key is stable for the durable order and survives provider success/local bind loss, process restart, and deployment config drift.
- Caller idempotency is bound by a digest plus canonical normalized request hash and PostgreSQL uniqueness.
- Checkout is `mode=payment`; browser success/cancel redirects are presentation correlation only.
- Caller amount, currency, Price, Stripe object identity, discount/provider state, or payment truth cannot be injected through the order request.

## 5. Stripe payment authority audit

- Webhook body is bounded before processing; the official Stripe signature verification boundary is used.
- Real Stripe Event ID is semantic event identity. `raw_body_sha256` is first-delivery byte evidence only and is not semantic identity.
- Same Event ID/same signed semantics is duplicate-safe even if JSON bytes differ; true Event identity conflicts fail closed.
- Reconciliation freshly retrieves the exact Checkout Session and line items.
- API version, livemode, session ID, client reference, metadata/catalog, Price, quantity `1`, and USD binding are checked.
- Paid authority requires `status=complete`, `payment_status=paid`, and a valid bound PaymentIntent.
- There is no `no_payment_required` payment-authority shortcut.
- Webhook-first provider success/local bind loss can safely bind the exact Session and converge.
- Paid transition and exactly one `order.paid.v1` durable outbox identity are atomic/idempotent.
- Server polling is a distinct recovery source with immutable poll receipt; it never fabricates a Stripe Event, `evt_*` identity, signature, or webhook inbox row.
- Paid-after-expired and expired-after-paid contradictions fail closed/attention rather than rewriting terminal truth.

## 6. Fulfillment / frozen SiteScore boundary audit

- Analysis operation key, request snapshot, hash, target, and retry identity are stable and durable.
- Commerce calls SiteScore through authenticated network `/v1`; it does not write SiteScore tables or import scoring/report runtime authority.
- Analysis/report IDs are server-observed and exactly bound to the Commerce order.
- Report resolution occurs only after server-observed completed analysis.
- `not_score_ready`, `analysis_failed`, `analysis_timed_out`, and `report_failed` remain distinct canonical outcomes.
- Delivery revalidates the bound ready report and authenticated report content rather than trusting an earlier orchestration assertion.

## 7. Full-refund authority audit

- Email or delivery failure does **not** itself authorize a refund.
- Refund eligibility is produced only from fresh canonical unfulfillable SiteScore proof.
- Refund amount is full captured amount only; no partial refund business path is authored by Commerce.
- Refund operation/provider idempotency identity is stable and durable.
- Stripe refund history is listed/reconciled before create.
- Reserved `sitescore_*` refund metadata must exactly bind to the durable SiteScore refund identity.
- Partial, mixed, multiple, malformed, or conflicting refund histories fail closed.
- A truly unattributed exact full succeeded external refund is accepted only under the locked external-full recovery rule.
- A terminal refunded order cannot later fabricate fulfillment.

## 8. n8n orchestration audit

- n8n `2.33.4` is pinned; workflow bytes are locked by the hashes recorded above.
- Order workflow uses native Webhook/IF/Respond/HTTP Request/Wait/NoOp/StopAndError nodes; no Code/Function business-authority node exists.
- n8n does not receive Stripe secret/webhook secret, Postmark token, SiteScore service credential, DB/Redis/S3 master credentials, recipient email, raw delivery token, or report bytes.
- n8n starts with authoritative Commerce state and mutates only through bodyless Commerce `advance`/`deliver` boundaries.
- Continuing advance/refund/wait/delivery cycles are paced through finite horizon + Wait; horizon exhaustion fails the workflow execution without mutating Commerce truth.
- Restart and duplicate trigger executions converge from durable Commerce state.
- Delivery is performed through Commerce `/deliver`, never direct Postmark.
- Recovery scheduler contains only a 5-minute Schedule Trigger and bodyless authenticated `POST /v1/automation/recovery/run`.

## 9. Delivery / email audit

- `TOKEN_BYTES = 32`; CSPRNG token generation therefore provides 256 bits of entropy.
- Raw token is not persisted; Commerce persists SHA-256 digest only.
- Grant is exactly bound to order/report and has seven-day UTC expiry by default.
- Grant is reusable until expiry unless revoked; it is not burned by a scanner/download attempt.
- `/d/{opaque_token}` rechecks paid/not-refunded durable state, current exact report binding, ready report authority, and content integrity.
- Private S3/MinIO URL/key/credential is never returned or redirected to the caller.
- Public delivery URL authority comes from server-owned configured HTTPS base, not `Host` header.
- Download response remains private/no-store with no-referrer and nosniff protections and non-oracular unavailable behavior.
- Postmark network send occurs outside the DB transaction.
- `provider_accepted` requires the complete locked acceptance evidence, including durable MessageID/submission evidence.
- HTTP 200 with incomplete/unverifiable acceptance evidence is `provider_uncertain`, not accepted.
- Explicit nonzero provider error is rejection.
- Uncertain retry may create a fresh grant/attempt without silently treating the prior uncertain send as acceptance.
- Fulfilled requires paid + completed analysis + ready report + valid grant + durable accepted Postmark evidence.
- Delivery failure leaves payment paid and moves to the locked delivery-failed/attention shape rather than inventing refund authority.

## 10. Recovery / reconciliation audit

- Scanner is bounded and deterministic/oldest-first.
- Work is claimed with durable lease token/expiry and `FOR UPDATE SKIP LOCKED` semantics.
- Claim is committed before external provider/n8n I/O; DB row locks are not held across network calls.
- Post-I/O writes re-lock exact durable state and are fenced by current lease identity; an expired/reclaimed stale worker cannot overwrite the newer worker result.
- Legacy pre-0005 real Stripe inbox rows remain recoverable after populated 0004 -> 0005 upgrade without synthetic Event identity.
- New-lineage missing/mismatching candidate identity fails closed.
- Paid outbox recovery validates durable paid/Stripe authority before n8n I/O.
- Unpublished publish and published replay reuse the exact original outbox UUID, event type, order ID, and occurred-at identity.
- Published replay does not clear or rewrite historical `published_at` as a new logical event.
- n8n transport 2xx confirms accepted transport only; timeout/connection/429/5xx is retryable/uncertain, while auth/contract rejection becomes bounded attention.
- Recovery restarts existing orchestration to re-enter locked analysis/report/refund/delivery state machines; it does not duplicate them.
- Missing/duplicate paid outbox, contradictory payment bindings, reserved refund metadata conflicts, and other impossible shapes become sanitized durable findings/attention rather than silent repair.

## 11. Security / privacy / secret boundary audit

The freeze gate audits source/workflows/configuration for leakage or authority drift involving:

- Stripe secret and webhook secret;
- Postmark token;
- SiteScore service credential;
- DB/Redis/S3 master credentials;
- raw delivery token persistence/logging;
- recipient/customer email crossing into n8n;
- forbidden raw provider response persistence;
- private storage URL exposure;
- Host-header-derived delivery URL authority;
- caller-controlled amount/Price/currency/provider state;
- unsanitized public provider/storage/database errors.

Customer email is intentionally durable Commerce data needed for Checkout and transactional delivery. It is not exported to n8n workflow state or public error/download authority.

## 12. State / money invariant matrix

| Class | Order state | Payment state | Fulfillment state | Money / authority invariant | Recovery behavior |
|---|---|---|---|---|---|
| pending payment | `pending_payment` | `pending` | `not_started` | no paid authority | stale exact Checkout may be server-polled |
| expired/unpaid | `expired` | `expired` | `not_started` | no capture/refund fabrication | terminal; no provider business I/O |
| paid + analysis pending/running | `fulfillment_in_progress` or locked paid predecessor | `paid` | `analysis_pending` / `analysis_running` | capture authoritative; no fulfillment yet | same paid outbox replay resumes orchestration |
| paid + report pending | `fulfillment_in_progress` | `paid` | `report_pending` | no report-ready fabrication | same identity replay resumes Commerce authority |
| paid + delivery pending | `fulfillment_in_progress` | `paid` | `delivery_pending` | paid remains paid; delivery not yet accepted | replay re-enters `/deliver` path |
| paid + provider_uncertain delivery | `fulfillment_in_progress` | `paid` | `delivery_pending` | uncertain email is not fulfillment proof | bounded retry/reconciliation |
| paid + delivery_failed/attention | `attention_required` | `paid` | `delivery_failed` | delivery failure is not refund authority | operator attention; no hot loop |
| fulfilled | `fulfilled` | `paid` | `completed` | accepted delivery evidence exists; no refund fabrication | terminal/no recovery business I/O |
| refund pending | `fulfillment_in_progress` | `refund_pending` | canonical unfulfillable state | full refund operation already server-authorized | replay re-enters locked refund reconciliation |
| refunded | `refunded` | `refunded` | canonical unfulfillable state | exact full refund evidence | terminal/no fulfillment fabrication |
| corrupt/impossible | `attention_required` or unchanged safe state | unchanged authoritative payment truth | unchanged/safe failure state | no synthetic authority | sanitized durable finding/attention |

The composition permits at-least-once execution and duplicate safe reads/replays. It does **not** claim exactly-once delivery or exactly-once execution. Business effects converge through durable uniqueness/idempotency and authority revalidation.

## 13. Freeze-candidate conclusion

On the audited locked baseline, FAZ 6.0–6.5 form one coherent Commerce authority chain without frozen SiteScore source mutation or a second authority path. The 6-FINAL candidate intentionally changes only this audit artifact and executable freeze-gate tests. Any newly discovered production/runtime defect must reopen the exact locked checkpoint through Reviewer authority rather than being silently changed here.
