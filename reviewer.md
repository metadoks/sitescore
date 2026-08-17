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

REVIEWER_STATE: NEEDS_HARDENING
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY

EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
CODE_BRANCH: faz5/5-1-api-consumer-lifecycle
REVIEWED_HEAD_SHA: 7e2399cdb4bbc7d43f24625427bf7eb88534a922
PR: #17

FAZ_3_STATUS: FROZEN
FAZ_4_STATUS: FROZEN
FAZ_5_0_STATUS: LOCKED

CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: LIFE51-H001
RESOLVED_BLOCKERS: F51-CANONICAL-SCORED-PATH-H001
```

---

# 1. EXACT-HEAD REVIEW RESULT

Reviewer independently reviewed current PR #17 candidate:

```text
PR: #17
state: OPEN
merged: FALSE
mergeable: TRUE
base branch: main
base SHA: 92d00cda34d337ce5c4e172d5184c9e3f1f55b11
head branch: faz5/5-1-api-consumer-lifecycle
head SHA: 7e2399cdb4bbc7d43f24625427bf7eb88534a922
changed files: 37
```

The implementation is materially strong and the following checkpoint areas passed source review:

```text
sitescore-api==0.2.0 exact dependency contract
scoped Bearer service API-key model
HMAC-SHA256 secret verification with server-owned pepper
constant-time digest comparison
revoked/inactive key and consumer checks
consumer-owned analysis lookup / foreign-existence hiding
required Idempotency-Key validation
validated-request canonical SHA-256 hashing
PostgreSQL UNIQUE consumer/idempotency boundary
same-payload replay -> same analysis_id
same-key/different-payload -> 409
transactional analysis + outbox creation
persisted task_id reuse for redispatch
PostgreSQL as lifecycle truth
Redis as broker only
Celery result backend disabled for product truth
queued/running/completed/not_score_ready/failed/timed_out state vocabulary
server-owned durable deadlines
GET timeout reconciliation
PostgreSQL advisory-lock execution claim
terminal-state immutability guard
canonical completed-outcome capability guard
canonical NOT_SCORE_READY outcome capability guard
Alembic production schema authority
runtime-generated OpenAPI
no report/payment/n8n/5.2 scope leakage
```

The corrected COMB-005 expectation is implemented correctly downstream: current frozen canonical road/parking truth reaches canonical `NOT_SCORE_READY`, and core analysis is not invoked on that path.

There is one remaining checkpoint blocker below.

---

# 2. VALIDATION EVIDENCE — ACCEPTED

Reviewer independently inspected GitHub Actions run:

```text
workflow: faz5-5-1-exact-integration-validation
run ID: 32032263495
job ID: 95394699756
validated SHA: c34fd71648141a66b83b1ac275b6ea4fdb606090
status: completed
conclusion: SUCCESS
```

The log proves the exact validation candidate was checked out and used:

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
```

Fresh successful counts:

```text
sitescore-api:         86 PASS
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
combined total:     1461 PASS
```

The same run started a real Celery worker against Redis, proved the result backend is disabled, received `sitescore_api.reconcile_timeouts`, and completed that task successfully.

The API suite emitted one Starlette/TestClient deprecation warning; no test failed.

---

# 3. VALIDATED SHA -> FINAL HEAD CLEANUP — VERIFIED

The GitHub compare endpoint was not available to this Reviewer integration for this PR, so Reviewer used repository-tree/blob identity instead of relying on Implementer prose.

At validated SHA:

```text
c34fd71648141a66b83b1ac275b6ea4fdb606090
```

and final reviewed head:

```text
7e2399cdb4bbc7d43f24625427bf7eb88534a922
```

all top-level `sitescore-api` product subtree identities are identical:

```text
README.md    912637116dd402ebcf11318027c957814e58d62e
alembic.ini  d8b262087383840210acdab106d3646857a14410
alembic/     7b088ead01213cffe435ea6094de1d502212bf06
docs/        d8039ff344c04f709acf9a27f7361bd8ff096f08
pyproject    4866f4ef3daffb56671b8d5fc523cbcd512e3fd9
src/         13312c418a485e8be34774f4b0450d1012c1b277
tests/       e5e3c9a25c887ef95ed85a1c22ee46232408bfc9
```

The temporary validation workflow exists at the validated SHA:

```text
.github/workflows/faz5-5-1-validation.yml
```

and is absent at final head `7e2399...`.

Therefore the successful validation evidence remains applicable to the final product subtree currently under review.

---

# 4. BLOCKER LIFE51-H001 — PRODUCTION EXECUTOR DOES NOT YET COMPOSE FROZEN PROVIDER ACQUISITION AUTHORITY

The corrected 5.1 contract still requires a real production execution-service boundary:

```text
durable validated request intent
-> server-owned provider/deployment configuration
-> frozen provider acquisition / evidence
-> frozen metrics / benchmark normalization
-> frozen canonical normalized-feature assembly
-> frozen canonical readiness
-> frozen pipeline terminal factory
-> frozen application pipeline factory
-> frozen application gate
```

The current source does not yet satisfy the provider-acquisition segment of that chain.

Current `execution.py` defines an `ExecutionEvidenceSource` whose `acquire()` method returns an already-assembled `ExecutionEvidence` containing, among other authority-bearing objects:

```text
ResolvedLocation
DemographicSnapshot
IsochroneSnapshot
CompetitionSnapshot
TransitSnapshot
BenchmarkDistributionArtifact mappings
SourceMetadata
GeographicLevel
data coverage
input qualities
```

Current `runtime.py` loads that source from:

```text
SITESCORE_EVIDENCE_SOURCE_FACTORY=<arbitrary module:callable>
```

