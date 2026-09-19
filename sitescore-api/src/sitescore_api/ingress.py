from __future__ import annotations

from dataclasses import dataclass
from typing import Union
from uuid import UUID

from sitescore.config.sectors import Sector
from sitescore.schemas.revenue_inputs import (
    BeautyRevenueInput,
    CoffeeRevenueInput,
    GymRevenueInput,
    RestaurantRevenueInput,
)

from .errors import IngressCommandValidationError
from .models import (
    AnalysisRequest,
    BeautyAnalysisRequest,
    CoffeeAnalysisRequest,
    GymAnalysisRequest,
    RestaurantAnalysisRequest,
)

RevenueInput = Union[
    CoffeeRevenueInput,
    RestaurantRevenueInput,
    GymRevenueInput,
    BeautyRevenueInput,
]

_INGRESS_FACTORY_TOKEN = object()


@dataclass(frozen=True, slots=True)
class AddressIntent:
    country_code: str
    street: str
    city: str | None
    state: str | None
    zip_code: str | None


@dataclass(frozen=True, slots=True, init=False)
class AnalysisIngressCommand:
    request_id: UUID
    analysis_id: UUID
    address: AddressIntent
    sector: Sector
    revenue_input: RevenueInput
    monthly_rent: float
    fixed_labor: float
    fixed_overhead: float

    def __init__(
        self,
        *,
        request_id: UUID,
        analysis_id: UUID,
        address: AddressIntent,
        sector: Sector,
        revenue_input: RevenueInput,
        monthly_rent: float,
        fixed_labor: float,
        fixed_overhead: float,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _INGRESS_FACTORY_TOKEN:
            raise TypeError("AnalysisIngressCommand is server-factory owned")
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "analysis_id", analysis_id)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "sector", sector)
        object.__setattr__(self, "revenue_input", revenue_input)
        object.__setattr__(self, "monthly_rent", monthly_rent)
        object.__setattr__(self, "fixed_labor", fixed_labor)
        object.__setattr__(self, "fixed_overhead", fixed_overhead)


def _require_uuid4(value: UUID, field_name: str) -> None:
    if value.version != 4:
        raise IngressCommandValidationError(f"{field_name} must be UUIDv4")


def build_analysis_ingress_command(
    request: AnalysisRequest,
    *,
    request_id: UUID,
    analysis_id: UUID,
) -> AnalysisIngressCommand:
    _require_uuid4(request_id, "request_id")
    _require_uuid4(analysis_id, "analysis_id")
    if request_id == analysis_id:
        raise IngressCommandValidationError("request_id and analysis_id must be distinct")

    if isinstance(request, CoffeeAnalysisRequest):
        sector = Sector.COFFEE
        business = request.business_inputs
        revenue_input: RevenueInput = CoffeeRevenueInput(**business.model_dump())
    elif isinstance(request, RestaurantAnalysisRequest):
        sector = Sector.RESTAURANT
        business = request.business_inputs
        revenue_input = RestaurantRevenueInput(**business.model_dump())
    elif isinstance(request, GymAnalysisRequest):
        sector = Sector.GYM
        business = request.business_inputs
        revenue_input = GymRevenueInput(**business.model_dump())
    elif isinstance(request, BeautyAnalysisRequest):
        sector = Sector.BEAUTY
        business = request.business_inputs
        revenue_input = BeautyRevenueInput(**business.model_dump())
    else:
        raise IngressCommandValidationError("unsupported analysis request variant")

    if request.sector != sector.value:
        raise IngressCommandValidationError("sector/business input mismatch")

    address = AddressIntent(
        country_code=request.location.country_code,
        street=request.location.street,
        city=request.location.city,
        state=request.location.state,
        zip_code=request.location.zip_code,
    )
    costs = request.costs

    return AnalysisIngressCommand(
        request_id=request_id,
        analysis_id=analysis_id,
        address=address,
        sector=sector,
        revenue_input=revenue_input,
        monthly_rent=costs.monthly_rent,
        fixed_labor=costs.fixed_labor,
        fixed_overhead=costs.fixed_overhead,
        _factory_token=_INGRESS_FACTORY_TOKEN,
    )
