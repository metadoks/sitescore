# SiteScore AI — Reviewer → Implementer Handoff

## CONTROL HEADER

```text
HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: REVIEWER CHAT
CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-6
CHECKPOINT_TITLE: Feature-Specific Normalization + Compatibility
REVIEWER_STATE: READY_TO_LOCK
IMPLEMENTER_ACTION: LOCK_IF_USER_AUTHORIZED
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: 530869a06fd5e1a64357701fff3f226d70ac6d1d
CODE_BRANCH: faz3.4/cp3.4-6-feature-normalization-compatibility
REVIEWED_HEAD_SHA: 7b8e4594ba3e58b31ae5163960220832e28b4970
PR: #3
CONTRACT_CHANGE_REQUIRED: 0
```

---

# 1. REVIEW DECISION

```text
FAZ 3.4 — CHECKPOINT 3.4-6
Decision: READY TO LOCK
Repository: metadoks/sitescore
PR: #3
Base: 530869a06fd5e1a64357701fff3f226d70ac6d1d
Reviewed HEAD: 7b8e4594ba3e58b31ae5163960220832e28b4970
```

Acceptance is SHA-specific. `READY_TO_LOCK` is not `LOCKED`.

Do not merge until the user explicitly sends `LOCK` to the Implementer chat.

Do not start checkpoint 3.4-7 during the LOCK transition.

---

# 2. INDEPENDENT REVIEW SCOPE

Reviewer independently inspected the current `implementer.md`, PR #3 metadata and changed-file set, full load-bearing `normalization.py`, normalization regressions and lineage tests, locked 3.4-4 compatibility/distribution semantics, locked 3.4-5 ECDF semantics, validation commit-to-final-HEAD comparison, and GitHub Actions validation state.

No decision is based solely on Implementer claims.

---

# 3. VERIFIED NORMALIZATION SEMANTICS

Canonical direct V1 mappings are correctly frozen:

```text
walkable_population -> walkable_population_score -> 100 * P
target_population_density -> target_population_density_score -> 100 * P
competition_pressure -> competition_opportunity_score -> 100 * (1-P)
walkable_reach_area_km2 -> walkable_reach_area_score -> 100 * P
transit_service_departure_equivalents_per_hour -> transit_access_score -> 100 * P
household_income -> household_income_score -> 100 * P
```

Direction comes from canonical versioned policies. The domain `normalize_feature` path does not accept caller-supplied percentile, score, invert flag, direction, or compatibility assertion.

No second ECDF implementation exists; available domain normalization delegates to locked `MID_ECDF_V1`.

---

# 4. SITE NUMERIC GATE — VERIFIED

The actual `DerivedMetricMeasurement` with `SubjectKind.SITE` is the query authority.

Available direct normalization requires the actual nested `MetricValue` to have:

```text
value != None
availability == AVAILABLE
score_eligibility == ELIGIBLE
calibration_state == CALIBRATED
finite numeric value
```

Missing, unavailable, ineligible, uncalibrated, or invalid numeric SITE inputs do not receive a percentile or score. No missing→0, unresolved→0, or generic neutral fallback exists.

---

# 5. SITE ↔ BENCHMARK COMPATIBILITY — VERIFIED

Compatibility is derived from actual SITE measurement and actual `BenchmarkDistributionArtifact` objects.

Exact compared dimensions include:

```text
MetricDefinition identity
MetricDerivationPolicy identity
MeasurementPrecisionPolicy identity
unit
actual measurement method_version
metric-specific source_bundle_compatibility
```

Metric key equality alone is not authority.

Benchmark state must be `AVAILABLE`; unavailable/no-observation/incompatible distributions cannot emit a normalized score.

Per-observation/source refs are retained as provenance but are not incorrectly required to be identical across site and benchmark populations.

---

# 6. TRANSIT / COMPETITION LINEAGE — VERIFIED

Transit requires exact equality of:

```text
transit_source_bundle_fingerprint
```

Cross-bundle SITE/benchmark inputs are explicitly incompatible and receive no score.

Competition compatibility preserves exact:

```text
competition_measurement_definition_id
```

The structural competition direction `100*(1-P)` exists, while canonical `competition_pressure` remains unresolved/nonnumeric. No reduction was fabricated merely to create a score.

---

# 7. AGE FALLBACK — VERIFIED UNIQUE EXCEPTION

The only neutral fallback is the dedicated age contract:

