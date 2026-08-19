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

Transport timeout/network uncertainty is recorded as `provider_uncertain`; provider rejection is `provider_rejected`. Neither marks the order fulfilled. A retry creates a fresh grant/attempt; a prior uncertain grant is not blindly revoked because the first provider request may actually have been accepted. Known durable provider acceptance converges without another send.

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

## Validation requirements

Exact-head validation must cover PostgreSQL 16 migration upgrade/downgrade/re-upgrade, digest-only schema, 313 commerce tests, fake Postmark wire/adversarial behavior, pinned n8n 2.33.4 import/publish/auth/delivery/retry/restart/horizon behavior, secret/frozen-scope scans, private S3-compatible storage, Redis/Celery transport, and the frozen FAZ 3/4/5 1504-test baseline.
