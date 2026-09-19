from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import math

import pytest

from sitescore_data.validation import (
    SectorKey,
    require_aware_datetime,
    require_bounded_number,
    require_canonical_identifier,
    require_finite_number,
    require_latitude,
    require_longitude,
    require_nonnegative_number,
    require_positive_number,
)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_values_are_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        require_finite_number(value)


def test_bool_is_not_accepted_as_numeric() -> None:
    with pytest.raises(TypeError):
        require_finite_number(True)


def test_nonnegative_positive_and_bounded_validation() -> None:
    assert require_nonnegative_number(0) == 0
    assert require_positive_number(0.1) == 0.1
    assert require_bounded_number(100, low=0, high=100) == 100

    with pytest.raises(ValueError):
        require_nonnegative_number(-0.1)
    with pytest.raises(ValueError):
        require_positive_number(0)
    with pytest.raises(ValueError):
        require_bounded_number(101, low=0, high=100)


@pytest.mark.parametrize("value", [-90.0001, 90.0001, math.nan, math.inf, -math.inf])
def test_invalid_latitude_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        require_latitude(value)


@pytest.mark.parametrize("value", [-180.0001, 180.0001, math.nan, math.inf, -math.inf])
def test_invalid_longitude_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        require_longitude(value)


def test_valid_latitude_longitude_edges_are_accepted() -> None:
    assert require_latitude(-90.0) == -90.0
    assert require_latitude(90.0) == 90.0
    assert require_longitude(-180.0) == -180.0
    assert require_longitude(180.0) == 180.0


def test_naive_datetime_rejected() -> None:
    with pytest.raises(ValueError):
        require_aware_datetime(datetime(2026, 8, 12, 12, 0, 0))


def test_aware_datetime_accepted() -> None:
    value = datetime(2026, 8, 12, 12, 0, 0, tzinfo=timezone.utc)
    assert require_aware_datetime(value) is value


@pytest.mark.parametrize(
    "value",
    [
        "",
        " Coffee",
        "coffee ",
        "Coffee",
        "coffee shop",
        "coffee/shop",
        "_coffee",
        "coffee..shop",
        "çoffee",
    ],
)
def test_invalid_canonical_identifier_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        require_canonical_identifier(value)


@pytest.mark.parametrize(
    "value",
    ["coffee", "restaurant_v2", "fitness-center", "beauty.us", "sector2"],
)
def test_valid_canonical_identifier_accepted(value: str) -> None:
    assert require_canonical_identifier(value) == value


def test_sector_key_does_not_enforce_core_sector_vocabulary() -> None:
    key = SectorKey("future_sector")
    assert key.value == "future_sector"
    assert str(key) == "future_sector"


def test_sector_key_is_deterministic_and_immutable() -> None:
    left = SectorKey("coffee")
    right = SectorKey("coffee")
    assert left == right
    assert hash(left) == hash(right)

    with pytest.raises(FrozenInstanceError):
        left.value = "restaurant"  # type: ignore[misc]


def test_invalid_sector_key_rejected() -> None:
    with pytest.raises(ValueError):
        SectorKey("Coffee Shop")
