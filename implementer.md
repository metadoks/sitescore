# SiteScore AI — Implementer → Reviewer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.1
CHECKPOINT_TITLE: API Consumer Reliability + Execution Lifecycle

IMPLEMENTER_STATE: READY_FOR_REVIEW
LOCK_AUTHORITY: USER_ONLY
USER_LOCK_AUTHORIZED: NO

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
CODE_BRANCH: faz5/5-1-api-consumer-lifecycle
CODE_HEAD_SHA: 2cebddd79b292c18babb2ea0258a15f6123a539a
PR: #17
PR_STATE: OPEN
PR_MERGEABLE: TRUE
PR_MERGED: FALSE

REVIEWER_STATE_SEEN: NEEDS_HARDENING
IMPLEMENTER_ACTION_SEEN: HARDEN
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS_REPORTED_BY_IMPLEMENTER: NONE
RESOLVED_BLOCKERS: F51-CANONICAL-SCORED-PATH-H001_BY_REVIEWER_EXPECTATION_CORRECTION, LIFE51-H001_BY_PROVIDER_AUTHORITY_HARDENING

VALIDATED_SHA: 758ad1fbcb7dab9667e0d0dd0c65136d281d8262
VALIDATION_WORKFLOW: faz5-5-1-exact-integration-validation
VALIDATION_RUN_ID: 32042847147
VALIDATION_JOB_ID: 95425120484
VALIDATION_CONCLUSION: SUCCESS
TEMP_VALIDATION_WORKFLOW_REMOVED: YES
VALIDATED_TO_FINAL_DELTA: ONLY .github/workflows/faz5-5-1-validation.yml REMOVAL
VALIDATED_TO_FINAL_COMMITS: 1 CONTENTS_API CLEANUP COMMIT

SITESCORE_API_TESTS: 88 PASS
FROZEN_REGRESSION_TESTS: 1375 PASS
COMBINED_TESTS: 1463 PASS
```

## 1. Reviewer blocker LIFE51-H001 resolved

Reviewer found that the previous production execution seam sat after provider authority construction:

```text
SITESCORE_EVIDENCE_SOURCE_FACTORY=<module:callable>
-> arbitrary acquire()
-> already assembled ExecutionEvidence
```

That surface could supply authority-bearing objects after the frozen provider layer, including `ResolvedLocation`, demographic/pedestrian/competition/transit snapshots, benchmark distributions, source metadata, data coverage, and input-quality authority.

This production seam has been removed.

Production now uses only:

```text
SITESCORE_ACQUISITION_DEPLOYMENT_FACTORY=<module:callable>
```

The factory result must be the exact `CanonicalAcquisitionDeployment` type. Runtime itself constructs `CanonicalProviderEvidenceSource`; a deployment factory cannot return assembled `ExecutionEvidence` or frozen post-provider snapshots.

`CanonicalAcquisitionDeployment` is restricted to genuine server/deployment boundaries and pinned configuration:

```text
HTTPTransport
ValhallaJSONTransport
ArtifactStore
raw DeploymentArtifactLoader
server-owned BenchmarkArtifactLoader
Census manifest / acceptance / persistence policy
ACS manifest / age policy / persistence policy / credential
pedestrian budget / graph / execution / geometry / area policies
Overture manifest / taxonomy / dedup / lifecycle policies
GTFS source bundle / profile / persistence policy
server-owned quality configuration
```

If deployment configuration is absent, production execution remains fail-closed through `MissingExecutionEvidenceSource`.

The explicit Python argument `build_runtime(..., evidence_source=...)` remains only an in-process test seam and is not exposed through production environment configuration.

---

## 2. Concrete frozen provider acquisition chain

New `sitescore-api/src/sitescore_api/acquisition.py` composes the available frozen public provider authority rather than accepting detached provider DTOs.

Canonical execution evidence is now built server-side as:

```text
external AddressIntent
-> CensusAddressRequest using server-owned manifest
-> CensusGeocoderClient.acquire_geocode
-> persisted raw artifact + request fingerprint
-> canonical geocode parser
-> server-owned GeocodeAcceptancePolicy
-> Census geography acquisition at accepted provider coordinates
-> canonical geography parser + source lineage
-> build_resolved_location

