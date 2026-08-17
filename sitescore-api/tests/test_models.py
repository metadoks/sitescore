from __future__ import annotations

from copy import deepcopy
from typing import get_args

import pytest
from pydantic import TypeAdapter, ValidationError

from sitescore_api.models import AnalysisRequest


ADAPTER = TypeAdapter(AnalysisRequest)


def test_all_four_sector_payloads_validate(valid_payloads):
    for sector, payload in valid_payloads.items():
        parsed = ADAPTER.validate_python(payload)
        assert parsed.sector == sector


@pytest.mark.parametrize(
    "field,value",
    [
        ("category_scores", {"demand": 100}),
        ("location_score", 99),
        ("decision", "Prime Opportunity"),
        ("confidence", 100),
        ("analysis_fingerprint", "fake"),
        ("readiness_fingerprint", "fake"),
        ("score_ready", True),
        ("trusted", True),
        ("force", True),
        ("geographic_level", "block"),
        ("data_age_years", 0),
        ("data_coverage", 1),
        ("input_qualities", {}),
        ("provider_manifest", {}),
        ("benchmark", "fake"),
        ("vintage", "2025"),
        ("source_refs", []),
        ("artifact_refs", []),
    ],
)
def test_root_authority_injection_rejected(valid_payloads, field, value):
    payload = deepcopy(valid_payloads["coffee"])
    payload[field] = value
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_unknown_nested_field_rejected(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["business_inputs"]["mystery"] = 1
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_provider_authority_nested_in_location_rejected(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["location"]["resolved_latitude"] = 30.26
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_sector_business_subtype_mismatch_rejected(valid_payloads):
    payload = deepcopy(valid_payloads["restaurant"])
    payload["sector"] = "coffee"
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_rejected(valid_payloads, bad):
    payload = deepcopy(valid_payloads["coffee"])
    payload["business_inputs"]["average_ticket"] = bad
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_bool_as_numeric_rejected(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["business_inputs"]["target_population"] = True
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_numeric_string_coercion_rejected(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["business_inputs"]["target_population"] = "50000"
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_invalid_rate_ordering_rejected(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["business_inputs"]["capture_rate_conservative"] = 0.04
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_negative_common_cost_rejected(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["costs"]["monthly_rent"] = -1
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


@pytest.mark.parametrize(
    "location",
    [
        {"country_code": "US", "street": "123 Main"},
        {"country_code": "US", "street": "   ", "zip_code": "78701"},
        {"country_code": "US", "street": "123 Main", "city": "Austin"},
    ],
)
def test_invalid_us_address_shape_rejected(valid_payloads, location):
    payload = deepcopy(valid_payloads["coffee"])
    payload["location"] = location
    with pytest.raises((ValidationError, TypeError)):
        ADAPTER.validate_python(payload)


def test_non_us_country_rejected(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["location"]["country_code"] = "TR"
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_zip_only_address_is_valid(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["location"] = {
        "country_code": "US",
        "street": "123 Main St",
        "zip_code": "78701",
    }
    parsed = ADAPTER.validate_python(payload)
    assert parsed.location.zip_code == "78701"


def test_strings_are_trimmed(valid_payloads):
    payload = deepcopy(valid_payloads["coffee"])
    payload["location"]["street"] = "  123 Main St  "
    parsed = ADAPTER.validate_python(payload)
    assert parsed.location.street == "123 Main St"
