# SiteScore AI — FAZ 7 Production Runtime Contract

**Checkpoint:** FAZ 7.0 — Production Baseline + Operational Contract + Compatibility Audit  
**Authoritative base:** `main@3762ec643426e310ff82bdb00b20f58fb4ae9e09`  
**Selected platform:** DigitalOcean App Platform + Managed PostgreSQL + Managed Valkey + Spaces + VPC, GHCR, GitHub Actions, OpenTofu, Cloudflare, Better Stack, k6.  
**Status of this file:** normative deployment design authority for later FAZ 7 checkpoints; **no infrastructure is created by this document**.

> **Mathematically validated scoring engine; empirical validation pending.**

---

## 1. Non-negotiable authority model

Runtime/deployment code may move bytes, start processes, route traffic, schedule work, inject configuration, persist infrastructure state, and observe health. It may not become product/business authority.

```text
Stripe = external processor evidence
Commerce PostgreSQL = durable commercial truth
SiteScore API/PostgreSQL = analysis/report durable truth
Redis/Valkey/Celery = transport/execution, not durable business truth
n8n = orchestration only
Postmark = email transport/provider evidence
Spaces object = report artifact storage, not scoring authority
```

Analytical authority remains frozen:

```text
COMB-005 approval_state = NOT_APPROVED
approved registry = ()
weights = ()
composition = UNRESOLVED
real production analysis may correctly terminate not_score_ready
```

Production orchestration/IaC must preserve:

```text
missing != zero
missing != neutral
unavailable != bad
uncalibrated != calibrated
NOT_SCORE_READY != successful score
PIPELINE_ERROR != successful empty result
```

A successful deploy, HTTP 2xx, queue ack, workflow completion, provider response, email acceptance, or object write must never be promoted into an analytical/business fact beyond its frozen authority.

---

## 2. Environment model: two independent systems

There are exactly two first-class deployment environments for FAZ 7:

```text
staging
production
```

They are separate operational systems. Staging is not a namespace inside production and production is not a promoted staging database.

### 2.1 Separation matrix

| Resource / authority | Staging | Production | Sharing rule |
|---|---|---|---|
| App Platform app/project | dedicated staging app/project | dedicated production app/project | **do not share** |
| PostgreSQL cluster / logical DBs | dedicated staging cluster or explicitly isolated staging cluster/DB/users | dedicated production cluster/DB/users | customer/business data **do not share** |
| API database | `sitescore_api` staging DB/user | `sitescore_api` production DB/user | **do not share creds/data** |
| Commerce database | `sitescore_commerce` staging DB/user | `sitescore_commerce` production DB/user | **do not share creds/data** |
| n8n database | dedicated n8n staging DB/user | dedicated n8n production DB/user | **do not share creds/data** |
| Valkey | dedicated staging Managed Valkey | dedicated production Managed Valkey | **do not share credentials/queue state** |
| Spaces bucket | dedicated staging report bucket | dedicated production report bucket | **do not share** |
| Stripe mode | **test mode** | intended live mode only after production authorization | **strictly separate** |
| Stripe secret key | staging test key | production live key | **do not share** |
| Stripe webhook secret | staging endpoint secret | production endpoint secret | **do not share** |
| Stripe Price ID | staging test Price | production Price | **do not share when environment-specific** |
| Postmark token | staging credential | production credential | **do not share** |
| SiteScore service credentials | staging API consumer/service key | production API consumer/service key | **do not share** |
| API key pepper | staging pepper | production pepper | **do not share** |
| Commerce automation key | staging key | production key | **do not share** |
| Commerce n8n ingress secret | staging secret | production secret | **do not share** |
| n8n encryption key | staging key | production key | **do not share** |
| Spaces access/secret key | staging least-privilege credential | production least-privilege credential | **do not share** |
| provider API credentials/budgets | staging credential/quota/budget where provider supports it | production credential/quota/budget | **prefer strict isolation; never silently share money authority** |
| OpenAI credential/budget | staging credential/project/budget | production credential/project/budget | **do not share** |
| Cloudflare hostname/policies | staging hostname/policy set | production hostname/policy set | separate policy targeting |
| Better Stack source/token | staging source/token | production source/token | **do not share token/source identity** |
| customer emails | synthetic/approved test recipients only | real customer recipients | **never copy production customer mail flow into staging** |
| delivery capability tokens | staging-generated only | production-generated only | **never share/replay across environments** |

