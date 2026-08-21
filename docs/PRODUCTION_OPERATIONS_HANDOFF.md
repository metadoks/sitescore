# SiteScore AI — Production Operations Handoff

**Phase:** FAZ 7.0 — Production Baseline + Operational Contract + Compatibility Audit
**Authoritative base:** `main@3762ec643426e310ff82bdb00b20f58fb4ae9e09`
**Base tree:** `3cc9fe7c0f8da20a4c2763661a4df304c96c94ce`
**Purpose:** source-grounded production runtime inventory for FAZ 7.1–7.7.
**Nature of this checkpoint:** documentation/inventory only; this document does not create deployment, infrastructure, container, migration, scoring, payment, report, or orchestration authority.

> Product validity claim remains: **Mathematically validated scoring engine; empirical validation pending.**

---

## 1. Frozen authority boundaries

These boundaries are operational invariants, not deployment suggestions.

| System | Authority |
|---|---|
| Stripe | external processor evidence; verified/reconciled evidence can support payment/refund authority through frozen Commerce logic |
| Commerce PostgreSQL | durable commercial/order/payment/fulfillment/delivery/recovery truth |
| SiteScore API + API PostgreSQL | durable analysis/report lifecycle and report metadata truth |
| Redis/Valkey + Celery | execution/transport only; never durable business truth |
| n8n | orchestration only; never payment, scoring, readiness, report, refund, delivery, or financial truth |
| Postmark | email transport/provider evidence only |
| Spaces/S3-compatible object | private report artifact byte storage; not scoring/report semantic authority |
| Provider responses/artifacts | external evidence under frozen provider contracts; not caller-authored business truth |

Analytical composition remains unresolved:

```text
COMB-005 approval_state = NOT_APPROVED
approved registry = ()
weights = ()
composition = UNRESOLVED
real production analysis may correctly terminate not_score_ready
```

No operations layer may calculate or fabricate location score, category score, BEC, confidence, decision, readiness, percentile, benchmark, payment state, or report truth.

---

## 2. Exact production-relevant package inventory

Versions below are derived from repository package metadata at the authoritative base, not chat history.

| Package/runtime | Version | Authoritative source |
|---|---:|---|
| `sitescore-core` | `0.1.0` | `sitescore-core/pyproject.toml` `[project].version` |
| `sitescore-data` | `0.1.0` | `sitescore-data/pyproject.toml` |
| `sitescore-providers` | `0.1.0` | `sitescore-providers/pyproject.toml` |
| `sitescore-spatial` | `0.1.0` | `sitescore-spatial/pyproject.toml` |
| `sitescore-metrics` | `0.1.0` | `sitescore-metrics/pyproject.toml` |
| `sitescore-benchmarks` | `0.1.0` | `sitescore-benchmarks/pyproject.toml` |
| `sitescore-pipeline` | `0.1.0` | `sitescore-pipeline/pyproject.toml` |
| `sitescore-app` | `0.1.0` | `sitescore-app/pyproject.toml` |
| `sitescore-report` | `0.3.0` | `sitescore-report/pyproject.toml` |
| `sitescore-api` | `0.3.0` | `sitescore-api/pyproject.toml` |
| `sitescore-commerce` | `0.6.0` | `sitescore-commerce/pyproject.toml` and `sitescore-commerce/src/sitescore_commerce/__init__.py` |
| n8n | `2.33.4` | `automation/n8n/runtime/docker-compose.yml` and final FAZ 6 audit |

Production-relevant pinned dependencies visible in package metadata include:

```text
sitescore-api:
  fastapi 0.140.0
  pydantic 2.13.4
  SQLAlchemy 2.0.51
  alembic 1.18.5
  psycopg 3.3.4
  celery 5.6.3
  redis 7.4.1
  boto3 1.43.55

sitescore-commerce:
  fastapi 0.140.0
  pydantic 2.13.4
  SQLAlchemy 2.0.51
  alembic 1.18.5
  psycopg 3.3.4
  stripe 15.4.0
  httpx 0.28.1

sitescore-report:
  openai 3.2.0
  Jinja2 3.1.6
  matplotlib 3.11.1
  weasyprint 69.0

sitescore-spatial:
  shapely 2.1.2
  pyproj 3.7.2
```

---

## 3. Runtime process inventory

### 3.1 `commerce-web`

| Property | Contract |
|---|---|
| Owner | `sitescore-commerce==0.6.0` |
| Source entry authority | `sitescore-commerce/src/sitescore_commerce/api.py::create_app()` |
| FastAPI runtime | `create_app()` returns the complete frozen seven-route application |
| Canonical production ASGI command | **Not yet present in repository at FAZ 7.0.** No ASGI server is pinned by `sitescore-commerce/pyproject.toml`. FAZ 7.1 must canonicalize the image/bootstrap without changing Commerce semantics. |
| Required future command shape | Instantiate `sitescore_commerce.api:create_app` and serve the returned ASGI app on the App Platform exposed port bound to `0.0.0.0`; the exact server binary/version is a 7.1 supply-chain decision, not invented here. |
| Listener | HTTP listener once containerized |
| Classification | public service with strict edge route allowlist; automation routes remain internal-only |
| Durable state | Commerce PostgreSQL only |
| External dependencies | Stripe, SiteScore internal API, Postmark; download path proxies SiteScore report bytes |
| Scale constraints | web replicas may later scale only after DB/provider budgets and idempotency constraints are proved; capacity proof belongs to 7.5 |
| Shutdown | future ASGI process must drain/terminate normally; no special in-source shutdown hook is canonicalized at 7.0 |

Authoritative route source: `sitescore-commerce/src/sitescore_commerce/api.py`; exact route-set freeze check: `sitescore-commerce/tests/test_runtime_http_surface.py`.

### 3.2 `api-web`

