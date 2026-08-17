# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.1
CHECKPOINT_TITLE: API Consumer Reliability + Execution Lifecycle

REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
CODE_BRANCH: faz5/5-1-api-consumer-lifecycle
REVIEWED_HEAD_SHA: 2cebddd79b292c18babb2ea0258a15f6123a539a
PR: #17

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
ADDITIONAL_REOPEN_REQUIRED: 0

BLOCKERS: NONE
RESOLVED_BLOCKERS: F51-CANONICAL-SCORED-PATH-H001, LIFE51-H001
```

---

# 1. EXACT-HEAD REVIEW DECISION

Reviewer independently reviewed current PR #17 exact candidate:

```text
PR: #17
state: OPEN
merged: FALSE
mergeable: TRUE
base branch: main
base SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
head branch: faz5/5-1-api-consumer-lifecycle
head SHA: 2cebddd79b292c18babb2ea0258a15f6123a539a
changed files: 40
```

Current `main` was independently read from GitHub and remains exactly:

```text
92d00cda34d337ce5c4e172d5184c9e3f1f55b11
```

The base-to-head compare has merge-base exactly equal to that locked main SHA, is ahead by 57 commits and behind by 0. Every changed product file is under:

```text
sitescore-api/**
```

No frozen FAZ 3 / FAZ 4 package file is modified. No FAZ 5.2/report/narrative/PDF/S3/payment/n8n/FAZ 6 product scope is introduced.

Decision:

```text
REVIEW_DECISION: READY_TO_LOCK
READY_TO_LOCK: YES
LOCK_RESULT: PENDING_USER_AUTHORIZATION
```

---

# 2. LIFE51-H001 — RESOLVED

The previously blocked production authority seam has been materially corrected.

Superseded design:

```text
SITESCORE_EVIDENCE_SOURCE_FACTORY=<module:callable>
-> arbitrary acquire()
-> already assembled ExecutionEvidence
```

That design allowed a deployment plugin to sit after frozen provider authority and supply detached provider-domain DTOs.

Current production design uses:

```text
SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY=<module:callable>
-> exact CanonicalAcquisitionDeployment
-> runtime-owned CanonicalProviderEvidenceSource
-> frozen provider acquisition/parsing/lineage
-> ExecutionEvidence
```

`runtime.py` requires the factory result to be the exact `CanonicalAcquisitionDeployment` type and then constructs `CanonicalProviderEvidenceSource` itself. Production environment configuration can no longer directly install an `ExecutionEvidenceSource` that returns assembled post-provider evidence.

The remaining configurable seams are deployment/external boundaries and pinned server configuration: provider-neutral HTTP transport, Valhalla transport, artifact storage/reader inputs, exact provider manifests/policies/credentials, precomputed boundaries explicitly permitted by the frozen provider contracts, and server-owned benchmark artifacts/quality configuration.

The explicit Python `build_runtime(..., evidence_source=...)` argument remains an in-process injection seam; it is not selected from production environment configuration and is not a network/API authority surface.

---

# 3. FROZEN PROVIDER AUTHORITY COMPOSITION — ACCEPTED

The new production `sitescore-api/src/sitescore_api/acquisition.py` composes the frozen public provider contracts rather than accepting detached provider snapshots.

## Census

Validated external address intent is converted into frozen `CensusAddressRequest` with server-owned manifest/policies and passed through:

```text
CensusGeocoderClient.acquire_geocode
-> raw acquisition artifact / request fingerprint
-> canonical parser
-> GeocodeAcceptancePolicy
-> provider-derived coordinates
-> Census geography acquisition
-> canonical geography parser
-> SourceMetadata
-> build_resolved_location
```

Caller JSON cannot provide trusted coordinates, Census manifests or canonical `ResolvedLocation` authority.

## ACS

Resolved Census geography is passed through:

```text
build_acs_query_plan
-> ACSClient.acquire
-> frozen statistical parsing
-> source metadata
-> evidence bundle
-> build_demographic_snapshot
```

## Pedestrian / Valhalla

Provider-built location authority is passed through:

```text
PedestrianRoutingOrigin.from_resolved_location
-> PedestrianIsochroneClient
-> frozen Valhalla parsing / request lineage
-> pinned network-content hash verification
-> PedestrianAreaEvidence tied to exact contour geometry identity + server-owned area policy
-> build_pedestrian_frozen_result
```

Reviewer checked the frozen 3.3-5 record: precomputed/caller area evidence is an intentional frozen upstream boundary; no geodesic/equal-area production computation backend was selected in that checkpoint. The new server-owned deployment artifact seam therefore does not recreate the prior post-provider DTO bypass.

## Overture competition

Pinned partition bytes/descriptors are hash-verified and then passed through:

```text
build_partition_raw_artifact
-> parse_overture_partition
-> frozen competition builder
```

Reviewer also checked the frozen 3.3-4 contract. Decoded row reading and precomputed catchment membership are intentional provider boundaries, while empirical coverage sufficiency policy remains deferred. The current implementation conservatively supplies `CoverageState.UNKNOWN`, so the frozen builder returns UNKNOWN/non-AVAILABLE competition rather than manufacturing a zero competitor count.

This is safe under the current locked model and is not a LOCK blocker: no AVAILABLE competition claim or false zero is created.

## GTFS / transit

Raw GTFS ZIP bytes are bound to exact frozen source identity and passed through:

```text
acquire_gtfs_zip_bytes
-> parse_gtfs_zip
-> server-owned precomputed reachability boundary
-> ReachableTransitStopSet bound to exact transit bundle + pedestrian derivation/walking-budget identities
-> build_transit_snapshot
```

Reviewer checked frozen 3.3-6: precomputed pedestrian-reachable stop membership is explicitly the frozen provider design.

## Benchmarks

Server-owned benchmark loader must return exactly the six required direct-feature keys, and every value must be an exact `BenchmarkDistributionArtifact`.

No caller request field can provide benchmark artifacts, readiness, scores, confidence, provider snapshots or result authority.

---

# 4. CURRENT CANONICAL PRODUCT TRUTH PRESERVED

The corrected 5.1 contract remains intact:

```text
COMB005_V1_POLICY = NOT_APPROVED
APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 = ()
road/parking composite = POLICY_NOT_APPROVED
road_parking_access_score = no numeric value
canonical readiness = NOT_SCORE_READY
```

Current real production lifecycle target remains:

```text
queued -> running -> not_score_ready
```

The new provider-boundary integration starts from a valid external request, traverses frozen Census/ACS/Valhalla/Overture/GTFS provider APIs and the frozen downstream metrics/benchmark/readiness/application chain, and proves:

```text
completed = None
not_score_ready != None
is_score_ready = False
core analyze invocation count = 0
```

No fake approved COMB-005 state, neutral fill, zero score, forged readiness, fabricated `CategoryScores`, detached `CanonicalAnalysisResult` or caller-provided successful result is used.

`completed` remains modeled for a future genuinely ELIGIBLE frozen authority state, but this checkpoint does not claim current reachability.

---

# 5. DURABLE API / RELIABILITY REVIEW — ACCEPTED

The previously reviewed 5.1 reliability architecture remains intact after hardening:

```text
scoped Bearer analysis:write / analysis:read
HMAC-SHA256 API-key verifier with server-owned pepper
constant-time verification
raw API secret not persisted
revoked/inactive key and consumer checks
consumer-owned analysis resource isolation
foreign UUID and missing UUID -> same 404 analysis_not_found semantics
mandatory Idempotency-Key
canonical SHA-256 request-intent hash
PostgreSQL UNIQUE (consumer_id, idempotency_key)
same key + same payload -> same logical analysis_id
same key + different payload -> 409 idempotency_conflict
transactional analysis + dispatch-outbox creation
persisted task_id reuse for redispatch
PostgreSQL = durable lifecycle truth
Redis = broker transport only
Celery result backend = disabled
queued/running/completed/not_score_ready/failed/timed_out exact public state set
server-owned durable deadline
GET timeout reconciliation
PostgreSQL advisory execution lock
physical DB connection pinned for advisory-lock lifetime
terminal-state immutability
canonical completed-outcome capability guard
canonical NOT_SCORE_READY capability guard
Alembic = production schema authority
runtime-generated OpenAPI
V1 callback/webhook = NONE
V1 consumer integration = polling
```

No reopening of frozen FAZ 3 / FAZ 4 contracts is required.

---

# 6. EXACT DEPENDENCY CONTRACT — VERIFIED

Final `sitescore-api==0.2.0` directly pins:

```text
fastapi==0.140.0
pydantic==2.13.4
SQLAlchemy==2.0.51
alembic==1.18.5
psycopg[binary]==3.3.4
celery==5.6.3
redis==7.4.1
sitescore-core==0.1.0
sitescore-data==0.1.0
sitescore-providers==0.1.0
sitescore-metrics==0.1.0
sitescore-benchmarks==0.1.0
sitescore-pipeline==0.1.0
sitescore-app==0.1.0
```

Dev/test:

```text
httpx==0.28.1
pytest==8.4.2
```

No OpenAI/Jinja2/WeasyPrint/Matplotlib/S3/payment dependency enters 5.1.

---

# 7. FRESH HARDENING VALIDATION — INDEPENDENTLY VERIFIED

Authoritative hardening run:

```text
workflow: faz5-5-1-exact-integration-validation
run ID: 32042847147
job ID: 95425120484
validated SHA: 758ad1fbcb7dab9667e0d0dd0c65136d281d8262
status: completed
conclusion: SUCCESS
```

Reviewer independently inspected the run metadata, job steps and full job log. The workflow checked out the exact validated SHA.

Exact runtime evidence:

```text
Python 3.11.15
PostgreSQL 16.15
Redis server 7.4.10
FastAPI 0.140.0
Pydantic 2.13.4
SQLAlchemy 2.0.51
Alembic 1.18.5
psycopg 3.3.4
Celery 5.6.3
redis-py 7.4.1
HTTPX 0.28.1
pytest 8.4.2
Shapely 2.1.2
pyproj 3.7.2
sitescore-providers 0.1.0
```

The run used real PostgreSQL and Redis service containers, upgraded the Alembic schema, started a real Celery worker, proved `results: disabled://`, received `sitescore_api.reconcile_timeouts`, and completed the task successfully.

Fresh exact-SHA test counts:

```text
sitescore-api:         88 PASS
sitescore-app:         19 PASS
sitescore-pipeline:    53 PASS
sitescore-benchmarks: 191 PASS
sitescore-metrics:     67 PASS
sitescore-spatial:    180 PASS
sitescore-providers:  418 PASS
sitescore-data:       361 PASS
sitescore-core:        86 PASS
--------------------------------
frozen regression:  1375 PASS
combined total:     1463 PASS
```

One Starlette/TestClient deprecation warning remains. It is non-blocking for the exact selected/pinned 5.1 dependency contract; no test failed.

---

# 8. VALIDATED SHA -> FINAL HEAD CLOSURE — VERIFIED

Reviewer independently compared:

```text
758ad1fbcb7dab9667e0d0dd0c65136d281d8262
->
2cebddd79b292c18babb2ea0258a15f6123a539a
```

GitHub reports:

```text
status: ahead
ahead_by: 1
behind_by: 0
total_commits: 1
changed files: 1
```

The sole changed file is:

```text
.github/workflows/faz5-5-1-validation.yml
status: REMOVED
```

No source, test, migration, dependency, API contract or documentation semantic changed after successful validation.

Therefore the fresh validation applies to the exact final product candidate now under review.

---

# 9. ACCEPTANCE CHECKLIST

```text
[YES] exact base SHA unchanged
[YES] PR open / mergeable / not merged
[YES] exact head independently resolved
[YES] final diff confined to sitescore-api/**
[YES] frozen FAZ 3 / FAZ 4 packages unchanged
[YES] scoped Bearer auth / consumer isolation
[YES] durable PostgreSQL idempotency race authority
[YES] transactional outbox / broker recovery
[YES] PostgreSQL lifecycle truth / Redis broker only
[YES] duplicate-worker concurrency guard
[YES] durable timeout and terminal-state integrity
[YES] no arbitrary JSON completed-result authority
[YES] production post-provider evidence plugin removed
[YES] external request binds through frozen Census provider acquisition
[YES] ACS provider acquisition/parsing composed
[YES] Valhalla provider acquisition/parsing composed
[YES] Overture pinned partition parser/lineage composed
[YES] GTFS parser/source/reachability authority composed
[YES] server-owned benchmark artifact boundary
[YES] current canonical NOT_SCORE_READY propagated truthfully
[YES] core analyze remains uncalled for NOT_SCORE_READY
[YES] exact dependency versions validated
[YES] fresh API + frozen regression suites passed
[YES] validated-to-final delta is validation-workflow deletion only
[YES] no 5.2+ scope leakage
```

---

# 10. LOCK GATE

Acceptance is valid only for exact head:

```text
2cebddd79b292c18babb2ea0258a15f6123a539a
```

If PR #17 HEAD changes before merge, this READY_TO_LOCK becomes stale and Reviewer must review the new exact head.

Reviewer does not merge and does not self-lock.

```text
USER_LOCK_AUTHORIZED: NO
LOCK_RESULT: PENDING_USER_AUTHORIZATION
IMPLEMENTER_NEXT_ACTION: WAIT_FOR_USER_LOCK
```

When and only when the user sends literal `LOCK` to the Implementer chat while this exact-head acceptance remains current, Implementer may perform the protocol-authorized merge/lock closure for FAZ 5.1.

Do not start FAZ 5.2 before successful LOCK closure is recorded and independently verified.

STOP.
