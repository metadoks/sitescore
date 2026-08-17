from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

REPO_ROOT = Path(__file__).resolve().parents[2]


PREFIX = r'''
from __future__ import annotations

import copy
import dataclasses
import inspect
import json
from datetime import datetime, timezone

import sitescore_pipeline
from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
from sitescore.schemas.revenue_inputs import BeautyRevenueInput, CoffeeRevenueInput, GymRevenueInput, RestaurantRevenueInput
from sitescore_data.enums import AvailabilityState, CalibrationState, DataQualityState, PipelineStatus, ScoreEligibility
from sitescore_data.feature_surface import NORMALIZED_FEATURE_NAMES
from sitescore_data.schemas.common import DataContractVersions, MetricValue
from sitescore_data.schemas.features import DerivedLocationMetrics, NormalizedLocationFeatures
from sitescore_data.schemas.geography import ResolvedLocation
from sitescore_data.schemas.pipeline import RealDataPipelineResult
from sitescore_data.schemas.readiness import ScoringFeatureReadiness, ScoringReadinessResult
from sitescore_data.validation import SectorKey

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
SOURCE_REF = "test.source"


def metric(value, unit="score_0_100"):
    return MetricValue(
        value=value,
        unit=unit,
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=CalibrationState.CALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=(SOURCE_REF,),
        method_version="test/1",
        reason_codes=(),
    )


def terminal(sector: str, score: float) -> RealDataPipelineResult:
    contracts = DataContractVersions.current()
    derived = DerivedLocationMetrics(
        walkable_population=metric(1000.0, "people"),
        target_population_density=metric(50.0, "people_per_km2"),
        household_income=metric(75000.0, "usd"),
        household_income_ratio=metric(1.1, "ratio"),
        competition_pressure=metric(0.4, "pressure_index"),
        walkable_reach_area_km2=metric(2.0, "km2"),
        transit_service_departure_equivalents_per_hour=metric(10.0, "departures_per_hour"),
        road_reachable_area_km2=metric(3.0, "km2"),
        parking_public_offstreet_capacity=metric(100.0, "spaces"),
        parking_legal_curb_length_m=metric(250.0, "m"),
        demographic_snapshot_ref=None,
        competition_snapshot_ref=None,
        road_snapshot_ref=None,
        parking_snapshot_ref=None,
        source_refs=(SOURCE_REF,),
        feature_contract_version=contracts.data_feature_contract_version,
        generated_at=T0,
    )
    normalized = NormalizedLocationFeatures(
        walkable_population_score=metric(score),
        target_population_density_score=metric(score),
        age_target_concentration_score=metric(score),
        competition_opportunity_score=metric(score),
        walkable_reach_area_score=metric(score),
        transit_access_score=metric(score),
        road_parking_access_score=metric(score),
        household_income_score=metric(score),
        competition_benchmark_ref=None,
        competition_measurement_definition_id=None,
        competition_normalization_policy_version=None,
        transit_benchmark_ref=None,
        transit_source_bundle_fingerprint=None,
        transit_normalization_policy_version=None,
        road_parking_composite_policy_version="test/1",
        source_refs=(SOURCE_REF,),
        feature_contract_version=contracts.data_feature_contract_version,
        generated_at=T0,
    )
    states = tuple(
        ScoringFeatureReadiness(
            feature_name=name,
            required=True,
            availability=AvailabilityState.AVAILABLE,
            data_quality=DataQualityState.FULL,
            score_eligibility=ScoreEligibility.ELIGIBLE,
            calibration_state=CalibrationState.CALIBRATED,
            required_policy_version=None,
            resolved_policy_version=None,
            fallback_policy_id=None,
            fallback_policy_version=None,
            reason_codes=(),
        )
        for name in NORMALIZED_FEATURE_NAMES
    )
    readiness = ScoringReadinessResult(
        is_score_ready=True,
        missing_required_features=(),
        uncalibrated_features=(),
        insufficient_quality_features=(),
        incompatible_features=(),
        reason_codes=(),
        required_policy_versions=(),
        resolved_policy_versions=(),
        feature_states=states,
        validator_version="test/1",
        evaluated_at=T0,
        readiness_fingerprint=f"test.readiness.{sector}.{score}",
    )
    location = ResolvedLocation(
        latitude=30.2672,
        longitude=-97.7431,
        formatted_address="100 Congress Ave, Austin, TX 78701",
        country_code="US",
        geography_refs=(),
        source_refs=(SOURCE_REF,),
        resolution_method_version="test/1",
        generated_at=T0,
    )
    return RealDataPipelineResult(
        status=PipelineStatus.SCORE_READY,
        sector_key=SectorKey(sector),
        resolved_location=location,
        demographics=None,
        pedestrian_catchment=None,
        isochrone=None,
        competition=None,
        transit=None,
        road=None,
        parking=None,
        derived_metrics=derived,
        normalized_features=normalized,
        scoring_readiness=readiness,
        source_metadata=(),
        pipeline_version="test/1",
        data_contract_versions=contracts,
        generated_at=T0,
        reason_codes=(),
    )


TERMINALS = []
def test_terminal_factory(**_kwargs):
    return TERMINALS.pop(0)

# Patch only the upstream test boundary before sitescore_app captures its frozen terminal factory.
# Positive report authority still comes exclusively from public application factories.
sitescore_pipeline.build_real_data_pipeline_result = test_terminal_factory

from sitescore_app import (
    ApplicationAnalysisResult,
    aggregate_application_category_scores,
    analyze_application_core_input,
    build_application_core_analysis_input,
    build_application_pipeline_result,
    build_application_scoring_input,
    require_canonical_application_analysis_result,
)
from sitescore_report import (
    CanonicalReportFacts,
    ReportDomainModel,
    REPORT_PACKAGE_VERSION,
    REPORT_PROJECTION_VERSION,
    REPORT_SCHEMA_VERSION,
    build_canonical_report_facts,
    build_report_domain_model,
    require_canonical_report_domain_model,
    require_canonical_report_facts,
)

REVENUE = {
    "coffee": CoffeeRevenueInput(10000.0, .55, .01, .02, .03, 3.0, 8.75),
    "restaurant": RestaurantRevenueInput(80, 2.4, .45, .62, .80, 31.25, 30),
    "gym": GymRevenueInput(30000.0, .01, .025, .04, 1600.0, .12, 59.95),
    "beauty": BeautyRevenueInput(8, 48.0, 1.25, .45, .62, .80, 72.5),
}


def build_scored(
    sector: str,
    *,
    score: float = 80.0,
    monthly_rent: float = 1234.56789,
    fixed_labor: float = 2000.125,
    fixed_overhead: float = 500.375,
    geographic_level=GeographicLevel.TRACT,
    data_age_years=1,
    data_coverage=None,
    input_qualities=None,
):
    TERMINALS.append(terminal(sector, score))
    pipeline = build_application_pipeline_result(
        readiness=None,
        sector_key=None,
        resolved_location=None,
        derived_metrics=None,
        source_metadata=(),
        generated_at=None,
    )
    scoring = build_application_scoring_input(pipeline)
    category = aggregate_application_category_scores(scoring)
    core_input = build_application_core_analysis_input(
        category,
        revenue_input=REVENUE[sector],
        monthly_rent=monthly_rent,
        fixed_labor=fixed_labor,
        fixed_overhead=fixed_overhead,
        geographic_level=geographic_level,
        data_age_years=data_age_years,
        data_coverage=(
            {k: CoverageLevel.FULL for k in ("demand", "competition", "accessibility", "economics")}
            if data_coverage is None else data_coverage
        ),
        input_qualities=(
            {k: InputQuality.USER for k in ("rent", "price", "capacity", "schedule")}
            if input_qualities is None else input_qualities
        ),
    )
    result = analyze_application_core_input(core_input)
    assert require_canonical_application_analysis_result(result) is result
    return result
'''


