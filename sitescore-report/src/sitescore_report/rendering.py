from __future__ import annotations

import base64
from dataclasses import dataclass, fields
from enum import Enum
from importlib import metadata, resources
from io import StringIO
from types import MappingProxyType
from urllib.parse import urlparse

from jinja2 import Environment, StrictUndefined, select_autoescape
from matplotlib import rc_context
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from weasyprint import CSS, HTML, default_url_fetcher

from .domain import ReportDomainModel, require_canonical_report_domain_model
from .narrative import ValidatedReportNarrative, require_validated_report_narrative

PRESENTATION_SCHEMA_VERSION = "sitescore-presentation-v1"
PRESENTATION_POLICY_VERSION = "sitescore-presentation-policy-v1"
TEMPLATE_VERSION = "sitescore-report-template-v1"
STYLESHEET_VERSION = "sitescore-report-stylesheet-v1"
CHART_VERSION = "sitescore-report-charts-v1"
RENDERER_VERSION = "sitescore-pdf-renderer-v1"

JINJA2_RUNTIME_VERSION = "3.1.6"
MATPLOTLIB_RUNTIME_VERSION = "3.11.1"
WEASYPRINT_RUNTIME_VERSION = "69.0"

UNAVAILABLE_TOKEN = "Not available"

_RENDER_RUNTIME_VERSIONS = MappingProxyType(
    {
        "Jinja2": JINJA2_RUNTIME_VERSION,
        "matplotlib": MATPLOTLIB_RUNTIME_VERSION,
        "weasyprint": WEASYPRINT_RUNTIME_VERSION,
    }
)