No production secret value belongs in Git, PR text, workflow exports, Terraform/OpenTofu outputs, logs, issue comments, or this contract.

---

## 3. Logical production topology

The intended topology is:

```text
                         Internet
                            |
                       Cloudflare
                     /               \
                    /                 \
      public Commerce allowlist   exact n8n order-paid ingress
                |                         |
          commerce-web               n8n-automation
          /    |     \                    |
         /     |      \                   | internal/private
Commerce PG  Stripe  Postmark              v
         \      |                        Commerce automation API
          \     |                           |
           \    +-----> SiteScore api-web <-+
                         (internal only)
                           /   |    \
                          /    |     \
                    API PG   Valkey   Spaces
                              ^         ^
                              |         |
                          api-worker ---+
                              |
                   provider/report dependencies

api-beat -> Valkey -> API task scheduling only
commerce-dispatcher -> Commerce PG -> exact n8n HTTPS ingress
n8n -> dedicated n8n PostgreSQL
```

### 3.1 Important source-grounded qualification

The current repository does **not** contain a canonical production App Platform spec, Dockerfile set, OpenTofu stack, or deployed network proof. This topology is the required target consumed by 7.1/7.2; it must not be represented as already deployed.

---

## 4. App Platform component contract

### 4.1 `commerce-web`

```text
platform role: public App Platform service
owner: sitescore-commerce==0.6.0
application factory: sitescore-commerce/src/sitescore_commerce/api.py::create_app
initial replicas: 1 unless later capacity evidence authorizes more
public ingress: Cloudflare allowlist only
internal ingress: automation routes from n8n/internal network
```

The repository has no pinned ASGI server or canonical production command today. FAZ 7.1 must create a reproducible container/bootstrap that instantiates `create_app()` and serves it on `0.0.0.0:${PORT}` without modifying frozen Commerce route/business semantics.

Health: process/socket/TCP is acceptable at this stage because no new app health route is authorized.

### 4.2 `api-web`

```text
platform role: App Platform internal service
owner: sitescore-api==0.3.0
ASGI import target: sitescore_api.app:app
public ingress: NONE
allowed caller: private Commerce/application operations as authorized
initial replicas: 1 unless later capacity evidence authorizes more
```

The current package does not pin an ASGI server. FAZ 7.1 must canonicalize a reproducible launch command/image targeting `sitescore_api.app:app`. It must not expose the API publicly merely because FastAPI has HTTP routes.

### 4.3 `api-worker`

```text
platform role: worker
command shape: celery -A sitescore_api.tasks:celery_app worker
broker: Managed Valkey rediss://
result backend: NONE
public listener: NONE
staging initial concurrency: 1
```

Worker autoscaling/concurrency beyond initial bounded operation requires 7.5 capacity/backpressure evidence.

### 4.4 `api-beat`

```text
platform role: worker/scheduler
command shape: celery -A sitescore_api.tasks:celery_app beat
public listener: NONE
replicas: EXACTLY 1
drain_outbox: every 10 seconds
reconcile_timeouts: every 15 seconds
```

Horizontal beat scaling is forbidden absent an explicitly reviewed scheduler-deduplication design.

### 4.5 `commerce-dispatcher`

```text
platform role: worker
canonical one-shot command: sitescore-commerce-dispatch-paid-outbox
public listener: NONE
DB: Commerce PostgreSQL
outbound: exact n8n order-paid HTTPS ingress
```

The source is deliberately one-shot. Deployment may wrap it with an operations-owned supervisor loop only:

```text
loop:
  execute frozen one-shot dispatcher
  if EMPTY -> short bounded sleep
  if success/published -> continue
  if transport/process failure -> bounded backoff
  if termination signal -> clean exit
```

The wrapper cannot inspect or mutate order/payment/outbox business state, mint event IDs, mark publish state, construct alternate payloads, or bypass `sitescore_commerce.dispatcher`.

### 4.6 `n8n-automation`

```text
runtime: n8n 2.33.4
frozen image digest:
  n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162
initial replicas: 1
production persistence: dedicated n8n PostgreSQL DB/user
editor/admin/rest: non-public
public path: exact order-paid webhook only
```

