# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 6
CURRENT_CHECKPOINT: 6.0-CORRECTIVE-REOPEN
CHECKPOINT_TITLE: Commerce Runtime Public HTTP Surface Correction

REVIEWER_STATE: IMPLEMENTATION_AUTHORIZED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 287367ce8eb708efce0ebae0a2f9c90d681cce01
LIVE_MAIN_SHA_AT_AUTHORIZATION: 287367ce8eb708efce0ebae0a2f9c90d681cce01
EXPECTED_CODE_BRANCH: corrective/faz6-6-0-runtime-http-surface
EXPECTED_NEW_PR: SEPARATE_FROM_PR_29

BLOCKED_FINAL_PR: #29
BLOCKED_FINAL_PR_HEAD: 1adce96b9645dc572c6819e1f782fd30ae83da91
BLOCKED_FINAL_PR_ACTION: HOLD_DO_NOT_MERGE

FIN6-H001: RESOLVED
FIN6-H002: OPEN_CORRECTIVE_REOPEN_AUTHORIZED
BLOCKERS: FIN6-H002
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0
REOPEN_REASON: FIN6-H002

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_STATUS: FROZEN
FAZ_6_STATUS: IN_PROGRESS
FAZ_6_0_STATUS: CORRECTIVE_REOPEN_IN_PROGRESS
FAZ_6_1_STATUS: LOCKED
FAZ_6_2_STATUS: LOCKED
FAZ_6_3_STATUS: LOCKED
FAZ_6_4_STATUS: LOCKED
FAZ_6_5_STATUS: LOCKED
FAZ_6_FINAL_STATUS: PAUSED_PENDING_CORRECTIVE_LOCK
START_POST_FAZ6: NO
```

---

# 1. AUTHORITY DECISION

Reviewer authorizes one narrow corrective reopen of the Commerce API/application foundation for the runtime-surface defect discovered during FAZ 6-FINAL.

This is NOT a general reopen of FAZ 6.0 and is NOT permission to redesign commerce, payment, fulfillment, refund, delivery, recovery, or n8n behavior.

The sole invariant to correct is:

```text
resolved runtime public HTTP route set == exact authorized seven-route Commerce surface
```

The existing FAZ 6-FINAL PR #29 remains open but blocked. It must not be merged, rebased, or used as the production-fix PR before this corrective reopen is independently reviewed and user-LOCKed.

---

# 2. EXACT DEFECT — FIN6-H002

Current production construction is effectively:

```python
app = FastAPI(title="SiteScore Commerce API", version="0.6.0")
```

FastAPI default application setup can register OpenAPI/documentation routes in addition to the seven intended Commerce routes. Those framework-injected routes are not visible to the source-only AST freeze extractor.

Therefore the current final-freeze claim of an exact seven-route runtime surface is not yet proven and is not accepted.

```text
FIN6-H002: OPEN_CORRECTIVE_REOPEN_AUTHORIZED
```

---

# 3. EXACT AUTHORIZED PUBLIC SURFACE

After correction the resolved runtime application must expose only these Commerce route registrations:

```text
POST /v1/orders
POST /v1/webhooks/stripe
POST /v1/automation/orders/{order_id}/advance
POST /v1/automation/orders/{order_id}/deliver
GET  /v1/automation/orders/{order_id}
POST /v1/automation/recovery/run
GET  /d/{opaque_token}
```

No public OpenAPI, Swagger, ReDoc, OAuth2 redirect helper, router mount, websocket route, or other implicit/explicit route is authorized by this corrective reopen.

---

# 4. AUTHORIZED IMPLEMENTATION SCOPE

Create a separate corrective branch only from exact:

```text
main@287367ce8eb708efce0ebae0a2f9c90d681cce01
```

Expected branch:

```text
corrective/faz6-6-0-runtime-http-surface
```

Expected minimal production correction is at application construction in:

```text
sitescore-commerce/src/sitescore_commerce/api.py
```

Acceptable correction direction is explicit disabling of framework-generated documentation/OpenAPI surfaces, including the relevant FastAPI constructor controls such as:

```python
openapi_url=None
docs_url=None
redoc_url=None
swagger_ui_oauth2_redirect_url=None
```

Use the smallest production change that makes the resolved runtime route table conform to the already-authorized seven-route contract.

Authorized test changes are limited to Commerce API/runtime-surface regression proof. Prefer an existing API test file if appropriate; otherwise one narrowly named test file is acceptable.

Temporary exact-SHA validation workflows under `.github/workflows/` are allowed only for validation and must be removed before READY_FOR_REVIEW unless repository policy requires otherwise.

---

# 5. STRICTLY FORBIDDEN IN THIS REOPEN

Do NOT change:

```text
order/catalog semantics
Stripe Checkout semantics
Stripe webhook/payment authority
payment state machine
order.paid.v1 identity/outbox behavior
SiteScore /v1 integration contracts
analysis/report truth
refund authority or refund amount semantics
delivery grant/token semantics
Postmark semantics
recovery/reconciliation semantics
n8n workflow JSON or runtime version
migration chain or schema
package version
runtime dependency pins
frozen FAZ 3/4/5 source
FAZ 6-FINAL audit artifacts on PR #29
post-FAZ6 implementation
```

No endpoint may be added or removed except the unintended framework-generated documentation/OpenAPI surfaces being disabled.

If fixing FIN6-H002 unexpectedly requires any broader production behavior or contract change, STOP and report:

```text
CONTRACT_CHANGE_REQUIRED: 1
```

or, if architectural redesign is required:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
```