def _run(body: str) -> None:
    script = textwrap.dedent(PREFIX + "\n" + body)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_four_sector_exact_fidelity_and_json_deep_ownership():
    _run(r'''
for sector in ("coffee", "restaurant", "gym", "beauty"):
    source = build_scored(sector)
    facts = build_canonical_report_facts(source)
    domain = build_report_domain_model(facts)
    assert require_canonical_report_facts(facts) is facts
    assert require_canonical_report_domain_model(domain) is domain
    assert domain.canonical_facts is facts

    analysis_input = source.application_core_input.analysis_input
    core = source.core_result

    assert facts.provenance.report_package_version == REPORT_PACKAGE_VERSION == "0.2.0"
    assert facts.provenance.report_schema_version == REPORT_SCHEMA_VERSION
    assert facts.provenance.report_projection_version == REPORT_PROJECTION_VERSION
    assert facts.provenance.source_analysis_fingerprint == core.analysis_fingerprint

    for field in dataclasses.fields(core.model_versions):
        assert getattr(facts.provenance.model_versions, field.name) == getattr(core.model_versions, field.name)

    assert facts.analysis.sector is analysis_input.sector
    for name in ("demand", "competition", "accessibility", "economics"):
        assert getattr(facts.category_scores, name) == getattr(analysis_input.category_scores, name)

    assert facts.business_assumptions.monthly_rent == analysis_input.monthly_rent
    assert facts.business_assumptions.fixed_labor == analysis_input.fixed_labor
    assert facts.business_assumptions.fixed_overhead == analysis_input.fixed_overhead
    revenue_facts = facts.business_assumptions.revenue_input
    assert revenue_facts.kind == sector
    for field in dataclasses.fields(analysis_input.revenue_input):
        assert getattr(revenue_facts, field.name) == getattr(analysis_input.revenue_input, field.name)

    for name in ("base_score", "penalty_multiplier", "final_score", "structural_band", "dominant_risk_category"):
        assert getattr(facts.location, name) == getattr(core.location, name)
    for name in (
        "variable_cost_base", "contribution_margin_base", "fixed_costs", "operating_profit_base",
        "break_even_revenue", "bec_base", "bec_conservative", "rent_burden_pct",
        "rent_burden_severity", "operating_margin_pct", "break_even_volume", "stress_test_failed",
    ):
        assert getattr(facts.financial, name) == getattr(core.financial, name)
    for name in ("conservative", "base", "optimistic"):
        assert getattr(facts.financial.revenue, name) == getattr(core.financial.revenue, name)
    for name in ("decision_class", "structural_band", "financial_band", "headline", "risk_flags"):
        assert getattr(facts.decision, name) == getattr(core.decision, name)
    for name in ("overall_score", "label", "geographic_precision", "data_vintage", "data_coverage", "input_completeness"):
        assert getattr(facts.confidence, name) == getattr(core.confidence, name)

    assert facts.data_quality.geographic_level is analysis_input.geographic_level
    assert facts.data_quality.data_age_years == analysis_input.data_age_years
    assert dict(facts.data_quality.data_coverage) == analysis_input.data_coverage
    assert dict(facts.data_quality.input_qualities) == analysis_input.input_qualities

    view = facts.to_dict()
    json.dumps(view, allow_nan=False)
    assert view["provenance"]["source_analysis_fingerprint"] == core.analysis_fingerprint
    assert "analysis_id" not in repr(view)
    assert "report_id" not in repr(view)
    view["category_scores"]["demand"] = -999
    view["decision"]["risk_flags"].append("FORGED")
    view["data_quality"]["data_coverage"]["demand"] = "forged"
    assert facts.category_scores.demand == analysis_input.category_scores.demand
    assert facts.decision.risk_flags == core.decision.risk_flags
    assert facts.data_quality.data_coverage.get("demand") is analysis_input.data_coverage.get("demand")

    domain_view = domain.to_dict()
    domain_view["business_assumptions"]["monthly_rent"] = -1
    assert domain.business_assumptions.monthly_rent == analysis_input.monthly_rent
''')


