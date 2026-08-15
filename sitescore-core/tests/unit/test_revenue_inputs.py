import pytest

from sitescore.config.sectors import Sector
from sitescore.engines.revenue import calculate_revenue
from sitescore.schemas.revenue_inputs import (
    BeautyRevenueInput,
    CoffeeRevenueInput,
    GymRevenueInput,
    RestaurantRevenueInput,
)


def test_coffee_revenue():
    data = CoffeeRevenueInput(
        target_population=10000,
        target_rate=0.25,
        capture_rate_conservative=0.03,
        capture_rate_base=0.05,
        capture_rate_optimistic=0.07,
        visit_frequency_per_month=4,
        average_ticket=8,
    )

    result = calculate_revenue(
        Sector.COFFEE,
        data,
    )

    assert result.conservative == pytest.approx(2400)
    assert result.base == pytest.approx(4000)
    assert result.optimistic == pytest.approx(5600)


def test_restaurant_revenue():
    data = RestaurantRevenueInput(
        seats=50,
        turnover_per_day=2.0,
        utilization_conservative=0.45,
        utilization_base=0.65,
        utilization_optimistic=0.85,
        average_ticket=25,
        operating_days_per_month=26,
    )

    result = calculate_revenue(
        Sector.RESTAURANT,
        data,
    )

    assert result.conservative == 29250
    assert result.base == 42250
    assert result.optimistic == 55250


def test_gym_capacity_caps_demand():
    data = GymRevenueInput(
        target_population=10000,
        penetration_rate_conservative=0.02,
        penetration_rate_base=0.05,
        penetration_rate_optimistic=0.10,
        usable_area=500,
        members_per_area_unit=1.0,
        monthly_membership_fee=50,
    )

    result = calculate_revenue(
        Sector.GYM,
        data,
    )

    assert result.conservative == 10000
    assert result.base == 25000

    # Demand would imply 1000 members,
    # but physical capacity is capped at 500.
    assert result.optimistic == 25000


def test_beauty_revenue():
    data = BeautyRevenueInput(
        stations=4,
        operating_hours_per_week=40,
        average_service_duration_hours=1,
        utilization_conservative=0.40,
        utilization_base=0.60,
        utilization_optimistic=0.80,
        average_ticket=50,
    )

    result = calculate_revenue(
        Sector.BEAUTY,
        data,
    )

    assert result.conservative == pytest.approx(
        13856
    )

    assert result.base == pytest.approx(
        20784
    )

    assert result.optimistic == pytest.approx(
        27712
    )


def test_wrong_revenue_input_rejected():
    data = RestaurantRevenueInput(
        seats=50,
        turnover_per_day=2,
        utilization_conservative=0.4,
        utilization_base=0.6,
        utilization_optimistic=0.8,
        average_ticket=25,
        operating_days_per_month=26,
    )

    with pytest.raises(TypeError):
        calculate_revenue(
            Sector.COFFEE,
            data,
        )