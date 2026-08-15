# sitescore-benchmarks

Provider-neutral benchmark frame, measurement-population, coverage, and raw real-unit distribution contracts for SiteScore FAZ 3.4.

Checkpoint 3.4-2 remains the locked commercial equal-area frame foundation. Checkpoint 3.4-4 additively binds complete eligible frame-cell populations to the locked `sitescore-metrics` measurement semantics, derives coverage from actual attempts, preserves compatibility lineage, and produces raw real-unit benchmark observations. It intentionally does not implement ECDF, percentile ranking, 0–100 normalization, COMB-005, readiness, or scoring.

Runtime dependencies: locked `sitescore-spatial==0.1.0` and `sitescore-metrics==0.1.0`.