| Property | Contract |
|---|---|
| Owner | `sitescore-api==0.3.0` |
| Import target | `sitescore_api.app:app` (`app = create_app(load_environment=True)`) |
| Canonical production ASGI command | **Not yet present in repository at FAZ 7.0.** `sitescore-api/pyproject.toml` does not pin an ASGI server. |
| Required future command shape | Serve `sitescore_api.app:app` on `0.0.0.0:${PORT}` with a pinned server/image defined in 7.1; API remains internal-only. |
| Listener | HTTP listener once containerized |
| Classification | internal service; no public ingress |
| Durable state | API PostgreSQL; private report objects in Spaces/S3-compatible storage |
| Execution transport | Celery/Managed Valkey |
| External dependencies | provider acquisition deployment, object storage, optional OpenAI narrative provider during report generation |
| Scale constraints | web scale later bounded by DB/provider limits; no business authority may move to load balancer/edge |
| Shutdown | future ASGI runtime must terminate cleanly; no application-specific shutdown primitive is currently canonicalized |

Source anchors: `sitescore-api/src/sitescore_api/app.py`, `routes.py`, `runtime.py`.

### 3.3 `api-worker`

| Property | Contract |
|---|---|
| Owner | `sitescore-api==0.3.0`, Celery `5.6.3` |
| Celery app | `sitescore_api.tasks:celery_app` |
| Command shape | `celery -A sitescore_api.tasks:celery_app worker` with deployment-owned concurrency options |
| Listener | no public HTTP listener |
| Classification | worker/internal |
| Durable state | API PostgreSQL + private report object storage |
| Broker | Managed Valkey using production `rediss://...` |
| Tasks | `sitescore_api.execute_analysis`, `sitescore_api.drain_outbox`, `sitescore_api.reconcile_timeouts` |
| Scaling | horizontally bounded; **staging initial concurrency = 1**. Broader capacity/concurrency proof belongs to 7.5. |
| Shutdown | Celery worker signal handling must be allowed to perform normal clean termination; platform must not replace task/business semantics |

### 3.4 `api-beat`

| Property | Contract |
|---|---|
| Owner | `sitescore-api==0.3.0`, Celery `5.6.3` |
| Celery app | `sitescore_api.tasks:celery_app` |
| Command shape | `celery -A sitescore_api.tasks:celery_app beat` |
| Listener | none |
| Classification | scheduler/internal worker |
| Broker | Managed Valkey via `rediss://...` |
| Schedule | `sitescore-outbox-drain` every `10.0s`; `sitescore-timeout-reconcile` every `15.0s` |
| Replica constraint | **exactly one intended scheduler instance** |
| Horizontal scale | forbidden unless future scheduler-deduplication proof explicitly changes this contract |
| Shutdown | normal Celery beat signal termination; no business truth stored in scheduler |

### 3.5 `commerce-dispatcher`

| Property | Contract |
|---|---|
| Owner | `sitescore-commerce==0.6.0` |
| Exact console script | `sitescore-commerce-dispatch-paid-outbox` -> `sitescore_commerce.dispatcher:main` |
| Current execution form | **ONE-SHOT** |
| One invocation | constructs dispatcher, calls exactly one `dispatch_once()`, prints state, exits |
| Listener | none |
| Classification | worker/internal |
| Durable state | Commerce PostgreSQL |
| External dependency | exact configured n8n order-paid HTTPS ingress |
| Transport semantics | at-least-once; same durable outbox identity reused; DB transaction/row lock is not held across HTTP I/O |
| Scale | multiple invocations can duplicate transport; n8n/Commerce must converge from durable authority; deployment should initially keep one supervised worker unless later capacity proof says otherwise |

Exit behavior from source:

```text
UNPUBLISHED -> exit 1
EMPTY       -> exit 0
PUBLISHED   -> exit 0
```

**Future deployment wrapper requirement:** App Platform worker must own supervision/looping around the frozen one-shot command. The wrapper may:

- invoke the one-shot command repeatedly;
- sleep briefly after `EMPTY` before invoking again;
- use bounded backoff after transport/process failure;
- handle termination signals and exit cleanly.

The wrapper must **not**:

- calculate or rewrite payment/order state;
- mint/replace outbox event identity;
- mark events published itself;
- bypass the command's frozen database/HTTP behavior;
- create alternate n8n payloads or retry identities;
- contain scoring/report/refund/delivery business logic.

### 3.6 `n8n-automation`

| Property | Contract |
|---|---|
| Runtime | n8n `2.33.4` |
| Frozen image | `n8nio/n8n@sha256:f9a15cc65378e4e5b6c3b1445c83985131938db8d8b5b1ab891d7d50196b2162` |
| Local runtime evidence | `automation/n8n/runtime/docker-compose.yml` |
| Current compose port | `127.0.0.1:5678:5678` (local evidence only, not production topology) |
| Production persistence target | dedicated PostgreSQL database/user per environment; current repository compose still uses `/home/node/.n8n` volume and is **not** the final production persistence spec |
| Required secret | `N8N_ENCRYPTION_KEY` |
| Initial replica target | 1 |
| External surface | only exact locked order-paid production webhook path; editor/admin/REST must remain non-public |
| Internal calls | Commerce automation API only, authenticated by `COMMERCE_AUTOMATION_API_KEY` |
| Business authority | none; orchestration only |

Frozen final identities from `sitescore-commerce/docs/FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md`:

```text
order workflow file:
  automation/n8n/workflows/sitescore-order-paid-v1.json
order workflow SHA-256:
  02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
order business identity:
  sitescore-order-paid-v1
current repository workflow meta version:
  1.1.0
webhook path:
  sitescore-order-paid-v1

recovery workflow file:
  automation/n8n/workflows/sitescore-recovery-schedule-v1.json
recovery workflow SHA-256:
  f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
recovery business identity:
  sitescore-recovery-schedule-v1
schedule:
  every 5 minutes
```

