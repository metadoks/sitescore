# sitescore-report

`sitescore-report==0.3.0` preserves the locked FAZ 5.2 canonical report domain and FAZ 5.3 narrative authority while adding a deterministic customer-facing visual/PDF view layer.

Locked analytical authority remains:

```text
factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
```

Locked narrative authority remains:

```text
canonical ReportDomainModel
-> ApprovedNarrativeContext
-> active code-owned NarrativeClaimId contract
-> untrusted OpenAI Responses API claim selection OR deterministic fallback selection
-> exact claim/state/evidence validation
-> code-owned narrative templates
-> ValidatedReportNarrative
```

FAZ 5.4 adds only:

```text
exact canonical ReportDomainModel
+ exact ValidatedReportNarrative bound to that same model
-> versioned presentation policy
-> canonical tables + deterministic in-memory SVG charts
-> package-controlled Jinja2 HTML template + CSS
-> WeasyPrint
-> in-memory PDF bytes
```

The rendering layer is a view layer. It does not calculate or reinterpret scores, financial feasibility, break-even, BEC, rent burden, operating margin, decision, confidence, readiness, normalization, benchmark percentile, or analysis fingerprints.

## Exact rendering dependencies

Runtime rendering pins are:

```text
Jinja2==3.1.6
matplotlib==3.11.1
weasyprint==69.0
```

The locked narrative runtime pins remain:

```text
openai==3.2.0
pydantic==2.13.4
```

PDF structural tests use dev-only:

```text
pypdf==6.14.2
```

## Authority and lineage

Rendering requires both exact factory-owned objects:

```text
ReportDomainModel A
ValidatedReportNarrative N
N.approved_context.report_domain_model is A
```

A narrative from another report domain fails closed. Plain dictionaries, JSON views, fingerprints, copied/manual authority shells, caller score/financial/decision/confidence values, caller-authored chart values, caller templates, caller CSS, and caller prose are not rendering authority.

## Presentation policy

The versioned code-owned presentation policy defines consistent formatting for scores, currency, fractions displayed as percentages, already-percentage canonical fields, ratios/BEC, booleans/status labels, risk flags, and missing values.

The same canonical value uses the same policy wherever repeated. Chart annotations and table cells therefore share display formatting. Presentation rounding never feeds back into analytical authority.

Missing values use the explicit `Not available` token. Missing mapping keys remain visibly unavailable rather than becoming zero, neutral, or positive.

## Charts

Matplotlib builds deterministic in-memory SVG assets from canonical report values only. Current visualizations include:

- canonical category scores;
- canonical conservative/base/optimistic revenue scenarios.

No hidden normalization, stochastic data generation, external asset download, or caller-provided chart values are used.

## Controlled templates and asset security

The Jinja2 template and CSS are package-owned versioned assets. Jinja autoescaping remains enabled with strict undefined handling. Validated narrative strings enter the template only as escaped text/data.

The renderer does not accept caller template source, caller CSS, arbitrary asset paths, remote HTTP(S) assets, `file://` assets, or network fonts. The WeasyPrint URL fetch boundary allows embedded `data:` assets only.

## PDF rendering

`render_report_pdf(...)` returns PDF bytes in memory. It creates no durable report identifier, storage key, database row, object-storage object, API resource, payment state, or delivery workflow.

Invalid canonical authority, source/narrative mismatch, missing required package asset, chart generation failure, forbidden external asset access, WeasyPrint failure, or invalid PDF output raises an explicit render error. Failed rendering is never converted into empty/fake-valid PDF bytes.

## Current locked product limitation

Frozen COMB-005 remains not approved, so the real production analysis lifecycle remains:

```text
queued -> running -> not_score_ready
```

FAZ 5.4 does not manufacture a scored report/PDF from that path. Positive rendering fixtures use the established test-only upstream SCORE_READY substitution while still obtaining genuine factory-owned `ApplicationAnalysisResult -> ReportDomainModel -> ValidatedReportNarrative` authority.

## Still out of scope

FAZ 5.4 does **not** introduce:

```text
report_id
analysis_id <-> durable report resource binding
PostgreSQL report-resource tables
S3/object storage
storage_key
report API routes
payment/Stripe
n8n
email delivery
commercial order workflow
frontend application
empirical validation
FAZ 6+
```

See:

- `docs/CHECKPOINT_5_2_CANONICAL_REPORT_DOMAIN.md`
- `docs/CHECKPOINT_5_3_NARRATIVE_INSIGHT_AUTHORITY.md`
- `docs/CHECKPOINT_5_4_VISUAL_REPORT_PDF_RENDERING.md`

> Mathematically validated scoring engine; empirical validation pending.