class ReportRenderError(RuntimeError):
    """Explicit fail-closed visual-report rendering failure."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


class RenderAsset(str, Enum):
    TEMPLATE = "templates/report.html"
    STYLESHEET = "assets/report.css"


@dataclass(frozen=True, slots=True)
class PresentationPolicy:
    version: str = PRESENTATION_POLICY_VERSION
    unavailable_token: str = UNAVAILABLE_TOKEN
    score_decimals: int = 1
    money_decimals: int = 2
    percent_decimals: int = 1
    ratio_decimals: int = 2
    number_decimals: int = 2

    def score(self, value: float) -> str:
        return f"{value:.{self.score_decimals}f}"

    def money(self, value: float) -> str:
        sign = "-" if value < 0 else ""
        return f"{sign}${abs(value):,.{self.money_decimals}f}"

    def fraction_percent(self, value: float) -> str:
        return f"{value * 100:.{self.percent_decimals}f}%"

    def percent_points(self, value: float) -> str:
        return f"{value:.{self.percent_decimals}f}%"

    def ratio(self, value: float) -> str:
        return f"{value:.{self.ratio_decimals}f}"

    def number(self, value: int | float) -> str:
        if isinstance(value, int) and not isinstance(value, bool):
            return f"{value:,d}"
        return f"{float(value):,.{self.number_decimals}f}"

    def boolean(self, value: bool) -> str:
        return "Yes" if value else "No"

    def optional_number(self, value: int | float | None) -> str:
        return self.unavailable_token if value is None else self.number(value)

    def label(self, value: object) -> str:
        raw = getattr(value, "value", value)
        if raw is None:
            return self.unavailable_token
        return str(raw).replace("_", " ").replace("-", " ").strip().title()

    def optional_label(self, value: object | None) -> str:
        return self.unavailable_token if value is None else self.label(value)

    def risk_flags(self, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(self.label(value) for value in values)


DEFAULT_PRESENTATION_POLICY = PresentationPolicy()


@dataclass(frozen=True, slots=True)
class ReportChartAsset:
    key: str
    data_uri: str
    labels: tuple[str, ...]
    display_values: tuple[str, ...]


_RATE_INPUT_FIELDS = frozenset(
    {
        "target_rate",
        "capture_rate_conservative",
        "capture_rate_base",
        "capture_rate_optimistic",
        "utilization_conservative",
        "utilization_base",
        "utilization_optimistic",
        "penetration_rate_conservative",
        "penetration_rate_base",
        "penetration_rate_optimistic",
    }
)
_MONEY_INPUT_FIELDS = frozenset({"average_ticket", "monthly_membership_fee"})
_INPUT_LABELS = MappingProxyType(
    {
        "target_population": "Target population",
        "target_rate": "Target rate",
        "capture_rate_conservative": "Capture rate — conservative",
        "capture_rate_base": "Capture rate — base",
        "capture_rate_optimistic": "Capture rate — optimistic",
        "visit_frequency_per_month": "Visits per month",
        "average_ticket": "Average ticket",
        "seats": "Seats",
        "turnover_per_day": "Turnover per day",
        "utilization_conservative": "Utilization — conservative",
        "utilization_base": "Utilization — base",
        "utilization_optimistic": "Utilization — optimistic",
        "operating_days_per_month": "Operating days per month",
        "penetration_rate_conservative": "Penetration — conservative",
        "penetration_rate_base": "Penetration — base",
        "penetration_rate_optimistic": "Penetration — optimistic",
        "usable_area": "Usable area",
        "members_per_area_unit": "Members per area unit",
        "monthly_membership_fee": "Monthly membership fee",
        "stations": "Stations",
        "operating_hours_per_week": "Operating hours per week",
        "average_service_duration_hours": "Average service duration (hours)",
    }
)


def _require_runtime_versions() -> None:
    for distribution, expected in _RENDER_RUNTIME_VERSIONS.items():
        try:
            actual = metadata.version(distribution)
        except metadata.PackageNotFoundError as exc:
            raise ReportRenderError(
                "render_dependency_missing", f"required render dependency missing: {distribution}"
            ) from exc
        if actual != expected:
            raise ReportRenderError(
                "render_dependency_version_mismatch",
                f"{distribution} runtime version {actual!r} != pinned {expected!r}",
            )


def _require_render_sources(
    report_domain_model: ReportDomainModel,
    validated_narrative: ValidatedReportNarrative,
) -> tuple[ReportDomainModel, ValidatedReportNarrative]:
    domain = require_canonical_report_domain_model(report_domain_model)
    narrative = require_validated_report_narrative(validated_narrative)
    context = narrative.approved_context
    if context.report_domain_model is not domain:
        raise ValueError(
            "validated narrative is not bound to the exact ReportDomainModel supplied for rendering"
        )
    return domain, narrative


def _load_asset_text(asset: RenderAsset) -> str:
    if not isinstance(asset, RenderAsset):
        raise TypeError("renderer assets must be selected from the closed RenderAsset enum")
    try:
        target = resources.files("sitescore_report").joinpath(asset.value)
        if not target.is_file():
            raise FileNotFoundError(asset.value)
        return target.read_text(encoding="utf-8")
    except Exception as exc:
        raise ReportRenderError(
            "required_render_asset_missing", f"required renderer asset unavailable: {asset.value}"
        ) from exc


def _jinja_environment() -> Environment:
    return Environment(
        autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _business_input_rows(domain: ReportDomainModel) -> list[dict[str, str]]:
    policy = DEFAULT_PRESENTATION_POLICY
    revenue_input = domain.business_assumptions.revenue_input
    rows: list[dict[str, str]] = []
    for field in fields(revenue_input):
        if field.name == "kind":
            continue
        value = getattr(revenue_input, field.name)
        if field.name in _RATE_INPUT_FIELDS:
            display = policy.fraction_percent(float(value))
        elif field.name in _MONEY_INPUT_FIELDS:
            display = policy.money(float(value))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            display = policy.number(value)
        else:
            display = policy.label(value)
        rows.append(
            {
                "label": _INPUT_LABELS.get(field.name, field.name.replace("_", " ").title()),
                "value": display,
            }
        )
    return rows


def _data_quality_rows(domain: ReportDomainModel) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    policy = DEFAULT_PRESENTATION_POLICY
    coverage_rows = [
        {
            "label": key.title(),
            "value": policy.optional_label(domain.data_quality.data_coverage.get(key)),
        }
        for key in ("demand", "competition", "accessibility", "economics")
    ]
    quality_rows = [
        {
            "label": key.title(),
            "value": policy.optional_label(domain.data_quality.input_qualities.get(key)),
        }
        for key in ("rent", "price", "capacity", "schedule")
    ]
    return coverage_rows, quality_rows


def _svg_data_uri(svg_text: str) -> str:
    payload = svg_text.encode("utf-8")
    return "data:image/svg+xml;base64," + base64.b64encode(payload).decode("ascii")


def _validate_chart_asset(asset: ReportChartAsset) -> None:
    prefix = "data:image/svg+xml;base64,"
    if not asset.data_uri.startswith(prefix):
        raise ReportRenderError("broken_chart_asset", f"chart {asset.key} is not an SVG data URI")
    try:
        decoded = base64.b64decode(asset.data_uri[len(prefix) :], validate=True)
    except Exception as exc:
        raise ReportRenderError("broken_chart_asset", f"chart {asset.key} has invalid base64") from exc
    if b"<svg" not in decoded[:1000]:
        raise ReportRenderError("broken_chart_asset", f"chart {asset.key} does not contain SVG markup")


def _render_bar_chart_svg(
    *,
    labels: tuple[str, ...],
    values: tuple[float, ...],
    display_values: tuple[str, ...],
    title: str,
    y_label: str,
    y_limit: tuple[float, float] | None,
) -> str:
    try:
        with rc_context(
            {
                "font.family": "DejaVu Sans",
                "font.size": 9.0,
                "svg.hashsalt": CHART_VERSION,
                "axes.unicode_minus": False,
            }
        ):
            figure = Figure(figsize=(7.2, 2.75), dpi=96)
            FigureCanvasSVG(figure)
            axis = figure.subplots()
            positions = list(range(len(values)))
            bars = axis.bar(positions, values, width=0.62)
            axis.set_title(title, loc="left", fontsize=11, fontweight="bold")
            axis.set_ylabel(y_label)
            axis.set_xticks(positions, labels)
            if y_limit is not None:
                axis.set_ylim(*y_limit)
            axis.grid(axis="y", linewidth=0.5, alpha=0.22)
            for bar, label in zip(bars, display_values, strict=True):
                height = bar.get_height()
                axis.annotate(
                    label,
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
            figure.tight_layout(pad=1.0)
            buffer = StringIO()
            figure.savefig(buffer, format="svg", metadata={"Date": None})
            return buffer.getvalue()
    except Exception as exc:
        raise ReportRenderError("chart_generation_failed", f"chart generation failed: {title}") from exc


def build_report_chart_assets(report_domain_model: ReportDomainModel) -> tuple[ReportChartAsset, ...]:
    """Build deterministic in-memory chart assets from exact canonical report facts only."""

    _require_runtime_versions()
    domain = require_canonical_report_domain_model(report_domain_model)
    policy = DEFAULT_PRESENTATION_POLICY

    category_labels = ("Demand", "Competition", "Accessibility", "Economics")
    category_values = (
        domain.category_scores.demand,
        domain.category_scores.competition,
        domain.category_scores.accessibility,
        domain.category_scores.economics,
    )
    category_display = tuple(policy.score(value) for value in category_values)
    category_svg = _render_bar_chart_svg(
        labels=category_labels,
        values=category_values,
        display_values=category_display,
        title="Category scores",
        y_label="Canonical score",
        y_limit=(0.0, 100.0),
    )

    revenue_labels = ("Conservative", "Base", "Optimistic")
    revenue_values = (
        domain.financial.revenue.conservative,
        domain.financial.revenue.base,
        domain.financial.revenue.optimistic,
    )
    revenue_display = tuple(policy.money(value) for value in revenue_values)
    revenue_svg = _render_bar_chart_svg(
        labels=revenue_labels,
        values=revenue_values,
        display_values=revenue_display,
        title="Revenue scenarios",
        y_label="Canonical currency amount",
        y_limit=None,
    )

    assets = (
        ReportChartAsset(
            key="category_scores",
            data_uri=_svg_data_uri(category_svg),
            labels=category_labels,
            display_values=category_display,
        ),
        ReportChartAsset(
            key="revenue_scenarios",
            data_uri=_svg_data_uri(revenue_svg),
            labels=revenue_labels,
            display_values=revenue_display,
        ),
    )
    for asset in assets:
        _validate_chart_asset(asset)
    require_canonical_report_domain_model(domain)
    return assets


def _build_presentation_view(
    domain: ReportDomainModel,
    narrative: ValidatedReportNarrative,
    charts: tuple[ReportChartAsset, ...],
) -> dict[str, object]:
    policy = DEFAULT_PRESENTATION_POLICY
    coverage_rows, quality_rows = _data_quality_rows(domain)
    chart_map = {asset.key: asset.data_uri for asset in charts}

    return {
        "presentation": {
            "schema_version": PRESENTATION_SCHEMA_VERSION,
            "policy_version": PRESENTATION_POLICY_VERSION,
            "template_version": TEMPLATE_VERSION,
            "stylesheet_version": STYLESHEET_VERSION,
            "chart_version": CHART_VERSION,
            "renderer_version": RENDERER_VERSION,
        },
        "analysis": {
            "sector": policy.label(domain.analysis.sector),
        },
        "category_scores": [
            {"label": "Demand", "value": policy.score(domain.category_scores.demand)},
            {"label": "Competition", "value": policy.score(domain.category_scores.competition)},
            {"label": "Accessibility", "value": policy.score(domain.category_scores.accessibility)},
            {"label": "Economics", "value": policy.score(domain.category_scores.economics)},
        ],
        "location": [
            {"label": "Base score", "value": policy.score(domain.location.base_score)},
            {"label": "Penalty multiplier", "value": policy.ratio(domain.location.penalty_multiplier)},
            {"label": "Final score", "value": policy.score(domain.location.final_score)},
            {"label": "Structural band", "value": policy.label(domain.location.structural_band)},
            {
                "label": "Dominant risk category",
                "value": policy.optional_label(domain.location.dominant_risk_category),
            },
        ],
        "business_assumptions": [
            {"label": "Monthly rent", "value": policy.money(domain.business_assumptions.monthly_rent)},
            {"label": "Fixed labor", "value": policy.money(domain.business_assumptions.fixed_labor)},
            {"label": "Fixed overhead", "value": policy.money(domain.business_assumptions.fixed_overhead)},
        ] + _business_input_rows(domain),
        "financial": [
            {"label": "Revenue — conservative", "value": policy.money(domain.financial.revenue.conservative)},
            {"label": "Revenue — base", "value": policy.money(domain.financial.revenue.base)},
            {"label": "Revenue — optimistic", "value": policy.money(domain.financial.revenue.optimistic)},
            {"label": "Variable cost — base", "value": policy.money(domain.financial.variable_cost_base)},
            {"label": "Contribution margin — base", "value": policy.money(domain.financial.contribution_margin_base)},
            {"label": "Fixed costs", "value": policy.money(domain.financial.fixed_costs)},
            {"label": "Operating profit — base", "value": policy.money(domain.financial.operating_profit_base)},
            {"label": "Break-even revenue", "value": policy.money(domain.financial.break_even_revenue)},
            {"label": "BEC — base", "value": policy.ratio(domain.financial.bec_base)},
            {"label": "BEC — conservative", "value": policy.ratio(domain.financial.bec_conservative)},
            {"label": "Rent burden", "value": policy.percent_points(domain.financial.rent_burden_pct)},
            {"label": "Rent burden severity", "value": policy.label(domain.financial.rent_burden_severity)},
            {"label": "Operating margin", "value": policy.percent_points(domain.financial.operating_margin_pct)},
            {"label": "Break-even volume", "value": policy.optional_number(domain.financial.break_even_volume)},
            {"label": "Stress test failed", "value": policy.boolean(domain.financial.stress_test_failed)},
        ],
        "decision": {
            "class": policy.label(domain.decision.decision_class),
            "headline": domain.decision.headline,
            "structural_band": policy.label(domain.decision.structural_band),
            "financial_band": policy.label(domain.decision.financial_band),
            "risk_flags": policy.risk_flags(domain.decision.risk_flags),
        },
        "confidence": [
            {"label": "Overall score", "value": policy.score(domain.confidence.overall_score)},
            {"label": "Label", "value": policy.label(domain.confidence.label)},
            {"label": "Geographic precision", "value": policy.number(domain.confidence.geographic_precision)},
            {"label": "Data vintage", "value": policy.number(domain.confidence.data_vintage)},
            {"label": "Data coverage", "value": policy.number(domain.confidence.data_coverage)},
            {"label": "Input completeness", "value": policy.number(domain.confidence.input_completeness)},
        ],
        "data_quality": {
            "geographic_level": policy.label(domain.data_quality.geographic_level),
            "data_age_years": policy.optional_number(domain.data_quality.data_age_years),
            "coverage": coverage_rows,
            "input_qualities": quality_rows,
        },
        "narrative": {
            "executive_summary": narrative.executive_summary,
            "strengths": [point.text for point in narrative.strengths],
            "risks": [point.text for point in narrative.risks],
            "recommendations": [point.text for point in narrative.recommendations],
            "caveats": list(narrative.caveats),
            "generation_mode": narrative.provenance.generation_mode,
            "provider": narrative.provenance.provider,
            "model_id": narrative.provenance.model_id or policy.unavailable_token,
        },
        "provenance": {
            "analysis_fingerprint": domain.provenance.source_analysis_fingerprint,
            "report_package_version": domain.provenance.report_package_version,
            "report_schema_version": domain.provenance.report_schema_version,
            "report_projection_version": domain.provenance.report_projection_version,
            "scoring_model_version": domain.provenance.model_versions.scoring_model_version,
            "financial_model_version": domain.provenance.model_versions.financial_model_version,
            "decision_model_version": domain.provenance.model_versions.decision_model_version,
            "confidence_model_version": domain.provenance.model_versions.confidence_model_version,
        },
        "charts": chart_map,
        "unavailable_token": policy.unavailable_token,
    }


def render_report_html(
    report_domain_model: ReportDomainModel,
    validated_narrative: ValidatedReportNarrative,
) -> str:
    """Render controlled HTML from exact canonical domain+narrative authority."""

    _require_runtime_versions()
    domain, narrative = _require_render_sources(report_domain_model, validated_narrative)
    charts = build_report_chart_assets(domain)
    template_source = _load_asset_text(RenderAsset.TEMPLATE)
    try:
        template = _jinja_environment().from_string(template_source)
        html = template.render(report=_build_presentation_view(domain, narrative, charts))
    except ReportRenderError:
        raise
    except Exception as exc:
        raise ReportRenderError("template_render_failed") from exc
    _require_render_sources(domain, narrative)
    if not html.lstrip().lower().startswith("<!doctype html>"):
        raise ReportRenderError("template_render_failed", "controlled template did not produce HTML")
    return html


def _restricted_url_fetcher(url: str, *args: object, **kwargs: object) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme != "data":
        raise ReportRenderError(
            "external_asset_forbidden", "visual report renderer allows data: assets only"
        )
    return default_url_fetcher(url, *args, **kwargs)


def render_report_pdf(
    report_domain_model: ReportDomainModel,
    validated_narrative: ValidatedReportNarrative,
) -> bytes:
    """Return in-memory PDF bytes. No report IDs, storage keys, or persistence are created."""

    _require_runtime_versions()
    domain, narrative = _require_render_sources(report_domain_model, validated_narrative)
    html = render_report_html(domain, narrative)
    stylesheet = _load_asset_text(RenderAsset.STYLESHEET)
    try:
        pdf = HTML(string=html, url_fetcher=_restricted_url_fetcher).write_pdf(
            stylesheets=[CSS(string=stylesheet)]
        )
    except ReportRenderError:
        raise
    except Exception as exc:
        raise ReportRenderError("pdf_render_failed") from exc
    _require_render_sources(domain, narrative)
    if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-") or len(pdf) < 1024:
        raise ReportRenderError("invalid_pdf_output")
    return pdf


__all__ = [
    "PRESENTATION_SCHEMA_VERSION",
    "PRESENTATION_POLICY_VERSION",
    "TEMPLATE_VERSION",
    "STYLESHEET_VERSION",
    "CHART_VERSION",
    "RENDERER_VERSION",
    "JINJA2_RUNTIME_VERSION",
    "MATPLOTLIB_RUNTIME_VERSION",
    "WEASYPRINT_RUNTIME_VERSION",
    "UNAVAILABLE_TOKEN",
    "ReportRenderError",
    "RenderAsset",
    "PresentationPolicy",
    "DEFAULT_PRESENTATION_POLICY",
    "ReportChartAsset",
    "build_report_chart_assets",
    "render_report_html",
    "render_report_pdf",
]