ResolvedLocation
-> build_acs_query_plan
-> ACSClient acquisition for each query chunk
-> canonical ACS statistical parsing
-> source metadata + evidence bundle
-> build_demographic_snapshot

ResolvedLocation
-> PedestrianRoutingOrigin.from_resolved_location
-> PedestrianIsochroneClient / Valhalla
-> canonical Valhalla parsing
-> pinned network content-hash verification
-> network/routing source metadata
-> area evidence bound to exact contour geometry identities
-> build_pedestrian_frozen_result

provider-built pedestrian catchments + raw Overture boundary
-> pinned partition artifact/content-hash verification
-> build_partition_raw_artifact
-> parse_overture_partition
-> server-owned catchment policy
-> build_competition_snapshot

provider-built pedestrian derivation + raw GTFS boundary
-> pinned GTFS ZIP content-hash verification
-> parse_gtfs_zip
-> server-owned ReachableTransitStopSet bound to GTFS/pedestrian identities
-> build_transit_snapshot

server-owned benchmark artifact authority
-> exact six BenchmarkDistributionArtifact objects

all provider-built typed evidence
-> frozen metrics
-> frozen benchmark normalization
-> frozen COMB-005
-> frozen normalized-feature assembly
-> frozen readiness
-> frozen application pipeline/gate
-> canonical NOT_SCORE_READY
```

Caller JSON cannot supply trusted coordinates, provider manifests/policies, snapshots, benchmark distributions, source metadata, data-coverage authority, input-quality authority, scoring readiness, or result authority.

`sitescore-providers==0.1.0` is now an explicit exact runtime dependency of `sitescore-api==0.2.0`.

---

## 3. External-boundary integration proof

Added:

```text
sitescore-api/tests/test_provider_acquisition.py
```

The test starts from a valid external coffee analysis request and uses deterministic fakes only at allowed true boundaries:

```text
generic HTTP transport for Census/ACS
Valhalla transport
in-memory ArtifactStore
raw pedestrian network bytes / area boundary
raw Overture partition bytes + decoded records boundary
raw GTFS ZIP boundary
raw reachable-stop-ID boundary
server-owned benchmark artifact loader
```

The test proves:

```text
external street + ZIP bind into Census request
Census address acquisition executes
Census geography acquisition executes
ACS acquisition executes
Valhalla acquisition executes
Overture artifact/parser path executes
GTFS artifact/parser path executes
provider source lineage exists
server-owned benchmark artifacts are loaded
frozen metrics/normalization/readiness/application path executes
completed = None
not_score_ready != None
is_score_ready = False
core analyze invocation count = 0
```

No internal terminal DTO, forged readiness, synthetic SCORE_READY result, or caller-provided provider authority is used.

---

## 4. Hardening defects found and resolved during fresh CI

### Run 32042487417 — superseded failure

Validated candidate exposed a real API orchestration defect:

```text
PedestrianCatchmentArtifact.scale_id
```

was assumed by API code although the frozen artifact has no such field.

Resolution:

```text
WalkingBudgetPolicy.scales
<strict tuple alignment>
PedestrianFrozenResult.catchments
```

The API now selects the analysis catchment according to the frozen builder ordering contract. No frozen DTO or semantic was modified.

### Run 32042690308 — superseded failure

The full provider chain already reached the correct canonical NOT_SCORE_READY outcome. The remaining failure was test methodology only: the valid fixture used the permitted street+city+state address shape while the assertion expected an outbound ZIP key.

Resolution: the common valid external fixture now includes ZIP `78701`, another valid 5.0 address shape. Production validation rules were not weakened.

Neither superseded run is acceptance evidence.

---

## 5. Current canonical scoring truth preserved

Frozen COMB-005 remains unapproved:

```text
APPROVED_ROAD_PARKING_COMPOSITE_POLICIES_V1 = ()
canonical road/parking composite -> POLICY_NOT_APPROVED
canonical road_parking_access_score -> no numeric value
canonical readiness -> NOT_SCORE_READY
```

Therefore current production lifecycle truth remains:

```text
queued -> running -> not_score_ready
```

The new provider-acquisition integration test preserves:

```text
core analyze invocation count = 0
```

`completed` remains modeled but is not claimed reachable under the current locked model. Existing canonical completed-outcome capability guards remain unchanged.

---

## 6. Existing 5.1 reliability semantics preserved

Hardening did not weaken the already reviewed reliability controls:

```text
scoped Bearer analysis:write / analysis:read
HMAC-SHA256 service key verification with server-owned pepper
raw secret not stored
revoked/inactive key and consumer checks
owner-scoped analysis lookup / foreign existence hiding
mandatory Idempotency-Key
canonical request hash over validated request intent
PostgreSQL UNIQUE (consumer_id, idempotency_key)
transactional analysis + dispatch outbox insert
persisted task_id reuse on redispatch
PostgreSQL as lifecycle truth
Redis broker transport only
Celery result backend disabled
session-level PostgreSQL advisory lock
physical PostgreSQL connection pinned for lock lifetime
durable deadlines and timeout reconciliation
terminal state immutability
canonical completed and NOT_SCORE_READY capability guards
Alembic production schema authority
runtime-generated OpenAPI
```

---

## 7. Fresh authoritative hardening validation

The old successful validation run `32032263495` is superseded for LIFE51-H001 code changes and is NOT reused as acceptance evidence.

Fresh authoritative run:

```text
workflow: faz5-5-1-exact-integration-validation
run ID: 32042847147
job/check ID: 95425120484
validated SHA: 758ad1fbcb7dab9667e0d0dd0c65136d281d8262
status: completed
conclusion: SUCCESS
```

Exact environment proven:

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

Real service evidence:

```text
empty PostgreSQL -> alembic upgrade head: PASS
real PostgreSQL race/lifecycle suite: PASS
real Celery worker starts against Redis: PASS
Celery result backend = disabled://
celery inspect = pong / node online
sitescore_api.reconcile_timeouts received and succeeded
```

Fresh test counts on exact validated SHA:

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

One Starlette/TestClient deprecation warning remains; no API test failed.

---

## 8. Validated SHA -> final candidate cleanup

Successful validation SHA:

```text
758ad1fbcb7dab9667e0d0dd0c65136d281d8262
```

After success, the only repository write on the code branch was deletion of:

```text
.github/workflows/faz5-5-1-validation.yml
```

through GitHub's contents API.

That cleanup created final candidate:

```text
2cebddd79b292c18babb2ea0258a15f6123a539a
```

The validation workflow is present at the validated SHA and absent at final branch HEAD. No runtime source, test, migration, dependency, API contract, or documentation file was changed after the successful validation run.

GitHub compare REST is currently unavailable to this integration with `403 Resource not accessible by integration`; therefore this closure is recorded from the exact successful checkout SHA, the exact contents-API delete operation, the resulting commit SHA, and direct absence of the workflow at final branch HEAD. Reviewer can independently verify subtree/blob identity as it did for the prior candidate.

---

## 9. Final PR state at handoff

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

The current PR metadata reports the exact expected base SHA and final head. The temporary validation workflow is absent from the final branch.

No merge was performed.
No user LOCK has been consumed.
No FAZ 5.2 work has started.

---

## 10. Reviewer action requested

Please independently review exact PR #17 HEAD:

```text
2cebddd79b292c18babb2ea0258a15f6123a539a
```

with special focus on LIFE51-H001:

```text
post-provider production evidence factory removed
production seam narrowed to real external/deployment boundaries
frozen Census/ACS/Valhalla/Overture/GTFS authority composed inside sitescore-api
external request integration proof reaches canonical NOT_SCORE_READY
core analyze invocation count = 0
completed authority guards preserved
fresh hardening validation = 1463 PASS
```

Canonical product validity statement remains:

> Mathematically validated scoring engine; empirical validation pending.

STOP. Await Reviewer exact-head decision. Do not merge and do not start 5.2.
