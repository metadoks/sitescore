# sitescore-benchmarks

Provider-neutral benchmark frame, measurement-population, coverage, raw real-unit distribution, generic mid-ECDF, and feature-specific normalization/compatibility contracts for SiteScore FAZ 3.4.

Checkpoint 3.4-2 remains the locked commercial equal-area frame foundation. Checkpoint 3.4-4 binds complete eligible frame-cell populations to the locked `sitescore-metrics` measurement semantics, derives coverage from actual attempts, preserves compatibility lineage, and produces raw real-unit benchmark observations. Checkpoint 3.4-5 defines finite canonical numeric samples, a separate exact/no-tolerance ECDF comparison policy, and the frozen generic mid-ECDF formula returning percentiles in `[0, 1]`.

Checkpoint 3.4-6 additively binds actual SITE measurements to actual compatible benchmark distributions before applying canonical feature direction: ordinary direct features use `100 * P`, while competition opportunity is structurally defined as `100 * (1 - P)`. It also defines the unique frozen age neutral fallback foundation (`50`, proxy, uncalibrated, `age_affinity_not_calibrated`). Current unresolved upstream metrics remain unresolved.

3.4-6 intentionally does **not** assemble the whole `NormalizedLocationFeatures` surface, does not emit `road_parking_access_score`, does not implement COMB-005, readiness, CategoryScores, Location Score, or `core.analyze()`.

Runtime dependencies remain: locked `sitescore-spatial==0.1.0` and `sitescore-metrics==0.1.0`.
