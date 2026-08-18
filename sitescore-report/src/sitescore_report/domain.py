from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any
from weakref import ref

from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
from sitescore.config.sectors import Sector
from sitescore.schemas.revenue_inputs import (
    BeautyRevenueInput,
    CoffeeRevenueInput,
    GymRevenueInput,
    RestaurantRevenueInput,
)
from sitescore_app import (
    ApplicationAnalysisResult,
    require_canonical_application_analysis_result,
)

REPORT_PACKAGE_VERSION = "0.2.0"
REPORT_SCHEMA_VERSION = "sitescore-report-v1"
REPORT_PROJECTION_VERSION = "application-analysis-result-v1"


@dataclass(frozen=True, slots=True)
class ReportModelVersionsFacts:
    package_version: str
    canonical_schema_version: str
    feature_schema_version: str
    scoring_model_version: str
    financial_model_version: str
    decision_model_version: str
    confidence_model_version: str


@dataclass(frozen=True, slots=True)
class ReportProvenanceFacts:
    report_package_version: str
    report_schema_version: str
    report_projection_version: str
    source_analysis_fingerprint: str
    model_versions: ReportModelVersionsFacts


@dataclass(frozen=True, slots=True)
class ReportAnalysisFacts:
    sector: Sector


@dataclass(frozen=True, slots=True)
class ReportCategoryScoresFacts:
    demand: float
    competition: float
    accessibility: float
    economics: float


@dataclass(frozen=True, slots=True)
class CoffeeBusinessInputFacts:
    kind: str
    target_population: float
    target_rate: float
    capture_rate_conservative: float
    capture_rate_base: float
    capture_rate_optimistic: float
    visit_frequency_per_month: float
    average_ticket: float


@dataclass(frozen=True, slots=True)
class RestaurantBusinessInputFacts:
    kind: str
    seats: int
    turnover_per_day: float
    utilization_conservative: float
    utilization_base: float
    utilization_optimistic: float
    average_ticket: float
    operating_days_per_month: int


@dataclass(frozen=True, slots=True)
class GymBusinessInputFacts:
    kind: str
    target_population: float
    penetration_rate_conservative: float
    penetration_rate_base: float
    penetration_rate_optimistic: float
    usable_area: float
    members_per_area_unit: float
    monthly_membership_fee: float


@dataclass(frozen=True, slots=True)
class BeautyBusinessInputFacts:
    kind: str
    stations: int
    operating_hours_per_week: float
    average_service_duration_hours: float
    utilization_conservative: float
    utilization_base: float
    utilization_optimistic: float
    average_ticket: float


RevenueInputFacts = (
    CoffeeBusinessInputFacts
    | RestaurantBusinessInputFacts
    | GymBusinessInputFacts
    | BeautyBusinessInputFacts
)


@dataclass(frozen=True, slots=True)
class ReportBusinessAssumptionsFacts:
    monthly_rent: float
    fixed_labor: float
    fixed_overhead: float
    revenue_input: RevenueInputFacts


@dataclass(frozen=True, slots=True)
class ReportLocationFacts:
    base_score: float
    penalty_multiplier: float
    final_score: float
    structural_band: str
    dominant_risk_category: str | None


@dataclass(frozen=True, slots=True)
class ReportRevenueFacts:
    conservative: float
    base: float
    optimistic: float


@dataclass(frozen=True, slots=True)
class ReportFinancialFacts:
    revenue: ReportRevenueFacts
    variable_cost_base: float
    contribution_margin_base: float
    fixed_costs: float
    operating_profit_base: float
    break_even_revenue: float
    bec_base: float
    bec_conservative: float
    rent_burden_pct: float
    rent_burden_severity: str
    operating_margin_pct: float
    break_even_volume: float | None
    stress_test_failed: bool


@dataclass(frozen=True, slots=True)
class ReportDecisionFacts:
    decision_class: str
    structural_band: str
    financial_band: str
    headline: str
    risk_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportConfidenceFacts:
    overall_score: float
    label: str
    geographic_precision: float
    data_vintage: float
    data_coverage: float
    input_completeness: float


