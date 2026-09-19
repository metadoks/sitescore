from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoffeeRevenueInput:
    target_population: float
    target_rate: float
    capture_rate_conservative: float
    capture_rate_base: float
    capture_rate_optimistic: float
    visit_frequency_per_month: float
    average_ticket: float

    def __post_init__(self):
        if self.target_population < 0:
            raise ValueError(
                "target_population cannot be negative"
            )

        if not 0 <= self.target_rate <= 1:
            raise ValueError(
                "target_rate must be between 0 and 1"
            )

        for value in (
            self.capture_rate_conservative,
            self.capture_rate_base,
            self.capture_rate_optimistic,
        ):
            if not 0 <= value <= 1:
                raise ValueError(
                    "capture rates must be between 0 and 1"
                )

        if not (
            self.capture_rate_conservative
            <= self.capture_rate_base
            <= self.capture_rate_optimistic
        ):
            raise ValueError(
                "capture rates must satisfy "
                "conservative <= base <= optimistic"
            )

        if self.visit_frequency_per_month < 0:
            raise ValueError(
                "visit_frequency_per_month cannot be negative"
            )

        if self.average_ticket <= 0:
            raise ValueError(
                "average_ticket must be greater than zero"
            )


@dataclass(frozen=True, slots=True)
class RestaurantRevenueInput:
    seats: int
    turnover_per_day: float
    utilization_conservative: float
    utilization_base: float
    utilization_optimistic: float
    average_ticket: float
    operating_days_per_month: int

    def __post_init__(self):
        if self.seats <= 0:
            raise ValueError(
                "seats must be greater than zero"
            )

        if self.turnover_per_day < 0:
            raise ValueError(
                "turnover_per_day cannot be negative"
            )

        for value in (
            self.utilization_conservative,
            self.utilization_base,
            self.utilization_optimistic,
        ):
            if not 0 <= value <= 1:
                raise ValueError(
                    "utilization must be between 0 and 1"
                )

        if not (
            self.utilization_conservative
            <= self.utilization_base
            <= self.utilization_optimistic
        ):
            raise ValueError(
                "utilization must satisfy "
                "conservative <= base <= optimistic"
            )

        if self.average_ticket <= 0:
            raise ValueError(
                "average_ticket must be greater than zero"
            )

        if self.operating_days_per_month <= 0:
            raise ValueError(
                "operating_days_per_month must be greater than zero"
            )


@dataclass(frozen=True, slots=True)
class GymRevenueInput:
    target_population: float
    penetration_rate_conservative: float
    penetration_rate_base: float
    penetration_rate_optimistic: float
    usable_area: float
    members_per_area_unit: float
    monthly_membership_fee: float

    def __post_init__(self):
        if self.target_population < 0:
            raise ValueError(
                "target_population cannot be negative"
            )

        for value in (
            self.penetration_rate_conservative,
            self.penetration_rate_base,
            self.penetration_rate_optimistic,
        ):
            if not 0 <= value <= 1:
                raise ValueError(
                    "penetration rates must be between 0 and 1"
                )

        if not (
            self.penetration_rate_conservative
            <= self.penetration_rate_base
            <= self.penetration_rate_optimistic
        ):
            raise ValueError(
                "penetration rates must satisfy "
                "conservative <= base <= optimistic"
            )

        if self.usable_area <= 0:
            raise ValueError(
                "usable_area must be greater than zero"
            )

        if self.members_per_area_unit <= 0:
            raise ValueError(
                "members_per_area_unit must be greater than zero"
            )

        if self.monthly_membership_fee <= 0:
            raise ValueError(
                "monthly_membership_fee must be greater than zero"
            )


@dataclass(frozen=True, slots=True)
class BeautyRevenueInput:
    stations: int
    operating_hours_per_week: float
    average_service_duration_hours: float
    utilization_conservative: float
    utilization_base: float
    utilization_optimistic: float
    average_ticket: float

    def __post_init__(self):
        if self.stations <= 0:
            raise ValueError(
                "stations must be greater than zero"
            )

        if self.operating_hours_per_week <= 0:
            raise ValueError(
                "operating_hours_per_week must be greater than zero"
            )

        if self.average_service_duration_hours <= 0:
            raise ValueError(
                "average_service_duration_hours must be greater than zero"
            )

        for value in (
            self.utilization_conservative,
            self.utilization_base,
            self.utilization_optimistic,
        ):
            if not 0 <= value <= 1:
                raise ValueError(
                    "utilization must be between 0 and 1"
                )

        if not (
            self.utilization_conservative
            <= self.utilization_base
            <= self.utilization_optimistic
        ):
            raise ValueError(
                "utilization must satisfy "
                "conservative <= base <= optimistic"
            )

        if self.average_ticket <= 0:
            raise ValueError(
                "average_ticket must be greater than zero"
            )