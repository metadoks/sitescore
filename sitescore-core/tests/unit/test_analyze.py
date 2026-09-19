import pytest

from sitescore.analyze import analyze
from sitescore.config.sectors import Sector
from sitescore.schemas.analysis import AnalysisInput
from sitescore.schemas.location import CategoryScores
from sitescore.schemas.canonical import CanonicalAnalysisResult
from sitescore.schemas.revenue_inputs import (
    CoffeeRevenueInput,
    RestaurantRevenueInput,
)
from sitescore.config.quality_levels import (
    CoverageLevel,
    GeographicLevel,
    InputQuality,
)

def make_input() -> AnalysisInput:
    return AnalysisInput(
        sector=Sector.COFFEE,

        category_scores=CategoryScores(
            demand=90,
            competition=60,
            accessibility=95,
            economics=20,
        ),

        # Revenue artık hazır sayı olarak verilmiyor.
        # Coffee Revenue Engine bunu hesaplıyor.
        #
        # Conservative:
        # 100000 × .25 × .015 × 4 × $8 = $12,000
        #
        # Base:
        # 100000 × .25 × .04 × 4 × $8 = $32,000
        #
        # Optimistic:
        # 100000 × .25 × .05625 × 4 × $8 = $45,000
        revenue_input=CoffeeRevenueInput(
            target_population=100000,
            target_rate=0.25,
            capture_rate_conservative=0.015,
            capture_rate_base=0.04,
            capture_rate_optimistic=0.05625,
            visit_frequency_per_month=4,
            average_ticket=8,
        ),

        monthly_rent=4000,
        fixed_labor=6000,
        fixed_overhead=1500,

        geographic_level=GeographicLevel.TRACT,
        data_age_years=2,

        data_coverage={
          "demand": CoverageLevel.FULL,
         "competition": CoverageLevel.DEGRADED,
         "accessibility": CoverageLevel.FULL,
         "economics": CoverageLevel.FULL,
            },

        input_qualities={
    "rent": InputQuality.USER,
    "price": InputQuality.USER,
    "capacity": InputQuality.DEFAULT,
    "schedule": InputQuality.DEFAULT,
},
    )


def test_analyze_returns_canonical_result():
    result = analyze(make_input())

    assert isinstance(
        result,
        CanonicalAnalysisResult,
    )


def test_analyze_is_deterministic():
    data = make_input()

    result_1 = analyze(data)
    result_2 = analyze(data)

    assert result_1 == result_2


def test_analyze_calculates_revenue_internally():
    result = analyze(make_input())

    assert result.financial.revenue.conservative == pytest.approx(
        12000
    )

    assert result.financial.revenue.base == pytest.approx(
        32000
    )

    assert result.financial.revenue.optimistic == pytest.approx(
        45000
    )


def test_analyze_expected_decision():
    result = analyze(make_input())

    assert (
        result.decision.decision_class
        == "prime_opportunity"
    )

    assert (
        result.decision.structural_band
        == "strong"
    )

    assert (
        result.decision.financial_band
        == "strong"
    )


def test_analyze_expected_location_score():
    result = analyze(make_input())

    assert result.location.base_score == pytest.approx(
        75.0
    )

    assert result.location.final_score == pytest.approx(
        75.0
    )

    assert result.location.penalty_multiplier == pytest.approx(
        1.0
    )


def test_analyze_expected_financial_metrics():
    result = analyze(make_input())

    assert result.financial.bec_base == pytest.approx(
        1.947826,
        rel=1e-6,
    )

    assert result.financial.bec_conservative == pytest.approx(
        0.730435,
        rel=1e-6,
    )

    assert result.financial.stress_test_failed is True

    assert result.financial.rent_burden_pct == pytest.approx(
        12.5
    )

    assert result.financial.operating_margin_pct == pytest.approx(
        34.0625
    )


def test_analyze_contains_confidence():
    result = analyze(make_input())

    assert (
        0
        <= result.confidence.overall_score
        <= 100
    )

    assert result.confidence.overall_score == pytest.approx(
        82.5
    )

    assert result.confidence.label == "moderate"


def test_analyze_contains_stress_test_flag():
    result = analyze(make_input())

    assert (
        "STRESS_TEST_FAILED"
        in result.decision.risk_flags
    )


def test_analyze_output_engines_are_consistent():
    result = analyze(make_input())

    assert (
        result.decision.structural_band
        == result.location.structural_band
    )

    if result.financial.bec_base >= 1.5:
        assert (
            result.decision.financial_band
            == "strong"
        )


def test_analysis_input_rejects_wrong_sector_revenue_input():
    with pytest.raises(TypeError):
        AnalysisInput(
            sector=Sector.COFFEE,

            category_scores=CategoryScores(
                demand=90,
                competition=60,
                accessibility=95,
                economics=20,
            ),

            revenue_input=RestaurantRevenueInput(
                seats=50,
                turnover_per_day=2,
                utilization_conservative=0.4,
                utilization_base=0.6,
                utilization_optimistic=0.8,
                average_ticket=25,
                operating_days_per_month=26,
            ),

            monthly_rent=4000,
            fixed_labor=6000,
            fixed_overhead=1500,

            geographic_level=GeographicLevel.TRACT,
            data_age_years=2,

            data_coverage={
                "demand": CoverageLevel.FULL,
                "competition": CoverageLevel.DEGRADED,
                "accessibility": CoverageLevel.FULL,
                "economics": CoverageLevel.FULL,
            },

            input_qualities={
                "rent": InputQuality.USER,
                "price": InputQuality.USER,
                "capacity": InputQuality.DEFAULT,
                "schedule": InputQuality.DEFAULT,
            },
        )