@dataclass(frozen=True, slots=True)
class ReportDataQualityFacts:
    geographic_level: GeographicLevel
    data_age_years: int | None
    data_coverage: Mapping[str, CoverageLevel]
    input_qualities: Mapping[str, InputQuality]


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class CanonicalReportFacts:
    """Factory-owned truth-preserving projection of one canonical application result."""

    provenance: ReportProvenanceFacts
    analysis: ReportAnalysisFacts
    category_scores: ReportCategoryScoresFacts
    business_assumptions: ReportBusinessAssumptionsFacts
    location: ReportLocationFacts
    financial: ReportFinancialFacts
    decision: ReportDecisionFacts
    confidence: ReportConfidenceFacts
    data_quality: ReportDataQualityFacts

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "CanonicalReportFacts is factory-owned; use build_canonical_report_facts"
        )

    def to_dict(self) -> dict[str, Any]:
        require_canonical_report_facts(self)
        return {
            "provenance": _json_safe(self.provenance),
            "analysis": _json_safe(self.analysis),
            "category_scores": _json_safe(self.category_scores),
            "business_assumptions": _json_safe(self.business_assumptions),
            "location": _json_safe(self.location),
            "financial": _json_safe(self.financial),
            "decision": _json_safe(self.decision),
            "confidence": _json_safe(self.confidence),
            "data_quality": _json_safe(self.data_quality),
        }


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ReportDomainModel:
    """Factory-owned report-consumption organization over exact canonical facts."""

    _canonical_facts: CanonicalReportFacts
    provenance: ReportProvenanceFacts
    analysis: ReportAnalysisFacts
    category_scores: ReportCategoryScoresFacts
    business_assumptions: ReportBusinessAssumptionsFacts
    location: ReportLocationFacts
    financial: ReportFinancialFacts
    decision: ReportDecisionFacts
    confidence: ReportConfidenceFacts
    data_quality: ReportDataQualityFacts

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ReportDomainModel is factory-owned; use build_report_domain_model"
        )

    @property
    def canonical_facts(self) -> CanonicalReportFacts:
        require_canonical_report_domain_model(self)
        return self._canonical_facts

    def to_dict(self) -> dict[str, Any]:
        require_canonical_report_domain_model(self)
        return {
            "provenance": _json_safe(self.provenance),
            "analysis": _json_safe(self.analysis),
            "category_scores": _json_safe(self.category_scores),
            "business_assumptions": _json_safe(self.business_assumptions),
            "location": _json_safe(self.location),
            "financial": _json_safe(self.financial),
            "decision": _json_safe(self.decision),
            "confidence": _json_safe(self.confidence),
            "data_quality": _json_safe(self.data_quality),
        }


