from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from weakref import ref

from sitescore_data.schemas.common import MetricValue
from sitescore_data.schemas.features import NormalizedLocationFeatures
from sitescore_data.validation import SectorKey, require_bounded_number

from .gating import (
    ApplicationScoringInput,
    require_canonical_application_scoring_input,
)

if TYPE_CHECKING:
    from sitescore.config.sectors import Sector


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class ApplicationCategoryAggregationResult:
    """Factory-owned authority for the four application category scores.

    This capability is downstream of a canonical ``ApplicationScoringInput``.
    It is not a core ``CategoryScores`` object and it does not mean Location Score
    analysis has occurred.
    """

    application_scoring_input: ApplicationScoringInput
    sector: Sector
    demand: float
    competition: float
    accessibility: float
    economics: float

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "ApplicationCategoryAggregationResult is factory-owned; use "
            "aggregate_application_category_scores"
        )


def _metric_score(
    features: NormalizedLocationFeatures,
    field_name: str,
) -> float:
    metric = getattr(features, field_name)
    if not isinstance(metric, MetricValue):
        raise TypeError(f"{field_name} must be a MetricValue")
    if metric.unit != "score_0_100":
        raise ValueError(f'{field_name} must use MetricValue.unit="score_0_100"')
    if metric.value is None:
        raise ValueError(f"{field_name} must be numeric for category aggregation")
    return float(
        require_bounded_number(
            metric.value,
            low=0.0,
            high=100.0,
            field_name=field_name,
        )
    )