Current local evidence `automation/n8n/runtime/docker-compose.yml` still uses a persistent `/home/node/.n8n` volume and does not define PostgreSQL. That file proves frozen runtime configuration but is **not** the production persistence topology. 7.2 must set the supported n8n PostgreSQL configuration and secret injection.

---

## 5. PostgreSQL contract

Per environment, Managed PostgreSQL must expose isolated logical databases/users:

```text
sitescore_api
sitescore_commerce
n8n
```

Minimum isolation requirements:

- API application credentials access only the API database/schema required by API migrations/runtime.
- Commerce application credentials access only Commerce durable state.
- n8n database credentials access only n8n persistence.
- n8n never receives API or Commerce PostgreSQL application credentials.
- Commerce and API migrations are executed by explicit release/predeploy authority, not by arbitrary web/worker replicas.
- Database backup/restore/DR proof is deferred to 7.6.
- Connection budgets and replica/concurrency capacity are deferred to 7.5.

### 5.1 API migration authority

```text
config: sitescore-api/alembic.ini
head: 0003_faz5_5
single writer: required
failure: blocks release
```

### 5.2 Commerce migration authority

```text
config: sitescore-commerce/alembic.ini
version table: commerce.alembic_version
head: 0005_recovery_reconciliation
single writer: required
failure: blocks release
```

### 5.3 n8n migration authority

n8n owns its runtime schema. n8n version upgrades must serialize its own database migration/startup authority. Neither SiteScore API Alembic nor Commerce Alembic may touch n8n persistence.

---

## 6. Managed Valkey contract

Per environment:

```text
private/VPC reachable
SSL/TLS required
auth/trusted-source restrictions enabled
production broker URL = rediss://...
```

The locked FAZ 7 entry corrective makes API Settings accept `rediss://` and passes it unchanged to Celery.

Production must **not** fall back to `redis://` merely because that scheme remains supported for local/test compatibility.

Valkey contents are transport/execution state. Loss/unavailability can interrupt/retry execution but cannot become a durable analysis, report, payment, order, or fulfillment truth source.

---

## 7. Spaces contract

Per environment:

```text
separate staging/prod buckets
private objects
public ACL = off
bucket listing/public access = off
report CDN = off
versioning target = on
least-privilege API credentials
no direct customer object URL
```

Current API object adapter is `S3CompatibleObjectStorage` in `sitescore-api/src/sitescore_api/report_artifacts.py` and constructs `boto3.client("s3", ...)` with server-owned bucket/region/endpoint.

Customer report delivery remains through frozen authority:

```text
Commerce opaque delivery grant
-> Commerce validates grant/payment/report binding
-> Commerce calls internal SiteScore report metadata/content routes
-> SiteScore verifies stored object integrity
-> Commerce proxies PDF bytes to customer
```

Cloudflare/Spaces configuration must not bypass this with direct public object links.

---

## 8. Public/private route matrix

### 8.1 Public allowlist candidates

Only these product paths may ultimately traverse public Cloudflare ingress:

```text
Commerce:
  POST /v1/orders
  POST /v1/webhooks/stripe
  GET  /d/{opaque_token}

n8n:
  exact order-paid webhook path for workflow sitescore-order-paid-v1
```

Current exact n8n webhook node path from repository workflow JSON:

```text
sitescore-order-paid-v1
```

The final external URL form is deployment-owned by `N8N_WEBHOOK_URL`/n8n route semantics, but the public rule must resolve to this exact locked webhook and nothing broader.

### 8.2 Internal-only Commerce routes

```text
POST /v1/automation/orders/{order_id}/advance
POST /v1/automation/orders/{order_id}/deliver
GET  /v1/automation/orders/{order_id}
POST /v1/automation/recovery/run
```

They are authenticated by Commerce automation authority and must not be reachable from arbitrary public clients.

### 8.3 Internal-only SiteScore API routes

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

All remain service-key authenticated and internal. Cloudflare must not turn them into a public product API in FAZ 7.

### 8.4 n8n administrative isolation

Non-public:

```text
editor UI
admin/setup UI
general REST/API
arbitrary workflow webhook paths
recovery schedule trigger
internal runtime/admin endpoints
```