The current `main` changed from the final FAZ 6 frozen main only in the two broker-TLS corrective files, so these n8n bytes/identities remain unchanged at the FAZ 7.0 base.

---

## 4. Celery runtime contract

Source: `sitescore-api/src/sitescore_api/celery_app.py` and `tasks.py`.

```text
Celery("sitescore_api", broker=settings.broker_url, backend=None)

result backend = None
task_ignore_result = true
task_store_errors_even_if_ignored = false
task_acks_late = true
task_acks_on_failure_or_timeout = true
task_reject_on_worker_lost = true
worker_prefetch_multiplier = 1
soft time limit = Settings.worker_soft_time_limit_seconds (default 840)
hard time limit = Settings.worker_hard_time_limit_seconds (default 900)
drain_outbox schedule = 10 seconds
reconcile_timeouts schedule = 15 seconds
```

`execute_analysis` retries `RetryableReportFinalization` after five seconds with no finite Celery retry count. Durable lifecycle/deadline semantics remain in API PostgreSQL and worker code; Celery retry count is not business-success authority.

Production broker requirements:

```text
scheme = rediss://
transport encryption = required
private/VPC reachability = required
broker result backend = none
Valkey is not durable business truth
```

`redis://` remains supported only for local/test compatibility; it is not an acceptable production substitution.

---

## 5. Environment-variable inventory

Every row below is row-local and explicitly carries consumer and source authority. Where a value is supplied by an SDK credential-provider chain rather than direct SiteScore `os.getenv`, that distinction is stated instead of inventing a SiteScore-bound environment name.

### 5.1 SiteScore API web / worker / beat

| Variable | Consumer | Source | Required / default | Secret? | Staging/prod sharing | Rotation / operational impact | Constraints / notes |
|---|---|---|---|---|---|---|---|
| `SITESCORE_DATABASE_URL` | API web, worker, task runtime | `sitescore-api/src/sitescore_api/settings.py` | required | **yes** | **NO** | restart/redeploy; DB sessions reconnect; coordinate credential rollover | PostgreSQL URL only; environment-specific DB/user |
| `SITESCORE_BROKER_URL` | API runtime, Celery worker, beat | `sitescore-api/src/sitescore_api/settings.py`; `celery_app.py` | required | **yes** | **NO** | worker/beat restart; in-flight execution transport may retry | production target `rediss://...`; `redis://` local/test compatibility only |
| `SITESCORE_API_KEY_PEPPER` | API authentication | `sitescore-api/src/sitescore_api/settings.py` | required | **yes** | **NO** | affects stored service-key hash verification; requires deliberate rollover | minimum 32 UTF-8 bytes |
| `SITESCORE_ANALYSIS_DEADLINE_SECONDS` | API lifecycle, worker contract | `sitescore-api/src/sitescore_api/settings.py` | default `900` | no | may share same value | redeploy changes durable timeout window | positive integer; hard worker limit must not exceed deadline |
| `SITESCORE_POLL_RETRY_AFTER_SECONDS` | API web responses | `sitescore-api/src/sitescore_api/settings.py` | default `3` | no | may share same value | redeploy changes client polling hint only | positive integer |
| `SITESCORE_WORKER_SOFT_LIMIT_SECONDS` | Celery worker | `sitescore-api/src/sitescore_api/settings.py`; `celery_app.py` | default `840` | no | may share same value | worker restart; changes soft termination timing | positive; less than hard limit |
| `SITESCORE_WORKER_HARD_LIMIT_SECONDS` | Celery worker | `sitescore-api/src/sitescore_api/settings.py`; `celery_app.py` | default `900` | no | may share same value | worker restart; changes hard termination timing | positive; greater than soft; <= analysis deadline |
| `SITESCORE_REPORT_STORAGE_BUCKET` | API report storage/generator | `sitescore-api/src/sitescore_api/settings.py`; `report_artifacts.py` | default `sitescore-reports` in source | no; resource identity | **NO** in production contract | changing bucket changes artifact location; requires migration/retention planning | separate staging/prod buckets required |
| `SITESCORE_REPORT_STORAGE_REGION` | API report storage | `sitescore-api/src/sitescore_api/settings.py`; `report_artifacts.py` | default `us-east-1` | no | may share only if both resources intentionally use same region | storage client restart/redeploy | non-empty; later Spaces config must bind intended region explicitly |
| `SITESCORE_REPORT_STORAGE_ENDPOINT_URL` | API report storage | `sitescore-api/src/sitescore_api/settings.py`; `report_artifacts.py` | optional | no | may share service endpoint only, never bucket/credential | storage client restart/redeploy | if present must be HTTP/HTTPS; production target is explicit Spaces HTTPS endpoint |
| `SITESCORE_REPORT_MAX_BYTES` | report generation/read | `sitescore-api/src/sitescore_api/settings.py`; `report_artifacts.py` | default `10485760` | no | may share same value | changes accepted artifact bound | positive integer |
| `SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY` | API worker/runtime acquisition | `sitescore-api/src/sitescore_api/runtime.py` | optional; absent => `MissingExecutionEvidenceSource` | no | may differ | worker restart; changes real acquisition deployment binding | `module:callable`; exact return type must be `CanonicalAcquisitionDeployment` |

### 5.2 Object-storage SDK credential surface

