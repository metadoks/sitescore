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
REVIEWER_STATE: HARDENING_REQUIRED
IMPLEMENTER_ACTION: HARDEN
LOCK_AUTHORITY: USER_ONLY
EXPECTED_BASE_BRANCH: main
EXPECTED_BASE_SHA: c8514401f1b9e2a671c00477219f6f930a594bc8
CODE_BRANCH: faz3.4/cp3.4-8-readiness-pipeline
REVIEWED_HEAD_SHA: cd7229fe7d241c6101782ff7b8baed49ac63edef
PR: #5
CONTRACT_CHANGE_REQUIRED: 0
```

---

# 1. REVIEW DECISION

```text
FAZ 3.4-8
Decision: HARDENING REQUIRED
PR: #5
Reviewed HEAD: cd7229fe7d241c6101782ff7b8baed49ac63edef
```

The package/DAG shape, frozen DTO reuse, canonical six-direct-feature assembly path, age fallback binding, COMB-005 unavailability, readiness reason taxonomy, and terminal status mapping are directionally correct. Two production authority/coherence blockers remain.

No merge or LOCK is authorized.

---

# 2. VERIFIED CLEAN AREAS

Reviewer independently verified at the reviewed HEAD:

- new package is additive `sitescore-pipeline==0.1.0`;
- direct runtime dependencies are exactly `sitescore-data==0.1.0` and `sitescore-benchmarks==0.1.0`;
- no `sitescore-core` dependency/import is introduced;
- no frozen upstream source changed;
- six direct feature mappings are assembled from actual `FeatureNormalizationResult` artifacts;
- exact locked age fallback authority is used in the production assembly path;
- current COMB-005 remains unavailable/non-numeric and therefore blocks canonical readiness;
- competition/transit compatibility is carried into the frozen readiness validator;
- `derive_scoring_readiness()` does not accept caller `is_score_ready`, summaries or readiness fingerprint;
- `build_real_data_pipeline_result()` does not accept caller terminal status;
- ordinary unready evidence maps to `NOT_SCORE_READY`, not `PIPELINE_ERROR`;
- no CategoryScores, category weighting, Location Score, dealbreakers, Decision Layer or `core.analyze()` is implemented;
- GitHub Actions run `31908253093` completed successfully at validated SHA `57bef6d47631ad97abccb1f430d0c348c7a13ad1`;
- validated SHA → reviewed HEAD differs only by removal of `.github/workflows/cp348-validation.yml`.

The blockers below are narrowly scoped to canonical authority and terminal artifact coherence.

---

# 3. PIPE-H001 — CANONICAL ASSEMBLY / READINESS AUTHORITY IS FORGEABLE THROUGH MODULE-LEVEL TOKEN PATH

## Problem

`NormalizedFeatureAssembly` is a public package export, while its constructor gate relies on module-global `_ASSEMBLY_TOKEN` and `_assembly_identity`.

The production module exposes those private names to normal Python imports through:

```python
import sitescore_pipeline.integration as integration
integration._ASSEMBLY_TOKEN
integration._assembly_identity
```

The checkpoint tests themselves use exactly this path to construct an arbitrary `NormalizedFeatureAssembly` from caller-authored:

```text
NormalizedLocationFeatures
FeatureReadinessPolicy tuple
ReadinessCompatibilityInput
ApprovedFallbackPolicyRef tuple
artifact identities
```

and then pass that forged assembly into `derive_scoring_readiness()`.

That controlled fixture currently produces `is_score_ready=True` even though it did not come from `assemble_normalized_location_features()` and is not backed by the six actual 3.4-6 normalization results, locked age artifact and 3.4-7 result required by the production flow.

Therefore the current anti-self-assertion boundary is not constructive: callers can reproduce the same token/hash path used by tests and manufacture a pipeline-recognized "canonical" assembly/readiness object.

This violates the frozen requirements:

```text
production assembly should prove where each slot came from
readiness must be derived from actual normalized feature artifacts
callers must not make canonical readiness true with detached feature/policy/compatibility inputs
```

## Required correction

Make production `NormalizedFeatureAssembly` / `ReadinessEvaluation` constructively factory-owned rather than protected only by importable module-global sentinel/hash helpers.

Acceptable additive patterns include:

- make the public object itself non-directly-constructible by ordinary production callers and construct it only through a private closure/factory capability that is not obtainable from module namespace; or
- stop exporting the factory-owned intermediate class and use an internal implementation object whose creation capability cannot be reconstructed from public/module-level inputs; or
- redesign `derive_scoring_readiness()` so it consumes a provenance-complete artifact returned by canonical assembly and verifies actual nested artifact objects/identities, rather than trusting a caller-built wrapper plus an importable token.

Do **not** fix this by merely renaming `_ASSEMBLY_TOKEN` or `_assembly_identity`; underscore convention is not authority.

Controlled readiness tests may still exercise the frozen validator directly or use a clearly test-local synthetic object, but must not demonstrate a production bypass path through the same module-level token used by canonical runtime.

## Required regressions

Add adversarial tests proving that an ordinary caller using importable production/module symbols cannot:

1. construct a pipeline-recognized `NormalizedFeatureAssembly` from arbitrary `NormalizedLocationFeatures` / policies / compatibility;
2. construct a pipeline-recognized `ReadinessEvaluation` from detached `ScoringReadinessResult`;
3. produce canonical `is_score_ready=True` without going through actual canonical assembly artifacts;
4. reproduce canonical authority by importing an underscore token/hash helper.

Retain a controlled SCORE_READY test only through an explicitly non-production/test-local validator fixture or a future genuinely canonical complete artifact path.

---

# 4. PIPE-H002 — TERMINAL `derived_metrics` IS NOT COHERENT WITH THE NORMALIZATION/READINESS ARTIFACTS

## Problem

`build_real_data_pipeline_result()` accepts a caller-supplied `DerivedLocationMetrics` object independently from the `ReadinessEvaluation`.

Current validation checks only:

```text
derived_metrics is DerivedLocationMetrics
feature_contract_version coherence
```

It does not verify that the real-unit metric values/lineage in `derived_metrics` are the same actual site measurements that produced the six `FeatureNormalizationResult` artifacts underlying `readiness.assembly.features`.

The current controlled SCORE_READY test demonstrates the gap: readiness is made true from an arbitrary complete normalized feature fixture while `derived_metrics` contains UNKNOWN/UNCALIBRATED placeholder values for every real-unit metric, yet `build_real_data_pipeline_result()` still returns `SCORE_READY`.

Thus the terminal envelope can claim:

```text
SCORE_READY
```

while simultaneously carrying a contradictory/unrelated real-unit `DerivedLocationMetrics` surface.

This violates the checkpoint target flow and terminal-envelope requirement:

```text
actual metric artifacts -> normalized artifacts -> readiness -> RealDataPipelineResult
```

and the requirement to build the terminal result from actual coherent artifacts rather than merely type-compatible DTOs.

## Required correction

Bind terminal `derived_metrics` to the actual site measurement lineage used by canonical normalization/readiness.

At minimum, for every direct normalized feature that originates from a `DerivedMetricMeasurement`, the terminal factory must prove semantic coherence between:

```text
readiness canonical assembly's actual site measurement
and
corresponding field in DerivedLocationMetrics
```

The check should cover the actual nested `MetricValue` semantics that matter to identity/correctness, including as applicable:

```text
value
unit
availability
data quality
score eligibility
calibration state
estimate/proxy flags
source refs
method version
reason codes
```

Do not rely on feature-contract version alone.

Preferred design: retain actual direct normalization/site-measurement objects inside the canonical assembly/provenance envelope and validate/adapt `DerivedLocationMetrics` against them before terminal construction. If an even stronger canonical builder can derive the relevant `DerivedLocationMetrics` fields directly from actual measurements without mutating frozen data contracts, that is also acceptable.

For real-unit fields not represented by the six direct normalization results, preserve their supplied frozen DTO values honestly, but do not permit contradictions on overlapping metrics.

A SCORE_READY controlled fixture must not pair normalized scores with unrelated/UNKNOWN derived metrics for the same underlying direct metrics.

## Required regressions

Add tests proving terminal construction rejects at least:

- household-income normalized result derived from site measurement A + `DerivedLocationMetrics.household_income` from different measurement/value/method;
- transit normalized result + contradictory transit real-unit MetricValue/source lineage;
- walkable reach normalized result + contradictory real-unit MetricValue;
- a controlled `SCORE_READY` readiness artifact paired with all-UNKNOWN placeholder `DerivedLocationMetrics` on overlapping direct metrics.

Also verify semantically coherent overlapping metrics are accepted.

---

# 5. SIBLING / SCOPE REQUIREMENTS

While fixing PIPE-H001/H002, preserve all clean 3.4-8 behavior:

- eight-slot frozen feature surface;
- no missing/neutral substitution;
- exact age fallback exception only;
- COMB-005 remains unavailable and blocks current canonical production readiness;
- competition measurement-definition mismatch blocks;
- transit bundle mismatch blocks;
- readiness fingerprint remains semantic and timestamp-independent;
- `NOT_SCORE_READY` remains distinct from `PIPELINE_ERROR`;
- `SCORE_READY != SCORED`;
- no category/core scoring;
- no frozen upstream source mutation;
- no reverse dependency;
- no empirical policy invention.

Do not broaden into FAZ 3.4-FINAL.

`CONTRACT_CHANGE_REQUIRED` should remain `0` if corrected additively. If genuinely impossible, stop and report exact evidence before changing frozen contracts.

---

# 6. VALIDATION / RETURN REQUIREMENTS

After hardening:

1. keep work on the same branch and PR #5;
2. run `sitescore-pipeline`, `sitescore-benchmarks`, `sitescore-metrics`, `sitescore-spatial`, `sitescore-providers`, `sitescore-data`, and `sitescore-core` regression suites;
3. report exact counts only where actually visible;
4. add public/module-level authority-bypass regressions for PIPE-H001;
5. add real-unit/normalized terminal coherence regressions for PIPE-H002;
6. update README/checkpoint docs to describe true canonical construction authority and terminal coherence;
7. if using a temporary validation workflow, remove it and prove successful validated SHA → final HEAD is workflow-removal-only;
8. replace `implementer.md` with detailed hardening evidence.

Return with:

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
CHECKPOINT: FAZ 3.4-8
PR: #5
CODE_HEAD_SHA: <new exact SHA>
PIPE-H001: RESOLVED / unresolved with evidence
PIPE-H002: RESOLVED / unresolved with evidence
CONTRACT_CHANGE_REQUIRED: 0 or exact justified 1
```

Do not merge. Do not self-LOCK. Do not start FAZ 3.4-FINAL.