def _json_safe(value: object) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_safe(getattr(value, field.name))
            for field in fields(value)
            if not field.name.startswith("_")
        }
    raise TypeError(
        "unsupported report projection value: "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def _semantic_record(value: object) -> object:
    if value is None:
        return ("none",)
    if isinstance(value, Enum):
        value_type = type(value)
        return (
            "enum",
            value_type.__module__,
            value_type.__qualname__,
            _semantic_record(value.value),
        )
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", value.hex())
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, Mapping):
        items = [
            (_semantic_record(key), _semantic_record(item))
            for key, item in value.items()
        ]
        items.sort(key=repr)
        return ("mapping", tuple(items))
    if isinstance(value, tuple):
        return ("tuple", tuple(_semantic_record(item) for item in value))
    if isinstance(value, list):
        return ("list", tuple(_semantic_record(item) for item in value))
    if is_dataclass(value) and not isinstance(value, type):
        value_type = type(value)
        return (
            "dataclass",
            value_type.__module__,
            value_type.__qualname__,
            tuple(
                (field.name, _semantic_record(getattr(value, field.name)))
                for field in fields(value)
            ),
        )
    raise TypeError(
        "unsupported authority-bearing report value: "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def _project_revenue_input(value: object) -> RevenueInputFacts:
    if isinstance(value, CoffeeRevenueInput):
        return CoffeeBusinessInputFacts(
            kind="coffee",
            target_population=value.target_population,
            target_rate=value.target_rate,
            capture_rate_conservative=value.capture_rate_conservative,
            capture_rate_base=value.capture_rate_base,
            capture_rate_optimistic=value.capture_rate_optimistic,
            visit_frequency_per_month=value.visit_frequency_per_month,
            average_ticket=value.average_ticket,
        )
    if isinstance(value, RestaurantRevenueInput):
        return RestaurantBusinessInputFacts(
            kind="restaurant",
            seats=value.seats,
            turnover_per_day=value.turnover_per_day,
            utilization_conservative=value.utilization_conservative,
            utilization_base=value.utilization_base,
            utilization_optimistic=value.utilization_optimistic,
            average_ticket=value.average_ticket,
            operating_days_per_month=value.operating_days_per_month,
        )
    if isinstance(value, GymRevenueInput):
        return GymBusinessInputFacts(
            kind="gym",
            target_population=value.target_population,
            penetration_rate_conservative=value.penetration_rate_conservative,
            penetration_rate_base=value.penetration_rate_base,
            penetration_rate_optimistic=value.penetration_rate_optimistic,
            usable_area=value.usable_area,
            members_per_area_unit=value.members_per_area_unit,
            monthly_membership_fee=value.monthly_membership_fee,
        )
    if isinstance(value, BeautyRevenueInput):
        return BeautyBusinessInputFacts(
            kind="beauty",
            stations=value.stations,
            operating_hours_per_week=value.operating_hours_per_week,
            average_service_duration_hours=value.average_service_duration_hours,
            utilization_conservative=value.utilization_conservative,
            utilization_base=value.utilization_base,
            utilization_optimistic=value.utilization_optimistic,
            average_ticket=value.average_ticket,
        )
    raise TypeError("canonical AnalysisInput carries an unsupported revenue input")


def _install_report_factories():
    fact_bindings: dict[int, tuple[object, ...]] = {}
    domain_bindings: dict[int, tuple[object, ...]] = {}
    section_names = (
        "provenance",
        "analysis",
        "category_scores",
        "business_assumptions",
        "location",
        "financial",
        "decision",
        "confidence",
        "data_quality",
    )

    def register_facts(
        value: CanonicalReportFacts,
        source: ApplicationAnalysisResult,
        application_core_input: object,
        analysis_input: object,
        core_result: object,
    ) -> None:
        object_id = id(value)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            fact_bindings.pop(object_id, None)

        fact_bindings[object_id] = (
            ref(value, cleanup),
            source,
            application_core_input,
            analysis_input,
            core_result,
            tuple(getattr(value, name) for name in section_names),
            _semantic_record(value),
        )

    def resolve_facts(value: CanonicalReportFacts) -> tuple[object, ...]:
        if not isinstance(value, CanonicalReportFacts):
            raise TypeError("value must be CanonicalReportFacts")
        binding = fact_bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("report facts are not canonical/factory-owned")

        source = binding[1]
        require_canonical_application_analysis_result(source)
        current_core_input = source.application_core_input
        current_analysis_input = current_core_input.analysis_input
        current_core_result = source.core_result
        if current_core_input is not binding[2]:
            raise ValueError("report facts source application-input binding changed")
        if current_analysis_input is not binding[3]:
            raise ValueError("report facts source AnalysisInput binding changed")
        if current_core_result is not binding[4]:
            raise ValueError("report facts source canonical-result binding changed")

        expected_sections = binding[5]
        for name, expected in zip(section_names, expected_sections, strict=True):
            if getattr(value, name) is not expected:
                raise ValueError(f"report facts {name} identity integrity violation")
        if _semantic_record(value) != binding[6]:
            raise ValueError("report facts semantic integrity violation")
        return binding

    def build_facts(
        application_analysis_result: ApplicationAnalysisResult,
    ) -> CanonicalReportFacts:
        source = require_canonical_application_analysis_result(
            application_analysis_result
        )
        application_core_input = source.application_core_input
        analysis_input = application_core_input.analysis_input
        core_result = source.core_result
        model_versions = core_result.model_versions

        provenance = ReportProvenanceFacts(
            report_package_version=REPORT_PACKAGE_VERSION,
            report_schema_version=REPORT_SCHEMA_VERSION,
            report_projection_version=REPORT_PROJECTION_VERSION,
            source_analysis_fingerprint=core_result.analysis_fingerprint,
            model_versions=ReportModelVersionsFacts(
                package_version=model_versions.package_version,
                canonical_schema_version=model_versions.canonical_schema_version,
                feature_schema_version=model_versions.feature_schema_version,
                scoring_model_version=model_versions.scoring_model_version,
                financial_model_version=model_versions.financial_model_version,
                decision_model_version=model_versions.decision_model_version,
                confidence_model_version=model_versions.confidence_model_version,
            ),
        )
        analysis = ReportAnalysisFacts(sector=analysis_input.sector)
        category_scores = ReportCategoryScoresFacts(
            demand=analysis_input.category_scores.demand,
            competition=analysis_input.category_scores.competition,
            accessibility=analysis_input.category_scores.accessibility,
            economics=analysis_input.category_scores.economics,
        )
        business_assumptions = ReportBusinessAssumptionsFacts(
            monthly_rent=analysis_input.monthly_rent,
            fixed_labor=analysis_input.fixed_labor,
            fixed_overhead=analysis_input.fixed_overhead,
            revenue_input=_project_revenue_input(analysis_input.revenue_input),
        )
        location_result = core_result.location
        location = ReportLocationFacts(
            base_score=location_result.base_score,
            penalty_multiplier=location_result.penalty_multiplier,
            final_score=location_result.final_score,
            structural_band=location_result.structural_band,
            dominant_risk_category=location_result.dominant_risk_category,
        )
        financial_result = core_result.financial
        financial = ReportFinancialFacts(
            revenue=ReportRevenueFacts(
                conservative=financial_result.revenue.conservative,
                base=financial_result.revenue.base,
                optimistic=financial_result.revenue.optimistic,
            ),
            variable_cost_base=financial_result.variable_cost_base,
            contribution_margin_base=financial_result.contribution_margin_base,
            fixed_costs=financial_result.fixed_costs,
            operating_profit_base=financial_result.operating_profit_base,
            break_even_revenue=financial_result.break_even_revenue,
            bec_base=financial_result.bec_base,
            bec_conservative=financial_result.bec_conservative,
            rent_burden_pct=financial_result.rent_burden_pct,
            rent_burden_severity=financial_result.rent_burden_severity,
            operating_margin_pct=financial_result.operating_margin_pct,
            break_even_volume=financial_result.break_even_volume,
            stress_test_failed=financial_result.stress_test_failed,
        )
        decision_result = core_result.decision
        decision = ReportDecisionFacts(
            decision_class=decision_result.decision_class,
            structural_band=decision_result.structural_band,
            financial_band=decision_result.financial_band,
            headline=decision_result.headline,
            risk_flags=tuple(decision_result.risk_flags),
        )
        confidence_result = core_result.confidence
        confidence = ReportConfidenceFacts(
            overall_score=confidence_result.overall_score,
            label=confidence_result.label,
            geographic_precision=confidence_result.geographic_precision,
            data_vintage=confidence_result.data_vintage,
            data_coverage=confidence_result.data_coverage,
            input_completeness=confidence_result.input_completeness,
        )
        data_quality = ReportDataQualityFacts(
            geographic_level=analysis_input.geographic_level,
            data_age_years=analysis_input.data_age_years,
            data_coverage=MappingProxyType(dict(analysis_input.data_coverage)),
            input_qualities=MappingProxyType(dict(analysis_input.input_qualities)),
        )

        require_canonical_application_analysis_result(source)
        if source.application_core_input is not application_core_input:
            raise ValueError("application analysis input changed during report projection")
        if application_core_input.analysis_input is not analysis_input:
            raise ValueError("AnalysisInput changed during report projection")
        if source.core_result is not core_result:
            raise ValueError("canonical result changed during report projection")

        value = object.__new__(CanonicalReportFacts)
        for name, section in (
            ("provenance", provenance),
            ("analysis", analysis),
            ("category_scores", category_scores),
            ("business_assumptions", business_assumptions),
            ("location", location),
            ("financial", financial),
            ("decision", decision),
            ("confidence", confidence),
            ("data_quality", data_quality),
        ):
            object.__setattr__(value, name, section)
        register_facts(
            value,
            source,
            application_core_input,
            analysis_input,
            core_result,
        )
        return value

    def require_facts(value: CanonicalReportFacts) -> CanonicalReportFacts:
        resolve_facts(value)
        return value

    def register_domain(
        value: ReportDomainModel,
        canonical_facts: CanonicalReportFacts,
    ) -> None:
        object_id = id(value)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            domain_bindings.pop(object_id, None)

        domain_bindings[object_id] = (
            ref(value, cleanup),
            canonical_facts,
            tuple(getattr(value, name) for name in section_names),
            _semantic_record(value),
        )

    def resolve_domain(value: ReportDomainModel) -> tuple[object, ...]:
        if not isinstance(value, ReportDomainModel):
            raise TypeError("value must be ReportDomainModel")
        binding = domain_bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError("report domain model is not canonical/factory-owned")
        canonical_facts = binding[1]
        require_facts(canonical_facts)
        if value._canonical_facts is not canonical_facts:
            raise ValueError("report domain canonical-facts binding integrity violation")
        for name, expected in zip(section_names, binding[2], strict=True):
            if getattr(value, name) is not expected:
                raise ValueError(f"report domain {name} identity integrity violation")
        if _semantic_record(value) != binding[3]:
            raise ValueError("report domain semantic integrity violation")
        return binding

    def build_domain(canonical_facts: CanonicalReportFacts) -> ReportDomainModel:
        facts = require_facts(canonical_facts)
        value = object.__new__(ReportDomainModel)
        object.__setattr__(value, "_canonical_facts", facts)
        for name in section_names:
            object.__setattr__(value, name, getattr(facts, name))
        register_domain(value, facts)
        return value

    def require_domain(value: ReportDomainModel) -> ReportDomainModel:
        resolve_domain(value)
        return value

    return build_facts, require_facts, build_domain, require_domain


(
    build_canonical_report_facts,
    require_canonical_report_facts,
    build_report_domain_model,
    require_canonical_report_domain_model,
) = _install_report_factories()
del _install_report_factories


__all__ = [
    "REPORT_PACKAGE_VERSION",
    "REPORT_SCHEMA_VERSION",
    "REPORT_PROJECTION_VERSION",
    "ReportModelVersionsFacts",
    "ReportProvenanceFacts",
    "ReportAnalysisFacts",
    "ReportCategoryScoresFacts",
    "CoffeeBusinessInputFacts",
    "RestaurantBusinessInputFacts",
    "GymBusinessInputFacts",
    "BeautyBusinessInputFacts",
    "RevenueInputFacts",
    "ReportBusinessAssumptionsFacts",
    "ReportLocationFacts",
    "ReportRevenueFacts",
    "ReportFinancialFacts",
    "ReportDecisionFacts",
    "ReportConfidenceFacts",
    "ReportDataQualityFacts",
    "CanonicalReportFacts",
    "ReportDomainModel",
    "build_canonical_report_facts",
    "require_canonical_report_facts",
    "build_report_domain_model",
    "require_canonical_report_domain_model",
]