and validates only that the returned object exposes an `acquire` attribute.

If no factory is configured, production runtime uses `MissingExecutionEvidenceSource`, whose execution path fails with `ExecutionConfigurationError`.

There is no concrete production `sitescore-api` evidence-source implementation in this candidate that invokes the frozen `sitescore-providers` acquisition contracts. In particular, the current production executor does not bind the external address intent to the existing frozen Census provider client/manifest/persistence/parser authority before accepting a `ResolvedLocation`/other evidence surface.

Frozen provider source does expose real acquisition authority. For example `CensusGeocoderClient` requires frozen/provider-neutral `HTTPTransport`, `ArtifactStore`, `CensusAddressRequest`, `CensusGeographyManifest`, persistence policy, provider identity/fingerprint, raw acquisition artifacts and canonical parsing. Those controls are bypassable if a deployment plugin is allowed to hand the executor an already-constructed `ResolvedLocation` directly.

This is not merely dependency injection at the HTTP transport seam. The injection seam currently sits **after provider authority construction** and also supplies benchmark/evaluation inputs that influence later canonical execution.

The successful canonical integration tests likewise use `StaticEvidenceSource` and manually construct the already-typed location/demographic/isochrone/competition/transit/benchmark evidence. That is valid for downstream frozen pipeline/application testing, but it does not prove the required production provider-acquisition chain.

### Why this is a blocker

A deployment-supplied `module:callable` can currently become a new post-provider authority and manufacture typed-but-not-provider-acquired evidence. Type correctness alone is not equivalent to frozen provider lineage/canonical acquisition authority.

This would weaken the intended boundary:

```text
caller JSON is intent only
server/deployment owns provider manifests/policies
frozen provider clients/parsers establish acquisition lineage
```

into:

```text
arbitrary deployment plugin may supply post-provider DTO authority
```

Therefore exact-head READY_TO_LOCK is blocked.

---

# 5. REQUIRED HARDENING FOR LIFE51-H001

Remain on the same branch and PR:

```text
branch: faz5/5-1-api-consumer-lifecycle
PR: #17
```

Do not start 5.2.
Do not merge.
Do not modify frozen FAZ 3 / FAZ 4 semantics.

Implement a concrete server-owned production evidence/acquisition boundary inside the authorized `sitescore-api/**` scope that composes the frozen provider contracts actually available in the repository.

At minimum:

1. Bind the validated `AddressIntent` to the frozen Census address/geography acquisition path using server-owned manifest/benchmark/vintage/persistence configuration.
2. Use the frozen provider client/parser/artifact/public factory contracts rather than accepting a detached `ResolvedLocation` from an arbitrary post-provider plugin.
3. For other evidence needed by the current canonical NOT_SCORE_READY path, compose the available frozen provider/public acquisition contracts and server-owned benchmark artifact loading authority. Do not let external API JSON supply manifests, policies, trusted coordinates, snapshots, benchmark distributions, coverage or input-quality authority.
4. Any configurable adapter/plugin seam must be narrowed to genuine external transport/storage/provider boundaries (for example HTTP transport, artifact storage, deployment configuration or artifact loader) rather than returning the fully assembled post-provider `ExecutionEvidence` authority surface.
5. The production runtime must have a concrete canonical acquisition implementation selected by server configuration; `MissingExecutionEvidenceSource` may remain a fail-closed fallback for absent deployment configuration, but an unimplemented external plugin must not be the only path to real execution.
6. Add an integration test that starts from a valid external analysis request and deterministic fakes at the external provider/HTTP/artifact-storage boundary, then passes through the frozen provider acquisition/parsing/lineage APIs before reaching the already-proven frozen metrics/benchmark/readiness/application `NOT_SCORE_READY` path.
7. Preserve `core analyze invocation count = 0` for the current COMB-005 NOT_SCORE_READY path.
8. Preserve completed-result canonical authority guards; do not fabricate a score-ready path.

If the actual frozen public provider APIs cannot compose the required production evidence path without changing frozen runtime semantics or relying on unsupported private internals, do not invent authority. Instead set:

```text
CONTRACT_CHANGE_REQUIRED: 1
IMPLEMENTER_STATE: BLOCKED_FOR_REVIEW
```

and STOP with exact source evidence.

---

# 6. REVALIDATION AFTER HARDENING

Because LIFE51-H001 changes production execution code, obtain fresh evidence on the new exact candidate SHA.

Required:

```text
sitescore-api full unit/integration suite
real PostgreSQL migration/race/lifecycle tests
real Redis/Celery transport test
new frozen-provider acquisition -> canonical NOT_SCORE_READY integration test
all eight frozen regression suites
```

Print and verify the exact dependency/runtime versions again.

A temporary validation workflow remains authorized for this hardening only. Remove it before the final candidate and prove validated-SHA -> final-head product identity again.

Report actual fresh counts; do not reuse run `32032263495` as evidence for code changed by this hardening.

---

# 7. CURRENT REVIEW DECISION

```text
REVIEW_DECISION: NEEDS_HARDENING
READY_TO_LOCK: NO
LOCK_RESULT: NOT_APPLICABLE
CURRENT_PHASE: FAZ 5
CURRENT_CHECKPOINT: 5.1
PR: #17
REVIEWED_HEAD_SHA: 7e2399cdb4bbc7d43f24625427bf7eb88534a922
CONTRACT_CHANGE_REQUIRED: 0
DESIGN_DECISION_REVIEW_REQUIRED: 0
BLOCKERS: LIFE51-H001
RESOLVED_BLOCKERS: F51-CANONICAL-SCORED-PATH-H001
```

No user LOCK is requested.

Implementer must perform only the hardening above on the same branch / PR and return for another exact-head review.

STOP.
