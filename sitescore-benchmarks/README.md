# sitescore-benchmarks

Provider-neutral benchmark frame, measurement-population, coverage, raw real-unit distribution, generic mid-ECDF, feature-specific normalization/compatibility, and COMB-005 gating contracts for SiteScore FAZ 3.4.

Checkpoint 3.4-2 remains the locked commercial equal-area frame foundation. Checkpoint 3.4-4 binds complete eligible frame-cell populations to the locked `sitescore-metrics` measurement semantics, derives coverage from actual attempts, preserves compatibility lineage, and produces raw real-unit benchmark observations. Checkpoint 3.4-5 defines finite canonical numeric samples, a separate exact/no-tolerance ECDF comparison policy, and the frozen generic mid-ECDF formula returning percentiles in `[0, 1]`.

Checkpoint 3.4-6 binds actual SITE measurements to actual compatible benchmark distributions before applying canonical feature direction: ordinary direct features use `100 * P`, while competition opportunity is structurally defined as `100 * (1 - P)`. It also defines the unique frozen age neutral fallback foundation (`50`, proxy, uncalibrated, `age_affinity_not_calibrated`). Current unresolved upstream metrics remain unresolved.

Checkpoint 3.4-7 additively owns the structural COMB-005 gate for the single frozen final feature `road_parking_access_score`. Road, public off-street parking capacity, and legal curb length remain distinct component semantics. Because no empirical COMB-005 weight set or canonical road/parking component-normalization authority is approved, the canonical V1 policy is explicitly `NOT_APPROVED`, carries no weights, the approved production registry is empty, and canonical execution returns no numeric score. Public production constructors cannot self-assert an `APPROVED` policy, an `AVAILABLE` component with detached score, or an `AVAILABLE` final result with caller-provided state/score. Synthetic available composition fixtures exist only inside tests.

Road-only/parking-only substitution, neutral fills, hidden weights, missing-side renormalization, production road/parking reductions, and caller-authored approval are forbidden. 3.4-7 intentionally does **not** assemble the whole `NormalizedLocationFeatures` surface or implement ScoringReadiness, RealDataPipelineResult, CategoryScores, Location Score, or `core.analyze()`.

Runtime dependencies remain: locked `sitescore-spatial==0.1.0` and `sitescore-metrics==0.1.0`.
