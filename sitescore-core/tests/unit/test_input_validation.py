import pytest

from sitescore.schemas.revenue_inputs import (
    CoffeeRevenueInput,
    RestaurantRevenueInput,
)


def test_coffee_rejects_invalid_capture_rate():
    with pytest.raises(ValueError):
        CoffeeRevenueInput(
            target_population=10000,
            target_rate=0.25,
            capture_rate_conservative=0.03,
            capture_rate_base=1.5,
            capture_rate_optimistic=0.07,
            visit_frequency_per_month=4,
            average_ticket=8,
        )


def test_coffee_rejects_reversed_scenarios():
    with pytest.raises(ValueError):
        CoffeeRevenueInput(
            target_population=10000,
            target_rate=0.25,
            capture_rate_conservative=0.08,
            capture_rate_base=0.05,
            capture_rate_optimistic=0.07,
            visit_frequency_per_month=4,
            average_ticket=8,
        )


def test_restaurant_rejects_invalid_utilization():
    with pytest.raises(ValueError):
        RestaurantRevenueInput(
            seats=50,
            turnover_per_day=2,
            utilization_conservative=0.4,
            utilization_base=0.6,
            utilization_optimistic=1.2,
            average_ticket=25,
            operating_days_per_month=26,
        )


def test_restaurant_rejects_zero_seats():
    with pytest.raises(ValueError):
        RestaurantRevenueInput(
            seats=0,
            turnover_per_day=2,
            utilization_conservative=0.4,
            utilization_base=0.6,
            utilization_optimistic=0.8,
            average_ticket=25,
            operating_days_per_month=26,
        )