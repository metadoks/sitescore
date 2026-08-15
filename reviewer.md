# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-8
CHECKPOINT_TITLE: Scoring Readiness + RealDataPipelineResult Integration
REVIEWER_STATE: IMPLEMENTATION_REQUESTED
IMPLEMENTER_ACTION: IMPLEMENT
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: c8514401f1b9e2a671c00477219f6f930a594bc8
CODE_BRANCH: faz3.4/cp3.4-8-readiness-pipeline
REVIEWED_HEAD_SHA: NONE
PR: NONE
CONTRACT_CHANGE_REQUIRED_EXPECTATION: 0
```

---

# 1. PREVIOUS CHECKPOINT LOCK VERIFICATION

FAZ 3.4-7 is accepted, user-authorized and merged.

Reviewer independently verified:

```text
PR #4 state: closed
PR #4 merged: true
reviewed branch HEAD: bff973bbf2ddacc2967eb6d8f35b4307fa00003c
merge/main SHA: c8514401f1b9e2a671c00477219f6f930a594bc8
```

Current `main` points exactly to:

```text
c8514401f1b9e2a671c00477219f6f930a594bc8
```

No checkpoint 3.4-8 branch existed at publication time.

Create exactly one branch from this baseline:

```text
faz3.4/cp3.4-8-readiness-pipeline
```

Re-fetch repository state before work. Do not reset legitimate work or create duplicate branches.

---

# 2. CHECKPOINT PURPOSE

Implement only:

```text
FAZ 3.4 — CHECKPOINT 3.4-8
Scoring Readiness + RealDataPipelineResult Integration
```

This is the terminal checkpoint of the FAZ 3.4 implementation chain before FAZ 3.4-FINAL audit.

The target semantic flow is:

```text
locked provider/spatial/metric artifacts
+
locked benchmark distributions / normalization results
+
locked age fallback
+
locked COMB-005 current unavailable state
→
honest NormalizedLocationFeatures assembly
→
ScoringReadinessResult
→
RealDataPipelineResult
```

Critical invariant:

```text
required evidence/feature unavailable, incompatible, ineligible or uncalibrated
→ NOT_SCORE_READY
→ no CategoryScores
→ no core analyze()
```

The only frozen exception is the explicit age neutral fallback contract.

This checkpoint is an integration/readiness boundary, not category scoring.

---

# 3. PACKAGE / DAG OWNERSHIP

Current repo has no `sitescore-pipeline` package yet.

The frozen DAG from FAZ 3.4-0 permits a later pipeline layer consuming:

```text
sitescore-data
sitescore-providers
sitescore-metrics
sitescore-benchmarks
```

and application code later consuming pipeline/data/core.

Preferred implementation is a new additive package:

```text
sitescore-pipeline
```

with exact pinned internal dependencies as needed, and no reverse dependency from any frozen upstream package.

Do not modify frozen `sitescore-data`, `sitescore-core`, `sitescore-providers`, `sitescore-spatial`, or `sitescore-metrics` source merely for convenience.

Do not make `sitescore-benchmarks` import pipeline.

If a new pipeline package is created, establish minimal package metadata, tests, README/docs and architecture guards consistent with repository conventions.

If correct additive implementation is genuinely impossible under the frozen DAG/contracts, stop and report:

```text
CONTRACT_CHANGE_REQUIRED = 1
```

with exact evidence before altering frozen contracts.

Expected result remains `0`.

---

# 4. FROZEN DATA CONTRACTS ARE TARGET CONTRACTS, NOT EDIT TARGETS

The frozen `sitescore-data` already defines:

```text
NormalizedLocationFeatures
ScoringReadinessResult
ScoringFeatureReadiness
FeatureReadinessPolicy
ReadinessCompatibilityInput
ApprovedFallbackPolicyRef
RealDataPipelineResult
PipelineStatus
```

Use those actual frozen contracts.

Do not fork/redefine lookalike versions in pipeline unless a small adapter-owned intermediate artifact is genuinely required.

Do not weaken constructor invariants in frozen data schemas.

`RealDataPipelineResult` explicitly defines:

```text
SCORE_READY != SCORED
```

and category aggregation is not owned there.

Preserve that boundary exactly.

---

# 5. EIGHT REQUIRED NORMALIZED FEATURE SLOTS

The frozen V1 normalized surface contains exactly:

```text
walkable_population_score
target_population_density_score
age_target_concentration_score
competition_opportunity_score
walkable_reach_area_score
transit_access_score
road_parking_access_score
household_income_score
```

All eight are required by the frozen readiness contract.

Do not silently drop unavailable slots.
Do not renormalize the model onto available features.
Do not represent missing/unresolved slots as neutral 50 or zero.

The assembly layer must preserve a `MetricValue` for each frozen slot with honest state semantics, even when numeric value is unavailable.

---

# 6. DIRECT NORMALIZATION RESULTS → MetricValue ADAPTATION

Checkpoint 3.4-6 provides individual `FeatureNormalizationResult` artifacts for six direct feature mappings.

For each direct feature, adaptation into the frozen normalized `MetricValue` must be derived from the actual normalization artifact, not caller-supplied score/state strings.

When `FeatureNormalizationResult.state == AVAILABLE`:

```text
value = actual result.score
unit = score_0_100
availability = AVAILABLE
score_eligibility = ELIGIBLE
calibration_state = CALIBRATED
```

with source/method/reason/lineage fields derived deterministically from actual nested measurement/benchmark/normalization semantics.

When a normalization result is not available, the adapter must not fabricate a numeric score. Preserve the appropriate unavailable/ineligible/uncalibrated/incompatible semantics in `MetricValue`.

Do not convert a 3.4-6 failure reason into an unrelated data-quality claim unless contractually justified.

---

# 7. AGE FALLBACK — UNIQUE APPROVED EXCEPTION

The only allowed numeric uncalibrated feature is the locked 3.4-6 age fallback:

```text
feature = age_target_concentration_score
value = 50
unit = score_0_100
availability = AVAILABLE
score_eligibility = ELIGIBLE
calibration_state = UNCALIBRATED
is_proxy = true
reason = age_affinity_not_calibrated
method semantic = age_neutral_fallback/1.0
```

Readiness must accept this only when an actual trusted/approved fallback identity proves the exact frozen age fallback policy.

Do not trust only caller-provided:

```text
fallback_policy_id="age_neutral_fallback"
version="1.0"
```

without binding to actual locked age fallback authority.

No other feature may use this exception.

---

# 8. ROAD/PARKING SLOT — CURRENT CANONICAL RESULT MUST BLOCK READINESS

Checkpoint 3.4-7 froze the current canonical COMB-005 state:

```text
no approved empirical policy
COMB005_V1_POLICY = NOT_APPROVED
approved registry = empty
canonical composite score = None
```

Therefore current canonical:

```text
road_parking_access_score
```

must be represented honestly as unavailable/non-numeric and must block score readiness with the frozen readiness reason:

```text
ROAD_PARKING_COMPOSITE_UNAVAILABLE
```

Do not invent production COMB weights or an AVAILABLE road/parking feature merely to construct a SCORE_READY happy path.

A synthetic/private readiness test may construct controlled complete feature fixtures to validate generic readiness logic, but production canonical integration must remain NOT_SCORE_READY while COMB-005 remains unapproved and other canonical upstream metrics remain unresolved.

---

# 9. COMPETITION / TRANSIT COMPATIBILITY MUST SURVIVE INTO READINESS

The frozen normalized surface includes compatibility lineage fields:

```text
competition_measurement_definition_id
competition_normalization_policy_version
transit_source_bundle_fingerprint
transit_normalization_policy_version
```

Readiness must not accept detached caller values as compatibility truth where actual 3.4-6 normalization/benchmark lineage exists.

For competition, exact measurement definition compatibility remains required.

For transit, exact source bundle fingerprint compatibility remains required.

Mismatch must produce the frozen readiness reasons:

```text
COMPETITION_MEASUREMENT_MISMATCH
TRANSIT_SOURCE_BUNDLE_MISMATCH
```

Do not let an available numeric score override incompatible lineage.

---

# 10. READINESS SEMANTICS

All eight V1 feature slots are required.

Ordinary feature readiness requires, structurally:

```text
availability == AVAILABLE
score_eligibility == ELIGIBLE
calibration_state == CALIBRATED
acceptable data quality
required normalization/composite policy configured and version-compatible
required compatibility lineage satisfied
```

Age is the sole exception described above.

A required feature must block readiness for any applicable condition including:

```text
missing/unavailable
ineligible
diagnostic-only
uncalibrated without approved age fallback
insufficient data quality
policy not configured
policy version mismatch
competition compatibility mismatch
transit bundle mismatch
road/parking composite unavailable
```

Use the existing frozen `ScoringReadinessReason` taxonomy; do not invent semantically duplicate reason strings if the frozen enum already expresses the state.

---

# 11. READINESS MUST BE DERIVED, NOT CALLER-ASSERTED

The canonical readiness validator/factory must consume actual normalized features plus actual resolved policy/compatibility authority and derive:

```text
feature_states
missing_required_features
uncalibrated_features
insufficient_quality_features
incompatible_features
reason_codes
is_score_ready
required_policy_versions
resolved_policy_versions
readiness_fingerprint
```

Do not expose a canonical production constructor/factory where callers can simply pass:

```text
is_score_ready=True
readiness_fingerprint="..."
```

and bypass derivation.

The frozen data DTO constructor necessarily exists, but the pipeline-owned production path must be anti-self-asserting and tests must prove callers cannot make canonical readiness true by supplying detached booleans/summary arrays.

The readiness fingerprint must be deterministically derived from the actual normalized feature surface, policy/version resolution, compatibility authority, feature states and validator semantics. `evaluated_at` should not silently become semantic identity unless explicitly intended by frozen contract.

---

# 12. DATA QUALITY

Honor the existing `DataQualityState` semantics rather than assuming every AVAILABLE value is sufficient.

Determine from frozen data enums/validators which quality states are acceptable for readiness. Do not invent a production threshold or numeric quality score.

Age fallback quality handling must remain consistent with its explicitly approved proxy semantics; do not accidentally reject the frozen exception solely because it is proxy/uncalibrated if the approved fallback authority is valid.

---

# 13. NORMALIZED FEATURE ASSEMBLY AUTHORITY

Create one canonical pipeline-owned assembly path for `NormalizedLocationFeatures` from actual 3.4-6/3.4-7 artifacts and upstream provenance.

Do not make the caller directly supply eight arbitrary `MetricValue` objects as the canonical production integration path and call that “assembled”.

Controlled low-level helpers may exist, but production assembly should prove where each slot came from.

At minimum bind/preserve:

- six direct feature normalization artifact identities;
- actual age fallback identity;
- actual COMB-005 result/policy identity;
- competition benchmark/measurement-definition lineage;
- transit benchmark/source-bundle lineage;
- source refs;
- normalization policy versions;
- feature contract version.

If a direct feature is structurally unresolved upstream, assemble an honest nonnumeric MetricValue for that slot, not a fake score.

---

# 14. CURRENT CANONICAL PRODUCTION TRUTH IS EXPECTED TO BE NOT_SCORE_READY

Do not treat lack of a production SCORE_READY end-to-end example as implementation failure.

Given current frozen unresolved/calibration-gated states, canonical real-data integration is expected to be capable of ending:

```text
PipelineStatus.NOT_SCORE_READY
```

with complete typed evidence and readiness reasons.

This is correct architecture.

Do not modify unresolved metric contracts, benchmark rules, or COMB-005 to force a production SCORE_READY sample.

---

# 15. RealDataPipelineResult TERMINAL ENVELOPE

Build a canonical pipeline-owned factory/builder that creates the frozen `RealDataPipelineResult` from actual artifacts and the derived readiness result.

Preserve frozen status semantics:

## SCORE_READY

Requires:

```text
resolved_location present
normalized_features present
scoring_readiness present
scoring_readiness.is_score_ready == True
reason_codes == ()
```

It means downstream application aggregation/scoring is permitted, not already performed.

## NOT_SCORE_READY

Requires:

```text
scoring_readiness present
is_score_ready == False
pipeline reason = SCORING_NOT_READY
```

Retain upstream evidence; do not null everything just because scoring is blocked.

## PIPELINE_ERROR

Represents execution/stage failure, not ordinary missing/unready evidence.
It must not contain a scoring readiness result under the frozen DTO contract.

Do not misuse `PIPELINE_ERROR` for ordinary unavailable competition, road, benchmark or feature evidence that should instead end in NOT_SCORE_READY.

---

# 16. PIPELINE STATUS MUST BE DERIVED

Canonical terminal factory must derive pipeline status from actual execution outcome/readiness, not accept arbitrary caller status as production authority.

At minimum:

```text
successful pipeline stages + readiness true  -> SCORE_READY
successful pipeline stages + readiness false -> NOT_SCORE_READY
actual stage execution failure                -> PIPELINE_ERROR
```

Do not allow detached `status=SCORE_READY` to bypass readiness.

---

# 17. NO CATEGORY / CORE SCORING

This checkpoint must stop before category aggregation.

Do not create or compute:

```text
Demand score
Competition category score
Accessibility category score
Economics category score
CategoryScores
base Location Score
dealbreaker penalties
final Location Score
Decision Layer
core.analyze()
ReadyCategoryScorePayload as computed aggregation output
```

`SCORE_READY` is permission to proceed later, not scoring itself.

Architecture/source guards should enforce absence of `sitescore-core` import in pipeline if core is not needed for readiness.

---

# 18. POLICY VERSION COHERENCE

The frozen readiness contract carries required and resolved policy versions.

The canonical implementation must derive these from actual locked normalization/fallback/composite policy authorities, not free-form caller strings.

Mismatch must block readiness with:

```text
POLICY_VERSION_MISMATCH
```

Missing required policy authority must block with:

```text
POLICY_NOT_CONFIGURED
```

For currently unapproved COMB-005, do not misrepresent `UNAPPROVED_V1` as an approved resolved normalization policy version enabling readiness.

---

# 19. SOURCE / PROVENANCE PRESERVATION

`NormalizedLocationFeatures.source_refs` must cover nested normalized MetricValue/benchmark references according to the frozen schema.

`RealDataPipelineResult.source_metadata` must obey its frozen deterministic/unique source-id rules.

Do not pretend every opaque `source_ref` is necessarily a `SourceMetadata.source_id`; the frozen pipeline contract explicitly says these namespaces are not universally identical.

Preserve typed artifact references and actual lineage rather than inventing a universal source registry.

---

# 20. DETERMINISM / IDENTITY

The canonical readiness fingerprint and any new pipeline assembly identity should be deterministic for identical semantic inputs.

Semantic changes that must affect identity/fingerprint include as applicable:

```text
feature value/state/quality/eligibility/calibration
normalization artifact identity
benchmark compatibility identity
policy version/authority
age fallback authority
COMB-005 state/policy identity
transit bundle identity
competition measurement definition identity
```

Incidental ordering, timestamps, filesystem paths, worker execution order and object allocation must not silently alter semantic identity.

Canonicalize collection ordering before hashing.

---

# 21. REQUIRED ADVERSARIAL TEST MATRIX

Add tests at minimum for:

## READY-001 — all eight slots required
Removing/unavailable any ordinary required slot blocks readiness.

## READY-002 — no missing neutralization
Missing direct feature cannot become 0 or 50.

## READY-003 — uncalibrated ordinary feature blocks
AVAILABLE + ELIGIBLE + numeric but UNCALIBRATED ordinary feature -> NOT ready.

## READY-004 — age exception accepted only exactly
Exact locked age fallback with actual approved authority can pass its slot despite UNCALIBRATED.

## READY-005 — age exception cannot leak
Same 50/proxy/uncalibrated shape on transit/income/etc. does not pass readiness.

## READY-006 — competition mismatch
Mismatched competition measurement definition blocks readiness.

## READY-007 — transit mismatch
Mismatched transit source bundle fingerprint blocks readiness.

## READY-008 — COMB-005 unavailable
Current canonical road/parking composite produces unavailable road_parking slot and blocks readiness with `ROAD_PARKING_COMPOSITE_UNAVAILABLE`.

## READY-009 — policy missing
Required policy not configured blocks readiness.

## READY-010 — policy version mismatch
Required vs actual resolved normalization policy version mismatch blocks readiness.

## READY-011 — insufficient quality
Structurally insufficient data-quality state blocks readiness without numeric substitution.

## READY-012 — readiness anti-self-assertion
Canonical validator exposes no caller `is_score_ready` / detached fingerprint authority.

## PIPE-001 — readiness false -> NOT_SCORE_READY
Canonical terminal factory produces frozen NOT_SCORE_READY status and `SCORING_NOT_READY` reason.

## PIPE-002 — readiness true fixture -> SCORE_READY
Controlled structurally valid complete fixture may prove generic terminal status semantics without changing canonical unresolved production state.

## PIPE-003 — SCORE_READY != SCORED
No CategoryScores/core result exists in SCORE_READY terminal envelope.

## PIPE-004 — ordinary unready evidence is not pipeline error
Missing/unresolved benchmark/feature evidence that reaches readiness must terminate NOT_SCORE_READY, not PIPELINE_ERROR.

## PIPE-005 — stage failure -> PIPELINE_ERROR
Explicit pipeline-stage execution failure produces PIPELINE_ERROR and no scoring_readiness object.

## PIPE-006 — status anti-self-assertion
Canonical production factory cannot be forced to SCORE_READY by caller-supplied status.

## PIPE-007 — lineage/version mismatch rejection
Frozen DTO coherence for feature contract, transit bundle and competition definition remains enforced through canonical assembly.

## PIPE-008 — deterministic readiness fingerprint
Same semantics -> same fingerprint; meaningful policy/feature/compatibility change -> different fingerprint.

## SCOPE-001
No category aggregation, Location Score, dealbreaker or `core.analyze()` implementation.

---

# 22. TEST / REGRESSION REQUIREMENTS

Run all relevant suites including at minimum:

```text
sitescore-pipeline (if created)
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