Do not self-authorize expansion.

---

# 6. MANDATORY RUNTIME PROOF

Source parsing alone is insufficient.

Add executable proof using the actual constructed FastAPI application and its resolved runtime route table (`app.routes` or an equivalently authoritative runtime inspection).

The proof must establish at minimum:

1. `/openapi.json` is absent.
2. `/docs` is absent.
3. `/redoc` is absent.
4. the Swagger OAuth2 redirect helper route is absent.
5. no other unexpected route registration exists.
6. the seven approved Commerce routes remain present with their expected methods.
7. all existing endpoint behavior remains unchanged.

The test must fail if a future FastAPI constructor/config drift re-enables an implicit documentation/OpenAPI route.

Do not replace this with another source regex/AST-only assertion.

---

# 7. REQUIRED REGRESSION / VALIDATION GATES

Before READY_FOR_REVIEW, produce fresh exact-SHA evidence for the corrective head.

Required:

```text
full sitescore-commerce suite PASS
runtime route-table regression PASS
migration 0001 -> 0005 / downgrade base / re-upgrade PASS
migration head == 0005_recovery_reconciliation
n8n static 12 baseline PASS
locked order n8n 2.33.4 runtime regression PASS
recovery scheduler/replay regression PASS
frozen FAZ 3/4/5 total 1504 PASS
private S3 regression PASS
Redis/Celery transport PASS
frozen scope scan PASS
secret boundary scan PASS
```

Also prove:

```text
sitescore-commerce version == 0.6.0
n8n runtime == 2.33.4
order workflow SHA256 == 02000eddd70914e76dc528d6d3f43915c50d3e2909c849393ebc0dfcd398dea1
recovery workflow SHA256 == f5409839cec1fa86b6af20f6cd242e71d52dceec8dcdb6cf35fd0b237e4a489c
```

Fresh CI must checkout the exact validated corrective SHA. If temporary validation workflows are deleted after validation, validated-SHA -> final-head delta must contain only those non-semantic workflow removals.

---

# 8. IMPLEMENTER HANDOFF REQUIREMENTS

When complete, write `implementer.md` with at least:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
IMPLEMENTER_ACTION: STOP
EXPECTED_BASE_SHA: 287367ce8eb708efce0ebae0a2f9c90d681cce01
CODE_BRANCH: corrective/faz6-6-0-runtime-http-surface
PR: <new corrective PR>
FINAL_HEAD_SHA: <exact SHA>
VALIDATED_SHA: <exact SHA>
FIN6-H002: RESOLVED_BY_IMPLEMENTER_PENDING_REVIEW
BLOCKERS: NONE
USER_LOCK_AUTHORIZED: NO
FAZ_6_FINAL_RESUME: NO
```

Record exact changed files, CI run/job IDs, test totals, runtime route-table evidence, and validated-to-final delta.

Then STOP.

Do not merge. Do not touch PR #29 production semantics. Do not resume FAZ 6-FINAL until Reviewer verifies the corrective candidate and the user separately authorizes LOCK.

---

# 9. REVIEWER NEXT GATE

On the next Reviewer `Devam`, Reviewer will independently verify:

- live main is still the exact expected base;
- corrective PR base/head and scope;
- production diff is minimal;
- real runtime route table is exact;
- docs/OpenAPI/OAuth helper routes are absent;
- all seven intended endpoints and semantics remain intact;
- full Commerce + n8n + frozen validation is fresh and exact-SHA bound;
- no scope creep exists.

Only if all gates pass may Reviewer issue `READY_TO_LOCK` for the corrective PR.

After user-authorized corrective LOCK and post-merge verification, FAZ 6-FINAL will be recreated/rebased from the new locked main and revalidated. Existing PR #29 is not currently lock-authorized.

Reviewer STOP.