| Variable / credential surface | Consumer | Source | Required / default | Secret? | Staging/prod sharing | Rotation / operational impact | Constraints / notes |
|---|---|---|---|---|---|---|---|
| boto3 credential provider chain, commonly `AWS_ACCESS_KEY_ID` | API S3/Spaces client | `sitescore-api/src/sitescore_api/report_artifacts.py` constructs `boto3.client(...)`; credential resolution is **SDK-level, not direct SiteScore `os.getenv`** | required when selected credential mechanism needs explicit access key | **yes** | **NO** | storage client/process restart or provider-supported rollover | do not infer that SiteScore source binds this exact env name; selected boto3-supported mechanism is 7.2 authority |
| boto3 credential provider chain, commonly `AWS_SECRET_ACCESS_KEY` | API S3/Spaces client | same SDK-level credential provider chain | required with access-key credential mode | **yes** | **NO** | coordinated storage credential rollover | least privilege to environment bucket only |
| boto3 session token when selected credential type uses one | API S3/Spaces client | boto3 SDK credential provider chain | optional / credential-mode dependent | **yes** | **NO** | token refresh/rotation per selected credential mode | do not commit or persist in report metadata |

### 5.3 Narrative provider

| Variable / credential surface | Consumer | Source | Required / default | Secret? | Staging/prod sharing | Rotation / operational impact | Constraints / notes |
|---|---|---|---|---|---|---|---|
| `SITESCORE_NARRATIVE_MODEL_ID` | report narrative provider selection | `sitescore-report/src/sitescore_report/narrative.py::NarrativeProviderConfig.from_environment` | optional; unset => provider unconfigured/fallback behavior | no | may share model ID | report process restart/redeploy changes selected model | model selection never changes canonical analytical authority |
| OpenAI SDK credential provider, commonly `OPENAI_API_KEY` | `OpenAI()` SDK client used by report narrative provider | `sitescore-report/src/sitescore_report/narrative.py`; **SDK-level, not direct SiteScore `os.getenv`** | required only when provider is actually configured and SDK needs credential | **yes** | **NO** | rotate provider credential/project; redeploy if platform injection requires | SiteScore does not canonically bind the exact credential env name; do not invent additional provider env names |

### 5.4 Commerce web

| Variable | Consumer | Source | Required / default | Secret? | Staging/prod sharing | Rotation / operational impact | Constraints / notes |
|---|---|---|---|---|---|---|---|
| `COMMERCE_ENV` | Commerce web/settings | `sitescore-commerce/src/sitescore_commerce/settings.py` | default `production`; allowed production/development/test | no | may differ | redeploy changes production validation mode | staging must not masquerade as production; production URL validators require HTTPS |
| `SITESCORE_COMMERCE_DATABASE_URL` | Commerce web/store | `sitescore-commerce/src/sitescore_commerce/settings.py` | required | **yes** | **NO** | DB reconnect/redeploy; coordinate credential rotation | dedicated environment Commerce DB/user |
| `STRIPE_SECRET_KEY` | Checkout/payment/refund gateways | `sitescore-commerce/src/sitescore_commerce/settings.py`; Stripe gateway sources | required | **yes** | **NO** | staged provider key rollover; money-provider calls affected | key mode must align with environment |
| `STRIPE_PRICE_LOCATION_REPORT_V1` | Commerce catalog/Checkout | `sitescore-commerce/src/sitescore_commerce/settings.py`; `checkout.py` | required | no; provider resource ID | **NO** where environment-specific | catalog deployment change; no secret rotation | must satisfy valid `price_` shape; staging uses test-mode Price |
| `COMMERCE_SUCCESS_URL_BASE` | Checkout redirect construction | `sitescore-commerce/src/sitescore_commerce/settings.py`; `checkout.py` | required | no | normally **NO** by hostname | redeploy changes customer redirect target | production HTTPS |
| `COMMERCE_CANCEL_URL_BASE` | Checkout redirect construction | `sitescore-commerce/src/sitescore_commerce/settings.py`; `checkout.py` | required | no | normally **NO** by hostname | redeploy changes customer redirect target | production HTTPS |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | `sitescore-commerce/src/sitescore_commerce/settings.py`; webhook source | required | **yes** | **NO** | endpoint/secret rollover must be coordinated to avoid rejecting valid events | signed external processor ingress authority |
| `STRIPE_EXPECTED_LIVEMODE` | payment evidence validation | `sitescore-commerce/src/sitescore_commerce/settings.py` | required bool | no | **NO** | redeploy changes expected mode and can reject evidence | staging=false/test; production must match intended live mode |
| `STRIPE_API_VERSION` | Stripe SDK requests | `sitescore-commerce/src/sitescore_commerce/settings.py`; gateway sources | optional but pinned | no | may share | API-version change is contract-sensitive; not casual rotation | must equal `2026-07-29.dahlia` |
| `SITESCORE_API_BASE_URL` | Commerce fulfillment/delivery SiteScore client | `sitescore-commerce/src/sitescore_commerce/settings.py`; fulfillment/delivery sources | required | no | **NO** by environment endpoint | redeploy reroutes internal dependency | production HTTPS; no path component |
| `SITESCORE_API_SERVICE_KEY` | Commerce -> SiteScore authentication | `sitescore-commerce/src/sitescore_commerce/settings.py`; SiteScore gateway sources | required | **yes** | **NO** | rotate with API consumer credential provisioning; coordinate overlap | `ssk1_` frozen format; secret body >=24 bytes |
| `SITESCORE_API_TARGET_ID` | durable SiteScore target binding | `sitescore-commerce/src/sitescore_commerce/settings.py` | required | no | normally **NO** | target identity change requires deliberate deployment reconciliation | <=128 UTF-8 bytes |
| `SITESCORE_API_TIMEOUT_SECONDS` | Commerce SiteScore HTTP calls | `sitescore-commerce/src/sitescore_commerce/settings.py`; delivery/fulfillment gateways | default `10` | no | may share same value | redeploy changes timeout/failure classification timing | >0 and <=60 seconds |
| `COMMERCE_AUTOMATION_API_KEY` | internal Commerce automation auth; n8n caller credential validation | `sitescore-commerce/src/sitescore_commerce/settings.py`; automation route auth | required | **yes** | **NO** | rotate coordinated with n8n; temporary dual-key support would require explicit source authority | >=24 bytes; distinct from n8n ingress secret |
| `POSTMARK_SERVER_TOKEN` | Postmark delivery gateway | `sitescore-commerce/src/sitescore_commerce/settings.py`; `delivery.py` | required | **yes** | **NO** | rotate coordinated with email provider | >=16 bytes |
| `POSTMARK_FROM_EMAIL` | Postmark delivery | `sitescore-commerce/src/sitescore_commerce/settings.py`; `delivery.py` | required | no | may differ | sender change may affect deliverability/provider verification | validated email shape |
| `POSTMARK_TEMPLATE_ALIAS` | Postmark template send | `sitescore-commerce/src/sitescore_commerce/settings.py`; `delivery.py` | required | no | may share if intentionally same alias exists | template deployment/alias change affects rendered email | `[A-Za-z0-9._-]{1,100}` |
| `POSTMARK_TIMEOUT_SECONDS` | Postmark HTTP transport | `sitescore-commerce/src/sitescore_commerce/settings.py`; `delivery.py` | default `10` | no | may share same value | redeploy changes uncertain/retry timing | >0 and <=60 seconds |
| `COMMERCE_PUBLIC_BASE_URL` | delivery capability URL creation | `sitescore-commerce/src/sitescore_commerce/settings.py`; `delivery.py` | required | no | **NO** by environment hostname | redeploy changes generated delivery URLs | production HTTPS; server-owned, never caller Host authority |

