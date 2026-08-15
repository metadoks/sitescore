from sitescore.schemas.financial import RevenueScenarios


def coffee_monthly_revenue(
    population: float,
    target_rate: float,
    capture_rate: float,
    monthly_visit_frequency: float,
    average_ticket: float,
) -> float:
    vals = (population, target_rate, capture_rate, monthly_visit_frequency, average_ticket)
    if min(vals) < 0:
        raise ValueError("Coffee revenue inputs cannot be negative")
    if target_rate > 1 or capture_rate > 1:
        raise ValueError("Rates must be decimals between 0 and 1")
    monthly_transactions = population * target_rate * capture_rate * monthly_visit_frequency
    return monthly_transactions * average_ticket


def gym_monthly_revenue(
    target_population: float,
    penetration_rate: float,
    usable_area: float,
    density_factor: float,
    monthly_fee: float,
) -> float:
    vals = (target_population, penetration_rate, usable_area, density_factor, monthly_fee)
    if min(vals) < 0:
        raise ValueError("Gym revenue inputs cannot be negative")
    if penetration_rate > 1:
        raise ValueError("penetration_rate must be a decimal between 0 and 1")
    potential_members = target_population * penetration_rate
    capacity = usable_area * density_factor
    active_members = min(potential_members, capacity)
    return active_members * monthly_fee


def restaurant_monthly_revenue(
    seats: float,
    turnover: float,
    utilization: float,
    average_ticket: float,
    operating_days: float,
) -> float:
    vals = (seats, turnover, utilization, average_ticket, operating_days)
    if min(vals) < 0:
        raise ValueError("Restaurant revenue inputs cannot be negative")
    if utilization > 1:
        raise ValueError("utilization must be a decimal between 0 and 1")
    daily_covers = seats * turnover * utilization
    return daily_covers * average_ticket * operating_days


def beauty_monthly_revenue(
    stations: float,
    operating_hours_per_week: float,
    average_service_duration_hours: float,
    utilization: float,
    average_ticket: float,
    weeks_per_month: float = 4.33,
) -> float:
    if min(stations, operating_hours_per_week, utilization, average_ticket, weeks_per_month) < 0:
        raise ValueError("Beauty revenue inputs cannot be negative")
    if average_service_duration_hours <= 0:
        raise ValueError("average_service_duration_hours must be > 0")
    if utilization > 1:
        raise ValueError("utilization must be a decimal between 0 and 1")
    weekly_slots = stations * operating_hours_per_week / average_service_duration_hours
    appointments = weekly_slots * utilization
    return appointments * average_ticket * weeks_per_month


def scenarios(conservative: float, base: float, optimistic: float) -> RevenueScenarios:
    return RevenueScenarios(conservative, base, optimistic)

from sitescore.config.sectors import Sector
from sitescore.schemas.financial import RevenueScenarios
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
def calculate_coffee_revenue(
    data: CoffeeRevenueInput,
) -> RevenueScenarios:

    def scenario(capture_rate: float) -> float:
        captured_customers = (
            data.target_population
            * data.target_rate
            * capture_rate
        )

        monthly_transactions = (
            captured_customers
            * data.visit_frequency_per_month
        )

        return monthly_transactions * data.average_ticket

    return RevenueScenarios(
        conservative=scenario(data.capture_rate_conservative),
        base=scenario(data.capture_rate_base),
        optimistic=scenario(data.capture_rate_optimistic),
    )
def calculate_restaurant_revenue(
    data: RestaurantRevenueInput,
) -> RevenueScenarios:

    def scenario(utilization: float) -> float:
        daily_covers = (
            data.seats
            * data.turnover_per_day
            * utilization
        )

        return (
            daily_covers
            * data.average_ticket
            * data.operating_days_per_month
        )

    return RevenueScenarios(
        conservative=scenario(data.utilization_conservative),
        base=scenario(data.utilization_base),
        optimistic=scenario(data.utilization_optimistic),
    )
def calculate_gym_revenue(
    data: GymRevenueInput,
) -> RevenueScenarios:

    capacity = (
        data.usable_area
        * data.members_per_area_unit
    )

    def scenario(penetration_rate: float) -> float:
        potential_members = (
            data.target_population
            * penetration_rate
        )

        active_members = min(
            potential_members,
            capacity,
        )

        return (
            active_members
            * data.monthly_membership_fee
        )

    return RevenueScenarios(
        conservative=scenario(
            data.penetration_rate_conservative
        ),
        base=scenario(
            data.penetration_rate_base
        ),
        optimistic=scenario(
            data.penetration_rate_optimistic
        ),
    )
def calculate_beauty_revenue(
    data: BeautyRevenueInput,
) -> RevenueScenarios:

    max_weekly_slots = (
        data.stations
        * data.operating_hours_per_week
        / data.average_service_duration_hours
    )

    def scenario(utilization: float) -> float:
        weekly_appointments = (
            max_weekly_slots
            * utilization
        )

        return (
            weekly_appointments
            * data.average_ticket
            * 4.33
        )

    return RevenueScenarios(
        conservative=scenario(
            data.utilization_conservative
        ),
        base=scenario(
            data.utilization_base
        ),
        optimistic=scenario(
            data.utilization_optimistic
        ),
    )
def calculate_revenue(
    sector: Sector,
    data: RevenueInput,
) -> RevenueScenarios:

    if sector == Sector.COFFEE:
        if not isinstance(data, CoffeeRevenueInput):
            raise TypeError(
                "Coffee sector requires CoffeeRevenueInput"
            )
        return calculate_coffee_revenue(data)

    if sector == Sector.RESTAURANT:
        if not isinstance(data, RestaurantRevenueInput):
            raise TypeError(
                "Restaurant sector requires RestaurantRevenueInput"
            )
        return calculate_restaurant_revenue(data)

    if sector == Sector.GYM:
        if not isinstance(data, GymRevenueInput):
            raise TypeError(
                "Gym sector requires GymRevenueInput"
            )
        return calculate_gym_revenue(data)

    if sector == Sector.BEAUTY:
        if not isinstance(data, BeautyRevenueInput):
            raise TypeError(
                "Beauty sector requires BeautyRevenueInput"
            )
        return calculate_beauty_revenue(data)

    raise ValueError(f"Unsupported sector: {sector}")