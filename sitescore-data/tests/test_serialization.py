from datetime import date, datetime, timezone
import math

import pytest

from sitescore_data.enums import (
    AvailabilityState,
    CalibrationState,
    DataQualityState,
    ScoreEligibility,
)
from sitescore_data.schemas.common import MetricValue
from sitescore_data.serialization import to_primitive


def make_metric() -> MetricValue:
    return MetricValue(
        value=0,
        unit="count",
        availability=AvailabilityState.AVAILABLE,
        data_quality=DataQualityState.FULL,
        score_eligibility=ScoreEligibility.ELIGIBLE,
        calibration_state=CalibrationState.CALIBRATED,
        is_estimate=False,
        is_proxy=False,
        source_refs=("source_one", "source_two"),
        method_version="metric-v1",
        reason_codes=("observed_zero",),
    )


def test_deterministic_dataclass_serialization() -> None:
    left = to_primitive(make_metric())
    right = to_primitive(make_metric())
    assert left == right
    assert list(left.keys()) == [
        "value",
        "unit",
        "availability",
        "data_quality",
        "score_eligibility",
        "calibration_state",
        "is_estimate",
        "is_proxy",
        "source_refs",
        "method_version",
        "reason_codes",
    ]


def test_enum_serialization_uses_stable_value() -> None:
    assert to_primitive(AvailabilityState.UNKNOWN) == "unknown"


def test_tuple_serialization_preserves_order() -> None:
    assert to_primitive(("b", "a", "c")) == ["b", "a", "c"]


def test_date_serialization() -> None:
    assert to_primitive(date(2026, 8, 12)) == "2026-08-12"


def test_aware_datetime_serialization() -> None:
    value = datetime(2026, 8, 12, 12, 30, tzinfo=timezone.utc)
    assert to_primitive(value) == "2026-08-12T12:30:00+00:00"


def test_naive_datetime_serialization_rejected() -> None:
    with pytest.raises(ValueError):
        to_primitive(datetime(2026, 8, 12, 12, 30))


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_serializer_rejects_nonfinite_float(value: float) -> None:
    with pytest.raises(ValueError):
        to_primitive(value)


def test_serializer_rejects_mutable_collections() -> None:
    with pytest.raises(TypeError):
        to_primitive([1, 2, 3])
    with pytest.raises(TypeError):
        to_primitive({"a": 1})
    with pytest.raises(TypeError):
        to_primitive({1, 2})