### 5.5 Commerce dispatcher

| Variable | Consumer | Source | Required / default | Secret? | Staging/prod sharing | Rotation / operational impact | Constraints / notes |
|---|---|---|---|---|---|---|---|
| `COMMERCE_ENV` | dispatcher settings | `sitescore-commerce/src/sitescore_commerce/dispatcher.py` / Commerce settings construction | default production | no | may differ | redeploy affects HTTPS validation mode | production dispatcher requires HTTPS webhook |
| `SITESCORE_COMMERCE_DATABASE_URL` | dispatcher durable outbox access | `sitescore-commerce/src/sitescore_commerce/dispatcher.py`; Commerce settings/store | required | **yes** | **NO** | DB reconnect/redeploy | must point to same environment's Commerce truth |
| `COMMERCE_N8N_ORDER_PAID_WEBHOOK_URL` | dispatcher outbound transport | `sitescore-commerce/src/sitescore_commerce/dispatcher.py` | required | no | **NO** by environment endpoint | redeploy reroutes transport target | production must be HTTPS; exact locked webhook ingress only |
| `COMMERCE_N8N_INGRESS_SECRET` | dispatcher -> n8n Bearer auth | `sitescore-commerce/src/sitescore_commerce/dispatcher.py` | required | **yes** | **NO** | rotate coordinated with n8n ingress; failed coordination leaves events unpublished/retryable | >=24 bytes; must be distinct from automation key when both present |
| `COMMERCE_AUTOMATION_API_KEY` | dispatcher distinct-secret validation; broader Commerce/n8n automation auth | `sitescore-commerce/src/sitescore_commerce/dispatcher.py`; Commerce settings | optional in dispatcher-only context, required elsewhere | **yes** | **NO** | coordinated n8n/Commerce rotation | must not equal ingress secret |
| `COMMERCE_N8N_TIMEOUT_SECONDS` | dispatcher HTTP transport | `sitescore-commerce/src/sitescore_commerce/dispatcher.py` | default `10` | no | may share same value | redeploy changes timeout/uncertain transport behavior | >0 and <=30 seconds |

### 5.6 n8n runtime/workflows

