from __future__ import annotations

from test_report_projection_authority import _run


def test_four_sector_html_pdf_and_chart_table_fidelity():
    _run(r'''
from io import BytesIO
from pypdf import PdfReader
from sitescore_report import (
    DEFAULT_PRESENTATION_POLICY,
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_chart_assets,
    build_report_domain_model,
    build_validated_report_narrative,
    render_report_html,
    render_report_pdf,
)

policy = DEFAULT_PRESENTATION_POLICY
for sector in ("coffee", "restaurant", "gym", "beauty"):
    source = build_scored(sector)
    domain = build_report_domain_model(build_canonical_report_facts(source))
    narrative = build_validated_report_narrative(
        domain, config=NarrativeProviderConfig(model_id=None)
    )

    html = render_report_html(domain, narrative)
    assets = build_report_chart_assets(domain)
    pdf = render_report_pdf(domain, narrative)

    assert html.startswith("<!doctype html>")
    assert pdf.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) >= 3
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Location Intelligence Report" in extracted
    assert "Canonical decision" in extracted
    assert domain.decision.headline in extracted

    category = next(asset for asset in assets if asset.key == "category_scores")
    revenue = next(asset for asset in assets if asset.key == "revenue_scenarios")
    expected_category = (
        policy.score(domain.category_scores.demand),
        policy.score(domain.category_scores.competition),
        policy.score(domain.category_scores.accessibility),
        policy.score(domain.category_scores.economics),
    )
    expected_revenue = (
        policy.money(domain.financial.revenue.conservative),
        policy.money(domain.financial.revenue.base),
        policy.money(domain.financial.revenue.optimistic),
    )
    assert category.display_values == expected_category
    assert revenue.display_values == expected_revenue
    for value in expected_category + expected_revenue:
        assert value in html

    assert policy.score(domain.location.final_score) in html
    assert policy.money(domain.financial.fixed_costs) in html
    assert policy.percent_points(domain.financial.rent_burden_pct) in html
    assert policy.percent_points(domain.financial.operating_margin_pct) in html
    assert narrative.executive_summary in html
    assert domain.provenance.source_analysis_fingerprint in html
''')


def test_presentation_policy_preserves_fraction_percentage_and_missingness_semantics():
    _run(r'''
from sitescore_report import (
    DEFAULT_PRESENTATION_POLICY,
    NarrativeProviderConfig,
    UNAVAILABLE_TOKEN,
    build_canonical_report_facts,
    build_report_chart_assets,
    build_report_domain_model,
    build_validated_report_narrative,
    render_report_html,
)

source = build_scored(
    "coffee",
    data_age_years=None,
    data_coverage={"demand": CoverageLevel.DEGRADED},
    input_qualities={"rent": InputQuality.DEFAULT},
)
domain = build_report_domain_model(build_canonical_report_facts(source))
narrative = build_validated_report_narrative(
    domain, config=NarrativeProviderConfig(model_id=None)
)
html = render_report_html(domain, narrative)
policy = DEFAULT_PRESENTATION_POLICY

assert policy.fraction_percent(.55) == "55.0%"
assert "55.0%" in html
expected_rent_burden = policy.percent_points(domain.financial.rent_burden_pct)
assert f"Rent burden</th><td>{expected_rent_burden}</td>" in html
assert f"Data age (years)</th><td>{UNAVAILABLE_TOKEN}</td>" in html
assert f"Competition</th><td>{UNAVAILABLE_TOKEN}</td>" in html
assert f"Price</th><td>{UNAVAILABLE_TOKEN}</td>" in html
assert narrative.approved_context.report_domain_model is domain

category_asset = next(
    asset for asset in build_report_chart_assets(domain) if asset.key == "category_scores"
)
assert category_asset.display_values[0] == policy.score(domain.category_scores.demand)
assert category_asset.display_values[0] in html
''')