def _install_category_aggregation_factories():
    # Capture the exact frozen core authorities in closure state. They remain the
    # only production source of semantic sector vocabulary and subfeature weights.
    from sitescore.config.sectors import Sector as frozen_sector_enum
    from sitescore.config.subfeature_weights import (
        ACCESSIBILITY_SUBFEATURE_WEIGHTS as frozen_accessibility_weights,
        DEMAND_SUBFEATURE_WEIGHTS as frozen_demand_weights,
    )

    category_bindings: dict[int, tuple[object, ...]] = {}

    def resolve_frozen_sector(sector_key: SectorKey):
        if not isinstance(sector_key, SectorKey):
            raise TypeError("canonical application scoring sector must be a SectorKey")
        try:
            return frozen_sector_enum(sector_key.value)
        except ValueError as exc:
            raise ValueError(
                f"unsupported canonical sector for category aggregation: {sector_key.value}"
            ) from exc

    def current_scoring_authority(
        application_scoring_input: ApplicationScoringInput,
    ) -> tuple[SectorKey, NormalizedLocationFeatures, str]:
        require_canonical_application_scoring_input(application_scoring_input)
        sector_key = application_scoring_input.sector_key
        normalized_features = application_scoring_input.normalized_features
        readiness_fingerprint = application_scoring_input.readiness_fingerprint
        if not isinstance(sector_key, SectorKey):
            raise RuntimeError("canonical application scoring sector binding corrupted")
        if not isinstance(normalized_features, NormalizedLocationFeatures):
            raise RuntimeError("canonical application scoring feature binding corrupted")
        if not isinstance(readiness_fingerprint, str):
            raise RuntimeError("canonical application scoring readiness binding corrupted")
        return sector_key, normalized_features, readiness_fingerprint

    def compute_categories(
        sector,
        features: NormalizedLocationFeatures,
    ) -> tuple[float, float, float, float]:
        walkable_population = _metric_score(features, "walkable_population_score")
        target_population_density = _metric_score(
            features,
            "target_population_density_score",
        )
        age_target_concentration = _metric_score(
            features,
            "age_target_concentration_score",
        )
        competition = _metric_score(features, "competition_opportunity_score")
        walkable_reach_area = _metric_score(features, "walkable_reach_area_score")
        transit_access = _metric_score(features, "transit_access_score")
        road_parking_access = _metric_score(features, "road_parking_access_score")
        economics = _metric_score(features, "household_income_score")

        demand_weights = frozen_demand_weights[sector]
        accessibility_weights = frozen_accessibility_weights[sector]

        demand = float(
            walkable_population * demand_weights["walkable_population"]
            + target_population_density
            * demand_weights["target_population_density"]
            + age_target_concentration
            * demand_weights["age_target_concentration"]
        )
        accessibility = float(
            walkable_reach_area * accessibility_weights["walkable_reach_area"]
            + transit_access * accessibility_weights["transit_access"]
            + road_parking_access * accessibility_weights["road_parking_access"]
        )

        for field_name, value in (
            ("demand", demand),
            ("competition", competition),
            ("accessibility", accessibility),
            ("economics", economics),
        ):
            require_bounded_number(
                value,
                low=0.0,
                high=100.0,
                field_name=field_name,
            )
        return demand, competition, accessibility, economics

    def register_category_binding(
        value: ApplicationCategoryAggregationResult,
        application_scoring_input: ApplicationScoringInput,
        sector,
        normalized_features: NormalizedLocationFeatures,
        readiness_fingerprint: str,
        demand: float,
        competition: float,
        accessibility: float,
        economics: float,
    ) -> None:
        object_id = id(value)

        def cleanup(_dead_ref, *, object_id=object_id) -> None:
            category_bindings.pop(object_id, None)

        category_bindings[object_id] = (
            ref(value, cleanup),
            application_scoring_input,
            sector,
            normalized_features,
            readiness_fingerprint,
            demand,
            competition,
            accessibility,
            economics,
        )

    def aggregate(
        application_scoring_input: ApplicationScoringInput,
    ) -> ApplicationCategoryAggregationResult:
        sector_key, normalized_features, readiness_fingerprint = (
            current_scoring_authority(application_scoring_input)
        )
        sector = resolve_frozen_sector(sector_key)
        demand, competition, accessibility, economics = compute_categories(
            sector,
            normalized_features,
        )

        # Revalidate the nested capability after computation before granting a new
        # downstream authority object. No caller-visible mutable reference is trusted
        # across the authority transition without this second integrity check.
        current_sector_key, current_features, current_fingerprint = (
            current_scoring_authority(application_scoring_input)
        )
        if (
            current_sector_key is not sector_key
            or current_features is not normalized_features
            or current_fingerprint != readiness_fingerprint
        ):
            raise ValueError(
                "application scoring authority changed during category aggregation"
            )

        value = object.__new__(ApplicationCategoryAggregationResult)
        object.__setattr__(
            value,
            "application_scoring_input",
            application_scoring_input,
        )
        object.__setattr__(value, "sector", sector)
        object.__setattr__(value, "demand", demand)
        object.__setattr__(value, "competition", competition)
        object.__setattr__(value, "accessibility", accessibility)
        object.__setattr__(value, "economics", economics)
        register_category_binding(
            value,
            application_scoring_input,
            sector,
            normalized_features,
            readiness_fingerprint,
            demand,
            competition,
            accessibility,
            economics,
        )
        return value

    def resolve_category_binding(
        value: ApplicationCategoryAggregationResult,
    ) -> tuple[object, ...]:
        if not isinstance(value, ApplicationCategoryAggregationResult):
            raise TypeError("value must be an ApplicationCategoryAggregationResult")
        binding = category_bindings.get(id(value))
        if binding is None or binding[0]() is not value:
            raise ValueError(
                "application category aggregation result is not canonical/factory-owned"
            )

        application_scoring_input = binding[1]
        sector = binding[2]
        normalized_features = binding[3]
        readiness_fingerprint = binding[4]
        demand = binding[5]
        competition = binding[6]
        accessibility = binding[7]
        economics = binding[8]

        if value.application_scoring_input is not application_scoring_input:
            raise ValueError("application category aggregation result integrity violation")
        if value.sector is not sector:
            raise ValueError("application category aggregation result integrity violation")
        for current, expected in (
            (value.demand, demand),
            (value.competition, competition),
            (value.accessibility, accessibility),
            (value.economics, economics),
        ):
            if type(current) is not float or current != expected:
                raise ValueError(
                    "application category aggregation result integrity violation"
                )

        current_sector_key, current_features, current_fingerprint = (
            current_scoring_authority(application_scoring_input)
        )
        if (
            current_features is not normalized_features
            or current_fingerprint != readiness_fingerprint
            or resolve_frozen_sector(current_sector_key) is not sector
        ):
            raise ValueError(
                "application category aggregation result nested authority integrity violation"
            )
        return binding

    def require_category_result(
        value: ApplicationCategoryAggregationResult,
    ) -> ApplicationCategoryAggregationResult:
        resolve_category_binding(value)
        return value

    return aggregate, require_category_result


(
    aggregate_application_category_scores,
    require_canonical_application_category_aggregation_result,
) = _install_category_aggregation_factories()
del _install_category_aggregation_factories


__all__ = [
    "ApplicationCategoryAggregationResult",
    "aggregate_application_category_scores",
    "require_canonical_application_category_aggregation_result",
]