| Variable | Consumer | Source | Required / default | Secret? | Staging/prod sharing | Rotation / operational impact | Constraints / notes |
|---|---|---|---|---|---|---|---|
| `N8N_ENCRYPTION_KEY` | n8n runtime credential encryption | `automation/n8n/runtime/docker-compose.yml` | required | **yes** | **NO** | requires deliberate n8n-aware credential migration/rotation; blind replacement can make stored credentials unreadable | never log/export value |
| `N8N_HOST` | n8n runtime listener config | `automation/n8n/runtime/docker-compose.yml` | default `0.0.0.0` | no | may differ | restart/redeploy networking impact | deployment networking value |
| `N8N_PORT` | n8n runtime | `automation/n8n/runtime/docker-compose.yml` | fixed `5678` in current compose | no | may share | restart/redeploy if changed later | internal listener |
| `N8N_PROTOCOL` | n8n URL/webhook context | `automation/n8n/runtime/docker-compose.yml` | default `https` | no | may share | restart/redeploy | production ingress must remain HTTPS |
| `N8N_WEBHOOK_URL` | n8n webhook URL generation | `automation/n8n/runtime/docker-compose.yml` | required | no | **NO** by environment hostname | restart/redeploy changes externally generated webhook base | only exact locked order-paid path may be public |
| `N8N_USE_WORKFLOW_PUBLICATION_SERVICE` | n8n activation compatibility | `automation/n8n/runtime/docker-compose.yml` | fixed `false` | no | may share | runtime compatibility setting; change requires revalidation | frozen 2.33.4 activation mode |
| `N8N_DIAGNOSTICS_ENABLED` | n8n runtime | `automation/n8n/runtime/docker-compose.yml` | `false` | no | may share | restart/redeploy | telemetry disabled in current runtime evidence |
| `N8N_VERSION_NOTIFICATIONS_ENABLED` | n8n runtime | `automation/n8n/runtime/docker-compose.yml` | `false` | no | may share | restart/redeploy | current runtime evidence |
| `N8N_PERSONALIZATION_ENABLED` | n8n runtime | `automation/n8n/runtime/docker-compose.yml` | `false` | no | may share | restart/redeploy | current runtime evidence |
| `N8N_BLOCK_ENV_ACCESS_IN_NODE` | workflow env access | `automation/n8n/runtime/docker-compose.yml`; workflow JSON uses `$env` | `false` | no | may share | changing to true breaks current workflow env references | remains frozen until workflows/config are jointly reviewed |
| `EXECUTIONS_DATA_SAVE_ON_ERROR` | n8n execution persistence | `automation/n8n/runtime/docker-compose.yml` | `none` | no | may share | restart/redeploy | minimizes stored execution data |
| `EXECUTIONS_DATA_SAVE_ON_SUCCESS` | n8n execution persistence | `automation/n8n/runtime/docker-compose.yml` | `none` | no | may share | restart/redeploy | minimizes stored execution data |
| `COMMERCE_N8N_INGRESS_SECRET` | order-paid workflow ingress authentication | `automation/n8n/workflows/sitescore-order-paid-v1.json` | required | **yes** | **NO** | coordinate with dispatcher; bad rotation rejects ingress while Commerce outbox stays durable | Bearer comparison only; no business authority |
| `COMMERCE_AUTOMATION_API_KEY` | n8n -> Commerce internal calls | order/recovery workflow JSON | required | **yes** | **NO** | coordinate with Commerce automation auth | distinct from ingress secret |
| `SITESCORE_COMMERCE_AUTOMATION_BASE_URL` | n8n HTTP nodes | order/recovery workflow JSON | required | no | **NO** by environment endpoint | reroutes internal Commerce dependency | internal/private Commerce base only |
| `SITESCORE_N8N_POLL_SECONDS` | order workflow paced polling | `automation/n8n/workflows/sitescore-order-paid-v1.json` | default `15` | no | may share | changes orchestration pacing/cost; redeploy/workflow runtime config | finite paced polling only |
| `SITESCORE_N8N_MAX_POLLS` | order workflow poll horizon | `automation/n8n/workflows/sitescore-order-paid-v1.json` | default `60` | no | may share | changes execution horizon, not Commerce terminal truth | exhaustion must not synthesize business state |

Production PostgreSQL variables required by n8n are not canonicalized in the current local compose. FAZ 7.2 must configure the **n8n-supported PostgreSQL environment surface** against a dedicated n8n database/user; FAZ 7.0 deliberately does not invent exact variable names/values that are not present in current repository authority.

### 5.7 Provider credential surfaces

| Variable / credential surface | Consumer | Source | Required / default | Secret? | Staging/prod sharing | Rotation / operational impact | Constraints / notes |
|---|---|---|---|---|---|---|---|
| deployment-factory ACS API credential (**no canonical env name in current source**) | `ACSClient` inside canonical acquisition deployment | `sitescore-providers/src/sitescore_providers/acs/client.py`; `sitescore-api/src/sitescore_api/acquisition.py` | required when ACS acquisition is configured | **yes** | **NO** | provider credential rotation through deployment factory/config injection | credential is executor state only; must not enter fingerprints/artifact metadata |
| deployment-factory Valhalla endpoint/binding configuration | pedestrian provider deployment | `sitescore-api/src/sitescore_api/acquisition.py`; pedestrian provider package | required for configured pedestrian deployment | endpoint no; any auth header/credential **yes** | **NO** for credentials; endpoint may differ | deployment restart/rebind; compatibility evidence must remain exact | no invented env name; use reviewed deployment factory binding |
| Overture/GTFS artifact-loader access configuration | deployment artifact loader | `sitescore-api/src/sitescore_api/acquisition.py` protocol boundary | deployment-specific | credential if required by selected storage/source | **NO** for credentials | rotate selected storage/source credential | source does not canonically define env names here |

Current live acquisition source directly wires these provider/data families:

```text
Census Geocoder
Census ACS
Overture Places artifacts
Valhalla pedestrian/routing
GTFS transit artifacts
```

**Not observed as active canonical runtime wiring at this base:** direct Google Places, OSM/Nominatim, or Mapbox client wiring in `sitescore-api/src/sitescore_api/acquisition.py`. They must not be represented as deployed dependencies merely because they existed in earlier planning. A later authorized deployment factory may only add provider wiring consistent with frozen provider contracts and Reviewer authority.

---

## 6. External dependency matrix