def test_render_authority_rejects_cross_source_dict_copy_and_mutation():
    _run(r'''
import copy
from sitescore_report import (
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
    render_report_html,
    render_report_pdf,
)

source_a = build_scored("coffee")
domain_a = build_report_domain_model(build_canonical_report_facts(source_a))
narrative_a = build_validated_report_narrative(
    domain_a, config=NarrativeProviderConfig(model_id=None)
)
source_b = build_scored("gym")
domain_b = build_report_domain_model(build_canonical_report_facts(source_b))
narrative_b = build_validated_report_narrative(
    domain_b, config=NarrativeProviderConfig(model_id=None)
)

for renderer in (render_report_html, render_report_pdf):
    try:
        renderer(domain_a, narrative_b)
    except ValueError:
        pass
    else:
        raise AssertionError("cross-source narrative substitution must fail closed")

    for bad_domain in (domain_a.to_dict(), copy.copy(domain_a)):
        try:
            renderer(bad_domain, narrative_a)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("noncanonical report domain must not render")

    for bad_narrative in (narrative_a.to_dict(), copy.copy(narrative_a)):
        try:
            renderer(domain_a, bad_narrative)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("noncanonical narrative must not render")

original_summary = narrative_a.executive_summary
object.__setattr__(narrative_a, "executive_summary", "mutated")
try:
    render_report_pdf(domain_a, narrative_a)
except ValueError:
    pass
else:
    raise AssertionError("mutated validated narrative must fail before rendering")
object.__setattr__(narrative_a, "executive_summary", original_summary)
''')


def test_template_css_and_url_security_are_closed_and_autoescaped():
    _run(r'''
from sitescore_report import RenderAsset, ReportRenderError
from sitescore_report.rendering import (
    _jinja_environment,
    _load_asset_text,
    _restricted_url_fetcher,
)

rendered = _jinja_environment().from_string("{{ value }}").render(
    value='<script>alert("x")</script><b>unsafe</b>'
)
assert "<script>" not in rendered
assert "<b>unsafe</b>" not in rendered
assert "&lt;script&gt;" in rendered

html_template = _load_asset_text(RenderAsset.TEMPLATE)
stylesheet = _load_asset_text(RenderAsset.STYLESHEET)
assert "|safe" not in html_template
for forbidden in ("http://", "https://", "file://"):
    assert forbidden not in html_template.lower()
    assert forbidden not in stylesheet.lower()

try:
    _load_asset_text("../../../../etc/passwd")
except TypeError:
    pass
else:
    raise AssertionError("arbitrary asset paths must not be accepted")

for url in (
    "https://example.com/asset.png",
    "http://example.com/asset.png",
    "file:///etc/passwd",
):
    try:
        _restricted_url_fetcher(url)
    except ReportRenderError as exc:
        assert exc.code == "external_asset_forbidden"
    else:
        raise AssertionError("external/local assets must be rejected")
''')


def test_chart_template_and_pdf_failures_are_explicit_not_fake_success():
    _run(r'''
from unittest.mock import patch
from sitescore_report import (
    NarrativeProviderConfig,
    ReportRenderError,
    build_canonical_report_facts,
    build_report_chart_assets,
    build_report_domain_model,
    build_validated_report_narrative,
    render_report_html,
    render_report_pdf,
)

source = build_scored("restaurant")
domain = build_report_domain_model(build_canonical_report_facts(source))
narrative = build_validated_report_narrative(
    domain, config=NarrativeProviderConfig(model_id=None)
)

with patch("sitescore_report.rendering.Figure.savefig", side_effect=RuntimeError("chart boom")):
    try:
        build_report_chart_assets(domain)
    except ReportRenderError as exc:
        assert exc.code == "chart_generation_failed"
    else:
        raise AssertionError("chart failure must not be hidden")

with patch(
    "sitescore_report.rendering._load_asset_text",
    side_effect=ReportRenderError("required_render_asset_missing"),
):
    try:
        render_report_html(domain, narrative)
    except ReportRenderError as exc:
        assert exc.code == "required_render_asset_missing"
    else:
        raise AssertionError("missing controlled template must fail")

with patch("sitescore_report.rendering.HTML.write_pdf", side_effect=RuntimeError("pdf boom")):
    try:
        render_report_pdf(domain, narrative)
    except ReportRenderError as exc:
        assert exc.code == "pdf_render_failed"
    else:
        raise AssertionError("renderer exception must not become fake PDF bytes")
''')