```text
feature: age_target_concentration_score
score: 50
unit: score_0_100
availability: available
score eligibility: eligible
calibration: uncalibrated
proxy: true
reason: age_affinity_not_calibrated
method: age_neutral_fallback/1.0
```

The fallback builder is not generic and policy construction rejects retargeting to another feature. Non-age missing features never inherit this fallback.

---

# 8. COMB-005 / LATER-SCOPE BOUNDARY — VERIFIED

No direct normalized policy exists for raw road or parking metrics.

Checkpoint 3.4-6 does not emit `road_parking_access_score` and does not introduce:

```text
road-only substitution
parking-only substitution
50/50 composition
missing-side neutral 50
available-side renormalization
road/parking weights
```

COMB-005 remains checkpoint 3.4-7 scope.

No whole `NormalizedLocationFeatures` assembly, ScoringReadiness, RealDataPipelineResult orchestration, CategoryScores, Location Score, or `core.analyze()` was introduced.

---

# 9. IDENTITY / ANTI-SELF-ASSERTION — VERIFIED

Feature normalization policy identity binds canonical metric definition/policy, normalized feature target, direction, ECDF policy, numeric comparison policy, and compatibility rule.

Compatibility identity binds actual SITE measurement identity, benchmark distribution identity, derived site/benchmark compatibility identities, state and reasons.

Normalization-result identity binds actual SITE measurement, actual benchmark distribution, compatibility decision, normalization policy, ECDF evaluation, state/reasons, percentile and score.

No detached caller ID, score, percentile, or compatible flag is authoritative.

---

# 10. DEPENDENCY / FROZEN PACKAGE REVIEW

Only `sitescore-benchmarks` changed in PR #3.

No dependency metadata changed. Existing direct runtime dependencies remain:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

No direct core/data/providers/pipeline dependency or reverse metrics→benchmarks edge was introduced. Frozen upstream package source remains unchanged.

`CONTRACT_CHANGE_REQUIRED = 0`.

---

# 11. TEST / VALIDATION STATUS

GitHub Actions independently verified:

```text
workflow: cp346-validation
run id: 31905150049
validated commit: d0fe64d5bf34bdbb4fb1acce53535b211e0cc0c3
conclusion: SUCCESS
```

Visible job steps show successful execution of all six package suites:

```text
sitescore-benchmarks
sitescore-metrics
sitescore-spatial
sitescore-providers
sitescore-data
sitescore-core
```

Reported exact changed-package counts include:

```text
sitescore-benchmarks: 169/169 PASS
sitescore-metrics: 67/67 PASS
```

Reviewer independently compared validated commit `d0fe64d5...` to final review HEAD `7b8e4594...` and verified that the only change is deletion of the temporary branch-only validation workflow:

```text
.github/workflows/cp346-validation.yml
```

Therefore reviewed source/tests/docs equal the successfully validated source/tests/docs.

---

# 12. REVIEW CONCLUSION

No reproducible production correctness blocker remains within checkpoint 3.4-6 scope at reviewed HEAD.

```text
FAZ 3.4-6: READY TO LOCK
REVIEWED_HEAD_SHA: 7b8e4594ba3e58b31ae5163960220832e28b4970
PR: #3
CONTRACT_CHANGE_REQUIRED: 0
```

---

# 13. USER-AUTHORIZED LOCK INSTRUCTION

Only if the user explicitly sends:

```text
LOCK
```

the Implementer may perform the transition.

Immediately before merge, re-fetch PR #3 and verify:

```text
current PR HEAD == 7b8e4594ba3e58b31ae5163960220832e28b4970
PR base == main
PR is open
main remains compatible with expected base
CONTRACT_CHANGE_REQUIRED == 0
```

If current HEAD differs, do not merge. Record:

```text
IMPLEMENTER_STATE: LOCK_BLOCKED_REVIEW_STALE
```

and return for Reviewer re-review.

If exact reviewed SHA is current and the user explicitly authorized `LOCK`, merge PR #3 using expected-head-SHA protection when available and update `implementer.md` with at minimum:

```text
IMPLEMENTER_STATE: LOCKED
CHECKPOINT: FAZ 3.4-6
REVIEWED_HEAD_SHA: 7b8e4594ba3e58b31ae5163960220832e28b4970
PR: #3
MERGED_MAIN_SHA: <actual merge/main SHA>
LOCK_TRANSITION_STATUS: SUCCESS
TAG: <actual tag / PENDING / NOT REQUIRED>
```

Do not start 3.4-7 during the LOCK transition. After successful LOCK, stop and wait for the user to send `devam` to Reviewer.