| Dependency | Caller | Purpose | Authority level | Transport / timeout / retry visible in source | Failure posture | Cost-bearing |
|---|---|---|---|---|---|---|
| Managed PostgreSQL — API | API web/worker | durable analysis/report lifecycle | **authoritative for API durable state** | SQLAlchemy/psycopg; pool pre-ping in DB boundary | persistence failure must fail/degrade API; not replaced by broker | yes infrastructure |
| Managed PostgreSQL — Commerce | Commerce web/dispatcher | durable commercial truth | **authoritative commercial truth** | SQLAlchemy/psycopg | persistence unavailable => fail closed/503 or worker failure | yes infrastructure |
| Managed PostgreSQL — n8n | n8n | workflow/runtime persistence only | orchestration persistence, not business truth | production target; exact DB env config deferred to 7.2 | n8n unavailable/degraded; cannot synthesize Commerce truth | yes infrastructure |
| Managed Valkey | Celery worker/beat | queue/scheduling transport | transport only | production `rediss://`; no result backend | unavailable transport must not be interpreted as completed/empty business state | yes infrastructure |
| Spaces/S3-compatible | API worker/report backend | private report PDF bytes | artifact storage only | boto3 client; source has no custom retry policy | storage error => report failure/reconciliation path, no fabricated content | yes infrastructure/storage |
| Stripe | Commerce | Checkout, payment/refund evidence/reconciliation | external processor evidence | Stripe SDK `15.4.0`, API `2026-07-29.dahlia`; no custom timeout/retry override visible in checkout gateway | provider unavailable/invariant failures fail closed; durable Commerce revalidates evidence | **yes** |
| Postmark | Commerce delivery | transactional email | provider evidence only | httpx timeout default from env `10s`; network => uncertain; 429/5xx retryable; strict 200-body validation | uncertainty is not fulfillment proof | **yes** |
| SiteScore API | Commerce | analysis/report fulfillment and report byte verification | analysis/report authority | httpx timeout default `10s`; network + 429/5xx retryable; auth/not-found/conflict/malformed fail closed | Commerce never fabricates SiteScore truth | internal service cost |
| n8n order-paid ingress | Commerce dispatcher | trigger orchestration from durable paid outbox | transport/orchestration only | httpx timeout default `10s`, no redirects; any non-2xx or request failure leaves event unpublished | at-least-once retry of same event identity | infrastructure |
| Commerce automation API | n8n | query/advance/deliver/recovery commands | Commerce remains authority | n8n HTTP nodes timeout `10s`, `maxTries=3`, `waitBetweenTries=2s`; workflow polling paced | replay re-reads durable Commerce state | internal |
| Census Geocoder | API worker through provider deployment | geocoding/geography evidence | provider evidence | provider-neutral HTTP default `15s`, no generic transport retry; 429/5xx classified retryable | provider failure represented explicitly | generally public service; budget/rate limits still operationally relevant |
| Census ACS | API worker | demographic statistical evidence | provider evidence | HTTP default `15s`; ACS key; 429/5xx retryable classification | explicit provider failure, never zero/neutral substitution | API quotas/cost governance relevant |
| Overture Places | API worker/artifact loader | competition evidence | external artifact evidence | artifact-loader boundary; exact remote retrieval implementation is deployment-owned | missing/unresolved evidence must not be fabricated | storage/egress may cost |
| Valhalla | API worker | pedestrian/routing evidence | provider evidence | execution binding + transport contract in provider layer | unavailable/invalid evidence stays failure/unknown | deployment/provider cost |
| GTFS | API worker/artifact loader | transit evidence | provider artifact evidence | artifact acquisition/loading under frozen transit contracts | unavailable data does not become bad/zero | source/storage cost possible |
| OpenAI | report generation when configured | select emphasis/order only from approved closed claims | **untrusted narrative provider selection**; never analytical truth | OpenAI SDK; model from `SITESCORE_NARRATIVE_MODEL_ID`; no SiteScore-specific timeout/retry config observed here | provider-unconfigured/failure path must not alter canonical facts; deterministic fallback exists in report layer | **yes** |

---

## 7. Migration inventory and deployment authority

### 7.1 SiteScore API

```text
Alembic config:
  sitescore-api/alembic.ini
script location:
  sitescore-api/alembic
current head:
  0003_faz5_5
head source:
  sitescore-api/alembic/versions/0003_faz5_5_canonical_success_boundary.py
```

Future predeploy command shape, from repository root:

```text
alembic -c sitescore-api/alembic.ini upgrade head
```

or equivalently from the package directory with the same pinned runtime:

```text
alembic upgrade head
```

Production rule: exactly one migration writer/predeploy job per environment/release. Migration failure **blocks deployment**. Web/worker/beat processes are not migration authority.

### 7.2 Commerce

```text
Alembic config:
  sitescore-commerce/alembic.ini
version table:
  commerce.alembic_version
current head:
  0005_recovery_reconciliation
head source:
  sitescore-commerce/alembic/versions/0005_recovery_reconciliation.py
```

Future predeploy command shape:

```text
cd sitescore-commerce && alembic upgrade head
```

A release may encode the same operation differently only if it resolves the same config/script path deterministically. Exactly one writer; failure blocks release.

### 7.3 n8n

n8n owns its own runtime persistence schema. SiteScore Alembic **must not** migrate n8n tables. Production requires a dedicated n8n PostgreSQL database/user. Version upgrade/migration must be serialized as an n8n runtime deployment operation, with one upgrade authority and rollback/backup planning in later checkpoints.

No production migration was executed in FAZ 7.0.

---

## 8. Public/private HTTP surface inventory

### Commerce

| Method/path | Intended exposure | Authentication/authority note |
|---|---|---|
| `POST /v1/orders` | **public candidate** through Cloudflare | customer purchase intent + required Idempotency-Key; server owns catalog/price |
| `POST /v1/webhooks/stripe` | **public candidate** through Cloudflare | Stripe signature verification; external processor evidence |
| `GET /d/{opaque_token}` | **public candidate** through Cloudflare | opaque expiring delivery capability; Commerce revalidates paid/report binding and proxies bytes |
| `POST /v1/automation/orders/{order_id}/advance` | **internal only** | Commerce automation Bearer; empty body; Commerce authors state |
| `POST /v1/automation/orders/{order_id}/deliver` | **internal only** | Commerce automation Bearer; empty body |
| `GET /v1/automation/orders/{order_id}` | **internal only** | sanitized Commerce projection |
| `POST /v1/automation/recovery/run` | **internal only** | authenticated recovery trigger; bodyless |

Framework `/openapi.json`, `/docs`, `/redoc`, `/docs/oauth2-redirect` are disabled in the frozen Commerce app.

### SiteScore API

