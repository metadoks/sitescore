from pprint import pprint

from sitescore.analyze import analyze
from sitescore.config.quality_levels import (
    CoverageLevel,
    GeographicLevel,
    InputQuality,
)
from sitescore.config.sectors import Sector
from sitescore.schemas.analysis import AnalysisInput
from sitescore.schemas.location import CategoryScores
from sitescore.schemas.revenue_inputs import CoffeeRevenueInput


input_data = AnalysisInput(
    sector=Sector.COFFEE,

    category_scores=CategoryScores(
        demand=90,
        competition=60,
        accessibility=95,
        economics=20,
    ),

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

result = analyze(input_data)

pprint(
    result.to_dict(),
    sort_dicts=False,
)