# FAZ 6.4 — Delivery Grant + Transactional Email

## Scope and authority

FAZ 6.4 owns customer delivery only. Payment truth remains Stripe-authoritative through commerce; analysis/report truth remains frozen SiteScore API authority. n8n remains orchestration-only and receives no delivery capability token, customer recipient, report identity/content, Postmark evidence, SiteScore service credential, database credential, or private object-store credential. FAZ 6.5 recovery scanning is not implemented.

## Delivery capability

A delivery grant is bound to one durable `order_id` and one exact bound `report_id`.

- raw capability tokens come from 32 CSPRNG bytes (256 bits) and are URL-safe;
- raw tokens exist only transiently while the email URL is assembled;
- persistence stores only `SHA-256(raw_token)`;
- default lifetime is exactly seven days from server-side issuance;
- a grant is reusable until expiration or revocation;
- revocation writes only `revoked_at`; it never mutates payment, analysis, or report truth;
- `revoke_delivery_grant` is idempotent and does not require/recover the raw token.

Capability URLs are bearer secrets. Production edge/reverse-proxy access logging MUST omit or redact the `/d/{opaque_token}` path segment. The URL must not be placed into analytics, third-party query parameters, referrers, or telemetry. Public download responses use `Cache-Control: private, no-store` and `Referrer-Policy: no-referrer`.

## Public download proxy

`GET /d/{opaque_token}` is served by commerce. It never redirects to a private S3/object-store URL.

Each request hashes the presented token, resolves an unexpired/unrevoked grant, re-checks exact order/report binding, then freshly reads frozen SiteScore report metadata and content using the server-owned service credential. Success requires all of:

- exact report ID and analysis ID match the durable fulfillment binding;
- report state is `ready`;
- report metadata MIME is `application/pdf`;
- metadata byte length is positive;
- metadata `content_sha256` is a canonical 64-hex digest;
- content response MIME is PDF;
- content `Content-SHA256` equals the metadata digest;
- content byte length equals metadata length;
- local SHA-256 equals the same digest;
- content begins with a PDF signature.

Any mismatch fails closed without exposing provider/storage details.

## Postmark acceptance authority

Commerce uses the server-owned Postmark template-send endpoint, sender, template alias, message stream, server token, and timeout. The caller and n8n cannot override them.

Before provider I/O, commerce commits the grant and durable delivery attempt. No database transaction or row lock is held across the Postmark HTTP request.

A send is accepted only when the provider response satisfies the complete acceptance contract: HTTP 200, integer `ErrorCode == 0`, non-empty valid `MessageID`, exact `To` equal to the durable customer email, and timezone-aware `SubmittedAt`. HTTP success alone is never fulfillment evidence.

Provider outcome classification is evidence-driven:

- explicit, trustworthy provider rejection evidence becomes `provider_rejected`;
- timeout, connection loss, response loss, or a success-like HTTP 200 whose body cannot safely prove either acceptance or rejection becomes `provider_uncertain`;
- HTTP 200 malformed/truncated/non-object JSON, missing or invalid `ErrorCode`, or `ErrorCode == 0` with invalid/missing/mismatched `MessageID`, `To`, or `SubmittedAt` is therefore `provider_uncertain`, never definitive rejection and never acceptance;
- integer `ErrorCode != 0` remains affirmative Postmark rejection evidence.

Neither rejected nor uncertain evidence marks the order fulfilled. While below the bounded attempt limit, an uncertain attempt keeps payment `paid`, fulfillment `delivery_pending`, and retry guidance available. A retry creates a fresh grant/attempt; a prior uncertain grant is not blindly revoked because the first provider request may actually have been accepted. Later fully validated acceptance converges to one durable `fulfilled / paid / completed` state. Known durable provider acceptance converges without another send.

## Fulfillment and failure state

`fulfilled` requires the conjunction of:

1. durable payment state `paid`;
2. exact bound analysis `completed`;
3. exact bound report `ready`;
4. a valid exact report-bound delivery grant; and
5. persisted validated Postmark provider acceptance.

Retryable delivery failure keeps payment `paid`, fulfillment `delivery_pending`, and `next_action=delivery`. Non-retryable failure or exhaustion of three attempts changes only delivery/order handling to `attention_required / paid / delivery_failed`; analysis and report bindings remain unchanged. Terminal delivery replay is a clean no-op and never re-enters provider I/O.

## n8n extension

The locked 6.3 graph is extended only at its reserved delivery boundary:

```text
commerce GET -> next_action=delivery
-> empty POST /v1/automation/orders/{order_id}/deliver
-> Within Poll Horizon?
-> Wait Before Poll
-> authoritative commerce GET
```

The `/deliver` request body is empty and uses only the existing commerce automation bearer. The same finite horizon/pacing semantics apply to delivery retries; n8n never authors `fulfilled` or provider truth.

Pinned-runtime evidence must separately exercise the delivery branch itself. A retryable delivery execution is stopped after the first bodyless `/deliver` has left commerce in authoritative `paid / delivery_pending / next_action=delivery`, while the execution is on the shared Wait cycle. n8n is restarted with the same durable volume and must resume or safely converge from commerce truth without `/advance`, without minting analytical identity, and without fabricating `fulfilled` before commerce reports acceptance. A permanently retryable delivery case must also stop at the configured finite poll horizon. Runtime evidence labels include `N8N_DELIVERY_WAIT_RESTART=PASS` and `N8N_DELIVERY_POLL_HORIZON=PASS`.

## Validation requirements

Exact-head validation must cover PostgreSQL 16 migration upgrade/downgrade/re-upgrade, digest-only schema, the full commerce suite including raw malformed HTTP-200 Postmark uncertainty/replay PostgreSQL assertions, fake Postmark wire/adversarial behavior, pinned n8n 2.33.4 import/publish/auth/delivery/retry/delivery-wait-restart/delivery-horizon behavior, secret/frozen-scope scans, private S3-compatible storage, Redis/Celery transport, and the frozen FAZ 3/4/5 1504-test baseline.