def test_report_authority_rejects_detached_forged_and_substituted_values():
    _run(r'''
source = build_scored("coffee")
facts = build_canonical_report_facts(source)
domain = build_report_domain_model(facts)
core = source.core_result

assert list(inspect.signature(build_canonical_report_facts).parameters) == ["application_analysis_result"]
assert list(inspect.signature(build_report_domain_model).parameters) == ["canonical_facts"]

for detached in (core, core.to_dict(), core.analysis_fingerprint):
    try:
        build_canonical_report_facts(detached)
    except TypeError:
        pass
    else:
        raise AssertionError("detached core material must not grant report authority")

manual_source = object.__new__(ApplicationAnalysisResult)
object.__setattr__(manual_source, "_application_core_input", source.application_core_input)
object.__setattr__(manual_source, "_core_result", source.core_result)
try:
    build_canonical_report_facts(manual_source)
except ValueError:
    pass
else:
    raise AssertionError("forged ApplicationAnalysisResult shell must be rejected")

for copier in (copy.copy, copy.deepcopy):
    try:
        candidate = copier(facts)
    except Exception:
        continue
    try:
        require_canonical_report_facts(candidate)
    except ValueError:
        pass
    else:
        raise AssertionError("copied report facts must not become authority")

manual_facts = object.__new__(CanonicalReportFacts)
for name in ("provenance", "analysis", "category_scores", "business_assumptions", "location", "financial", "decision", "confidence", "data_quality"):
    object.__setattr__(manual_facts, name, getattr(facts, name))
try:
    require_canonical_report_facts(manual_facts)
except ValueError:
    pass
else:
    raise AssertionError("manual equal-value report facts must be rejected")

original_location = facts.location
replacement_location = dataclasses.replace(original_location)
object.__setattr__(facts, "location", replacement_location)
try:
    require_canonical_report_facts(facts)
except ValueError:
    pass
else:
    raise AssertionError("equal-value nested section substitution must fail closed")
object.__setattr__(facts, "location", original_location)
assert require_canonical_report_facts(facts) is facts

original_score = facts.location.base_score
object.__setattr__(facts.location, "base_score", original_score + 1.0)
try:
    require_canonical_report_facts(facts)
except ValueError:
    pass
else:
    raise AssertionError("nested semantic mutation must fail closed")
object.__setattr__(facts.location, "base_score", original_score)
assert require_canonical_report_facts(facts) is facts

for copier in (copy.copy, copy.deepcopy):
    try:
        candidate = copier(domain)
    except Exception:
        continue
    try:
        require_canonical_report_domain_model(candidate)
    except ValueError:
        pass
    else:
        raise AssertionError("copied report domain must not become authority")

other = build_canonical_report_facts(build_scored("gym"))
original_facts = domain._canonical_facts
object.__setattr__(domain, "_canonical_facts", other)
try:
    require_canonical_report_domain_model(domain)
except ValueError:
    pass
else:
    raise AssertionError("domain source-facts substitution must fail closed")
object.__setattr__(domain, "_canonical_facts", original_facts)
assert require_canonical_report_domain_model(domain) is domain
''')


