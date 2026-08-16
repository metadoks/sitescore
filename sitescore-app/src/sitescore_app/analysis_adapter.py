from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from weakref import ref

from sitescore.config.quality_levels import CoverageLevel, GeographicLevel, InputQuality
from sitescore.config.sectors import Sector
from sitescore.schemas.analysis import AnalysisInput, RevenueInput
from sitescore.schemas.location import CategoryScores

from .aggregation import (
    ApplicationCategoryAggregationResult,
    _resolve_trusted_application_category_authority,
)


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ApplicationCoreAnalysisInput:
    """Factory-owned application authority over one exact frozen core AnalysisInput."""

    _category_result: ApplicationCategoryAggregationResult
    _analysis_input: AnalysisInput

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ApplicationCoreAnalysisInput is factory-owned; use "
            "build_application_core_analysis_input"
        )

    @property
    def category_result(self) -> ApplicationCategoryAggregationResult:
        binding = _resolve_trusted_application_core_analysis_input(self)
        return binding[1]

    @property
    def analysis_input(self) -> AnalysisInput:
        binding = _resolve_trusted_application_core_analysis_input(self)
        return binding[14]


def _semantic_record(value: object) -> object:
    """Deterministic recursive authority record for supported core DTO surfaces."""
    if value is None:
        return ("none",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", value.hex())
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, Enum):
        value_type = type(value)
        return (
            "enum",
            value_type.__module__,
            value_type.__qualname__,
            _semantic_record(value.value),
        )
    if isinstance(value, dict):
        items = [
            (_semantic_record(key), _semantic_record(item_value))
            for key, item_value in value.items()
        ]
        items.sort(key=repr)
        return ("dict", tuple(items))
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
        "unsupported authority-bearing value in semantic record: "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def _install_core_analysis_input_factories():
    bindings: dict[int, tuple[object, ...]] = {}

    def register(
        wrapper: ApplicationCoreAnalysisInput,
        category_result: ApplicationCategoryAggregationResult,
        sector: Sector,
        demand: float,
        competition: float,
        accessibility: float,
        economics: float,
        category_scores: CategoryScores,
        revenue_input: RevenueInput,
        revenue_record: object,
        monthly_rent: float,
        fixed_labor: float,
        fixed_overhead: float,
        geographic_level: GeographicLevel,
        data_age_years: int | None,
        data_coverage: dict[str, CoverageLevel],
        data_coverage_record: object,
        input_qualities: dict[str, InputQuality],
        input_qualities_record: object,
        analysis_input: AnalysisInput,
        analysis_record: object,
    ) -> None:
        object_id = id(wrapper)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            bindings.pop(object_id, None)

        bindings[object_id] = (
            ref(wrapper, cleanup),
            category_result,
            sector,
            demand,
            competition,
            accessibility,
            economics,
            category_scores,
            revenue_input,
            revenue_record,
            monthly_rent,
            fixed_labor,
            fixed_overhead,
            geographic_level,
            analysis_input,
            data_age_years,
            data_coverage,
            data_coverage_record,
            input_qualities,
            input_qualities_record,
            analysis_record,
        )

    def resolve(
        value: ApplicationCoreAnalysisInput,
    ) -> tuple[object, ...]:
        if not isinstance(value, ApplicationCoreAnalysisInput):
            raise TypeError("value must be an ApplicationCoreAnalysisInput")
        binding = bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError(
                "application core analysis input is not canonical/factory-owned"
            )

        category_result = binding[1]
        sector = binding[2]
        demand = binding[3]
        competition = binding[4]
        accessibility = binding[5]
        economics = binding[6]
        category_scores = binding[7]
        revenue_input = binding[8]
        revenue_record = binding[9]
        monthly_rent = binding[10]
        fixed_labor = binding[11]
        fixed_overhead = binding[12]
        geographic_level = binding[13]
        analysis_input = binding[14]
        data_age_years = binding[15]
        data_coverage = binding[16]
        data_coverage_record = binding[17]
        input_qualities = binding[18]
        input_qualities_record = binding[19]
        analysis_record = binding[20]

        if value._category_result is not category_result:
            raise ValueError("application core analysis input category binding violation")
        if value._analysis_input is not analysis_input:
            raise ValueError("application core analysis input redirect/integrity violation")

        trusted = _resolve_trusted_application_category_authority(category_result)
        if trusted != (sector, demand, competition, accessibility, economics):
            raise ValueError("nested category authority integrity violation")

        if analysis_input.sector is not sector:
            raise ValueError("core AnalysisInput sector integrity violation")
        if analysis_input.category_scores is not category_scores:
            raise ValueError("core CategoryScores identity integrity violation")
        if analysis_input.revenue_input is not revenue_input:
            raise ValueError("core revenue input identity integrity violation")
        if analysis_input.data_coverage is not data_coverage:
            raise ValueError("core data_coverage identity integrity violation")
        if analysis_input.input_qualities is not input_qualities:
            raise ValueError("core input_qualities identity integrity violation")

        if (
            category_scores.demand != demand
            or category_scores.competition != competition
            or category_scores.accessibility != accessibility
            or category_scores.economics != economics
        ):
            raise ValueError("core CategoryScores semantic integrity violation")
        if _semantic_record(revenue_input) != revenue_record:
            raise ValueError("core revenue input semantic integrity violation")
        if analysis_input.monthly_rent != monthly_rent:
            raise ValueError("monthly_rent integrity violation")
        if analysis_input.fixed_labor != fixed_labor:
            raise ValueError("fixed_labor integrity violation")
        if analysis_input.fixed_overhead != fixed_overhead:
            raise ValueError("fixed_overhead integrity violation")
        if analysis_input.geographic_level is not geographic_level:
            raise ValueError("geographic_level integrity violation")
        if analysis_input.data_age_years != data_age_years:
            raise ValueError("data_age_years integrity violation")
        if _semantic_record(data_coverage) != data_coverage_record:
            raise ValueError("data_coverage semantic integrity violation")
        if _semantic_record(input_qualities) != input_qualities_record:
            raise ValueError("input_qualities semantic integrity violation")
        if _semantic_record(analysis_input) != analysis_record:
            raise ValueError("core AnalysisInput semantic integrity violation")
        return binding

    def build(
        category_result: ApplicationCategoryAggregationResult,
        *,
        revenue_input: RevenueInput,
        monthly_rent: float,
        fixed_labor: float,
        fixed_overhead: float,
        geographic_level: GeographicLevel,
        data_age_years: int | None,
        data_coverage: dict[str, CoverageLevel],
        input_qualities: dict[str, InputQuality],
    ) -> ApplicationCoreAnalysisInput:
        sector, demand, competition, accessibility, economics = (
            _resolve_trusted_application_category_authority(category_result)
        )
        if not isinstance(sector, Sector):
            raise RuntimeError("trusted category sector is not frozen core Sector")

        category_scores = CategoryScores(
            demand=demand,
            competition=competition,
            accessibility=accessibility,
            economics=economics,
        )
        coverage_copy = dict(data_coverage)
        quality_copy = dict(input_qualities)

        analysis_input = AnalysisInput(
            sector=sector,
            category_scores=category_scores,
            revenue_input=revenue_input,
            monthly_rent=monthly_rent,
            fixed_labor=fixed_labor,
            fixed_overhead=fixed_overhead,
            geographic_level=geographic_level,
            data_age_years=data_age_years,
            data_coverage=coverage_copy,
            input_qualities=quality_copy,
        )

        # Revalidate the upstream authority after all caller-owned input handling and
        # core construction, before granting the downstream application capability.
        current_trusted = _resolve_trusted_application_category_authority(category_result)
        if current_trusted != (sector, demand, competition, accessibility, economics):
            raise ValueError("category authority changed during core adapter construction")

        wrapper = object.__new__(ApplicationCoreAnalysisInput)
        object.__setattr__(wrapper, "_category_result", category_result)
        object.__setattr__(wrapper, "_analysis_input", analysis_input)
        register(
            wrapper,
            category_result,
            sector,
            demand,
            competition,
            accessibility,
            economics,
            category_scores,
            revenue_input,
            _semantic_record(revenue_input),
            monthly_rent,
            fixed_labor,
            fixed_overhead,
            geographic_level,
            data_age_years,
            coverage_copy,
            _semantic_record(coverage_copy),
            quality_copy,
            _semantic_record(quality_copy),
            analysis_input,
            _semantic_record(analysis_input),
        )
        return wrapper

    def require(value: ApplicationCoreAnalysisInput) -> ApplicationCoreAnalysisInput:
        resolve(value)
        return value

    return build, require, resolve


(
    build_application_core_analysis_input,
    require_canonical_application_core_analysis_input,
    _resolve_trusted_application_core_analysis_input,
) = _install_core_analysis_input_factories()
del _install_core_analysis_input_factories


__all__ = [
    "ApplicationCoreAnalysisInput",
    "build_application_core_analysis_input",
    "require_canonical_application_core_analysis_input",
]
