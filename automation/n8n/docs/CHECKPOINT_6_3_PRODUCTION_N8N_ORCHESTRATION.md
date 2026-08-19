# FAZ 6.3 — Production n8n Orchestration Workflow

## Scope

FAZ 6.3 owns only the production n8n orchestration workflow and the narrow `order.paid.v1` outbox-to-n8n dispatch boundary. n8n is an orchestrator, never payment, analysis, report, refund, delivery, scoring, or financial authority. Frozen FAZ 3/4/5 sources are unchanged. FAZ 6.4 delivery/Postmark/token work and FAZ 6.5 broad recovery scanning are not implemented.

## Runtime identity

- n8n version: `2.33.4`
- container tag: `n8nio/n8n:2.33.4`
- validated image digest: `PENDING_EXACT_HEAD_VALIDATION`
- runtime definition: `automation/n8n/runtime/docker-compose.yml`
- persistent runtime data: `/home/node/.n8n`
- external task runners: not used

The exact image digest is resolved from the pulled 2.33.4 image during exact-head CI and must be written here and to `implementer.md` before review handoff.

## Repository workflow authority

- workflow path: `automation/n8n/workflows/sitescore-order-paid-v1.json`
- human name: `SiteScore Order Paid Orchestration v1.0.0`
- SiteScore business identity: `sitescore-order-paid-v1`
- repository workflow version: `1.0.0`
- workflow SHA-256: resolved from final repository bytes during validation/handoff

The sanitized GitHub JSON is durable workflow authority. n8n internal database IDs are runtime-local import identities and are not SiteScore business identities.

## Credentials and privilege boundary

Inbound commerce dispatcher authentication uses the transport-only environment secret name `COMMERCE_N8N_INGRESS_SECRET`. Outbound n8n calls use only the existing narrow commerce automation bearer name `COMMERCE_AUTOMATION_API_KEY`. The commerce automation base URL is `SITESCORE_COMMERCE_AUTOMATION_BASE_URL`.

The two security roles are distinct. Commerce production configuration rejects reusing the automation bearer as the n8n ingress secret.

n8n does not receive or use Stripe secret/webhook keys, the frozen SiteScore service key, Postmark tokens, commerce/frozen PostgreSQL credentials, Redis/Celery business credentials, or S3/object-store credentials. Exported workflow JSON contains environment references only, never credential values.

## Minimal `order.paid.v1` transport payload

The commerce dispatcher constructs the trigger from durable `commerce.outbox_events` identity/timestamps and sends exactly:

```json
{
  "event_id": "<outbox UUID>",
  "event_type": "order.paid.v1",
  "order_id": "<order UUID>",
  "occurred_at": "<UTC server timestamp>"
}
```

The stored JSONB outbox payload is deliberately not forwarded, so future or stale payload fields cannot broaden the n8n authority surface. No customer analysis request, Stripe payload/identity, report content, provider credential, or payment data is dispatched.

## Dispatcher semantics

`sitescore-commerce==0.4.0` adds a focused one-event dispatcher command: `sitescore-commerce-dispatch-paid-outbox`.

1. read the oldest durable unpublished `order.paid.v1` identity into an immutable snapshot;
2. close the database session;
3. POST the minimal snapshot to the protected n8n webhook;
4. only after a confirmed 2xx response open a new transaction and mark that same `outbox_id` `published_at`;
5. timeout, network failure, 4xx, 429, 5xx, or uncertain response leaves the same event unpublished and retryable.

No database transaction/row lock is intentionally held across n8n HTTP I/O. Multiple dispatchers may race and send the same event more than once. This is intentional at-least-once transport; the durable unique paid outbox identity is not reminted and n8n must converge from commerce authority.

No schema revision is needed. Migration head remains `0003_fulfillment_refund`; historical migrations are unchanged.

## Workflow node inventory

Business orchestration uses only native nodes:

- Webhook
- IF
- Respond to Webhook
- HTTP Request
- Wait
- NoOp terminal boundary
- Stop And Error for safe execution failure

There are zero Code/Function nodes. No node calculates or authors payment, analysis, report, refund, or delivery truth.

## State machine

Authenticated/shape-valid `order.paid.v1` is acknowledged with 202. The first business action is always:

```text
GET /v1/automation/orders/{order_id}
```

The workflow branches only on the sanitized commerce projection (`terminal`, `next_action`, and server-owned state fields):

- `advance` -> empty `POST /v1/automation/orders/{order_id}/advance` -> GET again
- `refund` -> the same empty `/advance` trigger -> GET again; commerce re-proves refund authority
- `wait` -> finite Wait -> GET again
- `delivery` -> stop cleanly at `delivery_pending`; FAZ 6.4 owns delivery
- `none` or `terminal=true` -> stop with no business mutation

n8n never sends analysis JSON/IDs, report IDs, paid flags, refund amount/reason, Stripe IDs, or fulfillment state.

## Retry, replay, and restart

HTTP request nodes use bounded per-node retries. Polling uses `SITESCORE_N8N_POLL_SECONDS` and `SITESCORE_N8N_MAX_POLLS`; defaults are finite and no busy-loop is used. Reaching the execution polling horizon fails only the n8n execution and does not synthesize a terminal commerce state.

Duplicate identical events, distinct event IDs for the same order, response-loss replay, and n8n restart during Wait all re-enter by reading current commerce durable state. n8n execution/static data is never business dedupe authority.

## Error safety

Ingress failures return only sanitized `unauthorized` or `invalid_trigger`. Unexpected guidance or poll-horizon exhaustion uses generic Stop And Error messages stating durable commerce state is unchanged. The workflow does not persist authorization values or raw provider error bodies as business evidence and never marks paid/refunded/fulfilled from workflow success/failure.

## Validation

Exact-head CI validates:

- running n8n reports exactly `2.33.4` and resolves the image digest;
- clean persistent-volume workflow import/activation;
- webhook auth and malformed/wrong-type rejection before commerce lookup;
- authoritative GET before any advance;
- empty-body `/advance` behavior;
- duplicate same/different event convergence;
- delivery stop and all four canonical refund-guidance paths;
- refund-pending Wait behavior;
- persisted Wait restart/resume convergence;
- sanitized export/static security checks and zero Code nodes;
- commerce PostgreSQL tests and Alembic rollback/re-forward;
- frozen 1504-test baseline, private S3 regression, and Redis/Celery transport regression.

No live Stripe, Postmark, or paid external service is required for CI.

## Known boundary

A normal dispatcher invocation processes at most one currently unpublished paid event. Broad scheduling, stale-event discovery, operational recovery sweeps, and observability/alerting belong to FAZ 6.5. Customer delivery grant/token/email and `fulfilled` authority belong to FAZ 6.4.
