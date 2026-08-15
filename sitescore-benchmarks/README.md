# sitescore-benchmarks

Provider-neutral benchmark frame, measurement-population, coverage, raw real-unit distribution, and generic mid-ECDF contracts for SiteScore FAZ 3.4.

Checkpoint 3.4-2 remains the locked commercial equal-area frame foundation. Checkpoint 3.4-4 binds complete eligible frame-cell populations to the locked `sitescore-metrics` measurement semantics, derives coverage from actual attempts, preserves compatibility lineage, and produces raw real-unit benchmark observations. Checkpoint 3.4-5 additively defines finite canonical numeric samples, a separate exact/no-tolerance ECDF comparison policy, and the frozen generic mid-ECDF formula returning percentiles in `[0, 1]`.

3.4-5 intentionally does **not** implement feature-specific 0–100 normalization, competition opportunity inversion, directionality, COMB-005, readiness, CategoryScores, Location Score, or `core.analyze()`.

Runtime dependencies remain: locked `sitescore-spatial==0.1.0` and `sitescore-metrics==0.1.0`.