Commerce production settings require the n8n order-paid ingress URL to be HTTPS.

If App Platform routing cannot prove exact safe path isolation for the n8n service, the only allowed later alternative is a **minimal operations-owned relay** that:

- accepts only the exact locked webhook path;
- enforces transport authentication, body size and traffic/rate controls;
- forwards to private n8n;
- does not parse/author payment, order, analysis, report, refund, delivery, readiness, scoring, or financial truth;
- contains no alternate outbox/event identity logic.

Do **not** solve n8n ingress by exposing the entire n8n service.

---

## 9. Cloudflare boundary

Cloudflare is an edge/security layer, not business authority.

Later 7.2/7.4 must implement and prove:

- environment-specific hostnames;
- TLS to public origin paths as applicable;
- exact public path/method allowlist;
- denial of internal Commerce automation routes;
- denial of SiteScore API public ingress;
- denial of n8n editor/admin/general REST;
- body/rate/abuse controls that do not reinterpret application state;
- Stripe webhook path treatment compatible with frozen signature verification;
- opaque delivery-token path without logging/token leakage beyond required operational metadata.

No Cloudflare configuration exists as canonical repo authority at 7.0 entry.

---

## 10. External-provider runtime boundary

### 10.1 Commerce providers

```text
Stripe:
  Commerce-only caller
  external payment/refund evidence
  SDK 15.4.0
  frozen API 2026-07-29.dahlia

Postmark:
  Commerce delivery-only caller
  provider evidence
  HTTP endpoint https://api.postmarkapp.com/email/withTemplate
  strict acceptance evidence required; HTTP 200 alone insufficient

SiteScore API:
  internal Commerce dependency for analysis/report truth
```

n8n never receives Stripe secret/webhook secrets, SiteScore service key, Postmark token, DB credentials, Valkey credentials, Spaces credentials, raw delivery tokens, or report bytes as orchestration authority.

### 10.2 Analytical/provider acquisition path

Current canonical acquisition source at the 7.0 base wires contracts for:

```text
Census Geocoder
Census ACS
Overture Places artifacts
Valhalla pedestrian/routing
GTFS transit
```

The production deployment factory is selected through:

```text
SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY=module:callable
```

It must return exact `CanonicalAcquisitionDeployment` and owns concrete artifact/provider bindings.

The provider-neutral HTTP boundary defaults to a 15-second request timeout and explicitly implements no generic retry/auth/cache semantics. Provider clients classify HTTP/network failure according to frozen provider logic. Infrastructure must not replace unavailable evidence with zero/bad/neutral values.

Earlier planning references to Google Places, OSM/Nominatim, or Mapbox are **not observed as active current canonical runtime wiring in `sitescore-api/src/sitescore_api/acquisition.py` at this base**. They must not be deployed or budgeted as active dependencies without a later source-authorized deployment binding.

### 10.3 OpenAI narrative boundary

`sitescore-report` uses OpenAI only as an untrusted structured claim-selection provider. It may choose emphasis/order among approved claims; it cannot create facts, scores, decisions, confidence, readiness, benchmarks, empirical conclusions, or free-form authoritative prose.

Runtime model selection:

```text
SITESCORE_NARRATIVE_MODEL_ID
```

Provider credential/budget must be environment-isolated. The SiteScore source constructs the OpenAI SDK client with SDK defaults and does not directly define the credential env name; 7.2 must inject a supported SDK credential without committing it.

---

## 11. n8n workflow contract

Frozen final identities:

```text
runtime:
  n8n 2.33.4
image:
  n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162

order workflow:
  automation/n8n/workflows/sitescore-order-paid-v1.json
  business identity = sitescore-order-paid-v1
  repository meta version = 1.1.0
  SHA256 = 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
  webhook node path = sitescore-order-paid-v1

recovery workflow:
  automation/n8n/workflows/sitescore-recovery-schedule-v1.json
  business identity = sitescore-recovery-schedule-v1
  version = 1.0.0
  SHA256 = f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
  schedule = every 5 minutes
```

Order workflow outbound HTTP nodes use Commerce automation Bearer auth, 10-second node timeouts, up to three tries, and two-second wait between tries where configured. Long-running state polling is additionally paced by `SITESCORE_N8N_POLL_SECONDS` (default 15) and capped by `SITESCORE_N8N_MAX_POLLS` (default 60).

