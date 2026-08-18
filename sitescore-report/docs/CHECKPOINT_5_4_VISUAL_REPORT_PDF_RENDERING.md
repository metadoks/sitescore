# FAZ 5.4 — Visual Report + PDF Rendering

## Status and scope

- Package: `sitescore-report==0.3.0`
- Exact locked base: `main@30a12424cebfb6bcd53ad6fcd5d5db1b2315d9ae`
- Product scope: `sitescore-report/**`
- Renderer: WeasyPrint
- Template: package-controlled Jinja2 HTML
- Stylesheet: package-controlled CSS
- Charts: deterministic in-memory Matplotlib SVG
- Durable report resource/storage: not introduced
- Database migration: none

> Mathematically validated scoring engine; empirical validation pending.

## Locked upstream authority

FAZ 5.4 consumes but does not reopen the locked report/narrative chain:

```text
factory-owned ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
-> ApprovedNarrativeContext
-> closed canonical-state NarrativeClaimId selection
-> exact claim/section/evidence validation
-> code-owned narrative text
-> ValidatedReportNarrative
```

The LLM remains non-authoritative. The visual layer cannot create business truth.

## Rendering authority

The rendering entrypoints require:

```text
ReportDomainModel A
ValidatedReportNarrative N
N.approved_context.report_domain_model is A
```

Both values are revalidated through their locked factory-owned authority validators. Cross-source substitution fails closed.

Not accepted as rendering authority:

```text
plain dict / JSON
analysis fingerprint
copied or manually allocated report/narrative shells
caller scores or financials
caller decision/confidence
caller chart values
caller HTML/template/CSS
caller narrative prose
```

Rendering does not issue or accept a durable `report_id`.

## Versioned presentation/render identities

```text
PRESENTATION_SCHEMA_VERSION = sitescore-presentation-v1
PRESENTATION_POLICY_VERSION = sitescore-presentation-policy-v1
TEMPLATE_VERSION            = sitescore-report-template-v1
STYLESHEET_VERSION          = sitescore-report-stylesheet-v1
CHART_VERSION               = sitescore-report-charts-v1
RENDERER_VERSION            = sitescore-pdf-renderer-v1
```

These are presentation provenance only. They are not scoring/report authority tokens.

## Exact dependency contract

Runtime direct dependencies remain exact-pinned. FAZ 5.4 adds:

```text
Jinja2==3.1.6
matplotlib==3.11.1
weasyprint==69.0
```

Locked report/narrative dependencies remain:

```text
sitescore-app==0.1.0
sitescore-core==0.1.0
openai==3.2.0
pydantic==2.13.4
```

Dev-only PDF parser evidence uses:

```text
pytest==8.4.2
pypdf==6.14.2
```

No direct `sitescore-api`, SQLAlchemy, Alembic, Celery, Redis, FastAPI, boto/S3, Stripe or n8n dependency is added to `sitescore-report`.

## No analytical recomputation

Presentation code consumes exact `ReportDomainModel` fields. It does not compute/reinterpret:

```text
location score
category scores
financial feasibility
break-even
BEC
operating margin
rent burden
structural band
financial band
decision
confidence
normalization
benchmark percentile
readiness
analysis fingerprint
```

Tables contain display projections of canonical facts. Charts use canonical values directly; no hidden normalization or missing-value substitution is applied.

## Presentation policy

One code-owned frozen `PresentationPolicy` handles display transforms consistently.

Policy classes:

- scores: fixed display decimals;
- currency: display-only currency formatting;
- canonical `0..1` rate inputs: multiplied once for percentage display;
- already-percentage canonical fields such as `rent_burden_pct` and `operating_margin_pct`: displayed without another scale transform;
- BEC/ratios: ratio formatting;
- booleans: explicit `Yes` / `No`;
- labels/risk flags: display-only humanization;
- `None` or absent expected mapping entries: `Not available`.

The same policy is used for repeated table/chart labels. Display rounding never feeds back into authority.

## Tables and report sections

Controlled templates render material canonical classes including:

