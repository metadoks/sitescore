import pytest

from sitescore.analyze import analyze
from sitescore.config.quality_levels import (
    CoverageLevel,
    GeographicLevel,
    InputQuality,
)
from sitescore.config.sectors import Sector
from sitescore.schemas.analysis import AnalysisInput
from sitescore.schemas.location import CategoryScores
from sitescore.schemas.revenue_inputs import (
    BeautyRevenueInput,
    CoffeeRevenueInput,
    GymRevenueInput,
    RestaurantRevenueInput,
)


def common_kwargs():
    return {
        "category_scores": CategoryScores(
            demand=80,
            competition=70,
            accessibility=75,
            economics=70,
        ),
        "monthly_rent": 4000,
        "fixed_labor": 5000,
        "fixed_overhead": 1500,
        "geographic_level": GeographicLevel.TRACT,
        "data_age_years": 2,
        "data_coverage": {
            "demand": CoverageLevel.FULL,
            "competition": CoverageLevel.FULL,
            "accessibility": CoverageLevel.FULL,
            "economics": CoverageLevel.FULL,
        },
        "input_qualities": {
            "rent": InputQuality.USER,
            "price": InputQuality.USER,
            "capacity": InputQuality.USER,
            "schedule": InputQuality.USER,
        },
    }


def make_coffee():
    return AnalysisInput(
        sector=Sector.COFFEE,
        revenue_input=CoffeeRevenueInput(
            target_population=100000,
            target_rate=0.25,
            capture_rate_conservative=0.015,
            capture_rate_base=0.04,
            capture_rate_optimistic=0.06,
            visit_frequency_per_month=4,
            average_ticket=8,
        ),
        **common_kwargs(),
    )


def make_restaurant():
    return AnalysisInput(
        sector=Sector.RESTAURANT,
        revenue_input=RestaurantRevenueInput(
            seats=60,
            turnover_per_day=2.0,
            utilization_conservative=0.45,
            utilization_base=0.65,
            utilization_optimistic=0.85,
            average_ticket=25,
            operating_days_per_month=26,
        ),
        **common_kwargs(),
    )


def make_gym():
    return AnalysisInput(
        sector=Sector.GYM,
        revenue_input=GymRevenueInput(
            target_population=15000,
            penetration_rate_conservative=0.02,
            penetration_rate_base=0.04,
            penetration_rate_optimistic=0.06,
            usable_area=700,
            members_per_area_unit=1.0,
            monthly_membership_fee=50,
        ),
        **common_kwargs(),
    )


def make_beauty():
    return AnalysisInput(
        sector=Sector.BEAUTY,
        revenue_input=BeautyRevenueInput(
            stations=5,
            operating_hours_per_week=40,
            average_service_duration_hours=1.0,
            utilization_conservative=0.40,
            utilization_base=0.60,
            utilization_optimistic=0.80,
            average_ticket=50,
        ),
        **common_kwargs(),
    )


@pytest.mark.parametrize(
    "factory",
    [
        make_coffee,
        make_restaurant,
        make_gym,
        make_beauty,
    ],
)
def test_sector_analysis_runs_end_to_end(factory):
    result = analyze(factory())

    assert 0 <= result.location.final_score <= 100
    assert 0 <= result.confidence.overall_score <= 100

    assert (
        result.financial.revenue.conservative
        <= result.financial.revenue.base
        <= result.financial.revenue.optimistic
    )

    assert result.financial.break_even_revenue >= 0

    assert result.decision.decision_class


@pytest.mark.parametrize(
    "factory",
    [
        make_coffee,
        make_restaurant,
        make_gym,
        make_beauty,
    ],
)
def test_sector_analysis_is_deterministic(factory):
    data = factory()

    first = analyze(data)
    second = analyze(data)

    assert first == second