n8n workflow completion/failure does not modify the meaning of durable Commerce truth. Replay must re-enter via current Commerce state.

---

## 12. Secrets contract

Secret classes that must be injected from environment/platform secret facilities and never committed:

```text
API PostgreSQL credentials
Commerce PostgreSQL credentials
n8n PostgreSQL credentials
Valkey credentials
Stripe secret key
Stripe webhook secret
Postmark server token
SiteScore service/API key material
API key pepper
Commerce automation API key
Commerce n8n ingress secret
n8n encryption key
Spaces access/secret keys
OpenAI provider credential
provider API credentials (including ACS credential where used)
Better Stack source/token
Cloudflare API/deployment credentials used by automation
GitHub deployment credentials/tokens if any
```

Rotation must preserve identity/authority boundaries. In particular:

- n8n ingress secret and Commerce automation key are distinct roles and must remain distinct.
- n8n encryption-key rotation requires n8n-aware credential migration, not blind replacement.
- API key pepper rotation can affect authentication of stored service-key hashes and therefore requires deliberate rollover.
- Stripe webhook-secret rotation must be coordinated with endpoint/provider configuration.
- DB/Valkey/Spaces rotations require connection restart/rollover planning but cannot create alternate data truth.

---

## 13. Health/readiness model

No application-source health endpoint is added by this checkpoint.

Normative distinction:

```text
process live != dependencies healthy != business/scoring ready
```

### Liveness

For `commerce-web` and `api-web`, App Platform process/socket/TCP health is acceptable if no frozen route is appropriate for probing.

For workers/schedulers, process survival + platform worker state is the liveness signal.

### Dependency health

Observed separately for at least:

```text
API PostgreSQL
Commerce PostgreSQL
n8n PostgreSQL
Valkey TLS connectivity
Spaces access
Stripe provider reachability/error rate
Postmark provider reachability/error/uncertainty rate
internal Commerce <-> SiteScore API
Commerce dispatcher -> n8n
provider acquisition failures/rate limits
OpenAI provider failures/fallback usage
```

### Readiness

Infrastructure readiness must never be named or interpreted as SiteScore scoring readiness. A `not_score_ready` canonical analysis may occur in a perfectly healthy production deployment.

Detailed metrics/SLO/alerts belong to 7.3.

---

## 14. Release and migration boundary

Future production release must satisfy:

```text
source = user-LOCKed main SHA only
application/runtime images = immutable digests
production GitHub Environment = explicit approval gate
production deploy_on_push = forbidden
API migration = explicit serialized predeploy job
Commerce migration = explicit serialized predeploy job
migration failure = release blocked
n8n version/schema upgrade = serialized runtime upgrade authority
release record = source SHA + image digests + migration heads + deploy result
```

Deployment metadata is not business evidence. Rollback/roll-forward procedures cannot rewrite durable payment/fulfillment truth.

Release safety/canary/rollback capacity mechanics belong to 7.5; backup restore/DR belongs to 7.6.

---

## 15. Current compatibility verdict

### Secure broker gate

```text
Managed Valkey production TLS requirement: compatible
production target: rediss://
Settings accepts rediss://: YES
Celery receives URL unchanged: YES
TLS downgrade/rewrite: NONE
```

Source anchors: `sitescore-api/src/sitescore_api/settings.py`, `celery_app.py`, `tests/test_broker_tls_compatibility.py`.

### PostgreSQL compatibility

API and Commerce both use SQLAlchemy/psycopg PostgreSQL URLs and Alembic migrations. Current Commerce frozen runtime identity was validated with PostgreSQL 16. Production topology must keep API/Commerce/n8n databases isolated.

### Spaces/S3 compatibility

API uses a boto3 S3-compatible adapter with configurable bucket, region, and endpoint URL. Production Spaces use must remain private and least-privilege; exact endpoint/credentials are 7.2 configuration.

### App Platform compatibility

Application components can be represented as web/worker/scheduler roles, but **canonical production container images and exact web bootstrap commands are not yet present**. That is a 7.1 entry requirement, not evidence of a deployed service.

### n8n compatibility