def test_missingness_partial_context_and_adversarial_results_are_not_improved():
    _run(r'''
strong = build_scored(
    "coffee",
    score=95.0,
    monthly_rent=200.0,
    fixed_labor=200.0,
    fixed_overhead=100.0,
)
strong_facts = build_canonical_report_facts(strong)
assert strong.core_result.location.dominant_risk_category is None
assert strong_facts.location.dominant_risk_category is None
assert strong_facts.decision.risk_flags == strong.core_result.decision.risk_flags
assert strong_facts.decision.risk_flags == ()

low_conf = build_scored(
    "gym",
    score=72.0,
    geographic_level=GeographicLevel.UNKNOWN,
    data_age_years=None,
    data_coverage={"demand": CoverageLevel.DEGRADED},
    input_qualities={"rent": InputQuality.DEFAULT},
)
low_conf_facts = build_canonical_report_facts(low_conf)
assert low_conf_facts.data_quality.data_age_years is None
assert dict(low_conf_facts.data_quality.data_coverage) == {"demand": CoverageLevel.DEGRADED}
assert dict(low_conf_facts.data_quality.input_qualities) == {"rent": InputQuality.DEFAULT}
assert low_conf_facts.confidence.label == low_conf.core_result.confidence.label
assert low_conf_facts.confidence.overall_score == low_conf.core_result.confidence.overall_score
assert low_conf.core_result.confidence.label == "low"

weak = build_scored(
    "restaurant",
    score=5.0,
    monthly_rent=500000.0,
    fixed_labor=500000.0,
    fixed_overhead=250000.0,
)
weak_facts = build_canonical_report_facts(weak)
assert weak.core_result.financial.stress_test_failed is True
assert weak_facts.financial.stress_test_failed is True
assert weak_facts.decision.decision_class == weak.core_result.decision.decision_class
assert weak_facts.decision.headline == weak.core_result.decision.headline
assert weak_facts.decision.risk_flags == weak.core_result.decision.risk_flags
assert weak_facts.location.final_score == weak.core_result.location.final_score
assert weak_facts.location.final_score < strong_facts.location.final_score
''')