If a new package is created, include architecture/dependency tests proving the intended DAG and no reverse imports.

Report exact test counts only where actually visible.

If a temporary validation workflow is used, remove it before final review HEAD and prove successful validated SHA → final HEAD is workflow-removal-only.

Do not modify frozen upstream package source to make new integration tests pass.

---

# 23. DOCUMENTATION REQUIREMENTS

Document at minimum:

- 3.4-8 ownership and package boundary;
- eight-slot frozen normalized surface;
- direct normalization adaptation semantics;
- unique age fallback exception;
- current COMB-005 unavailable effect on readiness;
- competition/transit compatibility;
- readiness gates/reasons;
- policy-version authority;
- RealDataPipelineResult status semantics;
- `SCORE_READY != SCORED`;
- current canonical production may legitimately remain NOT_SCORE_READY;
- no category/core scoring in this checkpoint;
- dependency DAG;
- validation evidence.

Do not claim empirical calibration is complete.

---

# 24. STOP CONDITION / HANDOFF

When implementation is complete:

1. commit/push only the 3.4-8 branch;
2. open exactly one PR against `main`;
3. do not merge;
4. replace `implementer.md` with detailed implementation/test/self-audit report;
5. report actual base/head SHA and PR number;
6. report `CONTRACT_CHANGE_REQUIRED` truthfully.

Expected handoff header:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
CHECKPOINT: FAZ 3.4-8
CHECKPOINT_TITLE: Scoring Readiness + RealDataPipelineResult Integration
BASE_SHA: c8514401f1b9e2a671c00477219f6f930a594bc8
CODE_BRANCH: faz3.4/cp3.4-8-readiness-pipeline
CODE_HEAD_SHA: <exact SHA>
PR: #<N>
CONTRACT_CHANGE_REQUIRED: 0
```

Do not self-LOCK.
Do not begin FAZ 3.4-FINAL.
