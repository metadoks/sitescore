# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.0
CHECKPOINT_TITLE: External API Ingress + Versioned Contract Foundation

REVIEWER_STATE: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN_VALIDATION_ONLY
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: c34445e59ea37b4aa430ba1ffa1b4021be52c752
CODE_BRANCH: faz5/5-0-external-api-ingress-contract
REVIEWED_HEAD_SHA: e83123e588a14e741962e26416df3950ce15440b
PR: #16

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

BLOCKERS: VAL-5.0-H001
RESOLVED_BLOCKERS: NONE
```

---

# 1. INDEPENDENT REVIEW RESULT

Reviewer independently inspected exact PR #16 head:

```text
e83123e588a14e741962e26416df3950ce15440b
```

Live GitHub facts at review time:

```text
main = c34445e59ea37b4aa430ba1ffa1b4021be52c752
PR #16 = OPEN
PR base = main
PR base SHA = c34445e59ea37b4aa430ba1ffa1b4021be52c752
PR head branch = faz5/5-0-external-api-ingress-contract
PR head SHA = e83123e588a14e741962e26416df3950ce15440b
PR mergeable = true
compare status = ahead
merge base = c34445e59ea37b4aa430ba1ffa1b4021be52c752
changed files = 17
frozen-package changed files = 0
combined status contexts = none
pull-request workflow runs = none
```

All 17 changed files are additions under:

```text
sitescore-api/**
```

No frozen FAZ 3 / FAZ 4 product file is changed by the reviewed head.

---

# 2. SOURCE REVIEW — NO VERIFIED PRODUCT-CODE BLOCKER AT THIS HEAD

Reviewer inspected the full PR diff and did not find a verified runtime/authority defect requiring code hardening at this stage.

The reviewed source correctly preserves the intended 5.0 boundary:

```text
untrusted JSON
-> strict Pydantic discriminated request schema
-> server UUIDv4 request_id
-> distinct server UUIDv4 analysis_id candidate
-> server-factory-owned AnalysisIngressCommand
-> exact frozen sector-specific RevenueInput construction
-> injected lifecycle submit/retrieve port
```

Verified source properties include:

```text
sector literals = coffee / restaurant / gym / beauty
unknown external fields rejected
non-US address rejected
Census-compatible address shape enforced
bool-as-number rejected
numeric-string coercion rejected
NaN / Infinity rejected
rate/utilization/penetration ordering validated
negative common costs rejected
exact frozen RevenueInput dataclasses constructed
request_id and analysis_id required distinct UUIDv4 values at ingress construction
route layer does not import or invoke sitescore.analyze
route layer does not import sitescore.engines
route layer contains no scoring/financial/decision formula implementation
default lifecycle backend contains no process-local persistence claim
default POST -> 503 analysis_lifecycle_unavailable
default GET -> 503 analysis_lifecycle_unavailable
no default 202 persisted-resource claim
validation failures normalize to SiteScore error envelope
unexpected failures normalize to internal_server_error
OpenAPI derives from runtime FastAPI/Pydantic models
no 5.1+ database/queue/auth/idempotency/report/payment/n8n stack introduced
```

This is a source-review finding only. READY_TO_LOCK still requires the validation evidence below.

---

# 3. BLOCKER VAL-5.0-H001 — REQUIRED VALIDATION EVIDENCE IS INCOMPLETE

The original 5.0 acceptance contract requires both:

```text
[ ] new sitescore-api tests pass under the exact pinned dependency runtime
[ ] frozen regression passes as a fresh execution
```

Implementer truthfully reported that the current execution image used:

```text
FastAPI 0.128.2   != required 0.140.0
Pydantic 2.13.4   = required 2.13.4
HTTPX 0.28.1      = required 0.28.1
pytest 9.0.2      != required 8.4.2
```

and that only:

```text
sitescore-api: 68 / 68 PASS
sitescore-core: 86 / 86 PASS
```

were freshly executed in that environment.

The historical frozen baseline:

```text
sitescore-app:         19
sitescore-pipeline:    53
sitescore-benchmarks: 191
sitescore-metrics:     67
sitescore-spatial:    180
sitescore-providers:  418
sitescore-data:       361
sitescore-core:        86
TOTAL:               1375
```

must not be reused as if freshly executed.

Therefore exact-head READY_TO_LOCK is currently BLOCKED by evidence, not by a known product-code defect.

---

# 4. AUTHORIZED HARDENING — VALIDATION ONLY

Remain on the same branch and PR:

```text
branch: faz5/5-0-external-api-ingress-contract
PR: #16
```

Do not start Checkpoint 5.1.
Do not merge.
Do not modify frozen product semantics.

For this hardening only, Reviewer explicitly authorizes one **temporary validation workflow artifact** under:

```text
.github/workflows/
```

solely to obtain reproducible GitHub-hosted validation evidence.

This temporary workflow is not a product-scope expansion and MUST be removed from the final candidate head before READY_TO_LOCK.

The workflow must validate the exact PR product tree using a clean GitHub-hosted Python environment and must install/use at least the exact 5.0 pins:

```text
fastapi==0.140.0
pydantic==2.13.4
httpx==0.28.1
pytest==8.4.2
```

plus the repository's exact required external dependencies for the frozen packages, including their already-pinned spatial dependencies where needed.

Local repository packages may be installed in editable/local mode with dependency resolution arranged so that local `0.1.0` packages satisfy their existing internal package dependencies. Do not publish or substitute external packages for SiteScore local packages.

---

# 5. REQUIRED VALIDATION RUN

On one exact validation SHA, execute fresh tests for:

```text
sitescore-api
sitescore-app
sitescore-pipeline
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Record actual counts. Do not merely copy historical values.

If the frozen suites remain unchanged, the expected arithmetic reference is:

```text
frozen historical reference = 1375
current sitescore-api suite  = 68
combined reference          = 1443
```

but the workflow result itself is authoritative; do not force the count to 1443 if discovery genuinely differs.

The validation run must also demonstrate that the actual imported versions for the API test job are exactly:

```text
FastAPI 0.140.0
Pydantic 2.13.4
HTTPX 0.28.1
pytest 8.4.2
```

Print these versions in the workflow log before running the API suite.

---

# 6. FAILURE HANDLING

If exact-pin `sitescore-api` tests fail because of 5.0 code/API compatibility:

```text
- fix only within the already-authorized sitescore-api/** scope
- remain on the same branch / PR
- rerun the full validation
```

If frozen regression fails and resolving it would require changing a frozen FAZ 3 / FAZ 4 runtime-observable contract:

```text
CONTRACT_CHANGE_REQUIRED: 1
IMPLEMENTER_STATE: BLOCKED_FOR_REVIEW
```

and STOP. Do not edit the frozen package to make the test green.

If a selected dependency/version proves technically incompatible and cannot be resolved without changing the Reviewer-selected architecture/dependency decision:

```text
DESIGN_DECISION_REVIEW_REQUIRED: 1
IMPLEMENTER_STATE: BLOCKED_FOR_REVIEW
```

and STOP.

---

# 7. TEMPORARY WORKFLOW CLOSURE REQUIREMENT

After obtaining a fully successful validation run:

1. record the workflow run ID,
2. record the job ID(s),
3. record the exact validated commit SHA,
4. record exact imported dependency versions,
5. record actual per-package PASS counts,
6. remove the temporary `.github/workflows/...` validation file,
7. push the workflow-removal commit,
8. verify the final PR head differs from the validated SHA only by deletion of that temporary workflow unless a reviewed code fix was also part of the validated SHA,
9. ensure the final PR changed-file set returns to only `sitescore-api/**`,
10. update `implementer.md` with both the validated SHA and final post-cleanup PR head SHA.

The final candidate must not retain the temporary workflow.

---

# 8. REQUIRED IMPLEMENTER HANDOFF

After successful validation and workflow cleanup, update `implementer.md` with at least:

```text
CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.0
IMPLEMENTER_STATE: READY_FOR_REVIEW
BASE_SHA: c34445e59ea37b4aa430ba1ffa1b4021be52c752
CODE_BRANCH: faz5/5-0-external-api-ingress-contract
PR: #16
VALIDATED_SHA: <exact validation SHA>
CODE_HEAD_SHA: <final post-cleanup head>
TEMP_VALIDATION_WORKFLOW_REMOVED: YES
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
```

Also include:

```text
workflow run ID
job ID(s)
exact dependency versions printed by the run
sitescore-api fresh PASS count
all eight frozen package fresh PASS counts
combined actual PASS count
compare proof validated SHA -> final head
final changed-file inventory
```

Then STOP.

---

# 9. CURRENT REVIEW DECISION

```text
REVIEW_DECISION: NEEDS_HARDENING
READY_TO_LOCK: NO
LOCK_RESULT: NOT_APPLICABLE
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: VAL-5.0-H001
```

No user LOCK is requested at this stage.

Implementer should perform only the validation hardening above and return to Reviewer.

STOP.
