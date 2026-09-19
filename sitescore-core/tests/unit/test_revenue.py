import pytest

from sitescore.engines.revenue import (
    beauty_monthly_revenue,
    coffee_monthly_revenue,
    gym_monthly_revenue,
    restaurant_monthly_revenue,
    scenarios,
)


def test_coffee_monthly_frequency_has_no_operating_days_multiplier():
    revenue = coffee_monthly_revenue(10_000, 0.4, 0.02, 8, 8)
    assert revenue == pytest.approx(5_120.0)


def test_gym_bottleneck_uses_minimum():
    revenue = gym_monthly_revenue(10_000, 0.05, 500, 0.5, 50)
    # market potential = 500, physical capacity = 250
    assert revenue == pytest.approx(12_500.0)


def test_restaurant_revenue():
    revenue = restaurant_monthly_revenue(100, 2.0, 0.65, 30, 26)
    assert revenue == pytest.approx(101_400.0)


def test_beauty_revenue():
    revenue = beauty_monthly_revenue(5, 40, 1.0, 0.60, 50)
    assert revenue == pytest.approx(25_980.0)


def test_scenario_order_required():
    with pytest.raises(ValueError):
        scenarios(100, 90, 200)