- sector;
- category scores;
- location result;
- business assumptions and sector-specific revenue inputs;
- canonical financial result;
- decision/headline/risk flags;
- confidence;
- data-quality and missingness context;
- exact validated narrative sections;
- locked model/report provenance;
- presentation/render provenance.

No financial subtotal or analytical field is recomputed merely for layout.

## Deterministic charts

Matplotlib uses an object-oriented in-memory SVG path. Current charts are:

```text
category_scores
revenue_scenarios
```

Category chart values are the four canonical category scores. Revenue chart values are the exact canonical conservative/base/optimistic revenue values.

Chart annotations use the same presentation policy as table cells. SVG generation fixes DejaVu Sans and a code-owned SVG hash salt and removes date metadata. Assets are embedded as `data:image/svg+xml;base64,...` URIs.

A malformed/broken chart asset is rejected; a chart generation exception is surfaced as an explicit render failure.

## Template, HTML, CSS and asset security

The renderer loads template and CSS only from a closed `RenderAsset` enum backed by package resources:

```text
templates/report.html
assets/report.css
```

There is no caller path parameter.

Jinja2 uses autoescaping and `StrictUndefined`. Validated narrative text is ordinary template data; it is not marked safe HTML.

The controlled template/CSS contains no external network references. Fonts use environment-stable/package-independent `DejaVu Sans` / `DejaVu Sans Mono`; no network font download is used.

The WeasyPrint fetch boundary accepts only `data:` assets. `http:`, `https:` and `file:` URLs fail closed. Arbitrary local filesystem reads and path traversal are not exposed through the public renderer API.

## PDF rendering semantics

`render_report_pdf(...)`:

1. validates exact report+narrative authority and identity binding;
2. renders controlled HTML;
3. loads controlled stylesheet;
4. invokes WeasyPrint in memory;
5. revalidates authority;
6. requires nontrivial bytes beginning with `%PDF-`.

Explicit failures include:

```text
invalid/noncanonical source -> authority error before rendering
source/narrative mismatch -> authority error
missing required renderer asset -> ReportRenderError
chart generation failure -> ReportRenderError
forbidden external asset -> ReportRenderError
WeasyPrint exception -> ReportRenderError
invalid/empty PDF bytes -> ReportRenderError
```

No failure is converted into a fake-valid or empty PDF.

## Missingness and adverse states

Visual output preserves unfavorable/missing canonical truth:

- `None` -> `Not available`;
- absent expected quality-map entry -> `Not available`;
- low confidence remains visibly low;
- stress-test failure remains `Yes`;
- weak/non-viable classifications and risk flags remain visible;
- missing optional facts are not shown as zero or neutral.

## Pagination and layout robustness

The controlled A4 stylesheet defines explicit page breaks between major report sections, table-header repetition semantics, `break-inside` protection for critical cards/rows, overflow wrapping, a page counter, and bounded chart sizing.

Validation uses parser-readable multi-page PDFs from representative genuine test authority chains. Representative evidence fixtures are required for:

```text
normal/strong
financially stressed
low-confidence / incomplete evidence
```

The generated PDFs are validation artifacts only; they are not durable customer report resources.

## Current production limitation

Frozen COMB-005 remains `NOT_APPROVED`. Current real production execution can still terminate:

```text
queued -> running -> not_score_ready
```

5.4 does not create a production SCORE_READY forcing seam and does not fabricate a scored PDF from NOT_SCORE_READY.

Positive rendering tests use the established test-only upstream SCORE_READY substitution and then use public/factory-owned construction to obtain genuine:

```text
ApplicationAnalysisResult
-> CanonicalReportFacts
-> ReportDomainModel
-> ValidatedReportNarrative
```

Top-level report/narrative authority is not forged for positive rendering tests.

## Explicitly out of scope

5.4 does not implement:

```text
report_id
analysis_id <-> durable report resource binding
PostgreSQL report metadata/resource tables
S3/object storage
storage_key
report API routes
POST /v1/reports
GET /v1/reports/{report_id}
report content endpoint
Stripe/payment
n8n
email delivery
commercial order workflow
frontend application
empirical validation
FAZ 6+
```

Those concerns remain later-checkpoint work.
