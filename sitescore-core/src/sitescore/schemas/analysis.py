from dataclasses import dataclass

from sitescore.config.quality_levels import (
    CoverageLevel,
    GeographicLevel,
    InputQuality,
)
from sitescore.config.sectors import Sector
from sitescore.schemas.location import CategoryScores
from sitescore.schemas.revenue_inputs import (
    BeautyRevenueInput,
    CoffeeRevenueInput,
    GymRevenueInput,
    RestaurantRevenueInput,
)


RevenueInput = (
    CoffeeRevenueInput
    | RestaurantRevenueInput
    | GymRevenueInput
    | BeautyRevenueInput
)


@dataclass(frozen=True, slots=True)
class AnalysisInput:
    sector: Sector
    category_scores: CategoryScores
    revenue_input: RevenueInput

    monthly_rent: float
    fixed_labor: float
    fixed_overhead: float

    geographic_level: GeographicLevel
    data_age_years: int | None

    data_coverage: dict[str, CoverageLevel]
    input_qualities: dict[str, InputQuality]

    def __post_init__(self):
        # -------------------------------------------------
        # Core type validation
        # -------------------------------------------------

        if not isinstance(self.sector, Sector):
            raise TypeError(
                "sector must be a Sector"
            )

        if not isinstance(
            self.category_scores,
            CategoryScores,
        ):
            raise TypeError(
                "category_scores must be CategoryScores"
            )

        valid_revenue_types = (
            CoffeeRevenueInput,
            RestaurantRevenueInput,
            GymRevenueInput,
            BeautyRevenueInput,
        )
        sector_input_types = {
            Sector.COFFEE: CoffeeRevenueInput,
            Sector.RESTAURANT: RestaurantRevenueInput,
            Sector.GYM: GymRevenueInput,
            Sector.BEAUTY: BeautyRevenueInput,
        }

        expected_type = sector_input_types[
            self.sector
        ]

        if not isinstance(
            self.revenue_input,
            expected_type,
        ):
            raise TypeError(
                f"{self.sector.value} sector requires "
                f"{expected_type.__name__}"
            )
        if not isinstance(
            self.revenue_input,
            valid_revenue_types,
        ):
            raise TypeError(
                "revenue_input must be a supported "
                "sector revenue input type"
            )

        if not isinstance(
            self.geographic_level,
            GeographicLevel,
        ):
            raise TypeError(
                "geographic_level must be GeographicLevel"
            )

        # -------------------------------------------------
        # Financial input validation
        # -------------------------------------------------

        if self.monthly_rent < 0:
            raise ValueError(
                "monthly_rent cannot be negative"
            )

        if self.fixed_labor < 0:
            raise ValueError(
                "fixed_labor cannot be negative"
            )

        if self.fixed_overhead < 0:
            raise ValueError(
                "fixed_overhead cannot be negative"
            )

        # -------------------------------------------------
        # Data vintage validation
        # -------------------------------------------------

        if (
            self.data_age_years is not None
            and self.data_age_years < 0
        ):
            raise ValueError(
                "data_age_years cannot be negative"
            )

        # -------------------------------------------------
        # Data coverage validation
        # -------------------------------------------------

        required_categories = {
            "demand",
            "competition",
            "accessibility",
            "economics",
        }

        unknown_coverage_keys = (
            set(self.data_coverage)
            - required_categories
        )

        if unknown_coverage_keys:
            raise ValueError(
                "Unknown data coverage categories: "
                f"{sorted(unknown_coverage_keys)}"
            )

        for key, value in self.data_coverage.items():
            if not isinstance(
                value,
                CoverageLevel,
            ):
                raise TypeError(
                    f"data_coverage['{key}'] "
                    "must be CoverageLevel"
                )

        # -------------------------------------------------
        # Input quality validation
        # -------------------------------------------------

        required_inputs = {
            "rent",
            "price",
            "capacity",
            "schedule",
        }

        unknown_input_keys = (
            set(self.input_qualities)
            - required_inputs
        )

        if unknown_input_keys:
            raise ValueError(
                "Unknown input quality fields: "
                f"{sorted(unknown_input_keys)}"
            )

        for key, value in self.input_qualities.items():
            if not isinstance(
                value,
                InputQuality,
            ):
                raise TypeError(
                    f"input_qualities['{key}'] "
                    "must be InputQuality"
                )