Frozen runtime is containerized at n8n 2.33.4 with known image digest/workflows, but the existing local compose does not yet prove production PostgreSQL persistence or exact public-path isolation. Those are 7.2 staging topology proofs.

---

## 16. Known production gaps and ownership

At this base, independent repository/state review establishes:

| Gap | Current state | Owner checkpoint |
|---|---|---|
| canonical production Docker assets | not observed | 7.1 |
| immutable SiteScore API/Commerce image digest build | not implemented | 7.1 |
| SBOM/provenance/supply-chain governance | not implemented | 7.1 |
| protected `main` + required status checks | current branch protection false/enforcement off | 7.1 |
| OpenTofu production stack | not observed | 7.2 |
| App Platform staging/prod specs | not observed | 7.2 |
| VPC/private networking proof | not deployed/proved | 7.2 |
| environment secret injection | not deployed/proved | 7.2 |
| n8n PostgreSQL production persistence | target defined, not deployed | 7.2 |
| exact n8n external path isolation | target defined, not proved | 7.2 |
| Cloudflare production rules | not observed | 7.2/7.4 |
| Better Stack logging/monitoring | not observed | 7.3 |
| SLOs/alerts | not implemented | 7.3 |
| WAF/rate/body/abuse controls | not implemented | 7.4 |
| provider/OpenAI budget controls | not implemented | 7.4 |
| backpressure/capacity/load-driven concurrency | not proved | 7.5 |
| release safety/canary/rollback evidence | not proved | 7.5 |
| backup/restore/data protection | not proved | 7.6 |
| disaster recovery drill | not proved | 7.6 |
| staging E2E with real topology | not performed | 7.7 |
| k6 load/failure drills | not performed | 7.7 |
| production launch authorization | **NO** | 7-FINAL/user governance only after evidence |

No gap above may be closed by weakening frozen application validation, exposing an internal authority surface, using plaintext production Redis, sharing secrets/data between environments, or fabricating business readiness.

---

## 17. Source-to-runtime traceability

Minimum authoritative repository anchors for this contract:

```text
sitescore-api/pyproject.toml
sitescore-api/src/sitescore_api/settings.py
sitescore-api/src/sitescore_api/app.py
sitescore-api/src/sitescore_api/routes.py
sitescore-api/src/sitescore_api/runtime.py
sitescore-api/src/sitescore_api/celery_app.py
sitescore-api/src/sitescore_api/tasks.py
sitescore-api/src/sitescore_api/report_artifacts.py
sitescore-api/src/sitescore_api/acquisition.py
sitescore-api/alembic.ini
sitescore-api/alembic/versions/0003_faz5_5_canonical_success_boundary.py

sitescore-commerce/pyproject.toml
sitescore-commerce/src/sitescore_commerce/settings.py
sitescore-commerce/src/sitescore_commerce/api.py
sitescore-commerce/src/sitescore_commerce/dispatcher.py
sitescore-commerce/src/sitescore_commerce/checkout.py
sitescore-commerce/src/sitescore_commerce/delivery.py
sitescore-commerce/src/sitescore_commerce/delivery_runtime.py
sitescore-commerce/alembic.ini
sitescore-commerce/alembic/versions/0005_recovery_reconciliation.py
sitescore-commerce/tests/test_runtime_http_surface.py
sitescore-commerce/docs/FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md

automation/n8n/runtime/docker-compose.yml
automation/n8n/workflows/sitescore-order-paid-v1.json
automation/n8n/workflows/sitescore-recovery-schedule-v1.json

sitescore-providers/src/sitescore_providers/http.py
sitescore-providers/src/sitescore_providers/census/client.py
sitescore-providers/src/sitescore_providers/acs/client.py
sitescore-report/src/sitescore_report/narrative.py
```

---

## 18. FAZ 7.0 conclusion

This contract makes production architecture explicit without pretending later checkpoint work exists.

The selected target is compatible with the frozen code **provided** later checkpoints implement immutable containers, secure/private topology, separate environment state/secrets, exact ingress isolation, serialized migrations, observability, traffic/cost controls, capacity/backpressure, backup/DR, and staging readiness evidence exactly within their authority.

FAZ 7.0 itself authorizes none of those mutations. It freezes the operational contract they must satisfy.