from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Type
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter

from sitescore.config.sectors import Sector
from sitescore.schemas.revenue_inputs import (
    BeautyRevenueInput,
    CoffeeRevenueInput,
    GymRevenueInput,
    RestaurantRevenueInput,
)
from sitescore_api.errors import IngressCommandValidationError
from sitescore_api.ingress import AnalysisIngressCommand, build_analysis_ingress_command
from sitescore_api.models import AnalysisRequest


ADAPTER = TypeAdapter(AnalysisRequest)


@pytest.mark.parametrize(
    "sector,expected_sector,expected_type",
    [
        ("coffee", Sector.COFFEE, CoffeeRevenueInput),
        ("restaurant", Sector.RESTAURANT, RestaurantRevenueInput),
        ("gym", Sector.GYM, GymRevenueInput),
        ("beauty", Sector.BEAUTY, BeautyRevenueInput),
    ],
)
def test_factory_constructs_exact_frozen_revenue_type(
    valid_payloads,
    sector: str,
    expected_sector: Sector,
    expected_type: Type,
):
    parsed = ADAPTER.validate_python(valid_payloads[sector])
    request_id = uuid4()
    analysis_id = uuid4()
    command = build_analysis_ingress_command(
        parsed,
        request_id=request_id,
        analysis_id=analysis_id,
    )
    assert command.request_id == request_id
    assert command.analysis_id == analysis_id
    assert command.request_id != command.analysis_id
    assert command.request_id.version == 4
    assert command.analysis_id.version == 4
    assert command.sector is expected_sector
    assert type(command.revenue_input) is expected_type
    assert command.monthly_rent == valid_payloads[sector]["costs"]["monthly_rent"]
    assert command.fixed_labor == valid_payloads[sector]["costs"]["fixed_labor"]
    assert command.fixed_overhead == valid_payloads[sector]["costs"]["fixed_overhead"]
    for key, value in valid_payloads[sector]["business_inputs"].items():
        assert getattr(command.revenue_input, key) == value


def test_external_pydantic_object_is_not_ingress_authority(valid_payloads):
    parsed = ADAPTER.validate_python(valid_payloads["coffee"])
    assert not isinstance(parsed, AnalysisIngressCommand)


def test_ingress_command_cannot_be_directly_constructed_without_server_token():
    with pytest.raises(TypeError):
        AnalysisIngressCommand(  # type: ignore[call-arg]
            request_id=uuid4(),
            analysis_id=uuid4(),
            address=None,
            sector=Sector.COFFEE,
            revenue_input=None,
            monthly_rent=0,
            fixed_labor=0,
            fixed_overhead=0,
        )


def test_ingress_command_is_immutable(valid_payloads):
    parsed = ADAPTER.validate_python(valid_payloads["coffee"])
    command = build_analysis_ingress_command(parsed, request_id=uuid4(), analysis_id=uuid4())
    with pytest.raises(FrozenInstanceError):
        command.monthly_rent = 1  # type: ignore[misc]


def test_non_uuid4_operational_identity_rejected(valid_payloads):
    parsed = ADAPTER.validate_python(valid_payloads["coffee"])
    with pytest.raises(IngressCommandValidationError):
        build_analysis_ingress_command(
            parsed,
            request_id=UUID("00000000-0000-1000-8000-000000000000"),
            analysis_id=uuid4(),
        )


def test_request_and_analysis_identity_must_be_distinct(valid_payloads):
    parsed = ADAPTER.validate_python(valid_payloads["coffee"])
    same = uuid4()
    with pytest.raises(IngressCommandValidationError):
        build_analysis_ingress_command(parsed, request_id=same, analysis_id=same)