def test_strong_stressed_and_low_confidence_reports_remain_truthful_and_multi_page():
    _run(r'''
from io import BytesIO
from pypdf import PdfReader
from sitescore_report import (
    NarrativeProviderConfig,
    UNAVAILABLE_TOKEN,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
    render_report_html,
    render_report_pdf,
)

cases = (
    build_scored(
        "coffee",
        score=95.0,
        monthly_rent=200.0,
        fixed_labor=200.0,
        fixed_overhead=100.0,
    ),
    build_scored(
        "restaurant",
        score=5.0,
        monthly_rent=500000.0,
        fixed_labor=500000.0,
        fixed_overhead=250000.0,
    ),
    build_scored(
        "gym",
        score=72.0,
        geographic_level=GeographicLevel.UNKNOWN,
        data_age_years=None,
        data_coverage={"demand": CoverageLevel.DEGRADED},
        input_qualities={"rent": InputQuality.DEFAULT},
    ),
)

for source in cases:
    domain = build_report_domain_model(build_canonical_report_facts(source))
    narrative = build_validated_report_narrative(
        domain, config=NarrativeProviderConfig(model_id=None)
    )
    html = render_report_html(domain, narrative)
    pdf = render_report_pdf(domain, narrative)
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) >= 3
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "SiteScore AI" in text
    assert "empirical validation pending" in text.lower()
    assert domain.decision.headline in text
    if domain.financial.stress_test_failed:
        assert "Stress test failed" in text
        assert ">Yes<" in html
    if domain.data_quality.data_age_years is None:
        assert UNAVAILABLE_TOKEN in html
        assert domain.confidence.label == "low"
''')


def test_unicode_and_long_provenance_content_wraps_without_breaking_pdf():
    _run(r'''
import json
from io import BytesIO
from types import SimpleNamespace
from pypdf import PdfReader
from sitescore_report import (
    NarrativeClaimId,
    NarrativeDraft,
    NarrativeDraftAnchors,
    NarrativePointDraft,
    NarrativeProviderConfig,
    build_canonical_report_facts,
    build_report_domain_model,
    build_validated_report_narrative,
    render_report_html,
    render_report_pdf,
)


def selection(payload, claim_id):
    approved = payload["approved_claims"][claim_id.value]
    return NarrativePointDraft(
        claim_id=claim_id,
        evidence_keys=list(approved["evidence_keys"]),
    )


class FakeResponses:
    def parse(self, **kwargs):
        payload = json.loads(kwargs["input"])
        return SimpleNamespace(
            status="completed",
            output_parsed=NarrativeDraft(
                canonical_anchors=NarrativeDraftAnchors(**payload["canonical_anchors"]),
                executive_summary=[selection(payload, NarrativeClaimId.EXECUTIVE_CANONICAL_DECISION)],
                strengths=[],
                risks=[],
                recommendations=[selection(payload, NarrativeClaimId.RECOMMEND_REVIEW_CANONICAL_DECISION)],
                caveats=[
                    selection(payload, NarrativeClaimId.CAVEAT_EMPIRICAL_VALIDATION_PENDING),
                    selection(payload, NarrativeClaimId.CAVEAT_LANGUAGE_LAYER),
                ],
            ),
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


source = build_scored(
    "restaurant",
    score=5.0,
    monthly_rent=500000.0,
    fixed_labor=500000.0,
    fixed_overhead=250000.0,
)
domain = build_report_domain_model(build_canonical_report_facts(source))
model_id = "model-İstanbul-Çeşme-ğüşöç-" * 18
narrative = build_validated_report_narrative(
    domain,
    config=NarrativeProviderConfig(model_id=model_id),
    client=FakeClient(),
)
assert narrative.provenance.generation_mode == "llm"
assert narrative.provenance.model_id == model_id

html = render_report_html(domain, narrative)
assert model_id in html
pdf = render_report_pdf(domain, narrative)
reader = PdfReader(BytesIO(pdf))
assert len(reader.pages) >= 3
text = "\n".join(page.extract_text() or "" for page in reader.pages)
assert "SiteScore AI" in text
assert "empirical validation pending" in text.lower()
assert domain.decision.headline in text
''')