All current SiteScore API routes are **internal only** and require service Bearer scopes:

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
POST /v1/reports
GET  /v1/reports/{report_id}
GET  /v1/reports/{report_id}/content
```

No API route is a public candidate in this production topology.

### n8n

Externally reachable candidate is only the exact locked order-paid webhook path corresponding to workflow path:

```text
sitescore-order-paid-v1
```

The n8n editor, admin surface, general REST/API, arbitrary webhook paths, health/admin utilities, and recovery scheduler are **not public product surfaces**. Recovery is internally scheduled by n8n and calls internal Commerce.

---

## 9. Health semantics

FAZ 7.0 does not add application health endpoints.

Normative model for later deployment:

```text
liveness/health = process + socket/TCP where sufficient
dependency health = observed separately
readiness must not fabricate business/scoring readiness
```

A TCP-successful `commerce-web` or `api-web` process can be **process-live** while PostgreSQL, Valkey, Spaces, a provider, Stripe, Postmark, or another dependency is degraded. Those conditions must be surfaced separately through observability/alerts in 7.3; they must not be conflated with canonical SiteScore scoring readiness.

For App Platform services with no frozen `/health` route, TCP/process checks are acceptable. Adding a business-misleading `/health` or `/ready` application route is not authorized in 7.0.

---

## 10. Current production gaps — inventory only

Independent repository discovery at FAZ 7.0 base found:

```text
main branch protected = false
required status checks / enforcement = absent at current branch observation
canonical production Dockerfile set = NOT OBSERVED
canonical OpenTofu/Terraform production stack = NOT OBSERVED
canonical DigitalOcean App Platform staging/production spec = NOT OBSERVED
production/staging cloud deployment proof = NOT OBSERVED
production ingress/path-isolation proof = NOT OBSERVED
Better Stack production log pipeline proof = NOT OBSERVED
Cloudflare production WAF/rate-limit proof = NOT OBSERVED
backup/restore drill proof = NOT OBSERVED
DR proof = NOT OBSERVED
k6 production-readiness load evidence = NOT OBSERVED
```

Repository searches for `Dockerfile`, OpenTofu/Terraform `.tf`/stack terms, and App Platform specification terms returned no canonical production assets. The existing `automation/n8n/runtime/docker-compose.yml` is historical/local n8n runtime evidence, **not** the FAZ 7 canonical production container/IaC stack.

Ownership of gaps:

```text
7.1 -> reproducible containers / supply chain / GitHub governance
7.2 -> IaC / staging deployment / networking / secrets
7.3 -> observability / SLO / alerts
7.4 -> traffic safety / abuse / provider-cost controls
7.5 -> resilience / backpressure / capacity / release safety
7.6 -> backup / restore / data protection / DR
7.7 -> staging E2E / load / failure drills / production readiness
```

---

## 11. Release boundary preview

Future production release constraints, recorded but not implemented here:

```text
production deploy only from user-LOCKed main SHA
immutable application/n8n image digests
explicit production GitHub Environment approval
no automatic deploy_on_push to production
API + Commerce Alembic migrations as explicit predeploy jobs
migration failure blocks release
release record binds source SHA + image digests + migration heads + deploy result
```

A release record cannot upgrade the product claim to empirically validated and cannot treat deployment success as proof of business-outcome validity.

---

## 12. Source-to-runtime traceability index

| Assertion family | Source anchors |
|---|---|
| API version/dependencies | `sitescore-api/pyproject.toml` |
| API settings/TLS | `sitescore-api/src/sitescore_api/settings.py` |
| API app/routes | `sitescore-api/src/sitescore_api/app.py`, `routes.py` |
| API runtime composition | `sitescore-api/src/sitescore_api/runtime.py` |
| Celery configuration/tasks | `sitescore-api/src/sitescore_api/celery_app.py`, `tasks.py` |
| Report storage | `sitescore-api/src/sitescore_api/report_artifacts.py` |
| Acquisition provider wiring | `sitescore-api/src/sitescore_api/acquisition.py` |
| Provider HTTP behavior | `sitescore-providers/src/sitescore_providers/http.py` |
| Census/ACS behavior | `sitescore-providers/src/sitescore_providers/census/client.py`, `acs/client.py` |
| Narrative provider | `sitescore-report/src/sitescore_report/narrative.py`, `sitescore-report/pyproject.toml` |
| Commerce version/deps/script | `sitescore-commerce/pyproject.toml`, `src/sitescore_commerce/__init__.py` |
| Commerce settings | `sitescore-commerce/src/sitescore_commerce/settings.py` |
| Commerce HTTP routes | `sitescore-commerce/src/sitescore_commerce/api.py`, `tests/test_runtime_http_surface.py` |
| Dispatcher | `sitescore-commerce/src/sitescore_commerce/dispatcher.py` |
| Stripe Checkout | `sitescore-commerce/src/sitescore_commerce/checkout.py` |
| Delivery/Postmark | `sitescore-commerce/src/sitescore_commerce/delivery.py`, `delivery_runtime.py` |
| API migrations | `sitescore-api/alembic.ini`, `alembic/versions/0003_faz5_5_canonical_success_boundary.py` |
| Commerce migrations | `sitescore-commerce/alembic.ini`, `alembic/versions/0005_recovery_reconciliation.py` |
| n8n runtime | `automation/n8n/runtime/docker-compose.yml` |
| n8n order workflow | `automation/n8n/workflows/sitescore-order-paid-v1.json` |
| n8n recovery workflow | `automation/n8n/workflows/sitescore-recovery-schedule-v1.json` |
| frozen final n8n hashes/image | `sitescore-commerce/docs/FAZ6_FINAL_INTEGRATED_COMMERCE_AUDIT.md` |

---

## 13. Handoff conclusion

FAZ 7.0 establishes the inventory and operational boundary only. It does not claim that production infrastructure exists.

The codebase can represent the selected secure production broker transport (`rediss://`), while the remaining production system—containers, governance, IaC, staging topology, secret injection, path isolation, observability, traffic safety, capacity, backup/DR, E2E/load/failure proof—remains explicit future FAZ 7 work.

No deployment operator may close those gaps by weakening the frozen business/analytical boundaries described above.
