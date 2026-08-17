# sitescore-report

`sitescore-report==0.1.0` is the FAZ 5.2 canonical report-fact and report-domain package for SiteScore AI.

It is intentionally a **truth-preserving domain projection only**.

```text
factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
```

Production report authority begins only from the exact frozen application result and calls `require_canonical_application_analysis_result(...)` before projection. A `CanonicalAnalysisResult` by itself, `to_dict()` JSON, an analysis fingerprint, detached input pieces, or caller-provided category/financial/decision/confidence values cannot grant report authority.

The package preserves, without reweighting or presentation conversion:

- report/schema/projection provenance and exact core model versions;
- source `analysis_fingerprint` as provenance metadata only;
- sector and exact category scores;
- common financial assumptions and all four sector-specific revenue-input variants;
- canonical location result;
- canonical financial result;
- canonical decision and ordered risk flags;
- canonical confidence result;
- geographic level, data age, partial data-coverage mapping, and partial input-quality mapping.

`None` remains `None`; missing mapping keys remain missing; floats are not presentation-rounded; rates are not rescaled; strings are not customer-friendly relabeled. `to_dict()` returns a deep-owned JSON-safe view and is not authority.

## Current locked product limitation

FAZ 5.1 remains authoritative: frozen COMB-005 is not approved, so the current real production acquisition/lifecycle path terminates `not_score_ready`. FAZ 5.2 does not reinterpret that state as a scored report and does not manufacture a `completed` result. `CanonicalReportFacts` exists only for a genuine scored, factory-owned `ApplicationAnalysisResult`.

## Explicitly out of scope

FAZ 5.2 does not implement narrative generation, recommendations, HTML, charts, PDF rendering, report persistence, report IDs, report API routes, database migrations, S3/object storage, payments, n8n, email, or FAZ 6 behavior.

The durable server `analysis_id <-> report/artifact` association belongs to the later report-resource/artifact checkpoint; 5.2 therefore does not accept or emit `analysis_id` or `report_id` as report-fact authority.

See `docs/CHECKPOINT_5_2_CANONICAL_REPORT_DOMAIN.md` for the complete checkpoint contract.

> Mathematically validated scoring engine; empirical validation pending.
