import pytest

from sitescore.config.quality_levels import (
    CoverageLevel,
    GeographicLevel,
    InputQuality,
)
from sitescore.config.sectors import Sector
from sitescore.schemas.analysis import AnalysisInput
from sitescore.schemas.location import CategoryScores
from sitescore.schemas.revenue_inputs import (
    CoffeeRevenueInput,
)


def valid_coffee_input_kwargs():
    return {
        "sector": Sector.COFFEE,

        "category_scores": CategoryScores(
            demand=80,
            competition=70,
            accessibility=75,
            economics=70,
        ),

        "revenue_input": CoffeeRevenueInput(
            target_population=100000,
            target_rate=0.25,
            capture_rate_conservative=0.015,
            capture_rate_base=0.04,
            capture_rate_optimistic=0.06,
            visit_frequency_per_month=4,
            average_ticket=8,
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


def test_rejects_string_geographic_level():
    kwargs = valid_coffee_input_kwargs()

    kwargs["geographic_level"] = "tract"

    with pytest.raises(TypeError):
        AnalysisInput(**kwargs)


def test_rejects_string_coverage_level():
    kwargs = valid_coffee_input_kwargs()

    kwargs["data_coverage"] = {
        "demand": "full",
        "competition": CoverageLevel.FULL,
        "accessibility": CoverageLevel.FULL,
        "economics": CoverageLevel.FULL,
    }

    with pytest.raises(TypeError):
        AnalysisInput(**kwargs)


def test_rejects_string_input_quality():
    kwargs = valid_coffee_input_kwargs()

    kwargs["input_qualities"] = {
        "rent": "user",
        "price": InputQuality.USER,
        "capacity": InputQuality.USER,
        "schedule": InputQuality.USER,
    }

    with pytest.raises(TypeError):
        AnalysisInput(**kwargs)


def test_rejects_unknown_coverage_category():
    kwargs = valid_coffee_input_kwargs()

    kwargs["data_coverage"] = {
        "demand": CoverageLevel.FULL,
        "competition": CoverageLevel.FULL,
        "accessibility": CoverageLevel.FULL,
        "economics": CoverageLevel.FULL,
        "banana": CoverageLevel.FULL,
    }

    with pytest.raises(ValueError):
        AnalysisInput(**kwargs)


def test_rejects_unknown_input_quality_field():
    kwargs = valid_coffee_input_kwargs()

    kwargs["input_qualities"] = {
        "rent": InputQuality.USER,
        "price": InputQuality.USER,
        "capacity": InputQuality.USER,
        "schedule": InputQuality.USER,
        "banana": InputQuality.USER,
    }

    with pytest.raises(ValueError):
        AnalysisInput(**kwargs)


def test_rejects_negative_rent():
    kwargs = valid_coffee_input_kwargs()

    kwargs["monthly_rent"] = -1

    with pytest.raises(ValueError):
        AnalysisInput(**kwargs)


def test_rejects_negative_data_age():
    kwargs = valid_coffee_input_kwargs()

    kwargs["data_age_years"] = -1

    with pytest.raises(ValueError):
        AnalysisInput(**kwargs)